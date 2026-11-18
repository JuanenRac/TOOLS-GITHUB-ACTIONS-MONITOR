# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the Delivery sentinel reads of ONE repository, through the API and without a clone (GET only, nothing is ever written to GitHub).

`read(endpoint)` answers the JSON of a read or raises (the sentinel gives it the `gh` of the account). One round of one repository makes at most:
  1 call for the latest releases (`/releases?per_page=10`)             only if one of the signals that use releases is on
  1 call for the latest tags (`/tags?per_page=10`)                       only if `tag_without_release` is on
  1+ calls for the CHANGELOG (the first of `changelog_paths` that exists; a 404 tries the next)   only if `unreleased_pending` or `version_mismatch` is on
  1 call for each of `version_files` (a file the repository does not have is skipped)             only if `version_mismatch` is on
A read that fails for a reason other than "not found" on a CONTENT file raises (the repository is then listed as one that could not be read); a missing file is simply absent.
"""
import base64

from github_actions_monitor.integrations import remote_workflows

MAX_TEXT = 262144      # a file bigger than this is cut (a CHANGELOG is read from its top, where [Unreleased] lives)
PER_PAGE = 10


def _content(body):
    """The text of an answer of the contents API ('' when it is not a file or is too big for the API to carry its content)."""
    if isinstance(body, dict) and body.get("encoding") == "base64":
        return base64.b64decode(str(body.get("content") or "")).decode("utf-8", "replace")[:MAX_TEXT]
    return ""


def _file(read, path_endpoint):
    """(text, found): found is False for a file that does not exist."""
    try:
        return _content(read(path_endpoint)), True
    except Exception as error:      # noqa: BLE001 - only "not found" means "absent"; the rest is a repository that cannot be read
        if remote_workflows.reason_of(error) == "not_found":
            return "", False
        raise


def plan(cfg):
    """What a round of one repository needs, from the settings: {"releases", "tags", "changelog_paths", "version_files"} (empty/False = not read)."""
    on = {name: bool(entry.get("enabled")) for name, entry in cfg["signals"].items()}
    need_changelog = on.get("unreleased_pending") or on.get("version_mismatch")
    return {"releases": any(on.get(n) for n in ("unreleased_pending", "tag_without_release", "release_without_notes", "assets_missing")), "tags": bool(on.get("tag_without_release")),
            "changelog_paths": list(cfg["changelog_paths"]) if need_changelog else [], "version_files": list(cfg["version_files"]) if on.get("version_mismatch") else []}


def minimum_calls(need):
    """The fewest calls a round of one repository can make with this plan (the sentinel does not start a repository it cannot even begin)."""
    return int(bool(need["releases"])) + int(bool(need["tags"])) + (1 if need["changelog_paths"] else 0) + len(need["version_files"])


def fetch(read, owner, repo, need, budget):
    """(facts, calls, complete) of one repository. `facts` = {"releases": list | None, "tags": [names] | None, "changelog": text | None, "versions": {path: text}}; `complete` is False when the
    budget of calls ended before everything the plan asked for was read (the sentinel then keeps what it knew). Raises when a read fails for any reason other than a missing file."""
    base = f"repos/{owner}/{repo}"
    facts, calls, complete = {"releases": None, "tags": None, "changelog": None, "versions": {}}, 0, True
    if need["releases"]:
        if calls >= budget:
            return facts, calls, False
        calls += 1
        answer = read(f"{base}/releases?per_page={PER_PAGE}")
        facts["releases"] = [r for r in answer if isinstance(r, dict)] if isinstance(answer, list) else []
    if need["tags"]:
        if calls >= budget:
            return facts, calls, False
        calls += 1
        answer = read(f"{base}/tags?per_page={PER_PAGE}")
        facts["tags"] = [str(t.get("name")) for t in answer if isinstance(t, dict) and t.get("name")] if isinstance(answer, list) else []
    for path in need["changelog_paths"]:
        if calls >= budget:
            return facts, calls, False
        calls += 1
        text, found = _file(read, f"{base}/contents/{path}")
        if found:
            facts["changelog"] = text
            break
    for path in need["version_files"]:
        if calls >= budget:
            return facts, calls, False
        calls += 1
        text, found = _file(read, f"{base}/contents/{path}")
        if found:
            facts["versions"][path] = text
    return facts, calls, complete


def fetch_pin_table(read, owner, source):
    """(current version, {repo: pinned version}) of a pin table of the provider of a shared contract, or raises. `current` is the tag of the latest published release of the provider."""
    base = f"repos/{owner}/{source['provider']}"
    latest = read(f"{base}/releases/latest")
    current = str(latest.get("tag_name") or "") if isinstance(latest, dict) else ""
    text, found = _file(read, f"{base}/contents/{source.get('file') or ''}")
    table = {}
    if found:
        import json
        try:
            data = json.loads(text or "{}")
        except ValueError:
            data = {}
        table = data.get(str(source.get("key") or "consumers")) if isinstance(data, dict) else None
    return current, ({k: v for k, v in table.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(table, dict) else {})
