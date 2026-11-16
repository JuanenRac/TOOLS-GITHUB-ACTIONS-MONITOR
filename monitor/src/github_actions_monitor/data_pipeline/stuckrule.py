# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""When is a run that is not finished "stuck", and why does it wait.

By default one limit (`stuck_minutes`) decides, as always. Three settings of the block `ci.stuck` make it fairer without changing anything for who does not touch them:

  * `learned` (off): the limit of a workflow is what its own recent runs say (a percentile of the durations of its successful runs times a margin), kept between `min_minutes` and `max_minutes`,
    so a build that lasts six hours is not "stuck" at hour two while a build of two minutes that runs for an hour is.
  * `workflow_minutes` / `runner_minutes` (empty): a fixed limit for a workflow file (`build.yml=420`) or for a runner label (`self-hosted=720`); the workflow wins over the label.
  * `queue_minutes` (0 = same limit as a running build): a longer limit for a run that has not even started because it waits for a runner.

Every run that waits also says WHY: `queue` (it waits for a runner), `awaiting_approval` (it waits for a person), `runner_down` (it waits and every self-hosted runner with its label is offline)
or `build` (it is running). Pure functions: no network, no clock.
"""
import fnmatch
import math

DEFAULTS = {"learned": False, "percentile": 95, "margin": 2.0, "min_samples": 3, "min_minutes": 30, "max_minutes": 720, "queue_minutes": 0,
            "workflow_minutes": [], "runner_minutes": [], "awaiting_stuck": True}
REASONS = ("queue", "awaiting_approval", "runner_down", "build")
QUEUE_STATES = ("queued", "pending", "requested")


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def _pairs(value):
    """["build.yml=420"] -> [("build.yml", 420)]; an entry that is not `pattern=minutes` is ignored."""
    out = []
    for item in value if isinstance(value, (list, tuple)) else ():
        name, _, minutes = str(item).partition("=")
        if name and minutes.isdigit() and 1 <= int(minutes) <= 100000:
            out.append((name, int(minutes)))
    return out


def settings(config):
    """The block `ci.stuck` with its conservative defaults; an invalid value keeps the default."""
    ci = (config or {}).get("ci")
    block = ci.get("stuck") if isinstance(ci, dict) and isinstance(ci.get("stuck"), dict) else {}
    margin = block.get("margin")
    low = _int(block.get("min_minutes"), 1, 10000, DEFAULTS["min_minutes"])
    high = _int(block.get("max_minutes"), 1, 100000, DEFAULTS["max_minutes"])
    return {"learned": block.get("learned") is True, "percentile": _int(block.get("percentile"), 50, 100, DEFAULTS["percentile"]),
            "margin": float(margin) if isinstance(margin, (int, float)) and not isinstance(margin, bool) and 1.0 <= margin <= 20 else DEFAULTS["margin"],
            "min_samples": _int(block.get("min_samples"), 2, 100, DEFAULTS["min_samples"]), "min_minutes": min(low, high), "max_minutes": max(low, high),
            "queue_minutes": _int(block.get("queue_minutes"), 0, 100000, 0), "workflow_minutes": _pairs(block.get("workflow_minutes")),
            "runner_minutes": _pairs(block.get("runner_minutes")), "awaiting_stuck": block.get("awaiting_stuck") is not False}


def workflow_key(run):
    return run.get("path") or run.get("name") or ""


def percentile(values, pct):
    """Nearest-rank percentile of a list of numbers (None when empty)."""
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[max(0, min(len(ordered) - 1, math.ceil(pct / 100 * len(ordered)) - 1))]


def learn(runs, cfg):
    """{(repo, workflow): minutes} from the successful, finished runs the monitor already holds. Only a workflow with `min_samples` runs gets a learned limit."""
    seen = {}
    for run in runs:
        if run.get("status") == "completed" and run.get("conclusion") == "success" and (run.get("seconds") or 0) > 0 and not run.get("fork"):
            seen.setdefault((run.get("repo"), workflow_key(run)), []).append(run["seconds"] / 60)
    out = {}
    for key, durations in seen.items():
        if len(durations) >= cfg["min_samples"]:
            wanted = percentile(durations, cfg["percentile"]) * cfg["margin"]
            out[key] = int(min(cfg["max_minutes"], max(cfg["min_minutes"], math.ceil(wanted))))
    return out


def _match(pattern, text):
    return fnmatch.fnmatchcase(str(text or "").lower(), pattern.lower())


def reason_of(run, labels=(), offline_labels=()):
    status = run.get("status")
    if run.get("conclusion") == "action_required" or status == "waiting":
        return "awaiting_approval"
    if status in QUEUE_STATES:
        wanted = {str(x).lower() for x in labels}
        if wanted and wanted & {str(x).lower() for x in offline_labels}:
            return "runner_down"
        return "queue"
    return "build"


def evaluate(run, base_minutes, cfg, learned=None, labels=(), offline_labels=()):
    """(stuck, reason, limit_minutes) of one unfinished run. `base_minutes` is the classic `stuck_minutes`; `learned` is the result of learn(); `labels` the runner labels of its jobs (when known)."""
    reason = reason_of(run, labels, offline_labels)
    limit = base_minutes
    key = (run.get("repo"), workflow_key(run))
    if cfg["learned"] and learned and key in learned:
        limit = learned[key]
    for pattern, minutes in cfg["runner_minutes"]:
        if any(_match(pattern, label) for label in labels):
            limit = minutes
            break
    for pattern, minutes in cfg["workflow_minutes"]:
        if _match(pattern, workflow_key(run)) or _match(pattern, run.get("name")):
            limit = minutes
            break
    if reason in ("queue", "runner_down") and cfg["queue_minutes"]:
        limit = max(limit, cfg["queue_minutes"])
    if reason == "awaiting_approval" and not cfg["awaiting_stuck"]:
        return False, reason, limit
    return (run.get("seconds") or 0) > limit * 60, reason, limit


def offline_labels(runner_payload):
    """The labels that only offline self-hosted runners carry (a run asking for one of them waits for ever): from the payload of integrations/runners.py."""
    online, off = set(), set()
    for item in (runner_payload or {}).get("runners") or []:
        target = off if item.get("state") == "offline" else online
        target.update(str(x).lower() for x in item.get("labels") or [] if str(x).lower() not in ("self-hosted", "linux", "windows", "macos", "x64", "arm64"))
    return off - online
