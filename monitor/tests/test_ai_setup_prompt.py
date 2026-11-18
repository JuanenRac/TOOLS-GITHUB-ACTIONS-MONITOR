# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The prompt that sets the monitor up with an AI (docs/AI_SETUP_PROMPT*.md): it exists in the eight languages, travels in the zip of a release, lists the same settings in every language, names
only settings that exist in the template or in the schema of the Settings tab, keeps the dangerous switches off in the template it promises, points only to files of the package and is listed in the
Documentation of the README and in the index of the Help."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))

import _testenv  # noqa: F401,E402
import make_release  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402

TAILS = {"en": "", "es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}
DOCS = HERE / "docs"
EXAMPLE = HERE / "assets" / "examples" / "actions_monitor.example.json"
#: switches the prompt promises to leave off, with the value they have in the template
OFF = {"ai.actions.enabled": False, "ai.actions.execute": False, "github_actions.enabled": False, "act.enabled": False, "listen.network": False, "auth.enabled": False,
       "webhook.enabled": False, "chatops.enabled": False, "github_token.enabled": False, "notify.enabled": False, "ai.provider": "none"}


def flat(tree, prefix=""):
    found = {}
    for key, value in tree.items():
        found[prefix + key] = value
        if isinstance(value, dict):
            found.update(flat(value, prefix + key + "."))
    return found


def path_of(tail):
    return DOCS / f"AI_SETUP_PROMPT{tail}.md"


def prompt_of(tail):
    """The text inside the ```text box of one language."""
    text = path_of(tail).read_text(encoding="utf-8")
    found = re.search(r"```text\n(.*?)\n```", text, re.S)
    assert found, f"{path_of(tail).name}: no ```text box"
    return found.group(1)


def keys_of(tail):
    found = re.search(r"\[keys\]\n(.*?)\n\[/keys\]", prompt_of(tail), re.S)
    assert found, f"{path_of(tail).name}: no [keys] list"
    return [k.strip() for k in found.group(1).split(",") if k.strip()]


class TheFiles(unittest.TestCase):
    def test_the_prompt_exists_in_the_eight_languages_with_the_authorship(self):
        for lang, tail in TAILS.items():
            path = path_of(tail)
            self.assertTrue(path.is_file(), path.name)
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:6])
            self.assertIn(make_release.BRAND, head, path.name)
            self.assertIn(make_release.LICENSE_LINE, head, path.name)

    def test_every_language_links_the_eight_languages(self):
        for tail in TAILS.values():
            text = path_of(tail).read_text(encoding="utf-8")
            for other in TAILS.values():
                if other != tail:      # the language of the file is shown in bold, without a link
                    self.assertTrue(f"(AI_SETUP_PROMPT{other}.md)" in text, f"{path_of(tail).name} does not link {path_of(other).name}")
            self.assertEqual(sum(1 for line in text.splitlines()[:8] if line.count("](AI_SETUP_PROMPT") == 7), 1, path_of(tail).name)

    def test_the_eight_files_travel_in_the_zip_of_a_release(self):
        names = {p.relative_to(HERE).as_posix() for p in make_release.members()}
        for tail in TAILS.values():
            self.assertIn(f"docs/AI_SETUP_PROMPT{tail}.md", names)

    def test_the_prompt_is_a_text_for_the_public(self):
        for tail in TAILS.values():
            text = path_of(tail).read_text(encoding="utf-8")
            self.assertEqual(make_release.privacy_problems({f"docs/{path_of(tail).name}": text.encode("utf-8")}), [])
            self.assertNotRegex(text, r"(?i)claude|co-authored|generated with")


