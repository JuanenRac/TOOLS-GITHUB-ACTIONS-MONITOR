# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A feed of alerts for the AIs (and scripts) that work in your repositories, so that a red workflow reaches them instead of waiting for someone to look at the page.

  * Local and read only: the monitor writes, in the folder `ai_alerts.folder` (default: next to the monitor), `ai_alerts.jsonl` (one line per EVENT: opened, resolved, acknowledged) and
    `ALERTS_BRIEF.md` (rewritten at every cycle, short: `ai_alerts.brief_max_bytes`, 2 KB by default). An AI reads the brief when it starts. No network is used for this.
  * One alert per red workflow, with a stable id, severity, repository, workflow, conclusion, since when, streak, link, a probable cause classified as REAL or TRANSIENT with rules you can edit
    (`ai_alerts.transient_patterns`: 502/503/504, timeouts, rate limits, download failures... are transient), a suggested action and a state: open, acknowledged or resolved (by itself when the
    workflow turns green again). Acknowledging (`ack`) only changes this local state.
  * Everything written goes through `redact()` first: tokens, keys, e-mail addresses, IP addresses and the home folder of the user never reach the feed, the brief, an endpoint or a hook.
  * Optional, OFF by default: a hook (`ai_alerts.hook`) that POSTs a NEW real alert (closed list of fields) to an address on THIS computer, at most `max_per_hour` times an hour, so that a script of
    yours can wake an AI session. Nothing goes to an external provider from here, and nothing here runs a command or writes to GitHub.
  * 1.7.6 - the connection between the monitor and an AI: the feed and the brief are rewritten at EVERY refresh of the alert centre (not one cycle later), each alert can carry the failing step and
    the last relevant lines of its log (`ai_alerts.diagnose`, off by default: it reads logs of GitHub), alerts that fall together because of one red repository are grouped under it
    (`ai_alerts.cascade`), a read-only stream of events (`ai_alerts.stream`, off by default), and a heartbeat file that tells the status bar whether an AI is reading the feed (`ai_alerts.heartbeat`).
"""
from github_actions_monitor.app import degraded
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from github_actions_monitor.util import tzdisplay
import urllib.request
from pathlib import Path
from github_actions_monitor.security import private_io
from github_actions_monitor.security import netguard

from github_actions_monitor.util import paths
FEED = "ai_alerts.jsonl"
BRIEF = "ALERTS_BRIEF.md"
STATE = "ai_alerts_state.json"
HEARTBEAT = "ai_heartbeat.json"
FIELDS = ("id", "severity", "class", "repo", "workflow", "conclusion", "since", "streak", "url", "cause", "action", "state")      # the closed list a hook or an endpoint may carry
EXTRA = ("diagnosis", "origin", "panel")      # what the feed, the stream and the endpoints add to FIELDS (never the hook: its list is the closed one above)
RUN_RE = re.compile(r"/actions/runs/(\d+)")
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
STAMP_RE = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z\s*")
RELEVANT_RE = re.compile(r"(?i)\b(error|errors|fail|failed|failure|fatal|exception|traceback|not found|denied|cannot|can't|unable|exit code|assert\w*|no such)\b")
VIA = ("stream", "mcp", "hook", "endpoint")
TRANSIENT_DEFAULT = [r"\b50[234]\b", r"bad gateway", r"service unavailable", r"gateway time-?out", r"timed? ?out", r"rate limit", r"secondary rate", r"tls", r"connection (?:reset|refused|closed)",
                     r"unexpected eof", r"codeql.*download", r"download.*codeql", r"could not resolve host", r"no space left", r"the runner has received a shutdown signal"]
LOOP_RE = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}(/[A-Za-z0-9._~/%-]{0,100})?\Z")

_SECRETS = [
    (re.compile(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"), "[pem]"),
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@"), r"\1[credentials]@"),      # user:password@host in an address
    (re.compile(r"(?i)\bhooks\.slack\.com/services/[A-Za-z0-9/_-]+"), "hooks.slack.com/services/[webhook]"),
    (re.compile(r"(?i)\bdiscord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9._-]+"), "discord.com/api/webhooks/[webhook]"),
    (re.compile(r"\bbot\d{6,}:[A-Za-z0-9_-]{20,}"), "bot[token]"),
    (re.compile(r"""(?i)(x-monitor-access|monitor_access)(["']?\s*[:=]\s*)(?:"[^"\n]{0,300}"|'[^'\n]{0,300}'|["']?[^\s"',;]+)"""), r"\1\2[secret]"),
    (re.compile(r"(?<![A-Za-z0-9])(?:glpat-[A-Za-z0-9_-]{10,}|npm_[A-Za-z0-9]{16,}|pypi-[A-Za-z0-9_-]{16,})"), "[token]"),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,})"), "[token]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{12,}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,})"), "[key]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "[jwt]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 [secret]"),
    (re.compile(r"""(?i)([A-Za-z0-9_.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|authorization)[A-Za-z0-9_.-]*)(["']?\s*[:=]\s*)(?:"[^"\n]{0,300}"|'[^'\n]{0,300}'|["']?[^\s"',;]+)"""), r"\1\2[secret]"),      # DB_PASSWORD=, AWS_SECRET_ACCESS_KEY=, MYSQL_PWD=
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[ip]"),
    (re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}\b"), "[ip]"),
    (re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s]+"), "~"),
    (re.compile(r"/(?:home|Users)/[^/\s]+"), "~"),
    (re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,}(?![0-9A-Fa-f])"), "[hex]"),
    (re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}"), "[blob]"),
]


