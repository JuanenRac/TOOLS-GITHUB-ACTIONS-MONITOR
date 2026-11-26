# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The routes of the page for the plugins (declared in families/plugins). The server has already checked the session, the role, that the request comes from this computer and the one-use token."""
from github_actions_monitor.plugins import plugin_host as host
from github_actions_monitor.plugins import plugin_manifest as manifests
from github_actions_monitor.plugins import plugin_package as packages
from github_actions_monitor.security import audit_log


def _name(request):
    name = request.body.get("name")
    return name if isinstance(name, str) and manifests.NAME_RE.match(name) else ""


def _path(request):
    path = request.body.get("path")
    network = ("\\\\", "//")      # a share of another computer is never opened
    return path if isinstance(path, str) and 0 < len(path) <= 400 and path.endswith(".zip") and not path.startswith(network) else ""


def _refused(reason):
    return 400, {"ok": False, "reason": reason}


def catalogue(request):
    return host.catalogue(request.config)


def enable(request):
    name, enabled = _name(request), request.body.get("enabled")
    if not name or not isinstance(enabled, bool):
        return _refused("request")
    audit_log.note(f"{name} {'on' if enabled else 'off'}")
    if name in host.official():      # switched by its setting; here it can only be resumed after a pause
        if not enabled:
            return _refused("official")
        host.resume(name)
        return {"ok": True}
    try:
        packages.set_enabled(name, enabled)
    except packages.PackageError as error:
        return _refused(error.code)
    if enabled:
        host.resume(name)
    return {"ok": True}


def uninstall(request):
    name = _name(request)
    audit_log.note(name or "?")
    try:
        done = packages.uninstall(name)
    except packages.PackageError as error:
        return _refused(error.code)
    host.save_state(name, None)
    return dict(done, ok=done["removed"])


def inspect(request):
    path = _path(request)
    if not path:
        return _refused("request")
    try:
        return dict(packages.inspect(path, host.user_keys()), ok=True)
    except packages.PackageError as error:
        return _refused(error.code)
    except OSError:
        return _refused("absent")


def install(request):
    path = _path(request)
    if not path:
        return _refused("request")
    try:
        done = packages.install(path, host.user_keys(), request.body.get("fingerprint"))
    except packages.PackageError as error:
        audit_log.note("refused " + error.code)
        return _refused(error.code)
    except OSError:
        return _refused("absent")
    audit_log.note(f"{done['name']} {done['version']} {done['fingerprint'][:16]}")
    return {"ok": True, "name": done["name"], "enabled": done["enabled"]}
