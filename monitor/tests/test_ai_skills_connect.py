# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The skills for the AIs do not depend on one assistant or one model, say how to connect by kind of tool and carry the version of the monitor."""
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor
from github_actions_monitor.integrations import skills
from github_actions_monitor.tool_version import TOOL_VERSION

HERE = Path(__file__).resolve().parent.parent
DOCS = HERE / "docs"
VENDORS = re.compile(r"(?i)\b(openai|anthropic|claude|gemini|copilot|cursor|chatgpt|codex|mistral|grok|deepseek|windsurf|aider|ollama|llama|lm studio)\b")
HAND_WRITTEN = {"internal": ("SKILL.md", "references/scenarios.md", "references/security.md", "references/learning.md"),
                "external": ("SKILL.md", "references/protocol.md", "references/scenarios.md", "references/security.md", "references/learning-cycle.md", "references/connect.md")}


class SkillsNameNoAssistant(unittest.TestCase):
    def test_the_instructions_name_no_company_or_assistant(self):
        for name, files in HAND_WRITTEN.items():
            for file in files:
                text = skills.read(name, file)
                self.assertIsNotNone(text, (name, file))
                self.assertIsNone(VENDORS.search(text), (name, file, VENDORS.search(text) and VENDORS.search(text).group(0)))

    def test_the_external_skill_has_the_five_ways_and_points_to_the_table(self):
        connect = skills.read("external", "references/connect.md")
        for way in ("read files", "make HTTP requests", "speak MCP", "keep a connection open", "run commands"):
            self.assertIn("| " + way + " |", connect)
        for command in ("bin/mcp_server.py", "/api/ai/brief", "/api/ai/stream", "monitor_cli.py", "ai doctor", "install-skill external"):
            self.assertIn(command, connect)
        self.assertIn("references/connect.md", skills.read("external"))
        self.assertIn("Version and compatibility", connect)
        self.assertLess(len(skills.read("external")), 6500)

    def test_the_list_of_skills_says_the_version_of_the_monitor(self):
        kind, document = actions_monitor.skills_get("")
        self.assertEqual(kind, "json")
        self.assertEqual(document["monitor_version"], TOOL_VERSION)
        self.assertEqual({s["version"] for s in document["skills"]}, {TOOL_VERSION})
        self.assertIn("references/connect.md", next(s for s in document["skills"] if s["name"] == "external")["files"])

    def test_every_language_has_the_table_of_ways_to_connect(self):
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (DOCS / f"AI_CONNECTION{suffix}.md").read_text(encoding="utf-8")
            self.assertIn("install-skill external --dest", text, suffix)
            self.assertIn("monitor_version", text, suffix)
            self.assertEqual(len(re.findall(r"^\| .* \| (?:`ai_alerts.enabled`|`ai_alerts.stream.enabled`) \|$", text, re.M)), 2, suffix)
            self.assertIn("python bin/mcp_server.py", text, suffix)


if __name__ == "__main__":
    unittest.main()
