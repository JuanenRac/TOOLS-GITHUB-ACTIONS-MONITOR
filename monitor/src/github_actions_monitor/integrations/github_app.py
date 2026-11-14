# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""An optional GitHub App for the READS of the monitor: its own allowance, separate from the one of the user (an App installed on many repositories gets a bigger one). Standard library and the `openssl` program.

  github_app.enabled          false (default)
  github_app.app_id           the number of the App
  github_app.key_path         ONLY the path of its private key (a .pem kept outside any repository)
  github_app.installation_id  optional: found by itself with GET /app/installations

How it works: a JWT (RS256, valid at most 10 minutes) is signed by `openssl dgst -sha256 -sign <path>`: the path is handed to openssl, the monitor never reads, copies, prints or logs the key. The JWT asks for an
installation token (valid one hour) that is kept in memory and renewed five minutes before it expires; `gh` gets it as GH_TOKEN for READS only. Writes and actions keep using the token of the user. If the App fails,
or lacks a permission, the read is made again with the user's token. Create the App with read-only permissions: Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues,
Pull requests, Secret scanning alerts and Metadata.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
DEFAULTS = {"enabled": False, "app_id": "", "key_path": "", "installation_id": "", "openssl_path": ""}
OPENSSL = {"configured": ""}      # the program chosen in the configuration (settings() keeps it here so that the signature finds it)
PERMISSIONS = ("actions", "checks", "security_events", "statuses", "contents", "vulnerability_alerts", "issues", "pull_requests", "secret_scanning_alerts", "metadata")
_STATE = {"token": "", "expires": 0.0, "installation": "", "error": "", "failed_at": 0.0}
RETRY_AFTER = 300      # seconds before a failed App is tried again (the reads use the token of the user meanwhile)


def settings(config):
    block = (config or {}).get("github_app") if isinstance((config or {}).get("github_app"), dict) else {}
    key = block.get("key_path") if isinstance(block.get("key_path"), str) else ""
    ok_path = bool(key) and len(key) <= 260 and not any(ord(c) < 32 for c in key) and not key.startswith(("\\\\", "//")) and not re.match(r"^(?:[Dd]:|/mnt/[dD](?:/|$))", key)
    ident = lambda value: str(value) if str(value).isdigit() and 0 < len(str(value)) <= 12 else ""      # noqa: E731
    program = block.get("openssl_path") if isinstance(block.get("openssl_path"), str) else ""
    program = program if program and len(program) <= 260 and not any(ord(c) < 32 for c in program) and re.split(r"[\\/]", program)[-1].lower() in ("openssl", "openssl.exe") else ""
    OPENSSL["configured"] = program
    return {"enabled": block.get("enabled") is True, "app_id": ident(block.get("app_id", "")), "key_path": key if ok_path else "", "installation_id": ident(block.get("installation_id", "")), "openssl_path": program}


def known_openssl(env=None, exists=None):
    """Places where an openssl lives that is NOT in the PATH of an ordinary console: the one that comes with Git for Windows (a launcher from a .bat or a service does not see it) and the usual ones of macOS and Linux."""
    env = os.environ if env is None else env
    exists = exists or os.path.isfile
    roots = [env.get(name, "") for name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
    if env.get("LOCALAPPDATA"):
        roots.append(os.path.join(env["LOCALAPPDATA"], "Programs"))
    found = []
    for root in roots:
        if root:
            for parts in (("Git", "usr", "bin", "openssl.exe"), ("Git", "mingw64", "bin", "openssl.exe")):
                found.append(os.path.join(root, *parts))
    found += ["/opt/homebrew/bin/openssl", "/usr/local/bin/openssl", "/usr/bin/openssl"]
    return [path for path in found if exists(path)]


def find_openssl(exists=None, env=None):
    """The program to sign with: the one named in `github_app.openssl_path`, else the one of the PATH, else one of Git for Windows or of the usual places. "" when there is none."""
    exists = exists or os.path.isfile
    if OPENSSL["configured"] and exists(OPENSSL["configured"]):
        return OPENSSL["configured"]
    on_path = shutil.which("openssl")
    if on_path:
        return on_path
    known = known_openssl(env, exists)
    return known[0] if known else ""


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _sign(data, key_path):
    program = find_openssl() or "openssl"
    done = subprocess.run([program, "dgst", "-sha256", "-sign", key_path], input=data, capture_output=True, timeout=20, shell=False)
    if done.returncode != 0 or not done.stdout:
        raise RuntimeError("openssl could not sign (check the key file)")
    return done.stdout


def make_jwt(app_id, key_path, now=None, signer=None):
    """The JWT of the App: RS256, issued a minute in the past (clock drift) and valid nine more: never more than the ten minutes GitHub allows."""
    now = int(time.time() if now is None else now)
    header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"iat": now - 60, "exp": now + 540, "iss": str(app_id)}, separators=(",", ":")).encode())
    signing = header + b"." + payload
    return (signing + b"." + _b64((signer or _sign)(signing, key_path))).decode()


