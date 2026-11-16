# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What reaches the notification channels when there are many alerts, or the same ones again and again. Everything is OFF or empty by default: with no setting the events pass as they always did.

  * `alerts.silences`: permanent silences by pattern, one text each: `repo:workflow:branch;reason;review-date` (every part but the repo may be left out or be `*`; `*` stands for any text; the
    reason and the date of review are optional). A silenced event is still written in the feed (marked) but nobody is told. When the date of review comes, ONE reminder event is announced and the
    silence keeps working until somebody removes it. The Alerts tab shows the alerts that match as silenced.
  * `alerts.service`: a workflow that only runs on a schedule or by hand (a short cron, a service) and fails now and then must not alert in a loop. With `enabled`, its red is announced only after
    `failures` failures in a row, or when `rate_percent` (0 = off) of its last runs failed; it is announced once and cleared once. `workflows` adds more `repo:workflow` patterns to the class.
  * `alerts.group`: with `by_commit`, `min` or more new reds of one repository on the same commit are told as ONE event that lists the workflows.
  * `alerts.digest`: with `minutes` > 0, once more than `threshold` events were told in the last hour, the rest are held and told as ONE summary every `minutes` minutes.
Pure functions and a small state object: no network, the clock is a parameter.
"""
import fnmatch
import re
import time
from datetime import datetime, timezone

SILENCE_RE = re.compile(r"^[\w.*-]{1,100}(:[\w .()*/@+-]{1,120}){0,2}(;[^;\x00-\x1f]{0,200}(;\d{4}-\d{2}-\d{2})?)?\Z")
PATTERN_RE = re.compile(r"^[\w.*-]{1,100}(:[\w .()*/@+-]{1,120}){0,2}\Z")
DEFAULTS = {"silences": [], "service": {"enabled": False, "failures": 3, "rate_percent": 0, "workflows": []}, "group": {"by_commit": False, "min": 3}, "digest": {"minutes": 0, "threshold": 10}}
POLICY = {"silences": [], "service": dict(DEFAULTS["service"]), "group": dict(DEFAULTS["group"]), "digest": dict(DEFAULTS["digest"])}      # replaced by configure(): the whole monitor shares it
FOREVER = "9999-12-31T23:59:59Z"


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def parse_silence(text):
    """{"repo", "workflow", "branch", "reason", "review_by", "text"} from `repo:workflow:branch;reason;date`, or None when the text is not one."""
    if not isinstance(text, str) or not SILENCE_RE.match(text):
        return None
    head, _, rest = text.partition(";")
    reason, _, review = rest.partition(";")
    parts = (head.split(":") + ["*", "*"])[:3]
    if review:
        try:
            datetime.strptime(review, "%Y-%m-%d")
        except ValueError:
            return None
    return {"repo": parts[0], "workflow": parts[1], "branch": parts[2], "reason": reason.strip(), "review_by": review, "text": text}


def _patterns(items):
    out = []
    for item in items if isinstance(items, (list, tuple)) else ():
        if isinstance(item, str) and PATTERN_RE.match(item):
            parts = (item.split(":") + ["*", "*"])[:3]
            out.append({"repo": parts[0], "workflow": parts[1], "branch": parts[2]})
    return out


def settings(config):
    block = (config or {}).get("alerts")
    block = block if isinstance(block, dict) else {}
    service = block.get("service") if isinstance(block.get("service"), dict) else {}
    group = block.get("group") if isinstance(block.get("group"), dict) else {}
    digest = block.get("digest") if isinstance(block.get("digest"), dict) else {}
    return {"silences": [s for s in (parse_silence(x) for x in (block.get("silences") if isinstance(block.get("silences"), list) else [])) if s],
            "service": {"enabled": service.get("enabled") is True, "failures": _int(service.get("failures"), 2, 50, 3), "rate_percent": _int(service.get("rate_percent"), 0, 100, 0),
                        "workflows": _patterns(service.get("workflows"))},
            "group": {"by_commit": group.get("by_commit") is True, "min": _int(group.get("min"), 2, 50, 3)},
            "digest": {"minutes": _int(digest.get("minutes"), 0, 1440, 0), "threshold": _int(digest.get("threshold"), 3, 500, 10)}}


def configure(config):
    POLICY.clear()
    POLICY.update(settings(config))


def _glob(pattern, text):
    return pattern == "*" or fnmatch.fnmatchcase(str(text or "").lower(), pattern.lower())


def matches(entry, repo, names=(), branch=None):
    """True when the repository, one of the names of the workflow (display name or file) and the branch fit the pattern. A pattern with a branch other than `*` needs a branch to compare."""
    if not _glob(entry["repo"], repo):
        return False
    if entry["workflow"] != "*" and not any(_glob(entry["workflow"], n) for n in names if n):
        return False
    return entry["branch"] == "*" or bool(branch and _glob(entry["branch"], branch))


def silence_of(repo, names=(), branch=None, policy=None):
    """The first permanent silence that covers this finding (a dict), else None."""
    for entry in (policy or POLICY)["silences"]:
        if matches(entry, repo, names, branch):
            return entry
    return None


def review_due(entry, now):
    return bool(entry["review_by"]) and entry["review_by"] <= datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")


def is_service(row, policy=None):
    policy = policy or POLICY
    if row.get("kind") == "service":
        return True
    return any(matches(p, row.get("repo"), (row.get("workflow"), row.get("file")), None) for p in policy["service"]["workflows"])


def service_allows(row, policy=None):
    """False for the red of a workflow of the class `service` that has not failed often enough yet to be worth an alert (see the head of this file). Everything else is allowed."""
    policy = policy or POLICY
    cfg = policy["service"]
    if not cfg["enabled"] or not is_service(row, policy):
        return True
    if (row.get("streak") or 0) >= cfg["failures"]:
        return True
    return bool(cfg["rate_percent"]) and (row.get("recent_runs") or 0) >= 4 and (row.get("fail_rate") or 0) >= cfg["rate_percent"]


def event_names(event):
    args = event.get("args") if isinstance(event.get("args"), dict) else {}
    return [args.get("workflow"), args.get("name"), event.get("file")]


class Flow:
    """The state that spans cycles: what was told in the last hour, what is held for the summary, which reminders were already made."""

    def __init__(self):
        self.sent, self.held, self.held_since, self.reminded = [], [], 0.0, set()

    def shape(self, events, now=None, policy=None):
        """(notify, record): `notify` is what the channels get, `record` everything that is written in the feed (the silenced, held and grouped events marked as such, plus the events made here)."""
        policy = policy or POLICY
        now = time.time() if now is None else now
        record, notify = list(events), []
        for event in events:
            hit = silence_of(event.get("repo"), event_names(event), event.get("branch"), policy) if event.get("repo") else None
            if hit:
                event["silenced"], event["silence_reason"] = True, hit["reason"]
            else:
                notify.append(event)
        notify = self._group(notify, record, policy)
        for entry in policy["silences"]:
            if review_due(entry, now) and entry["text"] not in self.reminded:
                self.reminded.add(entry["text"])
                made = _made("silence_review", "info", "", pattern=entry["text"].partition(";")[0], reason=entry["reason"] or "-", date=entry["review_by"])
                record.append(made)
                notify.append(made)
        return self._digest(notify, record, now, policy), record

    def _group(self, notify, record, policy):
        cfg = policy["group"]
        if not cfg["by_commit"]:
            return notify
        buckets = {}
        for event in notify:
            if event.get("kind") == "red_new" and event.get("sha") and event.get("repo"):
                buckets.setdefault((event["repo"], event["sha"]), []).append(event)
        merged = {k: v for k, v in buckets.items() if len(v) >= cfg["min"]}
        if not merged:
            return notify
        out, done = [], set()
        for event in notify:
            key = (event.get("repo"), event.get("sha"))
            if key not in merged:
                out.append(event)
            elif key not in done:
                done.add(key)
                members = merged[key]
                names = [str((m.get("args") or {}).get("workflow") or "") for m in members]
                made = _made("red_new", "bad", key[0], url=members[0].get("url"), repo=key[0], count=len(members), sha=key[1], list=", ".join(names[:5]) + (", ..." if len(names) > 5 else ""), _text="evt.red_group")
                made.update({"sha": key[1], "grouped": len(members), "args": {"repo": key[0], "workflows": names, "count": len(members), "sha": key[1]}})
                for m in members:
                    m["grouped_into"] = key[1]
                record.append(made)
                out.append(made)
        return out

    def _digest(self, notify, record, now, policy):
        cfg = policy["digest"]
        if not cfg["minutes"]:
            return notify
        self.sent = [t for t in self.sent if now - t < 3600]
        out = []
        for event in notify:
            if len(self.sent) < cfg["threshold"]:
                self.sent.append(now)
                out.append(event)
            else:
                event["held"] = True
                self.held.append(event)
                self.held_since = self.held_since or now
        if self.held and now - self.held_since >= cfg["minutes"] * 60:
            kinds = [e.get("kind") for e in self.held]
            made = _made("alerts_digest", "warn", "", n=len(self.held), red=kinds.count("red_new"), stuck=kinds.count("stuck_new"), other=len(kinds) - kinds.count("red_new") - kinds.count("stuck_new"),
                         minutes=cfg["minutes"])
            made["args"]["items"] = [{"kind": e.get("kind"), "repo": e.get("repo"), "text": e.get("text")} for e in self.held[:50]]
            record.append(made)
            out.append(made)
            self.held, self.held_since = [], 0.0
        return out


def _made(kind, level, _repo, url=None, _text=None, **args):
    from github_actions_monitor import i18n
    from github_actions_monitor.data_pipeline import events
    return {"kind": kind, "code": kind, "level": level, "repo": _repo, "owner": events.owner_of(_repo), "text": i18n.t(_text or "evt." + kind, **args), "url": url, "args": args}
