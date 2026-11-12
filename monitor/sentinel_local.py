#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Sentinel (layer A) for the local GitHub Actions monitor: deterministic, read-only, no AI needed.

It runs inside actions_monitor.py (a thread of its own, slower than the run refresh) and feeds the
"Centinela" tab through /api/sentinel. Everything comes from `gh` GET calls (REST and GraphQL queries)
plus the run cache of the monitor and a few local files; nothing is written to GitHub.

  A1 stuck / failed builds          A5 releases (rule of the owner, green builds without release)
  A2 CI in red (criterion below)    A6 hygiene (ruleset, SHA pinning, labels, files, disabled schedules)
  A3 CodeQL / Dependabot / secrets  A7 consumption (minutes, API allowance)
  A4 Dependabot pull requests       A8 state of the audits and rounds (local files only)
  A9 the GitHub Roadmap boards and whether they are alive (reads only; GitHub view needs gh with read:project)

Single criterion of "red": the LAST completed run of each workflow on the default branch (cancelled,
skipped and similar runs do not count). Cost control: one GraphQL query per 15 repositories every
refresh_seconds; alert details by REST per repository only when "hot" (alerts or a recent push) every
alerts_hot_seconds, the rest every alerts_cold_seconds; hygiene every hygiene_seconds; a cap per tick and an
hourly budget (budget_per_hour) of REST calls. The last picture is kept in sentinel_cache.json so the tab
shows something at once after a restart; the daily trend lives in sentinel_history.json (60 days).
"""
import degraded
import importlib.util
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import events
import i18n
import lint_workflows
import readiness
import redrule
import roadmap_a9
import sentinel_ai
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # works also under `py -3 -I`
import workspace
import ci_red
import signstate
import sigverify
import surface
import toolconfig
from tool_version import TOOL_VERSION
import private_io

HERE = Path(__file__).resolve().parent
GITHUB_DIR = workspace.workspace_root_soft()
SIGNED_DIR = workspace.signed_dir_soft()   # local records of the signing: batches/*.json and <REPO>/release-<version>/ (optional: without it the monitor runs in reduced mode)
AUDIT_DIR = workspace.audit_dir_soft()
CACHE_FILE = HERE / "sentinel_cache.json"
HISTORY_FILE = HERE / "sentinel_history.json"
HISTORY_DAYS = 60
# One criterion of "red", the same as the public dashboard (the profile repository's scripts/ci_watch.py: RED = failure, timed_out, startup_failure, action_required).
# A run that waits for an approval is red too: it needs a person. Cancelled, skipped, neutral and stale say nothing.
BAD = ("failure", "timed_out", "startup_failure", "action_required")
IGNORED = ("cancelled", "skipped", "neutral", "stale")
BOT_ACTORS = ("dependabot[bot]", "github-actions[bot]")   # plus the owner of the repositories (toolconfig.github_owner())
RELEASE_WF = re.compile(r"(release|build|publish|package|apk|firmware|exe|dist|site|sign|deploy)", re.I)
BUMP_RE = re.compile(r"[Bb]ump\s+(?P<pkg>\S+)\s+from\s+(?P<a>\S+)\s+to\s+(?P<b>\S+)")
DEFAULT_AUDIT_FILES = {"reconciliation": "RECONCILIATION_TOTAL_*.txt", "rounds": "ROUNDS_MAP_2*.txt", "rounds_extra": "ROUNDS_MAP_EXTRA_*.txt"}   # A8: names of the files of the audit folder

DEFAULTS = {
    "audit_files": dict(DEFAULT_AUDIT_FILES),
    "enabled": True, "refresh_seconds": 900, "alerts_hot_seconds": 900, "alerts_cold_seconds": 3600,
    "hygiene_seconds": 21600, "max_calls_per_tick": 70, "budget_per_hour": 600, "workers": 8,
    "candidate_days": 2.0, "pending_sign_hours": 24, "notify_command": [], "candidate_min_entries": 1, "stale_pr_days": 7, "hot_hours": 3,
    "required_files": [["README.md"], ["LICENSE", "LICENSE.md"], ["CHANGELOG.md"], ["SECURITY.md"]],
    "skip_candidate_prefixes": [], "min_rate_remaining": 800,
    # minutes_budget: ceiling of Actions minutes per ecosystem, e.g. {"hydra": 600}; empty = no ceiling. The period is "7d" (default) or "24h".
    "minutes_budget": {}, "minutes_budget_period": "7d",
    # ci_red_file: where ci_red.json (repo -> red workflows + pending_sign) is written: "" = next to the monitor, "off" = not written, or a path.
    "ci_red_file": "", "ci_red_audit_copy": False,
    # A signed folder lowers the pending-signature alert only when its signatures verify against the PUBLIC key pinned by the ecosystem
    # (sigverify.py). false = the old rule (a release-kind signature is enough). signature_pubkeys: {"armor"|"urtc"|"hydra": 64 hex digits} overrides
    # the keys read from the repositories (public keys only; no private key is ever read).
    "require_verified_signature": True, "signature_pubkeys": {},
    # a2_full_sample_unknown: A2 shows "unknown" (never green) while a repository's run list is as long as the sample asked for AND a workflow file of its
    # clone has no run in it (an older workflow may be hidden beyond the sample). false = the old behaviour (only informative).
    "a2_full_sample_unknown": True,
    # a2_resolve_*: a repository with a full run sample and a workflow of its clone missing from it is resolved by asking GitHub for the LAST run of that one
    # workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`): red counts as red in A2, none stays inconclusive for that workflow only.
    # Same quota gate as A10 (min_rate_remaining x surface.min_rate_factor, and the hourly budget). max_calls_per_tick 0 = never ask; ttl = how long an answer is kept.
    "a2_resolve_max_calls_per_tick": 4, "a2_resolve_ttl_seconds": 3600,
    # surface: the A10 layer ("Actions & releases surface"): a switch per check and its threshold, see surface.py (DEFAULTS is the template).
    "surface": surface.DEFAULTS,
    # readiness: the A11 layer (release readiness, ecosystem health, dependency pins), see readiness.py (DEFAULTS is the template).
    "readiness": readiness.DEFAULTS,
}


def sentinel_config(config):
    merged = dict(DEFAULTS)
    value = (config or {}).get("sentinel")
    if isinstance(value, dict):
        merged.update({k: v for k, v in value.items() if k in DEFAULTS})
    merged["surface"] = surface.settings(config)   # merged key by key: a partial block keeps the defaults of the rest
    merged["readiness"] = readiness.settings(config)
    return merged


def read_none(cfg):
    """The pin picture when there is nothing to read (no workspace or no source configured): every non-external ecosystem is listed as having no source."""
    return {"rows": [], "checked": 0, "sources": [], "missing": [], "at": None,
            "no_source": [k for k in toolconfig.ecosystem_names() if not toolconfig.is_external(k)]}


def parse_time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if text else None
    except ValueError:
        return None


# ---------- pure rules (tested without network) ----------

def workflow_key(run):
    return run.get("path") or run.get("name") or ""


def red_workflows(runs_by_repo, default_branches=None):
    """A2: the last completed run of each workflow on the default branch; red when it failed. Streak = consecutive reds. The rule lives in redrule.py (the lite edition uses it too)."""
    return redrule.red_workflows(runs_by_repo, default_branches)[0]


def a2_unchecked(runs_by_repo):
    """Repositories with no run data at all: they were NOT checked, so they must not count as green."""
    return sorted(r for r, runs in runs_by_repo.items() if not runs)


def a2_full_sample(runs_by_repo, cfg):
    """Repositories whose run list is as long as the sample asked for: an older workflow may be hidden beyond it (informative)."""
    caps = {int((cfg or {}).get("cold_runs_per_repo") or 0), int((cfg or {}).get("runs_per_repo") or 0)} - {0}
    return sorted(r for r, runs in runs_by_repo.items() if runs and len(runs) in caps)


def a2_missing(runs_by_repo, caps, scans=None):
    """Repositories with a full run sample that may hide a workflow, as {repo: [workflow file, ...]}: the files of the clone that count (they can run on the
    default branch: `main_triggered` is not False) and have no run in the sample. The value is None when nobody can tell (no clone, so a full sample is
    inconclusive by itself); an unparseable `on:` counts as before. A repository whose every counted file shows up in the sample is not in the result."""
    out = {}
    for repo in a2_full_sample(runs_by_repo, caps):
        listed = [w for w in ((scans or {}).get(repo) or {}).get("workflows") or [] if w.get("file")]
        if not listed:
            out[repo] = None
            continue
        seen = {workflow_key(r).rsplit("/", 1)[-1] for r in runs_by_repo.get(repo) or []}
        missing = sorted(w["file"] for w in listed if w.get("main_triggered") is not False and w["file"] not in seen)
        if missing:
            out[repo] = missing
    return out


A2_RESOLVE_DEPTH = 10                      # completed runs of one workflow asked for; the first with a real conclusion is the one that counts
A2_IGNORED_CONCLUSIONS = ("cancelled", "skipped")   # no verdict: they never hide an earlier red nor make a green


def a2_pick_concluded(answer):
    """The last run of a workflow that says something: completed, with a conclusion, neither cancelled nor skipped. A run in progress or a cancelled one is not
    "seen" (it could hide an earlier red), so the walk goes on to the previous one; none -> None (the workflow stays inconclusive on its own)."""
    for item in answer if isinstance(answer, list) else []:
        if not isinstance(item, dict):
            continue
        conclusion = item.get("conclusion") or None
        if (item.get("status") or "completed") != "completed" or not conclusion or conclusion in A2_IGNORED_CONCLUSIONS:
            continue
        return item
    return None


def a2_fresh(entry, now_ts, ttl):
    """A resolved entry (the last run of one workflow on the default branch, asked once) counts while it is younger than the TTL."""
    return bool(entry) and now_ts - float(entry.get("at") or 0) <= ttl


def a2_resolution(missing, resolved, now_ts, ttl, reason="pending"):
    """Applies the per-workflow answers to a2_missing: a workflow with a last run on the default branch is resolved (it is no longer hidden); one without any
    stays inconclusive with reason `no_runs`; one not asked yet (or whose answer expired) stays with `reason` (`quota` / `pending`). Returns the details
    [{repo, workflow (None without clone), reason}] and the repositories that still have one."""
    details = []
    for repo, files in sorted(missing.items()):
        if files is None:
            details.append({"repo": repo, "workflow": None, "reason": "no_clone"})
            continue
        for name in files:
            entry = (resolved or {}).get(f"{repo}|{name}")
            if a2_fresh(entry, now_ts, ttl):
                if entry.get("state") == "none":
                    details.append({"repo": repo, "workflow": name, "reason": "no_runs"})
                continue
            details.append({"repo": repo, "workflow": name, "reason": reason})
    return details, sorted({d["repo"] for d in details})


def a2_resolved_runs(resolved, branches, now_ts, ttl):
    """The resolved last runs as run records (same shape as the monitor's), so the A2 red rule treats them like any other run of the default branch."""
    out = {}
    for key, entry in (resolved or {}).items():
        if entry.get("state") != "run" or not a2_fresh(entry, now_ts, ttl):
            continue
        repo, _, name = key.partition("|")
        out.setdefault(repo, []).append({"repo": repo, "id": entry.get("id"), "name": entry.get("name") or name, "path": name, "branch": (branches or {}).get(repo) or entry.get("branch") or "main",
                                         "status": entry.get("status") or "completed", "conclusion": entry.get("conclusion"), "started": entry.get("started"), "url": entry.get("url"),
                                         "sha": entry.get("sha") or "", "seconds": None, "actor": "", "event": None, "title": ""})
    return out


def a2_inconclusive(runs_by_repo, caps, scans=None, resolved=None, now_ts=0.0, ttl=3600):
    """Repositories whose run sample is full AND may hide a workflow (see a2_missing), minus the workflows resolved by asking GitHub for their last run on the
    default branch (a2_resolution)."""
    return a2_resolution(a2_missing(runs_by_repo, caps, scans), resolved, now_ts, ttl)[1]


def a2_labels(details):
    """The readable list for the panel: the workflow is named, not only the repository."""
    out = []
    for d in details:
        base = d["repo"] if d["workflow"] is None else f'{d["repo"]}/{d["workflow"]}'
        note = i18n.t("ui.a2_reason_" + d["reason"])
        out.append(f"{base} ({note})")
    return out


def ecosystem_summary(s, eco):
    """One row per ecosystem (ARMOR, URTC, HYDRA, EH3D) with what every layer found, so an ecosystem with nothing to report still shows a row of zeros
    instead of silently missing from the panels. `eco` maps repo -> ecosystem key."""
    keys = tuple(toolconfig.ecosystem_names())
    rows = {k: {"repos": 0, "red": 0, "stuck": 0, "alerts": 0, "prs": 0, "candidates": 0, "pending_sign": 0, "hygiene": 0, "dep_off": 0} for k in keys}

    def bucket(repo):
        return rows.get(eco.get(repo) or "")

    for repo, kind in eco.items():
        if kind in rows:
            rows[kind]["repos"] += 1
    for r in s["a2"]["red"]:
        if bucket(r["repo"]):
            bucket(r["repo"])["red"] += 1
    for r in s["a1"]["stuck"]:
        if bucket(r["repo"]):
            bucket(r["repo"])["stuck"] += 1
    for r in s["a3"]["rows"]:
        if bucket(r["repo"]):
            bucket(r["repo"])["alerts"] += (r.get("codeql") or 0) + (r.get("dependabot") or 0) + (r.get("secret") or 0)
    for r in s["a4"]["dependabot"]:
        if bucket(r["repo"]):
            bucket(r["repo"])["prs"] += 1
    for r in s["a5"]["candidates"]:
        if bucket(r["repo"]):
            bucket(r["repo"])["candidates"] += 1
    for r in s["a5"].get("pending_sign") or []:
        if bucket(r["repo"]):
            bucket(r["repo"])["pending_sign"] += 1
    for repo in s["a3"].get("dependency_alerts_off") or []:
        if bucket(repo):
            bucket(repo)["dep_off"] += 1
    for r in s["a6"]["rows"]:
        if bucket(r["repo"]) and r.get("problems"):
            bucket(r["repo"])["hygiene"] += 1
    return rows


def parse_bump(title):
    match = BUMP_RE.search(title or "")
    return (match.group("pkg"), match.group("a"), match.group("b")) if match else None


def major_jump(old, new):
    a, b = re.match(r"v?(\d+)", old or ""), re.match(r"v?(\d+)", new or "")
    if not a or not b:
        return None
    return int(b.group(1)) > int(a.group(1))


def classify_pr(repo, pr, now):
    author = ((pr.get("author") or {}).get("login") or "").lower()
    files = [f.get("path", "") for f in ((pr.get("files") or {}).get("nodes") or [])]
    workflows = [p for p in files if p.startswith(".github/workflows/")]
    bump = parse_bump(pr.get("title"))
    created = parse_time(pr.get("createdAt"))
    return {
        "repo": repo, "number": pr.get("number"), "title": (pr.get("title") or "")[:140], "url": pr.get("url"),
        "dependabot": author in ("dependabot", "app/dependabot", "dependabot[bot]"), "draft": bool(pr.get("isDraft")),
        "age_days": round((now - created).total_seconds() / 86400, 1) if created else None,
        "conflict": pr.get("mergeable") == "CONFLICTING", "mergeable": pr.get("mergeable") or "UNKNOWN",
        "major": major_jump(bump[1], bump[2]) if bump else None, "pkg": bump[0] if bump else "",
        "grouped": bool(re.search(r"\b(group|updates)\b", pr.get("title") or "", re.I)) and not bump,
        "touches_workflows": bool(workflows),
        "touches_codeowners": any(p.rsplit("/", 1)[-1].upper() == "CODEOWNERS" for p in files),
        "ci_only": bool(files) and all(p.startswith(".github/") for p in files),
        "review": pr.get("reviewDecision") or "",
        "checks": ((((pr.get("commits") or {}).get("nodes") or [{}])[-1].get("commit") or {}).get("statusCheckRollup") or {}).get("state") or "",
        "touches_release_workflows": any(RELEASE_WF.search(p.rsplit("/", 1)[-1]) for p in workflows),
    }


def release_candidates_rule(unreleased, release_age_days, days, min_entries, skip_prefixes=()):
    """A5, rule of the owner: >= min_entries in [Unreleased] and last release older than `days` (or none)."""
    rows = []
    for repo, count in unreleased.items():
        if repo.startswith(tuple(skip_prefixes)) or count < min_entries:
            continue
        age = release_age_days.get(repo)
        if age is None or age > days:
            rows.append({"repo": repo, "entries": count, "age_days": None if age is None else round(age, 1)})
    return sorted(rows, key=lambda r: -r["entries"])


def green_without_release(targets, runs_by_repo, releases, default_branches=None):
    """A5: the latest successful run of a release workflow on the default branch is newer than the last release."""
    out, seen = [], set()
    for name, target in targets.items():
        repo, workflow = target.get("repo", name), target.get("workflow", "")
        if (repo, workflow) in seen:
            continue
        seen.add((repo, workflow))
        branch = (default_branches or {}).get(repo) or "main"
        runs = signstate.completed_runs(runs_by_repo.get(repo, []), branch, workflow)
        if not runs:
            continue
        last = max(runs, key=lambda r: r.get("started") or "")
        published = (releases.get(repo) or {}).get("publishedAt")
        if last.get("conclusion") == "success" and (not published or (last.get("started") or "") > published):
            out.append({"repo": repo, "workflow": workflow, "since": last.get("started"), "url": last.get("url"),
                        "release": (releases.get(repo) or {}).get("tagName", "")})
    return sorted(out, key=lambda r: r["repo"])


def pending_sign(green, now, hours):
    """A5: a green release build (built on GitHub) that has waited more than `hours` for the local signing and publishing."""
    out = []
    for g in green:
        since = parse_time(g.get("since"))
        if not since:
            continue
        waited = (now - since).total_seconds() / 3600
        if waited > hours:
            out.append({**g, "hours": round(waited, 1)})
    return sorted(out, key=lambda r: -r["hours"])


def hygiene_problems(info, perms, required_files):
    """A6: list of (code, text). `perms` None = not checked yet (not reported as a problem)."""
    problems = []
    rulesets = info.get("rulesets") or []
    if not any(r.get("name") == "protect-main" and str(r.get("enforcement", "")).upper() == "ACTIVE" for r in rulesets):
        problems.append(("ruleset", i18n.t("hyg.ruleset")))
    if not info.get("label_dependencies"):
        problems.append(("label", i18n.t("hyg.label")))
    present = info.get("files") or {}
    for group in required_files:
        if not any(present.get(name) for name in group):
            problems.append(("file", i18n.t("hyg.file", name="/".join(group))))
    if perms:
        if perms.get("sha_pinning_required") is not True:
            problems.append(("sha", i18n.t("hyg.sha")))
        if perms.get("allowed_actions") != "selected":
            problems.append(("allowed", f"allowed_actions={perms.get('allowed_actions')}"))
        for name in perms.get("wf_disabled") or []:
            problems.append(("schedule", i18n.t("hyg.schedule", name=name)))
    return problems


def alert_totals(alerts, repo_info):
    """Per repo: CodeQL open alerts, Dependabot alerts (GraphQL), secret scanning. Counts only known values."""
    rows = {}
    for repo, info in repo_info.items():
        a = alerts.get(repo) or {}
        codeql = a.get("codeql")
        rows[repo] = {"codeql": len(codeql) if codeql is not None else None, "dependabot": info.get("vuln_total", 0),
                      "secret": a.get("secret"), "sev": dict(info.get("vuln_sev") or {})}
        for item in codeql or []:
            sev = (item.get("severity") or "?").lower()
            rows[repo]["sev"][sev] = rows[repo]["sev"].get(sev, 0) + 1
    return rows


def update_history(history, today, totals, per_repo):
    days = history.setdefault("days", {})
    days[today] = {**totals, "repos": {k: v for k, v in per_repo.items() if any(v)}}
    for old in sorted(days)[:-HISTORY_DAYS]:
        days.pop(old, None)
    return history


def new_alerts_since(history, today, per_repo):
    """Positive differences per repo against the latest stored day before today. None = no reference yet."""
    previous = [d for d in (history.get("days") or {}) if d < today]
    if not previous:
        return None
    base = history["days"][max(previous)].get("repos") or {}
    out = {}
    for repo, now in per_repo.items():
        before = base.get(repo) or [0, 0, 0]
        delta = sum(max(0, n - b) for n, b in zip(now, before))
        if delta:
            out[repo] = delta
    return out


def trend(history, key):
    days = sorted((history.get("days") or {}))
    return {"dates": days, "values": [history["days"][d].get(key, 0) for d in days]}


def parse_audit_files(audit_dir, patterns=None):
    """A8: counts from the latest files of the audit folder named by `sentinel.audit_files` (file name patterns; the defaults are neutral and a project sets its own).
    Files only, no generation."""
    out = {"audits": {}, "rounds": {}, "files": []}
    names = dict(DEFAULT_AUDIT_FILES)
    names.update({k: v for k, v in (patterns or {}).items() if k in names and isinstance(v, str) and v.strip() and "/" not in v and "\\" not in v})
    try:
        recon = sorted(Path(audit_dir).glob(names["reconciliation"]))
        rounds = sorted(Path(audit_dir).glob(names["rounds"]))
        rounds_eh3d = sorted(Path(audit_dir).glob(names["rounds_extra"]))   # written by another session; read only
    except OSError:
        return out
    now = time.time()
    if recon:
        text = recon[-1].read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"^([A-Z0-9-]+): (\d+) IDs\s+(\{.*\})\s*$", text, re.M):
            try:
                counts = json.loads(match.group(3).replace("'", '"'))
            except ValueError:
                continue
            out["audits"][match.group(1)] = {"ids": int(match.group(2)), "counts": counts}
        out["files"].append({"name": recon[-1].name, "age_days": round((now - recon[-1].stat().st_mtime) / 86400, 1)})
    if rounds:
        text = rounds[-1].read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"^== SERIE ([A-Z0-9]+): (\{.*\})\s*$", text, re.M):
            try:
                out["rounds"][match.group(1)] = json.loads(match.group(2).replace("'", '"'))
            except ValueError:
                continue
        out["files"].append({"name": rounds[-1].name, "age_days": round((now - rounds[-1].stat().st_mtime) / 86400, 1)})
    if rounds_eh3d:
        text = rounds_eh3d[-1].read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"^== SERIE ([A-Z0-9-]+): (\{.*\})\s*$", text, re.M):
            try:
                out["rounds"]["EH3D " + match.group(1)] = json.loads(match.group(2).replace("'", '"'))
            except ValueError:
                continue
        out["files"].append({"name": rounds_eh3d[-1].name, "age_days": round((now - rounds_eh3d[-1].stat().st_mtime) / 86400, 1)})
    return out


