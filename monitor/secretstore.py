# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""An OPTIONAL token of GitHub kept by the monitor itself (`github_token.enabled`, OFF by default). The default way stays the one of every release so far: your own `gh login`, or an
environment variable named in a setting.

Where the token is kept, in this order (the setting `github_token.store` can force `system` or `file`):
  * Windows: DPAPI (the blob only this Windows account can open) in a file of the user folder;
  * macOS: the Keychain, through the `security` command;
  * Linux: the Secret Service (GNOME Keyring / KWallet), through `secret-tool`, which reads the secret from its standard input;
  * anywhere else, or when the tools above are missing: a file with permissions 600 (owner only) in a folder with permissions 700 - the weakest option, and the panel says so.
The token is NEVER written to actions_monitor.json, a log, the About panel, the text for support, the metrics or any answer of the server: the page can only learn whether one is stored and where.
It is handed to `gh` through the environment variable GH_TOKEN of the `gh` process ONLY (gh_kwargs(); never set in the environment of this process, so no other child inherits it), and `redact()` removes it from any text before it is shown.
"""
import base64
import ctypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SERVICE = "github-actions-monitor"
ACCOUNT = "github-token"
TOKEN_RE = re.compile(r"^(gh[pousr]_[A-Za-z0-9]{20,255}|github_pat_[A-Za-z0-9_]{20,255}|[0-9a-f]{40})$")
STORES = ("auto", "system", "file")


def folder():
    base = os.environ.get("MONITOR_SECRET_DIR")
    return Path(base) if base else Path.home() / ".config" / "github-actions-monitor"


APPLIED = {"token": ""}     # the token this process put in GH_TOKEN (a GH_TOKEN the user set himself is never removed)


def settings(config):
    cfg = config.get("github_token") if isinstance(config, dict) and isinstance(config.get("github_token"), dict) else {}
    return {"enabled": cfg.get("enabled") is True, "store": cfg.get("store") if cfg.get("store") in STORES else "auto"}


def valid(token):
    return isinstance(token, str) and bool(TOKEN_RE.match(token.strip()))


def redact(text, token=None):
    """The text without the stored token and without anything that looks like a GitHub token."""
    out = str(text)
    if token:
        out = out.replace(token, "***")
    out = re.sub(r"(gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,})", "***", out)
    return re.sub(r"(?<![0-9A-Fa-f])[0-9a-f]{40}(?![0-9A-Fa-f])", "***", out)      # the old 40-hex tokens (TOKEN_RE accepts them)


def _run(args, data=None, runner=None):
    runner = runner or (lambda a, d: subprocess.run(a, input=d, capture_output=True, text=True, encoding="utf-8", timeout=15))
    try:
        done = runner(args, data)
        return done.returncode, done.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return 127, ""


# --- Windows: DPAPI through ctypes (no package, no command line argument carries the token) ---------------------------------------------------------------------------------------------------
class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data, protect):
    if sys.platform != "win32":
        raise OSError("DPAPI is Windows only")
    crypt = ctypes.windll.crypt32
    source = _Blob(len(data), ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_char)))
    out = _Blob()
    call = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    if not call(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(out)):
        raise OSError("DPAPI failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _private_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


class Store:
    """The place of the token. `runner(args, stdin) -> CompletedProcess-like` is replaceable so the tests need no keychain."""

    def __init__(self, store="auto", runner=None, platform=None):
        self.store, self.runner, self.platform = store if store in STORES else "auto", runner, platform or sys.platform

    def backend(self):
        """'dpapi' | 'keychain' | 'secret-service' | 'file'."""
        if self.store == "file":
            return "file"
        if self.platform == "win32":
            return "dpapi"
        if self.platform == "darwin" and shutil.which("security"):
            return "keychain"
        if self.platform.startswith("linux") and shutil.which("secret-tool"):
            return "secret-service"
        return "file"

    def _file(self, name):
        return folder() / name

    def save(self, token):
        token = str(token).strip()
        if not valid(token):
            return False, "format"
        kind = self.backend()
        try:
            if kind == "dpapi":
                _private_file(self._file("token.dpapi"), base64.b64encode(_dpapi(token.encode(), True)))
            elif kind == "keychain":
                # `security -i` reads its commands from standard input: the token never sits in the argument list (visible to every user with `ps`). A token has only letters, digits and underscores.
                code, _out = _run(["security", "-i"], f'add-generic-password -U -s "{SERVICE}" -a "{ACCOUNT}" -w "{token}"\n', self.runner)
                if code:
                    return False, "keychain"
            elif kind == "secret-service":
                code, _out = _run(["secret-tool", "store", "--label", SERVICE, "service", SERVICE, "account", ACCOUNT], token, self.runner)
                if code:
                    return False, "secret-service"
            else:
                _private_file(self._file("token.600"), token.encode())
        except OSError:
            return False, "write"
        return True, kind

    def load(self):
        kind = self.backend()
        try:
            if kind == "dpapi":
                path = self._file("token.dpapi")
                return _dpapi(base64.b64decode(path.read_bytes()), False).decode() if path.is_file() else ""
            if kind == "keychain":
                code, out = _run(["security", "find-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w"], runner=self.runner)
                return out.strip() if code == 0 else ""
            if kind == "secret-service":
                code, out = _run(["secret-tool", "lookup", "service", SERVICE, "account", ACCOUNT], runner=self.runner)
                return out.strip() if code == 0 else ""
            path = self._file("token.600")
            return path.read_text(encoding="utf-8").strip() if path.is_file() else ""
        except (OSError, ValueError):
            return ""

    def delete(self):
        """Removes the token from every place it could be (a change of store never leaves a copy behind). Returns True when nothing is left."""
        for name in ("token.dpapi", "token.600"):
            try:
                self._file(name).unlink()
            except FileNotFoundError:
                pass
            except OSError:
                return False
        if self.platform == "darwin" and shutil.which("security"):
            _run(["security", "delete-generic-password", "-s", SERVICE, "-a", ACCOUNT], runner=self.runner)
        if self.platform.startswith("linux") and shutil.which("secret-tool"):
            _run(["secret-tool", "clear", "service", SERVICE, "account", ACCOUNT], runner=self.runner)
        return not self.load()

    def status(self):
        """What the page may know: {"backend", "stored", "weak"} - never the token, nor a part of it."""
        kind = self.backend()
        return {"backend": kind, "stored": bool(self.load()), "weak": kind == "file"}


def apply_to_environment(config, store=None):
    """Puts the stored token in GH_TOKEN of this process when the setting is on and one is stored. Returns True when it did. Never prints anything."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return False
    token = (store or Store(cfg["store"])).load()
    if not valid(token):
        return False
    APPLIED["token"] = token       # kept in this module only: it is NOT put in os.environ, so no child process inherits it by accident
    return True


def gh_kwargs():
    """Extra arguments for a subprocess call that runs `gh`: {"env": ...} with the stored token as GH_TOKEN when the monitor keeps one, else {} (gh then uses its own login). It is passed
    to `gh` calls ONLY - never to `act`, to a notification command or to any program of the user."""
    if not APPLIED["token"]:
        return {}
    env = dict(os.environ)
    env["GH_TOKEN"] = APPLIED["token"]
    return {"env": env}


def clear_environment():
    """After a delete or when the setting is turned off: the monitor stops using the stored token. (A GH_TOKEN the user set in his own environment is never touched.)"""
    APPLIED["token"] = ""
