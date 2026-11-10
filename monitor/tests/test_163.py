# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.3: the About and Help panels, the update notice, the one-use token, discovery, doctor, the demo and the interactive terminal application."""
import asyncio
import json
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

import _testenv  # noqa: F401,E402
import about  # noqa: E402
import actions_monitor as am  # noqa: E402
import demo_mode  # noqa: E402
import discovery  # noqa: E402
import doctor  # noqa: E402
import helpdocs  # noqa: E402
import i18n  # noqa: E402
try:
    import make_help_index  # noqa: E402     (the tools live in the repository, not in the zip)
except ImportError:
    make_help_index = None
import updatecheck as uc  # noqa: E402
from tool_version import TOOL_VERSION  # noqa: E402


class Semver(unittest.TestCase):
    def test_parse_and_compare_as_numbers(self):
        self.assertEqual(uc.parse_semver("v1.6.3"), (1, 6, 3))
        self.assertEqual(uc.parse_semver("1.6.3.1"), (1, 6, 3, 1))
        for bad in ("1.7.0-rc1", "1.7", "latest", "", None, "1.6.3+build", "v1.x.2"):
            self.assertIsNone(uc.parse_semver(bad), bad)
        self.assertTrue(uc.is_newer("1.6.10", "1.6.9"))
        self.assertTrue(uc.is_newer("v1.7.0", "1.6.99"))
        self.assertFalse(uc.is_newer("1.6.3", "1.6.3"))
        self.assertFalse(uc.is_newer("1.6.2", "1.6.3"))
        self.assertFalse(uc.is_newer("1.7.0-rc1", "1.6.3"))      # a pre-release is never offered
        self.assertTrue(uc.is_newer("1.6.3.1", "1.6.3"))


class UpdateNotice(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "u.json"

    def tearDown(self):
        self.tmp.cleanup()

    def release(self, tag, **extra):
        return {"tag_name": tag, "html_url": f"https://github.com/{uc.REPO}/releases/tag/{tag}", "published_at": "2026-01-01T00:00:00Z", **extra}

    def test_a_newer_equal_and_older_release(self):
        newer = uc.check({}, "1.6.3", lambda e: self.release("v1.6.4"), now=1000, state_file=self.state)
        self.assertTrue(newer["newer"])
        self.assertEqual((newer["latest"], newer["url"].startswith("https://github.com/"), newer["changelog"].endswith("monitor/CHANGELOG.md")), ("1.6.4", True, True))
        for tag in ("v1.6.3", "v1.6.2"):
            info = uc.check({}, "1.6.3", lambda e, tag=tag: self.release(tag), now=1000, state_file=self.state, force=True)
            self.assertFalse(info["newer"], tag)
            self.assertEqual(info["url"], "")

    def test_only_one_read_a_day_and_nothing_with_offline_air_gap_or_switch_off(self):
        calls = []

        def reader(endpoint):
            calls.append(endpoint)
            return self.release("v1.6.4")
        uc.check({}, "1.6.3", reader, now=1000, state_file=self.state)
        uc.check({}, "1.6.3", reader, now=1000 + 3600, state_file=self.state)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], f"repos/{uc.REPO}/releases/latest")
        uc.check({}, "1.6.3", reader, now=1000 + 86400 + 5, state_file=self.state)
        self.assertEqual(len(calls), 2)
        fresh = Path(self.tmp.name) / "other.json"
        for config, offline in (({"updates": {"check": False}}, False), ({"airgapped": True}, False), ({}, True)):
            info = uc.check(config, "1.6.3", reader, now=1, state_file=fresh, offline=offline)
            self.assertFalse(info["newer"])
        self.assertEqual(len(calls), 2)
        self.assertFalse(uc.settings({"airgapped": True})["check"])
        with mock.patch.dict("os.environ", {"MONITOR_AIRGAPPED": "1"}):
            self.assertFalse(uc.settings({})["check"])

    def test_a_failure_is_silent_and_retried_later_and_a_prerelease_is_ignored(self):
        def broken(endpoint):
            raise RuntimeError("no route to host")
        info = uc.check({}, "1.6.3", broken, now=1000, state_file=self.state)
        self.assertEqual((info["newer"], info["latest"]), (False, ""))
        calls = []
        uc.check({}, "1.6.3", lambda e: calls.append(1) or self.release("v1.6.4"), now=1000 + 600, state_file=self.state)
        self.assertEqual(calls, [])              # too soon after a failure
        uc.check({}, "1.6.3", lambda e: calls.append(1) or self.release("v1.6.4"), now=1000 + 3700, state_file=self.state)
        self.assertEqual(calls, [1])
        for body in (self.release("v9.0.0", prerelease=True), self.release("v9.0.0", draft=True), {"tag_name": "nightly"}, "text", None):
            self.assertIsNone(uc.clean_release(body))
        self.assertEqual(uc.clean_release({"tag_name": "v1.6.9", "html_url": "https://evil.example/x"})["url"], f"https://github.com/{uc.REPO}/releases/tag/v1.6.9")

    def test_the_console_line_and_the_text_in_the_eight_languages(self):
        info = {"newer": True, "latest": "1.6.4", "current": "1.6.3", "url": "https://x"}
        for lang in i18n.LANGS:
            self.assertIn("1.6.4", uc.notice(info, lambda k, **v: i18n.tl(lang, k, **v)))
        self.assertEqual(uc.notice({"newer": False}, i18n.t), "")

    def test_the_switch_is_a_setting_in_the_basic_tab(self):
        import settings_api as sa
        self.assertEqual(sa.FIELDS["updates.check"][0], "basic")
        self.assertEqual(sa.FIELDS["airgapped"][0], "basic")