# The address of a page of GitHub (a repository, a run, a commit, an issue, a file): public, it carries no secret and the AI needs it whole. Only a closed list of SHAPES passes untouched and the
# address is cut at the first character outside [A-Za-z0-9._/-]: what follows (a query, a fragment, an encoded character, a colon, a comma...) is cleaned like any other text.
_GITHUB_URL = re.compile(r"https://(?P<api>api\.)?github\.com(?![A-Za-z0-9@:-]|\.[A-Za-z0-9])(?P<path>(?:/[A-Za-z0-9._-]*)*)")
_SEG = r"[A-Za-z0-9._-]*[A-Za-z0-9_-]"
_GITHUB_SHAPE = re.compile(
    rf"(?:/repos)?/{_SEG}(?:/{_SEG}(?:/actions/runs/\d+(?:/job/\d+|/attempts/\d+)?|/commit/[0-9A-Fa-f]{{40}}|/(?:issues|pull)/\d+|/(?:blob|tree)(?=/)(?:/{_SEG})*)?)?(?![A-Za-z0-9_-])")
_OPAQUE_SEGMENT = re.compile(r"[0-9A-Fa-f]{32,}|[A-Za-z0-9_-]{40,}")      # what the rules of the text turn into [hex] and [blob]


def _github_safe(match):
    """The part of a github.com address that may pass untouched: the host and the longest prefix of the path that has one of the shapes of the list, with no segment that looks like a secret."""
    path = match.group("path") or ""
    shape = _GITHUB_SHAPE.match(path)
    if not shape or not path.startswith("/"):
        return "https://" + ("api." if match.group("api") else "") + "github.com"
    kept = shape.group(0)
    parts = kept.split("/")
    for index, part in enumerate(parts):
        if index and _OPAQUE_SEGMENT.search(part) and not (index >= 2 and parts[index - 1] == "commit"):      # the 40 hexadecimal digits of a commit are public; any other opaque segment is not
            kept = "/".join(parts[:index])
            break
    return "https://" + ("api." if match.group("api") else "") + "github.com" + kept


def redact(text, limit=None):
    """The text without tokens, keys, e-mail addresses, IP addresses, the home folder of a person and long opaque strings. The addresses of github.com that have the shape of a repository, a run,
    a commit, an issue, a pull request or a file pass untouched (a run link is longer than the 40 characters of an opaque string and used to be cut to [blob]); nothing after the first character
    outside [A-Za-z0-9._/-] does."""
    out = str(text or "").replace("\ue000", "").replace("\ue001", "")      # the marks below belong to this function only
    home = str(Path.home())
    for variant in {home, home.replace("\\", "/")}:
        if len(variant) > 3:
            out = out.replace(variant, "~")
    kept = []

    def keep(match):
        url = _github_safe(match)
        if match.string[match.end():match.end() + 1] == "@" or any(pattern.search(url) for pattern, replacement in _SECRETS if replacement not in ("[hex]", "[blob]")):      # an address that goes on as an e-mail, or that itself holds a token, a key, a home folder...: it is cleaned like any text
            return match.group(0)
        kept.append(url)
        return f"\ue000{len(kept) - 1}\ue001" + match.group(0)[len(url):]
    out = _GITHUB_URL.sub(keep, out)
    for pattern, replacement in _SECRETS:
        out = pattern.sub(replacement, out)
    for index, url in enumerate(kept):
        out = out.replace(f"\ue000{index}\ue001", url)
    return out[:limit] if limit else out


def redact_data(value, limit=None):
    """The same cleaning for a structure (dict, list, text): every text inside is cleaned ON ITS OWN, keys included, and the structure is serialised afterwards. Never clean a JSON that is already
    written: a value that ends at the quote of its string would take the quote with it and break the document."""
    if isinstance(value, str):
        return redact(value, limit)
    if isinstance(value, dict):
        return {(redact(k) if isinstance(k, str) else k): redact_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_data(v) for v in value]
    return value


