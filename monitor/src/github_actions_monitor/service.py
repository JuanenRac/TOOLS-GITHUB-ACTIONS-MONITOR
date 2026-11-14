# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`python -m github_actions_monitor.service`: the complete monitor as a service (the container image, the systemd unit, any machine nobody sits at).

It does what a person does by hand before the first start, from the environment, and then starts the monitor without a browser:

  * `MONITOR_SERVICE=1` is set (the doctor and the retention rules treat the monitor as a service);
  * the configuration file named by `MONITOR_CONFIG` is created on the first start (never overwritten later: what you edited stays) and the `listen` and `auth` keys the environment names are
    written into it at every start, so the environment of the container stays the authority for them (see `LISTEN_ENV`);
  * the folder of the accounts (`MONITOR_ACCOUNTS_DIR`) gets its first account from `MONITOR_ACCOUNT` / `MONITOR_GITHUB_OWNER` (or several from `MONITOR_ACCOUNTS`) when it has none;
  * in the network mode the access token comes from `MONITOR_ACCESS_TOKEN`, or from the file named by `MONITOR_ACCESS_TOKEN_FILE`, or from a file it keeps in `MONITOR_STATE_DIR` (made once, mode
    600, never printed) so that every start of the same volume asks for the same token and the health check can read it;
  * the credential of GitHub is NOT touched here: `GH_TOKEN`, the file named by `GH_TOKEN_FILE` or the login of `gh` are read by each account (see security/credential.py).

