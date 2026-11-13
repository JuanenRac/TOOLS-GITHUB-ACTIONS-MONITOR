#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Draft of release notes from the commits since the last tag. A PROPOSAL for a person to edit: it reads the local clone with `git log`, prints
Markdown (or writes it to a file you name) and never publishes, tags, pushes or touches GitHub.

  py -3 release_notes.py REPO [--root DIR] [--since TAG] [--out FILE]

REPO is a folder name under the workspace root (MONITOR_ROOT, "workspace_root" in actions_monitor.json, or --root). Commit subjects that mention
internal-review wording, tool names or co-author trailers are left out of the draft (they do not belong in public notes); the footer says how many were left out.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from github_actions_monitor import i18n
from github_actions_monitor.util import platform_compat


class _Text(dict):
    """TEXT[key] -> the text in the current language (keys are the texts "rn.<key>" of locales/*.json)."""

    def __getitem__(self, key):
        return i18n.t("rn." + key)


TEXT = _Text.fromkeys(("no_clone", "no_commits", "heading", "since", "start", "footer", "d_refused", "wrote", "left_out"), "")
GROUPS = (("feat", "Added"), ("fix", "Fixed"), ("perf", "Performance"), ("docs", "Documentation"), ("refactor", "Changed"), ("test", "Tests"), ("ci", "CI"), ("build", "Build"), ("chore", "Maintenance"))
LEFT_OUT = re.compile(r"audit|claude|assistant|co-authored|\bAI\b", re.I)
PREFIX = re.compile(r"^(\w+)(?:\([^)]*\))?!?:\s*(.+)$")


def git(root, repo, *args):
    done = subprocess.run(["git", "-C", str(Path(root) / repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    return done.stdout.strip() if done.returncode == 0 else ""


def last_tag(root, repo):
    return git(root, repo, "describe", "--tags", "--abbrev=0")


def subjects(root, repo, since=None):
    span = f"{since}..HEAD" if since else "HEAD"
    out = git(root, repo, "log", span, "--no-merges", "--format=%s")
    return [line for line in out.splitlines() if line.strip()]


def draft(subject_lines, since=None):
    """Markdown from commit subjects, grouped by their conventional prefix; pure function (the tests call it)."""
    groups = {title: [] for _, title in GROUPS}
    groups["Other"] = []
    kept = left = 0
    for line in subject_lines:
        if LEFT_OUT.search(line):
            left += 1
            continue
        match = PREFIX.match(line)
        title = next((t for p, t in GROUPS if match and match.group(1).lower() == p), "Other")
        groups[title].append(match.group(2) if match and title != "Other" else line)
        kept += 1
    if not kept:
        return TEXT["heading"] + "\n\n" + TEXT["no_commits"] + "\n"
    lines = [TEXT["heading"], "", i18n.t("rn.since", what=since or TEXT["start"]), ""]
    for title, items in groups.items():
        if items:
            lines += [f"### {title}", ""] + [f"- {item[:1].upper() + item[1:]}" for item in items] + [""]
    lines.append(TEXT["footer"] + (" " + i18n.t("rn.left_out", n=left) if left else ""))
    return "\n".join(lines) + "\n"


def main():
    i18n.cli_language()
    platform_compat.console_utf8()
    ap = argparse.ArgumentParser(description=i18n.t("rn.description"), formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", help=i18n.t("rn.help_repo"))
    ap.add_argument("--root", help=i18n.t("rn.help_root"))
    ap.add_argument("--since", help=i18n.t("rn.help_since"))
    ap.add_argument("--out", help=i18n.t("rn.help_out"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = ap.parse_args()
    from github_actions_monitor.app import workspace
    root = Path(args.root) if args.root else workspace.workspace_root()
    if not (root / args.repo / ".git").exists():
        print(TEXT["no_clone"] + str(root / args.repo))
        return 2
    since = args.since or last_tag(root, args.repo) or None
    text = draft(subjects(root, args.repo, since), since)
    if args.out:
        if str(args.out).upper().startswith(("D:", "/MNT/D", "/D/")):
            print(TEXT["d_refused"])
            return 4
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
        print(TEXT["wrote"] + str(args.out))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
