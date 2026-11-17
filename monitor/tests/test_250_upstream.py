# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Follow the original repository of each fork (`upstream.*`, off by default). The case is the one of the account measured in the study of forks: hundreds of forks, almost none with a CI of their own,
and a few projects they follow that go red or publish. Everything is read with one GraphQL request for several forks and bounded by settings."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import upstream  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ci, sentinel_local  # noqa: E402

NOW = 1_800_000_000.0
HOUR = 3600


def node(state="SUCCESS", tag="v1.0.0", parent="acme/tool", draft=False):
    return {"name": "x", "parent": {"nameWithOwner": parent, "url": "https://github.com/" + parent, "isArchived": False,
                                    "defaultBranchRef": {"name": "main", "target": {"oid": "a" * 40, "committedDate": "2026-11-01T00:00:00Z", "statusCheckRollup": {"state": state} if state else None}},
                                    "latestRelease": {"tagName": tag, "publishedAt": "2026-10-01T00:00:00Z", "isDraft": draft, "isPrerelease": False, "url": "https://github.com/%s/releases/tag/%s" % (parent, tag)} if tag else None}}


def on(**kw):
    return upstream.settings({"upstream": dict({"enabled": True}, **kw)})


class TheSettings(unittest.TestCase):
    def test_it_is_off_and_bounded_by_default(self):
        cfg = upstream.settings({})
        self.assertEqual((cfg["enabled"], cfg["notify"], cfg["repos"]), (False, False, []))
        self.assertEqual((cfg["refresh_hours"], cfg["requests_per_hour"], cfg["forks_per_request"], cfg["news_days"]), (12, 6, 8, 7))

    def test_a_wrong_value_keeps_the_default(self):
        cfg = upstream.settings({"upstream": {"enabled": "yes", "refresh_hours": 0, "requests_per_hour": True, "forks_per_request": 99, "news_days": "7", "repos": ["ok", "bad name", 5]}})
        self.assertEqual((cfg["enabled"], cfg["refresh_hours"], cfg["requests_per_hour"], cfg["forks_per_request"], cfg["news_days"]), (False, 12, 6, 8, 7))
        self.assertEqual(cfg["repos"], ["ok"])

    def test_the_defaults_of_the_program_are_the_same_as_the_module(self):
        self.assertEqual(am.DEFAULTS["upstream"], upstream.DEFAULTS)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["upstream"], upstream.DEFAULTS)


class TheQuery(unittest.TestCase):
    def test_one_request_reads_several_forks(self):
        text = upstream.query("owner", ["a", "b", "c"])
        self.assertEqual(text.count("repository(owner:"), 3)
        self.assertIn("statusCheckRollup", text)
        self.assertIn("latestRelease", text)

    def test_a_name_that_is_not_a_plain_name_never_reaches_the_text(self):
        text = upstream.query("owner", ['x"){y} #', "good"])
        self.assertEqual(text.count("repository(owner:"), 1)
        self.assertNotIn("#", text)
        self.assertEqual(upstream.query('bad"owner', ["a"]), "")
        self.assertEqual(upstream.query("owner", []), "")


