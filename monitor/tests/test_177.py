# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One rule for the open failures (tile, list of alerts, bar at the foot), damaged state files, the zone check of the doctor, the clock of the bar and the start-up banner."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import doctor  # noqa: E402
import i18n  # noqa: E402
import redrule  # noqa: E402
import sentinel_collab  # noqa: E402
import sentinel_local  # noqa: E402

PAGE = (HERE / "actions_monitor.html").read_text(encoding="utf-8")


def run(ident, repo, name, conclusion, branch="main", started="2026-01-01T10:00:00Z", status="completed"):
    return {"id": ident, "repo": repo, "name": name, "path": name + ".yml", "status": status, "conclusion": conclusion, "event": "push", "branch": branch, "sha": "abc", "url": "u", "started": started, "seconds": 5}


class OneRuleForOpenFailures(unittest.TestCase):
    def test_a_failure_on_a_work_branch_is_not_an_open_alert_and_the_tile_agrees(self):
        runs = [run(1, "a", "ci", "failure", started="2026-01-01T10:00:00Z"),
                run(2, "b", "sync", "failure", branch="work-branch"),                     # not the default branch: nobody has to act
                run(3, "b", "sync", "success", started="2026-01-01T09:00:00Z"),
                run(4, "c", "ci", "failure", started="2026-01-01T08:00:00Z"), run(5, "c", "ci", "success", started="2026-01-01T09:00:00Z"),      # resolved
                run(6, "d", "ci", "cancelled", started="2026-01-01T11:00:00Z"), run(7, "d", "ci", "failure", started="2026-01-01T10:00:00Z")]   # a cancelled run hides nothing
        failing = am.unresolved_failures(runs)
        self.assertEqual(sorted((r["repo"], r["name"]) for r in failing), [("a", "ci"), ("d", "ci")])
        red = redrule.red_workflows({r: [x for x in runs if x["repo"] == r] for r in "abcd"}, None, True)[0]
        self.assertEqual(len(failing), len(red))      # "red on main" and the open failures are the same number
        self.assertEqual(sorted((r["repo"], r["workflow"]) for r in red), sorted((r["repo"], r["name"]) for r in failing))

    def test_a_default_branch_that_is_not_main_is_respected(self):
        runs = [run(1, "a", "ci", "failure", branch="trunk")]
        self.assertEqual(len(am.unresolved_failures(runs, {"a": "trunk"})), 1)
        self.assertEqual(am.unresolved_failures(runs, {"a": "main"}), [])

    def test_the_bar_at_the_foot_is_never_green_with_open_alerts(self):
        self.assertIn("OPENALERTS=a.length", PAGE)
        self.assertIn('text:T("ui.sb_open_alerts"', PAGE)
        for lang in i18n.LANGS:
            self.assertNotEqual(i18n.tl(lang, "ui.sb_open_alerts"), "ui.sb_open_alerts", lang)
            self.assertIn("{n}", i18n.tl(lang, "ui.sb_open_alerts"), lang)


class DamagedStateFiles(unittest.TestCase):
    def test_the_sentinel_ignores_files_of_the_wrong_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            for text in ("[1, 2]", "7", "null", "{broken", '"text"'):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(sentinel_local.Sentinel._load(path, {"days": {}}), {"days": {}}, text)
            path.write_text('{"days": {"2026-01-01": 1}}', encoding="utf-8")
            self.assertEqual(sentinel_local.Sentinel._load(path, {"days": {}}), {"days": {"2026-01-01": 1}})

    def test_the_collab_state_keeps_only_entries_the_rest_of_the_code_can_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "collab.json"
            path.write_text(json.dumps({"alerts": {"ok": {"repo": "r", "n": 1}, "bad1": 5, "bad2": {"no_repo": 1}, "bad3": {"repo": 3}}, "per_repo": {"r": {"scanned": 1}, "x": "oops"}}), encoding="utf-8")
            state = sentinel_collab.load_state(path)
            self.assertEqual(list(state["alerts"]), ["ok"])
            self.assertEqual(list(state["per_repo"]), ["r"])
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(sentinel_collab.load_state(path), {"alerts": {}, "per_repo": {}, "last_full_scan": None})


class TimeZoneCheck(unittest.TestCase):
    def test_the_doctor_warns_about_a_zone_nothing_knows_and_the_times_show_utc(self):
        with mock.patch.dict(os.environ, {"MONITOR_TIMEZONE": "Nowhere/Atlantis"}):
            status, detail = doctor.time_zone({})
            self.assertEqual((status, detail), ("warn", "Nowhere/Atlantis"))
        with mock.patch.dict(os.environ, {"MONITOR_TIMEZONE": ""}):
            self.assertEqual(doctor.time_zone({"display": {"timezone": "Europe/Madrid"}}), ("ok", "Europe/Madrid"))
            self.assertEqual(doctor.time_zone({"display": {"timezone": "Mars/Olympus"}})[0], "warn")
            self.assertEqual(doctor.time_zone({})[0], "ok")
        self.assertIn("timezone", doctor.ORDER)
        for lang in i18n.LANGS:
            for key in ("doctor.t.timezone", "doctor.f.timezone"):
                self.assertNotEqual(i18n.tl(lang, key), key, lang)


class ClockOfTheBar(unittest.TestCase):
    def test_the_clock_is_a_box_with_large_bold_tabular_digits_and_a_small_zone(self):
        self.assertIn('id="ck-t"', PAGE)
        self.assertIn('id="ck-z"', PAGE)
        self.assertRegex(PAGE, r"#statusbar \.ck-t\{[^}]*font-weight:800[^}]*font-variant-numeric:tabular-nums")
        self.assertIn("#statusbar .sb-clock{", PAGE)
        self.assertIn('tileClock("tv-upd"', PAGE)      # the time of the tile of the last reading keeps its zone apart, in small letters


class RedTilesBlink(unittest.TestCase):
    def test_only_red_tiles_blink_and_the_setting_can_turn_it_off(self):
        import settings_api
        self.assertRegex(PAGE, r'@media \(prefers-reduced-motion:no-preference\)\{:root\[data-blink="1"\] \.tile\.bad:not\(\.skel\)')      # only the red state, only with motion allowed
        self.assertNotRegex(PAGE, r'data-blink="1"\] \.tile\.(ok|warn|run)')
        self.assertRegex(PAGE, r'@media \(prefers-reduced-motion:reduce\)\{:root\[data-blink="1"\] \.tile\.bad[^}]*inset 0 0 0 3px var\(--bad\)')      # reduced motion: a fixed thicker edge
        self.assertIn('dataset.blink=I18N.blink===false?"0":"1"', PAGE)
        self.assertIs(am.DEFAULTS["display"]["blink_red_tiles"], True)
        self.assertIn("display.blink_red_tiles", settings_api.FIELDS)
        for lang in i18n.LANGS:
            for key in ("cfg.f.display.blink_red_tiles", "cfg.h.display.blink_red_tiles"):
                self.assertNotEqual(i18n.tl(lang, key), key, lang)


if __name__ == "__main__":
    unittest.main()