class HelpIndex(unittest.TestCase):
    @unittest.skipIf(make_help_index is None, "the tools live in the repository")
    def test_the_index_agrees_with_the_documents(self):
        self.assertEqual(make_help_index.TARGET.read_text(encoding="utf-8"), make_help_index.render(), "run tools/make_help_index.py")

    def test_every_document_is_in_the_index_in_every_language_that_exists(self):
        files = helpdocs.index()["files"]
        for path in list((HERE / "docs").glob("*.md")) + list(ROOT.glob("README*.md")) + list(HERE.glob("QUICKSTART_*.txt")) + [ROOT / "docs" / "ROADMAP.md", HERE / "CHANGELOG.md", ROOT / "CONTRIBUTING.md"]:
            self.assertIn(path.name, files, path.name)
        ids = {t["id"] for t in helpdocs.topics("en")}
        for needed in ("readme", "quickstart", "first_steps", "sentinel", "settings", "migrating", "roadmap", "changelog", "contributing"):
            self.assertIn(needed, ids)
        for lang in i18n.LANGS:
            self.assertTrue(helpdocs.topic("settings", lang)["sections"], lang)
            self.assertFalse(helpdocs.topic("settings", lang)["fallback"], lang)

    def test_a_missing_translation_falls_back_to_english(self):
        item = helpdocs._find("roadmap")
        saved = item["sections"].pop("es")
        try:
            found = helpdocs.topic("roadmap", "es")
            self.assertTrue(found["fallback"])
            self.assertEqual(found["lang"], "en")
        finally:
            item["sections"]["es"] = saved

    def test_the_search_works_in_the_language_of_the_page(self):
        self.assertTrue(helpdocs.search("webhook", "es"))
        self.assertTrue(helpdocs.search("センチネル", "ja") or helpdocs.search("webhook", "ja"))
        self.assertEqual(helpdocs.search("x", "en"), [])
        self.assertEqual(helpdocs.search("qwzxqwzxqwzx", "en"), [])

    def test_every_tab_has_a_topic(self):
        for tab in ("now", "sent", "charts", "repos", "hist", "cfg"):
            self.assertIsNotNone(helpdocs.topic(helpdocs.tab_topic(tab), "en"), tab)

    def test_the_markdown_is_rendered_safely(self):
        out = helpdocs.render("# T\n\n<script>alert(1)</script> **b** `<i>` [x](javascript:alert(1)) [ok](https://example.org/a?b=1&c=2) ![img](http://track.example/p.png)\n\n```\n<b>raw</b>\n```\n\n| a | b |\n|---|---|\n| <u>1</u> | 2 |\n")
        self.assertNotIn("<script", out)
        self.assertNotIn("javascript:", out)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn('rel="noopener noreferrer"', out)
        self.assertIn("<code>&lt;i&gt;</code>", out)
        self.assertIn("&lt;b&gt;raw&lt;/b&gt;", out)
        self.assertIn("<table>", out)
        self.assertNotIn("<u>", out)
        for topic in helpdocs.topics("en"):
            body = "".join(s["html"] for s in helpdocs.topic(topic["id"], "en")["sections"])
            self.assertNotRegex(body, r"<(script|iframe|img|object|style)\b", topic["id"])
            self.assertNotRegex(body, r"\son\w+=", topic["id"])

    def test_the_console_help_lists_prints_and_searches(self):
        code, text = helpdocs.console([], "es", i18n.t)
        self.assertEqual(code, 0)
        self.assertIn("settings", text)
        code, text = helpdocs.console(["settings"], "de", i18n.t)
        self.assertEqual(code, 0)
        self.assertIn("settings_api", text)
        self.assertEqual(helpdocs.console(["zzzzqqqq"], "en", i18n.t)[0], 1)
        self.assertEqual(helpdocs.console(["--search", "webhook"], "en", i18n.t)[0], 0)
        self.assertFalse(helpdocs.console(["changelog"], "fr", i18n.t)[1].startswith("("))      # the history is translated: no "shown in English" notice


class AboutData(unittest.TestCase):
    def test_support_text_has_no_secret_and_hides_the_home_folder(self):
        data = about.info(False, {"ok": True, "loaded": True, "offline": False, "uptime_seconds": 5}, {"config": Path.home() / "x" / "actions_monitor.json"}, {"enabled": True, "latest": "1.6.4"}, "en")
        text = about.support_text(data)
        self.assertIn(TOOL_VERSION, text)
        self.assertNotIn(str(Path.home()), text)
        self.assertIn("~", text)
        for forbidden in ("token", "secret", "password", "api_key"):
            self.assertNotIn(forbidden, text.lower())

    def test_console_about_in_every_language(self):
        data = about.lone(lite=True)
        for lang in i18n.LANGS:
            text = about.console_text(data, lambda k, lang=lang, **v: i18n.tl(lang, k, **v))
            self.assertIn(TOOL_VERSION, text)
            self.assertIn(i18n.tl(lang, "ui.edition_lite"), text)


