#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E3 - behind a trusted proxy: Caddy with its own TLS in front of the monitor, started with the Compose file of the version. Host and Origin, the Secure cookie, the routes that need the
access token, a client that lies in X-Forwarded-For, and what happens when the proxy is not declared."""
import json
import sys

import audit_lib as lib
import proxy_stack as ps

JSON = {"Content-Type": "application/json", "Origin": "https://%s" % ps.SITE}


def access(token, extra=None, repeat=1, origin="https://%s" % ps.SITE):
    return {"method": "POST", "url": "https://%s/api/access" % ps.SITE, "ca": "/root.crt", "headers": dict(JSON, Origin=origin, **(extra or {})), "body": {"json": {"token": token}}, "repeat": repeat}


def body(s):
    image = s.image()
    s.base_digests("python:3.13-slim", lib.CADDY_IMAGE.split("@")[0])
    stack = ps.Stack(s, image)
    stack.write(trusted=True)
    ok, out = stack.up()
    if not s.check("docker compose --profile proxy up brings the monitor (healthy) and Caddy up", ok, out[-1500:]):
        return
    monitor, caddy = stack.prepare_client()
    s.check("the access token of the first start can be read", len(stack.token) >= 16, "")
    state, answer = stack.account_state()
    if state != "ok":
        s.check("the login written as the guide says (a file with mode 600, a Docker secret) is readable by the monitor in the container", False,
                "state of the account: %s; %s %s (the container runs as user 10001, the file belongs to the user of the host)" % (state, answer["status"], answer["body"][:200]))
        stack.login_file.chmod(0o644)
        s.run(stack.compose_cmd() + ["restart", "monitor"], timeout=240)
        s.wait_healthy(monitor, 180)
    else:
        s.check("the login written as the guide says (a file with mode 600, a Docker secret) is readable by the monitor in the container", True)
    ready, first = stack.wait_proxy()
    s.check("Caddy answers over HTTPS for %s" % ps.SITE, ready, json.dumps(first)[:400] if first else "")
    login = stack.request(ps.CLIENT_A, [{"url": "https://%s/login" % ps.SITE, "ca": "/root.crt"}])[0]["first"]
    s.check("the certificate of Caddy's own authority verifies for %s (TLS internal)" % ps.SITE, login["status"] != 0, login["body"][:300])

    # the routes of the contract, with no token, through the proxy: none may answer
    contract = json.loads((s.target / "monitor" / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
    paths = [row["path"] for row in contract["endpoints"]]
    results = stack.request(ps.CLIENT_D, [{"url": "https://%s%s" % (ps.SITE, p), "ca": "/root.crt", "headers": {"Origin": "https://%s" % ps.SITE}} for p in paths], timeout=300)
    open_paths = [p for p, r in zip(paths, results) if r["first"]["status"] not in (401, 403, 429)]
    s.check("none of the %d read routes of the contract answers without the access token (401/403; 429 once the address is locked)" % len(paths), not open_paths and results[0]["first"]["status"] in (401, 403),
            "answered: " + ", ".join("%s=%s" % (p, results[paths.index(p)]["first"]["status"]) for p in open_paths))
    s.note("requests without any token from one address: %s (a missing token counts as a failed attempt, so the address is locked after a few)" % {k: sum(r["statuses"].get(k, 0) for r in results) for k in ("401", "403", "429")})
    page = stack.request(ps.CLIENT_D, [{"url": "https://%s/" % ps.SITE, "ca": "/root.crt"}, {"url": "https://%s/api/ai/stream" % ps.SITE, "ca": "/root.crt", "timeout": 8}])
    s.check("the page and the stream of the AI tools need the token too", page[0]["first"]["status"] in (401, 403, 429) and page[1]["first"]["status"] in (401, 403, 429), "page %s, stream %s" % (page[0]["first"]["status"], page[1]["first"]["status"]))

    # Host, Origin and the Secure cookie
    good = stack.request(ps.CLIENT_A, [access(stack.token)])[0]["first"]
    cookie = lib.header(good, "Set-Cookie")
    s.check("POST /api/access with the right token through the proxy gives a cookie", good["status"] == 200 and cookie != "", "%s %s" % (good["status"], good["body"][:200]))
    s.check("the cookie is Secure, HttpOnly and SameSite=Strict", all(x in cookie for x in ("Secure", "HttpOnly", "SameSite=Strict")), cookie)
    session = cookie.split(";")[0]
    health = stack.request(ps.CLIENT_A, [{"url": "https://%s/api/health" % ps.SITE, "ca": "/root.crt", "headers": {"Cookie": session}}])[0]["first"]
    s.check("the cookie opens /api/health through the proxy", health["status"] == 200, "%s %s" % (health["status"], health["body"][:200]))
    cross = stack.request(ps.CLIENT_A, [access(stack.token, origin="http://%s" % ps.SITE), access(stack.token, origin="https://evil.example")])
    s.check("an Origin with the other scheme, or another host, is refused (403)", cross[0]["first"]["status"] == 403 and cross[1]["first"]["status"] == 403, "%s / %s" % (cross[0]["first"]["status"], cross[1]["first"]["status"]))
    spoof = stack.request(ps.CLIENT_A, [access(stack.token, {"X-Forwarded-Host": "evil.example", "X-Forwarded-Proto": "http", "Forwarded": "host=evil.example;proto=http"})])[0]["first"]
    s.check("X-Forwarded-Host / -Proto / Forwarded sent by the client change nothing (cookie still Secure)", spoof["status"] == 200 and "Secure" in lib.header(spoof, "Set-Cookie"), "%s %s" % (spoof["status"], lib.header(spoof, "Set-Cookie")))
    direct = stack.request(ps.CLIENT_A, [{"url": "http://monitor:8765/api/health", "headers": {"Host": "evil.example", "X-Monitor-Access": stack.token}},
                                         {"url": "http://monitor:8765/api/health", "headers": {"Host": ps.SITE, "X-Monitor-Access": stack.token}}])
    s.check("a request that reaches the monitor with a Host that is not its own is refused (403)", direct[0]["first"]["status"] == 403, direct[0]["first"]["status"])
    s.check("the declared public name is accepted as Host", direct[1]["first"]["status"] == 200, "%s %s" % (direct[1]["first"]["status"], direct[1]["first"]["body"][:200]))
    local = stack.request(ps.CLIENT_A, [{"method": "POST", "url": "https://%s/api/mode" % ps.SITE, "ca": "/root.crt", "headers": {"Cookie": session, "Origin": "https://%s" % ps.SITE, "Content-Type": "application/json"}, "body": {"json": {"mode": "fast"}}}])[0]["first"]
    s.check("through the proxy nothing counts as the computer of the monitor: a local-only action is refused (not 200)", local["status"] != 200, "%s %s" % (local["status"], local["body"][:200]))

    # a client that lies in X-Forwarded-For: Caddy adds the real address at the end, so the lie does not move the lock
    liar = stack.request(ps.CLIENT_A, [access("wrong-%s" % "x" * 20, {"X-Forwarded-For": "203.0.113.{i}"}, repeat=14)])[0]
    s.check("a client that forges X-Forwarded-For still gets locked (401 then 429)", "401" in liar["statuses"] and "429" in liar["statuses"], "statuses %s, first 429 at %s" % (liar["statuses"], liar["first_index"].get("429")))
    again = stack.request(ps.CLIENT_A, [access(stack.token, {"X-Forwarded-For": "198.51.100.9"})])[0]["first"]
    s.check("and the lock holds with the right token and another forged address (429)", again["status"] == 429, "%s %s" % (again["status"], again["body"][:200]))
    other = stack.request(ps.CLIENT_B, [access(stack.token)])[0]["first"]
    s.check("another visitor behind the same proxy is NOT locked out by it (200)", other["status"] == 200, "%s %s" % (other["status"], other["body"][:200]))
    # the same lie from a container of the Compose network that does not go through Caddy: the monitor believes the proxies of its own network
    unchecked = stack.request(ps.CLIENT_C, [{"method": "POST", "url": "http://monitor:8765/api/access", "headers": {"Host": ps.SITE, "Origin": "https://%s" % ps.SITE, "Content-Type": "application/json",
                                                                                                                "X-Forwarded-For": "192.0.2.{i}"}, "body": {"json": {"token": "wrong-%s" % ("y" * 20)}}, "repeat": 14}])[0]
    s.note("a container of the proxy network that skips Caddy and changes X-Forwarded-For at each try: statuses %s (429 present = the lock still holds; none = it can choose its own address, which the guide says "
           "about the networks listed in trusted_proxies)" % unchecked["statuses"])

    # the variables are taken out of the environment: the guide says the environment stays the authority for the keys it names
    stack.write(trusted=False)
    ok, out = stack.up()
    s.check("the monitor restarts with MONITOR_TRUSTED_PROXY and MONITOR_TRUSTED_PROXIES empty", ok, out[-800:])
    monitor, _caddy = stack.prepare_client()
    s.wait_healthy(stack.container("monitor"), 180)
    _c, listen = s.python_in(monitor, "import json; print(json.dumps(json.load(open('/config/actions_monitor.json')).get('listen', {})))", label="read listen.* of the configuration file")
    try:
        kept = json.loads(listen.strip().splitlines()[-1])
    except ValueError:
        kept = {}
    s.check("taking MONITOR_TRUSTED_PROXY out of the environment (empty) switches listen.trusted_proxy off again", not kept.get("trusted_proxy"), "listen in the file after the restart: %s" % json.dumps(kept))
    # and switched off explicitly, the conservative behaviour: the lock is counted against the address of Caddy
    stack.write(trusted="off")
    ok, out = stack.up()
    s.check("the monitor restarts with MONITOR_TRUSTED_PROXY=0", ok, out[-800:])
    monitor, _caddy = stack.prepare_client()
    s.wait_healthy(stack.container("monitor"), 180)
    flood = stack.request(ps.CLIENT_A, [access("wrong-%s" % "z" * 20, repeat=12)])[0]
    shared = stack.request(ps.CLIENT_B, [access(stack.token)])[0]["first"]
    s.note("proxy NOT trusted (MONITOR_TRUSTED_PROXY=0): the first visitor's 12 wrong tokens got %s; then another visitor with the right token gets %s (429 = the lock is counted against the address of "
           "Caddy: the conservative behaviour that MONITOR_TRUSTED_PROXY exists to change)" % (flood["statuses"], shared["status"]))
    s.check("without the trusted proxy a lock stays on the address that failed (the first visitor gets 429)", "429" in flood["statuses"], "statuses %s" % flood["statuses"])


if __name__ == "__main__":
    sys.exit(lib.main_of("E3", "Behind a trusted proxy (Caddy with TLS): Host, Origin, Secure cookie, token routes, forged X-Forwarded-For", body))
