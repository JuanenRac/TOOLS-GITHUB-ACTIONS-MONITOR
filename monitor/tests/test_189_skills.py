# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two skills of the monitor (skills/internal for the AI built into the monitor, skills/external for the AIs that talk to it): they cover everything the code lets a person or an AI touch
(a test reads the endpoints, the commands, the settings, the files and the tabs from the code and fails when one is not named), they travel in the package, they are installed without overwriting
what is not theirs, the page shows them and the AI of the monitor gets the core of the first one in its prompt."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(TOOLS))
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.integrations import ai_index, skills  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402

try:
    import make_skill_refs  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    make_skill_refs = None


def corpus(name):
    return "\n".join((HERE / "skills" / name / f).read_text(encoding="utf-8") for f in skills.files(name))


class TheFiles(unittest.TestCase):
    def test_each_skill_has_a_front_matter_a_short_core_and_its_references(self):
        for name in skills.names():
            text = skills.read(name)
            self.assertRegex(text, rf"\A---\nname: github-actions-monitor-{name}\ndescription: .{{80,}}\n---\n", name)
            self.assertLess(len(text), 6500, "the core stays short: a small local model must be able to take it")
            for reference in re.findall(r"`(references/[a-z-]+\.md)`", text):
                self.assertIn(reference, skills.files(name), (name, reference))
        self.assertTrue({"references/scenarios.md", "references/security.md", "references/learning.md", "references/providers.md"} <= set(skills.files("internal")))
        self.assertTrue({"references/protocol.md", "references/learning-cycle.md", "references/scenarios.md", "references/security.md", "references/cli.md"} <= set(skills.files("external")))

    def test_nothing_private_travels_in_a_skill(self):
        for name in skills.names():
            text = corpus(name)
            for word in ("SONNET", "Claude", "MON-", "2026-"):
                self.assertNotIn(word, text, (name, word))

    def test_the_scenarios_are_all_there(self):
        for name in skills.names():
            text = (HERE / "skills" / name / "references" / "scenarios.md").read_text(encoding="utf-8")
            for scenario in ("A real red", "A transient red", "Low quota", "A degraded monitor", "A repeated failure", "A new lesson", "No network", "Several screens"):
                self.assertIn("## " + scenario, text, (name, scenario))

    def test_the_endpoints_a_skill_cites_exist_in_the_code(self):
        if make_skill_refs is None:
            self.skipTest("the tools folder does not travel in the zip")
        known = set(make_skill_refs.endpoints())
        for name in skills.names():
            for path in re.findall(r"`(/api/[a-z0-9/_-]*[a-z0-9_-])[`?]", corpus(name)):
                self.assertIn(path, known, (name, path))


