# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The service of the score: keeps a small ledger of the runs and of the collaboration alerts the monitor has seen, so that a window of days can be scored even though the page only lists the
latest runs of each repository, and writes the snapshot of the account once an hour.

  ledger     the document `score_ledger` of the account: {"first_seen", "last_tick", "runs": {run id: [started, conclusion, seconds, repo, workflow]},
             "collab": {alert id: [opened, closed or None]}}. Only the finished runs that count (a success or a failure) are kept, only as long as two windows need them, and never more than
             MAX_RUNS; the collaboration alerts are followed from the moment they appear until they are gone (that is when they count as resolved).
  snapshot   {"schema", "at", "window_days", the answer of the engine, "repos": [...]} saved under the hour it was made, one per account and hour.

`tick` is cheap when it is not due (the ledger is updated in memory only when a pass really runs) and never raises into the caller's loop beyond what it returns.
"""
import time
from datetime import datetime, timezone

from github_actions_monitor.data_pipeline.analytics import BAD
from github_actions_monitor.app import degraded
from github_actions_monitor.scoring import collector, drop, engine
from github_actions_monitor.util import clock

LEDGER_DOC = "score_ledger"
MIN_INTERVAL = 600          # seconds between two passes
MAX_RUNS = 20000
MAX_COLLAB = 5000
MAX_REPOS = 200
SCHEMA = 1


def empty_ledger(now):
    return {"first_seen": now, "last_tick": 0, "runs": {}, "collab": {}, "drop_open": False}


def clean_ledger(data, now):
    """A ledger read back from the storage with anything unreadable dropped (a hand-edited or half-written document must not stop the score)."""
    ledger = empty_ledger(now)
    if not isinstance(data, dict):
        return ledger
    if isinstance(data.get("first_seen"), (int, float)) and not isinstance(data.get("first_seen"), bool):
        ledger["first_seen"] = float(clock.settle(data["first_seen"], now))      # a clock set back: the watch counts from now, not from a moment that has not come yet
    if isinstance(data.get("last_tick"), (int, float)) and not isinstance(data.get("last_tick"), bool):
        ledger["last_tick"] = 0.0 if clock.in_future(data["last_tick"], now) else float(data["last_tick"])      # a pass saved with a clock that was ahead: the next pass is due now and writes a good moment, not when the old clock is reached again
    ledger["drop_open"] = data.get("drop_open") is True
    if isinstance(data.get("truncated_at"), (int, float)) and not isinstance(data.get("truncated_at"), bool):
        ledger["truncated_at"] = float(data["truncated_at"])
    for key, row in (data.get("runs") or {}).items() if isinstance(data.get("runs"), dict) else []:
        if isinstance(row, list) and len(row) == 5 and isinstance(row[0], (int, float)) and row[1] in ("success", *BAD):
            ledger["runs"][str(key)] = row
    for key, row in (data.get("collab") or {}).items() if isinstance(data.get("collab"), dict) else []:
        if isinstance(row, list) and len(row) == 2 and isinstance(row[0], (int, float)):
            ledger["collab"][str(key)] = row
    return ledger


def run_key(run):
    """The key of a run in the ledger: its id, and `id:attempt` from the second attempt on. GitHub keeps the id when a run is re-run, so each attempt is its own execution:
    the failed first one and the green second one both count, and the recovery between them is seen."""
    attempt = run.get("attempt")
    if isinstance(attempt, int) and not isinstance(attempt, bool) and attempt > 1:
        return f"{run['id']}:{attempt}"
    return str(run["id"])


def update_ledger(ledger, runs, collab_alerts, now, keep_days, collab_known=True):
    """Adds the finished runs not seen before and follows the collaboration alerts; forgets what is older than `keep_days`. `runs` are the run dicts of the monitor,
    `collab_alerts` the open alerts of the collaboration sentinel ({"id", "created_at"}); `collab_known` is False while that sentinel is off or has not looked yet, so an empty list is not read as "everything was resolved"."""
    for run in runs or []:
        if not isinstance(run, dict) or run.get("status") != "completed" or run.get("conclusion") not in ("success", *BAD) or run.get("id") is None:
            continue
        started = collector.to_ts(run.get("started"))
        if started is None:
            continue
        seconds = run.get("seconds") if isinstance(run.get("seconds"), (int, float)) and not isinstance(run.get("seconds"), bool) else None
        ledger["runs"].setdefault(run_key(run), [started, run["conclusion"], seconds, str(run.get("repo") or "")[:100], str(run.get("name") or "")[:100]])
    open_now = set()
    for alert in (collab_alerts or []) if collab_known else []:
        if not isinstance(alert, dict) or not alert.get("id"):
            continue
        key = str(alert["id"])[:200]
        open_now.add(key)
        if key not in ledger["collab"]:
            ledger["collab"][key] = [collector.to_ts(alert.get("created_at")) or now, None]
    for key, row in (ledger["collab"].items() if collab_known else []):
        if row[1] is None and key not in open_now:
            row[1] = now
    horizon = now - keep_days * collector.DAY
    ledger["runs"] = {k: v for k, v in ledger["runs"].items() if v[0] >= horizon}
    ledger["collab"] = {k: v for k, v in ledger["collab"].items() if v[1] is None or v[1] >= horizon}
    if len(ledger["runs"]) > MAX_RUNS:
        newest = sorted(ledger["runs"].items(), key=lambda kv: kv[1][0], reverse=True)[:MAX_RUNS]
        ledger["runs"] = dict(newest)
        cut = newest[-1][1][0]      # everything older than the oldest run kept was dropped: from here on the ledger is incomplete
        ledger["truncated_at"] = max(cut, ledger.get("truncated_at") or 0.0)
    if len(ledger["collab"]) > MAX_COLLAB:
        newest = sorted(ledger["collab"].items(), key=lambda kv: kv[1][0], reverse=True)[:MAX_COLLAB]
        ledger["collab"] = dict(newest)
    return ledger


def ledger_runs(ledger):
    return [{"id": rid, "repo": row[3], "name": row[4], "status": "completed", "conclusion": row[1], "seconds": row[2], "started": row[0]} for rid, row in ledger["runs"].items()]


def ledger_collab(ledger):
    return [{"opened": row[0], "closed": row[1]} for row in ledger["collab"].values()]


def repo_rows(runs, end, cfg):
    """The breakdown by repository: how each one stands on its own (its CI only; the collaboration part has no data at this level and is left out)."""
    span = cfg["window_days"] * collector.DAY
    rows = []
    for repo, metrics in collector.by_repo(runs, end - span, end).items():
        samples = metrics["samples"]["runs"]
        if not samples:
            continue
        answer = engine.compute(metrics, cfg, watched_hours=None)
        rows.append({"repo": repo, "state": answer["state"], "score": answer["score"], "letter": answer["letter"], "runs": samples, "success_rate": metrics["success_rate"]})
    rows.sort(key=lambda r: (r["score"] is None, r["score"] if r["score"] is not None else 0, r["repo"]))
    return rows[:MAX_REPOS]


def make_snapshot(ledger, cfg, now, account=None, security=None):
    """The snapshot of the account for the window that ends at `now`. `security` is {"penalty", "repos"} from the Security sentinel, or None while it is off or has seen too little."""
    runs, collab = ledger_runs(ledger), ledger_collab(ledger)
    watched_hours = max(0.0, (now - ledger["first_seen"]) / 3600.0)
    answer = engine.score_window(runs, collab, now, cfg, watched_hours=watched_hours, security=security)
    cut = ledger.get("truncated_at")
    if isinstance(cut, (int, float)) and cut > now - cfg["window_days"] * collector.DAY:      # the ledger dropped runs that belong to this window: the figures see only part of it, and it is said
        answer["data_quality"]["truncated"] = True
        answer["data_quality"]["reasons"] = [*answer["data_quality"]["reasons"], "truncated"]
    return {"schema": SCHEMA, "at": now, "account": account, "window_days": cfg["window_days"], **answer, "repos": repo_rows(runs, now, cfg)}


def hour_key(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H")


def tick(storage, account_id, config, runs, collab_alerts, now=None, force=False, collab_known=True, security=None):
    """One pass: updates the ledger, writes the snapshot of the hour and returns it; None when the score is off or the pass is not due. Needs the storage of the account."""
    now = time.time() if now is None else now
    cfg = engine.settings(config)
    if not cfg["enabled"]:
        return None
    try:
        stored = storage.load_doc(account_id, LEDGER_DOC, None, strict=True)
    except OSError as error:        # the ledger exists but cannot be read now: no pass, so the last good ledger is never written over by an empty one
        degraded.note("score", error)
        return None
    ledger = clean_ledger(stored, now)
    if not force and now - ledger["last_tick"] < MIN_INTERVAL:
        return None
    keep_days = min(180, 2 * cfg["window_days"] + 1)
    update_ledger(ledger, runs, collab_alerts, now, keep_days, collab_known)
    ledger["last_tick"] = now
    snapshot = make_snapshot(ledger, cfg, now, account_id, security)
    snapshot["drop"] = drop.detect(snapshot, cfg)
    fresh = bool(snapshot["drop"]) and not ledger.get("drop_open")      # the moment the drop appears: the only time it goes out through the notification channels
    ledger["drop_open"] = bool(snapshot["drop"])
    storage.save_doc(account_id, LEDGER_DOC, ledger)
    storage.save_score_snapshot(account_id, hour_key(now), snapshot)
    snapshot = {**snapshot, "drop_new": fresh}
    return snapshot
