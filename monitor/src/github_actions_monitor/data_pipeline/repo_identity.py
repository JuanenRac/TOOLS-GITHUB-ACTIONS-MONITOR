# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The identity of a watched repository is (source, owner, name): two repositories with one name that come from two places, or belong to two owners, are two repositories.

  source   "github", or "<kind>@<host>" for a repository read from an external CI server
  owner    the account on that source (the namespace of the project on an external server)
  name     the name of the repository there

The routes and the pages keep naming a repository by its name; the identity travels beside it as `repo_key` ("source:owner/name"). A record without `repo_key` was written before it existed and belongs to
("github", the owner the monitor recorded for its data, name): storage/identity_migration.py keeps that record. Standard library only; nothing here reads the network."""
import re
from collections import namedtuple
from urllib.parse import unquote, urlsplit

GITHUB = "github"
Identity = namedtuple("Identity", "source owner name")
KEY_RE = re.compile(r"^(github|[a-z]+@[A-Za-z0-9._\[\]-]*(?::\d{1,5})?):(.*)/([^/]+)\Z")


def key(source, owner, name):
    """"source:owner/name". GitHub does not tell upper from lower case, so a GitHub key is lower case; another server may, so only the source is lowered there."""
    source = str(source or GITHUB).strip().lower()
    owner, name = str(owner or "").strip().strip("/"), str(name or "").strip()
    if source == GITHUB:
        owner, name = owner.lower(), name.lower()
    return f"{source}:{owner}/{name}"


def parse(value):
    """The Identity of a key, or None when the text is not one."""
    found = KEY_RE.match(value) if isinstance(value, str) else None
    return Identity(*found.groups()) if found else None


def host_of(url):
    try:
        parts = urlsplit(str(url or ""))
        host = (parts.hostname or "").lower()
        return f"{host}:{parts.port}" if parts.port else host
    except ValueError:
        return ""


def external(kind, url, project, name):
    """The key of a repository of an external CI server: the namespace of `project` is the owner and its last part the name; `name` (the mirror) is used when the source names no project."""
    parts = [p for p in unquote(str(project or "")).split("/") if p]
    return key(f"{kind}@{host_of(url)}", "/".join(parts[:-1]), parts[-1] if parts else name)


def github(owner, name):
    return key(GITHUB, owner, name)


def of_record(record, home_owner):
    """The key of a record that names a repository: its own `repo_key`, else the repository of that name of the home owner on GitHub. "" when it names none."""
    if not isinstance(record, dict):
        return ""
    if parse(record.get("repo_key")):
        return record["repo_key"]
    name = record.get("repo")
    return github(home_owner, name) if isinstance(name, str) and name else ""


def same_owner(record_key, owner):
    """False only when the key is of a GitHub repository of ANOTHER owner than `owner` (both known)."""
    found = parse(record_key)
    if found is None or found.source != GITHUB or not found.owner or not owner:
        return True
    return found.owner == str(owner).strip().lower()
