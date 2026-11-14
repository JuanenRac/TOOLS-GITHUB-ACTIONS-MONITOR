# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The order of the lists of the page and who remembers it.

The page sorts what it draws (it has the runs in memory and the order costs nothing), so this module holds only what has to agree between the settings, the page and the server: the closed list
of orders each list accepts, the order that applies when nobody chose one (`ui.now_sort` in the configuration file) and the order a signed-in user chose (kept in the record of the user, so it
follows them to another browser). Anything outside the closed list is dropped, never stored.

* "now": the section "Happening now" of the first tab. `ecosystem` (the default, with a heading per ecosystem), `severity` (stuck first, then the runs with a failed job, then the rest), `age`
  (the longest running first), `newest` (the latest start first), `repo`, `event` (the kind of trigger: push, pull_request, schedule...) and `state` (running before queued).
"""
KINDS = {
    "now": ("ecosystem", "severity", "age", "newest", "repo", "event", "state"),
}
DEFAULTS = {"now": "ecosystem"}
SETTINGS = {"now": "now_sort"}


def configured(config, kind):
    """The order the configuration file asks for a list (`ui.<setting>`), or the default of the list when it is missing or not one of the closed list."""
    section = (config or {}).get("ui") if isinstance((config or {}).get("ui"), dict) else {}
    value = section.get(SETTINGS[kind])
    return value if value in KINDS[kind] else DEFAULTS[kind]


def clean_view(raw):
    """The orders of a user from whatever was stored or sent: only known lists with a key of their closed list."""
    if not isinstance(raw, dict):
        return {}
    return {kind: raw[kind] for kind in KINDS if raw.get(kind) in KINDS[kind]}


def get_view(storage, user):
    return clean_view((storage.get_record("users", user) or {}).get("view"))


def set_view(storage, user, body):
    """Saves the orders a user sends. Returns (view, "") or (None, code). A list that is not named stays as it was; the value "" forgets the choice (the order of the configuration file applies again)."""
    from github_actions_monitor.security import auth
    if not isinstance(body, dict):
        return None, "body_invalid"
    for kind, value in body.items():
        if kind not in KINDS:
            return None, "kind_invalid"
        if value != "" and value not in KINDS[kind]:
            return None, "order_invalid"
    with auth._lock:
        record = storage.get_record("users", user)
        if record is None:
            return None, "user_unknown"
        view = clean_view(record.get("view"))
        for kind, value in body.items():
            if value == "":
                view.pop(kind, None)
            else:
                view[kind] = value
        record["view"] = view
        storage.put_record("users", user, record)
    return view, ""
