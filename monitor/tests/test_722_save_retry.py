# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The shared files of the monitor are saved again when two processes write at the same time on Windows: the temporary file has a name of its own and a refused replace is tried again."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.security import private_io
from github_actions_monitor.storage import state_io


class SaveRetry(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "state.json"
        patcher = mock.patch.object(private_io, "REPLACE_FIRST_WAIT", 0.0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _refusing(self, times, error=PermissionError):
        real = os.replace
        state = {"left": times, "calls": 0}

        def replace(src, dst):
            state["calls"] += 1
            if state["left"] > 0:
                state["left"] -= 1
                raise error(13, "refused")
            return real(src, dst)
        return replace, state

    def test_a_refused_replace_is_tried_again_and_the_file_is_saved(self):
        for error in (PermissionError, FileNotFoundError):
            with self.subTest(error=error.__name__):
                replace, state = self._refusing(3, error)
                with mock.patch.object(os, "replace", replace):
                    state_io.save_text(self.path, json.dumps({"count": 7}))
                self.assertEqual(state["calls"], 4)
                self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"count": 7})
                self.assertEqual([p.name for p in self.path.parent.iterdir()], ["state.json"])

    def test_a_replace_that_never_works_raises_and_leaves_no_temporary_file(self):
        replace, _ = self._refusing(10 ** 6)
        with mock.patch.object(os, "replace", replace), mock.patch.object(private_io, "REPLACE_RETRY_SECONDS", 0.05):
            with self.assertRaises(OSError):
                state_io.save_text(self.path, "{}")
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_every_writer_has_a_temporary_file_of_its_own(self):
        names = {private_io.unique_tmp(self.path).name for _ in range(50)}
        seen = []
        thread = threading.Thread(target=lambda: seen.append(private_io.unique_tmp(self.path).name))
        thread.start()
        thread.join()
        self.assertEqual(len(names), 50)
        self.assertNotIn(seen[0], names)
        self.assertTrue(all(n.endswith(".tmp") and n.startswith("state.json.") for n in names))

    def test_a_read_refused_while_another_process_replaces_the_file_is_tried_again(self):
        self.path.write_text('{"count": 3}', encoding="utf-8")
        real = Path.read_text
        state = {"left": 3}

        def read_text(self_path, *args, **kwargs):
            if state["left"] > 0:
                state["left"] -= 1
                raise PermissionError(13, "refused")
            return real(self_path, *args, **kwargs)
        with mock.patch.object(Path, "read_text", read_text):
            self.assertEqual(state_io.load_json(self.path), {"count": 3})
        self.assertEqual(state["left"], 0)
        with self.assertRaises(FileNotFoundError):
            state_io.load_json(self.path.with_name("missing.json"))

    def test_the_store_waits_for_a_file_it_knew_that_another_process_is_replacing(self):
        from github_actions_monitor.sentinels import sentinel_ai
        self.path.write_text(json.dumps({"day": sentinel_ai.Store.today(), "count": 4, "entries": {}}), encoding="utf-8")
        store = sentinel_ai.Store(self.path)
        real = state_io.load_json
        state = {"left": 3}

        def load_json(path):
            if state["left"] > 0:
                state["left"] -= 1
                raise FileNotFoundError(str(path))
            return real(path)
        with mock.patch.object(state_io, "load_json", load_json):
            store.sync()
        self.assertEqual((state["left"], store.data["count"]), (0, 4))
        fresh = sentinel_ai.Store(Path(self.folder.name) / "never.json")      # a file that never existed is not waited for
        with mock.patch.object(state_io, "load_json", side_effect=FileNotFoundError("x")) as load:
            fresh.sync()
        self.assertEqual(load.call_count, 1)

    def test_the_answer_saved_after_a_call_does_not_erase_what_another_process_counted_meanwhile(self):
        from github_actions_monitor.sentinels import sentinel_ai as ai
        cfg = ai.ai_config({"ai": {"provider": "openai-compatible", "base_url": "http://127.0.0.1:1/v1", "model": "m", "daily_limit": 50, "model_daily_limit": 9, "skill": False}})
        from github_actions_monitor.sentinels import ai_chain
        mine, other = ai.Store(self.path), ai.Store(self.path)
        real = ai_chain.add_model_usage

        def usage_then_other_process_counts(*args, **kwargs):
            real(*args, **kwargs)
            with other.exclusive():      # the other process counts a call between the usage and the saving of the answer
                other.add_call()
        with mock.patch.object(ai_chain, "add_model_usage", usage_then_other_process_counts):
            ai.explain("build", "log one", cfg, mine, transport=lambda c, s, u: "answer")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["count"], 2)

    def test_the_store_of_the_ai_keeps_its_data_and_says_so_when_the_save_fails(self):
        from github_actions_monitor.sentinels import sentinel_ai
        store = sentinel_ai.Store(self.path)
        store.data["count"] = 5
        with mock.patch.object(state_io, "save_text", side_effect=PermissionError(13, "refused")):
            with self.assertLogs("github_actions_monitor.sentinel_ai", level="WARNING"):
                store.save()
        self.assertEqual(store.data["count"], 5)
        store.save()
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["count"], 5)


if __name__ == "__main__":
    unittest.main()
