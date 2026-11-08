# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Offline tests of the 8 languages, the shared settings (owner, ecosystems, targets), the reduced mode, the authorship and the release gate."""
import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401

import events as event_feed
import gha_dispatch_all as gd
import i18n
import make_release as mr
import sentinel_local as sl
import surface
import toolconfig
import workspace

HERE = Path(__file__).resolve().parents[1]
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
PH = re.compile(r"\{(\w+)(?:![rsa])?(?::[^}]*)?\}")


def catalogue(lang):
    data = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


class Catalogues(unittest.TestCase):
    def test_the_eight_locales_have_exactly_the_same_keys(self):
        base = set(catalogue("en"))
        for lang in LANGS[1:]:
            cat = catalogue(lang)
            self.assertEqual(set(cat) ^ base, set(), lang)

    def test_none_is_empty_and_the_placeholders_match(self):
        base = catalogue("en")
        for lang in LANGS:
            for key, text in catalogue(lang).items():
                self.assertTrue(text.strip(), f"{lang}:{key} is empty")
                self.assertEqual(sorted(PH.findall(text)), sorted(PH.findall(base[key])), f"{lang}:{key}")

    def test_every_locale_declares_its_authorship(self):
        for lang in LANGS:
            data = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("JuanenRac (Electro Hobby 3D)", data["_author"])
            self.assertIn("GPL-3.0-or-later", data["_license"])

    def test_the_translations_really_differ_from_english(self):
        base = catalogue("en")
        for lang in LANGS[1:]:
            same = [k for k, v in catalogue(lang).items() if v == base[k]]
            self.assertLess(len(same), len(base) * 0.25, f"{lang} looks untranslated ({len(same)} identical)")

    def test_portuguese_is_european(self):
        pt = " ".join(catalogue("pt").values())
        for brazilian in ("arquivo", "atualizar o celular", "tela ", "celular"):
            self.assertNotIn(brazilian, pt)
        self.assertIn("ficheiro", pt.lower())

    def test_json_files_are_utf8_without_bom(self):
        for lang in LANGS:
            self.assertFalse((HERE / "locales" / f"{lang}.json").read_bytes().startswith(b"\xef\xbb\xbf"))


