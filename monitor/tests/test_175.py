# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The round after 1.7.4: the command line takes the access token of the monitor under its own name (and warns about plain http), the edition is called `complete` by the API (the clients
still understand `full`), the bar at the foot does not hand out the address of the computer to a client of the network, the address with `?access=` can be turned off, a silence can last
"until the item changes", the doctor notices one token shared by several accounts, the webhook lets nothing sensitive through, and the workflows of this repository are pinned to commits."""
import contextlib
import hashlib
import io
import json
import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import alert_center  # noqa: E402
import doctor  # noqa: E402
import i18n  # noqa: E402
import localguard  # noqa: E402
import monitor_cli as cli  # noqa: E402
import webhook  # noqa: E402
from test_164 import LiveServer  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
WANTED = "S3cret-access-token-for-the-fake-monitor"
SEEN = []
JSON = {"Accept": "application/json"}


class Strict(BaseHTTPRequestHandler):
    """A monitor of the network mode that answers only to a client that sends the access token in the header."""

    def do_GET(self):    # noqa: N802
        SEEN.append(self.headers.get("X-Monitor-Access"))
        if self.headers.get("X-Monitor-Access") != WANTED:
            self.send_response(401)
            self.end_headers()
            return
        path = self.path.partition("?")[0]
        body = json.dumps({"ok": True, "version": "1.7.4", "lite": False, "uptime_seconds": 5, "account": "a"} if path == "/api/health" else
                          {"data": {"repos": [], "figures": {}, "rate": {"remaining": 4000, "limit": 5000}, "offline": {"offline": False}}, "error": None}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def run(env, *argv):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(cli.os.environ, env, clear=False), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliToken(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Strict)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def ask(self, env, *extra):
        clean = {"MONITOR_ACCESS_TOKEN": "", "MONITOR_TOKEN": ""}
        return run({**clean, **env}, "status", "--url", self.url, "--lang", "en", *extra)

    def test_the_variable_the_monitor_itself_reads_is_the_first_choice(self):
        SEEN.clear()
        code, out, _ = self.ask({"MONITOR_ACCESS_TOKEN": WANTED})
        self.assertEqual(code, 0, out)
        self.assertEqual(set(SEEN), {WANTED})

    def test_the_old_name_is_an_alias_and_the_flag_is_the_last_resort(self):
        self.assertEqual(self.ask({"MONITOR_TOKEN": WANTED})[0], 0)
        self.assertEqual(self.ask({}, "--token", WANTED)[0], 0)
        self.assertEqual(cli.resolve_token({"MONITOR_ACCESS_TOKEN": "a", "MONITOR_TOKEN": "b"}, "c"), "a")
        self.assertEqual(cli.resolve_token({"MONITOR_TOKEN": "b"}, "c"), "b")
        self.assertEqual(cli.resolve_token({}, " c "), "c")
        self.assertEqual(cli.resolve_token({}, ""), "")

    def test_a_wrong_or_missing_token_is_exit_three_and_the_message_names_the_variable(self):
        code, _, err = self.ask({"MONITOR_ACCESS_TOKEN": "wrong"})
        self.assertEqual(code, 3)
        self.assertIn("MONITOR_ACCESS_TOKEN", err)
        self.assertEqual(self.ask({})[0], 3)

    def test_the_help_and_the_guide_name_the_token(self):
        text = cli.build_parser().format_help()
        self.assertIn("--token", text)
        self.assertIn("MONITOR_ACCESS_TOKEN", (HERE / "docs" / "CLI.md").read_text(encoding="utf-8"))
        for lang in LANGS:
            self.assertIn("MONITOR_ACCESS_TOKEN", i18n.tl(lang, "cli.refused"), lang)
            self.assertIn("MONITOR_ACCESS_TOKEN", i18n.tl(lang, "cli.help_token"), lang)

    def test_the_quickstart_of_every_language_names_the_variable(self):
        for lang in LANGS:
            self.assertIn("MONITOR_ACCESS_TOKEN", (HERE / f"QUICKSTART_{lang}.txt").read_text(encoding="utf-8"), lang)


class PlainHttpWarning(unittest.TestCase):
    def test_http_to_another_computer_is_told_and_this_computer_is_not(self):
        self.assertEqual(cli.plain_http_to_network("http://192.168.0.20:8765"), "192.168.0.20")
        self.assertEqual(cli.plain_http_to_network("http://monitor.lan:8765"), "monitor.lan")
        for quiet in ("http://127.0.0.1:8765", "http://localhost:8765", "https://192.168.0.20:8765", "http://[::1]:8765"):
            self.assertEqual(cli.plain_http_to_network(quiet), "", quiet)

    def test_the_warning_goes_to_stderr_not_to_the_answer(self):
        _code, out, err = run({"MONITOR_ACCESS_TOKEN": ""}, "status", "--url", "http://192.0.2.1:9", "--timeout", "1", "--json", "--lang", "en")
        self.assertIn("192.0.2.1", err)
        self.assertIn("unencrypted", err)
        self.assertNotIn("unencrypted", out)
        _code, _out, err = run({}, "status", "--url", "http://127.0.0.1:9", "--timeout", "1", "--lang", "en")
        self.assertNotIn("unencrypted", err)

    def test_the_warning_exists_in_every_language(self):
        for lang in LANGS:
            self.assertIn("{host}", i18n.tl(lang, "cli.plain_http"), lang)


class EditionName(unittest.TestCase):
    def test_the_api_says_complete_and_never_full(self):
        import about
        self.assertEqual(about.info(False, {}, {}, {}, "en")["edition"], "complete")
        self.assertEqual(about.info(True, {}, {}, {}, "en")["edition"], "lite")
        self.assertEqual(doctor.as_json([], "complete")["edition"], "complete")
        self.assertEqual(doctor.as_json([], "full")["edition"], "complete")
        self.assertEqual(am.statusbar_payload(8765)["edition"], "complete")
        self.assertEqual(cli.PORTS, {"complete": 8765, "lite": 8766})

    def test_the_clients_understand_both_names(self):
        html = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('T("ui.edition_"+(a.edition==="lite"?"lite":"complete"))', html)
        for lang in LANGS:
            self.assertNotEqual(i18n.tl(lang, "ui.edition_complete"), "ui.edition_complete", lang)
            self.assertNotEqual(i18n.tl(lang, "cli.edition_complete"), "cli.edition_complete", lang)
        health = {"version": "1.7.4", "lite": False, "account": "a"}
        with mock.patch.object(cli, "fetch", side_effect=[health, {"data": {"repos": []}}]):
            payload, lines, _ = cli.cmd_status({"base": "http://x", "account": "", "timeout": 1, "token": ""})
        self.assertEqual(payload["edition"], "complete")
        self.assertIn("complete edition", lines[0])


class SilencesAreLocal(unittest.TestCase):
    def test_silencing_needs_the_computer_of_the_monitor(self):
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        route = text.split('if path in ("/api/gh-action/plan"', 1)[1].split(")", 1)[0]
        self.assertIn('"/api/alerts/mute"', route)
        self.assertIn('"/api/alerts/unmute"', route)
        self.assertIn("if not self.guard() or not self.this_computer()", text)

    def test_a_client_of_the_network_cannot_silence(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            with mock.patch.object(localguard, "from_this_computer", return_value=False):
                status, _ = server.call("/api/alerts/mute", {"scope": "code", "value": "ci.red"}, {"Cookie": "monitor_access=" + access, "X-Monitor-Token": "x"})
            self.assertIn(status, (401, 403))

    def test_the_documentation_says_so_in_every_language(self):
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"COLLAB{suffix}.md").read_text(encoding="utf-8")
            self.assertIn("this_computer", text, suffix)


class StatusBarAddress(unittest.TestCase):
    def tearDown(self):
        localguard.configure(False)

    def test_the_address_of_the_computer_is_not_handed_to_a_client_of_the_network(self):
        localguard.configure(True, "0.0.0.0", "T" * 24)
        self.assertIn("lan_address", am.statusbar_payload(8765, True))
        self.assertNotIn("lan_address", am.statusbar_payload(8765, False))
        localguard.configure(False)
        self.assertIn("lan_address", am.statusbar_payload(8765, False))            # without the network mode nobody but this computer can ask

    def test_the_bar_still_draws_without_the_address(self):
        html = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('SBINFO.bind==="0.0.0.0"&&SBINFO.lan_address?SBINFO.lan_address:"127.0.0.1"', html)


class QueryAccess(unittest.TestCase):
    def test_the_address_works_by_default_but_only_on_a_get(self):
        self.assertTrue(localguard.query_access_allowed({}))
        self.assertTrue(localguard.query_token_counts("GET", "/?access=x", {}))
        self.assertFalse(localguard.query_token_counts("POST", "/api/settings?access=x", {}))

    def test_the_switch_turns_it_off(self):
        config = {"listen": {"query_access": False}}
        self.assertFalse(localguard.query_access_allowed(config))
        self.assertFalse(localguard.query_token_counts("GET", "/?access=x", config))
        self.assertTrue(localguard.query_access_allowed({"listen": {"query_access": "no"}}))        # only a real false turns it off

    def test_a_real_server_follows_the_switch_and_the_post_keeps_working(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            self.assertEqual(server.call("/api/about?access=" + access, headers=JSON)[0], 200)
        with LiveServer({"listen": {"query_access": False}}, network=access) as server:
            self.assertEqual(server.call("/api/about?access=" + access, headers=JSON)[0], 401)
            status, _ = server.call("/api/access", {"token": access})
            self.assertEqual(status, 200)

    def test_the_redirect_marks_the_address_as_deprecated(self):
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('self.send_header("Deprecation", "true")', text)
        self.assertTrue(am.DEFAULTS["listen"]["query_access"])

    def test_the_setting_is_in_the_schema_the_example_and_the_eight_languages(self):
        import settings_api
        self.assertIn("listen.query_access", settings_api.META)
        self.assertIs(json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))["listen"]["query_access"], True)
        for lang in LANGS:
            for key in ("cfg.f.listen.query_access", "cfg.h.listen.query_access", "mon.network_token_deprecated", "mon.network_token_post"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        self.assertIn("listen.query_access", (HERE / "docs" / "SETTINGS.md").read_text(encoding="utf-8"))


class SnoozeUntilChange(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(alert_center, "STATE_FILE", Path(self.tmp.name) / "alert_mutes.json")
        patch.start()
        self.addCleanup(patch.stop)

    @staticmethod
    def alert(updated):
        return {"id": "collab.issue.stale:r:7", "code": "collab.issue.stale", "sentinel": "collab", "details": {"updated": updated}}

    def test_the_silence_lasts_until_the_updated_at_changes(self):
        entry = alert_center.mute("alert", "collab.issue.stale:r:7", 24, until_change="2030-01-01T10:00:00Z", now=1_900_000_000)
        self.assertEqual(entry["until_change"], "2030-01-01T10:00:00Z")
        live = alert_center.active(1_900_000_100)
        self.assertEqual(len(live), 1)
        self.assertIsNotNone(alert_center.muted_until(self.alert("2030-01-01T10:00:00Z"), live))
        self.assertIsNone(alert_center.muted_until(self.alert("2030-01-02T08:00:00Z"), live))          # a new comment: it speaks again

    def test_it_still_ends_with_the_hours_and_an_alert_without_the_field_stays_silenced(self):
        alert_center.mute("alert", "collab.issue.stale:r:7", 1, until_change="v1", now=1_900_000_000)
        self.assertEqual(alert_center.active(1_900_000_000 + 3601), [])
        alert_center.mute("alert", "collab.issue.stale:r:7", 5, until_change="v1", now=1_900_000_000)
        self.assertIsNotNone(alert_center.muted_until({"id": "collab.issue.stale:r:7", "details": {}}, alert_center.active(1_900_000_100)))

    def test_only_an_alert_can_wait_for_a_change_and_the_plain_silence_is_unchanged(self):
        self.assertNotIn("until_change", alert_center.mute("code", "ci.red", 2, until_change="v1", now=1_900_000_000))
        self.assertNotIn("until_change", alert_center.mute("alert", "x", 2, now=1_900_000_000))

    def test_the_collab_alerts_carry_the_updated_at(self):
        import sentinel_collab
        issue = {"number": 7, "title": "t", "url": "u", "created": "2020-01-01T00:00:00Z", "updated": "2020-01-02T00:00:00Z", "labels": [], "bot": False, "assoc": "NONE", "comments": 0}
        found = sentinel_collab.evaluate("r", [issue], [], sentinel_collab.DEFAULTS["rules"], 1_900_000_000)
        self.assertEqual([a["code"] for a in found.values()], ["collab.issue.stale"])
        self.assertEqual([a["updated"] for a in found.values()], ["2020-01-02T00:00:00Z"])
        self.assertIn('"updated": a.get("updated")', (HERE / "sentinel_collab.py").read_text(encoding="utf-8"))


class SharedCredential(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def make(self, *ids, token_enabled=()):
        for account_id in ids:
            folder = self.base / "accounts" / account_id
            folder.mkdir(parents=True)
            cfg = {"github_owner": account_id, "github_token": {"enabled": account_id in token_enabled, "store": "file"}}
            (folder / "actions_monitor.json").write_text(json.dumps(cfg), encoding="utf-8")

    def check(self, env, loader=None):
        with mock.patch.dict("os.environ", {"MONITOR_ACCOUNTS_DIR": str(self.base / "accounts")}):
            return doctor.shared_credential(self.base, env=env, loader=loader)

    def test_two_accounts_with_the_same_token_warn_with_a_fingerprint_and_never_the_token(self):
        self.make("one", "two", token_enabled=("one", "two"))
        status, detail = self.check({}, loader=lambda: "ghp_" + "A" * 36)
        self.assertEqual(status, "warn")
        self.assertIn(hashlib.sha256(("ghp_" + "A" * 36).encode()).hexdigest()[:8], detail)
        self.assertIn("one", detail)
        self.assertNotIn("ghp_", detail)

    def test_the_token_of_the_environment_is_shared_by_every_account(self):
        self.make("one", "two", "three")
        status, detail = self.check({"GH_TOKEN": "ghp_" + "B" * 36})
        self.assertEqual(status, "warn")
        self.assertIn("three", detail)

    def test_one_account_or_the_login_of_gh_is_fine(self):
        self.make("one")
        self.assertEqual(self.check({"GH_TOKEN": "ghp_" + "B" * 36})[0], "ok")
        self.make("two")
        self.assertEqual(self.check({})[0], "ok")                                                  # nothing to compare: each uses the login of gh

    def test_the_check_is_in_the_doctor_in_every_language_and_in_the_order(self):
        self.assertIn("credential", doctor.ORDER)
        for lang in LANGS:
            self.assertNotEqual(i18n.tl(lang, "doctor.t.credential"), "doctor.t.credential", lang)
            self.assertNotEqual(i18n.tl(lang, "doctor.f.credential"), "doctor.f.credential", lang)
        self.assertEqual(doctor.fingerprint("abc"), hashlib.sha256(b"abc").hexdigest()[:8])


class WebhookHygiene(unittest.TestCase):
    SENSITIVE = ("hunter2-secret", "leak@example.com", "do not show this commit message", "ghs_SHOULDNEVERAPPEAR")

    def payload(self):
        sensitive = self.SENSITIVE
        run = {"id": 91, "name": "CI", "path": ".github/workflows/ci.yml@refs/heads/main", "status": "completed", "conclusion": "failure", "head_branch": "main", "head_sha": "0123456789abcdef0123",
               "html_url": "https://github.com/o/r/actions/runs/91", "run_started_at": "2030-01-01T10:00:00Z", "updated_at": "2030-01-01T10:05:00Z", "run_attempt": 1,
               "display_title": sensitive[2], "head_commit": {"message": sensitive[2], "author": {"email": sensitive[1]}}, "actor": {"login": "someone", "email": sensitive[1]},
               "secret": sensitive[0], "token": sensitive[3], "environment": {"API_KEY": sensitive[0]}}
        return json.dumps({"repository": {"name": "r", "full_name": "o/r"}, "workflow_run": run, "sender": {"email": sensitive[1]}, "installation": {"token": sensitive[3]}}).encode()

    def test_the_parsed_record_has_only_the_allowed_fields_and_none_of_the_sensitive_text(self):
        record = webhook.parse_event("workflow_run", self.payload())
        self.assertIsNotNone(record)
        self.assertTrue(set(record) <= set(webhook.LIVE_FIELDS) | {"steps"}, set(record) - set(webhook.LIVE_FIELDS))
        dumped = json.dumps(record)
        for text in self.SENSITIVE:
            self.assertNotIn(text, dumped)

    def test_the_live_list_the_feed_and_the_notification_carry_none_of_it(self):
        record = webhook.parse_event("workflow_run", self.payload())
        record = dict(record, extra_field=self.SENSITIVE[0], steps={"s": 1})                       # even a field that slipped into the record must not get out
        told = []
        saved = list(am.LIVE_EVENTS)
        self.addCleanup(lambda: am.LIVE_EVENTS.__setitem__(slice(None), saved))
        am.LIVE_EVENTS.clear()
        with mock.patch("notifiers.notify", side_effect=lambda cfg, event: told.append(event)):
            am.apply_live_event(record, {})
        self.assertEqual(len(am.LIVE_EVENTS), 1)
        self.assertTrue(set(am.LIVE_EVENTS[0]) <= set(webhook.LIVE_FIELDS) | {"at"})
        wire = json.dumps(am.LIVE_EVENTS) + json.dumps(told, default=str)
        for text in self.SENSITIVE:
            self.assertNotIn(text, wire)
        self.assertEqual(told[0]["kind"], "workflow_failed")

    def test_the_live_endpoint_serves_only_the_list(self):
        saved = list(am.LIVE_EVENTS)
        self.addCleanup(lambda: am.LIVE_EVENTS.__setitem__(slice(None), saved))
        am.LIVE_EVENTS.clear()
        with mock.patch("notifiers.notify"):
            am.apply_live_event(webhook.parse_event("workflow_run", self.payload()), {})
        with LiveServer({}) as server:
            status, answer = server.call("/api/live-events")
        self.assertEqual(status, 200)
        for text in self.SENSITIVE:
            self.assertNotIn(text, json.dumps(answer))


class PinnedWorkflows(unittest.TestCase):
    def test_every_action_of_every_workflow_is_pinned_to_a_full_commit(self):
        files = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        if not files:
            self.skipTest("the workflows are not part of the package")
        for path in files:
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"\s*-?\s*uses:\s*([^\s#]+)", line)
                if match and not match.group(1).startswith("./"):
                    self.assertRegex(match.group(1), r"@[0-9a-f]{40}$", f"{path.name}: {line.strip()}")


def _run(repo, name, conclusion, started, path="ci.yml", rid=1):
    return {"repo": repo, "id": rid, "name": name, "path": ".github/workflows/" + path, "branch": "main", "status": "completed", "conclusion": conclusion, "started": started,
            "url": f"https://github.com/JuanenRac/{repo}/actions/runs/{rid}"}


class IssueNeedsItsOwnWorkflow(unittest.TestCase):
    ISSUE = [{"repo": "R", "number": 9, "title": "Firmware build failed", "url": "u", "created": "2030-01-01T10:00:00Z"}]

    def suggest(self, runs):
        import surface
        return surface.issue_close_suggestions(self.ISSUE, {"R": runs}, set(), {}, 1_900_000_000)

    def test_a_green_run_of_another_workflow_never_proposes_closing(self):
        runs = [_run("R", "Notify central ecosystem dashboard", "success", "2030-01-02T10:00:00Z", "notify.yml", 2),
                _run("R", "Firmware", "failure", "2030-01-01T09:00:00Z", "firmware-build.yml", 1)]
        self.assertEqual(self.suggest(runs), [])

    def test_the_same_workflow_green_after_the_issue_does(self):
        runs = [_run("R", "Notify central ecosystem dashboard", "success", "2030-01-03T10:00:00Z", "notify.yml", 3),
                _run("R", "Firmware", "success", "2030-01-02T10:00:00Z", "firmware-build.yml", 2)]
        rows = self.suggest(runs)
        self.assertEqual([r["number"] for r in rows], [9])
        self.assertIn("2", rows[0]["reason"])            # the run it points to is the one of the firmware, not the dashboard

    def test_the_same_workflow_still_red_or_green_before_the_issue_does_not(self):
        self.assertEqual(self.suggest([_run("R", "Firmware", "failure", "2030-01-02T10:00:00Z", "firmware-build.yml", 2)]), [])
        self.assertEqual(self.suggest([_run("R", "Firmware", "success", "2029-12-30T10:00:00Z", "firmware-build.yml", 2)]), [])

    def test_an_issue_that_names_no_workflow_proposes_nothing(self):
        import surface
        issue = [dict(self.ISSUE[0], title="Something broke")]
        runs = {"R": [_run("R", "Build", "success", "2030-01-02T10:00:00Z", "build.yml", 2)]}
        self.assertEqual(surface.issue_close_suggestions(issue, runs, set(), {}, 1_900_000_000), [])
        self.assertTrue(surface.workflow_in_title({"name": "Build", "path": ""}, "Build failed: Build"))
        self.assertFalse(surface.workflow_in_title({"name": "CI", "path": ".github/workflows/ci.yml"}, "Decision made"))          # whole words only


class TagAgainstManifest(unittest.TestCase):
    def rows(self, tag, local="0.2.1", remote=None, repo_tag=None):
        import surface
        from test_surface import SurfaceInTheSnapshot
        data = SurfaceInTheSnapshot().inp()
        data["repo_info"]["R"]["release"]["tagName"] = tag
        data["scans"]["R"]["manifest"]["version"] = local
        data["scans"]["R"]["changelog_top"] = local
        if remote:
            data["repo_info"]["R"]["remote_manifest"] = {"tag": repo_tag or tag, "version": remote}
        return {s["key"]: s["rows"] for s in surface.build(data)["sections"]}["tag_vs_version"]

    def test_a_tag_ahead_of_an_old_reading_warns_and_the_manifest_of_the_branch_clears_it(self):
        self.assertTrue(self.rows("v0.2.2"))                                                      # the clone says 0.2.1
        self.assertEqual(self.rows("v0.2.2", remote="0.2.2"), [])                                # main already had 0.2.2
        self.assertTrue(self.rows("v0.2.3", remote="0.2.2"))                                      # still ahead: a real warning
        self.assertTrue(self.rows("v0.2.2", remote="0.2.2", repo_tag="v0.2.1"))                 # a reading made for an older release is not used

    def test_a_tag_that_is_not_a_version_says_nothing(self):
        import surface
        self.assertEqual(self.rows("meshes-1", local="0.2.1"), [])
        for good in ("v1.2", "0.8.0.1", "v2.0.0-rc1"):
            self.assertTrue(surface.is_version_tag(good), good)
        for bad in ("meshes-1", "nightly", "", None, "v1"):
            self.assertFalse(surface.is_version_tag(bad), bad)

    def test_the_branch_manifest_is_read_once_per_release_and_only_when_the_tag_is_ahead(self):
        import base64
        import surface
        calls = []

        def gh(*args, **kw):
            calls.append(args)
            return {"content": base64.b64encode(json.dumps({"version": "0.2.2"}).encode()).decode()}

        collector = surface.Collector(gh, tempfile.gettempdir(), surface.settings({}))
        collector.scans = {"R": {"manifest": {"file": "r.project.json", "version": "0.2.1"}}, "Q": {"manifest": {"file": "q.project.json", "version": "1.0.0"}}}
        collector.raw = {"R": {"release": {"tagName": "v0.2.2"}}, "Q": {"release": {"tagName": "v1.0.0"}}}
        self.assertEqual(collector.confirm_manifests(["R", "Q"], {}, 10), 1)
        self.assertEqual(collector.raw["R"]["remote_manifest"], {"tag": "v0.2.2", "version": "0.2.2"})
        self.assertIn("r.project.json", " ".join(calls[0]))
        self.assertEqual(collector.confirm_manifests(["R", "Q"], {}, 10), 0)                       # already read for this tag
        self.assertEqual(len(calls), 1)


class NextStepOfACandidate(unittest.TestCase):
    BASE = {"unreleased": {"ARMOR-NODE-X": 6}, "min_entries": 5, "releases": {"ARMOR-NODE-X": {"tagName": "v0.1.0"}}, "local_versions": {"ARMOR-NODE-X": "0.1.1"},
            "runs": {"ARMOR-NODE-X": [{"repo": "ARMOR-NODE-X", "id": 1, "name": "CI", "path": "ci.yml", "branch": "main", "status": "completed", "conclusion": "success",
                                       "started": "2030-01-01T10:00:00Z", "sha": "abc1234"}]}}

    def rows(self, eco_of=lambda repo: "armor", **extra):
        import readiness
        return readiness.release_rows({**self.BASE, "eco_of": eco_of, **extra})

    def test_bump_build_and_sign_sign_and_publish_are_told_apart(self):
        import readiness
        state = lambda st, **kw: [{"repo": "ARMOR-NODE-X", "workflow": "firmware-build.yml", "state": st, **kw}]  # noqa: E731
        self.assertEqual(self.rows(local_versions={"ARMOR-NODE-X": "0.1.0"})[0]["next"], "bump")
        self.assertEqual(self.rows(states=state("published"))[0]["next"], "build_sign")
        self.assertEqual(self.rows(states=state("built_on_gha"))[0]["next"], "sign")
        self.assertEqual(self.rows(states=state("signed_local", trusted=True))[0]["next"], "publish")
        self.assertTrue(readiness.needs_signature("firmware-build.yml"))
        self.assertFalse(readiness.needs_signature("apk-build.yml"))
        for lang in LANGS:
            self.assertNotEqual(i18n.tl(lang, "rd.n.build_sign"), "rd.n.build_sign", lang)

    def test_a_repository_handled_elsewhere_is_not_a_candidate(self):
        self.assertEqual(self.rows(eco_of=lambda repo: "eh3d"), [])
        self.assertEqual(len(self.rows()), 1)


if __name__ == "__main__":
    unittest.main()
