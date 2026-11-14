# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The supervisor as a service: the deep health check, a blind account that does not touch the others, the administrator endpoint to replace a login, SIGHUP, and the network mode (access token,
cookie, the second port of the person at the computer, the keys that stay with that computer)."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.accounts import accounts, accounts_supervisor as sup  # noqa: E402
from github_actions_monitor.security import auth, auth_http, localguard  # noqa: E402

STUB = r'''
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
account, port, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
KEY = os.environ.get("MONITOR_SUPERVISOR_KEY", "")
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            cred = {"state": "blind", "reason": "revoked", "since": 1} if mode == "blind" else {"state": "ok", "reason": ""}
            ok = mode != "stuck"
            return self.send(200 if ok else 503, {"ok": ok, "version": "9.9.9", "loaded": True, "offline": False, "account": account, "credential": cred, "cycle": {"stuck": not ok}})
        if path == "/api/data": return self.send(200, {"data": {"owner": account, "repos": [], "active": [], "failing": [], "figures": {}, "rate": {}}})
        if path == "/api/echo": return self.send(200, {"account": account, "remote": self.headers.get("X-Monitor-Remote"), "supervisor": self.headers.get("X-Monitor-Supervisor")})
        self.send(404, {})
    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0); body = json.loads(self.rfile.read(size) or b"{}")
        if self.path.split("?")[0] == "/api/credential":
            if not KEY or self.headers.get("X-Monitor-Supervisor") != KEY: return self.send(403, {"ok": False, "status": "forbidden"})
            if body.get("action") == "replace" and body.get("token") == "ghp_" + "R" * 36: return self.send(422, {"ok": False, "status": "rejected"})
            return self.send(200, {"ok": True, "status": "saved" if body.get("action") == "replace" else "reloaded", "seen": body})
        self.send(200, {"account": account, "got": body})
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
'''


def stub_command(folder, modes):
    path = Path(folder) / "stub182.py"
    path.write_text(STUB, encoding="utf-8")
    return lambda account_id, port: [sys.executable, "-I", str(path), account_id, str(port), modes.get(account_id, "ok")]


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


def free_stretch():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1] + 20


class Running(unittest.TestCase):
    modes = {"alpha": "ok", "beta": "ok"}
    handler = sup.Handler

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(self.base / "accounts")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in self.modes:
            accounts.create_account(name, name + "-owner")
        self.supervisor = sup.Supervisor(command_for=stub_command(self.base, self.modes), port_start=free_stretch())
        self.addCleanup(self.supervisor.stop)
        self.supervisor.sync()
        for _ in range(60):
            self.supervisor.check()
            if all(c.health is not None for c in self.supervisor.children.values()):
                break
            time.sleep(0.25)
        sup.SUPERVISOR["obj"] = self.supervisor
        self.addCleanup(lambda: sup.SUPERVISOR.update(obj=None))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close()))
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.addCleanup(localguard.configure, False)
        self.addCleanup(localguard.reset_limits)

    def post(self, path, payload, headers=None):
        return get(self.url + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})}, method="POST")


class BlindAccount(Running):
    modes = {"alpha": "blind", "beta": "ok"}

    def test_only_that_account_is_blind_in_the_summary(self):
        states = {a["id"]: a["state"] for a in get(self.url + "/api/accounts")[1]["accounts"]}
        self.assertEqual(states, {"alpha": "blind", "beta": "ok"})
        alpha = next(a for a in get(self.url + "/api/accounts")[1]["accounts"] if a["id"] == "alpha")
        self.assertEqual(alpha["credential"]["reason"], "revoked")

    def test_the_deep_health_check_stays_green_and_names_the_blind_account(self):
        status, answer, _ = get(self.url + "/api/health?deep=1")
        self.assertEqual(status, 200)
        self.assertEqual((answer["ok"], answer["blind"], answer["states"]), (True, ["alpha"], {"alpha": "blind", "beta": "ok"}))

    def test_the_other_account_goes_on_answering(self):
        self.assertEqual(get(self.url + "/api/echo?account=beta")[1]["account"], "beta")