class Server(unittest.TestCase):
    def setUp(self):
        self.saved = (dict(am.LIVE_CONFIG), am.LITE["on"])
        self.patch = mock.patch.object(am, "update_info", return_value={"enabled": True, "newer": True, "latest": "9.9.9", "current": TOOL_VERSION, "url": "https://github.com/x", "changelog": "https://github.com/y", "airgapped": False})
        self.patch.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.patch.stop()
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update(self.saved[0])
        am.LITE["on"] = self.saved[1]

    def call(self, path, body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method="POST" if data is not None else "GET", headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:
                return answer.status, json.loads(answer.read() or b"null")
        except urllib.error.HTTPError as error:
            return error.code, None

    def test_about_help_and_discovery_answer_in_both_editions(self):
        for lite in (False, True):
            am.LITE["on"] = lite
            code, about_data = self.call("/api/about?lang=es")
            self.assertEqual(code, 200)
            self.assertEqual((about_data["version"], about_data["edition"]), (TOOL_VERSION, "lite" if lite else "full"))
            self.assertTrue(about_data["update"]["newer"])
            self.assertIn("Python", about_data["support"])
            self.assertEqual(set(about_data["links"]) >= {"repository", "releases", "changelog", "documentation", "issues"}, True)
            self.assertEqual(self.call("/api/help/topics?tab=cfg&lang=de")[1]["tab_topic"], "settings")
            self.assertEqual(self.call("/api/help/topic?id=settings&lang=de")[1]["lang"], "de")
            self.assertEqual(self.call("/api/help/topic?id=nope")[0], 404)
            self.assertTrue(self.call("/api/help/search?q=webhook&lang=en")[1]["hits"])
            self.assertEqual(self.call("/api/discovery")[0], 200)
        self.assertNotIn("token", json.dumps(about_data).lower().replace("session", ""))

    def test_the_foreign_host_cannot_read_them(self):
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/about", headers={"Host": "evil.example:80"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_the_one_use_token_guards_the_writes(self):
        import settings_api
        with tempfile.TemporaryDirectory() as tmp:
            saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, settings_api.BACKUP_DIR)
            am.CONFIG_FILE = settings_api.CONFIG_FILE = Path(tmp) / "c.json"
            settings_api.BACKUP_DIR = Path(tmp) / "b"
            (Path(tmp) / "c.json").write_text("{}", encoding="utf-8")
            try:
                am.LIVE_CONFIG["session_guard"] = True
                self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 60}})[0], 403)
                token = self.call("/api/session-token")[1]
                self.assertTrue(token["required"] and len(token["token"]) == 32)
                self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 60}}, {"X-Monitor-Token": token["token"]})[0], 200)
                self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 70}}, {"X-Monitor-Token": token["token"]})[0], 403)      # one use
                self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 70}}, {"X-Monitor-Token": "0" * 32})[0], 403)
                am.LIVE_CONFIG["session_guard"] = False
                self.assertEqual(self.call("/api/session-token")[1], {"required": False, "token": ""})
                self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 80}})[0], 200)
            finally:
                am.CONFIG_FILE, settings_api.CONFIG_FILE, settings_api.BACKUP_DIR = saved

    def test_tokens_expire_and_are_limited(self):
        now = [0]
        store = am.SessionTokens(clock=lambda: now[0])
        first = store.issue()
        now[0] = 601
        self.assertFalse(store.use(first))
        for _ in range(30):
            store.issue()
        self.assertLessEqual(len(store.items), 20)


class PageWiring(unittest.TestCase):
    page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")

    def test_buttons_panels_and_shortcut_exist(self):
        for needle in ('id="about-open"', 'id="help-tab"', 'id="about-dlg"', 'id="help-dlg"', 'id="restartbar"', 'e.key==="?"', "/api/help/search", "X-Monitor-Token", 'href="#i-info"', 'href="#i-help"'):
            self.assertIn(needle, self.page, needle)

    def test_the_new_texts_exist_in_the_eight_languages(self):
        keys = set(re.findall(r'T\("(ui\.(?:about|help|wiz|disc|lvl|update|path|health|credit|edition)[a-z_0-9]*)"', self.page)) | {"ui.ic_about", "ui.ic_help", "upd.available", "doctor.title", "help.none"}
        keys = {k for k in keys if not k.endswith("_")} | {f"ui.wiz_{n}_{p}" for n in (1, 2, 3) for p in "ht"} | {f"ui.credit_{c}" for c in ("python", "gh", "rich", "textual")} | {"ui.edition_full", "ui.edition_lite"}
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for key in keys:
                self.assertIn(key, cat, f"{lang} {key}")
            for key in ("cfg.f.updates.check", "cfg.h.updates.check", "cfg.f.airgapped", "cfg.f.session_guard", "cfg.f.discovery.events", "cfg.f.discovery.hide", "ui.cfg_g_basic"):
                self.assertIn(key, cat, f"{lang} {key}")


