# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Reading the page comfortably: density, less movement and a palette for colour blindness, updates that wait while you read, what is new after an update, the glossary and the limits of the analysis
(also at the end of the reports), the scope of the header filter, the states of the selectors, the actions of an empty or failed page, the touch targets of a phone and the contrast gate."""
import json
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api, toolconfig  # noqa: E402
from github_actions_monitor.reporting import tab_report  # noqa: E402
from github_actions_monitor.ui import glossary, whats_new  # noqa: E402

try:
    import check_contrast  # noqa: E402
except ImportError:
    check_contrast = None

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
EXTRAS = (HERE / "assets" / "static" / "ui_extras.js").read_text(encoding="utf-8")
LOG = """# Changelog

## [Unreleased]

### Added

- **Not yet released**: a thing.

## [2.1.7]

### Added

- **Third**: the third `thing` with a [link](https://example.com).
  It goes on a second line.
- **Fourth**: the fourth.

## [2.1.6]

### Added

- **Second**: the second.

## [2.1.5]

- **First**: the first.
"""


class WhatsNew(unittest.TestCase):
    def test_the_versions_and_their_entries_are_read_from_the_changelog(self):
        got = dict(whats_new.versions(LOG))
        self.assertEqual(list(got), ["2.1.7", "2.1.6", "2.1.5"])      # the unreleased entries are not "new" yet
        self.assertEqual(got["2.1.7"][0], "Third: the third thing with a link. It goes on a second line.")
        self.assertEqual(len(got["2.1.7"]), 2)

    def test_only_the_versions_after_the_last_seen_one_up_to_the_installed_one_are_given(self):
        rows = whats_new.since(LOG, "2.1.5", "2.1.7")
        self.assertEqual([r["version"] for r in rows], ["2.1.7", "2.1.6"])
        self.assertEqual([r["version"] for r in whats_new.since(LOG, "2.1.7", "2.1.7")], [])
        self.assertEqual([r["version"] for r in whats_new.since(LOG, "", "2.1.6")], ["2.1.6"])      # nothing seen yet: just the installed version
        self.assertEqual([r["version"] for r in whats_new.since(LOG, "2.1.5", "2.1.6")], ["2.1.6"])      # a version newer than the installed one is never shown

    def test_the_size_is_limited(self):
        log = "## [9.0.0]\n\n" + "".join(f"- entry {i} " + "x" * 600 + "\n" for i in range(30)) + "".join(f"## [8.0.{i}]\n\n- a\n\n" for i in range(9))
        rows = whats_new.since(log, "1.0.0", "9.0.0")
        self.assertEqual(len(rows), whats_new.MAX_VERSIONS)
        self.assertEqual((len(rows[0]["items"]), rows[0]["more"]), (whats_new.MAX_ENTRIES, 30 - whats_new.MAX_ENTRIES))
        self.assertTrue(all(len(x) <= whats_new.MAX_CHARS for x in rows[0]["items"]))

    def test_the_real_changelog_of_every_language_has_the_same_versions(self):
        english = [v for v, _ in whats_new.versions(whats_new.changelog_text("en"))]
        self.assertIn("2.1.5", english)
        for lang in LANGS[1:]:
            self.assertEqual([v for v, _ in whats_new.versions(whats_new.changelog_text(lang))], english, lang)

    def test_the_answer_keeps_a_wrong_version_out_and_the_switch_closes_it(self):
        self.assertEqual(whats_new.payload("en", "../x", "2.1.5", True)["seen"], "")
        self.assertEqual(whats_new.payload("en", "2.1.0", "2.1.5", False), {"enabled": False, "current": "2.1.5", "seen": "2.1.0", "versions": []})
        self.assertTrue(whats_new.payload("es", "2.1.0", "2.1.5", True)["versions"])


class Glossary(unittest.TestCase):
    def test_every_figure_is_defined_with_the_real_parameters(self):
        rows = glossary.metrics({"ci": {"red_events": ["push"], "inactive_days": 45, "red_age_days": 10}})
        self.assertEqual([r["id"] for r in rows], list(glossary.METRICS))
        red = rows[0]["definition"]
        self.assertIn("push", red)
        self.assertIn("45", red)
        self.assertIn("10", red)
        self.assertNotIn("{", red)
        self.assertIn(", ".join(am.redrule.RED_EVENTS), glossary.metrics({})[0]["definition"])      # the default events of the calculation, not a copy

    def test_every_text_exists_in_the_eight_languages_and_is_translated(self):
        keys = [f"gl.m.{m}.{p}" for m in glossary.METRICS for p in ("name", "def")] + [f"gl.a.{a}.{p}" for a in glossary.ATTACKS for p in ("name", "def")]
        keys += [f"ui.rx_limits_{n}" for n in range(1, glossary.LIMITS + 1)] + ["ui.rx_limits_title", "ui.rx_limits_col", "ui.gl_title", "ui.gl_metrics", "ui.gl_attacks", "ui.gl_resources"]
        for lang in LANGS:
            for key in keys:
                self.assertTrue(LOCALES[lang].get(key), (lang, key))
        for lang in LANGS[1:]:
            for key in [k for k in keys if k.endswith(".def") or "limits_" in k]:
                self.assertNotEqual(LOCALES[lang][key], LOCALES["en"][key], (lang, key))

    def test_the_payload_has_everything_and_the_links_are_public_documentation(self):
        got = glossary.payload({})
        self.assertEqual((len(got["metrics"]), len(got["attacks"]), len(got["limits"])), (len(glossary.METRICS), len(glossary.ATTACKS), glossary.LIMITS))
        self.assertTrue(all(r["url"].startswith("https://") for r in got["resources"]))
        self.assertTrue(all(not t.startswith(("gl.", "ui.")) for t in got["limits"] + [m["definition"] for m in got["metrics"]]))
        with i18n.use_language("es"):
            self.assertNotEqual(glossary.payload({})["limits"], got["limits"])


class ReportLimits(unittest.TestCase):
    def build(self, **kw):
        state = {"signals": [], "edition": "complete", "version": "9.9.9"}
        return tab_report.build("now", state, "en", i18n.tl, data={}, **kw)

    def test_the_limits_end_the_report_when_asked_and_only_then(self):
        plain, with_limits = self.build(), self.build(limits=True)
        if plain is None:
            self.skipTest("no tab report without the state of the AIs")
        self.assertEqual(len(with_limits["sections"]), len(plain["sections"]) + 1)
        last = with_limits["sections"][-1]
        self.assertEqual(last["title"], i18n.tl("en", "ui.rx_limits_title"))
        self.assertEqual(len(last["rows"]), 5)
        self.assertIn(last["rows"][0][0], tab_report.render_text(with_limits))

    def test_the_setting_is_on_by_default_and_a_wrong_value_keeps_it(self):
        self.assertIs(tab_report.settings({})["limits"], True)
        self.assertIs(tab_report.settings({"report_export": {"limits": False}})["limits"], False)
        self.assertIs(tab_report.settings({"report_export": {"limits": "no"}})["limits"], True)


class Settings(unittest.TestCase):
    KEYS = ("display.live_throttle_s", "display.whats_new", "display.density", "display.reduce_motion", "display.palette", "report_export.limits")

    def test_every_setting_is_registered_with_a_safe_default_its_example_and_its_words(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        for key in self.KEYS:
            self.assertIn(key, settings_api.META, key)
            node = example
            for part in key.split("."):
                node = node[part]
            for lang in LANGS:
                self.assertTrue(LOCALES[lang].get("cfg.f." + key) and LOCALES[lang].get("cfg.h." + key), (lang, key))
        d = am.DEFAULTS["display"]
        self.assertEqual((d["live_throttle_s"], d["whats_new"], d["density"], d["reduce_motion"], d["palette"]), (30, True, "normal", "auto", "default"))

    def test_the_values_are_checked(self):
        self.assertEqual(settings_api.check_value("display.density", "dense"), (True, "dense"))
        self.assertEqual(settings_api.check_value("display.density", "huge")[0], False)
        self.assertEqual(settings_api.check_value("display.palette", "colorblind"), (True, "colorblind"))
        self.assertEqual(settings_api.check_value("display.live_throttle_s", 301)[0], False)
        self.assertEqual(settings_api.check_value("display.reduce_motion", "off")[0], False)      # the preference of the system is never overridden by turning movement ON against it


class Page(unittest.TestCase):
    def test_the_words_the_page_uses_exist_in_the_eight_languages(self):
        keys = set(re.findall(r'"(ui\.(?:wn|gl|sel|es|scope|er|cls|al|pal)_[a-z_]+)"', EXTRAS))
        keys.discard("ui.er_err_")
        keys |= {f"ui.er_err_{c}" for c in ("off", "bad_repo", "bad_workflow", "no_reason", "no_owner", "full")}
        keys |= {f"ui.cls_{c}" for c in ("pr", "main", "nightly", "manual", "queue", "chained", "other")}
        keys |= set(re.findall(r'data-i18n="(ui\.(?:cls|al)_[a-z_]+)"', PAGE))
        for lang in LANGS:
            self.assertEqual([k for k in sorted(keys) if not LOCALES[lang].get(k)], [], lang)

    def test_the_filter_scope_names_every_tab_exactly_once(self):
        obeys = re.search(r'OBEYS=\[([^\]]*)\]', EXTRAS).group(1)
        glob = re.search(r'GLOBAL=\[([^\]]*)\]', EXTRAS).group(1)
        names = re.findall(r'"(\w+)"', obeys) + re.findall(r'"(\w+)"', glob)
        tabs = re.search(r'const TABS=LITE\?\[[^\]]*\]:\[([^\]]*)\]', PAGE).group(1)
        full = re.findall(r'"(\w+)"', tabs)
        self.assertEqual(sorted(names), sorted(full))

    def test_the_page_draws_with_the_new_rules_and_a_phone_gets_big_targets(self):
        for rule in (":root.dense", ":root.reduce-motion", ":root[data-palette=colorblind]", ".wn-bar", ".es-box", "pointer:coarse", "min-height:44px"):
            self.assertIn(rule, PAGE)
        self.assertIn('id="al-class"', PAGE)
        self.assertIn("reduce-motion", EXTRAS)
        self.assertIn("display.live_throttle_s", (HERE / "src" / "github_actions_monitor" / "app" / "settings_api.py").read_text(encoding="utf-8"))

    def test_the_page_left_to_a_person_shows_the_state_with_a_word_and_a_shape(self):
        self.assertIn("ui.es_alerts_clear", EXTRAS)
        self.assertIn('dataset.retry', EXTRAS)

    def test_the_rendered_page_carries_the_display_settings(self):
        page = am.render_page()
        self.assertIn('"display":{"live_throttle_s": 30', page.replace('"display": {', '"display":{'))
        self.assertIn("/*", page)


class Contrast(unittest.TestCase):
    def setUp(self):
        if check_contrast is None:
            self.skipTest("the tools of the repository are not in this folder")

    def test_no_pair_of_colours_of_any_theme_falls_under_the_minimum(self):
        self.assertEqual(check_contrast.problems(), [])

    def test_the_sixteen_themes_and_the_two_palettes_are_all_measured(self):
        names = set(check_contrast.themes())
        self.assertTrue({"dark", "light", "colorblind (dark)", "colorblind (light)", "High contrast", "Armor", "Blueprint"} <= names)
        self.assertEqual(len(names), 2 + 16 + 2)

    def test_the_gate_catches_a_pair_that_is_too_close_and_a_state_that_cannot_be_told_apart(self):
        text = PAGE.replace("--mut:#94a3b8", "--mut:#46506a", 1)
        self.assertTrue(any("--mut on --bg" in p for p in check_contrast.problems(text)))
        blind = PAGE.replace("--ok:#56b4e9;--bad:#e8702a", "--ok:#e8702a;--bad:#e8702a", 1)
        self.assertTrue(any("look alike" in p for p in check_contrast.problems(blind)))

    def test_the_ratio_is_the_wcag_one(self):
        self.assertAlmostEqual(check_contrast.ratio("#000000", "#ffffff"), 21.0, places=1)
        self.assertAlmostEqual(check_contrast.ratio("#777777", "#ffffff"), 4.48, places=1)

    def test_text_is_not_dimmed_with_opacity_more_than_it_was(self):
        self.assertLessEqual(check_contrast.opacity_rules(), check_contrast.OPACITY_BASELINE)


class Server(unittest.TestCase):
    def start(self, config):
        self.guard = _testenv.guard(unittest.TestCase())
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "actions_monitor.json"
        self.file.write_text(json.dumps(config), encoding="utf-8")
        self.saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE, dict(am.LIVE_CONFIG), settings_api.BACKUP_DIR)
        am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = self.file
        settings_api.BACKUP_DIR = Path(self.tmp.name) / "backups"
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, **config})
        toolconfig.forget()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        if getattr(self, "server", None):
            self.server.shutdown()
            self.server.server_close()
            am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE = self.saved[:3]
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(self.saved[3])
            settings_api.BACKUP_DIR = self.saved[4]
            toolconfig.forget()
            self.tmp.cleanup()
            self.guard()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=8) as answer:
                return answer.status, json.loads(answer.read())
        except urllib.error.HTTPError as error:
            return error.code, None

    def test_the_two_notes_answer_read_only_and_in_the_language_asked(self):
        self.start({})
        status, glossary_answer = self.get("/api/glossary")
        self.assertEqual(status, 200)
        self.assertEqual(len(glossary_answer["metrics"]), len(glossary.METRICS))
        status, news = self.get("/api/whats-new?since=2.1.0")
        self.assertEqual((status, news["enabled"], news["current"]), (200, True, am.TOOL_VERSION))
        self.assertTrue(news["versions"])
        self.assertEqual(self.get("/api/whats-new?since=../../x")[1]["seen"], "")

    def test_the_switch_of_the_notice_closes_the_answer(self):
        self.start({"display": {"whats_new": False}})
        status, news = self.get("/api/whats-new?since=2.1.0")
        self.assertEqual((status, news["enabled"], news["versions"]), (200, False, []))


if __name__ == "__main__":
    unittest.main()