class StuckAccount(Running):
    modes = {"alpha": "ok", "beta": "stuck"}

    def test_a_stuck_cycle_of_one_account_fails_the_deep_check_with_a_503(self):
        status, answer, _ = get(self.url + "/api/health?deep=1")
        self.assertEqual(status, 503)
        self.assertEqual((answer["ok"], answer["problems"]), (False, [{"id": "beta", "state": "stuck"}]))
        self.assertEqual(next(a for a in get(self.url + "/api/accounts")[1]["accounts"] if a["id"] == "beta")["state"], "stuck")

    def test_the_shallow_check_does_not_fail(self):
        self.assertEqual(get(self.url + "/api/health")[0], 200)


class Deep(Running):
    def test_healthy(self):
        status, answer, _ = get(self.url + "/api/health?deep=1")
        self.assertEqual((status, answer["ok"], answer["stale"], answer["problems"]), (200, True, False, []))

    def test_a_supervision_loop_that_stopped_turning_fails_it(self):
        self.supervisor.beat = time.time() - sup.STALE_AFTER - 5
        status, answer, _ = get(self.url + "/api/health?deep=1")
        self.assertEqual((status, answer["stale"], answer["ok"]), (503, True, False))

    def test_not_one_account_answering_after_the_grace_fails_it_and_before_the_grace_does_not(self):
        for child in self.supervisor.children.values():
            child.health = None
        ok, _ = self.supervisor.deep_health(now=time.time())
        self.assertTrue(ok, "still inside the start grace")
        ok, document = self.supervisor.deep_health(now=time.time() + sup.START_GRACE + 10)
        self.assertFalse(ok)
        self.assertEqual(sorted(p["state"] for p in document["problems"]), ["down", "down"])

    def test_the_listening_word_is_in_the_summary_and_the_shallow_health(self):
        self.assertEqual(get(self.url + "/api/accounts")[1]["listening"], "this_computer")
        self.assertEqual(get(self.url + "/api/health")[1]["listening"], "this_computer")


class Credential(Running):
    def test_replace_goes_to_that_account_only_with_the_key_of_the_supervisor(self):
        status, answer, _ = self.post("/api/accounts/alpha/credential", {"action": "replace", "token": "ghp_" + "N" * 36})
        self.assertEqual((status, answer["ok"], answer["status"]), (200, True, "saved"))
        self.assertEqual(answer["seen"]["action"], "replace")

    def test_a_token_that_github_refuses_comes_back_as_not_done(self):
        status, answer, _ = self.post("/api/accounts/alpha/credential", {"action": "replace", "token": "ghp_" + "R" * 36})
        self.assertEqual((status, answer["status"]), (422, "rejected"))

    def test_reload_and_the_requests_that_are_wrong(self):
        self.assertEqual(self.post("/api/accounts/beta/credential", {"action": "reload"})[1]["status"], "reloaded")
        self.assertEqual(self.post("/api/accounts/alpha/credential", {"action": "delete"})[0], 400)
        self.assertEqual(self.post("/api/accounts/alpha/credential", {"action": "replace"})[0], 400)
        self.assertEqual(self.post("/api/accounts/nobody/credential", {"action": "reload"})[0], 404)
        self.assertEqual(self.post("/api/accounts/..%2Fx/credential", {"action": "reload"})[0], 404)

    def test_reload_all_is_what_sighup_does(self):
        self.assertEqual(self.supervisor.reload_credentials(), {"alpha": "reloaded", "beta": "reloaded"})

    def test_the_key_is_not_known_to_anybody_else_and_the_client_cannot_send_it_on(self):
        child = self.supervisor.child("alpha")
        status, _, _ = get(child.url("/api/credential"), data=b"{}", headers={"Content-Type": "application/json", "X-Monitor-Supervisor": "guess"}, method="POST")
        self.assertEqual(status, 403)
        answer = get(self.url + "/api/echo?account=alpha", headers={"X-Monitor-Supervisor": self.supervisor.key, "X-Monitor-Remote": "1"})[1]
        self.assertIsNone(answer["supervisor"])
        self.assertIsNone(answer["remote"], "a client cannot say it is remote or the supervisor")

    def test_the_key_is_given_to_every_account_process(self):
        self.assertTrue(all(c.key == self.supervisor.key for c in self.supervisor.children.values()))
        self.assertGreaterEqual(len(self.supervisor.key), 32)

    def test_nothing_in_the_answer_repeats_the_token(self):
        token = "ghp_" + "N" * 36
        self.assertNotIn(token, json.dumps(self.post("/api/accounts/alpha/credential", {"action": "replace", "token": token})[1]).replace('"token": "' + token + '"', ""))