class TheReading(unittest.TestCase):
    def test_the_checks_of_the_parent_are_mapped(self):
        states = {"SUCCESS": "success", "FAILURE": "failure", "ERROR": "failure", "PENDING": "pending", "EXPECTED": "pending", None: "none"}
        for raw, want in states.items():
            self.assertEqual(upstream.parse_parent(node(state=raw))["state"], want, raw)

    def test_a_fork_without_a_parent_or_a_release_is_read_without_failing(self):
        self.assertIsNone(upstream.parse_parent({"name": "x", "parent": None}))
        self.assertIsNone(upstream.parse_parent(None))
        self.assertIsNone(upstream.parse_parent(node(tag=None))["release"])
        self.assertIsNone(upstream.parse_parent(node(draft=True))["release"])

    def test_the_first_reading_is_not_news_and_a_new_tag_is(self):
        store = {}
        upstream.read(lambda text: {"r0": node(tag="v1.0.0")}, "o", ["f"], NOW, store)
        self.assertIsNone(store["f"]["release_changed"])
        upstream.read(lambda text: {"r0": node(tag="v1.1.0")}, "o", ["f"], NOW + 13 * HOUR, store)
        self.assertEqual(store["f"]["release_changed"], NOW + 13 * HOUR)
        picture = upstream.build(store, ["f"], on(), NOW + 14 * HOUR)
        self.assertEqual((picture["news"], picture["rows"][0]["news"]), (1, True))
        self.assertEqual(upstream.build(store, ["f"], on(), NOW + 20 * 86400)["news"], 0)      # a week later it is no longer news

    def test_the_moment_the_original_turned_red_is_kept(self):
        store = {}
        upstream.read(lambda text: {"r0": node("SUCCESS")}, "o", ["f"], NOW, store)
        upstream.read(lambda text: {"r0": node("FAILURE")}, "o", ["f"], NOW + 20 * HOUR, store)
        upstream.read(lambda text: {"r0": node("FAILURE")}, "o", ["f"], NOW + 40 * HOUR, store)
        self.assertEqual(store["f"]["state_since"], NOW + 20 * HOUR)
        self.assertEqual(upstream.build(store, ["f"], on(), NOW + 41 * HOUR)["red"], 1)

    def test_an_answer_that_misses_a_fork_leaves_it_unread(self):
        store = {}
        self.assertEqual(upstream.read(lambda text: {"r0": node()}, "o", ["a", "b"], NOW, store), 1)
        picture = upstream.build(store, ["a", "b"], on(), NOW)
        self.assertEqual((picture["tracked"], picture["unread"]), (1, 1))

    def test_a_deleted_original_is_shown_as_detached(self):
        store = {}
        upstream.read(lambda text: {"r0": {"name": "f", "parent": None}}, "o", ["f"], NOW, store)
        row = upstream.build(store, ["f"], on(), NOW)["rows"][0]
        self.assertEqual((row["state"], row["red"]), ("detached", False))


class TheLimits(unittest.TestCase):
    forks = ["fork%03d" % n for n in range(727)]      # the account of the study: 727 repositories, 722 of them forks

    def test_nothing_is_read_while_it_is_off(self):
        self.assertEqual(upstream.pick_due(self.forks, {}, NOW, upstream.settings({})), [])
        self.assertEqual(upstream.build({}, self.forks, upstream.settings({}), NOW), {"enabled": False})

    def test_one_request_never_has_more_forks_than_the_setting(self):
        self.assertEqual(len(upstream.pick_due(self.forks, {}, NOW, on())), 8)
        self.assertEqual(len(upstream.pick_due(self.forks, {}, NOW, on(forks_per_request=25))), 25)

    def test_the_hourly_limit_stops_the_reads(self):
        self.assertEqual(upstream.pick_due(self.forks, {}, NOW, on(), requests_last_hour=6), [])
        self.assertTrue(upstream.pick_due(self.forks, {}, NOW, on(), requests_last_hour=5))

    def test_the_least_recently_read_go_first_and_a_fresh_one_waits(self):
        store = {"fork000": {"at": NOW - 1 * HOUR}, "fork001": {"at": NOW - 13 * HOUR}, "fork002": {"at": NOW - 30 * HOUR}}
        picked = upstream.pick_due(self.forks[:3], store, NOW, on())
        self.assertEqual(picked, ["fork002", "fork001"])

    def test_the_whole_account_is_covered_in_turns_without_passing_the_limit(self):
        store, requests, clock = {}, 0, NOW
        for hour in range(200):      # a long run of hours: six requests an hour at most
            clock = NOW + hour * HOUR
            used = 0
            while True:
                names = upstream.pick_due(self.forks, store, clock, on(), used)
                if not names:
                    break
                upstream.read(lambda text, names=names: {"r%d" % i: node() for i in range(len(names))}, "o", names, clock, store)
                used += 1
                requests += 1
            self.assertLessEqual(used, 6)
        self.assertEqual(len(store), 727)
        self.assertLessEqual(requests, 6 * 200)

    def test_only_the_named_forks_are_followed_when_there_is_a_list(self):
        cfg = on(repos=["fork001", "fork003", "not-a-fork"])
        self.assertEqual(upstream.pick_due(self.forks, {}, NOW, cfg), ["fork001", "fork003"])
        self.assertEqual(upstream.build({}, self.forks, cfg, NOW)["unread"], 2)


