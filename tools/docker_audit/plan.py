#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Plans a run of the container checks: which version to check, which checks, and which version came before it (the migration check starts from its image).

    python tools/docker_audit/plan.py --repo . --ref v2.0.8 --scenarios all --previous auto

Prints the plan as JSON; with GITHUB_OUTPUT set it also writes it there for the next jobs. The inputs are checked before anything uses them: a version name is letters, digits and `._/-`,
the list of checks is `all` or codes such as `E1,E3`.
"""
import argparse
import json
import os
import re
import subprocess
import sys

SCENARIOS = {
    "E1": ("e1_basic_start.py", 25, "Basic start, health check, API contract"),
    "E2": ("e2_team_mode.py", 25, "Team mode in a container"),
    "E3": ("e3_proxy.py", 35, "Behind a trusted proxy (Caddy, TLS)"),
    "E4": ("e4_hardening.py", 25, "Hardening: no root, read-only, no capabilities"),
    "E5": ("e5_volumes.py", 45, "Volumes, backup, restore, migration"),
    "E6": ("e6_secrets.py", 25, "Secrets"),
    "E7": ("e7_shutdown.py", 30, "SIGTERM, kill -9, memory"),
    "E8": ("e8_webhook.py", 35, "Webhook behind the proxy"),
    "E9": ("e9_shared_files.py", 25, "Files shared by several processes (os_lock, process_lock)"),
}
NAME = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")


def git(repo, *args):
    done = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else ""


def version_key(tag):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", tag.lstrip("v")))


def tags(repo):
    return sorted((t for t in git(repo, "tag", "--list", "v[0-9]*").splitlines() if re.fullmatch(r"v\d+(\.\d+)*", t)), key=version_key)


def plan(repo, ref, scenarios, previous):
    if scenarios.strip().lower() in ("", "all"):
        codes = list(SCENARIOS)
    else:
        codes = [c.strip().upper() for c in scenarios.split(",") if c.strip()]
        if not codes or any(c not in SCENARIOS for c in codes):
            raise SystemExit("the list of checks must be `all` or codes between E1 and E9 separated by commas: %r" % scenarios)
    known = tags(repo)
    ref = ref.strip() or (known[-1] if known else "")
    if not ref or not NAME.match(ref):
        raise SystemExit("the version to check must be a tag or a commit name: %r" % ref)
    previous = previous.strip()
    if previous in ("", "auto"):
        if ref in known:
            index = known.index(ref)
            previous = known[index - 1] if index > 0 else ""
        else:
            previous = known[-1] if known else ""
    elif previous.lower() in ("none", "no", "-"):
        previous = ""
    if previous and not NAME.match(previous):
        raise SystemExit("the previous version must be a tag or a commit name: %r" % previous)
    include = [{"code": c, "script": SCENARIOS[c][0], "minutes": SCENARIOS[c][1], "title": SCENARIOS[c][2]} for c in codes]
    return {"ref": ref, "ref_safe": re.sub(r"[^A-Za-z0-9._-]", "-", ref), "previous": previous if "E5" in codes else "", "codes": ",".join(codes), "matrix": {"include": include}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".", help="a clone of the repository with its tags")
    parser.add_argument("--ref", default="", help="tag or commit to check (default: the latest tag)")
    parser.add_argument("--scenarios", default="all", help="`all` or a list such as E1,E3")
    parser.add_argument("--previous", default="auto", help="the version before it, for the migration check (`auto`, a tag, or `none`)")
    args = parser.parse_args(argv)
    result = plan(args.repo, args.ref, args.scenarios, args.previous)
    print(json.dumps(result, indent=1))
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            for key, value in result.items():
                handle.write("%s=%s\n" % (key, json.dumps(value, separators=(",", ":")) if isinstance(value, dict) else value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
