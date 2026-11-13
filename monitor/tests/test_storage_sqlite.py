# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The SQLite backend: the same contract as the files, plus what is specific to a database: versioned migrations that are atomic (an interrupted one leaves nothing half done), a newer
schema is refused, WAL and busy timeout, indexes, a process killed in the middle of a write, two accounts ticking at once (two processes), the shared file of model B read while others
write, and the migration tool between the two backends."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.storage import base, factory, file_storage, sqlite_storage  # noqa: E402
from test_storage import Contract  # noqa: E402

NEW = "2026-06-01T12:00:00Z"


class SqliteContract(Contract, unittest.TestCase):
    def make(self):
        return sqlite_storage.SqliteStorage(Path(self.tmp.name) / f"db{len(os.listdir(self.tmp.name))}" / "storage.sqlite3")

    def reopen(self):
        return sqlite_storage.SqliteStorage(self.storage.path)


class Schema(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "s.sqlite3"

    def tables(self):
        con = sqlite3.connect(str(self.db))
        try:
            return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            con.close()

    def test_a_new_database_has_the_schema_the_indexes_and_wal(self):
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        self.assertEqual(s.schema_version(), sqlite_storage.SCHEMA_VERSION)
        self.assertTrue({"accounts", "configs", "sentinel_states", "events", "analytics_snapshots", "users", "user_accounts", "sessions", "meta"} <= self.tables())
        info = s.describe()
        self.assertEqual((info["journal_mode"], info["busy_timeout_ms"]), ("wal", 30000))
        con = sqlite3.connect(str(self.db))
        try:
            indexes = {r[1]: [c[2] for c in con.execute(f"PRAGMA index_info({r[1]})")] for r in con.execute("PRAGMA index_list(events)")}
        finally:
            con.close()
        self.assertIn(["account_id", "ts"], indexes.values())

    def test_the_query_of_the_feed_uses_the_index(self):
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        plan = " ".join(str(r) for r in s._conn().execute("EXPLAIN QUERY PLAN SELECT data FROM events WHERE account_id = ? AND ts >= ? ORDER BY ts DESC, id DESC LIMIT 5", ("a", "x")))
        self.assertIn("events_account_ts", plan)

    def test_opening_again_changes_nothing(self):
        s = sqlite_storage.SqliteStorage(self.db)
        s.save_config("alpha", {"a": 1})
        s.close()
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        self.assertEqual((s.schema_version(), s.load_config("alpha")), (1, {"a": 1}))

    def test_a_later_migration_runs_on_an_existing_database_and_keeps_the_data(self):
        s = sqlite_storage.SqliteStorage(self.db)
        s.save_config("alpha", {"a": 1})
        s.close()
        later = dict(sqlite_storage.MIGRATIONS)
        later[2] = ["ALTER TABLE users ADD COLUMN note TEXT", "CREATE INDEX users_note ON users (note)"]
        s = sqlite_storage.SqliteStorage(self.db, migrations=later)
        self.addCleanup(s.close)
        self.assertEqual((s.schema_version(), s.load_config("alpha")), (2, {"a": 1}))

    def test_a_migration_that_fails_in_the_middle_leaves_the_database_as_it_was(self):
        s = sqlite_storage.SqliteStorage(self.db)
        s.save_config("alpha", {"a": 1})
        s.close()
        later = dict(sqlite_storage.MIGRATIONS)
        later[2] = ["ALTER TABLE users ADD COLUMN note TEXT", "THIS IS NOT SQL"]
        with self.assertRaises(sqlite3.Error):
            sqlite_storage.SqliteStorage(self.db, migrations=later)
        con = sqlite3.connect(str(self.db))
        try:
            self.assertEqual(con.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0], "1")
            self.assertNotIn("note", [c[1] for c in con.execute("PRAGMA table_info(users)")])      # the first statement of the failed migration was rolled back too
        finally:
            con.close()
        later[2] = ["ALTER TABLE users ADD COLUMN note TEXT"]
        s = sqlite_storage.SqliteStorage(self.db, migrations=later)      # and the next try runs it whole
        self.addCleanup(s.close)
        self.assertEqual(s.schema_version(), 2)

    def test_a_process_killed_in_the_middle_of_the_first_migration_leaves_no_half_schema(self):
        code = textwrap.dedent("""
            import os, sys
            sys.path.insert(0, sys.argv[1])
            from github_actions_monitor.storage import sqlite_storage
            def hook(version, statement):
                if "events" in statement:
                    os._exit(9)      # dies inside the transaction of the migration, after some tables were created
            sqlite_storage.SqliteStorage(sys.argv[2], hook=hook)
        """)
        result = subprocess.run([sys.executable, "-I", "-c", code, str(HERE / "src"), str(self.db)], capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 9)
        con = sqlite3.connect(str(self.db))
        try:
            names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            con.close()
        self.assertFalse({"accounts", "configs", "events"} & names, names)      # nothing of the schema survived, so there is nothing half done to repair
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        self.assertEqual(s.schema_version(), 1)
        self.assertEqual(s.verify(), [])

    def test_a_database_of_a_newer_version_is_refused_and_left_alone(self):
        later = dict(sqlite_storage.MIGRATIONS)
        later[2] = ["CREATE TABLE future (x TEXT)"]
        sqlite_storage.SqliteStorage(self.db, migrations=later).close()
        with self.assertRaises(base.StorageError):
            sqlite_storage.SqliteStorage(self.db)
        self.assertIn("future", self.tables())

    def test_verify_finds_a_row_that_is_not_json(self):
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        s.save_config("alpha", {"a": 1})
        s._conn().execute("UPDATE configs SET data = 'oops'")
        self.assertTrue(any("not JSON" in p for p in s.verify()))
        self.assertEqual(s.load_config("alpha"), {})      # and a damaged row reads as empty, like a damaged file

    def test_a_failed_write_is_rolled_back_whole(self):
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        s.append_event("alpha", {"at": NEW, "kind": "k"})
        with self.assertRaises(TypeError):
            s.append_events("alpha", [{"at": NEW, "kind": "good"}, {"at": NEW, "kind": "bad", "x": object()}])
        self.assertEqual([e["kind"] for e in s.load_events("alpha", None, 10)], ["k"])

    def test_the_raw_backup_is_a_consistent_database(self):
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        s.save_config("alpha", {"a": 1})
        s.append_event("alpha", {"at": NEW, "kind": "k"})
        copy = Path(self.tmp.name) / "copy.sqlite3"
        self.assertGreater(s.backup_file(copy), 0)
        other = sqlite_storage.SqliteStorage(copy)
        self.addCleanup(other.close)
        self.assertEqual((other.load_config("alpha"), len(other.load_events("alpha", None, 10)), other.verify()), ({"a": 1}, 1, []))

    def test_the_documents_of_the_account_and_the_feed_can_be_moved_between_backends(self):
        files = file_storage.FileStorage(Path(self.tmp.name) / "acc", "accounts")
        files.save_config("alpha", {"a": 1})
        files.save_sentinel_state("alpha", "collab_state", {"b": 2})
        files.append_events("alpha", [{"at": NEW, "kind": "k", "args": {"n": 1}}])
        s = sqlite_storage.SqliteStorage(self.db)
        self.addCleanup(s.close)
        s.import_account("alpha", files.export_account("alpha"))
        self.assertEqual(s.export_account("alpha"), files.export_account("alpha"))


