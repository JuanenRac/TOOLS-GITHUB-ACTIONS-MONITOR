# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Every live stream the monitor serves ends when the session that opened it is revoked or expires. The three streams of events (live events, alerts for AIs, progress of an update) must take the guard
of the handler, and a server of WebSockets may not appear without one: the only WebSocket the monitor has is the outgoing forwarder of GitHub's CLI (webhook.transport = websocket), which carries no
session of a person. Static checks on the source: they fail when a new stream forgets the guard."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "src" / "github_actions_monitor"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402


class Streams(unittest.TestCase):
    def source(self):
        return (SRC / "app" / "actions_monitor.py").read_text(encoding="utf-8")

    def test_every_event_stream_takes_the_guard(self):
        source = self.source()
        calls = re.findall(r"for frame in ([A-Za-z_.]+\.(?:sse_frames|stream_frames))\(([^\n]*)", source)
        self.assertGreaterEqual(len(calls), 3, "the three streams of the handler")
        for name, rest in calls:
            self.assertIn("stop=self.stream_guard()", rest, name + " does not end with its session")
        self.assertEqual({name for name, _rest in calls}, {"webhook.sse_frames", "ai_alerts.stream_frames", "updates.stream_frames"})

    def test_every_text_event_stream_route_is_one_of_those(self):
        self.assertEqual(self.source().count('"text/event-stream; charset=utf-8"'), 3)

    def test_no_server_of_websockets_without_a_guard(self):
        for path in sorted(SRC.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("Sec-WebSocket-Accept", text, str(path.name) + ": a WebSocket server needs the revalidation of the session (auth.stream_revalidate_min) before it is added")
            self.assertNotIn("258EAFA5-E914-47DA-95CA-C5AB0DC85B11", text, str(path.name))


if __name__ == "__main__":
    unittest.main()
