# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Secrets of the notification channels (the web address of a Teams channel, the access token of a ntfy topic), kept where secretstore.py keeps the token of GitHub.

A secret goes in by name (`user.<name>.teams`) and comes out only to the code that sends the message: no answer of the server, no log, no page, no export and no configuration file ever carries
it (the page can only learn whether one is stored). Where it is kept: DPAPI on Windows, the Keychain on macOS, the Secret Service on Linux, and a file with permissions 600 in a folder with
permissions 700 where none of those exists (the weakest place, said so by `status()`).
"""
import base64
import os
import re
import shutil
import sys

from github_actions_monitor.security import secretstore

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}\Z")
MAX_LENGTH = 2000
SERVICE = "github-actions-monitor-notify"


def _account(name):
    return "notify-" + name


def _file(name, suffix):
    return secretstore.folder() / f"notify-{name}.{suffix}"


def backend(platform=None):
    """Where the secrets go. MONITOR_SECRET_BACKEND=file forces the file with permissions 600 (a computer without a keyring, a container)."""
    if os.environ.get("MONITOR_SECRET_BACKEND") == "file":
        return "file"
    platform = platform or sys.platform
    if platform == "win32":
        return "dpapi"
    if platform == "darwin" and shutil.which("security"):
        return "keychain"
    if platform.startswith("linux") and shutil.which("secret-tool"):
        return "secret-service"
    return "file"


def valid_name(name):
    return isinstance(name, str) and bool(NAME_RE.match(name))


def valid_value(value):
    return isinstance(value, str) and 1 <= len(value.strip()) <= MAX_LENGTH and not re.search(r"[\x00-\x1f\x7f]", value.strip())


def put(name, value, runner=None, platform=None):
    """(True, backend) or (False, reason). The value is never in a command line: DPAPI and the file take it as bytes, the Keychain and the Secret Service read it from standard input."""
    if not valid_name(name):
        return False, "name"
    if not valid_value(value):
        return False, "format"
    value, kind = value.strip(), backend(platform)
    try:
        if kind == "dpapi":
            secretstore._private_file(_file(name, "dpapi"), base64.b64encode(secretstore._dpapi(value.encode("utf-8"), True)))
        elif kind == "keychain":
            safe = value.replace("\\", "\\\\").replace('"', '\\"')
            code, _out = secretstore._run(["security", "-i"], f'add-generic-password -U -s "{SERVICE}" -a "{_account(name)}" -w "{safe}"\n', runner)
            if code:
                return False, "keychain"
        elif kind == "secret-service":
            code, _out = secretstore._run(["secret-tool", "store", "--label", SERVICE, "service", SERVICE, "account", _account(name)], value, runner)
            if code:
                return False, "secret-service"
        else:
            secretstore._private_file(_file(name, "600"), value.encode("utf-8"))
    except OSError:
        return False, "write"
    return True, kind


def get(name, runner=None, platform=None):
    """The secret, or "" when there is none (or it cannot be read). Only the code that sends the message may call this."""
    if not valid_name(name):
        return ""
    kind = backend(platform)
    try:
        if kind == "dpapi":
            path = _file(name, "dpapi")
            return secretstore._dpapi(base64.b64decode(path.read_bytes()), False).decode("utf-8") if path.is_file() else ""
        if kind == "keychain":
            code, out = secretstore._run(["security", "find-generic-password", "-s", SERVICE, "-a", _account(name), "-w"], runner=runner)
            return out.strip() if code == 0 else ""
        if kind == "secret-service":
            code, out = secretstore._run(["secret-tool", "lookup", "service", SERVICE, "account", _account(name)], runner=runner)
            return out.strip() if code == 0 else ""
        path = _file(name, "600")
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    except (OSError, ValueError):
        return ""


def has(name, runner=None, platform=None):
    return bool(get(name, runner, platform))


def delete(name, runner=None, platform=None):
    """Removes the secret from every place it could be. True when nothing is left."""
    if not valid_name(name):
        return False
    for suffix in ("dpapi", "600"):
        try:
            _file(name, suffix).unlink()
        except FileNotFoundError:
            pass
        except OSError:
            return False
    kind = backend(platform)
    if kind == "keychain":
        secretstore._run(["security", "delete-generic-password", "-s", SERVICE, "-a", _account(name)], runner=runner)
    if kind == "secret-service":
        secretstore._run(["secret-tool", "clear", "service", SERVICE, "account", _account(name)], runner=runner)
    return not get(name, runner, platform)


def status(platform=None):
    kind = backend(platform)
    return {"backend": kind, "weak": kind == "file"}
