# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Plugins for sentinels: what a plugin declares (`plugin.json`), who is allowed to load, and a guard that keeps a failing plugin from stopping anything else.

Honesty first: a manifest is a LABEL, not a sandbox. `permissions` tells the person what the plugin says it needs; it does not stop code that runs inside the monitor's process from doing more.
Therefore the registry loads only `trust: "official"` plugins (the ones that ship in the product tree) by default; a `third_party` plugin is refused unless the person switches on
`plugins.allow_third_party`, and the documentation says plainly that it then has the same power as the monitor. The supported road for third parties later is a worker process with a narrow IPC,
and until then nothing here is described as a sandbox.

  validate_manifest(data)       (manifest, problems) - a clear list of reasons instead of a half-loaded plugin
  discover(directories, ...)    manifests found in folders (one level, `plugin.json`), invalid ones reported and skipped
  PluginRegistry                decides what loads, builds the sentinels through a factory it is given, keeps the per-account switches and the health of each plugin
  Guard                         wraps one sentinel: an exception in `tick`, `get_alerts`, `get_status` or `get_metrics` is caught, counted and, after a number of failures in a row, the plugin is set aside

The registry never imports anything by itself: `importer(entry)` is given by the caller (the product passes one that imports only from its own tree for official plugins)."""
import json
import re
from pathlib import Path

from github_actions_monitor.phase4 import msgs

API_COMPAT = "1"
TRUST_LEVELS = ("official", "third_party")
PERMISSIONS = ("read_github", "read_monitor", "write_state", "notify")
FORBIDDEN_PERMISSIONS = ("write_github", "execute", "network_any", "secrets")      # never granted: the monitor does not write to GitHub from a sentinel
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}\Z")
VERSION_RE = re.compile(r"^\d{1,4}\.\d{1,4}\.\d{1,4}\Z")
ENTRY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,119}:[A-Za-z_][A-Za-z0-9_]{0,59}\Z")
KNOWN_FIELDS = ("name", "version", "api_compat", "author", "permissions", "trust", "entry", "description")
REQUIRED_FIELDS = ("name", "version", "api_compat", "permissions", "trust", "entry")
ALERT_KEYS = ("id", "code", "level", "sentinel", "account_id", "repo", "title", "details", "created_at")
LEVELS = ("info", "warning", "error", "critical")
CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}(\.[a-z0-9_]{1,31}){1,3}\Z")
RESERVED_NAMES = ("ci", "collab", "security", "ai", "local")      # the sentinels of the core


def validate_manifest(data):
    """(manifest or None, problems). `problems` are stable codes with the field, e.g. "missing:name", "bad:version", "forbidden_permission:write_github"."""
    problems = []
    if not isinstance(data, dict):
        return None, ["not_an_object"]
    for field in REQUIRED_FIELDS:
        if field not in data:
            problems.append("missing:" + field)
    for field in data:
        if field not in KNOWN_FIELDS:
            problems.append("unknown_field:" + str(field)[:40])
    name = data.get("name")
    if "name" in data and (not isinstance(name, str) or not NAME_RE.match(name)):
        problems.append("bad:name")
    elif isinstance(name, str) and name in RESERVED_NAMES:
        problems.append("reserved_name:" + name)
    if "version" in data and (not isinstance(data["version"], str) or not VERSION_RE.match(data["version"])):
        problems.append("bad:version")
    if "api_compat" in data and data["api_compat"] != API_COMPAT:
        problems.append("incompatible_api:" + str(data["api_compat"])[:10])
    if "trust" in data and data["trust"] not in TRUST_LEVELS:
        problems.append("bad:trust")
    if "entry" in data and (not isinstance(data["entry"], str) or not ENTRY_RE.match(data["entry"])):
        problems.append("bad:entry")
    if "author" in data and (not isinstance(data["author"], str) or len(data["author"]) > 80):
        problems.append("bad:author")
    perms = data.get("permissions")
    if "permissions" in data:
        if not isinstance(perms, list) or not all(isinstance(p, str) for p in perms):
            problems.append("bad:permissions")
        else:
            for p in perms:
                if p in FORBIDDEN_PERMISSIONS:
                    problems.append("forbidden_permission:" + p)
                elif p not in PERMISSIONS:
                    problems.append("unknown_permission:" + p[:40])
            if len(set(perms)) != len(perms):
                problems.append("duplicate_permissions")
    if problems:
        return None, problems
    return {k: data[k] for k in KNOWN_FIELDS if k in data}, []


def describe_problems(problems, lang="en"):
    return msgs.t(lang, "plugin.invalid_manifest", reason=", ".join(problems))


def discover(directories, base, read=None):
    """[(path, manifest or None, problems)] for each `<dir>/<plugin>/plugin.json` below `base`. Names that try to leave `base` are ignored. `read(path)` returns the text (tests give a fake)."""
    reader = read or (lambda p: Path(p).read_text(encoding="utf-8"))
    out = []
    root = Path(base).resolve()
    for directory in directories:
        folder = (root / directory).resolve()
        if root != folder and root not in folder.parents:
            continue
        if not folder.is_dir():
            continue
        for child in sorted(folder.iterdir()):
            manifest_file = child / "plugin.json"
            if not manifest_file.is_file():
                continue
            try:
                data = json.loads(reader(manifest_file))
            except (OSError, ValueError, UnicodeDecodeError):
                out.append((manifest_file, None, ["unreadable"]))
                continue
            manifest, problems = validate_manifest(data)
            out.append((manifest_file, manifest, problems))
    return out


class Guard:
    """Wraps a sentinel built by a plugin. Whatever it raises stays here; the monitor sees a status of "error" and the supervisor keeps going."""

    def __init__(self, name, sentinel, max_failures=3, clock=None):
        self.name, self.sentinel, self.max_failures = name, sentinel, max_failures
        self._clock = clock or (lambda: 0.0)
        self.failures = 0          # in a row
        self.total_failures = 0
        self.set_aside = False
        self.last_error = ""
        self.ticks_ok = 0

    def _fail(self, where, exc):
        self.failures += 1
        self.total_failures += 1
        self.last_error = "{} in {}: {}".format(type(exc).__name__, where, str(exc)[:120])
        if self.failures >= self.max_failures:
            self.set_aside = True

    def reset(self):
        """A person puts the plugin back after fixing it."""
        self.failures, self.set_aside, self.last_error = 0, False, ""

    def tick(self):
        if self.set_aside:
            return False
        try:
            self.sentinel.tick()
        except Exception as exc:   # noqa: BLE001 - the whole point: a plugin never stops the supervisor
            self._fail("tick", exc)
            return False
        self.failures = 0
        self.ticks_ok += 1
        return True

    def alerts(self):
        """The alerts of the plugin, kept only when they have the shape of the contract; the sentinel name is forced to the plugin's, so it cannot pass for the core's."""
        if self.set_aside:
            return []
        try:
            raw = list(self.sentinel.get_alerts())
        except Exception as exc:   # noqa: BLE001
            self._fail("get_alerts", exc)
            return []
        good = []
        for alert in raw:
            if (isinstance(alert, dict) and all(k in alert for k in ALERT_KEYS) and alert["level"] in LEVELS and isinstance(alert["code"], str) and CODE_RE.match(alert["code"])
                    and isinstance(alert["id"], str) and 0 < len(alert["id"]) <= 200):
                fixed = dict(alert)
                fixed["sentinel"] = self.name
                good.append(fixed)
        return good

    def status(self):
        base = {}
        if not self.set_aside:
            try:
                value = self.sentinel.get_status()
                base = dict(value) if isinstance(value, dict) else {}
            except Exception as exc:   # noqa: BLE001
                self._fail("get_status", exc)
        base.update({"plugin": self.name, "set_aside": self.set_aside, "failures": self.failures, "last_error": self.last_error})
        if self.set_aside or self.last_error:
            base["level"] = "error" if self.set_aside else base.get("level", "degraded")
        return base

    def metrics(self):
        out = {}
        if not self.set_aside:
            try:
                value = self.sentinel.get_metrics()
                out = {k: v for k, v in value.items() if isinstance(v, (int, float)) and not isinstance(v, bool)} if isinstance(value, dict) else {}
            except Exception as exc:   # noqa: BLE001
                self._fail("get_metrics", exc)
        out.update({"plugin_failures_total": self.total_failures, "plugin_ticks_ok": self.ticks_ok, "plugin_set_aside": int(self.set_aside)})
        return out


class PluginRegistry:
    """Loads the plugins that are allowed, one Guard each. `factory(manifest, ctx, config)` builds the sentinel (the caller decides how the entry is imported)."""

    def __init__(self, settings, factory, ctx=None, clock=None):
        self.settings, self.factory, self.ctx, self.clock = settings, factory, ctx, clock
        self.guards = {}
        self.rejected = {}         # name -> (code, human text key info)

    def _reject(self, name, code):
        self.rejected[name] = code
        return None

    def load(self, manifest, config=None):
        """The Guard of an accepted manifest, or None (the reason is kept in `rejected`). A manifest must already have passed `validate_manifest`."""
        name = manifest["name"]
        if not self.settings.get("enabled"):
            return self._reject(name, "plugins_off")
        if name in self.guards:
            return self._reject(name, "duplicate")
        if manifest["trust"] != "official" and not self.settings.get("allow_third_party"):
            return self._reject(name, "untrusted")
        try:
            sentinel = self.factory(manifest, self.ctx, config or {})
        except Exception:   # noqa: BLE001 - a plugin that cannot even be built is rejected, never raised
            return self._reject(name, "build_failed")
        guard = Guard(name, sentinel, self.settings.get("max_consecutive_failures", 3), self.clock)
        self.guards[name] = guard
        return guard

    def load_all(self, found):
        """`found` is the output of `discover`. Returns the names loaded. Invalid manifests are recorded under their path."""
        loaded = []
        for path, manifest, problems in found:
            if manifest is None:
                self.rejected[str(path)] = "invalid:" + ",".join(problems)
            elif self.load(manifest):
                loaded.append(manifest["name"])
        return loaded

    def enabled_for(self, name, account_id):
        """Whether the plugin runs for `account_id` (a switch per account in `plugins.disabled_by_account`)."""
        return name in self.guards and name not in (self.settings.get("disabled_by_account") or {}).get(account_id or "", [])

    def tick_all(self, account_id=""):
        """One round: every enabled plugin ticks, whatever the others do. {name: True/False}."""
        return {name: guard.tick() for name, guard in self.guards.items() if self.enabled_for(name, account_id)}

    def alerts(self, account_id=""):
        out = []
        for name, guard in self.guards.items():
            if self.enabled_for(name, account_id):
                out.extend(guard.alerts())
        return out

    def health(self):
        return {name: {"set_aside": g.set_aside, "failures": g.failures, "last_error": g.last_error} for name, g in self.guards.items()}

    def rejection_text(self, name, lang="en"):
        code = self.rejected.get(name, "")
        if code == "untrusted":
            return msgs.t(lang, "plugin.not_loaded_untrusted", name=name)
        if code.startswith("invalid:"):
            return msgs.t(lang, "plugin.invalid_manifest", reason=code[8:])
        return code
