# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.6: the same-origin guard under HTTPS (direct TLS and a proxy), the exposure keys of the network mode taken from the schema, the local run of `act` that frees
itself after a Stop and closes its pipe, the visible warning for the network mode on every interface, the one-use session post and the counter of silent failures."""
import hashlib
import http.client
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import warnings
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.integrations import actlocal  # noqa: E402
from github_actions_monitor.security import localguard  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402
from test_164 import LiveServer  # noqa: E402


# --- the same-origin guard follows the scheme of the session ------------------------------------------------------------------------------------------------------------------------------
class OriginFollowsTheScheme(unittest.TestCase):
    def tearDown(self):
        localguard.configure(False)

    def headers(self, origin=None, host="127.0.0.1:8765"):
        out = {"Host": host}
        if origin is not None:
            out["Origin"] = origin
        return out

    def test_http_session_accepts_an_http_origin(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=False)
        self.assertTrue(localguard.local_request_ok(self.headers("http://127.0.0.1:8765"), 8765))
        self.assertTrue(localguard.local_request_ok(self.headers(), 8765))

    def test_https_session_accepts_an_https_origin(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True)
        self.assertTrue(localguard.local_request_ok(self.headers("https://127.0.0.1:8765"), 8765))
        self.assertTrue(localguard.local_request_ok(self.headers("HTTPS://LOCALHOST:8765", host="localhost:8765"), 8765))

    def test_https_session_refuses_an_http_origin(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True)
        self.assertFalse(localguard.local_request_ok(self.headers("http://127.0.0.1:8765"), 8765))

    def test_http_session_refuses_an_https_origin(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=False)
        self.assertFalse(localguard.local_request_ok(self.headers("https://127.0.0.1:8765"), 8765))

    def test_a_foreign_host_port_or_malformed_origin_is_refused(self):
        for secure, scheme in ((False, "http"), (True, "https")):
            localguard.configure(True, "127.0.0.1", "T" * 32, secure=secure)
            for origin in (f"{scheme}://evil.example:8765", f"{scheme}://127.0.0.1:9999", f"{scheme}://127.0.0.1", f"{scheme}://127.0.0.1:8765/path", f"{scheme}://127.0.0.1:8765@evil.example",
                           "null", "", f"{scheme}:127.0.0.1:8765", f"{scheme}://127.0.0.1:8765 "):
                self.assertFalse(localguard.local_request_ok(self.headers(origin), 8765), (secure, origin))
            self.assertFalse(localguard.local_request_ok(self.headers(f"{scheme}://127.0.0.1:8765", host="evil.example:8765"), 8765))
            self.assertFalse(localguard.local_request_ok(self.headers(f"{scheme}://127.0.0.1:8765", host="127.0.0.1:9999"), 8765))

    def test_the_loopback_mode_is_http(self):
        localguard.configure(False)
        self.assertTrue(localguard.local_request_ok(self.headers("http://127.0.0.1:8765"), 8765))
        self.assertFalse(localguard.local_request_ok(self.headers("https://127.0.0.1:8765"), 8765))


def make_certificate(folder):
    """A self-signed certificate for 127.0.0.1 made with the `openssl` program of the machine (nothing is stored in the repository), or (None, None) when there is none."""
    binary = shutil.which("openssl")
    if not binary:
        return None, None
    cert, key = Path(folder) / "cert.pem", Path(folder) / "key.pem"
    conf = Path(folder) / "req.cnf"      # our own minimal configuration: a broken OPENSSL_CONF of the machine must not matter
    conf.write_text("\n".join(["[req]", "distinguished_name=dn", "prompt=no", "x509_extensions=v3", "[dn]", "CN=127.0.0.1", "[v3]", "subjectAltName=IP:127.0.0.1", ""]), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "OPENSSL_CONF"}
    done = subprocess.run([binary, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cert), "-days", "2", "-config", str(conf)],
                          capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, env=env)
    return (str(cert), str(key)) if done.returncode == 0 and cert.exists() and key.exists() else (None, None)


class DirectTlsPost(unittest.TestCase):
    """A real server with direct TLS: the same-origin POST of the page must reach the settings (the browser sends `Origin: https://host:port`)."""

    def test_a_same_origin_post_reaches_the_settings_under_tls(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cert, key = make_certificate(tmp.name)
        if cert is None:
            self.skipTest("no `openssl` program here: the check by hand is in tools/manual_check_live.py (tls)")
        access = "T" * 24
        config_file = Path(tmp.name) / "actions_monitor.json"
        config_file.write_text("{}", encoding="utf-8")
        saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE, dict(am.LIVE_CONFIG), dict(localguard.STATE), settings_api.BACKUP_DIR, set(am.RESTART_PENDING))

        def restore():
            am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE = saved[:3]
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(saved[3])
            localguard.STATE.clear()
            localguard.STATE.update(saved[4])
            settings_api.BACKUP_DIR = saved[5]
            am.RESTART_PENDING.clear()
            am.RESTART_PENDING.update(saved[6])
            toolconfig.forget()
        self.addCleanup(restore)
        am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = config_file
        settings_api.BACKUP_DIR = Path(tmp.name) / "backups"
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, "session_guard": True})
        toolconfig.forget()
        localguard.configure(True, "127.0.0.1", access, secure=True)
        server = am.QuietServer(("127.0.0.1", 0), am.Handler)
        server.tls_context = localguard.tls_context(cert, key)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        port = server.server_address[1]
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        def call(method, path, body=None, extra=None):
            connection = http.client.HTTPSConnection("127.0.0.1", port, context=context, timeout=15)
            try:
                headers = {"X-Monitor-Access": access, "Content-Type": "application/json", **(extra or {})}
                connection.request(method, path, None if body is None else json.dumps(body), headers)
                answer = connection.getresponse()
                raw = answer.read()
                return answer.status, (json.loads(raw) if raw.startswith(b"{") else raw)
            finally:
                connection.close()
        origin = {"Origin": f"https://127.0.0.1:{port}"}
        token = call("GET", "/api/session-token", extra=origin)[1]["token"]
        status, answer = call("POST", "/api/settings", {"changes": {"refresh_seconds": 61}}, {**origin, "X-Monitor-Token": token})
        self.assertEqual(status, 200, answer)
        token = call("GET", "/api/session-token", extra=origin)[1]["token"]
        status, _ = call("POST", "/api/settings", {"changes": {"refresh_seconds": 62}}, {"Origin": f"http://127.0.0.1:{port}", "X-Monitor-Token": token})
        self.assertEqual(status, 403, "an http origin on an https session stays refused")


# --- the exposure keys come from the schema ------------------------------------------------------------------------------------------------------------------------------------------
class ExposureKeysFromTheSchema(unittest.TestCase):
    def test_every_secure_key_needs_this_computer_in_network_mode(self):
        secure = sorted(k for k, meta in settings_api.META.items() if meta["secure"])
        self.assertGreater(len(secure), 30)
        access = "T" * 24
        with LiveServer({"session_guard": True}, network=access) as server:
            headers = {"X-Monitor-Access": access}
            with mock.patch.object(localguard, "from_this_computer", return_value=False):
                for key in secure:
                    token = server.call("/api/session-token", headers=headers)[1]["token"]
                    status, answer = server.call("/api/settings", {"changes": {key: True}}, {**headers, "X-Monitor-Token": token})
                    self.assertEqual((status, answer["errors"]["_"]), (403, "local_only"), key)
                token = server.call("/api/session-token", headers=headers)[1]["token"]
                self.assertEqual(server.call("/api/settings", {"changes": {"refresh_seconds": 77}}, {**headers, "X-Monitor-Token": token})[0], 200, "a key that is not an exposure key still works")

    def test_from_loopback_the_secure_keys_still_work(self):
        access = "T" * 24
        with LiveServer({"session_guard": True}, network=access) as server:
            headers = {"X-Monitor-Access": access}
            token = server.call("/api/session-token", headers=headers)[1]["token"]
            status, answer = server.call("/api/settings", {"changes": {"webhook.enabled": False}}, {**headers, "X-Monitor-Token": token})
            self.assertEqual(status, 200, answer)

    def test_the_rule_is_one_function_shared_by_the_handler(self):
        self.assertTrue(localguard.local_only_key("webhook.enabled"))
        self.assertTrue(localguard.local_only_key("listen.host"))
        self.assertFalse(localguard.local_only_key("refresh_seconds"))
        source = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("localguard.local_only_key", source)
        self.assertNotIn("startswith(localguard.LOCAL_ONLY_PREFIXES", source)


# --- act: Stop frees the run, the pipe is closed --------------------------------------------------------------------------------------------------------------------------------------
def reset_run():
    actlocal.RUN.update({"proc": None, "lines": [], "bytes": 0, "running": False, "exit": None, "plan": None, "stopping": False})


class StuckProcess:
    """A process that never ends by itself and ignores terminate() and kill(): the worker blocks on its output."""

    pid = None

    def __init__(self):
        self.release = threading.Event()
        self.stdout = self

    def __iter__(self):
        return self

    def __next__(self):
        self.release.wait(60)
        raise StopIteration

    def close(self):
        pass

    def poll(self):
        return None

    def wait(self, timeout=None):
        self.release.wait(timeout if timeout is not None else 60)
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


def confirmed(item):
    """The item of a plan as `actlocal.plan` makes it: bound to the path and the content of its workflow (checked again by `start`)."""
    folder = Path(tempfile.mkdtemp())
    flow = folder / "ci.yml"
    flow.write_text("on: push\n", encoding="utf-8")
    item["workflow_path"], item["workflow_sha256"] = str(flow.resolve()), hashlib.sha256(flow.read_bytes()).hexdigest()
    return item


class ActStopFreesTheRun(unittest.TestCase):
    def setUp(self):
        reset_run()
        self.snap = mock.patch.object(actlocal, "docker_snapshot", lambda: None)
        self.snap.start()
        self.config = {"act": {"enabled": True, "allowed": ["r:ci.yml:push"]}}

    def tearDown(self):
        self.snap.stop()
        reset_run()

    def start_item(self, popen):
        item = {"repo": "r", "workflow": "ci.yml", "event": "push", "job": "", "command": "act", "argv": ["act"], "timeout_seconds": 60}
        plan_id = actlocal.PENDING.add("act", confirmed(item))
        return actlocal.start(self.config, plan_id, popen=popen)

    def test_stop_then_start_is_not_busy_when_the_worker_does_not_end(self):
        fake = StuckProcess()
        self.addCleanup(fake.release.set)
        with mock.patch.object(actlocal, "STOP_WAIT", 0.3):
            self.assertEqual(self.start_item(lambda *a, **k: fake)["status"], "started")
            end = time.time() + 5
            while time.time() < end and actlocal.RUN["proc"] is None:
                time.sleep(0.02)
            self.assertIs(actlocal.RUN["proc"], fake)
            self.assertEqual(actlocal.stop()["status"], "stopping")
            status = actlocal.status()
            self.assertFalse(status["running"], "Stop left the run marked as running")
            self.assertIsNone(actlocal.RUN["proc"])
            self.assertFalse(actlocal.RUN["stopping"])
            self.assertIsNotNone(actlocal.RUN["exit"])
            self.assertEqual(self.start_item(lambda *a, **k: StuckProcess())["status"], "started", "start answered busy because of a flag left by the Stop")

    def test_a_late_worker_does_not_overwrite_the_next_run(self):
        fake = StuckProcess()
        with mock.patch.object(actlocal, "STOP_WAIT", 0.2):
            self.start_item(lambda *a, **k: fake)
            end = time.time() + 5
            while time.time() < end and actlocal.RUN["proc"] is None:
                time.sleep(0.02)
            actlocal.stop()
            second = StuckProcess()
            self.addCleanup(second.release.set)
            self.assertEqual(self.start_item(lambda *a, **k: second)["status"], "started")
            fake.release.set()          # the first worker ends late
            time.sleep(0.5)
            self.assertTrue(actlocal.status()["running"], "the late worker of the first run closed the second one")

    def test_a_real_process_that_ignores_terminate_is_ended_and_freed(self):
        code = "import signal, time, sys\nsignal.signal(signal.SIGTERM, signal.SIG_IGN) if hasattr(signal, 'SIGTERM') else None\nprint('up', flush=True)\ntime.sleep(120)\n"
        item = {"repo": "r", "workflow": "ci.yml", "event": "push", "job": "", "command": "x", "argv": [sys.executable, "-c", code], "timeout_seconds": 300}
        plan_id = actlocal.PENDING.add("act", confirmed(item))
        self.assertEqual(actlocal.start(self.config, plan_id)["status"], "started")
        end = time.time() + 20
        while time.time() < end and "up" not in actlocal.status()["lines"]:
            time.sleep(0.1)
        self.assertIn("up", actlocal.status()["lines"])
        self.assertEqual(actlocal.stop()["status"], "stopping")
        end = time.time() + 20
        while time.time() < end and actlocal.status()["running"]:
            time.sleep(0.1)
        self.assertFalse(actlocal.status()["running"])
        self.assertIsNone(actlocal.RUN["proc"])
        self.assertIsNotNone(actlocal.RUN["exit"])


class ActClosesItsPipe(unittest.TestCase):
    def setUp(self):
        reset_run()
        self.snap = mock.patch.object(actlocal, "docker_snapshot", lambda: None)
        self.snap.start()
        self.seen = []

    def tearDown(self):
        self.snap.stop()
        reset_run()

    def launch(self, *args, **kwargs):
        proc = subprocess.Popen(*args, **kwargs)
        self.seen.append(proc)
        return proc

    def item(self, code, seconds=30):
        return {"argv": [sys.executable, "-c", code], "timeout_seconds": seconds}

    def test_normal_exit_closes_stdout(self):
        actlocal.RUN["running"] = True
        actlocal._worker(self.item("print('ok')"), self.launch, time.time)
        self.assertTrue(self.seen[0].stdout.closed)
        self.assertFalse(actlocal.status()["running"])

    def test_time_limit_closes_stdout(self):
        actlocal.RUN["running"] = True
        actlocal._worker(self.item("import time; print('x', flush=True); time.sleep(60)", seconds=1), self.launch, time.time)
        self.assertTrue(self.seen[0].stdout.closed)
        self.assertFalse(actlocal.status()["running"])

    def test_stop_closes_stdout(self):
        actlocal.RUN["running"] = True
        thread = threading.Thread(target=actlocal._worker, args=(self.item("import time; print('x', flush=True); time.sleep(60)"), self.launch, time.time), daemon=True)
        thread.start()
        end = time.time() + 20
        while time.time() < end and "x" not in actlocal.status()["lines"]:
            time.sleep(0.05)
        actlocal.stop()
        thread.join(30)
        self.assertFalse(thread.is_alive())
        self.assertTrue(self.seen[0].stdout.closed)

    def test_an_unexpected_error_still_frees_the_run_and_the_timer(self):
        class Broken:
            pid = None
            stdout = None

            def __init__(self):
                self.stdout = iter(())
                self.closed = False

            def poll(self):
                return 0

            def wait(self, timeout=None):
                raise RuntimeError("boom")

            terminate = kill = lambda self: None
        actlocal.RUN["running"] = True
        before = threading.active_count()
        actlocal._worker({"argv": ["x"], "timeout_seconds": 600}, lambda *a, **k: Broken(), time.time)
        self.assertFalse(actlocal.status()["running"])
        self.assertIsNotNone(actlocal.RUN["exit"])
        self.assertIsNone(actlocal.RUN["proc"])
        time.sleep(0.2)
        self.assertLessEqual(threading.active_count(), before, "the timer thread was left running")

    def test_no_resource_warning_from_a_run(self):
        actlocal.RUN["running"] = True
        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            actlocal._worker(self.item("print('ok')"), subprocess.Popen, time.time)
            import gc
            gc.collect()


# --- the session is opened with a POST, not with the address -----------------------------------------------------------------------------------------------------------------------------
class OpenSessionByPost(unittest.TestCase):
    def tearDown(self):
        localguard.reset_limits()

    def post(self, server, body, headers=None, raw=None):
        import urllib.request
        data = raw if raw is not None else json.dumps(body).encode()
        request = urllib.request.Request(server.base + "/api/access", data=data, method="POST", headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:
                return answer.status, dict(answer.headers), json.loads(answer.read())
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), json.loads(error.read() or b"{}")

    def test_the_right_token_sets_the_cookie_and_a_wrong_one_does_not(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            status, headers, answer = self.post(server, {"token": access})
            self.assertEqual((status, answer), (200, {"ok": True}))
            self.assertIn("monitor_access=" + access, headers["Set-Cookie"])
            self.assertIn("HttpOnly", headers["Set-Cookie"])
            self.assertEqual(headers.get("Referrer-Policy"), "no-referrer")
            self.assertEqual(self.post(server, {"token": "x" * 24})[0], 401)
            self.assertEqual(self.post(server, {"nothing": 1})[0], 400)
            self.assertEqual(self.post(server, None, raw=b"not json")[0], 400)
            self.assertEqual(self.post(server, {"token": "y" * 5000})[0], 400)
            # the cookie it gave opens the page without any token in the address
            status, _ = server.call("/api/about", headers={"Cookie": "monitor_access=" + access})
            self.assertEqual(status, 200)

    def test_wrong_tokens_lock_the_address_out(self):
        access = "T" * 24
        with LiveServer({"listen": {"max_failed_attempts": 3}}, network=access) as server:
            for _ in range(3):
                self.post(server, {"token": "bad" * 8})
            self.assertEqual(self.post(server, {"token": access})[0], 429)

    def test_without_the_network_mode_there_is_nothing_to_open(self):
        with LiveServer({}) as server:
            self.assertEqual(self.post(server, {"token": "T" * 24})[0], 404)

    def test_a_foreign_host_is_refused(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            self.assertEqual(self.post(server, {"token": access}, {"Origin": "http://evil.example"})[0], 403)

    def test_the_old_redirect_still_works(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            self.assertEqual(server.call("/api/about?access=" + access, headers={"Accept": "application/json"})[0], 200)


# --- the warning for the network mode on every interface ----------------------------------------------------------------------------------------------------------------------------
class NetworkAllInterfacesWarning(unittest.TestCase):
    def tearDown(self):
        localguard.configure(False)

    def test_the_state_carries_the_host_the_page_checks(self):
        localguard.configure(True, "0.0.0.0", "T" * 24)
        self.assertEqual(localguard.public_state()["host"], "0.0.0.0")
        localguard.configure(True, "192.168.1.20", "T" * 24)
        self.assertNotEqual(localguard.public_state()["host"], "0.0.0.0")

    def test_the_page_has_the_bar_in_settings_and_the_text_in_eight_languages(self):
        html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('id="cfg-netwarn"', html)
        self.assertIn('I18N.network.host==="0.0.0.0"', html)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            catalog = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("0.0.0.0", catalog["ui.adv_net_all"], lang)
            self.assertTrue(catalog["ui.health_degraded"] and catalog["doctor.t.degraded"] and catalog["doctor.f.degraded"], lang)


# --- swallowed failures are counted -----------------------------------------------------------------------------------------------------------------------------------------------------------
class DegradedCounter(unittest.TestCase):
    def setUp(self):
        from github_actions_monitor.app import degraded
        self.degraded = degraded
        degraded.reset()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.degraded.FILE["path"] = None
        self.degraded.reset()
        self.tmp.cleanup()

    def test_counts_by_origin_and_never_keeps_a_token(self):
        self.degraded.note("notify", RuntimeError("failed with token=abc123456789 and ghp_" + "a" * 30))
        self.degraded.note("notify", ValueError("x"))
        self.degraded.note("quota", None)
        snap = self.degraded.snapshot()
        self.assertEqual((snap["total"], snap["origins"]), (3, {"notify": 2, "quota": 1}))
        text = json.dumps(snap)
        self.assertNotIn("abc123456789", text)
        self.assertNotIn("ghp_" + "a" * 30, text)

    def test_noting_never_raises(self):
        class Evil:
            def __str__(self):
                raise RuntimeError("no")
        self.degraded.note(Evil(), Evil())      # must not raise

    def test_doctor_reads_what_the_running_monitor_saved(self):
        from github_actions_monitor.cli import doctor
        path = Path(self.tmp.name) / "degraded.json"
        self.degraded.attach(path)
        self.degraded.note("mirror.item", OSError("disk"))
        self.degraded.save(force=True)
        checks = {c["id"]: c for c in doctor.run(runner=lambda *a, **k: (1, "", ""), folder=self.tmp.name, config={})}
        self.assertEqual(checks["degraded"]["status"], "warn")
        self.assertIn("mirror.item", checks["degraded"]["detail"])
        path.unlink()
        checks = {c["id"]: c for c in doctor.run(runner=lambda *a, **k: (1, "", ""), folder=self.tmp.name, config={})}
        self.assertEqual(checks["degraded"]["status"], "ok")

    def test_the_health_answer_and_the_worker_use_it(self):
        self.assertIn("degraded", am.health_payload())
        reset_run()
        with mock.patch.object(actlocal, "docker_snapshot", lambda: None):
            actlocal.RUN["running"] = True
            actlocal._worker({"argv": ["x"], "timeout_seconds": 60}, mock.Mock(side_effect=RuntimeError("boom")), time.time)
        self.assertEqual(self.degraded.snapshot()["origins"].get("actlocal.worker"), 1)
        self.assertFalse(actlocal.status()["running"])


# --- the history of changes in eight languages ----------------------------------------------------------------------------------------------------------------------------------------
try:
    sys.path.insert(0, str(HERE.parent / "tools"))
    import make_help_index  # noqa: E402     (the tools live in the repository, not in the zip)
except ImportError:
    make_help_index = None


@unittest.skipIf(make_help_index is None, "the tools folder is not part of the package")
class ChangelogTranslations(unittest.TestCase):
    TAILS = {"es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}

    def versions(self, path):
        import re
        return re.findall(r"(?m)^## \[([^\]]+)\]", Path(path).read_text(encoding="utf-8"))

    def test_every_translation_lists_every_version_of_the_source_in_the_same_order(self):
        want = self.versions(HERE / "CHANGELOG.md")
        self.assertGreater(len(want), 20)
        for lang, tail in self.TAILS.items():
            self.assertEqual(self.versions(HERE / "docs" / f"CHANGELOG{tail}.md"), want, lang)
        self.assertEqual(make_help_index.changelog_problems(), [])

    def test_a_missing_version_is_caught(self):
        both = chr(10).join(["# C", "", "## [2.0.0]", "", "x", "", "## [1.0.0]", "", "y", ""])
        one = chr(10).join(["# C", "", "## [2.0.0]", "", "x", ""])
        with tempfile.TemporaryDirectory() as folder:
            mon = Path(folder)
            (mon / "docs").mkdir()
            (mon / "CHANGELOG.md").write_text(both, encoding="utf-8")
            for lang, tail in self.TAILS.items():
                (mon / "docs" / f"CHANGELOG{tail}.md").write_text(both, encoding="utf-8")
            with mock.patch.object(make_help_index, "MON", mon):
                self.assertEqual(make_help_index.changelog_problems(), [])
                (mon / "docs" / "CHANGELOG_jpn.md").write_text(one, encoding="utf-8")
                self.assertEqual(make_help_index.changelog_problems(), [("ja", "1.0.0")])

    def test_the_new_entry_is_translated_not_copied(self):
        english = (HERE / "CHANGELOG.md").read_text(encoding="utf-8").split("## [1.6.5]")[0]
        for lang, tail in self.TAILS.items():
            text = (HERE / "docs" / f"CHANGELOG{tail}.md").read_text(encoding="utf-8")
            entry = text.split("## [1.6.6]")[1].split("## [1.6.5]")[0]
            self.assertNotIn("### Added", entry, lang)
            self.assertNotEqual(entry.strip(), english.split("## [1.6.6]")[1].strip(), lang)
            self.assertNotIn("only in English", entry)


if __name__ == "__main__":
    unittest.main()
