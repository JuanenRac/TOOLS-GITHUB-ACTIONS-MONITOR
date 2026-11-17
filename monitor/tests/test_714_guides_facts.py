# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Facts of the guides that were wrong and the code makes checkable, in the eight languages: the webhook checklist, what turning the wall screens off does, the tabs and the AI paths of the lite
edition, and the Python the launchers ask for."""
import json
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor

HERE = Path(__file__).resolve().parent.parent
DOCS = HERE / "docs"
SUFFIX = {"en": "", "es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}
TABS = ("now", "al", "charts", "sent", "sci", "scol", "ssec", "team", "fleet", "repos", "rep", "trep", "les", "hist", "cfg")


def guide(name, lang):
    path = DOCS / f"{name}{SUFFIX[lang]}.md"
    return path.read_text(encoding="utf-8") if path.is_file() else None


def texts(lang):
    return json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


class WebhookChecklist(unittest.TestCase):
    def test_the_checklist_does_not_ask_for_a_redelivery_to_show_in_the_live_view(self):
        """A redelivery reuses the delivery id (ignored as a repeat) and a `ping` names no repository, so it never reaches the Live view."""
        for lang in SUFFIX:
            text = guide("WEBHOOK", lang)
            if text is None:
                continue
            with self.subTest(lang=lang):
                for line in text.splitlines():
                    self.assertFalse("Redeliver" in line and "view=live" in line, line)
                self.assertIn("ping", next(ln for ln in text.splitlines() if "view=live" in ln and ln.startswith("3.")))


class ScreensOff(unittest.TestCase):
    def test_the_guide_names_the_addresses_that_answer_404_and_the_ones_that_do_not(self):
        for lang in SUFFIX:
            text = guide("SCREENS", lang)
            if text is None:
                continue
            row = next(ln for ln in text.splitlines() if ln.startswith("| `screens.enabled`"))
            with self.subTest(lang=lang):
                for address in ("/screen/overview", "/screen/now", "/screen/sentinels", "/api/screens/data", "/screen/1", "/screen/3"):
                    self.assertIn(address, row)

    def test_the_numbered_screens_do_not_depend_on_the_setting_in_the_code(self):
        source = Path(actions_monitor.__file__).read_text(encoding="utf-8")
        self.assertRegex(source, r're\.fullmatch\(r"/screen/\[1-3\]/\?", path\)')


class LiteGuide(unittest.TestCase):
    def test_the_complete_column_lists_every_tab_of_the_page(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        tabs = re.search(r'const TABS=LITE\?\[([^\]]*)\]:\[([^\]]*)\]', page)
        lite = re.findall(r'"(\w+)"', tabs.group(1))
        complete = re.findall(r'"(\w+)"', tabs.group(2))
        self.assertEqual(tuple(complete), TABS)
        for lang in SUFFIX:
            text = guide("LITE", lang)
            if text is None:
                continue
            labels = texts(lang)
            row = next(ln for ln in text.splitlines() if ln.startswith("|") and labels["ui.tab_sent"] in ln and labels["ui.tab_team"] in ln)
            with self.subTest(lang=lang):
                for tab in complete:
                    self.assertIn(labels["ui.tab_" + tab], row, tab)
                self.assertEqual(len(lite), 5)

    def test_the_ai_row_names_the_channels_the_lite_edition_does_serve(self):
        for channel in actions_monitor.LITE_SHARED:
            for lang in SUFFIX:
                text = guide("LITE", lang)
                if text is None:
                    continue
                with self.subTest(lang=lang, channel=channel):
                    self.assertIn(channel, text)


class PythonVersion(unittest.TestCase):
    def test_the_launchers_and_the_plain_readme_ask_for_the_python_the_readme_asks_for(self):
        needed = re.search(r"Python (\d+\.\d+)\+", (HERE.parent / "README.md").read_text(encoding="utf-8")) if (HERE.parent / "README.md").is_file() else None
        want = needed.group(1) if needed else "3.11"
        for name in ("README.txt", "BATCH_GITHUB_ACTIONS.sh", "MONITOR_GITHUB_ACTIONS.sh", "MONITOR_LITE_GITHUB_ACTIONS.sh"):
            text = (HERE / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertEqual(set(re.findall(r"Python (\d+\.\d+)\+", text)), {want})
        for name in ("BATCH_GITHUB_ACTIONS.sh", "MONITOR_GITHUB_ACTIONS.sh", "MONITOR_LITE_GITHUB_ACTIONS.sh"):
            self.assertIn("が見つかりません", (HERE / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