def redact_json(value, limit=None, **dumps):
    """JSON of `value` with every text cleaned (see redact_data); `limit` cuts the written text."""
    text = json.dumps(redact_data(value), **({"ensure_ascii": False} | dumps))
    return text[:limit] if limit else text


def _num(block, key, low, high, default):
    value = block.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def _block(cfg, name):
    return cfg.get(name) if isinstance(cfg.get(name), dict) else {}


def settings(config):
    cfg = config.get("ai_alerts") if isinstance(config, dict) and isinstance(config.get("ai_alerts"), dict) else {}
    hook = _block(cfg, "hook")
    diagnose, cascade, stream, beat, client = (_block(cfg, n) for n in ("diagnose", "cascade", "stream", "heartbeat", "client_hook"))
    size = cfg.get("brief_max_bytes")
    per_hour = hook.get("max_per_hour")
    patterns = cfg.get("transient_patterns") if isinstance(cfg.get("transient_patterns"), list) else TRANSIENT_DEFAULT
    links = cascade.get("map") if isinstance(cascade.get("map"), dict) else {}
    folder_text = cfg.get("folder") if isinstance(cfg.get("folder"), str) else ""
    # OFF by default (1.7.6). A configuration that never said anything and whose feed already exists - it was on by default before - keeps working, and `legacy` tells the console to say so once.
    legacy = not isinstance(cfg.get("enabled"), bool) and in_use(folder_text)
    return {"enabled": cfg["enabled"] if isinstance(cfg.get("enabled"), bool) else legacy, "legacy": legacy, "folder": folder_text,
            "brief_max_bytes": size if isinstance(size, int) and not isinstance(size, bool) and 512 <= size <= 20000 else 2048,
            "transient_patterns": [p for p in patterns if isinstance(p, str) and 0 < len(p) <= 120][:40],
            "hook": {"enabled": hook.get("enabled") is True and bool(LOOP_RE.match(str(hook.get("url") or ""))), "url": str(hook.get("url") or ""),
                     "max_per_hour": per_hour if isinstance(per_hour, int) and not isinstance(per_hour, bool) and 1 <= per_hour <= 60 else 6},
            # reads logs of GitHub (the allowance): OFF until you turn it on
            "diagnose": {"enabled": diagnose.get("enabled") is True, "max_per_cycle": _num(diagnose, "max_per_cycle", 1, 10, 3), "log_lines": _num(diagnose, "log_lines", 3, 40, 10),
                         "max_bytes": _num(diagnose, "max_bytes", 200, 4000, 1500)},
            # only a way of showing the alerts: on. `map` = {"base-repo": ["client-repo", ...]} for the cascades that a log does not name
            "cascade": {"enabled": cascade.get("enabled", True) is True,
                        "map": {str(k)[:100]: [str(v)[:100] for v in vs if isinstance(v, str)][:50] for k, vs in list(links.items())[:50] if isinstance(vs, list)}},
            # a read-only stream of events for an AI session: OFF until you turn it on
            "stream": {"enabled": stream.get("enabled") is True, "max_seconds": _num(stream, "max_seconds", 60, 86400, 3600), "max_clients": _num(stream, "max_clients", 1, 10, 3)},
            "heartbeat": {"enabled": beat.get("enabled", True) is True, "window_minutes": _num(beat, "window_minutes", 1, 1440, 15)},
            # the gate script `ai_hook.py` (installed with `monitor_cli.py ai-hook install`): it injects the brief; blocking the end of a turn is OFF until you turn it on
            "client_hook": {"enabled": client.get("enabled", True) is True, "block_on_stop": client.get("block_on_stop") is True, "cooldown_minutes": _num(client, "cooldown_minutes", 1, 1440, 20),
                            "stale_hours": _num(client, "stale_hours", 1, 168, 3), "max_lines": _num(client, "max_lines", 1, 40, 12), "max_chars": _num(client, "max_chars", 400, 8000, 2400)}}


def in_use(folder_text):
    """True when a feed of this monitor already exists in the folder (so that an installation that had it on by default is not switched off by the new default)."""
    folder = folder_of({"folder": folder_text})
    return (folder / STATE).is_file() or (folder / BRIEF).is_file()


def folder_of(cfg):
    text = cfg["folder"].strip()
    ok = bool(text) and len(text) <= 260 and not any(ord(c) < 32 for c in text) and not text.startswith(("\\\\", "//")) and not re.match(r"^(?:[Dd]:|/mnt/[dD](?:/|$))", text)
    return Path(text) if ok else paths.folder("ai")      # ai/ (or where MONITOR_AI_DIR / config/paths.json put it): what an AI reads lives in one folder


