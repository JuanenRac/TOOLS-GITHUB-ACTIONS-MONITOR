# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two secrets that reach the monitor through its environment (the key the supervisor gives to the process of each account, and the access token of the network mode) are read ONCE when the
process starts and taken out of `os.environ`, in every process (the monitor, the supervisor and the process of each account) and before the first program is started. Every program the monitor starts
afterwards (`gh`, `git`, `openssl`, the command of a notice) inherits an environment without them. The values live in this module only; the supervisor hands them to the process of an account
explicitly (`for_account_process`). Limit: on Linux `/proc/<pid>/environ` keeps showing the environment the process was STARTED with, to the same user, whatever is removed afterwards.
"""
import os

SUPERVISOR_KEY_ENV = "MONITOR_SUPERVISOR_KEY"
ACCESS_TOKEN_ENV = "MONITOR_ACCESS_TOKEN"
WEBHOOK_SECRET_ENV = "MONITOR_WEBHOOK_SECRET"
#: names of environment variables that can NEVER be named as the home of a secret of the monitor (the setting would turn the secret into a value that is not secret, or take a variable the programs need out of the environment)
SYSTEM_NAMES = ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_PAT", "PATH", "PATHEXT", "COMSPEC", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP", "APPDATA", "LOCALAPPDATA", "PYTHONPATH", "SSH_AUTH_SOCK")
SECRET_NAMES = (SUPERVISOR_KEY_ENV, ACCESS_TOKEN_ENV, WEBHOOK_SECRET_ENV)      # the secrets the monitor itself defines: each setting may name only its own
#: every setting that NAMES an environment variable with a secret (key of the setting -> the variable that belongs to it by default, '' = none). A name can be written in one setting only, and none of
#: them may name a variable of the system or a secret that belongs to another setting.
ENV_SETTINGS = {"webhook.secret_env": WEBHOOK_SECRET_ENV, "listen.token_env": ACCESS_TOKEN_ENV, "ai.api_key_env": "", "notify.channels.telegram.token_env": "", "notify.channels.discord.url_env": "",
                "notify.channels.slack.url_env": "", "notify.channels.apprise.urls_env": "", "notify.channels.matrix.token_env": ""}
HELD = {}            # name -> value, taken out of the environment
NAMES = {SUPERVISOR_KEY_ENV, ACCESS_TOKEN_ENV}      # the names that never go to a program of the user (the variable that holds the access token can be renamed: see hold)


def forbidden_name(name, own=()):
    """True when `name` cannot be the variable of a secret: a variable of the system or of the login to GitHub, or a secret of the monitor that belongs to another setting (`own` = the one of this setting)."""
    return name in SYSTEM_NAMES or (name in SECRET_NAMES and name not in own)


class NamePattern:
    """Like a compiled pattern for `.match(name)`: a plain variable name that is not forbidden (see forbidden_name). For the places that read the variable a setting names."""

    def __init__(self, own=()):
        import re
        self.own, self.plain = tuple(own), re.compile(r"^[A-Z_][A-Z0-9_]{0,63}\Z")

    def match(self, name):
        return self.plain.match(name) if isinstance(name, str) and not forbidden_name(name, self.own) else None


def shared_names(config):
    """The names written in more than one of the ENV_SETTINGS of this configuration: [(name, [keys])]. A name used twice would make two features read (and one of them hold) the same secret."""
    seen = {}
    for key in ENV_SETTINGS:
        node = config
        for part in key.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        name = node if isinstance(node, str) and node else ENV_SETTINGS[key]
        if name:
            seen.setdefault(name, []).append(key)
    return [(name, keys) for name, keys in sorted(seen.items()) if len(keys) > 1]


def hold(*names):
    """Takes these variables (and the two fixed ones) out of the environment of this process, keeping their values here."""
    NAMES.update(n for n in names if isinstance(n, str) and n)
    for name in NAMES:
        value = os.environ.pop(name, None)
        if value:
            HELD[name] = value


def get(name, default=""):
    """The value of a held variable: what is in the environment now (a test or a parent that set it) else the one taken out of it at start."""
    return os.environ.get(name) or HELD.get(name, default)


def clean_environment(env=None):
    """A copy of the environment for a program the monitor starts, without the supervisor key and the access token."""
    out = dict(os.environ if env is None else env)
    for name in NAMES:
        out.pop(name, None)
    return out


def for_account_process(extra=None, other_secrets=()):
    """The environment of the process of an account: the real one plus what was taken out (it needs both) plus `extra`, WITHOUT the variables in `other_secrets` (the secrets of the webhook of the
    other accounts and of the main configuration: the process of an account, and every program it starts, only holds the secret its own configuration names)."""
    env = {**os.environ, **HELD, **(extra or {})}
    for name in other_secrets:
        env.pop(name, None)
    return env
