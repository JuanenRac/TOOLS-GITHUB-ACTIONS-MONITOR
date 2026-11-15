# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two secrets that reach the monitor through its environment (the key the supervisor gives to the process of each account, and the access token of the network mode) are read ONCE when the
process starts and taken out of `os.environ`. Every program the monitor starts afterwards (`gh`, `git`, `openssl`, the command of a notice) inherits an environment without them, and on Linux
`/proc/<pid>/environ` of this process no longer shows them. The values live in this module only; the supervisor hands them to the process of an account explicitly (`for_account_process`).
"""
import os

SUPERVISOR_KEY_ENV = "MONITOR_SUPERVISOR_KEY"
ACCESS_TOKEN_ENV = "MONITOR_ACCESS_TOKEN"
HELD = {}            # name -> value, taken out of the environment
NAMES = {SUPERVISOR_KEY_ENV, ACCESS_TOKEN_ENV}      # the names that never go to a program of the user (the variable that holds the access token can be renamed: see hold)


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


def for_account_process(extra=None):
    """The environment of the process of an account: the real one plus what was taken out (it needs both) plus `extra`."""
    return {**os.environ, **HELD, **(extra or {})}
