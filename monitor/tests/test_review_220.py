# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Limits that the parts of 2.2.0 must hold: a restriction of the monitor also binds the plugins of other people, a token never goes where it should not, an unsigned release cannot carry a signed
version, a damaged state file is read without an exception and the one automatic re-run stays one."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_220_release_signing as signing  # noqa: E402
from github_actions_monitor.families.actions import actions_engine  # noqa: E402
from github_actions_monitor.integrations import compliance_audit_export as export  # noqa: E402
from github_actions_monitor.integrations import ghactions  # noqa: E402
from github_actions_monitor.integrations.external_ci import extci_engine  # noqa: E402
from github_actions_monitor.integrations.external_ci.extci_fetch import Failed, Reader  # noqa: E402
from github_actions_monitor.plugins import plugin_manifest as manifests  # noqa: E402
from github_actions_monitor.plugins import plugin_worker  # noqa: E402
from github_actions_monitor.security import compliance_guard, netguard  # noqa: E402

mu = signing.mu


def folder(case):
    made = Path(tempfile.mkdtemp(prefix="review220_"))
    case.addCleanup(shutil.rmtree, str(made), True)
    return made


class PluginsUnderARestriction(unittest.TestCase):
    def run_plugin(self, require=None):
        where = folder(self)
        marker = where / "loaded"
        code = f"open({str(marker)!r}, 'w').close()\ndef run(ctx):\n    return {{'alerts': []}}\n"
        (where / "plugin.py").write_text(code, encoding="utf-8")
        manifest = manifests.parse(json.dumps({"name": "demo", "version": "1.0.0", "api_compat": "1", "author": "a", "description": "d", "trust": "third_party", "entry": "plugin.py",
                                               "permissions": [], "get_paths": []}))
        try:
            _answer, isolation = plugin_worker.run(where, manifest, lambda method, args: None, timeout_s=60, require_isolation=require)
        except plugin_worker.WorkerError as error:
            return error.code, marker.exists(), False
        return "", marker.exists(), isolation["network_isolated"]

    def check(self, outcome):
        code, loaded, isolated = outcome
        if code:      # the system could not take the network away (always on Windows and macOS): not one line of the plugin ran
            self.assertEqual((code, loaded), ("restricted", False))
        else:
            self.assertTrue(isolated and loaded)
        if sys.platform in ("win32", "darwin"):
            self.assertEqual(code, "restricted")

    def test_a_plugin_that_would_keep_the_network_is_not_loaded(self):
        self.check(self.run_plugin(require=True))

    def test_what_the_process_holds_is_the_default(self):
        with mock.patch.dict(compliance_guard.STATE, {"strict": True}):
            self.check(self.run_plugin())

    def test_with_no_restriction_it_runs_as_before(self):
        self.assertEqual(self.run_plugin(require=False)[:2], ("", True))