class TheSentinel(unittest.TestCase):
    def snapshot(self, config, store):
        from datetime import datetime, timezone
        repo = {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [], "label_dependencies": False, "files": {}, "license": None}
        info = {"fork-a": dict(repo, fork=True), "own": dict(repo, fork=False)}
        inp = {"now": datetime.fromtimestamp(NOW, timezone.utc), "today": "2026-11-04", "cfg": sentinel_local.sentinel_config(config), "repos": sorted(info), "eco": {r: "main" for r in info},
               "repo_info": info, "alerts": {}, "perms": {}, "runs": {"fork-a": [], "own": []}, "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}},
               "unreleased": {}, "targets": {}, "errors": {}, "loading": "", "audits": None, "lint": None, "upstream": store, "upstream_calls": 2}
        return sentinel_local.compute_snapshot(inp)

    def test_off_the_snapshot_says_so_and_costs_nothing(self):
        self.assertEqual(self.snapshot({}, {})["upstream"], {"enabled": False})

    def test_on_only_the_forks_are_in_the_picture(self):
        store = {"fork-a": upstream.merge(None, upstream.parse_parent(node("FAILURE")), NOW), "own": upstream.merge(None, upstream.parse_parent(node()), NOW)}
        picture = self.snapshot({"upstream": {"enabled": True}}, store)["upstream"]
        self.assertEqual([r["repo"] for r in picture["rows"]], ["fork-a"])
        self.assertEqual((picture["red"], picture["requests_last_hour"]), (1, 2))

    def test_the_notices_come_only_with_the_switch_and_are_information(self):
        store = {"fork-a": upstream.merge(None, upstream.parse_parent(node("FAILURE")), NOW)}
        store["fork-a"]["release_changed"] = NOW - 3600
        for notify, count in ((False, 0), (True, 2)):
            snap = self.snapshot({"upstream": {"enabled": True, "notify": notify}}, store)

            class Held(sentinel_ci.SentinelCI):
                def __init__(self):      # no sentinel behind it: only the picture is asked
                    pass

                def _picture(self):
                    return snap
                account_id = ""
                name = "ci"
            alerts = [a for a in Held().get_alerts() if a["code"].startswith("ci.upstream")]
            self.assertEqual(len(alerts), count, notify)
            self.assertTrue(all(a["level"] == "info" for a in alerts))


class TheSurface(unittest.TestCase):
    def test_the_settings_are_in_the_schema_with_texts_in_eight_languages(self):
        keys = ["upstream." + k for k in ("enabled", "refresh_hours", "requests_per_hour", "forks_per_request", "news_days", "notify", "repos")]
        for key in keys:
            self.assertIn(key, settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(texts.get("cfg.f." + key) and texts.get("cfg.h." + key), (lang, key))
            for key in ("ui.cfg_b_upstream", "evt.upstream_red", "evt.upstream_release", "ui.upstream_title", "ui.upstream_summary", "ui.upstream_new", "ui.upstream_calls",
                        "ui.upstream_state_success", "ui.upstream_state_failure", "ui.upstream_state_pending", "ui.upstream_state_none", "ui.upstream_state_detached"):
                self.assertTrue(texts.get(key), (lang, key))

    def test_the_page_draws_the_originals(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for key in ("ui.upstream_title", "ui.upstream_summary", "ui.upstream_new", "ui.upstream_calls", "ui.upstream_state_"):
            self.assertIn(key, page)


if __name__ == "__main__":
    unittest.main()
