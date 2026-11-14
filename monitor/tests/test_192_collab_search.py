# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Collab sentinel can read the open issues and pull requests of the whole account with a few calls of the Search API (`sentinels.collab.search_api`, off by default) instead of two lists for each
repository. Both ways must give the same alerts; when the Search API fails the round reads each repository as before."""
import json
import sys
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from test_173 import NOW, FakeGitHub, build, issue, pull  # noqa: E402


class SearchFake(FakeGitHub):
    """Answers the Search API with the same items as the lists of each repository, and counts every call."""

    def __init__(self):
        super().__init__()
        self.by_repo = {}
        self.search_fail = False
        self.search_calls = 0

    def put(self, repo, issues=(), pulls=()):
        self.by_repo[repo] = ([dict(i) for i in issues], [dict(p) for p in pulls])

    def run_gh(self, args):
        endpoint = args[-1]
        repo = endpoint.split("/")[2] if endpoint.startswith("repos/") else ""
        if repo in self.by_repo:
            self.issues, self.pulls = self.by_repo[repo]
        return super().run_gh(args)

    def gh(self, *args, **kw):
        endpoint = args[1]
        if endpoint.startswith("search/issues"):
            self.search_calls += 1
            self.calls.append(list(args))
            if self.search_fail:
                raise RuntimeError("HTTP 403 rate limit")
            kind_pr = "is:pr" in endpoint
            items = []
            for repo, (issues, pulls) in self.by_repo.items():
                for raw in (pulls if kind_pr else issues):
                    item = dict(raw)
                    item["repository_url"] = f"https://api.github.com/repos/o/{repo}"
                    if kind_pr:
                        item["pull_request"] = {}
                        item.pop("requested_reviewers", None)
                        item.pop("requested_teams", None)
                    items.append(item)
            return {"total_count": len(items), "items": items}
        return super().gh(*args, **kw)


def data(fake):
    fake.put("a", [issue(1, updated=20), issue(2, updated=1, labels=["security"])], [pull(5, updated=5), pull(6, updated=1, draft=True, created=40)])
    fake.put("b", [issue(3, updated=30, assoc="NONE")], [pull(7, updated=2, bot=True)])
    fake.details = {5: "dirty"}


def view(sentinel):
    return sorted((a["repo"], a["code"], a["title"]) for a in sentinel.get_alerts())


class TheTwoWaysAgree(unittest.TestCase):
    def run_mode(self, search):
        fake = SearchFake()
        data(fake)
        sentinel, fake, _folder = build(self, {"search_api": search}, repos=("a", "b"), fake=fake)
        sentinel.tick(NOW)
        sentinel.tick(NOW + 8 * 86400)      # the conflict of a pull request counts days: the second round makes it an alert in both ways
        return sentinel, fake

    def test_both_ways_raise_the_same_alerts(self):
        usual, _f1 = self.run_mode(False)
        search, f2 = self.run_mode(True)
        self.assertTrue(view(usual), "the data must raise something or the test proves nothing")
        self.assertEqual(view(search), view(usual))
        self.assertGreater(f2.search_calls, 0)

    def test_the_search_way_reads_no_list_of_a_repository(self):
        _s, fake = self.run_mode(True)
        listed = [c for c in fake.calls if any(str(x).startswith("repos/") and ("/issues?" in str(x) or "/pulls?state" in str(x)) for x in c)]
        self.assertEqual(listed, [])

    def test_it_is_off_by_default_and_reads_no_search(self):
        from github_actions_monitor.sentinels import sentinel_collab as sc
        self.assertFalse(sc.DEFAULTS["search_api"])
        self.assertFalse(sc.settings({})["search_api"])
        self.assertFalse(sc.settings({"sentinels": {"collab": {"search_api": "yes"}}})["search_api"])
        _s, fake = self.run_mode(False)
        self.assertEqual(fake.search_calls, 0)

    def test_when_the_search_fails_each_repository_is_read_as_before(self):
        fake = SearchFake()
        data(fake)
        fake.search_fail = True
        sentinel, fake, _folder = build(self, {"search_api": True}, repos=("a", "b"), fake=fake)
        sentinel.tick(NOW)
        sentinel.tick(NOW + 8 * 86400)
        usual, _f = self.run_mode(False)
        self.assertEqual(view(sentinel), view(usual))
        self.assertIn("search", sentinel.errors)

    def test_a_plain_owner_name_only(self):
        sentinel, _fake, _folder = build(self, {"search_api": True})
        self.assertIsNone(sentinel.search_lists("bad name; drop"))

    def test_the_setting_and_its_text_exist_in_eight_languages(self):
        key = "sentinels.collab.search_api"
        self.assertIn(key, settings_api.FIELDS)
        for lang in i18n.LANGS:
            self.assertNotEqual(i18n.tl(lang, "cfg.f." + key), "cfg.f." + key, lang)
            self.assertNotEqual(i18n.tl(lang, "cfg.h." + key), "cfg.h." + key, lang)


if __name__ == "__main__":
    unittest.main()
