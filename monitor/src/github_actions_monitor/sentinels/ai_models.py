# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The models of the AI provider, read live: the catalog, the table of data per model, the test of one model and the doctor that says why an AI does not answer.

Nothing here is a list of models in the code: the names and the figures come from the provider (`/models`, the equivalent of Anthropic, `/api/tags` of Ollama) or from the person; what neither says
stays "unknown" (never a figure that was made up). Everything is read only: the catalog is a GET with the key in a header (the key is read from the environment variable named in the settings and is
never stored or printed), the test sends a SYNTHETIC text (never data of a repository) and the AI never runs anything. The catalog is OFF for background use by default (`ai.catalog.enabled`); the
person asking for it (the button, the command `ai models`) is always allowed, inside a cap of requests per day.
"""
import difflib
import re
import time
import urllib.error
import urllib.request
from datetime import datetime

from github_actions_monitor import i18n
from github_actions_monitor.security import netguard
from github_actions_monitor.sentinels import sentinel_ai

CATALOG_DEFAULTS = {"enabled": False, "ttl_minutes": 360, "max_requests_per_day": 20, "fit_context": False}
MAX_MODELS = 2000
CONTEXT_KEYS = ("context_window", "context_length", "max_context_length", "max_input_tokens", "inputTokenLimit", "input_token_limit", "n_ctx")
FIELDS = ("context", "in_per_mtok", "out_per_mtok", "tools")
LIMIT_FIELDS = ("daily_limit", "cost_limit")
MODEL_ID = re.compile(r"^[A-Za-z0-9._:/@+-]{1,100}\Z")

# A SYNTHETIC failure for the test of a model: invented repository, invented log. Never data of a real repository.
SYNTHETIC = ("repository: example/demo-app\nworkflow: CI\njob: unit-tests\nstep: Run tests\n"
             "AssertionError: expected 3 but got 2 (tests/test_parser.py:41)\nProcess completed with exit code 1.")


def catalog_config(ai_cfg):
    """The `ai.catalog` block with its defaults and its limits (a wrong value falls back to the default)."""
    value = ai_cfg.get("catalog") if isinstance(ai_cfg.get("catalog"), dict) else {}
    out = dict(CATALOG_DEFAULTS)
    for key in ("enabled", "fit_context"):
        out[key] = value.get(key) is True
    for key, low, high in (("ttl_minutes", 5, 10080), ("max_requests_per_day", 1, 200)):
        try:
            out[key] = max(low, min(high, int(value.get(key, CATALOG_DEFAULTS[key]))))
        except (TypeError, ValueError):
            out[key] = CATALOG_DEFAULTS[key]
    return out


def _positive_int(value, high=10_000_000):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 0 < number <= high else None


def _price(value):
    """A price per token (a number or a text) to the price per million tokens, or None."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value) * 1_000_000
    except (TypeError, ValueError):
        return None
    return round(number, 6) if 0 <= number <= 1_000_000 else None


def info_of(entry):
    """What the provider says about one model, and nothing else: {context, in_per_mtok, out_per_mtok, tools} with None where it does not say."""
    context = None
    for key in CONTEXT_KEYS:
        context = context or _positive_int(entry.get(key))
    top = entry.get("top_provider")
    if context is None and isinstance(top, dict):
        context = _positive_int(top.get("context_length"))
    price_in = price_out = None
    pricing = entry.get("pricing")
    if isinstance(pricing, dict):
        price_in, price_out = _price(pricing.get("prompt") or pricing.get("input")), _price(pricing.get("completion") or pricing.get("output"))
    tools = None
    params, caps = entry.get("supported_parameters"), entry.get("capabilities")
    if isinstance(params, list):
        tools = "tools" in params
    elif isinstance(caps, list):
        tools = "tools" in caps or "function_calling" in caps
    elif isinstance(caps, dict):
        for key in ("tools", "function_calling", "tool_use"):
            value = caps.get(key)
            if isinstance(value, bool):
                tools = value
            elif isinstance(value, dict) and isinstance(value.get("supported"), bool):
                tools = value["supported"]
    return {"context": context, "in_per_mtok": price_in, "out_per_mtok": price_out, "tools": tools}


