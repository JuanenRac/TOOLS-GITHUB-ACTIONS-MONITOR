#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Shared helpers of the container checks in tools/docker_audit/ (standard library only).

A check is a small program (e1_*.py ... e8_*.py) that builds or reuses the image of a checkout, starts real containers, asks them questions and writes two files, `<code>.json` and
`<code>.txt`, with every command it ran, what came back and one verdict: PASS, FAIL or NO-APLICA (not applicable, with the reason). The exit code is 0 unless a check failed.
It needs Docker (and the Docker Compose plugin for the proxy checks) and nothing else: no secret, no registry login, no network service of the monitor owner.
"""
import argparse
import http.client
import json
import os
import re
import secrets
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FAKE_GH = REPO / "deploy" / "test" / "fake_gh.py"
CLIENT = HERE / "client.py"
PASS, FAIL, NA = "PASS", "FAIL", "NO-APLICA"
CADDY_IMAGE = os.environ.get("CADDY_IMAGE", "caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d")
OUTPUT_LIMIT = 6000
LABEL = "docker-audit=1"


def clip(text, limit=OUTPUT_LIMIT):
    text = text if isinstance(text, str) else str(text)
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n[... %d characters left out ...]\n" % (len(text) - limit) + text[-half:]


def http_request(port, method, path, headers=None, body=None, host="127.0.0.1", tls=False, timeout=20):
    """One request from this machine. Returns {"status", "headers", "body"}; status 0 = no answer (the reason is in body)."""
    if tls:
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ssl._create_unverified_context())      # noqa: S323 - a throw-away certificate of a test
    else:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        answer = conn.getresponse()
        raw = answer.read(65536)
        return {"status": answer.status, "headers": answer.getheaders(), "body": raw.decode("utf-8", "replace")}
    except (OSError, http.client.HTTPException) as error:
        return {"status": 0, "headers": [], "body": "%s: %s" % (type(error).__name__, error)}
    finally:
        conn.close()


def header(answer, name):
    """All the values of a response header (case-insensitive) joined with a newline."""
    return "\n".join(v for k, v in answer.get("headers", []) if k.lower() == name.lower())


def jbody(answer):
    try:
        return json.loads(answer.get("body") or "")
    except ValueError:
        return None


class Scenario:
    """One check: the commands it runs, the checks it makes, the verdict."""

    def __init__(self, code, title, argv=None, description=""):
        parser = argparse.ArgumentParser(prog=code.lower(), description=description or title)
        parser.add_argument("--target", default=str(REPO), help="a checkout of the version to check (default: this repository)")
        parser.add_argument("--out", default="docker-audit-out", help="folder for the result files")
        parser.add_argument("--ref", default="", help="name of the version, only for the report (default: the name of the target folder)")
        parser.add_argument("--image", default="", help="an image that is already built (default: build it from the target)")
        parser.add_argument("--previous", default="", help="a checkout of the previous version (the migration check builds its image from it)")
        parser.add_argument("--keep", action="store_true", help="leave the containers, volumes and networks in place at the end (to look at them)")
        self.args = parser.parse_args(argv)
        self.code, self.title = code, title
        self.target = Path(self.args.target).resolve()
        self.out = Path(self.args.out).resolve()
        self.ref = self.args.ref or self.target.name
        self.work = Path(tempfile.mkdtemp(prefix="docker-audit-%s-" % code.lower()))
        self.suffix = secrets.token_hex(3)
        self.steps, self.checks, self.notes, self.environment = [], [], [], {}
        self.skipped = ""
        self.redact = {}
        self.containers, self.volumes, self.networks, self.compose = [], [], [], []
        self.started = time.time()

    # --- records -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def secret(self, value, label):
        """A value that must never appear in the result files (a throw-away secret of this run)."""
        self.redact[value] = "<%s>" % label
        return value

    def scrub(self, text):
        for value, label in self.redact.items():
            if value:
                text = text.replace(value, label)
        return text

    def say(self, line):
        print(self.scrub(line), flush=True)

    def check(self, name, ok, evidence=""):
        ok = bool(ok)
        self.checks.append({"name": name, "ok": ok, "evidence": clip(self.scrub(str(evidence)), 1500)})
        self.say("%s  %s%s" % ("ok   " if ok else "FAIL ", name, "" if ok or not evidence else "  <- " + clip(self.scrub(str(evidence)), 300).replace("\n", " | ")))
        return ok

    def note(self, text):
        """Something worth reading that does not change the verdict."""
        self.notes.append(self.scrub(text))
        self.say("note  " + text)

    def skip(self, reason):
        self.skipped = reason
        self.say("skip  " + reason)

    def run(self, cmd, timeout=180, input_text=None, label="", env=None, record=True):
        """Runs a command, records it with its output, returns (exit code, output)."""
        shown = self.scrub(shlex.join(str(c) for c in cmd))
        started = time.time()
        try:
            done = subprocess.run([str(c) for c in cmd], input=input_text, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env, check=False)
            code, output = done.returncode, (done.stdout or "") + (done.stderr or "")
        except subprocess.TimeoutExpired as error:
            code, output = 124, "timeout after %ss\n%s" % (timeout, (error.stdout or b"").decode("utf-8", "replace") if isinstance(error.stdout, bytes) else (error.stdout or ""))
        except OSError as error:
            code, output = 127, str(error)
        if record:
            self.steps.append({"label": label or shown[:80], "command": shown, "exit": code, "seconds": round(time.time() - started, 1), "output": clip(self.scrub(output))})
        return code, output

    def docker(self, *args, **kw):
        return self.run(["docker", *args], **kw)

    # --- environment -------------------------------------------------------------------------------------------------------------------------------------------------------------
    def describe_environment(self):
        for key, cmd in (("docker", ["docker", "version", "--format", "client {{.Client.Version}} / server {{.Server.Version}}"]), ("compose", ["docker", "compose", "version", "--short"]),
                         ("kernel", ["uname", "-sr"])):
            code, out = self.run(cmd, timeout=30, record=False)
            self.environment[key] = out.strip()[:200] if code == 0 else "not available"
        self.environment["target"] = str(self.target.name)
        self.environment["caddy_image"] = CADDY_IMAGE

    def base_digests(self, *names):
        for name in names:
            code, out = self.run(["docker", "image", "inspect", name, "--format", "{{json .RepoDigests}}"], timeout=30, record=False)
            self.environment["base:" + name] = out.strip() if code == 0 else "not present"

    # --- images and containers -----------------------------------------------------------------------------------------------------------------------------------------------------
    def build_image(self, src, tag, version):
        code, out = self.docker("build", "-f", str(Path(src) / "deploy" / "Dockerfile"), "--build-arg", "VERSION=" + version, "-t", tag, str(src), timeout=1500, label="docker build " + tag)
        self.check("the image of %s builds" % version, code == 0, out[-800:] if code else "")
        return code == 0

    def image(self):
        """The image to check: the one given, or the one built from the target (once)."""
        if self.args.image:
            return self.args.image
        tag = "docker-audit/monitor:%s-%s" % (re.sub(r"[^a-z0-9_.-]", "-", self.ref.lower()), self.suffix)
        if not getattr(self, "_built", False):
            if not self.build_image(self.target, tag, self.ref):
                raise SystemExit(self.finish())
            self._built = tag
        return self._built

    def name(self, what):
        return "audit-%s-%s-%s" % (self.code.lower(), what, self.suffix)

    def file(self, name, content, mode=0o644):
        """A file in the work folder, readable by the user 10001 of the container (bind mounts keep the mode of the host)."""
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8", newline="\n")
        path.chmod(mode)
        return path

    def fake_gh(self):
        """The folder with the stand-in for `gh` (answers like GitHub from a list of good tokens) and the list itself. Returns (gh path, list path)."""
        folder = self.work / "fake"
        folder.mkdir(exist_ok=True)
        gh = folder / "gh"
        gh.write_text(FAKE_GH.read_text(encoding="utf-8").replace("\r\n", "\n"), encoding="utf-8", newline="\n")
        gh.chmod(0o755)
        good = folder / "good"
        return gh, good

    def login_files(self, owner="audit-owner"):
        """The login of GitHub the way the guide wants it (a file, a Docker secret) with the stand-in `gh`. Returns (bind mounts, environment, the throw-away token)."""
        token = self.secret("ghp_" + secrets.token_hex(18), "github-token")
        gh, good = self.fake_gh()
        good.write_text(token + "\n", encoding="utf-8", newline="\n")
        good.chmod(0o644)
        secret_file = self.file("secrets/gh_token", token)
        mounts = ["%s:/usr/local/bin/gh:ro" % gh, "%s:/fake/good:ro" % good, "%s:/run/secrets/gh_token:ro" % secret_file]
        return mounts, {"MONITOR_GITHUB_OWNER": owner, "GH_TOKEN_FILE": "/run/secrets/gh_token", "FAKE_GH_GOOD": "/fake/good"}, token

    def volume(self, what):
        name = self.name(what)
        self.docker("volume", "create", "--label", LABEL, name, record=False)
        self.volumes.append(name)
        return name

    def service(self, what, image, volumes=(), env=None, ports=(), extra=(), network=None, ip=None, detach=True, entry=None, command=()):
        """Starts the container the way the guide says: read-only, no capabilities, no new privileges, /tmp in memory."""
        name = self.name(what)
        cmd = ["run", "--name", name, "--label", LABEL, "--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true"]
        cmd += ["-d"] if detach else []
        for volume in volumes:
            cmd += ["-v", volume]
        for key, value in (env or {}).items():
            cmd += ["-e", "%s=%s" % (key, value)]
        for port in ports:
            cmd += ["-p", port]
        if network:
            cmd += ["--network", network] + (["--ip", ip] if ip else [])
        cmd += list(extra)
        if entry:
            cmd += ["--entrypoint", entry]
        cmd += [image, *command]
        code, out = self.docker(*cmd, label="start %s" % what, timeout=300)
        if code == 0:
            self.containers.append(name)
        return name, code, out

    def health(self, name):
        code, out = self.run(["docker", "inspect", "-f", "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}", name], timeout=30, record=False)
        return out.strip() if code == 0 else "gone"

    def wait_healthy(self, name, limit=180):
        end = time.time() + limit
        status = ""
        while time.time() < end:
            status = self.health(name)
            if status in ("healthy", "gone"):
                break
            code, out = self.run(["docker", "inspect", "-f", "{{.State.Status}}", name], timeout=30, record=False)
            if code == 0 and out.strip() in ("exited", "dead"):
                status = "exited"
                break
            time.sleep(3)
        self.steps.append({"label": "wait for %s to be healthy" % name, "command": "docker inspect (health) until healthy", "exit": 0 if status == "healthy" else 1, "seconds": 0, "output": "health: " + status})
        return status == "healthy"

    def logs(self, name):
        return self.run(["docker", "logs", name], timeout=60, record=False)[1]

    def python_in(self, name, code, timeout=60, user=None, label="python in container"):
        """Runs a short Python program inside a running container; returns (exit code, output)."""
        cmd = ["docker", "exec"] + (["-u", user] if user else []) + [name, "python", "-c", code]
        return self.run(cmd, timeout=timeout, label=label)

    def read_token(self, name):
        code, out = self.run(["docker", "exec", name, "cat", "/data/state/access_token"], timeout=30, record=False)
        token = out.strip() if code == 0 else ""
        if token:
            self.secret(token, "access-token")
        return token

    def client(self, network, ip, image, requests, timeout=240, extra_mounts=()):
        """Sends a batch of requests from a throw-away container on `network` with address `ip` (see client.py). Returns the list of results."""
        payload = json.dumps({"requests": requests})
        cmd = ["docker", "run", "--rm", "-i", "--label", LABEL, "--network", network, "--ip", ip, "-v", "%s:/client.py:ro" % CLIENT] + [x for m in extra_mounts for x in ("-v", m)] + ["--entrypoint", "python", image, "/client.py"]
        code, out = self.run(cmd, input_text=payload, timeout=timeout, label="client %s: %s" % (ip, ", ".join("%s %s" % (r.get("method", "GET"), r["url"][:60]) for r in requests[:3])))
        try:
            return json.loads(out[out.index("["):out.rindex("]") + 1])
        except ValueError:
            self.check("the client container answered", False, out[-600:])
            return [{"count": 0, "statuses": {}, "first": {"status": 0, "headers": [], "body": ""}, "last": {"status": 0, "headers": [], "body": ""}, "first_index": {}} for _ in requests]

    # --- the end -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def cleanup(self):
        if self.args.keep:
            self.say("--keep: leaving %d containers, %d volumes, %d networks and the folder %s" % (len(self.containers), len(self.volumes), len(self.networks), self.work))
            return
        for project, compose_files, env_file in self.compose:
            cmd = ["docker", "compose", "-p", project]
            for item in compose_files:
                cmd += ["-f", str(item)]
            self.run(cmd + ["--profile", "proxy", "down", "-v", "--remove-orphans", "-t", "5"], timeout=180, record=False)
        for name in reversed(self.containers):
            self.run(["docker", "rm", "-f", "-v", name], timeout=60, record=False)
        for name in self.networks:
            self.run(["docker", "network", "rm", name], timeout=60, record=False)
        for name in self.volumes:
            self.run(["docker", "volume", "rm", "-f", name], timeout=60, record=False)
        shutil.rmtree(self.work, ignore_errors=True)

    def verdict(self):
        if any(not c["ok"] for c in self.checks):
            return FAIL
        if self.skipped and not self.checks:
            return NA
        return PASS if self.checks else NA

    def finish(self):
        verdict = self.verdict()
        self.out.mkdir(parents=True, exist_ok=True)
        record = {"scenario": self.code, "title": self.title, "ref": self.ref, "verdict": verdict, "reason": self.skipped, "seconds": round(time.time() - self.started, 1), "environment": self.environment,
                  "checks": self.checks, "notes": self.notes, "steps": self.steps}
        (self.out / ("%s.json" % self.code)).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        lines = ["%s - %s" % (self.code, self.title), "version checked: %s" % self.ref, "VERDICT: %s%s" % (verdict, "  (%s)" % self.skipped if self.skipped else ""), "", "Environment"]
        lines += ["  %s: %s" % (k, v) for k, v in self.environment.items()]
        lines += ["", "Checks"] + ["  [%s] %s%s" % ("ok  " if c["ok"] else "FAIL", c["name"], "" if c["ok"] or not c["evidence"] else "\n         evidence: " + c["evidence"].replace("\n", "\n         ")) for c in self.checks]
        if self.notes:
            lines += ["", "Notes"] + ["  - " + n for n in self.notes]
        lines += ["", "Commands"]
        for index, step in enumerate(self.steps, 1):
            lines += ["", "[%d] %s  (exit %s, %ss)" % (index, step["command"], step["exit"], step["seconds"])] + ["    " + row for row in step["output"].splitlines()[:80]]
        (self.out / ("%s.txt" % self.code)).write_text(self.scrub("\n".join(lines)) + "\n", encoding="utf-8")
        self.say("%s=%s" % (self.code, verdict))
        return 0 if verdict != FAIL else 1


def main_of(code, title, body, description=""):
    """Runs `body(scenario)`; whatever it raises is a failure of the script, reported as such, and the containers are always removed."""
    scenario = Scenario(code, title, description=description)
    try:
        scenario.describe_environment()
        body(scenario)
    except SystemExit:
        pass
    except Exception:      # noqa: BLE001 - the report must be written whatever happens
        scenario.check("the script of this check ran to the end (SCRIPT-ERROR)", False, traceback.format_exc()[-1500:])
    finally:
        scenario.cleanup()
    return scenario.finish()
