# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The optional GitHub App for the reads: a JWT of at most ten minutes signed by openssl (the key is never read by the monitor), the installation token kept in memory, reads only, a fall back to the user's
token, the status without the key or the token, and the doctor."""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor.integrations import github_app  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402

SECRET_TOKEN = "ghs_" + "A1b2C3d4E5" * 4
CONFIG = {"github_app": {"enabled": True, "app_id": "12345", "key_path": "/some/where/key.pem"}}


class FakeGitHub:
    """A small simulated GitHub: the installations, the token and the rate limit of the App."""

    def __init__(self, fail_token=False):
        self.calls = []
        self.fail_token = fail_token

    def __call__(self, request):
        path, method = request.full_url.replace(github_app.API, ""), request.get_method()
        self.calls.append((method, path, request.get_header("Authorization", "")[:12]))
        if path == "/app/installations":
            return [{"id": 777, "account": {"login": "demo-owner"}}], {}
        if path == "/app/installations/777/access_tokens":
            if self.fail_token:
                raise RuntimeError("HTTP 401 Bad credentials Bearer eyJhbGciOiJSUzI1NiJ9.abcdefghijklmnop.sig")
            return {"token": SECRET_TOKEN, "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))}, {}
        if path == "/app":
            return {"name": "demo-reader"}, {}
        if path == "/app/installations/777":
            return {"permissions": {"actions": "read", "contents": "read", "metadata": "read"}}, {}
        if path == "/rate_limit":
            return {"resources": {"core": {"remaining": 10000, "limit": 10550, "reset": int(time.time()) + 1800}}}, {}
        raise AssertionError(path)


def fake_signer(data, key_path):
    return b"signature-bytes" * 16


class JwtAndToken(unittest.TestCase):
    def setUp(self):
        github_app.reset()

    def test_the_jwt_lives_at_most_ten_minutes_and_names_the_app(self):
        jwt = github_app.make_jwt("12345", "/k.pem", now=1_000_000, signer=fake_signer)
        head, payload, signature = jwt.split(".")
        pad = lambda text: text + "=" * (-len(text) % 4)      # noqa: E731
        body = json.loads(base64.urlsafe_b64decode(pad(payload)))
        self.assertEqual(json.loads(base64.urlsafe_b64decode(pad(head))), {"alg": "RS256", "typ": "JWT"})
        self.assertEqual(body["iss"], "12345")
        self.assertLessEqual(body["exp"] - body["iat"], 600)
        self.assertTrue(signature)

    @unittest.skipUnless(shutil.which("openssl"), "no openssl on this computer")
    def test_a_real_openssl_signs_with_a_key_the_monitor_never_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "app.pem"
            subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], capture_output=True, check=True)
            jwt = github_app.make_jwt("12345", str(key))
            signature = jwt.split(".")[2]
            self.assertGreater(len(base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))), 200)
            source = (HERE / "src" / "github_actions_monitor" / "integrations" / "github_app.py").read_text(encoding="utf-8")
            self.assertNotIn("read_text(key", source)
            self.assertNotIn("open(key", source)
            self.assertIn('[program, "dgst", "-sha256", "-sign", key_path]', source)      # only the PATH goes to openssl, and the program is the one that was found

    def test_the_token_is_found_cached_and_renewed_before_it_expires(self):
        fake = FakeGitHub()
        got = github_app.token(CONFIG, opener=fake, signer=fake_signer, now=1000)
        self.assertEqual(got, SECRET_TOKEN)
        self.assertEqual([c[1] for c in fake.calls], ["/app/installations", "/app/installations/777/access_tokens"])      # the installation is discovered
        self.assertEqual(github_app.token(CONFIG, opener=fake, signer=fake_signer, now=1000 + 60), SECRET_TOKEN)
        self.assertEqual(len(fake.calls), 2, "cached")
        github_app._STATE["expires"] = 2000
        github_app.token(CONFIG, opener=fake, signer=fake_signer, now=2000 - 200)      # five minutes before it expires: renewed
        self.assertEqual(len(fake.calls), 3)

    def test_off_or_incomplete_gives_no_token_and_a_failure_falls_back_to_the_user(self):
        fake = FakeGitHub()
        self.assertEqual(github_app.token({}, opener=fake, signer=fake_signer), "")
        self.assertEqual(github_app.token({"github_app": {"enabled": True}}, opener=fake, signer=fake_signer), "")
        self.assertEqual(fake.calls, [])
        broken = FakeGitHub(fail_token=True)
        self.assertEqual(github_app.token(CONFIG, opener=broken, signer=fake_signer, now=5000), "")
        self.assertEqual(github_app.token(CONFIG, opener=broken, signer=fake_signer, now=5010), "", "no hammering: it waits before trying again")
        self.assertEqual(len([c for c in broken.calls if "access_tokens" in c[1]]), 1)
        self.assertNotIn("eyJ", github_app._STATE["error"])      # a message never carries a token

    def test_only_reads_use_the_app_and_a_refused_read_is_repeated_with_the_user(self):
        for args, expect in ((["api", "repos/o/r/actions/runs"], True), (["run", "list", "--repo", "o/r"], True), (["api", "-X", "POST", "x"], False), (["api", "x", "-f", "a=b"], False),
                             (["run", "rerun", "1"], False), (["release", "create", "v1"], False), (["workflow", "run", "ci.yml"], False)):
            self.assertEqual(github_app.is_read(args), expect, args)
        self.assertTrue(github_app.should_retry_with_user("HTTP 403: Resource not accessible by integration"))
        self.assertFalse(github_app.should_retry_with_user("HTTP 404: Not Found"))

    def test_the_status_shows_name_installation_permissions_and_allowance_and_never_a_secret(self):
        fake = FakeGitHub()
        out = github_app.status(CONFIG, opener=fake, signer=fake_signer, now=1000)
        self.assertTrue(out["ok"])
        self.assertEqual((out["app"], out["installation_id"], out["rate"]["limit"]), ("demo-reader", "777", 10550))
        self.assertEqual(out["permissions"]["actions"], "read")
        self.assertEqual(out["permissions"]["issues"], "missing")      # what the App lacks for a panel
        text = json.dumps(out)
        self.assertNotIn(SECRET_TOKEN, text)
        self.assertNotIn("key.pem", text)
        self.assertFalse(github_app.status({}, opener=fake)["enabled"])


class SettingsAndDoctor(unittest.TestCase):
    def test_the_settings_only_keep_valid_values(self):
        cfg = github_app.settings({"github_app": {"enabled": True, "app_id": "abc", "key_path": "D:/keys/k.pem", "installation_id": "9"}})
        self.assertEqual((cfg["app_id"], cfg["key_path"], cfg["installation_id"]), ("", "", "9"))      # no letters in an id, never the D: drive
        self.assertFalse(github_app.settings({})["enabled"])
        from github_actions_monitor.app import settings_api
        for key in ("github_app.enabled", "github_app.app_id", "github_app.key_path", "github_app.installation_id"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in i18n.LANGS:
                for prefix in ("cfg.f.", "cfg.h."):
                    self.assertNotEqual(i18n.tl(lang, prefix + key), prefix + key, (lang, key))
        from github_actions_monitor.security import localguard
        self.assertNotIn("github_app.key_path", localguard.REMOTE_WRITABLE)

    def test_the_doctor_checks_openssl_and_the_key_file_and_never_prints_them(self):
        self.assertEqual(doctor.github_app_check({}), ("ok", "off"))
        status, detail = doctor.github_app_check(CONFIG)
        self.assertEqual(status, "warn")
        self.assertIn("the key file", detail)
        self.assertNotIn("/some/where", detail)
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "k.pem"
            key.write_text("not a real key", encoding="utf-8")
            if os.name == "posix":
                os.chmod(key, 0o644)
                self.assertIn("other users", doctor.github_app_check({"github_app": {"enabled": True, "app_id": "1", "key_path": str(key)}})[1])
                os.chmod(key, 0o600)
            with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/openssl"):
                self.assertEqual(doctor.github_app_check({"github_app": {"enabled": True, "app_id": "1", "key_path": str(key)}}), ("ok", "on"))
        self.assertIn("github_app", doctor.ORDER)
        for lang in i18n.LANGS:
            for key_name in ("doctor.t.github_app", "doctor.f.github_app"):
                self.assertNotEqual(i18n.tl(lang, key_name), key_name, lang)

    def test_the_monitor_hands_the_app_token_only_to_reads(self):
        from github_actions_monitor.app import actions_monitor as am
        old = am.LIVE_CONFIG
        am.LIVE_CONFIG = CONFIG
        try:
            with mock.patch.object(github_app, "token", return_value=SECRET_TOKEN):
                self.assertEqual(am.read_source(["api", "repos/o/r"], "app")[1]["env"]["GH_TOKEN"], SECRET_TOKEN)
                self.assertEqual(am.read_source(["api", "-X", "POST", "repos/o/r/x"])[1], {})      # a write: the user, whatever the pool says
                self.assertEqual(am.read_source(["workflow", "run", "ci.yml"])[1], {})
            with mock.patch.object(github_app, "token", return_value=""):
                self.assertEqual(am.read_source(["api", "repos/o/r"], "app")[1], {})
        finally:
            am.LIVE_CONFIG = old


if __name__ == "__main__":
    unittest.main()
