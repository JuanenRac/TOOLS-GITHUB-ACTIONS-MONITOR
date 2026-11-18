# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A link built from data on the page goes through `safeUrl`, which parses the address: only http(s) of the host of GitHub (or of the configured GitHub Enterprise host) passes, never an address with a
user name or a password, a script scheme, a blank or control character or a backslash. A filter on the first letters of the text let through whatever a parser reads differently."""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


def line_of_safe_url():
    start = PAGE.index("const safeUrl=")
    return PAGE[start:PAGE.index("\n", start)]


def run(host, urls):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("no node here")
    script = ('const GH="https://%s/";\n%s\nconsole.log(JSON.stringify(%s.map(u=>safeUrl(u))))' % (host, line_of_safe_url(), json.dumps(urls)))
    done = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout.strip().splitlines()[-1])


class TheLinksOfThePage(unittest.TestCase):
    def test_the_address_is_parsed_not_matched_by_its_first_letters(self):
        line = line_of_safe_url()
        self.assertIn("new URL(", line)
        self.assertNotIn("startsWith", line)

    def test_what_belongs_to_github_passes_and_nothing_else(self):
        good = ["https://github.com/JuanenRac/X/actions/runs/1", "https://github.com/", "https://GITHUB.com/a?b=c#d"]
        bad = ["javascript:alert(1)", "data:text/html,x", "http://github.com/a", "https://github.com.evil.example/a", "https://github.com@evil.example/a", "https://user:pass@github.com/a",
               "https://evil.example/https://github.com/", "//github.com/a", "/relative", "https://github.com/a b", "https://github.com/a\\b", "https://github.com/\tx", "https://github.com/\nx", "", "#", None, 5]
        got = run("github.com", good + bad)
        self.assertEqual(got[:len(good)], good)
        self.assertEqual(got[len(good):], ["#"] * len(bad))

    def test_the_configured_enterprise_host_passes_and_github_com_stays_https_only(self):
        got = run("git.example.org", ["https://git.example.org/o/r", "http://git.example.org/o/r", "https://github.com/o/r", "http://github.com/o/r", "https://git.example.org.evil.example/"])
        self.assertEqual(got, ["https://git.example.org/o/r", "http://git.example.org/o/r", "https://github.com/o/r", "#", "#"])


if __name__ == "__main__":
    unittest.main()
