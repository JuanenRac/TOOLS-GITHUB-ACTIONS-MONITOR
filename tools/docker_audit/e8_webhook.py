#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E8 - the incoming webhook behind the proxy: a valid and an invalid signature, a replayed delivery, a body that is too big, and the rate limit: is it counted against the real visitor
(the address Caddy adds to X-Forwarded-For) or against Caddy, so that one visitor's flood stops the signed deliveries of everybody else?"""
import json
import secrets
import sys

import audit_lib as lib
import proxy_stack as ps

PAYLOAD = json.dumps({"zen": "audit", "repository": {"name": "audit-repo", "full_name": "audit-owner/audit-repo"}})
PATCH = r'''
import json
path = "/data/accounts/default/actions_monitor.json"
data = json.load(open(path, encoding="utf-8"))
data["webhook"] = {"enabled": True}
open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
print("webhook enabled in " + path)
'''


def hook(secret, event="ping", delivery="{rand}-{i}", body=PAYLOAD, sign=True, repeat=1, headers=None):
    head = {"Content-Type": "application/json", "X-GitHub-Event": event}
    if delivery:
        head["X-GitHub-Delivery"] = delivery
    head.update(headers or {})
    spec = {"method": "POST", "url": "https://%s/api/webhook" % ps.SITE, "ca": "/root.crt", "headers": head, "body": body, "repeat": repeat}
    if sign:
        spec["hmac"] = {"secret": secret}
    return spec


