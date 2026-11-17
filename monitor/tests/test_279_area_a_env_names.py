# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Every setting that names an environment variable with a secret: none may name a variable of the system or the secret that belongs to another setting, a name is written in one setting only, and the
places that read the variable refuse the same names."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.integrations import notifiers  # noqa: E402
from github_actions_monitor.security import envguard  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402

BAD = ("PATH", "GH_TOKEN", "GITHUB_TOKEN", "HOME", "USERPROFILE", "PYTHONPATH", "MONITOR_SUPERVISOR_KEY")


class EverySettingThatNamesAVariable(unittest.TestCase):
    def test_the_table_lists_exactly_the_settings_of_the_page_that_end_in_env(self):
        on_the_page = {key for key in settings_api.FIELDS if key.endswith(("_env", "_envs"))}
        self.assertEqual(set(envguard.ENV_SETTINGS), on_the_page)

    def test_none_accepts_a_variable_of_the_system_or_the_secret_of_another_setting(self):
        for key, own in envguard.ENV_SETTINGS.items():
            pattern = settings_api.FIELDS[key][3]
            for name in BAD + tuple(n for n in envguard.SECRET_NAMES if n != own):
                self.assertFalse(pattern.match(name), (key, name))
            self.assertTrue(pattern.match("MY_OWN_VARIABLE"), key)
            self.assertTrue(pattern.match(""), key + ": empty means none")
            if own:
                self.assertTrue(pattern.match(own), (key, own))

    def test_the_places_that_read_the_variable_refuse_the_same_names(self):
        for name in BAD + envguard.SECRET_NAMES:
            self.assertFalse(sentinel_ai.ENV_NAME.match(name), name)
            self.assertFalse(notifiers.ENV_RE.match(name), name)
            self.assertEqual(notifiers.secret(name), "")
        self.assertTrue(sentinel_ai.ENV_NAME.match("PROVIDER_KEY"))
        self.assertEqual(notifiers.secret("PATH"), "", "a channel never reads PATH as its secret")


class ANameIsWrittenInOneSettingOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "actions_monitor.json"
        self.path.write_text("{}", encoding="utf-8")
        from unittest import mock
        for target, name, value in ((settings_api, "BACKUP_DIR", Path(self.tmp.name) / "b"),):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_second_setting_to_take_a_name_is_refused(self):
        self.assertTrue(settings_api.apply({"webhook.secret_env": "SHARED_NAME"}, self.path)["ok"])
        answer = settings_api.apply({"notify.channels.telegram.token_env": "SHARED_NAME"}, self.path)
        self.assertEqual((answer["ok"], answer["errors"]), (False, {"notify.channels.telegram.token_env": "invalid"}))
        self.assertNotIn("notify", json.loads(self.path.read_text(encoding="utf-8")))
        self.assertTrue(settings_api.apply({"notify.channels.telegram.token_env": "TELEGRAM_TOKEN"}, self.path)["ok"])

    def test_two_names_that_come_in_one_request_are_both_refused(self):
        answer = settings_api.apply({"ai.api_key_env": "SAME_ONE", "notify.channels.slack.url_env": "SAME_ONE"}, self.path)
        self.assertFalse(answer["ok"])
        self.assertEqual(set(answer["errors"]), {"ai.api_key_env", "notify.channels.slack.url_env"})

    def test_the_default_name_of_a_setting_counts_as_taken_by_it(self):
        self.assertEqual(envguard.shared_names({"listen": {"token_env": "MONITOR_WEBHOOK_SECRET"}}), [("MONITOR_WEBHOOK_SECRET", ["webhook.secret_env", "listen.token_env"])])
        self.assertEqual(envguard.shared_names({}), [])
        self.assertEqual(envguard.shared_names({"webhook": {"secret_env": "ONE"}, "ai": {"api_key_env": "ONE"}}), [("ONE", ["webhook.secret_env", "ai.api_key_env"])])

    def test_a_clash_that_was_already_in_the_file_does_not_block_other_changes(self):
        self.path.write_text(json.dumps({"webhook": {"secret_env": "OLD_SHARED"}, "ai": {"api_key_env": "OLD_SHARED"}}), encoding="utf-8")
        self.assertTrue(settings_api.apply({"language": "es"}, self.path)["ok"])


if __name__ == "__main__":
    unittest.main()
