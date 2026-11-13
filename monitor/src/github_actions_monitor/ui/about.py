# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The About panel: what the tool is, which version and edition runs, where its files are and whether it is healthy. The same data feeds the web panel (`/api/about`), the console
(`--about`, the terminal views) and the "copy for support" text. It holds no secret: no token, no key, no webhook secret, no list of repositories; the home folder of the user is shown as `~`
in the text meant to be pasted somewhere else.
"""
import platform
from pathlib import Path

from github_actions_monitor.app import updatecheck
from github_actions_monitor.tool_version import AUTHOR, LICENSE_ID, TOOL_VERSION

REPO_URL = "https://github.com/" + updatecheck.REPO
LINKS = {"repository": REPO_URL, "releases": REPO_URL + "/releases", "changelog": REPO_URL + "/blob/main/CHANGELOG.md", "documentation": REPO_URL + "#readme", "bridge": REPO_URL + "/blob/main/monitor/docs/CI_RED_BRIDGE.md",
         "issues": REPO_URL + "/issues", "license": REPO_URL + "/blob/main/LICENSE"}
CREDITS = (("python", "Python", "PSF-2.0", None), ("gh", "GitHub CLI (gh)", "MIT", None), ("rich", "Rich", "MIT", "rich"), ("textual", "Textual", "MIT", "textual"))


def library_state(module):
    if module is None:
        return True
    try:
        import importlib.util
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def home_free(text):
    """The home folder of the user replaced by ~ (the text is meant to be pasted in an issue)."""
    text = str(text)
    home = str(Path.home())
    for variant in {home, home.replace("\\", "/")}:
        if variant and len(variant) > 3:
            text = text.replace(variant, "~")
    return text


def info(lite, health, paths, update, language):
    """The dictionary of the panel. `paths` is {"config": Path, "log": Path, ...} (names to files; only the paths are shown, never their content)."""
    return {"version": TOOL_VERSION, "edition": "lite" if lite else "complete", "author": AUTHOR, "license": LICENSE_ID, "links": dict(LINKS),
            "python": platform.python_version(), "implementation": platform.python_implementation(), "system": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "paths": {name: home_free(path) for name, path in paths.items()}, "health": health, "update": update, "language": language,
            "credits": [{"id": i, "name": n, "license": lic, "installed": library_state(mod)} for i, n, lic, mod in CREDITS]}


def support_text(data):
    """The block to paste in an issue: versions, edition, system, health and the folder names; no secret by construction (it is built from the fields above only)."""
    health = data.get("health") or {}
    update = data.get("update") or {}
    lines = [f"GitHub Actions Monitor {data['version']} ({data['edition']})", f"Python {data['python']} ({data['implementation']})", f"System: {data['system']}",
             f"Language: {data.get('language', '')}", f"License: {data['license']}",
             "Health: " + ", ".join(f"{k}={health[k]}" for k in ("ok", "loaded", "offline", "uptime_seconds", "degraded") if k in health),
             "Update check: " + ("off" if not update.get("enabled") else f"on, latest {update.get('latest') or 'unknown'}"),
             "Files:"]
    lines += [f"  {name}: {home_free(path)}" for name, path in sorted((data.get("paths") or {}).items())]
    lines += ["Libraries: " + ", ".join(f"{c['name']}={'yes' if c['installed'] else 'no'}" for c in data.get("credits", [])), "Repository: " + data["links"]["repository"]]
    return "\n".join(lines) + "\n"


def console_text(data, translate):
    """The plain text of `--about`."""
    update = data.get("update") or {}
    rows = [translate("ui.about_title"), "=" * 40,
            f"{translate('ui.about_version')}: {data['version']}", f"{translate('ui.about_edition')}: {translate('ui.edition_' + data['edition'])}",
            f"{translate('ui.about_author')}: {data['author']}", f"{translate('ui.about_license')}: {data['license']}",
            f"{translate('ui.about_python')}: {data['python']}", f"{translate('ui.about_system')}: {data['system']}", ""]
    rows += [f"{translate('ui.about_' + key)}: {url}" for key, url in data["links"].items() if key != "license"]
    rows += ["", translate("ui.about_credits") + ":"] + [f"  {c['name']} ({c['license']}) - {translate('ui.credit_' + c['id'])}" + ("" if c["installed"] else " [-]") for c in data["credits"]]
    line = updatecheck.notice(update, translate)
    if line:
        rows += ["", line]
    elif not update.get("enabled"):
        rows += ["", translate("ui.update_off")]
    return "\n".join(rows) + "\n"


def lone(translate=None, lite=False):
    """About for a process that does not run the server (console views, --about): no health, no paths, the update state of the last check."""
    state = updatecheck._load(updatecheck.STATE_FILE)
    from github_actions_monitor.app import toolconfig
    update = updatecheck.view(toolconfig.raw_config(), TOOL_VERSION, state)
    return info(lite, {}, {}, update, "")