def minutes(runs_by_repo, now):
    rows = {}
    for repo, runs in runs_by_repo.items():
        d1 = d7 = n1 = 0
        for run in runs:
            started = parse_time(run.get("started"))
            if not started:
                continue
            age = (now - started).total_seconds()
            if age <= 86400:
                d1 += run.get("seconds", 0)
                n1 += 1
            if age <= 7 * 86400:
                d7 += run.get("seconds", 0)
        if d7:
            rows[repo] = {"min24": round(d1 / 60), "min7d": round(d7 / 60), "runs24": n1}
    return rows


def minutes_budget(mins, eco, cfg):
    """A7: used minutes per ecosystem against the ceilings in cfg['minutes_budget'] ({"hydra": 600}); empty/invalid = no budget.
    Period 'minutes_budget_period': '7d' (default) or '24h'. Level: ok < 80 % <= warn < 100 % <= over."""
    limits = cfg.get("minutes_budget") if isinstance(cfg.get("minutes_budget"), dict) else {}
    key = "min24" if str(cfg.get("minutes_budget_period")) == "24h" else "min7d"
    rows = []
    for name in toolconfig.ecosystem_names():
        limit = limits.get(name)
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit <= 0:
            continue
        used = sum(v.get(key, 0) for repo, v in mins.items() if eco.get(repo) == name)
        pct = round(100.0 * used / limit, 1)
        rows.append({"ecosystem": name, "limit": limit, "used": used, "pct": pct, "period": "24h" if key == "min24" else "7d",
                     "level": "over" if pct >= 100 else ("warn" if pct >= 80 else "ok")})
    return rows