def classify(conclusion, text="", patterns=None):
    """('transient' | 'real', cause): an infrastructure conclusion or a known passing message is transient; everything else is a real failure until a log says otherwise."""
    for pattern in patterns if patterns is not None else TRANSIENT_DEFAULT:
        try:
            if text and re.search(pattern, text, re.I):
                return "transient", f"matches /{pattern}/"
        except re.error:
            continue
    if conclusion == "startup_failure":
        return "transient", "the run did not start (GitHub or the runner)"
    if conclusion == "timed_out":
        return "transient", "the run hit its time limit (look at the log: it may be a hang)"
    if conclusion == "action_required":
        return "real", "a run waits for an approval nobody gave"
    return "real", "the workflow failed (read the log of the run)"


def alert_id(repo, workflow):
    return hashlib.sha1(f"{repo}|{workflow}".encode()).hexdigest()[:12]


def build_panel_alert(row):
    """An alert that comes from a panel of the Sentinel tab (A1..A13, the second sentinel): "real" when the panel says act ("bad"), "watch" when it says keep an eye on it ("warn")."""
    real = row.get("level") == "bad"
    return {"id": alert_id(row["repo"], row["workflow"]), "severity": "high" if real else "warn", "class": "real" if real else "watch", "repo": row["repo"], "workflow": row["workflow"], "conclusion": "panel",
            "since": None, "streak": 1, "url": row.get("url"), "cause": redact(str(row.get("detail") or ""), 240), "panel": row.get("panel"),
            "action": f"open the panel {str(row.get('panel')).upper()} of the Sentinel tab and deal with it"}


def build_alert(row, patterns, text=""):
    if row.get("conclusion") == "panel":
        return build_panel_alert(row)
    kind, cause = classify(row.get("conclusion"), text, patterns)
    streak = int(row.get("streak") or 1)
    severity = "info" if kind == "transient" and streak < 3 else ("high" if streak >= 3 or kind == "real" and row.get("conclusion") == "failure" else "warn")
    action = "re-run once and look again" if kind == "transient" and streak < 3 else "open the log of the run, find the first failing step and fix it"
    return {"id": alert_id(row["repo"], row["workflow"]), "severity": severity, "class": kind, "repo": row["repo"], "workflow": row["workflow"], "conclusion": row.get("conclusion"),
            "since": row.get("since"), "streak": streak, "url": row.get("url"), "cause": redact(cause, 200), "action": action}


def _read(path, default):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except (OSError, ValueError):
        return default


def _write(path, text):
    tmp = Path(str(path) + ".tmp")
    private_io.write_tmp(tmp, text)
    os.replace(tmp, path)


def _event(folder, kind, alert, now):
    line = {"at": int(now), "event": kind, **{k: alert.get(k) for k in FIELDS + EXTRA}}
    with private_io.open_append(Path(folder) / FEED) as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def run_id_of(url):
    match = RUN_RE.search(str(url or ""))
    return int(match.group(1)) if match else 0


def gh_runner(args, timeout=60):
    """Runs `gh` (read only calls) with the token the monitor keeps, if any. Returns (code, text out, text err)."""
    kwargs = {}
    try:
        from github_actions_monitor.security import secretstore
        kwargs = secretstore.gh_kwargs()
    except Exception:   # noqa: BLE001 - without the store gh uses its own login
        pass
    done = subprocess.run(["gh", *args], capture_output=True, timeout=timeout, **kwargs)
    return done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")


def relevant_lines(log, count=10):
    """The last `count` lines of a failed log that say what went wrong (error, failed, not found...), else the last lines; time stamps, colours and group marks removed."""
    cleaned = []
    for raw in str(log or "").splitlines():
        parts = raw.split("\t", 2)
        text = STAMP_RE.sub("", ANSI_RE.sub("", parts[2] if len(parts) == 3 else raw)).strip()
        if text and not text.startswith(("##[group]", "##[endgroup]")):
            cleaned.append(text)
    hits = [line for line in cleaned if RELEVANT_RE.search(line)]
    return [line[:200] for line in (hits[-count:] if hits else cleaned[-count:])]


def diagnose(owner, repo, url, runner, count=10, max_bytes=1500):
    """The probable cause of a red run, read from its log: {"run", "step" (the first failing step), "lines" (about ten relevant ones)}. Everything goes through redact() and the answer never
    exceeds `max_bytes` once written. None when the address carries no run; {"run", "unavailable": True} when GitHub did not answer (so it is not asked again for the same run)."""
    run = run_id_of(url)
    if not run:
        return None
    try:
        code, out, _err = runner(["api", f"repos/{owner}/{repo}/actions/runs/{run}/jobs?per_page=30"], 60)
        if code != 0:
            return {"run": run, "unavailable": True}
        step = ""
        for job in json.loads(out).get("jobs") or []:
            failed = [x for x in job.get("steps") or [] if x.get("conclusion") == "failure"]
            if failed:
                step = f"{job.get('name')}: {failed[0].get('name')}"
                break
        code, log, _err = runner(["run", "view", str(run), "--repo", f"{owner}/{repo}", "--log-failed"], 90)
    except (ValueError, OSError, subprocess.SubprocessError, AttributeError):
        return {"run": run, "unavailable": True}
    lines = [redact(line) for line in relevant_lines(log if code == 0 else "", count)]
    result = {"run": run, "step": redact(step, 160), "lines": lines}
    while lines and len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > max_bytes:
        lines.pop(0)
    return result


