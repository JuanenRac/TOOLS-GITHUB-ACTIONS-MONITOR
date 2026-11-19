# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The updater from the first byte to the last, against a false release server on this computer: the real downloader (GitHubSource) fetches the SHA256SUMS and the zip over HTTP, the real checks
verify them and the real engine applies, goes wrong and goes back. Cases: an intact release, a hash that does not match, a zip that tries to leave its folder (path, absolute path, link), a download
that is cut, one that is too big, a redirect to a host that is not allowed, two updaters at once, and a failure injected in each phase of the update (the installation must be as it was). The one
thing that is NOT defended is also written down: a zip and its sums replaced together on the allowed host are accepted, because the trust rests on GitHub. Nothing here reaches the network."""
import hashlib
import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_66_updater_engine as base  # noqa: E402

mu = base.mu
PLAN = {}      # what the false server does, set by each test


class Server(BaseHTTPRequestHandler):
    def do_GET(self):    # noqa: N802
        kind = self.path.strip("/")
        PLAN.setdefault("seen", []).append(kind)
        if PLAN.get("delay"):
            time.sleep(PLAN["delay"])
        if kind == "redirect":
            self.send_response(302)
            self.send_header("Location", PLAN["redirect_to"])
            self.end_headers()
            return
        body = PLAN["zip"] if kind == "zip" else PLAN["sums"]
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body[:PLAN["cut"]] if kind == "zip" and PLAN.get("cut") else body)      # a download that promises more than it sends is a cut one

    def log_message(self, *args):
        pass


class WireSource(mu.GitHubSource):
    """The real downloader; only the list of releases comes from the test, and the address check lets this computer through."""

    def __init__(self, base_url, version, **kw):
        super().__init__(**kw)
        self.base_url, self.version = base_url, version

    def _page(self, page):
        if page > 1:
            return []
        assets = [{"name": mu.ZIP_NAME, "browser_download_url": self.base_url + "/" + PLAN.get("zip_path", "zip"), "size": 1}, {"name": mu.SUMS_NAME, "browser_download_url": self.base_url + "/sums", "size": 1}]
        return [{"tag_name": "v" + self.version, "name": "x", "assets": assets, "prerelease": False, "draft": False, "body": ""}]


def only_this_computer(url):
    return str(url).startswith("http://127.0.0.1:")


class Wire(base.Base):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Server)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(5)

    def setUp(self):
        super().setUp()
        PLAN.clear()
        self.real_host_ok = mu.host_ok
        patch = mock.patch.object(mu, "host_ok", only_this_computer)
        patch.start()
        self.addCleanup(patch.stop)
        self.root = base.make_install(self.tmp / "i", "2.0.4", base.config_from_defaults("2.0.4"))
        self.before = base.tree_hash(self.root)

    def serve(self, data=None, sums=None):
        data = data if data is not None else (self.tmp / "good.zip").read_bytes() if (self.tmp / "good.zip").is_file() else base.build_zip(self.tmp / "good.zip", "2.0.8").read_bytes()
        PLAN["zip"] = data
        PLAN["sums"] = (sums if sums is not None else f"{hashlib.sha256(data).hexdigest()}  {mu.ZIP_NAME}\n").encode()

    def updater(self, version="2.0.8", **kw):
        return mu.Updater(self.root, WireSource(self.url, version), backups=self.tmp / "copies", env={}, probe=base.NO_MONITOR, **kw)

    def bad_zip(self, name, link=False):
        path = self.tmp / "bad.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel, data in sorted(base.product_files("2.0.8").items()):
                zf.writestr(zipfile.ZipInfo(f"github_actions_monitor/{rel}", (2026, 1, 1, 0, 0, 0)), data)
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            if link:
                info.external_attr = 0o120777 << 16
            zf.writestr(info, "../../outside" if link else "evil")
        return path.read_bytes()

    # --- the intact release
    def test_an_intact_release_goes_over_the_wire_and_is_applied(self):
        self.serve()
        report = self.updater().apply("2.0.8", {})
        self.assertTrue(report["ok"], report)
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")
        self.assertEqual(sorted(set(PLAN["seen"])), ["sums", "zip"])
        self.assertEqual(report["plan"]["verified"], "sums")
        self.assertEqual(report["plan"]["sha256"], hashlib.sha256(PLAN["zip"]).hexdigest())

    # --- what does not match or is not safe changes nothing
    def test_a_hash_that_does_not_match_changes_nothing(self):
        self.serve(sums=f"{'0' * 64}  {mu.ZIP_NAME}\n")
        report = self.updater().apply("2.0.8", {})
        self.assertNotEqual(report["code"], mu.OK)
        self.assertEqual(base.tree_hash(self.root), self.before)

    def test_a_release_without_sums_is_not_applied(self):
        self.serve(sums="nothing useful here\n")
        report = self.updater().apply("2.0.8", {})
        self.assertNotEqual(report["code"], mu.OK)
        self.assertEqual(base.tree_hash(self.root), self.before)

    def test_a_zip_that_leaves_its_folder_is_refused_with_the_hash_right(self):
        for name, link in (("github_actions_monitor/../../escape.txt", False), ("/etc/escape.txt", False), ("C:/escape.txt", False), ("github_actions_monitor/link", True)):
            self.serve(self.bad_zip(name, link))
            report = self.updater().apply("2.0.8", {})
            self.assertNotEqual(report["code"], mu.OK, name)
            self.assertEqual(base.tree_hash(self.root), self.before, name)
            self.assertFalse((self.tmp / "escape.txt").exists())
            shutil.rmtree(str(self.tmp / "copies"), ignore_errors=True)

    def test_a_zip_and_its_sums_replaced_together_are_accepted_because_the_trust_rests_on_the_host(self):
        # the known limit, written down so that nobody believes the opposite: the hash proves that the zip is the one that the release lists, not who made the release.
        # What stops this in real life is the list of allowed hosts (below) and the account of the repository on GitHub.
        self.serve(base.build_zip(self.tmp / "other.zip", "2.0.8", extra={"docs/README.md": b"replaced\n"}).read_bytes())
        report = self.updater().apply("2.0.8", {})
        self.assertTrue(report["ok"], report)

    def test_a_host_that_is_not_allowed_is_refused_before_the_connection(self):
        for url in ("http://127.0.0.1:1/zip", "https://github.com.evil.example/x.zip", "https://evilgithub.com/x.zip", "https://127.0.0.1/x.zip", "ftp://github.com/x.zip"):
            self.assertFalse(self.real_host_ok(url), url)
        self.assertTrue(self.real_host_ok("https://github.com/o/r/releases/download/v1/x.zip"))
        self.assertTrue(self.real_host_ok("https://objects.githubusercontent.com/x"))
        with self.assertRaises(mu.UpdaterError):      # and the downloader itself refuses it, with the check of the product and not the one of the test
            with mock.patch.object(mu, "host_ok", self.real_host_ok):
                mu.GitHubSource()._download("http://127.0.0.1:1/zip", self.tmp / "x.zip", 100)

    def test_a_redirect_to_another_host_is_refused(self):
        self.serve()
        PLAN["zip_path"] = "redirect"
        PLAN["redirect_to"] = self.url.replace("127.0.0.1", "localhost") + "/zip"
        report = self.updater().apply("2.0.8", {})
        self.assertNotEqual(report["code"], mu.OK)
        self.assertEqual(base.tree_hash(self.root), self.before)

    def test_a_download_that_is_cut_changes_nothing(self):
        self.serve()
        PLAN["cut"] = len(PLAN["zip"]) // 2      # the header promises the whole zip and the connection ends at half of it
        try:
            report = self.updater().apply("2.0.8", {})
        except Exception as error:      # noqa: BLE001 - what matters is below: whatever the way it ends, the installation is as it was
            report = {"code": "raised", "error": repr(error)}
        self.assertNotEqual(report["code"], mu.OK)
        self.assertEqual(base.tree_hash(self.root), self.before)

    def test_a_download_larger_than_the_limit_is_refused(self):
        self.serve()
        with mock.patch.object(mu, "MAX_ZIP", 200):
            report = self.updater().apply("2.0.8", {})
        self.assertNotEqual(report["code"], mu.OK)
        self.assertEqual(base.tree_hash(self.root), self.before)

    # --- two updaters at once
    def test_two_updaters_at_once_apply_it_once_and_leave_a_whole_installation(self):
        self.serve()
        PLAN["delay"] = 0.3
        reports, errors = [], []

        def go():
            try:
                reports.append(self.updater().apply("2.0.8", {}))
            except Exception as error:      # noqa: BLE001
                errors.append(repr(error))
        threads = [threading.Thread(target=go) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(120)
        self.assertEqual(errors, [])
        self.assertEqual(len(reports), 2)
        self.assertEqual(sum(1 for r in reports if r["ok"] and r["steps"]), 1, [r["code"] for r in reports])      # one did the work; the other was kept apart or found nothing to do
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")
        self.assertEqual(sum(1 for line in (self.root / "data" / "update_history.jsonl").read_text(encoding="utf-8").splitlines() if '"result": "ok"' in line), 1)


class EveryPhase(base.Base):
    """A failure in each phase, with an error and with an interruption (KeyboardInterrupt): the installation is as it was and the copy is there."""
    PHASES = (("backup", "_snapshot"), ("copy", "_copy_product"), ("retire", "_retire"), ("launchers", "_launchers"), ("config", "_migrate_configs"), ("layout", "_layout"), ("verify", "_verify"))

    def setUp(self):
        super().setUp()
        self.root = base.make_install(self.tmp / "i", "2.0.4", base.config_from_defaults("2.0.4"))
        self.before = base.tree_hash(self.root)

    def test_every_phase_that_fails_is_rolled_back(self):
        for phase, method in self.PHASES:
            for failure in (RuntimeError("boom"), OSError("disk"), KeyboardInterrupt()):
                shutil.rmtree(str(self.tmp / "copies"), ignore_errors=True)
                with mock.patch.object(mu.Updater, method, side_effect=failure):
                    report = self.updater(self.root).apply("2.0.8", {})
                label = (phase, type(failure).__name__)
                self.assertEqual(report["code"], mu.ROLLED_BACK, label)
                self.assertTrue(report["rolled_back"], label)
                self.assertEqual(base.tree_hash(self.root), self.before, label)
                self.assertEqual(mu.read_tool_version(self.root), "2.0.4", label)
                self.assertTrue((Path(report["backup"]) / "report.json").is_file(), label)
                journal = json.loads((Path(report["backup"]) / "journal.json").read_text(encoding="utf-8"))
                self.assertEqual(journal["status"], "rolled_back", label)
                self.assertNotIn(phase, journal["steps"], label)      # the journal says where it stopped: the phase that failed was not marked as done

    def test_a_failure_while_unpacking_is_an_answer_and_changes_nothing(self):
        for failure in (OSError("disk full"), zipfile.BadZipFile("damaged")):
            with mock.patch.object(mu, "extract_zip", side_effect=failure):
                report = self.updater(self.root).apply("2.0.8", {})
            self.assertEqual(report["code"], mu.FETCH_FAILED, failure)
            self.assertEqual(base.tree_hash(self.root), self.before)

    def updater(self, root):
        return mu.Updater(root, base.FakeSource({"2.0.8": base.build_zip(self.tmp / "z.zip", "2.0.8")}), backups=self.tmp / "copies", env={}, probe=base.NO_MONITOR)


if __name__ == "__main__":
    unittest.main()
