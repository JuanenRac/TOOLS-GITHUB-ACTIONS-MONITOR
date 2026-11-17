# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A sweep of the guides in the eight languages against the code: a setting written in backticks must exist (or be one of the few names that are not settings, each with its reason), the guides of the
webhook say the secret in the configuration file is ignored unless `webhook.allow_config_secret` is on (and the code agrees), and the README does not claim a system the CI does not run."""
import re
import unittest
import unittest.mock
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor, settings_api
from github_actions_monitor.security import webhook

HERE = Path(__file__).resolve().parent.parent
DOCS = HERE / "docs"
# dotted names in the guides that are not settings of the page: a key of the data, a name of a mode, a setting that lives only in the configuration file or of another tool
NOT_SETTINGS = {
    "ai_alerts.transient_patterns": "only in the file",
    "ci.ghost_queue": "a key of the data and the sentinel",
    "ci.upstream_red": "an alert code",
    "ci.upstream_release": "an alert code",
    "dispatch.required_ci_profiles": "gha_dispatch_all, another tool",
    "dispatch.required_ci_repos": "gha_dispatch_all, another tool",
    "modes.fast": "a name of a mode",
    "modes.turbo": "a name of a mode",
    "runners.metrics": "a key of the data",
    "score.dropped": "a key of the data",
    "score.limits": "a key of the data",
    "sentinels.security.penalty": "a key of the data",
    "webhook.allow_config_secret": "only in the file, on purpose",
    "webhook.allowed_owners": "only in the file",
}
FILE_SUFFIXES = (".md", ".json", ".jsonl", ".yml", ".yaml", ".py", ".txt", ".pem", ".sh", ".bat", ".html", ".lng", ".ps1")


def flat(tree, prefix=""):
    found = set()
    for key, value in tree.items():
        found.add(prefix + key)
        if isinstance(value, dict):
            found |= flat(value, prefix + key + ".")
    return found


def guides():
    return sorted(p for p in DOCS.glob("*.md") if not p.name.startswith(("CHANGELOG", "SETTINGS")))


class SettingsInTheGuides(unittest.TestCase):
    def setUp(self):
        self.known = set(settings_api.FIELDS) | flat(actions_monitor.DEFAULTS)
        self.groups = {key.split(".")[0] for key in self.known}

    def invented(self, paths):
        bad = []
        for path in paths:
            for token in sorted(set(re.findall(r"`([a-z_]+(?:\.[a-z_]+)+)`", path.read_text(encoding="utf-8")))):
                if token.endswith(FILE_SUFFIXES) or token.split(".")[0] not in self.groups or token in NOT_SETTINGS:
                    continue
                if token not in self.known and not any(key.startswith(token + ".") for key in self.known):
                    bad.append((path.name, token))
        return bad

    def test_no_guide_names_a_setting_that_does_not_exist(self):
        self.assertEqual(self.invented(guides()), [])

    def test_the_sweep_sees_an_invented_setting(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "WEBHOOK.md"
            fake.write_text("Set `webhook.shared_secret_in_file` and `screens.made_up` and `webhook.enabled`.", encoding="utf-8")
            self.assertEqual(self.invented([fake]), [("WEBHOOK.md", "screens.made_up"), ("WEBHOOK.md", "webhook.shared_secret_in_file")])


class TheSecretInTheFile(unittest.TestCase):
    def test_the_code_ignores_the_secret_of_the_file_unless_it_is_allowed(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            long_secret = "x" * 40
            self.assertEqual(webhook.secret_source({"webhook": {"enabled": True, "secret": long_secret}}), "none")
            self.assertEqual(webhook.secret_source({"webhook": {"enabled": True, "secret": long_secret, "allow_config_secret": True}}), "config")

    def test_every_webhook_guide_names_the_switch_and_none_says_the_file_is_read_by_default(self):
        for path in sorted(DOCS.glob("WEBHOOK*.md")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(guide=path.name):
                self.assertIn("webhook.allow_config_secret", text)
                self.assertNotIn("it is read from there by default", text)


class TheSystemsOfTheCi(unittest.TestCase):
    def test_the_readme_does_not_claim_a_system_the_ci_does_not_run(self):
        workflow = HERE.parent / ".github" / "workflows" / "ci.yml"
        if not workflow.is_file():
            self.skipTest("the workflows live in the repository")
        matrix = re.search(r"os:\s*\[([^\]]+)\]", workflow.read_text(encoding="utf-8")).group(1).lower()
        for name in sorted(HERE.parent.glob("README*.md")):
            text = name.read_text(encoding="utf-8")
            block = text.split("<!-- glance:begin -->", 1)[-1].split("<!-- glance:end -->", 1)[0]
            row = next((ln for ln in block.splitlines() if "ubuntu" in ln.lower() or "windows" in ln.lower()), "")
            with self.subTest(readme=name.name):
                self.assertTrue(row, "the row of the systems")
                for system in ("macos", "ubuntu", "windows"):
                    self.assertEqual(system in row.lower(), system in matrix, (system, row))
        self.assertNotIn("three systems", (HERE.parent / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    import unittest.mock  # noqa: F401
    unittest.main()
