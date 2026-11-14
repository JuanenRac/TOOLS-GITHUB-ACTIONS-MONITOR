# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A10 "Actions & releases surface": what the A1-A9 layers do not look at, in the order the owner reads it.

Everything here is READ ONLY and deterministic (no AI anywhere near red / signing). Three kinds of input, none of them written back to GitHub:
  * local files of the clones (workflow YAML read as text, manifests, CHANGELOG, dependabot.yml): free, refreshed `local_seconds`;
  * data the sentinel already has (runs of the monitor cache, the hot GraphQL pass, alerts, hygiene): free;
  * a few extra COLD calls (`refresh_seconds`, default one day per repository, spread over the ticks, never in the hot cycle):
      per repository  artifacts (1 REST call) and resolved secret alerts (1 REST call);
      one GraphQL query per 15 repositories: drafts/pre-releases, open milestones, required status checks (rulesets and branch protection);
      only for repositories that have required checks: the check runs of the default branch (1 REST call);
      only for red runs / sign-queue entries: the jobs of the run (matrix per OS, parity step), the attestation lookup by digest;
      GitHub Packages: 3 REST calls for the whole account.
Every check has a switch and, when it makes sense, a threshold, under `sentinel.surface.checks.<name>` in actions_monitor.json (DEFAULTS below is the
template that make_release compares with the example file). `sentinel.surface.enabled = false` turns the whole layer off.

The module never closes an issue, merges a pull request, publishes a release or writes to a repository: a suggestion is an event/text for a person.
"""
import copy
import hashlib
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from github_actions_monitor import i18n
from github_actions_monitor.util import platform_compat
from github_actions_monitor.app import toolconfig

BAD = ("failure", "timed_out", "startup_failure", "action_required")
HEX40 = re.compile(r"^[0-9a-fA-F]{40}\Z")
HIGH = ("critical", "high")

DEFAULTS = {
    "enabled": True,
    "refresh_seconds": 86400,      # cold cycle of the per-repository calls (artifacts, resolved secrets, check runs)
    "local_seconds": 3600,         # local file scan (workflow YAML, manifests, CHANGELOG)
    "max_repos_per_tick": 6,       # repositories whose cold calls are made in one sentinel tick (2 REST calls each)
    "min_rate_factor": 2.0,        # no cold call while the allowance left is below min_rate_remaining x this (the page then says "A10 paused for quota")
    "budget_share": 0.5,           # fraction (0-1) of the sentinel's per-tick call budget that A10 may use; the rest stays for A3-A6. Conservative: half
    "checks": {
        "workflows_disabled": {"enabled": True},
        "dead_schedule": {"enabled": True, "days": 14},
        "unpinned_uses": {"enabled": True},
        "broad_permissions": {"enabled": True},
        "pr_target": {"enabled": True},
        "stuck_concurrency": {"enabled": True, "minutes": 60},
        "matrix_os": {"enabled": True, "max_per_tick": 4},
        "artifacts": {"enabled": True, "max_mb": 500, "retention_days": 30},
        "required_checks": {"enabled": True},
        "release_assets": {"enabled": True, "recent_days": 30, "required": {"default": ["sha256", "sig"], "apk-build.yml": ["sha256"]}},
        "tag_vs_version": {"enabled": True},
        "packages": {"enabled": True},
        "drafts": {"enabled": True, "days": 14},
        "security_aged": {"enabled": True, "days": 30},
        "coverage": {"enabled": True},
        "secret_resolved": {"enabled": True},
        "dependabot_priority": {"enabled": True},
        "issue_close": {"enabled": True},
        "milestones": {"enabled": True},
        "pr_human": {"enabled": True, "days": 7},
        "pr_workflow_touch": {"enabled": True},
        "merge_queue": {"enabled": True},
        "maturity": {"enabled": True},
        "parity": {"enabled": True},
        "attestation": {"enabled": True, "max_per_tick": 3},
    },
}

# (key, column keys) of every section of the tab; the order is the order of the page. The title of a section is the text "surf.t.<key>", a column
# is the text "col.<name>" (see locales/*.json); the sentences the module shows are "surf.<name>", with {} filled in.
SECTIONS = (
    ("workflows_disabled", ("repo", "workflow")),
    ("dead_schedule", ("repo", "workflow", "cron", "detail")),
    ("unpinned_uses", ("repo", "file", "reference", "type")),
    ("broad_permissions", ("repo", "file")),
    ("pr_target", ("repo", "file", "detail")),
    ("stuck_concurrency", ("repo", "workflow", "queued", "oldest")),
    ("matrix_os", ("repo", "run", "fails_on", "passes_on")),
    ("artifacts", ("repo", "artifacts", "size", "detail")),
    ("required_checks", ("repo", "check", "state")),
    ("release_assets", ("repo", "release", "missing")),
    ("tag_vs_version", ("repo", "tag", "manifest", "changelog", "notice")),
    ("packages", ("package", "type", "repo")),
    ("drafts", ("repo", "tag", "type", "age")),
    ("security_aged", ("repo", "critical", "high", "oldest", "overdue")),
    ("coverage", ("repo", "stack", "missing")),
    ("secret_resolved", ("repo", "open", "resolved")),
    ("dependabot_priority", ("priority", "repo", "pr", "title")),
    ("issue_close", ("repo", "issue", "reason", "command")),
    ("milestones", ("ecosystem", "repo", "milestone", "due")),
    ("pr_human", ("repo", "pr", "title", "age")),
    ("pr_workflow_touch", ("repo", "pr", "title", "touches")),
    ("merge_queue", ("repo", "pr", "title", "age")),
    ("maturity", ("repo", "maturity", "evidence", "notice")),
    ("parity", ("repo", "run", "detail")),
)
COLUMNS = {key: cols for key, cols in SECTIONS}
COPY_COLUMNS = {"issue_close": [3]}   # columns that hold a command: the page shows a Copy button next to it
EVENT_CHECK = {"required_check_red": "required_checks", "release_incomplete": "release_assets", "security_aged": "security_aged",
               "issue_close_suggest": "issue_close", "pr_workflow_touch": "pr_workflow_touch"}   # an event follows the switch of the check that makes it


def t(key, /, **values):
    return i18n.t(key, **values)


def owner():
    return toolconfig.github_owner()


def title_and_columns(key):
    return t("surf.t." + key), [t("col." + c) for c in COLUMNS[key]]


def pending_texts():
    """Things the layer does NOT do yet, said honestly."""
    return {"stale_cards": t("surf.pending_stale_cards")}


def settings(config):
    """The merged surface settings from actions_monitor.json (`sentinel.surface`), over DEFAULTS; unknown keys are dropped, a bad type keeps the default."""
    merged = copy.deepcopy(DEFAULTS)
    user = ((config or {}).get("sentinel") or {}).get("surface") if isinstance((config or {}).get("sentinel"), dict) else None
    if not isinstance(user, dict):
        return merged
    for key in DEFAULTS:
        if key == "checks":
            continue
        value = user.get(key)
        if isinstance(value, type(DEFAULTS[key])) and not (isinstance(value, bool) != isinstance(DEFAULTS[key], bool)):
            merged[key] = value
    for name, base in DEFAULTS["checks"].items():
        mine = (user.get("checks") or {}).get(name)
        if not isinstance(mine, dict):
            continue
        for key, default in base.items():
            if key in mine and isinstance(mine[key], type(default)) and isinstance(mine[key], bool) == isinstance(default, bool):
                merged["checks"][name][key] = mine[key]
    return merged


def on(cfg, name):
    return bool(cfg["enabled"] and cfg["checks"].get(name, {}).get("enabled"))


def parse_time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if text else None
    except (ValueError, TypeError):
        return None


def age_days(text, now):
    stamp = parse_time(text)
    return round((now - stamp).total_seconds() / 86400, 1) if stamp else None


# ---------- local files: workflow YAML as text ----------
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^\s'\"#]+)", re.M)
CRON = re.compile(r"^\s*-?\s*cron:\s*['\"]?([^'\"#\n]+?)['\"]?\s*(?:#.*)?$", re.M)
WRITE_ALL = re.compile(r"^\s*permissions:\s*write-all\b", re.M)
PRT = re.compile(r"(?m)^\s*pull_request_target\s*:|^\s*on:\s*\[[^\]]*pull_request_target|^\s*-\s*pull_request_target\b")
PR_REF = re.compile(r"ref:\s*['\"]?\$\{\{[^}]*(?:pull_request\.head|head_ref|refs/pull)[^}]*\}\}|ref:\s*['\"]?refs/pull/", re.I)
SCHEDULE_KEY = re.compile(r"(?m)^\s*schedule\s*:")


ON_KEY = re.compile(r"""^(?:on|"on"|'on'|true|True|TRUE)\s*:\s*(.*)$""")
# events whose runs never sit on the default branch: manual, release, called, and pull requests (their runs are on the pull request ref, so a workflow
# that only has pull_request never has a run "on main" and must not make A2 inconclusive)
OFF_BRANCH_EVENTS = {"workflow_dispatch", "release", "workflow_call", "pull_request", "pull_request_target"}


def _strip_comment(line):
    return re.sub(r"\s+#.*$", "", line).rstrip()


def workflow_events(text):
    """The events in the `on:` of a workflow, from its text (stdlib only): {event: text of its block}, or None when it cannot be parsed
    (flow map, odd layout, no `on:`). Accepts `on:` as a string, a list (flow or block) or a map, and the key `true` that YAML 1.1 makes of an unquoted `on`."""
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        match = ON_KEY.match(_strip_comment(raw)) if raw[:1] not in (" ", "\t", "#", "") else None
        if not match:
            continue
        inline = match.group(1).strip()
        if inline.startswith("{"):
            return None
        if inline.startswith("["):
            if not inline.endswith("]"):
                return None
            names = [n.strip().strip("'\"") for n in inline[1:-1].split(",") if n.strip()]
            return {n: "" for n in names} or None
        if inline:
            return {inline.strip("'\""): ""}
        body = []
        for nxt in lines[i + 1:]:
            clean = _strip_comment(nxt)
            if not clean.strip():
                continue
            if nxt[:1] not in (" ", "\t"):
                break
            body.append(clean)
        if not body:
            return None
        base = len(body[0]) - len(body[0].lstrip())
        events, current = {}, None
        for line in body:
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            if indent == base:
                if stripped.startswith("- "):
                    events[stripped[2:].strip().strip("'\"")] = ""
                    current = None
                    continue
                key = re.match(r"""^['"]?([A-Za-z_]+)['"]?\s*:\s*(.*)$""", stripped)
                if not key:
                    return None
                current = key.group(1)
                events[current] = key.group(2)
            elif current is not None:
                events[current] += "\n" + stripped
            else:
                return None
        return events or None
    return None


