# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The manifest of a plugin (plugin.json): strict reading with a stable reason for every refusal, and the paths a plugin may ask GitHub for. Standard library only.

  {"name": "my-plugin", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party", "entry": "plugin.py",
   "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
"""
import json
import re

API_VERSION = "1"                  # the version of the contract between the monitor and a plugin (ctx and the answer of run)
MANIFEST_NAME = "plugin.json"
MAX_MANIFEST = 32 * 1024
TRUSTS = ("official", "third_party")
PERMISSIONS = ("repos.list", "gh.get", "graphql.discussions")
#: the method of ctx -> the permission it needs
METHOD_PERMISSION = {"repos": "repos.list", "get": "gh.get", "discussions": "graphql.discussions"}
NAME_RE = re.compile(r"[a-z][a-z0-9-]{1,39}\Z")
VERSION_RE = re.compile(r"\d{1,4}\.\d{1,4}\.\d{1,6}\Z")
ENTRY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\.py\Z")
PATTERN_RE = re.compile(r"(?:repos|users|orgs)(?:/(?:[A-Za-z0-9_.-]+|\{(?:owner|repo|name)\}))+(?:\?[A-Za-z0-9_]+=[A-Za-z0-9_-]+(?:&[A-Za-z0-9_]+=[A-Za-z0-9_-]+)*)?\Z")
SEGMENT = r"(?!\.\.?(?:/|\?|\Z))[A-Za-z0-9_.%-]+"
KEYS = ("name", "version", "api_compat", "author", "description", "trust", "entry", "permissions", "get_paths", "refresh_seconds")


class ManifestError(ValueError):
    """`code` is a short stable word: json, size, keys, name, version, api_compat, author, trust, entry, permissions, get_paths, refresh."""

    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code


def parse(text):
    """The validated manifest (a new dict) of the text of a plugin.json."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if len(text) > MAX_MANIFEST:
        raise ManifestError("size")
    try:
        raw = json.loads(text)
    except ValueError:
        raise ManifestError("json") from None
    if not isinstance(raw, dict) or any(k not in KEYS and not k.startswith("_") for k in raw):
        raise ManifestError("keys", "unknown keys: " + ", ".join(sorted(k for k in raw if k not in KEYS)[:5]) if isinstance(raw, dict) else "not an object")
    name, version = raw.get("name"), raw.get("version")
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ManifestError("name", "the name is 2 to 40 lower case letters, digits or dashes")
    if not isinstance(version, str) or not VERSION_RE.match(version):
        raise ManifestError("version", "the version is N.N.N")
    if raw.get("api_compat") != API_VERSION:
        raise ManifestError("api_compat", f"this monitor speaks version {API_VERSION} of the plugin contract, the plugin asks for {str(raw.get('api_compat'))[:10]!r}")
    for key in ("author", "description"):
        if not isinstance(raw.get(key), str) or not raw[key].strip() or len(raw[key]) > 300:
            raise ManifestError("author", f"{key} is a text of 1 to 300 characters")
    if raw.get("trust") not in TRUSTS:
        raise ManifestError("trust", "trust is official or third_party")
    entry = raw.get("entry")
    if not isinstance(entry, str) or not ENTRY_RE.match(entry):
        raise ManifestError("entry", "entry is the name of a .py file of the plugin")
    permissions = raw.get("permissions")
    if not isinstance(permissions, list) or any(p not in PERMISSIONS for p in permissions) or len(set(permissions)) != len(permissions):
        raise ManifestError("permissions", "permissions are taken from " + ", ".join(PERMISSIONS))
    paths = raw.get("get_paths", [])
    if not isinstance(paths, list) or len(paths) > 20 or any(not isinstance(p, str) or len(p) > 200 or not PATTERN_RE.match(p) or "/../" in p + "/" for p in paths):
        raise ManifestError("get_paths", "get_paths are API paths under repos/, users/ or orgs/")
    if bool(paths) != ("gh.get" in permissions):
        raise ManifestError("get_paths", "get_paths and the permission gh.get go together")
    refresh = raw.get("refresh_seconds", 3600)
    if isinstance(refresh, bool) or not isinstance(refresh, int) or not 600 <= refresh <= 7 * 86400:
        raise ManifestError("refresh", "refresh_seconds is 600 to 604800")
    return {"name": name, "version": version, "api_compat": API_VERSION, "author": raw["author"].strip(), "description": raw["description"].strip(), "trust": raw["trust"], "entry": entry,
            "permissions": list(permissions), "get_paths": list(paths), "refresh_seconds": refresh}


def path_allowed(manifest, path, owner, repos):
    """True when `path` is one of the declared get_paths: {owner} is the account watched, {repo} a watched repository and {name} one plain segment."""
    if not isinstance(path, str) or len(path) > 300:
        return False
    for pattern in manifest["get_paths"]:
        regex = re.escape(pattern).replace(re.escape("{owner}"), re.escape(owner) if owner else "(?!)").replace(re.escape("{name}"), SEGMENT)
        regex = regex.replace(re.escape("{repo}"), "(?:" + ("|".join(re.escape(r) for r in repos) or "(?!)") + ")")
        if re.match(regex + r"\Z", path):
            return True
    return False