def provider_label(cfg):
    """How the table names a provider: `ollama`, `anthropic`, `copilot` or, for an OpenAI-style server, its host name (api.example.com, 127.0.0.1)."""
    if cfg["provider"] != "openai-compatible":
        return cfg["provider"]
    from urllib.parse import urlparse
    return (urlparse(cfg.get("base_url") or "").hostname or "openai-compatible").lower()


def key_of(cfg):
    """Which catalog this is: provider and address (the key of the environment never takes part)."""
    return "|".join((cfg["provider"], (cfg.get("ollama_url") if cfg["provider"] == "ollama" else cfg.get("base_url")) or ""))


def _normal(name, provider):
    name = str(name or "").strip()
    if name.startswith("models/"):
        name = name[7:]
    if provider == "ollama" and name and ":" not in name:
        name += ":latest"      # Ollama reads "llama3.2" as "llama3.2:latest"
    return name


def request_of(cfg):
    """(url, headers) of the list of models of the configured provider, or (None, reason). The key goes in a header only."""
    import os
    provider = cfg["provider"]
    if provider == "none":
        return None, i18n.t("ai.is_off")
    if provider == "copilot":
        return None, i18n.t("ai.cat_unsupported")
    if provider == "ollama":
        if not sentinel_ai._loopback(cfg["ollama_url"]):
            return None, i18n.t("ai.ollama_local")
        return cfg["ollama_url"].rstrip("/") + "/api/tags", {}
    if provider == "anthropic":
        problem = sentinel_ai.anthropic_problem(dict(cfg, model=cfg.get("model") or "x"))
        if problem:
            return None, problem
        return (cfg.get("base_url") or sentinel_ai.ANTHROPIC_URL).rstrip("/") + "/v1/models?limit=1000", {"x-api-key": os.environ[cfg["api_key_env"]], "anthropic-version": sentinel_ai.ANTHROPIC_VERSION}
    problem = sentinel_ai.compat_problem(dict(cfg, model=cfg.get("model") or "x"))
    if problem:
        return None, problem
    base = cfg["base_url"].rstrip("/")
    if base.endswith("/chat/completions"):
        base = base[:-len("/chat/completions")]
    key = os.environ.get(cfg.get("api_key_env") or "", "")
    return base + "/models", ({"Authorization": "Bearer " + key, "api-key": key} if key else {})


def _get_json(url, headers, timeout, use_proxy=False):
    request = urllib.request.Request(url, method="GET", headers=headers)
    with netguard.open_plain(request, timeout=timeout, use_proxy=use_proxy) as answer:
        import json
        return json.loads(answer.read(4_000_000).decode("utf-8", "replace"))


def parse(provider, body):
    """[{id, context, in_per_mtok, out_per_mtok, tools}] from the answer of a provider, whatever its shape (a list, `data`, `models`)."""
    rows = body if isinstance(body, list) else ((body.get("data") if isinstance(body, dict) else None) or (body.get("models") if isinstance(body, dict) else None) or [])
    found, seen = [], set()
    for entry in rows if isinstance(rows, list) else []:
        if isinstance(entry, str):
            entry = {"id": entry}
        if not isinstance(entry, dict):
            continue
        name = _normal(entry.get("id") or entry.get("name") or entry.get("model"), provider)
        if not MODEL_ID.match(name) or name in seen:
            continue
        seen.add(name)
        found.append({"id": name, **info_of(entry)})
        if len(found) >= MAX_MODELS:
            break
    return sorted(found, key=lambda m: m["id"])


def _count_request(cfg_cat, store):
    """True when one more request to a list of models fits today's cap (and counts it)."""
    today = store.today()
    with store.lock:
        usage = store.data.setdefault("catalog_requests", {})
        if usage.get("day") != today:
            usage.clear()
            usage.update({"day": today, "n": 0})
        if usage["n"] >= cfg_cat["max_requests_per_day"]:
            return False
        usage["n"] += 1
        return True


def cached(cfg, store):
    """The catalog kept for this provider, or None: {at, models, fresh}. Never touches the network."""
    entry = (store.data.get("catalog") or {}).get(key_of(cfg))
    if not isinstance(entry, dict) or not isinstance(entry.get("models"), list):
        return None
    ttl = catalog_config(cfg)["ttl_minutes"] * 60
    return {"at": entry.get("at", 0), "models": entry["models"], "fresh": time.time() - float(entry.get("at", 0) or 0) < ttl}


