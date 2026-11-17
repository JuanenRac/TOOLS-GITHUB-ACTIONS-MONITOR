#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A small linter for the workflow files of a repository (`.github/workflows/*.yml`), to run BEFORE you push. Read-only and local: it opens files, nothing else.

  py -3 bin/lint_workflows.py [PATH ...] [--remote OWNER/REPO ...] [--json] [--fail-on info|warn|bad] [--lang CODE]

With no PATH it looks at `.github/workflows` of the current folder. A PATH is a workflow file or a folder that holds them (or a repository root). `--remote OWNER/REPO` reads the workflow
files of a repository from GitHub through `gh` instead (no clone; one call for the list and one for each file) and says why when it cannot (SSO not authorised, no access).

Rules (each one can be switched off and given another severity in actions_monitor.json, `lint.rules.<rule>`):

  unpinned_uses      `uses:` of an action or reusable workflow that is not pinned to a full commit SHA (a tag or branch can be moved by its owner)
  permissions        no `permissions:` block (the token gets the default, broader permissions) or `write-all`
  secrets_in_clear   what looks like a token, key or password written in the file instead of coming from `secrets.*`. Only a value that LOOKS real is serious (a known token format, or
                     a long string with the entropy of a key); a readable filler (`placeholder`, `dummy`, `changeme`, `ci`...) is only information and any other value is a warning
  injection          a text controlled by someone else (`github.event.*.title`, `body`, `head_ref`...) pasted into a `run:` script
  pr_target          `pull_request_target` together with a checkout of the pull request's code (it runs untrusted code with the repository's permissions)

Optional rules (off until `lint.rules.<rule>.enabled` is true):

  no_timeout         a job without `timeout-minutes` (a stuck job runs for six hours; a call of a reusable workflow carries the limit of the called one)
  secrets_inherit    `secrets: inherit` in a call of a reusable workflow (the called workflow receives every secret of the caller)
  own_action_main    a `uses:` of an action of your own account that follows a branch (`@main`, `@master`) instead of a tag or a commit

`unpinned_uses` tells an action of your own account (`lint.own_owners`, plus `github_owner`) from one of a third party in the `kind` of the finding; `lint.unpinned_own` can lower the own ones to
information (`info`) or leave them out (`ignore`); the default (`same`) treats them like the rest.

A finding can be silenced where it is, with a comment on the same line or on the line before: `# monitor-lint: ignore secrets_in_clear because it is a filler for docker compose config`
(a rule name, or `all`). The monitor also reads `lint.ignore` (patterns `repository:file:rule`, with `*`). The VALUE of a suspected secret is never printed or stored: a finding names the
line, the variable and the kind of pattern only.

The reading is textual (there is no YAML parser on purpose); a line it cannot understand is skipped, never guessed. Exit code: 0 when nothing reaches --fail-on (default `bad`), 1 otherwise.
"""
import argparse
import fnmatch
import json
import math
import re
import sys
from pathlib import Path

from github_actions_monitor import i18n  # noqa: E402

SHA_RE = re.compile(r"^[0-9a-f]{40}\Z")
USES_RE = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^'\"\s#]+)")
SEVERITIES = ("info", "warn", "bad")
EXIT_NOT_READ = 2      # `--remote` could not read a repository (or its name is not OWNER/REPO): never "clean"
RULES = ("unpinned_uses", "permissions", "secrets_in_clear", "injection", "pr_target", "no_timeout", "secrets_inherit", "own_action_main")
DEFAULT_SEVERITY = {"unpinned_uses": "warn", "permissions": "warn", "secrets_in_clear": "bad", "injection": "warn", "pr_target": "bad", "no_timeout": "warn", "secrets_inherit": "warn", "own_action_main": "info"}
OPTIONAL = ("no_timeout", "secrets_inherit", "own_action_main")      # off until the person switches them on: a new rule never adds findings by itself
OWN_MODES = ("same", "info", "ignore")
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{1,39}\Z")
MOVING_REFS = ("main", "master", "develop", "dev", "trunk", "head")
SECRET_PATTERNS = [
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")), ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")), ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")), ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")), ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
]
ASSIGN_RE = re.compile(r"""(?i)\b([\w-]*(?:password|passwd|secret|token|api[_-]?key)[\w-]*)\s*[:=]\s*['"]?([A-Za-z0-9/+_.=-]{8,})['"]?\s*(?:#.*)?$""")
FILLER = ("placeholder", "dummy", "example", "changeme", "change-me", "change_me", "fake", "sample", "not-a-real", "notreal", "redacted", "todo", "xxx", "test", "local", "demo", "nothing", "your-", "your_", "ci-", "-ci", "_ci",
          "value", "secret-here", "insert", "replace", "ignored", "unused", "empty", "none")
