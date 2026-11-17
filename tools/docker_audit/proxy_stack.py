#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor behind Caddy, started with the Docker Compose file of the version under check (deploy/compose.yaml, profile `proxy`), used by the proxy and webhook checks.

Only three things differ from a real installation, and all three are on purpose: `tls internal` is switched on in the copy of the Caddyfile (a name of a private network), the login of GitHub
is the stand-in `gh` (the monitor never calls GitHub), and the Caddy image is the one named by CADDY_IMAGE (a tag and a digest). The login is written exactly as the guide says (a file with
mode 600), so a guide that does not work shows up here. Clients are throw-away containers with fixed addresses on the network of the Compose project.
"""
import json
import os
import shutil
import time

import audit_lib as lib

SUBNET = "172.29.77.0/24"
CLIENT_A, CLIENT_B, CLIENT_C, CLIENT_D = "172.29.77.50", "172.29.77.51", "172.29.77.52", "172.29.77.53"
SITE = "audit.test"


class Stack:
    def __init__(self, s, image):
        self.s, self.image = s, image
        self.project = "audit%s" % s.suffix
        self.dir = s.work / "stack"
        self.deploy = self.dir / "deploy"
        self.network = self.project + "_default"
        self.token = ""
        self.env = {}

    def compose_cmd(self):
        return ["docker", "compose", "-p", self.project, "-f", str(self.deploy / "compose.yaml"), "-f", str(self.deploy / "audit.override.yaml"), "--profile", "proxy"]

    def write(self, extra_env=None, extra_secrets=None, trusted=True):
        """Copies deploy/ of the target, writes .env, the override and the secret files. `extra_env` goes to the monitor container, `extra_secrets` is {name: value} (files mounted in /run/secrets)."""
        s = self.s
        shutil.copytree(s.target / "deploy", self.deploy, ignore=shutil.ignore_patterns("test"), dirs_exist_ok=True)
        caddyfile = self.deploy / "Caddyfile"
        text = caddyfile.read_text(encoding="utf-8").replace("\r\n", "\n")
        caddyfile.write_text(text.replace("\t# tls internal", "\ttls internal"), encoding="utf-8", newline="\n")
        gh, good = s.fake_gh()
        token = s.secret("ghp_" + __import__("secrets").token_hex(18), "github-token")
        (self.deploy / "fake").mkdir(exist_ok=True)
        shutil.copy(gh, self.deploy / "fake" / "gh")
        (self.deploy / "fake" / "gh").chmod(0o755)
        (self.deploy / "fake" / "good").write_text(token + "\n", encoding="utf-8", newline="\n")
        (self.deploy / "fake" / "good").chmod(0o644)
        login = self.deploy / "gh_token.txt"
        login.write_text(token, encoding="utf-8", newline="\n")
        login.chmod(0o600)      # exactly what the guide says: the login is a file with mode 600
        if os.name == "posix":      # and, like the guide, given to the user of the container (10001): a file of mode 600 that belongs to somebody else cannot be read in it
            s.run(["sudo", "-n", "chown", "10001:10001", str(login)], timeout=60, label="give the login file to the user of the container", record=False)
        self.login_file, self.github_token = login, token
        (self.deploy / "secrets").mkdir(exist_ok=True)
        names = []
        for name, value in (extra_secrets or {}).items():
            path = self.deploy / "secrets" / name
            path.write_text(value + "\n", encoding="utf-8", newline="\n")
            path.chmod(0o644)
            names.append(name)
        self.env = {"MONITOR_GITHUB_OWNER": "audit-owner", "MONITOR_IMAGE": self.image, "MONITOR_SITE": SITE, "MONITOR_PUBLIC_HOST": SITE, "MONITOR_SECURE_COOKIE": "1",
                    "MONITOR_TRUSTED_PROXY": "1" if trusted is True else ("0" if trusted == "off" else ""), "MONITOR_TRUSTED_PROXIES": SUBNET if trusted is True else "", "MONITOR_SUBNET": SUBNET, "MONITOR_PORT": "8765",
                    "AUDIT_CADDY_IMAGE": lib.CADDY_IMAGE}
        (self.deploy / ".env").write_text("".join("%s=%s\n" % kv for kv in self.env.items()), encoding="utf-8", newline="\n")
        env_lines = ["      FAKE_GH_GOOD: /fake/good"] + ["      %s: %s" % (k, json.dumps(v)) for k, v in (extra_env or {}).items()]
        override = ["services:", "  monitor:", "    environment:", *env_lines, "    volumes:", "      - ./fake/gh:/usr/local/bin/gh:ro", "      - ./fake/good:/fake/good:ro"]
        if names:
            override += ["    secrets:"] + ["      - %s" % n for n in names]
        override += ["  caddy:", "    image: ${AUDIT_CADDY_IMAGE}", "    networks:", "      default:", "        aliases:", "          - %s" % SITE]
        if names:
            override += ["secrets:"] + ["  %s:" % n + "\n    file: ./secrets/%s" % n for n in names]
        (self.deploy / "audit.override.yaml").write_text("\n".join(override) + "\n", encoding="utf-8", newline="\n")
        s.compose.append((self.project, [self.deploy / "compose.yaml", self.deploy / "audit.override.yaml"], None))

    def up(self, timeout=420):
        code, out = self.s.run(self.compose_cmd() + ["up", "-d", "--no-build", "--wait", "--wait-timeout", "300"], timeout=timeout, label="docker compose --profile proxy up")
        return code == 0, out

    def container(self, service):
        code, out = self.s.run(self.compose_cmd() + ["ps", "-q", service], timeout=60, record=False)
        return out.strip().splitlines()[0] if code == 0 and out.strip() else ""

    def prepare_client(self):
        """The access token and the root certificate of Caddy's own authority, ready for the clients."""
        s = self.s
        monitor = self.container("monitor")
        self.token = s.read_token(monitor)
        caddy = self.container("caddy")
        self.root = self.dir / "root.crt"
        for _ in range(30):
            code, _out = s.run(["docker", "cp", "%s:/data/caddy/pki/authorities/local/root.crt" % caddy, str(self.root)], timeout=30, record=False)
            if code == 0:
                break
            time.sleep(2)
        self.root.chmod(0o644) if self.root.exists() else None
        return monitor, caddy

    def request(self, ip, specs, timeout=240):
        """Requests from the client container with address `ip`; the root certificate of Caddy is mounted at /root.crt."""
        return self.s.client(self.network, ip, self.image, specs, timeout=timeout, extra_mounts=["%s:/root.crt:ro" % self.root])

    def wait_proxy(self, limit=90):
        end = time.time() + limit
        result = None
        while time.time() < end:
            result = self.request(CLIENT_A, [{"url": "https://%s/login" % SITE, "ca": "/root.crt"}])[0]
            if result["first"]["status"] in (200, 401, 403):
                return True, result
            time.sleep(3)
        return False, result

    def account_state(self):
        answer = lib.http_request(8765, "GET", "/api/accounts", {"Host": "127.0.0.1:8765", "X-Monitor-Access": self.token})
        data = lib.jbody(answer) or {}
        accounts = data.get("accounts") if isinstance(data, dict) else None
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            accounts = data["data"].get("accounts")
        return (accounts or [{}])[0].get("state", "?"), answer