def fetch(cfg, store, getter=None, force=True):
    """Reads the list of models of the provider (a GET), keeps it and returns {ok, state, models, at, message}. `state`: fresh | cached | off | unsupported | capped | error.
    Inside the cap of requests per day (`ai.catalog.max_requests_per_day`) and the time to live (`ai.catalog.ttl_minutes`) unless `force`. Never raises."""
    base = {"ok": False, "state": "error", "models": [], "at": 0, "message": ""}
    have = cached(cfg, store)
    if have and have["fresh"] and not force:
        return {**base, "ok": True, "state": "cached", "models": have["models"], "at": have["at"]}
    url, headers = request_of(cfg)
    if url is None:
        state = "off" if cfg["provider"] == "none" else ("unsupported" if cfg["provider"] == "copilot" else "error")
        return {**base, "state": state, "message": headers, "models": have["models"] if have else [], "at": have["at"] if have else 0}
    if not _count_request(catalog_config(cfg), store):
        return {**base, "state": "capped", "message": i18n.t("ai.cat_capped", n=catalog_config(cfg)["max_requests_per_day"]),
                "models": have["models"] if have else [], "at": have["at"] if have else 0}
    try:
        body = (getter or _get_json)(url, headers, cfg["timeout_seconds"], cfg.get("use_proxy") is True)
        models = parse(cfg["provider"], body)
    except urllib.error.HTTPError as error:
        return {**base, "message": i18n.t("ai.cat_fail", why=i18n.t("ai.provider_answered", code=error.code)), "code": error.code, "models": have["models"] if have else [], "at": have["at"] if have else 0}
    except Exception as error:   # noqa: BLE001 - a list that cannot be read is a state, not a crash
        return {**base, "message": i18n.t("ai.cat_fail", why=sentinel_ai.sanitize_text(str(error), 160, keep="head")), "models": have["models"] if have else [], "at": have["at"] if have else 0}
    now = time.time()
    with store.lock:
        store.data.setdefault("catalog", {})[key_of(cfg)] = {"at": now, "models": models}
        if len(store.data["catalog"]) > 12:      # a few providers at most; the oldest go
            for old in sorted(store.data["catalog"], key=lambda k: store.data["catalog"][k].get("at", 0))[:len(store.data["catalog"]) - 12]:
                store.data["catalog"].pop(old, None)
        for entry in models:      # what the provider says about each model fills the table (never over what the person wrote)
            remember_provider_data(store, cfg, entry)
        store.save()
    return {**base, "ok": True, "state": "fresh", "models": models, "at": now}


# ---------- validation ----------

def check_model(cfg, models, model=None):
    """{state: exists | missing | unknown, similar: [..]}: does the name exist in the list? `models` None/empty = it could not be checked (unknown), never "missing"."""
    name = _normal(model if model is not None else sentinel_ai.model_of(cfg), cfg["provider"])
    if not name:
        return {"state": "unknown", "similar": []}
    if not models:
        return {"state": "unknown", "similar": []}
    ids = [m["id"] if isinstance(m, dict) else str(m) for m in models]
    if name in ids:
        return {"state": "exists", "similar": []}
    return {"state": "missing", "similar": difflib.get_close_matches(name, ids, n=5, cutoff=0.5)}


def describe(cfg, check):
    model = sentinel_ai.model_of(cfg)
    if check["state"] == "exists":
        return i18n.t("ai.model_exists")
    if check["state"] == "missing":
        text = i18n.t("ai.model_missing", model=model)
        return text + (" " + i18n.t("ai.model_similar", list=", ".join(check["similar"])) if check["similar"] else "")
    return i18n.t("ai.model_unknown")


def state_of_configured(cfg, store):
    """The state of the configured model against the CATALOG KEPT (no network): {state, message}. `off` while `ai.catalog.enabled` is off or the provider is none."""
    if cfg["provider"] == "none" or not catalog_config(cfg)["enabled"]:
        return {"state": "off", "message": ""}
    have = cached(cfg, store)
    check = check_model(cfg, have["models"] if have else None)
    return {"state": check["state"], "message": describe(cfg, check), "similar": check["similar"]}


# ---------- the table of data per model ----------

def _table(store):
    table = store.data.get("model_data")
    if not isinstance(table, dict):
        table = store.data["model_data"] = {}
    return table