def main_triggered(text):
    """True when the workflow can run on the default branch (push, pull_request, schedule or anything not known to be manual/release/tag/called),
    False when it only runs on workflow_dispatch, release, tag pushes or workflow_call, None when `on:` cannot be parsed (counts as True, conservatively)."""
    events = workflow_events(text)
    if events is None:
        return None
    for event, block in events.items():
        if event in OFF_BRANCH_EVENTS:
            continue
        if event == "push" and re.search(r"\btags\s*:", block) and not re.search(r"\bbranches(?:-ignore)?\s*:", block):
            continue
        return True
    return False


def scan_workflow(text, name=""):
    """What one workflow file says, from its text (no YAML parser on purpose: the standard library only). Returns plain data."""
    unpinned, reusable = [], []
    for spec in USES.findall(text):
        if spec.startswith(("./", "docker://")) or "@" not in spec:
            continue
        path, _, ref = spec.partition("@")
        if HEX40.match(ref):
            continue
        (reusable if ".github/workflows/" in path else unpinned).append(spec)
    prt = bool(PRT.search(text))
    return {"file": name, "unpinned": sorted(set(unpinned)), "reusable_unpinned": sorted(set(reusable)), "write_all": bool(WRITE_ALL.search(text)),
            "main_triggered": main_triggered(text), "prt": prt, "prt_danger": bool(prt and PR_REF.search(text)),
            "cron": sorted(set(m.strip() for m in CRON.findall(text))) if SCHEDULE_KEY.search(text) else []}


STACKS = (("package.json", "node"), ("pyproject.toml", "python"), ("requirements.txt", "python"), ("setup.py", "python"), ("Cargo.toml", "rust"),
          ("go.mod", "go"), ("build.gradle", "java/kotlin"), ("build.gradle.kts", "java/kotlin"), ("pom.xml", "java"), ("CMakeLists.txt", "c/c++"))
CHANGELOG_TOP = re.compile(r"^## \[(\d[^\]]*)\]", re.M)


def read_text(path, limit=262144):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return None


