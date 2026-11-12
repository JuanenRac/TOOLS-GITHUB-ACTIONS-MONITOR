# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The help is always up to date: every setting has its help in the eight languages, and what the changelog announces (a setting, an endpoint) is written in the help or the guides."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import i18n  # noqa: E402
import settings_api  # noqa: E402

DOCS = HERE / "docs"
# groups that were written before this rule and share the help of their block: a NEW setting is not in this list and must carry its own cfg.h.<key> in the eight languages
SHARED_HELP = ("sentinel.surface.checks.", "sentinel.readiness.health.weights.", "lint.rules.", "notify.channels.")


class HelpSync(unittest.TestCase):
    def test_every_setting_has_its_label_and_its_help_in_the_eight_languages(self):
        missing = []
        for key in settings_api.FIELDS:
            for lang in i18n.LANGS:
                if i18n.tl(lang, "cfg.f." + key) == "cfg.f." + key and not key.startswith(SHARED_HELP):
                    missing.append(f"cfg.f.{key} ({lang})")
                if i18n.tl(lang, "cfg.h." + key) == "cfg.h." + key and not key.startswith(SHARED_HELP):
                    missing.append(f"cfg.h.{key} ({lang})")
        self.assertEqual(missing, [], "a setting without its help: add cfg.f.<key> and cfg.h.<key> to the eight locales")

    def test_every_tab_of_the_page_has_a_help_topic_in_the_eight_languages(self):
        import helpdocs
        index = __import__("json").loads((DOCS / "help_index.json").read_text(encoding="utf-8"))
        topics = {t.get("id") or t.get("key") or t.get("topic") for t in index["topics"] if isinstance(t, dict)}
        for tab, topic in helpdocs.TAB_TOPICS.items():
            self.assertIn(topic, topics, f"the tab {tab} has no help topic {topic}")

    def test_what_the_changelog_announces_is_in_the_help_or_the_guides(self):
        """Every setting (a.b.c) and every endpoint (/api/...) named in [Unreleased] must be written somewhere in docs/ (the generated list of settings counts)."""
        text = (HERE / "CHANGELOG.md").read_text(encoding="utf-8")
        match = re.search(r"## \[Unreleased\](.*?)(?=\n## \[)", text, re.S)
        if not match:
            self.skipTest("nothing is unreleased")
        corpus = "\n".join(p.read_text(encoding="utf-8") for p in DOCS.glob("*.md") if not p.name.startswith("CHANGELOG"))
        unknown = []
        for token in re.findall(r"`([^`\n]+)`", match.group(1)):
            setting = re.fullmatch(r"[a-z_]+(?:\.[a-z_]+)+", token) and not token.endswith((".md", ".json", ".py", ".jsonl", ".pem"))
            endpoint = token.startswith("GET /api/") or token.startswith("/api/")
            if not (setting or endpoint):
                continue
            probe = token.split(" ", 1)[-1] if endpoint else token
            probe = probe.split("?")[0].split("[")[0]
            if probe not in corpus:
                unknown.append(token)
        self.assertEqual(unknown, [], "announced in the changelog but not in the help or the guides")


if __name__ == "__main__":
    unittest.main()
