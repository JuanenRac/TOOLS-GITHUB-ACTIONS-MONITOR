#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract suite of the read API for clients (version 1): run it against any server that says it speaks it, to know whether a client written for the contract will work.

    python tools/api_contract_suite.py                          the monitor on 127.0.0.1:8765
    python tools/api_contract_suite.py --url https://host:8765 --token-file token.txt
    python tools/api_contract_suite.py --json                    one JSON document instead of lines

Only the standard library; it only reads (GET, plus a few other methods sent to the routes to prove that they refuse them) and asks GitHub for nothing. It takes the document the server serves
(`/api/v1/openapi.json`) as the description of what to check, so it works for a monitor of any later version that keeps the contract, and checks: the document itself, the shape of the answer of
every route that needs no parameter (keys and types the document requires), the header `X-API-Version`, the error envelope and its stable codes, the pages (cursor, limit, fields, compact profile),
gzip, and that nothing can be written under the prefix. The last line is `API_CONTRACT=PASS` or `API_CONTRACT=FAIL`; the exit code is 0 when it passes, 1 when it fails and 2 when nothing answers.
Give it a token of READ (the access token of the network mode, or a session with the role viewer): it never needs more."""
import argparse
import gzip
import http.client
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

PREFIX = "/api/v1"
TYPES = {"boolean": bool, "integer": int, "number": (int, float), "string": str, "array": list, "object": dict}
ENVELOPE = ("error", "code", "message")
STABLE_CODES = {"/repos?limit=0": "api.bad_limit", "/repos?limit=abc": "api.bad_limit", "/repos?cursor=%25%25": "api.bad_cursor", "/repos?fields=zzz": "api.unknown_field", "/repos?profile=x": "api.bad_profile"}
SAMPLE_PAGES = 3


class Client:
    def __init__(self, url, token="", timeout=30):
        parts = urlsplit(url)
        self.parts, self.token, self.timeout = parts, token, timeout
        self.host = parts.hostname
        self.port = parts.port or (443 if parts.scheme == "https" else 80)

    def call(self, method, path, headers=None, body=None):
        """(status, headers dict lower-cased, raw body bytes after the gzip is undone, was it gzipped)."""
        klass = http.client.HTTPSConnection if self.parts.scheme == "https" else http.client.HTTPConnection
        connection = klass(self.host, self.port, timeout=self.timeout)
        sent = {"Host": f"{self.host}:{self.port}", **(headers or {})}
        if self.token:
            sent["X-Monitor-Access"] = self.token
        if body is not None:
            sent["Content-Type"] = "application/json"
        try:
            connection.request(method, path, body, sent)
            answer = connection.getresponse()
            raw = answer.read(8_000_000)
            head = {k.lower(): v for k, v in answer.getheaders()}
        finally:
            connection.close()
        zipped = head.get("content-encoding") == "gzip"
        if zipped:
            try:
                raw = gzip.decompress(raw)
            except OSError:
                zipped = None
        return answer.status, head, raw, zipped

    def json(self, path, headers=None):
        status, head, raw, zipped = self.call("GET", path, headers)
        try:
            return status, head, json.loads(raw), zipped
        except ValueError:
            return status, head, None, zipped


class Report:
    def __init__(self):
        self.rows = []

    def check(self, name, ok, detail=""):
        self.rows.append({"check": name, "ok": bool(ok), "detail": "" if ok else str(detail)[:300]})
        return bool(ok)

    @property
    def failed(self):
        return [r for r in self.rows if not r["ok"]]


def shape_problems(label, body, schema):
    """What of the `schema` (a JSON schema fragment of the document: type, required, properties, items) the `body` does not keep. A key the schema does not name is allowed (an answer may grow)."""
    kind = schema.get("type")
    if body is None:
        return [] if schema.get("nullable") or kind is None else [f"{label}: null where the contract says {kind}"]
    if kind:
        want = TYPES.get(kind)
        if want is None:
            return []
        if isinstance(body, bool) and kind in ("integer", "number"):
            return [f"{label}: boolean where the contract says {kind}"]
        if not isinstance(body, want):
            return [f"{label}: {type(body).__name__} where the contract says {kind}"]
    problems = []
    if isinstance(body, dict):
        for key in schema.get("required", []):
            if key not in body:
                problems.append(f"{label}: the key `{key}` is missing")
        for key, sub in (schema.get("properties") or {}).items():
            if key in body:
                problems += shape_problems(f"{label}.{key}", body[key], sub)
    elif isinstance(body, list) and schema.get("items"):
        for index, item in enumerate(body[:SAMPLE_PAGES]):
            problems += shape_problems(f"{label}[{index}]", item, schema["items"])
    return problems


def check_document(client, report):
    status, head, doc, _ = client.json(PREFIX + "/openapi.json")
    if not report.check("openapi: served", status == 200 and isinstance(doc, dict), f"status {status}"):
        return None
    report.check("openapi: version 3", str(doc.get("openapi", "")).startswith("3."), doc.get("openapi"))
    report.check("openapi: the version of the contract", re.fullmatch(r"\d+\.\d+", str((doc.get("info") or {}).get("x-contract-version", ""))), (doc.get("info") or {}).get("x-contract-version"))
    paths = doc.get("paths") or {}
    report.check("openapi: has paths under the prefix", paths and all(p.startswith(PREFIX + "/") for p in paths), "paths missing or outside /api/v1/")
    report.check("openapi: read only", all(list(item) == ["get"] for item in paths.values()), "a path offers a method other than GET")
    ids = [(item.get("get") or {}).get("operationId") for item in paths.values()]
    report.check("openapi: operationId unique", len(ids) == len(set(ids)) and all(ids), "an operationId is missing or repeated")
    report.check("openapi: header X-API-Version", head.get("x-api-version") == "1", head.get("x-api-version"))
    return doc


def check_routes(client, report, doc):
    for path, item in sorted(doc["paths"].items()):
        operation = item["get"]
        if "{" in path or operation.get("x-experimental"):
            continue
        sample = "&".join(f"{p['name']}={p['example']}" for p in operation.get("parameters", []) if p.get("in") == "query" and "example" in p)      # the query the contract was frozen with
        status, head, body, _ = client.json(path + ("?" + sample if sample else ""))
        schema = (((operation.get("responses") or {}).get("200") or {}).get("content") or {}).get("application/json", {}).get("schema")
        local = operation.get("x-local-only") and status == 403
        if local:
            report.check(f"GET {path}", True)
            continue
        if not schema:      # a route documented with a fixed answer
            fixed = [int(code) for code in operation["responses"] if code.isdigit()]
            report.check(f"GET {path}", status in fixed, f"status {status}, the document says {fixed}")
            continue
        if status != 200:
            report.check(f"GET {path}", False, f"status {status}, the document says 200")
            continue
        problems = shape_problems(path, body, schema)
        report.check(f"GET {path}", not problems and head.get("x-api-version") == "1", "; ".join(problems[:3]) or f"header X-API-Version is {head.get('x-api-version')!r}")


def check_errors(client, report):
    for query, code in STABLE_CODES.items():
        status, _, body, _ = client.json(PREFIX + query)
        ok = status == 400 and isinstance(body, dict) and all(k in body for k in ENVELOPE) and body.get("code") == code and body.get("error") == "bad_request" and bool(body.get("message"))
        report.check(f"error {code}", ok, f"status {status}, answer {str(body)[:120]}")
    status, _, body, _ = client.json(PREFIX + "/no-such-route")
    report.check("unknown route is 404", status == 404, f"status {status}")
    status, _, _, _ = client.json("/api/v2/me")
    report.check("another version is 404", status == 404, f"status {status}")


def check_pages(client, report):
    status, _, first, _ = client.json(PREFIX + "/repos?limit=2")
    if not report.check("repos: first page", status == 200 and isinstance(first, dict) and isinstance(first.get("items"), list), f"status {status}"):
        return
    report.check("repos: the limit is kept", len(first["items"]) <= 2 and first.get("limit") == 2, f"{len(first['items'])} items, limit {first.get('limit')}")
    cursor = first.get("next_cursor")
    if cursor:
        status, _, second, _ = client.json(PREFIX + "/repos?limit=2&cursor=" + cursor)
        names = [i.get("repo") for i in first["items"]]
        ok = status == 200 and isinstance(second, dict) and not set(names) & {i.get("repo") for i in second.get("items", [])}
        report.check("repos: the second page does not repeat the first", ok, f"status {status}")
        status, _, body, _ = client.json(PREFIX + "/repos?limit=2&state=bad&cursor=" + cursor)
        report.check("repos: a cursor of another query is refused", status == 400 and isinstance(body, dict) and body.get("code") == "api.bad_cursor", f"status {status}")
    else:
        report.check("repos: one page holds everything", first.get("total", 0) <= 2, "no next_cursor with more items than the limit")
    status, _, compact, _ = client.json(PREFIX + "/repos?limit=1&profile=compact")
    if status == 200 and compact.get("items"):
        report.check("repos: the compact profile is shorter", len(compact["items"][0]) < len((first["items"] or [{}])[0]) or len(compact["items"][0]) <= 3, f"{sorted(compact['items'][0])}")
    status, _, some, _ = client.json(PREFIX + "/repos?limit=1&fields=repo,state")
    if status == 200 and some.get("items"):
        report.check("repos: fields= keeps only those fields", sorted(some["items"][0]) == ["repo", "state"], sorted(some["items"][0]))


def check_me(client, report):
    status, _, me, _ = client.json(PREFIX + "/me")
    if not report.check("me: served", status == 200 and isinstance(me, dict), f"status {status}"):
        return
    for key in ("api_version", "contract", "version", "edition", "mode", "authenticated", "user", "role", "accounts", "capabilities", "limits"):
        report.check(f"me: `{key}`", key in me, "missing")
    report.check("me: mode", me.get("mode") in ("individual", "team"), me.get("mode"))
    can = me.get("capabilities") or {}
    report.check("me: the prefix never writes", can.get("v1_write") is False and can.get("read") is True, can)


def check_transport(client, report):
    status, head, body, zipped = client.json(PREFIX + "/repos?limit=200", {"Accept-Encoding": "gzip"})
    if status == 200:
        report.check("gzip: the answer is valid when compressed", zipped is not None and isinstance(body, dict), "the gzip body could not be read")
        report.check("cache: not stored", "no-store" in head.get("cache-control", ""), head.get("cache-control"))
    status, _, _, _ = client.call("GET", PREFIX + "/me", {"Accept-Encoding": "identity"})
    report.check("gzip: identity is accepted", status == 200, f"status {status}")
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        try:
            status = client.call(method, PREFIX + "/me", None, "{}")[0]
        except (OSError, http.client.HTTPException):      # a server that closes the connection on a method it does not know has refused it
            status = 0
        report.check(f"nothing is written: {method} is refused", not (200 <= status < 300), f"status {status}")


def run(client):
    report = Report()
    doc = check_document(client, report)
    if doc:
        check_routes(client, report, doc)
    check_errors(client, report)
    check_pages(client, report)
    check_me(client, report)
    check_transport(client, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a server against the contract of the read API for clients (version 1).")
    parser.add_argument("--url", default="http://127.0.0.1:8765", help="address of the server (default http://127.0.0.1:8765)")
    parser.add_argument("--token-file", help="a file with the token of READ (never a token on the command line)")
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for each answer")
    parser.add_argument("--json", action="store_true", help="one JSON document instead of lines")
    args = parser.parse_args(argv)
    token = Path(args.token_file).read_text(encoding="utf-8").strip() if args.token_file else ""
    client = Client(args.url, token, args.timeout)
    try:
        report = run(client)
    except OSError as error:
        print(f"no answer from {args.url}: {error}")
        print("API_CONTRACT=FAIL")
        return 2
    failed = report.failed
    if args.json:
        print(json.dumps({"ok": not failed, "checks": len(report.rows), "failed": len(failed), "rows": report.rows}, indent=1))
    else:
        for row in report.rows:
            print(("PASS " if row["ok"] else "FAIL ") + row["check"] + ("" if row["ok"] else ": " + row["detail"]))
        print(f"{len(report.rows) - len(failed)}/{len(report.rows)} checks pass")
    print("API_CONTRACT=" + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