def scan_clone(path):
    """One clone, read only: workflow scan, stacks, dependabot.yml / CodeQL workflow, manifest and CHANGELOG version. None when there is no clone."""
    base = Path(path)
    if not (base / ".git").exists():
        return None
    workflows, codeql = [], False
    folder = base / ".github" / "workflows"
    try:
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix in (".yml", ".yaml"))[:60] if folder.is_dir() else []
    except OSError:
        files = []
    for file in files:
        text = read_text(file)
        if text is None:
            continue
        codeql = codeql or "github/codeql-action" in text
        workflows.append(scan_workflow(text, file.name))
    stacks = sorted({name for fname, name in STACKS if (base / fname).is_file()})
    manifest = None
    try:
        found = sorted(base.glob("*.project.json"))
    except OSError:
        found = []
    if found:
        text = read_text(found[0])
        try:
            import json
            data = json.loads(text) if text else {}
            manifest = {"file": found[0].name, "version": str(data.get("version") or ""), "maturity": str(data.get("maturity") or ""), "evidence": str(data.get("evidence") or ""),
                        "role": str(data.get("role") or "")}
        except ValueError:
            manifest = None
    changelog = read_text(base / "CHANGELOG.md", 65536)
    top = None
    if changelog:
        match = next((m for m in CHANGELOG_TOP.finditer(changelog) if m.group(1).strip().lower() != "unreleased"), None)
        top = match.group(1).strip() if match else None
    return {"workflows": workflows, "stacks": stacks, "dependabot_yml": any((base / ".github" / n).is_file() for n in ("dependabot.yml", "dependabot.yaml")),
            "codeql_yml": codeql, "manifest": manifest, "changelog_top": top}


# ---------- pure rules (tested without network) ----------
VERSION_TAG = re.compile(r"^v?\d+\.\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?\Z")


def is_version_tag(tag):
    """True for a tag that is a version (`v1.2`, `0.8.0.1`, `v2.0.0-rc1`); `meshes-1` or `nightly` are labels of another kind and say nothing about the manifest."""
    return bool(VERSION_TAG.match(str(tag or "").strip()))


def remote_manifest_version(gh, owner_name, repo, file, branch):
    """The `version` of the manifest as it is on the default branch of GitHub (one call), or None. The clone on this computer may be behind after a release."""
    import base64
    import json
    try:
        data = gh("api", f"repos/{owner_name}/{repo}/contents/{file}?ref={branch}", retries=1) or {}
        return str(json.loads(base64.b64decode(data.get("content") or "").decode("utf-8")).get("version") or "") or None
    except Exception:       # noqa: BLE001 - a missing file or a bad answer leaves the local reading
        return None
def version_tuple(text):
    nums = re.findall(r"\d+", str(text or ""))
    return tuple(int(n) for n in nums[:4]) if nums else None


def compare_versions(a, b):
    """-1, 0, 1 or None (one of them has no digits). Missing trailing components count as zero."""
    ta, tb = version_tuple(a), version_tuple(b)
    if ta is None or tb is None:
        return None
    size = max(len(ta), len(tb))
    ta, tb = ta + (0,) * (size - len(ta)), tb + (0,) * (size - len(tb))
    return (ta > tb) - (ta < tb)


OS_NAMES = (("windows", re.compile(r"windows|\bwin(?:32|64)?\b", re.I)), ("macos", re.compile(r"macos|\bmac\b|darwin|osx", re.I)),
            ("linux", re.compile(r"ubuntu|linux|debian", re.I)))


def os_of(job_name):
    """The operating system a matrix job name names, or None: 'build (windows-latest, 3.12)' -> windows."""
    inside = re.search(r"\(([^)]*)\)", job_name or "")
    text = inside.group(1) if inside else (job_name or "")
    for name, pattern in OS_NAMES:
        if pattern.search(text):
            return name
    return None


def summarize_jobs(jobs):
    """From the jobs of one run: the operating systems that failed and the ones that passed, plus the names of failed jobs/steps."""
    failed_os, ok_os, failed_names = set(), set(), []
    for job in jobs or []:
        system = os_of(job.get("name"))
        if job.get("conclusion") in BAD:
            failed_names.append(str(job.get("name")))
            failed_names += [str(s.get("name")) for s in job.get("steps") or [] if s.get("conclusion") in BAD]
            if system:
                failed_os.add(system)
        elif job.get("conclusion") == "success" and system:
            ok_os.add(system)
    return {"failed_os": sorted(failed_os), "ok_os": sorted(ok_os - failed_os), "failed": failed_names[:12]}


def artifacts_summary(artifacts, now):
    """From the `actions/artifacts` list: live count, bytes, the oldest live one in days and the longest retention given to one."""
    live = [a for a in artifacts or [] if not a.get("expired")]
    longest = 0.0
    oldest = None
    for item in live:
        created, expires = parse_time(item.get("created_at")), parse_time(item.get("expires_at"))
        if created and expires:
            longest = max(longest, (expires - created).total_seconds() / 86400)
        when = age_days(item.get("created_at"), now)
        if when is not None:
            oldest = when if oldest is None else max(oldest, when)
    return {"count": len(live), "bytes": sum(int(a.get("size_in_bytes") or 0) for a in live), "oldest_days": oldest, "retention_days": round(longest)}


def required_check_problems(required, check_runs):
    """[(context, 'red'|'missing')] for the required contexts against the check runs of the default branch head (name -> conclusion/None)."""
    seen = {}
    for check in check_runs or []:
        name = check.get("name")
        if name:
            if seen.get(name) in BAD:
                continue
            seen[name] = check.get("conclusion") if check.get("status") == "completed" else "pending"
    out = []
    for context in required or []:
        if context not in seen:
            out.append((context, "missing"))
        elif seen[context] in BAD:
            out.append((context, "red"))
    return out


def asset_template(workflow, cfg):
    spec = cfg["checks"]["release_assets"]["required"]
    return list(spec.get(workflow) or spec.get("default") or [])


def missing_assets(flags, required):
    """The required signature companions that the published release does not carry; flags None = the release has no assets at all."""
    if flags is None:
        return ["assets"]
    return [name for name in required if not flags.get(name)]


def secret_and_dependabot_age(info, alerts, now):
    """[(source, severity, age_days)] of the critical/high alerts of one repository: Dependabot (createdAt from the hot GraphQL pass) and CodeQL."""
    out = []
    for item in info.get("vuln_hi") or []:
        out.append(("dependabot", item.get("sev"), age_days(item.get("created"), now)))
    for item in (alerts or {}).get("codeql") or []:
        sev = (item.get("severity") or "").lower()
        if sev in HIGH:
            out.append(("codeql", sev, age_days(item.get("created"), now)))
    return out


def dependabot_priority(prs):
    """Dependabot PRs ordered by what matters: 1 = major bump of a runtime dependency, 2 = other runtime bump, 3 = major CI-only, 4 = other CI-only."""
    rows = []
    for pr in prs:
        ci_only = bool(pr.get("ci_only"))
        major = pr.get("major") is True
        rank = (3 if major else 4) if ci_only else (1 if major else 2)
        rows.append({**pr, "priority": rank})
    return sorted(rows, key=lambda p: (p["priority"], -(p.get("age_days") or 0), p["repo"]))


ISSUE_RUN = re.compile(r"actions/runs/(\d+)|\brun\s*#?(\d{6,})", re.I)


