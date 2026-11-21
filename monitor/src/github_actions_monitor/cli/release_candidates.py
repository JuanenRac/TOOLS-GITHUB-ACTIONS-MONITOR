#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Release candidates: every project with at least ONE entry in CHANGELOG [Unreleased] whose latest published GitHub release is
more than 2 days old is a candidate for closing its version and launching a release.

  py -3 bin/release_candidates.py [--days 2] [--min-entries 1] [--out FILE]

Lists the repositories of the ecosystems of the ecosystems file that this tool handles (never an "external" one; never the repositories without a CHANGELOG). Read-only (git + gh GET).
Columns: entries, age of the last release in days (or "no release"), version in the changelog, and what the release carries
(builds in Actions / no assets).
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
from github_actions_monitor import i18n
from github_actions_monitor.util import platform_compat
from github_actions_monitor.app import toolconfig
from github_actions_monitor.app import workspace
from github_actions_monitor.delivery import mainsource

G = workspace.workspace_root_soft()
OUT_DEFAULT = workspace.audit_dir_soft() / "RELEASE_CANDIDATES.txt"
BUILDS = {  # repositories whose release carries files built in Actions (see gha_dispatch_all.py)
}


def gh_json(*args):
    from github_actions_monitor.security import secretstore
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=60, **secretstore.gh_kwargs())
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def latest_release(name, run=subprocess.run):
    """("ok", release) | ("none", None) | ("unreadable", cause): a repository that has no release (404) is told apart from a read that failed (network, 403, 429, a broken answer): the second
    one is never taken for "no release", it is not evaluable and says why."""
    from github_actions_monitor.security import secretstore
    try:
        r = run(["gh", "api", f"repos/{toolconfig.github_owner()}/{name}/releases/latest"], capture_output=True, text=True, encoding="utf-8", timeout=60, **secretstore.gh_kwargs())
    except (OSError, subprocess.SubprocessError) as error:
        return "unreadable", str(error)[:80]
    if r.returncode != 0:
        why = (r.stderr or r.stdout or "").strip()
        return ("none", None) if re.search(r"\b404\b|not found", why, re.I) else ("unreadable", why[:80] or "gh failed")
    try:
        body = json.loads(r.stdout)
    except ValueError:
        return "unreadable", "not valid JSON"
    return ("ok", body) if isinstance(body, dict) and body.get("published_at") else ("unreadable", "no published_at")


def unreleased_count(text):
    """Number of list entries under `## [Unreleased]` (the one function of the monitor, `delivery/mainsource.py`)."""
    return mainsource.unreleased_count(text)


def main():
    i18n.cli_language()
    platform_compat.console_utf8()
    workspace.workspace_root()   # clear message here if the workspace cannot be found
    parser = argparse.ArgumentParser(description=i18n.t("rc.description"), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=float, default=2.0, help=i18n.t("rc.help_days"))
    parser.add_argument("--min-entries", type=int, default=1, help=i18n.t("rc.help_min"))
    parser.add_argument("--out", default=str(OUT_DEFAULT), help=i18n.t("rc.help_out"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = parser.parse_args()
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gha_dispatch_all", Path(__file__).resolve().with_name("gha_dispatch_all.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        BUILDS.update({name: t["workflow"] for name, t in mod.TARGETS.items()})
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    rows, skipped, unreadable = [], [], []
    for d in sorted(G.iterdir()):
        n = d.name
        if not toolconfig.is_internal(n):   # an "external" ecosystem is reported elsewhere, never a candidate here
            continue
        cl = d / "CHANGELOG.md"
        if not (d / ".git").exists() or not cl.is_file():
            continue
        text, _ = mainsource.read_changelog(d)
        count = unreleased_count(text or "")
        if count < args.min_entries:
            continue
        state, rel = latest_release(n)
        if state == "unreadable":
            unreadable.append((n, rel))      # not a candidate and not a repository without release: not evaluable
            continue
        age = None
        tag = ""
        if state == "ok":
            age = (now - datetime.strptime(rel["published_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds() / 86400
            tag = rel.get("tag_name", "")
        ok = age is None or age > args.days
        (rows if ok else skipped).append((n, count, age, tag, n in BUILDS))
    lines = [i18n.t("rc.title", min=args.min_entries, days=args.days), ""]
    lines.append(f"{i18n.t('rc.col_repo'):34} {i18n.t('rc.col_entries'):>8} {i18n.t('rc.col_age'):>8} {i18n.t('rc.col_last'):12} {i18n.t('rc.col_actions')}")
    for n, count, age, tag, build in sorted(rows, key=lambda r: -r[1]):
        lines.append(f"{n:34} {count:8d} {('%.1f' % age) if age is not None else i18n.t('rc.no_release'):>8} {tag:12} {i18n.t('rc.builds') if build else i18n.t('rc.no_files')}")
    lines += ["", i18n.t("rc.skipped", days=args.days, list=", ".join(f"{n} ({age:.1f} {i18n.t('unit.d')})" for n, _, age, _, _ in skipped))]
    if unreadable:
        lines += ["", i18n.t("rc.unreadable", list=", ".join(f"{n} ({why})" for n, why in unreadable))]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4]), "...", i18n.t("rc.summary", n=len(rows), m=len(skipped)))
    if unreadable:
        print(i18n.t("rc.unreadable", list=", ".join(f"{n} ({why})" for n, why in unreadable)))
        raise SystemExit(2)      # a list made with a failed read is not complete: it never ends as if all was well


if __name__ == "__main__":
    main()
