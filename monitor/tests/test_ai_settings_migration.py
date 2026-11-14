# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""1.5.1: the settings page can set the external AI of the sentinel (never the key itself), migrate_state.py brings old file names to the new ones, and the documents never send
the reader to a command that no longer exists."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import migrate_state  # noqa: E402
from github_actions_monitor.app import settings_api as sa  # noqa: E402


class AiSettings(unittest.TestCase):
    def test_the_ai_group_is_in_the_page_and_has_texts_in_every_language(self):
        self.assertIn("ai", sa.GROUPS)
        keys = [k for k in sa.FIELDS if k.startswith("ai.")]
        for needed in ("ai.api_key_env", "ai.base_url", "ai.daily_limit", "ai.model", "ai.ollama_url", "ai.provider"):
            self.assertIn(needed, keys)
        self.assertFalse([k for k in keys if k.endswith(("key", "secret", "token"))])      # only the NAME of a variable (api_key_env) can be set
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                self.assertNotEqual(i18n.t("ui.cfg_g_ai"), "ui.cfg_g_ai", lang)
                for key in keys:
                    self.assertNotEqual(i18n.t("cfg.f." + key), "cfg.f." + key, (lang, key))

    def test_provider_is_a_closed_list(self):
        self.assertEqual(sa.check_value("ai.provider", "ollama"), (True, "ollama"))
        self.assertEqual(sa.check_value("ai.provider", "openai-compatible"), (True, "openai-compatible"))
        self.assertEqual(sa.check_value("ai.provider", "none"), (True, "none"))
        self.assertFalse(sa.check_value("ai.provider", "anything")[0])

    def test_ollama_is_this_computer_only_and_the_remote_service_is_https_only(self):
        self.assertTrue(sa.check_value("ai.ollama_url", "http://127.0.0.1:11434")[0])
        self.assertTrue(sa.check_value("ai.ollama_url", "http://localhost:11434/")[0])
        self.assertFalse(sa.check_value("ai.ollama_url", "http://192.168.1.5:11434")[0])
        self.assertFalse(sa.check_value("ai.ollama_url", "http://example.com:11434")[0])
        self.assertTrue(sa.check_value("ai.base_url", "https://example.org/v1")[0])
        self.assertTrue(sa.check_value("ai.base_url", "")[0])
        self.assertFalse(sa.check_value("ai.base_url", "http://example.org/v1")[0])
        self.assertFalse(sa.check_value("ai.base_url", "ftp://example.org")[0])

    def test_only_the_name_of_the_variable_can_be_given_never_a_key(self):
        self.assertEqual(sa.check_value("ai.api_key_env", "MY_AI_KEY"), (True, "MY_AI_KEY"))
        self.assertTrue(sa.check_value("ai.api_key_env", "")[0])
        for not_a_name in ("sk-abc123def456ghi789", "my key", "abcdef", "KEY=value", "A" * 70):
            self.assertFalse(sa.check_value("ai.api_key_env", not_a_name)[0], not_a_name)

    def test_the_daily_limit_has_a_range(self):
        self.assertTrue(sa.check_value("ai.daily_limit", 30)[0])
        self.assertFalse(sa.check_value("ai.daily_limit", 100000)[0])
        self.assertFalse(sa.check_value("ai.daily_limit", -1)[0])


