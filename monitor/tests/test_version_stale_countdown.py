# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Three gaps of the wall screens and the sentinel, closed together:

1. `/api/version` (never cached) and the reload of a wall screen or a kiosk that stays on for days when the monitor was updated or restarted (`screens.version_check_seconds`).
2. A result that is too old is called stale (`ci.stale_result_hours`): information only, never red or green by itself, and not marked when the read of the repository failed.
3. The countdown to the 60 days after which GitHub switches off the scheduled workflows of a public repository (`sentinel.schedule_countdown_after_days`): an information row, from what the sentinel
   already holds, "not evaluable" without the date of the last push, never red.
No network."""
import json
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, screens, settings_api, surface  # noqa: E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402
from github_actions_monitor.surfaces import kiosk  # noqa: E402
from github_actions_monitor.tool_version import TOOL_VERSION  # noqa: E402
from test_200_contract import Served  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
SCREENS_PAGE = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
MAIN_PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
NEW_KEYS = ("screens.version_check_seconds", "ci.stale_result_hours", "sentinel.schedule_countdown_after_days")


class TheVersionRoute(unittest.TestCase):
    def test_it_answers_the_version_and_the_start_and_is_never_cached_in_both_editions(self):
        for lite in (False, True):
            served = Served(self, lite=lite)
            status, raw, answer = served.raw("GET", "/api/version")
            self.assertEqual(status, 200, lite)
            self.assertEqual(json.loads(raw), {"version": TOOL_VERSION, "started": int(am.STARTED)}, lite)
            self.assertIn("no-store", answer.getheader("Cache-Control"))

    def test_it_is_a_read_with_the_same_guard_as_the_others_and_asks_nothing_of_github(self):
        source = Path(am.__file__).read_text(encoding="utf-8")
        body = source[source.index('elif path == "/api/version"'):source.index('elif path == "/api/health"')]
        self.assertIn("if not self.guard():", body)
        self.assertNotIn("gh_read", body)
        contract = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
        row = next(r for r in contract["endpoints"] if r["path"] == "/api/version")
        self.assertEqual(row["complete"], {"version": "str", "started": "int"})

    def test_it_is_not_counted_as_somebody_looking(self):
        from github_actions_monitor.app import viewers
        self.assertNotIn("/api/version", viewers.WATCHED)


class TheCheckPace(unittest.TestCase):
    def test_the_default_is_five_minutes_and_the_program_and_the_example_say_the_same(self):
        self.assertEqual(screens.DEFAULTS["version_check_seconds"], 300)
        self.assertEqual(am.DEFAULTS["screens"]["version_check_seconds"], 300)
        self.assertEqual(screens.settings({})["version_check_seconds"], 300)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["screens"]["version_check_seconds"], 300)

    def test_zero_is_off_a_low_value_is_raised_to_the_least_and_a_wrong_one_is_the_default(self):
        pace = lambda value: screens.settings({"screens": {"version_check_seconds": value}})["version_check_seconds"]  # noqa: E731
        self.assertEqual([pace(v) for v in (0, 5, 29, 30, 31, 600, 10 ** 9)], [0, 30, 30, 30, 31, 600, 86400])
        self.assertEqual([pace(v) for v in (-1, True, False, "60", None, 12.5)], [300] * 6)

    def test_the_settings_page_knows_it_with_its_range(self):
        self.assertEqual(settings_api.FIELDS["screens.version_check_seconds"][2:4], ("int", (0, screens.MAX_VERSION_CHECK)))

    def test_the_wall_screens_and_the_kiosk_are_given_it(self):
        data = screens.page_data("now", screens.settings({"screens": {"version_check_seconds": 90}}), {}, lang="en")
        self.assertEqual(data["settings"]["version_check_seconds"], 90)
        self.assertEqual(kiosk.public({})["version_check_seconds"], 300)
        self.assertEqual(kiosk.public({"screens": {"version_check_seconds": 0}})["version_check_seconds"], 0)
        self.assertEqual(kiosk.public({"screens": {"version_check_seconds": 3}})["version_check_seconds"], 30)
        self.assertEqual(kiosk.settings({"kiosk": {"enabled": True}})["enabled"], True)      # the kiosk's own settings did not change


class TheReload(unittest.TestCase):
    def watch(self, page):
        start = page.index("/api/version")
        return page[start - 900:start + 900]

    def test_both_pages_ask_the_route_and_reload_only_after_a_valid_answer_that_differs(self):
        for name, page, pace in (("screens", SCREENS_PAGE, "S.version_check_seconds"), ("kiosk", MAIN_PAGE, "k.version_check_seconds")):
            self.assertEqual(page.count('fetch("/api/version"'), 1, name)
            code = self.watch(page)
            self.assertIn("Number(" + pace + ")", code, name)
            self.assertIn("every>=30", code, name)      # 0 never asks and nothing asks twice a minute
            self.assertIn('{cache:"no-store"}', code, name)
            self.assertIn("if(!r.ok)return;", code, name)      # a refused or broken answer says nothing
            self.assertIn('typeof j.version!=="string"||typeof j.started!=="number"', code, name)
            self.assertIn("if(base===null){base=j;return}", code, name)      # the first valid answer is the one the page lives with
            self.assertIn("j.version!==base.version||j.started!==base.started)location.reload()", code, name)
            self.assertEqual(code.count("location.reload()"), 1, name)
            self.assertIn("catch(e){}", code, name)      # a server that does not answer never reloads: no loop

    def test_the_kiosk_asks_only_inside_its_profile(self):
        start = MAIN_PAGE.index("(function(){const k=I18N.kiosk||{};")
        end = MAIN_PAGE.index("})();", MAIN_PAGE.index("/api/version", start))
        self.assertLess(start, MAIN_PAGE.index("/api/version", start))
        self.assertIn('if(k.enabled!==true||QS.get("kiosk")!=="1")return;', MAIN_PAGE[start:end])


class Rows:
    NOW = 1_800_000_000.0

    @staticmethod
    def stamp(hours_ago):
        return datetime.fromtimestamp(Rows.NOW - hours_ago * 3600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def run(ident, conclusion, hours, path="ci.yml", repo="demo", event="push"):
        return {"repo": repo, "id": ident, "name": path, "path": path, "branch": "main", "event": event, "fork": False, "status": "completed", "conclusion": conclusion, "started": Rows.stamp(hours)}


class TheStaleResult(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def test_it_is_off_by_default_and_a_wrong_value_is_off(self):
        self.assertEqual(redrule.POLICY["stale_result_hours"], 0)
        self.assertEqual(am.DEFAULTS["ci"]["stale_result_hours"], 0)
        for bad in (-1, True, "72", 72.5, 9000, None):
            redrule.configure({"ci": {"stale_result_hours": bad}})
            self.assertEqual(redrule.POLICY["stale_result_hours"], 0, bad)
        redrule.configure({"ci": {"stale_result_hours": 72}})
        self.assertEqual(redrule.POLICY["stale_result_hours"], 72)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["ci"]["stale_result_hours"], 0)

    def test_a_result_is_stale_only_past_the_limit_and_only_with_a_time_that_can_be_read(self):
        redrule.configure({"ci": {"stale_result_hours": 72}})
        now = Rows.NOW
        self.assertTrue(redrule.is_stale_result(Rows.stamp(73), now))
        self.assertFalse(redrule.is_stale_result(Rows.stamp(72), now))
        self.assertFalse(redrule.is_stale_result(Rows.stamp(1), now))
        for unreadable in (None, "", "yesterday", 12):
            self.assertFalse(redrule.is_stale_result(unreadable, now), unreadable)
        redrule.configure({})
        self.assertFalse(redrule.is_stale_result(Rows.stamp(10000), now))

    def test_the_rows_are_marked_unless_the_read_of_their_repository_failed(self):
        redrule.configure({"ci": {"stale_result_hours": 72}})
        rows = [{"repo": "a", "workflow": "ci", "since": Rows.stamp(200)}, {"repo": "b", "workflow": "ci", "since": Rows.stamp(200)}, {"repo": "a", "workflow": "new", "since": Rows.stamp(2)}]
        redrule.mark_stale(rows, failed={"b"}, now=Rows.NOW)
        self.assertEqual([bool(r.get("stale_result")) for r in rows], [True, False, False])
        self.assertNotIn("stale_result", rows[1])      # a key that is not true is not written

    def test_with_the_setting_off_the_rows_are_not_touched(self):
        rows = [{"repo": "a", "workflow": "ci", "since": Rows.stamp(5000)}]
        self.assertEqual(redrule.mark_stale(rows, now=Rows.NOW), [{"repo": "a", "workflow": "ci", "since": Rows.stamp(5000)}])

    def test_it_changes_neither_the_reds_nor_the_other_lists(self):
        runs = [Rows.run(1, "failure", 300), Rows.run(2, "success", 400, path="old.yml"), Rows.run(3, "failure", 1, path="fresh.yml")]
        before = redrule.states({"demo": runs}, {"demo": "main"}, now=Rows.NOW), redrule.red_workflows({"demo": runs}, {"demo": "main"}, now=Rows.NOW)[0]
        redrule.configure({"ci": {"stale_result_hours": 72}})
        after = redrule.states({"demo": runs}, {"demo": "main"}, now=Rows.NOW), redrule.red_workflows({"demo": runs}, {"demo": "main"}, now=Rows.NOW)[0]
        self.assertEqual(before, after)      # the rule of the reds never reads the new setting
        marked = redrule.mark_stale([dict(r) for r in after[1]], now=Rows.NOW)
        self.assertEqual({r["file"]: bool(r.get("stale_result")) for r in marked}, {"ci.yml": True, "fresh.yml": False})

    def test_the_data_of_the_cycle_and_the_sentinel_use_it(self):
        source = Path(am.__file__).read_text(encoding="utf-8")
        self.assertIn("for listed in (expected_rows, ignored_rows, aged_rows, quiet_rows):", source)
        self.assertIn("redrule.mark_stale(listed, errors)", source)
        self.assertIn('redrule.mark_stale(red, set(data.get("errors") or ()), now.timestamp())', Path(sl.__file__).read_text(encoding="utf-8"))

    def test_the_table_of_the_sentinel_ci_marks_the_row_and_the_words_exist_in_eight_languages(self):
        self.assertIn("r.stale_result?", MAIN_PAGE)
        for lang in LANGS:
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.a2_stale", "ui.a2_stale_hint", "ui.a6_info_h", "ui.th_info", "hyg.schedule_countdown", "hyg.schedule_countdown_due", "hyg.schedule_countdown_unknown"):
                self.assertTrue(texts.get(key), (lang, key))
        self.assertEqual(i18n.tl("es", "ui.a2_stale"), "obsoleto")
        self.assertEqual(i18n.tl("en", "ui.a2_stale"), "stale")

    def test_the_sentinel_snapshot_marks_a_red_row_and_keeps_it_red(self):
        now = datetime.fromtimestamp(Rows.NOW, timezone.utc)
        for hours, expected in ((0, None), (72, True)):
            redrule.configure({"ci": {"stale_result_hours": hours}})
            snap = compute(now, [Rows.run(1, "failure", 200)], errors={})
            self.assertEqual(len(snap["a2"]["red"]), 1)
            self.assertEqual(snap["a2"]["red"][0].get("stale_result"), expected)
            self.assertEqual(snap["a2"]["level"], "bad")      # it is still red: stale is only a label
        snap = compute(now, [Rows.run(1, "failure", 200)], errors={"demo": "HTTP 502"})
        self.assertNotIn("stale_result", snap["a2"]["red"][0])      # the read failed: no label


def repo_info(pushed):
    return {"branch": "main", "pushed": pushed, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [{"name": "protect-main", "enforcement": "ACTIVE"}],
            "label_dependencies": True, "files": {"README.md": True, "LICENSE": True, "CHANGELOG.md": True, "SECURITY.md": True}, "license": "mit"}


def compute(now, runs, errors=None, pushed=None, private=False, scans=None, cfg=None, skip=(), perms=None, repo="demo"):
    config = dict(sl.DEFAULTS, **(cfg or {}))
    config["hygiene"] = dict(config["hygiene"], skip=list(skip))
    stamp = (now - timedelta(days=pushed)).strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(pushed, (int, float)) else pushed
    inp = {"now": now, "today": now.strftime("%Y-%m-%d"), "cfg": config, "repos": [repo], "eco": {repo: "main"}, "repo_info": {repo: repo_info(stamp)}, "alerts": {},
           "perms": {repo: perms if perms is not None else {"sha_pinning_required": True, "allowed_actions": "selected", "wf_disabled": [], "at": 1}}, "runs": {repo: runs},
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}, "errors": errors or {}, "repo_meta": {repo: {"private": private, "branch": "main", "pushed": stamp}}},
           "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "", "audits": None, "scans": scans}
    return sl.compute_snapshot(inp)


class TheScheduleCountdown(unittest.TestCase):
    NOW = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
    NIGHTLY = [Rows.run(1, "success", 5, path="nightly.yml", event="schedule")]

    def row(self, snap):
        return snap["a6"]["rows"][0]

    def info(self, snap):
        return self.row(snap).get("info") or []

    def test_the_default_and_the_range_of_the_setting(self):
        self.assertEqual(sl.DEFAULTS["schedule_countdown_after_days"], 45)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["sentinel"]["schedule_countdown_after_days"], 45)
        self.assertEqual(settings_api.FIELDS["sentinel.schedule_countdown_after_days"][2:4], ("int", (1, 59)))
        for bad in (0, 60, 99, -3, True, "45", None, 2.5):
            self.assertEqual(sl.sentinel_config({"sentinel": {"schedule_countdown_after_days": bad}})["schedule_countdown_after_days"], 45, bad)
        self.assertEqual(sl.sentinel_config({"sentinel": {"schedule_countdown_after_days": 30}})["schedule_countdown_after_days"], 30)

    def test_a_public_repository_with_a_schedule_and_an_old_push_gets_the_days_left_as_information(self):
        snap = compute(self.NOW, self.NIGHTLY, pushed=50)
        note = self.info(snap)
        self.assertEqual([(n["code"], n["level"], n["days_left"]) for n in note], [("schedule_countdown", "info", 10)])
        self.assertIn("10", note[0]["text"])
        self.assertIn("50", note[0]["text"])
        self.assertEqual(self.row(snap)["problems"], [])      # never a violation
        self.assertNotEqual(snap["a6"]["level"], "warn")

    def test_a_push_inside_the_limit_a_private_repository_or_no_schedule_have_no_row(self):
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=45)), [])
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=3)), [])
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=50, private=True)), [])
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=50, private=None)), [])      # visibility not read: treated as private, nothing is claimed
        self.assertEqual(self.info(compute(self.NOW, [Rows.run(1, "success", 5)], pushed=50)), [])
        self.assertEqual(self.info(compute(self.NOW, [], pushed=50)), [])      # nothing known about its workflows

    def test_the_setting_moves_the_start_of_the_countdown(self):
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=20, cfg={"schedule_countdown_after_days": 10}))[0]["days_left"], 40)
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=50, cfg={"schedule_countdown_after_days": 55})), [])

    def test_the_workflow_files_say_it_when_they_are_scanned(self):
        scans = {"demo": surface.scan_remote({"a.yml": "on:\n  schedule:\n    - cron: '0 3 * * *'\n"})}
        self.assertEqual(len(self.info(compute(self.NOW, [Rows.run(1, "success", 5)], pushed=50, scans=scans))), 1)
        scans = {"demo": surface.scan_remote({"a.yml": "on:\n  push:\n"})}
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=50, scans=scans)), [])

    def test_without_the_date_of_the_last_push_it_says_not_evaluable_and_invents_nothing(self):
        note = self.info(compute(self.NOW, self.NIGHTLY, pushed=None))
        self.assertEqual([(n["level"], n["days_left"]) for n in note], [("unknown", None)])
        self.assertNotRegex(note[0]["text"], r"\d")

    def test_past_the_limit_it_says_so_but_not_when_github_already_switched_a_schedule_off(self):
        note = self.info(compute(self.NOW, self.NIGHTLY, pushed=70))
        self.assertEqual([(n["level"], n["days_left"]) for n in note], [("info", 0)])
        off = compute(self.NOW, self.NIGHTLY, pushed=70, perms={"sha_pinning_required": True, "allowed_actions": "selected", "wf_disabled": ["Nightly"], "at": 1})
        self.assertEqual(self.info(off), [])
        self.assertEqual([p["code"] for p in self.row(off)["problems"]], ["schedule"])      # the old warning is still the one that speaks

    def test_the_check_of_schedules_left_out_by_the_profile_leaves_out_its_countdown(self):
        self.assertEqual(self.info(compute(self.NOW, self.NIGHTLY, pushed=50, skip=("schedule",))), [])

    def test_it_asks_github_for_nothing_and_the_panel_shows_it(self):
        source = Path(sl.__file__).read_text(encoding="utf-8")
        body = source[source.index("def schedule_countdown("):source.index("def hygiene_problems(")]
        for word in ("_gh(", "gh_read", "subprocess", "urlopen"):
            self.assertNotIn(word, body)
        self.assertIn("(r.info||[]).length", MAIN_PAGE)
        self.assertIn('thk(["ui.th_repo","ui.th_info"])', MAIN_PAGE)

    def test_the_words_follow_the_language(self):
        with i18n.use_language("es"):
            note = self.info(compute(self.NOW, self.NIGHTLY, pushed=50))[0]["text"]
        self.assertIn("GitHub apagará", note)


class Documented(unittest.TestCase):
    def test_every_new_setting_has_its_words_its_guides_and_its_place_in_the_example(self):
        for key in NEW_KEYS:
            for lang in LANGS:
                texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
                self.assertTrue(texts.get("cfg.f." + key), (lang, key))
                self.assertTrue(texts.get("cfg.h." + key), (lang, key))
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho"):
            self.assertIn("`screens.version_check_seconds`", (HERE / "docs" / f"SCREENS{tail}.md").read_text(encoding="utf-8"), tail)
            self.assertIn("`/api/version`", (HERE / "docs" / f"API{tail}.md").read_text(encoding="utf-8"), tail)
            sentinel = (HERE / "docs" / f"SENTINEL{tail}.md").read_text(encoding="utf-8")
            for key in NEW_KEYS[1:]:
                self.assertIn("`" + key + "`", sentinel, (tail, key))
            self.assertTrue(re.search(r"`screens\.version_check_seconds`", (HERE / "docs" / f"KIOSK{tail}.md").read_text(encoding="utf-8")), tail)


if __name__ == "__main__":
    unittest.main()
