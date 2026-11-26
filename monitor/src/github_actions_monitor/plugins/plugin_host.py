# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Runs the plugins that are switched on and turns what they say into alerts. A plugin is a sentinel (sentinels/sentinel_base.BaseSentinel): it has its own cycle, its state, its alerts and its metrics.

Rules: everything a plugin says is untrusted data (cleaned and cut here); one plugin that fails never stops the others, the CI or Collab; after plugins.breaker.failures failures in a row it is paused
until the person switches it on again (`plugin enable NAME`); "no alerts" of a degraded or paused plugin is not "all fine", its state says so. Reads of GitHub are mediated: only the declared paths."""
import importlib.util
import json
import re
import threading
import time
from pathlib import Path

from github_actions_monitor import families, i18n
from github_actions_monitor.plugins import plugin_manifest as manifests
from github_actions_monitor.plugins import plugin_package as packages
from github_actions_monitor.plugins import plugin_worker
from github_actions_monitor.security import keyring, private_io, redactor
from github_actions_monitor.sentinels.sentinel_base import LEVELS, BaseSentinel
from github_actions_monitor.util import paths

OFFICIAL = Path(__file__).resolve().parent / "official"
STATE_NAME = "plugins_state.json"
MAX_ALERTS = 200
MAX_GETS = 200
URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_./#?=&%+-]{1,300}\Z")
ANSI = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)?|\[[0-?]*[ -/]*[@-~]|.)", re.S)
CODE_RE = re.compile(r"[^a-z0-9_]")
DISCUSSIONS_QUERY = ("query($q:String!){search(type:DISCUSSION,query:$q,first:50){discussionCount "
                     "nodes{... on Discussion{number title url createdAt closed repository{name} comments{totalCount}}}}}")
LOCK = threading.RLock()
PLUGINS = {}      # {name: PluginSentinel}
RUNNING = {"on": False}
STARTED = {"checked": False}


def settings(config):
    return families.block(config if isinstance(config, dict) else {}, "plugins")


def user_keys():
    try:
        return keyring.all_keys(paths.place("keyring.json"))
    except keyring.KeyringError:
        return keyring.builtin_keys()


def clean_text(value, limit):
    text = ANSI.sub("", value if isinstance(value, str) else "")
    text = " ".join("".join(c if c.isprintable() else " " for c in text[:4000]).split())
    text = redactor.redact(text) if text else ""
    return text if len(text) <= limit else text[:limit - 1] + "…"


def clean_alerts(name, trust, answer, repos, title_max=120, account=""):
    """The alerts of the answer of a plugin, in the shape of every alert; anything that does not fit is cut or dropped. ValueError when the answer is not the shape of an answer."""
    if not isinstance(answer, dict) or not isinstance(answer.get("alerts", []), list):
        raise ValueError("the answer of a plugin is an object with a list `alerts`")
    out, seen = [], set()
    for raw in answer.get("alerts", [])[:MAX_ALERTS]:
        if not isinstance(raw, dict):
            continue
        code = CODE_RE.sub("", str(raw.get("code") or "finding").lower()[:40]) or "finding"
        ident = f"plugin.{name}.{code}:{clean_text(str(raw.get('id') or len(out)), 120)}"
        if ident in seen:
            continue
        seen.add(ident)
        repo = raw.get("repo") if isinstance(raw.get("repo"), str) and raw["repo"] in repos else None
        url = raw.get("url") if isinstance(raw.get("url"), str) and URL_RE.match(raw["url"]) else ""
        level = raw.get("level") if raw.get("level") in LEVELS else "info"
        if trust != "official" and level == "critical":
            level = "error"      # only the monitor itself may call something critical
        out.append({"id": ident, "code": f"plugin.{name}.{code}", "level": level, "sentinel": "plugin", "account_id": account, "repo": repo,
                    "title": f"[{name}] " + clean_text(raw.get("title"), title_max), "details": {"plugin": name, "trust": trust, "url": url, "untrusted": trust != "official"},
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return out


class Reads:
    """What a plugin may read: the repositories watched and the declared paths. `gh` is the reader of the monitor."""

    def __init__(self, manifest, gh, owner, repos):
        self.manifest, self.gh, self.owner, self._repos = manifest, gh, owner, list(repos)
        self.count = 0

    def _need(self, permission):
        if permission not in self.manifest["permissions"]:
            raise PermissionError(f"the plugin did not declare the permission {permission}")
        self.count += 1
        if self.count > MAX_GETS:
            raise PermissionError("too many reads in one round")

    def repos(self):
        self._need("repos.list")
        return list(self._repos)

    def get(self, path):
        self._need("gh.get")
        if not manifests.path_allowed(self.manifest, path, self.owner, self._repos):
            raise PermissionError("that path is not in the get_paths of the plugin: " + str(path)[:80])
        return self.gh("api", path)

    def discussions(self):
        """The newest discussions of the account without any comment (one search, whatever the number of repositories), only of watched repositories."""
        self._need("graphql.discussions")
        if not re.match(r"[A-Za-z0-9-]{1,39}\Z", self.owner):
            raise PermissionError("the account to look at is not known")
        answer = self.gh("api", "graphql", "-f", "query=" + DISCUSSIONS_QUERY, "-f", f"q=user:{self.owner} comments:0 sort:created-desc")      # a fixed query: it can never be a mutation
        nodes = (((answer or {}).get("data") or {}).get("search") or {}).get("nodes") or []
        return [n for n in nodes if isinstance(n, dict) and (n.get("repository") or {}).get("name") in self._repos]

    def broker(self, method, args):
        if method in ("repos", "discussions") and not args:
            return getattr(self, method)()
        if method == "get" and len(args) == 1:
            return self.get(args[0])
        raise PermissionError("unknown call")


class Context:
    """The ctx of an official plugin (it runs in this process): the same methods a separate process offers."""

    def __init__(self, reads, options, now):
        self.owner, self.options, self.now = reads.owner, options, now
        self.repos, self.get, self.discussions = reads.repos, reads.get, reads.discussions


def official():
    """{name: (manifest, folder)} of the plugins that travel with the monitor."""
    out = {}
    if OFFICIAL.is_dir():
        for folder in sorted(OFFICIAL.iterdir()):
            path = folder / manifests.MANIFEST_NAME
            if path.is_file():
                manifest = manifests.parse(path.read_bytes())
                if manifest["trust"] == "official" and manifest["name"] == folder.name:
                    out[manifest["name"]] = (manifest, folder)
    return out


def official_options(config, name):
    return families.block(settings(config), "official").get(name, {}) if isinstance(settings(config).get("official"), dict) else {}


def load_official(folder, entry):
    spec = importlib.util.spec_from_file_location("github_actions_monitor_plugin_" + folder.name, folder / entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_state():
    try:
        data = json.loads(paths.place(STATE_NAME).read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    except (OSError, ValueError, AttributeError):
        return {}


def save_state(name, row):
    with LOCK:
        rows = load_state()
        if row is None:
            rows.pop(name, None)
        else:
            rows[name] = row
        target = paths.place(STATE_NAME)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = private_io.unique_tmp(target)
            private_io.write_tmp(temporary, json.dumps(rows, indent=1) + "\n")
            private_io.replace_with_retry(temporary, target)
        except OSError:
            pass      # the state is kept in memory; the next round tries again


class PluginSentinel(BaseSentinel):
    """One plugin as a sentinel. `runner()` returns (answer, isolation) and raises when the round fails."""

    name = "plugin"

    def __init__(self, ctx, config, manifest):
        super().__init__(ctx, config)
        self.manifest = manifest
        saved = load_state().get(manifest["name"]) or {}
        self.failures = saved.get("failures", 0) if isinstance(saved.get("failures"), int) else 0
        self.paused = saved.get("paused") is True
        self.reason = str(saved.get("reason") or "")[:200]
        self.alerts, self.isolation, self.last_ok = [], {}, 0.0

    @property
    def refresh_seconds(self):
        return self.manifest["refresh_seconds"]

    def _remember(self):
        save_state(self.manifest["name"], {"failures": self.failures, "paused": self.paused, "reason": self.reason})

    def pause(self, reason):
        self.paused, self.reason, self.alerts = True, reason[:200], []
        self._remember()

    def tick(self):
        if self.paused:
            return
        limit = settings(self.config).get("breaker", {}).get("failures", 3)
        try:
            answer, self.isolation = self.ctx["runner"]()
            self.alerts = clean_alerts(self.manifest["name"], self.manifest["trust"], answer, self.ctx["repos"], settings(self.config).get("alert_title_max", 120), self.ctx.get("account_id", ""))
            self.failures, self.reason, self.last_ok = 0, "", time.time()
        except packages.PackageError as error:      # revoked key, changed file...: it stops at once
            self.pause(f"{error.code}: {error}")
            return
        except Exception as error:   # noqa: BLE001 - one plugin never stops the others
            self.failures += 1
            self.reason = clean_text(f"{type(error).__name__}: {error}", 200)
            if self.failures >= limit:
                self.pause(self.reason)
                return
        self._remember()

    def state(self):
        if self.paused:
            return "paused"
        if self.failures:
            return "degraded" if self.last_ok else "error"
        return "healthy" if self.last_ok else "waiting"

    def get_status(self):
        return {"enabled": True, "state": self.state(), "paused": self.paused, "reason": self.reason, "isolation": dict(self.isolation), "alerts": len(self.alerts)}

    def get_alerts(self):
        return list(self.alerts)

    def get_metrics(self):
        return {"alerts": len(self.alerts), "failures": self.failures, "paused": int(self.paused)}

    def get_config_schema(self):
        return {"refresh_seconds": {"type": "int", "default": self.manifest["refresh_seconds"]}}


def enabled_names(config):
    """[(name, "official" | "third_party")] of what must run with this configuration."""
    cfg = settings(config)
    if cfg.get("enabled") is not True:
        return []
    out = [(name, "official") for name in official() if official_options(config, name).get("enabled") is True]
    if cfg.get("third_party", {}).get("enabled") is True:
        out += [(name, "third_party") for name, row in sorted(packages.registry().items()) if row.get("enabled") is True and name not in official()]
    return out


def third_party_runner(config, name, gh, owner, repos):
    def runner():
        import tempfile
        manifest, files = packages.load_installed(name, user_keys())
        worker = settings(config).get("worker", {})
        reads = Reads(manifest, gh, owner, repos)
        with tempfile.TemporaryDirectory(prefix="plugin_code_", ignore_cleanup_errors=True) as folder:
            packages.extract(files, folder)
            return plugin_worker.run(folder, manifest, reads.broker, owner=owner, timeout_s=worker.get("timeout_s", 20), max_output_kb=worker.get("max_output_kb", 256),
                                     memory_mb=worker.get("memory_mb", 256), platforms_ok=tuple(worker.get("platforms_ok") or ()))
    return runner


def official_runner(config, manifest, folder, gh, owner, repos):
    def runner():
        box = {}
        options = dict(official_options(config, manifest["name"]))
        context = Context(Reads(manifest, gh, owner, repos), options, time.time())

        def work():
            try:
                box["answer"] = load_official(folder, manifest["entry"]).run(context)
            except BaseException as error:   # noqa: BLE001 - carried to the caller
                box["error"] = error
        thread = threading.Thread(target=work, daemon=True, name="plugin-" + manifest["name"])      # a guard thread: a plugin that hangs does not hang the others
        thread.start()
        thread.join(settings(config).get("official_timeout_s", 300))
        if thread.is_alive():
            raise TimeoutError("the plugin did not finish in time")
        if "error" in box:
            raise RuntimeError(str(box["error"])[:200])
        return box.get("answer"), {"in_process": True}
    return runner


def start_check(config):
    """At the first round (plugins.reverify_on_start): every installed package is checked against the keyring again; a revoked or changed one is paused and says why."""
    if STARTED["checked"] or settings(config).get("reverify_on_start", True) is not True:
        return []
    STARTED["checked"] = True
    bad = [row for row in packages.audit(user_keys()) if row["state"] != "ok"]
    for row in bad:
        save_state(row["name"], {"failures": 0, "paused": True, "reason": row["state"]})
    return bad


def refresh(config, gh, owner, repos, account="", force=False, now=None):
    """One round of every plugin that is due. Returns the names that ran."""
    start_check(config)
    wanted = dict(enabled_names(config))
    ran = []
    with LOCK:
        for name in [n for n in PLUGINS if n not in wanted]:
            del PLUGINS[name]
    for name, trust in wanted.items():
        if trust == "official":
            manifest, folder = official()[name]
            runner = official_runner(config, manifest, folder, gh, owner, repos)
        else:
            try:
                manifest = packages.load_installed(name, user_keys())[0]
            except packages.PackageError as error:
                save_state(name, {"failures": 0, "paused": True, "reason": error.code})
                manifest = {"name": name, "trust": "third_party", "refresh_seconds": 3600, "permissions": [], "get_paths": []}
            runner = third_party_runner(config, name, gh, owner, repos)
        with LOCK:
            sentinel = PLUGINS.get(name)
            if sentinel is None:
                sentinel = PLUGINS[name] = PluginSentinel({}, config, manifest)
            sentinel.ctx, sentinel.config, sentinel.manifest = {"runner": runner, "repos": list(repos), "account_id": account}, config, manifest
        stored = load_state().get(name) or {}
        sentinel.paused = stored.get("paused") is True      # the command line can switch it back on while the monitor runs
        if not sentinel.paused:
            sentinel.reason = "" if not sentinel.failures else sentinel.reason
            sentinel.failures = stored.get("failures", sentinel.failures)
        else:
            sentinel.reason, sentinel.alerts = str(stored.get("reason") or "")[:200], []
        if not sentinel.paused and (force or sentinel.due(now)):
            sentinel.tick()
            sentinel.last_tick = time.time() if now is None else now
            ran.append(name)
    return ran


def tick(config, data):
    """After a cycle of the monitor: the round runs in its own thread, so a slow plugin never delays the monitor."""
    if not enabled_names(config):
        with LOCK:
            PLUGINS.clear()
        return
    with LOCK:
        if RUNNING["on"]:
            return
        RUNNING["on"] = True

    def work():
        try:
            from github_actions_monitor.app import actions_monitor, toolconfig
            repos = [r for r in ((data or {}).get("repos") or []) if isinstance(r, str)]
            refresh(config, actions_monitor.gh, toolconfig.github_owner(config), repos, actions_monitor.CHILD["account"] or "")
        except Exception as error:   # noqa: BLE001
            from github_actions_monitor.app import degraded
            degraded.note("plugins.tick", error)
        finally:
            RUNNING["on"] = False
    threading.Thread(target=work, daemon=True, name="plugins-round").start()


def alerts():
    """The alerts of the plugins, and one of its own for each plugin that was stopped."""
    out = []
    with LOCK:
        sentinels = list(PLUGINS.items())
    for name, sentinel in sentinels:
        out += sentinel.get_alerts()
        if sentinel.paused:
            out.append({"id": f"plugin.paused:{name}", "code": "plugin.paused", "level": "warning", "sentinel": "plugin", "account_id": "", "repo": None,
                        "title": i18n.t("ui.plugins.alert_paused", name=name, reason=sentinel.reason or "-"), "details": {"plugin": name}, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return out


def resume(name):
    """The person switched it on again: the counter of failures starts from zero."""
    save_state(name, {"failures": 0, "paused": False, "reason": ""})
    with LOCK:
        sentinel = PLUGINS.get(name)
        if sentinel:
            sentinel.paused, sentinel.failures, sentinel.reason, sentinel.last_tick = False, 0, "", 0.0


def isolation_label(trust, isolation):
    """The word shown next to a plugin: "in_process" (official), "separate_process" (no network) or "no_network_isolation" (what is true until a round proves otherwise)."""
    if trust == "official":
        return "in_process"
    return "separate_process" if isolation.get("network_isolated") else "no_network_isolation"


def catalogue(config):
    """Every plugin that exists here: official ones and installed ones, with permissions, key, state and isolation."""
    states, rows = load_state(), []
    keys = user_keys()
    checked = {row["name"]: row for row in packages.audit(keys)}
    for name, (manifest, _folder) in official().items():
        rows.append(_row(config, name, manifest, official_options(config, name).get("enabled") is True, states, {"key_id": "", "fingerprint": "", "check": "ok"}))
    for name, found in checked.items():
        try:
            manifest = packages.load_installed(name, keys)[0]
        except packages.PackageError:
            manifest = {"name": name, "version": found["version"], "trust": "third_party", "author": "", "description": "", "permissions": [], "get_paths": []}
        rows.append(_row(config, name, manifest, found["enabled"], states, {"key_id": found["key_id"], "fingerprint": found["fingerprint"], "check": found["state"]}))
    cfg = settings(config)
    return {"ok": True, "enabled": cfg.get("enabled") is True, "third_party": cfg.get("third_party", {}).get("enabled") is True, "plugins": rows,
            "candidates": packages.entry_point_candidates() if cfg.get("entry_points") is True else []}


def _row(config, name, manifest, enabled, states, extra):
    with LOCK:
        sentinel = PLUGINS.get(name)
    saved = states.get(name) or {}
    if saved.get("paused"):
        state = "paused"
    elif not enabled or settings(config).get("enabled") is not True:
        state = "off"
    else:
        state = sentinel.state() if sentinel else "waiting"
    return dict(extra, name=name, version=manifest["version"], trust=manifest["trust"], author=manifest["author"], description=manifest["description"], permissions=manifest["permissions"],
                get_paths=manifest["get_paths"], enabled=enabled, state=state, reason=str(saved.get("reason") or "")[:200], isolation=isolation_label(manifest["trust"], sentinel.isolation if sentinel else {}))
