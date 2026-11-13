# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.1: the sentinels behind one contract (BaseSentinel, SentinelRegistry, the CI sentinel that holds the old one) and the page with a side panel, the logo and sixteen themes."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.sentinels import sentinel_base  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ci  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local  # noqa: E402
from github_actions_monitor.sentinels import sentinel_registry as reg  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
THEMES = ["Armor", "Aqua", "Midnight", "Ember", "Forest", "Violet", "Solar", "Ice", "Crimson", "Mono", "High contrast", "Metallic", "Professional", "Videogame", "Terminal", "Blueprint"]


class Tiny(sentinel_base.BaseSentinel):
    name = "tiny"

    def __init__(self, ctx, config, every=60, fail=False):
        super().__init__(ctx, config)
        self.every, self.fail, self.ticks = every, fail, 0

    @property
    def refresh_seconds(self):
        return self.every

    def tick(self):
        self.ticks += 1
        if self.fail:
            raise RuntimeError("boom")

    def get_status(self):
        return {"ticks": self.ticks}

    def get_alerts(self):
        return [{"id": "tiny.a:x", "code": "tiny.a", "level": "warning", "sentinel": "tiny", "account_id": "", "repo": None, "title": "t", "details": {}, "created_at": "2030-01-01T00:00:00Z"}]

    def get_metrics(self):
        return {"tiny_ticks": self.ticks}

    def get_config_schema(self):
        return {"name": "tiny", "keys": {}}


def ctx_stub():
    return {"gh": lambda *a, **k: {}, "repos_fn": lambda: [], "runs_fn": lambda: {}, "data_fn": lambda: None, "eco_fn": lambda r: "main"}


def make_ci(config=None, tmp=None, ctx=None):
    with mock.patch.object(sentinel_local, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sentinel_local, "HISTORY_FILE", Path(tmp) / "h.json"):
        return sentinel_ci.SentinelCI(ctx or ctx_stub(), config or {})


class Contract(unittest.TestCase):
    def test_a_sentinel_must_answer_the_whole_contract(self):
        class Half(sentinel_base.BaseSentinel):
            name = "half"
        with self.assertRaises(TypeError):
            Half({}, {})
        self.assertIsInstance(Tiny({}, {}), sentinel_base.BaseSentinel)

    def test_each_sentinel_has_a_clock_of_its_own(self):
        slow, fast = Tiny({}, {}, every=600), Tiny({}, {}, every=5)
        slow.last_tick = fast.last_tick = 1000.0
        self.assertEqual((slow.due(1100.0), fast.due(1100.0)), (False, True))
        self.assertTrue(slow.due(1600.0))

    def test_the_alert_shape_has_the_fields_of_the_roadmap_and_a_language_free_code(self):
        self.assertEqual(set(sentinel_base.Alert.__annotations__), {"id", "code", "level", "sentinel", "account_id", "repo", "title", "details", "created_at"})
        self.assertEqual(sentinel_base.LEVELS, ("info", "warning", "error", "critical"))


