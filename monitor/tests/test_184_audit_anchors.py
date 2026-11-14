# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A check of a name, an identifier or an address with `^...$` lets a trailing line feed through (`$` also matches just before the last "\\n"), so "alpha\\n" would pass as an account id, a
repository name or a key. Every such check ends in `\\Z`; this test keeps it that way and proves the places that matter with the value that used to pass."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.accounts import accounts  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import graphql_checks  # noqa: E402
from github_actions_monitor.integrations import mcp_server, runners  # noqa: E402
from github_actions_monitor.security import auth, webhook  # noqa: E402
from github_actions_monitor.storage import base  # noqa: E402

SOURCE = HERE / "src" / "github_actions_monitor"
CHECK = re.compile(r're\.compile\(r"\^[^\n]*?\$"\s*[,)]')
MULTILINE = re.compile(r"re\.M\b|re\.MULTILINE")


class EveryCheckEndsInTheEndOfTheText(unittest.TestCase):
    def test_no_name_check_ends_in_a_dollar(self):
        found = []
        for path in sorted(SOURCE.rglob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if CHECK.search(line) and not MULTILINE.search(line):
                    found.append(f"{path.relative_to(SOURCE).as_posix()}:{number}")
        self.assertEqual(found, [], "end these checks with \\Z, not $")

    def test_every_compiled_check_of_the_modules_refuses_a_trailing_line_feed(self):
        checked = 0
        for module in (accounts, settings_api, graphql_checks, mcp_server, runners, auth, webhook, base):
            for name, value in vars(module).items():
                if name.endswith("_RE") and isinstance(value, re.Pattern) and value.pattern.startswith("^") and value.pattern.endswith("\\Z") and not value.flags & re.M:
                    sample = next((s for s in ("a", "alpha", "repo-1", "1", "abcdef12", "x" * 8) if value.match(s)), None)
                    if sample is not None:
                        checked += 1
                        self.assertIsNone(value.match(sample + "\n"), f"{module.__name__}.{name}")
        self.assertGreater(checked, 10)


class TheValuesThatUsedToPass(unittest.TestCase):
    def test_account_ids_and_keys(self):
        self.assertTrue(accounts.valid_id("alpha"))
        self.assertFalse(accounts.valid_id("alpha\n"))
        for bad in ("alpha\n", "al\npha", "\nalpha"):
            self.assertFalse(accounts.valid_id(bad), repr(bad))
        for pattern, good in ((base.NAME_RE, "doc-1"), (base.ACCOUNT_RE, "alpha"), (base.KEY_RE, "owner/repo:1".replace("/", "."))):
            self.assertTrue(pattern.match(good), good)
            self.assertIsNone(pattern.match(good + "\n"), good)

    def test_repository_names_for_the_query_the_exporter_and_the_ai_tools(self):
        for pattern in (graphql_checks.NAME_RE, mcp_server.NAME_RE, runners.NAME_RE, settings_api.NAME_RE, webhook.NAME_RE):
            self.assertTrue(pattern.match("my-repo.v2"))
            self.assertIsNone(pattern.match("my-repo\n"))
        self.assertIsNone(graphql_checks.OWNER_RE.match("owner\n"))

    def test_the_query_leaves_a_name_with_a_line_feed_out(self):
        self.assertNotIn("bad", graphql_checks.query("owner", ["good", "bad\n"]).replace("good", ""))
        with self.assertRaises(ValueError):
            graphql_checks.query("owner\n", ["good"])

    def test_settings_values(self):
        self.assertIsNone(settings_api.OWNER_RE.match("owner\n"))
        self.assertIsNone(settings_api.LOOP_URL_RE.match("http://127.0.0.1:8080\n"))
        self.assertIsNone(settings_api.OTLP_RE.match("https://collector.example.org/\n"))
        self.assertTrue(settings_api.OTLP_RE.match("https://collector.example.org/"))

    def test_user_names_still_pass_through_the_cleaning(self):
        self.assertEqual(auth.clean_username("  Ann \n"), "ann")
        self.assertEqual(auth.clean_username("an\nn"), "")

    def test_the_multiline_search_of_the_workflow_files_still_sees_every_line(self):
        from github_actions_monitor.app import surface
        text = "on:\n  schedule:\n    - cron: '0 3 * * *'\n    - cron: '5 4 * * 1'\n"
        self.assertEqual([m.group(1) for m in surface.CRON.finditer(text)], ["0 3 * * *", "5 4 * * 1"])


if __name__ == "__main__":
    unittest.main()
