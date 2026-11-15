# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The score chip of the page: it is in the markup, it reads the two routes, hides in Lite and when the score is off, says why there is no number, never shows a number as sure while a part is
missing, and every text it uses exists in the eight languages. The drawing function runs in node when node is there."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import pagecheck  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


def drawing_code():
    start = PAGE.index("function scoreSpark(")
    end = PAGE.index("async function scoreTick(")
    return PAGE[start:end]


class Markup(unittest.TestCase):
    def test_the_chip_is_in_the_header_next_to_the_readiness_chips_and_is_labelled(self):
        self.assertRegex(PAGE, r'<span class="rdy" id="k-score" role="group" data-i18n-aria="ui\.score_title" hidden></span>')

    def test_it_reads_both_routes_polls_slowly_and_is_never_started_in_lite(self):
        body = PAGE[PAGE.index("async function scoreTick("):PAGE.index("async function sentTick(")]
        self.assertIn('fetch("/api/score"', body)
        self.assertIn('"/api/score/history?hours="', body)
        self.assertIn("if(!el||LITE)return", body)
        self.assertIn("scoreTick();setInterval(scoreTick,60000)", PAGE)
        self.assertIn(".lite #k-score{display:none}", PAGE)

    def test_a_score_that_is_off_or_missing_hides_the_chip(self):
        body = PAGE[PAGE.index("async function scoreTick("):PAGE.index("async function sentTick(")]
        self.assertIn('a.state==="off"', body)
        self.assertIn("el.hidden=true", body)

    def test_no_function_of_the_page_is_defined_twice(self):
        self.assertEqual(pagecheck.duplicates(PAGE), [])

    def test_every_text_it_uses_exists_in_the_eight_languages(self):
        keys = {k for k in re.findall(r'"(ui\.score_[a-z_]+)"', drawing_code()) if not k.endswith("_")} | {"ui.score_title"}
        keys |= {"ui.score_p_" + p for p in ("reliability", "speed", "recovery", "collaboration", "security")}
        self.assertGreaterEqual(len(keys), 12)
        for lang in i18n.LANGS:
            for key in keys:
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        catalogue = i18n.ui_catalogues()["en"]
        for key in keys:
            self.assertIn(key, catalogue)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Drawing(unittest.TestCase):
    def render(self, answer, points):
        script = (
            "const esc=s=>String(s==null?'':s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));"
            "const T=(k,v)=>k+(v?JSON.stringify(v):'');"
            + drawing_code()
            + f"process.stdout.write(scoreChip({json.dumps(answer)},{json.dumps(points)}));"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chip.js"
            path.write_text(script, encoding="utf-8")
            done = subprocess.run(["node", str(path)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def scored(self, **over):
        base = {"state": "scored", "score": 82.5, "letter": "B", "trend": {"direction": "up", "delta": 3.0}, "coverage": 0.8, "window_days": 7, "stale": False,
                "missing_parts": ["security"], "parts": [{"part": "reliability", "weight": 40, "score": 90}], "repos": [{"repo": "a/x", "score": 61.0}], "data_quality": {"runs": 90}}
        base.update(over)
        return base

    def test_a_scored_account_shows_number_letter_trend_and_that_something_is_missing(self):
        html = self.render(self.scored(), [{"score": 70}, {"score": 80}, {"score": 82.5}])
        self.assertIn("<b>82.5</b>", html)
        self.assertIn("rdy-chip scr-chip ok", html)
        self.assertIn("ui.score_trend_up", html)
        self.assertIn("ui.score_missing", html)          # in the tooltip
        self.assertIn(">*</small>", html)              # and a visible mark
        self.assertIn("<polyline", html)

    def test_the_letter_gives_the_colour(self):
        for letter, cls in (("A", " ok"), ("B", " ok"), ("C", " warn"), ("D", " bad"), ("E", " bad")):
            self.assertIn("scr-chip" + cls, self.render(self.scored(letter=letter), []))

    def test_without_a_number_the_chip_is_neutral_and_says_why(self):
        for state, key in (("calibrating", "ui.score_state_calibrating"), ("insufficient_data", "ui.score_state_insufficient")):
            html = self.render(self.scored(state=state, score=None, letter=None), [])
            self.assertIn(key, html)
            self.assertNotIn("<b>", html)
            self.assertNotIn(" ok", html)
            self.assertNotIn(" bad", html)

    def test_an_old_snapshot_is_said_to_be_old(self):
        self.assertIn("ui.score_old", self.render(self.scored(stale=True), []))

    def test_markup_in_a_repository_name_is_escaped(self):
        html = self.render(self.scored(repos=[{"repo": "<img src=x onerror=1>", "score": 1}]), [])
        self.assertNotIn("<img", html)

    def test_a_single_point_draws_no_line(self):
        self.assertNotIn("<polyline", self.render(self.scored(), [{"score": 70}]))


if __name__ == "__main__":
    unittest.main()
