# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The conditional reads tell the truth: an entry belongs to the credential that read it, a state in motion is never answered from the cache, a refusal is remembered only briefly and the health of the cache
is visible."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from github_actions_monitor.data_pipeline import etagcache, signals  # noqa: E402
from github_actions_monitor.integrations import outputs  # noqa: E402

NOW = 1_800_000_000.0
RUNS = "repos/o/r/actions/runs?per_page=5"


def answer(status, tag, body):
    head = f"HTTP/2.0 {status} OK\n" + (f'Etag: {tag}\n' if tag else "")
    return 0, head + "\n" + body, ""


def make(**kw):
    return etagcache.EtagCache(Path(tempfile.mkdtemp()) / "e.json", **kw)


class Recorder:
    """A fake `gh`: remembers the arguments of every call and answers from a queue."""
    def __init__(self, *answers):
        self.calls, self.answers = [], list(answers)

    def __call__(self, args):
        self.calls.append(args)
        return self.answers.pop(0)

    def sent_etag(self, index):
        return any(a.startswith("If-None-Match") for a in self.calls[index])


class IdentityOfTheCredential(unittest.TestCase):
    def test_the_same_endpoint_read_with_two_credentials_has_two_entries(self):
        who = ["aaaaaaaa"]
        cache = make(identity=lambda: who[0])
        cache.fetch("repos/o/r", Recorder(answer(200, '"one"', '{"who": 1}')), now=NOW)
        who[0] = "bbbbbbbb"
        run = Recorder(answer(200, '"two"', '{"who": 2}'))
        data, status = cache.fetch("repos/o/r", run, now=NOW)
        self.assertEqual((data, status), ({"who": 2}, "200"))
        self.assertFalse(run.sent_etag(0), "the ETag of another credential is never sent")
        self.assertEqual(len(cache.entries), 2)
        who[0] = "aaaaaaaa"
        run = Recorder(answer(304, "", ""))
        self.assertEqual(cache.fetch("repos/o/r", run, now=NOW), ({"who": 1}, "304"))

    def test_the_fingerprint_is_short_stable_and_never_the_secret(self):
        value = etagcache.fingerprint("ghp_secret_value")
        self.assertEqual(len(value), 8)
        self.assertEqual(value, etagcache.fingerprint("ghp_secret_value"))
        self.assertNotIn("secret", value)
        self.assertEqual(etagcache.fingerprint(""), "00000000")
        self.assertNotEqual(value, etagcache.fingerprint("another"))

    def test_a_race_between_two_identities_never_hands_back_the_body_of_the_other(self):
        who = threading.local()
        cache = make(identity=lambda: who.name)
        errors = []

        def worker(name, tag):
            who.name = name
            for round_number in range(200):
                body = json.dumps({"owner": name})
                run = Recorder(answer(200, f'"{tag}{round_number}"', body))
                data, _status = cache.fetch("installation/repositories", run, now=NOW)
                if data != {"owner": name}:
                    errors.append((name, data))
                run = Recorder(answer(304, "", ""))
                data, _status = cache.fetch("installation/repositories", run, now=NOW)
                if data != {"owner": name}:
                    errors.append((name, data))
        threads = [threading.Thread(target=worker, args=(f"{n:08x}", chr(97 + n))) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(cache.entries), 4)

    def test_a_file_from_before_the_identity_is_read_as_an_empty_cache(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "e.json").write_text(json.dumps({"entries": {"repos/o/r": {"etag": '"x"', "at": NOW, "data": {}}}}), encoding="utf-8")
        self.assertEqual(etagcache.EtagCache(folder / "e.json").entries, {})

    def test_invalidating_a_repository_drops_it_whatever_the_identity(self):
        who = ["aaaaaaaa"]
        cache = make(identity=lambda: who[0])
        cache.fetch("repos/o/r/actions/runs", Recorder(answer(200, '"a"', "{}")), now=NOW)
        who[0] = "bbbbbbbb"
        cache.fetch("repos/o/r/actions/runs", Recorder(answer(200, '"b"', "{}")), now=NOW)
        self.assertEqual(cache.invalidate("r"), 2)


