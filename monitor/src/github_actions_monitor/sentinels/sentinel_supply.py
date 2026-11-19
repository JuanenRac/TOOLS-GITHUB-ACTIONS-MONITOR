# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Supply chain sentinel (2.1.1): what the workflow files of each repository let a moved tag or an outsider do with the repository's token and code. Read only, on a clock of its own, off by default.

It is the fourth sentinel behind `sentinel_base.BaseSentinel`. It reads the folder `.github/workflows` of each repository through the contents API (no clone needed; `integrations/remote_workflows.Reader`,
which never reads again a file whose SHA did not change) and hands the text to the linter of workflows (`delivery/supply.py` -> `cli/lint_workflows.lint_text`): no rule of its own. Signals (each can be switched
off or given another level under `sentinels.supply.signals`):
  actions.supply.unpinned / mutable_ref / permissions_wide / permissions_missing / pr_target_checkout   (see `delivery/supply.py`)
One alert per repository and signal, with the number of findings and a few files and examples in `details`. The value of a secret is never read (the secrets rule of the linter is off here).

A repository whose workflows cannot be read (no access, SSO not authorised, allowance spent, too many files) is NOT an alert and NOT a clean bill of health: it is listed under `unavailable` in the status, the alerts
it already had stay (marked unread) and, if it stays unreadable for a week, they are dropped without an event. A repository without a `.github/workflows` folder is read and has nothing to report.

