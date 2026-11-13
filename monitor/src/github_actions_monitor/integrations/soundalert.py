# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The sound of the monitor: a "bing bing" (two short tones) when something new fails, for the times the page is not open. Standard library only.

The page makes its own sound with the Web Audio API (see actions_monitor.html); this module is the SERVER side, behind `sound.server_beep` (OFF by default):

  Windows   winsound.Beep twice (880 Hz and 1175 Hz, 150 ms), else winsound.MessageBeep
  macOS     `afplay /System/Library/Sounds/Glass.aiff` (a fixed argument list, no shell)
  Linux     `canberra-gtk-play -i bell`, else the bell character of the terminal

It never uses the network or a proxy, never runs a shell, never raises (a missing program is simply not a sound) and keeps one beep apart from the next by `sound.cooldown_seconds`.
Settings in actions_monitor.json, block `sound`: enabled (true), on_new_red (true), on_connection_lost (true), cooldown_seconds (30), volume (40, for the page), server_beep (false).
"""
import shutil
import subprocess
import sys
import threading
import time

DEFAULTS = {"enabled": True, "on_new_red": True, "on_connection_lost": True, "cooldown_seconds": 30, "volume": 40, "server_beep": False}
_LOCK = threading.Lock()
_LAST = {"at": 0.0}


def settings(config):
    """The block `sound` with every value in its range (a wrong value falls back to the default)."""
    block = config.get("sound") if isinstance(config, dict) and isinstance(config.get("sound"), dict) else {}
    out = dict(DEFAULTS)
    for key in ("enabled", "on_new_red", "on_connection_lost", "server_beep"):
        if isinstance(block.get(key), bool):
            out[key] = block[key]
    for key, low, high in (("cooldown_seconds", 0, 3600), ("volume", 1, 100)):
        value = block.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    return out


def allowed(cfg, reason, now=None, mark=True):
    """Should a beep sound now for this reason ("new_red" | "connection_lost")? Counts the cooldown since the last one and, with `mark`, starts a new one."""
    if not (cfg["enabled"] and cfg["server_beep"]):
        return False
    if not cfg["on_new_red" if reason == "new_red" else "on_connection_lost"]:
        return False
    now = time.time() if now is None else now
    with _LOCK:
        if now - _LAST["at"] < cfg["cooldown_seconds"]:
            return False
        if mark:
            _LAST["at"] = now
    return True


def _play(runner=None):
    """Plays it once, in this thread. Returns the way it sounded ("winsound", "afplay", "canberra", "bell") or "" when nothing could."""
    runner = runner or (lambda args: subprocess.run(args, shell=False, check=False, timeout=5, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    try:
        if sys.platform == "win32":
            import winsound
            try:
                winsound.Beep(880, 150)
                winsound.Beep(1175, 150)
                return "winsound"
            except RuntimeError:
                winsound.MessageBeep()
                return "winsound"
        if sys.platform == "darwin":
            if shutil.which("afplay"):
                runner(["afplay", "/System/Library/Sounds/Glass.aiff"])
                return "afplay"
            return ""
        if shutil.which("canberra-gtk-play"):
            runner(["canberra-gtk-play", "-i", "bell"])
            return "canberra"
        if sys.stdout and sys.stdout.isatty():
            sys.stdout.write("\a")
            sys.stdout.flush()
            return "bell"
    except Exception:   # noqa: BLE001 - a sound never stops the monitor
        return ""
    return ""


def beep(config, reason="new_red", now=None, runner=None, wait=False):
    """Sounds the alert on this computer when the settings allow it; the sound runs in its own thread (it takes about half a second). Returns True when a sound was started."""
    cfg = settings(config)
    if not allowed(cfg, reason, now):
        return False
    thread = threading.Thread(target=_play, args=(runner,), daemon=True)
    thread.start()
    if wait:
        thread.join(5)
    return True


def reset():
    """For the tests: forget the last beep."""
    with _LOCK:
        _LAST["at"] = 0.0