class StateInMotion(unittest.TestCase):
    def test_a_list_with_a_running_run_is_read_in_full_next_time(self):
        cache = make()
        cache.fetch(RUNS, Recorder(answer(200, '"a"', json.dumps({"workflow_runs": [{"status": "in_progress"}]}))), now=NOW)
        run = Recorder(answer(200, '"b"', json.dumps({"workflow_runs": [{"status": "completed"}]})))
        data, status = cache.fetch(RUNS, run, now=NOW + 5)
        self.assertEqual(status, "200")
        self.assertFalse(run.sent_etag(0), "a finished run is never hidden behind an old 304")
        self.assertEqual(cache.stats()["skipped_active"], 1)

    def test_a_quiet_list_is_asked_with_its_etag(self):
        cache = make()
        cache.fetch(RUNS, Recorder(answer(200, '"a"', json.dumps({"workflow_runs": [{"status": "completed"}]}))), now=NOW)
        run = Recorder(answer(304, "", ""))
        self.assertEqual(cache.fetch(RUNS, run, now=NOW + 5)[1], "304")
        self.assertTrue(run.sent_etag(0))

    def test_the_jobs_of_a_run_and_the_check_suites_are_never_conditional(self):
        for endpoint in ("repos/o/r/actions/runs/123/jobs", "repos/o/r/actions/runs/123", "repos/o/r/commits/abc/check-suites", "repos/o/r/commits/abc/check-runs", "repos/o/r/commits/abc/status", "repos/o/r/actions/jobs/9"):
            self.assertTrue(etagcache.is_stateful(endpoint), endpoint)
            cache = make()
            cache.fetch(endpoint, Recorder(answer(200, '"a"', "{}")), now=NOW)
            run = Recorder(answer(200, '"a2"', "{}"))
            cache.fetch(endpoint, run, now=NOW + 1)
            self.assertFalse(run.sent_etag(0), endpoint)
        self.assertFalse(etagcache.is_stateful(RUNS))
        self.assertFalse(etagcache.is_stateful("repos/o/r"))

    def test_both_protections_can_be_turned_off(self):
        cache = make(skip_stateful=False, revalidate_active=False)
        cache.fetch("repos/o/r/actions/runs/1/jobs", Recorder(answer(200, '"a"', json.dumps({"jobs": [{"status": "queued"}]}))), now=NOW)
        run = Recorder(answer(304, "", ""))
        self.assertEqual(cache.fetch("repos/o/r/actions/runs/1/jobs", run, now=NOW + 1)[1], "304")

    def test_a_fake_transport_that_says_304_while_the_state_changed_is_not_believed_for_running_work(self):
        cache = make()
        cache.fetch(RUNS, Recorder(answer(200, '"a"', json.dumps({"workflow_runs": [{"id": 1, "status": "queued"}]}))), now=NOW)

        def lying(args):       # GitHub keeps saying 304 although the run finished; no If-None-Match is sent, so a real server cannot say it
            if any(a.startswith("If-None-Match") for a in args):
                return answer(304, "", "")
            return answer(200, '"c"', json.dumps({"workflow_runs": [{"id": 1, "status": "completed", "conclusion": "failure"}]}))
        data, _status = cache.fetch(RUNS, lying, now=NOW + 30)
        self.assertEqual(data["workflow_runs"][0]["conclusion"], "failure")

    def test_has_active_reads_the_shapes_of_the_api(self):
        self.assertTrue(etagcache.has_active({"jobs": [{"status": "waiting"}]}))
        self.assertTrue(etagcache.has_active({"check_runs": [{"status": "queued"}]}))
        self.assertFalse(etagcache.has_active({"workflow_runs": [{"status": "completed"}]}))
        self.assertFalse(etagcache.has_active([1, 2]))
        self.assertFalse(etagcache.has_active({"workflow_runs": "x"}))


