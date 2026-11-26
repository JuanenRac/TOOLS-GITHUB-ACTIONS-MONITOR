# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The signature of a release: the keyring of public keys, the verification of a downloaded folder, the updater (a release from 2.2.0 on needs a valid signature, an older one is installed with a warning),
the two bills of materials, the files a build leaves next to the zip and the short summary of a release in the eight languages. The keys used here are made for the test: nothing reads a real one."""
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_66_updater_engine as base  # noqa: E402
import release_summary  # noqa: E402
import sbom  # noqa: E402
import sign_release  # noqa: E402
from github_actions_monitor.app import updatecheck  # noqa: E402
from github_actions_monitor.security import keyring, release_verify, sigverify  # noqa: E402

mu = base.mu


def keypair(seed):
    """(secret scalar, prefix, public bytes) of a 32-byte seed, as RFC 8032 section 5.1.5 says."""
    digest = hashlib.sha512(seed).digest()
    scalar = int.from_bytes(digest[:32], "little") & ((1 << 254) - 8) | (1 << 254)
    return scalar, digest[32:], sigverify._compress(sigverify._mul(scalar, sigverify.BASE))


def sign(seed, message):
    scalar, prefix, public = keypair(seed)
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % sigverify._Q
    point = sigverify._compress(sigverify._mul(r, sigverify.BASE))
    k = int.from_bytes(hashlib.sha512(point + public + message).digest(), "little") % sigverify._Q
    return point + ((r + k * scalar) % sigverify._Q).to_bytes(32, "little")


def signature_line(seed, message):
    return base64.b64encode(sign(seed, message)).decode("ascii") + "\n"


SEED, OTHER_SEED = b"\x01" * 32, b"\x02" * 32
PUBLIC, OTHER_PUBLIC = keypair(SEED)[2].hex(), keypair(OTHER_SEED)[2].hex()


def entry(public=PUBLIC, **more):
    return dict({"id": "test", "public": public, "scopes": ["release"]}, **more)


class TheMathematics(unittest.TestCase):
    SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    PUBLIC = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    SIGNATURE = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")

    def test_the_first_vector_of_rfc_8032_in_the_updater_and_in_the_monitor(self):
        for verify in (mu.ed25519_verify, sigverify.ed25519_verify):
            self.assertTrue(verify(self.PUBLIC, b"", self.SIGNATURE))
            self.assertFalse(verify(self.PUBLIC, b"x", self.SIGNATURE))
            self.assertFalse(verify(self.PUBLIC, b"", self.SIGNATURE[:63]))
        self.assertEqual(sign(self.SEED, b""), self.SIGNATURE)      # the signer of these tests is the real one

    def test_the_updater_and_the_keyring_trust_the_same_release_keys(self):
        self.assertEqual(sorted(mu.RELEASE_KEYS), sorted(k["public"] for k in keyring.builtin_keys() if "release" in k["scopes"]))
        for key in keyring.builtin_keys():
            self.assertEqual(len(keyring.fingerprint(key["public"])), 64)
        self.assertEqual(mu.SIG_NAME, release_verify.SUMS_NAME + keyring.SIGNATURE_SUFFIX)


class Keyring(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="keyring_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def check(self, code, call):
        with self.assertRaises(keyring.KeyringError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_a_private_value_is_refused(self):
        header = "-----BEGIN " + "PRIVATE KEY-----"
        for raw in (entry(private="aa"), entry(note=header), entry(seed="00" * 32)):
            self.check("private_value", lambda: keyring.clean_entry(raw))
        self.check("bad_key", lambda: keyring.clean_entry(entry(public="ab")))
        self.check("bad_scope", lambda: keyring.clean_entry(entry(scopes=["everything"])))
        self.check("bad_date", lambda: keyring.clean_entry(entry(expires="2030-13-01")))
        self.check("bad_id", lambda: keyring.clean_entry(entry(id="a b")))

    def test_the_person_adds_and_revokes_their_own_keys_but_never_a_release_key(self):
        path = self.tmp / "keyring.json"
        self.check("builtin", lambda: keyring.add_key(path, "mine", PUBLIC, ["release"]))
        keyring.add_key(path, "mine", PUBLIC, ["plugins"])
        self.check("duplicate", lambda: keyring.add_key(path, "mine", OTHER_PUBLIC, ["plugins"]))
        self.check("duplicate", lambda: keyring.add_key(path, keyring.RELEASE_KEYS[0]["id"], OTHER_PUBLIC, ["plugins"]))
        message = b"a plugin"
        keys = keyring.all_keys(path)
        self.assertEqual(keyring.verify(message, signature_line(SEED, message), "plugins", keys), (keyring.VALID, "mine"))
        self.assertEqual(keyring.verify(message, signature_line(SEED, message), "release", keys)[0], keyring.INVALID)
        keyring.revoke_key(path, keyring.fingerprint(PUBLIC))
        self.assertEqual(keyring.verify(message, signature_line(SEED, message), "plugins", keyring.all_keys(path))[0], keyring.REVOKED)
        self.check("builtin", lambda: keyring.revoke_key(path, keyring.RELEASE_KEYS[0]["id"]))
        self.check("unknown", lambda: keyring.revoke_key(path, "nobody"))
        self.assertNotIn("PRIVATE", path.read_text(encoding="utf-8").upper())

    def test_a_release_scope_written_by_hand_in_the_file_is_ignored(self):
        path = self.tmp / "keyring.json"
        path.write_text(json.dumps({"keys": [entry()]}), encoding="utf-8")
        self.assertEqual(keyring.load_user_keys(path)[0]["scopes"], [])

    def test_the_results(self):
        data = b"sums"
        keys = [keyring.clean_entry(entry(expires="2030-01-01"))]
        good = signature_line(SEED, data)
        self.assertEqual(keyring.verify(data, good, keys=keys, today=date(2029, 1, 1))[0], keyring.VALID)
        self.assertEqual(keyring.verify(data, good, keys=keys, today=date(2030, 1, 2))[0], keyring.EXPIRED)
        self.assertEqual(keyring.verify(data + b"!", good, keys=keys)[0], keyring.INVALID)
        self.assertEqual(keyring.verify(data, signature_line(OTHER_SEED, data), keys=keys)[0], keyring.INVALID)
        self.assertEqual(keyring.verify(data, "", keys=keys)[0], keyring.ABSENT)
        self.assertEqual(keyring.verify(data, "not a signature", keys=keys)[0], keyring.INVALID)
        self.assertEqual(keyring.verify(data, good, scope="packs", keys=keys)[0], keyring.UNKNOWN_KEY)


def signed_folder(folder, files, seed=SEED):
    """A release folder: the files, SHA256SUMS and its signature."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (folder / name).write_bytes(data)
    sums = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in files.items()).encode("ascii")
    (folder / "SHA256SUMS").write_bytes(sums)
    if seed:
        (folder / mu.SIG_NAME).write_text(signature_line(seed, sums), encoding="ascii")
    return folder


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="verify_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.keys = [keyring.clean_entry(entry())]

    def test_a_signed_folder_is_ok_and_each_damage_is_named(self):
        folder = signed_folder(self.tmp / "r", {"github_actions_monitor.zip": b"zip", "a.json": b"{}"})
        self.assertTrue(release_verify.verify_release(folder, self.keys)["ok"])
        (folder / "a.json").write_bytes(b"[]")
        report = release_verify.verify_release(folder, self.keys)
        self.assertEqual((report["ok"], report["signature"], report["files"]["a.json"]), (False, "valid", "mismatch"))
        (folder / "a.json").unlink()
        self.assertEqual(release_verify.verify_release(folder, self.keys)["files"]["a.json"], "missing")
        with (folder / "SHA256SUMS").open("ab") as handle:
            handle.write(b"0" * 64 + b"  ../outside\n")
        report = release_verify.verify_release(folder, self.keys)
        self.assertEqual((report["ok"], report["signature"]), (False, "invalid"))
        self.assertTrue(report["bad_lines"])
        self.assertNotIn("../outside", report["files"])

    def test_without_signature_or_without_sums_it_is_not_ok(self):
        folder = signed_folder(self.tmp / "r", {"github_actions_monitor.zip": b"zip"}, seed=None)
        self.assertEqual((release_verify.verify_release(folder, self.keys)["signature"], release_verify.verify_release(folder, self.keys)["ok"]), ("absent", False))
        self.assertFalse(release_verify.verify_release(self.tmp / "nothing")["ok"])