class Registry(unittest.TestCase):
    def test_the_ci_sentinel_follows_the_old_switch_exactly_as_before(self):
        self.assertTrue(reg.is_enabled({}, "ci"))
        self.assertTrue(reg.is_enabled({"sentinel": {"enabled": True}}, "ci"))
        self.assertFalse(reg.is_enabled({"sentinel": {"enabled": False}}, "ci"))
        self.assertFalse(reg.is_enabled({}, "collab"), "a sentinel that is not in the old layout is off until it is switched on")

    def test_the_new_block_wins_over_the_old_one(self):
        self.assertFalse(reg.is_enabled({"sentinel": {"enabled": True}, "sentinels": {"ci": {"enabled": False}}}, "ci"))
        self.assertTrue(reg.is_enabled({"sentinel": {"enabled": False}, "sentinels": {"ci": {"enabled": True}}}, "ci"))
        self.assertTrue(reg.is_enabled({"sentinels": {"collab": {"enabled": True}}}, "collab"))
        self.assertTrue(reg.is_enabled({"sentinels": "nonsense"}, "ci"), "a block of the wrong type is ignored")

    def test_the_options_of_both_blocks_are_merged_and_the_old_block_is_not_touched(self):
        config = {"sentinel": {"refresh_seconds": 900, "workers": 4}, "sentinels": {"ci": {"refresh_seconds": 45}}}
        merged = reg.effective_config(config, "ci")
        self.assertEqual((merged["sentinel"]["refresh_seconds"], merged["sentinel"]["workers"], merged["sentinel"]["enabled"]), (45, 4, True))
        self.assertEqual(config["sentinel"], {"refresh_seconds": 900, "workers": 4})

    def test_the_registry_builds_the_ci_sentinel_and_it_keeps_the_old_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(sentinel_local, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sentinel_local, "HISTORY_FILE", Path(tmp) / "h.json"):
                registry = reg.SentinelRegistry.build(ctx_stub(), {})
        self.assertEqual(registry.names(), ["ci", "collab"])      # 1.7.3: the Collab sentinel is the second one (off by default)
        ci = registry.get("ci")
        for attribute in ("snapshot", "feed", "refresh_repos", "ai_explain", "gh_text", "loading", "cfg", "repo_info"):
            self.assertTrue(hasattr(ci, attribute), attribute)
        self.assertIs(ci.feed, ci.core.feed)

    def test_every_sentinel_ticks_on_its_own_clock_and_a_failing_one_does_not_stop_the_others(self):
        registry = reg.SentinelRegistry()
        registry.items = {"a": Tiny({}, {}, every=600), "b": Tiny({}, {}, every=5, fail=True), "c": Tiny({}, {}, every=5)}
        for item in registry.items.values():
            item.last_tick = 1000.0
        self.assertEqual(registry.tick_due(1010.0), ["b", "c"])
        self.assertEqual((registry.items["a"].ticks, registry.items["b"].ticks, registry.items["c"].ticks), (0, 1, 1))
        self.assertEqual(registry.tick_due(1011.0), [], "nothing is due a second later")
        self.assertEqual(registry.tick_due(1700.0), ["a", "b", "c"])

    def test_a_sentinel_that_is_off_never_ticks_and_gives_no_alerts(self):
        registry = reg.SentinelRegistry()
        off = Tiny({}, {})
        off.enabled = False
        registry.items = {"off": off}
        self.assertEqual(registry.tick_due(10 ** 10), [])
        self.assertEqual(registry.alerts(), [])

    def test_the_alerts_of_all_the_sentinels_come_in_one_list_the_worst_first(self):
        registry = reg.SentinelRegistry()
        one, two = Tiny({}, {}), Tiny({}, {})
        two.get_alerts = lambda: [{"id": "z:1", "code": "z", "level": "critical", "sentinel": "two", "account_id": "", "repo": None, "title": "", "details": {}, "created_at": ""}]
        registry.items = {"one": one, "two": two}
        self.assertEqual([a["level"] for a in registry.alerts()], ["critical", "warning"])


