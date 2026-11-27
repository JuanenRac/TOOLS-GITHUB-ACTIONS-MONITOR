# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Metadata columns: a column of the Repositories table whose value is one line of a file of each repository (the version of a template, the pin of an SDK), found by a path and a regular expression.

  fleet.meta_columns = [{"name": "Template", "path": ".template-version", "regex": "^version: (\\S+)"}, ...]     empty by default, at most 5

The monitor reads the file with the contents API (a conditional read: when the file did not change GitHub answers 304 and it costs no allowance), keeps the value by the SHA of the blob, and only reads
again when the SHA changes or `fleet.meta_ttl_hours` pass. A round reads at most `fleet.meta_per_call` pairs repository/column, so a large fleet fills in over a few refreshes. Read only; a file that does
not exist is a dash, never an error; only the first 8 KB of a file are looked at, and the regular expression is refused when it could take exponential time.

  settings(config)       {"columns": [...validated...], "per_call", "ttl_hours"}
  valid_column(item)     (clean column, "") or (None, reason)
  extract(text, regex)   the first match in the first lines: the first group, or the whole match, cut to 60 characters
  Reader                 the cache {(repo, column id): {"sha", "value", "at"}} and `fill(repos, columns, read, now)`
"""
import base64
import re
import threading
import time

MAX_COLUMNS = 5
MAX_BYTES = 8192
VALUE_MAX = 60
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,23}\Z")
PATH_RE = re.compile(r"^[A-Za-z0-9_.][A-Za-z0-9_. /+-]{0,118}\Z")
RISKY = re.compile(r"\\[1-9]|\(\?[=!<]")      # a back reference and look-around: with a repeat of a repeat (below), the shapes that can take exponential time
DEFAULTS = {"per_call": 20, "ttl_hours": 6}


def repeat_of_repeat(text):
    """True when a group that holds a `+` or `*` is itself repeated. Read in one pass: between two `)`, a `(` followed by `+` or `*`, and the `)` followed by `+`, `*` or `{`."""
    pieces = text.split(")")
    for piece, after in zip(pieces[:-1], pieces[1:], strict=True):
        _before, opened, inner = piece.partition("(")
        if opened and ("+" in inner or "*" in inner) and after[:1] in ("+", "*", "{"):
            return True
    return False


def column_id(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")[:24] or "col"


def valid_column(item):
    """(column, "") with `id`, `name`, `path`, `regex` (compiled to check it), or (None, reason): not_object, bad_name, bad_path, bad_regex, risky_regex."""
    if not isinstance(item, dict):
        return None, "not_object"
    name, path, regex = item.get("name"), item.get("path"), item.get("regex")
    if not isinstance(name, str) or not NAME_RE.match(name):
        return None, "bad_name"
    if not isinstance(path, str) or not PATH_RE.match(path) or ".." in path.split("/") or path.startswith("/"):
        return None, "bad_path"
    if not isinstance(regex, str) or not 0 < len(regex) <= 120:
        return None, "bad_regex"
    if RISKY.search(regex) or repeat_of_repeat(regex):
        return None, "risky_regex"
    try:
        re.compile(regex)
    except re.error:
        return None, "bad_regex"
    return {"id": column_id(name), "name": name, "path": path, "regex": regex}, ""


def settings(config):
    fleet = (config or {}).get("fleet") if isinstance((config or {}).get("fleet"), dict) else {}
    raw = fleet.get("meta_columns")
    columns, seen = [], set()
    for item in raw[:MAX_COLUMNS] if isinstance(raw, list) else []:
        column, _why = valid_column(item)
        if column and column["id"] not in seen:
            seen.add(column["id"])
            columns.append(column)

    def number(key, low, high):
        value = fleet.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else DEFAULTS[key.replace("meta_", "")]
    return {"columns": columns, "per_call": number("meta_per_call", 1, 200), "ttl_hours": number("meta_ttl_hours", 1, 168)}


def extract(text, regex):
    """The value of the first line (of the first 8 KB) that the expression matches: its first group, or the whole match; '' when nothing matches."""
    try:
        pattern = re.compile(regex, re.M)
    except re.error:
        return ""
    found = pattern.search(str(text or "")[:MAX_BYTES])
    if not found:
        return ""
    value = found.group(1) if pattern.groups and found.group(1) is not None else found.group(0)
    return re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()[:VALUE_MAX]


class Reader:
    def __init__(self):
        self.cache = {}
        self.lock = threading.RLock()

    def due(self, repo, column, ttl_hours, now):
        row = self.cache.get((repo, column["id"]))
        return row is None or now - row["at"] >= ttl_hours * 3600

    def fill(self, repos, columns, read, per_call, ttl_hours, now=None):
        """Reads at most `per_call` pairs that are due (the oldest first); `read(endpoint)` is a GET of the contents API (a dict with `sha` and `content`, or raises: a missing file is a dash). Returns
        how many pairs are still waiting."""
        now = time.time() if now is None else now
        with self.lock:
            todo = sorted(((self.cache.get((r, c["id"]), {}).get("at", 0), r, c) for r in repos for c in columns if self.due(r, c, ttl_hours, now)), key=lambda t: (t[0], t[1], t[2]["id"]))
            for _at, repo, column in todo[:per_call]:
                value, sha = "", ""
                try:
                    answer = read(f"repos/{repo}/contents/{column['path']}")
                    if isinstance(answer, dict) and answer.get("encoding") == "base64":
                        sha = str(answer.get("sha") or "")
                        before = self.cache.get((repo, column["id"]))
                        if before and before["sha"] == sha and before.get("regex") == column["regex"]:
                            value = before["value"]      # the blob did not change: the same value, nothing to read again
                        else:
                            raw = base64.b64decode(answer.get("content") or "")[:MAX_BYTES]
                            value = extract(raw.decode("utf-8", "replace"), column["regex"])
                except Exception:   # noqa: BLE001 - no file, no access, no network: a dash, and it is tried again after the ttl
                    value, sha = "", ""
                self.cache[(repo, column["id"])] = {"sha": sha, "value": value, "at": now, "regex": column["regex"]}
            return max(0, len(todo) - per_call)

    def rows(self, repos, columns):
        return {repo: {c["id"]: (self.cache.get((repo, c["id"])) or {}).get("value", "") for c in columns} for repo in repos}

    def forget(self):
        with self.lock:
            self.cache.clear()