class Migration(unittest.TestCase):
    def make(self, tmp):
        tmp = Path(tmp)
        root, audit, signed = tmp / "root", tmp / "audit", tmp / "signed"
        for d in (root, audit, signed / "lotes"):
            d.mkdir(parents=True)
        (root / "eventos_monitor.jsonl").write_text('{"a":1}\n', encoding="utf-8")
        (root / "eventos_estado.json").write_text("{}", encoding="utf-8")
        (audit / "PARTE_CENTINELA_DIA_2000-01-01.txt").write_text("old", encoding="utf-8")
        (audit / "PARTE_CENTINELA_DIA_2000-01-01.json").write_text("{}", encoding="utf-8")
        (audit / "CANDIDATAS_RELEASE.txt").write_text("c", encoding="utf-8")
        (signed / "lotes" / "lote_2000-01-01_0000.json").write_text("{}", encoding="utf-8")
        config = tmp / "actions_monitor.json"
        config.write_text(json.dumps({"parte_history_days": 12, "refresh_seconds": 60}), encoding="utf-8")
        return root, audit, signed, config

    def test_a_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, audit, signed, config = self.make(tmp)
            lines = []
            code = migrate_state.run(apply=False, root=root, audit=audit, signed=signed, config_path=config, out=lines.append)
            self.assertEqual(code, 0)
            self.assertFalse((root / "events_monitor.jsonl").exists())
            self.assertFalse((signed / "batches").exists())
            self.assertIn("parte_history_days", config.read_text(encoding="utf-8"))
            self.assertTrue(any("eventos_monitor.jsonl" in x for x in lines))

    def test_apply_copies_and_keeps_the_old_files_and_renames_the_setting_with_a_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, audit, signed, config = self.make(tmp)
            self.assertEqual(migrate_state.run(apply=True, root=root, audit=audit, signed=signed, config_path=config, out=lambda x: None), 0)
            self.assertEqual((root / "data" / "events_monitor.jsonl").read_text(encoding="utf-8"), '{"a":1}\n')
            self.assertTrue((root / "eventos_monitor.jsonl").exists())
            self.assertTrue((audit / "SENTINEL_REPORT_DAY_2000-01-01.txt").exists())
            self.assertTrue((audit / "RELEASE_CANDIDATES.txt").exists())
            self.assertTrue((signed / "batches" / "batch_2000-01-01_0000.json").exists())
            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual((data.get("report_history_days"), "parte_history_days" in data, data.get("refresh_seconds")), (12, False, 60))
            self.assertTrue((config.parent / "actions_monitor.json.before_migration").exists())

    def test_move_renames_and_nothing_is_ever_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, audit, signed, config = self.make(tmp)
            (root / "data").mkdir()
            (root / "data" / "events_monitor.jsonl").write_text("MINE", encoding="utf-8")
            migrate_state.run(apply=True, move=True, root=root, audit=audit, signed=signed, config_path=config, out=lambda x: None)
            self.assertEqual((root / "data" / "events_monitor.jsonl").read_text(encoding="utf-8"), "MINE")
            self.assertTrue((root / "eventos_monitor.jsonl").exists())   # not moved: the target existed
            self.assertFalse((root / "eventos_estado.json").exists())    # moved
            self.assertTrue((root / "data" / "events_state.json").exists())

    def test_nothing_to_do_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = []
            migrate_state.run(apply=True, root=Path(tmp) / "a", audit=Path(tmp) / "b", signed=Path(tmp) / "c", config_path=Path(tmp) / "none.json", out=lines.append)
            self.assertEqual(len(lines), 1)

    def test_every_language_has_the_migration_texts(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                for key in ("mig.would", "mig.done_file", "mig.nothing", "mon.catalog_example"):
                    self.assertNotEqual(i18n.t(key, old="a", new="b", names="c"), key, (lang, key))


class DocumentsDoNotSendToOldCommands(unittest.TestCase):
    OLD = re.compile(r"leer_parte\.py|LOTE_GITHUB_ACTIONS|eventos_monitor|eventos_estado|monitor_y_centinela")

    @classmethod
    def current_lines(cls, path):
        """The lines of a document that are not part of a table of old -> new names (those contain an arrow)."""
        return [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if cls.OLD.search(ln) and "->" not in ln and "→" not in ln]

    def test_only_the_tables_of_old_and_new_names_and_the_migration_guides_name_the_old_commands(self):
        offenders = []
        for path in HERE.glob("*.txt"):
            if self.current_lines(path):
                offenders.append(path.name)
        for path in (HERE / "docs").glob("*.md"):
            if not path.name.startswith(("MIGRATING", "CHANGELOG")) and self.current_lines(path):   # a history names the old commands on purpose
                offenders.append("docs/" + path.name)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