@unittest.skipIf(make_skill_refs is None, "the tools folder does not travel in the zip of a release")
class NothingIsLeftOut(unittest.TestCase):
    def test_the_generated_references_are_the_ones_the_code_gives(self):
        for path, text in make_skill_refs.outputs().items():
            self.assertEqual(path.read_text(encoding="utf-8").replace("\r\n", "\n"), text.replace("\r\n", "\n"), f"{path.name} is out of date: python tools/make_skill_refs.py")

    def test_every_endpoint_command_setting_file_and_tab_of_the_code_is_named_in_both_skills(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        tabs = set(re.findall(r'data-tab="([a-z]+)"', page))
        files = {row[0] for row in ai_index.FILES} | {"failures.jsonl", "lessons.json", "lessons_rules.json"}
        for name in skills.names():
            text = corpus(name)
            missing = [p for p in make_skill_refs.endpoints() if f"`{p}`" not in text]
            missing += [f"setting {k}" for k in settings_api.FIELDS if f"`{k}`" not in text]
            missing += [f"file {f}" for f in sorted(files) if f"`{f}`" not in text]
            missing += [f"tab {t}" for t in sorted(tabs) if f"`{t}`" not in text]
            self.assertEqual(missing, [], f"{name}: something in the code is not described to the AIs; add a note in tools/make_skill_refs.py")
        for name in skills.names():
            text = corpus(name)
            lost = [s for s in make_skill_refs.signal_ids() if f"`{s}`" not in text] + [p for p in make_skill_refs.panel_ids() if f"`{p}`" not in text]
            self.assertEqual(lost, [], f"{name}: a signal or a panel of the code is not named")
        external = corpus("external")
        self.assertEqual([c for c in monitor_cli.COMMANDS if f"`{c}`" not in external], [])
        for flag in (a for a in monitor_cli.build_parser()._actions if a.option_strings):
            self.assertIn(flag.option_strings[-1] if flag.option_strings[-1].startswith("--") else flag.option_strings[0], external)

    def test_a_new_signal_without_a_note_stops_the_generator(self):
        with mock.patch.object(make_skill_refs, "signal_ids", return_value=["now.brand-new"]), self.assertRaises(SystemExit):
            make_skill_refs.signals_md()

    def test_a_new_endpoint_without_a_note_stops_the_generator(self):
        with mock.patch.object(make_skill_refs, "endpoints", return_value=["/api/brand-new"]), self.assertRaises(SystemExit):
            make_skill_refs.api_md()

    def test_the_roles_and_the_classes_of_alerts_are_in_the_skills(self):
        from github_actions_monitor.security import auth
        for name in skills.names():
            text = corpus(name)
            for role in auth.ROLES:
                self.assertIn(f"`{role}`", text, (name, role))
            for word in ("real", "transient", "watch", "act", "critical"):
                self.assertIn(f"`{word}`", text, (name, word))

    def test_the_coverage_table_names_every_kind(self):
        text = (HERE / "skills" / "COVERAGE.md").read_text(encoding="utf-8")
        for kind in ("endpoints", "commands", "settings", "files", "roles", "tabs", "classes", "signals", "panels"):
            self.assertRegex(text, rf"\| {kind} \| \d+ \|")


class InThePackage(unittest.TestCase):
    def test_the_package_carries_both_skills_with_their_references(self):
        sys.path.insert(0, str(HERE / "tools"))
        import make_release
        names = {p.relative_to(HERE).as_posix() for p in make_release.members()}
        for name in skills.names():
            for file in skills.files(name):
                self.assertIn(f"skills/{name}/{file}", names)
        self.assertEqual(make_release.check_entries([f"github_actions_monitor/skills/{n}/SKILL.md" for n in skills.names()]), [])


class TheInstaller(unittest.TestCase):
    def test_it_writes_the_skill_and_a_second_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = skills.install("internal", tmp)
            self.assertTrue(first["ok"])
            self.assertEqual(len(first["written"]), len(skills.files("internal")))
            self.assertTrue((Path(tmp) / "github-actions-monitor-internal" / "SKILL.md").is_file())
            second = skills.install("internal", tmp)
            self.assertEqual((second["ok"], second["written"], len(second["same"])), (True, [], len(skills.files("internal"))))

    def test_it_never_overwrites_a_file_that_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills.install("external", tmp)
            mine = Path(tmp) / "github-actions-monitor-external" / "SKILL.md"
            mine.write_text("my own notes", encoding="utf-8")
            result = skills.install("external", tmp)
            self.assertFalse(result["ok"])
            self.assertEqual(result["kept"], ["SKILL.md"])
            self.assertEqual(mine.read_text(encoding="utf-8"), "my own notes")

    def test_it_refuses_a_bad_name_or_destination(self):
        self.assertEqual(skills.install("other", "x")["error"], "name")
        for dest in ("", "D:\\skills", "d:/x", "/mnt/d/x", "\\\\server\\share", "//server/share", "a\x00b"):
            self.assertEqual(skills.install("internal", dest)["error"], "dest", dest)

    def test_only_files_of_the_closed_list_can_be_read(self):
        for bad in ("../../README.md", "references/../SKILL.md", "SKILL.md.bak", "references/x.txt", "/etc/passwd"):
            self.assertIsNone(skills.read("internal", bad), bad)
        self.assertIsNone(skills.read("nope", "SKILL.md"))

    def test_the_command_line_installs_it_without_a_running_monitor(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(monitor_cli.main(["install-skill", "internal", "--dest", tmp]), 0)
            self.assertEqual(monitor_cli.main(["install-skill", "internal", "--dest", tmp]), 0)
            (Path(tmp) / "github-actions-monitor-internal" / "SKILL.md").write_text("mine", encoding="utf-8")
            self.assertNotEqual(monitor_cli.main(["install-skill", "internal", "--dest", tmp]), 0)
        self.assertNotEqual(monitor_cli.main(["install-skill", "internal"]), 0)
        self.assertNotEqual(monitor_cli.main(["install-skill", "--dest", "x"]), 0)


class ThePromptAndThePage(unittest.TestCase):
    def test_the_core_goes_into_the_prompt_of_the_ai_of_the_monitor_and_is_cut_to_the_size(self):
        core = skills.core("internal", 1500)
        self.assertTrue(core.startswith("# You are the AI inside the GitHub Actions Monitor"))
        self.assertLessEqual(len(core), 1500)
        self.assertLessEqual(len(skills.core("internal", 5)), 300, "never smaller than 300")
        system, _user = sentinel_ai.build_prompt("build", "log", "n1", "English", "", core)
        self.assertIn("Guide:", system)
        self.assertIn("UNTRUSTED DATA", system)
        self.assertNotIn("Guide:", sentinel_ai.build_prompt("build", "log", "n1", "English")[0])

    def test_explain_uses_it_only_when_it_is_on(self):
        seen = []

        def transport(cfg, system, user):
            seen.append(system)
            return "ok"
        store = sentinel_ai.Store(Path(tempfile.mkdtemp()) / "c.json")
        for flag in (True, False):
            cfg = sentinel_ai.ai_config({"ai": {"provider": "ollama", "skill": flag, "events": ["build"]}})
            sentinel_ai.explain("build", f"data {flag}", cfg, store, transport)
        self.assertIn("Guide:", seen[0])
        self.assertNotIn("Guide:", seen[1])
        self.assertEqual(sentinel_ai.ai_config({"ai": {"skill_max_chars": 5}})["skill_max_chars"], 300)

    def test_the_endpoint_serves_the_skills_and_nothing_else(self):
        from test_164 import LiveServer
        with LiveServer({"session_guard": True}) as server:
            status, body = server.call("/api/skills")
            self.assertEqual({s["name"] for s in body["skills"]}, {"internal", "external"})
            self.assertIn("name: github-actions-monitor-internal", server.call("/api/skills?name=internal")[1])
            self.assertIn("Security", server.call("/api/skills?name=external&file=references/security.md")[1])
            whole = server.call("/api/skills?name=external&all=1")[1]
            self.assertIn("The self-learning cycle", whole)
            self.assertEqual(server.call("/api/skills?name=internal&file=../../README.md")[0], 404)
            self.assertEqual(server.call("/api/skills?name=nope")[0], 404)

    def test_the_page_has_the_buttons_and_the_texts_exist_in_the_eight_languages(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ("sk-extra", "data-skc", "data-skd", "/api/skills?name="):
            self.assertIn(needle, page, needle)
        keys = ["ui.sk_h", "ui.sk_help", "ui.sk_internal", "ui.sk_external", "ui.sk_copy", "ui.sk_download", "ui.sk_copied", "cli.skill_action", "cli.skill_dest", "cli.skill_done", "cli.skill_kept", "cli.help_dest"]
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(catalogue.get(key), (lang, key))
        for key in ("ai.skill", "ai.skill_max_chars"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "cfg.f." + key), "cfg.f." + key)
                self.assertNotEqual(i18n.tl(lang, "cfg.h." + key), "cfg.h." + key)

    def test_registering_failures_from_outside_needs_the_switch(self):
        from github_actions_monitor.app import actions_monitor as am
        with mock.patch.object(am.toolconfig, "raw_config", return_value={}):
            self.assertEqual(am.handle_advanced_post("/api/ai/failures", {"lines": "x"})["status"], "write_off")


if __name__ == "__main__":
    unittest.main()
