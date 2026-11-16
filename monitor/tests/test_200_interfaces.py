# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The frozen interfaces of 2.x: the fields of an Alert, the methods of a sentinel and of a storage with the names of their parameters. A change here is a change of the contract: it needs a new major
version (or, for an addition with a default, a note in the changelog), never a quiet edit of this file."""
import inspect
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.sentinels import sentinel_base, sentinel_ci, sentinel_collab, sentinel_security
from github_actions_monitor.storage import base, file_storage, sqlite_storage

ALERT_FIELDS = ['id', 'code', 'level', 'sentinel', 'account_id', 'repo', 'title', 'details', 'created_at']
SENTINEL_METHODS = {
    'get_alerts': [],
    'get_config_schema': [],
    'get_metrics': [],
    'get_status': [],
    'refresh_seconds': [],
    'tick': [],
    'start': [],
    'stop': [],
    'due': ['now'],
    'run_loop': [],
}
STORAGE_METHODS = {
    'append_events': ['account_id', 'events'],
    'delete_record': ['kind', 'key'],
    'event_stats': ['account_id'],
    'export_account': ['account_id'],
    'export_records': [],
    'get_record': ['kind', 'key'],
    'import_account': ['account_id', 'payload'],
    'import_records': ['records'],
    'list_accounts': [],
    'list_records': ['kind'],
    'load_analytics': ['account_id'],
    'load_config': ['account_id'],
    'load_doc': ['account_id', 'name', 'default', 'strict'],
    'load_events': ['account_id', 'since', 'limit'],
    'load_score_snapshots': ['account_id', 'since', 'limit'],
    'load_sentinel_state': ['account_id', 'sentinel'],
    'purge_analytics': ['account_id', 'before_day'],
    'purge_events': ['account_id', 'before', 'archive_dir'],
    'purge_records': ['kind', 'expired_before'],
    'purge_score_snapshots': ['account_id', 'before_hour'],
    'put_record': ['kind', 'key', 'data', 'expires'],
    'save_analytics': ['account_id', 'data'],
    'save_config': ['account_id', 'data'],
    'save_doc': ['account_id', 'name', 'data'],
    'save_score_snapshot': ['account_id', 'hour', 'data'],
    'save_sentinel_state': ['account_id', 'sentinel', 'data'],
    'verify': [],
    'append_event': ['account_id', 'event'],
    'backup': ['dest'],
    'describe': [],
    'close': [],
}
RECORD_KINDS = ['users', 'user_accounts', 'sessions']


def parameters(function):
    function = function.fget if isinstance(function, property) else function
    return [name for name in inspect.signature(function).parameters if name != "self"]


class TheInterfacesAreFrozen(unittest.TestCase):
    def test_an_alert_has_exactly_these_fields(self):
        self.assertEqual(list(sentinel_base.Alert.__annotations__), ALERT_FIELDS)

    def test_a_sentinel_keeps_its_methods_and_their_parameters(self):
        for name, wanted in SENTINEL_METHODS.items():
            self.assertEqual(parameters(sentinel_base.BaseSentinel.__dict__[name]), wanted, name)
        self.assertEqual(sorted(sentinel_base.BaseSentinel.__abstractmethods__), sorted(["get_alerts", "get_config_schema", "get_metrics", "get_status", "refresh_seconds", "tick"]))

    def test_the_sentinels_that_exist_implement_it(self):
        for module, name in ((sentinel_ci, "CiSentinel"), (sentinel_collab, "CollabSentinel"), (sentinel_security, "SecuritySentinel")):
            cls = getattr(module, name, None)
            if cls is None:
                cls = next(c for c in vars(module).values() if isinstance(c, type) and issubclass(c, sentinel_base.BaseSentinel) and c is not sentinel_base.BaseSentinel)
            self.assertFalse(getattr(cls, "__abstractmethods__", frozenset()), f"{cls.__name__} leaves a method of the interface without a body")

    def test_a_storage_keeps_its_methods_and_their_parameters(self):
        for name, wanted in STORAGE_METHODS.items():
            self.assertEqual(parameters(base.Storage.__dict__[name]), wanted, name)
        self.assertEqual(sorted(base.Storage.__abstractmethods__), sorted(n for n in STORAGE_METHODS if n not in ("append_event", "backup", "describe", "close")))
        self.assertEqual(base.RECORD_KINDS, tuple(RECORD_KINDS))

    def test_both_storages_implement_every_method(self):
        for cls in (file_storage.FileStorage, sqlite_storage.SqliteStorage):
            self.assertFalse(cls.__abstractmethods__, cls.__name__)
            for name, wanted in STORAGE_METHODS.items():
                self.assertEqual(parameters(getattr(cls, name)), wanted, f"{cls.__name__}.{name}")


if __name__ == "__main__":
    unittest.main()
