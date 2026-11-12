# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.3: the Collab sentinel (issues and pull requests that need a person): its rules, its cost (conditional reads, a cap per round, a pause under the floor of the allowance), that it
only reads, that it is off by default and absent from the lite edition, its events, its settings in eight languages and its layer in the page. Nothing here reaches GitHub: the reads are fakes, and the
state and the feed go to a temporary folder (never next to the code)."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import accounts  # noqa: E402
import events  # noqa: E402
import i18n  # noqa: E402
import sentinel_collab as sc  # noqa: E402
import sentinel_registry  # noqa: E402
import settings_api  # noqa: E402

NOW = time.mktime(time.strptime("2026-11-10 12:00:00", "%Y-%m-%d %H:%M:%S")) - time.timezone
DAY = 86400


def when(days_ago):
    return sc.stamp(NOW - days_ago * DAY)


def issue(number, updated=0, labels=(), bot=False, created=None, assoc="OWNER", comments=1, pr=False):
    raw = {"number": number, "title": f"issue {number}", "html_url": f"https://github.com/o/r/issues/{number}", "created_at": when(created if created is not None else updated), "updated_at": when(updated),
           "labels": [{"name": n} for n in labels], "user": {"type": "Bot" if bot else "User"}, "author_association": assoc, "comments": comments}
    if pr:
        raw["pull_request"] = {}
    return raw


def pull(number, updated=0, created=None, draft=False, review=False, bot=False):
    return {"number": number, "title": f"pr {number}", "html_url": f"https://github.com/o/r/pull/{number}", "created_at": when(created if created is not None else updated), "updated_at": when(updated),
            "draft": draft, "requested_reviewers": [{"login": "x"}] if review else [], "requested_teams": [], "user": {"type": "Bot" if bot else "User"}}


RULES = json.loads(json.dumps(sc.DEFAULTS["rules"]))


def codes(found):
    return sorted(a["code"] for a in found.values())


class Rules(unittest.TestCase):
    def run_rules(self, issues=(), prs=(), rules=None, known=None):
        slim_i = [sc.slim_issue(i) for i in issues if "pull_request" not in i]
        slim_p = [sc.slim_pull(p) for p in prs]
        return sc.evaluate("r", slim_i, slim_p, rules or RULES, NOW, known)

    def test_a_quiet_issue_is_stale_only_after_the_days_of_the_rule(self):
        self.assertEqual(codes(self.run_rules([issue(1, updated=13)])), [])
        self.assertEqual(codes(self.run_rules([issue(1, updated=15)])), ["collab.issue.stale"])
        self.assertEqual(codes(self.run_rules([issue(1, updated=15)], rules={**RULES, "issue_stale_days": 30})), [])

    def test_a_critical_label_is_flagged_whatever_the_age_and_replaces_stale(self):
        found = self.run_rules([issue(2, updated=0, labels=["Security"]), issue(3, updated=40, labels=["critical", "bug"])])
        self.assertEqual(codes(found), ["collab.issue.critical", "collab.issue.critical"])
        self.assertEqual({a["level"] for a in found.values()}, {"error"})
        self.assertEqual(next(a for a in found.values() if a["number"] == 3)["labels"], ["critical"])

    def test_bots_and_pull_requests_in_the_issue_list_are_left_out(self):
        self.assertEqual(codes(self.run_rules([issue(4, updated=60, bot=True), issue(5, updated=60, pr=True)])), [])
        self.assertEqual(codes(self.run_rules(prs=[pull(6, updated=60, review=True, bot=True)])), [])

    def test_a_review_waiting_and_an_old_draft(self):
        found = self.run_rules(prs=[pull(7, updated=4, review=True), pull(8, updated=1, review=True), pull(9, created=31, updated=1, draft=True), pull(10, created=5, updated=5, draft=True)])
        self.assertEqual(sorted((a["code"], a["number"]) for a in found.values()), [("collab.pr.draft_old", 9), ("collab.pr.review_pending", 7)])

    def test_a_draft_never_waits_for_a_review(self):
        self.assertEqual(codes(self.run_rules(prs=[pull(11, updated=9, created=9, draft=True, review=True)])), [])

    def test_conflicts_count_from_the_first_time_they_were_seen(self):
        slim = sc.slim_pull(pull(12, updated=0))
        slim["dirty_since"] = NOW - 8 * DAY
        self.assertEqual(codes(sc.evaluate("r", [], [slim], RULES, NOW)), ["collab.pr.conflict"])
        slim["dirty_since"] = NOW - 2 * DAY
        self.assertEqual(codes(sc.evaluate("r", [], [slim], RULES, NOW)), [])

    def test_outsiders_are_only_watched_when_the_rule_is_on(self):
        stranger = issue(13, updated=2, created=2, assoc="NONE", comments=0)
        self.assertEqual(codes(self.run_rules([stranger])), [])
        self.assertEqual(codes(self.run_rules([stranger], rules={**RULES, "watch_external_comments": True})), ["collab.issue.external"])
        self.assertEqual(codes(self.run_rules([issue(14, updated=2, created=2, assoc="OWNER", comments=0)], rules={**RULES, "watch_external_comments": True})), [])

    def test_an_alert_that_stays_open_keeps_its_first_date(self):
        first = self.run_rules([issue(15, updated=20)])
        again = sc.evaluate("r", [sc.slim_issue(issue(15, updated=21))], [], RULES, NOW + DAY, first)
        key = next(iter(first))
        self.assertEqual(again[key]["created_at"], first[key]["created_at"])


