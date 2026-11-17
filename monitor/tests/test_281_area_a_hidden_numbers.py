# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The numbers of the hidden names on the wall screens (private-1, private-2...) go to the hidden repositories only, in the order of an HMAC of the name with a key of the installation that lives in a
private file of the data folder, never in the configuration."""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import screens  # noqa: E402

REPOS = ["alfa-publico", "cliente-secreto", "medio-publico", "misterio", "web-publica", "zz-fusion", "beta-privado", "gamma-privado"]
META = {"alfa-publico": {"private": False}, "medio-publico": {"private": False}, "web-publica": {"private": False}, "cliente-secreto": {"private": True}, "beta-privado": {"private": True},
        "gamma-privado": {"private": True}, "zz-fusion": {"private": True}}      # "misterio" has no visibility: private
HIDDEN = ["cliente-secreto", "misterio", "zz-fusion", "beta-privado", "gamma-privado"]


def numbers(key, repos=REPOS, meta=META):
    names = screens.Names(repos, meta, "public", key=key)
    return {r: names.name(r) for r in repos}


class OnlyTheHiddenOnesAreNumbered(unittest.TestCase):
    def test_the_numbers_are_one_to_n_over_the_hidden_repositories_and_nothing_else(self):
        shown = numbers("a" * 32)
        self.assertEqual(sorted(shown[r] for r in HIDDEN), ["private-%d" % n for n in range(1, len(HIDDEN) + 1)])
        self.assertEqual([shown[r] for r in REPOS if r not in HIDDEN], ["alfa-publico", "medio-publico", "web-publica"])

    def test_the_order_is_not_the_alphabetical_one_and_depends_on_the_key(self):
        one, two = numbers("a" * 32), numbers("b" * 32)
        alphabetical = {r: "private-%d" % (i + 1) for i, r in enumerate(sorted(HIDDEN))}
        self.assertNotEqual({r: one[r] for r in HIDDEN}, alphabetical)
        self.assertNotEqual({r: one[r] for r in HIDDEN}, {r: two[r] for r in HIDDEN})
        self.assertEqual(numbers("a" * 32), one, "the same key gives the same numbers")

    def test_a_new_public_repository_does_not_move_the_hidden_ones_and_says_nothing_about_where_they_fall(self):
        before = numbers("a" * 32)
        more = REPOS + ["000-new-public", "zzz-new-public"]
        after = numbers("a" * 32, more, dict(META, **{"000-new-public": {"private": False}, "zzz-new-public": {"private": False}}))
        self.assertEqual({r: before[r] for r in HIDDEN}, {r: after[r] for r in HIDDEN})

    def test_none_numbers_every_repository_the_same_way(self):
        names = screens.Names(REPOS, META, "none", key="a" * 32)
        self.assertEqual(sorted(names.name(r) for r in REPOS), ["repo-%d" % n for n in range(1, len(REPOS) + 1)])


class TheKeyOfTheInstallation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"MONITOR_DATA_DIR": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        saved = screens._KEY[0]
        self.addCleanup(screens._KEY.__setitem__, 0, saved)
        screens._KEY[0] = None
        self.file = Path(self.tmp.name) / screens.KEY_FILE

    def test_it_is_made_once_kept_in_a_private_file_and_read_again_at_the_next_start(self):
        first = screens.installation_key()
        self.assertEqual(self.file.read_text(encoding="utf-8").strip(), first)
        self.assertGreaterEqual(len(first), 32)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)
        screens._KEY[0] = None
        self.assertEqual(screens.installation_key(), first)

    def test_a_damaged_file_is_replaced_and_a_place_that_cannot_be_written_still_gives_a_key(self):
        self.file.write_text("not a key", encoding="utf-8")
        key = screens.installation_key()
        self.assertRegex(key, r"^[0-9a-f]{64}\Z")
        self.assertEqual(self.file.read_text(encoding="utf-8").strip(), key)
        screens._KEY[0] = None
        with mock.patch("github_actions_monitor.security.private_io.write_private", side_effect=OSError("read only")):
            self.file.unlink()
            self.assertRegex(screens.installation_key(), r"^[0-9a-f]{64}\Z")

    def test_the_key_is_not_in_the_configuration_nor_in_any_answer(self):
        from github_actions_monitor.app import actions_monitor, settings_api
        key = screens.installation_key()
        self.assertNotIn("key", " ".join(screens.DEFAULTS))
        self.assertFalse([k for k in settings_api.FIELDS if k.startswith("screens.") and "key" in k.rsplit(".", 1)[1]])
        payload = screens.build("overview", {"repos": ["x"], "repo_meta": {"x": {"private": True}}, "runs": []}, None, {}, None, screens.settings({}))
        self.assertNotIn(key, str(payload))
        self.assertTrue(actions_monitor)


if __name__ == "__main__":
    unittest.main()