class RefusalsAreRemembered(unittest.TestCase):
    def refuse(self, text):
        return (1, "", text)

    def test_a_404_is_not_asked_again_inside_the_time(self):
        cache = make(negative_ttl=300)
        with self.assertRaises(RuntimeError):
            cache.fetch("repos/o/r/dependabot/alerts", Recorder(self.refuse("gh: Not Found (HTTP 404)")), now=NOW)
        run = Recorder()
        with self.assertRaises(RuntimeError) as caught:
            cache.fetch("repos/o/r/dependabot/alerts", run, now=NOW + 299)
        self.assertEqual(run.calls, [], "no request is made while the refusal is remembered")
        self.assertIn("404", str(caught.exception))
        self.assertEqual(cache.stats()["denied_hits"], 1)
        self.assertEqual(cache.fetch("repos/o/r/dependabot/alerts", Recorder(answer(200, '"a"', "[]")), now=NOW + 300)[0], [])

    def test_a_rate_limit_or_a_server_error_is_never_remembered(self):
        for text in ("gh: API rate limit exceeded (HTTP 403)", "You have exceeded a secondary rate limit (HTTP 403)", "gh: Server Error (HTTP 502)", "timeout"):
            cache = make(negative_ttl=300)
            with self.assertRaises(RuntimeError):
                cache.fetch("e", Recorder(self.refuse(text)), now=NOW)
            self.assertEqual(cache.denied, {}, text)

    def test_zero_means_never_remembered(self):
        cache = make(negative_ttl=0)
        with self.assertRaises(RuntimeError):
            cache.fetch("e", Recorder(self.refuse("gh: Forbidden (HTTP 403)")), now=NOW)
        self.assertEqual(cache.denied, {})

    def test_the_memory_of_a_refusal_is_per_credential(self):
        who = ["aaaaaaaa"]
        cache = make(identity=lambda: who[0])
        with self.assertRaises(RuntimeError):
            cache.fetch("e", Recorder(self.refuse("gh: Not Found (HTTP 404)")), now=NOW)
        who[0] = "bbbbbbbb"
        self.assertEqual(cache.fetch("e", Recorder(answer(200, '"a"', "{}")), now=NOW)[0], {})

    def test_invalidating_a_repository_forgets_its_refusals(self):
        cache = make()
        with self.assertRaises(RuntimeError):
            cache.fetch("repos/o/r/dependabot/alerts", Recorder(self.refuse("gh: Not Found (HTTP 404)")), now=NOW)
        cache.invalidate("r")
        self.assertEqual(cache.denied, {})


class HealthIsVisible(unittest.TestCase):
    def test_answers_without_an_etag_are_counted(self):
        cache = make()
        for _ in range(3):
            self.assertEqual(cache.fetch("e", Recorder(answer(200, "", "{}")), now=NOW)[1], "plain")
        stats = cache.stats()
        self.assertEqual((stats["no_etag"], stats["calls"], stats["hit_pct"]), (3, 3, 0.0))

    def test_the_hit_share_counts_the_304(self):
        cache = make()
        cache.fetch("e", Recorder(answer(200, '"a"', "{}")), now=NOW)
        cache.fetch("e", Recorder(answer(304, "", "")), now=NOW)
        self.assertEqual(cache.stats()["hit_pct"], 50.0)

    def test_the_metrics_carry_the_new_counters(self):
        text = outputs.metrics_text({}, {}, extra={"etag": {"saved": 1, "entries": 1, "invalid": 0, "no_etag": 4, "skipped_stateful": 2, "skipped_active": 3, "denied_hits": 5}})
        self.assertIn("ghamon_etag_no_etag_total 4", text)
        self.assertIn("ghamon_etag_skipped_total 5", text)
        self.assertIn("ghamon_etag_refused_total 5", text)

    def test_the_signal_warns_only_when_the_cache_does_nothing(self):
        fine = signals.etag_health_signal({"calls": 100, "saved": 80, "no_etag": 0, "hit_pct": 80.0})
        self.assertEqual(fine["level"], "info")
        bad = signals.etag_health_signal({"calls": 100, "saved": 2, "no_etag": 60, "hit_pct": 2.0})
        self.assertEqual(bad["level"], "watch")
        self.assertIn("without ETag", bad["summary"])
        few = signals.etag_health_signal({"calls": 5, "saved": 0, "no_etag": 5, "hit_pct": 0.0})
        self.assertEqual(few["level"], "info")


class SettingsAreWired(unittest.TestCase):
    def test_the_defaults_and_the_rows_agree(self):
        from github_actions_monitor.app import actions_monitor as am, settings_api
        cache = am.DEFAULTS["cache"]
        self.assertEqual((cache["etag"]["skip_stateful"], cache["etag"]["revalidate_active"], cache["negative_ttl_s"]), (True, True, 300))
        keys = {row[2] for row in settings_api.ROWS}
        self.assertTrue({"cache.etag.skip_stateful", "cache.etag.revalidate_active", "cache.negative_ttl_s"} <= keys)

    def test_the_fingerprint_of_the_running_credential_is_a_short_hex_string(self):
        from github_actions_monitor.app import actions_monitor as am
        self.assertRegex(am.credential_fingerprint(), r"^[0-9a-f]{8}$")


if __name__ == "__main__":
    unittest.main()
