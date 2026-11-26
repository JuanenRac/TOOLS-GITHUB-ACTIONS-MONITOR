# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The registry of the parts of the monitor that plug in by themselves (families/declare.py says what a part can declare). The list is closed and fixed: a part is a folder of this package named here, so nothing
that is dropped on the disk is ever loaded. With parts that declare nothing, the monitor behaves exactly as without them.

The server, the settings, the command line, the texts, the page and the egress table ask this module; they never name a part."""
import contextlib
import copy
import importlib
from pathlib import Path

from github_actions_monitor.families.declare import Command, Egress, Family, Option, Request, Route, Setting  # noqa: F401 - the one place to import them from

NAMES = ("supply", "plugins", "assistant", "extci", "compliance", "actions", "fleet", "posture")      # the order in which their settings, commands and pages are added
FOLDER = Path(__file__).resolve().parent
_LOADED = []
_EXTRA = []      # (family, folder) added by a test (see `using`)


def _all():
    """[(family, its folder)] in the order of NAMES."""
    if not _LOADED:
        _LOADED.extend([(importlib.import_module(f"{__name__}.{name}").FAMILY, FOLDER / name) for name in NAMES])
    return _LOADED + _EXTRA


def all_families():
    return [family for family, _folder in _all()]


@contextlib.contextmanager
def using(family, folder=None):
    """A test adds a part of its own for a while: what is asked at run time (routes, roles, ticks, page) sees it. What is built once at import (settings, defaults, commands) is tested with the
    functions of this module that take the target."""
    entry = (family, Path(folder) if folder else FOLDER / family.name)
    _EXTRA.append(entry)
    try:
        yield family
    finally:
        _EXTRA.remove(entry)


# --- defaults and settings -------------------------------------------------------------------------------------------------------------------------------------------------------------

def merge_into(target, extra, path=""):
    """Adds the keys of `extra` to `target`, going into the blocks that both have. A key that already has a value is a mistake (ValueError): a part never changes a default of another."""
    for key, value in extra.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
        elif isinstance(target[key], dict) and isinstance(value, dict):
            merge_into(target[key], value, f"{path}{key}.")
        else:
            raise ValueError(f"the default {path}{key} is declared twice")
    return target


def defaults():
    out = {}
    for family in all_families():
        merge_into(out, family.defaults)
    return out


def default_of(dotted, fallback=None):
    node = defaults()
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return fallback
        node = node[part]
    return node


def _overlay(base, over):
    out = dict(base)
    for key, value in over.items():
        out[key] = _overlay(out[key], value) if isinstance(out.get(key), dict) and isinstance(value, dict) else value
    return out


def block(config, dotted):
    """The block `dotted` of the configuration over the defaults of the parts (load_config only merges the first level): what a part reads its settings with."""
    node = config
    for part in dotted.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    base = default_of(dotted, {})
    return _overlay(base if isinstance(base, dict) else {}, node if isinstance(node, dict) else {})


def settings():
    return [row for family in all_families() for row in family.settings]


def tab_order(base):
    """The tabs of Settings with the new ones of the parts, each after the tab it names (at the end when that tab does not exist)."""
    order = list(base)
    for family in all_families():
        for tab, after in family.settings_tabs:
            if tab not in order:
                order.insert(order.index(after) + 1 if after in order else len(order), tab)
    return tuple(order)


# --- routes ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def routes():
    return [route for family in all_families() for route in family.routes]


def find_route(method, path):
    method = "GET" if method == "HEAD" else method
    for route in routes():
        if route.path == path and route.method == method:
            return route
    return None


def role_for(method, path):
    """The least role of a route of a part, or None when no part owns it (security/auth.required_role then decides)."""
    route = find_route(method, path)
    if route is None:
        return None
    return route.role or ("viewer" if route.method == "GET" else "admin")


def audited():
    return {route.path: route.audit for route in routes() if route.method == "POST" and route.audit}


def exempt():
    return {route.path: route.exempt for route in routes() if route.method == "POST" and not route.audit}


# --- the command line --------------------------------------------------------------------------------------------------------------------------------------------------------------------

def commands():
    return [command for family in all_families() for command in family.commands]


# --- the loop and the network ----------------------------------------------------------------------------------------------------------------------------------------------------------

def run_ticks(config, data, failed):
    """Every tick of every part; one that raises is handed to `failed(name, error)` and the others still run."""
    for family in all_families():
        for tick in family.ticks:
            try:
                tick(config, data)
            except Exception as error:      # noqa: BLE001 - a part never stops the loop
                failed(f"family.{family.name}", error)


def egress():
    return [row for family in all_families() for row in family.egress]


# --- the texts and the page ------------------------------------------------------------------------------------------------------------------------------------------------------------

def catalogue_files(language):
    """The files with the texts of the parts for one language (only the ones that exist). It reads no module, so the translations can ask it at any moment."""
    folders = [FOLDER / name for name in NAMES] + [folder for _family, folder in _EXTRA]
    return [path for path in (folder / "i18n" / f"{language}.json" for folder in folders) if path.is_file()]


def _texts(folders, name):
    return [(folder.name, (folder / name).read_text(encoding="utf-8")) for folder in folders if (folder / name).is_file()]


def inject_page(page):
    """The styles and the scripts of the parts, added to the page after its own. Each script is in a tag of its own, so that one that does not parse does not stop the page. With no page.js and no
    page.css the page is returned as it came."""
    folders = [folder for _family, folder in _all()]
    styles, scripts = _texts(folders, "page.css"), _texts(folders, "page.js")
    if styles:
        page = page.replace("</head>", "".join(f"<style data-part=\"{name}\">\n{text}\n</style>\n" for name, text in styles) + "</head>", 1)
    if scripts:
        core = (FOLDER / "page.js").read_text(encoding="utf-8")
        tags = f"<script>\n{core}\n</script>\n" + "".join(f"<script data-part=\"{name}\">\ntry{{\n{text}\n}}catch(e){{console.error(e)}}\n</script>\n" for name, text in scripts)
        head, mark, tail = page.rpartition("</body>")
        page = head + tags + mark + tail if mark else page + tags
    return page