def remember_provider_data(store, cfg, entry):
    """Writes into the table what the provider said about a model; a field the person wrote by hand is never overwritten, and a field the provider does not say stays as it was (unknown)."""
    with store.lock:
        row = _table(store).setdefault(f"{provider_label(cfg)}/{entry['id']}", {})
        manual = row.setdefault("manual", {})
        provided = row.setdefault("provider", {})
        for field in FIELDS:
            if entry.get(field) is not None and field not in manual:
                provided[field] = entry[field]
        if not provided and not manual and len(row) <= 2 and not row.get("tested"):
            _table(store).pop(f"{provider_label(cfg)}/{entry['id']}", None)


def data_of(store, provider, model):      # `provider` is the label of provider_label()
    """The row of the table for a model: each field with its value (or None = unknown) and where it came from: `manual`, `provider` or `unknown`."""
    row = _table(store).get(f"{provider}/{_normal(model, provider)}") or _table(store).get(f"{provider}/{model}") or {}
    out = {}
    for field in FIELDS + LIMIT_FIELDS:
        if field in (row.get("manual") or {}):
            out[field], out[field + "_source"] = row["manual"][field], "manual"
        elif field in (row.get("provider") or {}) and field in FIELDS:
            out[field], out[field + "_source"] = row["provider"][field], "provider"
        else:
            out[field], out[field + "_source"] = None, "unknown"
    out["tested"] = row.get("tested")
    return out


def set_manual(store, provider, model, values):
    """Saves what the person typed for a model. A field set to None/"" goes back to unknown. Returns (ok, error_text)."""
    if not MODEL_ID.match(str(model or "")):
        return False, i18n.t("err.bad_value")
    clean = {}
    for field, raw in (values or {}).items():
        if field not in FIELDS + LIMIT_FIELDS:
            continue
        if raw in (None, ""):
            clean[field] = None
        elif field == "tools":
            if not isinstance(raw, bool):
                return False, i18n.t("err.bad_value")
            clean[field] = raw
        elif field in ("context", "daily_limit"):
            number = _positive_int(raw, 100_000_000)
            if number is None:
                return False, i18n.t("err.bad_value")
            clean[field] = number
        else:
            try:
                number = float(raw)
            except (TypeError, ValueError):
                return False, i18n.t("err.bad_value")
            if isinstance(raw, bool) or not 0 <= number <= 1_000_000:
                return False, i18n.t("err.bad_value")
            clean[field] = number
    with store.lock:
        row = _table(store).setdefault(f"{provider}/{model}", {})
        manual = row.setdefault("manual", {})
        for field, value in clean.items():
            if value is None:
                manual.pop(field, None)
            else:
                manual[field] = value
        store.save()
    return True, ""


def table(store):
    """Every model that has a row, with its data and where each figure came from (for the page and for `ai models`)."""
    rows = []
    for key in sorted(_table(store)):
        provider, _, model = key.partition("/")
        rows.append({"provider": provider, "model": model, **data_of(store, provider, model)})
    return rows