def minutes_by_ecosystem(mins, eco, cfg):
    """A7: Actions minutes used per ecosystem (24 h and 7 d, always, even without a budget) with the ceiling when one is set."""
    limits = cfg.get("minutes_budget") if isinstance(cfg.get("minutes_budget"), dict) else {}
    rows = []
    for name in toolconfig.ecosystem_names():
        part = [v for repo, v in mins.items() if eco.get(repo) == name]
        rows.append({"ecosystem": name, "min24": sum(v["min24"] for v in part), "min7d": sum(v["min7d"] for v in part), "limit": limits.get(name) if isinstance(limits.get(name), (int, float)) else None})
    return rows


def short_list(items, limit=5):
    items = list(items)
    return ", ".join(items[:limit]) + (i18n.t("parte.more", n=len(items) - limit) if len(items) > limit else "")


def build_parte(s):
    """The report, generated by rules (no AI), in the current language (see i18n.py): the important things first."""
    t = i18n.t
    red, stuck = len(s["a2"]["red"]), len(s["a1"]["stuck"])
    new = s["a3"]["new_total"] or 0
    cands = len(s["a5"]["candidates"])
    lines = []
    if s.get("reduced"):
        lines.append({"level": "info", "text": t("parte.reduced")})
    secret = s["a3"]["secret_total"]
    if secret:
        lines.append({"level": "bad", "text": t("parte.urgent_secret", n=secret, repos=short_list(s["a3"]["secret_repos"]))})
    if red:
        lines.append({"level": "bad", "text": t("parte.red", list=short_list(f"{r['repo']} ({r['workflow']})" for r in s["a2"]["red"]))})
    if stuck:
        lines.append({"level": "bad", "text": t("parte.stuck", list=short_list(f"{r['repo']} ({r['name']})" for r in s["a1"]["stuck"]))})
    if s["a1"]["issues"]:
        lines.append({"level": "warn", "text": t("parte.issues", n=len(s["a1"]["issues"]), repos=short_list(sorted({i['repo'] for i in s['a1']['issues']})))})
    high = s["a3"]["high_repos"]
    if high:
        lines.append({"level": "bad", "text": t("parte.high", repos=short_list(high))})
    if s["a3"].get("dependency_alerts_off"):
        off = s["a3"]["dependency_alerts_off"]
        lines.append({"level": "warn", "text": t("parte.dep_off", n=len(off), repos=short_list(off))})
    if s["a3"]["new"]:
        lines.append({"level": "warn", "text": t("parte.new_alerts", list=short_list(f"{k} +{v}" for k, v in s["a3"]["new"].items()))})
    mine = [c for c in s["a5"]["candidates"] if not toolconfig.is_external(toolconfig.ecosystem_of(c["repo"]))]
    theirs = [c for c in s["a5"]["candidates"] if toolconfig.is_external(toolconfig.ecosystem_of(c["repo"]))]
    if mine:
        lines.append({"level": "warn", "text": t("parte.decide_release", list=short_list(f"{c['repo']} ({c['entries']})" for c in mine))})
    if theirs:
        lines.append({"level": "info", "text": t("parte.external_unreleased", list=short_list(f"{c['repo']} ({c['entries']})" for c in theirs))})
    if s["a5"]["pending_sign"]:
        lines.append({"level": "warn", "text": t("parte.pending_sign", hours=s["a5"].get("pending_sign_hours", "N"), list=short_list(f"{g['repo']} ({g['hours']:.0f} {t('unit.h')})" for g in s["a5"]["pending_sign"]))})
    unverified = [g for g in s["a5"]["pending_sign"] if g.get("state") == "signed_local" and g.get("signature_kind") == "release"]
    if unverified:
        lines.append({"level": "warn", "text": t("parte.unverified", list=short_list(
            f"{g['repo']} ({t('parte.sig_bad') if g.get('signature_verified') is False else t('parte.sig_unchecked')})" for g in unverified))})
    if s["a5"].get("signed_unpublished"):
        lines.append({"level": "info", "text": t("parte.signed_unpublished", list=short_list(f"{g['repo']}" for g in s["a5"]["signed_unpublished"]))})
    for b in (s["a7"].get("budget") or []):
        if b["level"] != "ok":
            lines.append({"level": "bad" if b["level"] == "over" else "warn",
                          "text": t("parte.budget_over" if b["level"] == "over" else "parte.budget_warn", eco=b["ecosystem"], used=b["used"], limit=b["limit"], pct=f"{b['pct']:.0f}", period=b["period"])})
    if s["a5"]["green_unreleased"]:
        lines.append({"level": "info", "text": t("parte.green_unreleased", list=short_list(f"{g['repo']}" for g in s["a5"]["green_unreleased"]))})
    prs = s["a4"]["dependabot"]
    if prs:
        majors = sum(1 for p in prs if p["major"])
        conf = sum(1 for p in prs if p["conflict"])
        rel = sum(1 for p in prs if p["touches_release_workflows"])
        old = sum(1 for p in prs if (p["age_days"] or 0) > s["a4"]["stale_days"])
        lines.append({"level": "warn" if (majors or conf) else "info", "text": t("parte.dependabot", n=len(prs), majors=majors, conf=conf, rel=rel, old=old, days=s["a4"]["stale_days"])})
    queue_missing = [q for q in s["a5"].get("sign_queue") or [] if q.get("attestation") is False]
    if queue_missing:
        lines.append({"level": "warn", "text": t("parte.no_attestation", list=short_list(q["repo"] for q in queue_missing))})
    a10 = s.get("a10") or {}
    for sec in a10.get("sections") or []:
        if sec["level"] in ("bad", "warn") and sec["count"]:
            lines.append({"level": sec["level"], "text": t("parte.a10", title=sec["title"], n=sec["count"])})
    tag_rows = next((sec.get("rows") or [] for sec in a10.get("sections") or [] if sec.get("key") == "tag_vs_version"), [])
    ahead = [r[0] for r in tag_rows if len(r) > 4 and t("surf.tag_after") in str(r[4])]
    if ahead:   # a release tag that is ahead of the version of the manifest: the release was cut from a commit whose manifest says an older version
        lines.append({"level": "warn", "code": "tag_vs_manifest", "text": t("parte.tag_vs_manifest", n=len(ahead), list=short_list(ahead))})
    close_rows = next((sec.get("rows") or [] for sec in a10.get("sections") or [] if sec.get("key") == "issue_close"), [])
    if close_rows:   # one line, grouped by repository: the monitor closes nothing, it only suggests (the commands are in the A10 section)
        per_repo = {}
        for row in close_rows:
            per_repo[row[0]] = per_repo.get(row[0], 0) + 1
        lines.append({"level": "info", "code": "issue_close", "text": t("parte.issue_close", n=len(close_rows), list=short_list(f"{r} ({n})" for r, n in sorted(per_repo.items())))})
    lint = s.get("lint") or {}
    if lint.get("enabled") and lint.get("in_report") and (lint["summary"]["bad"] or lint["summary"]["warn"]):
        summary = lint["summary"]
        lines.append({"level": "bad" if summary["bad"] else "warn", "code": "workflow_lint",
                      "text": t("parte.lint", n=summary["findings"], repos=summary["repos"], bad=summary["bad"], warn=summary["warn"], list=short_list(f"{r} ({n})" for r, n in summary["top"]))})
    a11 = s.get("a11") or {}
    if a11.get("low_health"):
        lines.append({"level": "warn", "text": t("parte.a11_health", limit=a11.get("warn_below"), list=short_list(f"{toolconfig.label_of(h['ecosystem'])} ({h['score']})" for h in a11["low_health"]))})
    if a11.get("behind_repos"):
        lines.append({"level": "info", "text": t("parte.a11_pins", n=len(a11["behind_repos"]), list=short_list(a11["behind_repos"]))})
    minutes_line = ", ".join(f"{m['ecosystem']} {m['min24']}/{m['min7d']}" for m in s["a7"].get("by_ecosystem") or [] if m["min7d"])
    if minutes_line:
        lines.append({"level": "info", "text": t("parte.minutes", list=minutes_line)})
    hyg = [r for r in s["a6"]["rows"] if r["problems"]]
    if hyg:
        lines.append({"level": "warn", "text": t("parte.hygiene", n=len(hyg), list=short_list(f"{r['repo']}" for r in hyg))})
    if s["rate"] and s["rate"]["remaining"] < s["min_rate"]:
        lines.append({"level": "warn", "text": t("parte.rate_low", n=s["rate"]["remaining"])})
    if s["errors"]:
        lines.append({"level": "bad", "text": t("parte.errors", list=short_list((f"{e['section']}: {e['message']}" for e in s["errors"]), 3))})
    if s["loading"]:
        lines.append({"level": "info", "text": t("parte.loading", what=t("parte.starting") if s["loading"] == "starting" else s["loading"])})
    why = []
    if s["loading"]:
        why.append(t("parte.incomplete_loading"))
    if s.get("reduced"):
        why.append(t("parte.incomplete_reduced"))
    if s["errors"]:
        why.append(t("parte.incomplete_errors"))
    if why:
        lines.insert(0, {"level": "warn", "code": "incomplete", "text": t("parte.incomplete", why=", ".join(why))})
    pending = s["a5"]["pending_sign"]
    if pending:
        verified = sum(1 for g in pending if g.get("signature_verified") is True)
        bad = sum(1 for g in pending if g.get("signature_verified") is False)
        try:
            import gha_dispatch_all
            build_only = len(gha_dispatch_all.BUILD_ONLY)
        except BaseException:  # noqa: BLE001 - the catalogue is optional here (SystemExit when it is unreadable)
            build_only = 0
        lines.append({"level": "info", "code": "sign_summary", "text": t("parte.sign_summary", pending=len(pending), verified=verified, unchecked=len(pending) - verified - bad, bad=bad, build_only=build_only)})
    paused = (s.get("a10") or {}).get("paused")
    if paused:
        lines.append({"level": "info", "code": "a10_paused", "text": t("parte.a10_paused", remaining=paused.get("remaining"), needed=paused.get("needed"))})
    head_level = "bad" if any(line["level"] == "bad" for line in lines) else ("warn" if any(line["level"] == "warn" for line in lines) else "ok")
    headline = t("parte.headline", red=red, stuck=stuck, new=new, cands=cands)
    if head_level == "ok":
        headline += " " + t("parte.all_ok")
    return [{"level": head_level, "text": headline, "head": True}] + lines