class DiscoveryRules(unittest.TestCase):
    def test_news_between_two_listings(self):
        self.assertEqual(discovery.diff({}, ["a", "b"]), [])
        before = {"a": {"archived": False}, "b": {"archived": False}, "c": {"archived": True}}
        now = {"a": {"archived": True}, "c": {"archived": False}, "d": {"archived": False}}
        got = {(e["code"], e["repo"]) for e in discovery.diff(before, now)}
        self.assertEqual(got, {("repo_archived", "a"), ("repo_gone", "b"), ("repo_unarchived", "c"), ("repo_new", "d")})
        for lang in i18n.LANGS:
            for code in discovery.EVENT_CODES:
                self.assertIn("{repo}", i18n.tl(lang, "evt." + code))

    def test_lifecycle_rules(self):
        items = [{"name": "a"}, {"name": "f", "isFork": True}, {"name": "e", "isEmpty": True}, {"name": "p", "isPrivate": True}, {"name": "z", "isArchived": True}]
        self.assertEqual(discovery.lifecycle(items, {}), ["a", "f", "e", "p"])
        self.assertEqual(discovery.lifecycle(items, {"hide": ["fork", "private"]}), ["a", "e"])

    def test_groups_are_suggested_for_three_or_more_with_a_shared_prefix(self):
        names = ["acme-core", "acme-ui", "acme-api", "notes", "todo-app", "x-1"]
        found = discovery.suggest_groups(names)
        self.assertEqual([g["prefix"] for g in found], ["acme-"])
        self.assertEqual(found[0]["repos"], ["acme-api", "acme-core", "acme-ui"])
        self.assertEqual(discovery.suggest_groups(names, taken={"acme"}), [])
        self.assertEqual(discovery.suggest_groups(["a-1", "a-2"]), [])

    def test_a_group_is_added_after_a_copy_and_before_the_catch_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ecosystems.json"
            path.write_text(json.dumps({"ecosystems": {"mine": {"label": "Mine", "prefixes": ["m-"]}, "rest": {"label": "Rest", "prefixes": ["*"]}}}), encoding="utf-8")
            self.assertTrue(discovery.add_group(path, "acme", "acme-")["ok"])
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(list(data["ecosystems"]), ["mine", "acme", "rest"])
            self.assertEqual(len(list((Path(tmp) / "config_backups").glob("ecosystems-*.json"))), 1)
            self.assertEqual(discovery.add_group(path, "acme", "acme-")["error"], "exists")
            self.assertEqual(discovery.add_group(path, "Bad Key", "x")["error"], "invalid")
            fresh = Path(tmp) / "new.json"
            self.assertTrue(discovery.add_group(fresh, "acme", "acme-", example=HERE / "ecosystems.example.json")["ok"])
            self.assertIn("acme", json.loads(fresh.read_text(encoding="utf-8"))["ecosystems"])

    def test_the_automatic_frequency_stays_inside_the_budget(self):
        quiet = discovery.auto_frequency({"refresh_seconds": 45, "cold_refresh_seconds": 600}, 0, 100, 3000)
        busy = discovery.auto_frequency({"refresh_seconds": 45, "cold_refresh_seconds": 600}, 900, 100, 100000)
        self.assertGreater(quiet[0], 45)
        self.assertLess(busy[0], 45)
        tight = discovery.auto_frequency({"refresh_seconds": 45, "cold_refresh_seconds": 600}, 100, 500, 300)
        self.assertGreater(tight[1], 600)

    def test_the_account_listing_reports_news_and_applies_the_rules(self):
        am.DISCOVERED.update({"at": 0.0, "names": [], "snapshot": {}})
        config = {**am.DEFAULTS, "ecosystems": "all", "exclude": [], "github_owner": "demo-owner", "discovery": {"hide": ["fork"]}}
        first = [{"name": "demo-a", "isFork": False}, {"name": "demo-b", "isFork": True}]
        said = []
        with mock.patch.object(am, "announce_discovery", side_effect=lambda found, cfg: said.extend(found)):
            with mock.patch.object(am, "gh", return_value=first):
                self.assertEqual(am.watched_repos(config, force=True), ["demo-a"])
            with mock.patch.object(am, "gh", return_value=first + [{"name": "demo-c"}]):
                am.watched_repos(config, force=True)
        self.assertEqual(said, [{"code": "repo_new", "repo": "demo-c"}])
        am.DISCOVERED.update({"at": 0.0, "names": [], "snapshot": {}})


class DoctorAndDemo(unittest.TestCase):
    def test_doctor_names_the_fix_of_each_failure_in_every_language(self):
        def runner(args, timeout=20):
            return (1, "", "boom") if args[:3] == ["gh", "auth", "status"] else (0, json.dumps({"resources": {"core": {"remaining": 4000, "limit": 5000}}}), "")
        with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/gh"):
            checks = doctor.run(runner, ports=(0,))
        by = {c["id"]: c for c in checks}
        self.assertEqual([c["id"] for c in checks], list(doctor.ORDER))
        self.assertEqual((by["login"]["status"], by["login"]["fix"]), ("fail", "gh auth login"))
        self.assertEqual(by["quota"]["detail"], "4000/5000")
        self.assertEqual(doctor.exit_code(checks), 1)
        for lang in i18n.LANGS:
            text = doctor.text(checks, lambda k, lang=lang, **v: i18n.tl(lang, k, **v))
            self.assertIn("gh auth login", text)
            self.assertNotIn("doctor.", text)
        with mock.patch.object(doctor.shutil, "which", return_value=None):
            self.assertEqual({c["id"]: c["status"] for c in doctor.run(runner, ports=(0,))}["gh"], "fail")

    def test_the_demo_data_are_invented_and_complete(self):
        from datetime import datetime, timezone
        data = demo_mode.data(datetime.now(timezone.utc))
        self.assertTrue(all(r.startswith("demo-") for r in data["repos"]))
        self.assertTrue(data["runs"] and data["active"] and data["failing"])
        self.assertNotIn("github.com", json.dumps(data))


