# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Everything the monitor says is a signal for an AI tool: the inventory covers every tile, tab and panel of the page, the endpoint, the brief and the MCP tools agree, and both editions share the channels."""
import json
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import ai_alerts  # noqa: E402
import i18n  # noqa: E402
import sentinel_panels  # noqa: E402
import signals  # noqa: E402
from test_177_panels import snapshot  # noqa: E402

PAGE = (HERE / "actions_monitor.html").read_text(encoding="utf-8")


def data():
    return {"updated": "2026-01-01T10:00:00Z", "refresh_seconds": 120, "mode": "full", "figures": {"active": 2, "queued": 1, "fail24": 3, "ok24": 20}, "rate": {"remaining": 4000, "limit": 5000, "reset": "2026-01-01T11:00:00Z"},
            "active": [{"repo": "demo-a", "name": "Build", "status": "in_progress", "seconds": 9000, "stuck": True, "url": "u"}],
            "failing": [{"repo": "demo-b", "name": "CI", "conclusion": "failure", "started": "2026-01-01T09:00:00Z", "url": "https://github.com/o/demo-b/actions/runs/1"}],
            "issues": [{"repo": "demo-b", "number": 4, "title": "Build failed", "created": "2026-01-01T09:30:00Z", "url": "i"}], "errors": {"demo-c": "gh: timeout"}, "offline": {"offline": False}}


class Coverage(unittest.TestCase):
    def test_every_tile_and_tab_of_the_page_is_in_the_inventory_or_marked_decorative(self):
        tiles = set(re.findall(r'id="(k[tp]-[a-z0-9-]+)"', PAGE))
        tabs = set(re.findall(r'id="n-([a-z]+)"', PAGE))
        self.assertTrue(len(tiles) >= 14 and len(tabs) >= 7, (tiles, tabs))
        for tile in tiles:
            self.assertIn("tile:" + tile, signals.COVERAGE, f"the tile {tile} says nothing to an AI tool: add it to signals.COVERAGE (a signal, or decorative with the reason)")
        for tab in tabs:
            self.assertIn("tab:" + tab, signals.COVERAGE, tab)

    def test_the_covered_signals_exist(self):
        doc = signals.state(data(), sentinel_panels.panels(snapshot(), i18n.t, analytics={"enabled": True, "slower": [], "duration": [1], "flaky": []}, collab=[], owner="o"), "complete")
        ids = {s["id"] for s in doc["signals"]}
        for element, target in signals.COVERAGE.items():
            if target.startswith("decorative"):
                self.assertGreater(len(target), 14, element)      # the reason is written
            elif target.endswith(".*"):
                self.assertTrue([i for i in ids if i.startswith(target[:-1])], target)
            else:
                self.assertIn(target, ids, element)
        for panel in sentinel_panels.ORDER:
            self.assertIn("sentinel." + panel, ids)
        for sig in doc["signals"]:
            self.assertIn(sig["level"], signals.LEVELS)

    def test_a_signal_has_a_summary_and_rows_with_a_next_step(self):
        doc = signals.state(data(), [], "complete")
        by = {s["id"]: s for s in doc["signals"]}
        self.assertEqual(by["alerts.unresolved"]["level"], "act")
        self.assertTrue(by["alerts.unresolved"]["rows"][0]["next"])
        self.assertIsInstance(by["alerts.unresolved"]["rows"][0]["age_seconds"], int)
        self.assertEqual(by["now.runs"]["level"], "act")      # a stuck run
        self.assertTrue(by["repos.errors"]["transient"])
        self.assertEqual(doc["schema"], signals.SCHEMA)
        self.assertGreaterEqual(doc["act"], 3)


class Editions(unittest.TestCase):
    def test_the_state_says_the_edition_and_what_does_not_exist_in_lite(self):
        lite = signals.state(data(), [], "lite")
        full = signals.state(data(), sentinel_panels.panels(snapshot(), i18n.t, owner="o"), "complete")
        self.assertEqual(lite["edition"], "lite")
        self.assertIn("a3", lite["panels_not_in_this_edition"])
        self.assertTrue(lite["note"])
        self.assertEqual(full["panels_not_in_this_edition"], [])
        self.assertEqual({s["id"] for s in lite["signals"]} & {s["id"] for s in full["signals"]} >= {"now.runs", "alerts.unresolved", "quota", "connection", "health.refresh"}, True)

    def test_the_channels_are_shared_by_both_editions(self):
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        for path in ("/api/ai/state", "/api/ai/stream", "/api/ai/brief", "/api/ai/alerts"):
            self.assertIn(f'"{path}"', source.split("LITE_SHARED = (")[1].split(")")[0], path)
        self.assertEqual(source.count('path not in LITE_SHARED'), 2)
        body = source.split("def feed_alerts(")[1].split("def maintain_extras")[0]
        self.assertNotIn('if LITE["on"]', body)      # the feed is written by the lite edition too

    def test_a_running_monitor_answers_in_both_editions(self):
        for flavor in ("--lite", None):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            args = [sys.executable, "-I", str(HERE.parent / "tools" / "demo_monitor.py"), str(port)] + ([flavor] if flavor else [])
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(80):
                    try:
                        socket.create_connection(("127.0.0.1", port), 0.5).close()
                        break
                    except OSError:
                        time.sleep(0.5)
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ai/state", timeout=20) as answer:
                    doc = json.load(answer)
                self.assertEqual(doc["edition"], "lite" if flavor else "complete")
                self.assertEqual(bool(doc["panels_not_in_this_edition"]), bool(flavor))
                self.assertIn("alerts.unresolved", [s["id"] for s in doc["signals"]])
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ai/alerts", timeout=20) as answer:
                    self.assertIn(answer.status, (200,))
            finally:
                proc.terminate()
                proc.wait(10)


class Brief(unittest.TestCase):
    def test_the_brief_has_what_to_do_now_pending_and_health_and_the_counter(self):
        doc = signals.state(data(), [], "lite")
        text = signals.brief_sections(doc)
        for head in ("## What to do now", "## Pending", "## Monitor health"):
            self.assertIn(head, text)
        self.assertIn("demo-b: CI: failure", text)
        self.assertIn(f"signals to act on: {doc['act']}", text)
        self.assertIn("edition: lite", text)
        with tempfile.TemporaryDirectory() as tmp:
            config = {"ai_alerts": {"enabled": True, "folder": tmp}}
            ai_alerts.update(config, [], panels=None, sections=text)
            brief = (Path(tmp) / ai_alerts.BRIEF).read_text(encoding="utf-8")
            self.assertIn("## What to do now", brief)
            self.assertIn("signals to act on", brief)

    def test_the_mcp_tools_read_the_same_state(self):
        import mcp_server
        names = [t["name"] for t in mcp_server.TOOLS]
        for tool in ("monitor_state", "signals", "diagnose", "act"):
            self.assertIn(tool, names)
        doc = signals.state(data(), [], "complete")
        full = json.loads(mcp_server.call("monitor_state", {}, {}, getter=lambda path: doc))
        self.assertEqual(full["edition"], "complete")
        only = json.loads(mcp_server.call("signals", {"panel": "alerts", "only_act": True}, {}, getter=lambda path: doc))
        self.assertTrue(only["signals"])
        self.assertTrue(all(s["level"] == "act" and s["panel"] == "alerts" for s in only["signals"]))
        with self.assertRaises(ValueError):
            mcp_server.call("act", {"id": "x"}, {}, allow_ack=False)


if __name__ == "__main__":
    unittest.main()