Nothing here widens what the monitor does: the defaults are the ones of a monitor on its own (only this computer); the image turns the network mode on through the environment, on purpose.
"""
import json
import os
import secrets
import sys
from pathlib import Path

from github_actions_monitor import i18n
from github_actions_monitor.accounts import accounts
from github_actions_monitor.security import private_io
from github_actions_monitor.util import paths

#: environment variable -> (section, key, kind) of the configuration. A variable that is not set changes nothing; one that is set but empty or badly written is ignored with a notice.
LISTEN_ENV = {
    "MONITOR_LISTEN_NETWORK": ("listen", "network", "bool"),
    "MONITOR_LISTEN_HOST": ("listen", "host", "text"),
    "MONITOR_ALLOWED_HOSTS": ("listen", "allowed_hosts", "list"),
    "MONITOR_PROXY_PUBLIC_HOST": ("listen", "proxy_public_host", "text"),
    "MONITOR_SECURE_COOKIE": ("listen", "secure_cookie", "bool"),
    "MONITOR_TRUSTED_PROXY": ("listen", "trusted_proxy", "bool"),
    "MONITOR_LOCAL_PORT": ("listen", "local_port", "int"),
    "MONITOR_TLS_CERT_FILE": ("listen", "tls_cert_file", "text"),
    "MONITOR_TLS_KEY_FILE": ("listen", "tls_key_file", "text"),
    "MONITOR_QUERY_ACCESS": ("listen", "query_access", "bool"),
    "MONITOR_TEAM_MODE": ("auth", "enabled", "bool"),
}
TOKEN_FILE_NAME = "access_token"
DEFAULT_PORT = 8765
DEFAULT_ACCOUNT = "default"


def _convert(value, kind):
    text = str(value).strip()
    if kind == "bool":
        if text.lower() in ("1", "true", "yes", "on"):
            return True
        if text.lower() in ("0", "false", "no", "off"):
            return False
        raise ValueError(text)
    if kind == "int":
        return int(text)
    if kind == "list":
        return [part.strip() for part in text.split(",") if part.strip()]
    if not text:
        raise ValueError("empty")
    return text


def environment_changes(env=None):
    """({"listen": {...}, "auth": {...}}, [names of the variables that could not be read]) from the environment."""
    env = os.environ if env is None else env
    out, bad = {}, []
    for name, (section, key, kind) in LISTEN_ENV.items():
        if name not in env or str(env[name]).strip() == "":
            continue
        try:
            out.setdefault(section, {})[key] = _convert(env[name], kind)
        except ValueError:
            bad.append(name)
    return out, bad


def first_config(env=None):
    """The configuration written on the first start: a monitor that is left alone (no browser, retention on, the language of the environment)."""
    env = os.environ if env is None else env
    return {"_note": "Written by the service on its first start; edit it freely, it is never overwritten (only the listen and auth keys named by MONITOR_* variables are kept up to date).",
            "language": (env.get("MONITOR_LANG") or "").strip(), "open_browser": False, "retention": {"enabled": True, "mode": "archive"}}


def read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def prepare_config(env=None):
    """Creates the configuration on the first start and keeps the keys of the environment in it. Returns (path, created, changed, bad_variables); the path is None without `MONITOR_CONFIG`."""
    env = os.environ if env is None else env
    chosen = (env.get("MONITOR_CONFIG") or "").strip()
    if not chosen:
        return None, False, False, []
    path = Path(chosen)
    current = read_json(path)
    created = current is None
    if created and path.exists() and path.stat().st_size:
        raise ValueError("config")      # a file that is not a JSON object is the owner's to fix: it is never replaced
    config = first_config(env) if created else current
    changes, bad = environment_changes(env)
    changed = created
    for section, values in changes.items():
        block = config.get(section) if isinstance(config.get(section), dict) else {}
        merged = {**block, **values}
        if merged != block:
            config[section], changed = merged, True
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        private_io.write_private(path, json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    return path, created, changed, bad


def parse_accounts(env=None):
    """[(id, owner)] to create when the folder of the accounts is empty: `MONITOR_ACCOUNTS="personal:me,work:my-org"`, else `MONITOR_ACCOUNT` (default "default") with `MONITOR_GITHUB_OWNER`."""
    env = os.environ if env is None else env
    listed = (env.get("MONITOR_ACCOUNTS") or "").strip()
    out = []
    if listed:
        for part in listed.split(","):
            account_id, _, owner = part.strip().partition(":")
            if accounts.valid_id(account_id.strip().lower()):
                out.append((account_id.strip().lower(), owner.strip()))
        return out
    account_id = (env.get("MONITOR_ACCOUNT") or DEFAULT_ACCOUNT).strip().lower()
    return [(account_id if accounts.valid_id(account_id) else DEFAULT_ACCOUNT, (env.get("MONITOR_GITHUB_OWNER") or "").strip())]


def prepare_accounts(env=None):
    """Creates the first account(s) when the folder of the accounts holds none. Returns the ids created."""
    if accounts.list_accounts():
        return []
    made = []
    for account_id, owner in parse_accounts(env):
        try:
            path = accounts.create_account(account_id, owner)
        except FileExistsError:
            continue
        data = read_json(path) or {}
        data.setdefault("retention", {"enabled": True, "mode": "archive"})
        data["open_browser"] = False
        private_io.write_private(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        made.append(account_id)
    return made


def state_dir(env=None):
    env = os.environ if env is None else env
    chosen = (env.get("MONITOR_STATE_DIR") or "").strip()
    return Path(chosen) if chosen else paths.ROOT


def token_file(env=None):
    return state_dir(env) / TOKEN_FILE_NAME


def ensure_access_token(config, env=None):
    """In the network mode, makes sure the access token is in the environment of this process (so every account process inherits it). Returns "env" | "file" | "created" | "" (no network mode).
    The token is never returned nor printed."""
    env = os.environ if env is None else env
    from github_actions_monitor.security import localguard
    listen = localguard.settings_from(config)
    if not listen["network"]:
        return ""
    name = listen["token_env"]
    if len((env.get(name) or "").strip()) >= 16:
        return "env"
    named = (env.get(name + "_FILE") or "").strip()
    if named:
        try:
            with open(named, "r", encoding="utf-8-sig") as handle:
                value = handle.readline().strip()
        except (OSError, UnicodeError):
            value = ""
        if len(value) >= 16:
            env[name] = value
            return "file"
    path = token_file(env)
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        value = ""
    if len(value) >= 16:
        env[name] = value
        return "file"
    value = secrets.token_urlsafe(24)
    path.parent.mkdir(parents=True, exist_ok=True)
    private_io.write_private(path, value + "\n")
    env[name] = value
    return "created"


def prepare(env=None, out=print):
    """Everything the first start needs. Returns the exit code of a problem the owner must fix (78: configuration), or 0."""
    env = os.environ if env is None else env
    env["MONITOR_SERVICE"] = "1"
    try:
        path, created, changed, bad = prepare_config(env)
    except (OSError, ValueError):
        out(i18n.t("service.config_unusable", file=env.get("MONITOR_CONFIG", "")))
        return 78
    for name in bad:
        out(i18n.t("service.variable_ignored", name=name))
    if created:
        out(i18n.t("service.config_created", file=path))
    elif changed:
        out(i18n.t("service.config_updated", file=path))
    config = read_json(path) if path else None
    if config is None:
        from github_actions_monitor.app import toolconfig
        config = toolconfig.raw_config()
    for account_id in prepare_accounts(env):
        out(i18n.t("service.account_created", id=account_id))
    how = ensure_access_token(config, env)
    if how == "created":
        out(i18n.t("service.token_created", file=token_file(env)))
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    i18n.set_language(i18n.detect(os.environ.get("MONITOR_LANG")))
    code = prepare()
    if code:
        return code
    if "--prepare-only" in args:
        return 0
    from github_actions_monitor.app import actions_monitor
    port = os.environ.get("MONITOR_PORT", "").strip()
    sys.argv = [sys.argv[0], "--no-browser", "--port", port if port.isdigit() else str(DEFAULT_PORT), *[a for a in args if a != "--prepare-only"]]
    return actions_monitor.main()


if __name__ == "__main__":
    sys.exit(main())
