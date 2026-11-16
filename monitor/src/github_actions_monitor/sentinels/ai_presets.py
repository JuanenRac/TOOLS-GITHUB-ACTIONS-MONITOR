# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Presets of AI providers: a versioned file of data (ai_presets.json) that fills the address, the name of the variable of the key and an example model in the AI settings.
None is active by default and a preset never holds a key: the key is read from the environment variable whose NAME is stored. Nothing is downloaded and no model weights are shipped."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

PATH = Path(__file__).with_name("ai_presets.json")
PROVIDERS = ("openai-compatible", "anthropic", "ollama")
ID_RE = re.compile(r"^[a-z0-9-]{2,24}\Z")
ENV_RE = re.compile(r"^([A-Z_][A-Z0-9_]{0,63})?\Z")
FIELDS = ("id", "name", "kind", "provider", "base_url", "ollama_url", "api_key_env", "models", "privacy", "checked", "tested", "note", "docs", "docs_url", "notes")
FORBIDDEN_ENV = re.compile(r"^(?:GH_TOKEN|GITHUB_TOKEN|GITHUB_PAT|PATH|HOME|USERPROFILE|SYSTEMROOT|TEMP|TMP|APPDATA|LOCALAPPDATA|PYTHONPATH|MONITOR_.*)\Z")      # the key of a provider is never one of these


def problems(data):
    """What is wrong with a document of presets (empty list = valid). Used by the tests and by the loader."""
    found, seen = [], set()
    for item in data.get("presets", []):
        pid = item.get("id", "?")
        if not ID_RE.match(str(pid)) or pid in seen:
            found.append(f"{pid}: bad or repeated id")
        seen.add(pid)
        if item.get("provider") not in PROVIDERS or item.get("kind") not in ("hosted", "local") or item.get("privacy") not in ("cloud", "local"):
            found.append(f"{pid}: bad provider, kind or privacy")
        if not ENV_RE.match(item.get("api_key_env", "")) or FORBIDDEN_ENV.match(item.get("api_key_env", "")):
            found.append(f"{pid}: api_key_env must be a NAME that is not a variable of the system or of the monitor")
        extra = sorted(set(item) - set(FIELDS))
        if extra:
            found.append(f"{pid}: unknown field(s) {', '.join(extra)}")      # a field that is not on the list is never served (an \"api_key\" would reach GET /api/ai/presets)
        from github_actions_monitor.app import settings_api      # the same expressions as the settings page: a preset cannot hold an address the page would refuse
        url = item.get("base_url", "")
        host = (urlparse(url).hostname or "")
        if not settings_api.AI_URL_RE.match(url) or "@" in url:
            found.append(f"{pid}: base_url is not an address the settings accept")
        if item.get("ollama_url") and not settings_api.OLLAMA_RE.match(item["ollama_url"]):
            found.append(f"{pid}: ollama_url must be this computer")
        if item.get("privacy") == "cloud" and (host in ("127.0.0.1", "localhost", "::1") or re.match(r"^(?:10\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2\d|3[01])\.)", host)):
            found.append(f"{pid}: a cloud preset cannot point to this computer or to a private address")
        if url and not (url.startswith("https://") or (url.startswith("http://") and host in ("127.0.0.1", "localhost", "::1"))):
            found.append(f"{pid}: base_url must be https or loopback")
        if item.get("privacy") == "local" and url and host not in ("127.0.0.1", "localhost", "::1"):
            found.append(f"{pid}: a local preset must point to this computer")
        if item.get("privacy") == "cloud" and item.get("kind") == "hosted" and item.get("provider") == "openai-compatible" and not url:
            found.append(f"{pid}: hosted preset without base_url")
        if not item.get("models") or not all(isinstance(m, str) and m for m in item["models"]):
            found.append(f"{pid}: no example model")
        if item.get("tested") not in (True, False) or item.get("checked") not in (True, False):
            found.append(f"{pid}: checked/tested must be booleans")
    return found


def load():
    """The list of presets (a copy). A damaged file gives an empty list: the settings keep working without presets."""
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [] if problems(data) else [dict(p) for p in data["presets"]]


def changes_for(preset_id, model=""):
    """The settings a preset fills in: {key: value}. The key is never part of it."""
    for item in load():
        if item["id"] == preset_id:
            out = {"ai.provider": item["provider"], "ai.base_url": item.get("base_url", ""), "ai.api_key_env": item.get("api_key_env", ""),
                   "ai.model": model or item["models"][0]}
            if item.get("ollama_url"):
                out["ai.ollama_url"] = item["ollama_url"]
            return out
    return None
