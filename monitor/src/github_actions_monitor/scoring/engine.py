# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""ScoreEngine: turns the metrics of a window (see `collector`) into a number from 0 to 100, a letter from A to E and a trend against the window before. Pure functions.

The number is a weighted sum of five parts, each one 0..100: CI reliability (success rate), speed (95th percentile of the duration), recovery (time to recover),
collaboration (time to resolve) and security (the points the open findings of the Security sentinel take off 100). The weights and the limits of every part are settings (`score.*`), conservative by default.

What the score never does (the same philosophy as the readiness score of the sentinel): show a number it cannot stand behind.
  state `calibrating`        the account has been watched for less than `calibrating_hours`: no number, no letter
  state `insufficient_data`  fewer than `min_runs` finished runs in the window, or the parts that have data weigh less than `min_coverage` of the total: no number
  state `scored`             a number, a letter, a trend; `coverage` (share of the weights that had data) and `data_quality` always travel with it
The recovery part counts a workflow that is still red at the end of the window with the time it has been red so far, so a failure nobody fixes weighs more every hour instead of disappearing.
A part with no data is left out and the others are rescaled, which lowers `coverage`; it is never counted as 0 and never as 100. Security only has data while its sentinel is on and has looked at
enough repositories; without it the answer says so (`missing_parts`) and `complete` is False, so 85 is never read as "all clear". GitHub gives no history of the findings, so the security part is the
same in the window and in the one before it: the trend shows what the CI and the collaboration did.
"""
import copy

from github_actions_monitor.scoring import collector

DEFAULTS = {
    "enabled": True,
    "source": "recent600",        # which runs the score reads: "recent600" = the newest 600 of the page (the default until 2.1.6), "ledger" = every run the cycle read, counted once in the ledger
    "window_days": 7,             # the window the user chooses (per account); the previous window of the same length gives the trend
    "calibrating_hours": 24,      # watched for less than this: no score yet
    "min_runs": 20,               # fewer finished runs in the window: not enough data
    "min_coverage": 0.5,          # parts with data must weigh at least this share
    "trend_flat": 2,              # a change smaller than this many points is "flat"
    "weights": {"reliability": 30, "speed": 15, "recovery": 15, "collaboration": 15, "security": 25},
    # each part is 100 at `good` and 0 at `bad`, linear in between (reliability: share of successful runs; the others: seconds, lower is better)
    "limits": {"reliability": {"good": 0.98, "bad": 0.5}, "speed": {"good": 600, "bad": 3600}, "recovery": {"good": 1800, "bad": 86400},
               "collaboration": {"good": 172800, "bad": 1209600}, "security": {"good": 0, "bad": 100}},
    "grades": {"A": 90, "B": 80, "C": 70, "D": 55},          # minimum score of each letter; below the last one is E
    "alert": {"enabled": True, "drop_points": 10, "notify_external": False},
}
PARTS = ("reliability", "speed", "recovery", "collaboration", "security")
SOURCE = {"reliability": "success_rate", "speed": "duration_p95", "recovery": "mttr", "collaboration": "collab_resolution_time", "security": "security_penalty"}
SAMPLES = {"reliability": "runs", "speed": "durations", "recovery": "recoveries", "collaboration": "collab_closed", "security": "security_repos"}
MISSING_PARTS = ("security",)      # the parts that depend on something that can be off (a sentinel): when they have no data the answer says so and is not `complete`


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value not in (float("inf"), float("-inf"))


def settings(config):
    """`score` of the configuration merged over DEFAULTS. A value of the wrong type, out of range or unknown keeps the default; weights must not all be zero."""
    merged = copy.deepcopy(DEFAULTS)
    user = (config or {}).get("score") if isinstance((config or {}).get("score"), dict) else None
    if not user:
        return merged
    if isinstance(user.get("enabled"), bool):
        merged["enabled"] = user["enabled"]
    if user.get("source") in ("recent600", "ledger"):
        merged["source"] = user["source"]
    ranges = {"window_days": (1, 90), "calibrating_hours": (0, 720), "min_runs": (1, 100000), "trend_flat": (0, 100)}
    for key, (low, high) in ranges.items():
        v = user.get(key)
        if isinstance(v, int) and not isinstance(v, bool) and low <= v <= high:
            merged[key] = v
    v = user.get("min_coverage")
    if _number(v) and 0 <= v <= 1:
        merged["min_coverage"] = float(v)
    weights = user.get("weights")
    if isinstance(weights, dict):
        trial = dict(merged["weights"])
        for name in PARTS:
            if _number(weights.get(name)) and 0 <= weights[name] <= 1000:
                trial[name] = weights[name]
        if sum(trial.values()) > 0:
            merged["weights"] = trial
    limits = user.get("limits")
    if isinstance(limits, dict):
        for name in PARTS:
            entry = limits.get(name)
            if isinstance(entry, dict) and _number(entry.get("good")) and _number(entry.get("bad")) and entry["good"] != entry["bad"] and entry["good"] >= 0 and entry["bad"] >= 0:
                merged["limits"][name] = {"good": entry["good"], "bad": entry["bad"]}
    grades = user.get("grades")
    if isinstance(grades, dict):
        trial = {k: grades.get(k) for k in ("A", "B", "C", "D")}
        values = list(trial.values())
        if all(_number(x) and 0 <= x <= 100 for x in values) and all(values[i] > values[i + 1] for i in range(3)):
            merged["grades"] = {k: trial[k] for k in trial}
    alert = user.get("alert")
    if isinstance(alert, dict):
        for key in ("enabled", "notify_external"):
            if isinstance(alert.get(key), bool):
                merged["alert"][key] = alert[key]
        if _number(alert.get("drop_points")) and 1 <= alert["drop_points"] <= 100:
            merged["alert"]["drop_points"] = alert["drop_points"]
    return merged


def part_score(value, good, bad):
    """0..100 for a value between `bad` (0) and `good` (100), linear and clamped; works whichever of the two is larger."""
    if not _number(value):
        return None
    span = good - bad
    return round(max(0.0, min(100.0, (value - bad) / span * 100.0)), 2)


def letter(score, grades):
    for name in ("A", "B", "C", "D"):
        if score >= grades[name]:
            return name
    return "E"


def _parts(metrics, cfg):
    rows, weight_total, weight_with_data, total = [], 0.0, 0.0, 0.0
    for name in PARTS:
        weight = cfg["weights"][name]
        lim = cfg["limits"][name]
        value = metrics.get(SOURCE[name])
        sub = part_score(value, lim["good"], lim["bad"])
        samples = (metrics.get("samples") or {}).get(SAMPLES[name], 0)
        if name == "recovery":
            samples += (metrics.get("samples") or {}).get("recoveries_open", 0)
        if name == "collaboration":
            samples += (metrics.get("samples") or {}).get("collab_open", 0)
        weight_total += weight
        row = {"part": name, "weight": weight, "value": value, "score": sub, "samples": samples, "available": sub is not None}
        if sub is not None:
            weight_with_data += weight
            total += sub * weight
        rows.append(row)
    return rows, weight_total, weight_with_data, total


def compute(metrics, cfg, watched_hours=None, previous=None):
    """The answer for one window. `metrics` comes from `collector.collect`; `watched_hours` is how long the account has been watched (None = unknown, never calibrating);
    `previous` is the score (number) of the window before, or None."""
    runs = (metrics.get("samples") or {}).get("runs", 0)
    rows, weight_total, weight_with_data, total = _parts(metrics, cfg)
    coverage = round(weight_with_data / weight_total, 3) if weight_total else 0.0
    missing = [r["part"] for r in rows if r["part"] in MISSING_PARTS and not r["available"]]
    base = {"parts": rows, "coverage": coverage, "missing_parts": missing, "complete": not missing, "window_days": cfg["window_days"],
            "score": None, "letter": None, "trend": None}
    reasons = []
    if _number(watched_hours) and watched_hours < cfg["calibrating_hours"]:
        state = "calibrating"
        reasons.append("watched_briefly")
    else:
        if runs < cfg["min_runs"]:
            reasons.append("few_runs")
        if coverage < cfg["min_coverage"]:
            reasons.append("low_coverage")
        if weight_with_data <= 0:      # no part has data (possible with min_coverage 0): there is nothing to average
            reasons.append("no_data")
        state = "insufficient_data" if reasons else "scored"
    base["state"] = state
    base["data_quality"] = {"runs": runs, "min_runs": cfg["min_runs"], "coverage": coverage, "min_coverage": cfg["min_coverage"],
                            "watched_hours": watched_hours, "calibrating_hours": cfg["calibrating_hours"], "reasons": reasons}
    if state != "scored":
        return base
    score = round(total / weight_with_data, 1)
    base["score"], base["letter"] = score, letter(score, cfg["grades"])
    base["trend"] = trend(score, previous, cfg["trend_flat"])
    return base


def trend(score, previous, flat):
    """{"direction": up|down|flat|unknown, "delta": points or None} of this score against the previous window."""
    if not _number(previous) or not _number(score):
        return {"direction": "unknown", "delta": None}
    delta = round(score - previous, 1)
    direction = "flat" if abs(delta) < flat else ("up" if delta > 0 else "down")
    return {"direction": direction, "delta": delta}


def with_security(metrics, security):
    """The metrics with the security figures added: `security` is {"penalty": points, "repos": how many repositories they come from} or None (no data for that part)."""
    if isinstance(security, dict) and _number(security.get("penalty")) and _number(security.get("repos")) and security["repos"] > 0:
        metrics = {**metrics, "security_penalty": float(security["penalty"]), "samples": {**(metrics.get("samples") or {}), "security_repos": int(security["repos"])}}
    return metrics


def score_window(runs, collab_items, end, cfg, watched_hours=None, security=None):
    """Convenience: the window [end - window_days, end), the one before it for the trend, and the answer. The previous window is scored with the same rules
    and only gives a trend when it was itself `scored`. The security figures (see `with_security`) are the same in both windows: GitHub gives no history of them."""
    span = cfg["window_days"] * collector.DAY
    now_metrics = with_security(collector.collect(runs, collab_items, end - span, end), security)
    before_metrics = with_security(collector.collect(runs, collab_items, end - 2 * span, end - span), security)
    before = compute(before_metrics, cfg, watched_hours=None)
    return compute(now_metrics, cfg, watched_hours=watched_hours, previous=before["score"] if before["state"] == "scored" else None)
