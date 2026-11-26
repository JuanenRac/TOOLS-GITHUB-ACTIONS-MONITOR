# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""When each source is read, what it says (red, fine, could not be read) and what comes out of it: red rows in the shape of the red workflows of Actions, alerts, and the bounded and redacted end of a log.
A service that does not answer is "degraded", never a new red; the reds that were last seen stay (marked stale), because not looking is not fixing. Everything is kept in memory."""
import random
import re
import threading
import time
from urllib.parse import urlsplit

from github_actions_monitor import families, i18n
from github_actions_monitor.data_pipeline import redrule, repo_identity
from github_actions_monitor.integrations.external_ci import extci_adapters as adapters
from github_actions_monitor.integrations.external_ci.extci_fetch import Failed, Reader
from github_actions_monitor.security import redactor

CODE_RED, CODE_DEGRADED = "ci.external.red", "ci.external.degraded"
LINE_RE = re.compile(r"^(buildbot|gitlab|jenkins|azure)(;[a-z_]{2,12}=[^;\s,]{1,200}){2,7}\Z")
KEYS = ("repo", "url", "project", "job", "builders", "branch", "token_env")
MAX_SOURCES = 30
ANSI = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)?|\[[0-?]*[ -/]*[@-~]|.)", re.S)
LOCK = threading.RLock()
STATE = {}      # {source id: {...}}
RUNNING = {"on": False}


def settings(config):
    return families.block(config if isinstance(config, dict) else {}, "external_ci")


def parse(line):
    """(source, "") or (None, reason) from one line `kind;repo=name;url=https://...;...` of external_ci.sources."""
    if not isinstance(line, str) or not LINE_RE.match(line.strip()):
        return None, "format"
    parts = line.strip().split(";")
    source = {"kind": parts[0]}
    for part in parts[1:]:
        key, _eq, value = part.partition("=")
        if key not in KEYS or key in source:
            return None, "key"
        source[key] = value
    missing = [k for k in ("repo", "url") + adapters.REQUIRED[source["kind"]] if not source.get(k)]
    if missing:
        return None, "missing:" + missing[0]
    if source.get("token_env") and not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,63}\Z", source["token_env"]):
        return None, "token_env"
    source["id"] = f"{source['kind']}:{source['repo']}:{source.get('project') or source.get('job') or source.get('builders') or 'all'}"
    return source, ""


def configured(config):
    """The sources of the configuration that can be read: a kind whose switch is off (jenkins, azure) is left out, and a line that cannot be understood too (status() lists it)."""
    cfg = settings(config)
    out, seen = [], set()
    for line in cfg["sources"] if isinstance(cfg["sources"], list) else []:
        source, _why = parse(line)
        if source and (source["kind"] not in adapters.EXPERIMENTAL or cfg[source["kind"]]["enabled"]):
            source["host"] = repo_identity.host_of(source["url"])
            unique = (source["id"], source["host"])
            if unique not in seen:
                seen.add(unique)
                out.append(source)
    return identified(out[:MAX_SOURCES])


def identified(sources):
    """Gives each source its repository key and, only when two sources would otherwise be told apart by nothing (one kind and one mirror on two servers), puts the host in their id and label."""
    hosts_of = {}
    for source in sources:
        hosts_of.setdefault((source["kind"], source["repo"]), set()).add(source["host"])
    for source in sources:
        source["repo_key"] = repo_identity.external(source["kind"], source["url"], source.get("project") or source.get("job"), source["repo"])
        twin = len(hosts_of[(source["kind"], source["repo"])]) > 1
        source["label"] = f"{source['kind']} {source['host']}" if twin else source["kind"]
        if twin:
            source["id"] = f"{source['id']}@{source['host']}"
    return sources


def active(config):
    config = config if isinstance(config, dict) else {}
    return settings(config)["enabled"] is True and config.get("airgapped") is not True and bool(configured(config))


def hosts(config):
    found = []
    for source in configured(config):
        try:
            found.append((urlsplit(source["url"]).hostname or "").lower())
        except ValueError:
            continue
    return found


def _use_proxy(config):
    return isinstance(config.get("network"), dict) and config["network"].get("use_proxy") is True


def verdicts(runs):
    """(red items, number of workflows with a verdict) with the same rule as for Actions: the last completed run of each workflow on its branch."""
    out, judged = [], 0
    groups = {}
    for item in runs:
        groups.setdefault(item["name"], []).append(item)
    for name, found in groups.items():
        branch = redrule.guess_default_branch(found)
        done = sorted(redrule.completed_runs([r for r in found if r["conclusion"] != "unknown"], branch), key=lambda r: r["started"], reverse=True)
        if not done:
            continue
        judged += 1
        if done[0]["conclusion"] not in redrule.BAD:
            continue
        streak = 0
        for item in done:
            if item["conclusion"] not in redrule.BAD:
                break
            streak += 1
        out.append({"workflow": name, "run": done[0], "streak": streak, "total": len(done), "failed": sum(1 for r in done if r["conclusion"] in redrule.BAD)})
    return out, judged


def row_of(source, item):
    """A red row with the fields of the red workflows of Actions, so that the feed, the notifications, the header and the screens treat it the same way."""
    last = item["run"]
    label = source.get("label") or source["kind"]
    return {"repo": source["repo"], "repo_key": source.get("repo_key", ""), "workflow": f"{item['workflow']} ({label})", "conclusion": last["conclusion"], "since": last["started"], "url": last["url"], "streak": item["streak"],
            "sha": last["sha"], "origin": "external", "branch": last["branch"], "kind": "build", "run_id": last["id"], "reusable": [], "aged": False, "event": last["event"], "class": "main",
            "file": item["workflow"], "recent_runs": item["total"], "fail_rate": round(100 * item["failed"] / item["total"]), "source": last["source"], "source_id": source["id"]}


def clean_log(text, lines):
    """Hostile text from a service that is not ours: no terminal sequences, no control characters, only the last lines, through the redactor."""
    text = ANSI.sub("", str(text or "")).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(c for c in text if c in "\n\t" or c.isprintable())
    return redactor.redact("\n".join(text.split("\n")[-lines:]))


def _entry(source):
    with LOCK:
        return STATE.setdefault(source["id"], {"reader_cache": {}, "next": 0.0, "failures": 0, "last_ok": 0.0, "last_try": 0.0, "reason": "", "runs": [], "reds": [], "judged": 0, "missing": [], "logs": {}})


def read(source, cfg, use_proxy=False, opener=None, cache=None):
    """One read of one source: (reader, runs, missing). Raises fetch.Failed."""
    reader = Reader(source, cfg, use_proxy, opener)
    if cache is not None:
        reader.cache = cache
    try:
        runs, missing = adapters.ADAPTERS[source["kind"]](reader, source, cfg)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):      # an answer with another shape
        raise Failed("not_json") from None
    return reader, runs, missing


def refresh(config, now=None, opener=None, jitter=random.random):
    """Reads the sources whose turn has come. Returns the number of sources read."""
    if not active(config):
        return 0
    cfg = settings(config)
    now = time.time() if now is None else now
    sources = configured(config)
    with LOCK:
        for gone in set(STATE) - {s["id"] for s in sources}:
            del STATE[gone]
    done = 0
    every = max(300, cfg["refresh_seconds"])
    for source in sources:
        entry = _entry(source)
        if now < entry["next"]:
            continue
        done += 1
        entry["last_try"] = now
        try:
            reader, runs, missing = read(source, cfg, _use_proxy(config), opener, entry["reader_cache"])
        except Failed as error:
            entry["failures"] += 1
            entry["reason"] = error.reason
            over = entry["failures"] - cfg["breaker"]["failures"]
            entry["next"] = now + every * (min(8, 2 ** (over + 1)) if over >= 0 else 1)      # the circuit of this source: it waits longer, never shorter than the interval
            continue
        reds, judged = verdicts(runs)
        with LOCK:
            entry.update(failures=0, last_ok=now, reason="", runs=runs, judged=judged, missing=missing, next=now + every * (1 + 0.1 * jitter()), reds=[row_of(source, item) for item in reds])
        if cfg["logs"]["enabled"]:
            _logs(reader, source, entry, reds, cfg, now)
    return done


def _logs(reader, source, entry, reds, cfg, now):
    keep = {k: v for k, v in entry["logs"].items() if now - v["at"] < cfg["logs"]["keep_hours"] * 3600}
    for item in reds[:10]:
        ident = f"{item['workflow']}#{item['run']['id']}"
        if ident in keep:
            continue
        try:
            text, cut = adapters.log_tail(reader, source, item["run"], cfg["logs"]["max_kb"] * 1024)
        except (Failed, AttributeError, KeyError, TypeError, ValueError):
            continue
        keep[ident] = {"at": now, "text": clean_log(text, cfg["logs"]["tail_lines"]), "cut": cut, "url": item["run"]["url"]}
    with LOCK:
        entry["logs"] = dict(sorted(keep.items(), key=lambda kv: kv[1]["at"])[-20:])


def tick(config, data=None):
    """After a cycle of the monitor: the reads run in a thread of their own, so that a slow service never holds the cycle."""
    if not active(config) or RUNNING["on"]:
        return None
    RUNNING["on"] = True

    def work():
        try:
            refresh(config)
        finally:
            RUNNING["on"] = False
    thread = threading.Thread(target=work, name="external-ci", daemon=True)
    thread.start()
    return thread


def red_rows(config):
    """The red rows of every source, for the list of red workflows; [] while the feature or its alert is off."""
    if not active(config) or not settings(config)["alert"]["enabled"]:
        return []
    with LOCK:
        return [dict(row) for source in configured(config) for row in STATE.get(source["id"], {}).get("reds", [])]


def runs(config):
    """The runs of every source for the score. Each name carries its source, so that a build of another server is never counted as a run of the workflow of Actions with the same name."""
    if not active(config):
        return []
    with LOCK:
        return [dict(r, name=f"{r['name']} ({source['label']})", repo_key=source["repo_key"]) for source in configured(config)
                for r in STATE.get(source["id"], {}).get("runs", []) if r["conclusion"] != "unknown"]


def degraded_reason(entry, cfg):
    if entry["reason"] and (entry["failures"] >= cfg["breaker"]["failures"] or not entry["last_ok"]):
        return entry["reason"]
    return ("missing " + ", ".join(entry["missing"])) if entry["missing"] else ""


def alerts(config, account=""):
    """The alerts of the external sources in the shape of the alerts of the sentinels."""
    if not active(config):
        return []
    cfg = settings(config)
    if not cfg["alert"]["enabled"]:
        return []
    out = []
    with LOCK:
        for source in configured(config):
            entry = STATE.get(source["id"])
            if not entry:
                continue
            for row in entry["reds"]:
                where = f"{source['kind']}@{source['host']}" if source["label"] != source["kind"] else source["kind"]
                out.append({"id": f"{CODE_RED}:{where}:{row['repo']}:{row['file']}:{row['branch'] or ''}", "code": CODE_RED, "level": cfg["alert"]["level"], "sentinel": "ci", "account_id": account,
                            "repo": row["repo"], "repo_key": source["repo_key"], "title": i18n.t("ui.extci.alert_red", workflow=row["workflow"], repo=row["repo"]), "created_at": row["since"],
                            "details": {"workflow": row["file"], "branch": row["branch"], "url": row["url"], "source": source["kind"], "streak": row["streak"], "stale": bool(entry["reason"])}})
            why = degraded_reason(entry, cfg)
            if why:
                out.append({"id": f"{CODE_DEGRADED}:{source['id']}", "code": CODE_DEGRADED, "level": "info", "sentinel": "ci", "account_id": account, "repo": source["repo"],
                            "title": i18n.t("ui.extci.alert_degraded", source=source["kind"], repo=source["repo"], reason=why), "created_at": adapters.iso(entry["last_try"]), "details": {"reason": why}})
    return out


def status(config):
    """What every source says. "No red" is never shown as fine for a source that could not be read."""
    cfg = settings(config)
    rows, invalid = [], []
    for line in cfg["sources"] if isinstance(cfg["sources"], list) else []:
        source, why = parse(line)
        if source is None:
            invalid.append({"line": str(line)[:80], "reason": why})
        elif source["kind"] in adapters.EXPERIMENTAL and not cfg[source["kind"]]["enabled"]:
            invalid.append({"line": source["id"], "reason": "kind_off"})
    with LOCK:
        for source in configured(config):
            entry = STATE.get(source["id"])
            why = degraded_reason(entry, cfg) if entry else ""
            if not entry or not entry["last_try"]:
                state = "pending"
            elif why or entry["reason"]:
                state = "degraded"
            else:
                state = "red" if entry["reds"] else ("ok" if entry["judged"] else "no_builds")
            rows.append({"id": source["id"], "kind": source["kind"], "repo": source["repo"], "repo_key": source["repo_key"], "state": state, "reason": why or (entry["reason"] if entry else ""),
                         "experimental": cfg["experimental"] is True and source["kind"] in adapters.EXPERIMENTAL, "last_ok": adapters.iso(entry["last_ok"]) if entry else "",
                         "next_try": adapters.iso(entry["next"]) if entry else "", "red": [{"workflow": r["workflow"], "branch": r["branch"], "url": r["url"], "run_id": r["run_id"]} for r in (entry["reds"] if entry else [])],
                         "logs": sorted(entry["logs"]) if entry and cfg["logs"]["enabled"] else []})
    return {"ok": True, "enabled": cfg["enabled"] is True, "active": active(config), "sources": rows, "invalid": invalid}


def log_of(config, source_id, ident):
    cfg = settings(config)
    if not cfg["logs"]["enabled"]:
        return None
    with LOCK:
        found = STATE.get(source_id, {}).get("logs", {}).get(ident)
        if not found or time.time() - found["at"] >= cfg["logs"]["keep_hours"] * 3600:
            return None
        return {"text": found["text"], "cut": found["cut"], "url": found["url"]}


def probe(config, line, opener=None):
    """One read of a source that is not saved anywhere: what it sees, or why it cannot."""
    source, why = parse(line)
    if source is None:
        return {"ok": False, "reason": why}
    if (config or {}).get("airgapped") is True:
        return {"ok": False, "reason": "airgapped"}
    cfg = settings(config)
    try:
        _reader, found, missing = read(source, cfg, _use_proxy(config or {}), opener)
    except Failed as error:
        return {"ok": False, "reason": error.reason}
    reds, judged = verdicts(found)
    return {"ok": True, "reason": "", "kind": source["kind"], "workflows": len({r["name"] for r in found}), "builds": len(found), "judged": judged, "red": len(reds),
            "last_build": max((r["started"] for r in found), default=""), "missing": missing, "experimental": cfg["experimental"] is True and source["kind"] in adapters.EXPERIMENTAL}


def forget():
    with LOCK:
        STATE.clear()
