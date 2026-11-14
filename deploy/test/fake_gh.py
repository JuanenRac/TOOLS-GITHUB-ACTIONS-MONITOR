#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A stand-in for the GitHub CLI for the test of the container (deploy/test/container_test.sh): it needs no network and no real login.

It answers the few calls the monitor makes the way GitHub does. A call is accepted when the token in GH_TOKEN is one of the lines of the file named by FAKE_GH_GOOD; any other token (or none) is
refused exactly as GitHub refuses a revoked token (`HTTP 401: Bad credentials`) or a missing login. The test edits that file to "revoke" a token and to bring a good one back.
"""
import json
import os
import sys
import time

args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("gh version 2.99.0 (fake, for the test of the container)")
    sys.exit(0)
token = os.environ.get("GH_TOKEN", "").strip()
if not token:
    sys.stderr.write("gh: To use GitHub CLI in automation, set the GH_TOKEN environment variable.\n")
    sys.exit(4)
try:
    with open(os.environ.get("FAKE_GH_GOOD", "/fake/good"), encoding="utf-8") as handle:
        good = {line.strip() for line in handle if line.strip()}
except OSError:
    good = set()
if token not in good:
    sys.stderr.write("gh: Bad credentials (HTTP 401)\n")
    sys.exit(1)
rest = args[1:] if args[:1] == ["api"] else args
target = next((a for a in rest if not a.startswith("-")), "")
if args[:2] == ["repo", "list"]:
    out = []
elif target == "user":
    out = {"login": os.environ.get("FAKE_GH_LOGIN", "tester")}
elif target == "rate_limit":
    out = {"resources": {"core": {"limit": 5000, "remaining": 4999, "reset": int(time.time()) + 3600}}}
elif "/issues" in target or "/pulls" in target or target.endswith("/releases") or "/alerts" in target:
    out = []
else:
    out = {}
print(json.dumps(out))
