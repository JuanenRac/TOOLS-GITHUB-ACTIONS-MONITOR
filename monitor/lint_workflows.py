#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A small linter for the workflow files of a repository (`.github/workflows/*.yml`), to run BEFORE you push. Read-only and local: it opens files, nothing else.

  py -3 lint_workflows.py [PATH ...] [--json] [--fail-on info|warn|bad] [--lang CODE]

With no PATH it looks at `.github/workflows` of the current folder. A PATH is a workflow file or a folder that holds them (or a repository root).

Rules (each one can be switched off and given another severity in actions_monitor.json, `lint.rules.<rule>`):

  unpinned_uses      `uses:` of an action or reusable workflow that is not pinned to a full commit SHA (a tag or branch can be moved by its owner)
  permissions        no `permissions:` block (the token gets the default, broader permissions) or `write-all`
  secrets_in_clear   what looks like a token, key or password written in the file instead of coming from `secrets.*`
  injection          a text controlled by someone else (`github.event.*.title`, `body`, `head_ref`...) pasted into a `run:` script
  pr_target          `pull_request_target` together with a checkout of the pull request's code (it runs untrusted code with the repository's permissions)

The reading is textual (there is no YAML parser on purpose); a line it cannot understand is skipped, never guessed. Exit code: 0 when nothing reaches --fail-on (default `bad`), 1 otherwise.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # works also under `py -3 -I`
import i18n  # noqa: E402

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^'\"\s#]+)")
SEVERITIES = ("info", "warn", "bad")
RULES = ("unpinned_uses", "permissions", "secrets_in_clear", "injection", "pr_target")
DEFAULT_SEVERITY = {"unpinned_uses": "warn", "permissions": "warn", "secrets_in_clear": "bad", "injection": "warn", "pr_target": "bad"}
SECRET_PATTERNS = [
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"), re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
]
ASSIGN_RE = re.compile(r"""(?i)\b[\w-]*(password|passwd|secret|token|api[_-]?key)[\w-]*\s*[:=]\s*['"]?([A-Za-z0-9/+_.=-]{12,})['"]?\s*$""")
UNTRUSTED = re.compile(r"\$\{\{\s*github\.(?:event\.(?:issue|pull_request|comment|review|discussion)\.(?:title|body)|event\.head_commit\.message|head_ref|event\.pages\.\*\.page_name)\s*\}\}")


def settings(config):
    """`lint` of the configuration: {"enabled", "refresh_seconds", "rules": {rule: {"enabled", "severity"}}}, merged over the defaults."""
    out = {"enabled": True, "refresh_seconds": 3600, "in_report": True, "rules": {r: {"enabled": True, "severity": DEFAULT_SEVERITY[r]} for r in RULES}}
    user = (config or {}).get("lint")
    if not isinstance(user, dict):
        return out
    if isinstance(user.get("enabled"), bool):
        out["enabled"] = user["enabled"]
    if isinstance(user.get("in_report"), bool):
        out["in_report"] = user["in_report"]
    if isinstance(user.get("refresh_seconds"), int) and not isinstance(user.get("refresh_seconds"), bool) and 60 <= user["refresh_seconds"] <= 86400:
        out["refresh_seconds"] = user["refresh_seconds"]
    rules = user.get("rules")
    if isinstance(rules, dict):
        for rule in RULES:
            item = rules.get(rule)
            if isinstance(item, dict):
                if isinstance(item.get("enabled"), bool):
                    out["rules"][rule]["enabled"] = item["enabled"]
                if item.get("severity") in SEVERITIES:
                    out["rules"][rule]["severity"] = item["severity"]
    return out


