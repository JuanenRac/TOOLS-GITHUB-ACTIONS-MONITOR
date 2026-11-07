# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`finalize` (what it lists, what it runs and records, what it never does) and monitor_link (the note to the running monitor): offline, with fakes."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import _testenv  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gha_dispatch_all as gd  # noqa: E402
import monitor_link  # noqa: E402


class FakeAnswer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class MonitorLink(unittest.TestCase):
    def test_it_returns_the_port_that_accepts_and_sends_only_names_to_localhost(self):
        seen = []

        def opener(request, timeout):
            seen.append((request.full_url, request.data, request.get_method(), timeout))
            if ":8767/" not in request.full_url:
                raise OSError("closed")
            return FakeAnswer(b'{"ok": true}')

        self.assertEqual(monitor_link.notify_refresh(["B-REPO", "A-REPO", "A-REPO", ""], opener=opener), 8767)
        self.assertTrue(all(url.startswith("http://127.0.0.1:") and url.endswith(monitor_link.PATH) for url, *_ in seen))
        self.assertEqual(json.loads(seen[-1][1]), {"repos": ["A-REPO", "B-REPO"]})
        self.assertEqual(seen[-1][2], "POST")
        self.assertNotIn(b"token", seen[-1][1].lower())

    def test_nothing_to_say_or_nobody_listening_is_not_an_error(self):
        self.assertIsNone(monitor_link.notify_refresh([], opener=lambda *a, **k: self.fail("no request for an empty list")))
        self.assertIsNone(monitor_link.notify_refresh(["R"], opener=lambda *a, **k: (_ for _ in ()).throw(OSError("down"))))
        self.assertIsNone(monitor_link.notify_refresh(["R"], opener=lambda *a, **k: FakeAnswer(b'{"ok": false}')))
        self.assertIsNone(monitor_link.notify_refresh(["R"], opener=lambda *a, **k: FakeAnswer(b"not json")))

    def test_only_the_local_ports_are_tried(self):
        self.assertEqual(list(monitor_link.PORTS), list(range(8765, 8775)))


class Finalize(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "batch_1.json"
        self.name = next(n for n, t in gd.TARGETS.items() if not t.get("build_only") and ":" not in n)
        self.batch = {"dry_run": False, "targets": {self.name: {"run": 11, "sha_matched": True}}}
        self.path.write_text(json.dumps(self.batch), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_finalize(self, state, execute=False, answer="y", code=0):
        args = SimpleNamespace(json=False, execute=execute)
        out = io.StringIO()
        with mock.patch.object(gd, "last_batch", return_value=(self.path, json.loads(self.path.read_text(encoding="utf-8")))), \
                mock.patch.object(gd, "preflight", return_value=[]), mock.patch.object(gd, "run_state", return_value=state), \
                mock.patch("builtins.input", return_value=answer), mock.patch.object(gd.subprocess, "run", return_value=SimpleNamespace(returncode=code)) as run, \
                mock.patch.object(gd.monitor_link, "notify_refresh", return_value=8765) as notify, redirect_stdout(out):
            result = gd.cmd_finalize(args)
        return result, out.getvalue(), run, notify

    def test_a_ready_target_is_listed_with_its_exact_command_and_nothing_runs_without_execute(self):
        result, text, run, notify = self.run_finalize(("completed", "success", "https://example.invalid/run", []))
        self.assertEqual(result, 0)
        self.assertIn(self.name, text)
        self.assertIn("--run 11", text)
        run.assert_not_called()
        notify.assert_not_called()
        self.assertNotIn("signed_at", json.loads(self.path.read_text(encoding="utf-8"))["targets"][self.name])

    def test_a_target_that_is_not_green_is_not_offered(self):
        result, text, run, notify = self.run_finalize(("completed", "failure", "u", ["build"]), execute=True)
        self.assertEqual(result, 0)
        self.assertNotIn("--run 11", text)
        run.assert_not_called()

    def test_execute_asks_runs_records_and_tells_the_monitor(self):
        result, text, run, notify = self.run_finalize(("completed", "success", "u", []), execute=True)
        run.assert_called_once()
        notify.assert_called_once_with([gd.repo_of(self.name)])
        recorded = json.loads(self.path.read_text(encoding="utf-8"))["targets"][self.name]
        self.assertTrue(recorded["signed_at"].endswith("Z"))
        self.assertEqual(recorded["signed_at"], recorded["published_at"])

    def test_answering_no_runs_nothing(self):
        result, text, run, notify = self.run_finalize(("completed", "success", "u", []), execute=True, answer="n")
        run.assert_not_called()
        notify.assert_not_called()

    def test_a_failed_local_tool_records_nothing(self):
        result, text, run, notify = self.run_finalize(("completed", "success", "u", []), execute=True, code=1)
        notify.assert_not_called()
        self.assertNotIn("signed_at", json.loads(self.path.read_text(encoding="utf-8"))["targets"][self.name])

    def test_a_preflight_problem_stops_before_anything(self):
        out = io.StringIO()
        with mock.patch.object(gd, "last_batch", return_value=(self.path, self.batch)), mock.patch.object(gd, "preflight", return_value=["tool missing"]), \
                mock.patch.object(gd.subprocess, "run") as run, redirect_stdout(out):
            self.assertEqual(gd.cmd_finalize(SimpleNamespace(json=False, execute=True)), 2)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
