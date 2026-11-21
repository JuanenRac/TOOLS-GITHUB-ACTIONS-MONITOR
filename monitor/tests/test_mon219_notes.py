# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The notes of the monitor about the repositories: the class of what started a red, the workflows that are red on purpose (a reason, an owner and an end), the users who clone too many repositories,
the metadata columns read from a file of each repository and the people from outside the team who got no answer. Everything is off by default and read only."""
import base64
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api, toolconfig  # noqa: E402
from github_actions_monitor.data_pipeline import expected_red, meta_columns, redrule  # noqa: E402
from github_actions_monitor.sentinels import clone_anomaly  # noqa: E402
from github_actions_monitor.sentinels import sentinel_collab as sc  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
NOW = 1_800_000_000
DAY = 86400


def run(repo="a/b", path="ci.yml", conclusion="failure", event="push", started=NOW - 3600, branch="main", name="CI"):
    return {"repo": repo, "id": started, "name": name, "path": path, "event": event, "branch": branch, "status": "completed", "conclusion": conclusion, "started": time_text(started), "fork": False, "url": "u", "sha": "abc"}


def time_text(seconds):
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


class Isolated(unittest.TestCase):
    def setUp(self):
        _testenv.guard(self)
        for entry in expected_red.entries():
            expected_red.remove(entry["id"])
        expected_red.configure({"expected_red": {"enabled": True}})
        clone_anomaly.forget()

    def tearDown(self):
        for entry in expected_red.entries():
            expected_red.remove(entry["id"])
        expected_red.configure({})


class TriggerClass(unittest.TestCase):
    def test_every_event_has_a_class_that_does_not_depend_on_the_language(self):
        expected = {"push": "main", "schedule": "nightly", "workflow_dispatch": "manual", "repository_dispatch": "manual", "pull_request": "pr", "pull_request_target": "pr", "merge_group": "queue",
                    "workflow_run": "chained", "release": "other", "": "other"}
        for event, word in expected.items():
            self.assertEqual(redrule.trigger_class(event), word, event)
        self.assertEqual(redrule.trigger_class("push", "queue"), "queue")
        self.assertTrue(set(expected.values()) <= set(redrule.TRIGGER_CLASSES))

    def test_the_red_rows_and_the_failing_runs_say_what_started_them(self):
        redrule.configure({})
        runs = [run(event="schedule")]
        rows, _approx = redrule.red_workflows({"a/b": runs}, {"a/b": "main"})
        self.assertEqual((rows[0]["class"], rows[0]["event"]), ("nightly", "schedule"))
        self.assertEqual(redrule.red_runs(runs, "main")[0]["cls"], "nightly")
        self.assertEqual(am.unresolved_failures(runs, {"a/b": "main"})[0]["cls"], "nightly")

    def test_every_class_has_its_words_in_the_eight_languages(self):
        for lang in LANGS:
            for word in redrule.TRIGGER_CLASSES:
                self.assertTrue(LOCALES[lang].get("ui.cls_" + word), (lang, word))


class ExpectedRed(Isolated):
    def test_a_marked_workflow_is_listed_apart_and_comes_back_when_the_mark_runs_out(self):
        redrule.configure({"expected_red": {"enabled": True}})
        runs = [run()]
        self.assertEqual(len(redrule.classify(runs, "main")["red"]), 1)
        entry, why = expected_red.add("a/b", "ci.yml", "pipeline under construction", "ana", 3, 30)
        self.assertEqual(why, "")
        out = redrule.classify(runs, "main")
        self.assertEqual((len(out["red"]), len(out["expected"])), (0, 1))
        self.assertEqual(out["expected"][0]["mark"]["owner"], "ana")
        self.assertEqual(am.unresolved_failures(runs, {"a/b": "main"}), [])      # not counted as red and not alerted
        rows = redrule.states({"a/b": runs}, {"a/b": "main"})["expected"]
        self.assertEqual((rows[0]["reason"], rows[0]["owner"]), ("pipeline under construction", "ana"))
        self.assertEqual(expected_red.lookup("a/b", "ci.yml", now=NOW + 10 ** 9), None)      # the end has passed: red again
        self.assertEqual(expected_red.alerts("", now=NOW + 10 ** 9) and expected_red.alerts("", now=NOW + 10 ** 9)[0]["code"], "ci.expected_red_expired")
        self.assertTrue(expected_red.remove(entry["id"]))
        self.assertEqual(len(redrule.classify(runs, "main")["red"]), 1)

    def test_with_the_switch_off_a_mark_does_nothing(self):
        expected_red.add("a/b", "ci.yml", "x", "ana", 3, 30)
        expected_red.configure({})
        self.assertEqual(len(redrule.classify([run()], "main")["red"]), 1)
        self.assertEqual(expected_red.alerts(""), [])

    def test_a_mark_covers_only_what_it_names(self):
        expected_red.add("a/b", "ci.yml", "x", "ana", 3, 30)
        self.assertIsNotNone(expected_red.lookup("a/b", "CI.YML"))
        self.assertIsNone(expected_red.lookup("a/b", "other.yml"))
        self.assertIsNone(expected_red.lookup("a/c", "ci.yml"))
        expected_red.add("a/c", "*", "x", "ana", 3, 30)
        self.assertIsNotNone(expected_red.lookup("a/c", "anything.yml"))

    def test_a_mark_needs_a_reason_an_owner_and_never_lasts_longer_than_the_maximum(self):
        self.assertEqual(expected_red.add("a/b", "ci.yml", "", "ana", 3, 30)[1], "no_reason")
        self.assertEqual(expected_red.add("a/b", "ci.yml", "x", "", 3, 30)[1], "no_owner")
        self.assertEqual(expected_red.add("no repo", "ci.yml", "x", "ana", 3, 30)[1], "bad_repo")
        self.assertEqual(expected_red.add("a/b", "../x", "x", "ana", 3, 30)[1], "bad_workflow")
        entry, _ = expected_red.add("a/b", "ci.yml", "x", "ana", 9999, 30, now=NOW)
        self.assertEqual(entry["until"], NOW + 30 * DAY)
        self.assertEqual(expected_red.settings({"expected_red": {"enabled": True, "max_days": 9999}})["max_days"], 30)
        self.assertFalse(expected_red.settings({})["enabled"])

    def test_marking_again_renews_instead_of_adding_a_second_one(self):
        expected_red.add("a/b", "ci.yml", "x", "ana", 3, 30)
        expected_red.add("A/B", "CI.yml", "y", "ana", 5, 30)
        self.assertEqual(len(expected_red.entries()), 1)


class CloneAnomaly(Isolated):
    CFG = clone_anomaly.settings({"audit_feed": {"clone_alert": {"enabled": True}}})

    def entries(self, user, repos, at=NOW - 3600):
        return [{"action": "git.clone", "actor": user, "repo": f"org/{r}", "@timestamp": (at - i) * 1000, "actor_ip": "10.1.1.1"} for i, r in enumerate(repos)]

    def test_it_is_off_by_default_and_its_values_stay_in_range(self):
        self.assertFalse(clone_anomaly.settings({})["enabled"])
        self.assertEqual(clone_anomaly.settings({"audit_feed": {"clone_alert": {"threshold": 0, "window_hours": 9999, "bot_patterns": [1]}}})["threshold"], 5)
        self.assertEqual(clone_anomaly.settings({})["window_hours"], 24)

    def test_the_threshold_is_strict_and_different_repositories_are_counted_once(self):
        five = self.entries("ana", list("abcde"))
        six = self.entries("ana", list("abcdef"))
        self.assertEqual(clone_anomaly.analyze(clone_anomaly.parse(five), self.CFG, NOW), [])
        found = clone_anomaly.analyze(clone_anomaly.parse(six + six), self.CFG, NOW)
        self.assertEqual([(f["user"], f["count"]) for f in found], [("ana", 6)])

    def test_robots_and_old_events_are_left_out(self):
        events = self.entries("deploy-bot", list("abcdefg")) + self.entries("dependabot[bot]", list("abcdefg")) + self.entries("guardian", list("abcdefg")) + self.entries("bob", list("abcdefg"), at=NOW - 3 * DAY)
        self.assertEqual(clone_anomaly.analyze(clone_anomaly.parse(events), self.CFG, NOW), [])

    def test_no_address_is_kept_anywhere(self):
        parsed = clone_anomaly.parse(self.entries("ana", list("abcdefg")))
        self.assertNotIn("10.1.1.1", json.dumps(parsed))
        clone_anomaly._CACHE["answer"] = {"enabled": True, "window_hours": 24, "threshold": 5, "checked": NOW, "findings": clone_anomaly.analyze(parsed, self.CFG, NOW)}
        alerts = clone_anomaly.alerts("acc", now=NOW)
        self.assertEqual((alerts[0]["code"], alerts[0]["sentinel"], alerts[0]["details"]["count"]), ("audit.clone_anomaly", "system", 7))
        self.assertNotIn("10.1.1.1", json.dumps(alerts))
        self.assertIn("ana", alerts[0]["title"])

    def test_a_plan_without_the_git_events_is_unavailable_and_the_answer_is_kept(self):
        calls = []

        def refuse(endpoint):
            calls.append(endpoint)
            raise RuntimeError("404")
        answer = clone_anomaly.check(refuse, "org", self.CFG, now=NOW)
        self.assertEqual((answer["enabled"], answer["available"], answer["findings"]), (True, False, []))
        clone_anomaly.check(refuse, "org", self.CFG, now=NOW + 60)
        self.assertEqual(len(calls), 1)      # not read again inside check_minutes
        self.assertIn("include=git", calls[0])
        self.assertEqual(clone_anomaly.check(refuse, "org", {**self.CFG, "enabled": False}, now=NOW)["findings"], [])

    def test_a_read_that_works_names_the_user(self):
        clone_anomaly.forget()
        answer = clone_anomaly.check(lambda endpoint: self.entries("ana", list("abcdefg")), "org", self.CFG, now=NOW)
        self.assertTrue(answer["available"])
        self.assertEqual(answer["findings"][0]["user"], "ana")
        self.assertEqual(len(answer["findings"][0]["repos"]), 7)


class MetaColumns(unittest.TestCase):
    def test_a_column_is_checked_and_a_risky_expression_is_refused(self):
        ok, why = meta_columns.valid_column({"name": "Template", "path": ".template-version", "regex": r"^version: (\S+)"})
        self.assertEqual((ok["id"], why), ("template", ""))
        for bad, reason in (({"name": "", "path": "a", "regex": "x"}, "bad_name"), ({"name": "A", "path": "../x", "regex": "x"}, "bad_path"), ({"name": "A", "path": "/etc/x", "regex": "x"}, "bad_path"),
                            ({"name": "A", "path": "a", "regex": "("}, "bad_regex"), ({"name": "A", "path": "a", "regex": "(a+)+$"}, "risky_regex"), ({"name": "A", "path": "a", "regex": r"(a)\1"}, "risky_regex"),
                            ("x", "not_object")):
            self.assertEqual(meta_columns.valid_column(bad)[1], reason, bad)

    def test_the_settings_keep_at_most_five_valid_columns(self):
        cols = [{"name": f"C{i}", "path": "f", "regex": "x"} for i in range(9)] + [{"name": "bad", "path": "..", "regex": "x"}]
        self.assertEqual(len(meta_columns.settings({"fleet": {"meta_columns": cols}})["columns"]), 5)
        self.assertEqual(meta_columns.settings({})["columns"], [])
        self.assertEqual(meta_columns.settings({"fleet": {"meta_per_call": 9999}})["per_call"], 20)

    def test_extract_takes_the_first_group_of_the_first_match_and_cuts_it(self):
        self.assertEqual(meta_columns.extract("name: x\nversion: 1.2.3\nversion: 9", r"^version: (\S+)"), "1.2.3")
        self.assertEqual(meta_columns.extract("abc", r"b"), "b")
        self.assertEqual(meta_columns.extract("abc", r"zzz"), "")
        self.assertEqual(len(meta_columns.extract("v: " + "x" * 500, r"v: (.*)")), meta_columns.VALUE_MAX)

    def test_the_reader_reads_a_few_files_per_round_and_keeps_the_value_by_the_sha_of_the_blob(self):
        col, _ = meta_columns.valid_column({"name": "T", "path": "v.txt", "regex": r"^v=(\S+)"})
        reads = []

        def read(endpoint):
            reads.append(endpoint)
            if "/missing/" in endpoint:
                raise RuntimeError("404")
            return {"encoding": "base64", "sha": "s1", "content": base64.b64encode(b"v=7\n").decode()}
        reader = meta_columns.Reader()
        waiting = reader.fill(["o/a", "o/b", "o/missing"], [col], read, 2, 6, now=1000)
        self.assertEqual((len(reads), waiting), (2, 1))
        reader.fill(["o/a", "o/b", "o/missing"], [col], read, 2, 6, now=1001)
        self.assertEqual(reader.rows(["o/a", "o/missing"], [col]), {"o/a": {"t": "7"}, "o/missing": {"t": ""}})
        before = len(reads)
        reader.fill(["o/a"], [col], read, 5, 6, now=1002)      # inside the ttl: nothing is read
        self.assertEqual(len(reads), before)
        reader.fill(["o/a"], [col], read, 5, 6, now=1000 + 7 * 3600)      # after it: read again, same SHA, same value
        self.assertEqual(reader.rows(["o/a"], [col])["o/a"]["t"], "7")
        self.assertEqual(len(reads), before + 1)


def issue(number, updated=3, created=3, assoc="NONE", comments=0, login="stranger"):
    return {"number": number, "title": "t", "html_url": "u", "created_at": time_text(NOW - created * DAY), "updated_at": time_text(NOW - updated * DAY), "labels": [], "user": {"login": login, "type": "User"},
            "author_association": assoc, "comments": comments}


def pull(number, created=3, updated=None, assoc="NONE", login="stranger", draft=False, review=False):
    return {"number": number, "title": "t", "html_url": "u", "created_at": time_text(NOW - created * DAY), "updated_at": time_text(NOW - (created if updated is None else updated) * DAY), "labels": [],
            "user": {"login": login, "type": "User"}, "author_association": assoc, "draft": draft, "requested_reviewers": [{"login": "x"}] if review else []}


class CollabOutsiders(unittest.TestCase):
    RULES = {**sc.DEFAULTS["rules"], "watch_external_comments": True, "external_days": 3, "team_members": ["ana"]}

    def codes(self, issues=(), prs=(), rules=None):
        issues = [sc.slim_issue(i) if "created_at" in i else i for i in issues]
        prs = [sc.slim_pull(p) if "created_at" in p else p for p in prs]
        found = sc.evaluate("r", issues, prs, rules or self.RULES, NOW).values()
        return sorted((a["code"], a["number"], a["kind"]) for a in found if a["code"] == "collab.issue.external")

    def test_the_wait_is_the_setting_and_a_pull_request_counts_too(self):
        self.assertEqual(self.codes([issue(1, created=2, updated=2)], [pull(2, created=2)]), [])
        self.assertEqual(self.codes([issue(1, created=4, updated=4)], [pull(2, created=4)]), [("collab.issue.external", 1, "issue"), ("collab.issue.external", 2, "pr")])

    def test_a_person_of_the_team_list_is_never_chased_and_only_a_flag_is_kept(self):
        slim = sc.slim_issue(issue(3, created=9, updated=9, login="Ana"), {"ana"})
        self.assertTrue(slim["member"])
        self.assertNotIn("ana", json.dumps(slim).lower().replace("assoc", ""))
        self.assertEqual(self.codes([slim]), [])
        self.assertEqual(self.codes([sc.slim_pull(pull(4, created=9, login="ana"), None, {"ana"})]), [])

    def test_a_pull_request_somebody_touched_or_with_a_reviewer_is_not_chased(self):
        self.assertEqual(self.codes(prs=[sc.slim_pull(pull(5, created=9, updated=1))]), [])
        self.assertEqual(self.codes(prs=[sc.slim_pull(pull(6, created=9, review=True))]), [])
        self.assertEqual(self.codes(prs=[sc.slim_pull(pull(7, created=9, assoc="MEMBER"))]), [])

    def test_the_title_of_a_pull_request_says_so(self):
        alert = next(iter(sc.evaluate("r", [], [sc.slim_pull(pull(8, created=9))], self.RULES, NOW).values()))
        self.assertEqual(alert["kind"], "pr")
        sentinel = sc.SentinelCollab.__new__(sc.SentinelCollab)
        self.assertIn("Pull request", sentinel._title(alert))

    def test_the_new_settings_are_read_in_range(self):
        cfg = sc.settings({"sentinels": {"collab": {"rules": {"external_days": 500, "team_members": ["Ana", "Bob"]}}}})
        self.assertEqual((cfg["rules"]["external_days"], cfg["rules"]["team_members"]), (1, ["ana", "bob"]))


class Registered(unittest.TestCase):
    KEYS = ("fleet.meta_columns", "fleet.meta_per_call", "fleet.meta_ttl_hours", "sentinels.collab.rules.external_days", "sentinels.collab.rules.team_members", "expected_red.enabled", "expected_red.max_days",
            "audit_feed.clone_alert.enabled", "audit_feed.clone_alert.threshold", "audit_feed.clone_alert.window_hours", "audit_feed.clone_alert.check_minutes", "audit_feed.clone_alert.bot_patterns")

    def test_every_setting_has_its_place_its_example_and_its_words_in_the_eight_languages(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        for key in self.KEYS:
            self.assertIn(key, settings_api.META, key)
            node = example
            for part in key.split("."):
                node = node[part]
            for lang in LANGS:
                self.assertTrue(LOCALES[lang].get("cfg.f." + key) and LOCALES[lang].get("cfg.h." + key), (lang, key))
        for key in ("ui.cfg_b_expected_red", "ui.cfg_b_clones", "expected_red.alert_expired", "clones.alert", "collab.t.pr_external"):
            for lang in LANGS:
                self.assertTrue(LOCALES[lang].get(key), (lang, key))
        self.assertIs(am.DEFAULTS["expected_red"]["enabled"], False)
        self.assertIs(am.DEFAULTS["audit_feed"]["clone_alert"]["enabled"], False)
        self.assertEqual(am.DEFAULTS["fleet"]["meta_columns"], [])

    def test_the_setting_of_the_columns_refuses_a_bad_list(self):
        good = [{"name": "Template", "path": ".t", "regex": "^v=(.*)"}]
        self.assertEqual(settings_api.check_value("fleet.meta_columns", good), (True, good))
        self.assertEqual(settings_api.check_value("fleet.meta_columns", [{"name": "A", "path": "..", "regex": "x"}])[0], False)
        self.assertEqual(settings_api.check_value("fleet.meta_columns", [{"name": "A", "path": "a", "regex": "(a+)+"}])[0], False)
        self.assertEqual(settings_api.check_value("fleet.meta_columns", good * 6)[0], False)
        self.assertEqual(settings_api.check_value("fleet.meta_columns", [{"name": "A", "path": "a", "regex": "x", "extra": 1}])[0], False)


class Server(unittest.TestCase):
    token = "t" * 24

    def start(self, config):
        self.guard = _testenv.guard(unittest.TestCase())
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "actions_monitor.json"
        self.file.write_text(json.dumps(config), encoding="utf-8")
        self.saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE, dict(am.LIVE_CONFIG), settings_api.BACKUP_DIR)
        am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = self.file
        settings_api.BACKUP_DIR = Path(self.tmp.name) / "backups"
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, **config})
        toolconfig.forget()
        am.META["reader"] = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        if getattr(self, "server", None):
            self.server.shutdown()
            self.server.server_close()
            am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE = self.saved[:3]
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(self.saved[3])
            settings_api.BACKUP_DIR = self.saved[4]
            toolconfig.forget()
            for entry in expected_red.entries():
                expected_red.remove(entry["id"])
            expected_red.configure({})
            clone_anomaly.forget()
            self.tmp.cleanup()
            self.guard()

    def call(self, path, body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, method="GET" if body is None else "POST", headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:
                return answer.status, json.loads(answer.read() or b"{}")
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, (json.loads(raw) if raw[:1] == b"{" else raw)

    def sensitive(self, path, body):
        status, answer = self.call("/api/session-token")
        return self.call(path, body, {"X-Monitor-Token": answer["token"]})

    def test_the_marks_are_a_maintainer_note_behind_a_switch_and_the_one_use_token(self):
        self.start({})
        self.assertEqual(self.call("/api/expected-red")[1], {"enabled": False, "max_days": 30, "entries": []})
        self.assertEqual(self.sensitive("/api/expected-red", {"action": "add", "repo": "a/b", "workflow": "ci.yml", "reason": "x", "owner": "ana"})[0], 404)
        self.server.shutdown()
        self.server.server_close()
        self.tearDown()
        self.start({"expected_red": {"enabled": True, "max_days": 10}})
        body = {"action": "add", "repo": "a/b", "workflow": "ci.yml", "reason": "pipeline", "owner": "ana", "days": 99}
        self.assertEqual(self.call("/api/expected-red", body)[0], 403)      # no one-use token
        status, answer = self.sensitive("/api/expected-red", body)
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["entry"]["until"] - answer["entry"]["created"], 10 * DAY)
        self.assertEqual(self.sensitive("/api/expected-red", {"action": "add", "repo": "a/b", "workflow": "ci.yml", "reason": "", "owner": "ana"})[0], 400)
        listing = self.call("/api/expected-red")[1]
        self.assertEqual([e["state"] for e in listing["entries"]], ["active"])
        self.assertEqual(self.sensitive("/api/expected-red", {"action": "remove", "id": answer["entry"]["id"]})[0], 200)
        self.assertEqual(self.sensitive("/api/expected-red", {"action": "remove", "id": answer["entry"]["id"]})[0], 404)
        self.assertEqual(self.sensitive("/api/expected-red", {"action": "nothing"})[0], 400)

    def test_the_clone_answer_is_off_by_default(self):
        self.start({})
        status, answer = self.call("/api/clone-anomalies")
        self.assertEqual((status, answer["enabled"], answer["findings"]), (200, False, []))

    def test_the_columns_answer_lists_the_columns_and_never_fails_without_data(self):
        self.start({"fleet": {"meta_columns": [{"name": "Template", "path": ".t", "regex": "^v=(.*)"}, {"name": "bad", "path": "..", "regex": "x"}]}})
        status, answer = self.call("/api/meta-columns")
        self.assertEqual(status, 200)
        self.assertEqual(answer["columns"], [{"id": "template", "name": "Template"}])
        self.assertTrue(all(row == {"template": ""} for row in answer["rows"].values()), answer["rows"])      # no value is invented for a repository (a repository left in memory by another test has an empty cell)


if __name__ == "__main__":
    unittest.main()