class FakeGitHub:
    """What `run_gh` and `gh` answer. Records every call: `gh api -i [-H If-None-Match: x] endpoint` for the lists, `gh api endpoint` for the detail of a pull request."""

    def __init__(self):
        self.issues, self.pulls, self.details = [], [], {}
        self.etag = 1
        self.calls = []
        self.fail = set()

    def run_gh(self, args):
        self.calls.append(list(args))
        endpoint = args[-1]
        if any(f in endpoint for f in self.fail):
            return 1, "", "HTTP 500"
        tag = f'"v{self.etag}"'
        if f"If-None-Match: {tag}" in args:
            return 0, "HTTP/2.0 304 Not Modified\r\nEtag: " + tag + "\r\n\r\n", ""
        body = self.issues if "/issues?" in endpoint else self.pulls
        return 0, "HTTP/2.0 200 OK\r\nEtag: " + tag + "\r\nContent-Type: application/json\r\n\r\n" + json.dumps(body), ""

    def gh(self, *args, **kw):
        self.calls.append(list(args))
        number = args[1].rsplit("/", 1)[-1]
        return {"number": int(number), "mergeable_state": self.details.get(int(number), "clean")}


def build(case, config=None, repos=("r",), rate=None, fake=None):
    fake = fake or FakeGitHub()
    folder = Path(tempfile.mkdtemp(prefix="collab_test_"))
    saved = (sc.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE)
    sc.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE = folder / "collab_state.json", folder / "events.jsonl", folder / "events_state.json"
    case.addCleanup(lambda: (setattr(sc, "STATE_FILE", saved[0]), setattr(events, "EVENTS_FILE", saved[1]), setattr(events, "STATE_FILE", saved[2])))
    settings = {"sentinels": {"collab": {"enabled": True, **(config or {})}}}
    ctx = {"gh": fake.gh, "run_gh": fake.run_gh, "repos_fn": lambda: list(repos), "eco_fn": lambda r: "web" if r.startswith("w") else "other", "data_fn": lambda: {"rate": rate} if rate else None, "account_id": "main"}
    sentinel = sc.SentinelCollab(ctx, settings)
    sentinel.listened = []
    sentinel.feed.listeners.append(sentinel.listened.append)
    return sentinel, fake, folder


def lines(folder):
    path = folder / "events.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


