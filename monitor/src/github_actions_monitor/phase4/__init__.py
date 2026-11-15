# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The expansion modules of the complete and full editions, each one independent of the others and off by default:

  apiv1      the read API for clients (error envelope, cursor paging, compact payloads, versioning, the contract that tests hold it to)
  pwa        the manifest and the small service worker of the phone web app, and the `?view=` parameters
  plugins    manifests, trust and a loader that never lets a plugin stop the supervisor
  proposals  action proposals bound to a content hash, the policy engine, the executor (full edition only) and its append-only audit
  assistant  the local assistant: redaction before any prompt, providers, the air-gap rule and a read-only tool list
  scale      per-account queues with back-pressure, the monitor's own metrics and their Prometheus text

Nothing here talks to GitHub or to the network by itself: every outside call (a clock, a transport, a runner of actions) is given by the caller, so each module is tested without time or sockets.
`settings(config)` merges the `expansion` section of the configuration over the defaults (everything off, conservative values) and drops what has the wrong type or is out of range."""
import copy

DEFAULTS = {
    "api_v1": {"enabled": False, "bearer_clients": False, "default_limit": 50, "max_limit": 200, "compact_default_for_mobile": True, "cursor_ttl_seconds": 900, "gzip_min_bytes": 1024},
    "pwa": {"enabled": False, "name": "GitHub Actions Monitor", "short_name": "Actions", "cache_name": "gam-shell", "theme_color": "#0d1117", "background_color": "#0d1117"},
    "plugins": {"enabled": False, "allow_third_party": False, "directories": ["plugins"], "disabled_by_account": {}, "max_consecutive_failures": 3},
    "proposals": {"enabled": False, "ttl_seconds": 86400, "execute_enabled": False, "allowed_actions": ["rerun", "label", "comment"], "max_per_day": 20,
                  "allowed_roles": ["admin"], "hours": "", "merge_allowed": False, "audit_max_bytes": 5_000_000},
    "assistant": {"enabled": False, "airgapped": True, "provider": "", "endpoint": "", "model": "", "max_context_tokens": 3000, "log_prompts": False,
                  "allow_private_hosts": True, "timeout_seconds": 60},
    "scale": {"enabled": False, "queue_depth": 8, "per_account_parallel": 2, "tick_history": 50, "max_accounts": 20, "max_repos_per_install": 500},
}

BOUNDS = {
    ("api_v1", "default_limit"): (1, 1000), ("api_v1", "max_limit"): (1, 1000), ("api_v1", "cursor_ttl_seconds"): (30, 86400), ("api_v1", "gzip_min_bytes"): (0, 10_000_000),
    ("plugins", "max_consecutive_failures"): (1, 100),
    ("proposals", "ttl_seconds"): (60, 30 * 86400), ("proposals", "max_per_day"): (1, 10000), ("proposals", "audit_max_bytes"): (10_000, 500_000_000),
    ("assistant", "max_context_tokens"): (200, 32000), ("assistant", "timeout_seconds"): (1, 600),
    ("scale", "queue_depth"): (1, 1000), ("scale", "per_account_parallel"): (1, 16), ("scale", "tick_history"): (5, 1000), ("scale", "max_accounts"): (1, 1000),
    ("scale", "max_repos_per_install"): (1, 100000),
}


def _same_kind(default, value):
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, type(default))


def settings(config):
    """DEFAULTS with the user's `expansion` section merged in: unknown keys are dropped; a value of the wrong type or out of range keeps the default."""
    out = copy.deepcopy(DEFAULTS)
    user = (config or {}).get("expansion") if isinstance((config or {}).get("expansion"), dict) else {}
    for section, defaults in DEFAULTS.items():
        given = user.get(section) if isinstance(user.get(section), dict) else {}
        for key, default in defaults.items():
            if key not in given or not _same_kind(default, given[key]):
                continue
            value = given[key]
            low_high = BOUNDS.get((section, key))
            if low_high and not low_high[0] <= value <= low_high[1]:
                continue
            if isinstance(default, list) and not all(isinstance(x, str) for x in value):
                continue
            if isinstance(default, dict) and not all(isinstance(k, str) and isinstance(v, list) and all(isinstance(x, str) for x in v) for k, v in value.items()):
                continue
            out[section][key] = copy.deepcopy(value)
    api = out["api_v1"]
    if api["default_limit"] > api["max_limit"]:
        api["default_limit"] = api["max_limit"]
    return out
