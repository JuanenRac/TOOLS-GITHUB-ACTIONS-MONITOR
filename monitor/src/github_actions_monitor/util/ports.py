# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The ports of the two editions: the COMPLETE one (8765 by default) and the LITE one (8766 by default), both settable in the configuration file (`ports.complete`, `ports.lite`) and in the Settings page.

One place says which port an edition uses, so that the start, the check "there is already a monitor on this port", the doctor, the health check, the command line, the terminal views, the launchers
and the service all agree. The order is always the same: the number given on the command line (`--port`) wins; then, for the complete edition, `MONITOR_PORT` (a service or a container sets it);
then the configuration file of the edition itself; then the configuration file of the other edition (so one menu can set both); then the default. A number that is not a whole port from 1024 to
65535 is ignored, and the lite edition never takes the port of the complete one: when both name the same number the lite one keeps its default.
"""
import json
import os
from pathlib import Path

DEFAULTS = {"complete": 8765, "lite": 8766}
EDITIONS = tuple(DEFAULTS)
LOW, HIGH = 1024, 65535


def valid(value):
    """True for a whole number from 1024 to 65535 (not a bool, not a text)."""
    return isinstance(value, int) and not isinstance(value, bool) and LOW <= value <= HIGH


def of_config(config, edition):
    """The port the `ports` section of a configuration says for an edition, or None."""
    section = config.get("ports") if isinstance(config, dict) else None
    value = section.get(edition) if isinstance(section, dict) else None
    return value if valid(value) else None


def files():
    """{edition: path of its configuration file}."""
    from github_actions_monitor.util import paths
    return {"complete": paths.config_file(), "lite": paths.place("actions_monitor_lite.json")}


def read_file(path):
    """The content of a configuration file as a dict ({} when it is missing or damaged)."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _pick(edition, configs):
    own = of_config(configs.get(edition), edition)
    if own is not None:
        return own
    other = of_config(configs.get("lite" if edition == "complete" else "complete"), edition)
    return other if other is not None else DEFAULTS[edition]


def resolve(edition, flag=None, env=None, configs=None):
    """The port of an edition ("complete" or "lite"). `flag` is a `--port` given on the command line; `env` the environment (os.environ by default); `configs` {edition: dict} instead of reading the files
    (the tests give it). Never raises."""
    if edition not in DEFAULTS:
        raise ValueError(edition)
    if isinstance(flag, int) and not isinstance(flag, bool) and 0 <= flag <= HIGH:      # what a person types is not second-guessed
        return flag
    env = os.environ if env is None else env
    text = str(env.get("MONITOR_PORT", "")).strip() if edition == "complete" else ""
    if text.isdigit() and valid(int(text)):
        return int(text)
    if configs is None:
        configs = {name: read_file(path) for name, path in files().items()}
    port = _pick(edition, configs)
    if edition == "lite" and port == resolve("complete", env=env, configs=configs):      # two editions on one port cannot both listen: the lite one goes back to its own
        return DEFAULTS["lite"] if DEFAULTS["lite"] != port else DEFAULTS["lite"] + 1
    return port


def both(env=None, configs=None):
    """{edition: port} for the two editions."""
    return {edition: resolve(edition, env=env, configs=configs) for edition in EDITIONS}


def from_argv(argv, edition, env=None, configs=None):
    """The port asked with `--port N` in a list of arguments, else the one of the edition."""
    flag = next((int(argv[i + 1]) for i, a in enumerate(argv) if a == "--port" and i + 1 < len(argv) and argv[i + 1].isdigit()), None)
    return resolve(edition, flag=flag, env=env, configs=configs)