def _words(text):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).split())


def workflow_in_title(run, title):
    """True when the title of an issue names the workflow of this run: by its name ("Build failed: Build") or by the name of its file without the extension
    ("Firmware build failed" for firmware-build.yml). Whole words only."""
    haystack = " " + _words(title) + " "
    stem = str(run.get("path") or "").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    for candidate in (run.get("name"), stem):
        words = _words(candidate)
        if words and " " + words + " " in haystack:
            return True
    return False


def issue_close_suggestions(issues, runs_by_repo, red_keys, branches, now):
    """Open build-failed/build-stuck issues whose workflow is green again. NEVER closes anything: each row carries the text of `gh issue close`.
    The issue is tied to a run by a run id/URL in its title, else to a workflow by its name (or the name of its file, `firmware-build.yml` for "Firmware build failed")
    in the title. When nothing ties the issue to a workflow there is no suggestion: a green run of ANOTHER workflow says nothing about the one that failed. The latest
    completed run of that same workflow on the default branch must be a success and newer than the issue. (`red_keys` is kept for the callers.)"""
    rows = []
    for issue in issues:
        repo, number = issue["repo"], issue["number"]
        branch = (branches or {}).get(repo) or "main"
        runs = [r for r in runs_by_repo.get(repo, []) if r.get("status") == "completed" and r.get("branch") == branch
                and r.get("conclusion") not in ("cancelled", "skipped", "neutral", "stale")]
        if not runs:
            continue
        title = issue.get("title") or ""
        match = ISSUE_RUN.search(title)
        linked = next((r for r in runs_by_repo.get(repo, []) if match and r.get("id") == int(match.group(1) or match.group(2))), None)
        if linked:
            scope = [r for r in runs if r.get("path") == linked.get("path") or r.get("name") == linked.get("name")] or runs
        else:
            scope = [r for r in runs if workflow_in_title(r, title)]
        if not scope:
            continue
        last = max(scope, key=lambda r: r.get("started") or "")
        created = issue.get("created")
        if last.get("conclusion") != "success" or (created and (last.get("started") or "") <= created):
            continue
        text = t("surf.issue_comment", wf=last.get("name"), run=last.get("id"))
        command = platform_compat.command_text(["gh", "issue", "close", str(number), "-R", f"{owner()}/{repo}", "--comment", text])
        rows.append({"repo": repo, "number": number, "title": title[:100], "url": issue.get("url"), "reason": t("surf.issue_reason", wf=last.get("name"), run=last.get("id")),
                     "run_url": last.get("url"), "linked_run": bool(linked), "command": command})
    return sorted(rows, key=lambda r: (r["repo"], r["number"]))


def dead_schedules(scan, runs, days, now):
    """[(file, cron, detail)] of the schedules of one clone with no `schedule` run inside the window. Needs the sample of runs to cover the window:
    otherwise a missing run may be hidden beyond the sample and it is NOT reported (it is counted in `unverifiable`)."""
    started = [parse_time(r.get("started")) for r in runs if r.get("started")]
    oldest = min(started) if started else None
    covers = bool(oldest and (now - oldest).total_seconds() >= days * 86400)
    rows, unverifiable = [], 0
    for wf in scan.get("workflows") or []:
        if not wf.get("cron"):
            continue
        mine = [r for r in runs if r.get("event") == "schedule" and r.get("path") == wf["file"]]
        last = max((parse_time(r.get("started")) for r in mine if r.get("started")), default=None)
        if last and (now - last).total_seconds() < days * 86400:
            continue
        if not covers and not last:
            unverifiable += 1
            continue
        rows.append((wf["file"], ", ".join(wf["cron"][:2]), t("surf.dead_detail_last", when=last.strftime("%Y-%m-%d") if last else t("surf.dead_detail_none", d=days))))
    return rows, unverifiable


def stuck_groups(runs, minutes, now):
    """[(workflow path, queued count, oldest minutes)] where two or more runs of the same workflow wait in the queue and the oldest has waited too long."""
    groups = {}
    for run in runs:
        if run.get("status") in ("queued", "waiting", "pending") and run.get("event") != "dynamic":
            groups.setdefault(run.get("path") or run.get("name"), []).append(run)
    rows = []
    for path, items in groups.items():
        oldest = max(((now - parse_time(r["started"])).total_seconds() / 60 for r in items if parse_time(r.get("started"))), default=0)
        if len(items) >= 2 and oldest >= minutes:
            rows.append((path, len(items), round(oldest)))
    return rows


# ---------- the section builder ----------
def _section(key, rows, level=None, note="", links=None):
    title, cols = title_and_columns(key)
    return {"key": key, "title": title, "cols": cols, "rows": rows, "count": len(rows), "note": note, "copy": COPY_COLUMNS.get(key, []),
            "level": level or ("warn" if rows else "ok")}


