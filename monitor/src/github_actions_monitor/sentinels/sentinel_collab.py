# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Collab sentinel (1.7.3): open issues and pull requests that need a person, on a clock of its own and read only.

It is the second sentinel behind the contract of `sentinel_base.BaseSentinel` (the first is the CI one). It never writes to GitHub: every call is a GET of the list of open issues and the list
of open pull requests of one repository (conditional reads through the same client and cache as the rest of the monitor, so a repository that did not change costs no allowance), plus, for
the pull requests that could conflict, the detail of the pull request. Nothing else is read and nothing is sent.

What it flags (all of it can be tuned or silenced under `sentinels.collab.rules`):
  collab.issue.stale       an open issue with no activity for `issue_stale_days`
  collab.issue.critical    an open issue with one of the `issue_critical_labels` (always, whatever its age)
  collab.issue.external    (only with `watch_external_comments`) an issue opened by someone outside the team that nobody has answered after a day
  collab.pr.review_pending a pull request with a requested review that has waited `pr_review_pending_days`
  collab.pr.draft_old      a draft pull request older than `pr_draft_max_days`
  collab.pr.conflict       a pull request that has had conflicts for `pr_conflict_days`
Bots are left out (the Dependabot pull requests are the A4 check of the CI sentinel), and so is anything that carries one of the `ignore_labels` (`monitor:ignore` by default; the label is put by a person on
GitHub, the monitor never writes one). A silence of the monitor itself (an alert, a rule or the whole sentinel for some hours) is made in the Alerts tab (`alert_center.py`).

Cost: a round reads at most `max_repos_per_tick` repositories, two calls each (and up to six pull request details per round), the ones scanned longest ago first and the ones with an open
alert a little sooner, and it pauses while the allowance is below `min_rate_remaining`. One page of 100 per list: a repository with more than 100 open issues is read by recency. The state
(`collab_state.json`, next to the monitor) keeps the open alerts so that a restart announces nothing again; the events of the first look at a repository are not written (only the changes after it).
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from github_actions_monitor.data_pipeline import etagcache
from github_actions_monitor.data_pipeline import events
from github_actions_monitor import i18n
from github_actions_monitor.sentinels import sentinel_base
from github_actions_monitor.app import toolconfig
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import state_io

