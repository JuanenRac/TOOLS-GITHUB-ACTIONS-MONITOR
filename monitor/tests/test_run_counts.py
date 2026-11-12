# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The runs in progress and queued are counted ONCE: the header, the list "Right now", the status bar and the command line give the same numbers for the same data,
and when the filters of the page hide some the page says "3 of 13" and "Showing 3 of 13 (filters active)" instead of two numbers that look like one."""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import monitor_cli  # noqa: E402

PAGE = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
NEW_KEYS = ("ui.k_of", "ui.k_filtered_title", "ui.n_showing", "ui.n_showing_filters", "ui.sb_runs", "ui.sb_runs_t")


def run(ident, repo, status, event="push"):
    return {"id": ident, "repo": repo, "name": "ci", "status": status, "conclusion": None, "event": event, "branch": "main", "sha": "abc", "actor": "x", "url": "u", "seconds": 5,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "path": "ci.yml"}


def sample_runs():
    runs = [run(i, "repo-0" if i < 8 else "repo-1", "in_progress") for i in range(1, 14)]      # 13 running
    runs.append(run(100, "repo-1", "queued"))                                                   # 1 queued
    runs.append(run(101, "repo-1", "queued", event="dynamic"))                                  # internal job of Dependabot: never counted, neither in the list
    runs.append(dict(runs[0]))                                                                  # the same run twice
    return runs


def built(lite):
    runs = sample_runs()
    cache = {"repo-0": {"runs": [r for r in runs if r["repo"] == "repo-0"], "at": 0, "error": None},
             "repo-1": {"runs": [r for r in runs if r["repo"] == "repo-1"], "at": 0, "error": None}}
    cache["repo-1"]["runs"].append(dict(cache["repo-1"]["runs"][0]))        # a repository read twice
    saved = (dict(am.RUN_CACHE), am.LITE["on"], dict(am.ISSUE_CACHE))
    am.RUN_CACHE.clear()
    am.RUN_CACHE.update(cache)
    am.LITE["on"] = lite
    am.ISSUE_CACHE.update({"items": [], "at": time.time(), "busy": False})
    config = {"stuck_minutes": 60, "issues_refresh_seconds": 10 ** 6, "mode": "normal", "min_rate_remaining": 100, "refresh_seconds": 60, "max_workers": 1, "runs_per_repo": 30}
    try:
        with mock.patch.object(am, "gh", side_effect=RuntimeError("offline")), mock.patch.object(am, "run_jobs", return_value=[]):
            return am.build(config, ["repo-0", "repo-1"], time.time(), 0, False, "")
    finally:
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(saved[0])
        am.LITE["on"] = saved[1]
        am.ISSUE_CACHE.update(saved[2])


class ServerCounts(unittest.TestCase):
    def check(self, lite):
        data = built(lite)
        running = [r for r in data["active"] if r["status"] == "in_progress"]
        waiting = [r for r in data["active"] if r["status"] != "in_progress"]
        ids = [(r["repo"], r["id"]) for r in data["active"]]
        self.assertEqual(len(ids), len(set(ids)), "no run twice")
        self.assertEqual((data["figures"]["active"], data["figures"]["queued"]), (len(running), len(waiting)))
        self.assertEqual(len(data["active"]), data["figures"]["active"] + data["figures"]["queued"], "the list and the header are made from the same runs")
        self.assertNotIn("dynamic", {r["event"] for r in data["active"]})
        return data

    def test_complete_edition(self):
        data = self.check(False)
        self.assertEqual((data["figures"]["active"], data["figures"]["queued"]), (13, 1))

    def test_lite_edition(self):
        data = self.check(True)
        self.assertEqual((data["figures"]["active"], data["figures"]["queued"]), (13, 1))

    def test_waiting_and_pending_runs_count_as_queued(self):
        figures = am.header_figures([], [run(1, "r", "in_progress"), run(2, "r", "waiting"), run(3, "r", "pending"), run(4, "r", "requested")], [])
        self.assertEqual((figures["active"], figures["queued"]), (1, 3))

    def test_the_status_bar_and_the_command_line_give_the_same_figures(self):
        data = built(False)
        saved = am.STATE["data"]
        am.STATE["data"] = data
        try:
            self.assertEqual(am.statusbar_payload(8765)["runs"], {"active": 13, "queued": 1})
        finally:
            am.STATE["data"] = saved
        answers = {"/api/health": {"version": "1", "lite": False}, "/api/data": {"data": data}}
        ctx = {"base": "http://x", "account": None, "timeout": 1, "token": None}
        with mock.patch.object(monitor_cli, "fetch", side_effect=lambda base, path, *a: answers[path]):
            payload = monitor_cli.cmd_status(ctx)[0]
        self.assertEqual((payload["active"], payload["queued"]), (13, 1))

    def test_the_status_bar_has_no_figures_before_the_first_read(self):
        saved = am.STATE["data"]
        am.STATE["data"] = None
        try:
            self.assertEqual(am.statusbar_payload(8765)["runs"], {"active": None, "queued": None})
        finally:
            am.STATE["data"] = saved


class PageCounts(unittest.TestCase):
    def test_the_page_has_the_status_bar_item_and_the_line_and_the_texts_in_eight_languages(self):
        for needle in ('id="sb-runs"', "function runCounts(d)", "function showingLine(c)", 'runFig(c.sr,c.tr)', 'runFig(c.sq,c.tq)', 'id="now-count"', '"ui.sb_runs"'):
            self.assertIn(needle, PAGE)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in NEW_KEYS:
                self.assertTrue(texts.get(key), f"{lang} {key}")
            self.assertIn("{n}", texts["ui.k_of"])
            self.assertIn("{total}", texts["ui.n_showing_filters"])
            self.assertIn("{active}", texts["ui.sb_runs"])


@unittest.skipUnless(shutil.which("node"), "Node is not installed: the counting logic is checked only where it is")
class PageCountsForReal(unittest.TestCase):
    def evaluate(self, body):
        start = PAGE.index("function repoVisible(repo,d)")
        end = PAGE.index("function render(d){")
        script = ("const FILTER={eco:'',state:'',q:'',list:null};const T=(k,v)=>k+JSON.stringify(v||{});const esc=s=>String(s);\n" + PAGE[start:end] + "\n" + body)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "counts_test.js"
            path.write_text(script, encoding="utf-8")
            done = subprocess.run(["node", str(path)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    DATA = """const d={active:[],failing:[],ecosystems:{a:'x',b:'y'},figures:{active:13,queued:1}};
