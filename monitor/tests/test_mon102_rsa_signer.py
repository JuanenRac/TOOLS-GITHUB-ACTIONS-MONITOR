# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The GitHub App signs its JWT with the standard library, so it no longer depends on an `openssl` in the PATH: the key reader (PKCS#1 and PKCS#8) and the RS256 signature are proved against keys made
in the test (never a real key and never a key written in a file of the repository), against the `openssl` program when there is one, and against the public key when there is none; a key that cannot be
read says why, once, and the reads go on with the token of the user. Nothing here reaches GitHub."""
import base64
import hashlib
import json
import random
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
from github_actions_monitor.integrations import github_app, rsa_sign  # noqa: E402

OPENSSL = shutil.which("openssl")
DATA = b"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxMjM0NSJ9"


def is_prime(n, rng):
    if n < 4:
        return n in (2, 3)
    if n % 2 == 0:
        return False
    d, r = n - 1, 0
    while d % 2 == 0:
        d, r = d // 2, r + 1
    for _ in range(12):
        x = pow(rng.randrange(2, n - 1), d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def prime(bits, rng):
    while True:
        candidate = rng.getrandbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2)) | 1
        if is_prime(candidate, rng):
            return candidate


def make_key(bits=1024, seed=7):
    """A disposable key (a fixed seed: the same one every run; it protects nothing and exists only here)."""
    rng = random.Random(seed)
    e = 65537
    while True:
        p, q = prime(bits // 2, rng), prime(bits // 2, rng)
        if p != q and (p - 1) % e and (q - 1) % e and (p * q).bit_length() == bits:
            break
    if p < q:
        p, q = q, p
    n, d = p * q, pow(e, -1, (p - 1) * (q - 1))
    return n, e, d, p, q, d % (p - 1), d % (q - 1), pow(q, -1, p)


def der_int(value):
    raw = value.to_bytes((value.bit_length() + 8) // 8, "big")
    return b"\x02" + der_len(len(raw)) + raw


def der_len(size):
    if size < 128:
        return bytes([size])
    raw = size.to_bytes((size.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def der_seq(*parts, tag=0x30):
    body = b"".join(parts)
    return bytes([tag]) + der_len(len(body)) + body


def pkcs1(key):
    return der_seq(der_int(0), *[der_int(v) for v in key])


def pkcs8(key):
    algorithm = der_seq(b"\x06\x09" + rsa_sign.RSA_OID, b"\x05\x00")
    inner = pkcs1(key)
    return der_seq(der_int(0), algorithm, b"\x04" + der_len(len(inner)) + inner)


DASHES = "-" * 5      # built, not written: a scanner of secrets must not take a line of this file for a key


def fence(word, label):
    return f"{DASHES}{word} {label}{DASHES}"


def pem(label, der):
    body = base64.encodebytes(der).decode("ascii")
    return fence("BEGIN", label) + "\n" + body + fence("END", label) + "\n"


def expected(data, key):
    n, e = key[0], key[1]
    size = (n.bit_length() + 7) // 8
    info = rsa_sign.SHA256_PREFIX + hashlib.sha256(data).digest()
    return b"\x00\x01" + b"\xff" * (size - len(info) - 3) + b"\x00" + info


KEY = make_key()


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="ascii")
        if sys.platform != "win32":
            path.chmod(0o600)      # a key that others can read is a warning of the doctor of its own
        return str(path)


class TheSigner(Folder):
    def test_both_formats_give_the_signature_of_the_standard_and_it_opens_with_the_public_key(self):
        for label, der in (("RSA PRIVATE KEY", pkcs1(KEY)), ("PRIVATE KEY", pkcs8(KEY))):
            path = self.write("k.pem", pem(label, der))
            signature = rsa_sign.sign_file(DATA, path)
            n, e = KEY[0], KEY[1]
            self.assertEqual(len(signature), (n.bit_length() + 7) // 8)
            self.assertEqual(pow(int.from_bytes(signature, "big"), e, n).to_bytes(len(signature), "big"), expected(DATA, KEY), label)
            self.assertEqual(signature, rsa_sign.sign_file(DATA, path), "PKCS#1 v1.5 is deterministic")

    def test_the_slow_way_without_the_chinese_remainder_theorem_gives_the_same_signature(self):
        n, d = KEY[0], KEY[2]
        slow = pow(int.from_bytes(expected(DATA, KEY), "big"), d, n).to_bytes((n.bit_length() + 7) // 8, "big")
        self.assertEqual(rsa_sign.sign_numbers(DATA, KEY), slow)

    def test_a_fault_in_the_remainder_numbers_never_leaves_as_a_signature(self):
        broken = KEY[:5] + (KEY[5] + 2,) + KEY[6:]      # dp wrong: the quick way is wrong, the check catches it and the slow way answers
        self.assertEqual(rsa_sign.sign_numbers(DATA, broken), rsa_sign.sign_numbers(DATA, KEY))

    @unittest.skipUnless(OPENSSL, "there is no openssl on this computer: the public key proves the signature instead (the tests above)")
    def test_it_is_the_same_signature_as_the_one_of_openssl_for_a_key_that_openssl_made(self):
        for flags in (["-traditional"], []):
            key = self.dir / "o.pem"
            made = subprocess.run([OPENSSL, "genrsa", *flags, "-out", str(key), "2048"], capture_output=True, timeout=120)
            if made.returncode != 0 and flags:
                continue      # an old openssl has no -traditional (and already writes PKCS#1)
            self.assertEqual(made.returncode, 0)
            text = key.read_text(encoding="ascii")
            self.assertTrue(text.startswith(DASHES + "BEGIN"), flags)
            theirs = subprocess.run([OPENSSL, "dgst", "-sha256", "-sign", str(key)], input=DATA, capture_output=True, timeout=60).stdout
            self.assertEqual(rsa_sign.sign_file(DATA, str(key)), theirs, flags)

    @unittest.skipUnless(OPENSSL, "there is no openssl on this computer")
    def test_a_pkcs8_key_converted_by_openssl_is_read(self):
        key, converted = self.dir / "a.pem", self.dir / "b.pem"
        subprocess.run([OPENSSL, "genrsa", "-out", str(key), "2048"], capture_output=True, timeout=120, check=True)
        done = subprocess.run([OPENSSL, "pkcs8", "-topk8", "-nocrypt", "-in", str(key), "-out", str(converted)], capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0)
        self.assertIn("BEGIN PRIVATE KEY", converted.read_text(encoding="ascii"))
        theirs = subprocess.run([OPENSSL, "dgst", "-sha256", "-sign", str(converted)], input=DATA, capture_output=True, timeout=60).stdout
        self.assertEqual(rsa_sign.sign_file(DATA, str(converted)), theirs)

    def test_a_key_that_cannot_be_read_says_why_and_never_shows_a_byte_of_it(self):
        good = pem("RSA PRIVATE KEY", pkcs1(KEY))
        body = good.split("\n")[1]
        cases = {
            "empty": "", "no key": "hello\n", "truncated": good[:len(good) // 2],
            "bad base64": fence("BEGIN", "RSA PRIVATE KEY") + "\n!!!!\n" + fence("END", "RSA PRIVATE KEY") + "\n",
            "passphrase": fence("BEGIN", "ENCRYPTED PRIVATE KEY") + "\nAAAA\n" + fence("END", "ENCRYPTED PRIVATE KEY") + "\n",
            "not rsa": pem("PRIVATE KEY", der_seq(der_int(0), der_seq(b"\x06\x03\x2a\x03\x04", b"\x05\x00"), b"\x04\x02\x05\x00")),
            "numbers that do not add up": pem("RSA PRIVATE KEY", der_seq(der_int(0), *[der_int(v + 1) for v in KEY])),
        }
        for name, text in cases.items():
            path = self.write("bad.pem", text)
            with self.assertRaises(rsa_sign.KeyError_, msg=name) as caught:
                rsa_sign.sign_file(DATA, path)
            self.assertNotIn(body[:20], str(caught.exception), name)
        with self.assertRaises(rsa_sign.KeyError_):
            rsa_sign.sign_file(DATA, str(self.dir / "missing.pem"))
        big = self.write("big.pem", "A" * 30_000)
        with self.assertRaises(rsa_sign.KeyError_):
            rsa_sign.sign_file(DATA, big)

    def test_the_standard_library_alone_makes_the_jwt_and_it_opens_with_the_public_key(self):
        path = self.write("k.pem", pem("PRIVATE KEY", pkcs8(KEY)))
        jwt = github_app.make_jwt("12345", path, now=1_800_000_000)
        head, payload, sig = jwt.split(".")
        pad = lambda text: text + "=" * (-len(text) % 4)      # noqa: E731
        self.assertEqual(json.loads(base64.urlsafe_b64decode(pad(head))), {"alg": "RS256", "typ": "JWT"})
        self.assertEqual(json.loads(base64.urlsafe_b64decode(pad(payload)))["iss"], "12345")
        raw = base64.urlsafe_b64decode(pad(sig))
        n, e = KEY[0], KEY[1]
        self.assertEqual(pow(int.from_bytes(raw, "big"), e, n).to_bytes(len(raw), "big"), expected((head + "." + payload).encode(), KEY))


class FakeGitHub:
    def __init__(self):
        self.calls = []

    def __call__(self, request):
        path = request.full_url.replace(github_app.API, "")
        self.calls.append(path)
        if path == "/app/installations":
            return [{"id": 777}], {}
        if path == "/app/installations/777/access_tokens":
            return {"token": "ghs_" + "A1b2C3d4E5" * 4, "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))}, {}
        raise AssertionError(path)


class WithoutOpenssl(Folder):
    def setUp(self):
        super().setUp()
        github_app.reset()
        self.addCleanup(github_app.reset)
        stop = [mock.patch.object(github_app, "find_openssl", return_value=""), mock.patch("shutil.which", return_value=None)]
        for patch in stop:
            patch.start()
            self.addCleanup(patch.stop)

    def config(self, path):
        return {"github_app": {"enabled": True, "app_id": "12345", "key_path": path}}

    def test_a_computer_without_openssl_in_the_path_still_reads_with_the_app(self):
        path = self.write("k.pem", pem("RSA PRIVATE KEY", pkcs1(KEY)))
        fake = FakeGitHub()
        got = github_app.token(self.config(path), opener=fake)
        self.assertTrue(got.startswith("ghs_"))
        self.assertEqual(github_app._STATE["signer"], "builtin")
        self.assertEqual(github_app.notice(self.config(path), 10700)["state"], "using")
        self.assertEqual(doctor.github_app_check(self.config(path))[0], "ok")

    def test_a_key_that_cannot_be_read_gives_the_notice_the_code_and_one_event_only(self):
        path = self.write("k.pem", fence("BEGIN", "RSA PRIVATE KEY") + "\nAAAA\n" + fence("END", "RSA PRIVATE KEY") + "\n")
        with mock.patch("github_actions_monitor.app.degraded.note") as note:
            self.assertEqual(github_app.token(self.config(path), opener=FakeGitHub()), "")
            self.assertEqual(github_app.token(self.config(path), opener=FakeGitHub(), force=True), "")
            self.assertEqual(github_app.token(self.config(path), opener=FakeGitHub(), force=True), "")
        self.assertEqual(note.call_count, 1)
        shown = github_app.notice(self.config(path), 5000)
        self.assertEqual((shown["state"], shown["code"], shown["limit"]), ("fallback", "key_unreadable", 5000))
        state, detail = doctor.github_app_check(self.config(path))
        self.assertEqual(state, "warn")
        self.assertIn("key", detail)

    def test_the_codes_of_the_reasons(self):
        for text, code in (("the key cannot be used to sign: the key file cannot be read", "key_unreadable"), ("the key cannot be used to sign: the key does not sign", "sign_failed"),
                           ("the App is not installed on any account", "app_not_installed"), ("HTTP 401 Bad credentials", "token_refused"), ("timeout", "other")):
            self.assertEqual(github_app.reason_code(text), code, text)

    def test_the_app_that_is_off_has_no_notice(self):
        self.assertEqual(github_app.notice({}, 5000)["state"], "off")


class TheNoticeEverywhere(Folder):
    def test_the_quota_and_the_page_carry_the_notice_and_every_cause_has_its_words_in_eight_languages(self):
        from github_actions_monitor import i18n
        from github_actions_monitor.data_pipeline import quota
        github_app.reset()
        self.addCleanup(github_app.reset)
        shown = quota.app_notice({"github_app": {"enabled": True, "app_id": "1", "key_path": ""}}, 5000)
        self.assertEqual((shown["state"], shown["code"], shown["limit"]), ("fallback", "not_configured", 5000))
        self.assertEqual(quota.app_notice({}, 5000)["state"], "off")
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('q.app.state==="fallback"', page)
        for code in ("key_unreadable", "sign_failed", "app_not_installed", "token_refused", "not_configured", "other"):
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "ui.q_app_c_" + code), "ui.q_app_c_" + code, (lang, code))
        for lang in i18n.LANGS:
            self.assertIn("{limit}", i18n.catalogue(lang)["ui.q_app_fb"])

    def test_the_guides_and_the_skills_say_it(self):
        for name in ("QUOTA", "QUOTA_spa", "QUOTA_deu", "QUOTA_fra", "QUOTA_ita", "QUOTA_jpn", "QUOTA_zho", "QUOTA_por"):
            text = (HERE / "docs" / f"{name}.md").read_text(encoding="utf-8")
            for code in ("key_unreadable", "sign_failed", "app_not_installed", "token_refused", "not_configured"):
                self.assertIn(code, text, name)
        external = (HERE / "skills" / "external" / "references" / "connect.md").read_text(encoding="utf-8")
        internal = (HERE / "skills" / "internal" / "references" / "scenarios.md").read_text(encoding="utf-8")
        for text in (external, internal):
            self.assertIn("key_unreadable", text)
            self.assertIn("/api/quota", text)


if __name__ == "__main__":
    unittest.main()
