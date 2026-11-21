# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Updates menu, leftovers of its first version: the whole log of the process of an update and the button that discards one copy. The engine (copies, discard, process_log, the commands `copies`,
`discard` and `log`), the service of the monitor, the routes and the page. Nothing here reaches GitHub."""
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import monitor_updater as mu  # noqa: E402
from github_actions_monitor.ops import updates  # noqa: E402
from github_actions_monitor.security import audited_posts  # noqa: E402
from test_66_updater_engine import Base, config_from_defaults, make_install  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class Engine(Base):
    def setUp(self):
        super().setUp()
        self.root = make_install(self.tmp / "i", "2.0.1", config_from_defaults("2.0.1"))
        self.up = self.updater(self.root)

    def copy(self, name, status="ok", frm="2.0.1", to="2.0.8", manifest=True, size=100):
        folder = self.up.backups / name
        (folder / "files").mkdir(parents=True)
        (folder / "files" / "x.bin").write_bytes(b"x" * size)
        (folder / "journal.json").write_text(json.dumps({"status": status, "from": frm, "to": to}), encoding="utf-8")
        if manifest:
            (folder / "manifest.json").write_text("{}", encoding="utf-8")
        return folder

    def history_ok(self, name):
        self.up._history({"result": "ok", "backup": name, "from": "2.0.1", "to": "2.0.8"}, self.up.folders())

    def test_the_copies_are_listed_with_their_state_and_size(self):
        self.copy("20260101-000000_2.0.1_to_2.0.8", size=2048)
        self.copy("20260102-000000_2.0.8_to_2.0.9", status="applying", frm="2.0.8", to="2.0.9")
        rows = {c["name"]: c for c in self.up.copies()}
        self.assertGreaterEqual(rows["20260101-000000_2.0.1_to_2.0.8"]["bytes"], 2048)
        self.assertTrue(rows["20260101-000000_2.0.1_to_2.0.8"]["can_discard"])
        self.assertFalse(rows["20260102-000000_2.0.8_to_2.0.9"]["can_discard"])
        self.assertEqual(rows["20260102-000000_2.0.8_to_2.0.9"]["reason"], "running")

    def test_the_staging_and_downloads_folders_are_not_copies(self):
        (self.up.backups / "_staging").mkdir(parents=True)
        (self.up.backups / "downloads").mkdir()
        self.assertEqual(self.up.copies(), [])

    def test_a_copy_is_discarded_after_the_confirmation_and_only_that_one(self):
        keep = self.copy("keep_me")
        gone = self.copy("old_one")
        report = self.up.discard("old_one", confirm=lambda c: c["name"] == "old_one")
        self.assertTrue(report["ok"], report)
        self.assertFalse(gone.exists())
        self.assertTrue(keep.exists())
        self.assertTrue(self.root.exists())
        self.assertEqual(self.up.history()[-1]["result"], "discarded")

    def test_without_the_confirmation_nothing_is_discarded(self):
        folder = self.copy("old_one")
        report = self.up.discard("old_one", confirm=lambda c: False)
        self.assertEqual((report["ok"], report["code"], report["reason"]), (False, mu.NOT_CONFIRMED, "not_confirmed"))
        self.assertTrue(folder.exists())

    def test_the_copy_of_the_way_back_needs_force(self):
        folder = self.copy("way")
        self.history_ok("way")
        self.assertTrue(self.up.copies()[0]["way_back"])
        report = self.up.discard("way")
        self.assertEqual((report["ok"], report["reason"]), (False, "way_back"))
        self.assertTrue(folder.exists())
        self.assertTrue(self.up.discard("way", force=True)["ok"])
        self.assertIsNone(self.up.previous(), "after it the way back does not exist, and the updater says so")

    def test_the_copy_of_a_running_update_is_never_discarded_not_even_with_force(self):
        folder = self.copy("busy", status="applying")
        report = self.up.discard("busy", force=True)
        self.assertEqual((report["ok"], report["reason"]), (False, "running"))
        self.assertTrue(folder.exists())

    def test_a_name_that_is_not_a_copy_is_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "f").write_text("keep", encoding="utf-8")
        for name in ("../outside", "..", "", "a/b", "a\\b", "nope", "_staging", "downloads", "x" * 200):
            report = self.up.discard(name, force=True)
            self.assertFalse(report["ok"], name)
        self.assertTrue((outside / "f").exists())

    def test_the_log_is_the_tail_with_the_secrets_hidden(self):
        logs = self.up.folders()["logs"]
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "updater_handover.log").write_text("\n".join(["line %d" % i for i in range(300)] + ["GH_TOKEN=ghp_abc123 done", "password: hunter2", "\x1b[31mred\x1b[0m"]) + "\n", encoding="utf-8")
        got = self.up.process_log(50)
        self.assertEqual(len(got["lines"]), 50)
        self.assertTrue(got["truncated"])
        text = "\n".join(got["lines"])
        self.assertNotIn("ghp_abc123", text)
        self.assertNotIn("hunter2", text)
        self.assertNotIn("\x1b", text)
        self.assertIn("red", text)
        self.assertEqual(self.up.process_log(0)["lines"][-1], "red")      # 0 is "the default", never an empty answer by accident

    def test_a_missing_or_linked_log_is_an_empty_one(self):
        self.assertEqual(self.up.process_log(), {"lines": [], "bytes": 0, "truncated": False})

    def test_a_huge_log_is_read_only_at_its_end(self):
        logs = self.up.folders()["logs"]
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "updater_handover.log").write_bytes(b"A" * 1_000_000 + b"\nlast line\n")
        got = self.up.process_log(5, limit_bytes=4096)
        self.assertEqual(got["lines"][-1], "last line")
        self.assertTrue(got["truncated"])
        self.assertGreater(got["bytes"], 1_000_000)

    def test_the_commands_copies_discard_and_log(self):
        self.copy("old_one")
        out = []
        code = mu.main(["copies", "--dir", str(self.root), "--backups", str(self.up.backups), "--json"], out=type("O", (), {"write": lambda s, t: out.append(t), "flush": lambda s: None})())
        self.assertEqual(code, mu.OK)
        self.assertIn("old_one", "".join(out))
        out.clear()
        self.assertEqual(mu.main(["discard", "--dir", str(self.root), "--backups", str(self.up.backups)], out=type("O", (), {"write": lambda s, t: out.append(t), "flush": lambda s: None})()), mu.USAGE)
        self.assertEqual(mu.main(["discard", "--dir", str(self.root), "--backups", str(self.up.backups), "--name", "old_one", "--yes"], out=type("O", (), {"write": lambda s, t: out.append(t), "flush": lambda s: None})()), mu.OK)
        self.assertFalse((self.up.backups / "old_one").exists())
        self.assertEqual(mu.main(["log", "--dir", str(self.root), "--backups", str(self.up.backups)], out=type("O", (), {"write": lambda s, t: out.append(t), "flush": lambda s: None})()), mu.OK)

    def test_the_new_texts_exist_in_the_eight_languages(self):
        for key in ("r.no_copy", "r.copy_running", "r.copy_way_back", "r.copy_failed", "r.discarded", "r.discard_usage", "r.not_confirmed", "lbl.way_back", "lbl.no_copies", "lbl.no_log", "btn.discard"):
            for lang in LANGS:
                self.assertTrue(mu._CAT[lang].get(key), (key, lang))


class Service(unittest.TestCase):
    def test_discard_needs_the_confirmation_and_an_edition_that_updates(self):
        with self.assertRaises(updates.UpdatesError) as raised:
            updates.discard("x", None)
        self.assertEqual(raised.exception.code, "not_confirmed")
        for kind, code in (({"lite": True}, "lite"), ({"demo": True}, "demo")):
            with self.assertRaises(updates.UpdatesError) as raised:
                updates.discard("x", True, **kind)
            self.assertEqual(raised.exception.code, code)

    def test_discard_is_refused_while_an_update_runs(self):
        with mock.patch.object(updates, "running", return_value=True):
            with self.assertRaises(updates.UpdatesError) as raised:
                updates.discard("x", True)
        self.assertEqual(raised.exception.code, "busy")

    def test_the_reason_of_the_updater_becomes_the_code_of_the_page(self):
        class Up:
            def discard(self, name, force=False):
                return {"ok": False, "reason": "way_back", "code": 3, "error": "x"}

        with mock.patch.object(updates, "running", return_value=False), mock.patch.object(updates, "updater", return_value=(None, Up())):
            with self.assertRaises(updates.UpdatesError) as raised:
                updates.discard("x", True)
        self.assertEqual(raised.exception.code, "way_back")

    def test_the_route_is_for_this_computer_and_audited(self):
        from github_actions_monitor.app import actions_monitor
        self.assertIn("/api/updates/discard", actions_monitor.THIS_COMPUTER_ADVANCED)
        self.assertEqual(audited_posts.AUDITED.get("/api/updates/discard"), "update_discard")

    def test_the_two_reads_are_documented_as_unfrozen(self):
        contract = (HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8")
        for path in ("/api/updates/log", "/api/updates/copies"):
            self.assertIn('"path": "%s"' % path, contract)


class Page(unittest.TestCase):
    def test_the_page_has_the_boxes_the_buttons_and_the_texts(self):
        for needle in ('id="upd-copies"', 'id="upd-log"', "data-upd-discard", "upd-log-btn", 'updJ("copies")', 'updJ("log?lines=400")', 'updJ("discard"'):
            self.assertIn(needle, PAGE)
        for lang in LANGS:
            file = "pt" if lang == "pt" else lang
            texts = json.loads((HERE / "assets" / "locales" / f"{file}.json").read_text(encoding="utf-8"))
            for key in re.findall(r'T\("(ui\.upd_(?:copies|copy|discard|log|r_discarded|err_unknown_copy|err_way_back|err_running)[a-z_]*)"', PAGE):
                self.assertIn(key, texts, (lang, key))

    def test_a_discard_always_asks_and_the_way_back_asks_twice(self):
        body = PAGE[PAGE.index("async function updDiscard"):PAGE.index("async function updLogToggle")]
        self.assertEqual(body.count("askConfirm("), 2)
        self.assertLess(body.index("askConfirm("), body.index('updJ("discard"'))
        self.assertIn("confirm:true", body)


class TheStandaloneUpdater(Base):
    """The updater that runs without the monitor (page in the browser, text menu, window) has the same copies, log and discard as the Updates menu of the monitor."""

    def setUp(self):
        super().setUp()
        self.root = make_install(self.tmp / "i", "2.0.1", config_from_defaults("2.0.1"))
        self.up = self.updater(self.root)
        folder = self.up.backups / "old_one"
        (folder / "files").mkdir(parents=True)
        (folder / "files" / "x.bin").write_bytes(b"x" * 2048)
        (folder / "journal.json").write_text(json.dumps({"status": "ok", "from": "2.0.1", "to": "2.0.8"}), encoding="utf-8")
        (folder / "manifest.json").write_text("{}", encoding="utf-8")
        self.web = mu.WebApp(lambda local=None: self.up)

    def test_the_page_lists_the_copies_and_discards_one(self):
        status, body = self.web.handle("GET", "/api/copies", {}, {})
        self.assertEqual((status, [c["name"] for c in body["copies"]]), (200, ["old_one"]))
        status, body = self.web.handle("POST", "/api/discard", {}, {"name": "old_one"})
        self.assertTrue(body["ok"], body)
        self.assertIn("old_one", body["text"])
        self.assertEqual(self.web.handle("GET", "/api/copies", {}, {})[1]["copies"], [])

    def test_the_page_refuses_what_is_not_a_copy_and_says_why(self):
        status, body = self.web.handle("POST", "/api/discard", {}, {"name": "../i"})
        self.assertEqual((status, body["ok"]), (200, False))
        self.assertTrue(body["error"])
        self.assertTrue((self.root / "LICENSE").exists() or self.root.exists())

    def test_the_page_reads_the_log(self):
        logs = self.up.folders()["logs"]
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "updater_handover.log").write_text("one\npassword: hunter2\nthree\n", encoding="utf-8")
        status, body = self.web.handle("GET", "/api/log", {}, {})
        self.assertEqual(status, 200)
        self.assertEqual(body["lines"][0], "one")
        self.assertNotIn("hunter2", "\n".join(body["lines"]))

    def test_the_page_has_the_buttons_and_their_texts_in_the_eight_languages(self):
        for needle in ('id="copiesbtn"', 'id="logbtn"', 'id="copiescard"', 'id="logcard"', "/api/discard", "/api/copies", "/api/log"):
            self.assertIn(needle, mu.PAGE)
        for lang in LANGS:
            for key in ("btn.copies", "btn.log", "btn.discard", "web.confirm_discard", "lbl.no_copies", "lbl.no_log", "menu.7", "menu.8", "menu.9", "p.copy"):
                self.assertTrue(mu._CAT[lang].get(key), (lang, key))
        body = mu.PAGE[mu.PAGE.index("async function doDiscard"):mu.PAGE.index("async function loadCopies")]
        self.assertEqual(body.count("confirm("), 2)      # one question, a second for the copy of the way back
        self.assertLess(body.index("confirm("), body.index('"/api/discard"'))

    def test_the_text_menu_lists_discards_and_reads_the_log(self):
        import io
        answers = iter(["7", "8", "9", "old_one", "yes", "7", "0"])
        out = io.StringIO()
        self.assertEqual(mu.console_menu(self.up, lambda prompt="": next(answers), out), mu.OK)
        text = out.getvalue()
        self.assertIn("old_one", text)
        self.assertIn(mu.tr("lbl.no_log"), text)
        self.assertIn(mu.tr("lbl.no_copies"), text)
        self.assertFalse((self.up.backups / "old_one").exists())

    def test_the_text_menu_does_not_discard_without_the_answer_yes(self):
        import io
        answers = iter(["9", "old_one", "no", "0"])
        mu.console_menu(self.up, lambda prompt="": next(answers), io.StringIO())
        self.assertTrue((self.up.backups / "old_one").exists())


if __name__ == "__main__":
    unittest.main()