for(let i=0;i<10;i++)d.active.push({repo:'b',name:'n',status:'in_progress'});
for(let i=0;i<3;i++)d.active.push({repo:'a',name:'n',status:'in_progress'});
d.active.push({repo:'b',name:'n',status:'queued'});
"""
    TAIL = "const c=runCounts(d);console.log(JSON.stringify({c:c,line:showingLine(c)}));"

    def test_without_filters_the_list_and_the_header_agree_and_no_line_is_drawn(self):
        out = self.evaluate(self.DATA + self.TAIL)
        self.assertEqual((out["c"]["sr"], out["c"]["tr"], out["c"]["sq"], out["c"]["tq"]), (13, 13, 1, 1))
        self.assertFalse(out["c"]["differs"])
        self.assertEqual(out["line"], "")

    def test_with_a_filter_the_figures_say_how_many_are_hidden(self):
        out = self.evaluate(self.DATA + "FILTER.eco='x';" + self.TAIL)
        self.assertEqual((out["c"]["sr"], out["c"]["tr"], out["c"]["sq"], out["c"]["tq"], out["c"]["shown"], out["c"]["total"]), (3, 13, 0, 1, 3, 14))
        self.assertTrue(out["c"]["differs"] and out["c"]["filters"])
        self.assertIn("ui.n_showing_filters", out["line"])
        self.assertIn('"n":3,"total":14', out["line"])

    def test_a_search_a_state_and_a_list_are_filters_too(self):
        for assign in ("FILTER.q='a'", "FILTER.state='failed'", "FILTER.list=['a']"):
            out = self.evaluate(self.DATA + assign + ";" + self.TAIL)
            self.assertTrue(out["c"]["filters"], assign)
            self.assertIn("ui.n_showing_filters", out["line"], assign)

    def test_a_gap_without_filters_is_still_said(self):
        out = self.evaluate(self.DATA + "d.figures.active=15;" + self.TAIL)
        self.assertTrue(out["c"]["differs"] and not out["c"]["filters"])
        self.assertIn("ui.n_showing", out["line"])
        self.assertNotIn("filters", out["line"])


if __name__ == "__main__":
    unittest.main()
