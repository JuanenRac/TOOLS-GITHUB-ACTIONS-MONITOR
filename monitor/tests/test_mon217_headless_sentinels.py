# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The sentinels run with no interface at all: in a fresh process that never imports the page, the web server or any module of the interface, every sentinel that is switched on starts its own thread, reads
through the reader it was given (never through a page) and completes a cycle, and its alerts can be read afterwards. If a sentinel ever needed an open tab to do its work, this fails."""
import json
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

SCRIPT = textwrap.dedent('''
    import json, sys, threading, time
    sys.path.insert(0, sys.argv[1])
    from github_actions_monitor.sentinels import sentinel_registry
    calls = []

    def gh(*args, **kwargs):
        calls.append(str(args[:1]))
        return {}
    names = ("ci", "collab", "security", "supply", "delivery")
    config = {"sentinels": {name: {"enabled": True} for name in names}}
    ctx = {"gh": gh, "run_gh": lambda *a, **k: (0, "{}", ""), "repos_fn": lambda: [], "runs_fn": lambda: [], "data_fn": lambda: {}, "eco_fn": lambda r: "x", "account_id": ""}
    registry = sentinel_registry.SentinelRegistry.build(ctx, config)
    registry.start()
    started = time.time()
    while time.time() - started < 20:
        if all(s.last_tick > 0 for n, s in registry.items.items() if n != "ci" and getattr(s, "enabled", True)):
            break
        time.sleep(0.2)
    out = {
        "ticked": sorted(n for n, s in registry.items.items() if s.last_tick > 0),
        "threads": sorted(t.name for t in threading.enumerate() if t.name.startswith("sentinel")),
        "status": {n: bool(s.get_status()) for n, s in registry.items.items()},
        "alerts_readable": isinstance(registry.alerts(), list),
        "metrics_readable": sorted(registry.metrics()),
        "reads": len(calls),
        "interface_modules": sorted(m for m in sys.modules if m.startswith("github_actions_monitor.ui") or m.startswith("github_actions_monitor.app.actions_monitor") or m in ("http.server", "socketserver", "wsgiref")),
    }
    registry.stop()
    print(json.dumps(out))
''')


class WithoutAnInterface(unittest.TestCase):
    def test_every_sentinel_that_is_on_runs_with_no_page_no_server_and_no_tab(self):
        done = subprocess.run([sys.executable, "-I", "-c", SCRIPT, str(HERE / "src")], capture_output=True, text=True, timeout=90, check=False)
        self.assertEqual(done.returncode, 0, done.stderr[-800:])
        out = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(out["ticked"], ["collab", "delivery", "security", "supply"])      # each one has completed a cycle by itself
        self.assertEqual(out["threads"], ["sentinel", "sentinel-collab", "sentinel-delivery", "sentinel-security", "sentinel-supply"])      # the CI sentinel has its own loop ("sentinel")
        self.assertTrue(all(out["status"].values()))
        self.assertTrue(out["alerts_readable"])
        self.assertEqual(out["metrics_readable"], ["ci", "collab", "delivery", "security", "supply"])
        self.assertGreater(out["reads"], 0)      # they read through the reader they were given
        self.assertEqual(out["interface_modules"], [], "a sentinel needs the interface to work")

    def test_the_switches_decide_what_runs_and_nothing_else_does(self):
        script = SCRIPT.replace('config = {"sentinels": {name: {"enabled": True} for name in names}}', 'config = {"sentinels": {"collab": {"enabled": True}}, "sentinel": {"enabled": False}}')
        done = subprocess.run([sys.executable, "-I", "-c", script, str(HERE / "src")], capture_output=True, text=True, timeout=90, check=False)
        self.assertEqual(done.returncode, 0, done.stderr[-800:])
        out = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(out["ticked"], ["collab"])
        self.assertEqual(out["threads"], ["sentinel-collab"])


if __name__ == "__main__":
    unittest.main()