class Rounds(unittest.TestCase):
    def test_the_first_look_announces_nothing_and_the_next_one_announces_only_the_change(self):
        sentinel, fake, folder = build(self)
        fake.issues = [issue(1, updated=20)]
        sentinel.tick(NOW)
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["collab.issue.stale"])
        self.assertEqual(lines(folder), [], "the alerts that were already there are not news")
        fake.etag += 1
        fake.issues = [issue(1, updated=20), issue(2, updated=0, labels=["security"])]
        sentinel.tick(NOW + 700)
        found = lines(folder)
        self.assertEqual([(e["kind"], e["code"], e["sentinel"]) for e in found], [("collab_new", "collab.issue.critical", "collab")])
        self.assertEqual(found[0]["level"], "bad")
        self.assertEqual(found[0]["url"], "https://github.com/o/r/issues/2")
        self.assertTrue(found[0]["text"])
        fake.etag += 1
        fake.issues = [issue(2, updated=0, labels=["security"])]
        sentinel.tick(NOW + 1400)
        self.assertEqual([e["kind"] for e in lines(folder)][-1], "collab_fixed")
        self.assertEqual(len(sentinel.listened), 2, "the listeners (the notifications) hear what the file gets")

    def test_an_unchanged_repository_costs_no_allowance(self):
        sentinel, fake, _ = build(self)
        fake.issues, fake.pulls = [issue(1, updated=20)], [pull(5, updated=0)]
        sentinel.tick(NOW)
        first = len(fake.calls)
        sentinel.tick(NOW + 700)
        second = fake.calls[first:]
        self.assertTrue(all("If-None-Match" in " ".join(c) for c in second if "-i" in c), second)
        self.assertEqual([c for c in second if "-i" not in c], [], "the detail of a pull request is not asked for again so soon")
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["collab.issue.stale"], "a 304 keeps what was known")
        self.assertEqual(sentinel.get_status()["errors"], [], "a 304 is not an error")
        self.assertEqual(sentinel.state["per_repo"]["r"]["scanned"], NOW + 700, "and it counts as a look")

    def test_it_only_reads(self):
        sentinel, fake, _ = build(self)
        fake.issues, fake.pulls = [issue(1, updated=20)], [pull(5, updated=0, review=True)]
        sentinel.tick(NOW)
        self.assertTrue(fake.calls)
        for call in fake.calls:
            self.assertEqual(call[0], "api")
            self.assertFalse({"-X", "--method", "-f", "-F", "--field", "--raw-field", "--input"} & set(call), call)
            self.assertTrue(call[-1].startswith("repos/") and ("/issues" in call[-1] or "/pulls" in call[-1]), call)
        code = (HERE / "sentinel_collab.py").read_text(encoding="utf-8").split('"""', 2)[2]
        for word in ("POST", "PATCH", "PUT", "DELETE", "--method"):
            self.assertNotIn(word, code, word)

    def test_a_round_reads_at_most_the_repositories_of_its_cap_and_the_oldest_first(self):
        sentinel, fake, _ = build(self, {"max_repos_per_tick": 2}, repos=("a", "b", "c", "d"))
        sentinel.tick(NOW)
        self.assertEqual(sorted({c[-1].split("/")[2] for c in fake.calls}), ["a", "b"])
        fake.calls.clear()
        sentinel.tick(NOW + 700)
        self.assertEqual(sorted({c[-1].split("/")[2] for c in fake.calls}), ["c", "d"], "the ones not read yet go first")
        self.assertEqual(sentinel.get_status()["repos_checked"], 4)
        self.assertIsNotNone(sentinel.get_status()["last_full_scan"])

    def test_only_a_few_pull_request_details_are_read_per_round(self):
        sentinel, fake, _ = build(self)
        fake.pulls = [pull(n, updated=0) for n in range(1, 20)]
        sentinel.tick(NOW)
        self.assertEqual(len([c for c in fake.calls if "-i" not in c]), sc.DETAILS_PER_TICK)

    def test_a_conflict_is_flagged_after_its_days_and_goes_when_it_is_solved(self):
        sentinel, fake, _ = build(self)
        fake.pulls, fake.details = [pull(5, updated=0)], {5: "dirty"}
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_alerts(), [])
        fake.etag += 1
        sentinel.tick(NOW + 8 * DAY)
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["collab.pr.conflict"])
        fake.details = {5: "clean"}
        fake.pulls = [pull(5, updated=-9)]
        fake.etag += 1
        sentinel.tick(NOW + 9 * DAY)
        self.assertEqual(sentinel.get_alerts(), [])


    def test_the_round_pauses_under_the_floor_of_the_allowance_and_a_failing_repository_does_not_stop_the_others(self):
        sentinel, fake, _ = build(self, rate={"remaining": 50})
        self.assertFalse(sentinel.tick(NOW))
        self.assertEqual(fake.calls, [])
        self.assertTrue(sentinel.get_status()["paused"])
        sentinel, fake, _ = build(self, repos=("bad", "good"))
        fake.fail = {"/bad/"}
        fake.issues = [issue(1, updated=20)]
        sentinel.tick(NOW)
        self.assertEqual([a["repo"] for a in sentinel.get_alerts()], ["good"])
        self.assertEqual([e["section"] for e in sentinel.get_status()["errors"]], ["bad"])

    def test_the_state_survives_a_restart_and_the_alerts_are_not_announced_again(self):
        sentinel, fake, folder = build(self)
        fake.issues = [issue(1, updated=20)]
        sentinel.tick(NOW)
        again = sc.SentinelCollab(sentinel.ctx, {"sentinels": {"collab": {"enabled": True}}})
        again.feed.events_file = folder / "events.jsonl"
        self.assertEqual([a["id"] for a in again.get_alerts()], [a["id"] for a in sentinel.get_alerts()])
        fake.etag += 1
        again.tick(NOW + 700)
        self.assertEqual(lines(folder), [])
        self.assertTrue(json.loads((folder / "collab_state.json").read_text(encoding="utf-8"))["alerts"])

    def test_a_broken_state_file_is_an_empty_state(self):
        folder = Path(tempfile.mkdtemp(prefix="collab_test_"))
        (folder / "s.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(sc.load_state(folder / "s.json")["alerts"], {})
        (folder / "s.json").write_text('{"alerts": 3}', encoding="utf-8")
        self.assertEqual(sc.load_state(folder / "s.json")["per_repo"], {})

    def test_the_scope_follows_the_repos_setting(self):
        sentinel, _, _ = build(self, {"repos": ["web-a"]}, repos=("web-a", "web-b", "api"))
        self.assertEqual(sentinel.scope(), ["web-a"])
        sentinel, _, _ = build(self, {"repos": {"ecosystems": ["web"]}}, repos=("web-a", "web-b", "api"))
        self.assertEqual(sentinel.scope(), ["web-a", "web-b"])
        sentinel, _, _ = build(self, {"repos": "all"}, repos=("web-a", "api"))
        self.assertEqual(sentinel.scope(), ["web-a", "api"])


class Settings(unittest.TestCase):
    def test_the_defaults_are_off_and_conservative(self):
        cfg = sc.settings({})
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["rules"]["issue_stale_days"], 14)
        self.assertEqual(cfg["refresh_seconds"], 600)
        self.assertFalse(cfg["rules"]["watch_external_comments"])

    def test_a_bad_value_keeps_the_default_and_an_unknown_key_is_dropped(self):
        cfg = sc.settings({"sentinels": {"collab": {"enabled": "yes", "refresh_seconds": 5, "max_repos_per_tick": True, "color": "red", "repos": 7,
                                                    "rules": {"issue_stale_days": 0, "pr_conflict_days": "3", "issue_critical_labels": [1], "watch_external_comments": 1}}}})
        self.assertEqual(cfg, sc.DEFAULTS)
        ok = sc.settings({"sentinels": {"collab": {"enabled": True, "refresh_seconds": 120, "rules": {"issue_stale_days": 30, "issue_critical_labels": ["p0"]}}}})
        self.assertEqual((ok["enabled"], ok["refresh_seconds"], ok["rules"]["issue_stale_days"], ok["rules"]["issue_critical_labels"]), (True, 120, 30, ["p0"]))

    def test_the_page_of_settings_has_the_twelve_settings_in_one_block_of_the_sentinel_tab(self):
        keys = [k for k in settings_api.FIELDS if k.startswith("sentinels.collab.")]
        self.assertEqual(len(keys), 12)         # the eleven of the first look plus the labels that make an item ignored
        self.assertTrue(all(settings_api.FIELDS[k][0] == "sentinel" and settings_api.META[k]["block"] == "collab" for k in keys))
        self.assertEqual(settings_api.check_value("sentinels.collab.refresh_seconds", 30), (False, "range"))
        self.assertEqual(settings_api.check_value("sentinels.collab.repos", "all"), (True, "all"))
        self.assertEqual(settings_api.check_value("sentinels.collab.rules.issue_critical_labels", ["security"]), (True, ["security"]))
        for key in keys:
            self.assertFalse(settings_api.META[key]["secure"], key)

    def test_every_setting_and_text_of_the_sentinel_exists_in_the_eight_languages(self):
        wanted = [settings_api.help_key(k) for k in settings_api.FIELDS if k.startswith("sentinels.collab.")] + [f"collab.t.{n}" for n in ("issue_stale", "issue_critical", "issue_external", "pr_review", "pr_draft", "pr_conflict")]
        wanted += ["evt.collab_new", "evt.collab_fixed", "ui.cfg_b_collab", "ui.collab_title", "ui.collab_off", "ui.collab_none", "ui.collab_count", "ui.collab_foot", "ui.th_alert"]
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for key in wanted:
                self.assertTrue(cat.get(key, "").strip(), f"{lang} {key}")
            for key in ("collab.t.issue_stale", "collab.t.pr_conflict"):
                self.assertIn("{days}", cat[key], f"{lang} {key}")
                self.assertIn("{repo}", cat[key], f"{lang} {key}")