IGNORE_RE = re.compile(r"#\s*monitor-lint:\s*ignore\s+([a-z_]+)")
IGNORE_PATTERN_RE = re.compile(r"^[A-Za-z0-9._*-]{1,100}:[A-Za-z0-9._*/-]{1,100}:[a-z_*]{1,30}\Z")
ORDER = {"info": 0, "warn": 1, "bad": 2}
SOURCES = ("clone", "auto", "sparse")      # where the monitor reads the workflow files: the local clones only (default), the clones and, for the repositories without one, the API of GitHub, or a sparse clone
API_DEFAULTS = {"refresh_seconds": 21600, "max_calls_per_tick": 20, "max_files_per_repo": 40}
API_RANGES = {"refresh_seconds": (600, 604800), "max_calls_per_tick": (1, 200), "max_files_per_repo": (1, 100)}
SPARSE_DEFAULTS = {"refresh_seconds": 21600, "max_repos_per_tick": 2}
SPARSE_RANGES = {"refresh_seconds": (600, 604800), "max_repos_per_tick": (1, 20)}


def entropy(text):
    """Shannon entropy in bits per character."""
    if not text:
        return 0.0
    counts = {c: text.count(c) for c in set(text)}
    return -sum(n / len(text) * math.log2(n / len(text)) for n in counts.values())


def classify_value(value):
    """"filler" (a readable stand-in), "real" (it looks like a key) or "unknown". The value itself is only read here, never returned."""
    low = value.lower()
    if value.startswith(("$", "{")) or not value:
        return "reference"
    if any(word in low for word in FILLER):
        return "filler"
    if len(value) >= 20 and entropy(value) >= 3.5 and any(c.isdigit() for c in value) and any(c.isalpha() for c in value):
        return "real"
    if len(value) < 24 and entropy(value) < 3.0:
        return "filler"
    return "unknown"
UNTRUSTED = re.compile(r"\$\{\{\s*github\.(?:event\.(?:issue|pull_request|comment|review|discussion)\.(?:title|body)|event\.head_commit\.message|head_ref|event\.pages\.\*\.page_name)\s*\}\}")