def compute_snapshot(inp):
    """Builds the whole picture from plain inputs (no network): used by the server and by the tests."""
    now, cfg = inp["now"], inp["cfg"]
    repos, eco = inp["repos"], inp["eco"]
    info, alerts, perms = inp["repo_info"], inp["alerts"], inp["perms"]
    runs_by_repo = {r: inp["runs"].get(r, []) for r in repos}
    branches = {r: i.get("branch") for r, i in info.items()}
    data = inp.get("data") or {}
    rate = data.get("rate")
    stuck = [{"repo": r["repo"], "name": r["name"], "seconds": r["seconds"], "url": r["url"], "status": r["status"]} for r in data.get("active", []) if r.get("stuck")]
    issues = [{"repo": i["repo"], "number": i["number"], "title": i["title"][:120], "url": i["url"], "labels": i["labels"], "created": i.get("created")} for i in data.get("issues", [])]
    ttl = float(cfg.get("a2_resolve_ttl_seconds") or 0)
    resolved = inp.get("a2_resolved") or {}
    extra = a2_resolved_runs(resolved, branches, now.timestamp(), ttl)
    red = red_workflows({r: runs + extra.get(r, []) for r, runs in runs_by_repo.items()}, branches)
    caps = inp.get("sample_caps") or cfg   # the run-list sizes of the monitor (runs_per_repo, cold_runs_per_repo); a test may pass them in cfg
    totals = alert_totals(alerts, info)
    per_repo = {r: [t["codeql"] or 0, t["dependabot"] or 0, t["secret"] or 0] for r, t in totals.items()}
    new = new_alerts_since(inp["history"], inp["today"], per_repo)
    rows = []
    for repo, t in sorted(totals.items()):
        if any(t[k] for k in ("codeql", "dependabot", "secret")):
            rows.append({"repo": repo, **t})
    sev_high = lambda sev: sev.get("critical", 0) + sev.get("high", 0)  # noqa: E731
    codeql_list = []
    for repo, a in alerts.items():
        for item in a.get("codeql") or []:
            codeql_list.append({"repo": repo, **item})
    order = {"critical": 0, "high": 1, "error": 2, "medium": 3, "warning": 4, "low": 5}
    codeql_list.sort(key=lambda x: (order.get((x.get("severity") or "").lower(), 9), x["repo"]))
    unavailable = [r for r, a in alerts.items() if a.get("codeql") is None]
    prs_all = [classify_pr(repo, pr, now) for repo, i in info.items() for pr in i.get("prs", [])]
    dep_prs = sorted((p for p in prs_all if p["dependabot"]), key=lambda p: -(p["age_days"] or 0))
    releases = {r: i.get("release") for r, i in info.items() if i.get("release")}
    ages = {}
    for repo, rel in releases.items():
        published = parse_time(rel.get("publishedAt"))
        ages[repo] = (now - published).total_seconds() / 86400 if published else None
    candidates = release_candidates_rule({r: n for r, n in inp["unreleased"].items() if r in info}, ages, cfg["candidate_days"], cfg["candidate_min_entries"], cfg["skip_candidate_prefixes"])
    live_targets = {n: t for n, t in (inp.get("targets") or {}).items() if t.get("repo", n) in info}
    green = green_without_release(live_targets, runs_by_repo, releases, branches)
    states = signstate.target_states(live_targets, runs_by_repo, releases, eco, inp.get("local"), now, branches,
                                     require_verified=bool(cfg.get("require_verified_signature", True)))
    by_key = {(x["repo"], x["workflow"]): x for x in states}
    # local records of the batches/signing lower the alert without waiting for GitHub: published -> gone; signed with the release key -> only the publication is missing
    green = [g for g in green if not (by_key.get((g["repo"], g["workflow"])) or {}).get("published")]
    signed_wait = []
    for g in green:
        st = by_key.get((g["repo"], g["workflow"])) or {}
        g.update({"state": st.get("state", "built_on_gha"), "last_build_at": st.get("last_build_at"), "signature_kind": st.get("signature_kind", "none"),
                  "signature_verified": st.get("signature_verified", "unknown"), "last_signed_at": st.get("last_signed_at"), "run_id": st.get("run_id")})
        if st.get("state") == "signed_local" and st.get("signature_kind") == "release" and st.get("trusted"):
            signed_wait.append(g)
    unsigned = [g for g in green if g not in signed_wait]
    queue = signstate.sign_queue(states, inp.get("finalize_fn"))
    reduced = bool(inp.get("reduced"))
    if reduced:   # no local workspace: there are no local signing records, so nothing can be said about what is waiting to be signed
        queue, unsigned, signed_wait = [], [], []
    hyg_rows, pending = [], 0
    for repo in sorted(info):
        p = perms.get(repo)
        if not p:
            pending += 1
        probs = hygiene_problems(info[repo], p, cfg["required_files"])
        hyg_rows.append({"repo": repo, "problems": [{"code": c, "text": t} for c, t in probs], "checked": bool(p)})
    mins = minutes(runs_by_repo, now)
    errors = [{"section": k, "message": v["message"], "at": v["at"]} for k, v in sorted(inp["errors"].items())]
    sev_total = {"critical": 0, "high": 0}
    for t in totals.values():
        for k in sev_total:
            sev_total[k] += t["sev"].get(k, 0)
    a2_details, a2_repos = a2_resolution(a2_missing(runs_by_repo, caps, inp.get("scans")), resolved, now.timestamp(), ttl, inp.get("a2_pending_reason") or "pending")
    s = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "enabled": True, "loading": inp.get("loading", ""),
        "cache_age_seconds": inp.get("cache_age"), "reduced": reduced, "language": i18n.language(), "repos": len(repos), "ecosystems": {r: eco.get(r, "other") for r in repos},
        "rate": rate, "min_rate": cfg["min_rate_remaining"], "errors": errors, "ai": inp.get("ai"),
        "a1": {"stuck": stuck, "issues": issues, "stuck_minutes": data.get("stuck_minutes")},
        "a2": {"red": red, "workflows_checked": sum(1 for r in repos for _ in {workflow_key(x) for x in runs_by_repo.get(r, [])}),
               "unchecked": a2_unchecked(runs_by_repo), "full_sample": a2_full_sample(runs_by_repo, caps),
               "inconclusive": a2_repos, "inconclusive_workflows": a2_labels(a2_details), "inconclusive_details": a2_details},
        "a3": {"rows": rows, "codeql_total": sum(t["codeql"] or 0 for t in totals.values()), "dependabot_total": sum(t["dependabot"] or 0 for t in totals.values()),
               "dependency_alerts_off": sorted(r for r, i in info.items() if i.get("vuln_enabled") is False),
               "secret_total": sum(t["secret"] or 0 for t in totals.values()), "secret_repos": [r for r, t in sorted(totals.items()) if t["secret"]],
               "high_repos": [r for r, t in sorted(totals.items()) if sev_high(t["sev"])], "severity": sev_total,
               "new": new or {}, "new_total": (sum(new.values()) if new is not None else None), "has_reference": new is not None,
               "codeql": codeql_list[:200], "unavailable": len(unavailable), "alerts_checked": sum(1 for a in alerts.values() if a.get("at")),
               "trend": {k: trend(inp["history"], k) for k in ("codeql", "dependabot", "secret", "prs", "red", "candidates")}},
        "a4": {"dependabot": dep_prs, "other": sum(1 for p in prs_all if not p["dependabot"]), "stale_days": cfg["stale_pr_days"]},
        "tool_version": TOOL_VERSION,
        "a5": {"candidates": candidates, "green_unreleased": green, "pending_sign": [{**g, "pending_sign_hours": g["hours"]} for g in pending_sign(unsigned, now, cfg["pending_sign_hours"])],
               "pending_sign_hours": cfg["pending_sign_hours"], "states": states, "sign_queue": queue, "signed_unpublished": signed_wait,
               "versions": sorted(({"repo": r, "tag": rel.get("tagName"), "published": rel.get("publishedAt")} for r, rel in releases.items()), key=lambda x: x["repo"]),
               "days": cfg["candidate_days"]},
        "a6": {"rows": hyg_rows, "pending": pending},
        "a7": {"rows": sorted(({"repo": r, **v} for r, v in mins.items()), key=lambda x: -x["min24"]), "total24": sum(v["min24"] for v in mins.values()),
               "total7d": sum(v["min7d"] for v in mins.values()), "api": inp.get("api"), "budget": minutes_budget(mins, eco, cfg)},
        "a8": inp.get("audits") or {"audits": {}, "rounds": {}, "files": []},
        "a9": inp.get("roadmaps") or {"boards": [], "level": "unknown"},
    }
    s["a7"]["by_ecosystem"] = minutes_by_ecosystem(mins, eco, cfg)
    s["a10"] = surface.build({"now": now, "cfg": cfg["surface"], "repos": repos, "eco": eco, "repo_info": info, "alerts": alerts, "perms": perms, "runs": runs_by_repo,
                              "branches": branches, "scans": inp.get("scans"), "raw": inp.get("surface_raw"), "globals": inp.get("surface_glob"), "red": red,
                              "issues": issues, "prs": prs_all, "states": states, "queue": queue, "loading": inp.get("loading")})
    att = (inp.get("surface_glob") or {}).get("attestation") or {}
    for q in queue:   # existence of the build attestation (no signature check): True | False | "unknown" | None = not looked up
        q["attestation"] = att.get(f"{q['repo']}|{q.get('run_id')}")
    s["a1"]["level"] = "bad" if (stuck or issues) else "ok"
    # unknown is not green: a repository with no run data at all could not be checked
    s["a2"]["level"] = "bad" if red else ("unknown" if (s["a2"]["unchecked"] or (cfg.get("a2_full_sample_unknown", True) and s["a2"]["inconclusive"])) else "ok")
    s["a3"]["level"] = "bad" if (s["a3"]["secret_total"] or s["a3"]["high_repos"]) else ("warn" if (s["a3"]["codeql_total"] or s["a3"]["dependabot_total"]) else "ok")
    s["a4"]["level"] = "warn" if any(p["major"] or p["conflict"] for p in dep_prs) else ("info" if dep_prs else "ok")
    s["a5"]["level"] = "warn" if (candidates or s["a5"]["pending_sign"]) else ("info" if green else "ok")
    s["a6"]["level"] = "warn" if any(r["problems"] for r in hyg_rows) else ("info" if pending else "ok")
    s["a7"]["level"] = "warn" if ((rate and rate["remaining"] < cfg["min_rate_remaining"]) or any(b["level"] != "ok" for b in s["a7"]["budget"])) else "ok"
    s["a8"]["level"] = "info"
    s["a9"]["level"] = s["a9"].get("level", "unknown")
    s["a10"]["level"] = s["a10"].get("level", "unknown")
    s["a10"]["paused"] = inp.get("surface_paused")
    s["a11"] = readiness.build(inp, s, cfg.get("readiness") or readiness.DEFAULTS)
    s["a11"]["level"] = s["a11"].get("level", "unknown")
    lint = inp.get("lint")
    s["lint"] = {"enabled": False} if not lint else {"enabled": True, "summary": lint["summary"], "in_report": lint.get("in_report", True),
                                                    "rows": [dict(f, repo=r) for r, items in sorted(lint["by_repo"].items()) for f in items][:200]}
    for key in ("a3", "a4", "a5", "a6"):  # an "ok" with the data still loading would be a false green
        if s[key]["level"] == "ok" and (inp.get("loading") or not info or (key == "a3" and s["a3"]["alerts_checked"] < len(info))):
            s[key]["level"] = "unknown"
    s["totals"] = {"red": len(red), "stuck": len(stuck), "new_alerts": s["a3"]["new_total"] or 0, "candidates": len(candidates), "prs": len(dep_prs),
                   "codeql": s["a3"]["codeql_total"], "dependabot": s["a3"]["dependabot_total"], "secret": s["a3"]["secret_total"]}
    s["by_ecosystem"] = ecosystem_summary(s, eco)
    s["parte"] = build_parte(s)
    s["level"] = s["parte"][0]["level"]
    return s