def body(s):
    image = s.image()
    secret = s.secret("audit-hook-" + secrets.token_hex(20), "webhook-secret")
    stack = ps.Stack(s, image)
    stack.write(extra_env={"MONITOR_WEBHOOK_SECRET_FILE": "/run/secrets/webhook_secret"}, extra_secrets={"webhook_secret": secret}, trusted=True)
    ok, out = stack.up()
    if not s.check("the monitor behind Caddy comes up with the shared secret as a file", ok, out[-1500:]):
        return
    monitor, _caddy = stack.prepare_client()
    code, out = s.python_in(monitor, PATCH)
    s.check("the webhook is switched on in the configuration of the account", code == 0, out)
    stack.login_mode(0o644)
    s.run(stack.compose_cmd() + ["restart", "monitor"], timeout=240, label="restart the monitor")
    s.check("the monitor is healthy again", s.wait_healthy(monitor, 180), s.logs(monitor)[-800:])
    ready, _first = stack.wait_proxy()
    s.check("Caddy answers again", ready)
    status = lib.http_request(8765, "GET", "/api/live-status", {"Host": "127.0.0.1:8765", "X-Monitor-Access": stack.token})
    info = lib.jbody(status) or {}
    s.note("/api/live-status: %s" % status["body"][:300])
    if not s.check("the receiver is active (switched on and the secret is long enough)", info.get("enabled") is True and info.get("active") is True and info.get("secret_ok") is True, status["body"][:300]):
        return

    big = json.dumps({"repository": {"name": "audit-repo", "full_name": "audit-owner/audit-repo"}, "pad": "x" * 300000})
    other = json.dumps({"repository": {"name": "x", "full_name": "nobody-watches-this/x"}})
    results = stack.request(ps.CLIENT_A, [
        hook(secret),                                                                                  # 0 valid ping
        hook(secret, sign=False, headers={"X-Hub-Signature-256": "sha256=" + "0" * 64}),               # 1 wrong signature
        hook(secret, sign=False),                                                                      # 2 no signature
        hook(secret, body=PAYLOAD.replace("audit", "AUDIT"), sign=False, headers={"X-Hub-Signature-256": "sha256=" + "1" * 64}),   # 3 signature of another body
        hook(secret, event="push", delivery="replay-{rand}-same"),                                     # 4 valid push, first time
        hook(secret, event="push", delivery="replay-{rand}-same"),                                     # 5 the same delivery again (the run id is the same: {rand} is per client run)
        hook(secret, delivery=None),                                                                   # 6 valid signature, no delivery id
        hook(secret, body=big),                                                                        # 7 a body over the limit
        hook(secret, body=other),                                                                      # 8 a repository that no account watches
        {"method": "GET", "url": "https://%s/api/webhook" % ps.SITE, "ca": "/root.crt"},               # 9 GET
        hook(secret, event="issues"),                                                                  # 10 an event that is not in the closed list
    ])
    first = [r["first"] for r in results]
    s.check("a valid signature is accepted (200)", first[0]["status"] == 200, "%s %s" % (first[0]["status"], first[0]["body"][:200]))
    s.check("a wrong signature is refused (401)", first[1]["status"] == 401, "%s %s" % (first[1]["status"], first[1]["body"][:200]))
    s.check("no signature is refused (401)", first[2]["status"] == 401, "%s %s" % (first[2]["status"], first[2]["body"][:200]))
    s.check("the signature of another body is refused (401)", first[3]["status"] == 401, "%s %s" % (first[3]["status"], first[3]["body"][:200]))
    s.check("a delivery sent again is answered 202 and marked as a duplicate, never acted on", first[4]["status"] == 202 and first[5]["status"] == 202 and "duplicate" in first[5]["body"], "%s / %s %s" % (first[4]["status"], first[5]["status"], first[5]["body"][:200]))
    s.check("a valid signature without a delivery id is refused (400)", first[6]["status"] == 400, "%s %s" % (first[6]["status"], first[6]["body"][:200]))
    s.check("a body over the limit is refused (413)", first[7]["status"] == 413, "%s %s" % (first[7]["status"], first[7]["body"][:200]))
    s.check("an event for a repository that no account watches is answered 202 and ignored", first[8]["status"] == 202, "%s %s" % (first[8]["status"], first[8]["body"][:200]))
    s.check("GET /api/webhook gives no event (401, 404 or 405, never 200)", first[9]["status"] in (401, 404, 405), first[9]["status"])
    s.check("an event outside the closed list is answered 202 and dropped", first[10]["status"] == 202, "%s %s" % (first[10]["status"], first[10]["body"][:200]))

    # the rate limit: one visitor floods the receiver with garbage, then another sends a real delivery
    flood = stack.request(ps.CLIENT_A, [hook(secret, sign=False, headers={"X-Hub-Signature-256": "sha256=" + "2" * 64, "X-Forwarded-For": "203.0.113.{i}"}, repeat=140)])[0]
    s.check("the flood of one visitor meets a limit of its own (429)", "429" in flood["statuses"], "statuses %s, first 429 at request %s" % (flood["statuses"], flood["first_index"].get("429")))
    s.note("the flood by the first visitor: %s" % flood["statuses"])
    victim_body = json.dumps({"zen": "the delivery of another visitor", "repository": {"name": "audit-repo", "full_name": "audit-owner/audit-repo"}})      # its own delivery id AND its own body: the monitor also remembers what was signed, so the body of the first ping would be answered as a duplicate
    victim = stack.request(ps.CLIENT_B, [hook(secret, body=victim_body, delivery="visitor-b-{rand}-{i}")])[0]["first"]
    s.check("a real, signed delivery from ANOTHER visitor behind the same proxy is still accepted while the first one is limited (200)", victim["status"] == 200,
            "%s %s -- the limit is counted against the address of the proxy, not against the visitor" % (victim["status"], victim["body"][:200]))
    direct = stack.request(ps.CLIENT_C, [{"method": "POST", "url": "http://monitor:8765/api/webhook", "headers": {"Content-Type": "application/json", "X-GitHub-Event": "ping", "X-GitHub-Delivery": "direct-{rand}-{i}",
                                                                                                             "X-Forwarded-For": "192.0.2.{i}"}, "body": PAYLOAD, "hmac": {"secret": secret}}])[0]["first"]
    s.note("a signed delivery straight to the monitor (no proxy) while the proxy address is limited: %s" % direct["status"])


if __name__ == "__main__":
    sys.exit(lib.main_of("E8", "Incoming webhook behind the proxy: signatures, replay, size and the rate limit per real visitor", body))
