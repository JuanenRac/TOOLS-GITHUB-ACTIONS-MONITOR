#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A tiny HTTP client that the container checks run INSIDE a throw-away container, so that the request comes from a known address of a Docker network.

It reads one JSON document on the standard input, {"requests": [...]}, sends the requests in order and prints a JSON list with one result per request:

  request: {"method": "GET", "url": "https://audit.test/api/health", "headers": {"X-Forwarded-For": "10.{i}.0.1"}, "body": "text" | {"json": ...}, "repeat": 1,
            "ca": "/path/root.crt" (verify the server with it; without it the certificate is not checked), "hmac": {"secret": "...", "header": "X-Hub-Signature-256"}, "timeout": 20}
  Every `{i}` in a header value or in the body is replaced by the number of the repetition (0, 1, 2 ...), every `{rand}` by a random string of this run.
  result:  {"count": n, "statuses": {"200": 3, "429": 2}, "first_index": {"200": 0, "429": 3}, "first": {...}, "last": {...}}  where first/last are {"status", "headers", "body"}.
"""
import hashlib
import hmac
import http.client
import json
import secrets
import ssl
import sys
from urllib.parse import urlsplit

RUN = secrets.token_hex(4)


def one(spec, index):
    parts = urlsplit(spec["url"])
    https = parts.scheme == "https"
    timeout = spec.get("timeout", 20)
    if https:
        if spec.get("ca"):
            context = ssl.create_default_context(cafile=spec["ca"])
        else:
            context = ssl._create_unverified_context()      # noqa: S323 - a throw-away certificate of a test
        conn = http.client.HTTPSConnection(parts.hostname, parts.port or 443, timeout=timeout, context=context)
    else:
        conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=timeout)

    def fill(text):
        return text.replace("{i}", str(index)).replace("{rand}", RUN) if isinstance(text, str) else text
    headers = {k: fill(v) for k, v in (spec.get("headers") or {}).items()}
    body = spec.get("body")
    if isinstance(body, dict) and "json" in body:
        body = json.dumps(body["json"])
        headers.setdefault("Content-Type", "application/json")
    elif isinstance(body, str):
        body = fill(body)
    raw = body.encode("utf-8") if isinstance(body, str) else None
    if spec.get("hmac") and raw is not None:
        digest = hmac.new(spec["hmac"]["secret"].encode("utf-8"), raw, hashlib.sha256).hexdigest()
        headers[spec["hmac"].get("header", "X-Hub-Signature-256")] = "sha256=" + digest
    path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
    try:
        conn.request(spec.get("method", "GET"), path, body=raw, headers=headers)
        answer = conn.getresponse()
        text = answer.read(65536).decode("utf-8", "replace")
        return {"status": answer.status, "headers": answer.getheaders(), "body": text[:3000]}
    except (OSError, http.client.HTTPException) as error:
        return {"status": 0, "headers": [], "body": "%s: %s" % (type(error).__name__, error)}
    finally:
        conn.close()


def main():
    plan = json.load(sys.stdin)
    results = []
    for spec in plan["requests"]:
        statuses, first_index, first, last = {}, {}, None, None
        count = int(spec.get("repeat", 1))
        for index in range(count):
            answer = one(spec, index)
            key = str(answer["status"])
            statuses[key] = statuses.get(key, 0) + 1
            first_index.setdefault(key, index)
            first = first or answer
            last = answer
        results.append({"count": count, "statuses": statuses, "first_index": first_index, "first": first, "last": last})
    print(json.dumps(results))


if __name__ == "__main__":
    main()