class Retry(unittest.TestCase):
    def test_a_busy_step_is_tried_again_with_a_bounded_number_of_attempts(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise sqlite3.OperationalError("database is locked")
            return "ok"

        with mock.patch.object(sqlite_storage.time, "sleep") as pause:
            self.assertEqual(sqlite_storage.retrying(flaky), "ok")
        self.assertEqual((len(calls), pause.call_count), (3, 2))
        calls.clear()
        with mock.patch.object(sqlite_storage.time, "sleep"):
            with self.assertRaises(sqlite3.OperationalError):
                sqlite_storage.retrying(lambda: (calls.append(1), (_ for _ in ()).throw(sqlite3.OperationalError("database is busy")))[1], attempts=4)
        self.assertEqual(len(calls), 4)

    def test_another_error_is_not_retried(self):
        calls = []
        with mock.patch.object(sqlite_storage.time, "sleep") as pause:
            with self.assertRaises(sqlite3.OperationalError):
                sqlite_storage.retrying(lambda: (calls.append(1), (_ for _ in ()).throw(sqlite3.OperationalError("no such table")))[1])
        self.assertEqual((len(calls), pause.call_count), (1, 0))

    def test_the_wait_is_configurable_and_clamped(self):
        self.assertEqual(factory.settings({"busy_timeout_ms": 60000})["busy_timeout_ms"], 60000)
        for bad in (5, 10 ** 9, "x", True, None):
            self.assertEqual(factory.settings({"busy_timeout_ms": bad})["busy_timeout_ms"], 30000)
        with tempfile.TemporaryDirectory() as tmp:
            s = factory.create_storage({"backend": "sqlite", "busy_timeout_ms": 45000}, None, base_dir=Path(tmp))
            try:
                self.assertEqual(s.describe()["busy_timeout_ms"], 45000)
            finally:
                s.close()


class Factory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_sqlite_is_one_file_per_account_by_default(self):
        (self.root / "accounts" / "alpha").mkdir(parents=True)
        (self.root / "accounts" / "alpha" / "actions_monitor.json").write_text("{}", encoding="utf-8")
        s = factory.create_storage({"backend": "sqlite"}, "alpha", base_dir=self.root)
        self.addCleanup(s.close)
        self.assertEqual(s.path, self.root / "accounts" / "alpha" / "storage.sqlite3")

    def test_a_path_is_one_shared_file(self):
        s = factory.create_storage({"backend": "sqlite", "path": str(self.root / "shared" / "all.db")}, "alpha", base_dir=self.root)
        self.addCleanup(s.close)
        self.assertEqual(s.path, self.root / "shared" / "all.db")

    def test_a_single_installation_keeps_its_database_next_to_the_launchers(self):
        s = factory.create_storage({"backend": "sqlite"}, None, base_dir=self.root)
        self.addCleanup(s.close)
        self.assertEqual(s.path, self.root / "storage.sqlite3")

    def test_the_global_records_have_a_storage_of_their_own(self):
        files = factory.create_global_storage(None, base_dir=self.root)
        self.assertEqual((files.backend, files.root), ("file", self.root / "accounts"))
        sql = factory.create_global_storage({"backend": "sqlite"}, base_dir=self.root)
        self.addCleanup(sql.close)
        self.assertEqual(sql.path, self.root / "accounts" / "_global" / "storage.sqlite3")
        sql.put_record("users", "ana", {"role": "admin"})
        self.assertEqual(sql.get_record("users", "ana"), {"role": "admin"})
        self.assertEqual(factory.create_global_storage({"backend": "sqlite"}, lite=True, base_dir=self.root).backend, "file")

    def test_lite_never_creates_a_database(self):
        s = factory.create_storage({"backend": "sqlite"}, None, lite=True, base_dir=self.root)
        self.assertEqual(s.backend, "file")
        self.assertEqual(list(self.root.glob("*.sqlite3*")), [])


CHILD = textwrap.dedent("""
    import json, sys, time
    sys.path.insert(0, sys.argv[1])
    from github_actions_monitor.storage import factory, sqlite_storage, file_storage
    kind, target, account = sys.argv[2], sys.argv[3], sys.argv[4]
    s = sqlite_storage.SqliteStorage(target) if kind == "sqlite" else file_storage.FileStorage(target, "accounts")
    i = 0
    while True:
        i += 1
        s.append_event(account, {"kind": "tick", "n": i, "pad": "x" * 200})
        s.save_sentinel_state(account, "sentinel_cache", {"n": i, "pad": "y" * 5000})
        print(i, flush=True)      # written AFTER the commit: a number the parent saw is a number that must survive
""")


class Crash(unittest.TestCase):
    """kill -9 (Windows: TerminateProcess) of the process that writes, while it writes."""

    def run_case(self, kind):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "storage.sqlite3") if kind == "sqlite" else str(Path(tmp) / "accounts")
            proc = subprocess.Popen([sys.executable, "-I", "-c", CHILD, str(HERE / "src"), kind, target, "alpha"], stdout=subprocess.PIPE, text=True)
            acked = 0
            deadline = time.time() + 30
            try:
                while acked < 40 and time.time() < deadline:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    acked = int(line)
            finally:
                proc.kill()      # SIGKILL on POSIX, TerminateProcess on Windows: no chance to clean up
                proc.wait(timeout=30)
                proc.stdout.close()
            self.assertGreaterEqual(acked, 40, "the child did not get going")
            s = sqlite_storage.SqliteStorage(target) if kind == "sqlite" else file_storage.FileStorage(target, "accounts")
            try:
                events = s.load_events("alpha", None, None)
                numbers = [e["n"] for e in events]
                self.assertEqual(numbers, list(range(1, len(numbers) + 1)), "events are missing or out of order")
                self.assertGreaterEqual(len(numbers), acked)      # everything the child reported done is there
                state = s.load_sentinel_state("alpha", "sentinel_cache")
                self.assertTrue(state == {} or (state["pad"] == "y" * 5000 and state["n"] >= acked - 1), "the state is half written")
                self.assertEqual(s.verify(), [])
                s.append_event("alpha", {"kind": "after"})      # and the storage is usable
                self.assertEqual(s.load_events("alpha", None, 1)[0]["kind"], "after")
            finally:
                s.close()

    def test_sqlite_recovers_after_the_writer_is_killed(self):
        self.run_case("sqlite")

    def test_files_recover_after_the_writer_is_killed(self):
        self.run_case("file")