Cost: a round reads at most `max_repos_per_tick` repositories and `max_calls_per_tick` calls (one to list the folder, one more for each file that is new or changed), the ones read longest ago first and the ones with an open
alert a little sooner, and it pauses while the allowance is below `min_rate_remaining`. The state (`supply_state.json`) keeps the open alerts so that a restart announces nothing again; the first look at a repository
writes no event. Notifications reuse the kinds `security_new` / `security_fixed` (the event says `sentinel: supply`), so the preferences of a user for the security sentinel decide them.
"""
import json
import threading
import time
from datetime import datetime, timezone

from github_actions_monitor import i18n
from github_actions_monitor.app import toolconfig
from github_actions_monitor.cli import lint_workflows
from github_actions_monitor.data_pipeline import events
from github_actions_monitor.delivery import supply
from github_actions_monitor.integrations import remote_workflows
from github_actions_monitor.sentinels import sentinel_base
from github_actions_monitor.storage import state_io
from github_actions_monitor.util import paths

STATE_FILE = paths.place("supply_state.json")
RETRY_AFTER = (300, 1800, 21600)      # seconds a repository whose read fails waits before it is tried again: after the 1st, 2nd, 3rd and later failure in a row
UNREAD_KEEP = 7 * 24 * 3600           # alerts of a repository that stays unreadable are kept (marked unread) this long, then dropped without an event
MIN_COVERAGE = 0.5                    # "nothing open" with fewer readable repositories than this is `unknown`, not `ok`
DEFAULTS = {
    "enabled": False, "refresh_seconds": 3600, "max_repos_per_tick": 10, "deadline_s": 30, "max_calls_per_tick": 60, "max_files_per_repo": 40, "min_rate_remaining": 1000, "repos": "all", "ignore": [], "ignore_uses": [],
    "signals": {name: {"enabled": True, "level": supply.DEFAULT_LEVEL[name]} for name in supply.SIGNALS},
    "penalty": {"per_finding": 2, "cap_per_repo": 10},
}
BOUNDS = {"refresh_seconds": (600, 86400), "max_repos_per_tick": (1, 200), "deadline_s": (0, 600), "max_calls_per_tick": (1, 600), "max_files_per_repo": (1, 100), "min_rate_remaining": (100, 5000)}
TITLE_KEYS = {code: "supply.t." + name for name, code in supply.CODES.items()}


def settings(config):
    """The merged settings of `sentinels.supply` over DEFAULTS: unknown keys are dropped, a value of the wrong type or out of range keeps the default."""
    merged = json.loads(json.dumps(DEFAULTS))
    block = ((config or {}).get("sentinels") or {}).get("supply") if isinstance((config or {}).get("sentinels"), dict) else None
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
    if isinstance(block.get("ignore"), list):
        merged["ignore"] = [x for x in block["ignore"] if isinstance(x, str) and lint_workflows.IGNORE_PATTERN_RE.match(x)][:100]
    if isinstance(block.get("ignore_uses"), list):
        merged["ignore_uses"] = [x for x in block["ignore_uses"] if isinstance(x, str) and supply.USES_RE.match(x)][:100]
    signals = block.get("signals")
    if isinstance(signals, dict):
        for name in supply.SIGNALS:
            entry = signals.get(name)
            if not isinstance(entry, dict):
                continue
            if isinstance(entry.get("enabled"), bool):
                merged["signals"][name]["enabled"] = entry["enabled"]
            if entry.get("level") in supply.LEVELS:
                merged["signals"][name]["level"] = entry["level"]
    penalty = block.get("penalty")
    if isinstance(penalty, dict):
        for key, high in (("per_finding", 20), ("cap_per_repo", 100)):
            value = penalty.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= high:
                merged["penalty"][key] = value
    return merged


def stamp(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path):
    try:
        data = state_io.load_json(path)
        if isinstance(data, dict) and isinstance(data.get("alerts"), dict) and isinstance(data.get("per_repo"), dict):
            data["alerts"] = {str(k): v for k, v in data["alerts"].items() if isinstance(v, dict) and isinstance(v.get("repo"), str) and v.get("code") in TITLE_KEYS}
            data["per_repo"] = {str(k): v for k, v in data["per_repo"].items() if isinstance(v, dict)}
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return {"alerts": {}, "per_repo": {}, "last_full_scan": None}


class SentinelSupply(sentinel_base.BaseSentinel):
    round_cut = False      # the last round stopped for lack of time (deadline_s) and left repositories for the next one
    name = "supply"

    def __init__(self, ctx, config):
        super().__init__(ctx, config)
        self.cfg = settings(config)
        self.lock = threading.RLock()
        self.state = load_state(STATE_FILE)
        self.calls, self.errors, self.paused = [], {}, False
        self.feed = events.Feed(events.EVENTS_FILE, events.STATE_FILE)
        self.reader = remote_workflows.Reader(self._read, toolconfig.github_owner)      # the workflow files, read without a clone

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
        repos, budget = self.scope(), self.cfg["max_calls_per_tick"]
        deadline, self.round_cut = sentinel_base.round_deadline(self.cfg["deadline_s"]), False
        for repo in self._order(repos, now)[:self.cfg["max_repos_per_tick"]]:
            if budget < 1:
                break
            if sentinel_base.expired(deadline):      # the round ran out of time: the rest waits for the next one and is named as not checked
                self.round_cut = True
                break
            try:
                budget -= max(1, self.scan(repo, now, budget))
                self.errors.pop(repo, None)
            except Exception as error:      # one repository that fails never stops the round
                self.errors[repo] = {"message": str(error)[:80], "at": stamp(now)}
                with self.lock:
                    record = self.state["per_repo"].setdefault(repo, {})
                    record["fails"] = int(record.get("fails", 0)) + 1
                    record["tried"] = now
                    record["retry"] = now + RETRY_AFTER[min(record["fails"], len(RETRY_AFTER)) - 1]
            if (self.reader.state(repo) or {}).get("reason") == "rate_limited":
                self.paused = True      # the allowance ran out in the middle of the round: the rest waits for the next one
                break
        with self.lock:
            for gone in [r for r in self.state["per_repo"] if r not in repos]:
                self.state["per_repo"].pop(gone, None)
                self.reader.forget([gone])
            for key in [k for k, a in self.state["alerts"].items() if a["repo"] not in repos]:
                self.state["alerts"].pop(key, None)
            if repos and all((self.state["per_repo"].get(r) or {}).get("scanned") for r in repos):
                self.state["last_full_scan"] = stamp(now)
        self.persist()
        return True

    def scan(self, repo, now, budget):
        """Reads the workflow files of one repository and applies the rules. Returns the calls made."""
        calls = self.reader.refresh(repo, budget, self.cfg["max_files_per_repo"])
        info = self.reader.state(repo) or {}
        with self.lock:
            mine = dict(self.state["per_repo"].get(repo) or {})
        if info.get("state") != "ok":
            # not readable (or only in part) now: what was known is kept, marked unread, instead of being closed as fixed; after UNREAD_KEEP it is dropped without an event
            since = mine.get("unread_since") or now
            mine.update(unread_since=since, unavailable=info.get("reason") or info.get("state") or "error", tried=now, retry=now + RETRY_AFTER[0], files=info.get("files", 0))
            silent = now - since >= UNREAD_KEEP
            with self.lock:
                self.state["per_repo"][repo] = mine
                if silent:
                    for key in [k for k, a in self.state["alerts"].items() if a["repo"] == repo]:
                        self.state["alerts"].pop(key, None)
            return calls
        left = []
        found = supply.findings(repo, self.reader.texts(repo), self.config, toolconfig.github_owner(), self.cfg["ignore"], self.cfg["ignore_uses"], left)
        self._commit(repo, found, info, now, len(left))
        return calls

    def _commit(self, repo, found, info, now, left_out=0):
        """Applies the rules to what was read of one repository, replaces its alerts, and writes the events of what changed (nothing the first time the repository is looked at)."""
        with self.lock:
            before = {k: a for k, a in self.state["alerts"].items() if a["repo"] == repo}
            first = not (self.state["per_repo"].get(repo) or {}).get("scanned")
            alerts = supply.evaluate(repo, found, self.cfg["signals"], before, stamp(now))
            for key in before:
                self.state["alerts"].pop(key, None)
            self.state["alerts"].update(alerts)
            self.state["per_repo"][repo] = {"scanned": now, "files": info.get("files", 0), "skipped": list(info.get("skipped") or [])[:20], "truncated": bool(info.get("truncated")), "uses_left_out": int(left_out)}
        if first:
            return
        out = [self._event("security_new", alerts[k]) for k in alerts if k not in before] + [self._event("security_fixed", before[k]) for k in before if k not in alerts]
        if out:
            self.feed.emit(out)

    def _title(self, alert):
        d = alert.get("detail") or {}
        return i18n.t(TITLE_KEYS[alert["code"]], repo=alert["repo"], n=d.get("n", 0), files=d.get("files_total", 0))

    def _event(self, kind, alert):
        return {"kind": kind, "code": alert["code"], "level": ("ok" if kind == "security_fixed" else ("bad" if alert["level"] in ("critical", "error") else "warn")), "repo": alert["repo"],
                "owner": events.owner_of(alert["repo"]), "sentinel": self.name, "account_id": self.account_id, "text": i18n.t("evt." + kind, title=self._title(alert)), "url": None,
                "args": {"signal": supply.SIGNAL_OF[alert["code"]], **{k: v for k, v in (alert.get("detail") or {}).items() if isinstance(v, (int, str))}}}

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
                 "details": {"signal": supply.SIGNAL_OF[a["code"]], **(a.get("detail") or {}), "updated": a["created_at"], **({"unread_since": stamp(unread[a["repo"]])} if a["repo"] in unread else {})},
                 "created_at": a["created_at"]} for a in sorted(items, key=lambda x: x["id"])]

    def unavailable(self):
        """{reason: number of repositories whose workflows cannot be read} (no access, SSO, allowance, too many files...)."""
        out = {}
        with self.lock:
            for record in self.state["per_repo"].values():
                if record.get("unread_since"):
                    reason = str(record.get("unavailable") or "error")
                    out[reason] = out.get(reason, 0) + 1
        return out

    def get_status(self):
        """The state, with its `lifecycle` (healthy | degraded | paused | error | off): no alerts only means something when it is healthy."""
        status = self._status()
        status["lifecycle"] = sentinel_base.lifecycle(status)
        return status

    def _status(self):
        if not self.enabled:
            return {"enabled": False, "level": "off", "loading": "", "errors": [], "refresh_seconds": self.refresh_seconds, "repos_in_scope": 0, "repos_checked": 0, "last_full_scan": None, "paused": False,
                    "unavailable": {}, "partial": 0, "uses_left_out": 0}
        repos = self.scope()
        with self.lock:
            records = [self.state["per_repo"].get(r) or {} for r in repos]
            checked = sum(1 for rec in records if rec.get("scanned") or rec.get("unread_since"))
            readable = sum(1 for rec in records if rec.get("scanned") and not rec.get("unread_since"))
            partial = sum(1 for rec in records if rec.get("scanned") and (rec.get("skipped") or rec.get("truncated")))
            alerts = list(self.state["alerts"].values())
            last = self.state["last_full_scan"]
        level = "unknown" if not checked else ("bad" if any(a["level"] in ("critical", "error") for a in alerts) else ("warn" if alerts else "ok"))
        if level == "ok" and checked and readable / checked < MIN_COVERAGE:
            level = "unknown"      # nothing open because most of what was looked at could not be read: not a clean bill of health
        return {"enabled": True, "level": level, "loading": "" if checked or not repos else "starting", "errors": [{"section": r, "at": e["at"]} for r, e in sorted(self.errors.items())],
                "refresh_seconds": self.refresh_seconds, "repos_in_scope": len(repos), "repos_checked": checked, "repos_readable": readable, "last_full_scan": last, "paused": self.paused,
                "unavailable": self.unavailable(), "partial": partial, "uses_left_out": sum(int(rec.get("uses_left_out") or 0) for rec in records), "unchecked": sentinel_base.unchecked(repos, self.state["per_repo"]), "round_cut": self.round_cut}

    def get_metrics(self):
        if not self.enabled:
            return {}
        with self.lock:
            alerts = list(self.state["alerts"].values())
        status = self.get_status()
        return {"supply_alerts": len(alerts), "supply_findings": sum(int((a.get("detail") or {}).get("n", 1)) for a in alerts), "supply_penalty": supply.penalty(alerts, self.cfg["penalty"]["per_finding"], self.cfg["penalty"]["cap_per_repo"]),
                "supply_repos_checked": status["repos_checked"], "supply_repos_unreadable": sum(status["unavailable"].values()), "supply_calls_last_hour": len([t for t in self.calls if t > time.time() - 3600])}

    def get_config_schema(self):
        flat = {k: v for k, v in DEFAULTS.items() if k not in ("signals", "penalty")}
        for name, entry in DEFAULTS["signals"].items():
            for key, value in entry.items():
                flat[f"signals.{name}.{key}"] = value
        names = ((bool, "bool"), (int, "int"), (str, "str"), (list, "list"), (dict, "dict"))
        return {"name": self.name, "keys": {k: {"type": next(n for t, n in names if isinstance(v, t)), "default": v} for k, v in sorted(flat.items())}, "groups": []}

    def snapshot(self):
        status = self.get_status()
        return {"enabled": status["enabled"], "level": status["level"], "status": status, "alerts": self.get_alerts()}