class Network(Running):
    """The network mode of the supervisor: the access token, the lock, the cookie of the first visit, and what stays with the computer of the monitor."""

    def setUp(self):
        super().setUp()
        localguard.configure(True, "127.0.0.1", "T" * 32)
        self.t = {"X-Monitor-Access": "T" * 32}

    def test_every_request_needs_the_token_including_the_deep_health_check(self):
        for path in ("/api/accounts", "/api/health?deep=1", "/api/health"):
            self.assertEqual(get(self.url + path)[0], 401, path)
            self.assertEqual(get(self.url + path, headers=self.t)[0], 200, path)

    def test_the_session_is_opened_with_the_token_in_the_body_and_the_cookie_comes_back(self):
        status, answer, headers = self.post("/api/access", {"token": "T" * 32})
        self.assertEqual((status, answer), (200, {"ok": True}))
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertEqual(self.post("/api/access", {"token": "wrong"})[0], 401)
        cookie = headers["Set-Cookie"].split(";")[0]
        self.assertEqual(get(self.url + "/api/accounts", headers={"Cookie": cookie})[0], 200)

    def test_without_the_network_mode_there_is_nothing_to_open(self):
        localguard.configure(False)
        self.assertEqual(self.post("/api/access", {"token": "x"})[0], 404)

    def test_the_first_visit_of_a_page_with_the_token_in_the_address_gets_the_cookie_and_a_clean_address(self):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(self.url + "/?access=" + "T" * 32, headers={"Accept": "text/html"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            opener.open(request, timeout=10)
        self.assertEqual(caught.exception.code, 302)
        self.assertEqual(caught.exception.headers["Location"], "/")
        self.assertIn("monitor_access=", caught.exception.headers["Set-Cookie"])
        caught.exception.close()

    def test_wrong_tokens_lock_an_address_that_is_not_this_computer_not_this_computer_itself(self):
        # a request from this computer is never locked out of its own monitor (the same rule as a single monitor)
        for _ in range(15):
            get(self.url + "/api/accounts", headers={"X-Monitor-Access": "wrong"})
        self.assertEqual(get(self.url + "/api/accounts", headers=self.t)[0], 200)

    def test_a_request_of_a_client_of_the_network_is_marked_remote_for_the_account(self):
        with mock.patch.object(sup.Handler, "this_computer", return_value=False):
            self.assertEqual(get(self.url + "/api/echo?account=alpha", headers=self.t)[1]["remote"], "1")
        self.assertIsNone(get(self.url + "/api/echo?account=alpha", headers=self.t)[1]["remote"], "the person at this computer is not marked")

    def test_replacing_a_login_without_a_team_is_for_the_computer_of_the_monitor_only(self):
        with mock.patch.object(sup.Handler, "this_computer", return_value=False):
            status, answer, _ = self.post("/api/accounts/alpha/credential", {"action": "reload"}, self.t)
        self.assertEqual((status, answer["status"]), (403, "local_only"))
        self.assertEqual(self.post("/api/accounts/alpha/credential", {"action": "reload"}, self.t)[0], 200)

    def test_the_listening_word_says_network_and_then_proxy_when_a_proxy_is_declared(self):
        self.assertEqual(get(self.url + "/api/accounts", headers=self.t)[1]["listening"], "network")
        self.assertEqual(localguard.listening()["mode"], "network")
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host="monitor.example.org")
        self.assertEqual(localguard.listening(), {"mode": "proxy", "host": "127.0.0.1", "secure": True, "token_required": True})
        localguard.configure(False)
        self.assertEqual(localguard.listening()["mode"], "this_computer")
        self.assertEqual(localguard.public_state()["mode"], "this_computer")


class DoorServer(Running):
    handler = sup.DoorHandler

    def test_the_second_port_lets_the_person_at_the_computer_in_even_behind_a_proxy(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host="monitor.example.org")
        headers = {"X-Monitor-Access": "T" * 32}
        self.assertEqual(self.post("/api/accounts/alpha/credential", {"action": "reload"}, headers)[0], 200)
        main = sup.Handler
        with mock.patch.object(self.server, "RequestHandlerClass", main):
            pass
        self.assertTrue(main.door is False and sup.DoorHandler.door is True)


class Admin(Running):
    """The team mode: the credential endpoint needs an administrator (an unlisted POST is closed to everybody else)."""

    def test_the_role_for_the_endpoint_is_admin(self):
        self.assertEqual(auth.required_role("POST", "/api/accounts/alpha/credential"), "admin")
        self.assertEqual(auth.required_role("POST", "/api/credential"), "admin")

    def test_a_viewer_or_a_maintainer_cannot_and_an_admin_can(self):
        self.assertFalse(auth.allows("viewer", "admin"))
        self.assertFalse(auth.allows("maintainer", "admin"))
        self.assertTrue(auth.allows("admin", "admin"))

    def test_the_audit_line_of_a_replacement_has_no_token(self):
        lines = []
        with mock.patch.object(auth, "audit", side_effect=lambda cfg, *a, **k: lines.append(a)):
            handler = sup.Handler.__new__(sup.Handler)
            handler.auth_user = {"user": "root", "role": "admin"}
            handler.client_address = ("127.0.0.1", 1)
            handler.headers = {}
            handler.path = "/api/accounts/alpha/credential"
            handler.rfile = mock.Mock(read=lambda n: json.dumps({"action": "reload"}).encode())
            handler.headers = {"Content-Length": "19", "Host": "x"}
            handler.json = lambda payload, code=200: None
            handler.team_config = lambda: {}
            handler.this_computer = lambda: True
            handler.credential(self.supervisor, "alpha")
        self.assertTrue(lines)
        self.assertNotIn("ghp_", json.dumps(lines))


class InjectedClock(unittest.TestCase):
    """The wait before an account is started again is computed from the clock the caller gives, so no test depends on how fast the computer is."""

    def test_the_wait_after_a_death_grows_with_each_failure_and_is_the_same_whatever_the_real_time(self):
        supervisor = sup.Supervisor()
        child = sup.Child("alpha", 18999, [sys.executable, "-c", "pass"])
        supervisor.children["alpha"] = child
        for failures, expected in ((1, sup.BACKOFF[0]), (2, sup.BACKOFF[1]), (len(sup.BACKOFF) + 3, sup.BACKOFF[-1])):
            child.proc = mock.Mock(poll=mock.Mock(return_value=1))
            child.failures, child.started, child.next_start = failures - 1, 0.0, 10 ** 12
            with mock.patch.object(sup.time, "time", side_effect=AssertionError("the real clock must not be read")):
                supervisor.check(now=1000.0)
            self.assertEqual((child.failures, child.next_start), (failures, 1000.0 + expected))
            self.assertIsNone(child.proc)


if __name__ == "__main__":
    unittest.main()