TICKER = textwrap.dedent("""
    import sys
    sys.path.insert(0, sys.argv[1])
    from github_actions_monitor.storage import sqlite_storage
    path, account, count, gate = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    import os, time
    deadline = time.time() + 60
    while not os.path.exists(gate) and time.time() < deadline:      # every process opens the database at the same moment: the start is a file, not a guess
        time.sleep(0.001)
    s = sqlite_storage.SqliteStorage(path)
    for i in range(count):
        s.append_events(account, [{"kind": "tick", "n": i, "who": account}])
        s.save_sentinel_state(account, "sentinel_cache", {"n": i})
        s.save_analytics(account, {"daily": {}, "n": i})
    s.close()
""")


def spawn_tickers(shared_or_paths, count, gate):
    """Starts one ticking process per (account, database path), all waiting at the gate file."""
    return [subprocess.Popen([sys.executable, "-I", "-c", TICKER, str(HERE / "src"), str(path), name, str(count), str(gate)]) for name, path in shared_or_paths.items()]


class TwoAccounts(unittest.TestCase):
    """Model A: each account has its own database and its own process; model B: one shared database. In both, two accounts ticking at once corrupt nothing."""

    def tick_together(self, paths):
        gate = Path(next(iter(paths.values()))).parent / "gate"
        gate.parent.mkdir(parents=True, exist_ok=True)
        procs = spawn_tickers(paths, 150, gate)
        gate.write_text("go", encoding="utf-8")
        for proc in procs:
            self.assertEqual(proc.wait(timeout=180), 0)

    def test_model_a_two_accounts_two_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {"alpha": Path(tmp) / "alpha" / "storage.sqlite3", "beta": Path(tmp) / "beta" / "storage.sqlite3"}
            self.tick_together(paths)
            for name, path in paths.items():
                s = sqlite_storage.SqliteStorage(path)
                try:
                    self.assertEqual([e["n"] for e in s.load_events(name, None, None)], list(range(150)))
                    self.assertEqual(s.load_sentinel_state(name, "sentinel_cache"), {"n": 149})
                    self.assertEqual(s.verify(), [])
                finally:
                    s.close()

    def test_model_b_two_accounts_one_shared_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "shared.sqlite3"
            self.tick_together({"alpha": shared, "beta": shared})
            s = sqlite_storage.SqliteStorage(shared)
            try:
                for name in ("alpha", "beta"):
                    self.assertEqual([e["n"] for e in s.load_events(name, None, None)], list(range(150)), name)
                    self.assertEqual(s.load_sentinel_state(name, "sentinel_cache"), {"n": 149})
                self.assertEqual(s.list_accounts(), ["alpha", "beta"])
                self.assertEqual(s.verify(), [])
            finally:
                s.close()

    def test_model_b_reading_over_http_style_while_the_ticks_write_never_waits_long(self):
        """The page reads (load_events, list) from its own thread while the sentinels of other processes write: with WAL no read waits for a writer."""
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "shared.sqlite3"
            s = sqlite_storage.SqliteStorage(shared)
            self.assertEqual(s.describe()["journal_mode"], "wal")
            gate = Path(tmp) / "gate"
            procs = spawn_tickers({"alpha": shared, "beta": shared}, 300, gate)
            gate.write_text("go", encoding="utf-8")
            slowest, reads, last = 0.0, 0, 0
            try:
                while any(p.poll() is None for p in procs):
                    start = time.perf_counter()
                    rows = s.load_events("alpha", None, 20)
                    s.list_accounts()
                    slowest = max(slowest, time.perf_counter() - start)
                    reads += 1
                    if rows:
                        self.assertGreaterEqual(rows[-1]["n"], last)      # what a reader sees only moves forward
                        last = rows[-1]["n"]
            finally:
                for p in procs:
                    self.assertEqual(p.wait(timeout=180), 0)
                s.close()
            self.assertGreater(reads, 3)
            self.assertLess(slowest, 2.0, "a read waited for a writer")

    def test_model_b_the_page_answers_over_http_while_two_processes_tick(self):
        """A real HTTP server (the page of one process) reads the shared database for every request while two other processes write their ticks: every answer is complete and prompt."""
        import http.server
        import urllib.request
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "shared.sqlite3"
            store = sqlite_storage.SqliteStorage(shared)

            class Page(http.server.BaseHTTPRequestHandler):
                def do_GET(self):      # what an endpoint of the page does: read the feed of an account and the list of accounts
                    body = json.dumps({"events": store.load_events("alpha", None, 20), "accounts": store.list_accounts(), "state": store.load_sentinel_state("beta", "sentinel_cache")}).encode()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, *args):
                    pass

            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Page)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            gate = Path(tmp) / "gate"
            procs = spawn_tickers({"alpha": shared, "beta": shared}, 300, gate)
            gate.write_text("go", encoding="utf-8")
            slowest, answers = 0.0, 0
            try:
                while any(p.poll() is None for p in procs):
                    start = time.perf_counter()
                    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/", timeout=10) as answer:
                        document = json.loads(answer.read())
                    slowest = max(slowest, time.perf_counter() - start)
                    answers += 1
                    self.assertTrue(all(e["kind"] == "tick" and e["who"] == "alpha" for e in document["events"]))
            finally:
                for p in procs:
                    self.assertEqual(p.wait(timeout=180), 0)
                server.shutdown()
                server.server_close()
                store.close()
            self.assertGreater(answers, 3)
            self.assertLess(slowest, 3.0, "a request of the page waited for a writer")

    def test_several_threads_in_one_process_share_one_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = sqlite_storage.SqliteStorage(Path(tmp) / "s.sqlite3")
            errors = []

            def work(n):
                try:
                    for i in range(60):
                        s.append_event("alpha", {"kind": "t", "n": n, "i": i})
                        s.load_events("alpha", None, 5)
                except Exception as error:  # noqa: BLE001
                    errors.append(error)

            threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            try:
                self.assertEqual(errors, [])
                self.assertEqual(len(s.load_events("alpha", None, None)), 240)
            finally:
                s.close()


if __name__ == "__main__":
    unittest.main()