def fit_chars(cfg, store):
    """`max_input_chars` fitted to the context window when it is known and `ai.catalog.fit_context` is on: about half of the window in characters (three per token), never more than the configured value."""
    if not catalog_config(cfg)["fit_context"]:
        return cfg["max_input_chars"]
    context = data_of(store, provider_label(cfg), sentinel_ai.model_of(cfg)).get("context")
    if not context:
        return cfg["max_input_chars"]
    return max(500, min(cfg["max_input_chars"], int(context) * 3 // 2))


# ---------- cost ----------

def cost_of(store, provider, model, tokens_in, tokens_out):
    """Estimated cost in the units of the prices of the table, or None when a price is unknown (never a made up figure)."""
    row = data_of(store, provider, model)
    if row["in_per_mtok"] is None or row["out_per_mtok"] is None or tokens_in is None or tokens_out is None:
        return None
    return round(tokens_in / 1_000_000 * row["in_per_mtok"] + tokens_out / 1_000_000 * row["out_per_mtok"], 6)


# ---------- the test of one model ----------

def local_now():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")


def probe(cfg, store, transport=None):
    """Asks the model about the SYNTHETIC failure and measures: {ok, ms, tokens_in, tokens_out, tokens_estimated, cost, answer, tested_at}. The result is kept in the table as `tested`
    (provider/model and local date). It counts as one call of the daily cap. Never raises."""
    result = sentinel_ai.run_call(cfg, store, "build", SYNTHETIC, transport=transport)
    provider, model = provider_label(cfg), sentinel_ai.model_of(cfg)
    at = local_now()
    out = {"ok": result.get("ok", False), "provider": provider, "model": model, "ms": result.get("ms"), "tokens_in": result.get("tokens_in"), "tokens_out": result.get("tokens_out"),
           "tokens_estimated": result.get("tokens_estimated", True), "cost": result.get("cost"), "answer": result.get("text", "")[:600], "error": result.get("error", ""), "tested_at": at}
    if cfg["provider"] != "none" and MODEL_ID.match(model or ""):
        with store.lock:
            row = _table(store).setdefault(f"{provider}/{model}", {})
            row["tested"] = {"ok": out["ok"], "at": at, "ms": out["ms"]}
            store.save()
    return out


# ---------- the doctor ----------

def doctor(cfg, store, getter=None, transport=None, live=True):
    """Why an AI does not answer, in order: provider, address, key (only whether the variable is set), model name, existence in the catalog, the network, the cap. Never prints a key.
    Returns {ok, checks: [{id, ok, text}], verdict}. `live` makes one request to the list of models of the provider."""
    import os
    checks = []

    def add(ident, ok, text):
        checks.append({"id": ident, "ok": ok, "text": text})

    if cfg["provider"] == "none":
        add("provider", False, i18n.t("ai.doc_provider_none"))
        return {"ok": False, "checks": checks, "verdict": "provider"}
    add("provider", True, i18n.t("ai.doc_provider", provider=cfg["provider"]))
    stop = None
    if cfg["provider"] in ("openai-compatible", "anthropic"):
        url = cfg.get("base_url") or (sentinel_ai.ANTHROPIC_URL if cfg["provider"] == "anthropic" else "")
        add("address", bool(url), i18n.t("ai.doc_address_ok") if url else i18n.t("ai.need_base_url"))
        env = cfg.get("api_key_env") or ""
        need_key = not (cfg["provider"] == "openai-compatible" and sentinel_ai._loopback(cfg.get("base_url") or "") and not env)
        if need_key:
            if not sentinel_ai.ENV_NAME.match(env):
                add("key", False, i18n.t("ai.need_env_name"))
            elif not os.environ.get(env):
                add("key", False, i18n.t("ai.env_not_set", name=env))
            else:
                add("key", True, i18n.t("ai.doc_key_ok", name=env))
        else:
            add("key", True, i18n.t("ai.doc_key_none"))
    elif cfg["provider"] == "ollama":
        ok, why = sentinel_ai.ollama_available(cfg)
        add("address", ok, i18n.t("ai.ollama_ok") if ok else why)
    elif cfg["provider"] == "copilot":
        problem = sentinel_ai.copilot_problem(cfg)
        add("address", problem is None, problem or i18n.t("ai.copilot_ready"))
    if any(not c["ok"] for c in checks):
        stop = next(c["id"] for c in checks if not c["ok"])
    model = sentinel_ai.model_of(cfg)
    add("model", bool(model), i18n.t("ai.doc_model", model=model) if model else i18n.t("ai.need_model"))
    if not model and stop is None:
        stop = "model"
    if stop is None and live and cfg["provider"] != "copilot":
        listing = fetch(cfg, store, getter=getter, force=True)
        if listing["ok"]:
            add("network", True, i18n.t("ai.doc_network_ok", n=len(listing["models"])))
            check = check_model(cfg, listing["models"])
            add("exists", check["state"] != "missing", describe(cfg, check))
            if check["state"] == "missing":
                stop = "exists"
        else:
            code = listing.get("code")
            text = {401: i18n.t("ai.doc_auth"), 403: i18n.t("ai.doc_auth"), 404: i18n.t("ai.doc_not_found"), 429: i18n.t("ai.doc_quota")}.get(code) or listing["message"]
            add("network", False, text)
            stop = "network"
    elif stop is None:
        have = cached(cfg, store)
        if have:
            check = check_model(cfg, have["models"])
            add("exists", check["state"] != "missing", describe(cfg, check))
            if check["state"] == "missing":
                stop = "exists"
    used = store.used_today()
    add("budget", used < cfg["daily_limit"], i18n.t("ai.doc_budget", used=used, limit=cfg["daily_limit"]))
    if stop is None and used >= cfg["daily_limit"]:
        stop = "budget"
    last = data_of(store, provider_label(cfg), model).get("tested") if model else None
    if last:
        add("tested", bool(last.get("ok")), i18n.t("ai.doc_tested_ok" if last.get("ok") else "ai.doc_tested_fail", at=last.get("at", "")))
    return {"ok": stop is None, "checks": checks, "verdict": stop or "ok"}


# ---------- the provider of one test, one task or one fallback ----------

def resolve(cfg, ref, model=None):
    """The settings for another provider/model: `ref` is a preset id (`openai`, `ollama`...) or a protocol (`ollama`, `anthropic`, `openai-compatible`, `copilot`) and `model` the name.
    Same protocol as the general settings = they are inherited (address, variable of the key). Returns (settings, None) or (None, reason). Nothing here reads a key."""
    from github_actions_monitor.sentinels import ai_presets
    out = dict(cfg)
    ref = str(ref or "").strip()
    if model is not None:
        out["model"] = str(model).strip()
    if not ref or ref == cfg["provider"]:
        return out, None
    preset = next((p for p in ai_presets.load() if p["id"] == ref), None)
    if preset is not None:
        out.update({"provider": preset["provider"], "base_url": preset.get("base_url", ""), "api_key_env": preset.get("api_key_env", ""),
                    "ollama_url": preset.get("ollama_url") or sentinel_ai.AI_DEFAULTS["ollama_url"]})
        if model is None:
            out["model"] = ""
        return out, None
    if ref in ("ollama", "anthropic"):
        out.update({"provider": ref, "base_url": "", "api_key_env": cfg.get("api_key_env") if ref == "anthropic" else "", "ollama_url": sentinel_ai.AI_DEFAULTS["ollama_url"]})
        if model is None:
            out["model"] = ""
        return out, None
    return None, i18n.t("ai.unknown_provider", name=ref[:40])


def listing(cfg, store):
    """The document of `GET /api/ai/models`: the configured provider, the list kept (no network), the check of the configured model and the table of data. Read only."""
    have = cached(cfg, store)
    label = provider_label(cfg)
    models = []
    for entry in (have["models"] if have else []):
        models.append({"id": entry["id"], **{k: data_of(store, label, entry["id"])[k] for k in FIELDS}})
    check = check_model(cfg, have["models"] if have else None)
    return {"ok": True, "provider": cfg["provider"], "label": label, "model": sentinel_ai.model_of(cfg), "enabled": catalog_config(cfg)["enabled"],
            "catalog": {"state": "cached" if have else "none", "fresh": bool(have and have["fresh"]), "at": have["at"] if have else 0, "count": len(models)},
            "models": models, "check": {**check, "message": describe(cfg, check) if cfg["provider"] != "none" else i18n.t("ai.is_off")}, "table": table(store)}


def handle_post(path, request, cfg, store):
    """The four local-only POST routes: models/refresh, models/test, models/data, doctor. Returns a JSON-able dict. `request` may carry `provider` (preset or protocol) and `model`."""
    chosen, why = resolve(cfg, request.get("provider"), request.get("model") if request.get("model") is not None else None)
    if chosen is None:
        return {"ok": False, "error": why}
    if path == "/api/ai/models/refresh":
        answer = fetch(chosen, store, force=True)
        check = check_model(chosen, answer["models"]) if answer["ok"] else {"state": "unknown", "similar": []}
        return {"ok": answer["ok"], "state": answer["state"], "message": answer["message"], "count": len(answer["models"]), "at": answer["at"], "check": {**check, "message": describe(chosen, check)}}
    if path == "/api/ai/models/test":
        if chosen["provider"] == "none":
            return {"ok": False, "error": i18n.t("ai.is_off")}
        return probe(chosen, store)
    if path == "/api/ai/models/data":
        ok, error = set_manual(store, request.get("label") or provider_label(chosen), str(request.get("model") or ""), request.get("values") if isinstance(request.get("values"), dict) else {})
        return {"ok": ok, "error": error}
    if path == "/api/ai/doctor":
        return doctor(chosen, store)
    return {"ok": False, "error": "path"}
