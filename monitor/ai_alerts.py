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
"""
import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEED = "ai_alerts.jsonl"
BRIEF = "ALERTS_BRIEF.md"
STATE = "ai_alerts_state.json"
FIELDS = ("id", "severity", "class", "repo", "workflow", "conclusion", "since", "streak", "url", "cause", "action", "state")      # the closed list a hook or an endpoint may carry
TRANSIENT_DEFAULT = [r"\b50[234]\b", r"bad gateway", r"service unavailable", r"gateway time-?out", r"timed? ?out", r"rate limit", r"secondary rate", r"tls", r"connection (?:reset|refused|closed)",
                     r"unexpected eof", r"codeql.*download", r"download.*codeql", r"could not resolve host", r"no space left", r"the runner has received a shutdown signal"]
LOOP_RE = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{2,5}(/[A-Za-z0-9._~/%-]{0,100})?$")

_SECRETS = [
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,})"), "[token]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{12,}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,})"), "[key]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "[jwt]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 [secret]"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization)\b(\s*[:=]\s*)\S+"), r"\1\2[secret]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[ip]"),
    (re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}\b"), "[ip]"),
    (re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s]+"), "~"),
    (re.compile(r"/(?:home|Users)/[^/\s]+"), "~"),
    (re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}"), "[blob]"),
]


def redact(text, limit=None):
    """The text without tokens, keys, e-mail addresses, IP addresses, the home folder of a person and long opaque strings."""
    out = str(text or "")
    home = str(Path.home())
    for variant in {home, home.replace("\\", "/")}:
        if len(variant) > 3:
            out = out.replace(variant, "~")
    for pattern, replacement in _SECRETS:
        out = pattern.sub(replacement, out)
    return out[:limit] if limit else out


def settings(config):
    cfg = config.get("ai_alerts") if isinstance(config, dict) and isinstance(config.get("ai_alerts"), dict) else {}
    hook = cfg.get("hook") if isinstance(cfg.get("hook"), dict) else {}
    size = cfg.get("brief_max_bytes")
    per_hour = hook.get("max_per_hour")
    patterns = cfg.get("transient_patterns") if isinstance(cfg.get("transient_patterns"), list) else TRANSIENT_DEFAULT
    return {"enabled": cfg.get("enabled", True) is True, "folder": cfg.get("folder") if isinstance(cfg.get("folder"), str) else "",
            "brief_max_bytes": size if isinstance(size, int) and not isinstance(size, bool) and 512 <= size <= 20000 else 2048,
            "transient_patterns": [p for p in patterns if isinstance(p, str) and 0 < len(p) <= 120][:40],
            "hook": {"enabled": hook.get("enabled") is True and bool(LOOP_RE.match(str(hook.get("url") or ""))), "url": str(hook.get("url") or ""),
                     "max_per_hour": per_hour if isinstance(per_hour, int) and not isinstance(per_hour, bool) and 1 <= per_hour <= 60 else 6}}


def folder_of(cfg):
    text = cfg["folder"].strip()
    ok = bool(text) and len(text) <= 260 and not any(ord(c) < 32 for c in text) and not text.startswith(("\\\\", "//")) and not re.match(r"^(?:[Dd]:|/mnt/[dD](?:/|$))", text)
    return Path(text) if ok else HERE


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


def build_alert(row, patterns, text=""):
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
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _event(folder, kind, alert, now):
    line = {"at": int(now), "event": kind, **{k: alert.get(k) for k in FIELDS}}
    with open(Path(folder) / FEED, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def brief(alerts, limit):
    """The Markdown an AI reads when it starts: open alerts, the real ones first, within `limit` bytes."""
    live = [a for a in alerts if a["state"] != "resolved"]
    live.sort(key=lambda a: (a["state"] == "acknowledged", a["class"] != "real", a["repo"], a["workflow"]))
    real = sum(1 for a in live if a["class"] == "real" and a["state"] == "open")
    lines = ["# CI alerts", "", f"{real} real alert(s) open, {len(live)} in total. Transient ones usually clear by themselves; re-run once before you dig.", ""]
    for a in live:
        mark = {"open": "", "acknowledged": " (acknowledged)"}[a["state"]]
        lines.append(f"- [{a['severity']}/{a['class']}] {a['repo']} / {a['workflow']}: {a['conclusion']} x{a['streak']}{mark} - {a['cause']}. Next: {a['action']}. {a.get('url') or ''}".rstrip())
    text = "\n".join(lines) + "\n"
    if len(text.encode("utf-8")) > limit:
        kept = []
        for index, line in enumerate(lines):
            candidate = "\n".join(kept + [line, f"- ... and {len(lines) - index - 1} more in ai_alerts.jsonl"]) + "\n"
            if len(candidate.encode("utf-8")) > limit:
                break
            kept.append(line)
        text = "\n".join(kept + [f"- ... and {max(0, len(lines) - len(kept))} more in ai_alerts.jsonl"]) + "\n"
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
        (opener or (lambda r: urllib.request.urlopen(r, timeout=5).read()))(request)
        self.sent.append(now)


HOOK = Hook()


def update(config, red_rows, now=None, texts=None, opener=None):
    """Brings the feed up to date with the red workflows of this cycle. Returns {"opened": [...], "resolved": [...], "alerts": [...]}. Nothing is written when the feed is off."""
    cfg = settings(config)
    now = time.time() if now is None else now
    if not cfg["enabled"]:
        return {"opened": [], "resolved": [], "alerts": []}
    folder = folder_of(cfg)
    folder.mkdir(parents=True, exist_ok=True)
    state = _read(folder / STATE, {})
    seen, opened, resolved = set(), [], []
    for row in red_rows:
        alert = build_alert(row, cfg["transient_patterns"], (texts or {}).get(alert_id(row["repo"], row["workflow"]), ""))
        seen.add(alert["id"])
        old = state.get(alert["id"])
        if old and old.get("state") != "resolved":
            alert["state"], alert["first_seen"] = old["state"], old.get("first_seen", int(now))
        else:
            alert["state"], alert["first_seen"] = "open", int(now)
            opened.append(alert)
            _event(folder, "opened", alert, now)
        state[alert["id"]] = alert
    for key, old in list(state.items()):
        if key not in seen and old.get("state") != "resolved":
            old["state"], old["resolved_at"] = "resolved", int(now)
            resolved.append(old)
            _event(folder, "resolved", old, now)
    cutoff = now - 14 * 86400
    state = {k: v for k, v in state.items() if v.get("state") != "resolved" or v.get("resolved_at", 0) > cutoff}
    _write(folder / STATE, json.dumps(state, ensure_ascii=False, indent=1) + "\n")
    alerts = sorted(state.values(), key=lambda a: (a["repo"], a["workflow"]))
    _write(folder / BRIEF, brief(alerts, cfg["brief_max_bytes"]))
    if cfg["hook"]["enabled"]:
        for alert in opened:
            if alert["class"] == "real" and HOOK.allowed(cfg["hook"]["max_per_hour"], now):
                try:
                    HOOK.send(cfg["hook"]["url"], alert, now, opener)
                except Exception:   # noqa: BLE001 - a hook that is down never stops the monitor
                    pass
    return {"opened": opened, "resolved": resolved, "alerts": alerts}


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
    return [{**{k: a.get(k) for k in FIELDS}, "first_seen": a.get("first_seen")} for a in sorted(state.values(), key=lambda a: (a["repo"], a["workflow"]))
            if (states is None or a.get("state") in states) and max(a.get("first_seen", 0), a.get("resolved_at", 0)) >= since]


def read_brief(config):
    path = folder_of(settings(config)) / BRIEF
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return "# CI alerts\n\nNo cycle has finished yet.\n"


def hint(row, patterns=None):
    """The optional `ai_hint` of a red workflow in ci_red.json: {"class", "cause", "action"}."""
    alert = build_alert(row, patterns if patterns is not None else TRANSIENT_DEFAULT)
    return {"class": alert["class"], "cause": alert["cause"], "action": alert["action"]}