def build(inp):
    """The A10 block from plain inputs (the tests call it directly). Keys of `inp`: now, cfg (merged surface settings), repos, eco, repo_info, alerts,
    perms, runs, branches, scans (repo -> scan_clone), raw (repo -> cold data), globals, red (A2 rows), issues, prs (classified PRs), states (A5 states),
    queue (A5 sign queue), mins (minutes per repo), rate."""
    cfg, now = inp["cfg"], inp["now"]
    if not cfg["enabled"]:
        return {"enabled": False, "level": "unknown", "sections": [], "events": {}, "pending": pending_texts(), "note": t("surf.off")}
    repos, eco = inp["repos"], inp["eco"]
    info, alerts, perms, runs_by = inp["repo_info"], inp["alerts"], inp.get("perms") or {}, inp["runs"]
    scans, raw, glob = inp.get("scans") or {}, inp.get("raw") or {}, inp.get("globals") or {}
    branches = inp.get("branches") or {}
    sections, events = {}, {}
    disabled = []

    def put(key, rows, **kw):
        if not on(cfg, key):
            disabled.append(key)
            return
        sections[key] = _section(key, rows, **kw)

    def event(kind, level, repo, text, key, url=None):
        if kind in EVENT_CHECK and not on(cfg, EVENT_CHECK[kind]):
            return
        events[f"{kind}|{key}"] = {"kind": kind, "code": kind, "level": level, "repo": repo, "text": text, "url": url}

    # B1 workflows
    rows = [[repo, name] for repo in sorted(repos) for name in (perms.get(repo) or {}).get("wf_manual") or []]
    put("workflows_disabled", rows, level="warn" if rows else "ok")
    rows, unverifiable = [], 0
    for repo in sorted(repos):
        scan = scans.get(repo)
        if scan:
            found, hidden = dead_schedules(scan, runs_by.get(repo, []), cfg["checks"]["dead_schedule"]["days"], now)
            unverifiable += hidden
            rows += [[repo, f, cron, detail] for f, cron, detail in found]
    put("dead_schedule", rows, note=t("surf.dead_unverifiable", n=unverifiable, d=cfg["checks"]["dead_schedule"]["days"]) if unverifiable else "")
    rows = []
    for repo in sorted(repos):
        for wf in (scans.get(repo) or {}).get("workflows") or []:
            rows += [[repo, wf["file"], spec, t("surf.kind_reusable")] for spec in wf["reusable_unpinned"]]
            rows += [[repo, wf["file"], spec, t("surf.kind_action")] for spec in wf["unpinned"]]
    reusable = sum(1 for r in rows if r[3] == t("surf.kind_reusable"))
    put("unpinned_uses", rows, level="bad" if reusable else ("warn" if rows else "ok"))
    rows = [[repo, wf["file"]] for repo in sorted(repos) for wf in (scans.get(repo) or {}).get("workflows") or [] if wf["write_all"]]
    put("broad_permissions", rows, level="bad" if rows else "ok")
    rows = [[repo, wf["file"], t("surf.prt_detail")]
            for repo in sorted(repos) for wf in (scans.get(repo) or {}).get("workflows") or [] if wf["prt_danger"]]
    put("pr_target", rows, level="bad" if rows else "ok")
    for repo, f, _ in (rows if on(cfg, "pr_target") else []):
        event("workflow_risk", "bad", repo, t("surf.ev_prt", repo=repo, file=f), f"{repo}|{f}|prt")
    for repo, f in sections.get("broad_permissions", {}).get("rows", []):
        event("workflow_risk", "warn", repo, t("surf.ev_write_all", repo=repo, file=f), f"{repo}|{f}|wa")
    rows = []
    for repo in sorted(repos):
        for path, count, minutes in stuck_groups(runs_by.get(repo, []), cfg["checks"]["stuck_concurrency"]["minutes"], now):
            rows.append([repo, path, count, f"{minutes} {t('unit.min')}"])
    put("stuck_concurrency", rows)
    rows = []
    for run_id, row in sorted((glob.get("jobs") or {}).items()):
        if row.get("failed_os") and row.get("ok_os"):
            rows.append([row.get("repo"), run_id, ", ".join(row["failed_os"]), ", ".join(row["ok_os"])])
    put("matrix_os", rows, level="warn" if rows else "ok")
    # artifacts
    rows, total = [], 0
    limit = cfg["checks"]["artifacts"]["max_mb"] * 1024 * 1024
    retention = cfg["checks"]["artifacts"]["retention_days"]
    for repo in sorted(repos):
        art = (raw.get(repo) or {}).get("artifacts")
        if not art:
            continue
        total += art["bytes"]
        why = []
        if art["bytes"] > limit:
            why.append(t("surf.art_size", mb=cfg["checks"]["artifacts"]["max_mb"]))
        if art["retention_days"] > retention:
            why.append(t("surf.art_retention", d=art["retention_days"], limit=retention))
        if why:
            rows.append([repo, art["count"], f"{art['bytes'] / 1048576:.0f} MB", "; ".join(why)])
    put("artifacts", rows, note=t("surf.art_total", mb=total / 1048576))
    rows, reds = [], 0
    for repo in sorted(repos):
        r = raw.get(repo) or {}
        for context, state in required_check_problems(r.get("required"), r.get("check_runs")):
            rows.append([repo, context, t("surf.state_" + state)])
            reds += state == "red"
            if state == "red":
                event("required_check_red", "bad", repo, t("surf.ev_check_red", repo=repo, context=context), f"{repo}|{context}")
    put("required_checks", rows, level="bad" if reds else ("warn" if rows else "ok"))
    # B2 releases
    rows = []
    recent = cfg["checks"]["release_assets"]["recent_days"]
    seen = set()
    for st in inp.get("states") or []:
        repo = st["repo"]
        if (repo, st["workflow"]) in seen:
            continue
        seen.add((repo, st["workflow"]))
        rel = (info.get(repo) or {}).get("release")
        if not rel or (age_days(rel.get("publishedAt"), now) or 0) > recent:
            continue
        missing = missing_assets(rel.get("asset_flags"), asset_template(st["workflow"], cfg))
        if missing:
            rows.append([repo, rel.get("tagName"), ", ".join(missing)])
            event("release_incomplete", "bad", repo, t("surf.ev_release", repo=repo, tag=rel.get("tagName"), missing=", ".join(missing)), f"{repo}|{rel.get('tagName')}")
    put("release_assets", rows, level="bad" if rows else "ok")
    rows = []
    for repo in sorted(repos):
        scan = scans.get(repo) or {}
        man, top = (scan.get("manifest") or {}).get("version"), scan.get("changelog_top")
        rel = (info.get(repo) or {}).get("release")
        tag = rel.get("tagName") if rel else None
        remote = (info.get(repo) or {}).get("remote_manifest") or {}
        from_branch = bool(remote.get("version") and remote.get("tag") == tag)
        if from_branch:      # the manifest of the branch on GitHub, read after this release appeared: the clone may be behind (its CHANGELOG too)
            man = remote["version"]
        notes = []
        if tag and not is_version_tag(tag):
            tag = None
        if tag and man and compare_versions(tag, man) == 1:
            notes.append(t("surf.tag_after"))
        elif tag and man and compare_versions(man, tag) == 1:
            notes.append(t("surf.tag_before"))
        if man and top and not from_branch and compare_versions(man, top) not in (0, None):
            notes.append(t("surf.tag_changelog"))
        if notes:
            rows.append([repo, tag or "–", man or "–", top or "–", "; ".join(notes)])
    put("tag_vs_version", rows, level="warn" if any(t("surf.tag_after") in r[4] or t("surf.tag_changelog") in r[4] for r in rows) else ("info" if rows else "ok"))
    pk = glob.get("packages")
    put("packages", [[p.get("name"), p.get("type"), p.get("repo") or "–"] for p in (pk or {}).get("items") or []], level="info",
        note=(pk or {}).get("error") or (t("surf.pk_unread") if pk is None else ""))
    rows = []
    for repo in sorted(repos):
        for item in (raw.get(repo) or {}).get("drafts") or []:
            when = age_days(item.get("created"), now)
            if when is not None and when > cfg["checks"]["drafts"]["days"]:
                rows.append([repo, item.get("tag"), t("surf.draft") if item.get("draft") else t("surf.prerelease"), f"{when:.0f} {t('unit.d')}"])
    put("drafts", rows)
    # B3 security
    rows, ranking = [], []
    days = cfg["checks"]["security_aged"]["days"]
    for repo in sorted(repos):
        items = secret_and_dependabot_age(info.get(repo) or {}, alerts.get(repo), now)
        if not items:
            continue
        crit, high = sum(1 for i in items if i[1] == "critical"), sum(1 for i in items if i[1] == "high")
        ages = [i[2] for i in items if i[2] is not None]
        late = sum(1 for a in ages if a > days)
        ranking.append([repo, crit, high, f"{max(ages):.0f} {t('unit.d')}" if ages else "–", late])
        if late:
            event("security_aged", "bad", repo, t("surf.ev_aged", n=late, d=days, repo=repo), f"{repo}|{late}")
    ranking.sort(key=lambda r: (-r[1], -r[2], -r[4], r[0]))
    put("security_aged", ranking, level="bad" if any(r[4] for r in ranking) else ("warn" if ranking else "ok"))
    rows = []
    for repo in sorted(repos):
        scan = scans.get(repo)
        if not scan or not scan["stacks"]:
            continue
        missing = []
        if not scan["dependabot_yml"]:
            missing.append("Dependabot")
        if not scan["codeql_yml"] and (alerts.get(repo) or {}).get("codeql") is None:
            missing.append("CodeQL")
        if missing:
            rows.append([repo, ", ".join(scan["stacks"]), ", ".join(missing)])
    put("coverage", rows, note=t("surf.coverage_note"))
    rows = [[repo, (alerts.get(repo) or {}).get("secret") if (alerts.get(repo) or {}).get("secret") is not None else t("common.na"), (raw.get(repo) or {}).get("secret_resolved", t("common.na"))]
            for repo in sorted(repos) if ((alerts.get(repo) or {}).get("secret") or 0) or ((raw.get(repo) or {}).get("secret_resolved") or 0)]
    put("secret_resolved", rows, level="bad" if any(isinstance(r[1], int) and r[1] for r in rows) else ("info" if rows else "ok"))
    prs = [p for p in inp.get("prs") or [] if p.get("dependabot")]
    rows = [[p["priority"], p["repo"], "#%s" % p["number"], p["title"]] for p in dependabot_priority(prs)]
    put("dependabot_priority", rows, level="warn" if any(r[0] == 1 for r in rows) else ("info" if rows else "ok"),
        note=t("surf.dep_note"))
    # B4 issues
    red_keys = {(r["repo"], r["workflow"]) for r in inp.get("red") or []}
    sugg = issue_close_suggestions(inp.get("issues") or [], runs_by, red_keys, branches, now)
    put("issue_close", [[s["repo"], "#%s %s" % (s["number"], s["title"]), s["reason"], s["command"]] for s in sugg], level="info",
        note=t("surf.issue_note"))
    for s in sugg:
        event("issue_close_suggest", "info", s["repo"], t("surf.ev_issue", n=s["number"], repo=s["repo"], cmd=s["command"]), f"{s['repo']}#{s['number']}", s.get("url"))
    rows = []
    for repo in sorted(repos):
        for m in (raw.get(repo) or {}).get("milestones") or []:
            when = parse_time(m.get("due"))
            if when and when < now:
                rows.append([eco.get(repo, "other"), repo, m.get("title"), when.strftime("%Y-%m-%d")])
    put("milestones", sorted(rows))
    # B5 PRs
    allprs = inp.get("prs") or []
    humans = [p for p in allprs if not p.get("dependabot") and not p.get("draft")]
    put("pr_human", [[p["repo"], "#%s" % p["number"], p["title"], f"{p['age_days']} {t('unit.d')}"] for p in sorted(humans, key=lambda p: -(p.get("age_days") or 0))
                     if (p.get("age_days") or 0) > cfg["checks"]["pr_human"]["days"]])
    rows = [[p["repo"], "#%s" % p["number"], p["title"], "CODEOWNERS" if p.get("touches_codeowners") else "workflows"] for p in allprs if p.get("touches_workflows") or p.get("touches_codeowners")]
    put("pr_workflow_touch", rows, level="warn" if rows else "ok")
    for p in allprs:
        if p.get("touches_workflows") or p.get("touches_codeowners"):
            event("pr_workflow_touch", "warn", p["repo"], t("surf.ev_pr_touch", n=p["number"], repo=p["repo"], title=p["title"]), f"{p['repo']}#{p['number']}", p.get("url"))
    queue = [p for p in allprs if p.get("review") == "APPROVED" and p.get("checks") == "SUCCESS" and p.get("mergeable") == "MERGEABLE" and not p.get("draft")]
    put("merge_queue", [[p["repo"], "#%s" % p["number"], p["title"], f"{p['age_days']} {t('unit.d')}"] for p in queue], level="info" if queue else "ok")
    # B7 maturity and parity
    rows = []
    published = {s["repo"] for s in inp.get("states") or [] if s.get("published") or s.get("trusted")}
    signing = {s["repo"] for s in inp.get("states") or []}
    for repo in sorted(repos):
        man = (scans.get(repo) or {}).get("manifest")
        if not man or man["maturity"] != "established":
            continue
        notes = []
        if man["evidence"] == "none":
            notes.append(t("surf.mat_noevidence"))
        if repo in signing and repo not in published:
            notes.append(t("surf.mat_unsigned"))
        if notes:
            rows.append([repo, man["maturity"], man["evidence"], "; ".join(notes)])
    put("maturity", rows)
    rows = []
    for run_id, row in sorted((glob.get("jobs") or {}).items()):
        if any(re.search(r"parity|translation|readme", n, re.I) for n in row.get("failed") or []):
            rows.append([row.get("repo"), run_id, ", ".join(n for n in row["failed"] if re.search(r"parity|translation|readme", n, re.I))[:120]])
    for r in inp.get("red") or []:
        if re.search(r"parity|translation", r.get("workflow") or "", re.I) and not any(x[0] == r["repo"] for x in rows):
            rows.append([r["repo"], (r.get("url") or "").rsplit("/", 1)[-1], r["workflow"]])
    put("parity", rows, level="warn" if rows else "ok")
    # attestation (on the sign queue)
    att = glob.get("attestation") or {}
    missing_att = sorted(k for k, v in att.items() if v is False)
    levels = [s["level"] for s in sections.values()]
    level = "bad" if "bad" in levels else ("warn" if "warn" in levels else ("info" if "info" in levels else "ok"))
    if inp.get("loading"):
        level = "unknown" if level == "ok" else level
    collected = sum(1 for r in repos if (raw.get(r) or {}).get("at"))
    scanned = sum(1 for r in repos if r in scans)
    return {"enabled": True, "level": level, "sections": [sections[k] for k, _ in SECTIONS if k in sections], "events": events, "disabled": disabled,
            "pending": pending_texts(), "attestation": att, "attestation_missing": missing_att, "collected": collected, "scanned": scanned, "repos": len(repos),
            "calls_per_cycle": estimate_calls(cfg, len(repos), len(raw)), "note": ""}


