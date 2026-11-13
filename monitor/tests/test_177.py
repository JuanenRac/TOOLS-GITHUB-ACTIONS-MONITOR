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
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402
from github_actions_monitor.sentinels import sentinel_collab  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


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

    def test_the_two_failures_of_the_real_screenshot_are_classified_by_the_default_branch(self):
        """HYDRA-UMC-SDK "Sync check" and ARMOR-STUDIO "A.R.M.O.R. CI baseline" showed as open alerts while the tile said 0 red on main: they count when their last run is on the default branch and not otherwise."""
        on_work_branch = [run(1, "HYDRA-UMC-SDK", "Sync check", "failure", branch="work-branch"), run(2, "ARMOR-STUDIO", "A.R.M.O.R. CI baseline", "failure", branch="work-branch")]
        self.assertEqual(am.unresolved_failures(on_work_branch, {"HYDRA-UMC-SDK": "main", "ARMOR-STUDIO": "main"}), [])
        on_main = [run(3, "HYDRA-UMC-SDK", "Sync check", "failure"), run(4, "ARMOR-STUDIO", "A.R.M.O.R. CI baseline", "failure")]
        failing = am.unresolved_failures(on_main, {"HYDRA-UMC-SDK": "main", "ARMOR-STUDIO": "main"})
        self.assertEqual(sorted(r["repo"] for r in failing), ["ARMOR-STUDIO", "HYDRA-UMC-SDK"])
        red = redrule.red_workflows({r: [x for x in on_main if x["repo"] == r] for r in ("HYDRA-UMC-SDK", "ARMOR-STUDIO")}, {"HYDRA-UMC-SDK": "main", "ARMOR-STUDIO": "main"})[0]
        self.assertEqual(len(red), len(failing), "the tile of red on main and the list of alerts are one number")

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
        from github_actions_monitor.app import settings_api
        self.assertRegex(PAGE, r'@media \(prefers-reduced-motion:no-preference\)\{:root\[data-blink="1"\] \.tile\.bad:not\(\.skel\)')      # only the red state, only with motion allowed
        self.assertNotRegex(PAGE, r'data-blink="1"\] \.tile\.(ok|warn|run)')
        self.assertRegex(PAGE, r'@media \(prefers-reduced-motion:reduce\)\{:root\[data-blink="1"\] \.tile\.bad[^}]*inset 0 0 0 3px var\(--bad\)')      # reduced motion: a fixed thicker edge
        self.assertIn('dataset.blink=I18N.blink===false?"0":"1"', PAGE)
        self.assertIs(am.DEFAULTS["display"]["blink_red_tiles"], True)
        self.assertIn("display.blink_red_tiles", settings_api.FIELDS)
        for lang in i18n.LANGS:
            for key in ("cfg.f.display.blink_red_tiles", "cfg.h.display.blink_red_tiles"):
                self.assertNotEqual(i18n.tl(lang, key), key, lang)


class QuotaPace(unittest.TestCase):
    def test_the_loop_slows_down_below_the_floor_and_waits_for_the_renewal_when_nothing_is_left(self):
        now = 1_000_000
        stamp = lambda epoch: __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime(epoch))      # noqa: E731
        self.assertEqual(am.quota_delay({"remaining": 4000, "reset": stamp(now + 100)}, 800, 120, now), 120)
        self.assertEqual(am.quota_delay({"remaining": 500, "reset": stamp(now + 100)}, 800, 120, now), 180)
        self.assertEqual(am.quota_delay({"remaining": 0, "reset": stamp(now + 1200)}, 800, 120, now), 1205)
        self.assertEqual(am.quota_delay({"remaining": 0, "reset": stamp(now + 99999)}, 800, 120, now), 3900)
        self.assertEqual(am.quota_delay({"remaining": 0, "reset": "garbage"}, 800, 120, now), 600)
        self.assertEqual(am.quota_delay(None, 800, 120, now), 120)

    def test_the_bar_says_until_when_the_allowance_is_used_up(self):
        self.assertIn('T("ui.sb_quota_out"', PAGE)
        for lang in i18n.LANGS:
            self.assertIn("{time}", i18n.tl(lang, "ui.sb_quota_out"), lang)
            self.assertNotEqual(i18n.tl(lang, "ui.sb_quota_out_t"), "ui.sb_quota_out_t", lang)


class UpdateCheckNeverBlocks(unittest.TestCase):
    def test_a_slow_read_is_made_in_the_background_and_the_answer_of_the_cache_is_immediate(self):
        import threading
        import time as _time
        from github_actions_monitor.app import updatecheck
        gate = threading.Event()
        calls = []

        def slow_reader(endpoint):
            calls.append(endpoint)
            gate.wait(10)
            return {"tag_name": "v9.9.9", "html_url": "https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/tag/v9.9.9"}
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "u.json"
            started = _time.time()
            first = updatecheck.check({}, "1.0.0", slow_reader, state_file=state_file, background=True)
            second = updatecheck.check({}, "1.0.0", slow_reader, state_file=state_file, background=True)
            self.assertLess(_time.time() - started, 2, "the page does not wait for the network")
            self.assertFalse(first["newer"])
            self.assertFalse(second["newer"])
            gate.set()
            for _ in range(100):
                if state_file.is_file():
                    break
                _time.sleep(0.05)
            self.assertEqual(len(calls), 1, "one read at a time")
            self.assertTrue(updatecheck.check({}, "1.0.0", slow_reader, state_file=state_file, background=True)["newer"], "the next answer has what the thread read")
            self.assertIn("background=True", (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