class TheSettings(unittest.TestCase):
    def setUp(self):
        self.template = flat(json.loads(EXAMPLE.read_text(encoding="utf-8")))
        self.known = set(settings_api.FIELDS) | set(flat(actions_monitor.DEFAULTS)) | set(self.template)
        self.groups = {key.split(".")[0] for key in self.known}

    def test_every_language_lists_the_same_settings(self):
        english = keys_of("")
        self.assertEqual(len(english), len(set(english)), "a setting is listed twice")
        for tail in TAILS.values():
            self.assertEqual(keys_of(tail), english, path_of(tail).name)

    def test_every_listed_setting_exists_in_the_template_or_the_settings_schema(self):
        for key in keys_of(""):
            self.assertTrue(key in self.template or key in settings_api.FIELDS or key in flat(actions_monitor.DEFAULTS), f"{key} is not a setting of the monitor")

    def test_no_text_of_the_prompt_names_a_setting_that_is_not_listed_and_real(self):
        listed = set(keys_of(""))
        for tail in TAILS.values():
            for token in sorted(set(re.findall(r"(?<![\w./-])([a-z_]+(?:\.[a-z_]+)+)(?![\w/-])", prompt_of(tail)))):
                if token.split(".")[0] not in self.groups:
                    continue      # a file name or an address, not a setting
                self.assertIn(token, self.known, (path_of(tail).name, token))
                self.assertIn(token, listed, (path_of(tail).name, token, "a setting the prompt names must be in its [keys] list"))

    def test_the_switches_the_prompt_promises_to_leave_off_are_off_in_the_template(self):
        for key, value in OFF.items():
            self.assertEqual(self.template.get(key), value, key)
            self.assertIn(key, keys_of(""))

    def test_the_defaults_the_prompt_recommends_are_those_of_the_template(self):
        self.assertEqual((self.template["refresh_seconds"], self.template["cold_refresh_seconds"], self.template["min_rate_remaining"]), (120, 1200, 1500))
        self.assertEqual(self.template["sentinel.budget_per_hour"], 600)
        self.assertEqual(self.template["notify.max_per_hour"], 20)
        self.assertEqual(self.template["ai.daily_limit"], 30)
        self.assertEqual(actions_monitor.DEFAULTS["ports"], {"complete": 8765, "lite": 8766})
        text = prompt_of("")
        for number in ("120 and 1200", "1500", "600 calls", "20)", "(30)", "8765", "8766"):
            self.assertTrue(number in text, number)
        for event in self.template["notify.events"]:
            self.assertTrue(event in text, event)


class TheReferences(unittest.TestCase):
    def test_every_file_the_prompt_points_to_is_in_the_package(self):
        for tail in TAILS.values():
            text = prompt_of(tail)
            for ref in sorted(set(re.findall(r"\b((?:assets/examples|bin|tools|docs)/[A-Za-z0-9_./-]*[A-Za-z0-9]\.(?:json|py|md))", text))):
                self.assertTrue((HERE / ref).is_file(), (path_of(tail).name, ref))
            for launcher in sorted(set(re.findall(r"\b(MONITOR_(?:LITE_)?GITHUB_ACTIONS\.(?:bat|sh|command))", text))):
                self.assertTrue((HERE / launcher).is_file(), (path_of(tail).name, launcher))
            self.assertIn("github_actions_monitor.zip", text)
            self.assertIn("SHA256SUMS", text)

    def test_the_commands_of_the_prompt_exist(self):
        cli = (HERE / "src" / "github_actions_monitor" / "cli" / "monitor_cli.py").read_text(encoding="utf-8")
        for command in ("doctor", "status", "update"):
            self.assertIn(f'"{command}"', cli, command)
        main = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        for flag in ("--doctor", "--demo", "--lite"):
            self.assertIn(flag, main, flag)

    def test_the_zip_name_is_the_one_the_build_writes(self):
        self.assertIn('"github_actions_monitor.zip"', (HERE / "tools" / "make_release.py").read_text(encoding="utf-8"))


@unittest.skipUnless(all((ROOT / f"README{t}.md").is_file() for t in TAILS.values()), "the README of the repository does not travel in the zip of a release")
class TheHelp(unittest.TestCase):
    def test_every_readme_lists_the_prompt_in_its_language(self):
        for tail in TAILS.values():
            text = (ROOT / f"README{tail}.md").read_text(encoding="utf-8")
            self.assertEqual(text.count(f"(monitor/docs/AI_SETUP_PROMPT{tail}.md)"), 1, tail)

    def test_the_index_of_the_help_has_the_topic_in_the_eight_languages(self):
        index = json.loads((DOCS / "help_index.json").read_text(encoding="utf-8"))
        topic = next(t for t in index["topics"] if t["id"] == "ai_setup_prompt")
        self.assertEqual(sorted(topic["sections"]), sorted(TAILS))
        for tail in TAILS.values():
            self.assertEqual(index["files"][f"AI_SETUP_PROMPT{tail}.md"], "ai_setup_prompt")


if __name__ == "__main__":
    unittest.main()
