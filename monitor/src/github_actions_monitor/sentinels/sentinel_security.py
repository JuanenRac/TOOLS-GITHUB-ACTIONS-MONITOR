# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Security sentinel (1.9.1): what GitHub itself says is open or missing about the security of each repository, on a clock of its own and read only.

It is the third sentinel behind the contract of `sentinel_base.BaseSentinel` (after the CI one and Collab). It never writes to GitHub: every call is a GET, conditional (a repository that did not
change costs no allowance), and nothing else is read or sent.

What it reads, per repository, and the alert each signal can raise (all of it can be tuned or switched off under `sentinels.security.signals`):
  security.dependabot          open Dependabot alerts, counted by severity (from `signals.dependabot.min_severity` up)
  security.code_scanning       open code scanning alerts, the same
  security.secret              open secret scanning alerts (always critical: a secret that GitHub found is a secret that is out)
  security.branch_unprotected  the default branch has no protection at all
  security.workflow_write      the workflows get write permission on the repository by default
  security.codeowners_missing  there is no CODEOWNERS file (off by default: many repositories do not want one)
One alert per repository and signal, with the counts in `details`. A signal that GitHub does not answer for a repository (the feature is off, or the login may not read it: 403, 404) is NOT an
alert and NOT a clean bill of health: it is listed under `unavailable` in the status, so "no alerts" is never mistaken for "could not be checked".

Frontier with the CI sentinel (one owner per finding): the panels A3 (alerts by repository), A10 (coverage, aged alerts) and A4 (Dependabot pull requests) of the CI sentinel stay panels; the alerts
of the Alerts tab about these signals come only from here.

