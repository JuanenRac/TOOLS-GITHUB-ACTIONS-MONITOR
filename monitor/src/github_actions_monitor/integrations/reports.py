# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Four optional reports, each OFF by default (block `reports`), that answer questions the page did not: are the workflow files of my repositories well written, how long do jobs wait for a runner,
which repositories are ready for a release and which are blocked, and which releases carry a software bill of materials and signatures. Standard library only.

  workflow_hygiene   reads the workflow files of a few repositories a cycle from GitHub and applies the rules of `lint_workflows` (actions not pinned to a commit, permissions, injection, pull_request_target,
                     secrets in clear) plus two more: a job without `timeout-minutes` and a workflow without `concurrency`. For repositories that have no local clone (the panel A13 reads the clones).
  queue              reads the jobs of a few finished runs that waited, and says for each kind of runner (Linux, Windows, macOS, self-hosted, larger) how long a job waited before it started.
  release_view       no call at all: from the snapshot of the Sentinel, a repository is READY (entries in the changelog or a green build that nobody released, nothing red, no signature waiting) or BLOCKED
                     (a red workflow, or a signature that has waited), with the reasons.
  supply_chain       reads the latest release of a few repositories and says whether it carries a software bill of materials (SBOM), checksums and signatures or attestations.

`reports.max_calls_per_cycle` caps the calls of GitHub of all of them in one cycle. What is read is kept in memory for a day, only watched repositories are read, and nothing is ever written to GitHub."""
import base64
import re
import statistics
import threading
import time

from github_actions_monitor.app import degraded

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
FILE_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\.ya?ml\Z")
DAY = 86400
KEEP = 600      # entries of the queue report kept
KINDS = ("workflow_hygiene", "queue", "release_view", "supply_chain")
STATE = {"hygiene": {}, "supply": {}, "queue": [], "queue_seen": [], "turn": {"hygiene": 0, "supply": 0}}
LOCK = threading.RLock()


def settings(config):
    block = config.get("reports") if isinstance(config, dict) and isinstance(config.get("reports"), dict) else {}
    out = {k: (block.get(k) or {}).get("enabled") is True if isinstance(block.get(k), dict) else False for k in KINDS}
    calls = block.get("max_calls_per_cycle")
    out["max_calls_per_cycle"] = calls if isinstance(calls, int) and not isinstance(calls, bool) and 1 <= calls <= 50 else 4
    return out


def reset():
    with LOCK:
        STATE.update({"hygiene": {}, "supply": {}, "queue": [], "queue_seen": [], "turn": {"hygiene": 0, "supply": 0}})


# -- workflow hygiene --------------------------------------------------------------------------------------------------------------------------------------------------------------------

def hygiene_findings(text, name="workflow.yml"):
    """[{"rule", "line", "severity", "detail"}] of one workflow file: the rules of the linter plus `no_timeout` (a job without `timeout-minutes`) and `no_concurrency`."""
    from github_actions_monitor.cli import lint_workflows
    found = [{"rule": f["rule"], "line": f["line"], "severity": f["severity"], "detail": f.get("detail", "")} for f in lint_workflows.lint_text(text, name)]
    lines = text.replace("\r\n", "\n").split("\n")
    if not any(re.match(r"concurrency\s*:", line) for line in lines):
        found.append({"rule": "no_concurrency", "line": 1, "severity": "info", "detail": ""})
    jobs_at = next((i for i, line in enumerate(lines) if re.match(r"jobs\s*:\s*$", line)), None)
    if jobs_at is not None:
        starts = [(i, m.group(1)) for i, line in enumerate(lines[jobs_at + 1:], jobs_at + 1) for m in [re.match(r"^  ([A-Za-z0-9_-]+)\s*:\s*$", line)] if m]
        for index, (start, job) in enumerate(starts):
            end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
            block = [line for line in lines[start + 1:end]]
            if any(re.match(r"^    uses\s*:", line) for line in block):
                continue      # a call of a reusable workflow has no steps of its own: the called one carries the limit
            if not any(re.match(r"^    timeout-minutes\s*:", line) for line in block):
                found.append({"rule": "no_timeout", "line": start + 1, "severity": "warn", "detail": job})
    return found


# -- queue ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def runner_group(labels):
    names = [str(x).lower() for x in labels or []]
    if "self-hosted" in names:
        return "self-hosted"
    text = " ".join(names)
    if re.search(r"xlarge|-large|\blarger\b|\d+-core|\d+core", text):
        return "larger"
    for key, group in (("macos", "macos"), ("windows", "windows"), ("ubuntu", "linux"), ("linux", "linux")):
        if key in text:
            return group
    return "other"


def queue_stats(rows):
    """{group: {"jobs", "median", "max"}} from rows {"group", "wait"} (seconds a job waited before it started)."""
    by = {}
    for row in rows:
        by.setdefault(row["group"], []).append(max(0, int(row["wait"])))
    return {g: {"jobs": len(v), "median": int(statistics.median(v)), "max": max(v)} for g, v in sorted(by.items())}


def job_waits(body):
    """The rows of one answer of `actions/runs/ID/jobs`: how long each job waited between being created and starting."""
    from datetime import datetime
    rows = []

    def when(text):
        try:
            return datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ").timestamp()
        except ValueError:
            return None
    for job in (body or {}).get("jobs") or []:
        made, began = when(job.get("created_at")), when(job.get("started_at"))
        if made is not None and began is not None:
            rows.append({"group": runner_group(job.get("labels")), "wait": began - made})
    return rows


# -- the view of a release -----------------------------------------------------------------------------------------------------------------------------------------------------------

def release_view(snapshot):
    """[{"repo", "state": "ready" | "blocked", "entries", "reasons": [...]}] from the snapshot of the Sentinel (no call). Empty while the Sentinel has nothing."""
    s = snapshot if isinstance(snapshot, dict) else {}
    a5, a2 = s.get("a5") or {}, s.get("a2") or {}
    red = {r.get("repo") for r in (a2.get("red") or []) if isinstance(r, dict)}
    waiting = {g.get("repo") for g in (a5.get("pending_sign") or []) if isinstance(g, dict)}
    entries = {c.get("repo"): c.get("entries") for c in (a5.get("candidates") or []) if isinstance(c, dict)}
    green = {g.get("repo") for g in (a5.get("green_unreleased") or []) if isinstance(g, dict)}
    rows = []
    for repo in sorted(x for x in set(entries) | green | red | waiting if x):
        reasons = (["ci_red"] if repo in red else []) + (["signature_waiting"] if repo in waiting else [])
        if repo not in entries and repo not in green and not reasons:
            continue
        rows.append({"repo": repo, "state": "blocked" if reasons else "ready", "entries": entries.get(repo), "reasons": reasons})
    return sorted(rows, key=lambda r: (r["state"] != "blocked", r["repo"]))


# -- supply chain -------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def asset_class(names):
    """What the assets of a release say about its supply chain: {"sbom", "checksums", "signature"} (names only; the files are never downloaded)."""
    low = [str(n).lower() for n in names or []]
    return {"sbom": any(re.search(r"sbom|\.spdx|\.cdx|cyclonedx|bom\.json", n) for n in low), "checksums": any(re.search(r"sha256sums|sha512sums|checksums|\.sha256", n) for n in low),
            "signature": any(re.search(r"\.sig$|\.asc$|\.pem$|\.sigstore|\.intoto\.jsonl|attestation|\.minisig", n) for n in low)}


# -- the cycle -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _next(kind, repos, now):
    """The next watched repository whose answer is older than a day (round robin), or None."""
    with LOCK:
        known = STATE["hygiene" if kind == "hygiene" else "supply"]
        for step in range(len(repos)):
            repo = repos[(STATE["turn"][kind] + step) % len(repos)]
            if repo not in known or now - known[repo]["at"] > DAY:
                STATE["turn"][kind] = (STATE["turn"][kind] + step + 1) % len(repos)
                return repo
    return None


def cycle(config, owner, repos, runs, read, now=None):
    """Reads what the enabled reports need, within `reports.max_calls_per_cycle` calls. `read(endpoint)` answers the JSON of a read of the API (or raises). Returns the calls made. Never raises."""
    cfg = settings(config)
    now = time.time() if now is None else now
    repos = [r for r in repos if NAME_RE.match(str(r))]
    budget, spent = cfg["max_calls_per_cycle"], 0
    try:
        if cfg["queue"]:
            seen = set(STATE["queue_seen"])
            for run in runs or []:
                if spent >= budget:
                    break
                if run.get("status") == "completed" and (run.get("queued") or 0) >= 20 and run.get("id") not in seen and run.get("repo") in repos:
                    spent += 1
                    with LOCK:
                        STATE["queue_seen"] = (STATE["queue_seen"] + [run.get("id")])[-KEEP:]
                    rows = job_waits(read(f"repos/{owner}/{run['repo']}/actions/runs/{int(run['id'])}/jobs?per_page=100"))
                    with LOCK:
                        STATE["queue"] = (STATE["queue"] + rows)[-KEEP:]
        if cfg["supply_chain"] and repos and spent < budget:
            repo = _next("supply", repos, now)
            if repo:
                spent += 1
                try:
                    release = read(f"repos/{owner}/{repo}/releases/latest")
                    names = [a.get("name") for a in (release.get("assets") or []) if isinstance(a, dict)]
                    result = {"at": now, "tag": str(release.get("tag_name") or "")[:60], **asset_class(names)}
                except Exception:   # noqa: BLE001 - a repository without a release is "none", not a failure
                    result = {"at": now, "tag": "", "sbom": False, "checksums": False, "signature": False}
                with LOCK:
                    STATE["supply"][repo] = result
        if cfg["workflow_hygiene"] and repos and spent < budget:
            repo = _next("hygiene", repos, now)
            if repo:
                spent += 1
                findings, files = [], 0
                try:
                    listing = read(f"repos/{owner}/{repo}/contents/.github/workflows")
                except Exception:   # noqa: BLE001 - no workflows folder
                    listing = []
                for item in listing if isinstance(listing, list) else []:
                    name = str(item.get("name") or "") if isinstance(item, dict) else ""
                    if not FILE_RE.match(name) or spent >= budget:
                        continue
                    spent += 1
                    files += 1
                    body = read(f"repos/{owner}/{repo}/contents/.github/workflows/{name}")
                    text = base64.b64decode(str(body.get("content") or "")).decode("utf-8", "replace") if body.get("encoding") == "base64" else ""
                    findings += [dict(f, file=name) for f in hygiene_findings(text, name)]
                with LOCK:
                    STATE["hygiene"][repo] = {"at": now, "files": files, "findings": findings[:60]}
    except Exception as error:   # noqa: BLE001 - a report that cannot be read never stops the cycle
        degraded.note("reports.cycle", error)
    return spent


def payload(config, snapshot=None):
    """The document of `GET /api/reports`: for each report whether it is on and what it knows now."""
    cfg = settings(config)
    with LOCK:
        hygiene = [{"repo": r, "files": v["files"], "findings": v["findings"]} for r, v in sorted(STATE["hygiene"].items()) if v["findings"]]
        supply = [{"repo": r, **{k: v[k] for k in ("tag", "sbom", "checksums", "signature")}} for r, v in sorted(STATE["supply"].items())]
        queue = queue_stats(STATE["queue"])
    return {"schema": 1, "max_calls_per_cycle": cfg["max_calls_per_cycle"],
            "workflow_hygiene": {"enabled": cfg["workflow_hygiene"], "read": len(STATE["hygiene"]), "repos": hygiene[:30]},
            "queue": {"enabled": cfg["queue"], "groups": queue},
            "release_view": {"enabled": cfg["release_view"], "repos": release_view(snapshot) if cfg["release_view"] else []},
            "supply_chain": {"enabled": cfg["supply_chain"], "repos": supply[:60]}}
