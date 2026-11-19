# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Updates menu: the updater of the monitor (tools/monitor_updater.py) used from inside the page.

One engine, not two: this module loads the very same file the command `monitor_cli update` and the stand-alone page use, and calls it. The file stays where it is because it is also the way back
when the monitor does not start.

  status(...)      what the page shows without asking GitHub: the installed version, the version the notice found, the switches, whether this installation can be updated from here and why not
  check(...)       the list of published versions with their notes (ONE request to GitHub, only on explicit action, only while updates.check is on and the monitor is online)
  plan(target)     what would happen: the checks, the copy, the migrations, the restart (it changes nothing)
  apply(...)       starts the update in a process of its own and asks the monitor to stop: that process waits for the monitor, applies the update, starts the monitor again and, when it does not
                   start, puts the previous version back (and starts that one)
  rollback(...)    the same for the way back to the version before the last update
  progress()       the small JSON file that process writes: it survives the restart of the monitor
  history()        the updates already done and the ones undone

Nothing is downloaded or applied without an explicit action; the files of the person (configuration, data, keys, logs) are the updater's USER_RULES and are not touched here."""
import contextlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.util.paths import ROOT

TOOL = ROOT / "tools" / "monitor_updater.py"
STATUS_NAME = "update_status.json"
LOG_NAME = "updater_handover.log"
MAX_FAILURES = 5             # refused or failed attempts to apply / go back inside WINDOW before the cooldown starts
WINDOW = 600                  # seconds in which the failures are counted
COOLDOWN = 600                # seconds the menu refuses a new apply or way back after MAX_FAILURES (a stolen token cannot hammer the updater)
MAX_STATUS_BYTES = 262144     # a progress file larger than this is not read (it is never that big: events of one update)
START_GRACE = 180            # seconds a "starting" mark is believed while the process that applies the update has not yet written its own
NO_WINDOW = 0x08000000        # CREATE_NO_WINDOW: a hidden console that the git and gh calls of the monitor inherit
NEW_GROUP = 0x00000200        # CREATE_NEW_PROCESS_GROUP; never the flag that detaches from the console (a process without a console makes every child open a window)
_lock = threading.Lock()
_failures = []                # monotonic times of the recent failed attempts
_cooldown = {"until": 0.0}
_module = {"obj": None}