def estimate_calls(cfg, repos, with_required):
    """Extra REST calls per cold cycle (one day by default) the layer makes in the worst case, for the page header."""
    per_repo = (1 if on(cfg, "artifacts") else 0) + (1 if on(cfg, "secret_resolved") else 0)
    graphql = -(-repos // 15) if any(on(cfg, k) for k in ("required_checks", "drafts", "milestones")) else 0
    return per_repo * repos + graphql + (3 if on(cfg, "packages") else 0)


# ---------- collector (the only part that talks to GitHub) ----------
def summarize_graphql_node(node, branch="main"):
    """Cold data from one GraphQL repository node: required checks, forgotten drafts/pre-releases, open milestones."""
    required = []
    for rule in (node.get("branchProtectionRules") or {}).get("nodes") or []:
        required += [c.get("context") for c in rule.get("requiredStatusChecks") or [] if c.get("context")]
    for rs in (node.get("rulesets") or {}).get("nodes") or []:
        if str(rs.get("enforcement", "")).upper() != "ACTIVE":
            continue
        for rule in (rs.get("rules") or {}).get("nodes") or []:
            if rule.get("type") == "REQUIRED_STATUS_CHECKS":
                required += [c.get("context") for c in ((rule.get("parameters") or {}).get("requiredStatusChecks")) or [] if c.get("context")]
    drafts = [{"tag": r.get("tagName"), "draft": bool(r.get("isDraft")), "created": r.get("createdAt")}
              for r in (node.get("releases") or {}).get("nodes") or [] if r.get("isDraft") or r.get("isPrerelease")]
    return {"required": sorted(set(required)), "drafts": drafts,
            "milestones": [{"title": m.get("title"), "due": m.get("dueOn")} for m in (node.get("milestones") or {}).get("nodes") or []]}


def graphql_query(owner=None):
    owner = owner or toolconfig.github_owner()
    return ("query($after:String){rateLimit{remaining cost} repositoryOwner(login:\"%s\"){repositories(first:15,after:$after,ownerAffiliations:OWNER,isArchived:false)"
            "{pageInfo{hasNextPage endCursor} nodes{name defaultBranchRef{name}"
            " releases(first:10,orderBy:{field:CREATED_AT,direction:DESC}){nodes{tagName isDraft isPrerelease createdAt}}"
            " milestones(states:OPEN,first:10){nodes{title dueOn}}"
            " branchProtectionRules(first:5){nodes{pattern requiredStatusChecks{context}}}"
            " rulesets(first:5){nodes{name enforcement rules(first:20){nodes{type parameters{... on RequiredStatusChecksParameters{requiredStatusChecks{context}}}}}}}}}}}") % owner


class Collector:
    """Cold collection with its own state: `raw` (repo -> data) and `glob` (jobs, packages, attestation). `gh(*args)` returns parsed JSON and may raise."""

    def __init__(self, gh, root, cfg, clock=time.time):
        self.gh, self.root, self.cfg, self.clock = gh, Path(root), cfg, clock
        self.raw, self.glob, self.scans = {}, {"jobs": {}, "attestation": {}}, {}
        self.scan_at, self.graphql_at, self.packages_at = 0.0, 0.0, 0.0
        self.lock = threading.RLock()
        self.errors = {}

    def load(self, data):
        if isinstance(data, dict):
            self.raw = data.get("raw") or {}
            glob = data.get("glob") or {}
            self.glob = {"jobs": glob.get("jobs") or {}, "attestation": glob.get("attestation") or {}, **{k: v for k, v in glob.items() if k not in ("jobs", "attestation")}}
            self.graphql_at, self.packages_at = float(data.get("graphql_at") or 0), float(data.get("packages_at") or 0)

    def dump(self):
        with self.lock:
            return {"raw": self.raw, "glob": self.glob, "graphql_at": self.graphql_at, "packages_at": self.packages_at}

    def forget(self, repos):
        """Makes the next tick look again at these repositories (used after `finalize`)."""
        with self.lock:
            for repo in repos:
                if repo in self.raw:
                    self.raw[repo]["at"] = 0
            self.scan_at = 0.0

    # -- local, free
    def scan_local(self, repos):
        if self.clock() - self.scan_at < self.cfg["local_seconds"]:
            return False
        fresh = {}
        for repo in repos:
            try:
                scan = scan_clone(self.root / repo)
            except Exception as error:   # one broken clone never stops the others
                self.errors["scan:" + repo] = str(error)[:100]
                continue
            if scan:
                fresh[repo] = scan
        with self.lock:
            self.scans = fresh
            self.scan_at = self.clock()
        return True

    # -- cold REST per repository
    def due(self, repos):
        now = self.clock()
        return sorted((r for r in repos if now - (self.raw.get(r) or {}).get("at", 0) > self.cfg["refresh_seconds"]), key=lambda r: (self.raw.get(r) or {}).get("at", 0))

    def fetch_repo(self, repo, branch="main"):
        checks, now = self.cfg["checks"], datetime.now(timezone.utc)
        out = {**(self.raw.get(repo) or {}), "at": self.clock()}
        calls = 0
        if on(self.cfg, "artifacts"):
            try:
                calls += 1
                data = self.gh("api", f"repos/{owner()}/{repo}/actions/artifacts?per_page=100", retries=1) or {}
                out["artifacts"] = artifacts_summary(data.get("artifacts"), now)
            except Exception as error:
                out["artifacts_error"] = str(error)[:80]
        if on(self.cfg, "secret_resolved"):
            try:
                calls += 1
                out["secret_resolved"] = len(self.gh("api", f"repos/{owner()}/{repo}/secret-scanning/alerts?state=resolved&per_page=100", retries=1) or [])
            except Exception:
                out["secret_resolved"] = None
        if on(self.cfg, "required_checks") and out.get("required"):
            try:
                calls += 1
                data = self.gh("api", f"repos/{owner()}/{repo}/commits/{branch}/check-runs?per_page=100", retries=1) or {}
                out["check_runs"] = [{"name": c.get("name"), "status": c.get("status"), "conclusion": c.get("conclusion")} for c in data.get("check_runs") or []]
            except Exception as error:
                out["check_error"] = str(error)[:80]
        return out, calls

    def confirm_manifests(self, repos, branches, budget):
        """When the tag of the latest release is ahead of the manifest read from the clone, reads the manifest from the default branch on GitHub once for that tag (the clone may be
        behind after a release; the old reading must not raise a warning). One call per repository and per release; returns the calls made."""
        used = 0
        for repo in sorted(repos):
            if used >= budget:
                break
            manifest = (self.scans.get(repo) or {}).get("manifest") or {}
            tag = ((self.raw.get(repo) or {}).get("release") or {}).get("tagName")
            if not (tag and is_version_tag(tag) and manifest.get("version") and manifest.get("file")) or compare_versions(tag, manifest["version"]) != 1:
                continue
            if ((self.raw.get(repo) or {}).get("remote_manifest") or {}).get("tag") == tag:
                continue
            used += 1
            version = remote_manifest_version(self.gh, owner(), repo, manifest["file"], branches.get(repo) or "main")
            with self.lock:
                self.raw.setdefault(repo, {"at": 0})["remote_manifest"] = {"tag": tag, "version": version or ""}
        return used

    def refresh_graphql(self, repos):
        """The one batched query (15 repositories per call) for required checks, drafts and milestones. Returns the number of calls."""
        if self.clock() - self.graphql_at < self.cfg["refresh_seconds"] or not any(on(self.cfg, k) for k in ("required_checks", "drafts", "milestones")):
            return 0
        wanted, after, calls = set(repos), None, 0
        while True:
            args = ["api", "graphql", "-f", "query=" + graphql_query()] + (["-f", "after=" + after] if after else [])
            calls += 1
            data = self.gh(*args, retries=2)["data"]["repositoryOwner"]["repositories"]
            with self.lock:
                for node in data["nodes"]:
                    if node["name"] in wanted:
                        entry = self.raw.setdefault(node["name"], {"at": 0})
                        entry.update(summarize_graphql_node(node))
            if not data["pageInfo"]["hasNextPage"]:
                break
            after = data["pageInfo"]["endCursor"]
        self.graphql_at = self.clock()
        return calls

    def refresh_packages(self):
        if self.clock() - self.packages_at < self.cfg["refresh_seconds"] or not on(self.cfg, "packages"):
            return 0
        items, calls, error = [], 0, ""
        for kind in ("container", "npm", "maven"):
            calls += 1
            try:
                for pkg in self.gh("api", f"users/{owner()}/packages?package_type={kind}&per_page=100", retries=0) or []:
                    items.append({"name": pkg.get("name"), "type": kind, "repo": (pkg.get("repository") or {}).get("name")})
            except Exception as exc:
                error = t("surf.pk_error", e=str(exc)[:80])
        with self.lock:
            self.glob["packages"] = {"items": items, "error": error}
        self.packages_at = self.clock()
        return calls

    def fetch_jobs(self, red_rows, limit):
        """Jobs of red runs not looked at yet (matrix per OS, parity step). Returns the calls made."""
        if not (on(self.cfg, "matrix_os") or on(self.cfg, "parity")):
            return 0
        calls = 0
        for row in red_rows:
            run_id = (row.get("url") or "").rsplit("/", 1)[-1]
            if not run_id.isdigit() or run_id in self.glob["jobs"]:
                continue
            if calls >= limit:
                break
            calls += 1
            try:
                jobs = (self.gh("api", f"repos/{owner()}/{row['repo']}/actions/runs/{run_id}/jobs?per_page=50", retries=1) or {}).get("jobs", [])
                with self.lock:
                    self.glob["jobs"][run_id] = {"repo": row["repo"], **summarize_jobs(jobs)}
            except Exception:
                with self.lock:
                    self.glob["jobs"][run_id] = {"repo": row["repo"], "failed_os": [], "ok_os": [], "failed": []}
        with self.lock:   # runs that are no longer red are forgotten, so the table does not grow for ever
            keep = {(r.get("url") or "").rsplit("/", 1)[-1] for r in red_rows}
            for run_id in [k for k in self.glob["jobs"] if k not in keep]:
                self.glob["jobs"].pop(run_id, None)
        return calls

    def fetch_attestation(self, queue, signed_files, limit):
        """Attestation EXISTENCE by digest (no signature check) for the entries of the sign queue. `signed_files(repo)` -> [(name, sha256)]. Returns calls."""
        if not on(self.cfg, "attestation"):
            return 0
        calls = 0
        for entry in queue:
            key = f"{entry['repo']}|{entry.get('run_id')}"
            if key in self.glob["attestation"] or not entry.get("run_id"):
                continue
            files = signed_files(entry["repo"])[:2]
            if not files:
                continue
            if calls >= limit:
                break
            result = False
            for _, digest in files:
                calls += 1
                try:
                    data = self.gh("api", f"repos/{owner()}/{entry['repo']}/attestations/sha256:{digest}", retries=0) or {}
                    if data.get("attestations"):
                        result = True
                        break
                except Exception as error:
                    text = str(error).lower()
                    if "404" not in text and "not found" not in text:
                        result = "unknown"
                        break
            with self.lock:
                self.glob["attestation"][key] = result
        with self.lock:
            live = {f"{q['repo']}|{q.get('run_id')}" for q in queue}
            for key in [k for k in self.glob["attestation"] if k not in live]:
                self.glob["attestation"].pop(key, None)
        return calls

    def tick(self, repos, branches, budget, red_rows, queue, signed_files, rate_ok=True):
        """One pass of the cold work, bounded by `budget` calls. Returns the calls made. Local scan always (free); network only when rate_ok."""
        if not self.cfg["enabled"]:
            return 0
        self.scan_local(repos)
        if not rate_ok or budget <= 0:
            return 0
        used = 0
        try:
            used += self.refresh_graphql(repos)
            used += self.refresh_packages()
        except Exception as error:
            self.errors["graphql"] = str(error)[:100]
        for repo in self.due(repos)[: self.cfg["max_repos_per_tick"]]:
            if used >= budget:
                break
            entry, calls = self.fetch_repo(repo, branches.get(repo) or "main")
            used += calls
            with self.lock:
                self.raw[repo] = entry
        if used < budget:
            used += self.confirm_manifests(repos, branches, budget - used)
        if used < budget:
            used += self.fetch_jobs(red_rows, min(self.cfg["checks"]["matrix_os"]["max_per_tick"], budget - used))
        if used < budget:
            used += self.fetch_attestation(queue, signed_files, min(self.cfg["checks"]["attestation"]["max_per_tick"], budget - used))
        return used


def signed_files_of(signed_root, repo):
    """[(name, sha256)] of the files of the newest signed folder of a repository (what the signing tool published), for the attestation lookup."""
    base = Path(signed_root) / repo
    try:
        folders = [d for d in base.iterdir() if d.is_dir() and d.name.startswith("release-")]
        newest = max(folders, key=lambda d: [int(n) for n in re.findall(r"\d+", d.name)])
        files = sorted(f for f in newest.iterdir() if f.is_file() and not f.name.endswith((".sig", ".sig2", ".sha256", ".imgsig", ".json", ".hdr2", ".txt")))
    except (OSError, ValueError):
        return []
    out = []
    for f in files[:3]:
        try:
            h = hashlib.sha256()
            with open(f, "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    h.update(block)
            out.append((f.name, h.hexdigest()))
        except OSError:
            continue
    return out
