# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.5, local side: `act` stays inside the workspace and ends as a whole tree, the network mode, the webhook, the MCP server, the notification limit, the settings lock,
the token that only the `gh` process gets, a GET that never writes, the doctor warnings and the other regressions of the release."""
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import actlocal  # noqa: E402
import ai_alerts  # noqa: E402
import demo_mode  # noqa: E402
import doctor  # noqa: E402
import etagcache  # noqa: E402
import export_status  # noqa: E402
import helpdocs  # noqa: E402
import localguard  # noqa: E402
import make_release as mr  # noqa: E402
import mcp_server  # noqa: E402
import notifiers  # noqa: E402
import secretstore  # noqa: E402
import settings_api  # noqa: E402
import updatecheck  # noqa: E402
import webhook  # noqa: E402
from test_164 import LiveServer  # noqa: E402


# --- act: the workspace is a wall ---------------------------------------------------------------------------------------------------------------------------------------------------------
class ActInsideTheWorkspace(unittest.TestCase):
    CONFIG = {"act": {"enabled": True, "allowed": ["my-repo:ci.yml:push", "..:ci.yml:push"], "timeout_seconds": 60}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "workspace"
        self.root.mkdir()
        self.outside = Path(self.tmp.name) / "elsewhere"
        (self.outside / ".github" / "workflows").mkdir(parents=True)
        (self.outside / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, config=None, repo="my-repo"):
        return actlocal.plan(config or self.CONFIG, str(self.root), repo, "ci.yml", "push", None, which=lambda name: "/usr/bin/act")

    def link(self):
        try:
            os.symlink(self.outside, self.root / "my-repo", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available here")

    def test_a_clone_that_is_a_link_to_another_folder_is_refused(self):
        self.link()
        item, why = self.plan()
        self.assertEqual((item, why), (None, "symlink"))

    def test_the_link_can_be_allowed_on_purpose(self):
        self.link()
        item, why = self.plan({"act": {**self.CONFIG["act"], "allow_symlinks": True}})
        self.assertEqual(why, "ok")
        self.assertIn(str(self.outside.resolve()), item["command"])

    def test_a_parent_folder_name_is_not_a_clone(self):
        (self.root.parent / ".github" / "workflows").mkdir(parents=True)
        (self.root.parent / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
        self.assertEqual(self.plan(repo="..")[1], "no_clone")

    def test_a_workflows_folder_that_points_outside_the_clone_is_refused(self):
        clone = self.root / "my-repo"
        (clone / ".github").mkdir(parents=True)
        try:
            os.symlink(self.outside / ".github" / "workflows", clone / ".github" / "workflows", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available here")
        self.assertEqual(self.plan()[1], "outside")

    def test_a_normal_clone_with_a_space_in_the_path_works_and_the_path_is_resolved(self):
        spaced = self.root.parent / "my workspace"
        (spaced / "my-repo" / ".github" / "workflows").mkdir(parents=True)
        (spaced / "my-repo" / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
        item, why = actlocal.plan(self.CONFIG, str(spaced), "my-repo", "ci.yml", "push", None, which=lambda name: "/usr/bin/act")
        self.assertEqual(why, "ok")
        self.assertEqual(item["argv"][item["argv"].index("-C") + 1], str((spaced / "my-repo").resolve()))
        self.assertIsInstance(item["argv"], list)


# --- act: the whole tree ends ---------------------------------------------------------------------------------------------------------------------------------------------------------
CHILD = ("import subprocess, sys, time\n"
         "beat = sys.argv[1]\n"
         "grand = 'import time, pathlib, sys\\np = pathlib.Path(sys.argv[1])\\nfor _ in range(600):\\n    p.write_text(str(time.time()))\\n    time.sleep(0.1)\\n'\n"
         "subprocess.Popen([sys.executable, '-c', grand, beat])\n"
         "print('started', flush=True)\n"
         "time.sleep(120)\n")


class ActEndsAsATree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.beat = Path(self.tmp.name) / "beat.txt"
        actlocal.RUN.update({"proc": None, "lines": [], "bytes": 0, "running": False, "exit": None, "plan": None, "stopping": False})
        self.snap = mock.patch.object(actlocal, "docker_snapshot", lambda: None)
        self.snap.start()

    def tearDown(self):
        self.snap.stop()
        self.tmp.cleanup()

    def alive(self):
        """True while the grandchild keeps writing its heartbeat."""
        try:
            before = self.beat.read_text()
        except OSError:
            return False
        time.sleep(0.6)
        return self.beat.read_text() != before

    def item(self, seconds):
        return {"argv": [sys.executable, "-c", CHILD, str(self.beat)], "timeout_seconds": seconds}

    def test_the_time_limit_ends_the_child_and_the_grandchild(self):
        started = time.time()
        actlocal._worker(self.item(2), subprocess.Popen, time.time)
        self.assertLess(time.time() - started, 60, "the worker returned although the grandchild kept the pipe open")
        self.assertFalse(self.alive(), "the grandchild is still running")
        self.assertIsNotNone(actlocal.status()["exit"])
        self.assertFalse(actlocal.status()["running"])

    def test_stop_ends_the_tree(self):
        actlocal.RUN["running"] = True
        thread = threading.Thread(target=actlocal._worker, args=(self.item(300), subprocess.Popen, time.time), daemon=True)
        thread.start()
        end = time.time() + 20
        while time.time() < end and not self.beat.exists():
            time.sleep(0.1)
        self.assertTrue(self.beat.exists())
        self.assertEqual(actlocal.stop()["status"], "stopping")
        thread.join(30)
        self.assertFalse(thread.is_alive())
        self.assertFalse(self.alive())

    def test_only_containers_created_by_the_run_are_removed(self):
        removed = []

        def fake_run(args, **kw):
            removed.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")
        with mock.patch.object(actlocal.shutil, "which", return_value="docker"):
            handled = actlocal.clean_containers({"aaaaaaaaaaaa"}, run=fake_run, names=lambda: {"aaaaaaaaaaaa", "bbbbbbbbbbbb"})
        self.assertEqual(handled, ["bbbbbbbbbbbb"])
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0][-1], "bbbbbbbbbbbb")
        self.assertEqual(actlocal.clean_containers(None, run=fake_run), [])

    def test_a_process_the_module_did_not_start_has_no_group_to_kill(self):
        class Fake:
            pid = None
            calls = []

            def terminate(self):
                self.calls.append("terminate")

            def kill(self):
                self.calls.append("kill")
        fake = Fake()
        actlocal.kill_tree(fake)
        self.assertEqual(fake.calls, ["terminate", "kill"])


# --- the network mode -------------------------------------------------------------------------------------------------------------------------------------------------------------------
class NetworkMode(unittest.TestCase):
    def tearDown(self):
        localguard.reset_limits()

    def test_ipv6_is_refused_everywhere_in_the_same_way(self):
        for bad in ("::1", "[::1]", "fe80::1", "fd00::5", "2001:db8::1"):
            self.assertFalse(localguard.host_ok(bad), bad)
            self.assertEqual(localguard.settings_from({"listen": {"network": True, "host": bad}})["host"], "127.0.0.1", bad)
            self.assertIsNone(settings_api.LISTEN_HOST_RE.match(bad), bad)
        for good in ("127.0.0.1", "192.168.1.20", "10.0.0.4", "0.0.0.0", "localhost"):
            self.assertTrue(localguard.host_ok(good), good)

    def test_the_address_of_the_page_is_the_one_the_server_listens_on(self):
        self.assertEqual(localguard.display_host("192.168.1.20"), "192.168.1.20")
        self.assertEqual(localguard.display_host("0.0.0.0"), "127.0.0.1")
        self.assertEqual(localguard.display_host("127.0.0.1"), "127.0.0.1")
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("localguard.display_host(server.server_address[0])", source)

    def test_the_cookie_is_secure_only_when_the_connection_is_https(self):
        localguard.configure(True, "127.0.0.1", "t" * 20, secure=False)
        self.assertNotIn("Secure", localguard.cookie_header("abc"))
        localguard.configure(True, "127.0.0.1", "t" * 20, secure=True)
        header = localguard.cookie_header("abc")
        self.assertIn("; Secure", header)
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Strict", header)
        localguard.configure(False)
        self.assertFalse(localguard.public_state()["secure"], "never secure on the loopback mode")

    def test_the_first_visit_sets_the_cookie_and_goes_to_the_clean_address(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            class Stop(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **k):
                    return None
            opener = urllib.request.build_opener(Stop)
            try:
                opener.open(urllib.request.Request(server.base + "/?access=" + access, headers={"Accept": "text/html"}), timeout=8)
                self.fail("expected a redirect")
            except urllib.error.HTTPError as error:
                self.assertEqual(error.code, 302)
                self.assertNotIn("access", error.headers["Location"])
                self.assertIn(localguard.COOKIE, error.headers["Set-Cookie"])
                self.assertEqual(error.headers["Referrer-Policy"], "no-referrer")

    def test_wrong_tokens_lock_an_address_out_for_a_while(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            codes = [server.call("/api/health", headers={"X-Monitor-Access": "wrong" * 5})[0] for _ in range(12)]
            self.assertEqual(codes[:9], [401] * 9)
            self.assertEqual(codes[-1], 429)
            self.assertEqual(server.call("/api/health", headers={"X-Monitor-Access": "wrong" * 5})[0], 429, "a wrong token waits while the lock lasts")
            self.assertEqual(server.call("/api/health", headers={"X-Monitor-Access": access})[0], 200, "the right token always gets in (behind a proxy on this machine everybody shares one address)")

    def test_the_limiter_counts_per_address_and_expires(self):
        for _ in range(4):
            localguard.note_failure("10.0.0.1", 5, now=1000)
        self.assertFalse(localguard.is_locked("10.0.0.1", now=1001))
        self.assertTrue(localguard.note_failure("10.0.0.1", 5, now=1002))
        self.assertTrue(localguard.is_locked("10.0.0.1", now=1003))
        self.assertFalse(localguard.is_locked("10.0.0.2", now=1003))
        self.assertFalse(localguard.is_locked("10.0.0.1", now=1002 + localguard.LOCKOUT_SECONDS + 1))
        self.assertEqual(localguard.max_failed({"listen": {"max_failed_attempts": 2}}), 10)
        self.assertEqual(localguard.max_failed({"listen": {"max_failed_attempts": 7}}), 7)

    def test_the_webhook_has_a_rate_limit_per_address_on_the_network(self):
        self.assertFalse(any(localguard.over_rate("webhook", "10.0.0.9", 3, now=50 + i) for i in range(3)))
        self.assertTrue(localguard.over_rate("webhook", "10.0.0.9", 3, now=54))
        self.assertFalse(localguard.over_rate("webhook", "10.0.0.9", 3, now=200))

    def test_the_tls_files_are_read_from_the_configuration_and_a_bad_pair_is_an_error(self):
        self.assertEqual(localguard.tls_settings({}), {"cert": "", "key": "", "secure_cookie": False})
        self.assertEqual(localguard.tls_settings({"listen": {"tls_cert_file": "a.pem", "tls_key_file": "b.pem", "secure_cookie": True}}), {"cert": "a.pem", "key": "b.pem", "secure_cookie": True})
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.pem"
            bad.write_text("not a certificate", encoding="utf-8")
            with self.assertRaises(Exception):
                localguard.tls_context(str(bad), str(bad))

    def test_the_github_actions_keys_can_only_be_changed_from_this_computer(self):
        access = "T" * 24
        with LiveServer({"session_guard": True}, network=access) as server:
            headers = {"X-Monitor-Access": access}
            with mock.patch.object(localguard, "from_this_computer", return_value=False):
                for key in ("github_actions.enabled", "act.enabled", "act.allow_symlinks", "listen.tls_cert_file"):
                    token = server.call("/api/session-token", headers=headers)[1]["token"]
                    status, answer = server.call("/api/settings", {"changes": {key: True if key.endswith(("enabled", "symlinks")) else ""}}, {**headers, "X-Monitor-Token": token})
                    self.assertEqual((status, answer["errors"]["_"]), (403, "local_only"), key)

    def test_a_get_never_writes_and_the_copy_of_the_report_is_a_post_with_the_token(self):
        with tempfile.TemporaryDirectory() as folder, LiveServer({"session_guard": True}) as server:
            import sentinel_local
            with mock.patch.object(sentinel_local, "AUDIT_DIR", Path(folder)):
                server.call("/api/sentinel/parte.txt?save=1")
                self.assertEqual(list(Path(folder).iterdir()), [], "a GET must not write")
                self.assertEqual(server.call("/api/sentinel/parte/save", {})[0], 403, "the POST needs the one-use token")

    def test_every_post_body_of_the_advanced_endpoints_has_a_limit(self):
        with LiveServer({"session_guard": False}) as server:
            big = {"x": "y" * 20000}
            for path in ("/api/gh-action/plan", "/api/act/plan", "/api/github-token", "/api/mode", "/api/hot-only"):
                status, answer = server.call(path, big)      # a body over the limit is not read: it counts as an empty request
                self.assertFalse(isinstance(answer, dict) and (answer.get("ok") is True or answer.get("plan")), (path, status, answer))


# --- the webhook -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class WebhookReplay(unittest.TestCase):
    SECRET = "s" * 40
    CONFIG = {"webhook": {"enabled": True, "secret": SECRET, "replay_seconds": 600, "max_per_minute": 3}}

    def setUp(self):
        webhook.reset()
        self.n = 0

    def send(self, body=None, delivery="same-delivery-id", config=None, event="workflow_run", signature=None):
        raw = json.dumps(body or {"repository": {"name": "R", "full_name": "JuanenRac/R"}}).encode()
        headers = {"X-GitHub-Event": event, "X-Hub-Signature-256": signature or webhook.sign(self.SECRET, raw)}
        if delivery:
            headers["X-GitHub-Delivery"] = delivery
        return webhook.handle(config or self.CONFIG, raw, headers, ["R"])

    def test_the_same_signed_delivery_is_accepted_once(self):
        first = self.send()
        second = self.send()
        self.assertEqual((first[0], first[2]), (200, "R"))
        self.assertEqual((second[0], second[2], second[1].get("duplicate")), (202, None, True))

    def test_a_delivery_id_is_required(self):
        self.assertEqual(self.send(delivery=None)[0], 400)
        self.assertEqual(self.send(delivery="x y")[0], 400)

    def test_a_bad_signature_is_never_remembered(self):
        self.assertEqual(self.send(signature="sha256=" + "0" * 64)[0], 401)
        self.assertEqual(self.send()[0], 200, "the same id with a good signature still works")

    def test_the_replay_window_forgets_and_the_memory_is_bounded(self):
        self.assertFalse(webhook.replay("abcdefgh", 60, now=100))
        self.assertTrue(webhook.replay("abcdefgh", 60, now=120))
        self.assertFalse(webhook.replay("abcdefgh", 60, now=200))
        for i in range(webhook.MAX_DELIVERIES + 50):
            webhook.replay(f"delivery-{i}", 86400, now=1000)
        self.assertLessEqual(len(webhook._seen), webhook.MAX_DELIVERIES + 1)

    def test_one_repository_cannot_cause_endless_refreshes(self):
        codes = [self.send(delivery=f"delivery-{i}")[0] for i in range(5)]
        self.assertEqual(codes[:3], [200, 200, 200])
        self.assertEqual(codes[3:], [202, 202])

    def test_the_owner_in_the_payload_must_be_watched(self):
        self.assertEqual(self.send({"repository": {"name": "R", "full_name": "someone-else/R"}}, delivery="d-other-1")[2], None)
        self.assertEqual(self.send({"repository": {"name": "R", "full_name": "JuanenRac/Other"}}, delivery="d-other-2")[2], None)
        self.assertEqual(self.send({"repository": {"name": "R", "full_name": "JuanenRac/R"}}, delivery="d-other-3")[2], "R")
        config = {"webhook": {**self.CONFIG["webhook"], "allowed_owners": ["some-org"]}}
        self.assertEqual(self.send({"repository": {"name": "R", "full_name": "some-org/R"}}, delivery="d-other-4", config=config)[2], "R")

    def test_a_signature_header_with_odd_characters_is_a_plain_refusal(self):
        self.assertFalse(webhook.verify(self.SECRET, b"{}", "sha256=\u00e9\u00e9"))
        self.assertEqual(self.send(signature="sha256=\u00e9" * 3)[0], 401)

    def test_an_accepted_event_drops_the_cached_reads_and_marks_the_repository_for_the_next_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = etagcache.EtagCache(path=Path(tmp) / "e.json")
            cache.entries = {"repos/JuanenRac/R/actions/runs?per_page=20": {"etag": '"a"', "at": time.time(), "data": {"workflow_runs": []}},
                             "repos/JuanenRac/Other/actions/runs": {"etag": '"b"', "at": time.time(), "data": {}}}
            saved = (am.ETAG["cache"], dict(am.RUN_CACHE))
            am.ETAG["cache"] = cache
            am.RUN_CACHE.clear()
            am.RUN_CACHE["R"] = {"runs": [], "at": time.time(), "error": None}
            try:
                am.webhook_settle("R")
                self.assertEqual(list(cache.entries), ["repos/JuanenRac/Other/actions/runs"])
                self.assertEqual(am.RUN_CACHE["R"]["at"], 0)
            finally:
                am.ETAG["cache"] = saved[0]
                am.RUN_CACHE.clear()
                am.RUN_CACHE.update(saved[1])


class EtagFile(unittest.TestCase):
    def test_a_damaged_cache_file_is_a_miss_not_a_stale_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "e.json"
            path.write_text(json.dumps({"entries": {"a": {"etag": '"ok"', "at": 1, "data": "text"}, "b": {"etag": "bad etag", "at": 1, "data": {}}, "c": {"etag": '"c"', "at": 1, "data": {}}}}), encoding="utf-8")
            self.assertEqual(list(etagcache.EtagCache(path=path).entries), ["c"])
            path.write_text("{ not json", encoding="utf-8")
            self.assertEqual(etagcache.EtagCache(path=path).entries, {})

    def test_a_304_on_an_entry_without_a_body_is_read_again_in_full_and_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = etagcache.EtagCache(path=Path(tmp) / "e.json")
            cache.entries["x"] = {"etag": '"t"', "at": time.time(), "data": None}
            answers = iter([(0, "HTTP/2.0 304 Not Modified\n\n", ""), (0, 'HTTP/2.0 200 OK\netag: "n"\n\n{"a": 1}', "")])
            data, status = cache.fetch("x", lambda args: next(answers))
            self.assertEqual((data, status, cache.stats()["invalid"]), ({"a": 1}, "200", 1))


# --- the MCP server ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class McpRobust(unittest.TestCase):
    def test_malformed_messages_get_an_error_for_that_message_only(self):
        bad = ['{"jsonrpc":"2.0","id":1,"method":"tools/call","params":[1,2]}', '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":"x"}',
               '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_alerts","arguments":[1]}}', '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":5}}',
               '{"jsonrpc":"2.0","id":[1],"method":"ping"}', '{"jsonrpc":"2.0","id":6,"method":7}', '[1,2]', '"text"', '{"jsonrpc":"2.0","id":7,"method":"initialize","params":[1]}']
        good = '{"jsonrpc":"2.0","id":99,"method":"ping"}'
        out = io.StringIO()
        mcp_server.main([], stdin=io.StringIO("\n".join(bad + [good]) + "\n"), stdout=out)
        replies = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual(replies[-1], {"jsonrpc": "2.0", "id": 99, "result": {}}, "the server went on after every bad message")
        self.assertTrue(all("error" in r for r in replies[:-1]))
        self.assertEqual(len(replies), len(bad) + 1)

    def test_a_defect_inside_a_tool_is_an_internal_error_not_the_end(self):
        with mock.patch.object(mcp_server, "call", side_effect=KeyError("boom")):
            reply = mcp_server.serve_line('{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_alerts"}}', {})
        self.assertEqual(reply["error"]["code"], -32603)
        self.assertEqual(reply["id"], 5)

    def test_a_line_that_is_too_long_is_refused_without_ending_the_server(self):
        huge = '{"jsonrpc":"2.0","id":1,"method":"ping","params":{"x":"' + "a" * (mcp_server.MAX_LINE + 10) + '"}}\n'
        out = io.StringIO()
        mcp_server.main([], stdin=io.StringIO(huge + '{"jsonrpc":"2.0","id":2,"method":"ping"}\n'), stdout=out)
        replies = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual(replies[0]["error"]["message"], "request too large")
        self.assertEqual(replies[1]["id"], 2)


# --- notifications: the limit counts messages ------------------------------------------------------------------------------------------------------------------------------------------
class NotificationLimit(unittest.TestCase):
    def config(self, limit):
        return {"notify": {"enabled": True, "max_per_hour": limit, "events": ["red_new"], "channels": {
            "discord": {"enabled": True, "url_env": "T165_DISCORD"}, "slack": {"enabled": True, "url_env": "T165_SLACK"}, "matrix": {"enabled": False}}}}

    def setUp(self):
        notifiers._sent.clear()
        self.env = mock.patch.dict(os.environ, {"T165_DISCORD": "https://discord.com/api/webhooks/1/abc", "T165_SLACK": "https://hooks.slack.com/services/T/B/x"})
        self.env.start()
        self.requests = []

        class Answer:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        self.opener = lambda request, timeout=0: (self.requests.append(request.full_url), Answer())[1]

    def tearDown(self):
        self.env.stop()
        notifiers._sent.clear()

    def test_two_channels_and_a_limit_of_one_send_one_message(self):
        results = notifiers.notify(self.config(1), notifiers.test_event(), opener=self.opener)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(results), 1)

    def test_a_limit_of_two_lets_the_event_reach_both_and_the_next_event_none(self):
        notifiers.notify(self.config(2), notifiers.test_event(), opener=self.opener)
        notifiers.notify(self.config(2), notifiers.test_event(), opener=self.opener)
        self.assertEqual(len(self.requests), 2)

    def test_threads_never_go_over_the_limit(self):
        threads = [threading.Thread(target=notifiers.notify, args=(self.config(5), notifiers.test_event()), kwargs={"opener": self.opener}) for _ in range(12)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(self.requests), 5)

    def test_a_channel_that_cannot_send_books_nothing(self):
        config = self.config(1)
        config["notify"]["channels"]["slack"]["url_env"] = "T165_MISSING"
        results = notifiers.notify(config, notifiers.test_event(), opener=self.opener)
        self.assertEqual(len(self.requests), 1, "the working channel still had its one message")
        self.assertEqual(sorted(r["reason"] for r in results if not r["ok"]), ["no_secret"])


# --- settings: no lost update ------------------------------------------------------------------------------------------------------------------------------------------------------------
class SettingsLock(unittest.TestCase):
    def test_two_saves_at_once_both_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions_monitor.json"
            path.write_text(json.dumps({"refresh_seconds": 45, "stuck_minutes": 120}), encoding="utf-8")
            real = settings_api._read_file

            def slow(p):
                data = real(p)
                time.sleep(0.3)      # the window in which, without the lock, the second save starts from the old file
                return data
            results = []
            with mock.patch.object(settings_api, "_read_file", slow), mock.patch.object(settings_api, "BACKUP_DIR", Path(tmp) / "b"):
                threads = [threading.Thread(target=lambda c=c: results.append(settings_api.apply(c, path))) for c in ({"refresh_seconds": 50}, {"stuck_minutes": 130})]
                [t.start() for t in threads]
                [t.join() for t in threads]
            final = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((final["refresh_seconds"], final["stuck_minutes"]), (50, 130))
            self.assertTrue(all(r["ok"] for r in results))


# --- the token goes to gh only ------------------------------------------------------------------------------------------------------------------------------------------------------------
class TokenOnlyForGh(unittest.TestCase):
    TOKEN = "ghp_" + "a1B2c3D4" * 4

    def setUp(self):
        self.env = mock.patch.dict(os.environ)      # the test asserts about the environment of THIS process: a GH_TOKEN exported by whoever runs it must not decide the result
        self.env.start()
        for name in ("GH_TOKEN", "GITHUB_TOKEN"):
            os.environ.pop(name, None)
        secretstore.APPLIED["token"] = self.TOKEN

    def tearDown(self):
        self.env.stop()
        secretstore.clear_environment()

    def test_gh_gets_it_and_nothing_else_does(self):
        self.assertEqual(secretstore.gh_kwargs()["env"]["GH_TOKEN"], self.TOKEN)
        self.assertNotIn("GH_TOKEN", os.environ)
        self.assertNotIn("GH_TOKEN", actlocal.minimal_env())
        seen = {}

        def fake_run(args, **kw):
            seen["env"] = kw.get("env")
            return subprocess.CompletedProcess(args, 0, "{}", "")
        with mock.patch.object(am.subprocess, "run", fake_run):
            am.run_gh(["api", "user"])
        self.assertEqual(seen["env"]["GH_TOKEN"], self.TOKEN)

    def test_the_notification_command_and_the_hooks_do_not_inherit_it(self):
        with mock.patch.object(subprocess, "Popen") as popen:
            import events
            source = (HERE / "events.py").read_text(encoding="utf-8")
            self.assertNotIn("gh_kwargs", source)
        self.assertNotIn("GH_TOKEN", os.environ)


# --- waits with jitter ------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class RetryWaits(unittest.TestCase):
    def test_the_waits_grow_and_carry_a_jitter(self):
        self.assertEqual(am.secondary_wait("secondary rate limit", 0), 60)
        self.assertEqual(am.secondary_wait("secondary rate limit", 0, 1.0), 72)
        self.assertGreater(am.secondary_wait("secondary rate limit", 1, 0.5), am.secondary_wait("secondary rate limit", 0, 0.5))
        self.assertLessEqual(am.secondary_wait("secondary rate limit", 9, 1.0), 360)
        self.assertEqual(am.secondary_wait("timeout", 1), 4)
        import resilience
        waits = {resilience.backoff(2) for _ in range(20)}
        self.assertGreater(len(waits), 1, "the transient wait is randomised")


# --- the doctor ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class DoctorRisks(unittest.TestCase):
    def test_dangerous_combinations_are_named(self):
        self.assertEqual(doctor.risks({}), ("ok", ""))
        self.assertEqual(doctor.risks({"listen": {"network": True, "host": "0.0.0.0"}}), ("warn", "network_all"))
        self.assertEqual(doctor.risks({"listen": {"network": True, "host": "192.168.1.5"}}), ("ok", ""))
        status, codes = doctor.risks({"listen": {"network": True, "host": "192.168.1.5"}, "ai": {"actions": {"enabled": True, "execute": True}}, "github_token": {"enabled": True, "store": "file"},
                                      "act": {"enabled": True}})
        self.assertEqual(status, "warn")
        for code in ("execute_network", "token_file", "act_network"):
            self.assertIn(code, codes)
        self.assertEqual(doctor.risks({"ai": {"actions": {"enabled": True, "execute": True}}}), ("ok", ""), "no network, no combination")

    def test_the_backend_of_the_token_is_shown_and_never_the_token(self):
        class Store:
            def __init__(self, kind):
                self.kind = kind

            def backend(self):
                return "file" if self.kind == "file" else "system"
        self.assertEqual(doctor.token_backend({}), ("ok", "off"))
        self.assertEqual(doctor.token_backend({"github_token": {"enabled": True, "store": "file"}}, Store), ("warn", "file"))
        self.assertEqual(doctor.token_backend({"github_token": {"enabled": True, "store": "system"}}, Store), ("ok", "system"))

    def test_both_checks_are_in_the_report_in_every_language(self):
        checks = doctor.run(runner=lambda args, timeout=20: (0, "{}", ""), config={"listen": {"network": True, "host": "0.0.0.0"}})
        by = {c["id"]: c for c in checks}
        self.assertEqual(by["risks"]["status"], "warn")
        import i18n
        for lang in i18n.LANGS:
            self.assertTrue(i18n.tl(lang, "doctor.t.risks") and i18n.tl(lang, "doctor.f.backend"))


# --- exports: the reason is told -------------------------------------------------------------------------------------------------------------------------------------------------------------
class ExportReasons(unittest.TestCase):
    SNAP = {"generated": "x", "ecosystems": {}, "a5": {"pending_sign": []}}

    def test_each_refusal_has_its_own_reason_and_text(self):
        self.assertEqual(export_status.write_sign_queue(None, "q.json"), (None, "no_data"))
        self.assertEqual(export_status.write_sign_queue(self.SNAP, "//server/share/q.json"), (None, "path"))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(export_status.write_sign_queue(self.SNAP, tmp), (None, "is_dir"))
            blocker = Path(tmp) / "file"
            blocker.write_text("x", encoding="utf-8")
            target, why = export_status.write_sign_queue(self.SNAP, blocker / "inside" / "q.json")
            self.assertIsNone(target)
            self.assertTrue(why.startswith("write:"))
            self.assertIn(why[6:].strip(), export_status.reason_text(why))
        self.assertTrue(export_status.reason_text("path") and export_status.reason_text("is_dir") and export_status.reason_text("no_data"))


# --- the release gate ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class GateStages(unittest.TestCase):
    def test_the_ordinary_suite_runs_once_without_the_nested_install_test(self):
        seen = {}

        def fake(cmd, **kw):
            seen.update(cmd=cmd, env=kw["env"], timeout=kw.get("timeout"))
            return subprocess.CompletedProcess(cmd, 0, "Ran 1 test\nOK\n", "")
        with mock.patch.object(mr.subprocess, "run", fake):
            mr.run_tests()
        self.assertEqual(seen["env"]["MONITOR_NO_NESTED"], "1")
        self.assertEqual(seen["timeout"], mr.TEST_TIMEOUT)

    def test_a_failure_shows_stdout_and_stderr_and_a_hang_is_a_failure(self):
        with mock.patch.object(mr.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "OUT-TEXT", "ERR-TEXT")):
            with self.assertRaises(SystemExit) as raised:
                mr.run_tests()
        self.assertIn("OUT-TEXT", str(raised.exception))
        self.assertIn("ERR-TEXT", str(raised.exception))
        with mock.patch.object(mr.subprocess, "run", side_effect=subprocess.TimeoutExpired("x", 1)):
            with self.assertRaises(SystemExit) as raised:
                mr.run_tests(timeout=1)
        self.assertIn("did not finish", str(raised.exception))

    def test_the_nested_test_is_a_separate_opt_in_stage(self):
        text = (HERE / "tests" / "test_i18n.py").read_text(encoding="utf-8")
        self.assertIn("MONITOR_RUN_CLEAN_INSTALL", text)
        self.assertIn("clean_install_check", (HERE / "make_release.py").read_text(encoding="utf-8"))


# --- small regressions of the third review -------------------------------------------------------------------------------------------------------------------------------------------
class SmallRegressions(unittest.TestCase):
    def test_versions_compare_as_numbers_with_or_without_v(self):
        self.assertTrue(updatecheck.is_newer("1.6.10", "1.6.9"))
        self.assertTrue(updatecheck.is_newer("v1.7.0", "1.6.10"))
        self.assertFalse(updatecheck.is_newer("1.6.9", "v1.6.10"))
        self.assertFalse(updatecheck.is_newer("1.6.5", "1.6.5"))
        self.assertLess(updatecheck.parse_semver("1.6.9"), updatecheck.parse_semver("v1.6.10"))
        self.assertLess(updatecheck.parse_semver("1.6.10"), updatecheck.parse_semver("1.7.0"))

    def test_a_log_with_the_path_of_a_person_is_cleaned(self):
        for text in ("error in C:\\Users\\bob\\project\\a.py", "failed at /home/alice/work/x.py", "see /Users/carol/dev/x", "at C:/Users/dave/x"):
            out = ai_alerts.redact(text)
            for name in ("bob", "alice", "carol", "dave"):
                self.assertNotIn(name, out, text)

    def test_the_help_does_not_run_what_a_malicious_document_says(self):
        evil = ("# Title\n\n<script>alert(1)</script>\n\n[click](javascript:alert(1))\n\n[data](data:text/html;base64,AAAA)\n\n![x](http://evil.example/p.png)\n\n"
                "<img src=x onerror=alert(1)>\n\n[ok](https://example.org/a)\n")
        out = helpdocs.render(evil, files={})
        self.assertNotIn("<script", out)
        self.assertNotIn("javascript:", out.replace("&", "&"))
        self.assertNotIn('href="javascript', out)
        self.assertNotIn('href="data', out)
        self.assertNotIn("<img", out)
        self.assertNotIn("onerror=alert(1)>", out)
        self.assertIn('href="https://example.org/a"', out)

    def test_the_demo_data_never_looks_like_a_real_token(self):
        for name in ("demo_mode.py", "tests/test_164.py"):
            pass
        text = (HERE / "demo_mode.py").read_text(encoding="utf-8")
        for prefix in ("ghp_", "gho_", "ghu_", "ghs_", "github_pat_"):
            self.assertNotIn(prefix, text)
        for path in (HERE.parent / "docs" / "screenshots").glob("*"):
            if path.suffix in (".svg", ".txt", ".md", ".json"):
                body = path.read_text(encoding="utf-8", errors="replace")
                for prefix in ("ghp_", "gho_", "github_pat_"):
                    self.assertNotIn(prefix, body, path.name)

    def test_the_documents_describe_exactly_the_actions_the_code_has(self):
        import ghactions
        import ai_actions
        actions = set(ghactions.ACTIONS) if hasattr(ghactions, "ACTIONS") else set()
        self.assertIn("merge_pr", actions)
        runnable = set(ai_actions.RUNNABLE)
        self.assertNotIn("merge_pr", runnable, "the AI never merges")
        self.assertTrue(all(not a.startswith(("merge", "delete")) for a in runnable))
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"ADVANCED{suffix}.md").read_text(encoding="utf-8")
            for action in actions:
                self.assertIn(action, text, f"ADVANCED{suffix}.md names {action}")
            for forbidden in ("delete_branch", "delete_repo", "set_secret"):
                self.assertNotIn(forbidden, text)
        ai_text = (HERE / "docs" / "AI.md").read_text(encoding="utf-8")
        self.assertIn("merging pull requests", ai_text)


if __name__ == "__main__":
    unittest.main()
