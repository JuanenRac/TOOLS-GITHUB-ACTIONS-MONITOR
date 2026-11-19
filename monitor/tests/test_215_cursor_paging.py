# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Lists that reject ?page= hand out a cursor in the Link header: it is followed, bounded, only inside the API and said when something is cut."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import paging  # noqa: E402
from test_191_sentinel import NOW, Fake, build, dep, quiet_repo  # noqa: E402

BASE = "https://api.github.com/repos/acme/r/dependabot/alerts"


def link(url):
    return f'<{url}>; rel="next", <{BASE}?after=zzz>; rel="last"'


class TheHeader(unittest.TestCase):
    def test_the_next_address_is_read_from_the_link_header(self):
        self.assertEqual(paging.next_link(link(BASE + "?after=abc")), BASE + "?after=abc")
        self.assertEqual(paging.next_link('<https://x/y>; rel="prev"'), "")
        self.assertEqual(paging.next_link(""), "")
        self.assertEqual(paging.next_link(None), "")

    def test_only_addresses_of_the_api_are_followed(self):
        self.assertEqual(paging.endpoint_of(BASE + "?after=abc&per_page=100"), "repos/acme/r/dependabot/alerts?after=abc&per_page=100")
        for bad in ("http://api.github.com/x", "https://evil.example/x", "https://api.github.com.evil.example/x", "https://user:pw@api.github.com/x", "https://api.github.com:8443/x",
                    "https://api.github.com/../x", "https://api.github.com/", "/relative", "", None, "https://api.github.com/a/../b"):
            self.assertEqual(paging.endpoint_of(bad), "", bad)

    def test_a_server_of_the_enterprise_can_be_named(self):
        self.assertEqual(paging.endpoint_of("https://github.example.com/api/v3/x", hosts=("github.example.com",)), "api/v3/x")

    def test_the_cursor_is_followed_to_the_end_and_the_limit_cuts(self):
        pages = {"p2": ([2], link("https://api.github.com/p3")), "p3": ([3], "")}
        read = lambda endpoint: pages["p" + endpoint[-1]]      # noqa: E731
        done = paging.follow_cursor(read, link("https://api.github.com/p2"), 5)
        self.assertEqual((done["items"], done["pages"], done["cut"]), ([2, 3], 2, False))
        done = paging.follow_cursor(read, link("https://api.github.com/p2"), 1)
        self.assertEqual((done["items"], done["pages"], done["cut"]), ([2], 1, True))
        self.assertEqual(paging.follow_cursor(read, link("https://api.github.com/p2"), 0), {"items": [], "pages": 0, "cut": True})
        self.assertEqual(paging.follow_cursor(read, "", 5), {"items": [], "pages": 0, "cut": False})

    def test_a_page_that_cannot_be_read_cuts_and_keeps_what_was_read(self):
        answers = iter([([1], link("https://api.github.com/p3")), (None, "")])
        done = paging.follow_cursor(lambda endpoint: next(answers), link("https://api.github.com/p2"), 5)
        self.assertEqual((done["items"], done["cut"]), ([1], True))

    def test_the_setting_has_a_default_and_bounds(self):
        self.assertEqual(paging.settings({})["cursor_pages"], 3)
        self.assertEqual(paging.settings({"pagination": {"cursor_pages": 0}})["cursor_pages"], 0)
        self.assertEqual(paging.settings({"pagination": {"cursor_pages": 99}})["cursor_pages"], 3)


class InTheSecuritySentinel(unittest.TestCase):
    def fake_with_cursor(self, pages_after_first):
        fake = Fake()
        quiet_repo(fake)
        base = fake.run_gh

        def run(args):
            endpoint = args[-1]
            if "dependabot/alerts" in endpoint:
                fake.calls.append(list(args))
                if "after=" not in endpoint:
                    nxt = f'<{BASE}?after=c1>; rel="next"' if pages_after_first else ""
                    return 0, f'HTTP/2.0 200 OK\r\nEtag: "d1"\r\nLink: {nxt}\r\n\r\n' + json.dumps([dep("high")] * 100), ""
                number = int(endpoint.split("after=c")[1].split("&")[0])
                nxt = f'<{BASE}?after=c{number + 1}>; rel="next"' if number < pages_after_first else ""
                return 0, f'HTTP/2.0 200 OK\r\nLink: {nxt}\r\n\r\n' + json.dumps([dep("low")] * 7), ""
            return base(args)
        fake.run_gh = run
        return fake

    def scan(self, pages_after_first, config=None):
        fake = self.fake_with_cursor(pages_after_first)
        sentinel, _fake, _ = build(self, config=config, fake=fake)
        sentinel.tick(NOW)
        return sentinel.state["per_repo"]["r"]["facts"]["dependabot"], fake

    def test_a_first_page_without_a_cursor_costs_nothing_more(self):
        facts, fake = self.scan(0)
        self.assertEqual((len(facts["items"]), facts["cut"]), (100, False))
        self.assertEqual(sum(1 for c in fake.calls if "dependabot/alerts" in c[-1]), 1)

    def test_the_next_pages_are_read_and_counted(self):
        facts, fake = self.scan(2)
        self.assertEqual((len(facts["items"]), facts["cut"]), (114, False))
        self.assertEqual(sum(1 for c in fake.calls if "dependabot/alerts" in c[-1]), 3)

    def test_the_limit_of_pages_cuts_and_says_so(self):
        facts, _fake = self.scan(9)
        self.assertEqual((len(facts["items"]), facts["cut"]), (121, True))      # the first page plus three more


if __name__ == "__main__":
    unittest.main()