class UpdatesError(Exception):
    """A refusal with a short code the page translates (never a path, never the request)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def module():
    """The updater, loaded from its file (or None when the file is not there: a copy of the product without tools/)."""
    if _module["obj"] is None:
        if not TOOL.is_file():
            return None
        known = sys.modules.get("monitor_updater")
        if known is not None and Path(getattr(known, "__file__", "") or "").resolve() == TOOL.resolve():
            _module["obj"] = known      # already loaded from this very file (the command line, a test): one copy, not two
            return known
        spec = importlib.util.spec_from_file_location("monitor_updater", TOOL)
        loaded = importlib.util.module_from_spec(spec)
        sys.modules["monitor_updater"] = loaded
        spec.loader.exec_module(loaded)
        _module["obj"] = loaded
    return _module["obj"]


def test_zip(env=None):
    """The zip a test asks the updater to use instead of GitHub, or None. Both MONITOR_TEST_HOOKS=1 and MONITOR_TEST_UPDATE_ZIP (a file that exists) are needed; without them nothing changes. It never relaxes a
    check: the zip is the same local source the command line offers with --zip, so its contents, members and SHA-256 are checked as always."""
    env = os.environ if env is None else env
    path = env.get("MONITOR_TEST_UPDATE_ZIP", "")
    if env.get("MONITOR_TEST_HOOKS") == "1" and path and Path(path).is_file():
        return str(path)
    return None


def updater(source=None):
    mod = module()
    if mod is None:
        raise UpdatesError("tool_missing")
    hooked = test_zip()
    if source is None and hooked:
        source = mod.LocalZipSource(hooked)
    return mod, mod.Updater(ROOT, source or mod.GitHubSource(prefer_gh=True))


def status_file(up):
    return up.backups / STATUS_NAME


def cooldown_left(now=None):
    """Seconds still to wait before a new apply or way back is accepted (0 when none)."""
    now = time.monotonic() if now is None else now
    return max(0, int(_cooldown["until"] - now + 0.999)) if _cooldown["until"] > now else 0


def note_failure(now=None):
    """A refused or failed attempt. MAX_FAILURES inside WINDOW start the cooldown."""
    now = time.monotonic() if now is None else now
    _failures[:] = [t for t in _failures if now - t < WINDOW] + [now]
    if len(_failures) >= MAX_FAILURES:
        _cooldown["until"] = now + COOLDOWN
        del _failures[:]


def note_success():
    del _failures[:]
    _cooldown["until"] = 0.0


def reason_blocked(lite=False, demo=False, env=None):
    """Why this installation cannot be updated from the page ('' when it can). A service manager or a container owns the process: the update is made the way their documents say."""
    mod = module()
    if mod is None:
        return "tool_missing"
    if demo:
        return "demo"
    if lite:
        return "lite"
    if mod.in_container(env):
        return "container"
    if mod.under_service(env):
        return "service"
    return ""


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=10, creationflags=NO_WINDOW).stdout
            return str(pid) in out
        os.kill(pid, 0)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def progress():
    """What the process of the update wrote; a process that is gone without finishing is reported as stopped, never as running for ever."""
    mod = module()
    if mod is None:
        return {"running": False}
    path = status_file(mod.Updater(ROOT, mod.GitHubSource(prefer_gh=False)))
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_STATUS_BYTES:      # a link or a huge file is not the file the updater wrote
            return {"running": False}
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"running": False}
    if not isinstance(doc, dict):
        return {"running": False}
    if doc.get("running") and not pid_alive(doc.get("pid")) and not (doc.get("starting") and time.time() - float(doc.get("t") or 0) < START_GRACE):
        doc["running"], doc["stopped"] = False, True
    doc.pop("pid", None)
    return doc


def running():
    return bool(progress().get("running"))


STREAM_MAX_SECONDS = 900     # a listener is let go after this long (the page asks again if the update is still going)
STREAM_MAX_LISTENERS = 2
_STREAM = {"open": 0}
_STREAM_GUARD = threading.Lock()


def stream_acquire():
    with _STREAM_GUARD:
        if _STREAM["open"] >= STREAM_MAX_LISTENERS:
            return False
        _STREAM["open"] += 1
        return True


def stream_release():
    with _STREAM_GUARD:
        _STREAM["open"] = max(0, _STREAM["open"] - 1)


def _frame(event, data, number=None):
    head = "" if number is None else "id: %d\n" % number
    return "%sevent: %s\ndata: %s\n\n" % (head, event, json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def stream_frames(read=None, sleep=time.sleep, clock=time.monotonic, poll=0.5, keepalive=15.0, max_seconds=None, stop=lambda: False):
    """The progress of the update as server-sent events instead of a request every second and a half. `hello` first, then one `progress` frame each time what progress() answers changes (the same JSON
    the polling route gives, so the page has ONE reader for both), a comment every `keepalive` seconds, and `bye` when the update is over (nothing is running any more), the time is up or `stop()`
    says so. It reads the very small status file the process of the update writes; it asks nothing of GitHub and changes nothing."""
    read = read or progress
    limit = STREAM_MAX_SECONDS if max_seconds is None else max_seconds
    started = clock()
    current = read()
    yield _frame("hello", {"running": bool(current.get("running"))})
    last, number, beat = None, 0, started
    while not stop() and clock() - started < limit:
        text = json.dumps(current, sort_keys=True, default=str)
        if text != last:
            last, number, beat = text, number + 1, clock()
            yield _frame("progress", current, number)
        if not current.get("running"):
            yield _frame("bye", {"reason": "done"})
            return
        if clock() - beat >= keepalive:
            beat = clock()
            yield ": keepalive\n\n"
        sleep(poll)
        current = read()
    yield _frame("bye", {"reason": "stopped" if stop() else "time"})


def status(config, tool_version, notice, lite=False, demo=False, env=None):
    """The state for the page without any request to GitHub. `notice` is the view of the update notice the monitor already keeps."""
    mod = module()
    blocked = reason_blocked(lite, demo, env)
    out = {"installed": tool_version, "available": (notice or {}).get("latest") if (notice or {}).get("newer") else "", "newer": bool((notice or {}).get("newer")),
           "check": bool((notice or {}).get("enabled", True)), "offline": bool((notice or {}).get("offline")), "airgapped": bool((notice or {}).get("airgapped")),
           "can_apply": not blocked, "blocked_by": blocked, "blocked_reason": blocked or ("cooldown" if cooldown_left() else ""), "cooldown_seconds": cooldown_left(), "progress": progress(), "last": None, "can_go_back": False, "updater": getattr(mod, "UPDATER_VERSION", "") if mod else ""}
    if mod is not None:
        up = mod.Updater(ROOT, mod.GitHubSource(prefer_gh=False))
        history = up.history()
        out["last"] = history[-1] if history else None
        out["can_go_back"] = bool(up.previous())
    return out


def check(notice_settings, offline):
    """The published versions with their notes. Refused when the check is off or the monitor is offline; one request, only on explicit action."""
    if not notice_settings.get("check", True):
        raise UpdatesError("check_off")
    if offline:
        raise UpdatesError("offline")
    mod, up = updater()
    try:
        rels = up.annotate(up.releases(refresh=True))
    except mod.UpdaterError as error:
        raise UpdatesError("fetch_failed") from error
    return [{"version": r["version"], "name": r["name"], "published": r["published"], "notes": r["body"][:6000], "prerelease": r["prerelease"], "relation": r["relation"], "latest": r["latest"],
             "has_zip": mod.ZIP_NAME in r["assets"], "has_sums": "SHA256SUMS" in r["assets"]} for r in rels[:30] if not r["draft"]]


def plan(target, policy="conservative"):
    """What the update would do. The SHA256SUMS of the zip is checked here (the plan downloads and verifies the zip) and the result says whether it was verified."""
    mod, up = updater()
    try:
        done = up.plan(target or "latest", {"policy": policy if policy in ("conservative", "keep_old", "adopt_new") else "conservative", "handover": True, "allow_downgrade": False})
    finally:
        up.cleanup()
    for entry in done["config"]:
        for change in entry["changes"]:
            change["text"] = mod._change_text(change)
    done["backups"] = str(up.backups)
    return done


def _spawn(args, up):
    up.backups.mkdir(parents=True, exist_ok=True)
    logs = up.folders()["logs"]
    logs.mkdir(parents=True, exist_ok=True)
    kwargs = {"creationflags": NEW_GROUP | NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    with open(logs / LOG_NAME, "ab") as log:      # the child keeps its own copy of the handle; ours is closed here (no ResourceWarning, no handle left open)
        return subprocess.Popen([sys.executable, "-I", str(TOOL), *args], cwd=str(ROOT), stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs)


def _first_status(up, kind):
    path = status_file(up)
    path.parent.mkdir(parents=True, exist_ok=True)
    private_io.write_private(path, json.dumps({"kind": kind, "running": True, "starting": True, "t": time.time(), "events": [], "text": "", "report": None, "pid": os.getpid()}))


def apply(target, policy, confirm, edition, lang, lite=False, demo=False, env=None):
    """Starts the update. Needs the explicit confirmation of the person, one update at a time, and a plan that is not blocked. Returns what the page shows while the monitor stops."""
    if confirm is not True:
        raise UpdatesError("not_confirmed")
    blocked = reason_blocked(lite, demo, env)
    if blocked:
        raise UpdatesError(blocked)
    if cooldown_left():
        raise UpdatesError("cooldown")
    with _lock:
        if running():
            raise UpdatesError("busy")
        try:
            mod, up = updater()
            done = plan(target, policy)
            if done["blocked"]:
                raise UpdatesError("blocked")
            if done["direction"] == "same":
                raise UpdatesError("same")
        except Exception:
            note_failure()
            raise
        _first_status(up, "apply")
        args = ["apply", "--dir", str(ROOT), "--to", done["target"], "--yes", "--start", "--handover", "--status-file", str(status_file(up)), "--edition", "lite" if edition == "lite" else "complete",
                "--lang", lang or "en"] + {"keep_old": ["--keep-old-defaults"], "adopt_new": ["--adopt-new-defaults"]}.get(policy, [])
        if test_zip():
            args += ["--zip", test_zip()]
        _spawn(args, up)
        note_success()
        return {"started": True, "from": done["installed"], "to": done["target"], "backups": str(up.backups)}


def rollback(confirm, edition, lang, lite=False, demo=False, env=None):
    """The way back to the version before the last update, with the data when the schema asks for it; the same process, the same restart."""
    if confirm is not True:
        raise UpdatesError("not_confirmed")
    blocked = reason_blocked(lite, demo, env)
    if blocked:
        raise UpdatesError(blocked)
    if cooldown_left():
        raise UpdatesError("cooldown")
    with _lock:
        if running():
            raise UpdatesError("busy")
        mod, up = updater()
        if not up.previous():
            note_failure()
            raise UpdatesError("no_previous")
        _first_status(up, "rollback")
        _spawn(["rollback", "--dir", str(ROOT), "--yes", "--handover", "--status-file", str(status_file(up)), "--lang", lang or "en"], up)
        note_success()
        return {"started": True}


def history():
    mod = module()
    if mod is None:
        return []
    up = mod.Updater(ROOT, mod.GitHubSource(prefer_gh=False))
    return [{k: e.get(k) for k in ("at", "result", "from", "to", "backup", "error")} for e in reversed(up.history()[-50:])]


def stop_soon(server, seconds=1.5):
    """After the answer is sent: the monitor stops by itself so that the update can replace it (the process that applies it is waiting). A watchdog ends the process if the stop hangs."""
    def go():
        with contextlib.suppress(Exception):
            server.shutdown()
        threading.Timer(20, lambda: os._exit(0)).start()
    threading.Timer(seconds, go).start()