def _words(text):
    return {w.lower() for w in re.findall(r"[A-Za-z0-9._-]{4,100}", str(text or ""))}


def group_cascades(alerts, links=None):
    """Marks as `origin` (id, repo, workflow) the alerts that are red because of another red repository: the base repository is named by a rule of `ai_alerts.cascade.map` or by the log of the
    alert itself. The root of a chain wins; two repositories that name each other have no origin. Alerts without one lose a stale mark."""
    live = [a for a in alerts if a.get("state") != "resolved"]
    by_repo = {}
    for a in sorted(live, key=lambda x: (x["repo"], x["workflow"])):
        by_repo.setdefault(a["repo"], a)
    parent = {}
    for a in live:
        text = " ".join([str(a.get("cause") or "")] + list((a.get("diagnosis") or {}).get("lines") or []) + [str((a.get("diagnosis") or {}).get("step") or "")])
        words = _words(text)
        for repo, base in by_repo.items():
            if repo == a["repo"]:
                continue
            if a["repo"] in (links or {}).get(repo, []) or repo.lower() in words:
                parent[a["id"]] = base["id"]
                break
    index = {a["id"]: a for a in live}
    for a in live:
        a["origin"] = None
        seen, node = {a["id"]}, a["id"]
        while node in parent and parent[node] not in seen:
            node = parent[node]
            seen.add(node)
        if node != a["id"] and parent.get(node) not in seen:      # a chain that ends in a root
            root = index[node]
            a["origin"] = {"id": root["id"], "repo": root["repo"], "workflow": root["workflow"]}
    return alerts


def brief(alerts, limit, now=None, panels=None, sections="", status=""):
    """The Markdown an AI reads when it starts: open alerts, the real ones first, within `limit` bytes. An alert that is red because of another one is listed under that one."""
    live = [a for a in alerts if a["state"] != "resolved"]
    live.sort(key=lambda a: (a["state"] == "acknowledged", a["class"] != "real", a["repo"], a["workflow"]))
    real = sum(1 for a in live if a["class"] == "real" and a["state"] == "open")
    followers = {}
    for a in live:
        if a.get("origin"):
            followers.setdefault(a["origin"]["id"], []).append(a)
    roots = [a for a in live if not a.get("origin")]
    stamp = time.time() if now is None else now
    head = f"{real} real alert(s) open, {len(live)} in total" + (f", in {sum(1 for a in roots if a['class'] == 'real' and a['state'] == 'open')} independent group(s)" if followers else "")
    lines = ["# CI alerts", "", head + ". Transient ones usually clear by themselves; re-run once before you dig.", f"Updated: {tzdisplay.stamp(stamp)}", f"updated_epoch: {int(stamp)}"] + ([f"Monitor: {status}"] if status else []) + [""]
    for a in roots:
        mark = {"open": "", "acknowledged": " (acknowledged)"}[a["state"]]
        item = f"- [{a['severity']}/{a['class']}] {a['repo']} / {a['workflow']}: {a['conclusion']} x{a['streak']}{mark} - {a['cause']}. Next: {a['action']}. {a.get('url') or ''}".rstrip()
        diagnosis = a.get("diagnosis") or {}
        if diagnosis.get("step"):
            item += "\n  Failing step: " + str(diagnosis["step"]) + (" | " + str(diagnosis["lines"][-1]) if diagnosis.get("lines") else "")
        if followers.get(a["id"]):
            item += "\n  Also red because of it (fix this one first): " + ", ".join(f"{f['repo']} / {f['workflow']}" for f in followers[a["id"]])
        lines.append(item)
    text = "\n".join(lines) + "\n"
    if len(text.encode("utf-8")) > limit:
        kept = []
        for index, line in enumerate(lines):
            candidate = "\n".join(kept + [line, f"- ... and {len(lines) - index - 1} more in ai_alerts.jsonl"]) + "\n"
            if len(candidate.encode("utf-8")) > limit:
                break
            kept.append(line)
        text = "\n".join(kept + [f"- ... and {max(0, len(lines) - len(kept))} more in ai_alerts.jsonl"]) + "\n"
    if panels:      # the panels of the Sentinel tab have a section of their own, with the same size limit as the list above (it never pushes the CI alerts out)
        from github_actions_monitor.sentinels import sentinel_panels
        section = sentinel_panels.brief_section(panels)
        rows = section.rstrip("\n").split("\n")
        total = len(rows)
        while len(("\n".join(rows) + "\n").encode("utf-8")) > limit and len(rows) > 4:
            rows.pop()      # one line less every turn: the loop always ends
        if len(rows) < total:
            rows[-1] = "- ... more in ai_alerts.jsonl"
        section = "\n".join(rows) + "\n"
        text += "\n" + section
    if sections:      # what to do now, what is pending, the health of the monitor (signals.py), with the same size limit
        block = sections
        while len(block.encode("utf-8")) > limit and block.count("\n") > 6:
            block = block.rsplit("\n", 3)[0] + "\n"
        text += "\n" + block
    return redact(text)


