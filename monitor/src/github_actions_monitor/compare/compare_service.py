# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What `GET /api/compare` answers: the ledger and the snapshots of the score of ONE account (the one the process serves, so the usual scope of the account applies) read from the storage and set
against each other for two windows. Read only; nothing is asked of GitHub. The answer always carries `state`, `coverage` and `data_quality`; a figure that cannot be stood behind is null with a
state (`insufficient_data`, `baseline_unavailable`), never a 0 or a 100.

  state   off | calibrating | baseline_unavailable | compared
"""
import copy
import csv
import io
import json
import threading
import time

from github_actions_monitor.compare import changes, config, metrics, windows
from github_actions_monitor.scoring import engine, ledger as score_ledger
from github_actions_monitor.scoring.collector import DAY

SCHEMA = 1
FORMATS = ("json", "ndjson", "csv")
_CACHE = {}
MAX_CACHE = 32


def _empty(account, cfg, state, reason, wins=None):
    out = {"schema": SCHEMA, "account": account, "enabled": cfg["enabled"], "state": state, "windows": None, "days": cfg["default_days_filter"], "baseline": "previous", "metrics": {},
           "changes": {"worse": [], "better": [], "new_failures": [], "resolved_failures": [], "reason": reason}, "coverage": 0.0,
           "data_quality": {"runs_now": 0, "runs_base": 0, "min_runs": cfg["min_runs_per_window"], "truncated": False, "reasons": [reason]}}
    if wins:
        out["windows"] = _windows_view(wins)
        out["days"], out["baseline"] = wins["days"], wins["baseline"]
    return out


def _windows_view(wins):
    return {"now": {"from": wins["now"][0], "to": wins["now"][1]}, "base": {"from": wins["base"][0], "to": wins["base"][1]}, "days": wins["window_days"]}


def _baseline_problem(wins, ledger, now, cfg):
    """The reason the baseline cannot be used, or None. The ledger holds only what the score needs (two windows); a baseline older than that, or older than the monitor, is not made up."""
    oldest = min([row[0] for row in (ledger.get("runs") or {}).values() if isinstance(row, list) and row and isinstance(row[0], (int, float))] or [now])
    data_start = min(ledger["first_seen"], oldest)
    if (now - data_start) / DAY < cfg["min_days_of_history"]:
        return "history_too_short"
    if wins["base"][0] < data_start - 3600:
        return "before_history"
    return None


def _entry(name, now_side, base_side, usable):
    value_now, value_base = now_side["values"][name], base_side["values"][name] if base_side else None
    entry = {"now": value_now, "base": value_base, "delta": None, "direction": "unknown", "better": "lower" if metrics.LOWER_IS_BETTER[name] else "higher",
             "samples_now": now_side["samples"], "samples_base": base_side["samples"] if base_side else None}
    if not usable:
        entry["state"] = "baseline_unavailable"
    elif value_now is None or value_base is None:
        entry["state"] = "insufficient_data"
        entry["missing"] = ([{"window": "now", "reason": now_side["missing"].get(name, "few_runs")}] if value_now is None else []) + ([{"window": "base", "reason": base_side["missing"].get(name, "few_runs")}] if value_base is None else [])
    else:
        entry["state"] = "ok"
        entry["delta"] = round(value_now - value_base, 4)
        entry["direction"] = metrics.direction(name, value_now, value_base)
    return entry


def _compute(storage, account, raw_config, ask, now, zone):
    cfg = config.settings(raw_config)
    if not cfg["enabled"]:
        return _empty(account, cfg, "off", "off")
    wins = windows.resolve(ask, cfg, now)
    days = wins["days"]
    stored = storage.load_doc(account, score_ledger.LEDGER_DOC, None)
    if not isinstance(stored, dict):
        return _empty(account, cfg, "calibrating", "no_history", wins)
    ledger = score_ledger.clean_ledger(stored, now)
    if (now - ledger["first_seen"]) / 3600.0 < engine.settings(raw_config)["calibrating_hours"]:
        return _empty(account, cfg, "calibrating", "watched_briefly", wins)
    problem = _baseline_problem(wins, ledger, now, cfg)
    since = score_ledger.hour_key(min(wins["now"][0], wins["base"][0]))
    snapshots = storage.load_score_snapshots(account, since=since) if hasattr(storage, "load_score_snapshots") else []
    side_now = metrics.compute(ledger, snapshots, wins["now"], days, cfg, zone)
    side_base = None if problem else metrics.compute(ledger, snapshots, wins["base"], days, cfg, zone)
    table = {name: _entry(name, side_now, side_base, problem is None) for name in metrics.METRICS}
    ok = sum(1 for entry in table.values() if entry["state"] == "ok")
    truncated = isinstance(ledger.get("truncated_at"), (int, float)) and ledger["truncated_at"] > wins["base"][0]
    reasons = ([problem] if problem else []) + (["truncated"] if truncated else [])
    out = {"schema": SCHEMA, "account": account, "enabled": True, "state": "compared" if not problem else "baseline_unavailable", "windows": _windows_view(wins), "days": days, "baseline": wins["baseline"],
           "workdays": cfg["workdays"] if days != "all" else None, "metrics": table, "coverage": round(ok / len(table), 3),
           "data_quality": {"runs_now": side_now["samples"]["runs"], "runs_base": side_base["samples"]["runs"] if side_base else None, "min_runs": cfg["min_runs_per_window"], "truncated": truncated, "reasons": reasons},
           "changes": changes.build(ledger, wins, days, cfg, zone) if not problem else {"worse": [], "better": [], "new_failures": [], "resolved_failures": [], "reason": problem},
           "alerts": {"opened_now": side_now["samples"]["alerts_opened"], "open_at_end_now": side_now["samples"]["alerts_open_at_end"],
                      "opened_base": side_base["samples"]["alerts_opened"] if side_base else None, "open_at_end_base": side_base["samples"]["alerts_open_at_end"] if side_base else None}}
    if problem:
        out["baseline_unavailable"] = {"reason": problem}
    return out


def _long_window(ask, cfg):
    """The length in days of a request for the last N days longer than `compare.progressive_days`, else None (a request with `from` / `to` is never split)."""
    if not cfg["progressive"] or ask.get("from") or ask.get("to"):
        return None
    text = str(ask.get("window") or "").strip().lower().rstrip("d")
    length = int(text) if text.isdigit() else cfg["default_window_days"]
    return length if length > cfg["progressive_days"] else None


_COMPLETING = set()


def _finish_in_background(storage, account, raw_config, ask, zone, key):
    """Computes the whole window on a thread and keeps it in the cache; the next request takes it from there."""
    if key in _COMPLETING:
        return
    _COMPLETING.add(key)

    def work():
        try:
            full = _compute(storage, account, raw_config, ask, time.time(), zone)
            if len(_CACHE) >= MAX_CACHE:
                _CACHE.pop(next(iter(_CACHE)))
            _CACHE[key] = (time.monotonic(), copy.deepcopy(full))
        except Exception:   # noqa: BLE001 - the first answer was already given; a failure here only means the next request computes it
            pass
        finally:
            _COMPLETING.discard(key)
    threading.Thread(target=work, daemon=True, name="compare-complete").start()


def build(storage, account, raw_config, ask=None, now=None, zone=None):
    """The answer for `ask` (window, from, to, baseline, base_from, base_to, days). Raises windows.WindowError for a request that makes no sense. Cached for `compare.cache_seconds` unless `now` is given.
    With `compare.progressive` on, a window longer than `compare.progressive_days` is answered at once with its last days (marked `partial`) while the whole one is finished in the background."""
    cfg = config.settings(raw_config)
    if now is None and cfg["enabled"] and _long_window(ask or {}, cfg):
        ask = ask or {}
        full_key = (id(storage), account, tuple(sorted((str(k), str(v)) for k, v in ask.items())), json.dumps(cfg, sort_keys=True))
        hit = _CACHE.get(full_key)
        if hit and time.monotonic() - hit[0] < max(cfg["cache_seconds"], 60):
            return copy.deepcopy(hit[1])
        requested = _long_window(ask, cfg)
        first = _compute(storage, account, raw_config, {**ask, "window": f"{cfg['progressive_days']}d"}, time.time(), zone)
        first["partial"] = {"requested_days": requested, "shown_days": cfg["progressive_days"], "completing": True}
        _finish_in_background(storage, account, raw_config, ask, zone, full_key)
        return first
    key = None
    if now is None and cfg["cache_seconds"] > 0 and cfg["enabled"]:
        key = (id(storage), account, tuple(sorted((str(k), str(v)) for k, v in (ask or {}).items())), json.dumps(cfg, sort_keys=True))
        hit = _CACHE.get(key)
        if hit and time.monotonic() - hit[0] < cfg["cache_seconds"]:
            return copy.deepcopy(hit[1])
    answer = _compute(storage, account, raw_config, ask or {}, time.time() if now is None else now, zone)
    if key is not None:
        if len(_CACHE) >= MAX_CACHE:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (time.monotonic(), copy.deepcopy(answer))
    return answer


def off_answer(account):
    """The answer of a monitor that holds no history (--demo)."""
    return _empty(account, config.settings({}), "off", "off")


def clear_cache():
    _CACHE.clear()


def rows(answer):
    """One flat row per figure: the shape of the csv and ndjson exports."""
    return [{"metric": name, "now": entry["now"], "base": entry["base"], "delta": entry["delta"], "direction": entry["direction"], "state": entry["state"]} for name, entry in (answer.get("metrics") or {}).items()]


def render(answer, fmt):
    """(content type, text) of the answer as `ndjson` or `csv`; `json` is the answer itself and is not rendered here."""
    if fmt == "ndjson":
        return "application/x-ndjson", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows(answer))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["metric", "now", "base", "delta", "direction", "state"], lineterminator="\n")
    writer.writeheader()
    for row in rows(answer):
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return "text/csv", out.getvalue()