from github_actions_monitor.util.paths import ROOT as HERE   # the product folder: the data of the person who runs the monitor stays there
STATE_FILE = HERE / "collab_state.json"
PER_PAGE = 100
DETAILS_PER_TICK = 6                 # pull request details read in one round (the only calls beyond the two lists of a repository)
DETAIL_EVERY = 6 * 3600              # a pull request is looked at again for conflicts at most this often
OUTSIDE = ("NONE", "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "CONTRIBUTOR", "MANNEQUIN")      # author_association of someone who is not part of the team
DEFAULTS = {
    "enabled": False, "refresh_seconds": 600, "max_repos_per_tick": 10, "min_rate_remaining": 1000, "repos": "all",
    "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3, "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": False, "ignore_labels": ["monitor:ignore"]},
}
BOUNDS = {"refresh_seconds": (60, 86400), "max_repos_per_tick": (1, 100), "min_rate_remaining": (100, 5000), "issue_stale_days": (1, 365), "pr_review_pending_days": (1, 90),
          "pr_draft_max_days": (1, 365), "pr_conflict_days": (1, 90)}
TITLE_KEYS = {"collab.issue.stale": "collab.t.issue_stale", "collab.issue.critical": "collab.t.issue_critical", "collab.issue.external": "collab.t.issue_external",
              "collab.pr.review_pending": "collab.t.pr_review", "collab.pr.draft_old": "collab.t.pr_draft", "collab.pr.conflict": "collab.t.pr_conflict"}
LEVELS = {"collab.issue.stale": "warning", "collab.issue.critical": "error", "collab.issue.external": "warning", "collab.pr.review_pending": "warning", "collab.pr.draft_old": "info",
          "collab.pr.conflict": "warning"}


def settings(config):
    """The merged settings of `sentinels.collab` over DEFAULTS: unknown keys are dropped, a value of the wrong type or out of range keeps the default."""
    merged = json.loads(json.dumps(DEFAULTS))
    block = ((config or {}).get("sentinels") or {}).get("collab") if isinstance((config or {}).get("sentinels"), dict) else None
    if not isinstance(block, dict):
        return merged

    def number(value, key):
        low, high = BOUNDS[key]
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else None

    if isinstance(block.get("enabled"), bool):
        merged["enabled"] = block["enabled"]
    for key in ("refresh_seconds", "max_repos_per_tick", "min_rate_remaining"):
        if number(block.get(key), key) is not None:
            merged[key] = block[key]
    repos = block.get("repos")
    if repos == "all" or (isinstance(repos, list) and all(isinstance(r, str) for r in repos)) or (isinstance(repos, dict) and isinstance(repos.get("ecosystems"), list)):
        merged["repos"] = repos
    rules = block.get("rules")
    if isinstance(rules, dict):
        for key in ("issue_stale_days", "pr_review_pending_days", "pr_draft_max_days", "pr_conflict_days"):
            if number(rules.get(key), key) is not None:
                merged["rules"][key] = rules[key]
        labels = rules.get("issue_critical_labels")
        if isinstance(labels, list) and all(isinstance(x, str) for x in labels):
            merged["rules"]["issue_critical_labels"] = labels[:50]
        ignore = rules.get("ignore_labels")
        if isinstance(ignore, list) and all(isinstance(x, str) for x in ignore):
            merged["rules"]["ignore_labels"] = ignore[:50]
        if isinstance(rules.get("watch_external_comments"), bool):
            merged["rules"]["watch_external_comments"] = rules["watch_external_comments"]
    return merged


def parse_time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() if text else None
    except (TypeError, ValueError):
        return None


def stamp(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path):
    try:
        data = state_io.load_json(path)
        if isinstance(data, dict) and isinstance(data.get("alerts"), dict) and isinstance(data.get("per_repo"), dict):
            # a hand-edited or half-written file keeps only the entries the rest of the code can read (an alert is a dict with a repo, a repository record is a dict)
            data["alerts"] = {str(k): v for k, v in data["alerts"].items() if isinstance(v, dict) and isinstance(v.get("repo"), str)}
            data["per_repo"] = {str(k): v for k, v in data["per_repo"].items() if isinstance(v, dict)}
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return {"alerts": {}, "per_repo": {}, "last_full_scan": None}


def slim_issue(raw):
    """What is kept of an issue: enough to apply every rule again later without asking GitHub (no body, no author name)."""
    return {"number": raw.get("number"), "title": str(raw.get("title") or "")[:140], "url": str(raw.get("html_url") or ""), "created": raw.get("created_at"), "updated": raw.get("updated_at"),
            "labels": [str(l.get("name", ""))[:60] for l in raw.get("labels") or [] if isinstance(l, dict)][:30], "bot": (raw.get("user") or {}).get("type") == "Bot",
            "assoc": raw.get("author_association"), "comments": int(raw.get("comments") or 0)}


def slim_pull(raw, before=None):
    """The same for a pull request; the notes about conflicts (`dirty_since`, `checked`, `seen`) are carried over from the previous look."""
    before = before or {}
    return {"number": raw.get("number"), "title": str(raw.get("title") or "")[:140], "url": str(raw.get("html_url") or ""), "created": raw.get("created_at"), "updated": raw.get("updated_at"),
            "draft": bool(raw.get("draft")), "labels": [str(l.get("name", ""))[:60] for l in raw.get("labels") or [] if isinstance(l, dict)][:30], "review_requested": bool(raw.get("requested_reviewers") or raw.get("requested_teams")), "bot": (raw.get("user") or {}).get("type") == "Bot",
            "dirty_since": before.get("dirty_since"), "checked": before.get("checked", 0), "seen": before.get("seen")}


def evaluate(repo, issues, prs, rules, now, known=None):
    """{alert id: alert} of one repository from its slim issues and pull requests, at time `now` (seconds). Pure: no reading, no writing. `known` are the alerts already open (they keep their `created_at`)."""
    known, found = known or {}, {}
    critical = {x.lower() for x in rules["issue_critical_labels"]}
    ignored = {x.lower() for x in rules.get("ignore_labels") or []}       # a label put on GitHub by a person: the item raises no alert (the monitor never writes labels)

    def days(ref):
        when = parse_time(ref)
        return None if when is None else (now - when) / 86400

    def add(code, item, ref, labels=None):
        key = f"{code}:{repo}:{item['number']}"
        found[key] = {"id": key, "code": code, "level": LEVELS[code], "repo": repo, "number": item["number"], "title": item["title"], "url": item["url"], "ref": ref, "labels": labels or [], "updated": item.get("updated"),
                      "created_at": (known.get(key) or {}).get("created_at") or stamp(now)}

    for issue in issues:
        if issue.get("bot") or ignored & {l.lower() for l in issue["labels"]}:
            continue
        hit = [l for l in issue["labels"] if l.lower() in critical]
        idle, age = days(issue["updated"]), days(issue["created"])
        if hit:
            add("collab.issue.critical", issue, issue["updated"], hit)
        elif idle is not None and idle >= rules["issue_stale_days"]:
            add("collab.issue.stale", issue, issue["updated"])
        if rules["watch_external_comments"] and issue.get("assoc") in OUTSIDE and not issue.get("comments") and age is not None and age >= 1:
            add("collab.issue.external", issue, issue["created"])
    for pull in prs:
        if pull.get("bot") or ignored & {l.lower() for l in pull.get("labels") or []}:
            continue
        age, idle = days(pull["created"]), days(pull["updated"])
        if pull["draft"]:
            if age is not None and age >= rules["pr_draft_max_days"]:
                add("collab.pr.draft_old", pull, pull["created"])
            continue
        if pull["review_requested"] and idle is not None and idle >= rules["pr_review_pending_days"]:
            add("collab.pr.review_pending", pull, pull["updated"])
        if pull.get("dirty_since") and (now - pull["dirty_since"]) / 86400 >= rules["pr_conflict_days"]:
            add("collab.pr.conflict", pull, stamp(pull["dirty_since"]))
    return found


class SentinelCollab(sentinel_base.BaseSentinel):
    name = "collab"

    def __init__(self, ctx, config):
        super().__init__(ctx, config)
        self.cfg = settings(config)
        self.lock = threading.RLock()
        self.state = load_state(STATE_FILE)
        self.calls, self.errors, self.paused = [], {}, False
        self.feed = events.Feed(events.EVENTS_FILE, events.STATE_FILE)      # the paths of now: an account redirects them before this is built

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

    def fetch_list(self, endpoint, etag):
        """(status, list or None, etag): a conditional read of one list. 304 = unchanged (no allowance used). Without the `run_gh` of the monitor (a test, a script) it is a plain read."""
        self._count()
        run = (self.ctx or {}).get("run_gh")
        if run is None:
            data = self.ctx["gh"]("api", endpoint, retries=1)
            return 200, (data if isinstance(data, list) else []), ""
        code, out, err = run(["api", "-i"] + (["-H", f"If-None-Match: {etag}"] if etag else []) + [endpoint])
        status, headers, body = etagcache.split_response(out)
        if status == 304 and etag:
            return 304, None, etag
        if code != 0 or status not in (200, 0):
            raise RuntimeError((err or out or "gh failed").strip()[:200])
        try:
            data = json.loads(body) if body.strip() else []
        except ValueError:
            raise RuntimeError("the answer of the API is not valid JSON") from None
        tag = headers.get("etag", "")
        return 200, (data if isinstance(data, list) else []), (tag if etagcache.ETAG_RE.match(tag) else "")

    def read_one(self, endpoint):
        self._count()
        data = self.ctx["gh"]("api", endpoint, retries=1)
        return data if isinstance(data, dict) else {}

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
        budget = [DETAILS_PER_TICK]
        for repo in self._order(repos)[:self.cfg["max_repos_per_tick"]]:
            try:
                self.scan(repo, now, budget)
                self.errors.pop(repo, None)
            except Exception as error:     # one repository that fails never stops the round
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

    def scan(self, repo, now, budget):
        owner = toolconfig.github_owner()
        with self.lock:
            mine = dict(self.state["per_repo"].get(repo) or {})
        etag = dict(mine.get("etag") or {})
        issues, prs = mine.get("issues") or [], mine.get("prs") or []
        status, data, tag = self.fetch_list(f"repos/{owner}/{repo}/issues?state=open&sort=updated&direction=desc&per_page={PER_PAGE}", etag.get("issues", "") if mine.get("issues") is not None else "")
        if status == 200:
            issues, etag["issues"] = [slim_issue(i) for i in data if isinstance(i, dict) and "pull_request" not in i], tag      # the issues list also holds the pull requests: they are the other list
        status, data, tag = self.fetch_list(f"repos/{owner}/{repo}/pulls?state=open&sort=updated&direction=desc&per_page={PER_PAGE}", etag.get("pulls", "") if mine.get("prs") is not None else "")
        if status == 200:
            before = {p["number"]: p for p in prs}
            prs, etag["pulls"] = [slim_pull(p, before.get(p.get("number"))) for p in data if isinstance(p, dict)], tag
        for pull in prs:
            if pull["draft"] or pull["bot"]:
                continue
            due = pull.get("seen") != pull["updated"] or now - pull.get("checked", 0) >= DETAIL_EVERY
            if due and budget[0] > 0:
                budget[0] -= 1
                dirty = self.read_one(f"repos/{owner}/{repo}/pulls/{pull['number']}").get("mergeable_state") == "dirty"
                pull["dirty_since"] = (pull.get("dirty_since") or now) if dirty else None
                pull["checked"], pull["seen"] = now, pull["updated"]
        self._commit(repo, issues, prs, etag, now)

    def _commit(self, repo, issues, prs, etag, now):
        """Applies the rules to what is known of one repository, replaces its alerts, and writes the events of what changed (nothing the first time the repository is looked at)."""
        with self.lock:
            before = {k: a for k, a in self.state["alerts"].items() if a["repo"] == repo}
            first = not (self.state["per_repo"].get(repo) or {}).get("scanned")
            found = evaluate(repo, issues, prs, self.cfg["rules"], now, before)
            for key in before:
                self.state["alerts"].pop(key, None)
            self.state["alerts"].update(found)
            self.state["per_repo"][repo] = {"scanned": now, "etag": etag, "issues": issues, "prs": prs}
        if first:
            return
        out = [self._event("collab_new", found[k]) for k in found if k not in before] + [self._event("collab_fixed", before[k]) for k in before if k not in found]
        if out:
            self.feed.emit(out)

    def _title(self, alert):
        when = parse_time(alert.get("ref"))
        days = int((time.time() - when) // 86400) if when else 0
        return i18n.t(TITLE_KEYS[alert["code"]], repo=alert["repo"], number=alert["number"], title=alert["title"], days=days, labels=", ".join(alert.get("labels") or []))

    def _event(self, kind, alert):
        title = self._title(alert)
        return {"kind": kind, "code": alert["code"], "level": ("ok" if kind == "collab_fixed" else ("bad" if alert["level"] == "error" else "warn")), "repo": alert["repo"], "owner": events.owner_of(alert["repo"]),
                "sentinel": self.name, "account_id": self.account_id, "text": i18n.t("evt." + kind, title=title), "url": alert["url"] or None, "args": {"number": alert["number"], "title": alert["title"]}}

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
                 "details": {"number": a["number"], "title": a["title"], "url": a["url"], "labels": a.get("labels") or [], "updated": a.get("updated")}, "created_at": a["created_at"]} for a in sorted(items, key=lambda x: x["id"])]

    def get_status(self):
        if not self.enabled:
            return {"enabled": False, "level": "off", "loading": "", "errors": [], "refresh_seconds": self.refresh_seconds, "repos_in_scope": 0, "repos_checked": 0, "last_full_scan": None, "paused": False}
        repos = self.scope()
        with self.lock:
            checked = sum(1 for r in repos if (self.state["per_repo"].get(r) or {}).get("scanned"))
            alerts = list(self.state["alerts"].values())
            last = self.state["last_full_scan"]
        level = "unknown" if not checked else ("bad" if any(a["level"] == "error" for a in alerts) else ("warn" if alerts else "ok"))
        return {"enabled": True, "level": level, "loading": "" if checked or not repos else "starting", "errors": [{"section": r, "at": e["at"]} for r, e in sorted(self.errors.items())],
                "refresh_seconds": self.refresh_seconds, "repos_in_scope": len(repos), "repos_checked": checked, "last_full_scan": last, "paused": self.paused}

    def get_metrics(self):
        if not self.enabled:
            return {}
        return {"collab_alerts": len(self.state["alerts"]), "collab_repos_checked": self.get_status()["repos_checked"], "collab_calls_last_hour": len([t for t in self.calls if t > time.time() - 3600])}

    def get_config_schema(self):
        flat = {k: v for k, v in DEFAULTS.items() if k != "rules"}
        flat.update({f"rules.{k}": v for k, v in DEFAULTS["rules"].items()})
        names = ((bool, "bool"), (int, "int"), (str, "str"), (list, "list"), (dict, "dict"))
        return {"name": self.name, "keys": {k: {"type": next(n for t, n in names if isinstance(v, t)), "default": v} for k, v in sorted(flat.items())}, "groups": []}

    def snapshot(self):
        """What the page shows: the state and the alerts, in the language of the request."""
        status = self.get_status()
        return {"enabled": status["enabled"], "level": status["level"], "status": status, "alerts": self.get_alerts()}
