#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Smoke test of the external sources the monitor reads, against the REAL services (not mocks): the weekly workflow `sources-smoke.yml` runs it.

    python tools/smoke_sources.py [--only status,advisories,openapi,release] [--timeout 30]

  status      https://www.githubstatus.com/api/v2/summary.json has the fields the monitor reads (status.indicator, status.description, components[].name/status)
  advisories  https://api.github.com/advisories answers a list of advisories with ghsa_id, severity and vulnerabilities
  openapi     the description of the REST API of GitHub still has every endpoint the monitor calls (the list is checked against the code by a test, so it cannot go stale)
  release     the last release of this project is read by the same function the update notice uses

Each source is judged by a pure function (`check_*`) that the unit tests feed with a sample, so the test of the format runs offline and the smoke only decides whether the service still answers
that format. A service that cannot be reached is a failure of that source, said by name; nothing here writes anything anywhere and no token is used (public data, the limits of an anonymous reader)."""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "monitor" / "src"))

STATUS_URL = "https://www.githubstatus.com/api/v2/summary.json"
ADVISORIES_URL = "https://api.github.com/advisories?per_page=2"
OPENAPI_URL = "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json"
RELEASE_URL = "https://api.github.com/repos/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"
INDICATORS = ("none", "minor", "major", "critical")

#: (method, path) the monitor calls; tests/test_i200_smoke_sources.py checks that every path is still named in the code, and that every path of the code of this shape is here.
ENDPOINTS = (
    ("get", "/rate_limit"), ("get", "/repos/{owner}/{repo}/actions/runs"), ("get", "/repos/{owner}/{repo}/actions/runs/{run_id}"), ("get", "/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"),
    ("get", "/repos/{owner}/{repo}/actions/workflows"), ("get", "/repos/{owner}/{repo}/releases/latest"), ("get", "/repos/{owner}/{repo}/pulls"), ("get", "/repos/{owner}/{repo}/issues"),
    ("get", "/repos/{owner}/{repo}/actions/permissions"), ("get", "/repos/{owner}/{repo}/community/profile"), ("get", "/repos/{owner}/{repo}/contents/{path}"),
    ("post", "/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"), ("post", "/repos/{owner}/{repo}/actions/runs/{run_id}/cancel"), ("post", "/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs"),
)


def check_status(doc):
    """Problems of a document of githubstatus.com (empty = the monitor can read it)."""
    if not isinstance(doc, dict):
        return ["the status page does not answer an object"]
    problems = []
    status = doc.get("status")
    if not isinstance(status, dict) or status.get("indicator") not in INDICATORS or not isinstance(status.get("description"), str):
        problems.append("status.indicator / status.description are missing or changed (indicator: %r)" % (status.get("indicator") if isinstance(status, dict) else None))
    components = doc.get("components")
    if not isinstance(components, list) or not components:
        problems.append("components is not a list with items")
    elif not all(isinstance(c, dict) and isinstance(c.get("name"), str) and isinstance(c.get("status"), str) for c in components):
        problems.append("a component lost its name or its status")
    if not isinstance(doc.get("incidents"), list):
        problems.append("incidents is not a list")
    return problems


def check_advisories(doc):
    if not isinstance(doc, list) or not doc:
        return ["the advisories endpoint did not answer a list with items"]
    problems = []
    for item in doc:
        if not isinstance(item, dict) or not isinstance(item.get("ghsa_id"), str) or not re.match(r"^GHSA(-[a-z0-9]{4}){3}$", item.get("ghsa_id", "")):
            problems.append("an advisory lost its ghsa_id")
        elif item.get("severity") not in ("low", "medium", "high", "critical", "unknown", None):
            problems.append("an advisory has a severity that is not known: %r" % item.get("severity"))
        elif "vulnerabilities" in item and not isinstance(item["vulnerabilities"], list):
            problems.append("vulnerabilities is not a list")
    return problems


def check_openapi(doc, endpoints=ENDPOINTS):
    if not isinstance(doc, dict) or not isinstance(doc.get("paths"), dict):
        return ["the description of the API has no paths"]
    problems = []
    for method, path in endpoints:
        entry = doc["paths"].get(path)
        if not isinstance(entry, dict) or method not in entry:
            problems.append("the REST API no longer describes %s %s" % (method.upper(), path))
    return problems


def check_release(doc):
    try:
        from github_actions_monitor.app import updatecheck
    except ImportError as error:
        return ["the monitor cannot be imported: %s" % error]
    return [] if updatecheck.clean_release(doc) else ["the update notice cannot read the last release of the project (draft, pre-release or a tag it does not know)"]


def fetch(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": "github-actions-monitor-source-smoke", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as answer:      # nosec: public data, fixed https addresses above
        return json.loads(answer.read().decode("utf-8"))


SOURCES = {"status": (STATUS_URL, check_status), "advisories": (ADVISORIES_URL, check_advisories), "openapi": (OPENAPI_URL, check_openapi), "release": (RELEASE_URL, check_release)}


def run(only, timeout, getter=fetch):
    """{source: [problems]}: a source that cannot be read is a problem with its name."""
    out = {}
    for name in only:
        url, check = SOURCES[name]
        try:
            out[name] = check(getter(url, timeout))
        except (urllib.error.URLError, OSError, ValueError) as error:
            out[name] = ["cannot read %s: %s" % (url, str(error)[:160])]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", default=",".join(SOURCES))
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args(argv)
    only = [n.strip() for n in args.only.split(",") if n.strip() in SOURCES]
    if not only:
        print("SMOKE=ERROR no source named")
        return 2
    result = run(only, args.timeout)
    failed = False
    for name, problems in result.items():
        print(("FAIL " if problems else "ok   ") + name)
        for problem in problems:
            print("     " + problem)
        failed = failed or bool(problems)
    print("SMOKE=" + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