def _call(method, path, bearer, body=None, opener=None):
    request = urllib.request.Request(API + path, method=method, data=body, headers={"Authorization": "Bearer " + bearer, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "github-actions-monitor"})
    if opener is not None:
        return opener(request)
    from github_actions_monitor.security import netguard
    with netguard.open_url(request, timeout=20) as answer:
        return json.loads(answer.read(2_000_000).decode("utf-8") or "{}"), dict(answer.headers)


def _expires(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def token(config, opener=None, signer=None, now=None, force=False):
    """The installation token to read with, or "" (off, no key, App not installed, a recent failure): the caller then uses the token of the user. Nothing here ever prints the key or the token."""
    cfg = settings(config)
    now = time.time() if now is None else now
    if not (cfg["enabled"] and cfg["app_id"] and cfg["key_path"]):
        return ""
    if not force and _STATE["token"] and _STATE["expires"] - 300 > now:
        return _STATE["token"]
    if not force and _STATE["failed_at"] and now - _STATE["failed_at"] < RETRY_AFTER:
        return ""
    try:
        jwt = make_jwt(cfg["app_id"], cfg["key_path"], now, signer)
        install = cfg["installation_id"] or _STATE["installation"]
        if not install:
            data, _ = _call("GET", "/app/installations", jwt, opener=opener)
            if not data:
                raise RuntimeError("the App is not installed on any account")
            install = str(data[0]["id"])
            _STATE["installation"] = install
        data, _ = _call("POST", f"/app/installations/{install}/access_tokens", jwt, b"{}", opener=opener)
        _STATE.update({"token": data["token"], "expires": _expires(data["expires_at"]), "error": "", "failed_at": 0.0})
        return _STATE["token"]
    except Exception as error:   # noqa: BLE001 - a broken App is "use the user token", said once in the status
        _STATE.update({"token": "", "expires": 0.0, "error": clean(str(error))[:160], "failed_at": now})
        return ""


def clean(text):
    """Never a token or a key in a message."""
    return re.sub(r"(gh[opsu]_[A-Za-z0-9]{20,}|-----BEGIN[^-]*-----|Bearer\s+\S+|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_.-]+)", "[removed]", text)


def should_retry_with_user(error_text):
    """An App without the permission (or a revoked token) answers like this: the same read is made again with the token of the user."""
    return bool(re.search(r"not accessible by integration|bad credentials|installation .*(suspended|not found)|401", str(error_text), re.I))


#: the only options of `gh api` that a read may carry: the filter, the pages, a header of the kind a read sends, the status line and the cache. Everything else that starts with `-` (a method, a field,
#: a body, in any spelling: `-XPOST`, `--method=DELETE`, `-fa=b`, `--input=-`) makes the call one that is never spread over the other sources
READ_FLAGS = {"--jq": True, "-q": True, "--paginate": False, "-H": True, "--header": True, "-i": False, "--include": False, "--cache": True}
READ_HEADERS = ("accept", "if-none-match", "if-modified-since", "x-github-api-version")
#: what depends on WHO asks: the endpoints of the signed-in account. They are answered by the login of the user, never by the App or by a second account
IDENTITY_RE = re.compile(r"^(?:user|users/@me|notifications|applications|installation|app)(?:[/?]|$)|@me\b", re.I)


def identity_read(args):
    """True when the answer depends on who asks (the account itself, its organisations, its notifications, a search for `@me`, `gh auth`, `gh repo list` without an owner)."""
    args = [str(a) for a in args]
    if not args:
        return False
    if args[0] == "auth":
        return True
    if args[0] == "repo" and len(args) > 1 and args[1] == "list":
        return len(args) < 3 or args[2].startswith("-")
    if args[0] == "api":
        endpoint = next((a for a in args[1:] if not a.startswith("-") and a not in ("api",)), "")
        return bool(IDENTITY_RE.search(endpoint.lstrip("/")))
    return False


def is_read(args):
    """True for a `gh` call that only reads and does not depend on who asks. A WHITE list: `gh api ENDPOINT` with only the options of READ_FLAGS (and a header of the kind a read sends), or
    a verb that only reads (`gh run list`, `gh release view`...). When in doubt it is not a read, and then the user's login makes the call."""
    args = [str(a) for a in args]
    if not args or identity_read(args):
        return False
    if args[0] == "api":
        endpoints, i = 0, 1
        while i < len(args):
            a = args[i]
            if a.startswith("-"):
                if a not in READ_FLAGS:
                    return False
                if READ_FLAGS[a]:
                    if i + 1 >= len(args):
                        return False
                    if a in ("-H", "--header") and args[i + 1].split(":", 1)[0].strip().lower() not in READ_HEADERS:
                        return False
                    i += 1
            else:
                endpoints += 1
            i += 1
        return endpoints == 1
    return len(args) > 1 and args[1] in ("list", "view", "status", "diff", "checks", "download")      # gh run list, gh release view...: a verb that only reads


def key_warning(key_path):
    """"" or a warning: on a system with file modes the key must not be readable by others. (On Windows the modes cannot be judged: the folder permissions are yours.)"""
    try:
        if os.name == "posix":
            mode = os.stat(key_path).st_mode & 0o777
            if mode & 0o077:
                return "the key file can be read by other users (chmod 600)"
        return "" if os.path.isfile(key_path) else "the key file is not there"
    except OSError:
        return "the key file cannot be read"


def status(config, opener=None, signer=None, now=None):
    """What the settings page shows (never the key or the token): {"enabled", "ok", "installation_id", "expires_epoch", "rate", "permissions", "app", "error", "warning", "openssl"}."""
    cfg = settings(config)
    out = {"enabled": cfg["enabled"], "ok": False, "openssl": bool(find_openssl()), "openssl_path": find_openssl(), "warning": key_warning(cfg["key_path"]) if cfg["key_path"] else "", "error": ""}
    if not cfg["enabled"]:
        return out
    got = token(config, opener, signer, now, force=True)
    if not got:
        out["error"] = _STATE["error"] or "the App could not give a token"
        return out
    try:
        jwt = make_jwt(cfg["app_id"], cfg["key_path"], now, signer)
        app, _ = _call("GET", "/app", jwt, opener=opener)
        install = cfg["installation_id"] or _STATE["installation"]
        info, _ = _call("GET", f"/app/installations/{install}", jwt, opener=opener) if install else ({}, {})
        rate, _ = _call("GET", "/rate_limit", got, opener=opener)
        core = (rate.get("resources") or {}).get("core") or {}
        granted = info.get("permissions") or {}
        out.update({"ok": True, "app": str(app.get("name") or "")[:80], "installation_id": install, "expires_epoch": int(_STATE["expires"]),
                    "rate": {"remaining": core.get("remaining"), "limit": core.get("limit"), "reset": core.get("reset")},
                    "permissions": {p: granted.get(p, "missing") for p in PERMISSIONS}})
    except Exception as error:   # noqa: BLE001
        out["error"] = clean(str(error))[:160]
    return out


def reset():
    _STATE.update({"token": "", "expires": 0.0, "installation": "", "error": "", "failed_at": 0.0})