class CiSentinel(unittest.TestCase):
    SNAP = {"enabled": True, "generated": "2030-01-01T00:00:00Z", "loading": "", "level": "bad", "errors": [{"section": "graphql", "message": "x", "at": "2030-01-01T00:00:00Z"}],
            "a2": {"red": [{"repo": "R", "workflow": "ci.yml", "streak": 2, "url": "u", "since": "2030-01-01T00:00:00Z"}]},
            "a1": {"stuck": [{"repo": "R", "name": "Build", "seconds": 9000, "url": "u2"}]},
            "a5": {"pending_sign": [{"repo": "R", "workflow": "release.yml", "hours": 30.0, "url": "u3", "since": "2030-01-01T00:00:00Z"}]},
            "totals": {"red": 1, "stuck": 1, "prs": 0}, "rate": {"remaining": 4000}}

    def test_it_holds_the_old_sentinel_and_answers_the_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = make_ci({}, tmp)
            self.assertIsInstance(ci, sentinel_base.BaseSentinel)
            self.assertIsInstance(ci.core, sentinel_local.Sentinel)
            self.assertEqual((ci.name, ci.enabled, ci.refresh_seconds), ("ci", True, 900))
            self.assertEqual(ci.get_config_schema()["name"], "ci")
            self.assertIn("refresh_seconds", ci.get_config_schema()["keys"])

    def test_the_alerts_have_stable_codes_and_the_whole_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = make_ci({}, tmp)
            ci.core.last_snap = self.SNAP
            alerts = ci.get_alerts()
        self.assertEqual([a["code"] for a in alerts], ["ci.red", "ci.stuck", "ci.pending_sign"])
        self.assertEqual([a["level"] for a in alerts], ["error", "error", "warning"])
        for alert in alerts:
            self.assertEqual(set(alert), set(sentinel_base.Alert.__annotations__))
            self.assertEqual((alert["sentinel"], alert["account_id"], alert["repo"]), ("ci", "", "R"))
            self.assertIn(alert["level"], sentinel_base.LEVELS)
        self.assertEqual(alerts[0]["id"], "ci.red:R:ci.yml")

    def test_the_code_does_not_depend_on_the_language_but_the_title_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = make_ci({}, tmp)
            ci.core.last_snap = self.SNAP
            english = ci.get_alerts()[0]
            with i18n.use_language("es"):
                spanish = ci.get_alerts()[0]
        self.assertEqual((english["code"], english["id"]), (spanish["code"], spanish["id"]))
        self.assertNotEqual(english["title"], spanish["title"])

    def test_the_status_and_the_metrics_are_plain_serialisable_data(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            ci = make_ci({}, tmp)
            ci.core.last_snap = self.SNAP
            status, metrics = ci.get_status(), ci.get_metrics()
        json.dumps([status, metrics])
        self.assertEqual((status["enabled"], status["level"], status["errors"][0]["section"]), (True, "bad", "graphql"))
        self.assertEqual((metrics["ci_red"], metrics["ci_stuck"], metrics["ci_api_remaining"]), (1, 1, 4000))

    def test_switched_off_it_says_so_and_gives_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = make_ci({"sentinel": {"enabled": False}}, tmp)
            self.assertFalse(ci.enabled)
            self.assertEqual((ci.get_alerts(), ci.get_metrics(), ci.get_status()["level"]), ([], {}, "off"))

    def test_the_account_id_travels_in_the_context_to_every_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = make_ci({}, tmp, dict(ctx_stub(), account_id="org-acme"))
            ci.core.last_snap = self.SNAP
            self.assertEqual({a["account_id"] for a in ci.get_alerts()}, {"org-acme"})

    def test_the_picture_is_the_same_one_the_old_sentinel_gives(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = make_ci({}, tmp)
            direct, wrapped = ci.core.snapshot(), ci.snapshot()
        for key in ("a1", "a2", "a3", "totals", "level", "enabled"):
            self.assertEqual(direct.get(key), wrapped.get(key), key)


class LiteKnowsNoSentinelContract(unittest.TestCase):
    def test_lite_never_loads_the_contract_the_registry_or_the_ci_sentinel(self):
        script = ("import sys; sys.path.insert(0, %r); sys.argv = ['x', '--lite']; from github_actions_monitor.app import actions_monitor as am; am.enable_lite()\n"
                  "import threading, urllib.request\nfrom http.server import ThreadingHTTPServer\n"
                  "s = ThreadingHTTPServer(('127.0.0.1', 0), am.Handler); threading.Thread(target=s.serve_forever, daemon=True).start()\n"
                  "urllib.request.urlopen('http://127.0.0.1:%%d/' %% s.server_address[1], timeout=8).read()\n"
                  "print([m for m in ('github_actions_monitor.sentinels.sentinel_base', 'github_actions_monitor.sentinels.sentinel_registry', 'github_actions_monitor.sentinels.sentinel_ci', 'github_actions_monitor.sentinels.sentinel_local') if m in sys.modules])" % str(HERE / "src"))
        done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(done.stdout.strip(), "[]")

    def test_the_monitor_starts_the_sentinels_through_the_registry(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("sentinel_registry.SentinelRegistry.build(ctx, config)", text)
        self.assertIn('SENTINEL["registry"].start()', text)
        self.assertNotIn("sentinel_local.Sentinel(ctx, config)", text)


def luminance(colour):
    colour = colour.lstrip("#")
    r, g, b = (int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda v: v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4  # noqa: E731
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + .05) / (lo + .05)


def theme_vars(name):
    match = re.search(r':root\[data-theme="%s"\]\{([^}]*)\}' % re.escape(name), PAGE)
    assert match, name
    return dict(part.split(":", 1) for part in re.split(r";(?=--)", match.group(1)))


class Shell(unittest.TestCase):
    """The page is a side panel with the logo and the sections in groups, and a stage with the figures and the section."""

    def test_the_side_panel_has_the_logo_the_groups_and_the_help(self):
        side = PAGE.split('<aside class="sidebar"', 1)[1].split("</aside>", 1)[0]
        self.assertIn('<svg class="logo"', side)
        self.assertIn("ui.brand_sub", side)
        for tab in ("now", "sent", "charts", "repos", "hist", "cfg"):
            self.assertIn(f'id="n-{tab}" data-tab="{tab}"', side)
        for group in ("watch", "data", "system"):
            self.assertIn(f'data-group="{group}"', side)
        self.assertIn('id="help-tab"', side)
        self.assertNotIn("<header", side)

    def test_the_old_tab_bar_is_gone_and_the_tabs_are_a_vertical_list(self):
        self.assertEqual(PAGE.count("<nav"), 1)
        self.assertIn('<nav role="tablist" aria-orientation="vertical"', PAGE)
        self.assertLess(PAGE.index('<aside class="sidebar"'), PAGE.index("<header>"))
        self.assertIn('class="stage"', PAGE)
        self.assertNotRegex(PAGE, r"(?m)^nav\{display:flex;gap:4px;padding:8px 18px 0;")

    def test_the_logo_is_an_inline_svg_that_draws_with_the_colours_of_the_theme_and_stops_when_asked(self):
        logo = PAGE.split('<svg class="logo"', 1)[1].split("</svg>", 1)[0]
        self.assertIn('role="img"', logo)
        self.assertNotRegex(logo, r'(fill|stroke)="#')
        self.assertIn(".lg-body{fill:var(--bg);stroke:var(--acc)", PAGE)
        self.assertRegex(PAGE, r"@media \(prefers-reduced-motion:no-preference\)\{\.lg-pulse\{[^}]*animation:lg-run")

    def test_the_panel_folds_and_the_groups_fold_and_both_are_remembered(self):
        for needle in ("am-side", "am-nav-closed", "applySide()", "applyGroups()", 'classList.toggle("side-collapsed"', ".side-collapsed .sidebar{width:62px"):
            self.assertIn(needle, PAGE)

    def test_the_group_of_the_open_section_never_hides_it(self):
        self.assertIn('!g.querySelector("[aria-selected=true]")', PAGE)

    def test_the_arrow_keys_move_between_the_sections_in_both_directions(self):
        self.assertIn('["ArrowRight","ArrowLeft","ArrowDown","ArrowUp"]', PAGE)

    def test_every_new_text_comes_from_the_catalogues_in_the_eight_languages(self):
        keys = ("ui.logo_aria", "ui.brand_sub", "ui.nav_g_watch", "ui.nav_g_data", "ui.nav_g_system", "ui.side_collapse", "ui.side_expand", "ui.nav_fold", "ui.nav_unfold",
                "ui.theme_g_basic", "ui.theme_g_studio", "ui.theme_label")
        for lang in i18n.LANGS:
            catalogue = i18n.catalogue(lang)
            for key in keys:
                self.assertTrue(catalogue.get(key, "").strip(), f"{lang} {key}")

    def test_the_small_screen_puts_the_panel_on_top(self):
        self.assertRegex(PAGE, r"@media \(max-width:800px\)\{\.shell\{flex-direction:column")

    def test_the_view_title_follows_the_section_and_the_kiosk_hides_the_panel(self):
        self.assertIn("function setViewTitle()", PAGE)
        self.assertIn(".kiosk .sidebar", PAGE)


class Themes(unittest.TestCase):
    def test_the_page_offers_the_three_basic_ones_and_the_sixteen_of_the_alarm_system_studio(self):
        match = re.search(r"STUDIO_THEMES=\[([^\]]*)\]", PAGE)
        self.assertEqual(re.findall(r'"([^"]+)"', match.group(1)), THEMES)
        self.assertIn('BASIC_THEMES=["auto","light","dark"]', PAGE)
        self.assertIn("THEMES=[...BASIC_THEMES,...STUDIO_THEMES]", PAGE)

    def test_every_theme_has_a_block_with_all_the_variables_the_shell_reads(self):
        needed = {"--bg", "--page", "--panel", "--panel2", "--line", "--line2", "--text", "--mut", "--acc", "--on", "--glow", "--side", "--side-text", "--side-active", "--side-hi", "--radius",
                  "--font", "--edge", "--shadow", "--ok", "--bad", "--run", "--warn", "--on-ok", "--on-bad", "--on-run", "--on-warn", "--grey", "--ink", "--bev-hi", "--bev-lo", "--tex"}
        for name in THEMES:
            self.assertEqual(needed - set(theme_vars(name)), set(), name)

    def test_the_text_reads_on_the_page_the_panels_and_the_side_panel_in_every_theme(self):
        for name in THEMES:
            v = theme_vars(name)
            self.assertGreaterEqual(contrast(v["--text"], v["--bg"]), 4.5, name)
            self.assertGreaterEqual(contrast(v["--text"], v["--panel"]), 4.5, name)
            self.assertGreaterEqual(contrast(v["--mut"], v["--panel"]), 4.5, f"{name}: the small grey text")
            self.assertGreaterEqual(contrast(v["--acc"], v["--panel"]), 4.5, f"{name}: the accent")

    def test_the_figures_in_green_red_amber_and_blue_read_on_the_panels_and_a_badge_reads_on_its_colour(self):
        for name in THEMES:
            v = theme_vars(name)
            for status in ("ok", "bad", "run", "warn"):
                for ground in ("--panel", "--panel2", "--bg"):
                    self.assertGreaterEqual(contrast(v[f"--{status}"], v[ground]), 4.5, f"{name} {status} on {ground}")
                self.assertGreaterEqual(contrast(v[f"--on-{status}"], v[f"--{status}"]), 4.5, f"{name} text on a {status} badge")

    def test_the_corners_always_have_a_unit(self):
        for name in THEMES:
            self.assertRegex(theme_vars(name)["--radius"], r"^\d+(\.\d+)?px$", name)

    def test_a_theme_that_was_never_set_keeps_the_old_look(self):
        for needle in (":root[data-theme=light]{", ":root[data-theme=dark]{", "@media (prefers-color-scheme:light){:root:not([data-theme])"):
            self.assertIn(needle, PAGE)
        self.assertIn(":root{--on-ok:#fff;--on-bad:#fff;--on-run:#fff;--on-warn:#fff;--acc:var(--run);", PAGE)

    def test_the_theme_is_chosen_from_a_list_in_the_settings_tab_and_never_in_the_header(self):
        cfg = PAGE.split('id="t-cfg"', 1)[1].split("</main>", 1)[0]
        self.assertIn('<select id="theme"', cfg)
        header = PAGE.split("<header>", 1)[1].split("</header>", 1)[0]
        self.assertNotIn('id="theme"', header)

    def test_no_badge_is_filled_with_a_status_colour_and_white_text_any_more(self):
        self.assertNotRegex(PAGE, r"background:var\(--(bad|warn|ok|run)\);color:#fff")
        self.assertNotRegex(PAGE, r"color:#fff;background:var\(--(bad|warn|ok|run)\)")

    def test_a_theme_asked_in_the_address_is_applied_and_an_unknown_one_is_ignored(self):
        self.assertIn("THEMES.includes(asked)?asked:", PAGE)
        self.assertIn('document.documentElement.setAttribute("data-theme",t)', PAGE)



class RefusedPostKeepsItsAnswer(unittest.TestCase):
    """A POST refused before its body is read (403 for a missing token, 413 for a body too big) used to close the connection with data still unread: Windows turned that into a reset and the
    client lost the answer it was owed (test_163 failed once in the CI with ConnectionAbortedError). The server now reads and drops what is left, with a cap."""

    def setUp(self):
        import json
        import threading
        from http.server import ThreadingHTTPServer
        from github_actions_monitor.app import actions_monitor as am
        self.am, self.json = am, json
        self.saved = dict(am.LIVE_CONFIG)
        am.LIVE_CONFIG["session_guard"] = True
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.am.LIVE_CONFIG.clear()
        self.am.LIVE_CONFIG.update(self.saved)

    def raw_post(self, path, body, declared=None, delay=0.3):
        """The headers first, a pause (the server answers and would close), then the body: the order in which the loss happened."""
        import socket
        import time
        head = (f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\nContent-Length: {len(body) if declared is None else declared}\r\n"
                f"X-Monitor-Token: {'0' * 32}\r\n\r\n").encode()
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=8)
        try:
            sock.sendall(head)
            time.sleep(delay)
            try:
                sock.sendall(body)
            except OSError:
                pass
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            return data
        finally:
            sock.close()

    def test_a_refusal_before_the_body_still_reaches_the_client(self):
        body = self.json.dumps({"changes": {"refresh_seconds": 70}}).encode()
        for attempt in range(3):
            answer = self.raw_post("/api/settings", body)
            self.assertIn(b" 403 ", answer.split(b"\r\n", 1)[0], f"attempt {attempt}: {answer[:80]!r}")

    def test_a_body_that_was_read_is_not_read_twice_and_the_answer_is_the_same(self):
        import tempfile
        from github_actions_monitor.app import settings_api
        with tempfile.TemporaryDirectory() as tmp:
            saved = (self.am.CONFIG_FILE, settings_api.CONFIG_FILE, settings_api.BACKUP_DIR)
            self.am.CONFIG_FILE = settings_api.CONFIG_FILE = Path(tmp) / "c.json"
            settings_api.BACKUP_DIR = Path(tmp) / "b"
            (Path(tmp) / "c.json").write_text("{}", encoding="utf-8")
            self.am.LIVE_CONFIG["session_guard"] = False
            try:
                body = self.json.dumps({"changes": {"refresh_seconds": 70}}).encode()
                answer = self.raw_post("/api/settings", body, delay=0.0)
            finally:
                self.am.CONFIG_FILE, settings_api.CONFIG_FILE, settings_api.BACKUP_DIR = saved
        self.assertIn(b" 200 ", answer.split(b"\r\n", 1)[0], answer[:200])

    def test_an_absurd_declared_size_is_not_waited_for_and_never_hangs_the_server(self):
        import time
        started = time.time()
        answer = self.raw_post("/api/settings", b"{}", declared=10 ** 12, delay=0.0)
        self.assertIn(b" 403 ", answer.split(b"\r\n", 1)[0])
        self.assertLess(time.time() - started, self.am.DRAIN_WAIT + 6)

    def test_the_counter_counts_what_the_handlers_read_and_passes_everything_else_through(self):
        import io
        reader = self.am.CountedReader(io.BytesIO(b"abcdef"))
        self.assertEqual((reader.read(2), reader.read(10)), (b"ab", b"cdef"))
        self.assertEqual(reader.count, 6)
        self.assertEqual(reader.read(1), b"")
        self.assertTrue(callable(reader.readline))


if __name__ == "__main__":
    unittest.main()