class SentinelDocumentation(unittest.TestCase):
    def test_every_check_of_the_code_is_in_the_guide_and_the_other_way_round(self):
        code = (HERE / "sentinel_local.py").read_text(encoding="utf-8")
        in_code = {m for m in re.findall(r'^\s+"a(\d+)": ', code, re.M)} | {m for m in re.findall(r's\["a(\d+)"\] = ', code)}
        in_locale = {m for m in (re.match(r"ui\.a(\d+)_title$", k) for k in i18n.catalogue("en")) if m}
        checks = in_code | {m.group(1) for m in in_locale}
        for lang, name in (("en", "SENTINEL.md"), ("es", "SENTINEL_spa.md"), ("de", "SENTINEL_deu.md"), ("fr", "SENTINEL_fra.md"), ("it", "SENTINEL_ita.md"), ("ja", "SENTINEL_jpn.md"), ("zh", "SENTINEL_zho.md"), ("pt", "SENTINEL_por.md")):
            text = (HERE / "docs" / name).read_text(encoding="utf-8")
            documented = set(re.findall(r"^\| \*\*A(\d+)\*\* \|", text, re.M))
            self.assertEqual(documented, checks, name)
        self.assertEqual(checks, {str(n) for n in range(1, 14)})


@unittest.skipUnless(__import__("importlib").util.find_spec("textual"), "needs the optional package textual")
class InteractiveTerminal(unittest.TestCase):
    def test_helpers_and_a_headless_run(self):
        import tui_textual as tt
        from datetime import datetime, timezone
        data = demo_mode.data(datetime.now(timezone.utc))
        self.assertTrue(tt.repo_rows(data, "alpha"))
        self.assertEqual(tt.repo_rows(data, "nothing-like-this"), [])
        self.assertTrue(tt.build_rows(data))
        self.assertIn("[ok] fine", tt.summary_text(data, {"parte": [{"level": "ok", "text": "fine"}]}))
        self.assertNotIn("ui.", tt.summary_text(data, None))
        rows = [{"repo": "r", "file": "f", "line": 1, "rule": "x", "severity": "warn"}, {"repo": "r", "file": "g", "line": 2, "rule": "y", "severity": "bad"}]
        self.assertEqual(len(tt.lint_rows({"lint": {"rows": rows}}, ("warn",))), 1)

        async def run():
            app = tt.make_app(1, lite=True)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause(0.3)
                await pilot.press("a")
                await pilot.pause(0.2)
                await pilot.press("escape")
                await pilot.press("question_mark")
                await pilot.pause(0.2)
                await pilot.press("escape")
                await pilot.press("q")
        asyncio.run(run())


