# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The team mode (users, roles, sessions): the rules of security/auth.py and the gate of security/auth_http.py on the real server.

Off by default and then nothing changes; on, the first administrator is created from this computer once, every request needs a session, a role decides what a route may do, an account
that is not yours answers 403 (?account=, X-Account-Id), the cookie is HttpOnly and SameSite=Strict with a CSRF token on every POST, a script uses a Bearer token, a user is locked after
too many wrong passwords, and nothing secret (password, hash, token) is written to the audit."""
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
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api, toolconfig  # noqa: E402
from github_actions_monitor.security import auth, auth_http, localguard  # noqa: E402
from github_actions_monitor.storage import factory  # noqa: E402
from github_actions_monitor.accounts import accounts_supervisor as sup  # noqa: E402
from github_actions_monitor.sentinels import alert_center  # noqa: E402
import test_170 as t170  # noqa: E402

PASSWORD = "correct horse battery"
CFG = auth.settings({"auth": {"enabled": True}})


def new_storage(tmp):
    return factory.create_storage({"backend": "file", "path": str(tmp)})


class Rules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = new_storage(self.tmp.name)
        self.addCleanup(self.storage.close)
        auth.AUDIT_FILE = Path(self.tmp.name) / "audit.jsonl"
        self.addCleanup(setattr, auth, "AUDIT_FILE", None)

    def test_settings_are_off_by_default_and_a_wrong_value_reads_as_the_default(self):
        self.assertFalse(auth.settings({})["enabled"])
        self.assertFalse(auth.settings({"auth": {"enabled": "yes"}})["enabled"], "only a real true turns it on")
        self.assertEqual(auth.settings({"auth": {"session_hours": 5000, "max_failed_logins": 1, "lockout_minutes": "x"}}),
                         {**auth.settings({}), "session_hours": 12, "max_failed_logins": 5, "lockout_minutes": 15})
        self.assertFalse(auth.settings({})["allow_bearer"], "tokens for scripts are off until somebody turns them on")
        self.assertFalse(auth.settings({"auth": {"allow_bearer": "yes"}})["allow_bearer"], "only a real true turns it on")
        self.assertTrue(auth.settings({"auth": {"allow_bearer": True}})["allow_bearer"])

    def test_the_password_is_a_salted_scrypt_hash_and_never_the_text(self):
        first, second = auth.hash_password(PASSWORD), auth.hash_password(PASSWORD)
        self.assertNotEqual(first, second, "a new salt each time")
        self.assertTrue(first.startswith(("scrypt$", "pbkdf2$")))
        self.assertNotIn(PASSWORD, first)
        self.assertTrue(auth.verify_password(PASSWORD, first))
        self.assertFalse(auth.verify_password(PASSWORD + "x", first))
        for damaged in ("", "scrypt$1$2", "plain", "scrypt$99999999$8$1$AA==$AA==", "pbkdf2$1$AA==$AA=="):
            self.assertFalse(auth.verify_password(PASSWORD, damaged), damaged)

    def test_password_policy_gives_codes_and_never_echoes_the_password(self):
        self.assertEqual(auth.password_problem("", "ana", 10), "password_missing")
        self.assertEqual(auth.password_problem("short", "ana", 10), "password_short")
        self.assertEqual(auth.password_problem("aaaaaaaaaaaa", "ana", 10), "password_weak")
        self.assertEqual(auth.password_problem("x" * 300, "ana", 10), "password_too_long")
        self.assertEqual(auth.password_problem(PASSWORD, "ana", 10), "")

    def test_each_route_has_the_least_role_that_may_use_it(self):
        need = auth.required_role
        self.assertIsNone(need("GET", "/api/health"))
        self.assertIsNone(need("POST", "/api/auth/login"))
        self.assertEqual(need("GET", "/api/alerts"), "viewer")
        self.assertEqual(need("GET", "/"), "viewer")
        self.assertEqual(need("GET", "/api/github-token"), "admin")
        self.assertEqual(need("POST", "/api/alerts/mute"), "maintainer")
        self.assertEqual(need("POST", "/api/settings"), "admin")
        self.assertEqual(need("POST", "/api/ai/actions/confirm"), "admin")
        self.assertEqual(need("POST", "/api/a-route-added-later"), "admin", "an unknown write is closed until someone lists it")
        self.assertEqual(need("POST", "/api/auth/password"), "viewer")
        self.assertTrue(auth.allows("admin", "maintainer") and auth.allows("maintainer", "viewer"))
        self.assertFalse(auth.allows("viewer", "maintainer") or auth.allows("nobody", "viewer"))

    def test_the_first_administrator_is_made_once(self):
        user, code = auth.bootstrap_admin(self.storage, "Ana", PASSWORD)
        self.assertEqual((user["username"], user["role"], code), ("ana", "admin", ""))
        self.assertEqual(auth.bootstrap_admin(self.storage, "bob", PASSWORD), (None, "bootstrap_closed"))
        self.assertNotIn("hash", json.dumps(auth.list_users(self.storage)))

    def test_users_have_a_unique_valid_name_a_known_role_and_a_good_password(self):
        make = lambda *a, **k: auth.create_user(self.storage, *a, **k)  # noqa: E731
        self.assertEqual(make("ana", PASSWORD, "viewer")[1], "")
        self.assertEqual(make("ANA", PASSWORD, "viewer")[1], "user_exists")
        self.assertEqual(make("../x", PASSWORD, "viewer")[1], "username_invalid")
        self.assertEqual(make("bob", PASSWORD, "owner")[1], "role_invalid")
        self.assertEqual(make("bob", "short", "viewer")[1], "password_short")
        self.assertEqual(make("bob", PASSWORD, "viewer", ["A B"])[1], "accounts_invalid")
        self.assertEqual(auth.accounts_of(self.storage, "ana", "viewer"), ["default"], "the conservative default: the main account only")

    def test_there_is_always_an_active_admin(self):
        auth.create_user(self.storage, "root", PASSWORD, "admin")
        self.assertEqual(auth.update_user(self.storage, "root", role="viewer")[1], "last_admin")
        self.assertEqual(auth.update_user(self.storage, "root", active=False)[1], "last_admin")
        self.assertEqual(auth.delete_user(self.storage, "root"), "last_admin")
        auth.create_user(self.storage, "two", PASSWORD, "admin")
        self.assertEqual(auth.update_user(self.storage, "root", role="viewer")[1], "")
        self.assertEqual(auth.delete_user(self.storage, "nobody"), "user_unknown")

    def test_login_sessions_expire_and_a_changed_password_ends_them(self):
        auth.create_user(self.storage, "ana", PASSWORD, "viewer")
        session, code = auth.login(self.storage, "ana", PASSWORD, CFG, now=1000)
        self.assertEqual(code, "")
        self.assertNotIn(session["token"], json.dumps(self.storage.export_records()), "the token itself is never stored")
        self.assertEqual(auth.find_session(self.storage, session["token"], now=1001)["user"], "ana")
        self.assertIsNone(auth.find_session(self.storage, session["token"], now=1000 + 13 * 3600), "expired")
        self.assertIsNone(auth.find_session(self.storage, "x" * 40))
        again = auth.login(self.storage, "ana", PASSWORD, CFG, now=2000)[0]
        auth.update_user(self.storage, "ana", password="another long password")
        self.assertIsNone(auth.find_session(self.storage, again["token"], now=2001))

    def test_an_inactive_user_cannot_use_a_session_that_was_open(self):
        auth.create_user(self.storage, "root", PASSWORD, "admin")
        auth.create_user(self.storage, "ana", PASSWORD, "viewer")
        token = auth.login(self.storage, "ana", PASSWORD, CFG)[0]["token"]
        auth.update_user(self.storage, "ana", active=False)
        self.assertIsNone(auth.find_session(self.storage, token))
        self.assertEqual(auth.login(self.storage, "ana", PASSWORD, CFG), (None, "invalid_credentials"))

    def test_too_many_wrong_passwords_lock_the_user_for_a_while(self):
        auth.create_user(self.storage, "ana", PASSWORD, "viewer")
        cfg = auth.settings({"auth": {"enabled": True, "max_failed_logins": 3, "lockout_minutes": 10}})
        self.assertEqual([auth.login(self.storage, "ana", "wrong-" + str(i), cfg, now=100)[1] for i in range(3)], ["invalid_credentials", "invalid_credentials", "locked"])
        self.assertEqual(auth.login(self.storage, "ana", PASSWORD, cfg, now=101)[1], "locked", "even the right password waits")
        self.assertEqual(auth.locked_for(self.storage, "ana", now=101), 10 * 60 - 1)
        self.assertEqual(auth.login(self.storage, "ana", PASSWORD, cfg, now=100 + 601)[1], "")

    def test_an_unknown_user_gets_the_same_answer_as_a_wrong_password(self):
        auth.create_user(self.storage, "ana", PASSWORD, "viewer")
        self.assertEqual(auth.login(self.storage, "ghost", PASSWORD, CFG), (None, "invalid_credentials"))
        self.assertEqual(auth.login(self.storage, "ana", "wrong password!", CFG), (None, "invalid_credentials"))

    def test_scope_of_accounts(self):
        self.assertTrue(auth.can_see_account(["*"], "b"))
        self.assertTrue(auth.can_see_account(["a"], "a"))
        self.assertFalse(auth.can_see_account(["a"], "b"))
        self.assertFalse(auth.can_see_account([], "default"))

    def test_the_audit_records_who_and_what_but_never_a_secret(self):
        auth.audit(CFG, "login", "ana", "viewer", "127.0.0.1", "/api/auth/login?password=hunter2", "denied", "invalid_credentials")
        text = auth.audit_path().read_text(encoding="utf-8")
        self.assertIn('"user": "ana"', text)
        self.assertNotIn("hunter2", text, "the query string is cut")
        auth.audit({"audit": False}, "login", "off")
        self.assertEqual(len(auth.read_audit()), 1, "audit=false writes nothing")


class LiveTeam(unittest.TestCase):
    """The real Handler with the team mode on."""

    def start(self, config):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.leftovers = _testenv.guard(self)
        self.config_file = Path(self.tmp.name) / "actions_monitor.json"
        self.config_file.write_text(json.dumps(config), encoding="utf-8")
        saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE, dict(am.LIVE_CONFIG), dict(localguard.STATE), settings_api.BACKUP_DIR, auth.AUDIT_FILE)
        am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = self.config_file
        settings_api.BACKUP_DIR = Path(self.tmp.name) / "backups"
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, **config})
        toolconfig.forget()
        auth.AUDIT_FILE = Path(self.tmp.name) / "audit.jsonl"
        self.storage = new_storage(Path(self.tmp.name) / "data")
        auth.use_storage(self.storage)
        auth_http.forget_cache()
        localguard.reset_limits()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

        def stop():
            self.server.shutdown()
            self.server.server_close()
            am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE = saved[:3]
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(saved[3])
            localguard.STATE.clear()
            localguard.STATE.update(saved[4])
            settings_api.BACKUP_DIR, auth.AUDIT_FILE = saved[5], saved[6]
            auth.use_storage(None)
            auth_http.forget_cache()
            toolconfig.forget()
            self.storage.close()
            self.leftovers()
        self.addCleanup(stop)

    def call(self, path, body=None, headers=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, method=method or ("GET" if body is None else "POST"), headers={"Content-Type": "application/json", **(headers or {})})

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(request, timeout=8) as answer:
                raw, status, head = answer.read(), answer.status, dict(answer.headers)
        except urllib.error.HTTPError as error:
            raw, status, head = error.read(), error.code, dict(error.headers)
        return status, (json.loads(raw) if raw.startswith((b"{", b"[")) else raw.decode("utf-8", "replace")), head

    def make_admin(self):
        status, body, _ = self.call("/api/auth/bootstrap", {"username": "root", "password": PASSWORD})
        self.assertEqual(status, 200, body)

    def sign_in(self, username, password=PASSWORD, client="web"):
        status, body, head = self.call("/api/auth/login", {"username": username, "password": password, "client": client})
        self.assertEqual(status, 200, body)
        if client == "api":
            return {"Authorization": "Bearer " + body["token"]}
        cookie = head["Set-Cookie"].split(";")[0]
        return {"Cookie": cookie, "X-CSRF-Token": body["csrf"]}

    def add_user(self, admin, name, role, accounts=None):
        status, body, _ = self.call("/api/auth/users", {"username": name, "password": PASSWORD, "role": role, "accounts": accounts}, admin)
        self.assertEqual(status, 200, body)

    def test_off_by_default_the_individual_mode_is_untouched(self):
        self.start({})
        self.assertEqual(self.call("/api/health")[0], 200)
        self.assertEqual(self.call("/api/alerts")[0], 200)
        status, body, _ = self.call("/api/auth/me")
        self.assertEqual((status, body["enabled"], body["mode"], body["authenticated"]), (200, False, "individual", False))
        self.assertEqual(self.call("/api/auth/login", {"username": "a", "password": "b"})[0], 404)
        self.assertEqual(self.call("/api/auth/bootstrap", {"username": "root", "password": PASSWORD})[0], 404)
        self.assertEqual(self.call("/api/session-token")[0], 200, "the one-use token of the local page still works")

    def test_on_without_users_nothing_changes_until_the_first_admin_exists(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.assertEqual(self.call("/api/alerts")[0], 200)
        status, body, _ = self.call("/api/auth/me")
        self.assertEqual((body["mode"], body["bootstrap"]), ("individual", True))
        self.assertEqual(self.call("/api/auth/login", {"username": "root", "password": PASSWORD})[0], 401)

    def test_bootstrap_makes_one_admin_then_every_request_needs_a_session(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.assertEqual(self.call("/api/auth/bootstrap", {"username": "root", "password": "short"})[1]["code"], "password_short")
        self.make_admin()
        self.assertEqual(self.call("/api/auth/bootstrap", {"username": "x2", "password": PASSWORD})[0], 409, "closed after the first one")
        status, body, _ = self.call("/api/alerts")
        self.assertEqual((status, body["code"]), (401, "auth_required"))
        self.assertEqual(self.call("/api/health")[0], 200, "the health check is public")
        page = self.call("/", headers={"Accept": "text/html"})
        self.assertEqual((page[0], page[2].get("Location")), (302, "/login"))
        self.assertEqual(self.call("/login")[0], 200)
        self.assertNotEqual(self.call("/api/webhook", {"x": 1})[0], 401, "the webhook keeps its own HMAC proof, not a session")

    def test_a_proxy_in_front_cannot_bootstrap(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        status, body, _ = self.call("/api/auth/bootstrap", {"username": "root", "password": PASSWORD}, {"X-Forwarded-For": "203.0.113.5"})
        self.assertEqual((status, body["code"]), (403, "bootstrap_local_only"))

    def test_cookie_is_httponly_samesite_strict_and_posts_need_the_csrf_token(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        status, body, head = self.call("/api/auth/login", {"username": "root", "password": PASSWORD, "client": "web"})
        self.assertEqual(status, 200)
        cookie = head["Set-Cookie"]
        self.assertTrue(all(part in cookie for part in ("HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=")), cookie)
        self.assertNotIn("Secure", cookie, "plain HTTP on this computer")
        self.assertNotIn("token", body, "a browser gets the cookie, not the token in the body")
        jar = cookie.split(";")[0]
        self.assertEqual(self.call("/api/alerts", headers={"Cookie": jar})[0], 200)
        status, answer, _ = self.call("/api/alerts/mute", {"x": 1}, {"Cookie": jar})
        self.assertEqual((status, answer["code"]), (403, "csrf"))
        status, answer, _ = self.call("/api/alerts/mute", {"x": 1}, {"Cookie": jar, "X-CSRF-Token": "wrong"})
        self.assertEqual((status, answer["code"]), (403, "csrf"))
        self.assertNotEqual(self.call("/api/alerts/mute", {"x": 1}, {"Cookie": jar, "X-CSRF-Token": body["csrf"]})[0], 403)

    def test_the_one_use_token_of_a_post_still_applies_inside_a_session(self):
        self.start({"auth": {"enabled": True}, "session_guard": True})
        self.make_admin()
        admin = self.sign_in("root")
        status, body, _ = self.call("/api/alerts/mute", {"x": 1}, admin)
        self.assertEqual((status, body["errors"]["_"]), (403, "token"), "the session is not a replacement for the token of the page")
        token = self.call("/api/session-token", headers=admin)[1]["token"]
        self.assertNotEqual(self.call("/api/alerts/mute", {"x": 1}, {**admin, "X-Monitor-Token": token})[0], 403)

    def test_secure_cookie_over_https(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        localguard.STATE["secure"] = True
        self.assertIn("Secure", self.call("/api/auth/login", {"username": "root", "password": PASSWORD})[2]["Set-Cookie"])

    def test_roles_decide_what_each_route_may_do(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        admin = self.sign_in("root")
        self.add_user(admin, "view", "viewer")
        self.add_user(admin, "main", "maintainer")
        viewer, maintainer = self.sign_in("view"), self.sign_in("main")
        self.assertEqual(self.call("/api/alerts", headers=viewer)[0], 200)
        self.assertEqual(self.call("/api/alerts/mute", {"x": 1}, viewer)[1]["code"], "forbidden_role")
        self.assertNotEqual(self.call("/api/alerts/mute", {"x": 1}, maintainer)[0], 403, "a maintainer silences")
        self.assertEqual(self.call("/api/settings", {"values": {"refresh_seconds": 60}}, maintainer)[1]["code"], "forbidden_role")
        self.assertEqual(self.call("/api/github-token", headers=maintainer)[1]["code"], "forbidden_role")
        self.assertEqual(self.call("/api/auth/users", headers=maintainer)[0], 403)
        self.assertEqual(self.call("/api/auth/audit", headers=viewer)[0], 403)
        self.assertEqual(self.call("/api/auth/users", headers=admin)[0], 200)
        self.assertEqual(self.call("/api/auth/users", {"username": "z1", "password": PASSWORD, "role": "viewer"}, maintainer)[0], 403)
        self.assertNotEqual(self.call("/api/settings", {"values": {"refresh_seconds": 60}}, admin)[0], 403)

    def test_an_account_that_is_not_yours_is_refused_by_query_header_and_export(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        admin = self.sign_in("root")
        self.add_user(admin, "ana", "viewer", ["a"])
        ana = self.sign_in("ana")
        self.assertEqual(self.call("/api/alerts?account=a", headers=ana)[0] != 403, True)
        for path, extra in (("/api/alerts?account=b", {}), ("/api/events?account=b", {}), ("/api/alerts", {"X-Account-Id": "b"}), ("/api/outputs/dashboard.json?account=b", {}), ("/api/alerts", {})):
            status, body, _ = self.call(path, headers={**ana, **extra})
            self.assertEqual((status, body["code"]), (403, "account_scope"), path)
        self.assertNotEqual(self.call("/api/alerts?account=b", headers=admin)[0], 403, "an admin sees every account")

    def test_a_script_uses_a_bearer_token_without_csrf_and_it_can_be_turned_off(self):
        self.start({"auth": {"enabled": True, "allow_bearer": True}, "session_guard": False})
        self.make_admin()
        script = self.sign_in("root", client="api")
        self.assertEqual(self.call("/api/auth/me", headers=script)[1]["user"], "root")
        self.assertNotEqual(self.call("/api/alerts/mute", {"x": 1}, script)[0], 403)
        self.assertEqual(self.call("/api/alerts", headers={"Authorization": "Bearer msn_nothing-valid-at-all"})[0], 401)
        am.LIVE_CONFIG["auth"] = {"enabled": True, "allow_bearer": False}
        self.assertEqual(self.call("/api/auth/login", {"username": "root", "password": PASSWORD, "client": "api"})[1]["code"], "bearer_off")
        self.assertEqual(self.call("/api/alerts", headers=script)[0], 401, "a Bearer is ignored while the switch is off")

    def test_bearer_session_does_not_clash_with_the_network_access_token(self):
        localguard.configure(True, "127.0.0.1", "t" * 20)
        self.addCleanup(localguard.configure, False)
        self.assertEqual(localguard.presented({"Authorization": "Bearer msn_abc", "X-Monitor-Access": "tok"}), "tok")
        self.assertEqual(localguard.presented({"Authorization": "Bearer plain"}), "plain")

    def test_logout_ends_the_session_and_the_error_is_stable_json(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        admin = self.sign_in("root")
        self.assertEqual(self.call("/api/auth/logout", {}, admin)[0], 200)
        status, body, _ = self.call("/api/alerts", headers=admin)
        self.assertEqual((status, sorted(body)), (401, ["code", "error", "ok"]))
        self.assertEqual(self.call("/api/auth/login", {"bad": 1})[0], 401)

    def test_wrong_passwords_lock_the_user_and_nothing_secret_reaches_the_audit(self):
        self.start({"auth": {"enabled": True, "max_failed_logins": 3, "lockout_minutes": 5}, "session_guard": False})
        self.make_admin()
        codes = [self.call("/api/auth/login", {"username": "root", "password": f"wrong guess {i}"})[1]["code"] for i in range(3)]
        self.assertEqual(codes, ["invalid_credentials", "invalid_credentials", "locked"])
        status, body, head = self.call("/api/auth/login", {"username": "root", "password": PASSWORD})
        self.assertEqual((status, body["code"]), (429, "locked"))
        self.assertGreater(int(head["Retry-After"]), 0)
        text = auth.audit_path().read_text(encoding="utf-8")
        for secret in (PASSWORD, "wrong guess", "scrypt$"):
            self.assertNotIn(secret, text)
        self.assertIn('"action": "login"', text)

    def test_one_address_cannot_try_without_end(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        for i in range(70):
            status = self.call("/api/auth/login", {"username": f"ghost{i}", "password": "nope nope nope"})[0]
        self.assertEqual(status, 429)

    def test_own_password_change_revokes_the_other_sessions(self):
        self.start({"auth": {"enabled": True, "allow_bearer": True}, "session_guard": False})
        self.make_admin()
        first, second = self.sign_in("root"), self.sign_in("root", client="api")
        new = "a brand new password"
        self.assertEqual(self.call("/api/auth/password", {"current": "not the password", "new": new}, first)[0], 403)
        self.assertEqual(self.call("/api/auth/password", {"current": PASSWORD, "new": new}, first)[0], 200)
        self.assertEqual(self.call("/api/alerts", headers=first)[0], 200, "this session stays")
        self.assertEqual(self.call("/api/alerts", headers=second)[0], 401)

    def test_user_management_rules(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        admin = self.sign_in("root")
        self.add_user(admin, "ana", "viewer")
        self.assertEqual(self.call("/api/auth/users", {"username": "ana", "password": PASSWORD, "role": "viewer"}, admin)[1]["code"], "user_exists")
        self.assertEqual(self.call("/api/auth/users/update", {"username": "root", "role": "viewer"}, admin)[1]["code"], "last_admin")
        self.assertEqual(self.call("/api/auth/users/delete", {"username": "root"}, admin)[1]["code"], "last_admin")
        ana = self.sign_in("ana")
        self.assertEqual(self.call("/api/auth/users/revoke", {"username": "ana"}, admin)[1]["revoked"], 1)
        self.assertEqual(self.call("/api/alerts", headers=ana)[0], 401)
        self.assertEqual(self.call("/api/auth/users/update", {"username": "ana", "role": "maintainer"}, admin)[0], 200)
        self.assertEqual(self.call("/api/auth/users/delete", {"username": "ana"}, admin)[0], 200)
        self.assertEqual(self.call("/api/auth/users/delete", {"username": "ana"}, admin)[0], 404)
        users = self.call("/api/auth/users", headers=admin)[1]["users"]
        self.assertEqual([u["username"] for u in users], ["root"])
        self.assertNotIn("hash", json.dumps(users))

    def test_lite_never_has_a_login(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        saved = am.LITE["on"]
        am.LITE["on"] = True
        self.addCleanup(am.LITE.__setitem__, "on", saved)
        self.assertEqual(self.call("/api/ai/state")[0], 200)
        self.assertEqual(self.call("/api/auth/me")[0], 404, "the lite edition has no login endpoints at all")

    def test_the_login_page_speaks_the_eight_languages(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                page = auth_http.login_page()
            self.assertIn(i18n.tl(lang, "auth.sign_in"), page)
            self.assertNotIn("auth.sign_in", page, lang)
            self.assertNotEqual(i18n.tl(lang, "cfg.h.auth.enabled"), "cfg.h.auth.enabled", lang)

    def test_the_silence_keeps_who_made_it_and_the_alert_list_says_it(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        from unittest import mock
        patch = mock.patch.object(alert_center, "STATE_FILE", Path(self.tmp.name) / "alert_mutes.json")
        patch.start()
        self.addCleanup(patch.stop)
        self.make_admin()
        admin = self.sign_in("root")
        self.add_user(admin, "main", "maintainer")
        main = self.sign_in("main")
        status, body, _ = self.call("/api/alerts/mute", {"scope": "code", "value": "ci.stuck", "hours": 2}, main)
        self.assertEqual((status, body["ok"], body["mute"]["who"]), (200, True, "main"))
        live = alert_center.active()
        self.assertEqual(alert_center.muted_by({"code": "ci.stuck"}, live), "main")
        self.assertEqual(alert_center.muted_by({"code": "other"}, live), "")
        self.assertEqual(alert_center.history()[0]["who"], "main")

    def test_in_the_individual_mode_nobody_is_named(self):
        self.start({"session_guard": False})
        from unittest import mock
        patch = mock.patch.object(alert_center, "STATE_FILE", Path(self.tmp.name) / "alert_mutes.json")
        patch.start()
        self.addCleanup(patch.stop)
        self.assertEqual(self.call("/api/alerts/mute", {"scope": "code", "value": "ci.stuck"})[1]["mute"]["who"], "")


class TeamSupervisor(t170.Running):
    """The supervisor with several accounts: each user lists and reaches only the accounts assigned to them."""

    def setUp(self):
        from unittest import mock
        stub = t170.STUB.replace('"token": self.headers.get("X-Monitor-Token")}', '"token": self.headers.get("X-Monitor-Token"), "user": self.headers.get("X-Monitor-User")}').replace(
            '"host": self.headers.get("Host")})', '"host": self.headers.get("Host"), "user": self.headers.get("X-Monitor-User")})')
        for patcher in (mock.patch.object(t170, "STUB", stub), mock.patch.object(sup.Handler, "team_config", staticmethod(lambda: {"auth": {"enabled": True}, "session_guard": False}))):
            patcher.start()
            self.addCleanup(patcher.stop)
        super().setUp()
        self.tmp2 = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp2.cleanup)
        self.storage = new_storage(self.tmp2.name)
        auth.use_storage(self.storage)
        auth.AUDIT_FILE = Path(self.tmp2.name) / "audit.jsonl"
        auth_http.forget_cache()
        localguard.reset_limits()

        def undo():
            auth.use_storage(None)
            auth.AUDIT_FILE = None
            auth_http.forget_cache()
            self.storage.close()
        self.addCleanup(undo)
        auth.create_user(self.storage, "root", PASSWORD, "admin")
        auth.create_user(self.storage, "ana", PASSWORD, "maintainer", ["alpha"])
        auth.create_user(self.storage, "bob", PASSWORD, "viewer", ["beta"])
        auth_http.forget_cache()

    def sign(self, name):
        status, body, head = t170.get(self.url + "/api/auth/login", headers={"Content-Type": "application/json"}, data=json.dumps({"username": name, "password": PASSWORD}).encode())
        self.assertEqual(status, 200, body)
        return {"Cookie": head["Set-Cookie"].split(";")[0], "X-CSRF-Token": body["csrf"]}

    def test_the_list_and_the_status_show_only_the_accounts_of_the_user(self):
        for name, expected in (("root", ["alpha", "beta"]), ("ana", ["alpha"]), ("bob", ["beta"])):
            headers = self.sign(name)
            self.assertEqual([a["id"] for a in t170.get(self.url + "/api/accounts", headers)[1]["accounts"]], expected, name)
        ana = self.sign("ana")
        self.assertEqual(t170.get(self.url + "/api/accounts/alpha/status", ana)[0], 200)
        status, body, _ = t170.get(self.url + "/api/accounts/beta/status", ana)
        self.assertEqual((status, body["code"]), (403, "account_scope"))
        self.assertEqual(t170.get(self.url + "/api/accounts/beta/status", self.sign("root"))[0], 200)
        self.assertEqual(t170.get(self.url + "/api/accounts")[0], 401, "without a session nothing is listed")

    def test_a_request_for_another_account_never_reaches_its_monitor(self):
        ana = self.sign("ana")
        self.assertEqual(t170.get(self.url + "/api/echo?account=alpha", ana)[1]["account"], "alpha")
        for path, extra in (("/api/echo?account=beta", {}), ("/api/echo", {"X-Account-Id": "beta"})):
            status, body, _ = t170.get(self.url + path, {**ana, **extra})
            self.assertEqual((status, body["code"]), (403, "account_scope"), path)

    def test_the_page_lists_only_the_accounts_of_the_user(self):
        page = t170.get(self.url + "/?account=alpha", {**self.sign("ana"), "Accept": "text/html"})[1]
        self.assertIn('"accounts": ["alpha"]', page)

    def test_the_monitor_of_an_account_is_told_who_acts_and_a_forged_name_is_dropped(self):
        ana = {**self.sign("ana"), "Content-Type": "application/json", "X-Monitor-User": "root"}
        status, body, _ = t170.get(self.url + "/api/alerts/mute?account=alpha", ana, data=b"{}")
        self.assertEqual((status, body.get("user")), (200, "ana"), body)


class Recovery(unittest.TestCase):
    def test_the_console_makes_an_admin_resets_a_password_and_never_prints_a_secret(self):
        import contextlib
        import io
        import os
        from unittest import mock
        from github_actions_monitor.security import auth_cli
        with tempfile.TemporaryDirectory() as tmp:
            storage = new_storage(tmp)
            auth.AUDIT_FILE = Path(tmp) / "audit.jsonl"
            self.addCleanup(setattr, auth, "AUDIT_FILE", None)
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"MON_TEST_PW": PASSWORD}), contextlib.redirect_stdout(out):
                self.assertEqual(auth_cli.main(["create-admin", "Root", "--password-env", "MON_TEST_PW"], storage), 0)
                self.assertEqual(auth_cli.main(["create-admin", "root", "--password-env", "MON_TEST_PW"], storage), 1)
            with mock.patch.dict(os.environ, {"MON_TEST_PW": "a second long password"}), contextlib.redirect_stdout(out):
                self.assertEqual(auth_cli.main(["reset-password", "root", "--password-env", "MON_TEST_PW"], storage), 0)
                self.assertEqual(auth_cli.main(["list"], storage), 0)
                self.assertEqual(auth_cli.main(["revoke", "root"], storage), 0)
            self.assertIsNotNone(auth.login(storage, "root", "a second long password", CFG)[0])
            self.assertIsNone(auth.login(storage, "root", PASSWORD, CFG)[0])
            shown = out.getvalue() + auth.audit_path().read_text(encoding="utf-8")
            for secret in (PASSWORD, "a second long password", "scrypt$"):
                self.assertNotIn(secret, shown)
            storage.close()


class Wiring(unittest.TestCase):
    def test_settings_defaults_example_and_help_exist(self):
        keys = ("enabled", "session_hours", "max_failed_logins", "lockout_minutes", "min_length", "allow_bearer", "audit")
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(am.DEFAULTS["auth"]), sorted(keys))
        self.assertEqual(sorted(example["auth"]), sorted(keys))
        self.assertIs(am.DEFAULTS["auth"]["enabled"], False)
        for key in keys:
            self.assertIn("auth." + key, settings_api.META)
            self.assertTrue(settings_api.META["auth." + key]["secure"], "a security option is local-only on the network")
            self.assertTrue(localguard.local_only_key("auth." + key))
            for lang in i18n.LANGS:
                for prefix in ("cfg.f.", "cfg.h."):
                    self.assertNotEqual(i18n.tl(lang, prefix + "auth." + key), prefix + "auth." + key, (lang, key))
        for lang in i18n.LANGS:
            self.assertNotEqual(i18n.tl(lang, "ui.cfg_b_auth"), "ui.cfg_b_auth", lang)

    def test_the_account_children_do_not_ask_for_a_second_login(self):
        import os
        from unittest import mock
        handler = mock.Mock(path="/api/alerts", command="GET", headers={auth_http.SUPERVISOR_KEY_HEADER: "key-of-the-supervisor"})
        with mock.patch.dict(os.environ, {auth_http.CHILD_ENV: "1", auth_http.SUPERVISOR_KEY_ENV: "key-of-the-supervisor"}):
            self.assertTrue(auth_http.gate(handler, {"auth": {"enabled": True}}))
        self.assertTrue(auth_http.gate(handler, {"auth": {"enabled": True}}, lite=True))


if __name__ == "__main__":
    unittest.main()