def lint_text(text, name="workflow.yml", rules=None):
    """The findings of one workflow file: [{"file", "line", "rule", "severity", "detail"}]. `rules` = settings()["rules"] (all on when None)."""
    rules = rules or settings(None)["rules"]
    lines = text.replace("\r\n", "\n").split("\n")
    found = []

    def add(rule, line, detail=""):
        cfg = rules.get(rule) or {}
        if cfg.get("enabled", True):
            found.append({"file": name, "line": line, "rule": rule, "severity": cfg.get("severity", DEFAULT_SEVERITY[rule]), "detail": detail})

    has_permissions = any(re.match(r"^permissions\s*:", l) for l in lines)
    has_job_permissions = any(re.match(r"^\s{2,}permissions\s*:", l) for l in lines)
    in_run = False
    run_indent = 0
    pr_target = any(re.match(r"^\s*(?:on\s*:\s*\[?.*)?pull_request_target\b", l) or re.match(r"^\s+pull_request_target\s*:", l) for l in lines)
    checks_out_pr = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        uses = USES_RE.match(line)
        if uses:
            spec = uses.group(1)
            if not spec.startswith(("./", "docker://")) and "@" in spec and not SHA_RE.match(spec.split("@", 1)[1]):
                add("unpinned_uses", number, spec)
            if spec.startswith("actions/checkout"):
                window = "\n".join(lines[number:number + 6])
                if re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head\.(?:sha|ref)", window) or re.search(r"ref:\s*\$\{\{\s*github\.head_ref", window):
                    checks_out_pr = True
        if re.match(r"^\s*permissions\s*:\s*write-all\s*$", line):
            add("permissions", number, "write-all")
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                add("secrets_in_clear", number, pattern.pattern[:20])
                break
        else:
            assign = ASSIGN_RE.search(line)
            if assign and not assign.group(2).startswith(("$", "{")) and "secrets." not in line and "${{" not in line:
                add("secrets_in_clear", number, assign.group(1).lower())
        run = re.match(r"^(\s*)-?\s*run:\s*(\|[+-]?|>[+-]?)?\s*(.*)$", line)
        if run:
            in_run = True
            run_indent = len(run.group(1))
            if run.group(3) and UNTRUSTED.search(run.group(3)):
                add("injection", number, "")
        elif in_run:
            indent = len(line) - len(line.lstrip())
            if indent <= run_indent and stripped:
                in_run = False
            elif UNTRUSTED.search(line):
                add("injection", number, "")
    if not has_permissions and not has_job_permissions and any(re.match(r"^jobs\s*:", l) for l in lines):
        add("permissions", 1, "missing")
    if pr_target and checks_out_pr:
        add("pr_target", 1, "")
    return found


def workflow_files(path):
    path = Path(path)
    if path.is_file():
        return [path]
    base = path / ".github" / "workflows" if (path / ".github" / "workflows").is_dir() else path
    try:
        return sorted(p for p in base.iterdir() if p.is_file() and p.suffix in (".yml", ".yaml"))
    except OSError:
        return []


def lint_path(path, rules=None, root=None):
    """The findings of every workflow file under `path`; file names are shown relative to `root` when given."""
    out = []
    for file in workflow_files(path):
        try:
            text = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        label = str(file.relative_to(root)).replace("\\", "/") if root and Path(root) in file.parents else file.name
        out += lint_text(text, label, rules)
    return out


def scan_clones(workspace_root, repos, rules=None):
    """{repo: [findings]} for the repositories that have a clone with workflows. Plain file reads, no network."""
    result = {}
    for repo in repos:
        clone = Path(workspace_root) / repo
        if (clone / ".github" / "workflows").is_dir():
            found = lint_path(clone, rules, clone)
            if found:
                result[repo] = found
    return result


def summarize(by_repo):
    """{"findings": N, "repos": N, "bad": N, "warn": N, "info": N, "by_rule": {rule: N}, "top": [(repo, n)]} for the report."""
    counts = {"bad": 0, "warn": 0, "info": 0}
    by_rule = {}
    for items in by_repo.values():
        for item in items:
            counts[item["severity"]] += 1
            by_rule[item["rule"]] = by_rule.get(item["rule"], 0) + 1
    return {"findings": sum(counts.values()), "repos": len(by_repo), **counts, "by_rule": by_rule, "top": sorted(((r, len(v)) for r, v in by_repo.items()), key=lambda x: (-x[1], x[0]))[:5]}


def main(argv=None):
    i18n.cli_language()
    ap = argparse.ArgumentParser(description=i18n.t("lint.description"))
    ap.add_argument("paths", nargs="*", help=i18n.t("lint.help_paths"))
    ap.add_argument("--json", action="store_true", help=i18n.t("lint.help_json"))
    ap.add_argument("--fail-on", choices=SEVERITIES, default="bad", help=i18n.t("lint.help_fail_on"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = ap.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    findings = []
    for path in args.paths or ["."]:
        findings += lint_path(path)
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=1))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}: [{f['severity']}] {i18n.t('lint.rule.' + f['rule'])}" + (f" ({f['detail']})" if f["detail"] and f["detail"] != "missing" else ""))
        print(i18n.t("lint.summary", n=len(findings)))
    limit = SEVERITIES.index(args.fail_on)
    return 1 if any(SEVERITIES.index(f["severity"]) >= limit for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
