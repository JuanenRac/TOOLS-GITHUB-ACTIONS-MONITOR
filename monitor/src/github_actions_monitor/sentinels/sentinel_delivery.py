# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Delivery sentinel (2.1.1): whether what is built is also delivered. Read only, on a clock of its own, off by default.

It is the fifth sentinel behind `sentinel_base.BaseSentinel`. It reads, through the API and without a clone (`delivery/reader.py`), the latest releases, the latest tags, the CHANGELOG and the
version files you name of each repository, and raises one alert per repository and signal (`delivery/rules.py`; the code of the alert is `release.<signal>`):
  release.unreleased_pending / tag_without_release / release_without_notes / version_mismatch / assets_missing   (one repository alone)
  release.ecosystem_drift                                                                                    (a repository pins an older version of the provider of a shared contract)
Each signal has a switch and a level of its own. A repository that cannot be read (no access, SSO not authorised, allowance spent) is NOT an alert and NOT a clean bill of health: it is listed under
`unavailable`, the alerts it already had stay (marked unread) and, if it stays unreadable for a week, they are dropped without an event. A repository with no release at all is not judged: it does
not use releases.

Cost: a round reads at most `max_repos_per_tick` repositories and `max_calls_per_tick` calls (1 to 3 plus one for each version file), the ones read longest ago first and the ones with an open alert a
little sooner, and it pauses while the allowance is below `min_rate_remaining`. The pin tables of the drift signal are read once per cycle (two calls per source). There is no conditional request: the
cost is bounded by the settings, not by a 304. The state (`delivery_state.json`) keeps the open alerts, so a restart announces nothing again; the first look at a repository writes no event.
Frontier: the panel of release readiness (A11) is one row per repository drawn from clones; this sentinel produces ALERTS (stable id, silences, events) from the API. The score does not use it.
"""
import json
import threading
import time
from datetime import datetime, timezone

from github_actions_monitor import i18n
from github_actions_monitor.app import toolconfig
from github_actions_monitor.data_pipeline import events
from github_actions_monitor.delivery import reader, rules
from github_actions_monitor.integrations import remote_workflows
from github_actions_monitor.sentinels import readiness, sentinel_base
from github_actions_monitor.storage import state_io
from github_actions_monitor.util import paths

STATE_FILE = paths.place("delivery_state.json")
RETRY_AFTER = (300, 1800, 21600)      # seconds a repository whose read fails waits before it is tried again: after the 1st, 2nd, 3rd and later failure in a row
UNREAD_KEEP = 7 * 24 * 3600           # alerts of a repository that stays unreadable are kept (marked unread) this long, then dropped without an event
MIN_COVERAGE = 0.5                    # "nothing open" with fewer readable repositories than this is `unknown`, not `ok`
DEFAULTS = {
    "enabled": False, "refresh_seconds": 3600, "max_repos_per_tick": 10, "deadline_s": 30, "max_calls_per_tick": 60, "min_rate_remaining": 1000, "repos": "all",
    "unreleased_days": 14, "unreleased_min_entries": 1, "changelog_paths": ["CHANGELOG.md"], "version_files": [], "expected_assets": [],
    "signals": {name: {"enabled": True, "level": rules.DEFAULT_LEVEL[name]} for name in rules.SIGNALS},
}
BOUNDS = {"refresh_seconds": (600, 86400), "max_repos_per_tick": (1, 200), "deadline_s": (0, 600), "max_calls_per_tick": (1, 600), "min_rate_remaining": (100, 5000), "unreleased_days": (1, 365), "unreleased_min_entries": (1, 100)}
LISTS = {"changelog_paths": 5, "version_files": 20, "expected_assets": 20}      # the longest list of each setting
TITLE_KEYS = {code: "delivery.t." + name for name, code in rules.CODES.items()}


def clean_path(value):
    """True for a path of a file inside the repository: letters, digits, `.`, `_`, `-` and `/`, no `..`, not absolute."""
    return isinstance(value, str) and 0 < len(value) <= 120 and all(c.isalnum() or c in "._-/" for c in value) and not value.startswith("/") and ".." not in value.split("/") and not value.endswith("/")


def clean_pattern(value):
    return isinstance(value, str) and 0 < len(value) <= 100 and all(c.isalnum() or c in "._*? -" for c in value)


def settings(config):
    """The merged settings of `sentinels.delivery` over DEFAULTS: unknown keys are dropped, a value of the wrong type or out of range keeps the default."""
    merged = json.loads(json.dumps(DEFAULTS))
    block = ((config or {}).get("sentinels") or {}).get("delivery") if isinstance((config or {}).get("sentinels"), dict) else None
    if not isinstance(block, dict):
        return merged
    if isinstance(block.get("enabled"), bool):
        merged["enabled"] = block["enabled"]
    for key, (low, high) in BOUNDS.items():
        value = block.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            merged[key] = value
    repos = block.get("repos")
    if repos == "all" or (isinstance(repos, list) and all(isinstance(r, str) for r in repos)) or (isinstance(repos, dict) and isinstance(repos.get("ecosystems"), list)):
        merged["repos"] = repos
    for key, check in (("changelog_paths", clean_path), ("version_files", clean_path), ("expected_assets", clean_pattern)):
        value = block.get(key)
        if isinstance(value, list):
            kept = [x for x in value if check(x)][:LISTS[key]]
            if kept or key != "changelog_paths":      # an empty list of CHANGELOG paths keeps the default
                merged[key] = kept
    signals = block.get("signals")
    if isinstance(signals, dict):
        for name in rules.SIGNALS:
            entry = signals.get(name)
            if not isinstance(entry, dict):
                continue
            if isinstance(entry.get("enabled"), bool):
                merged["signals"][name]["enabled"] = entry["enabled"]
            if entry.get("level") in rules.LEVELS:
                merged["signals"][name]["level"] = entry["level"]
    return merged


def stamp(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path):
    try:
        data = state_io.load_json(path)
        if isinstance(data, dict) and isinstance(data.get("alerts"), dict) and isinstance(data.get("per_repo"), dict):
            data["alerts"] = {str(k): v for k, v in data["alerts"].items() if isinstance(v, dict) and isinstance(v.get("repo"), str) and v.get("code") in TITLE_KEYS}
            data["per_repo"] = {str(k): v for k, v in data["per_repo"].items() if isinstance(v, dict)}
            if not isinstance(data.get("drift_unavailable"), dict):
                data["drift_unavailable"] = {}
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return {"alerts": {}, "per_repo": {}, "last_full_scan": None, "drift_at": None, "drift_unavailable": {}}


class SentinelDelivery(sentinel_base.BaseSentinel):
    round_cut = False      # the last round stopped for lack of time (deadline_s) and left repositories for the next one
    name = "delivery"

    def __init__(self, ctx, config):
        super().__init__(ctx, config)
        self.cfg = settings(config)
        self.lock = threading.RLock()
        self.state = load_state(STATE_FILE)
        self.calls, self.errors, self.paused = [], {}, False
        self.feed = events.Feed(events.EVENTS_FILE, events.STATE_FILE)

    @property
    def enabled(self):
        return bool(self.cfg["enabled"])

    @property
    def refresh_seconds(self):
        return int(self.cfg["refresh_seconds"])

    @property
    def account_id(self):
        return str((self.ctx or {}).get("account_id") or "")

    def _read(self, endpoint):
        with self.lock:
            self.calls.append(time.time())
            self.calls = [t for t in self.calls if t > time.time() - 3600]
        return self.ctx["gh"]("api", endpoint, retries=1)      # GET only

    def scope(self):
        repos = list(self.ctx["repos_fn"]())
        wanted = self.cfg["repos"]
        if isinstance(wanted, list):
            return [r for r in repos if r in wanted]
        if isinstance(wanted, dict):
            return [r for r in repos if self.ctx["eco_fn"](r) in wanted["ecosystems"]]
        return repos

    def _order(self, repos, now):
        """The repositories read longest ago first (the ones with an open alert a little sooner); the ones whose last reads failed wait for their retry time at the end."""
        open_in = {a["repo"] for a in self.state["alerts"].values()}

        def key(r):
            record = self.state["per_repo"].get(r) or {}
            return (record.get("retry", 0) > now, max(record.get("scanned", 0), record.get("tried", 0)) - (self.refresh_seconds * 3 if r in open_in else 0), r)
        return sorted(repos, key=key)

    # -- one round
    def tick(self, now=None):
        if not self.enabled:
            return False
        now = time.time() if now is None else now
        rate = ((self.ctx.get("data_fn") or (lambda: None))() or {}).get("rate")
        self.paused = bool(rate and rate.get("remaining", 10 ** 9) < self.cfg["min_rate_remaining"])
        if self.paused:
            return False
        repos, budget, need = self.scope(), self.cfg["max_calls_per_tick"], reader.plan(self.cfg)
        if reader.minimum_calls(need):
            deadline, self.round_cut = sentinel_base.round_deadline(self.cfg["deadline_s"]), False
            for repo in self._order(repos, now)[:self.cfg["max_repos_per_tick"]]:
                if sentinel_base.expired(deadline):      # the round ran out of time: the rest waits for the next one and is named as not checked
                    self.round_cut = True
                    break
                if budget < reader.minimum_calls(need) and budget < self.cfg["max_calls_per_tick"]:
                    break      # what is left of the round cannot even begin a repository (when the whole budget cannot, `scan` lists it as unreadable for that reason)
                try:
                    budget -= max(1, self.scan(repo, now, budget, need))
                    self.errors.pop(repo, None)
                except Exception as error:      # one repository that fails never stops the round
                    self.errors[repo] = {"message": str(error)[:80], "at": stamp(now)}
                    with self.lock:
                        record = self.state["per_repo"].setdefault(repo, {})
                        record["fails"] = int(record.get("fails", 0)) + 1
                        record["tried"] = now
                        record["retry"] = now + RETRY_AFTER[min(record["fails"], len(RETRY_AFTER)) - 1]
                if self.paused:
                    break
        self._drift(repos, now, budget)
        with self.lock:
            for gone in [r for r in self.state["per_repo"] if r not in repos]:
                self.state["per_repo"].pop(gone, None)
            for key in [k for k, a in self.state["alerts"].items() if a["repo"] not in repos]:
                self.state["alerts"].pop(key, None)
            if repos and reader.minimum_calls(need) and all((self.state["per_repo"].get(r) or {}).get("scanned") for r in repos):
                self.state["last_full_scan"] = stamp(now)
        self.persist()
        return True

    def scan(self, repo, now, budget, need):
        """Reads one repository and applies the rules. Returns the calls made."""
        calls = 0
        try:
            if reader.minimum_calls(need) > self.cfg["max_calls_per_tick"]:
                raise RuntimeError("budget")      # the settings ask for more calls than a round may make
            facts, calls, complete = reader.fetch(self._read, toolconfig.github_owner(), repo, need, budget)
            reason = "" if complete else "budget"
        except Exception as error:      # noqa: BLE001 - a repository that cannot be read says why
            facts, complete, reason = None, False, ("budget" if str(error) == "budget" else remote_workflows.reason_of(error))
            calls = max(calls, 1)
            if reason == "rate_limited":
                self.paused = True
        with self.lock:
            mine = dict(self.state["per_repo"].get(repo) or {})
        if not complete:
            # not readable (or only in part) now: what was known is kept, marked unread, instead of being closed as fixed; after UNREAD_KEEP it is dropped without an event
            since = mine.get("unread_since") or now
            mine.update(unread_since=since, unavailable=reason or "error", tried=now, retry=now + RETRY_AFTER[0])
            with self.lock:
                self.state["per_repo"][repo] = mine
                if now - since >= UNREAD_KEEP:
                    for key in [k for k, a in self.state["alerts"].items() if a["repo"] == repo and a["code"] != rules.CODES["ecosystem_drift"]]:
                        self.state["alerts"].pop(key, None)
            return calls
        found = rules.repo_findings(facts, self.cfg, now)
        self._commit(repo, found, now)
        return calls

    def _commit(self, repo, found, now):
        """Applies the rules to what was read of one repository, replaces its alerts (the drift ones are not its own), and writes the events of what changed (nothing the first time)."""
        drift = rules.CODES["ecosystem_drift"]
        with self.lock:
            before = {k: a for k, a in self.state["alerts"].items() if a["repo"] == repo and a["code"] != drift}
            first = not (self.state["per_repo"].get(repo) or {}).get("scanned")
            alerts = rules.evaluate(repo, found, self.cfg["signals"], before, stamp(now))
            for key in before:
                self.state["alerts"].pop(key, None)
            self.state["alerts"].update(alerts)
            self.state["per_repo"][repo] = {"scanned": now}
        if first:
            return
        self._announce(before, alerts)

    def _announce(self, before, after):
        out = [self._event("delivery_new", after[k]) for k in after if k not in before] + [self._event("delivery_fixed", before[k]) for k in before if k not in after]
        if out:
            self.feed.emit(out)

    # -- the pin tables of the shared contracts (release.ecosystem_drift)
    def _sources(self):
        return [s for s in (readiness.settings(self.config)["pins"].get("sources") or []) if s.get("kind") == "pin_table" and isinstance(s.get("provider"), str) and isinstance(s.get("file"), str)][:20]

    def _drift(self, repos, now, budget):
        """Once per cycle: the pin tables of `sentinel.readiness.pins.sources` (kind pin_table) are read through the API and the repositories that pin an older version than the latest release of
        the provider get an alert. Two calls per source. A source that cannot be read keeps the alerts it had and is listed under `unavailable`."""
        rule = self.cfg["signals"]["ecosystem_drift"]
        sources = self._sources()
        with self.lock:
            last = self.state.get("drift_at")
        if not rule["enabled"] or not sources:
            with self.lock:      # switched off (or nothing to read): the alerts of the signal go away without an event
                for key in [k for k, a in self.state["alerts"].items() if a["code"] == rules.CODES["ecosystem_drift"]]:
                    self.state["alerts"].pop(key, None)
                self.state["drift_unavailable"] = {}
            return
        if (last is not None and now - last < self.refresh_seconds) or budget < 2 or self.paused:
            return
        rows, unavailable, owner, spent = [], {}, toolconfig.github_owner(), 0
        for source in sources:
            if budget - spent < 2:
                unavailable[source["provider"]] = "budget"
                continue
            spent += 2
            try:
                current, table = reader.fetch_pin_table(self._read, owner, source)
            except Exception as error:      # noqa: BLE001
                unavailable[source["provider"]] = remote_workflows.reason_of(error)
                continue
            if not rules.version_key(current):
                unavailable[source["provider"]] = "no_release"
                continue
            rows += rules.drift_rows(source, current, table, set(repos))
        drift = rules.CODES["ecosystem_drift"]
        with self.lock:
            before = {k: a for k, a in self.state["alerts"].items() if a["code"] == drift}
            first = self.state.get("drift_at") is None
            after = rules.drift_alerts(rows, rule, before, stamp(now))
            kept = {k: a for k, a in before.items() if k not in after and (a.get("detail") or {}).get("provider") in unavailable}      # a source that cannot be read keeps what it had
            for key in before:
                self.state["alerts"].pop(key, None)
            self.state["alerts"].update(after)
            self.state["alerts"].update(kept)
            self.state["drift_at"] = now
            self.state["drift_unavailable"] = unavailable
        if not first:
            self._announce(before, {**after, **kept})

    def _title(self, alert):
        d = alert.get("detail") or {}
        return i18n.t(TITLE_KEYS[alert["code"]], repo=alert["repo"], n=d.get("n", d.get("entries", 0)), days=d.get("days", 0), tag=d.get("tag", ""), current=d.get("current", ""))

    def _event(self, kind, alert):
        return {"kind": kind, "code": alert["code"], "level": ("ok" if kind == "delivery_fixed" else ("bad" if alert["level"] in ("critical", "error") else ("warn" if alert["level"] == "warning" else "info"))), "repo": alert["repo"],
                "owner": events.owner_of(alert["repo"]), "sentinel": self.name, "account_id": self.account_id, "text": i18n.t("evt." + kind, title=self._title(alert)), "url": None,
                "args": {"signal": rules.SIGNAL_OF[alert["code"]], **{k: v for k, v in (alert.get("detail") or {}).items() if isinstance(v, (int, str))}}}

    def persist(self):
        with self.lock:
            payload = json.dumps(self.state, ensure_ascii=False)
        try:
            state_io.save_text(STATE_FILE, payload)
        except OSError:
            pass

    # -- the contract
    def get_alerts(self):
        if not self.enabled:
            return []
        with self.lock:
            items = list(self.state["alerts"].values())
            unread = {r: v.get("unread_since") for r, v in self.state["per_repo"].items() if v.get("unread_since")}
        return [{"id": a["id"], "code": a["code"], "level": a["level"], "sentinel": self.name, "account_id": self.account_id, "repo": a["repo"], "title": self._title(a),
                 "details": {"signal": rules.SIGNAL_OF[a["code"]], **(a.get("detail") or {}), "updated": a["created_at"], **({"unread_since": stamp(unread[a["repo"]])} if a["repo"] in unread else {})},
                 "created_at": a["created_at"]} for a in sorted(items, key=lambda x: x["id"])]

    def unavailable(self):
        """{reason: number of repositories (or pin tables) that cannot be read} (no access, SSO, allowance, budget...)."""
        out = {}
        with self.lock:
            for record in self.state["per_repo"].values():
                if record.get("unread_since"):
                    reason = str(record.get("unavailable") or "error")
                    out[reason] = out.get(reason, 0) + 1
            for reason in (self.state.get("drift_unavailable") or {}).values():
                out[str(reason)] = out.get(str(reason), 0) + 1
        return out

    def get_status(self):
        """The state, with its `lifecycle` (healthy | degraded | paused | error | off): no alerts only means something when it is healthy."""
        status = self._status()
        status["lifecycle"] = sentinel_base.lifecycle(status)
        return status

    def _status(self):
        if not self.enabled:
            return {"enabled": False, "level": "off", "loading": "", "errors": [], "refresh_seconds": self.refresh_seconds, "repos_in_scope": 0, "repos_checked": 0, "last_full_scan": None, "paused": False,
                    "unavailable": {}}
        repos = self.scope()
        with self.lock:
            records = [self.state["per_repo"].get(r) or {} for r in repos]
            checked = sum(1 for rec in records if rec.get("scanned") or rec.get("unread_since"))
            readable = sum(1 for rec in records if rec.get("scanned") and not rec.get("unread_since"))
            alerts = list(self.state["alerts"].values())
            last = self.state["last_full_scan"]
        level = "unknown" if not checked else ("bad" if any(a["level"] in ("critical", "error") for a in alerts) else ("warn" if alerts else "ok"))
        if level == "ok" and checked and readable / checked < MIN_COVERAGE:
            level = "unknown"      # nothing open because most of what was looked at could not be read: not a clean bill of health
        return {"enabled": True, "level": level, "loading": "" if checked or not repos else "starting", "errors": [{"section": r, "at": e["at"]} for r, e in sorted(self.errors.items())],
                "refresh_seconds": self.refresh_seconds, "repos_in_scope": len(repos), "repos_checked": checked, "repos_readable": readable, "last_full_scan": last, "paused": self.paused,
                "unavailable": self.unavailable(), "unchecked": sentinel_base.unchecked(repos, self.state["per_repo"]), "round_cut": self.round_cut}

    def get_metrics(self):
        if not self.enabled:
            return {}
        with self.lock:
            alerts = list(self.state["alerts"].values())
        status = self.get_status()
        pending = [a for a in alerts if a["code"] == rules.CODES["unreleased_pending"]]
        return {"delivery_alerts": len(alerts), "delivery_unreleased_repos": len(pending), "delivery_unreleased_days_max": max([int((a.get("detail") or {}).get("days", 0)) for a in pending] or [0]),
                "delivery_repos_checked": status["repos_checked"], "delivery_repos_unreadable": sum(status["unavailable"].values()), "delivery_calls_last_hour": len([t for t in self.calls if t > time.time() - 3600])}

    def get_config_schema(self):
        flat = {k: v for k, v in DEFAULTS.items() if k != "signals"}
        for name, entry in DEFAULTS["signals"].items():
            for key, value in entry.items():
                flat[f"signals.{name}.{key}"] = value
        names = ((bool, "bool"), (int, "int"), (str, "str"), (list, "list"), (dict, "dict"))
        return {"name": self.name, "keys": {k: {"type": next(n for t, n in names if isinstance(v, t)), "default": v} for k, v in sorted(flat.items())}, "groups": []}

    def snapshot(self):
        status = self.get_status()
        return {"enabled": status["enabled"], "level": status["level"], "status": status, "alerts": self.get_alerts()}
