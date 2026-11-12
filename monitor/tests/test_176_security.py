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