class TokensOfExternalSources(unittest.TestCase):
    LINE = "gitlab;repo=m;url=https://ci.example.org;project=a/b;token_env={}"

    def test_no_secret_of_the_system_or_of_the_monitor_can_be_named(self):
        for name in ("GH_TOKEN", "github_token", "MONITOR_ACCESS_TOKEN", "MONITOR_WEBHOOK_SECRET", "PATH"):
            self.assertEqual(extci_engine.parse(self.LINE.format(name)), (None, "token_env"), name)
        self.assertIsNotNone(extci_engine.parse(self.LINE.format("MY_CI_VALUE"))[0])

    def test_nor_one_that_another_setting_names(self):
        config = {"ai": {"api_key_env": "MY_AI_VALUE"}, "external_ci": {"enabled": True, "sources": [self.LINE.format("MY_AI_VALUE")]}}
        self.assertEqual(extci_engine.configured(config), [])
        self.assertEqual(extci_engine.status(config)["invalid"][0]["reason"], "token_env")
        self.assertEqual(extci_engine.probe(config, self.LINE.format("MY_AI_VALUE"))["reason"], "token_env")

    def test_without_tls_a_token_only_goes_to_a_private_address(self):
        cfg = dict(extci_engine.settings({}), allow_private_targets=True)
        with mock.patch.dict(os.environ, {"MY_CI_VALUE": "sample"}):
            public = Reader({"kind": "gitlab", "url": "http://203.0.114.7", "token_env": "MY_CI_VALUE"}, cfg, opener=lambda *a, **k: self.fail("sent"))
            with self.assertRaises(Failed) as caught:
                public.json("/x")
            self.assertEqual(caught.exception.reason, "token_clear")
            self.assertEqual(Reader({"kind": "gitlab", "url": "x", "token_env": "MY_CI_VALUE"}, cfg)._headers("http://10.0.0.7/x")["PRIVATE-TOKEN"], "sample")

    def test_only_private_judges_every_address_of_a_name(self):
        def answer(*addresses):
            return lambda host, port, **kwargs: [(0, 0, 0, "", (a, port)) for a in addresses]
        self.assertTrue(netguard.only_private("http://nas/in", answer("192.168.1.4")))
        self.assertFalse(netguard.only_private("http://mixed/in", answer("192.168.1.4", "93.184.216.34")))
        self.assertFalse(netguard.only_private("http:///in"))

    def test_the_export_of_the_log_follows_the_same_rule(self):
        cfg = dict(export.DEFAULTS, url="http://203.0.114.7/in", token_env="MY_EXPORT_VALUE", allow_private_targets=True)
        with mock.patch.object(netguard, "open_url", side_effect=AssertionError("sent")), self.assertRaises(ValueError):
            export.send_http(cfg, [{"hash": "a"}], env={"MY_EXPORT_VALUE": "sample"})


class DamagedState(unittest.TestCase):
    def test_a_damaged_state_of_the_export_is_read_without_an_exception(self):
        where = folder(self) / "state.json"
        where.write_text(json.dumps({"cursor": "c", "sent": "many", "lost": [1], "backlog_bytes": 1e999, "at": "then", "last_error": 5}), encoding="utf-8")
        state = export.load_state(where)
        self.assertEqual((state["cursor"], state["sent"], state["lost"], state["backlog_bytes"], state["at"]), ("c", 0, 0, 0, 0))


class OneAutomaticReRun(unittest.TestCase):
    def test_what_cannot_be_written_down_is_not_sent(self):
        config = {"teamwork": {"enabled": True, "auto_rerun": True}, "github_actions": {"enabled": True, "allowed": ["rerun_failed"], "writer_lock": False, "preflight": False}}
        runs = [{"repo": "app", "id": 11, "name": "ci", "status": "completed", "conclusion": "timed_out", "attempt": 1, "fork": False, "started": "2026-01-01T00:00:00Z"}]
        now = 1767226000.0      # a few minutes after the run started
        with mock.patch.object(actions_engine, "state_file", return_value=folder(self) / "s.json"), mock.patch.object(actions_engine, "save", return_value=False), \
                mock.patch.object(ghactions, "execute", side_effect=AssertionError("sent")):
            self.assertEqual(actions_engine.auto_rerun(config, "me", runs, lambda *a: (0, "", ""), now), [])


class TheReleaseWorkflow(unittest.TestCase):
    def test_an_incomplete_draft_is_never_published(self):
        path = HERE.parent / ".github" / "workflows" / "release-image.yml"
        if not path.is_file():
            self.skipTest("the workflows are not part of the package")
        step = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertIn("SHA256SUMS.ed25519.sig", step.split("--draft=false", 1)[0])


class UnsignedRelease(signing.base.Base):
    def test_an_unsigned_release_with_an_older_number_cannot_carry_a_signed_version(self):
        root = signing.base.make_install(self.tmp / "i", "2.0.4", signing.base.config_from_defaults("2.0.8"))
        before = signing.base.tree_hash(root)
        up = mu.Updater(root, signing.SignedSource({"2.1.9": self.zip_of("2.2.0")}, seed=None), backups=self.tmp / "copies", env={}, probe=signing.base.NO_MONITOR, keys=(signing.PUBLIC,))
        plan = up.plan("2.1.9", {})
        self.assertEqual(({c["code"]: c["severity"] for c in plan["checks"]}.get("sig_missing"), plan["blocked"]), ("block", True))
        self.assertFalse(up.apply("2.1.9", {})["ok"])
        self.assertEqual(signing.base.tree_hash(root), before)


if __name__ == "__main__":
    unittest.main()