class SignedSource(base.FakeSource):
    """The releases of the tests, with the signature files of `seed` next to each downloaded zip (None: no signature)."""

    def __init__(self, zips, seed=SEED, **kw):
        super().__init__(zips, **kw)
        self.seed = seed

    def fetch_zip(self, release, dest_dir):
        target, expected, how = super().fetch_zip(release, dest_dir)
        sums = f"{expected}  {mu.ZIP_NAME}\n".encode("ascii")
        (Path(dest_dir) / mu.SUMS_NAME).write_bytes(sums)
        if self.seed:
            (Path(dest_dir) / mu.SIG_NAME).write_text(signature_line(self.seed, sums), encoding="ascii")
        return target, expected, how


class TheUpdater(base.Base):
    NEW = "2.2.0"

    def install(self, version="2.0.8"):
        return base.make_install(self.tmp / "i", version, base.config_from_defaults("2.0.8"))

    def of(self, root, source):
        return mu.Updater(root, source, backups=self.tmp / "copies", env={}, probe=base.NO_MONITOR, keys=(PUBLIC,))

    def codes(self, plan):
        return {c["code"]: c["severity"] for c in plan["checks"]}

    def test_a_signed_new_release_is_applied(self):
        root = self.install()
        up = self.of(root, SignedSource({self.NEW: self.zip_of(self.NEW)}))
        plan = up.plan(self.NEW, {})
        self.assertEqual((self.codes(plan).get("sig_ok"), plan["signature"], plan["blocked"]), ("info", "valid", False))
        report = up.apply(self.NEW, {})
        self.assertTrue(report["ok"], report)
        self.assertEqual(mu.read_tool_version(root), self.NEW)

    def test_a_new_release_without_a_valid_signature_changes_nothing(self):
        root = self.install()
        before = base.tree_hash(root)
        for seed, code, state in ((None, "sig_missing", "absent"), (OTHER_SEED, "sig_bad", "invalid")):
            up = self.of(root, SignedSource({self.NEW: self.zip_of(self.NEW)}, seed=seed))
            plan = up.plan(self.NEW, {})
            self.assertEqual((self.codes(plan).get(code), plan["signature"], plan["blocked"]), ("block", state, True))
            self.assertFalse(up.apply(self.NEW, {})["ok"])
        self.assertEqual(base.tree_hash(root), before)

    def test_the_default_keys_do_not_trust_a_key_of_somebody_else(self):
        up = mu.Updater(self.install(), SignedSource({self.NEW: self.zip_of(self.NEW)}), backups=self.tmp / "copies", env={}, probe=base.NO_MONITOR)
        self.assertEqual(up.plan(self.NEW, {})["signature"], "invalid")

    def test_an_older_zip_offered_as_a_newer_release_is_refused(self):
        up = self.of(self.install(), SignedSource({"2.3.0": self.zip_of(self.NEW)}))
        plan = up.plan("2.3.0", {})
        self.assertEqual(self.codes(plan).get("sig_version"), "block")

    def test_an_older_release_without_signature_only_warns_and_a_wrong_one_still_blocks(self):
        root = self.install("2.0.4")
        plan = self.of(root, SignedSource({"2.0.8": self.zip_of("2.0.8")}, seed=None)).plan("2.0.8", {})
        self.assertEqual((self.codes(plan).get("sig_unsigned"), plan["blocked"]), ("warn", False))
        plan = self.of(root, SignedSource({"2.0.8": self.zip_of("2.0.8")}, seed=OTHER_SEED)).plan("2.0.8", {})
        self.assertEqual((self.codes(plan).get("sig_bad"), plan["blocked"]), ("block", True))

    def test_a_zip_downloaded_by_hand_needs_its_two_files_next_to_it(self):
        zip_path = self.zip_of(self.NEW)
        root = self.install()
        self.assertTrue(self.of(root, mu.LocalZipSource(zip_path)).plan(None, {})["blocked"])
        sums = f"{hashlib.sha256(zip_path.read_bytes()).hexdigest()}  {mu.ZIP_NAME}\n".encode("ascii")
        (self.tmp / mu.SUMS_NAME).write_bytes(sums)
        (self.tmp / mu.SIG_NAME).write_text(signature_line(SEED, sums), encoding="ascii")
        named = self.tmp / mu.ZIP_NAME
        shutil.copyfile(zip_path, named)
        plan = self.of(root, mu.LocalZipSource(named)).plan(None, {})
        self.assertEqual((plan["signature"], plan["blocked"]), ("valid", False))

    def test_the_texts_of_the_signature_exist_in_the_eight_languages(self):
        for key in ("c.sig_ok", "c.sig_bad", "c.sig_missing", "c.sig_unsigned", "c.sig_version"):
            for lang in mu.LANGS:
                self.assertTrue(mu._CAT[lang][key], (lang, key))


