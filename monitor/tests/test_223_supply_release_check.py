# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The check of an installation against the bill of materials of a signed release, the attestation (never "invalid" without the means to ask), the download that is off by default, the warning before a key
expires, the announcement of a new key and the pinned downloads of the workflows."""
import argparse
import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import sbom  # noqa: E402
import test_220_release_signing as signing  # noqa: E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.families.supply import installed
from github_actions_monitor.families.supply import supply_cli as commands  # noqa: E402
from github_actions_monitor.security import keyring  # noqa: E402

VERSION = installed.TOOL_VERSION


def args(**options):
    base = dict(folder="", installed=False, attestations=False, fetch=False)
    base.update(options)
    return {"args": argparse.Namespace(**base)}


class Done:
    def __init__(self, code, err=""):
        self.returncode, self.stderr, self.stdout = code, err, ""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.root = self.folder / "install"
        (self.root / "bin").mkdir(parents=True)
        (self.root / "bin" / "a.py").write_bytes(b"one")
        self.entries = {"github_actions_monitor/bin/a.py": b"one"}

    def release(self, version=VERSION):
        made = sbom.documents(version, installed.ZIP_NAME, "ab" * 32, self.entries)
        files = {installed.ZIP_NAME: b"zip", installed.SPDX_NAME: made[sbom.SPDX_NAME]}
        return signing.signed_folder(self.folder / "release", files)


class TheInstallation(Base):
    def test_it_matches_or_names_what_differs(self):
        folder = self.release()
        found = installed.compare_installed(folder, self.root)
        self.assertEqual((found["ok"], found["checked"]), (True, 1))
        (self.root / "bin" / "a.py").write_bytes(b"two")
        self.assertEqual(installed.compare_installed(folder, self.root)["changed"], ["bin/a.py"])
        (self.root / "bin" / "a.py").unlink()
        self.assertEqual(installed.compare_installed(folder, self.root)["missing"], ["bin/a.py"])

    def test_the_bill_of_another_version_or_with_a_path_out_of_the_product_is_refused(self):
        self.assertEqual(installed.compare_installed(self.release("0.0.1"), self.root)["reason"], "other_version")
        self.entries = {"github_actions_monitor/../outside": b"x"}
        self.assertEqual(installed.compare_installed(self.release(), self.root)["reason"], "no_sbom")
        self.assertEqual(installed.compare_installed(self.folder / "nothing", self.root)["reason"], "no_sbom")

    def test_a_bill_of_materials_without_a_valid_signature_is_not_compared(self):
        folder = self.release()      # signed with the key of the tests, which the product does not trust
        report, lines, code = commands.verify_release_command(args(folder=str(folder), installed=True))
        self.assertEqual((report["signature"], code), ("invalid", commands.DEGRADED))
        self.assertNotIn("installed", report)
        self.assertEqual(commands.doctor_release(str(folder))[2], commands.DEGRADED)
        self.assertEqual(commands.doctor_release(str(self.folder / "nothing"))[2], commands.USAGE)

    def test_the_attestation_is_never_invalid_without_the_means_to_ask(self):
        folder = self.release()
        self.assertEqual(installed.attestation(self.folder / "nothing"), "not_checked")
        self.assertEqual(installed.attestation(folder, lambda c: Done(0)), "verified")
        self.assertEqual(installed.attestation(folder, lambda c: Done(1, "no attestations found")), "failed")
        self.assertEqual(installed.attestation(folder, lambda c: Done(1, "dial tcp: no such host")), "not_checked")

        def broken(command):
            raise OSError("no gh")
        self.assertEqual(installed.attestation(folder, broken), "not_checked")


class TheDownload(Base):
    def test_it_is_off_by_default(self):
        self.assertFalse(actions_monitor.DEFAULTS["ops"]["verify_release"]["fetch"])
        with mock.patch.object(commands.toolconfig, "raw_config", lambda: {}), mock.patch.object(installed, "fetch") as called:
            self.assertEqual(commands.verify_release_command(args(fetch=True))[2], commands.USAGE)
        called.assert_not_called()

    def test_it_takes_the_files_of_the_installed_version_only(self):
        class Source:
            got = []

            def releases(self):
                assets = {name: {"url": "https://github.com/" + name} for name in (installed.ZIP_NAME, "SHA256SUMS", "other.bin")}
                return [{"version": VERSION, "assets": assets}]

            def _download(self, url, dest, limit):
                self.got.append(Path(dest).name)

        self.assertEqual(installed.fetch(self.folder, Source()), 2)
        self.assertEqual(sorted(Source.got), sorted(["SHA256SUMS", installed.ZIP_NAME]))
        with self.assertRaises(ValueError):
            installed.fetch(self.folder, Source(), version="0.0.1")


class TheKeys(Base):
    def test_a_key_that_is_about_to_expire_is_told(self):
        keys = [keyring.clean_entry(signing.entry(expires="2031-03-01")), keyring.clean_entry(signing.entry(signing.OTHER_PUBLIC, id="later", expires="2032-01-01"))]
        self.assertEqual(keyring.expiring(keys, date(2031, 1, 30)), [("test", 30)])
        self.assertEqual(keyring.expiring(keys, date(2030, 1, 1)), [])

    def test_a_new_key_is_announced_with_the_signatures_of_both(self):
        path = self.folder / "rotation.json"
        data = json.dumps({"new": signing.entry(signing.OTHER_PUBLIC, id="next"), "replaces": "test"}).encode("utf-8")
        path.write_bytes(data)
        keys = [keyring.clean_entry(signing.entry())]
        self.assertEqual(keyring.verify_rotation(path, keys)["result"], "absent")
        (self.folder / ("rotation.json" + keyring.SIGNATURE_SUFFIX)).write_text(signing.signature_line(signing.SEED, data), encoding="ascii")
        self.assertEqual(keyring.verify_rotation(path, keys)["result"], "absent")
        (self.folder / ("rotation.json" + keyring.ROTATION_SUFFIX)).write_text(signing.signature_line(signing.OTHER_SEED, data), encoding="ascii")
        self.assertEqual(keyring.verify_rotation(path, keys), {"result": "valid", "new": "next", "replaces": "test"})
        (self.folder / ("rotation.json" + keyring.ROTATION_SUFFIX)).write_text(signing.signature_line(signing.SEED, data), encoding="ascii")
        self.assertEqual(keyring.verify_rotation(path, keys)["result"], "invalid")
        self.assertEqual(keyring.verify_rotation(path)["result"], "unknown_key")


class ThePinnedDownloads(unittest.TestCase):
    def test_every_tool_has_its_version_and_its_sha_and_the_workflows_use_the_script(self):
        script = ROOT / "tools" / "fetch_pinned.sh"
        if not script.is_file():
            self.skipTest("the tools of the repository are not in this folder")
        text = script.read_text(encoding="utf-8")
        urls, shas = re.findall(r'url="(https://github\.com/[^"]+)"', text), re.findall(r'sha="([0-9a-f]{64})"', text)
        self.assertEqual((len(urls), len(shas)), (3, 3))
        self.assertTrue(all("/releases/download/v" in url for url in urls))
        self.assertIn("sha256sum -c -", text)
        for name, tool in (("release-build.yml", "cosign"), ("release-image.yml", "cosign"), ("repo-hygiene.yml", "osv-scanner"), ("repo-hygiene.yml", "scorecard")):
            self.assertIn("tools/fetch_pinned.sh " + tool, (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"), name)


if __name__ == "__main__":
    unittest.main()
