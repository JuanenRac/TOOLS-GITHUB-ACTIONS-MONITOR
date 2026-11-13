# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The redactor of the feed, the brief and the hook keeps the https addresses of github.com whole (a run link used to become "https://github.[blob]") and still cleans everything else."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
from github_actions_monitor.integrations import ai_alerts  # noqa: E402

RUN = "https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/actions/runs/123456789012/job/98765432101"


class GithubAddressesPassWhole(unittest.TestCase):
    def test_a_run_link_passes_untouched(self):
        for url in (RUN, "https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL/actions/runs/42", "https://github.com/JuanenRac", "https://api.github.com/repos/JuanenRac/URTC/actions/runs/7",
                    "https://github.com/JuanenRac/URTC/commit/" + "0123456789abcdef" * 2 + "01234567"):
            self.assertEqual(ai_alerts.redact(url), url)
            self.assertEqual(ai_alerts.redact(f"red run: {url} (see the log)"), f"red run: {url} (see the log)")

    def test_two_links_and_the_text_around_them(self):
        text = f"{RUN} and https://github.com/JuanenRac/URTC/actions/runs/1."
        self.assertEqual(ai_alerts.redact(text), text)

    def test_the_rest_is_still_cleaned(self):
        home = "C:\\" + "Users\\" + "somebody" + "\\" + "work"
        self.assertNotIn("somebody", ai_alerts.redact(f"{RUN} in {home}"))
        self.assertIn(RUN, ai_alerts.redact(f"{RUN} in {home}"))
        for secret in ("ghp_" + "a" * 36, "AKIA" + "B" * 16, "x" * 45, "user@example.com", "10.1.2.3"):
            self.assertNotIn(secret, ai_alerts.redact(f"{RUN} {secret}"), secret)
        self.assertNotIn("somebody", ai_alerts.redact("/home/somebody/x and https://example.org/" + "a" * 60))

    def test_a_link_that_carries_a_secret_is_cleaned(self):
        token = "ghp_" + "c" * 36
        self.assertNotIn(token, ai_alerts.redact(f"https://github.com/JuanenRac/URTC/archive/{token}.zip"))
        self.assertNotIn("secretvalue", ai_alerts.redact("https://github.com/JuanenRac/URTC?token=secretvalue"))
        self.assertNotIn("a" * 45, ai_alerts.redact("https://evil.example/github.com/" + "a" * 45))

    def test_other_hosts_keep_the_old_rule(self):
        self.assertIn("[blob]", ai_alerts.redact("https://example.org/" + "z" * 60))


if __name__ == "__main__":
    unittest.main()
