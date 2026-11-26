# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The window that announces a newer version (setting updates.notify_window, on by default). It only reads what the update check already keeps: no request of its own is made."""
from github_actions_monitor import families
from github_actions_monitor.app import updatecheck


def enabled(config):
    return families.block(config, "updates").get("notify_window") is True


def answer(info, config, language):
    """The JSON of the window from the view of the update check: `show` is true only when there is a newer version, the window is on and that version was not dismissed."""
    show = bool(enabled(config) and info.get("newer") and not info.get("dismissed"))
    if not show:
        return {"show": False}
    return {"show": True, "version": info.get("latest", ""), "current": info.get("current", ""), "notes": updatecheck.pick_notes(info.get("notes"), language),
            "url": info.get("url", ""), "changelog": info.get("changelog", ""), "command": info.get("command", "")}


def state(request):
    from github_actions_monitor.app import actions_monitor
    return answer(actions_monitor.update_info(read=False), request.config, request.query.get("lang", "en"))


def dismiss(request):
    from github_actions_monitor.app import actions_monitor
    version = request.body.get("version")
    path = actions_monitor.state_dir() / ("update_check_lite.json" if actions_monitor.LITE["on"] else "update_check.json")
    if not isinstance(version, str) or len(version) > 40 or not updatecheck.dismiss(version, path):
        return 400, {"ok": False, "error": "version"}
    return {"ok": True}
