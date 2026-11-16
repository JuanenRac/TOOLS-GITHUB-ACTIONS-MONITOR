# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Files in use and several writers (Windows): a file that cannot be read for a moment is not an empty file, and processes that append to the same feed lose no line."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.storage import file_storage
from github_actions_monitor.storage.file_storage import FileStorage, read_json

SRC = str(Path(__file__).resolve().parent.parent / "src")


class UnreadableIsNotEmpty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "doc.json"
        self.path.write_text('{"a": 1}', encoding="utf-8")
        patcher = mock.patch.object(file_storage.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_file_held_for_a_moment_is_read_again(self):
        real = Path.read_text
        calls = {"n": 0}

        def held(path, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise PermissionError(13, "in use")
            return real(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", held):
            self.assertEqual(read_json(self.path), {"a": 1})
        self.assertEqual(calls["n"], 3)

    def test_a_missing_file_is_nothing_at_once_and_a_damaged_one_too(self):
        self.assertEqual(read_json(self.path.with_name("nope.json"), dict, {"x": 1}, strict=True), {"x": 1})
        self.path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(read_json(self.path, strict=True))

    def test_a_file_that_stays_unreadable_is_default_for_a_reader_and_an_error_for_whoever_will_write(self):
        with mock.patch.object(Path, "read_text", side_effect=PermissionError(13, "in use")):
            self.assertEqual(read_json(self.path, dict, {"d": 1}), {"d": 1})
            with self.assertRaises(PermissionError):
                read_json(self.path, dict, {}, strict=True)

    def test_a_record_is_not_written_on_top_of_a_file_that_could_not_be_read(self):
        storage = FileStorage(self.tmp.name, "accounts")
        storage.put_record("users", "ana", {"role": "admin"})
        storage.put_record("users", "bob", {"role": "viewer"})
        before = storage._records_path("users").read_bytes()
        real = Path.read_text

        def held(path, *args, **kwargs):
            if Path(path) == storage._records_path("users"):
                raise PermissionError(13, "in use")
            return real(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", held):
            with self.assertRaises(PermissionError):
                storage.put_record("users", "luis", {"role": "viewer"})
        self.assertEqual(storage._records_path("users").read_bytes(), before)
        self.assertEqual(sorted(storage.list_records("users")), ["ana", "bob"])


WRITER = """
import sys
sys.path.insert(0, sys.argv[1])
from github_actions_monitor.storage.file_storage import FileStorage
storage = FileStorage(sys.argv[2], "accounts")
for i in range(int(sys.argv[4])):
    storage.append_events("alpha", [{"type": "t", "who": sys.argv[3], "i": i, "k": k} for k in range(3)])
"""


class SeveralWritersOneFeed(unittest.TestCase):
    def test_processes_that_append_to_the_same_feed_lose_and_cut_no_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileStorage(tmp, "accounts")
            storage.save_config("alpha", {"github_owner": "me"})
            procs = [subprocess.Popen([sys.executable, "-c", WRITER, SRC, tmp, f"p{n}", "60"], stderr=subprocess.PIPE) for n in range(4)]
            for proc in procs:
                _, err = proc.communicate(timeout=240)
                self.assertEqual(proc.returncode, 0, err.decode("utf-8", "replace")[-400:])
            text = storage.events_path("alpha").read_text(encoding="utf-8")
            lines = [line for line in text.splitlines() if line.strip()]
            good = [json.loads(line) for line in lines]
            self.assertEqual(len(good), 4 * 60 * 3)


if __name__ == "__main__":
    unittest.main()