def settings(config):
    """`lint` of the configuration: {"enabled", "refresh_seconds", "rules": {rule: {"enabled", "severity"}}}, merged over the defaults."""
    out = {"enabled": True, "refresh_seconds": 3600, "in_report": True, "ignore": [], "rules": {r: {"enabled": r not in OPTIONAL, "severity": DEFAULT_SEVERITY[r]} for r in RULES},
           "source": "clone", "api": dict(API_DEFAULTS), "sparse": dict(SPARSE_DEFAULTS)}
    out["rules"]["_own"] = {"owners": [], "unpinned": "same"}      # not a rule: who counts as "own" and what to do with an own action that is not pinned
    if config is not None:
        from github_actions_monitor.app import toolconfig
        mine = toolconfig.github_owner(config)
        if mine:
            out["rules"]["_own"]["owners"].append(mine.lower())
    user = (config or {}).get("lint")
    if not isinstance(user, dict):
        return out
    if user.get("source") in SOURCES:
        out["source"] = user["source"]
    for block, defaults, ranges in (("api", API_DEFAULTS, API_RANGES), ("sparse", SPARSE_DEFAULTS, SPARSE_RANGES)):
        given = user.get(block)
        for key in defaults if isinstance(given, dict) else ():
            value = given.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and ranges[key][0] <= value <= ranges[key][1]:
                out[block][key] = value
    if isinstance(user.get("own_owners"), list):
        out["rules"]["_own"]["owners"] += [x.lower() for x in user["own_owners"] if isinstance(x, str) and OWNER_RE.match(x)]
    if user.get("unpinned_own") in OWN_MODES:
        out["rules"]["_own"]["unpinned"] = user["unpinned_own"]
    if isinstance(user.get("ignore"), list):
        out["ignore"] = [x for x in user["ignore"] if isinstance(x, str) and IGNORE_PATTERN_RE.match(x)]
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

    def silenced(number, rule):
        for index in (number - 1, number - 2):      # the line itself and the one before
            if 0 <= index < len(lines):
                match = IGNORE_RE.search(lines[index])
                if match and match.group(1) in (rule, "all"):
                    return True
        return False

    def add(rule, line, detail="", severity=None, kind=""):
        cfg = rules.get(rule) or {}
        if cfg.get("enabled", rule not in OPTIONAL) and not silenced(line, rule):
            base = cfg.get("severity", DEFAULT_SEVERITY[rule])
            if severity and ORDER[severity] < ORDER[base]:
                base = severity      # a weaker class never gets more serious than the rule says, only less
            found.append({"file": name, "line": line, "rule": rule, "severity": base, "detail": detail, "kind": kind})

    own_info = rules.get("_own") or {}
    own_owners, own_mode = set(own_info.get("owners") or ()), own_info.get("unpinned", "same")
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
                own = spec.split("/", 1)[0].lower() in own_owners
                if own and own_mode == "ignore":
                    pass
                else:
                    add("unpinned_uses", number, spec, severity="info" if (own and own_mode == "info") else None, kind="own" if own else "third_party")
                if own and spec.split("@", 1)[1].lower() in MOVING_REFS:
                    add("own_action_main", number, spec)
            if spec.startswith("actions/checkout"):
                window = "\n".join(lines[number:number + 6])
                if re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head\.(?:sha|ref)", window) or re.search(r"ref:\s*\$\{\{\s*github\.head_ref", window):
                    checks_out_pr = True
        if re.match(r"^\s*permissions\s*:\s*write-all\s*$", line):
            add("permissions", number, "write-all")
        if re.match(r"^\s*secrets\s*:\s*inherit\s*(?:#.*)?$", line):
            add("secrets_inherit", number, "")
        known = next((label for label, pattern in SECRET_PATTERNS if pattern.search(line)), None)
        if known:
            add("secrets_in_clear", number, known, kind="known_pattern")
        else:
            assign = ASSIGN_RE.search(line)
            if assign and "secrets." not in line and "${{" not in line:
                kind = classify_value(assign.group(2))
                if kind == "real":
                    add("secrets_in_clear", number, assign.group(1), kind="high_entropy")
                elif kind == "unknown":
                    add("secrets_in_clear", number, assign.group(1), severity="warn", kind="unknown_value")
                elif kind == "filler":
                    add("secrets_in_clear", number, assign.group(1), severity="info", kind="filler")
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
    if (rules.get("no_timeout") or {}).get("enabled", False):
        for start, job in jobs_without_timeout(lines):
            add("no_timeout", start, job)
    return found


def jobs_without_timeout(lines):
    """[(line, job name)] of the jobs of a workflow that have no `timeout-minutes` (a call of a reusable workflow has no steps of its own and is left out)."""
    jobs_at = next((i for i, line in enumerate(lines) if re.match(r"jobs\s*:\s*$", line)), None)
    if jobs_at is None:
        return []
    starts = [(i, m.group(1)) for i, line in enumerate(lines[jobs_at + 1:], jobs_at + 1) for m in [re.match(r"^  ([A-Za-z0-9_-]+)\s*:\s*$", line)] if m]
    out = []
    for index, (start, job) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        block = lines[start + 1:end]
        if any(re.match(r"^    uses\s*:", line) for line in block):
            continue
        if not any(re.match(r"^    timeout-minutes\s*:", line) for line in block):
            out.append((start + 1, job))
    return out


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


def ignored(repo, finding, patterns):
    """True when a `lint.ignore` pattern (`repository:file:rule`, with `*`) matches the finding."""
    names = {finding["file"], finding["file"].rsplit("/", 1)[-1]}      # the path inside the repository or just the file name
    return any(fnmatch.fnmatchcase(f"{repo}:{name}:{finding['rule']}", pattern) for name in names for pattern in patterns or ())


def scan_clones(workspace_root, repos, rules=None, ignore=None):
    """{repo: [findings]} for the repositories that have a clone with workflows. Plain file reads, no network. `ignore` = the patterns of lint.ignore."""
    result = {}
    for repo in repos:
        clone = Path(workspace_root) / repo
        if (clone / ".github" / "workflows").is_dir():
            found = [f for f in lint_path(clone, rules, clone) if not ignored(repo, f, ignore)]
            if found:
                result[repo] = found
    return result


def lint_remote(reader, repos, rules=None, ignore=None):
    """{repo: [findings]} for the repositories whose workflow files were read without a clone (`remote_workflows.Reader`). Same rules and same `ignore` as `scan_clones`; no network here."""
    result = {}
    for repo in repos:
        texts = reader.texts(repo)
        found = []
        for name in sorted(texts):
            found += [f for f in lint_text(texts[name], ".github/workflows/" + name, rules) if not ignored(repo, f, ignore)]
        if found:
            result[repo] = found
    return result


def lint_remote_status(name, read=None):
    """`(findings, failure)` for `OWNER/REPO` read through the API of GitHub (no clone). `failure` is None when the repository was read, otherwise the reason why it was not (the name is not OWNER/REPO, the
    repository does not exist or the token cannot see it, SSO not authorised, no network...). Each failure is printed on the standard error. "Not read" is never the same as "read and clean"."""
    from github_actions_monitor.integrations import remote_workflows
    owner, _, repo = str(name).partition("/")
    if not (remote_workflows.NAME_RE.match(owner) and remote_workflows.NAME_RE.match(repo)):
        print(i18n.t("lint.remote_bad_name", name=str(name)[:80]), file=sys.stderr)
        return [], "bad_name"
    read = read or remote_workflows.gh_read
    reader = remote_workflows.Reader(read, lambda: owner)
    reader.refresh(repo, 400, 100)
    state = reader.state(repo) or {}
    reason = state.get("reason", "error") if state.get("state") == "not_evaluable" else ""
    if not reason and not (reader.texts(repo) or {}):
        try:      # no workflow folder: a repository without workflows, or a repository that is not there for this token
            read(f"repos/{owner}/{repo}")
        except Exception as error:      # noqa: BLE001 - the answer is the reason, never a traceback
            reason = remote_workflows.reason_of(error)
    if reason:
        print(i18n.t("lint.remote_failed", name=f"{owner}/{repo}", reason=i18n.t("lint.reason." + reason)), file=sys.stderr)
        return [], reason
    return lint_remote(reader, [repo]).get(repo, []), None


def lint_remote_name(name, read=None):
    """The findings of `OWNER/REPO` read through the API of GitHub (no clone): `[{"file", "line", "rule", "severity", "detail"}]`, file names as `.github/workflows/NAME`. A repository that cannot be
    read prints why on the standard error (SSO not authorised, no access...) and gives no findings; `lint_remote_status` also tells whether it was read."""
    return lint_remote_status(name, read)[0]


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
    ap.add_argument("--remote", action="append", metavar="OWNER/REPO", help=i18n.t("lint.help_remote"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = ap.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    findings = []
    for path in args.paths or ([] if args.remote else ["."]):
        findings += lint_path(path)
    unread = 0
    for name in args.remote or []:
        found, failure = lint_remote_status(name)
        findings += found
        unread += 1 if failure else 0
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=1))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}: [{f['severity']}] {i18n.t('lint.rule.' + f['rule'])}" + (f" ({f['detail']}{', ' + f['kind'] if f.get('kind') else ''})" if f["detail"] and f["detail"] != "missing" else ""))
        print(i18n.t("lint.summary", n=len(findings)))
    limit = SEVERITIES.index(args.fail_on)
    if any(SEVERITIES.index(f["severity"]) >= limit for f in findings):
        return 1
    return EXIT_NOT_READ if unread else 0      # a repository that could not be read is not a clean one


if __name__ == "__main__":
    sys.exit(main())
