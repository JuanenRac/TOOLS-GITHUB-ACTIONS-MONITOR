# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The live events as a read-only stream (server-sent events): off by default, limited listeners, resume, a closed list of fields, a real server."""
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402


def event(n):
    return {"event": "workflow_run", "repo": f"o/r{n}", "status": "completed", "conclusion": "failure", "at": "t", "secret_body": "never"}


class Frames(unittest.TestCase):
    def gen(self, events, total=None, **kw):
        clock = {"t": 0.0}
        box = {"total": len(events) if total is None else total, "events": list(events)}

        def sleep(seconds):
            clock["t"] += seconds
        config = {"live": {"sse": {"enabled": True, "max_seconds": 60}}}
        return webhook.sse_frames(config, lambda: (box["total"], list(box["events"])), clock=lambda: clock["t"], sleep=sleep, **kw), box

    def test_hello_then_new_events_with_running_ids_then_bye(self):
        gen, box = self.gen([event(1)])
        hello = next(gen)
        self.assertTrue(hello.startswith("event: hello"))
        self.assertEqual(json.loads(hello.split("data: ")[1]), {"held": 1, "total": 1})
        box["events"].append(event(2))
        box["total"] = 2
        frame = next(gen)
        self.assertTrue(frame.startswith("id: 2\nevent: live"))
        data = json.loads(frame.split("data: ")[1])
        self.assertEqual(data["repo"], "o/r2")
        self.assertNotIn("secret_body", data, "only the closed list of fields")
        rest = list(gen)
        self.assertTrue(rest[-1].startswith("event: bye"))
        self.assertTrue(any(f.startswith(": keepalive") for f in rest))

    def test_resume_sends_what_is_still_held_and_never_more(self):
        gen, _ = self.gen([event(i) for i in range(3, 6)], total=5, since=2)
        next(gen)
        ids = [f.split("\n")[0] for f in gen if f.startswith("id:")]
        self.assertEqual(ids, ["id: 3", "id: 4", "id: 5"])
        gen, _ = self.gen([event(1)], total=1, since=99)      # a number from the future is clamped
        next(gen)
        self.assertFalse([f for f in gen if f.startswith("id:")])

    def test_settings_are_off_bounded_and_listeners_released(self):
        self.assertFalse(webhook.sse_settings({})["enabled"])
        self.assertEqual(webhook.sse_settings({"live": {"sse": {"enabled": "yes", "max_clients": 0, "max_seconds": True}}}), {"enabled": False, "max_seconds": 3600, "max_clients": 3})
        config = {"live": {"sse": {"enabled": True, "max_clients": 1}}}
        self.assertTrue(webhook.sse_acquire(config))
        self.assertFalse(webhook.sse_acquire(config))
        webhook.sse_release()
        webhook.sse_release()
        self.assertEqual(webhook.SSE_STREAMS[0], 0)

    def test_stop_ends_the_stream(self):
        gen, _ = self.gen([])
        next(gen)
        stop = {"v": True}
        gen2 = webhook.sse_frames({"live": {"sse": {"enabled": True}}}, lambda: (0, []), stop=lambda: stop["v"])
        next(gen2)
        self.assertIn("stopped", next(gen2))


class Wiring(unittest.TestCase):
    def test_the_three_settings_are_in_the_schema_and_the_defaults(self):
        keys = {row[2] for row in settings_api.ROWS}
        for key in ("live.sse.enabled", "live.sse.max_seconds", "live.sse.max_clients"):
            self.assertIn(key, keys)
        self.assertEqual(actions_monitor.DEFAULTS["live"]["sse"], {"enabled": False, "max_seconds": 3600, "max_clients": 3})
        self.assertTrue(settings_api.META["live.sse.enabled"]["secure"])

    def test_the_lite_edition_does_not_have_it(self):
        self.assertTrue(any("/api/live-events/stream".startswith(p) for p in actions_monitor.LITE_PATHS))


class RealServer(unittest.TestCase):
    def serve(self, config):
        server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for p in (mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config), mock.patch.object(actions_monitor, "LITE", {"on": False})):
            p.start()
            self.addCleanup(p.stop)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_off_by_default_then_limited_and_streams_an_accepted_event(self):
        base = self.serve({})
        with self.assertRaises(urllib.error.HTTPError) as off:
            urllib.request.urlopen(base + "/api/live-events/stream", timeout=10)
        self.assertEqual(off.exception.code, 404)
        base = self.serve({"live": {"sse": {"enabled": True, "max_clients": 1}}})
        answer = urllib.request.urlopen(base + "/api/live-events/stream", timeout=10)
        self.assertIn("text/event-stream", answer.headers["Content-Type"])
        self.assertTrue(answer.readline().decode().startswith("event: hello"))
        with self.assertRaises(urllib.error.HTTPError) as full:
            urllib.request.urlopen(base + "/api/live-events/stream", timeout=10)
        self.assertEqual(full.exception.code, 429)
        before = actions_monitor.LIVE_TOTAL[0]
        with mock.patch.object(actions_monitor, "RUN_CACHE", {}), mock.patch.object(actions_monitor, "HOT_FORCED", set()):
            actions_monitor.LIVE_EVENTS.append({"event": "workflow_run", "repo": "o/pushed", "status": "completed", "conclusion": "success", "at": "t"})
            actions_monitor.LIVE_TOTAL[0] += 1
        self.addCleanup(lambda: (actions_monitor.LIVE_EVENTS.pop(), actions_monitor.LIVE_TOTAL.__setitem__(0, before)))
        seen = ""
        for _ in range(20):
            line = answer.readline().decode()
            seen += line
            if "o/pushed" in line:
                break
        self.assertIn('"repo": "o/pushed"', seen)
        answer.close()


if __name__ == "__main__":
    unittest.main()