class Registry(unittest.TestCase):
    def test_collab_is_registered_off_by_default_and_ci_is_unchanged(self):
        ctx = {"gh": lambda *a, **k: [], "repos_fn": lambda: [], "eco_fn": lambda r: "other", "data_fn": lambda: None, "account_id": "main"}
        registry = sentinel_registry.SentinelRegistry.build(ctx, {})
        self.assertEqual(registry.names(), ["ci", "collab"])
        self.assertFalse(registry.get("collab").enabled)
        self.assertTrue(registry.get("ci").enabled)
        self.assertEqual(sentinel_registry.is_enabled({}, "collab"), False)
        self.assertEqual(sentinel_registry.is_enabled({"sentinels": {"collab": {"enabled": True}}}, "collab"), True)

    def test_a_sentinel_that_is_off_runs_nothing_and_shows_nothing(self):
        sentinel = sc.SentinelCollab({"gh": None, "repos_fn": lambda: ["r"], "eco_fn": lambda r: "x"}, {})
        self.assertFalse(sentinel.tick(NOW))
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual(sentinel.get_metrics(), {})
        self.assertEqual(sentinel.get_status()["level"], "off")

    def test_the_alerts_of_both_sentinels_come_in_one_list_with_their_origin(self):
        sentinel, fake, _ = build(self)
        fake.issues = [issue(1, updated=20), issue(2, updated=0, labels=["security"])]
        sentinel.tick(NOW)

        class Quiet(sentinel_registry.sentinel_base.BaseSentinel):
            name, refresh_seconds = "ci", 60

            def tick(self): return None
            def get_status(self): return {}
            def get_metrics(self): return {}
            def get_config_schema(self): return {}
            def get_alerts(self): return [{"id": "ci.red:x", "code": "ci.red", "level": "error", "sentinel": "ci", "account_id": "main", "repo": "x", "title": "red", "details": {}, "created_at": ""}]

        registry = sentinel_registry.SentinelRegistry()
        registry.items = {"ci": Quiet({}, {}), "collab": sentinel}
        alerts = registry.alerts()
        self.assertEqual({a["sentinel"] for a in alerts}, {"ci", "collab"})
        self.assertEqual(alerts[0]["level"], "error")
        for alert in alerts:
            self.assertEqual(set(alert), {"id", "code", "level", "sentinel", "account_id", "repo", "title", "details", "created_at"})
        self.assertEqual(registry.metrics()["collab"]["collab_alerts"], 2)

    def test_the_contract_is_complete_and_the_title_is_in_the_language_of_the_request(self):
        sentinel, fake, _ = build(self)
        fake.issues = [issue(1, updated=20)]
        sentinel.tick(NOW)
        with i18n.use_language("es"):
            spanish = sentinel.get_alerts()[0]["title"]
        with i18n.use_language("en"):
            english = sentinel.get_alerts()[0]["title"]
        self.assertNotEqual(spanish, english)
        self.assertIn("#1", english)
        self.assertEqual(sentinel.get_config_schema()["name"], "collab")
        self.assertIn("rules.issue_stale_days", sentinel.get_config_schema()["keys"])
        snap = sentinel.snapshot()
        self.assertEqual((snap["enabled"], snap["level"], len(snap["alerts"])), (True, "warn", 1))