class Hook:
    def __init__(self):
        self.sent = []

    def allowed(self, per_hour, now):
        self.sent = [t for t in self.sent if now - t < 3600]
        return len(self.sent) < per_hour

    def send(self, url, alert, now, opener=None):
        body = json.dumps({k: alert.get(k) for k in FIELDS}).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        (opener or (lambda r: netguard.local_open(r, timeout=5).read()))(request)
        self.sent.append(now)


HOOK = Hook()


def update(config, red_rows, now=None, texts=None, opener=None, runner=None, owner="", panels=None, sections="", extra_rows=None, status=""):
    """Brings the feed up to date with the red workflows of this cycle. Returns {"opened": [...], "resolved": [...], "alerts": [...]}. Nothing is written when the feed is off.
    With a `runner` (read only calls to `gh`) and `ai_alerts.diagnose.enabled`, a new or changed red run also gets its diagnosis; without a runner the diagnosis already kept is reused."""
    cfg = settings(config)
    now = time.time() if now is None else now
    if not cfg["enabled"]:
        return {"opened": [], "resolved": [], "alerts": []}
    folder = folder_of(cfg)
    private_io.private_dir(folder)
    state = _read(folder / STATE, {})
    seen, opened, resolved = set(), [], []
    budget = cfg["diagnose"]["max_per_cycle"] if runner is not None and cfg["diagnose"]["enabled"] else 0
    if extra_rows:      # the signals of the monitor that are not a red workflow or a panel (the allowance, the connection, the health): an event when they appear, change or are solved
        red_rows = list(red_rows) + list(extra_rows)
    if panels:
        from github_actions_monitor.sentinels import sentinel_panels
        red_rows = list(red_rows) + sentinel_panels.alert_rows(panels)      # what the panels of the Sentinel tab ask for travels the same way as a red workflow
    for row in red_rows:
        ident = alert_id(row["repo"], row["workflow"])
        old = state.get(ident)
        diagnosis = old.get("diagnosis") if old and old.get("state") != "resolved" else None
        run = run_id_of(row.get("url"))
        if budget and run and (not diagnosis or diagnosis.get("run") != run):
            budget -= 1
            try:
                diagnosis = diagnose(owner, row["repo"], row.get("url"), runner, cfg["diagnose"]["log_lines"], cfg["diagnose"]["max_bytes"]) or diagnosis
            except Exception as error:   # noqa: BLE001 - a diagnosis that fails never stops the feed
                degraded.note("ai_alerts.diagnose", error)
        text = ((texts or {}).get(ident, "") + "\n" + "\n".join((diagnosis or {}).get("lines") or [])).strip()
        alert = build_alert(row, cfg["transient_patterns"], text)
        alert["diagnosis"] = diagnosis
        alert["origin"] = None
        seen.add(alert["id"])
        if old and old.get("state") != "resolved":
            alert["state"], alert["first_seen"] = old["state"], old.get("first_seen", int(now))
        else:
            alert["state"], alert["first_seen"] = "open", int(now)
            opened.append(alert)
        state[alert["id"]] = alert
    for key, old in list(state.items()):
        if key not in seen and old.get("state") != "resolved":
            old["state"], old["resolved_at"] = "resolved", int(now)
            resolved.append(old)
    for item in state.values():
        if not cfg["cascade"]["enabled"]:
            item["origin"] = None
    if cfg["cascade"]["enabled"]:
        group_cascades(list(state.values()), cfg["cascade"]["map"])
    for alert in opened:      # the events carry the final form of the alert (diagnosis, origin)
        _event(folder, "opened", alert, now)
    for old in resolved:
        _event(folder, "resolved", old, now)
    cutoff = now - 14 * 86400
    state = {k: v for k, v in state.items() if v.get("state") != "resolved" or v.get("resolved_at", 0) > cutoff}
    _write(folder / STATE, json.dumps(state, ensure_ascii=False, indent=1) + "\n")
    alerts = sorted(state.values(), key=lambda a: (a["repo"], a["workflow"]))
    _write(folder / BRIEF, brief(alerts, cfg["brief_max_bytes"], now, panels, sections, status))
    if cfg["hook"]["enabled"]:
        for alert in opened:
            if alert["class"] == "real" and HOOK.allowed(cfg["hook"]["max_per_hour"], now):
                try:
                    HOOK.send(cfg["hook"]["url"], alert, now, opener)
                except Exception as error:   # noqa: BLE001 - a hook that is down never stops the monitor
                    degraded.note("ai_alerts.hook", error)
                    pass
    return {"opened": opened, "resolved": resolved, "alerts": alerts}


