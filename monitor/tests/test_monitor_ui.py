# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tests of the interface support: report history (retention, yesterday vs today), Markdown report, "only hot" switch and its endpoint."""
import json
import sys
import tempfile
import threading
import unittest
import _testenv  # noqa: F401
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import actions_monitor as am  # noqa: E402
import report_history as ph  # noqa: E402


def snap(red=(), pend=(), generated="2026-11-05T10:00:00Z", **extra):
    s = {"generated": generated, "enabled": True, "loading": "",
         "parte": [{"level": "bad", "text": "Hay rojos", "head": True}, {"level": "warn", "text": "Verde sin firmar"}],
         "totals": {"red": len(red), "stuck": 0, "new_alerts": 1, "candidates": 2, "prs": 3},
         "a2": {"red": [{"repo": r, "workflow": "CI"} for r in red]}, "a5": {"pending_sign": [{"repo": r, "hours": 30} for r in pend]}}
    s.update(extra)
    return s


class History(_testenv.Spanish, unittest.TestCase):
    def test_save_and_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for day in ("2026-09-01", "2026-10-01", "2026-10-20", "2026-11-04"):
                (folder / f"{ph.PREFIX}{day}.txt").write_text("x", encoding="utf-8")
                (folder / f"{ph.PREFIX}{day}.json").write_text("{}", encoding="utf-8")
            (folder / "OTRO_FICHERO.txt").write_text("keep", encoding="utf-8")
            self.assertEqual(ph.save_day(folder, snap(), keep_days=30, today="2026-11-05"), "2026-11-05")
            names = sorted(p.name for p in folder.iterdir())
            self.assertNotIn(f"{ph.PREFIX}2026-09-01.txt", names)
            self.assertNotIn(f"{ph.PREFIX}2026-10-01.json", names)       # 35 days old
            self.assertIn(f"{ph.PREFIX}2026-10-20.txt", names)           # 16 days old
            self.assertIn("OTRO_FICHERO.txt", names)                     # files with another name are never touched
            self.assertIn("PARTE DEL CENTINELA", (folder / f"{ph.PREFIX}2026-11-05.txt").read_text(encoding="utf-8"))

    def test_retention_is_configurable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for day in ("2026-11-01", "2026-11-03", "2026-11-04"):
                (folder / f"{ph.PREFIX}{day}.json").write_text("{}", encoding="utf-8")
            ph.save_day(folder, snap(), keep_days=2, today="2026-11-05")
            self.assertEqual(ph.saved_days(folder), ["2026-11-04", "2026-11-05"])

    def test_missing_folder_or_incomplete_snapshot_does_not_fail(self):
        self.assertIsNone(ph.save_day(Path("Z:/no/existe/nunca"), snap()))
        self.assertIsNone(ph.save_day(None, snap()))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ph.save_day(Path(tmp), snap(loading="3/10")))   # data still loading: not the report of the day
            self.assertEqual(ph.saved_days(Path(tmp)), [])

    def test_yesterday_vs_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertFalse(ph.yesterday_vs_today(folder, snap(), "2026-11-05")["available"])
            ph.save_day(folder, snap(red=["A", "B"], pend=["P"]), today="2026-11-04")
            view = ph.yesterday_vs_today(folder, snap(red=["B", "C"], pend=[]), "2026-11-05")
            self.assertTrue(view["available"] and view["is_yesterday"])
            self.assertEqual(view["red"]["appeared"], ["C (CI)"])
            self.assertEqual(view["red"]["disappeared"], ["A (CI)"])
            self.assertEqual(view["pending_sign"]["disappeared"], ["P"])
            self.assertEqual(view["pending_sign"]["appeared"], [])

    def test_markdown_and_text(self):
        md = ph.parte_markdown(snap(red=["A"]))
        self.assertTrue(md.startswith("## Parte del Centinela"))
        self.assertIn("- **bad**: Hay rojos", md)
        self.assertIn("| Rojos |", md)
        self.assertTrue(ph.parte_text(snap()).startswith("PARTE DEL CENTINELA - 2026-11-05"))
        self.assertIn("[warn] Verde sin firmar", ph.parte_text(snap()))


class HotOnly(unittest.TestCase):
    def setUp(self):
        am.RUN_CACHE.clear()
        am.HOT_ONLY.update({"on": False, "until": 0.0})
        self.cfg = dict(am.DEFAULTS)
        self.fetched = []
        self.orig = am.fetch_runs
        am.fetch_runs = lambda repo, per_page: self._fake(repo)

    def _fake(self, repo):
        self.fetched.append(repo)
        return [], None

    def tearDown(self):
        am.fetch_runs = self.orig
        am.RUN_CACHE.clear()
        am.HOT_ONLY.update({"on": False, "until": 0.0})

    def old_cache(self):
        am.RUN_CACHE["COLD"] = {"runs": [], "at": 0.0, "error": None}   # cold (no runs) and expired

    def test_cold_refreshes_normally(self):
        self.old_cache()
        am.refresh_runs(["COLD"], self.cfg)
        self.assertEqual(self.fetched, ["COLD"])

    def test_hot_only_skips_cold_but_not_new_repos(self):
        self.old_cache()
        state = am.set_hot_only(True, self.cfg)
        self.assertTrue(state["on"])
        self.assertGreater(state["seconds_left"], 0)
        am.refresh_runs(["COLD", "NEW"], self.cfg)
        self.assertEqual(self.fetched, ["NEW"])   # the cold one waits; a repo never seen is still fetched once

    def test_expires_by_itself_after_one_long_cycle(self):
        self.cfg["cold_refresh_seconds"] = 600
        am.set_hot_only(True, self.cfg, now=1000.0)
        self.assertTrue(am.hot_only_state(now=1500.0)["on"])
        self.assertFalse(am.hot_only_state(now=1601.0)["on"])
        self.assertFalse(am.set_hot_only(False, self.cfg)["on"])


class Endpoint(unittest.TestCase):
    def setUp(self):
        am.HOT_ONLY.update({"on": False, "until": 0.0})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        am.HOT_ONLY.update({"on": False, "until": 0.0})

    def post(self, body, host=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/hot-only", data=body, method="POST", headers={"Content-Type": "application/json"})
        if host:
            req.remove_header("Host")
            req.add_unredirected_header("Host", host)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def test_switch_on_and_off(self):
        code, j = self.post(json.dumps({"on": True}).encode())
        self.assertEqual(code, 200)
        self.assertTrue(j["hot_only"]["on"])
        self.assertTrue(am.hot_only_state()["on"])
        code, j = self.post(json.dumps({"on": False}).encode())
        self.assertFalse(j["hot_only"]["on"])

    def test_rejects_foreign_host_and_bad_body(self):
        code, _ = self.post(json.dumps({"on": True}).encode(), host="evil.example:80")
        self.assertEqual(code, 403)
        self.assertFalse(am.hot_only_state()["on"])
        code, _ = self.post(b'{"on": "yes"}')
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
