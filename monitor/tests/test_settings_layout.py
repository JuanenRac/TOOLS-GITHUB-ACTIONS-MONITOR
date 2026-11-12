# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The order and structure of the settings menu: every setting in exactly one tab and block, texts in the eight languages, nothing forbidden, the page built with accessible tabs."""
import json
import re
import sys
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402
import settings_api as sa  # noqa: E402
import surface  # noqa: E402

FORGOTTEN = (
    "sentinel.hot_hours", "sentinel.minutes_budget", "sentinel.minutes_budget_period", "sentinel.a2_full_sample_unknown", "sentinel.skip_candidate_prefixes",
    "sentinel.required_files", "sentinel.audit_files.reconciliation", "sentinel.audit_files.rounds", "sentinel.audit_files.rounds_extra",
    "sentinel.readiness.pins.sources", "sentinel.readiness.pins.max_depth", "sentinel.readiness.pins.refresh_seconds", "webhook.enabled", "repos",
)
NEVER = ("sentinel.notify_command", "webhook.secret", "sentinel.signature_pubkeys", "ai.api_key")


class Layout(unittest.TestCase):
    def test_every_key_belongs_to_exactly_one_tab_and_block(self):
        seen = {}
        for tab, blocks in sa.layout():
            for block, keys in blocks:
                for key in keys:
                    self.assertNotIn(key, seen, key)
                    seen[key] = (tab, block)
        self.assertEqual(set(seen), set(sa.FIELDS))
        self.assertEqual(len(sa.ROWS), len(sa.FIELDS))      # no key twice in the schema

    def test_no_tab_and_no_block_is_empty_and_the_order_goes_from_common_to_advanced(self):
        layout = sa.layout()
        self.assertTrue(all(blocks and all(keys for _b, keys in blocks) for _t, blocks in layout))
        order = [tab for tab, _ in layout]
        self.assertEqual(order[:5], ["basic", "general", "polling", "cache", "quota"])
        self.assertLess(order.index("ai"), order.index("webhook"))
        self.assertLess(order.index("webhook"), order.index("notify"))
        self.assertLess(order.index("notify"), order.index("analytics"))
        self.assertEqual(order[-1], "console")
        self.assertLess(order.index("readiness"), order.index("paths"))
        self.assertLess(order.index("paths"), order.index("outputs"))
        self.assertLess(order.index("outputs"), order.index("ai"))

    def test_the_main_switch_comes_first_in_its_block(self):
        for _tab, blocks in sa.layout():
            for block, keys in blocks:
                if block.startswith("chk_"):
                    self.assertTrue(keys[0].endswith(".enabled"), keys[0])
                    self.assertEqual(sa.FIELDS[keys[0]][2], "bool")

    def test_every_check_of_a10_has_its_switch_and_its_parameters(self):
        for check, config in surface.DEFAULTS["checks"].items():
            self.assertIn(f"sentinel.surface.checks.{check}.enabled", sa.FIELDS)
            for param in config:
                if param in ("enabled", "required"):
                    continue
                self.assertIn(f"sentinel.surface.checks.{check}.{param}", sa.FIELDS, f"{check}.{param}")

    def test_the_forgotten_settings_are_in_and_the_dangerous_ones_are_out(self):
        for key in FORGOTTEN:
            self.assertIn(key, sa.FIELDS)
        for key in NEVER:
            self.assertNotIn(key, sa.FIELDS)
        weights = [k for k in sa.FIELDS if k.startswith("sentinel.readiness.health.weights.")]
        self.assertEqual(len(weights), 8)

    def test_every_unit_and_block_has_a_text_in_the_eight_languages(self):
        units = {meta["unit"] for meta in sa.META.values() if meta["unit"]}
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for unit in units:
                self.assertIn("ui.cfg_u_" + unit, cat, f"{lang} {unit}")
            for tab, blocks in sa.layout():
                self.assertIn("ui.cfg_g_" + tab, cat)
                for block, _keys in blocks:
                    self.assertIn(sa.block_title_key(block), cat, f"{lang} {block}")
        for key, (_t, _k, kind, bounds, _r) in sa.FIELDS.items():
            if kind in ("int", "float"):
                self.assertLessEqual(bounds[0], bounds[1], key)

    def test_the_template_value_of_every_setting_is_accepted(self):
        template = json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))
        for key, row in sa.FIELDS.items():
            value = sa._get(template, key, "\0missing")
            if value == "\0missing" or row[2] == "status":
                continue
            ok, why = sa.check_value(key, value)
            self.assertTrue(ok, f"{key}: {why}")

    def test_structured_values(self):
        self.assertEqual(sa.check_value("sentinel.minutes_budget", {"armor": 600}), (True, {"armor": 600}))
        self.assertFalse(sa.check_value("sentinel.minutes_budget", {"armor": -1})[0])
        self.assertFalse(sa.check_value("sentinel.minutes_budget", {"../x": 1})[0])
        self.assertTrue(sa.check_value("sentinel.required_files", [["README.md"], ["LICENSE", "LICENSE.md"]])[0])
        self.assertFalse(sa.check_value("sentinel.required_files", [["../secret"]])[0])
        self.assertFalse(sa.check_value("sentinel.required_files", [])[0])
        source = {"ecosystem": "armor", "kind": "pin_table", "provider": "ARMOR-COMMON", "file": "pins.json", "key": "consumers"}
        self.assertTrue(sa.check_value("sentinel.readiness.pins.sources", [source])[0])
        self.assertFalse(sa.check_value("sentinel.readiness.pins.sources", [dict(source, kind="shell")])[0])
        self.assertFalse(sa.check_value("sentinel.readiness.pins.sources", [dict(source, command="x")])[0])
        self.assertEqual(sa.check_value("repos", "all"), (True, "all"))
        self.assertTrue(sa.check_value("repos", ["A-1", "b.c"])[0])
        self.assertFalse(sa.check_value("sentinel.audit_files.rounds", "../x")[0])

    def test_the_webhook_state_never_leaks_the_secret(self):
        for secret, state in (("", "undefined"), ("short", "short"), ("x" * 40, "defined")):
            self.assertEqual(sa.webhook_state({"webhook": {"secret": secret}}), state)
        self.assertEqual(sa.webhook_state({}), "undefined")
        text = json.dumps(sa.describe(HERE / "nonexistent.json"))
        self.assertNotIn("xxxxxxxx", text)