# ---------- collector ----------

def repo_query(file_names):
    aliases = " ".join(f'f{i}:object(expression:"HEAD:{name}"){{id}}' for i, name in enumerate(file_names))
    return ("query($after:String){rateLimit{remaining cost} repositoryOwner(login:\"%s\"){repositories(first:15,after:$after,ownerAffiliations:OWNER,isArchived:false)"
            "{totalCount pageInfo{hasNextPage endCursor} nodes{name pushedAt hasVulnerabilityAlertsEnabled defaultBranchRef{name} latestRelease{tagName publishedAt isDraft releaseAssets(first:100){nodes{name}}}"
            " vulnerabilityAlerts(states:OPEN,first:50){totalCount nodes{createdAt securityVulnerability{severity}}}"
            " pullRequests(states:OPEN,first:10){nodes{number title url author{login} createdAt isDraft mergeable reviewDecision commits(last:1){nodes{commit{statusCheckRollup{state}}}} files(first:20){nodes{path}}}}"
            " rulesets(first:5){nodes{name enforcement}} labels(first:20,query:\"dependencies\"){nodes{name}} %s}}}}") % (toolconfig.github_owner(), aliases)


def parse_repo_node(node, file_names):
    rel = node.get("latestRelease")
    sev, hi = {}, []
    for v in (node.get("vulnerabilityAlerts") or {}).get("nodes") or []:
        key = ((v.get("securityVulnerability") or {}).get("severity") or "?").lower()
        sev[key] = sev.get(key, 0) + 1
        if key in ("critical", "high") and len(hi) < 20:
            hi.append({"sev": key, "created": v.get("createdAt")})
    return {
        "name": node["name"], "pushed": node.get("pushedAt"), "branch": (node.get("defaultBranchRef") or {}).get("name") or "main",
        "release": {"tagName": rel["tagName"], "publishedAt": rel["publishedAt"],
                    "asset_flags": signstate.asset_flags([n.get("name", "") for n in (rel.get("releaseAssets") or {}).get("nodes") or []])} if rel and not rel.get("isDraft") else None,
        "vuln_total": (node.get("vulnerabilityAlerts") or {}).get("totalCount", 0), "vuln_sev": sev,
        "vuln_enabled": node.get("hasVulnerabilityAlertsEnabled"), "vuln_hi": hi,
        "prs": (node.get("pullRequests") or {}).get("nodes") or [],
        "rulesets": (node.get("rulesets") or {}).get("nodes") or [],
        "label_dependencies": any((l.get("name") or "").lower() == "dependencies" for l in (node.get("labels") or {}).get("nodes") or []),
        "files": {name: bool(node.get(f"f{i}")) for i, name in enumerate(file_names)},
    }