class TheFilesOfABuild(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="build_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def test_both_bills_of_materials_are_reproducible_and_list_files_and_optional_libraries(self):
        entries = {"github_actions_monitor/a.py": b"a", "github_actions_monitor/b.py": b"b"}
        first = sbom.documents("2.2.0", "github_actions_monitor.zip", "ab" * 32, entries)
        self.assertEqual(first, sbom.documents("2.2.0", "github_actions_monitor.zip", "ab" * 32, dict(reversed(list(entries.items())))))
        cdx, spdx = json.loads(first[sbom.CDX_NAME]), json.loads(first[sbom.SPDX_NAME])
        self.assertEqual((cdx["bomFormat"], cdx["specVersion"], spdx["spdxVersion"]), ("CycloneDX", "1.5", "SPDX-2.3"))
        for names in ({c["name"] for c in cdx["components"]}, {p["name"] for p in spdx["packages"]}):
            self.assertTrue({"cryptography", "rich", "textual"} <= names)
        self.assertEqual([f["fileName"] for f in spdx["files"]], ["./github_actions_monitor/a.py", "./github_actions_monitor/b.py"])
        self.assertEqual(cdx["metadata"]["component"]["version"], "2.2.0")

    def test_sha256sums_names_the_zip_first_and_the_three_files_next_to_it(self):
        import make_release
        target = self.tmp / "github_actions_monitor.zip"
        target.write_bytes(b"zip")
        (self.tmp / "old.ed25519.sig").write_text("stale", encoding="ascii")
        made = make_release.write_release_files(self.tmp, "2.2.0", target, {"github_actions_monitor/a.py": b"a"})
        listed, bad = release_verify.parse_sums((self.tmp / "SHA256SUMS").read_text(encoding="ascii"))
        self.assertEqual(bad, [])
        self.assertEqual(made[0][0], "github_actions_monitor.zip")
        self.assertEqual(sorted(listed), sorted(["github_actions_monitor.zip", "monitor_updater.py", sbom.CDX_NAME, sbom.SPDX_NAME]))
        self.assertFalse((self.tmp / "old.ed25519.sig").exists())
        loose = (self.tmp / "monitor_updater.py").read_text(encoding="utf-8")
        self.assertIn("EMBEDDED_REGISTRY = json.loads(", loose)
        compile(loose, "monitor_updater.py", "exec")

    def test_the_drive_d_is_refused_except_on_a_runner_of_github(self):
        import make_release
        self.assertTrue(make_release.drive_refused(r"d:\out", {}))
        self.assertFalse(make_release.drive_refused("D:/runner/temp/release", {"GITHUB_ACTIONS": "true"}))
        self.assertFalse(make_release.drive_refused(r"C:\out", {}))

    def test_signing_with_openssl_and_checking_the_set(self):
        openssl = shutil.which("openssl")
        if not openssl:
            self.skipTest("openssl is not installed")
        key = self.tmp / "test_key.pem"
        if subprocess.run([openssl, "genpkey", "-algorithm", "ed25519", "-out", str(key)], capture_output=True).returncode != 0:
            self.skipTest("this openssl makes no Ed25519 key")
        public = subprocess.run([openssl, "pkey", "-in", str(key), "-pubout", "-outform", "DER"], capture_output=True, check=True).stdout[-32:].hex()
        folder = signed_folder(self.tmp / "r", {"github_actions_monitor.zip": b"zip", "monitor_updater.py": b"print()"}, seed=None)
        try:
            sign_release.sign(folder, key)
        except SystemExit:
            self.skipTest("this openssl cannot sign a file in one step (-rawin)")
        keys = [keyring.clean_entry(entry(public))]
        self.assertEqual(sign_release.verify(folder, keys), [])
        self.assertTrue(release_verify.verify_release(folder, keys)["ok"])
        self.assertEqual(release_signature_of(folder, public), "valid")
        self.assertTrue(sign_release.verify(folder))      # the key of the test is not the key of the product
        (folder / ("monitor_updater.py" + keyring.SIGNATURE_SUFFIX)).unlink()
        self.assertIn("monitor_updater.py: signature absent", sign_release.verify(folder, keys))


def release_signature_of(folder, public):
    return mu.release_signature(folder, hashlib.sha256((Path(folder) / mu.ZIP_NAME).read_bytes()).hexdigest(), (public,))


class TheSummaryOfARelease(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="summary_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def write(self, version, data):
        path = release_summary.path_of(version, self.tmp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_it_is_required_from_2_2_0_in_the_eight_languages(self):
        self.assertEqual(release_summary.problems("2.1.9", self.tmp), [])
        self.assertTrue(release_summary.problems("2.2.0", self.tmp))
        self.write("2.2.0", {lang: "text" for lang in release_summary.LANGS if lang != "pt"})
        self.assertEqual(len(release_summary.problems("2.2.0", self.tmp)), 1)
        self.write("2.2.0", {lang: "text " + lang for lang in release_summary.LANGS})
        self.assertEqual(release_summary.problems("2.2.0", self.tmp), [])

    def test_the_blocks_of_the_notes_are_what_the_update_check_reads(self):
        self.write("2.2.0", {lang: f"Summary {lang}\n- one" for lang in release_summary.LANGS})
        body = "## Notes\n\ntext\n\n" + release_summary.blocks("2.2.0", self.tmp)
        notes = updatecheck.parse_notes(body.replace("\n", "\r\n"))
        self.assertEqual(sorted(notes), sorted(updatecheck.LANGS))
        self.assertEqual(notes["es"], "Summary es\n- one")
        self.assertEqual(updatecheck.pick_notes(notes, "de-DE"), "Summary de\n- one")
        self.assertEqual(updatecheck.pick_notes({"en": "x"}, "ja"), "x")
        self.assertEqual(updatecheck.pick_notes({}, "ja"), "")

    def test_the_notes_travel_with_the_answer_and_a_dismissed_version_stays_dismissed(self):
        state = self.tmp / "update_check.json"
        body = {"tag_name": "v9.0.0", "body": "<!-- whats-new:en\nNew things\n-->\n<!-- whats-new:xx\nno\n-->"}
        first = updatecheck.check({}, "2.1.8", lambda endpoint: body, now=1, state_file=state)
        self.assertEqual((first["notes"], first["dismissed"]), ({"en": "New things"}, False))
        self.assertFalse(updatecheck.dismiss("nightly", state))
        self.assertTrue(updatecheck.dismiss("9.0.0", state))
        again = updatecheck.check({}, "2.1.8", lambda endpoint: body, now=1 + updatecheck.INTERVAL, state_file=state)
        self.assertEqual((again["dismissed"], again["notes"]), (True, {"en": "New things"}))
        newer = updatecheck.check({}, "2.1.8", lambda endpoint: dict(body, tag_name="v9.0.1"), now=1 + 2 * updatecheck.INTERVAL, state_file=state)
        self.assertEqual((newer["latest"], newer["dismissed"]), ("9.0.1", False))


class TheWorkflows(unittest.TestCase):
    def text(self, name):
        path = ROOT / ".github" / "workflows" / name
        if not path.is_file():
            self.skipTest("the workflows are not part of the package")
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_every_action_is_of_github_and_pinned_by_commit(self):
        for name in ("release-build.yml", "repo-hygiene.yml"):
            used = [line.split("uses:", 1)[1].split("#")[0].strip() for line in self.text(name).splitlines() if line.strip().lstrip("- ").startswith("uses:")]
            self.assertTrue(used, name)
            for action in used:
                self.assertRegex(action, r"^(actions|github)/[A-Za-z0-9._/-]+@[0-9a-f]{40}$")

    def test_the_key_is_only_in_the_job_that_signs_and_nothing_is_published(self):
        source = self.text("release-build.yml")
        before, signing = source.split("\n  sign:\n", 1)
        self.assertNotIn("secrets.", before)
        self.assertIn("environment: release-signing", signing)
        self.assertIn("inputs.sign", signing)
        self.assertIn("merge-base --is-ancestor HEAD origin/main", signing)
        for forbidden in ("gh release", "git tag", "git push", "contents: write", "set -x"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
