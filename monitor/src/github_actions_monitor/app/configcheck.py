# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A check of the configuration file when the monitor starts: a key that nobody reads (a typo), a value of the wrong type and a number out of its range are named, with the closest known key.

Nothing is changed and nothing is refused unless `config_check.strict` is on (off by default): the monitor starts, uses the default of what it could not read and says what it found, so a mistyped key
is not silently ignored for months. A key counts as KNOWN when the schema of the Settings tab, the defaults of the monitor or the example file that ships with the product know it, or when it lies inside
a free-form value (a map or a list the product reads whole). Keys that start with an underscore are notes and are never judged.
"""
import difflib
import json

from github_actions_monitor.util import paths

MAX_PROBLEMS = 50
_KNOWN = {}


def _leaves(tree, prefix=""):
    """Every path of a nested dict down to the first value that is not a non-empty dict."""
    for key, value in tree.items():
        path = prefix + str(key)
        if isinstance(value, dict) and value:
            yield path, None
            yield from _leaves(value, path + ".")
        else:
            yield path, value


def known_paths():
    """(all known paths, the paths that are leaves of the schema). Built once: the schema, the defaults of the monitor and the example file."""
    if _KNOWN:
        return _KNOWN["all"], _KNOWN["fields"]
    from github_actions_monitor.app import actions_monitor, settings_api
    names = set(settings_api.FIELDS)
    defaults = dict(_leaves(actions_monitor.DEFAULTS))
    names.update(defaults)
    try:
        example = json.loads((paths.EXAMPLES / "actions_monitor.example.json").read_text(encoding="utf-8"))
        names.update(path for path, _ in _leaves(example))
    except (OSError, ValueError):
        pass
    for path in list(names):       # the parents of every known path are known too
        parts = path.split(".")
        names.update(".".join(parts[:n]) for n in range(1, len(parts)))
    _KNOWN.update(all=names, fields=set(settings_api.FIELDS), defaults=defaults)
    return names, _KNOWN["fields"]


def check(config):
    """[{"path", "problem": unknown | type | range, "hint"}] for a configuration read from its file. Never raises; at most MAX_PROBLEMS entries."""
    from github_actions_monitor.app import settings_api
    if not isinstance(config, dict):
        return []
    names, fields = known_paths()
    defaults = _KNOWN["defaults"]
    out = []

    def walk(tree, prefix):
        for key, value in tree.items():
            if len(out) >= MAX_PROBLEMS:
                return
            if not isinstance(key, str) or key.startswith("_"):
                continue
            path = prefix + key
            if path in fields:
                if path in defaults and defaults[path] == value:      # what the monitor itself holds as the default is never a defect
                    continue
                ok, why = settings_api.check_value(path, value)
                if not ok:
                    out.append({"path": path, "problem": "range" if why in ("range", "bounds") else "type", "hint": ""})
                continue
            if path in names:
                if isinstance(value, dict):
                    walk(value, path + ".")
                continue
            if _inside_free_form(path, fields):
                continue
            close = difflib.get_close_matches(path, sorted(names), n=1, cutoff=0.8)
            out.append({"path": path, "problem": "unknown", "hint": close[0] if close else ""})
    walk(config, "")
    return out


def _inside_free_form(path, fields):
    """True when a parent of the path is a setting that is read whole (a map, a list, a table): its inner keys are not judged."""
    parts = path.split(".")
    return any(".".join(parts[:n]) in fields for n in range(1, len(parts)))


def settings(config):
    block = config.get("config_check") if isinstance(config, dict) and isinstance(config.get("config_check"), dict) else {}
    return {"strict": block.get("strict") is True}
