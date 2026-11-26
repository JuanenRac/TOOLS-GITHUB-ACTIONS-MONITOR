# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The sound of the monitor: a "bing bing" (two short tones) when something new fails, for the times the page is not open. Standard library only.

The page makes its own sound with the Web Audio API (see actions_monitor.html); this module is the SERVER side, behind `sound.server_beep` (OFF by default). It has the same kinds of event as the page
(a new red, a lost connection, a warning, a solved one, a report, a lesson, a security alert, a stuck run, a score drop, a notice) and the recovery of the live connection, each with its own pattern:

  Windows   winsound.Beep with the tones of the kind (TONES), else winsound.MessageBeep
  macOS     `afplay /System/Library/Sounds/<sound of the kind>.aiff` (a fixed argument list, no shell)
  Linux     `canberra-gtk-play -i <event of the kind>`, else the bell character of the terminal

It never uses the network or a proxy, never runs a shell, never raises (a missing program is simply not a sound), keeps one burst apart from the next by `sound.cooldown_seconds` and keeps the quiet hours.
Settings in actions_monitor.json, block `sound`: enabled (true), on_new_red (true), on_connection_lost (true), on_live_recovered (true), cooldown_seconds (30), volume (40, for the page), server_beep (false),
one switch per kind of event (on_warning, on_resolved, on_report, on_lesson, on_sentinel, on_stuck, on_score_drop, on_info; all true; they rule the sound of this computer too), theme ("classic" or "soft",
for the page) the quiet hours (quiet_enabled false, quiet_from_hour 22, quiet_to_hour 7), `voices` (a text of kind=sound pairs that gives a kind another sound of the library; see soundlib.py), and the two optional
backgrounds of the page and the wall screens, `ambient` / `ambient_volume` (false, 10) and `tick` / `tick_seconds` (false, 1).
"""
import shutil
import subprocess
import sys
import threading
import time

from github_actions_monitor.integrations import soundlib

KINDS = ("new_red", "connection_lost", "live_recovered", "warning", "resolved", "report", "lesson", "sentinel", "stuck", "score_drop", "info")      # one switch `on_<kind>` each; the page has one sound for each (see the table in docs/SOUNDS.md)
PRIORITY = ("new_red", "sentinel", "stuck", "score_drop", "connection_lost", "warning", "resolved", "report", "lesson", "info", "live_recovered")      # the order in which kinds sound when several come in one look
BURST = 3
THEMES = ("classic", "soft")
DEFAULTS = {"enabled": True, **{f"on_{kind}": True for kind in KINDS}, "cooldown_seconds": 30, "volume": 40, "server_beep": False, "theme": "classic", "quiet_enabled": False, "quiet_from_hour": 22, "quiet_to_hour": 7,
            "voices": {}, "ambient": False, "ambient_volume": 10, "tick": False, "tick_seconds": 1}
# the tones of this computer, one pattern per kind with the rhythm of the pattern of the page: (Hz, milliseconds)
TONES = {"new_red": ((880, 150), (1175, 150)), "sentinel": ((330, 140), (330, 140), (330, 140)), "stuck": ((740, 350), (370, 350)), "score_drop": ((784, 160), (622, 160), (466, 280)),
         "connection_lost": ((392, 300), (262, 400)), "warning": ((660, 160), (660, 160)), "resolved": ((523, 120), (659, 120), (784, 250)), "report": ((1047, 120), (784, 300)),
         "lesson": ((1319, 80), (1568, 80), (1976, 160)), "info": ((988, 220),), "live_recovered": ((392, 120), (523, 120), (659, 120), (880, 220))}
# the sound of the system for each kind where the computer has no tone generator (macOS, Linux)
MAC_SOUNDS = {"new_red": "Glass", "sentinel": "Basso", "stuck": "Sosumi", "score_drop": "Funk", "connection_lost": "Bottle", "warning": "Tink", "resolved": "Hero", "report": "Pop", "lesson": "Purr",
              "info": "Ping", "live_recovered": "Blow"}
LINUX_SOUNDS = {"new_red": "bell", "sentinel": "dialog-error", "stuck": "dialog-warning", "score_drop": "software-update-urgent", "connection_lost": "network-connectivity-lost", "warning": "dialog-information", "resolved": "complete",
                "report": "message", "lesson": "software-update-available", "info": "message-new-instant", "live_recovered": "network-connectivity-established"}
_LOCK = threading.Lock()
_LAST = {"at": 0.0}


def settings(config):
    """The block `sound` with every value in its range (a wrong value falls back to the default)."""
    block = config.get("sound") if isinstance(config, dict) and isinstance(config.get("sound"), dict) else {}
    out = dict(DEFAULTS)
    for key in ("enabled", "server_beep", "quiet_enabled", "ambient", "tick", *[f"on_{kind}" for kind in KINDS]):
        if isinstance(block.get(key), bool):
            out[key] = block[key]
    if block.get("theme") in THEMES:
        out["theme"] = block["theme"]
    for key, low, high in (("cooldown_seconds", 0, 3600), ("volume", 1, 100), ("quiet_from_hour", 0, 23), ("quiet_to_hour", 0, 23), ("ambient_volume", 1, 50), ("tick_seconds", 1, 60)):
        value = block.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    out["voices"] = soundlib.parse_voices(block.get("voices"))      # a kind of event with another sound of the library (soundlib.py)
    return out


def quiet(cfg, now=None):
    """True inside the quiet hours of the settings (the hours of this computer; they may cross midnight)."""
    if not cfg["quiet_enabled"] or cfg["quiet_from_hour"] == cfg["quiet_to_hour"]:
        return False
    hour = time.localtime(time.time() if now is None else now).tm_hour
    low, high = cfg["quiet_from_hour"], cfg["quiet_to_hour"]
    return low <= hour < high if low < high else (hour >= low or hour < high)


def allowed(cfg, reason, now=None, mark=True):
    """Should a beep sound now for this kind of event (one of KINDS)? Counts the cooldown since the last one and, with `mark`, starts a new one."""
    if not (cfg["enabled"] and cfg["server_beep"]) or reason not in KINDS or not cfg[f"on_{reason}"]:
        return False
    now = time.time() if now is None else now
    if quiet(cfg, now):
        return False
    with _LOCK:
        if now - _LAST["at"] < cfg["cooldown_seconds"]:
            return False
        if mark:
            _LAST["at"] = now
    return True


def tones_of(kind, voices=None):
    """The (Hz, milliseconds) of a kind on this computer: the sound the settings gave it (sound.voices) or its own."""
    name = (voices or {}).get(kind)
    return soundlib.server_tones(name) if name else TONES[kind]


def _play(runner=None, kinds=("new_red",), voices=None):
    """Plays the kinds one after the other, in this thread. Returns the way it sounded ("winsound", "afplay", "canberra", "bell") or "" when nothing could."""
    runner = runner or (lambda args: subprocess.run(args, shell=False, check=False, timeout=5, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    kinds = [k for k in kinds if k in KINDS] or ["new_red"]
    try:
        if sys.platform == "win32":
            import winsound
            try:
                for kind in kinds:
                    for hertz, length in tones_of(kind, voices):
                        winsound.Beep(hertz, length)
                    time.sleep(0.25)
                return "winsound"
            except RuntimeError:
                winsound.MessageBeep()
                return "winsound"
        if sys.platform == "darwin":
            if shutil.which("afplay"):
                for kind in kinds:
                    runner(["afplay", f"/System/Library/Sounds/{MAC_SOUNDS[kind]}.aiff"])
                return "afplay"
            return ""
        if shutil.which("canberra-gtk-play"):
            for kind in kinds:
                runner(["canberra-gtk-play", "-i", LINUX_SOUNDS[kind]])
            return "canberra"
        if sys.stdout and sys.stdout.isatty():
            sys.stdout.write("\a")
            sys.stdout.flush()
            return "bell"
    except Exception:   # noqa: BLE001 - a sound never stops the monitor
        return ""
    return ""


def beep_kinds(config, kinds, now=None, runner=None, wait=False):
    """Sounds the kinds that the settings allow in ONE burst (the most serious first, at most BURST of them), in a thread of its own. Returns the kinds that sounded (an empty list when none did)."""
    cfg = settings(config)
    wanted = set(kinds or ())
    chosen = [k for k in PRIORITY if k in wanted and cfg[f"on_{k}"]][:BURST]
    if not chosen or not allowed(cfg, chosen[0], now):
        return []
    thread = threading.Thread(target=_play, args=(runner, tuple(chosen)), kwargs={"voices": cfg["voices"]} if cfg["voices"] else {}, daemon=True)
    thread.start()
    if wait:
        thread.join(5)
    return chosen


def beep(config, reason="new_red", now=None, runner=None, wait=False):
    """Sounds one kind of event on this computer when the settings allow it; the sound runs in its own thread (it takes about half a second). Returns True when a sound was started."""
    return bool(beep_kinds(config, [reason], now, runner, wait))


def kind_of(code, level=""):
    """Which kind an alert of the list is (the same rule as the page): the code says it, else the level."""
    code, level = str(code or ""), str(level or "")
    if code in ("ci.red", "ci.external.red"):
        return "new_red"
    if code == "score.dropped":
        return "score_drop"
    if code in ("ci.stuck", "ci.ghost_queue") or code.startswith("runner."):
        return "stuck"
    if code.startswith(("security.", "system.")) or level in ("error", "critical"):
        return "sentinel"
    return "warning" if level == "warning" else "info"


class Watch:
    """What is new between two looks at the list of alerts, for the sound of this computer: a new alert sounds as its kind, a serious one that is gone sounds as solved, a silenced one never sounds and the
    first look only remembers (`ci.red` has its own look in the cycle)."""

    def __init__(self):
        self.known = None

    def look(self, alerts):
        current = {}
        for item in alerts or []:
            if isinstance(item, dict) and item.get("id") and item.get("code") != "ci.red":
                current[str(item["id"])] = (kind_of(item.get("code"), item.get("level")), bool(item.get("muted_until")))
        previous, self.known = self.known, current
        if previous is None:
            return []
        kinds = [kind for key, (kind, muted) in current.items() if key not in previous and not muted]
        if any(kind in ("sentinel", "stuck", "score_drop") for key, (kind, muted) in previous.items() if key not in current and not muted):
            kinds.append("resolved")
        return kinds


def report_keys(reports):
    """What the four optional reports show now, one key each (the same ones as the page): a key that was not there at the last look is a new report."""
    keys = set()
    reports = reports if isinstance(reports, dict) else {}

    def rows(name, field="repos"):
        part = reports.get(name)
        return [r for r in (part.get(field) or []) if isinstance(r, dict)] if isinstance(part, dict) and part.get("enabled") else []
    for repo in rows("workflow_hygiene"):
        keys.update(f"h|{repo.get('repo')}|{f.get('rule')}" for f in repo.get("findings") or [] if isinstance(f, dict))
    keys.update(f"r|{r.get('repo')}" for r in rows("release_view") if r.get("state") == "blocked")
    keys.update(f"s|{r.get('repo')}|{r.get('tag') or ''}" for r in rows("supply_chain") if not (r.get("sbom") and r.get("signature")))
    queue = reports.get("queue")
    if isinstance(queue, dict) and queue.get("enabled") and isinstance(queue.get("groups"), dict):
        keys.update(f"q|{g}" for g in queue["groups"])
    return keys


def lesson_keys(lessons):
    """The categories of the lessons that appear, repeat or apply now (the same keys as the page)."""
    keys = set()
    if isinstance(lessons, dict) and lessons.get("enabled"):
        keys.update(f"{c.get('category')}|{'r' if c.get('recurring') else 'n'}" for c in lessons.get("categories") or [] if isinstance(c, dict))
        keys.update(f"now|{x.get('category')}" for x in lessons.get("apply_now") or [] if isinstance(x, dict))
    return keys


class KeyWatch:
    """A new kind of sound for a set of keys that grows: the first look only remembers, a key that was not there before is news."""

    def __init__(self, kind):
        self.kind, self.known = kind, None

    def look(self, keys):
        keys = set(keys)
        previous, self.known = self.known, keys
        return [self.kind] if previous is not None and keys - previous else []


def reset():
    """For the tests: forget the last beep."""
    with _LOCK:
        _LAST["at"] = 0.0