def slim_alert(a):
    rule = a.get("rule") or {}
    inst = a.get("most_recent_instance") or {}
    loc = inst.get("location") or {}
    return {"number": a.get("number"), "rule": rule.get("id"), "description": (rule.get("description") or "")[:160],
            "severity": rule.get("security_severity_level") or rule.get("severity") or "?", "path": loc.get("path"), "line": loc.get("start_line"),
            "url": a.get("html_url"), "created": a.get("created_at"), "message": ((inst.get("message") or {}).get("text") or "")[:300]}


class Sentinel:
    def __init__(self, ctx, config):
        self.ctx = ctx
        self.config = config
        self.cfg = sentinel_config(config)
        self.ai_cfg = sentinel_ai.ai_config(config)
        self.ai_store = sentinel_ai.Store()
        self.lock = threading.RLock()
        self.repo_info, self.alerts, self.perms, self.unreleased = {}, {}, {}, {}
        self.local_versions = {}
        self.pins_cache = {"at": 0.0, "value": None}
        self.lint_cache = {"at": 0.0, "value": None}
        self.errors = {}
        self.calls = []
        self.gql_at = 0.0
        self.gql_cursor = None
        self.loading = "starting"
        self.saved_at = None
        self.history = self._load(HISTORY_FILE, {"days": {}})
        if not isinstance(self.history.get("days"), dict):
            self.history = {"days": {}}
        dispatch = self._load_dispatch()
        self.targets = dict(dispatch.TARGETS) if dispatch else {}
        self.finalize_fn = (lambda name, run_id, _m=dispatch: _m.finalize_command(name, run_id)) if dispatch else None   # the command `gha_dispatch_all.py finalize` prints
        self.local_cache = {"at": 0.0, "value": {"signed": {}, "batches": {}}}
        self.surface = surface.Collector(lambda *a, **k: self._gh(*a, **k), GITHUB_DIR, self.cfg["surface"])   # A10: cold calls and local scans, see surface.py
        self.last_snap = None
        self.surface_paused = None   # {"remaining", "needed"} while A10 waits for the allowance, else None
        self.a2_resolved = {}        # "repo|workflow file" -> last run on the default branch (or none), see _a2_resolve_tick
        self.a2_reason = "pending"   # why an unresolved workflow is still unresolved: "pending" (waiting its turn) or "quota"
        self.dirty = False
        self.audit_cache = {"at": 0.0, "value": None}
        self.feed = events.Feed(notify_command=self.cfg.get("notify_command"))   # one JSON line per change, for whoever follows events_monitor.jsonl
        self.roadmaps = roadmap_a9.Watcher(ctx["gh"], GITHUB_DIR / toolconfig.github_owner())   # A9: refreshed in its own thread, nothing is written
        cached = self._load(CACHE_FILE, {})
        if cached:
            def mapping(key):      # a cache written by hand or cut in half must not take the sentinel down: only dictionaries are taken
                return cached.get(key) if isinstance(cached.get(key), dict) else {}
            self.repo_info, self.alerts, self.perms = mapping("repo_info"), mapping("alerts"), mapping("perms")
            self.unreleased, self.saved_at = mapping("unreleased"), cached.get("saved")
            self.local_versions = mapping("local_versions")
            self.surface.load(cached.get("surface"))
            if isinstance(cached.get("a2_resolved"), dict):
                self.a2_resolved = cached["a2_resolved"]

    # -- helpers
    @staticmethod
    def _load(path, default):
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default
        return value if isinstance(value, type(default)) else default      # a file of the wrong shape (a list, a number) is as good as no file

    @staticmethod
    def _save(path, value):
        try:
            tmp = Path(str(path) + ".tmp")
            private_io.write_tmp(tmp, json.dumps(value, ensure_ascii=False))
            tmp.replace(path)
        except OSError:
            pass

    @staticmethod
    def _load_dispatch():
        """The batch module (targets come from targets.json, validated there); None when it cannot be loaded."""
        try:
            spec = importlib.util.spec_from_file_location("gha_dispatch_all", HERE / "gha_dispatch_all.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except (Exception, SystemExit):   # a broken targets.json must not stop the sentinel
            return None

    @classmethod
    def _load_targets(cls):
        mod = cls._load_dispatch()
        return dict(mod.TARGETS) if mod else {}

    def _local(self):
        """Local signing records (batches + signed folders), cached 60 s: plain file reads, no network."""
        if time.time() - self.local_cache["at"] > 60:
            try:
                self.local_cache = {"at": time.time(), "value": signstate.local_records(SIGNED_DIR, sigverify.pinned_keys(GITHUB_DIR, (self.cfg.get("signature_pubkeys") if isinstance(self.cfg.get("signature_pubkeys"), dict) else {})))}
            except Exception as error:   # never stop the picture for a local file
                degraded.note("sentinel.local", error)
                self.local_cache = {"at": time.time(), "value": {"signed": {}, "batches": {}}}
        return self.local_cache["value"]

    def _pins(self, repos, eco):
        """A11 dependency pins: plain file reads of the local clones, cached `pins.refresh_seconds` (600 by default); nothing without a workspace."""
        cfg = self.cfg["readiness"]["pins"]
        if not workspace.has_workspace() or not cfg.get("sources"):
            return read_none(cfg)
        if self.pins_cache["value"] is None or time.time() - self.pins_cache["at"] > cfg["refresh_seconds"]:
            try:
                value = readiness.read_pins(GITHUB_DIR, repos, lambda r: eco.get(r) or toolconfig.ecosystem_of(r), cfg)
            except Exception as error:   # a pin file must never stop the picture
                degraded.note("sentinel.pins", error)
                value = read_none(cfg)
            self.pins_cache = {"at": time.time(), "value": value}
        return self.pins_cache["value"]

    def _lint(self, repos):
        """The workflow linter over the local clones (plain file reads, cached `lint.refresh_seconds`); None when it is off or there is no workspace."""
        cfg = lint_workflows.settings(self.config)
        if not cfg["enabled"] or not workspace.has_workspace():
            return None
        if self.lint_cache["value"] is None or time.time() - self.lint_cache["at"] > cfg["refresh_seconds"]:
            try:
                by_repo = lint_workflows.scan_clones(GITHUB_DIR, repos, cfg["rules"], cfg.get("ignore"))
                value = {"by_repo": by_repo, "summary": lint_workflows.summarize(by_repo), "in_report": cfg["in_report"]}
            except Exception as error:   # a workflow file must never stop the picture
                degraded.note("sentinel.lint", error)
                value = None
            self.lint_cache = {"at": time.time(), "value": value}
        return self.lint_cache["value"]

    def _export_ci_red(self, snap):
        try:
            ci_red.export(snap, self.cfg, AUDIT_DIR)
        except Exception as error:   # an export problem never stops the sentinel
            degraded.note("sentinel.export", error)
            pass

    def error(self, section, message):
        with self.lock:
            self.errors[section] = {"message": str(message)[:200], "at": datetime.now(timezone.utc).strftime("%H:%M:%S")}

    def ok(self, section):
        with self.lock:
            self.errors.pop(section, None)

    def _gh(self, *args, **kw):
        with self.lock:
            self.calls.append(time.time())
            self.calls = [t for t in self.calls if t > time.time() - 3600]
        return self.ctx["gh"](*args, **kw)

    def calls_last_hour(self):
        with self.lock:
            return len([t for t in self.calls if t > time.time() - 3600])

    # -- collection
    def refresh_graphql(self):
        files = sorted({name for group in self.cfg["required_files"] for name in group})
        query = repo_query(files)
        watched = set(self.ctx["repos_fn"]())
        seen, after = {}, self.gql_cursor  # a failed pass resumes where it stopped
        while True:
            args = ["api", "graphql", "-f", "query=" + query] + (["-f", "after=" + after] if after else [])
            self.gql_cursor = after
            data = self._gh(*args, retries=3)["data"]
            page = data["repositoryOwner"]["repositories"]
            with self.lock:
                for node in page["nodes"]:
                    if node["name"] in watched:
                        seen[node["name"]] = parse_repo_node(node, files)
                        self.repo_info[node["name"]] = seen[node["name"]]
                self.loading = f"{len(seen)}/{len(watched)}"
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
        self.gql_cursor = None
        with self.lock:
            for gone in [r for r in self.repo_info if r not in watched]:
                self.repo_info.pop(gone, None)
            self.loading = ""
        self._scan_changelogs()
        self.gql_at = time.time()
        self.ok("graphql")

    def _scan_changelogs(self):
        try:
            spec = importlib.util.spec_from_file_location("release_candidates", HERE / "release_candidates.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            counts, versions = {}, {}
            for repo in self.repo_info:
                path = GITHUB_DIR / repo / "CHANGELOG.md"
                if toolconfig.is_ours(repo) and path.is_file() and (GITHUB_DIR / repo / ".git").exists():
                    counts[repo] = mod.unreleased_count(path.read_text(encoding="utf-8", errors="replace"))
                    if counts[repo]:
                        versions[repo] = readiness.local_version(GITHUB_DIR / repo)   # A11: is the version already above the last release?
            with self.lock:
                self.unreleased = counts
                self.local_versions = versions
            self.ok("changelogs")
        except Exception as error:
            self.error("changelogs", error)

    def _hot(self, repo):
        info, a = self.repo_info.get(repo) or {}, self.alerts.get(repo) or {}
        if a.get("codeql") or a.get("secret") or info.get("vuln_total"):
            return True
        pushed = parse_time(info.get("pushed"))
        return bool(pushed and (datetime.now(timezone.utc) - pushed).total_seconds() < self.cfg["hot_hours"] * 3600)

    def _alerts_due(self):
        now, due = time.time(), []
        for repo in self.repo_info:
            at = (self.alerts.get(repo) or {}).get("at")
            if at is None:
                due.append((0, repo))
            elif now - at > (self.cfg["alerts_hot_seconds"] if self._hot(repo) else self.cfg["alerts_cold_seconds"]):
                due.append((at, repo))
        return [r for _, r in sorted(due)]

    def _fetch_alerts(self, repo):
        res = {"at": time.time(), "codeql": [], "secret": 0, "note": ""}
        try:
            res["codeql"] = [slim_alert(a) for a in (self._gh("api", f"repos/{toolconfig.github_owner()}/{repo}/code-scanning/alerts?state=open&per_page=100", retries=1) or [])]
        except Exception as error:
            text = str(error).lower()
            if "no analysis found" in text:
                res["codeql"] = []
            elif any(k in text for k in ("not enabled", "advanced security", "404", "403")):
                res["codeql"], res["note"] = None, "codeql_off"
            else:
                res["codeql"], res["note"] = (self.alerts.get(repo) or {}).get("codeql"), "error: " + str(error)[:80]
        try:
            res["secret"] = len(self._gh("api", f"repos/{toolconfig.github_owner()}/{repo}/secret-scanning/alerts?state=open&per_page=100", retries=1) or [])
        except Exception:
            res["secret"] = (self.alerts.get(repo) or {}).get("secret")
        return repo, res

    def _perms_due(self):
        now = time.time()
        return [r for r in self.repo_info if now - (self.perms.get(r) or {}).get("at", 0) > self.cfg["hygiene_seconds"]]

    def _fetch_perms(self, repo):
        res = {"at": time.time()}
        try:
            p = self._gh("api", f"repos/{toolconfig.github_owner()}/{repo}/actions/permissions", retries=1) or {}
            res.update({"allowed_actions": p.get("allowed_actions"), "sha_pinning_required": p.get("sha_pinning_required")})
            wfs = (self._gh("api", f"repos/{toolconfig.github_owner()}/{repo}/actions/workflows?per_page=100", retries=1) or {}).get("workflows", [])
            res["wf_disabled"] = [w.get("name") for w in wfs if w.get("state") == "disabled_inactivity"]
            res["wf_manual"] = [w.get("name") for w in wfs if w.get("state") == "disabled_manually"]   # same call: no extra request
        except Exception as error:
            res = {**(self.perms.get(repo) or {}), "at": time.time() - self.cfg["hygiene_seconds"] + 600, "error": str(error)[:80]}
            if "allowed_actions" not in res:
                return repo, None
        return repo, res

    def _budget(self):
        left = self.cfg["budget_per_hour"] - self.calls_last_hour()
        rate = (self.ctx["data_fn"]() or {}).get("rate")
        if rate and rate["remaining"] < self.cfg["min_rate_remaining"]:
            return 0
        return max(0, min(self.cfg["max_calls_per_tick"], left))

    def tick(self):
        did = False
        if time.time() - self.gql_at > self.cfg["refresh_seconds"]:
            try:
                self.refresh_graphql()
                did = True
            except Exception as error:
                self.error("graphql", error)
                self.gql_at = time.time() - self.cfg["refresh_seconds"] + 30
        budget = self._budget()
        todo = self._alerts_due()
        batch = todo[: max(0, budget // 2)]
        if batch:
            with ThreadPoolExecutor(max_workers=self.cfg["workers"]) as pool:
                for repo, res in pool.map(self._fetch_alerts, batch):
                    with self.lock:
                        self.alerts[repo] = res
            self.ok("alerts")
            did = True
        budget = self._budget()
        todo = self._perms_due()
        batch = todo[: max(0, min(budget // 2, 20))]
        if batch:
            with ThreadPoolExecutor(max_workers=self.cfg["workers"]) as pool:
                for repo, res in pool.map(self._fetch_perms, batch):
                    if res:
                        with self.lock:
                            self.perms[repo] = res
            self.ok("hygiene")
            did = True
        did = self._surface_tick() or did
        did = self._a2_resolve_tick() or did
        if did or self.dirty:
            self.dirty = False
            self._persist()
        return bool(self._alerts_due() or self._perms_due()) and self._budget() > 0

    def _surface_tick(self):
        """A10 cold work: the local scan (free) and a few extra calls, only while the allowance is healthy and inside the hourly budget."""
        if not self.cfg["surface"]["enabled"] or not self.repo_info:
            return False
        snap = self.last_snap or {}
        rate = (self.ctx["data_fn"]() or {}).get("rate")
        needed = self.cfg["min_rate_remaining"] * self.cfg["surface"]["min_rate_factor"]
        healthy = not rate or rate["remaining"] >= needed
        self.surface_paused = None if healthy else {"remaining": rate["remaining"], "needed": int(needed)}
        branches = {r: i.get("branch") for r, i in self.repo_info.items()}
        try:
            used = self.surface.tick(sorted(self.repo_info), branches, int(self._budget() * min(1.0, max(0.0, self.cfg["surface"]["budget_share"]))), (snap.get("a2") or {}).get("red") or [], (snap.get("a5") or {}).get("sign_queue") or [],
                                     lambda repo: surface.signed_files_of(SIGNED_DIR, repo), rate_ok=healthy)
            self.ok("surface")
        except Exception as error:
            self.error("surface", error)
            return False
        return bool(used)

    def _a2_resolve_tick(self):
        """A2: for a repository with a full run sample that hides a workflow of its clone, asks GitHub for the last run of THAT workflow on the default branch
        (one call each, `gh run list -w <file> --branch <default> -L 1`). Same quota gate as A10, at most `a2_resolve_max_calls_per_tick` calls a tick; the answers are
        kept `a2_resolve_ttl_seconds`. Nothing is written to GitHub."""
        limit = int(self.cfg.get("a2_resolve_max_calls_per_tick") or 0)
        if limit <= 0 or not self.repo_info:
            return False
        repos = self.ctx["repos_fn"]()
        runs = {r: list((self.ctx["runs_fn"]().get(r) or {}).get("runs", [])) for r in repos}
        caps = {"runs_per_repo": self.config.get("runs_per_repo"), "cold_runs_per_repo": self.config.get("cold_runs_per_repo")}
        missing = a2_missing(runs, caps, dict(self.surface.scans))
        now_ts, ttl = time.time(), float(self.cfg.get("a2_resolve_ttl_seconds") or 0)
        todo = [(repo, name) for repo, files in sorted(missing.items()) for name in files or [] if not a2_fresh(self.a2_resolved.get(f"{repo}|{name}"), now_ts, ttl)]
        if not todo:
            self.a2_reason = "pending"
            return False
        rate = (self.ctx["data_fn"]() or {}).get("rate")
        needed = self.cfg["min_rate_remaining"] * self.cfg["surface"]["min_rate_factor"]
        budget = self._budget()
        if budget <= 0 or (rate and rate["remaining"] < needed):
            self.a2_reason = "quota"
            return False
        self.a2_reason = "pending"
        todo.sort(key=lambda x: float((self.a2_resolved.get(f"{x[0]}|{x[1]}") or {}).get("at") or 0))   # never asked first, then the oldest answer
        branches = {r: i.get("branch") for r, i in self.repo_info.items()}
        did = False
        for repo, name in todo[: min(limit, budget)]:
            branch = branches.get(repo) or "main"
            try:
                answer = self._gh("run", "list", "-R", f"{toolconfig.github_owner()}/{repo}", "-w", name, "--branch", branch, "--status", "completed", "-L", str(A2_RESOLVE_DEPTH),
                                  "--json", "databaseId,name,conclusion,status,createdAt,startedAt,url,headSha")
            except Exception as error:   # a failed question stays unresolved; the others go on
                self.error("a2_resolve", error)
                continue
            first = a2_pick_concluded(answer)
            if first:
                entry = {"at": now_ts, "state": "run", "id": first.get("databaseId"), "name": first.get("name") or "", "conclusion": first.get("conclusion") or None,
                         "status": first.get("status") or "completed", "started": first.get("startedAt") or first.get("createdAt"), "url": first.get("url"),
                         "sha": (first.get("headSha") or "")[:7], "branch": branch}
            else:
                entry = {"at": now_ts, "state": "none", "branch": branch}
            with self.lock:
                self.a2_resolved[f"{repo}|{name}"] = entry
            did = True
        if did:
            self.ok("a2_resolve")
        return did

    def refresh_repos(self, repos):
        """Called by the local endpoint after `finalize`: forget what we know about THESE repositories only and rewrite ci_red.json at once."""
        names = [r for r in repos if r in self.repo_info]
        with self.lock:
            self.local_cache["at"] = 0.0   # the signed folders / batch records are read again
            for repo in names:
                self.alerts.pop(repo, None)
                self.perms.pop(repo, None)
        self.surface.forget(names)
        self.dirty = True
        try:
            self._export_ci_red(self.snapshot())
        except Exception as error:
            self.error("refresh", error)
        return names

    def _persist(self):
        with self.lock:
            self._save(CACHE_FILE, {"saved": time.time(), "repo_info": self.repo_info, "alerts": self.alerts, "perms": self.perms, "unreleased": self.unreleased, "local_versions": self.local_versions, "surface": self.surface.dump(), "a2_resolved": self.a2_resolved})
        snap = self.snapshot()
        self.last_snap = snap
        self._export_ci_red(snap)
        t = snap["totals"]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        per_repo = {r["repo"]: [r["codeql"] or 0, r["dependabot"] or 0, r["secret"] or 0] for r in snap["a3"]["rows"]}
        if snap["a3"]["alerts_checked"] >= len(self.repo_info) > 0:  # only a complete picture goes into the daily history
            with self.lock:
                update_history(self.history, today, {"codeql": t["codeql"], "dependabot": t["dependabot"], "secret": t["secret"], "prs": t["prs"],
                                                      "red": t["red"], "candidates": t["candidates"]}, per_repo)
                self._save(HISTORY_FILE, self.history)

    def loop(self):
        while True:
            pending = False
            try:
                pending = self.tick()
                self.ok("module")
            except Exception as error:
                self.error("module", error)
            try:
                self.feed.feed(self.snapshot())
            except Exception as error:   # the feed must never stop the sentinel
                self.error("events", error)
            time.sleep(5 if pending else 30)

    def start(self):
        if self.cfg["enabled"]:
            threading.Thread(target=self.loop, daemon=True, name="sentinel").start()

    # -- views
    def _audits(self):
        if time.time() - self.audit_cache["at"] > 300:
            self.audit_cache = {"at": time.time(), "value": parse_audit_files(AUDIT_DIR, self.cfg.get("audit_files"))}
        return self.audit_cache["value"]

    def snapshot(self):
        if not self.cfg["enabled"]:
            return {"enabled": False, "errors": [], "parte": [{"level": "info", "text": i18n.t("parte.disabled"), "head": True}]}
        now = datetime.now(timezone.utc)
        repos = self.ctx["repos_fn"]()
        runs = {r: list((self.ctx["runs_fn"]().get(r) or {}).get("runs", [])) for r in repos}
        pins = self._pins(repos, {r: self.ctx["eco_fn"](r) for r in repos})
        with self.lock:
            inp = {
                "now": now, "today": now.strftime("%Y-%m-%d"), "cfg": self.cfg, "repos": repos, "eco": {r: self.ctx["eco_fn"](r) for r in repos},
                "repo_info": dict(self.repo_info), "alerts": dict(self.alerts), "perms": dict(self.perms), "runs": runs, "data": self.ctx["data_fn"](),
                "history": self.history, "unreleased": dict(self.unreleased), "targets": self.targets,
                "scans": dict(self.surface.scans), "surface_raw": dict(self.surface.raw), "surface_glob": dict(self.surface.glob), "audits": self._audits(), "roadmaps": self.roadmaps.get(),
                "local": self._local(), "finalize_fn": self.finalize_fn, "reduced": not workspace.has_workspace(),
                "errors": dict(self.errors), "loading": self.loading, "ai": sentinel_ai.status(self.ai_cfg, self.ai_store) if self.ai_cfg["provider"] != "none" else
                {"provider": "none", "enabled": False, "message": i18n.t("ai.off"), "label": i18n.t("ai.label")},
                "cache_age": round(time.time() - self.saved_at) if (self.saved_at and not self.gql_at) else None,
                "api": {"calls_last_hour": len([t for t in self.calls if t > time.time() - 3600]), "budget_per_hour": self.cfg["budget_per_hour"]},
                "sample_caps": {"runs_per_repo": self.config.get("runs_per_repo"), "cold_runs_per_repo": self.config.get("cold_runs_per_repo")},
                "surface_paused": self.surface_paused, "a2_resolved": dict(self.a2_resolved), "a2_pending_reason": self.a2_reason, "local_versions": dict(self.local_versions), "pins": pins,
                "lint": self._lint(repos),
            }
        return compute_snapshot(inp)

    # -- layer B (only on request of the page, only our repositories and actors)
    def gh_text(self, *args, limit=300000):
        import subprocess
        with self.lock:
            self.calls.append(time.time())
        import secretstore
        result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, **secretstore.gh_kwargs())
        if result.returncode != 0:
            raise RuntimeError((result.stderr or "gh failed").strip()[:200])
        return result.stdout[-limit:]

    def ai_explain(self, request):
        """The answer of the model for one request, with the proposals of actions (level 3) found in its text; nothing is run here."""
        result = self._ai_explain(request)
        try:
            import ai_actions
            repo = str(request.get("repo", ""))
            if result.get("ok") and repo:
                runs = lambda r: (self.ctx["runs_fn"]().get(r) or {}).get("runs", [])   # noqa: E731
                issues = (self.ctx["data_fn"]() or {}).get("issues", [])
                result["proposals"] = ai_actions.ACTIONS.propose(
                    result.get("text", ""), repo, self.config, self.ctx["repos_fn"](), lambda r, n: any(x.get("id") == n for x in runs(r)),
                    lambda r, n: any(i.get("repo") == r and i.get("number") == n for i in issues), toolconfig.github_owner())
        except Exception:   # a proposal problem never hides the answer
            result.setdefault("proposals", [])
        return result

    def _ai_explain(self, request):
        kind, repo = str(request.get("kind", "")), str(request.get("repo", ""))
        if kind == "report":   # the daily report of the sentinel itself: nothing of any repository's files, only the lines the page already shows
            if self.ai_cfg["provider"] == "none":
                return sentinel_ai.explain(kind, "", self.ai_cfg, self.ai_store)
            return sentinel_ai.explain("report", "\n".join(f"[{l.get('level')}] {l.get('text')}" for l in (self.snapshot().get("parte") or [])), self.ai_cfg, self.ai_store)
        if repo not in self.ctx["repos_fn"]():
            return {"ok": False, "error": i18n.t("err.unknown_repo")}
        if self.ai_cfg.get("allowed_repos") and repo not in self.ai_cfg["allowed_repos"]:
            return {"ok": False, "error": i18n.t("ai.repo_not_allowed", repo=repo)}
        if kind == "ask":   # "ask the AI" about one repository: the question (short, sanitised) and the summary of its latest runs
            question = sentinel_ai.sanitize_text(str(request.get("question", "")), 400, keep="head")
            if not question or self.ai_cfg["provider"] == "none":
                return sentinel_ai.explain("ask", "", self.ai_cfg, self.ai_store) if self.ai_cfg["provider"] == "none" else {"ok": False, "error": i18n.t("err.bad_kind")}
            recent = [f"{r.get('name')}: {r.get('conclusion') or r.get('status')} ({r.get('branch')}, {r.get('sha')})" for r in (self.ctx["runs_fn"]().get(repo) or {}).get("runs", [])[:15]]
            return sentinel_ai.explain("ask", f"QUESTION: {question}\nrepo: {repo}\nlatest runs:\n" + "\n".join(recent), self.ai_cfg, self.ai_store)
        if kind == "build":
            try:
                run_id = int(request.get("run_id"))
            except (TypeError, ValueError):
                return {"ok": False, "error": i18n.t("err.bad_run_id")}
            run = next((r for r in (self.ctx["runs_fn"]().get(repo) or {}).get("runs", []) if r["id"] == run_id), None)
            if not run or run.get("conclusion") not in BAD:
                return {"ok": False, "error": i18n.t("err.not_a_failure")}
            if run.get("actor") not in (toolconfig.github_owner(), *BOT_ACTORS):
                return {"ok": False, "error": i18n.t("err.external_actor")}
            if self.ai_cfg["provider"] == "none":
                return sentinel_ai.explain(kind, "", self.ai_cfg, self.ai_store)
            parts = [f"repo: {repo}", f"workflow: {run.get('name')}", f"branch: {run.get('branch')}", f"event: {run.get('event')}"]
            try:
                jobs = self._gh("api", f"repos/{toolconfig.github_owner()}/{repo}/actions/runs/{run_id}/jobs?per_page=30", retries=1).get("jobs", [])
                for job in jobs:
                    if job.get("conclusion") in BAD:
                        steps = [s.get("name") for s in job.get("steps") or [] if s.get("conclusion") in BAD]
                        parts.append(f"failed job: {job.get('name')}; failed steps: {', '.join(steps)}")
                parts.append("--- end of the log of the failed steps ---")
                parts.append(self.gh_text("run", "view", str(run_id), "-R", f"{toolconfig.github_owner()}/{repo}", "--log-failed"))
            except Exception as error:
                parts.append("(the log could not be read: " + str(error)[:120] + ")")
            return sentinel_ai.explain("build", "\n".join(parts), self.ai_cfg, self.ai_store)
        if kind == "codeql":
            try:
                number = int(request.get("number"))
            except (TypeError, ValueError):
                return {"ok": False, "error": i18n.t("err.bad_alert_number")}
            alert = next((a for a in (self.alerts.get(repo) or {}).get("codeql") or [] if a["number"] == number), None)
            if not alert:
                return {"ok": False, "error": i18n.t("err.unknown_alert")}
            if self.ai_cfg["provider"] == "none":
                return sentinel_ai.explain(kind, "", self.ai_cfg, self.ai_store)
            parts = [f"repo: {repo}", f"rule: {alert['rule']} ({alert['description']})", f"severity: {alert['severity']}", f"file: {alert['path']}:{alert['line']}",
                     f"message: {alert['message']}"]
            path = alert.get("path") or ""
            if re.fullmatch(r"[A-Za-z0-9._/ -]{1,200}", path) and ".." not in path and alert.get("line"):
                try:
                    from urllib.parse import quote
                    text = self.gh_text("api", f"repos/{toolconfig.github_owner()}/{repo}/contents/{quote(path)}", "-H", "Accept: application/vnd.github.raw", limit=400000)
                    lines, at = text.splitlines(), int(alert["line"])
                    parts.append("--- code around the line ---")
                    parts += [f"{n + 1}: {lines[n]}" for n in range(max(0, at - 11), min(len(lines), at + 10))]
                except Exception as error:
                    parts.append("(the file could not be read: " + str(error)[:100] + ")")
            return sentinel_ai.explain("codeql", "\n".join(parts), self.ai_cfg, self.ai_store)
        return {"ok": False, "error": i18n.t("err.bad_kind")}


def local_request_ok(headers, port):
    """DNS-rebinding / cross-site guard (kept here for the callers of the sentinel; the rule lives in localguard.py, which the lite edition loads without the sentinel)."""
    import localguard
    return localguard.local_request_ok(headers, port)
