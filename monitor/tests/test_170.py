# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.0: several accounts in the complete edition (the folder of accounts, the supervisor that runs one monitor per account, the account of a request, the migration from the old layout),
the shell of the page (the switcher, the page of all accounts, ?view= and ?chrome=0) and the proof that the lite edition knows nothing of any of it. No test here calls GitHub: the monitor of an
account is replaced by a small stub that answers the same few endpoints."""
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import accounts  # noqa: E402
import accounts_supervisor as sup  # noqa: E402
import localguard  # noqa: E402


class AccountIds(unittest.TestCase):
    def test_a_safe_id_is_lower_case_letters_digits_underscore_and_dash(self):
        for good in ("personal", "org-acme", "a", "a_b-c9", "x" * 40):
            self.assertTrue(accounts.valid_id(good), good)

    def test_an_unsafe_id_is_refused_and_can_never_leave_the_folder_of_accounts(self):
        for bad in ("", "Org", "../x", "a/b", "a\\b", "a b", "-x", "_x", "x" * 41, ".", "..", "con\x00", None, 5, ["a"], "a.b", "\u00e9"):
            self.assertFalse(accounts.valid_id(bad), repr(bad))
            with self.assertRaises(ValueError):
                accounts.account_dir(bad if isinstance(bad, str) else "")

    def test_an_id_made_from_free_text_is_always_valid_or_the_fallback(self):
        self.assertEqual(accounts.clean_id("Acme Corp!"), "acme-corp")
        self.assertEqual(accounts.clean_id("###"), "default")
        self.assertEqual(accounts.clean_id("", "none"), "none")
        for text in ("Org/../x", "A" * 200, "  \u00dcn\u00ef C\u00f6d\u00e9  ", "-_-"):
            self.assertTrue(accounts.valid_id(accounts.clean_id(text)), text)


class Folders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": ""})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_without_the_folder_it_is_the_old_single_account(self):
        self.assertEqual(accounts.layout(self.base), "single")
        self.assertEqual(accounts.list_accounts(self.base), [])
        self.assertEqual(accounts.default_account(self.base), "")

    def test_an_account_is_a_folder_with_a_configuration_inside_and_the_list_is_sorted(self):
        accounts.create_account("zeta", "z", self.base)
        accounts.create_account("alpha", "a", self.base)
        (accounts.root_dir(self.base) / "empty").mkdir()
        (accounts.root_dir(self.base) / "Bad Name").mkdir()
        (accounts.root_dir(self.base) / "Bad Name" / accounts.CONFIG_NAME).write_text("{}")
        self.assertEqual(accounts.list_accounts(self.base), ["alpha", "zeta"])
        self.assertEqual(accounts.layout(self.base), "accounts")
        self.assertEqual(json.loads(accounts.config_path("alpha", self.base).read_text(encoding="utf-8"))["github_owner"], "a")

    def test_creating_never_overwrites_and_refuses_an_unsafe_id(self):
        accounts.create_account("one", "o", self.base)
        with self.assertRaises(FileExistsError):
            accounts.create_account("one", "other", self.base)
        with self.assertRaises(ValueError):
            accounts.create_account("../x", "o", self.base)
        self.assertEqual(json.loads(accounts.config_path("one", self.base).read_text(encoding="utf-8"))["github_owner"], "o")

    def test_global_json_chooses_the_enabled_accounts_and_the_default_and_a_damaged_one_is_ignored(self):
        for name in ("a", "b", "c"):
            accounts.create_account(name, name, self.base)
        self.assertEqual(accounts.enabled_accounts(self.base), ["a", "b", "c"])
        self.assertEqual(accounts.default_account(self.base), "a")
        path = accounts.root_dir(self.base) / accounts.GLOBAL_NAME
        path.write_text(json.dumps({"default_account": "c", "enabled_accounts": ["c", "b", "nope", "../x"]}), encoding="utf-8")
        self.assertEqual(accounts.enabled_accounts(self.base), ["c", "b"])
        self.assertEqual(accounts.default_account(self.base), "c")
        path.write_text(json.dumps({"default_account": "a", "enabled_accounts": ["b"]}), encoding="utf-8")
        self.assertEqual(accounts.default_account(self.base), "b")      # the default must be an enabled account
        for broken in ("{", "[]", "null", '{"enabled_accounts": 5}', '{"default_account": "../x"}'):
            path.write_text(broken, encoding="utf-8")
            self.assertEqual(accounts.enabled_accounts(self.base), ["a", "b", "c"], broken)

    def test_the_environment_can_move_the_folder_of_accounts(self):
        elsewhere = self.base / "else"
        with mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(elsewhere)}):
            accounts.create_account("w", "w", self.base)
            self.assertEqual(accounts.list_accounts(self.base), ["w"])
        self.assertTrue((elsewhere / "w" / accounts.CONFIG_NAME).is_file())
        self.assertFalse((self.base / "accounts").exists())


class Migration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.src = self.base / "old"
        self.src.mkdir()
        (self.src / "actions_monitor.json").write_text('{"github_owner": "me"}', encoding="utf-8")
        (self.src / "etag_cache.json").write_text("{}", encoding="utf-8")
        (self.src / "config_backups").mkdir()
        (self.src / "config_backups" / "b.json").write_text("{}", encoding="utf-8")
        (self.src / "actions_monitor_lite.json").write_text('{"x": 1}', encoding="utf-8")
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": ""})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_dry_run_writes_nothing(self):
        done = accounts.migrate(self.base, self.src)
        self.assertFalse(done["applied"])
        self.assertEqual(len(done["items"]), 3)
        self.assertFalse((self.base / "accounts").exists())

    def test_apply_copies_keeps_the_originals_and_leaves_a_marker(self):
        done = accounts.migrate(self.base, self.src, apply=True)
        self.assertTrue(done["applied"])
        self.assertEqual((done["copied"], done["problems"]), (3, []))
        folder = accounts.account_dir("default", self.base)
        self.assertEqual(json.loads((folder / "actions_monitor.json").read_text(encoding="utf-8"))["github_owner"], "me")
        self.assertTrue((folder / "cache" / "etag_cache.json").is_file())
        self.assertTrue((folder / "config_backups" / "b.json").is_file())
        self.assertTrue((self.src / "actions_monitor.json").is_file(), "the originals are never deleted")
        self.assertTrue((folder / accounts.MARKER).is_file())
        self.assertFalse((folder / "actions_monitor_lite.json").exists(), "the lite edition's files are not part of the migration")

    def test_a_second_run_refuses_so_two_states_never_mix(self):
        accounts.migrate(self.base, self.src, apply=True)
        again = accounts.migrate(self.base, self.src, apply=True)
        self.assertEqual((again["applied"], again["items"], again["copied"]), (False, [], 0))

    def test_nothing_to_migrate_without_the_old_files(self):
        empty = self.base / "empty"
        empty.mkdir()
        self.assertEqual(accounts.migrate(self.base, empty, apply=True)["items"], [])
        self.assertFalse((self.base / "accounts").exists())


# --- a stub that stands for the monitor of one account ----------------------------------------------------------------------------------------------------------------------------------
STUB = r'''
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
account, port = sys.argv[1], int(sys.argv[2])
mode = sys.argv[3] if len(sys.argv) > 3 else "ok"
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, payload, kind="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code); self.send_header("Content-Type", kind); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health": return self.send(200, {"ok": True, "version": "9.9.9", "loaded": True, "offline": False, "account": account, "host": self.headers.get("Host"), "query": self.path})
        if path == "/api/data": return self.send(200, {"data": {"owner": account + "-owner", "repos": ["r1", "r2", "r3"], "active": [{}], "failing": [{}, {}], "figures": {"fail24": 2, "ok24": 7}, "rate": {"remaining": 4000}}, "error": None, "hint": None})
        if path == "/": return self.send(200, ("<html>const I18N=null;const ACC=/*ACCOUNTS_DATA*/null;" + account + "</html>").encode(), "text/html; charset=utf-8")
        if path == "/api/echo": return self.send(200, {"account": account, "path": self.path, "origin": self.headers.get("Origin"), "x_account": self.headers.get("X-Account-Id"), "token": self.headers.get("X-Monitor-Token")})
        self.send(404, {"error": "no"})
    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(size)
        if self.path.split("?")[0] == "/api/webhook":
            return self.send(202, {"webhook_for": account, "event": self.headers.get("X-GitHub-Event"), "signature": self.headers.get("X-Hub-Signature-256"), "cookie": self.headers.get("Cookie")})
        self.send(200, {"account": account, "got": json.loads(body or b"{}"), "origin": self.headers.get("Origin"), "host": self.headers.get("Host")})
if mode == "crash": sys.exit(3)
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
'''


def stub_command(folder, mode="ok"):
    path = Path(folder) / "stub_child.py"
    path.write_text(STUB, encoding="utf-8")
    return lambda account_id, port: [sys.executable, "-I", str(path), account_id, str(port), mode]


def get(url, headers=None, data=None, method=None):
    request = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            raw = answer.read()
            return answer.status, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw.decode("utf-8", "replace")), dict(answer.headers)
    except urllib.error.HTTPError as error:
        try:
            raw = error.read()
            return error.code, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw.decode("utf-8", "replace")), dict(error.headers)
        finally:
            error.close()


class Running(unittest.TestCase):
    """A supervisor with two stub accounts and a real HTTP server in front of it."""
    names = ("alpha", "beta")
    mode = "ok"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(self.base / "accounts")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in self.names:
            accounts.create_account(name, name + "-owner")
        self.supervisor = sup.Supervisor(command_for=stub_command(self.base, self.mode))
        self.addCleanup(self.supervisor.stop)
        self.supervisor.sync()
        self.settle()
        sup.SUPERVISOR["obj"] = self.supervisor
        self.addCleanup(lambda: sup.SUPERVISOR.update(obj=None))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), sup.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close()))
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.addCleanup(localguard.configure, False)

    def settle(self, rounds=40):
        for _ in range(rounds):
            self.supervisor.check()
            if all(c.health is not None for c in self.supervisor.children.values()):
                return
            time.sleep(0.25)


class SupervisorApi(Running):
    def test_the_summary_lists_every_enabled_account_with_the_figures_its_monitor_gave(self):
        status, answer, _ = get(self.url + "/api/accounts")
        self.assertEqual(status, 200)
        self.assertEqual([a["id"] for a in answer["accounts"]], ["alpha", "beta"])
        self.assertEqual(answer["default"], "alpha")
        one = answer["accounts"][0]
        self.assertEqual((one["state"], one["repos"], one["running"], one["failing"], one["fail24"], one["ok24"], one["owner"]), ("ok", 3, 1, 2, 2, 7, "alpha-owner"))
        self.assertNotIn("token", json.dumps(answer).lower())

    def test_each_account_answers_for_itself_by_query_or_by_header(self):
        for account in ("alpha", "beta"):
            self.assertEqual(get(f"{self.url}/api/health?account={account}")[1]["account"], account)
            self.assertEqual(get(self.url + "/api/health", headers={"X-Account-Id": account})[1]["account"], account)
        self.assertEqual(get(self.url + "/api/echo")[1]["account"], "alpha", "no account asked: the default one")

    def test_the_child_never_sees_the_account_parameter_or_the_header_and_gets_its_own_host(self):
        answer = get(f"{self.url}/api/echo?account=beta&lang=es", headers={"X-Account-Id": "beta"})[1]
        self.assertEqual(answer["path"], "/api/echo?lang=es")
        self.assertIsNone(answer["x_account"])
        health = get(f"{self.url}/api/health?account=beta")[1]
        self.assertTrue(health["host"].startswith("127.0.0.1:"))

    def test_an_unknown_or_disabled_account_is_a_404_and_an_unsafe_id_cannot_reach_a_file(self):
        for bad in ("nope", "..", "../alpha", "ALPHA", "a" * 60, "alpha%2F..", ""):
            status = get(f"{self.url}/api/health?account={bad}")[0]
            self.assertIn(status, (404, 200), bad)
            if bad:
                self.assertEqual(status, 404 if bad != "" else 200, bad)
        for bad in ("..%2Fx", "x%2F..", "ALPHA", "no"):
            self.assertEqual(get(f"{self.url}/api/accounts/{bad}/status")[0], 404, bad)

    def test_one_account_status_has_its_entry_and_its_own_document(self):
        status, answer, _ = get(self.url + "/api/accounts/beta/status")
        self.assertEqual((status, answer["id"], answer["state"], answer["data"]["owner"]), (200, "beta", "ok", "beta-owner"))

    def test_a_post_reaches_only_the_account_asked_for_with_its_own_origin(self):
        body = json.dumps({"x": 1}).encode()
        headers = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.server.server_address[1]}"}
        status, answer, _ = get(f"{self.url}/api/echo2?account=beta", headers=headers, data=body)
        self.assertEqual((status, answer["account"], answer["got"]), (200, "beta", {"x": 1}))
        self.assertEqual(answer["origin"], "http://127.0.0.1:%d" % self.supervisor.child("beta").port)
        self.assertEqual(answer["host"], "127.0.0.1:%d" % self.supervisor.child("beta").port)

    def test_the_page_carries_the_list_of_accounts_and_the_current_one(self):
        status, page, _ = get(self.url + "/?account=beta")
        self.assertEqual(status, 200)
        self.assertNotIn("/*ACCOUNTS_DATA*/", page)
        info = json.loads(page.split("const ACC=")[1].split(";beta")[0])
        self.assertEqual((info["current"], info["accounts"], info["default"]), ("beta", ["alpha", "beta"], "alpha"))
        info_all = json.loads(get(self.url + "/?account=all")[1].split("const ACC=")[1].split(";alpha")[0])
        self.assertEqual(info_all["current"], "alpha", "the page of all accounts is the page of the default one with the grid on top")

    def test_a_request_with_a_wrong_host_is_refused_like_in_a_single_monitor(self):
        self.assertEqual(get(self.url + "/api/accounts", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(get(self.url + "/api/accounts", headers={"Origin": "http://evil.example"})[0], 403)

    def test_in_network_mode_the_access_token_is_needed_for_everything_including_the_summary(self):
        localguard.configure(True, "127.0.0.1", "T" * 32)
        self.assertEqual(get(self.url + "/api/accounts")[0], 401)
        self.assertEqual(get(self.url + "/api/health?account=alpha")[0], 401)
        self.assertEqual(get(self.url + "/api/accounts", headers={"X-Monitor-Access": "T" * 32})[0], 200)
        self.assertEqual(get(self.url + "/api/accounts", headers={"X-Monitor-Access": "wrong"})[0], 401)

    def test_a_body_that_is_too_large_is_refused_before_it_reaches_any_account(self):
        request = urllib.request.Request(f"{self.url}/api/echo2?account=alpha", data=b"x", method="POST", headers={"Content-Length": str(sup.MAX_BODY + 1)})
        try:
            with urllib.request.urlopen(request, timeout=5) as answer:
                self.fail("answered %s" % answer.status)
        except urllib.error.HTTPError as error:
            error.close()
            self.assertEqual(error.code, 413)
        except (urllib.error.URLError, ConnectionError):
            pass


class Isolation(Running):
    def test_a_dead_account_is_noticed_and_started_again_while_the_other_keeps_answering(self):
        victim = self.supervisor.child("alpha")
        first_pid = victim.proc.pid
        victim.proc.kill()
        victim.proc.wait(timeout=5)
        self.supervisor.check()
        self.assertEqual(victim.failures, 1)
        self.assertIsNone(victim.health)
        self.assertEqual(get(f"{self.url}/api/health?account=beta")[1]["account"], "beta", "the other account never noticed")
        status, answer, _ = get(f"{self.url}/api/health?account=alpha")
        self.assertEqual(status, 503, "while it is down its requests say so instead of hanging")
        states = {a["id"]: a["state"] for a in get(self.url + "/api/accounts")[1]["accounts"]}
        self.assertEqual((states["alpha"], states["beta"]), ("down", "ok"))
        victim.next_start = 0
        self.settle()
        self.assertTrue(victim.alive())
        self.assertNotEqual(victim.proc.pid, first_pid)
        self.assertEqual(victim.restarts, 1)
        self.assertEqual(get(f"{self.url}/api/health?account=alpha")[1]["account"], "alpha")

    def test_the_wait_before_a_new_start_grows_and_a_healthy_account_forgets_it(self):
        child = self.supervisor.child("alpha")
        for expected in (2, 5, 15, 30, 60, 120, 120):
            child.proc.kill()
            child.proc.wait(timeout=5)
            before = time.time()
            self.supervisor.check(now=before)
            self.assertAlmostEqual(child.next_start - before, expected, delta=0.01)
            child.next_start = 0
            self.supervisor.check()          # started again
        self.settle()
        self.assertEqual(child.failures, 0, "a start that became healthy resets the count")

    def test_an_account_that_dies_at_once_is_retried_with_a_wait_and_never_stops_the_supervisor(self):
        self.supervisor.stop()
        self.supervisor = sup.Supervisor(command_for=stub_command(self.base, "crash"))
        self.addCleanup(self.supervisor.stop)
        self.supervisor.sync()
        for _ in range(3):
            self.supervisor.check()
            time.sleep(0.6)
        self.supervisor.check()
        for child in self.supervisor.children.values():
            self.assertGreaterEqual(child.failures, 1)
            self.assertIsNone(child.health)
            self.assertGreater(child.next_start, 0, "a wait was scheduled")
            self.assertLessEqual(child.next_start - child.started, sup.BACKOFF[-1] + 60, "and it is a bounded wait")
        waits = [c.next_start for c in self.supervisor.children.values()]
        before = time.time()
        self.supervisor.check(now=before)           # asking again at once starts nothing new while the wait lasts
        self.assertEqual([c.next_start for c in self.supervisor.children.values()], waits)

    def test_switching_an_account_off_stops_its_process_and_switching_it_on_starts_it(self):
        path = accounts.root_dir() / accounts.GLOBAL_NAME
        beta_pid = self.supervisor.child("beta").proc.pid
        path.write_text(json.dumps({"enabled_accounts": ["alpha"]}), encoding="utf-8")
        self.supervisor.sync()
        self.assertEqual(sorted(self.supervisor.children), ["alpha"])
        time.sleep(0.5)
        self.assertEqual(get(self.url + "/api/accounts")[1]["accounts"][0]["id"], "alpha")
        self.assertEqual(get(f"{self.url}/api/health?account=beta")[0], 404)
        time.sleep(1.0)
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {beta_pid}", "/NH"], capture_output=True, text=True).stdout
            self.assertNotIn(str(beta_pid), out, "the process of the account that was switched off is gone")
        else:
            with self.assertRaises(ProcessLookupError):
                os.kill(beta_pid, 0)
        path.write_text(json.dumps({"enabled_accounts": "all"}), encoding="utf-8")
        self.supervisor.sync()
        self.settle()
        self.assertEqual(get(f"{self.url}/api/health?account=beta")[1]["account"], "beta")

    def test_stopping_the_supervisor_ends_every_process_it_started(self):
        pids = [c.proc.pid for c in self.supervisor.children.values()]
        self.supervisor.stop()
        time.sleep(1.0)
        for pid in pids:
            if sys.platform == "win32":
                out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
                self.assertNotIn(str(pid), out)
            else:
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)

    def test_two_accounts_never_get_the_same_port_even_when_the_first_free_one_is_taken(self):
        busy = {c.port for c in self.supervisor.children.values()}         # the two stub children of setUp already listen on the first ports: the next supervisor must move past them
        other = sup.Supervisor(command_for=stub_command(self.base))
        other.sync()                       # it only chooses ports: nothing is started, so nothing is bound yet, which is exactly when a repeated port used to happen
        ports = [c.port for c in other.children.values()]
        self.assertEqual(len(ports), 2)
        self.assertEqual(len(set(ports)), 2, ports)
        self.assertFalse(busy & set(ports), (busy, ports))
        self.assertEqual(sup.free_port(sup.CHILD_PORT_START, taken={p for p in range(sup.CHILD_PORT_START, sup.CHILD_PORT_START + 50) if p != sup.CHILD_PORT_START + 49}), sup.CHILD_PORT_START + 49)

    def test_each_child_gets_its_own_free_port_on_the_loopback_address_only(self):
        ports = [c.port for c in self.supervisor.children.values()]
        self.assertEqual(len(set(ports)), len(ports))
        for command in (c.command for c in self.supervisor.children.values()):
            self.assertNotIn("0.0.0.0", " ".join(command))



class WebhookRouting(Running):
    """One /api/webhook for the whole installation: the event goes to the account that watches the owner of the repository."""

    def setUp(self):
        super().setUp()
        self.post = lambda owner, headers=None, account=None, host=None: get(
            self.url + "/api/webhook" + (f"?account={account}" if account else ""), method="POST", data=json.dumps({"repository": {"full_name": f"{owner}/repo", "name": "repo"}}).encode(),
            headers={"Content-Type": "application/json", "X-GitHub-Event": "workflow_run", "X-GitHub-Delivery": "abcdef12-0000", "X-Hub-Signature-256": "sha256=00", **({"Host": host} if host else {}), **(headers or {})})

    def test_the_event_goes_to_the_account_that_watches_the_owner(self):
        for owner, account in (("alpha-owner", "alpha"), ("beta-owner", "beta"), ("BETA-OWNER", "beta")):
            status, answer, _ = self.post(owner)
            self.assertEqual((status, answer["webhook_for"], answer["event"]), (202, account, "workflow_run"), owner)
            self.assertEqual(answer["signature"], "sha256=00", "the signature travels untouched: the account verifies it with its own secret")
        self.assertEqual(self.post("nobody")[0:2], (202, {"ok": True, "ignored": True}), "no account watches that owner: answered and ignored")

    def test_it_reaches_the_right_child_with_the_headers_the_signature_needs(self):
        seen = {}
        real = sup.fetch

        def spy(url, **kw):
            seen[url] = kw
            return real(url, **kw)
        with mock.patch.object(sup, "fetch", spy):
            self.post("beta-owner")
        target = [u for u in seen if u.endswith("/api/webhook")]
        self.assertEqual(len(target), 1)
        self.assertIn(":%d/" % self.supervisor.child("beta").port, target[0])
        headers = {k.lower(): v for k, v in seen[target[0]]["headers"].items()}
        for name in ("x-hub-signature-256", "x-github-event", "x-github-delivery"):
            self.assertIn(name, headers)
        self.assertNotIn("cookie", headers)
        self.assertNotIn("x-monitor-access", headers)

    def test_a_tunnel_with_its_own_host_is_not_refused_like_in_a_single_monitor_and_needs_no_token(self):
        localguard.configure(True, "127.0.0.1", "T" * 32)
        status, answer, _ = self.post("alpha-owner", host="my-tunnel.example.org", headers={"Cookie": "monitor_access=secret"})
        self.assertEqual((status, answer["webhook_for"]), (202, "alpha"), "forwarded: no Host check and no access token, the HMAC is the proof")
        self.assertIsNone(answer["cookie"], "a cookie of the session is never passed on to the account")
        self.assertEqual(get(self.url + "/api/accounts", headers={"Host": "my-tunnel.example.org"})[0], 403, "everything else keeps the guard")

    def test_the_account_can_be_named_and_a_wrong_name_is_ignored(self):
        status, answer, _ = self.post("nobody", account="beta")
        self.assertEqual((status, answer["webhook_for"]), (202, "beta"), "named by the sender: that account, whatever the owner says")
        self.assertEqual(self.post("alpha-owner", account="nope")[0:2], (202, {"ok": True, "ignored": True}))

    def test_a_body_that_is_not_json_or_has_no_repository_is_ignored_and_a_huge_one_is_refused(self):
        for body in (b"{", b"[]", b"null", b'{"repository": 5}', b'{"repository": {"full_name": 5}}', b"\xff\xfe"):
            self.assertEqual(get(self.url + "/api/webhook", method="POST", data=body, headers={"Content-Type": "application/json"})[0], 202, body)
        self.assertEqual(sup.account_of_event(b'{"repository": {"full_name": "alpha-owner/x"}}'), "alpha")
        self.assertIsNone(sup.account_of_event(b'{"repository": {"full_name": "noslash"}}'))

    def test_two_accounts_with_the_same_owner_send_the_event_to_the_first_in_order(self):
        accounts.create_account("zz-second", "alpha-owner")
        self.assertEqual(sup.account_of_event(b'{"repository": {"full_name": "alpha-owner/x"}}'), "alpha")



class TokenOfTheRightAccount(unittest.TestCase):
    """The one-use token of a change must come from the SAME account the change is sent to, or the account refuses it. The page asks for it with the account of the request."""

    def test_the_page_asks_for_the_token_of_the_account_it_posts_to(self):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("no node here: the page is checked in a browser by tools/make_screenshots.py")
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        start = page.index("(function(){const raw=window.fetch.bind(window)")
        snippet = page[start:page.index("})();", start) + 5]
        script = ("const calls=[];globalThis.window={fetch:async(u,o)=>{calls.push(String(u));return {json:async()=>({token:'T'})}}};\n" + snippet +
                  "\n(async()=>{await window.fetch('/api/settings?account=beta&lang=en',{method:'POST',headers:{}});await window.fetch('/api/settings',{method:'POST',headers:{}});"
                  "await window.fetch('/api/mode?account=org-acme',{method:'POST'});console.log(JSON.stringify(calls))})();")
        done = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        calls = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertIn("/api/session-token?account=beta", calls)
        self.assertIn("/api/session-token", calls, "without an account the token is asked as always")
        self.assertIn("/api/session-token?account=org-acme", calls)
        self.assertNotIn("/api/session-token?account=", [c for c in calls if c.endswith("account=")])



class LiveStatus(unittest.TestCase):
    """The Live view shows the receiver of webhooks: on or off, counters, the newest event. Never the secret."""

    def setUp(self):
        import actions_monitor as am
        self.am = am
        saved = dict(am.WEBHOOK_STATS), list(am.LIVE_EVENTS)
        self.addCleanup(lambda: (am.WEBHOOK_STATS.update(saved[0]), am.LIVE_EVENTS.__setitem__(slice(None), saved[1])))
        am.WEBHOOK_STATS.update(accepted=0, bad_signature=0, ignored=0, duplicates=0, refused=0, last_at=None)
        am.LIVE_EVENTS.clear()

    def test_each_answer_is_counted_in_its_own_box_and_a_closed_receiver_counts_nothing(self):
        for code, dup in ((200, False), (200, False), (401, False), (202, False), (202, True), (400, False), (413, False), (429, False), (404, False)):
            self.am.webhook_count(code, dup)
        stats = self.am.WEBHOOK_STATS
        self.assertEqual((stats["accepted"], stats["bad_signature"], stats["ignored"], stats["duplicates"], stats["refused"]), (2, 1, 1, 1, 3))
        self.assertIsNotNone(stats["last_at"])

    def test_the_status_says_on_off_or_too_short_and_never_carries_the_secret(self):
        secret = "S" * 40
        off = self.am.webhook_status({})
        self.assertEqual((off["enabled"], off["active"]), (False, False))
        short = self.am.webhook_status({"webhook": {"enabled": True, "secret": "short"}})
        self.assertEqual((short["enabled"], short["active"], short["secret_ok"]), (True, False, False))
        on = self.am.webhook_status({"webhook": {"enabled": True, "secret": secret, "live_events_keep": 50}})
        self.assertEqual((on["active"], on["secret_ok"], on["keep"], on["held"], on["last"]), (True, True, 50, 0, None))
        for status in (off, short, on):
            self.assertNotIn(secret, json.dumps(status))
            self.assertNotIn("short", json.dumps({k: v for k, v in status.items() if k != "text"}).replace("secret_ok", ""))

    def test_the_newest_event_is_named_with_only_short_fields(self):
        self.am.LIVE_EVENTS.append({"repo": "r", "name": "CI", "event": "workflow_run", "status": "completed", "conclusion": "success", "at": "2030-01-01T10:00:00Z", "title": "do not show", "actor": "x"})
        last = self.am.webhook_status({"webhook": {"enabled": True, "secret": "S" * 40}})["last"]
        self.assertEqual(sorted(last), ["at", "conclusion", "event", "name", "repo", "status"])

    def test_the_endpoint_exists_in_the_complete_edition_and_not_in_lite(self):
        self.assertIn("/api/live-status", self.am.LITE_PATHS)
        script = ("import threading, urllib.request, urllib.error\n"
                  "from http.server import ThreadingHTTPServer\n"
                  "s = ThreadingHTTPServer(('127.0.0.1', 0), am.Handler); threading.Thread(target=s.serve_forever, daemon=True).start()\n"
                  "try:\n    urllib.request.urlopen('http://127.0.0.1:%d/api/live-status' % s.server_address[1], timeout=5); print('200')\n"
                  "except urllib.error.HTTPError as e:\n    print(e.code)\n")
        done = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, %r); sys.argv = ['x', '--lite']; import actions_monitor as am; am.enable_lite(); %s" % (str(HERE), script)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.stdout.strip(), "404", done.stdout + done.stderr)


class LiteKnowsNothing(unittest.TestCase):
    """The lite edition is one account, simple. It never imports the accounts, never sees the options, and its page does not carry the switcher."""

    def run_lite(self, code):
        script = "import sys; sys.path.insert(0, %r); sys.argv = ['x', '--lite']; import actions_monitor as am; am.enable_lite(); %s" % (str(HERE), code)
        done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout.strip()

    def test_lite_never_loads_the_modules_of_the_accounts(self):
        out = self.run_lite("import threading, urllib.request\n"
                            "from http.server import ThreadingHTTPServer\n"
                            "s = ThreadingHTTPServer(('127.0.0.1', 0), am.Handler); threading.Thread(target=s.serve_forever, daemon=True).start()\n"
                            "urllib.request.urlopen('http://127.0.0.1:%d/' % s.server_address[1], timeout=8).read()\n"
                            "print([m for m in ('accounts', 'accounts_supervisor', 'account_child', 'sentinel_local') if m in sys.modules])")
        self.assertEqual(out, "[]")

    def test_the_options_of_the_accounts_are_not_in_the_help_of_lite(self):
        done = subprocess.run([sys.executable, str(HERE / "actions_monitor.py"), "--lite", "--help"], capture_output=True, text=True, timeout=60, cwd=str(HERE))
        self.assertEqual(done.returncode, 0, done.stderr)
        for option in ("--account", "--accounts", "--migrate-accounts", "--apply"):
            self.assertNotIn(option, done.stdout, option)

    def test_the_complete_edition_has_the_options_of_the_accounts_in_its_help(self):
        done = subprocess.run([sys.executable, str(HERE / "actions_monitor.py"), "--help"], capture_output=True, text=True, timeout=60, cwd=str(HERE),
                              env=dict(os.environ, MONITOR_ACCOUNTS_DIR=str(Path(tempfile.gettempdir()) / "no_such_accounts_dir")))
        self.assertEqual(done.returncode, 0, done.stderr)
        for option in ("--account", "--accounts", "--migrate-accounts"):
            self.assertIn(option, done.stdout, option)

    def test_the_page_of_one_account_has_no_data_for_the_switcher(self):
        import actions_monitor as am
        self.assertIn("/*ACCOUNTS_DATA*/null", (HERE / "actions_monitor.html").read_text(encoding="utf-8"))
        page = am.render_page()
        self.assertIn("const ACC=/*ACCOUNTS_DATA*/null;", page, "only the supervisor fills it in")

    def test_without_an_accounts_folder_the_complete_monitor_is_the_old_single_one(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(Path(tmp) / "accounts")}):
            self.assertEqual(accounts.layout(), "single")
            import actions_monitor as am
            self.assertEqual((am.CHILD["account"], am.state_dir()), ("", am.HERE))


class ChildRedirect(unittest.TestCase):
    """account_child.redirect points every state file of the monitor at the folder of ONE account, including the stores that were built with a fixed default path."""

    def test_every_state_file_and_every_default_store_lands_in_the_folder_of_the_account(self):
        code = (
            "import os, sys, tempfile\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, %r)\n"
            "t = tempfile.mkdtemp()\n"
            "os.environ['MONITOR_ACCOUNTS_DIR'] = str(Path(t) / 'accounts')\n"
            "import accounts, account_child\n"
            "accounts.create_account('alpha', 'a')\n"
            "import actions_monitor as am, etagcache, analytics, events, sentinel_ai, sentinel_local, settings_api, toolconfig\n"
            "root = Path(t) / 'accounts' / 'alpha'\n"
            "account_child.redirect('alpha')\n"
            "bad = []\n"
            "for module, attribute, relative in accounts.STATE_FILES:\n"
            "    mod = sys.modules.get(module)\n"
            "    if mod is None or root not in Path(getattr(mod, attribute)).parents: bad.append((module, attribute))\n"
            "stores = {'etag': etagcache.EtagCache().path, 'analytics': analytics.Store().path, 'events': events.Feed().events_file, 'events_state': events.Feed().state_file, 'ai': sentinel_ai.Store().path}\n"
            "bad += [name for name, path in stores.items() if root not in Path(path).parents]\n"
            "bad += [name for name, path in {'config': am.CONFIG_FILE, 'settings': settings_api.CONFIG_FILE, 'toolconfig': toolconfig.CONFIG_FILE, 'backups': settings_api.BACKUP_DIR}.items() if root not in Path(path).parents]\n"
            "print('BAD', bad)\n") % str(HERE)
        done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=90)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(done.stdout.strip().endswith("BAD []"), done.stdout)

    def test_two_accounts_never_share_a_file(self):
        names = {rel for _m, _a, rel in accounts.STATE_FILES}
        self.assertEqual(len(names), len(accounts.STATE_FILES), "every state file has its own place inside the folder of an account")
        for _module, _attribute, relative in accounts.STATE_FILES:
            self.assertFalse(Path(relative).is_absolute() or ".." in Path(relative).parts, relative)

    def test_a_child_for_an_unknown_account_refuses_to_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, "-I", str(HERE / "account_child.py"), "ghost", "--port", "1"], capture_output=True, text=True, timeout=60,
                                  env=dict(os.environ, MONITOR_ACCOUNTS_DIR=str(Path(tmp) / "accounts")))
            self.assertEqual(done.returncode, 2)
            self.assertIn("unknown account", done.stdout)


if __name__ == "__main__":
    unittest.main()
