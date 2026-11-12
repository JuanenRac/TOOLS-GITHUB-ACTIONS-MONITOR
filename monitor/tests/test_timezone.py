# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Times for people are shown in the zone of the computer (or the one chosen in display.timezone) and say which zone it is; the fields for machines stay in UTC and get a readable sibling.
Also the button "until it changes" of the alerts tab."""
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import ai_alerts  # noqa: E402
import alert_center  # noqa: E402
import ci_red  # noqa: E402
import i18n  # noqa: E402
import report_history  # noqa: E402
import settings_api  # noqa: E402
import tzdisplay  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
MADRID, TOKYO = "Europe/Madrid", "Asia/Tokyo"


class Zones(unittest.TestCase):
    def test_winter_in_madrid_is_cet_and_the_owner_sees_the_local_hour(self):
        self.assertEqual(tzdisplay.stamp("2026-11-12T10:43:07Z", MADRID), "2026-11-12 11:43:07 CET (10:43:07 UTC)")
        self.assertEqual(tzdisplay.clock("2026-11-12T10:43:07Z", MADRID), "11:43 CET")
        self.assertEqual(tzdisplay.iso_local("2026-11-12T10:43:07Z", MADRID), "2026-11-12T11:43:07+01:00")

    def test_summer_in_madrid_is_cest(self):
        self.assertEqual(tzdisplay.stamp("2026-07-12T10:43:07Z", MADRID), "2026-07-12 12:43:07 CEST (10:43:07 UTC)")
        self.assertEqual(tzdisplay.iso_local("2026-07-12T10:43:07Z", MADRID), "2026-07-12T12:43:07+02:00")

    def test_the_change_of_hour_happens_at_01_00_utc_on_the_last_sundays(self):
        self.assertEqual(tzdisplay.clock("2026-03-29T00:59:59Z", MADRID, seconds=True), "01:59:59 CET")
        self.assertEqual(tzdisplay.clock("2026-03-29T01:00:00Z", MADRID, seconds=True), "03:00:00 CEST")
        self.assertEqual(tzdisplay.clock("2026-10-25T00:59:59Z", MADRID, seconds=True), "02:59:59 CEST")
        self.assertEqual(tzdisplay.clock("2026-10-25T01:00:00Z", MADRID, seconds=True), "02:00:00 CET")
        self.assertEqual(tzdisplay.clock("2027-03-28T01:00:00Z", MADRID), "03:00 CEST")      # the next year: the last Sunday of March 2027

    def test_utc_says_utc_and_nothing_else(self):
        self.assertEqual(tzdisplay.stamp("2026-11-12T10:43:07Z", "utc"), "2026-11-12 10:43:07 UTC")
        self.assertEqual(tzdisplay.iso_local("2026-11-12T10:43:07Z", "utc"), "2026-11-12T10:43:07+00:00")

    def test_tokyo_has_no_daylight_saving_time_and_may_be_on_the_next_day(self):
        self.assertEqual(tzdisplay.stamp("2026-07-12T22:43:07Z", TOKYO), "2026-07-13 07:43:07 JST (2026-07-12 22:43:07 UTC)")
        self.assertEqual(tzdisplay.stamp("2026-12-12T10:43:07Z", TOKYO), "2026-12-12 19:43:07 JST (10:43:07 UTC)")

    def test_the_united_states_change_on_their_own_dates(self):
        self.assertEqual(tzdisplay.clock("2026-03-08T06:59:59Z", "America/New_York"), "01:59 EST")
        self.assertEqual(tzdisplay.clock("2026-03-08T07:00:00Z", "America/New_York"), "03:00 EDT")
        self.assertEqual(tzdisplay.clock("2026-11-01T05:59:59Z", "America/New_York"), "01:59 EDT")
        self.assertEqual(tzdisplay.clock("2026-11-01T06:00:00Z", "America/New_York"), "01:00 EST")

    def test_the_zone_of_this_computer_is_the_default(self):
        fake = lambda ts: __import__("datetime").datetime.fromtimestamp(ts, __import__("datetime").timezone(__import__("datetime").timedelta(hours=1), "CET"))   # noqa: E731
        with mock.patch.object(tzdisplay, "_local", fake):
            self.assertEqual(tzdisplay.stamp("2026-11-12T10:43:07Z", "local"), "2026-11-12 11:43:07 CET (10:43:07 UTC)")

    def test_a_long_system_name_becomes_an_offset(self):
        import datetime as d
        fake = lambda ts: d.datetime.fromtimestamp(ts, d.timezone(d.timedelta(hours=1), "Hora estándar romance"))   # noqa: E731
        with mock.patch.object(tzdisplay, "_local", fake):
            self.assertEqual(tzdisplay.clock("2026-11-12T10:43:07Z", "local"), "11:43 UTC+01")

    def test_the_setting_comes_from_the_environment_then_the_file_and_defaults_to_local(self):
        with mock.patch.dict(os.environ, {"MONITOR_TIMEZONE": MADRID}):
            self.assertEqual(tzdisplay.setting(), MADRID)
            self.assertEqual(tzdisplay.stamp("2026-11-12T10:43:07Z"), "2026-11-12 11:43:07 CET (10:43:07 UTC)")
        with mock.patch.dict(os.environ, {"MONITOR_TIMEZONE": ""}), mock.patch("toolconfig.raw_config", return_value={"display": {"timezone": TOKYO}}):
            self.assertEqual(tzdisplay.setting(), TOKYO)
        with mock.patch.dict(os.environ, {"MONITOR_TIMEZONE": ""}), mock.patch("toolconfig.raw_config", return_value={}):
            self.assertEqual(tzdisplay.setting(), "local")

    def test_what_cannot_be_read_comes_back_unchanged(self):
        self.assertEqual(tzdisplay.stamp("yesterday", MADRID), "yesterday")
        self.assertIsNone(tzdisplay.stamp(None, MADRID))
        self.assertEqual(tzdisplay.localize("no time here", MADRID), "no time here")

    def test_localize_changes_every_utc_time_in_a_text_and_nothing_else(self):
        text = "2026-11-12T10:43:07Z repos=3 rate={'reset': '2026-11-12T10:54:09Z'} 2026-11-12 plain"
        out = tzdisplay.localize(text, MADRID)
        self.assertEqual(out, "2026-11-12 11:43:07 CET (10:43:07 UTC) repos=3 rate={'reset': '2026-11-12 11:54:09 CET (10:54:09 UTC)'} 2026-11-12 plain")

    def test_an_unknown_name_falls_back_to_the_computer_and_is_refused_by_the_check(self):
        self.assertTrue(tzdisplay.valid_setting("local") and tzdisplay.valid_setting("utc") and tzdisplay.valid_setting(MADRID))
        self.assertFalse(tzdisplay.valid_setting("Nowhere/Atlantis"))


class Texts(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"MONITOR_TIMEZONE": MADRID})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_catalogue_texts_show_the_local_hour_with_its_zone(self):
        line = i18n.t("cli.status_updated", when="2026-11-12T10:43:07Z")
        self.assertIn("11:43:07 CET (10:43:07 UTC)", line)
        self.assertNotIn("10:43:07Z", line)

    def test_ci_red_keeps_utc_for_machines_and_adds_a_readable_sibling(self):
        out = ci_red.build({"generated": "2026-07-12T10:43:07Z", "a2": {"red": []}, "a5": {"pending_sign": []}, "ecosystems": {}})
        self.assertEqual(out["generated"], "2026-07-12T10:43:07Z")
        self.assertEqual(out["generated_local"], "2026-07-12 12:43:07 CEST (10:43:07 UTC)")

    def test_the_alerts_brief_says_when_it_was_written(self):
        text = ai_alerts.brief([], 2048, now=1783853000)       # 2026-07-12 10:43:20 UTC
        self.assertRegex(text, r"Updated: 2026-07-12 12:43:\d\d CEST \(10:43:\d\d UTC\)")

    def test_the_report_title_uses_the_local_time(self):
        text = report_history.parte_text({"generated": "2026-11-12T10:43:07Z"})
        self.assertIn("2026-11-12 11:43:07 CET (10:43:07 UTC)", text.splitlines()[0])

    def test_the_log_line_of_the_monitor_is_localised(self):
        line = "2026-11-12T10:43:07Z repos=1 rate={'reset': '2026-11-12T10:54:09Z'}\n"
        out = tzdisplay.localize(line)
        self.assertTrue(out.startswith("2026-11-12 11:43:07 CET (10:43:07 UTC) repos=1"))
        self.assertIn("11:54:09 CET", out)

    def test_the_command_line_status_says_the_zone(self):
        import monitor_cli as cli
        replies = {"/api/health": {"version": "1", "account": "a"}, "/api/data": {"data": {"updated": "2026-11-12T10:43:07Z", "repos": [], "figures": {}, "rate": {}}}}
        with mock.patch.object(cli, "fetch", lambda base, path, *a, **k: replies[path]):
            payload, lines, _ = cli.cmd_status({"base": "x", "account": None, "timeout": 1, "token": ""})
        self.assertEqual(payload["updated"], "2026-11-12T10:43:07Z")
        self.assertEqual(payload["updated_local"], "2026-11-12 11:43:07 CET (10:43:07 UTC)")
        self.assertIn("11:43:07 CET", "\n".join(lines))

    def test_a_notification_carries_the_local_time(self):
        import notifiers
        sent = []
        event = {"kind": "red_new", "text": "red since 2026-11-12T10:43:07Z", "url": "https://x"}
        with mock.patch.dict(os.environ, {"TOK": "1"}):
            notifiers._post = lambda url, payload, headers=None, opener=None: sent.append(payload) or 200
            result = notifiers.send_channel("telegram", {"enabled": True, "token_env": "TOK", "chat_id": "1"}, event, opener=object())
        self.assertTrue(result["ok"], result)
        self.assertIn("11:43:07 CET (10:43:07 UTC)", sent[0]["text"])


class Setting(unittest.TestCase):
    def test_the_setting_is_in_the_schema_with_its_texts_in_the_eight_languages(self):
        self.assertIn("display.timezone", settings_api.FIELDS)
        self.assertEqual(settings_api.check_value("display.timezone", "Europe/Madrid"), (True, "Europe/Madrid"))
        self.assertEqual(settings_api.check_value("display.timezone", "utc"), (True, "utc"))
        self.assertFalse(settings_api.check_value("display.timezone", "a b; rm")[0])
        for lang in LANGS:
            cat = i18n.catalogue(lang)
            self.assertTrue(cat.get("cfg.f.display.timezone") and cat.get("cfg.h.display.timezone"), lang)

    def test_the_default_and_the_template_say_local(self):
        import actions_monitor as am
        self.assertEqual(am.DEFAULTS["display"], {"timezone": "local"})
        template = json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(template["display"]["timezone"], "local")

    def test_the_page_shows_the_zone_in_the_clocks_and_receives_the_setting(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("timeZoneName", page)
        self.assertIn("I18N.tz", page)
        self.assertIn("timeStyle:\"long\"", page)       # the clock of the bar at the foot
        import actions_monitor as am
        with mock.patch.dict(os.environ, {"MONITOR_TIMEZONE": TOKYO}):
            self.assertIn('"tz": "Asia/Tokyo"', am.render_page())


class UntilItChanges(unittest.TestCase):
    """The button of the alerts tab that silences an alert until the item changes."""

    def test_the_page_offers_the_button_only_when_the_alert_has_a_version_to_compare(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertRegex(page, r'\(a\.details\|\|\{\}\)\.updated\?`<button type="button" data-mc="alert"')
        self.assertIn("until_change", page)
        self.assertIn('T(onChange(a)?"ui.al_muted_change":"ui.al_muted_until"', page)

    def test_the_texts_exist_in_the_eight_languages(self):
        for lang in LANGS:
            cat = i18n.catalogue(lang)
            for key in ("ui.al_mute_change", "ui.al_mute_change_t", "ui.al_muted_change"):
                self.assertTrue(cat.get(key), f"{lang}: {key}")
            self.assertIn("{h}", cat["ui.al_mute_change_t"], lang)
            self.assertIn("{time}", cat["ui.al_muted_change"], lang)

    def test_the_silence_ends_when_the_item_changes_and_not_before(self):
        alert = {"id": "collab:r#1", "code": "c", "sentinel": "collab", "details": {"updated": "2026-11-12T10:00:00Z"}}
        entry = {"scope": "alert", "value": "collab:r#1", "until": "2099-01-01T00:00:00Z", "until_change": "2026-11-12T10:00:00Z"}
        self.assertEqual(alert_center.muted_until(alert, [entry]), "2099-01-01T00:00:00Z")
        alert["details"]["updated"] = "2026-11-12T11:00:00Z"
        self.assertIsNone(alert_center.muted_until(alert, [entry]))


if __name__ == "__main__":
    unittest.main()
