# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Profiles: ready-made groups of settings. Only settings that exist and values that the Settings page accepts are written, a missing setting never breaks a profile, nothing is applied
by itself, and the page and the first-start guide offer them. Synthetic configuration files in a temporary folder."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import profiles  # noqa: E402
from github_actions_monitor.app import settings_api as sa  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
FAKE = {"owner_team": {"sentinel.stale_pr_days": 7, "discovery.events": True, "no.such.setting": 1}, "solo_developer": {"sentinel.stale_pr_days": 30, "discovery.events": False, "sentinel.workers": 999}}


class Profiles(unittest.TestCase):
    def test_three_profiles_in_order(self):
        self.assertEqual(profiles.ORDER, ("owner_team", "open_source_org", "solo_developer"))
        self.assertEqual(set(profiles.PRESETS), set(profiles.ORDER))

    def test_every_value_that_a_profile_names_is_accepted_by_the_page(self):
        for name, values in profiles.PRESETS.items():
            for key, value in values.items():
                if key in sa.FIELDS:
                    self.assertTrue(sa.check_value(key, value)[0], f"{name}: {key}")

    def test_the_owner_profile_is_the_strict_one_and_the_others_loosen_it(self):
        strict = profiles.PRESETS["owner_team"]
        for name in ("open_source_org", "solo_developer"):
            self.assertEqual(set(profiles.PRESETS[name]), set(strict), name)      # the same settings, other values: choosing one profile after another leaves nothing behind
            self.assertNotEqual(profiles.PRESETS[name], strict)

    def test_a_missing_or_refused_setting_is_left_out_not_an_error(self):
        with mock.patch.dict(profiles.PRESETS, FAKE):
            self.assertEqual(profiles.changes("owner_team"), {"sentinel.stale_pr_days": 7, "discovery.events": True})
            self.assertEqual(profiles.changes("solo_developer"), {"sentinel.stale_pr_days": 30, "discovery.events": False})      # sentinel.workers=999 is out of range
        self.assertIsNone(profiles.changes("nonsense"))

    def test_the_listing_for_the_page(self):
        with mock.patch.dict(profiles.PRESETS, FAKE):
            listing = profiles.listing()
        self.assertEqual([p["id"] for p in listing], list(profiles.ORDER))
        self.assertEqual(listing[0]["settings"], {"sentinel.stale_pr_days": 7, "discovery.events": True})
        self.assertEqual(profiles.listing(lite=True), [])      # the short page of the Lite edition has none

    def test_describe_carries_them_and_nothing_is_applied_by_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions_monitor.json"
            path.write_text(json.dumps({"sentinel": {"stale_pr_days": 3}}), encoding="utf-8")
            with mock.patch.dict(profiles.PRESETS, FAKE):
                page = sa.describe(path)
                self.assertEqual([p["id"] for p in page["presets"]], list(profiles.ORDER))
                self.assertEqual(sa.describe(path, lite=True)["presets"], [])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"sentinel": {"stale_pr_days": 3}})

    def test_applying_one_goes_through_the_checked_path_and_keeps_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sa, "BACKUP_DIR", Path(tmp) / "backups"):
            path = Path(tmp) / "actions_monitor.json"
            path.write_text(json.dumps({"github_owner": "someone", "sentinel": {"stale_pr_days": 3}}), encoding="utf-8")
            with mock.patch.dict(profiles.PRESETS, FAKE):
                changes = profiles.changes("solo_developer")
            clean, errors = sa.validate(changes)
            self.assertEqual(errors, {})
            sa.apply(clean, path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((saved["github_owner"], saved["sentinel"]["stale_pr_days"], saved["discovery"]["events"]), ("someone", 30, False))


class Page(unittest.TestCase):
    def test_the_texts_exist_in_the_eight_languages(self):
        keys = ["ui.preset_title", "ui.preset_hint", "ui.preset_applied", "ui.wiz_profile"] + [f"ui.preset_{n}{s}" for n in profiles.ORDER for s in ("", "_d")]
        for lang in i18n.LANGS:
            for key in keys:
                self.assertNotEqual(i18n.tl(lang, key), key, f"{key} ({lang})")

    def test_the_page_and_the_first_start_guide_offer_them(self):
        html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("function presetBox(presets)", html)
        self.assertIn("presetApply(", html)
        self.assertIn("wiz-preset", html)
        self.assertIn('g.id==="basic"', html)

    def test_the_guide_for_large_accounts_exists_in_the_eight_languages(self):
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"LARGE_ACCOUNTS{suffix}.md").read_text(encoding="utf-8")
            self.assertIn("discovery.fork_policy", text, suffix)
            self.assertIn("sentinel.budget_per_hour", text, suffix)


if __name__ == "__main__":
    unittest.main()
