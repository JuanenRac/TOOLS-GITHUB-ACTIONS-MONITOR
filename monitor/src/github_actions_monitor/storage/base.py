# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The storage interface: what the monitor needs to keep, with no word about how it is kept.

A backend (files, SQLite) implements `Storage`; the rest of the monitor asks for what it needs and never builds a path. Everything is per account (`account_id`, the id of
accounts/<id>/; a single-account installation is the account "default"), except the global records (users, their accounts and sessions) that belong to the installation.

What is kept, by purpose:

  config          the configuration of an account (a dict)
  sentinel state  one document per sentinel and name ("sentinel_cache", "collab_state"...): state the sentinels can rebuild, but that saves reads of GitHub
  events          the feed: one dict per event, in time order, each with its `at` (UTC, "YYYY-MM-DDTHH:MM:SSZ")
  analytics       the local samples of the analytics (queue times, step times, the daily p50)
  documents       the small named state of an account (the silences, the state of the feed, the update notice...)
  records         global: `users`, `user_accounts` and `sessions`, key -> dict, with an optional expiry (a session)

Rules every backend keeps (the tests of tests/test_storage_contract.py run on each of them):

  * a write is atomic: a reader sees the old value or the new one, never half of it, and a process killed in the middle leaves the old value;
  * a missing or damaged item reads as the empty value ({} / [] / default), it never raises: the monitor must start with whatever is on the disk;
  * an event is appended whole or not at all; a damaged line of the feed is skipped by the reader;
  * purging removes only old events and old analytics days: it never touches the configuration, the sentinel state or the documents.
"""
import re
from abc import ABC, abstractmethod

#: global kinds of records (the tables of the SQLite backend); a new kind is added here AND in a schema migration
RECORD_KINDS = ("users", "user_accounts", "sessions")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,59}\Z")      # a sentinel / document name: also a file name, so it can never carry a path
ACCOUNT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}\Z")   # same rule as accounts.valid_id
KEY_RE = re.compile(r"^[A-Za-z0-9._@:+-]{1,200}\Z")        # the key of a record
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?Z?)?\Z")


class StorageError(Exception):
    """The backend cannot do what was asked (an unsafe name, a newer schema, a damaged copy). Never raised for a missing or damaged item: that reads as empty."""


def check_account(account_id):
    if not isinstance(account_id, str) or not ACCOUNT_RE.match(account_id):
        raise StorageError("account id")
    return account_id


def check_name(name):
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise StorageError("name")
    return name


def check_kind(kind):
    if kind not in RECORD_KINDS:
        raise StorageError("record kind")
    return kind


def check_key(key):
    if not isinstance(key, str) or not KEY_RE.match(key):
        raise StorageError("record key")
    return key


def event_ts(event):
    """The `at` of an event as text ('' when it has none)."""
    value = event.get("at") if isinstance(event, dict) else None
    return value if isinstance(value, str) else ""


def stamp_events(events, at=None):
    """The events that are dicts, each as a new dict that has its `at` (the one it had when it is text, else `at`, else the time of now)."""
    from datetime import datetime, timezone
    at = at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for event in events:
        if isinstance(event, dict):
            out.append({**event, "at": event["at"] if isinstance(event.get("at"), str) and event["at"] else at})
    return out


class Storage(ABC):
    """The interface. `backend` names the implementation ("file", "sqlite")."""

    backend = ""

    # -- configuration
    @abstractmethod
    def load_config(self, account_id):
        """The configuration of the account as a dict ({} when there is none or it is damaged)."""

    @abstractmethod
    def save_config(self, account_id, data):
        """Replaces the configuration of the account, atomically."""

    # -- sentinels
    @abstractmethod
    def load_sentinel_state(self, account_id, sentinel):
        """The state a sentinel keeps under this name, as a dict ({} when missing or damaged)."""

    @abstractmethod
    def save_sentinel_state(self, account_id, sentinel, data):
        """Replaces that state, atomically."""

    # -- events
    @abstractmethod
    def append_events(self, account_id, events):
        """Appends events (dicts) in order. An event without `at` gets the time of now (UTC). All of them or none of them for a backend with transactions."""

    def append_event(self, account_id, event):
        self.append_events(account_id, [event])

    @abstractmethod
    def load_events(self, account_id, since=None, limit=100):
        """The newest `limit` events (None = all) whose `at` is not older than `since` (inclusive, the same text format as `at`), oldest first."""

    # -- analytics
    @abstractmethod
    def load_analytics(self, account_id):
        """The samples of the analytics as a dict ({} when missing)."""

    @abstractmethod
    def save_analytics(self, account_id, data):
        """Replaces them, atomically."""

    # -- named documents of an account
    @abstractmethod
    def load_doc(self, account_id, name, default=None):
        """A small named document (a dict), or `default` when it is missing or damaged."""

    @abstractmethod
    def save_doc(self, account_id, name, data):
        """Replaces it, atomically."""

    # -- global records (the users, their accounts, the sessions)
    @abstractmethod
    def put_record(self, kind, key, data, expires=None):
        """Creates or replaces one record. `expires` (epoch seconds) lets `purge_records` remove it later (a session)."""

    @abstractmethod
    def get_record(self, kind, key):
        """The record (a dict) or None."""

    @abstractmethod
    def delete_record(self, kind, key):
        """Removes it; True when it existed."""

    @abstractmethod
    def list_records(self, kind):
        """{key: data} of every record of the kind."""

    @abstractmethod
    def purge_records(self, kind, expired_before):
        """Removes the records whose `expires` is set and older than `expired_before` (epoch seconds). Returns how many."""

    # -- accounts
    @abstractmethod
    def list_accounts(self):
        """The ids of the accounts this storage knows, sorted."""

    # -- maintenance (retention, backup, migration)
    @abstractmethod
    def event_stats(self, account_id):
        """{"count", "bytes", "oldest", "newest"} of the feed of the account (oldest/newest are '' when it is empty)."""

    @abstractmethod
    def purge_events(self, account_id, before, archive_dir=None):
        """Removes the events whose `at` is older than `before` (events without a time stay). With `archive_dir` the removed ones are first written to a .gz there (one file per call).
        Returns {"removed": n, "kept": n, "archived": path or ""}."""

    @abstractmethod
    def purge_analytics(self, account_id, before_day):
        """Removes the days of `daily` older than `before_day` ("YYYY-MM-DD"). Returns {"removed": n}."""

    @abstractmethod
    def export_account(self, account_id):
        """Everything of one account as plain data: {"config", "sentinels": {name: dict}, "docs": {name: dict}, "events": [dict], "analytics": dict}. Used by the migration and the backup."""

    @abstractmethod
    def import_account(self, account_id, payload):
        """Replaces everything of one account with `payload` (the shape of `export_account`). Idempotent: running it twice leaves the same result."""

    @abstractmethod
    def verify(self):
        """A list of problems found in the data (empty = sound). Reads only."""

    @abstractmethod
    def export_records(self):
        """Every global record as {kind: {key: {"data": dict, "expires": float or None}}}."""

    @abstractmethod
    def import_records(self, records):
        """Creates or replaces the records of `export_records` (the shape is the same)."""

    def backup(self, dest):
        """Writes a verifiable copy of the whole storage to the file `dest` (a .zip with a manifest of sizes and SHA-256) that any backend can restore. Returns the manifest."""
        from github_actions_monitor.storage import backup
        return backup.make_backup(self, dest)

    def describe(self):
        return {"backend": self.backend}

    def close(self):
        """Releases what the backend holds open. Safe to call twice."""