class Wiring(unittest.TestCase):
    def test_every_account_and_the_demo_keep_the_state_of_collab_apart(self):
        self.assertIn(("sentinel_collab", "STATE_FILE", "sentinel_state/collab_state.json"), accounts.STATE_FILES)
        self.assertIn("collab_state.json", [old for old, _new in accounts.LEGACY])
        import demo_mode
        self.assertIn("sentinel_collab", [m for m, _a, _n in demo_mode.STATE_FILES])
        self.assertIn("collab_state.json", _testenv.WATCHED)

    def test_the_notifications_know_the_two_new_events_and_the_schema_lists_them(self):
        import notifiers
        self.assertIn("collab_new", notifiers.KNOWN_EVENTS)
        self.assertIn("collab_fixed", notifiers.KNOWN_EVENTS)
        schema = json.loads((HERE / "docs" / "schemas" / "notification_event.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["properties"]["kind"]["enum"]), set(notifiers.KNOWN_EVENTS))
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_por", "_jpn", "_zho"):
            self.assertIn("collab_fixed", (HERE / "docs" / f"NOTIFICATIONS{suffix}.md").read_text(encoding="utf-8"), suffix)

    def test_the_file_of_state_is_never_published_nor_committed(self):
        import make_release
        self.assertIn("collab_state.json", make_release.FORBIDDEN_NAMES)
        if (HERE.parent / ".gitignore").is_file():         # the zip of the package carries no .gitignore
            self.assertIn("monitor/collab_state.json", (HERE.parent / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_the_endpoint_is_absent_from_lite_and_the_page_has_the_layer(self):
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('"/api/sentinel"', text.split("LITE_PATHS = (", 1)[1].split(")", 1)[0])
        self.assertIn('path == "/api/sentinel/collab"', text)
        self.assertNotIn("sentinel_collab", (HERE / "actions_monitor_lite.py").read_text(encoding="utf-8") if (HERE / "actions_monitor_lite.py").exists() else "")
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('section("collab"', "function collabBox", "/api/sentinel/collab", "ui.collab_off"):
            self.assertIn(needle, page, needle)
        self.assertLess(page.index('section("a13"'), page.index('section("collab"'))
        self.assertIn("safeUrl", page.split("function collabBox", 1)[1].split("function collabLevel", 1)[0] + "safeUrl")      # the link goes through `link()`, which only lets github.com through
        self.assertIn("link(a.details.url", page)


if __name__ == "__main__":
    unittest.main()
