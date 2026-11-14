# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor does not open the network before the first administrator exists.

With the team mode on and the network mode on, no user yet: the start stops with a message that says how to create the first administrator from this computer. In the local mode, with the team mode
off, or once a user exists, the start goes on.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_auth as ta  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402

NETWORK = {"auth": {"enabled": True}, "listen": {"network": True, "host": "0.0.0.0"}}


class NeedsAnAdministrator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = ta.new_storage(Path(self.tmp.name) / "data")
        self.addCleanup(self.storage.close)
        auth.use_storage(self.storage)
        self.addCleanup(auth.use_storage, None)

    def test_the_network_with_the_team_mode_and_nobody_is_refused(self):
        self.assertTrue(am.network_needs_administrator(NETWORK))

    def test_the_local_mode_and_the_individual_mode_start(self):
        self.assertFalse(am.network_needs_administrator({"auth": {"enabled": True}}), "local: the bootstrap is done from this computer")
        self.assertFalse(am.network_needs_administrator({"auth": {"enabled": True}, "listen": {"network": False}}))
        self.assertFalse(am.network_needs_administrator({"listen": {"network": True, "host": "0.0.0.0"}}), "no team mode: the access token of the network mode is the protection")
        self.assertFalse(am.network_needs_administrator({"auth": {"enabled": "yes"}, "listen": {"network": True}}), "only a real true turns the team mode on")

    def test_with_an_administrator_the_network_starts(self):
        user, code = auth.create_user(self.storage, "root", "correct horse battery", "admin")
        self.assertEqual(code, "")
        self.assertFalse(am.network_needs_administrator(NETWORK))

    def test_a_storage_that_cannot_be_read_does_not_stop_the_start(self):
        with mock.patch.object(auth, "users_exist", side_effect=OSError("disk")):
            self.assertFalse(am.network_needs_administrator(NETWORK))

    def test_main_stops_with_the_message_and_does_not_listen(self):
        printed = []
        config_file = Path(self.tmp.name) / "actions_monitor.json"
        config_file.write_text(json.dumps(NETWORK), encoding="utf-8")
        with mock.patch.object(sys, "argv", ["actions_monitor.py"]), mock.patch.object(am.toolconfig, "raw_config", lambda: NETWORK), mock.patch.object(am, "accounts_cli", lambda argv: None), \
                mock.patch.object(am.paths, "ensure", lambda *a: None), mock.patch.object(am.rootmigrate, "auto", lambda *a: None), \
                mock.patch("github_actions_monitor.integrations.ai_index.write", lambda *a, **k: None), \
                mock.patch("builtins.print", lambda *a, **k: printed.append(" ".join(str(x) for x in a))), mock.patch.object(am, "QuietServer", side_effect=AssertionError("must not listen")):
            code = am.main()
        self.assertEqual(code, 1)
        self.assertTrue(any("no administrator yet" in line and "listen.network" in line for line in printed), printed)

    def test_main_goes_on_in_the_local_mode(self):
        gone = RuntimeError("went on")
        with mock.patch.object(sys, "argv", ["actions_monitor.py"]), mock.patch.object(am.toolconfig, "raw_config", lambda: {"auth": {"enabled": True}}), mock.patch.object(am, "accounts_cli", lambda argv: None), \
                mock.patch.object(am.paths, "ensure", lambda *a: None), mock.patch.object(am.rootmigrate, "auto", lambda *a: None), mock.patch("github_actions_monitor.integrations.ai_index.write", lambda *a, **k: None), \
                mock.patch.object(am, "lite_requested", lambda: False), mock.patch("github_actions_monitor.accounts.accounts.layout", side_effect=gone):
            with self.assertRaises(RuntimeError) as raised:
                am.main()
        self.assertIs(raised.exception, gone, "the start passed the check and reached the choice of layout")

    def test_the_message_is_in_the_eight_languages_and_names_the_way_out(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            data = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("listen.network", data["mon.network_needs_admin"], lang)


if __name__ == "__main__":
    unittest.main()