def monitor_status(config, status, now=None):
    """The brief says what the monitor is doing while a cycle runs, the connection is down or a cycle failed: the alerts it lists are the ones kept from the last complete cycle (none is opened
    or resolved here, because a partial cycle must not close an alert) and its `Updated` line is the time of this note. False when the feed is off or nothing could be written."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return False
    now = time.time() if now is None else now
    folder = folder_of(cfg)
    try:
        state = _read(folder / STATE, {})
        alerts = sorted(state.values(), key=lambda a: (a["repo"], a["workflow"]))
        private_io.private_dir(folder)
        _write(folder / BRIEF, brief(alerts, cfg["brief_max_bytes"], now, None, "", status))
    except OSError:
        return False
    return True


def ack(config, alert_id_, now=None):
    """Marks an open alert as acknowledged (local state only). True when it existed."""
    cfg = settings(config)
    folder = folder_of(cfg)
    state = _read(folder / STATE, {})
    item = state.get(str(alert_id_))
    if not item or item.get("state") != "open":
        return False
    item["state"] = "acknowledged"
    _write(folder / STATE, json.dumps(state, ensure_ascii=False, indent=1) + "\n")
    _event(folder, "acknowledged", item, time.time() if now is None else now)
    return True


def alerts(config, since=0, states=None):
    """The alerts as a list of dicts with the closed list of fields (plus `first_seen`), those changed after `since` (epoch seconds)."""
    cfg = settings(config)
    state = _read(folder_of(cfg) / STATE, {})
    return [{**{k: a.get(k) for k in FIELDS + EXTRA}, "first_seen": a.get("first_seen")} for a in sorted(state.values(), key=lambda a: (a["repo"], a["workflow"]))
            if (states is None or a.get("state") in states) and max(a.get("first_seen", 0), a.get("resolved_at", 0)) >= since]


def read_brief(config):
    path = folder_of(settings(config)) / BRIEF
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return "# CI alerts\n\nNo cycle has finished yet.\n"


def brief_info(config, now=None):
    """The brief with how old it is: {"brief", "updated" (epoch), "updated_local", "age_seconds"}. `updated` is None before the first cycle."""
    path = folder_of(settings(config)) / BRIEF
    now = time.time() if now is None else now
    try:
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^updated_epoch: (\d+)$", text, re.M)
        stamp = int(match.group(1)) if match else int(path.stat().st_mtime)
    except OSError:
        return {"brief": read_brief(config), "updated": None, "updated_local": None, "age_seconds": None}
    return {"brief": text, "updated": stamp, "updated_local": tzdisplay.stamp(stamp), "age_seconds": max(0, int(now - stamp))}


# -- the heartbeat: who read the feed last, and how
_BEAT = {}


def touch(config, via, client="", now=None):
    """Notes that something read the feed (`via`: stream, mcp, hook, endpoint). A file in the feed folder, so that another process (the MCP server, the gate script) can say it too.
    Not more than once every 5 seconds per way. Returns True when written."""
    cfg = settings(config)
    if not cfg["enabled"] or not cfg["heartbeat"]["enabled"] or via not in VIA:
        return False
    now = time.time() if now is None else now
    if now - _BEAT.get(via, 0) < 5:
        return False
    _BEAT[via] = now
    folder = folder_of(cfg)
    try:
        private_io.private_dir(folder)
        data = _read(folder / HEARTBEAT, {})
        reads = data.get("reads") if isinstance(data.get("reads"), dict) else {}
        reads[via] = {"at": int(now), "client": redact(client, 40)}
        _write(folder / HEARTBEAT, json.dumps({"reads": reads}, ensure_ascii=True) + "\n")
        return True
    except OSError:
        return False


def presence(config, now=None):
    """Is an AI connected? {"enabled", "connected" (a read within `window_minutes`, or a stream open), "last_at", "age_seconds", "via", "client", "streams"}."""
    cfg = settings(config)
    now = time.time() if now is None else now
    out = {"enabled": cfg["enabled"] and cfg["heartbeat"]["enabled"], "connected": False, "last_at": None, "age_seconds": None, "via": None, "client": "", "streams": STREAMS[0]}
    if not out["enabled"]:
        return out
    reads = _read(folder_of(cfg) / HEARTBEAT, {}).get("reads")
    best = None
    for via, item in (reads.items() if isinstance(reads, dict) else []):
        if via in VIA and isinstance(item, dict) and isinstance(item.get("at"), int) and (best is None or item["at"] > best[1]["at"]):
            best = (via, item)
    if best:
        age = max(0, int(now - best[1]["at"]))
        out.update({"last_at": best[1]["at"], "age_seconds": age, "via": best[0], "client": str(best[1].get("client") or "")[:40]})
        out["connected"] = age <= cfg["heartbeat"]["window_minutes"] * 60
    out["connected"] = out["connected"] or STREAMS[0] > 0
    return out


# -- the stream: server-sent events, read only
STREAMS = [0]
STREAM_LOCK = threading.Lock()


def stream_acquire(config):
    """True when one more stream may start (`ai_alerts.stream.max_clients`); call stream_release() when it ends."""
    cfg = settings(config)
    with STREAM_LOCK:
        if STREAMS[0] >= cfg["stream"]["max_clients"]:
            return False
        STREAMS[0] += 1
        return True


def stream_release():
    with STREAM_LOCK:
        STREAMS[0] = max(0, STREAMS[0] - 1)


def public_event(event):
    """One line of the feed as the stream sends it: the closed list of fields, cleaned once more."""
    keep = {k: event.get(k) for k in ("at", "event") + FIELDS + EXTRA if k in event}
    return redact_data(keep)


def _safe_public(event):
    try:
        return public_event(event)
    except (ValueError, TypeError):
        return None


def _frame(name, data, ident=None):
    return (f"id: {ident}\n" if ident is not None else "") + f"event: {name}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


def hello(config, now=None):
    """What a new listener is told when it connects: how many real alerts are open, the first of them and the age of the brief."""
    open_alerts = [a for a in alerts(config, states=("open",)) if a["class"] == "real"]
    info = brief_info(config, now)
    return {"open_real": len(open_alerts), "updated": info["updated"], "age_seconds": info["age_seconds"], "alerts": [e for e in (_safe_public(a) for a in open_alerts[:10]) if e is not None]}


def stream_frames(config, stop=lambda: False, sleep=time.sleep, clock=time.time, offset=None, only_real=False, keepalive=15, poll=1.0):
    """The frames of the stream: `hello` at once, then one `alert` frame per new line of ai_alerts.jsonl (its `id` is the byte offset, to resume with Last-Event-ID), a comment every `keepalive`
    seconds, and `bye` when `ai_alerts.stream.max_seconds` is over or `stop()` says so. Nothing is written anywhere except the heartbeat."""
    cfg = settings(config)
    path = folder_of(cfg) / FEED
    started = clock()
    touch(config, "stream", now=started)
    try:      # where to start is fixed BEFORE the first frame leaves, so nothing written meanwhile is lost
        size = path.stat().st_size
        position = size if offset is None else max(0, min(int(offset), size))
    except (OSError, ValueError):
        position = 0
    yield _frame("hello", hello(config, started))
    last_beat = started
    while not stop() and clock() - started < cfg["stream"]["max_seconds"]:
        try:
            size = path.stat().st_size
            if size < position:
                position = 0
            if size > position:
                with open(path, "rb") as handle:
                    handle.seek(position)
                    chunk = handle.read(size - position)
                for raw in chunk[:chunk.rfind(b"\n") + 1].split(b"\n")[:-1]:
                    position += len(raw) + 1
                    try:
                        event = json.loads(raw.decode("utf-8", "replace"))
                    except ValueError:
                        continue
                    if isinstance(event, dict) and (not only_real or event.get("class") in ("real", None)):
                        try:
                            frame = _frame("alert", public_event(event), position)
                        except (ValueError, TypeError):      # one broken line of the feed never silences the stream: it is skipped
                            continue
                        yield frame
                last_beat = clock()
        except OSError:
            pass
        if clock() - last_beat >= keepalive:
            last_beat = clock()
            touch(config, "stream", now=last_beat)
            yield ": keepalive\n\n"
        sleep(poll)
    yield _frame("bye", {"reason": "stopped" if stop() else "time"})


def hint(row, patterns=None):
    """The optional `ai_hint` of a red workflow in ci_red.json: {"class", "cause", "action"}."""
    alert = build_alert(row, patterns if patterns is not None else TRANSIENT_DEFAULT)
    return {"class": alert["class"], "cause": alert["cause"], "action": alert["action"]}
