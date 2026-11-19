# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The progress of an update as server-sent events (GET /api/updates/stream): the frames, the limit of listeners, the route over HTTP and the page that falls back to asking."""
import json
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.ops import updates
from github_actions_monitor.security import auth

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


def parse(frames):
    out = []
    for frame in frames:
        if frame.startswith(":"):
            out.append(("comment", None))
            continue
        lines = dict(line.split(": ", 1) for line in frame.strip().split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


class Frames(unittest.TestCase):
    def test_hello_then_a_frame_per_change_then_bye_when_it_is_over(self):
        states = iter([{"running": True, "step": "backup"}, {"running": True, "step": "backup"}, {"running": True, "step": "copy"}, {"running": False, "report": {"ok": True}}])
        got = parse(updates.stream_frames(read=lambda: next(states), sleep=lambda s: None, clock=iter(range(0, 1000)).__next__))
        self.assertEqual([k for k, _ in got], ["hello", "progress", "progress", "progress", "bye"])
        self.assertEqual(got[2][1]["step"], "copy")
        self.assertEqual(got[-1][1]["reason"], "done")

    def test_a_listener_is_let_go_after_the_time_and_when_the_caller_stops(self):
        ticks = iter(range(0, 10000))
        got = parse(updates.stream_frames(read=lambda: {"running": True}, sleep=lambda s: None, clock=lambda: next(ticks), max_seconds=40, keepalive=10))
        self.assertEqual(got[-1], ("bye", {"reason": "time"}))
        self.assertIn(("comment", None), got)
        got = parse(updates.stream_frames(read=lambda: {"running": True}, sleep=lambda s: None, stop=lambda: True))
        self.assertEqual([k for k, _ in got], ["hello", "bye"])
        self.assertEqual(got[-1][1]["reason"], "stopped")

    def test_nothing_running_answers_at_once_and_closes(self):
        got = parse(updates.stream_frames(read=lambda: {"running": False}, sleep=lambda s: self.fail("it must not wait")))
        self.assertEqual([k for k, _ in got], ["hello", "progress", "bye"])

    def test_only_two_listeners(self):
        self.assertTrue(updates.stream_acquire())
        self.assertTrue(updates.stream_acquire())
        try:
            self.assertFalse(updates.stream_acquire())
        finally:
            updates.stream_release()
            updates.stream_release()
        self.assertTrue(updates.stream_acquire())
        updates.stream_release()


class Route(unittest.TestCase):
    def setUp(self):
        _testenv.guard(self)

    def test_the_stream_answers_over_http_and_is_read_only(self):
        from test_164 import LiveServer
        server = LiveServer({})
        server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        answer = urllib.request.urlopen(server.base + "/api/updates/stream", timeout=10)
        self.assertIn("text/event-stream", answer.headers["Content-Type"])
        body = answer.read().decode("utf-8")
        events = [line[7:] for line in body.splitlines() if line.startswith("event: ")]
        self.assertEqual(events, ["hello", "progress", "bye"])
        self.assertEqual(auth.required_role("GET", "/api/updates/stream"), "viewer")
        with mock.patch.object(updates, "stream_acquire", return_value=False):
            with self.assertRaises(urllib.error.HTTPError) as full:
                urllib.request.urlopen(server.base + "/api/updates/stream", timeout=10)
            self.assertEqual(full.exception.code, 429)

    def test_the_stream_is_a_route_of_the_complete_edition_only(self):
        from github_actions_monitor.app import actions_monitor as am
        self.assertTrue(any("/api/updates/stream".startswith(p) for p in am.LITE_PATHS))


class Page(unittest.TestCase):
    def test_the_page_opens_the_stream_and_falls_back_to_asking(self):
        self.assertIn('new EventSource("/api/updates/stream")', PAGE)
        self.assertIn("typeof EventSource===\"undefined\"", PAGE)
        body = PAGE[PAGE.index("function updPoll()"):PAGE.index("async function updApply")]
        self.assertIn("setTimeout(async()=>{", body)      # the polling stays: it also covers the restart of the monitor
        self.assertIn("updStream()", body)


if __name__ == "__main__":
    unittest.main()