class Quotas(unittest.TestCase):
    def setUp(self):
        import quota
        self.q = quota
        self.data = quota.load()

    def test_the_figures_come_from_the_data_file_and_not_from_the_code(self):
        self.assertEqual(self.q.included_minutes("free", self.data), 2000)
        self.assertEqual(self.q.included_minutes("pro", self.data), 3000)
        self.assertEqual(self.q.included_minutes("enterprise", self.data), 50000)
        self.assertIsNone(self.q.included_minutes("unknown", self.data))
        self.assertEqual((self.q.multiplier("linux", self.data), self.q.multiplier("windows", self.data), self.q.multiplier("macos", self.data)), (1.0, 1.667, 10.333))
        with tempfile.TemporaryDirectory() as tmp:
            edited = Path(tmp) / "q.json"
            edited.write_text(json.dumps({"plans": {"free": {"included_usd": 6, "storage_mb": 1, "concurrent_jobs": 2, "concurrent_macos": 1}}, "rates_usd_per_minute": {"macos": 0.12}}), encoding="utf-8")
            data = self.q.load(edited)
            self.assertEqual(self.q.included_minutes("free", data), 1000)
            self.assertEqual(self.q.multiplier("macos", data), 20.0)
            self.assertEqual(self.q.load(Path(tmp) / "missing.json")["limits"]["job_hours"], 6)       # a missing or broken file leaves the defaults
        source = (HERE / "quota.py").read_text(encoding="utf-8")
        self.assertNotIn("2000", source)
        self.assertNotIn("50000", source)

    def test_public_repositories_cost_nothing_private_ones_use_the_multiplier(self):
        runs = [{"repo": "pub", "seconds": 600, "id": 1}, {"repo": "priv", "seconds": 61, "id": 2}, {"repo": "priv", "seconds": 120, "id": 3}, {"repo": "priv", "seconds": 60, "id": 4}]
        got = self.q.billable(runs, {"priv"}, self.data, "linux", {3: "windows", 4: "macos", 2: "self"})
        self.assertEqual(got["clock"], 10 + 2 + 2 + 1)
        self.assertEqual(got["billable"], round(2 * 1.667 + 1 * 10.333))      # the self-hosted run costs nothing, the public one neither
        self.assertEqual(got["by_system"], {"linux": 0, "windows": 2, "macos": 1})
        self.assertTrue(got["estimate"])
        self.assertEqual(self.q.billable(runs, set(), self.data)["billable"], 0)
        self.assertEqual((self.q.runner_system(["windows-latest"]), self.q.runner_system(["macos-14"]), self.q.runner_system(["self-hosted", "linux"]), self.q.runner_system(["ubuntu-latest"]), self.q.runner_system([])), ("windows", "macos", "self", "linux", None))

    def test_the_levels_and_the_projection(self):
        cfg = self.q.settings({"quota": {"warn_percent": 75, "alert_percent": 90}})
        self.assertEqual(self.q.projection(10), 300)
        self.assertEqual([self.q.level(u, 2000, cfg) for u in (100, 1500, 1800, 2500)], ["ok", "warn", "alert", "alert"])
        self.assertEqual(self.q.level(5, None, cfg), "unknown")
        self.assertEqual(self.q.settings({"quota": {"warn_percent": 0, "alert_percent": "x"}})["warn_percent"], 75)
        self.assertEqual(self.q.settings({})["plan"], "unknown")
        alerts = self.q.Alerts(clock=lambda: 0)
        self.assertEqual([alerts.due("warn"), alerts.due("warn"), alerts.due("alert"), alerts.due("ok")], [True, False, True, False])

    def test_the_api_allowance_is_read_from_github_and_the_modes_are_named(self):
        self.assertEqual([self.q.api_mode(n) for n in (60, 1000, 5000, 15000, 12500, 7777, None)], ["unauthenticated", "actions_token", "token", "enterprise", "token", "custom", "unknown"])
        for lang in i18n.LANGS:
            for mode in ("unauthenticated", "actions_token", "token", "enterprise", "custom", "unknown"):
                self.assertIn("ui.q_api_" + mode, i18n.catalogue(lang))
        self.assertEqual(am.secondary_wait("You have exceeded a secondary rate limit", 0), 60)
        self.assertEqual(am.secondary_wait("secondary rate limit", 2), 240)
        self.assertEqual(am.secondary_wait("secondary rate limit", 9), 300)
        self.assertEqual(am.secondary_wait("timeout", 1), 4)

    def test_concurrency_and_jobs_near_the_limit(self):
        active = [{"status": "in_progress", "jobs": [{}] * 20, "repo": "a"}, {"status": "queued", "repo": "b"}]
        got = self.q.concurrency(active, "free", self.data)
        self.assertEqual((got["running"], got["queued"], got["limit"], got["level"]), (20, 1, 20, "alert"))
        self.assertEqual(self.q.concurrency(active, "enterprise", self.data)["level"], "ok")
        self.assertEqual(self.q.concurrency(active, "unknown", self.data)["level"], "unknown")
        near = self.q.long_jobs([{"status": "in_progress", "seconds": 5 * 3600, "repo": "x", "name": "n"}, {"status": "in_progress", "seconds": 3600, "repo": "y"}], self.data)
        self.assertEqual([j["repo"] for j in near], ["x"])

    def test_the_billing_report_is_optional_read_only_and_degrades(self):
        calls = []

        def ok(endpoint):
            calls.append(endpoint)
            if endpoint.startswith("users/"):
                raise RuntimeError("HTTP 404")
            return {"usageItems": [{"product": "actions", "sku": "Actions Linux", "quantity": 120, "unitType": "Minutes"}, {"product": "actions", "sku": "Actions macOS", "quantity": 30.5, "unitType": "Minutes"}, {"product": "copilot", "quantity": 99, "unitType": "Minutes"}]}
        got = self.q.billing_usage("acme", ok)
        self.assertEqual(got["minutes"], 150.5)
        self.assertEqual(calls, ["users/acme/settings/billing/usage", "organizations/acme/settings/billing/usage"])

        def forbidden(endpoint):
            raise RuntimeError("HTTP 403")
        self.assertIsNone(self.q.billing_usage("acme", forbidden))
        off = self.q.summary({"account": {"plan": "free"}}, [], [], set(), reader=ok, owner="acme", rate_limit=5000)
        self.assertIsNone(off["billing"])           # off by default: nothing is requested
        self.assertEqual(off["included_minutes"], 2000)
        on = self.q.summary({"account": {"plan": "free"}, "quota": {"billing_api": True}}, [], [], set(), reader=forbidden, owner="acme", rate_limit=60)
        self.assertEqual((on["billing"], on["billing_requested"], on["api_mode"]), (None, True, "unauthenticated"))
        real = self.q.summary({"account": {"plan": "free"}, "quota": {"billing_api": True}}, [], [], set(), reader=ok, owner="acme", rate_limit=15000)
        self.assertEqual((real["billing"]["minutes"], real["level"]), (150.5, "ok"))
        self.assertEqual(real["api_mode"], "enterprise")

    def test_the_endpoint_and_the_settings(self):
        import settings_api as sa
        for key in ("account.plan", "quota.billing_api", "quota.warn_percent", "quota.alert_percent", "quota.default_runner"):
            self.assertEqual(sa.FIELDS[key][0], "basic", key)
        self.assertFalse(json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))["quota"]["billing_api"])
        am.PRIVATE.clear()
        am.PRIVATE.add("priv")
        server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/api/quota", timeout=8) as answer:
                got = json.load(answer)
            self.assertEqual(got["plan"], "unknown")
            self.assertEqual(got["limits"]["job_hours"], 6)
            self.assertIn("estimate", got["billable"])
        finally:
            server.shutdown()
            server.server_close()
            am.PRIVATE.clear()


