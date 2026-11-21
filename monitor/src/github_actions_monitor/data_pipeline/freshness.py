# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Fresh, stale and expired answers for the heavy queries, and a time ceiling for them.

A heavy query (the comparison of two periods, the optional reports) reads a lot of stored data. Its answer is kept in memory with the moment it was made and each request finds it in one of three states:

  fresh    younger than `cache.heavy_fresh_s`: served as it is, nothing is computed (a burst of requests costs one computation);
  stale    older than that but younger than `cache.heavy_fresh_s` + `cache.stale_serve_h` hours: served AT ONCE and marked with the headers `X-Monitor-Freshness: stale` and `X-Monitor-Age` while ONE computation
           refreshes it in the background, so the person is never made to wait for a figure that is only a little old and is never shown an old figure as if it were new;
  expired  older than that, or never made: computed now, and a copy that old is never served.

A computation has a ceiling, `analytics.query_timeout_s` (120 seconds by default): past it the request is answered `timeout` instead of waiting for ever and, if a copy that may still be served exists, that
copy is served marked stale. A thread cannot be killed, so a computation that outlives its ceiling is left to end on its own; no second one is started for the same key meanwhile (single flight), which
is what keeps a slow query from piling up. A failure of the computation is never kept as an answer. Nothing here calls GitHub.

`serve(key, build, cfg)` returns (state, value, age_seconds) with state in fresh | stale | timeout | error (an expired or missing copy is computed now and served as fresh; `STATS["expired"]` counts
those); `value` is the answer, or the exception for `error`, or None for `timeout`.
"""
import threading
import time

DEFAULTS = {"fresh_s": 5, "stale_serve_h": 1, "query_timeout_s": 120}
BOUNDS = {"fresh_s": (0, 3600), "stale_serve_h": (0, 168), "query_timeout_s": (5, 3600)}
STATES = ("fresh", "stale", "timeout", "error")
MAX_KEYS = 200

_LOCK = threading.Lock()
_ENTRIES = {}      # key -> {"value", "at"}
_RUNNING = {}      # key -> threading.Event, set when the computation that was started for the key ends
STATS = {"fresh": 0, "stale": 0, "expired": 0, "timeout": 0, "error": 0, "refreshes": 0}


def _whole(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    """{"fresh_s", "stale_serve_h", "query_timeout_s"} from `cache.heavy_fresh_s`, `cache.stale_serve_h` and `analytics.query_timeout_s`; a value of the wrong type or out of range keeps the default."""
    cache = (config or {}).get("cache") if isinstance((config or {}).get("cache"), dict) else {}
    analytics = (config or {}).get("analytics") if isinstance((config or {}).get("analytics"), dict) else {}
    return {"fresh_s": _whole(cache.get("heavy_fresh_s"), *BOUNDS["fresh_s"], DEFAULTS["fresh_s"]),
            "stale_serve_h": _whole(cache.get("stale_serve_h"), *BOUNDS["stale_serve_h"], DEFAULTS["stale_serve_h"]),
            "query_timeout_s": _whole(analytics.get("query_timeout_s"), *BOUNDS["query_timeout_s"], DEFAULTS["query_timeout_s"])}


def state_of(age, cfg):
    """fresh | stale | expired for an answer `age` seconds old."""
    if age <= cfg["fresh_s"]:
        return "fresh"
    return "stale" if age <= cfg["fresh_s"] + cfg["stale_serve_h"] * 3600 else "expired"


def clear():
    with _LOCK:
        _ENTRIES.clear()


def _compute(key, build, timeout, clock):
    """Runs `build()` in a thread of its own and waits at most `timeout` seconds. ("ok", value) | ("timeout", None) | ("error", exception). Single flight: while a computation of the key is still running
    nothing else is started, the caller waits for that one (up to the ceiling)."""
    with _LOCK:
        done = _RUNNING.get(key)
        started_here = done is None
        if started_here:
            done = _RUNNING[key] = threading.Event()
    box = {}
    if started_here:
        def work():
            try:
                box["value"] = build()
            except BaseException as error:   # noqa: BLE001 - the caller decides what to do with it
                box["error"] = error
            finally:
                if "value" in box:
                    with _LOCK:
                        if len(_ENTRIES) >= MAX_KEYS and key not in _ENTRIES:
                            _ENTRIES.pop(min(_ENTRIES, key=lambda k: _ENTRIES[k]["at"]), None)
                        _ENTRIES[key] = {"value": box["value"], "at": clock()}      # kept even when the caller stopped waiting: the next request finds it
                with _LOCK:
                    _RUNNING.pop(key, None)
                done.set()
        threading.Thread(target=work, daemon=True, name="heavy-query").start()
    if not done.wait(timeout):
        return "timeout", None
    if started_here:
        if "error" in box:
            return "error", box["error"]
        return "ok", box["value"]
    with _LOCK:
        entry = _ENTRIES.get(key)
    return ("ok", entry["value"]) if entry else ("error", RuntimeError("the computation that was running did not give an answer"))


def serve(key, build, cfg, clock=time.time):
    """See the module. `build` is called without arguments, in another thread, at most once at a time for the same `key`."""
    now = clock()
    with _LOCK:
        entry = _ENTRIES.get(key)
    age = (now - entry["at"]) if entry else None
    if entry is not None:
        state = state_of(age, cfg)
        if state == "fresh":
            STATS["fresh"] += 1
            return "fresh", entry["value"], age
        if state == "stale":
            STATS["stale"] += 1
            with _LOCK:
                idle = key not in _RUNNING
            if idle:
                STATS["refreshes"] += 1
                _compute_in_background(key, build, cfg["query_timeout_s"], clock)
            return "stale", entry["value"], age
    outcome, value = _compute(key, build, cfg["query_timeout_s"], clock)
    if outcome == "ok":
        STATS["expired"] += 1      # the copy was expired or missing: it was computed now, so what is served is fresh
        return "fresh", value, 0.0
    STATS[outcome] += 1
    return outcome, value, age


def _compute_in_background(key, build, timeout, clock):
    threading.Thread(target=_compute, args=(key, build, timeout, clock), daemon=True, name="heavy-refresh").start()


def headers(state, age):
    """The headers that say an answer is not fresh: {"X-Monitor-Freshness": "stale", "X-Monitor-Age": "N"}, or {} for a fresh one. They are headers and not a key of the body so that the shape of the
    answer is the same whether it is fresh or not (a reader of the body, the frozen contract of the API and the page see no difference)."""
    if state == "fresh":
        return {}
    return {"X-Monitor-Freshness": state, "X-Monitor-Age": str(int(age or 0))}
