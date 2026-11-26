# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The parts that plug in by themselves (families/): the rules every one of them keeps, and that what a part declares really reaches the server, the roles, the page, the texts, the command line, the loop
and the egress table. A part made up here stands for the real ones."""
import argparse
import json
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import families, i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.families import Command, Egress, Family, Option, Route, Setting  # noqa: E402
from github_actions_monitor.ops import egress  # noqa: E402
from github_actions_monitor.security import audit_log, audited_posts, auth  # noqa: E402

PH = re.compile(r"\{(\w+)(?:![rsa])?(?::[^}]*)?\}")


def allowed_key(family, key):
    """Whether a text of a part may have this name (families/declare.py says the rule)."""
    keys = {s.key for s in family.settings}
    exact = {f"cfg.{kind}.{k}" for k in keys for kind in "fht"} | {f"ui.cfg_b_{s.block}" for s in family.settings} | {f"ui.cfg_g_{tab}" for tab, _after in family.settings_tabs}
    exact |= {f"egress.{kind}.{row.id}" for row in family.egress for kind in ("use", "fail")}
    exact |= {x for s in family.settings for x in (s.label or []) + ([s.help] if s.help else [])}
    exact |= {f"doctor.{kind}.{row.id}" for row in family.checks for kind in "tf"}
    if key.startswith(f"ui.cfg_err_{family.name}_"):
        return True
    return key in exact or re.match(rf"^[a-z]+\.{family.name}[._]", key) is not None


class EveryPart(unittest.TestCase):
    """What every real part must keep; with parts that declare nothing these hold by themselves."""

    def test_the_list_is_closed_and_every_folder_of_the_package_is_in_it(self):
        folders = sorted(p.name for p in families.FOLDER.iterdir() if (p / "__init__.py").is_file())
        self.assertEqual(folders, sorted(families.NAMES))
        self.assertEqual([f.name for f in families.all_families()], list(families.NAMES))

    def test_the_routes_are_new_described_and_say_how_they_are_recorded(self):
        source = "".join(p.read_text(encoding="utf-8") for p in _testenv.source_files() if families.FOLDER not in p.parents)
        seen = set()
        for route in families.routes():
            self.assertIn(route.method, ("GET", "POST"), route.path)
            self.assertTrue(route.path.startswith("/api/") and route.note, route.path)
            self.assertNotIn(f'"{route.path}"', source, f"{route.path} is a route of the monitor itself")
            self.assertNotIn((route.method, route.path), seen)
            seen.add((route.method, route.path))
            self.assertIn(route.role, ("", "viewer", "maintainer", "admin"), route.path)
            if route.method == "POST":
                self.assertNotEqual(bool(route.audit), len(route.exempt) > 20, f"{route.path}: audit or a reason to be exempt, one of the two")
                if route.audit:
                    self.assertRegex(route.audit, audit_log.ACTION_RE)

    def test_the_settings_have_a_default_and_are_declared_once(self):
        keys = [row.key for row in families.settings()]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(settings_api.ROWS), len({row[2] for row in settings_api.ROWS}), "a part declared a setting that already exists")
        for family in families.all_families():
            for row in family.settings:
                node = family.defaults
                for part in row.key.split("."):
                    self.assertIn(part, node, f"{row.key} has no default in the part {family.name}")
                    node = node[part]

    def test_the_commands_are_new_and_have_their_help(self):
        names = [c.name for c in families.commands()]
        self.assertEqual(len(monitor_cli.COMMANDS), len(set(monitor_cli.COMMANDS)), "a part reuses the name of a command")
        for command in families.commands():
            self.assertIn(command.name, names)
            self.assertIs(monitor_cli.HANDLERS[command.name], command.run)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, command.help), command.help, (command.name, lang))

    def test_the_texts_are_in_the_eight_languages_under_names_of_their_own(self):
        base = json.loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8"))
        for family in families.all_families():
            folder = families.FOLDER / family.name / "i18n"
            if not folder.is_dir():
                continue
            self.assertEqual(sorted(p.name for p in folder.glob("*.json")), sorted(f"{lang}.json" for lang in i18n.LANGS), family.name)
            texts = {}
            for lang in i18n.LANGS:
                data = json.loads((folder / f"{lang}.json").read_text(encoding="utf-8"))
                self.assertIn("JuanenRac (Electro Hobby 3D)", data["_author"])
                self.assertIn("GPL-3.0-or-later", data["_license"])
                texts[lang] = {k: v for k, v in data.items() if not k.startswith("_")}
            for lang in i18n.LANGS:
                self.assertEqual(set(texts[lang]), set(texts["en"]), (family.name, lang))
                for key, value in texts[lang].items():
                    self.assertTrue(value.strip(), (lang, key))
                    self.assertEqual(sorted(PH.findall(value)), sorted(PH.findall(texts["en"][key])), (lang, key))
            for key in texts["en"]:
                self.assertTrue(allowed_key(family, key), f"{family.name}: the name {key} is not one of its own")
                self.assertNotIn(key, base, f"{family.name}: {key} is already a text of the monitor")

    def test_the_page_files_carry_their_authorship_ask_through_the_page_and_use_texts_that_exist(self):
        english = i18n.catalogue("en")
        for path in sorted(families.FOLDER.rglob("*.js")) + sorted(families.FOLDER.rglob("*.css")):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Copyright (C) 2026 JuanenRac", text[:300], path.name)
            self.assertNotIn("</script", text.lower(), path.name)
            if path.suffix == ".js":
                self.assertIsNone(re.search(r"(?<![\w.])(confirm|alert|prompt)\(\w*[\"'`]", text), f"{path}: use askConfirm")
                for key in re.findall(r"\bT\(\s*[\"'](ui\.[a-z0-9_.]+)[\"']\s*[,)]", text):
                    self.assertIn(key, english, (path.name, key))


def made_up(handler=lambda request: {"ok": True}):
    return Family("zz", defaults={"zz": {"enabled": False, "names": []}, "ui": {"zz_extra": 3}},
                  settings=(Setting("zztab", "zz", "zz.enabled", "bool", secure=True), Setting("zztab", "zz", "zz.names", "names", re.compile(r"^x[0-9]+\Z"))), settings_tabs=(("zztab", "ai"),),
                  routes=(Route("GET", "/api/zz/state", handler, "state"), Route("POST", "/api/zz/do", handler, "do", audit="zz_do", max_body=64),
                          Route("POST", "/api/zz/ask", handler, "ask", role="maintainer", token=False, lite=True, exempt="only reads what the page already holds"),
                          Route("GET", "/api/zz/local", handler, "local", this_computer=True)),
                  egress=(Egress("zz", ("zz.example.org",), "zz.enabled"),))


class TheRegistry(unittest.TestCase):
    def test_a_default_goes_into_a_block_that_exists_and_never_replaces_a_value(self):
        target = {"ui": {"theme": "auto"}}
        families.merge_into(target, {"ui": {"zz": 1}, "zz": {"a": []}})
        self.assertEqual(target, {"ui": {"theme": "auto", "zz": 1}, "zz": {"a": []}})
        with self.assertRaises(ValueError):
            families.merge_into(target, {"ui": {"theme": "dark"}})

    def test_the_tabs_of_settings_take_the_new_one_after_the_one_it_names(self):
        with families.using(made_up()):
            order = families.tab_order(("basic", "ai", "console"))
        real = {tab for family in families.all_families() for tab, _after in family.settings_tabs}      # the tabs that the real parts add are not what is looked at here
        self.assertEqual(tuple(tab for tab in order if tab not in real), ("basic", "ai", "zztab", "console"))

    def test_a_part_reads_its_block_over_its_defaults(self):
        with families.using(made_up()):
            self.assertEqual(families.block({"zz": {"enabled": True}}, "zz"), {"enabled": True, "names": []})
            self.assertEqual(families.block({}, "zz"), {"enabled": False, "names": []})
            self.assertEqual(families.default_of("ui.zz_extra"), 3)
        self.assertIsNone(families.default_of("zz.enabled"))

    def test_the_role_and_the_destinations_of_a_part(self):
        with families.using(made_up()):
            self.assertEqual(auth.required_role("GET", "/api/zz/state"), "viewer")
            self.assertEqual(auth.required_role("HEAD", "/api/v1/zz/state"), "viewer")
            self.assertEqual(auth.required_role("POST", "/api/zz/do"), "admin")
            self.assertEqual(auth.required_role("POST", "/api/zz/ask"), "maintainer")
            self.assertEqual(families.audited(), {**families.audited(), "/api/zz/do": "zz_do"})
            self.assertIn("/api/zz/ask", families.exempt())
            with mock.patch.object(egress, "ROWS", egress.ROWS + (("zz", ("zz.example.org",), "zz.enabled"),)):
                row = egress.table({"zz": {"enabled": True}})[-1]
        self.assertEqual((row["id"], row["hosts"], row["active"]), ("zz", ["zz.example.org"], True))

    def test_a_tick_that_fails_is_noted_and_the_next_one_still_runs(self):
        ran, noted = [], []

        def broken(config, data):
            raise RuntimeError("boom")
        with families.using(Family("zz", ticks=(broken, lambda config, data: ran.append(data)))):
            families.run_ticks({}, "d", lambda name, error: noted.append((name, str(error))))
        self.assertEqual((ran, noted), (["d"], [("family.zz", "boom")]))

    def test_the_commands_of_a_part_add_their_help_and_options(self):
        command = Command("zz-cmd", lambda ctx: ({}, [], 0), "cli.help_json", options=(Option("--zz-flag", "cli.help_json", {"action": "store_true"}),))
        self.assertTrue(monitor_cli.command_help([command]).startswith(i18n.t("cli.help_command") + " zz-cmd: "))
        self.assertEqual(monitor_cli.command_help([]), i18n.t("cli.help_command"))
        parser = argparse.ArgumentParser()
        monitor_cli.add_family_options(parser, [command, command])      # two commands may share a flag
        self.assertTrue(parser.parse_args(["--zz-flag"]).zz_flag)

    def test_a_list_setting_of_a_part_is_checked_with_its_own_shape(self):
        row = ("zztab", "zz.names", "names", re.compile(r"^x[0-9]+\Z"), True)
        with mock.patch.dict(settings_api.FIELDS, {"zz.names": row}):
            self.assertEqual(settings_api.check_value("zz.names", ["x1"]), (True, ["x1"]))
            self.assertEqual(settings_api.check_value("zz.names", ["other"]), (False, "names"))


class TheTextsAndThePage(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name) / "zz"
        (self.folder / "i18n").mkdir(parents=True)
        (self.folder / "i18n" / "en.json").write_text(json.dumps({"_author": "x", "ui.zz.title": "Made up", "ui.close": "replaced"}), encoding="utf-8")
        (self.folder / "page.js").write_text("window.FAM.on('tab',()=>{});", encoding="utf-8")
        (self.folder / "page.css").write_text("#zz{color:inherit}", encoding="utf-8")
        i18n._catalogues.clear()
        self.addCleanup(i18n._catalogues.clear)

    def test_the_texts_of_a_part_are_added_and_never_replace_one(self):
        with families.using(Family("zz"), self.folder):
            cat = i18n.catalogue("en")
        self.assertEqual(cat["ui.zz.title"], "Made up")
        self.assertNotEqual(cat["ui.close"], "replaced")

    def test_the_page_gets_the_helper_once_and_each_script_in_its_own_tag(self):
        page = "<html><head></head><body><p></p></body></html>"
        with families.using(Family("zz"), self.folder):
            out = families.inject_page(page)
        self.assertIn('<style data-part="zz">', out.split("</head>")[0])
        self.assertEqual(out.count("window.FAM=(function"), 1)
        self.assertIn('<script data-part="zz">', out)
        self.assertTrue(out.endswith("</body></html>"))

    def test_without_page_files_the_page_is_the_same(self):
        page = "<html><head></head><body></body></html>"
        with mock.patch.object(families, "_all", return_value=[(Family("zz"), self.folder / "empty")]):
            self.assertEqual(families.inject_page(page), page)

    def test_the_page_calls_the_helper_only_when_it_is_there(self):
        html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for name in ("tab", "data", "settings"):
            self.assertEqual(html.count(f'if(window.FAM)window.FAM.run("{name}"'), 1, name)


class TheServer(unittest.TestCase):
    def setUp(self):
        self.asked = []

        def handler(request):
            self.asked.append(request)
            if request.query.get("fail"):
                raise ValueError("no")
            return (201, {"ok": True}) if request.method == "POST" else {"ok": True, "q": request.query}
        part = families.using(made_up(handler))
        part.__enter__()
        self.addCleanup(part.__exit__, None, None, None)
        self.lite = {"on": False}
        self.guarded = False
        server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for patch in (mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={}), mock.patch.object(actions_monitor, "LITE", self.lite),
                      mock.patch.object(actions_monitor, "token_required", lambda: self.guarded), mock.patch.object(actions_monitor.degraded, "note"),
                      mock.patch.dict(audited_posts.AUDITED, {"/api/zz/do": "zz_do"}), mock.patch.object(actions_monitor, "audit_action")):
            patch.start()
            self.addCleanup(patch.stop)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"

    def call(self, path, body=None):
        request = urllib.request.Request(self.base + path, data=body, headers={"Content-Type": "application/json"} if body is not None else {})
        try:
            with urllib.request.urlopen(request, timeout=10) as answer:
                return answer.status, json.loads(answer.read() or b"{}")
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, json.loads(raw) if raw else {}

    def test_a_get_and_a_post_reach_their_handler(self):
        self.assertEqual(self.call("/api/zz/state?a=1"), (200, {"ok": True, "q": {"a": "1"}}))
        self.assertEqual(self.call("/api/zz/do", b'{"x": 2}'), (201, {"ok": True}))
        self.assertEqual(self.asked[-1].body, {"x": 2})
        self.assertEqual(actions_monitor.audit_action.call_args[0][1], "zz_do")

    def test_the_server_refuses_before_the_handler(self):
        self.assertEqual(self.call("/api/zz/do", b'{"x": "' + b"a" * 100 + b'"}')[0], 413)
        self.assertEqual(self.call("/api/zz/do", b"[1]")[0], 400)
        self.assertEqual(self.call("/api/zz/do", b"{nope")[0], 400)
        self.guarded = True
        self.assertEqual(self.call("/api/zz/do", b"{}")[0], 403)
        self.assertEqual(self.asked, [])
        self.assertEqual(self.call("/api/zz/ask", b"{}")[0], 201)      # a route without the one-use token

    def test_a_route_for_this_computer_refuses_another_one(self):
        def refuse(handler):
            handler.json_reply({"ok": False}, 403)
            return False
        with mock.patch.object(actions_monitor.Handler, "this_computer", refuse):
            self.assertEqual(self.call("/api/zz/local")[0], 403)
            self.assertEqual(self.asked, [])
            self.assertEqual(self.call("/api/zz/state")[0], 200)
        self.assertEqual(self.call("/api/zz/local")[0], 200)

    def test_the_lite_edition_only_has_the_routes_that_say_so(self):
        self.lite["on"] = True
        self.assertEqual(self.call("/api/zz/state")[0], 404)
        self.assertEqual(self.call("/api/zz/ask", b"{}")[0], 201)

    def test_a_handler_that_fails_answers_an_error_and_the_server_goes_on(self):
        self.assertEqual(self.call("/api/zz/state?fail=1"), (500, {"ok": False, "error": "server"}))
        self.assertEqual(self.call("/api/zz/state")[0], 200)


if __name__ == "__main__":
    unittest.main()
