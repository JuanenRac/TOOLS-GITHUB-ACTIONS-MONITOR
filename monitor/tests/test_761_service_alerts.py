# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The workflows GitHub makes for itself and their alerts: a failing "Dependabot Updates" is an alert of its own with medium severity (level warning), the activity of Copilot is information (level info,
off by default) and neither is ever a red of the repository. Both have a switch, can be silenced like any alert and have their texts in eight languages."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_241_dynamic_services as dyn  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402
from github_actions_monitor.sentinels import alert_center, sentinel_ci, sentinel_local  # noqa: E402


def services_of(cases):
    """The rows of the services as the sentinel builds them: the real shapes of the API go through the real parser."""
    runs = []
    for number, case in enumerate(cases, 1):
        repo, path, name, event = case
        runs += actions_monitor.parse_runs(repo.split("/")[1], {"workflow_runs": [dyn.api_run(repo, path, name, event, rid=number)]})
    return redrule.service_rows(runs, now=dyn.NOW)


def alerts_for(rows, config=None):
    snap = {"enabled": True, "generated": "2030-01-01T00:00:00Z", "loading": "", "level": "ok", "errors": [], "a2": {"red": [], "services": rows}, "a5": {"pending_sign": []}, "a1": {"stuck": []}, "totals": {}}
    redrule.configure(config or {})
    try:
        from test_171 import ctx_stub
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sentinel_local, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sentinel_local, "HISTORY_FILE", Path(tmp) / "h.json"):
            ci = sentinel_ci.SentinelCI(ctx_stub(), {})
            ci.core.last_snap = snap
            return ci.get_alerts()
    finally:
        redrule.configure({})


class TheAlerts(unittest.TestCase):
    def setUp(self):
        self.rows = services_of(dyn.MEASURED)

    def test_a_failing_dependabot_update_is_an_alert_of_its_own_with_medium_severity(self):
        found = [a for a in alerts_for(self.rows) if a["code"] == "ci.dependabot_failed"]
        self.assertEqual(sorted(a["repo"] for a in found), ["hashcat", "sumatrapdf"])
        self.assertEqual({a["level"] for a in found}, {"warning"})
        self.assertEqual(len({a["id"] for a in found}), 2, "one alert for each repository, with its own identity")
        self.assertTrue(all("Dependabot" in a["title"] and a["repo"] in a["title"] for a in found))

    def test_copilot_is_information_never_an_error_and_only_when_asked_for(self):
        self.assertEqual([a for a in alerts_for(self.rows) if a["code"] == "ci.copilot_activity"], [], "off by default")
        found = [a for a in alerts_for(self.rows, {"ci": {"copilot_alerts": True}}) if a["code"] == "ci.copilot_activity"]
        self.assertEqual(sorted(a["repo"] for a in found), ["alacritty", "bat", "firecracker"])
        self.assertEqual({a["level"] for a in found}, {"info"})
        self.assertEqual(len({a["id"] for a in found}), 3)

    def test_the_other_services_never_make_an_alert_and_none_is_red(self):
        codes = {a["code"] for a in alerts_for(self.rows, {"ci": {"copilot_alerts": True}})}
        self.assertEqual(codes, {"ci.dependabot_failed", "ci.copilot_activity"}, "no alert for the dependency graph or the default CodeQL")
        self.assertNotIn("ci.red", codes)
        held = redrule.states({r["repo"]: [] for r in self.rows}, {}, True)
        self.assertEqual(held.get("red", []), [])

    def test_the_switch_of_dependabot_turns_its_alert_off(self):
        self.assertEqual([a for a in alerts_for(self.rows, {"ci": {"dependabot_alerts": False}}) if a["code"] == "ci.dependabot_failed"], [])

    def test_the_levels_of_the_rows_are_the_ones_the_alerts_follow(self):
        self.assertEqual({r["service"]: r["level"] for r in self.rows if r["service"] in ("dependabot", "copilot")}, {"dependabot": "warning", "copilot": "info"})

    def test_a_green_run_after_the_failure_clears_the_alert(self):
        failed = ("sumatrapdfreader/sumatrapdf", "dynamic/dependabot/dependabot-updates", "Dependabot Updates", "dynamic")
        runs = actions_monitor.parse_runs("sumatrapdf", {"workflow_runs": [dyn.api_run(failed[0], failed[1], failed[2], failed[3], rid=1, days=2),
                                                                      dyn.api_run(failed[0], failed[1], failed[2], failed[3], rid=2, conclusion="success", days=1)]})
        self.assertEqual(redrule.service_rows(runs, now=dyn.NOW), [])

    def test_the_alert_can_be_silenced_by_its_code_like_any_other(self):
        alerts = [a for a in alerts_for(self.rows) if a["code"] == "ci.dependabot_failed"]
        self.assertEqual(len(alerts), 2)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(alert_center, "STATE_FILE", Path(tmp) / "m.json"):
            self.assertIsNotNone(alert_center.mute("code", "ci.dependabot_failed", 1, None, now=1000))
            live = alert_center.active(now=1001)
            self.assertTrue(all(alert_center.muted_until(a, live) for a in alerts))


class TheSettings(unittest.TestCase):
    def test_defaults_rows_and_texts_in_eight_languages(self):
        ci = actions_monitor.DEFAULTS["ci"]
        self.assertEqual((ci["dependabot_alerts"], ci["copilot_alerts"]), (True, False))
        redrule.configure({})
        self.assertEqual((redrule.POLICY["dependabot_alerts"], redrule.POLICY["copilot_alerts"]), (True, False))
        redrule.configure({"ci": {"dependabot_alerts": False, "copilot_alerts": True}})
        self.assertEqual((redrule.POLICY["dependabot_alerts"], redrule.POLICY["copilot_alerts"]), (False, True))
        redrule.configure({"ci": {"dependabot_alerts": "no", "copilot_alerts": "yes"}})
        self.assertEqual((redrule.POLICY["dependabot_alerts"], redrule.POLICY["copilot_alerts"]), (True, False), "a value that is not a switch keeps the default")
        redrule.configure({})
        for key in ("ci.dependabot_alerts", "ci.copilot_alerts"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in i18n.LANGS:
                for prefix in ("cfg.f.", "cfg.h."):
                    self.assertNotEqual(i18n.tl(lang, prefix + key), prefix + key, (lang, key))
        for key in ("evt.dependabot_failed", "evt.copilot_activity"):
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual((example["ci"]["dependabot_alerts"], example["ci"]["copilot_alerts"]), (True, False))


if __name__ == "__main__":
    unittest.main()