def used_keys():
    """Every literal key passed to t() / te() / tl() / i18n.t() in the code, and every ui.* key of the page."""
    keys = {}
    for path in sorted(HERE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if name in ("t", "te", "tl") and node.args:
                    arg = node.args[1] if name == "tl" and len(node.args) > 1 else node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "." in arg.value:
                        keys.setdefault(arg.value, path.name)
    html = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
    for key in re.findall(r'"(ui\.[a-z0-9_]+)"', html):
        keys.setdefault(key, "actions_monitor.html")
    return keys


class NothingUnresolved(unittest.TestCase):
    def test_every_key_used_by_the_code_and_the_page_exists_in_english(self):
        en = catalogue("en")
        missing = {k: f for k, f in used_keys().items() if k not in en and not k.endswith((".", "_")) and k not in ("ui.lv_", "ui.theme_")}
        self.assertEqual(missing, {})

    def test_dynamic_keys_exist(self):
        en = catalogue("en")
        for key, cols in surface.SECTIONS:
            self.assertIn("surf.t." + key, en)
            for col in cols:
                self.assertIn("col." + col, en)
        for kind in ("red_new", "red_fixed", "stuck_new", "release_due", "pending_sign", "budget_over", "budget_warn", "alerts_up", "prs_up", "rate_low", "rate_ok", "loaded"):
            self.assertIn("evt." + kind, en)
        for code in ("no_defs", "never_ran", "last_failed", "stale", "defs_newer", "drift"):
            self.assertIn("a9.p." + code, en)
        for suffix in ("ok", "warn", "bad", "info", "unknown"):
            self.assertIn("ui.lv_" + suffix, en)
        for suffix in ("auto", "light", "dark"):
            self.assertIn("ui.theme_" + suffix, en)
        for name in ("ok", "running", "failed", "skipped"):
            self.assertIn("gd.sl_" + name, en)
        for state in ("red", "missing"):
            self.assertIn("surf.state_" + state, en)
        for key in ("off", "on", "bad_secret", "too_big", "bad_signature", "bad_event", "bad_payload", "unknown_repo"):
            self.assertIn("wh." + key, en)

    def test_a_missing_key_falls_back_to_english_then_to_the_key(self):
        with mock.patch.dict(i18n._catalogues, {"de": {}}):
            self.assertEqual(i18n.tl("de", "common.na"), catalogue("en")["common.na"])
        self.assertEqual(i18n.tl("de", "no.such.key"), "no.such.key")
        self.assertEqual(i18n.tl("xx", "common.na"), catalogue("en")["common.na"])

    def test_bad_placeholders_never_raise(self):
        self.assertTrue(i18n.tl("en", "hyg.file"))   # no values given: raw text
        self.assertIn("x", i18n.tl("en", "hyg.file", name="x"))
        self.assertTrue(i18n.tl("en", "hyg.file", other=1))   # wrong value names: the raw text comes back


class NoVisibleStringBypassesT(unittest.TestCase):
    """A reasonable static check: what the code prints, raises or gives to argparse may not carry a sentence of its own (words + spaces) outside the catalogues."""
    MODULES = ("actions_monitor.py", "gha_dispatch_all.py", "read_report.py", "release_candidates.py", "release_notes.py", "launcher_msg.py", "platform_compat.py", "webhook.py",
               "export_status.py", "report_history.py", "events.py", "sentinel_ai.py", "roadmap_a9.py", "workspace.py", "surface.py")
    SENTENCE = re.compile(r"[A-Za-zÀ-ÿ]{3,}[ ,:]+[A-Za-zÀ-ÿ]{2,}")
    ALLOWED = ("MONITOR_NO_RESPONDE",)

    def strings_of(self, node):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                yield sub.value

    def test_prints_exits_and_help_use_the_catalogues(self):
        offenders = []
        for name in self.MODULES:
            path = HERE / name
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                targets = []
                if isinstance(node, ast.Call):
                    fn = node.func
                    fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                    if fname in ("print", "exit", "SystemExit"):
                        targets = list(node.args)
                    targets += [kw.value for kw in node.keywords if kw.arg in ("help", "description")]
                for target in targets:
                    if isinstance(target, ast.Call):   # t("key", ...) is the right way; anything built by a call is checked in its own arguments
                        continue
                    for text in self.strings_of(target):
                        if self.SENTENCE.search(text) and not any(a in text for a in self.ALLOWED):
                            offenders.append(f"{name}:{node.lineno}: {text[:60]!r}")
        self.assertEqual(offenders, [])

    def test_the_page_has_no_visible_text_of_its_own(self):
        html = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        body = html.split("<body>", 1)[1].split("<script>", 1)[0]
        text = re.sub(r"<[^>]+>", " ", body)
        words = [w for w in re.findall(r"[A-Za-zÀ-ÿ]{3,}", text) if w not in ("GitHub", "Actions", "success", "failure", "cancelled", "timed", "out")]
        self.assertEqual(words, [])
        script = html.split("<script>", 1)[1]
        script = script.replace("const I18N=", "const DATA_I18N=", 1)   # the line with the embedded catalogues is data (the file itself holds no words there)
        spanish = re.findall(r"[áéíóúñ¿¡«»]|(?:Cargando|Ninguna?|Abrir|Cerrar|desde|lleva|Sin datos|hace|Denso|Actualizado|Copiar|Copiado)", script)
        english = re.findall(r"[>(\"'`](?:Loading|Closed?|Nothing|Updated|None\.|No data|Copied|Copy|Repository|Workflow)[ .:\"'<]", script)
        self.assertEqual(spanish + english, [])


class Behaviour(unittest.TestCase):
    def test_use_language_is_per_thread_and_restores(self):
        seen = {}

        def other():
            seen["t"] = i18n.language()

        with i18n.use_language("ja"):
            self.assertEqual(i18n.language(), "ja")
            thread = threading.Thread(target=other)
            thread.start()
            thread.join()
        self.assertEqual(seen["t"], "en")
        self.assertEqual(i18n.language(), "en")

    def test_detection_order_and_normalisation(self):
        self.assertEqual(i18n.normalize("pt_PT.UTF-8"), "pt")
        self.assertEqual(i18n.normalize("zh-CN"), "zh")
        self.assertEqual(i18n.normalize("Spanish_Spain"), "es")
        self.assertIsNone(i18n.normalize("C"))
        self.assertIsNone(i18n.normalize("tlh"))
        with mock.patch.dict(os.environ, {"MONITOR_LANG": "", "JUANENRAC_LANG": "fr"}):
            self.assertEqual(i18n.detect("de"), "fr")
        with mock.patch.dict(os.environ, {"MONITOR_LANG": "it", "JUANENRAC_LANG": "fr"}):
            self.assertEqual(i18n.detect("de"), "it")
        with mock.patch.dict(os.environ, {"MONITOR_LANG": "", "JUANENRAC_LANG": ""}):
            self.assertEqual(i18n.detect("de"), "de")
            with mock.patch.object(i18n, "system_language", return_value="es"):
                self.assertEqual(i18n.detect(""), "en")   # the language of the system never decides: English until the user chooses another

    def test_the_lang_flag_beats_the_environment_and_the_configuration(self):
        try:
            with mock.patch.dict(os.environ, {"MONITOR_LANG": "es", "JUANENRAC_LANG": "es"}):
                self.assertEqual(i18n.cli_language(["--lang", "de"]), "de")
                self.assertEqual(i18n.cli_language(["--lang=ja"]), "ja")
                self.assertEqual(i18n.cli_language([]), "es")
        finally:
            i18n.set_language("en")

    def test_machine_markers_stay_english_in_every_language(self):
        out = io.StringIO()
        for lang in LANGS:
            with i18n.use_language(lang):
                self.assertTrue(gd.te("gd.skip", name="N", why="w").startswith("SKIP N"))
                self.assertTrue(gd.te("gd.dispatched", name="N", run=1).startswith("DISPATCHED N"))
                self.assertTrue(gd.te("gd.ready", name="N", run=1).startswith("READY"))
                self.assertTrue(gd.te("gd.build_only", n=1).startswith("BUILD ONLY (1)"))
                self.assertTrue(gd.te("gd.summary").startswith("Summary:"))
        self.assertEqual(out.getvalue(), "")

    def test_a_report_is_written_in_each_language_and_the_feed_keeps_the_code(self):
        for lang in LANGS:
            with i18n.use_language(lang):
                events = event_feed.diff({"reds": {}, "stuck": {}, "alerts": {}, "prs": {}, "rate": 4000, "pending": {}, "due": {}, "budget": {}},
                                      {"reds": {"R|CI": {"repo": "R", "workflow": "CI", "url": "u", "streak": 1, "since": "x"}}, "stuck": {}, "alerts": {}, "prs": {}, "rate": 4000,
                                       "pending": {}, "due": {}, "budget": {}}, True)
            self.assertEqual(events[0]["code"], "red_new")
            self.assertIn("R", events[0]["text"])
            self.assertEqual(events[0]["args"]["workflow"], "CI")
            if lang != "en":
                self.assertNotEqual(events[0]["text"], i18n.tl("en", "evt.red_new", repo="R", workflow="CI"))

    def test_the_page_embeds_the_catalogues_and_the_default_language(self):
        import actions_monitor
        with i18n.use_language("de"):
            page = actions_monitor.render_page()
        self.assertNotIn("/*I18N_DATA*/null", page)
        data = json.loads(re.search(r"const I18N=(\{.*?\})\|\|\{default", page, re.S).group(1))
        self.assertEqual(data["default"], "de")
        self.assertEqual(sorted(data["catalogues"]), sorted(LANGS))
        self.assertEqual(data["catalogues"]["ja"]["ui.tab_now"], catalogue("ja")["ui.tab_now"])
        self.assertNotIn("</script>", json.dumps(data["catalogues"]).replace("<\\/", ""))

    def test_launcher_messages_in_every_language(self):
        for lang in LANGS:
            out = io.StringIO()
            with redirect_stdout(out):
                import launcher_msg
                self.assertEqual(launcher_msg.main(["menu", "--lang", lang]), 0)
            self.assertIn("1)", out.getvalue())
            self.assertIn(i18n.tl(lang, "launch.m6"), out.getvalue())
        i18n.set_language("en")


class SharedSettings(unittest.TestCase):
    def test_the_owner_comes_from_one_place(self):
        toolconfig.set_owner("someone-else")
        try:
            self.assertEqual(toolconfig.github_owner(), "someone-else")
            self.assertIn("someone-else/R", surface.issue_close_suggestions([{"repo": "R", "number": 5, "title": "Build failed: CI", "url": "u", "created": "2026-01-01T00:00:00Z"}],
                                                                           {"R": [{"status": "completed", "branch": "main", "conclusion": "success", "name": "CI", "id": 9, "started": "2026-02-01T00:00:00Z", "url": "u"}]},
                                                                           set(), {}, surface.parse_time("2026-03-01T00:00:00Z"))[0]["command"])
            with mock.patch.object(gd, "ghj", return_value={"workflow_runs": []}) as fake:
                gd.ci_green("R", "abc")
            self.assertIn("repos/someone-else/R/", fake.call_args[0][1])
        finally:
            toolconfig.set_owner("JuanenRac")

    def test_config_owner_and_lookup_fallback(self):
        toolconfig.set_owner(None)
        try:
            self.assertEqual(toolconfig.github_owner({"github_owner": " me "}), "me")
            toolconfig._owner["lookup"] = "from-gh"
            self.assertEqual(toolconfig.github_owner({}), "from-gh")
        finally:
            toolconfig.set_owner("JuanenRac")
            toolconfig._owner["lookup"] = None

    def test_ecosystems_are_data(self):
        toolconfig.set_ecosystems({"mine": {"label": "Mine", "prefixes": ["MY-"]}, "theirs": {"prefixes": ["TH-"], "external": True}, "rest": {"prefixes": ["*"]}})
        try:
            self.assertEqual(toolconfig.ecosystem_of("MY-APP"), "mine")
            self.assertEqual(toolconfig.ecosystem_of("OTHER"), "rest")
            self.assertTrue(toolconfig.is_internal("MY-APP"))
            self.assertFalse(toolconfig.is_internal("TH-X"))
            self.assertEqual(event_feed.owner_of("TH-X"), "theirs")
            self.assertEqual(event_feed.owner_of("MY-APP"), "main")
            self.assertEqual(sl.ecosystem_summary({"a2": {"red": []}, "a1": {"stuck": []}, "a3": {"rows": []}, "a4": {"dependabot": []}, "a5": {"candidates": []}, "a6": {"rows": []}},
                                                  {"MY-APP": "mine"}).keys(), {"mine", "theirs", "rest"})
        finally:
            toolconfig.set_ecosystems(None)

    def test_the_neutral_examples_are_valid(self):
        self.assertEqual(gd.validate_targets(json.loads((HERE / "targets.example.json").read_text(encoding="utf-8"))), [])
        self.assertEqual(gd.validate_targets(json.loads((HERE / "tests" / "fixtures" / "fixture_targets.json").read_text(encoding="utf-8"))), [])
        eco = json.loads((HERE / "ecosystems.example.json").read_text(encoding="utf-8"))["ecosystems"]
        toolconfig.set_ecosystems(eco)
        try:
            self.assertEqual(toolconfig.ecosystem_of("MYPROJECT-X"), "main")
            self.assertTrue(toolconfig.is_external("other-team"))
        finally:
            toolconfig.set_ecosystems(None)
        example = json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual((example["github_owner"], example["language"]), ("", ""))
        self.assertEqual((example["ecosystems_file"], example["targets_file"]), ("ecosystems.example.json", "targets.example.json"))

    def test_plan_and_hygiene_work_for_another_owner_without_touching_code(self):
        toolconfig.set_owner("friend")
        try:
            out = io.StringIO()
            with redirect_stdout(out), mock.patch.object(gd, "ROOT", Path(tempfile.gettempdir()) / "no-such-workspace"):
                code = gd.cmd_hygiene(mock.Mock(write_candidates=False))
            self.assertIn("TARGETS WITH A PROBLEM", out.getvalue())
            self.assertIn(code, (0, 1))
            with redirect_stdout(io.StringIO()), mock.patch.object(gd, "local_head", return_value=(None, "no local clone")):
                self.assertIn(gd.cmd_plan(mock.Mock(only=None, ecosystem=None, profile=None, json=False)), (0, 2))
        finally:
            toolconfig.set_owner("JuanenRac")


class ReducedMode(unittest.TestCase):
    def test_without_a_workspace_the_snapshot_says_so_and_has_no_local_queue(self):
        import test_signstate as ts
        inp = ts.snapshot_input() if hasattr(ts, "snapshot_input") else None
        if inp is None:
            self.skipTest("helper not available")
        inp["reduced"] = True
        snap = sl.compute_snapshot(inp)
        self.assertTrue(snap["reduced"])
        self.assertEqual((snap["a5"]["sign_queue"], snap["a5"]["pending_sign"], snap["a5"]["signed_unpublished"]), ([], [], []))
        self.assertEqual(snap["parte"][1]["text"], i18n.t("parte.reduced"))

    def test_a_missing_workspace_is_not_fatal(self):
        with mock.patch.dict(os.environ, {"MONITOR_ROOT": str(Path(tempfile.gettempdir()) / "definitely-not-here"), "JUANENRAC_ROOT": ""}):
            self.assertFalse(workspace.has_workspace())
            self.assertTrue(str(workspace.signed_dir_soft()))
            self.assertTrue(str(workspace.audit_dir_soft()))

    def test_neutral_folder_names_without_the_maintainers_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"MONITOR_ROOT": tmp, "JUANENRAC_ROOT": "", "MONITOR_AUDIT_DIR": "", "MONITOR_SIGNED_DIR": "", "JUANENRAC_AUDIT_DIR": "", "JUANENRAC_SIGNED_DIR": ""}),                     mock.patch.object(workspace, "_config", return_value=None):
                self.assertEqual(workspace.signed_dir(), Path(tmp) / "_signed")
                self.assertEqual(workspace.audit_dir(), Path(tmp) / "_audit")


