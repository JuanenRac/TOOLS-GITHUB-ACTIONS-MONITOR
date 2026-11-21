# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The profile `qa`: an observer that refuses every action, on another port and with an ETag cache in a temporary file that is deleted at the end. No network, no GitHub."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import qaprofile  # noqa: E402
from github_actions_monitor.integrations import ghactions  # noqa: E402
from github_actions_monitor.util import ports  # noqa: E402

QA = {"MONITOR_PROFILE": "qa"}
NO_CONFIG = {"complete": {}, "lite": {}}


class QaProfile(unittest.TestCase):
    def test_only_the_word_qa_in_any_case_activates_it(self):
        self.assertTrue(qaprofile.active({"MONITOR_PROFILE": "qa"}))
        self.assertTrue(qaprofile.active({"MONITOR_PROFILE": " QA "}))
        for other in ("", "prod", "qa2", "q"):
            self.assertFalse(qaprofile.active({"MONITOR_PROFILE": other}), other)
        self.assertFalse(qaprofile.active({}))

    def test_the_port_is_another_one_unless_it_was_asked_for(self):
        self.assertEqual(ports.resolve("complete", env={}, configs=NO_CONFIG), 8765)
        self.assertEqual(ports.resolve("complete", env=QA, configs=NO_CONFIG), 8865)
        self.assertEqual(ports.resolve("lite", env=QA, configs=NO_CONFIG), 8866)
        self.assertEqual(ports.resolve("complete", flag=9000, env=QA, configs=NO_CONFIG), 9000)      # what a person types is not second-guessed
        self.assertEqual(ports.resolve("complete", env={"MONITOR_PROFILE": "qa", "MONITOR_PORT": "9100"}, configs=NO_CONFIG), 9200)
        self.assertEqual(ports.resolve("complete", env=QA, configs={"complete": {"ports": {"complete": 65500}}, "lite": {}}), 65400)      # past 65535: minus 100
        self.assertEqual(qaprofile.shift_port(8765), 8865)
        self.assertEqual(qaprofile.shift_port(65500), 65400)

    def test_the_real_ports_do_not_change_without_the_profile(self):
        self.assertEqual(ports.both(env={}, configs=NO_CONFIG), {"complete": 8765, "lite": 8766})
        self.assertEqual(ports.from_argv(["--port", "9000"], "complete", env=QA, configs=NO_CONFIG), 9000)

    def test_it_is_always_an_observer(self):
        state = ghactions.writer_state({"github_actions": {"writer_lock": False}}, QA, lock_path=Path(tempfile.gettempdir()) / "gha_qa_never_used.lock")
        self.assertEqual(state, ("observer", "qa"))

    def test_the_cache_is_a_temporary_file_of_the_process_and_it_is_forgotten(self):
        path = qaprofile.etag_file()
        self.assertEqual(path.parent, Path(tempfile.gettempdir()))
        self.assertIn(str(os.getpid()), path.name)
        self.assertNotEqual(path, qaprofile.etag_file(pid=1))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "etag.json"
            target.write_text("{}", encoding="utf-8")
            Path(str(target) + ".tmp").write_text("{}", encoding="utf-8")
            qaprofile.forget(target)
            self.assertFalse(target.exists() or Path(str(target) + ".tmp").exists())
            qaprofile.forget(target)      # already gone: no error

    def test_the_flag_and_the_texts_exist(self):
        from github_actions_monitor.app import actions_monitor
        source = Path(actions_monitor.__file__).read_text(encoding="utf-8")
        self.assertIn('"--profile", choices=qaprofile.PROFILES', source)
        self.assertIn("etagcache.EtagCache(**({\"path\": qa_cache}", source)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            i18n.set_language(lang)
            self.addCleanup(i18n.set_language, "en")
            for key in ("mon.help_profile", "mon.profile_qa"):
                self.assertNotEqual(i18n.t(key, port=1), key, (lang, key))

    def test_the_etag_cache_can_live_in_another_file(self):
        from github_actions_monitor.data_pipeline import etagcache
        with tempfile.TemporaryDirectory() as folder:
            cache = etagcache.EtagCache(path=Path(folder) / "qa.json")
            self.assertEqual(cache.path, Path(folder) / "qa.json")
            self.assertNotEqual(cache.path, etagcache.CACHE_FILE)


if __name__ == "__main__":
    unittest.main()
