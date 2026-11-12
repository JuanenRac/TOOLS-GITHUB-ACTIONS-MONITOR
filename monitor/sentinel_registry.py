# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The sentinels of the complete edition, by name (1.7.1): `ci` and, since 1.7.3, `collab` (off until `sentinels.collab.enabled` is true). The next ones are added to `_registry()` and nothing else of the monitor changes.

`config["sentinels"][name]["enabled"]` switches one on or off. Without it the old setting decides: the CI sentinel follows `sentinel.enabled` exactly as before. The options of
`config["sentinels"]["ci"]` are the same ones as `sentinel.*` (the old block keeps working; where both say something, the new block wins).

The lite edition does not load this module.
"""
import time

import sentinel_base


def _registry():
    import sentinel_ci
    import sentinel_collab
    return {sentinel_ci.SentinelCI.name: sentinel_ci.SentinelCI, sentinel_collab.SentinelCollab.name: sentinel_collab.SentinelCollab}


def section(config, name):
    value = ((config or {}).get("sentinels") or {}).get(name) if isinstance((config or {}).get("sentinels"), dict) else None
    return value if isinstance(value, dict) else {}


def is_enabled(config, name):
    """True when the sentinel `name` must run: the new block first, then the old one (only the CI sentinel has one)."""
    flag = section(config, name).get("enabled")
    if isinstance(flag, bool):
        return flag
    if name == "ci":
        old = (config or {}).get("sentinel")
        return not (isinstance(old, dict) and old.get("enabled") is False)
    return False


def effective_config(config, name):
    """The configuration a sentinel is built with: the old block of the CI sentinel under `sentinel`, overridden by what `sentinels.<name>` says."""
    merged = dict(config or {})
    if name == "ci":
        block = dict(merged.get("sentinel")) if isinstance(merged.get("sentinel"), dict) else {}
        block.update(section(config, name))
        block["enabled"] = is_enabled(config, name)
        merged["sentinel"] = block
    return merged


class SentinelRegistry:
    def __init__(self):
        self.items = {}

    @classmethod
    def build(cls, ctx, config):
        """One instance of every registered sentinel, switched on or off by the configuration."""
        registry = cls()
        for name, kind in _registry().items():
            registry.items[name] = kind(ctx, effective_config(config, name))      # each one reads its own `enabled` from the configuration it is given
        return registry

    def get(self, name):
        return self.items.get(name)

    def names(self):
        return sorted(self.items)

    def start(self):
        for sentinel in self.items.values():
            if getattr(sentinel, "enabled", True):
                sentinel.start()

    def stop(self):
        for sentinel in self.items.values():
            sentinel.stop()

    def tick_due(self, now=None):
        """Runs `tick()` of every enabled sentinel whose time has come, each on its own clock; returns the names that ran. A failing one is skipped and the others still run."""
        now = time.time() if now is None else now
        ran = []
        for name in self.names():
            sentinel = self.items[name]
            if not getattr(sentinel, "enabled", True) or not sentinel.due(now):
                continue
            try:
                sentinel.tick()
            except Exception:   # noqa: BLE001
                pass
            sentinel.last_tick = now
            ran.append(name)
        return ran

    def status(self):
        return {name: self.items[name].get_status() for name in self.names()}

    def alerts(self):
        """The alerts of every enabled sentinel in one list, the worst first."""
        out = []
        for name in self.names():
            if getattr(self.items[name], "enabled", True):
                out.extend(self.items[name].get_alerts())
        order = {level: i for i, level in enumerate(reversed(sentinel_base.LEVELS))}
        return sorted(out, key=lambda a: (order.get(a["level"], 9), a["sentinel"], a["id"]))

    def metrics(self):
        return {name: self.items[name].get_metrics() for name in self.names()}