class WorkingModes(unittest.TestCase):
    def setUp(self):
        import modes
        self.m = modes
        self.now = [1000.0]
        self.config = {"min_rate_remaining": 800, "refresh_seconds": 45, "cold_refresh_seconds": 600, "runs_per_repo": 20, "hot_hours": 3}

    def test_a_change_of_mode_and_its_expiry(self):
        state = self.m.State(clock=lambda: self.now[0])
        self.assertEqual(state.current(self.config), "normal")
        self.assertEqual(state.set("turbo", 60, self.config, 5000, 4000), (True, "ok"))
        self.assertEqual((state.current(self.config), state.seconds_left()), ("turbo", 3600))
        self.now[0] += 1800
        self.assertEqual(state.seconds_left(), 1800)
        self.now[0] += 1801
        self.assertEqual(state.current(self.config), "normal")
        self.assertEqual(state.notice, "expired")
        self.assertEqual(state.set("fast", 0, self.config, 5000, 4000), (True, "ok"))
        self.assertIsNone(state.seconds_left())            # no limit: until it is changed
        self.assertEqual(state.set("normal", None, self.config), (True, "ok"))
        self.assertEqual((state.name, state.notice), ("normal", ""))

    def test_the_allowance_floor_ends_the_mode_and_a_low_one_refuses_it(self):
        state = self.m.State(clock=lambda: self.now[0])
        state.set("fast", 60, self.config, 5000, 4000)
        self.assertEqual(state.current(self.config, 2000), "fast")
        self.assertEqual(state.current(self.config, 799), "normal")
        self.assertEqual(state.notice, "quota")
        self.assertEqual(state.set("turbo", 10, self.config, 5000, 500), (False, "low_quota"))

    def test_without_a_login_only_normal_is_allowed(self):
        state = self.m.State()
        self.assertEqual(state.set("turbo", 10, self.config, 60, 55), (False, "no_token"))
        self.assertEqual(state.set("fast", 10, self.config, 60, 55), (False, "no_token"))
        self.assertEqual(state.set("normal", None, self.config, 60, 55), (True, "ok"))
        self.assertEqual(state.set("warp", 10, self.config, 5000, 4000), (False, "unknown"))
        self.assertEqual(state.set("fast", -5, self.config, 5000, 4000), (False, "minutes"))
        self.assertEqual(state.name, "normal")

    def test_presets_are_editable_bounded_and_never_slower_than_yours(self):
        custom = {**self.config, "modes": {"fast": {"refresh_seconds": 20, "runs_per_repo": 999, "hot_hours": 8}, "turbo": {"refresh_seconds": 1}}}
        got = self.m.presets(custom)
        self.assertEqual((got["fast"]["refresh_seconds"], got["fast"]["runs_per_repo"], got["fast"]["hot_hours"]), (20, 30, 8))      # 999 is out of range: the default stays
        self.assertEqual(got["turbo"]["refresh_seconds"], 15)                                                                           # under 10 s is never taken
        self.assertEqual(self.m.effective(self.config, "refresh_seconds", "normal"), 45)
        self.assertEqual(self.m.effective(self.config, "refresh_seconds", "turbo"), 15)
        self.assertEqual(self.m.effective({**self.config, "refresh_seconds": 10}, "refresh_seconds", "fast"), 10)                      # yours was already faster
        self.assertEqual(self.m.effective({**self.config, "runs_per_repo": 80}, "runs_per_repo", "fast"), 80)
        self.assertEqual(self.m.effective(self.config, "hot_hours", "turbo"), 12)
        self.assertEqual(self.m.settings({})["start"], "normal")
        self.assertEqual(self.m.settings({"modes": {"start": "turbo"}})["start"], "turbo")
        self.assertEqual(self.m.settings({"modes": {"start": "warp"}})["start"], "normal")

    def test_the_estimate_comes_before_the_switch_and_the_cache_lowers_it(self):
        est = self.m.estimate(self.config, 100, 10, 4000, 0.5)
        self.assertGreater(est["turbo"]["calls_per_hour"], est["fast"]["calls_per_hour"])
        self.assertGreater(est["fast"]["calls_per_hour"], est["normal"]["calls_per_hour"])
        self.assertEqual(est["turbo"]["with_cache_per_hour"], round(est["turbo"]["calls_per_hour"] * 0.5))
        self.assertEqual(est["normal"]["minutes_left"], round(60 * 4000 / est["normal"]["calls_per_hour"]))
        self.assertIsNone(self.m.estimate(self.config, 5, 1, None)["fast"]["minutes_left"])

    def test_the_interval_of_the_loop_follows_the_mode_and_the_endpoint_answers(self):
        saved = (am.MODE.name, am.MODE.until, am.MODE.notice, dict(am.LIVE_CONFIG))
        am.LIVE_CONFIG.update({"session_guard": False, "min_rate_remaining": 800})
        server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def call(body=None):
            request = urllib.request.Request(base + "/api/mode", data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST", headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=8) as answer:
                    return answer.status, json.load(answer)
            except urllib.error.HTTPError as error:
                return error.code, json.load(error)
        try:
            with am.LOCK:
                am.STATE["data"] = {"rate": {"remaining": 4500, "limit": 5000}, "repos": ["a", "b"], "hot": 1}
            self.assertEqual(call()[1]["mode"], "normal")
            code, got = call({"mode": "turbo", "minutes": 30})
            self.assertEqual((code, got["mode"], got["seconds_left"] > 0), (200, "turbo", True))
            self.assertEqual(am.tuned({**am.DEFAULTS, "github_owner": "x"}, "refresh_seconds"), 15)
            self.assertEqual(call({"mode": "normal"})[1]["mode"], "normal")
            self.assertEqual(am.tuned(am.DEFAULTS, "refresh_seconds"), am.DEFAULTS["refresh_seconds"])
            with am.LOCK:
                am.STATE["data"] = {"rate": {"remaining": 55, "limit": 60}, "repos": [], "hot": 0}
            code, got = call({"mode": "turbo", "minutes": 30})
            self.assertEqual((code, got["reason"], got["allowed"]), (400, "no_token", False))
            am.LIVE_CONFIG["session_guard"] = True
            self.assertEqual(call({"mode": "fast"})[0], 403)
        finally:
            server.shutdown()
            server.server_close()
            am.MODE.name, am.MODE.until, am.MODE.notice = saved[:3]
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(saved[3])
            with am.LOCK:
                am.STATE["data"] = None

    def test_the_page_has_the_selector_and_every_text_in_eight_languages(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('id="mode-sel"', 'id="mode-left"', "/api/mode", "ui.mode_confirm"):
            self.assertIn(needle, page, needle)
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for key in ("ui.mode_title", "ui.mode_normal", "ui.mode_fast", "ui.mode_turbo", "ui.mode_est", "ui.mode_confirm", "ui.mode_no_token", "ui.mode_back_expired", "ui.mode_back_quota", "mode.back_quota", "mon.help_mode"):
                self.assertIn(key, cat, f"{lang} {key}")
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("modes.State()", source)
        self.assertIn("--mode", source)


class EditionBanner(unittest.TestCase):
    def test_the_banner_says_which_edition_runs_in_every_language(self):
        import banner
        for lang in i18n.LANGS:
            tr = lambda k, lang=lang, **v: i18n.tl(lang, k, **v)   # noqa: E731
            lite = banner.line(True, 8766, "actions_monitor_lite.json", tr, "http://127.0.0.1:8766/")
            full = banner.line(False, 8765, "actions_monitor.json", tr, "http://127.0.0.1:8765/")
            self.assertTrue(lite.startswith(f"GitHub Actions Monitor LITE {TOOL_VERSION}"), lite)
            self.assertTrue(full.startswith(f"GitHub Actions Monitor COMPLETE {TOOL_VERSION}"), full)
            self.assertIn("8766", lite)
            self.assertIn("actions_monitor_lite.json", lite)
            self.assertIn("8765", full)
            self.assertNotEqual(lite.split(" · ")[3], full.split(" · ")[3])      # sentinel off / on
            self.assertNotIn("banner.", lite + full)
        self.assertEqual((banner.tag(True), banner.tag(False)), ("[LITE]", "[COMPLETE]"))

    def test_the_title_is_set_only_on_a_terminal(self):
        import io
        import banner

        class Tty(io.StringIO):
            def isatty(self):
                return True
        quiet, loud = io.StringIO(), Tty()
        banner.set_title("x", quiet)
        banner.set_title("GitHub Actions Monitor LITE", loud)
        self.assertEqual(quiet.getvalue(), "")
        self.assertEqual(loud.getvalue(), chr(27) + "]0;GitHub Actions Monitor LITE" + chr(7))

    def test_the_launchers_and_the_start_up_code_carry_the_mark(self):
        for name, mark in (("MONITOR_LITE_GITHUB_ACTIONS", "LITE - port 8766 - no sentinel"), ("MONITOR_GITHUB_ACTIONS", "COMPLETE - port 8765 - sentinel on")):
            self.assertIn("title GitHub Actions Monitor " + mark, (HERE / (name + ".bat")).read_text(encoding="utf-8"))
            for ext in (".sh", ".command"):
                text = (HERE / (name + ext)).read_text(encoding="utf-8")
                self.assertIn(chr(92) + "033]0;%s" + chr(92) + "007", text)
                self.assertIn("Monitor " + mark, text)
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        for needle in ("banner.line(", "banner.set_title(", "banner.tag("):
            self.assertIn(needle, source)
        data = about.lone(lite=True)
        self.assertEqual(data["edition"], "lite")
        self.assertIn("LITE", doctor.text([{"id": "python", "status": "ok", "detail": "", "fix": ""}], i18n.t, "lite").split("\n")[0])
        self.assertIn("COMPLETE", doctor.text([{"id": "python", "status": "ok", "detail": "", "fix": ""}], i18n.t, "full").split("\n")[0])


class Packaging(unittest.TestCase):
    def test_the_new_files_travel_in_the_zip_and_need_no_package(self):
        import make_release
        names = {p.name for p in make_release.members()}
        for needed in ("about.py", "helpdocs.py", "updatecheck.py", "discovery.py", "doctor.py", "demo_mode.py", "tui_textual.py", "banner.py", "modes.py", "quota.py", "quotas.json", "MODES.md", "QUOTAS.md", "help_index.json", "SENTINEL.md", "FIRST_STEPS.md"):
            self.assertIn(needed, names, needed)

    def test_importing_the_monitor_never_loads_textual_or_rich(self):
        import subprocess
        code = "import sys; sys.path.insert(0, %r); import actions_monitor, about, helpdocs, updatecheck, discovery, doctor; print('textual' in sys.modules or 'rich' in sys.modules)" % str(HERE)
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.stdout.strip(), "False", done.stderr)


if __name__ == "__main__":
    unittest.main()