Cost: a round reads at most `max_repos_per_tick` repositories (seven calls each at most, most of them answered 304), the ones scanned longest ago first and the ones with an open alert a little sooner,
and it pauses while the allowance is below `min_rate_remaining`. The state (`security_state.json`) keeps the open alerts so that a restart announces nothing again; the events of the first look at a
repository are not written. The metrics carry `security_penalty`: points taken off the security part of the score for what is open.
"""
import json
import threading
import time
from datetime import datetime, timezone

from github_actions_monitor.data_pipeline import etagcache
from github_actions_monitor.data_pipeline import events
from github_actions_monitor import i18n
from github_actions_monitor.sentinels import sentinel_base
from github_actions_monitor.app import toolconfig
from github_actions_monitor.storage import state_io

from github_actions_monitor.util import paths
STATE_FILE = paths.place("security_state.json")
PER_PAGE = 100
CODEOWNERS_EVERY = 24 * 3600          # a repository without a CODEOWNERS file is looked at again this often (three reads)
CODEOWNERS_PATHS = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
SEVERITIES = ("low", "medium", "high", "critical")
SIGNALS = ("dependabot", "code_scanning", "secret", "branch", "workflow", "codeowners")
DEFAULTS = {
    "enabled": False, "refresh_seconds": 1800, "max_repos_per_tick": 5, "min_rate_remaining": 1500, "repos": "all",
    "signals": {"dependabot": {"enabled": True, "min_severity": "high"}, "code_scanning": {"enabled": True, "min_severity": "high"}, "secret": {"enabled": True},
                "branch": {"enabled": True}, "workflow": {"enabled": True}, "codeowners": {"enabled": False}},
    "penalty": {"critical": 25, "high": 10, "medium": 3, "low": 1, "branch": 5, "workflow": 3, "codeowners": 1},
}
BOUNDS = {"refresh_seconds": (300, 86400), "max_repos_per_tick": (1, 100), "min_rate_remaining": (100, 5000)}
TITLE_KEYS = {"security.dependabot": "security.t.dependabot", "security.code_scanning": "security.t.code_scanning", "security.secret": "security.t.secret",
              "security.branch_unprotected": "security.t.branch", "security.workflow_write": "security.t.workflow", "security.codeowners_missing": "security.t.codeowners"}
SIGNAL_OF = {"security.dependabot": "dependabot", "security.code_scanning": "code_scanning", "security.secret": "secret", "security.branch_unprotected": "branch",
             "security.workflow_write": "workflow", "security.codeowners_missing": "codeowners"}


def settings(config):
    """The merged settings of `sentinels.security` over DEFAULTS: unknown keys are dropped, a value of the wrong type or out of range keeps the default."""
    merged = json.loads(json.dumps(DEFAULTS))
    block = ((config or {}).get("sentinels") or {}).get("security") if isinstance((config or {}).get("sentinels"), dict) else None
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
    signals = block.get("signals")
    if isinstance(signals, dict):
        for name in SIGNALS:
            entry = signals.get(name)
            if not isinstance(entry, dict):
                continue
            if isinstance(entry.get("enabled"), bool):
                merged["signals"][name]["enabled"] = entry["enabled"]
            if "min_severity" in merged["signals"][name] and entry.get("min_severity") in SEVERITIES:
                merged["signals"][name]["min_severity"] = entry["min_severity"]
    penalty = block.get("penalty")
    if isinstance(penalty, dict):
        for key in DEFAULTS["penalty"]:
            value = penalty.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100:
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


def severity_of(kind, raw):
    """low | medium | high | critical of one raw alert of the API (Dependabot or code scanning); medium when GitHub does not say."""
    if kind == "dependabot":
        value = ((raw.get("security_advisory") or {}).get("severity") or (raw.get("security_vulnerability") or {}).get("severity") or "").lower()
    else:
        rule = raw.get("rule") or {}
        value = (rule.get("security_severity_level") or {"error": "high", "warning": "medium", "note": "low"}.get(str(rule.get("severity") or "").lower(), "")).lower()
    return value if value in SEVERITIES else "medium"


def counts(kind, items, min_severity):
    """{"n", "critical", "high", "medium", "low"} of the alerts at or above the least severity wanted."""
    floor = SEVERITIES.index(min_severity)
    out = {"n": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
    for raw in items:
        if not isinstance(raw, dict):
            continue
        level = severity_of(kind, raw)
        if SEVERITIES.index(level) >= floor:
            out["n"] += 1
            out[level] += 1
    return out


def evaluate(repo, facts, cfg, now, known=None):
    """{alert id: alert} of one repository from the facts read about it (see `SentinelSecurity.scan`), at time `now`. Pure. `known` are the alerts already open (they keep their `created_at`)."""
    known, found = known or {}, {}
    rules = cfg["signals"]

    def add(code, level, **detail):
        key = f"{code}:{repo}"
        found[key] = {"id": key, "code": code, "level": level, "repo": repo, "detail": detail, "created_at": (known.get(key) or {}).get("created_at") or stamp(now)}

    for kind, code in (("dependabot", "security.dependabot"), ("code_scanning", "security.code_scanning")):
        fact = facts.get(kind)
        if rules[kind]["enabled"] and isinstance(fact, dict) and fact.get("items") is not None:
            c = counts(kind, fact["items"], rules[kind]["min_severity"])
            if c["n"]:
                add(code, "critical" if c["critical"] else ("error" if c["high"] else "warning"), **c)
    secret = facts.get("secret")
    if rules["secret"]["enabled"] and isinstance(secret, dict) and secret.get("items"):
        add("security.secret", "critical", n=len(secret["items"]))
    if rules["branch"]["enabled"] and facts.get("branch_protected") is False:
        add("security.branch_unprotected", "warning", branch=facts.get("default_branch") or "")
    if rules["workflow"]["enabled"] and facts.get("workflow_permissions") == "write":
        add("security.workflow_write", "warning")
    if rules["codeowners"]["enabled"] and facts.get("codeowners") is False:
        add("security.codeowners_missing", "info")
    return found


def penalty(alerts, cfg):
    """Points taken off the security part of the score for the open alerts: severity weights for Dependabot and code scanning, the critical weight per secret, a flat one for the rest."""
    weights, total = cfg["penalty"], 0.0
    for a in alerts:
        d = a.get("detail") or {}
        if a["code"] in ("security.dependabot", "security.code_scanning"):
            total += sum(d.get(level, 0) * weights[level] for level in SEVERITIES)
        elif a["code"] == "security.secret":
            total += d.get("n", 1) * weights["critical"]
        elif a["code"] == "security.branch_unprotected":
            total += weights["branch"]
        elif a["code"] == "security.workflow_write":
            total += weights["workflow"]
        elif a["code"] == "security.codeowners_missing":
            total += weights["codeowners"]
    return total


class SentinelSecurity(sentinel_base.BaseSentinel):
    name = "security"

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

    # -- reading (GET only)
    def _count(self):
        with self.lock:
            self.calls.append(time.time())
            self.calls = [t for t in self.calls if t > time.time() - 3600]

    def fetch(self, endpoint, etag=""):
        """(status, parsed body or None, etag): a conditional read. 304 = unchanged; 403/404/451 are answers, not failures (the feature is off or may not be read). Anything else raises."""
        self._count()
        run = (self.ctx or {}).get("run_gh")
        if run is None:
            data = self.ctx["gh"]("api", endpoint, retries=1)
            return 200, data, ""
        code, out, err = run(["api", "-i"] + (["-H", f"If-None-Match: {etag}"] if etag else []) + [endpoint])
        status, headers, body = etagcache.split_response(out)
        if status == 304 and etag:
            return 304, None, etag
        if status in (403, 404, 451):
            return status, None, ""
        if code != 0 or status not in (200, 0):
            raise RuntimeError((err or out or "gh failed").strip()[:200])
        try:
            data = json.loads(body) if body.strip() else None
        except ValueError:
            raise RuntimeError("the answer of the API is not valid JSON") from None
        tag = headers.get("etag", "")
        return 200, data, (tag if etagcache.ETAG_RE.match(tag) else "")

    def scope(self):
        repos = list(self.ctx["repos_fn"]())
        wanted = self.cfg["repos"]
        if isinstance(wanted, list):
            return [r for r in repos if r in wanted]
        if isinstance(wanted, dict):
            return [r for r in repos if self.ctx["eco_fn"](r) in wanted["ecosystems"]]
        return repos

    def _order(self, repos):
        open_in = {a["repo"] for a in self.state["alerts"].values()}
        return sorted(repos, key=lambda r: ((self.state["per_repo"].get(r) or {}).get("scanned", 0) - (self.refresh_seconds * 3 if r in open_in else 0), r))

    # -- one round
    def tick(self, now=None):
        if not self.enabled:
            return False
        now = time.time() if now is None else now
        rate = ((self.ctx.get("data_fn") or (lambda: None))() or {}).get("rate")
        self.paused = bool(rate and rate.get("remaining", 10 ** 9) < self.cfg["min_rate_remaining"])
        if self.paused:
            return False
        repos = self.scope()
        for repo in self._order(repos)[:self.cfg["max_repos_per_tick"]]:
            try:
                self.scan(repo, now)
                self.errors.pop(repo, None)
            except Exception as error:      # one repository that fails never stops the round
                self.errors[repo] = {"message": str(error)[:80], "at": stamp(now)}
                with self.lock:
                    self.state["per_repo"].setdefault(repo, {})["retry"] = now + 300
        with self.lock:
            for gone in [r for r in self.state["per_repo"] if r not in repos]:
                self.state["per_repo"].pop(gone, None)
            for key in [k for k, a in self.state["alerts"].items() if a["repo"] not in repos]:
                self.state["alerts"].pop(key, None)
            if repos and all((self.state["per_repo"].get(r) or {}).get("scanned") for r in repos):
                self.state["last_full_scan"] = stamp(now)
        self.persist()
        return True

    def scan(self, repo, now):
        owner = toolconfig.github_owner()
        with self.lock:
            mine = dict(self.state["per_repo"].get(repo) or {})
        etag, facts, unavailable = dict(mine.get("etag") or {}), dict(mine.get("facts") or {}), dict(mine.get("unavailable") or {})
        rules = self.cfg["signals"]

        def read(key, endpoint):
            """Reads one source; returns (status, body). A 304 keeps what was known; 403/404 mark the source unavailable for this repository."""
            status, body, tag = self.fetch(endpoint, etag.get(key, ""))
            if status == 200:
                etag[key] = tag
                unavailable.pop(key, None)
            elif status in (403, 404, 451):
                etag.pop(key, None)
                unavailable[key] = status
            return status, body

        status, body = read("repo", f"repos/{owner}/{repo}")
        if status == 200 and isinstance(body, dict):
            facts["default_branch"] = body.get("default_branch") or "main"
            facts["archived"] = bool(body.get("archived"))
        if facts.get("archived"):
            facts = {"default_branch": facts.get("default_branch"), "archived": True}      # an archived repository is read-only: nothing to ask of it
        else:
            for kind, key, endpoint in (("dependabot", "dependabot", "dependabot/alerts"), ("code_scanning", "code_scanning", "code-scanning/alerts"), ("secret", "secret", "secret-scanning/alerts")):
                if not rules[kind]["enabled"]:
                    continue
                status, body = read(key, f"repos/{owner}/{repo}/{endpoint}?state=open&per_page={PER_PAGE}")
                if status == 200:
                    facts[kind] = {"items": [i for i in (body if isinstance(body, list) else []) if isinstance(i, dict)][:PER_PAGE]}
                elif status != 304:
                    facts.pop(kind, None)
            if rules["branch"]["enabled"]:
                status, _body = read("branch", f"repos/{owner}/{repo}/branches/{facts.get('default_branch') or 'main'}/protection")
                if status == 200:
                    facts["branch_protected"] = True
                elif status == 404:      # "Branch not protected": the answer for an unprotected branch (403 is a login that may not read it: unavailable, not a finding)
                    facts["branch_protected"] = False
                    unavailable.pop("branch", None)
                elif status != 304:
                    facts.pop("branch_protected", None)
            if rules["workflow"]["enabled"]:
                status, body = read("workflow", f"repos/{owner}/{repo}/actions/permissions/workflow")
                if status == 200 and isinstance(body, dict):
                    facts["workflow_permissions"] = body.get("default_workflow_permissions")
                elif status != 304:
                    facts.pop("workflow_permissions", None)
            if rules["codeowners"]["enabled"] and (facts.get("codeowners") is not True) and now - mine.get("codeowners_at", 0) >= CODEOWNERS_EVERY:
                found_file = False
                for path in CODEOWNERS_PATHS:
                    status, _body, _tag = self.fetch(f"repos/{owner}/{repo}/contents/{path}")
                    if status == 200:
                        found_file = True
                        break
                facts["codeowners"] = found_file
                mine["codeowners_at"] = now
        self._commit(repo, facts, etag, unavailable, mine.get("codeowners_at", 0), now)

    def _commit(self, repo, facts, etag, unavailable, codeowners_at, now):
        """Applies the rules to what is known of one repository, replaces its alerts, and writes the events of what changed (nothing the first time the repository is looked at)."""
        with self.lock:
            before = {k: a for k, a in self.state["alerts"].items() if a["repo"] == repo}
            first = not (self.state["per_repo"].get(repo) or {}).get("scanned")
            found = evaluate(repo, facts, self.cfg, now, before)
            for key in before:
                self.state["alerts"].pop(key, None)
            self.state["alerts"].update(found)
            self.state["per_repo"][repo] = {"scanned": now, "etag": etag, "facts": facts, "unavailable": unavailable, "codeowners_at": codeowners_at}
        if first:
            return
        out = [self._event("security_new", found[k]) for k in found if k not in before] + [self._event("security_fixed", before[k]) for k in before if k not in found]
        if out:
            self.feed.emit(out)

    def _title(self, alert):
        d = alert.get("detail") or {}
        return i18n.t(TITLE_KEYS[alert["code"]], repo=alert["repo"], n=d.get("n", 0), critical=d.get("critical", 0), high=d.get("high", 0), branch=d.get("branch", ""))

    def _event(self, kind, alert):
        title = self._title(alert)
        return {"kind": kind, "code": alert["code"], "level": ("ok" if kind == "security_fixed" else ("bad" if alert["level"] in ("critical", "error") else "warn")), "repo": alert["repo"],
                "owner": events.owner_of(alert["repo"]), "sentinel": self.name, "account_id": self.account_id, "text": i18n.t("evt." + kind, title=title), "url": None,
                "args": {"signal": SIGNAL_OF[alert["code"]], **{k: v for k, v in (alert.get("detail") or {}).items() if isinstance(v, (int, str))}}}

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
        return [{"id": a["id"], "code": a["code"], "level": a["level"], "sentinel": self.name, "account_id": self.account_id, "repo": a["repo"], "title": self._title(a),
                 "details": {"signal": SIGNAL_OF[a["code"]], **(a.get("detail") or {}), "updated": a["created_at"]}, "created_at": a["created_at"]} for a in sorted(items, key=lambda x: x["id"])]

    def unavailable(self):
        """{signal: number of repositories where GitHub does not answer it} (the feature is off or the login may not read it)."""
        names = {"dependabot": "dependabot", "code_scanning": "code_scanning", "secret": "secret", "branch": "branch", "workflow": "workflow"}
        out = {}
        with self.lock:
            for record in self.state["per_repo"].values():
                for key in (record.get("unavailable") or {}):
                    if key in names:
                        out[names[key]] = out.get(names[key], 0) + 1
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
            checked = sum(1 for r in repos if (self.state["per_repo"].get(r) or {}).get("scanned"))
            alerts = list(self.state["alerts"].values())
            last = self.state["last_full_scan"]
        level = "unknown" if not checked else ("bad" if any(a["level"] in ("critical", "error") for a in alerts) else ("warn" if alerts else "ok"))
        return {"enabled": True, "level": level, "loading": "" if checked or not repos else "starting", "errors": [{"section": r, "at": e["at"]} for r, e in sorted(self.errors.items())],
                "refresh_seconds": self.refresh_seconds, "repos_in_scope": len(repos), "repos_checked": checked, "last_full_scan": last, "paused": self.paused, "unavailable": self.unavailable()}

    def get_metrics(self):
        if not self.enabled:
            return {}
        with self.lock:
            alerts = list(self.state["alerts"].values())
        return {"security_alerts": len(alerts), "security_critical": sum(1 for a in alerts if a["level"] == "critical"), "security_penalty": penalty(alerts, self.cfg),
                "security_repos_checked": self.get_status()["repos_checked"], "security_calls_last_hour": len([t for t in self.calls if t > time.time() - 3600])}

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
