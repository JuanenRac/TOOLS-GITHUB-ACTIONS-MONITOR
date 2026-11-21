#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The audit of the dependencies as a gate of the CI.

    python tools/audit_dependencies.py [--requirements .github/ci-requirements.txt] [--suppressions .github/audit-suppressions.json] [--report FILE.json]
    python tools/audit_dependencies.py --check-file pip-audit.json      judge an answer of pip-audit that was saved (no network, no pip-audit)

It runs `pip-audit` on the packages the CI installs (the monitor itself needs none) and fails when:
  * a package has a known vulnerability that no suppression covers;
  * a suppression has expired (its date has passed): it must be renewed with a new reason or the package updated;
  * a suppression is dead: the vulnerability it names is no longer found (the package was updated or the advisory withdrawn), so the line must be deleted.

The suppressions file is a list of {"id": "GHSA-...", "reason": "why it does not apply here", "expires": "YYYY-MM-DD"}; all three fields are required, and an expiry more than 180 days away is
refused (a suppression is a loan, not a decision). Standard library only; the call to pip-audit is the only thing that needs the network."""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_DAYS = 180


def load_suppressions(path):
    """(list of valid suppressions, list of problems with the file)."""
    problems, good = [], []
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else []
    except (OSError, ValueError) as error:
        return [], [f"the file of suppressions cannot be read: {error}"]
    if not isinstance(raw, list):
        return [], ["the file of suppressions must be a list"]
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item.get(k).strip() for k in ("id", "reason", "expires")):
            problems.append(f"suppression {i + 1}: id, reason and expires are all required")
            continue
        try:
            datetime.date.fromisoformat(item["expires"])
        except ValueError:
            problems.append(f"suppression {item['id']}: expires must be YYYY-MM-DD")
            continue
        good.append(item)
    return good, problems


def findings(answer):
    """{vulnerability id: set of 'package version'} from the JSON of pip-audit (it also counts the aliases, so a suppression may name a CVE or a GHSA)."""
    found = {}
    deps = answer.get("dependencies") if isinstance(answer, dict) else answer
    for dep in deps or []:
        if not isinstance(dep, dict):
            continue
        for vuln in dep.get("vulns") or []:
            who = f"{dep.get('name', '?')} {dep.get('version', '?')}"
            for name in [vuln.get("id")] + list(vuln.get("aliases") or []):
                if name:
                    found.setdefault(str(name), set()).add(who)
    return found


def evaluate(answer, suppressions, today=None, max_days=MAX_DAYS):
    """(problems, notes): the problems fail the job. Pure: given the answer of pip-audit, the suppressions and the date."""
    today = today or datetime.date.today()
    found = findings(answer)
    problems, notes = [], []
    covered = set()
    for item in suppressions:
        due = datetime.date.fromisoformat(item["expires"])
        if (due - today).days > max_days:
            problems.append(f"suppression {item['id']}: it expires on {item['expires']}, more than {max_days} days away")
        if due < today:
            problems.append(f"suppression {item['id']} expired on {item['expires']}: renew it with a new reason or update the package")
            continue
        if item["id"] not in found:
            problems.append(f"suppression {item['id']} is dead: that vulnerability is no longer found, delete the line")
            continue
        covered.add(item["id"])
        notes.append(f"{item['id']} suppressed until {item['expires']}: {item['reason']}")
    primary = {}
    for dep in (answer.get("dependencies") if isinstance(answer, dict) else answer) or []:
        for vuln in (dep.get("vulns") or []) if isinstance(dep, dict) else []:
            names = {str(n) for n in [vuln.get("id")] + list(vuln.get("aliases") or []) if n}
            primary[str(vuln.get("id"))] = (names, f"{dep.get('name', '?')} {dep.get('version', '?')}", vuln.get("fix_versions") or [])
    for vid, (names, who, fixes) in sorted(primary.items()):
        if not (names & covered):
            problems.append(f"{vid} in {who}" + (f" (fixed in {', '.join(map(str, fixes))})" if fixes else " (no fixed version yet)"))
    return problems, notes


def run_pip_audit(requirements):
    done = subprocess.run([sys.executable, "-m", "pip_audit", "-r", str(requirements), "-f", "json", "--progress-spinner", "off"], capture_output=True, text=True, timeout=600)
    text = done.stdout.strip()
    if not text:
        raise RuntimeError("pip-audit gave no answer: " + (done.stderr or "").strip()[-300:])
    return json.loads(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--requirements", default=str(ROOT / ".github" / "ci-requirements.txt"))
    ap.add_argument("--suppressions", default=str(ROOT / ".github" / "audit-suppressions.json"))
    ap.add_argument("--report", default="")
    ap.add_argument("--check-file", default="", help="judge a saved answer of pip-audit instead of running it")
    args = ap.parse_args(argv)
    suppressions, bad = load_suppressions(args.suppressions)
    try:
        answer = json.loads(Path(args.check_file).read_text(encoding="utf-8")) if args.check_file else run_pip_audit(args.requirements)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"AUDIT=ERROR {error}")      # an audit that did not run is not a pass
        return 2
    problems, notes = evaluate(answer, suppressions)
    problems = bad + problems
    for line in notes:
        print("note: " + line)
    for line in problems:
        print("FAIL: " + line)
    if args.report:
        Path(args.report).write_text(json.dumps({"problems": problems, "notes": notes}, indent=1) + "\n", encoding="utf-8")
    print("AUDIT=" + ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
