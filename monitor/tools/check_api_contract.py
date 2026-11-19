#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Checks a running monitor against the frozen contract of its read endpoints (docs/schemas/api_contract.json).

    python tools/check_api_contract.py                       the complete edition on 127.0.0.1:8765
    python tools/check_api_contract.py --lite                the lite edition on 127.0.0.1:8766
    python tools/check_api_contract.py --url http://host:8765 --token-file token.txt
    python tools/check_api_contract.py --v1                   everything under /api/v1/ (the monitor must have api.v1_enabled on): the frozen shapes of its own routes AND the whole
                                                              contract suite for clients (tools/api_contract_suite.py), so that this tool is the one place to ask "does the contract hold?"

It only reads (GET, plus one POST to a path that does not exist), asks GitHub for nothing and prints one line per failure and a last line `CONTRACT=PASS` or `CONTRACT=FAIL`.
The exit code is 0 when it passes. A key the contract does not list is allowed (an answer may grow); a key it lists must be there with its type.
"""
import argparse
import http.client
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

CONTRACT = Path(__file__).resolve().parent.parent / "docs" / "schemas" / "api_contract.json"
PYTHON_TYPES = {"bool": (bool,), "int": (int,), "number": (int, float), "str": (str,), "list": (list,), "object": (dict,)}


ELEMENT_SAMPLE = 3      # how many elements of a list with a described shape are looked at


def type_ok(value, name):
    if name == "any":
        return True
    if name == "int" and isinstance(value, bool):
        return False
    if name == "number" and isinstance(value, bool):
        return False
    return isinstance(value, PYTHON_TYPES[name])


def keys_problems(label, body, keys):
    if not isinstance(body, dict):
        return [f"{label}: the answer is not a JSON object"]
    problems = []
    for key, name in keys.items():
        if key not in body:
            problems.append(f"{label}: the key `{key}` is missing")
        elif isinstance(name, dict):      # a nested object: its own keys and types, one level down
            if isinstance(body[key], dict):
                problems += keys_problems(f"{label}.{key}", body[key], name)
            else:
                problems.append(f"{label}: the key `{key}` is {type(body[key]).__name__}, the contract says object")
        elif isinstance(name, list):      # a list whose elements have this shape (`[{...}]`): the first ELEMENT_SAMPLE elements are checked; an empty list proves nothing and passes
            if not isinstance(body[key], list):
                problems.append(f"{label}: the key `{key}` is {type(body[key]).__name__}, the contract says list")
            else:
                for index, item in enumerate(body[key][:ELEMENT_SAMPLE]):
                    problems += keys_problems(f"{label}.{key}[{index}]", item, name[0])
        elif not type_ok(body[key], name):
            problems.append(f"{label}: the key `{key}` is {type(body[key]).__name__}, the contract says {name}")
    return problems


def check(call, edition, contract=None):
    """`call(method, path, host=None, body=None)` returns (status, parsed body or None). Returns the list of problems (empty = the contract holds)."""
    contract = contract or json.loads(CONTRACT.read_text(encoding="utf-8"))
    problems = []
    for row in contract["endpoints"]:
        want = row["complete"] if edition == "complete" else (row["complete"] if row["lite"] == "same" else row["lite"])
        status, body = call("GET", row["path"])
        label = f"GET {row['path']}"
        if row.get("local_only") and status == 403:      # a route for the computer of the monitor only: from the network the right answer is the refusal
            continue
        if isinstance(want, int):
            if status != want:
                problems.append(f"{label}: status {status}, the contract says {want}")
            continue
        if status != 200:
            problems.append(f"{label}: status {status}, the contract says 200")
            continue
        problems += keys_problems(label, body, want)
    for row in contract["errors"]:
        if edition not in row["editions"]:
            continue
        status, body = call(row["method"], row["path"], host=row.get("host"), body=row.get("body"))
        label = f"{row['method']} {row['path']}" + (f" (Host {row['host']})" if row.get("host") else "")
        if status != row["status"]:
            problems.append(f"{label}: status {status}, the contract says {row['status']}")
        else:
            if row.get("json_keys"):
                problems += keys_problems(label, body, row["json_keys"])
            for key, value in (row.get("json_values") or {}).items():      # the code of an error is part of the contract, not only its type
                if not isinstance(body, dict) or body.get(key) != value:
                    problems.append(f"{label}: `{key}` is {body.get(key) if isinstance(body, dict) else None!r}, the contract says {value!r}")
    return problems


def check_fed(call, owner, contract=None):
    """The answers that need data to exist (a repository, the sentinel envelope): `call` must talk to a monitor that holds the invented data of the demo. `{owner}` in a path is the account that is watched."""
    contract = contract or json.loads(CONTRACT.read_text(encoding="utf-8"))
    problems = []
    for row in contract.get("fed_endpoints", []):
        status, body = call("GET", row["path"].replace("{owner}", owner))
        label = f"GET {row['path']}"
        if status != row["status"]:
            problems.append(f"{label}: status {status}, the contract says {row['status']}")
        else:
            problems += keys_problems(label, body, row["keys"])
    return problems


def check_v1(call, contract=None):
    """The routes of the read API under /api/v1/ (they answer only while `api.v1_enabled` is on): the status and the keys of each one, as `check_fed` does for the routes that need data."""
    contract = contract or json.loads(CONTRACT.read_text(encoding="utf-8"))
    problems = []
    for row in contract.get("v1_endpoints", []):
        status, body = call("GET", row["path"])
        label = f"GET {row['path']}"
        if status != row["status"]:
            problems.append(f"{label}: status {status}, the contract says {row['status']}")
        else:
            problems += keys_problems(label, body, row["keys"])
    return problems


def check_v1_suite(url, token="", timeout=30.0):
    """The contract suite for clients (tools/api_contract_suite.py, next to this file) run against `url`: one problem per failed check. Nothing is checked twice - the suite takes the document the server serves
    as the description of what to look for, and this tool only adds the shapes frozen in `v1_endpoints`."""
    import importlib.util
    path = Path(__file__).resolve().parent / "api_contract_suite.py"
    spec = importlib.util.spec_from_file_location("api_contract_suite", path)
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    report = suite.run(suite.Client(url, token, timeout))
    return [f"suite: {row['check']}: {row['detail']}" for row in report.failed]


def make_caller(url, token=""):
    parts = urlsplit(url)
    name, port = parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)

    def call(method, path, host=None, body=None):
        connection_class = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        connection = connection_class(name, port, timeout=30)
        headers = {"Host": host or f"{name}:{port}"}
        if token:
            headers["X-Monitor-Access"] = token
        if body is not None:
            headers["Content-Type"] = "application/json"
        try:
            connection.request(method, path, body, headers)
            answer = connection.getresponse()
            raw = answer.read()
        finally:
            connection.close()
        try:
            return answer.status, json.loads(raw)
        except ValueError:
            return answer.status, None
    return call


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a running monitor against the frozen contract of its read endpoints.")
    parser.add_argument("--url", help="address of the monitor (default http://127.0.0.1:8765, or :8766 with --lite)")
    parser.add_argument("--lite", action="store_true", help="the lite edition")
    parser.add_argument("--v1", action="store_true", help="check the routes under /api/v1/ instead (the monitor must have api.v1_enabled on)")
    parser.add_argument("--token-file", help="a file with the access token of the network mode (never a token on the command line)")
    args = parser.parse_args(argv)
    url = args.url or ("http://127.0.0.1:8766" if args.lite else "http://127.0.0.1:8765")
    token = Path(args.token_file).read_text(encoding="utf-8").strip() if args.token_file else ""
    try:
        problems = (check_v1(make_caller(url, token)) + check_v1_suite(url, token)) if args.v1 else check(make_caller(url, token), "lite" if args.lite else "complete")
    except OSError as error:
        print(f"no answer from {url}: {error}")
        print("CONTRACT=FAIL")
        return 2
    for line in problems:
        print(line)
    print("CONTRACT=" + ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
