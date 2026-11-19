# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Which model answers, and what happens when it cannot: a model per task, a chain of fallbacks and a budget per model.

Everything here is OFF until you write it in the settings, and then it only chooses among providers YOU named. With nothing configured the list of candidates is the one model of
`ai.provider` / `ai.model`, exactly as before.

  * `ai.tasks.<task>.*` (build, codeql, report, diagnose, alert): another provider/model and its own limits for that kind of question. A task that names no model uses the general one.
  * `ai.fallback`: an ordered list `provider=model, provider=model` tried when the main model fails (any error, a refusal of the key, a model that does not exist, a quota error, a slow answer
    when `ai.fallback_after_seconds` is set) or has been retired from the catalog. `ai.fallback_max_attempts` caps the whole chain; there is no loop and a cached answer costs nothing.
  * Budgets: calls per model per day (`ai.model_daily_limit`, or the figure typed for a model in the table), estimated cost per model and in total (only when the prices are known), on top of the
    general `ai.daily_limit`. A model whose budget is spent is skipped: the next one answers, or nobody does. A limit is never jumped.
The first failure of the main model is written down (log and the brief of the AIs) with its reason.
"""
import logging
import re
import threading
import time
from datetime import datetime, timezone

from github_actions_monitor import i18n
from github_actions_monitor.sentinels import ai_models, sentinel_ai

LOG = logging.getLogger("github_actions_monitor.ai")
LOG.addHandler(logging.NullHandler())
TASKS = ("build", "codeql", "report", "diagnose", "alert")
KIND_TASK = {"build": "build", "codeql": "codeql", "report": "report", "release_notes": "report", "ask": "diagnose"}
TASK_LIMITS = ("max_input_chars", "max_output_chars", "timeout_seconds")
REF_RE = re.compile(r"^[A-Za-z0-9-]{1,40}\Z")
LOCK = threading.RLock()
STATE = {"failovers": []}      # the last failures of a main model, for the brief (the store keeps the same list for the page)
MAX_FAILOVERS = 30
BOUNDS = {"max_input_chars": (500, 20000), "max_output_chars": (200, 8000), "timeout_seconds": (5, 300)}


def task_of(kind, task=None):
    return task if task in TASKS else KIND_TASK.get(kind, "diagnose")


def classify(error):
    """Why a call failed, in one word: auth (401/403), model_not_found (404), quota (429), slow, config or error. Only a word: the text of the error is not kept."""
    code = getattr(error, "code", None)
    if code in (401, 403):
        return "auth"
    if code == 404:
        return "model_not_found"
    if code == 429:
        return "quota"
    text = str(error).lower()
    if isinstance(error, TimeoutError) or "timed out" in text or "timeout" in text or "did not answer in time" in text:
        return "slow"
    if "environment variable" in text or "base_url" in text or "model (model)" in text:
        return "config"
    return "error"


def parse_fallback(value):
    """[(ref, model)] from `ai.fallback`: a text `ref=model, ref=model` or a list of such texts or of {provider, model}. A wrong item is dropped, never guessed."""
    if isinstance(value, str):
        items = [p.strip() for p in value.split(",")]
    elif isinstance(value, list):
        items = value
    else:
        items = []
    out = []
    for item in items:
        if isinstance(item, dict):
            ref, model = str(item.get("provider") or ""), str(item.get("model") or "")
        elif isinstance(item, str) and "=" in item:
            ref, _, model = item.partition("=")
        else:
            continue
        ref, model = ref.strip(), model.strip()
        if REF_RE.match(ref) and ai_models.MODEL_ID.match(model):
            out.append((ref, model))
    return out[:5]


def task_settings(cfg, task):
    value = (cfg.get("tasks") or {}).get(task) if isinstance(cfg.get("tasks"), dict) else None
    return value if isinstance(value, dict) else {}


def label_of(cfg):
    return f"{ai_models.provider_label(cfg)}/{sentinel_ai.model_of(cfg)}"


def task_cfg(cfg, task):
    """The settings for one task: the general ones with the limits of the task and, if the task names a model, its provider/model. Returns (settings, role) where role is `task` or `general`."""
    mine = task_settings(cfg, task)
    base = dict(cfg)
    for key in TASK_LIMITS:
        low, high = BOUNDS[key]
        try:
            number = int(mine.get(key) or 0)
        except (TypeError, ValueError):
            number = 0
        if number:
            base[key] = max(low, min(high, number))
    model = str(mine.get("model") or "").strip()
    ref = str(mine.get("provider") or "").strip()
    if not model or not ai_models.MODEL_ID.match(model) or (ref and not REF_RE.match(ref)):
        return base, "general"
    chosen, _ = ai_models.resolve(base, ref, model)
    return (chosen, "task") if chosen is not None else (base, "general")


def candidates(cfg, kind, task=None):
    """[{cfg, label, role}]: the model of the task first, then the fallbacks in order, at most `ai.fallback_max_attempts` and without repeating one."""
    first, role = task_cfg(cfg, task_of(kind, task))
    chain = [{"cfg": first, "label": label_of(first), "role": role}]
    try:
        limit = max(1, min(5, int(cfg.get("fallback_max_attempts", 3))))
    except (TypeError, ValueError):
        limit = 3
    for ref, model in parse_fallback(cfg.get("fallback")):
        if len(chain) >= limit:
            break
        other, why = ai_models.resolve(first, ref, model)
        if other is None or other["provider"] == "none":
            continue
        entry = {"cfg": other, "label": label_of(other), "role": "fallback"}
        if is_cloud(other) and not _allowed_cloud(cfg, ref, other):      # a provider on the internet receives the text of a build only if the person wrote its name
            entry["blocked"] = "not_allowed"
        if all(entry["label"] != done["label"] for done in chain):
            chain.append(entry)
    return chain


def is_cloud(cfg):
    """True when the provider is not on this computer (anthropic, copilot, and an address that is not 127.0.0.1 / localhost / ::1)."""
    if cfg.get("provider") in ("anthropic", "copilot"):
        return True
    if cfg.get("provider") == "ollama":
        return not sentinel_ai._loopback(cfg.get("ollama_url") or "")
    if cfg.get("provider") == "openai-compatible":
        return not sentinel_ai._loopback(cfg.get("base_url") or "")
    return False


def _allowed_cloud(cfg, ref, other):
    allowed = cfg.get("fallback_cloud_allowed")
    names = {str(x).strip().lower() for x in (allowed if isinstance(allowed, list) else [])}
    return bool(names & {str(ref).strip().lower(), ai_models.provider_label(other).lower(), str(other.get("provider")).lower()})


CLOUD_HOOKS = []      # functions (from_label, to_label) called when the chain goes from this computer to the internet: the log of actions and the notice are registered by the monitor


def cloud_switch(first, used):
    """Writes down that the chain went from a model on this computer to one on the internet: log of actions, the log of the program and the hooks (the notice). Never raises."""
    LOG.warning("ai chain went from %s (this computer) to %s (internet)", first, used)
    try:
        from github_actions_monitor.security import audit_log
        audit_log.record({}, "ai.cloud_fallback", target=used[:100], details={"from": first[:100], "to": used[:100]}, force=True)
    except Exception:   # noqa: BLE001
        pass
    for hook in list(CLOUD_HOOKS):
        try:
            hook(first, used)
        except Exception:   # noqa: BLE001
            pass


# ---------- the budget ----------

def _usage(store):
    today = store.today()
    usage = store.data.get("usage")
    if not isinstance(usage, dict) or usage.get("day") != today:
        usage = store.data["usage"] = {"day": today, "models": {}, "cost": 0.0}
    usage.setdefault("models", {})
    usage.setdefault("cost", 0.0)
    return usage


def _number(value, cast=float):
    try:
        return cast(value) if value else 0
    except (TypeError, ValueError):
        return 0


def limits_of(cfg, store):
    """(calls per day, cost per day) allowed for the model of `cfg`: what is typed in the table wins over the general settings; 0 = no limit."""
    row = ai_models.data_of(store, ai_models.provider_label(cfg), sentinel_ai.model_of(cfg))
    calls = row.get("daily_limit") or _number(cfg.get("model_daily_limit"), int)
    cost = row.get("cost_limit") or _number(cfg.get("model_cost_limit_daily"))
    return int(calls or 0), float(cost or 0)


def budget_block(cfg, store):
    """Why this model may not be called now, or None: `model_calls` (its calls of the day are spent), `model_cost` (its estimated cost) or `cost` (the total estimated cost)."""
    with store.lock, LOCK:
        usage = _usage(store)
        mine = usage["models"].get(label_of(cfg), {})
        calls_limit, cost_limit = limits_of(cfg, store)
        if calls_limit and mine.get("calls", 0) >= calls_limit:
            return "model_calls"
        if cost_limit and mine.get("cost", 0.0) >= cost_limit:
            return "model_cost"
        total = _number(cfg.get("cost_limit_daily"))
        if total and usage.get("cost", 0.0) >= total:
            return "cost"
    return None


def add_model_call(store, cfg):
    """Counts one call of this model today (before the call, like the general counter: a failing provider also spends its budget)."""
    with store.lock, LOCK:
        row = _usage(store)["models"].setdefault(label_of(cfg), {"calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0})
        row["calls"] = row.get("calls", 0) + 1


def add_model_usage(store, cfg, tokens_in, tokens_out, cost):
    with store.exclusive(), LOCK:
        usage = _usage(store)
        row = usage["models"].setdefault(label_of(cfg), {"calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0})
        row["tokens_in"] = row.get("tokens_in", 0) + min(max(int(tokens_in or 0), 0), sentinel_ai.MAX_REPORTED_TOKENS)
        row["tokens_out"] = row.get("tokens_out", 0) + min(max(int(tokens_out or 0), 0), sentinel_ai.MAX_REPORTED_TOKENS)
        if cost is not None:
            row["cost"] = round(row.get("cost", 0.0) + cost, 6)
            usage["cost"] = round(usage.get("cost", 0.0) + cost, 6)
        else:
            row["cost_unknown"] = row.get("cost_unknown", 0) + 1      # calls whose price is not known: the total cost is a lower bound


def retired(cfg, store):
    """True when the list kept for this provider (never fetched here) says the model is not there. Only with `ai.catalog.enabled`."""
    if not ai_models.catalog_config(cfg)["enabled"]:
        return False
    have = ai_models.cached(cfg, store)
    return bool(have) and ai_models.check_model(cfg, have["models"])["state"] == "missing"


def view(cfg, store):
    """The document of `GET /api/ai/budget`: calls and estimated cost today, in total and for each model, with the limits, and the last failures of a main model. Read only."""
    with store.lock, LOCK:
        usage = _usage(store)
        rows = []
        for label in sorted(usage["models"]):
            row = usage["models"][label]
            provider, _, model = label.partition("/")
            calls_limit, cost_limit = _number(cfg.get("model_daily_limit"), int), _number(cfg.get("model_cost_limit_daily"))
            table_row = ai_models.data_of(store, provider, model)
            calls_limit, cost_limit = table_row.get("daily_limit") or calls_limit, table_row.get("cost_limit") or cost_limit
            rows.append({"model": label, "calls": row.get("calls", 0), "calls_limit": calls_limit or None, "cost": row.get("cost", 0.0) if not row.get("cost_unknown") or row.get("cost") else None,
                         "cost_known": not row.get("cost_unknown"), "cost_limit": cost_limit or None, "tokens_in": row.get("tokens_in", 0), "tokens_out": row.get("tokens_out", 0)})
        return {"ok": True, "day": usage["day"], "calls": store.used_today(), "calls_limit": cfg["daily_limit"], "cost": usage.get("cost", 0.0),
                "cost_limit": _number(cfg.get("cost_limit_daily")) or None, "models": rows, "failovers": list(store.data.get("failovers") or [])[-10:]}


# ---------- the failures of the main model ----------

def note_failover(store, task, failed, reason, used):
    """Writes down that the main model of a task failed (reason in one word) and which one answered instead (or "" = nobody). Log, page and brief."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {"at": now, "task": task, "failed": failed, "reason": reason, "used": used}
    with store.lock, LOCK:
        rows = store.data.setdefault("failovers", [])
        rows.append(entry)
        del rows[:-MAX_FAILOVERS]
        STATE["failovers"] = list(rows)
        store.save()
    LOG.warning("ai model failed: task=%s model=%s reason=%s answered_by=%s", task, failed, reason, used or "nobody")


def brief_lines(now=None):
    """The lines for the brief of the AIs: the failures of a main model in the last 24 hours. Empty when nothing happened (the brief is then exactly the one of before)."""
    stamp = time.time() if now is None else now
    out = []
    for row in list(STATE["failovers"])[-3:]:
        try:
            when = datetime.strptime(row["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        except (KeyError, ValueError):
            continue
        if 0 <= stamp - when <= 86400:
            out.append(f"- AI: the main model {row['failed']} failed for {row['task']} ({row['reason']}); " + (f"{row['used']} answered instead." if row.get("used") else "nobody answered."))
    return ("\n## AI models\n" + "\n".join(out) + "\n") if out else ""


def reason_text(reason):
    return i18n.t("ai.chain_" + reason) if reason in ("model_calls", "model_cost", "cost", "retired", "not_allowed", "auth", "model_not_found", "quota", "slow", "config", "error", "no_text", "airgap") else reason