class Guide(unittest.TestCase):
    """docs/SETTINGS*.md lists every setting of the schema (the part between the markers is written by tools/make_settings_doc.py)."""
    names = ("SETTINGS.md", "SETTINGS_spa.md", "SETTINGS_deu.md", "SETTINGS_fra.md", "SETTINGS_ita.md", "SETTINGS_jpn.md", "SETTINGS_zho.md", "SETTINGS_por.md")

    def test_every_key_is_in_the_eight_guides(self):
        for name in self.names:
            text = (HERE / "docs" / name).read_text(encoding="utf-8")
            self.assertIn("<!-- settings:begin -->", text, name)
            for key in sa.FIELDS:
                if ".checks." in key:
                    continue          # the checks are listed once per block as `sentinel.surface.checks.<name>.*`
                self.assertIn(f"`{key}`", text, f"{name}: {key}")
            for check in surface.DEFAULTS["checks"]:
                self.assertIn(f"sentinel.surface.checks.{check}.*", text, f"{name}: {check}")

    def test_the_guides_are_up_to_date_with_the_schema(self):
        import subprocess
        script = HERE.parent / "tools" / "make_settings_doc.py"
        if not script.is_file():
            self.skipTest("the generator lives in the repository, not in the zip of the monitor")
        done = subprocess.run([sys.executable, "-I", str(script), "--check"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class Page(unittest.TestCase):
    page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")

    def test_the_subtabs_are_accessible(self):
        for needle in ('id="cfg-tabs" role="tablist"', 'id="cfg-search"', "role=tabpanel", "aria-controls", "aria-selected", "ArrowRight", "ArrowLeft", '"Home"', '"End"',
                       'id="cfg-save"', 'id="cfg-discard"', "am-cfg-tab"):
            self.assertIn(needle, self.page, needle)

    def test_the_save_bar_is_outside_the_scrolling_area(self):
        self.assertRegex(self.page, r"#cfg-panels\{[^}]*overflow:auto")
        self.assertLess(self.page.index('id="cfg-panels"'), self.page.index('class="cfg-bar"'))

    def test_the_remembered_tab_goes_through_the_safe_store(self):
        self.assertIn('store.set("am-cfg-tab"', self.page)
        self.assertRegex(self.page, r"const store=\{get\(k\)\{try\{")


if __name__ == "__main__":
    unittest.main()
