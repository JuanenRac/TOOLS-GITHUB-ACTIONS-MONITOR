# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.6, security: a proxy of the environment cannot turn the check of destinations around, the actions and the test endpoints are for this computer only, a plan of `act` is bound to the
content of its workflow, the macOS Keychain never gets the token on a command line, everything `gh` prints is cleaned, the list of refused addresses is bounded, a silence that could not be
saved is not reported as saved, and the command line never shows a traceback for an answer of the wrong shape. Offline, with fake servers on this computer."""
import io
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor  # noqa: E402
import actlocal  # noqa: E402
import ai_actions  # noqa: E402
import alert_center  # noqa: E402
import ghactions  # noqa: E402
import localguard  # noqa: E402
import monitor_cli  # noqa: E402
import netguard  # noqa: E402
import notifiers  # noqa: E402
import secretstore  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
PROXY_HITS = []


class FakeProxy(BaseHTTPRequestHandler):
    """A proxy that answers every request with a redirect to the metadata address of the cloud."""

    def do_GET(self):
        PROXY_HITS.append(self.path)
        self.send_response(302)
        self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
        self.end_headers()

    def log_message(self, *args):
        pass


def public_resolver(host, port, type=0):      # noqa: A002 - the signature of socket.getaddrinfo
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34" if host == "public.example" else "10.0.0.5", port))]


class ProxyOfTheEnvironment(unittest.TestCase):
    def setUp(self):
        PROXY_HITS.clear()
        self.proxy = HTTPServer(("127.0.0.1", 0), FakeProxy)
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()
        self.addCleanup(self.proxy.server_close)
        self.addCleanup(self.proxy.shutdown)
        url = f"http://127.0.0.1:{self.proxy.server_address[1]}"
        env = mock.patch.dict(os.environ, {"http_proxy": url, "HTTP_PROXY": url, "https_proxy": url, "HTTPS_PROXY": url})
        env.start()
        self.addCleanup(env.stop)
        for name in ("no_proxy", "NO_PROXY"):
            os.environ.pop(name, None)

    def test_by_default_the_proxy_of_the_environment_is_not_used(self):
        seen = []

        def fake_connect(address, *a, **k):
            seen.append(address)
            raise OSError("no network in the test")
        with mock.patch("socket.create_connection", fake_connect), self.assertRaises(OSError):
            netguard.open_url(urllib.request.Request("http://public.example/x"), 2, False, public_resolver)
        self.assertEqual(seen, [("93.184.216.34", 80)], "the connection goes to the destination that was checked, not to the proxy")
        self.assertEqual(PROXY_HITS, [])

    def test_with_the_switch_a_redirect_to_the_metadata_address_is_refused(self):
        with self.assertRaises(OSError) as raised:
            netguard.open_url(urllib.request.Request("http://public.example/x"), 3, False, public_resolver, use_proxy=True)
        self.assertEqual(netguard.reason_of(raised.exception), "private_target")
        self.assertEqual(len(PROXY_HITS), 1, "the proxy saw the first request only: the redirect was refused before it was followed")

    def test_with_the_switch_a_private_destination_is_refused_before_the_proxy_hears_of_it(self):
        with self.assertRaises(OSError) as raised:
            netguard.open_url(urllib.request.Request("http://private.example/x"), 3, False, public_resolver, use_proxy=True)
        self.assertEqual(netguard.reason_of(raised.exception), "private_target")
        self.assertEqual(PROXY_HITS, [])

    def test_the_setting_reaches_the_notifier_and_is_off_by_default(self):
        self.assertFalse(notifiers.settings({})["use_proxy"])
        self.assertTrue(notifiers.settings({"network": {"use_proxy": True}})["use_proxy"])
        self.assertFalse(notifiers.settings({"network": {"use_proxy": "yes"}})["use_proxy"])
        self.assertFalse(actions_monitor.DEFAULTS["network"]["use_proxy"])
        import settings_api
        self.assertIn("network.use_proxy", settings_api.META)


class LocalOnlyEndpoints(unittest.TestCase):
    def post(self, base, path):
        request = urllib.request.Request(base + path, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as answer:
                return answer.status, json.loads(answer.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def test_the_action_and_test_endpoints_are_for_this_computer_in_the_network_mode(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        paths = ("/api/ai/actions/confirm", "/api/ai/actions/unlock", "/api/ai/test", "/api/notify/test")
        with mock.patch.dict(localguard.STATE, {"network": True}), mock.patch.object(localguard, "access_ok", return_value=True), \
                mock.patch.object(localguard, "from_this_computer", return_value=False), mock.patch.object(actions_monitor, "token_required", return_value=False):
            for path in paths:
                code, body = self.post(base, path)
                self.assertEqual((code, body.get("errors", {}).get("_")), (403, "local_only"), path)
        with mock.patch.dict(localguard.STATE, {"network": True}), mock.patch.object(localguard, "access_ok", return_value=True), \
                mock.patch.object(localguard, "from_this_computer", return_value=True), mock.patch.object(actions_monitor, "token_required", return_value=False):
            for path in paths:
                code, body = self.post(base, path)
                self.assertNotEqual(body.get("errors", {}).get("_") if isinstance(body.get("errors"), dict) else None, "local_only", path)


class NetworkClientsWriteOnlyAShortList(LocalOnlyEndpoints):
    def test_only_the_allow_list_can_be_written_from_another_computer(self):
        import settings_api
        for key in settings_api.META:
            if key in localguard.REMOTE_WRITABLE:
                self.assertFalse(localguard.local_only_key(key), key)
            else:
                self.assertTrue(localguard.local_only_key(key), key)
        for key in ("notify.channels.matrix.homeserver", "notify.channels.matrix.token_env", "dispatch.required_ci", "tools_dir", "targets_file", "signed_dir", "sentinel.ci_red_file",
                    "ai_alerts.folder", "ai.api_key_env", "workspace_root", "audit_dir"):
            self.assertTrue(localguard.local_only_key(key), key)
        self.assertTrue(localguard.local_only_key("a.key.that.does.not.exist.yet"), "a new setting is local-only until it is listed on purpose")
        self.assertFalse(localguard.REMOTE_WRITABLE - set(settings_api.META), "every listed key exists")

    def test_a_remote_client_cannot_point_a_channel_at_a_secret_or_rewrite_the_trusted_files(self):
        import settings_api
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        attacks = [{"notify.channels.matrix.enabled": True, "notify.channels.matrix.homeserver": "https://evil.example", "notify.channels.matrix.room": "!x:evil.example",
                    "notify.channels.matrix.token_env": "GH_TOKEN"},
                   {"dispatch.required_ci": ["docs.yml"], "tools_dir": "/tmp/other", "targets_file": "/tmp/other.json", "signed_dir": "/tmp/x", "ai_alerts.folder": "/tmp/y", "ai.api_key_env": "GH_TOKEN"}]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(settings_api, "CONFIG_FILE", Path(tmp) / "c.json"), mock.patch.object(settings_api, "BACKUP_DIR", Path(tmp) / "b"),                 mock.patch.dict(localguard.STATE, {"network": True}), mock.patch.object(localguard, "access_ok", return_value=True),                 mock.patch.object(localguard, "from_this_computer", return_value=False), mock.patch.object(actions_monitor, "token_required", return_value=False):
            for changes in attacks:
                request = urllib.request.Request(base + "/api/settings", data=json.dumps({"changes": changes}).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(urllib.error.HTTPError) as refused:
                    urllib.request.urlopen(request, timeout=10)
                self.assertEqual(refused.exception.code, 403)
            self.assertFalse((Path(tmp) / "c.json").exists(), "nothing was written")


class ActPlanIsBoundToItsWorkflow(unittest.TestCase):
    CONFIG = {"act": {"enabled": True, "allowed": ["my-repo:ci.yml:push"], "timeout_seconds": 60}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "ws"
        self.flow = self.root / "my-repo" / ".github" / "workflows" / "ci.yml"
        self.flow.parent.mkdir(parents=True)
        self.flow.write_text("on: push\njobs: {}\n", encoding="utf-8")
        snap = mock.patch.object(actlocal, "docker_snapshot", lambda: None)
        snap.start()
        self.addCleanup(snap.stop)
        actlocal.RUN.update({"proc": None, "lines": [], "bytes": 0, "running": False, "exit": None, "plan": None, "stopping": False})

    def make(self):
        item, why = actlocal.plan(self.CONFIG, str(self.root), "my-repo", "ci.yml", "push", None, which=lambda name: "/usr/bin/act")
        self.assertEqual(why, "ok")
        return item

    def test_the_plan_keeps_the_path_and_the_hash(self):
        item = self.make()
        self.assertEqual(len(item["workflow_sha256"]), 64)
        self.assertEqual(Path(item["workflow_path"]), self.flow.resolve())

    def test_a_workflow_edited_after_the_plan_does_not_run(self):
        item = self.make()
        self.flow.write_text("on: push\njobs:\n  x:\n    runs-on: self-hosted\n    steps: [{run: evil}]\n", encoding="utf-8")
        popen = mock.Mock()
        answer = actlocal.start(self.CONFIG, item["id"], popen=popen, threaded=False)
        self.assertEqual(answer, {"ok": False, "status": "workflow_changed"})
        popen.assert_not_called()
        self.assertFalse(actlocal.RUN["running"])

    def test_a_workflow_that_disappeared_does_not_run_and_an_unchanged_one_does(self):
        gone = self.make()
        self.flow.unlink()
        popen = mock.Mock()
        self.assertEqual(actlocal.start(self.CONFIG, gone["id"], popen=popen, threaded=False)["status"], "workflow_changed")
        popen.assert_not_called()
        self.flow.write_text("on: push\n", encoding="utf-8")
        fine = self.make()
        popen = mock.Mock(side_effect=OSError("stop here"))
        self.assertTrue(actlocal.start(self.CONFIG, fine["id"], popen=popen, threaded=False)["ok"])
        popen.assert_called_once()

    def test_the_page_has_a_text_for_it_in_each_language(self):
        for lang in LANGS:
            cat = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(cat.get("ui.adv_why_workflow_changed"), lang)


class KeychainWithoutArgv(unittest.TestCase):
    TOKEN = "ghp_" + "A1b2C3d4" * 5

    def test_the_token_goes_through_standard_input_not_the_argument_list(self):
        calls = []

        def runner(args, data):
            calls.append((list(args), data))
            return mock.Mock(returncode=0, stdout="")
        store = secretstore.Store("auto", runner=runner, platform="darwin")
        with mock.patch.object(secretstore.shutil, "which", return_value="/usr/bin/security"):
            ok, kind = store.save(self.TOKEN)
        self.assertEqual((ok, kind), (True, "keychain"))
        args, data = calls[0]
        self.assertEqual(args, ["security", "-i"])
        self.assertNotIn(self.TOKEN, " ".join(args))
        self.assertIn(self.TOKEN, data)
        self.assertIn("add-generic-password", data)

    def test_a_failure_does_not_repeat_the_token(self):
        store = secretstore.Store("auto", runner=lambda a, d: mock.Mock(returncode=1, stdout="boom"), platform="darwin")
        with mock.patch.object(secretstore.shutil, "which", return_value="/usr/bin/security"):
            ok, why = store.save(self.TOKEN)
        self.assertEqual((ok, why), (False, "keychain"))
        self.assertNotIn(self.TOKEN, why)


class EverythingGhPrintsIsCleaned(unittest.TestCase):
    FORMATS = {"classic": "ghp_" + "a" * 36, "oauth": "gho_" + "b" * 36, "fine-grained": "github_pat_" + "C" * 40 + "_" + "d" * 20, "old 40 hex": "0123456789abcdef" * 2 + "01234567"}

    def test_redact_covers_every_format_and_the_known_token(self):
        for name, token in self.FORMATS.items():
            cleaned = secretstore.redact(f"error: bad credentials {token} for you", None)
            self.assertNotIn(token, cleaned, name)
            self.assertIn("***", cleaned, name)
        self.assertNotIn("an-odd-token", secretstore.redact("x an-odd-token y", "an-odd-token"))
        self.assertEqual(secretstore.redact("a commit abc123"), "a commit abc123", "a short hash is not a token")

    def test_the_log_of_an_ai_action_never_keeps_a_token(self):
        for name, token in self.FORMATS.items():
            with tempfile.TemporaryDirectory() as tmp:
                actions = ai_actions.Actions(log_file=Path(tmp) / "log.jsonl")
                config = {"ai": {"actions": {"enabled": True, "execute": True, "allowed": ["rerun_failed"]}}}
                argv = ["gh", "run", "rerun", "1"]
                actions.pending["p1"] = {"at": actions.clock(), "ttl": 600, "command": "gh run rerun 1", "argv": argv, "action": "rerun_failed", "repo": "r"}
                with mock.patch.object(ai_actions, "RUNNABLE", ("rerun_failed",)), mock.patch.object(ai_actions, "settings", return_value={"enabled": True, "execute": True, "allowed": ["rerun_failed"], "max_per_hour": 9}):
                    result = actions.run("p1", "gh run rerun 1", config, runner=lambda a, **k: mock.Mock(returncode=1, stdout=f"HTTP 401 {token}", stderr=""))
                self.assertFalse(result["ok"], name)
                self.assertNotIn(token, (Path(tmp) / "log.jsonl").read_text(encoding="utf-8"), name)

    def test_a_refused_github_action_does_not_keep_the_token_either(self):
        token = self.FORMATS["old 40 hex"]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "g.jsonl"
            config = {"github_actions": {"enabled": True}}
            with mock.patch.object(ghactions, "settings", return_value={"enabled": True}), mock.patch.object(ghactions, "scopes", return_value=["repo"]), \
                    mock.patch.object(ghactions, "permission", return_value=True):
                plan_id = ghactions.PENDING.add("ghaction", {"method": "POST", "endpoint": "repos/o/r/actions/runs/1/rerun", "fields": {}, "scope": "repo"})
                result = ghactions.execute(config, plan_id, lambda args, timeout=40: (1, "", f"HTTP 403 {token}"), log_file=log)
            self.assertNotIn(token, json.dumps(result))
            self.assertNotIn(token, log.read_text(encoding="utf-8") if log.exists() else "")


class RefusedAddressesAreBounded(unittest.TestCase):
    def setUp(self):
        localguard.reset_limits()
        self.addCleanup(localguard.reset_limits)

    def test_a_lock_that_ended_is_purged_by_the_next_lock_of_any_address(self):
        for i in range(50):
            localguard._locked[f"10.0.0.{i}"] = 100.0       # all of them ended long ago
        self.assertTrue(localguard.note_failure("9.9.9.9", 1, now=1000.0))
        self.assertEqual(list(localguard._locked), ["9.9.9.9"])

    def test_the_list_never_grows_over_its_limit(self):
        with mock.patch.object(localguard, "MAX_LOCKED", 20):
            for i in range(200):
                localguard.note_failure(f"8.8.{i // 250}.{i % 250}", 1, now=1000.0 + i)
            self.assertLessEqual(len(localguard._locked), 20)
            self.assertTrue(localguard.is_locked("8.8.0.199", now=1200.0), "the newest locks stay")
            self.assertFalse(localguard.is_locked("8.8.0.0", now=1200.0), "the oldest went")


class SilenceThatCouldNotBeSaved(unittest.TestCase):
    def test_the_answer_is_not_ok_when_the_file_cannot_be_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "mutes.json"
            with mock.patch.object(alert_center, "STATE_FILE", target):
                self.assertIsNotNone(alert_center.mute("alert", "a1", 1, now=1_800_000_000))
                with mock.patch.object(alert_center.os, "replace", side_effect=OSError("disk full")):
                    self.assertIsNone(alert_center.mute("alert", "a2", 1, now=1_800_000_000))
                    self.assertFalse(alert_center.unmute("alert", "a1"))
                self.assertEqual([e["value"] for e in alert_center.active(1_800_000_000)], ["a1"], "nothing half-written")
                with mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={}), mock.patch.object(alert_center.os, "replace", side_effect=OSError("disk full")):
                    answer = actions_monitor.handle_advanced_post("/api/alerts/mute", {"scope": "alert", "value": "a3"})
                self.assertFalse(answer["ok"])


class RealRedirectIsFollowedAndJudged(unittest.TestCase):
    """The first hop is served (a public name that resolves to a harmless address), the redirect to the 'metadata' name is refused before anything reaches it."""

    def test_first_hop_served_then_redirect_to_a_blocked_address_is_refused(self):
        hits = []

        class Jump(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                if self.path == "/jump":
                    self.send_response(302)
                    self.send_header("Location", f"http://meta.example:{self.server.server_address[1]}/latest/meta-data")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Length", "2")
                    self.end_headers()
                    self.wfile.write(b"ok")

            def log_message(self, *args):
                pass
        server = HTTPServer(("0.0.0.0", 0), Jump)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def resolver(host, port, type=0):      # noqa: A002
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ({"public.example": "127.0.0.1", "meta.example": "127.0.0.2"}[host], port))]
        with mock.patch.object(netguard, "blocked_ip", lambda value: str(value) != "127.0.0.1"):
            with self.assertRaises(urllib.error.URLError) as caught:
                netguard.open_url(urllib.request.Request(f"http://public.example:{server.server_address[1]}/jump"), resolver=resolver)
        self.assertEqual(netguard.reason_of(caught.exception), "private_target")
        self.assertEqual(hits, ["/jump"], "the first hop is served; the target of the redirect never receives the request")


class DispatchAndSigning(unittest.TestCase):
    SHA, OTHER = "a" * 40, "b" * 40

    def fire(self, listings):
        """`listings` = what each call to `gh run list` answers, in order (the first one is the list BEFORE the dispatch)."""
        import gha_dispatch_all as gd
        name = next(n for n in gd.TARGETS if ":" not in n)
        calls = []
        answers = iter(listings)
        last = [listings[-1]]

        def ghj(*args):
            return next(answers, last[0])
        with mock.patch.object(gd, "gh", side_effect=lambda *a: calls.append(a) or ""), mock.patch.object(gd, "ghj", side_effect=ghj), mock.patch.object(gd.time, "sleep"), mock.patch("builtins.print"):
            return gd.fire(name, name, self.SHA, False), calls

    @staticmethod
    def made(ident, sha):
        return {"databaseId": ident, "createdAt": "2000-01-01T00:00:00Z", "headSha": sha, "event": "workflow_dispatch"}

    def test_a_new_run_on_the_checked_commit_is_matched(self):
        result, calls = self.fire([[], [self.made(7, self.SHA)]])
        self.assertEqual((result["run"], result["sha_matched"]), (7, True))
        self.assertIn("ref=" + self.SHA, calls[0], "the dispatch builds exactly the commit that was checked")

    def test_a_new_run_on_another_commit_is_not_matched(self):
        result, _ = self.fire([[], [self.made(8, self.OTHER)]])
        self.assertEqual((result["run"], result["sha_matched"]), (8, False))

    def test_a_run_that_already_existed_is_never_taken_for_the_new_one(self):
        old = self.made(5, self.SHA)      # a dispatch of another batch on the same commit, a few seconds earlier
        result, _ = self.fire([[old], [old]])
        self.assertIsNone(result["run"])
        self.assertFalse(result["sha_matched"])

    def test_two_new_candidates_cannot_be_told_apart_and_need_review(self):
        result, _ = self.fire([[], [self.made(9, self.SHA), self.made(10, self.SHA)]])
        self.assertFalse(result["sha_matched"], "which of the two is ours cannot be known: it is not offered for signing")

    def test_a_required_workflow_is_a_file_not_a_visible_name(self):
        import gha_dispatch_all as gd
        ok = {"status": "completed", "conclusion": "success"}
        runs = [{"id": 1, "path": ".github/workflows/zzz.yml", "name": "ci.yml", **ok}]
        with mock.patch.object(gd, "ghj", return_value={"total_count": 1, "workflow_runs": runs}):
            green, bad, _pending = gd.ci_green("REPO", "a" * 40, required=["ci.yml"])
        self.assertFalse(green, bad)
        runs = [{"id": 1, "path": ".github/workflows/ci.yml", "name": "Anything", **ok}]
        with mock.patch.object(gd, "ghj", return_value={"total_count": 1, "workflow_runs": runs}):
            self.assertTrue(gd.ci_green("REPO", "a" * 40, required=["ci.yml"])[0])

    def test_the_name_of_a_batch_is_in_utc(self):
        source = (HERE / "gha_dispatch_all.py").read_text(encoding="utf-8")
        self.assertIn("datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')", source)
        self.assertNotIn("datetime.now().strftime", source)


class RedactorCoversTheFormats(unittest.TestCase):
    SAMPLES = {
        "gh classic": ("ghp_" + "a1B2" * 9, "a1B2a1B2"), "gh fine-grained": ("github_pat_" + "A1b2_" * 12, "A1b2_A1b2_"), "gh app": ("ghs_" + "Z9" * 18, "Z9Z9Z9Z9"),
        "telegram": ("https://api.telegram.org/" + "bot123456789:" + "AAH" + "x1Y2z3" * 5 + "ab/sendMessage", "x1Y2z3x1Y2z3"),
        "slack webhook": ("https://hooks." + "slack.com/services/" + "T01ABCDEF/B01ABCDEF/" + "abcdefghijklm" + "nopqrstuvwx", "abcdefghijklmnopqrstuvwx"),
        "discord webhook": ("https://discord.com/api/" + "webhooks/" + "123456789012345678/" + "aB3_" * 17, "aB3_aB3_aB3_"), "url credentials": ("https://deploy:Sup3rS3cret!@git.example.org/repo.git", "Sup3rS3cret"),
        "gitlab": ("glpat-" + "aB3d" * 5, "aB3daB3d"), "npm": ("npm_" + "aB3d" * 9, "aB3daB3d"), "pypi": ("pypi-AgEIcHlwaS5vcmc" + "aB3d" * 10, "aB3daB3daB3d"),
        "sk": ("sk-ant-api03-" + "aB3d" * 10, "aB3daB3d"), "aws secret": ("wJalrXUtnFEMI/K7MDENG/bPxRfiCY" + "EXAMPLEKEY", "bPxRfiCYEXAMPLEKEY"),
        "pem": ("-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ\n-----END OPENSSH PRIVATE KEY-----", "b3BlbnNzaC1rZXktdjEAAAAABG5vbmU"),
        "DB_PASSWORD": ("DB_PASSWORD=hunter2hunter2", "hunter2"), "MYSQL_PWD": ("MYSQL_PWD=hunter2hunter2", "hunter2"), "AWS_SECRET_ACCESS_KEY": ("AWS_SECRET_ACCESS_KEY=abcd1234wxyz", "abcd1234wxyz"),
        "API_TOKEN": ("API_TOKEN: zzzz9999yyyy", "zzzz9999yyyy"), "bearer": ("Authorization: Bearer abcdefghijkl", "abcdefghijkl"),
        "x-monitor-access": ("X-Monitor-Access: TTTTTTTTTTTTTTTTTTTTTTTT", "TTTTTTTT"), "cookie": ("Cookie: monitor_access=TTTTTTTTTTTTTTTTTTTTTTTT", "TTTTTTTT"),
        "hex 32": ("api secret 0123456789abcdef0123456789abcdef", "0123456789abcdef0123456789abcdef"), "e-mail": ("write to dev@example.com", "dev@example.com"),
    }

    def test_no_sample_leaks(self):
        import ai_alerts
        for name, (text, secret) in self.SAMPLES.items():
            cleaned = ai_alerts.redact(text)
            self.assertNotIn(secret, cleaned, name)
            self.assertNotEqual(cleaned, text, name)

    def test_ordinary_text_is_left_alone(self):
        import ai_alerts
        self.assertEqual(ai_alerts.redact("Error: step Run tests failed with exit code 1"), "Error: step Run tests failed with exit code 1")


class McpOnlyForWatchedRepositories(unittest.TestCase):
    def test_a_repository_that_is_not_watched_is_refused_and_gh_is_not_called(self):
        import mcp_server
        calls = []

        def runner(args, timeout=60):
            calls.append(args)
            return 0, '{"jobs": []}', ""
        config = {"github_owner": "JuanenRac", "repos": ["URTC"], "ai": {"allowed_repos": ["URTC"]}, "ai_alerts": {"enabled": False}}
        answer = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_run_failure", "arguments": {"repo": "PRIVATE-NOT-WATCHED", "run": 5}}}, config, runner=runner)
        self.assertTrue(answer["result"].get("isError"))
        self.assertEqual(calls, [])
        ok = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_run_failure", "arguments": {"repo": "URTC", "run": 5}}}, config, runner=runner)
        self.assertFalse(ok["result"].get("isError"))
        listed = {"github_owner": "JuanenRac", "repos": ["URTC"]}
        self.assertFalse(mcp_server.watched(listed, "OTHER"))
        self.assertTrue(mcp_server.watched(listed, "URTC"))


class BehindAProxyOnThisMachine(unittest.TestCase):
    def test_a_forwarded_request_or_the_public_name_is_never_this_computer(self):
        peer = ("127.0.0.1", 5000)
        self.assertTrue(localguard.is_this_computer(peer, {}))
        for header in ("Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Real-IP"):
            self.assertFalse(localguard.is_this_computer(peer, {header: "203.0.113.9"}), header)
        with mock.patch.dict(localguard.STATE, {"proxy_host": "monitor.example"}):
            self.assertFalse(localguard.is_this_computer(peer, {"Host": "monitor.example"}))
            self.assertTrue(localguard.is_this_computer(peer, {"Host": "127.0.0.1:8765"}))
        self.assertFalse(localguard.is_this_computer(("10.0.0.2", 1), {}))

    def test_the_right_token_gets_in_even_when_the_address_is_locked(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        token = "T" * 24
        localguard.reset_limits()
        self.addCleanup(localguard.reset_limits)
        with mock.patch.dict(localguard.STATE, {"network": True, "token": token, "allowed": set(), "host": "127.0.0.1"}):
            for _ in range(12):
                request = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/health", headers={"X-Monitor-Access": "wrong"})
                try:
                    urllib.request.urlopen(request, timeout=10)
                except urllib.error.HTTPError:
                    pass
            self.assertTrue(localguard.is_locked("127.0.0.1"))
            good = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/health", headers={"X-Monitor-Access": token})
            with urllib.request.urlopen(good, timeout=10) as answer:
                self.assertEqual(answer.status, 200)


class LoopbackNeverUsesAProxy(unittest.TestCase):
    def test_a_call_to_this_computer_ignores_the_proxy_variables(self):
        class Plain(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Plain)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with mock.patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9"}):
            os.environ.pop("no_proxy", None)
            os.environ.pop("NO_PROXY", None)
            with netguard.local_open(f"http://127.0.0.1:{server.server_address[1]}/", timeout=5) as answer:
                self.assertEqual(answer.read(), b"ok")

    def test_no_module_opens_a_loopback_address_with_plain_urlopen(self):
        for name in ("monitor_cli", "accounts_supervisor", "mcp_server", "monitor_link", "read_report", "tui", "tui_textual", "ai_alerts", "notifiers"):
            self.assertNotIn("urllib.request.urlopen", (HERE / f"{name}.py").read_text(encoding="utf-8"), name)


class HeadersAndHost(unittest.TestCase):
    def test_every_answer_forbids_framing_and_the_page_checks_the_host(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        with mock.patch.dict(localguard.STATE, {"network": False}):
            for path in ("/", "/api/health"):
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as answer:
                    self.assertEqual(answer.headers["X-Frame-Options"], "DENY", path)
                    self.assertIn("frame-ancestors 'none'", answer.headers["Content-Security-Policy"], path)
                    self.assertEqual(answer.headers["X-Content-Type-Options"], "nosniff", path)
            rebinding = urllib.request.Request(f"http://127.0.0.1:{port}/", headers={"Host": "rebind.attacker.example:8765"})
            with self.assertRaises(urllib.error.HTTPError) as refused:
                urllib.request.urlopen(rebinding, timeout=10)
            self.assertEqual(refused.exception.code, 403)

    def test_the_old_address_with_the_token_says_deprecated_on_every_answer(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        token = "T" * 24
        with mock.patch.dict(localguard.STATE, {"network": True, "token": token, "allowed": set(), "host": "127.0.0.1"}), mock.patch.object(localguard, "query_token_counts", return_value=True):
            request = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/health?access={token}", headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=10) as answer:
                self.assertEqual(answer.headers["Deprecation"], "true")
            clean = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/health", headers={"X-Monitor-Access": token})
            with urllib.request.urlopen(clean, timeout=10) as answer:
                self.assertIsNone(answer.headers["Deprecation"])


class FilesWithTheWrongShape(unittest.TestCase):
    def test_a_silence_file_edited_by_hand_loses_only_the_bad_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "mutes.json"
            good = {"scope": "alert", "value": "a1", "until": "2999-01-01T00:00:00Z", "until_ts": 32503680000}
            target.write_text(json.dumps({"active": [good, "x", 7, {"scope": "nope", "value": "a"}, {"scope": "alert", "value": 5, "until_ts": "z"}, {"scope": "alert", "value": "b", "until_ts": True, "until": "x"}],
                                          "history": [1, {"value": "h"}, None]}), encoding="utf-8")
            with mock.patch.object(alert_center, "STATE_FILE", target):
                self.assertEqual(alert_center.active(1_800_000_000), [good])
                self.assertEqual([h["value"] for h in alert_center.history()], ["h"])

    def test_an_update_state_with_fields_of_the_wrong_type_is_ignored(self):
        import updatecheck
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "u.json"
            for body in ('[]', '{"release": "x", "checked_at": "now"}', '{"release": {"tag": 5, "url": []}, "checked_at": true}'):
                path.write_text(body, encoding="utf-8")
                state = updatecheck._load(path)
                view = updatecheck.view({}, "1.7.6", state)
                self.assertEqual(view["latest"], "")
                self.assertIsInstance(view["checked_at"], (int, float))


class TimeZones(unittest.TestCase):
    def test_cairo_follows_the_daylight_saving_time_it_has_since_2023(self):
        import tzdisplay
        from datetime import datetime, timezone

        def hours(text):
            return tzdisplay.at(datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc), "Africa/Cairo").utcoffset().total_seconds() / 3600
        with mock.patch.object(tzdisplay, "_zoneinfo", lambda name: None):
            self.assertEqual([hours("2024-04-25T12:00:00Z"), hours("2024-04-26T12:00:00Z"), hours("2024-10-30T12:00:00Z"), hours("2024-10-31T22:30:00Z"), hours("2022-07-01T12:00:00Z")], [2, 3, 3, 2, 2])

    def test_a_zone_the_system_does_not_know_is_refused_in_the_settings(self):
        import settings_api
        import tzdisplay
        with mock.patch.object(tzdisplay, "_zoneinfo", lambda name: None):
            self.assertFalse(settings_api.check_value("display.timezone", "Europe/Madird")[0])
            self.assertTrue(settings_api.check_value("display.timezone", "Europe/Madrid")[0])
            self.assertTrue(settings_api.check_value("display.timezone", "utc")[0])


class CommandLineStatusAndRedirects(unittest.TestCase):
    def test_status_without_data_is_degraded_like_health_and_wrong_types_are_unreadable(self):
        for answers, expected in (({"/api/health": {"version": "1"}, "/api/data": {"data": None}}, monitor_cli.EXIT_DEGRADED),
                                  ({"/api/health": {}, "/api/data": {"data": {"figures": 3}}}, None), ({"/api/health": {}, "/api/data": {"data": {"updated": {"x": 1}}}}, None),
                                  ({"/api/health": {}, "/api/data": {"data": {"repos": 7}}}, None)):
            with mock.patch.object(monitor_cli, "fetch", lambda base, path, *a, **k: answers[path]):
                ctx = {"base": "", "account": "", "timeout": 1, "token": ""}
                if expected is not None:
                    self.assertEqual(monitor_cli.cmd_status(ctx)[2], expected)
                else:
                    with self.assertRaises((ValueError, AttributeError, TypeError)):
                        monitor_cli.cmd_status(ctx)

    def test_the_access_token_does_not_follow_a_redirect_to_another_origin(self):
        seen = []

        class Redirecting(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append((self.server.server_address[1], self.headers.get("X-Monitor-Access")))
                if self.server.target:
                    self.send_response(302)
                    self.send_header("Location", f"http://127.0.0.1:{self.server.target}/stolen")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Length", "2")
                    self.end_headers()
                    self.wfile.write(b"{}")

            def log_message(self, *args):
                pass
        other = HTTPServer(("127.0.0.1", 0), Redirecting)
        other.target = None
        first = HTTPServer(("127.0.0.1", 0), Redirecting)
        first.target = other.server_address[1]
        for server in (other, first):
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        with self.assertRaises(monitor_cli.CliError) as raised:
            monitor_cli.fetch(f"http://127.0.0.1:{first.server_address[1]}", "/api/health", None, 5, "SECRET-TOKEN")
        self.assertEqual(raised.exception.code, monitor_cli.EXIT_DEGRADED)
        self.assertEqual([s for s in seen if s[0] == other.server_address[1]], [], "the second address never received the request")


class HeaderFigureOfTheCompleteEdition(unittest.TestCase):
    def test_the_complete_edition_reports_the_red_workflows_too(self):
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('red = red_rows({"runs": runs, "repos": repos})', source)


class FakeMonitor(BaseHTTPRequestHandler):
    BODY = b"[]"

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.BODY)

    def log_message(self, *args):
        pass


class CommandLineAnswersOfTheWrongShape(unittest.TestCase):
    def run_cli(self, body, *argv):
        FakeMonitor.BODY = body
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeMonitor)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = monitor_cli.main([*argv, "--url", f"http://127.0.0.1:{server.server_address[1]}", "--lang", "en", "--timeout", "3"])
            return code, out.getvalue(), err.getvalue()
        finally:
            server.shutdown()
            server.server_close()

    def test_a_list_null_or_number_is_degraded_never_a_traceback(self):
        for body in (b"[]", b"null", b"42", b'"text"'):
            for command in ("status", "accounts", "alerts", "live", "health"):
                code, out, err = self.run_cli(body, command)
                self.assertEqual(code, monitor_cli.EXIT_DEGRADED, (body, command, err))
                self.assertNotIn("Traceback", out + err)

    def test_a_field_of_the_wrong_type_inside_an_object_is_degraded_too(self):
        for body in (b'{"data": [], "version": 1}', b'{"data": 42}', b'{"accounts": 42, "alerts": "x", "events": 7}', b'{"data": {"figures": [], "rate": 5, "repos": 3}}'):
            for command in ("status", "accounts", "alerts", "live"):
                code, out, err = self.run_cli(body, command)
                self.assertNotIn("Traceback", out + err, (body, command))
                self.assertIn(code, (monitor_cli.EXIT_OK, monitor_cli.EXIT_DEGRADED, monitor_cli.EXIT_AUTH), (body, command, code))
        code, out, _err = self.run_cli(b'{"data": 42}', "status", "--json")
        self.assertEqual(json.loads(out)["exit"], monitor_cli.EXIT_DEGRADED)

    def test_the_message_exists_in_each_language(self):
        for lang in LANGS:
            cat = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(cat.get("cli.bad_shape"), lang)


if __name__ == "__main__":
    unittest.main()