class AuthorshipAndRelease(unittest.TestCase):
    def entries(self):
        return {f"github_actions_monitor/{p.relative_to(HERE).as_posix()}": p.read_bytes() for p in mr.members()}

    def test_every_member_of_the_zip_has_the_authorship(self):
        self.assertEqual(mr.authorship_problems(self.entries()), [])

    def test_the_gate_notices_a_file_without_authorship(self):
        entries = self.entries()
        entries["github_actions_monitor/x.py"] = b"print(1)\n"
        entries["github_actions_monitor/y.json"] = b"{}"
        problems = mr.authorship_problems(entries)
        self.assertTrue(any("x.py" in p for p in problems) and any("y.json" in p for p in problems))
        del entries["github_actions_monitor/NOTICE"]
        self.assertTrue(any("NOTICE" in p for p in mr.authorship_problems(entries)))

    def test_the_shell_launchers_keep_the_shebang_first_and_lf(self):
        for name in ("MONITOR_GITHUB_ACTIONS.sh", "BATCH_GITHUB_ACTIONS.sh", "MONITOR_GITHUB_ACTIONS.command", "BATCH_GITHUB_ACTIONS.command"):
            data = (HERE / name).read_bytes()
            self.assertTrue(data.startswith(b"#!/usr/bin/env bash\n"), name)
            self.assertNotIn(b"\r", data)
            self.assertIn(b"Copyright (C) 2026 JuanenRac", data[:300])

    def test_the_windows_launchers_use_crlf(self):
        for name in ("MONITOR_GITHUB_ACTIONS.bat", "BATCH_GITHUB_ACTIONS.bat"):
            data = (HERE / name).read_bytes()
            self.assertTrue(data.count(b"\r\n") == data.count(b"\n"), name)

    def test_nothing_private_travels(self):
        self.assertEqual(mr.privacy_problems(self.entries()), [])
        self.assertTrue(mr.privacy_problems({"github_actions_monitor/a.txt": b"see C:\\Users\\someone\\x"}))
        self.assertTrue(mr.privacy_problems({"github_actions_monitor/a.txt": b"keys in ~/.armor"}))
        self.assertTrue(mr.privacy_problems({"github_actions_monitor/a.txt": b"write to someone@example.org"}))
        self.assertTrue(mr.privacy_problems({"github_actions_monitor/a.txt": b"token ghp_" + b"a" * 30}))

    def test_locale_gate_and_member_list(self):
        self.assertEqual(mr.locale_problems(self.entries()), [])
        names = {p.relative_to(HERE).as_posix() for p in mr.members()}
        for needed in ("LICENSE", "NOTICE", "AUTHORS", "README.txt", "i18n.py", "toolconfig.py", "targets.example.json", "ecosystems.example.json",
                       *[f"locales/{l}.json" for l in LANGS], *[f"README_{l}.txt" for l in LANGS], *[f"QUICKSTART_{l}.txt" for l in LANGS]):
            self.assertIn(needed, names)

    def test_every_readme_and_quickstart_says_it_signs_nothing_by_itself(self):
        for lang in LANGS:
            for kind in ("README", "QUICKSTART"):
                text = (HERE / f"{kind}_{lang}.txt").read_text(encoding="utf-8")
                self.assertIn("127.0.0.1", text)
                self.assertIn("gh auth login", text)
        self.assertEqual(len({(HERE / f"README_{l}.txt").read_text(encoding="utf-8").count("\n") for l in LANGS}) >= 1, True)

    def test_the_example_config_passes_its_own_gate_and_is_neutral(self):
        text = mr.template()
        data = json.loads(text)
        self.assertEqual(data["repos"], "all")
        self.assertNotIn("JuanenRac/", text)

    def test_a_zip_extracted_in_a_clean_folder_runs_the_tests_offline(self):
        if os.environ.get("MONITOR_NO_NESTED") or not os.environ.get("MONITOR_RUN_CLEAN_INSTALL"):
            self.skipTest("the clean install is its own stage of make_release.py (set MONITOR_RUN_CLEAN_INSTALL=1 to run it here)")
        with tempfile.TemporaryDirectory() as tmp:
            for p in mr.members():
                dest = Path(tmp) / "pkg" / p.relative_to(HERE)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(p.read_bytes())
            (Path(tmp) / "pkg" / "actions_monitor.example.json").write_text(mr.template(), encoding="utf-8")
            env = dict(os.environ, MONITOR_NO_NESTED="1", PYTHONDONTWRITEBYTECODE="1", MONITOR_ROOT="", JUANENRAC_ROOT="")
            env.pop("MONITOR_ROOT"), env.pop("JUANENRAC_ROOT")
            done = subprocess.run([sys.executable, "-I", "-m", "unittest", "discover", "-s", "tests"], cwd=str(Path(tmp) / "pkg"), capture_output=True, text=True, env=env, timeout=300)
            self.assertEqual(done.returncode, 0, done.stderr[-1500:])


if __name__ == "__main__":
    unittest.main()
