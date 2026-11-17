#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Joins the result files of the container checks (E1.json ... E8.json) into one summary: a table with a verdict per check and the evidence of every failed check.

    python tools/docker_audit/collect.py --dir results --ref v2.0.8 [--expected E1,E2,...]

Writes summary.md and summary.json in the folder, prints the Markdown (the workflow copies it to the step summary) and exits 1 when a check failed or an expected result is missing.
"""
import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default="results")
    parser.add_argument("--ref", default="")
    parser.add_argument("--expected", default="", help="codes that must have a result, e.g. E1,E2")
    args = parser.parse_args(argv)
    folder = Path(args.dir)
    found = {}
    for path in sorted(folder.glob("E[0-9].json")):
        try:
            found[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            found[path.stem] = {"scenario": path.stem, "title": "unreadable result", "verdict": "FAIL", "checks": [], "notes": [], "seconds": 0}
    expected = [c for c in args.expected.split(",") if c] or sorted(found)
    lines = ["## Container checks of %s" % (args.ref or "the version"), "", "| Check | Verdict | Checks passed | Seconds | What it covers |", "|---|---|---|---|---|"]
    summary, bad = [], False
    for code in expected:
        row = found.get(code)
        if row is None:
            lines.append("| %s | **NO RESULT** | - | - | the job ended before it wrote its result |" % code)
            summary.append({"scenario": code, "verdict": "NO-RESULT"})
            bad = True
            continue
        checks = row.get("checks", [])
        passed = sum(1 for c in checks if c.get("ok"))
        lines.append("| %s | **%s** | %d / %d | %s | %s |" % (code, row["verdict"], passed, len(checks), row.get("seconds", ""), row.get("title", "")))
        summary.append({"scenario": code, "verdict": row["verdict"], "passed": passed, "total": len(checks)})
        bad = bad or row["verdict"] == "FAIL"
    for code in expected:
        row = found.get(code)
        if not row:
            continue
        failed = [c for c in row.get("checks", []) if not c.get("ok")]
        if failed or row.get("notes") or row.get("reason"):
            lines += ["", "### %s - %s" % (code, row.get("title", ""))]
            if row.get("reason"):
                lines.append("Not applicable: %s" % row["reason"])
            for c in failed:
                lines.append("- FAIL: %s" % c["name"])
                if c.get("evidence"):
                    lines.append("  - evidence: `%s`" % c["evidence"].replace("`", "'").replace("\n", " ")[:600])
            for note in row.get("notes", []):
                lines.append("- note: %s" % note.replace("\n", " ")[:600])
    environment = next((row.get("environment") for row in found.values() if row.get("environment")), {})
    if environment:
        lines += ["", "### Environment", ""] + ["- %s: `%s`" % (k, v) for k, v in environment.items()]
    text = "\n".join(lines) + "\n"
    (folder / "summary.md").write_text(text, encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({"ref": args.ref, "results": summary, "ok": not bad}, indent=1) + "\n", encoding="utf-8")
    print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
