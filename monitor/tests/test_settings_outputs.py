# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The settings menu (settings_api.py and its two endpoints), the optional outputs (outputs.py: /metrics, Grafana JSON, dashboard document) and the icons of the page."""
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

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import actions_monitor as am  # noqa: E402
import i18n  # noqa: E402
import outputs  # noqa: E402
import settings_api as sa  # noqa: E402


class Validation(unittest.TestCase):
    def test_only_the_schema_is_accepted(self):
        clean, errors = sa.validate({"refresh_seconds": 60, "webhook.secret": "x", "sentinel.notify_command": ["rm"], "signed_dir_x": 1})
        self.assertEqual(clean, {"refresh_seconds": 60})
        self.assertEqual(set(errors), {"webhook.secret", "sentinel.notify_command", "signed_dir_x"})
        self.assertTrue(all(reason == "unknown" for reason in errors.values()))

    def test_secrets_and_commands_are_not_in_the_schema(self):
        for key in sa.FIELDS:
            self.assertFalse(re.search(r"secret|token|password|pubkey|command|key$", key.split(".")[-1]), key)

    def test_types_and_ranges(self):
        self.assertEqual(sa.check_value("refresh_seconds", 9), (False, "range"))
        self.assertEqual(sa.check_value("refresh_seconds", 10), (True, 10))
        self.assertEqual(sa.check_value("refresh_seconds", True), (False, "type"))          # a boolean is not a number
        self.assertEqual(sa.check_value("refresh_seconds", "60"), (False, "type"))
        self.assertEqual(sa.check_value("sentinel.surface.min_rate_factor", 2), (True, 2.0))
        self.assertEqual(sa.check_value("sentinel.surface.budget_share", 1.5), (False, "range"))
        self.assertEqual(sa.check_value("sentinel.enabled", 1), (False, "type"))
        self.assertEqual(sa.check_value("language", "de"), (True, "de"))
        self.assertEqual(sa.check_value("language", "xx"), (False, "enum"))
        self.assertEqual(sa.check_value("mode", "lite"), (True, "lite"))
        self.assertEqual(sa.check_value("github_owner", "JuanenRac"), (True, "JuanenRac"))
        self.assertEqual(sa.check_value("github_owner", "bad name!"), (False, "text"))
        self.assertEqual(sa.check_value("exclude", ["A-1", "b.c"]), (True, ["A-1", "b.c"]))
        self.assertEqual(sa.check_value("exclude", ["../x"]), (False, "names"))
        self.assertEqual(sa.check_value("exclude", "a"), (False, "names"))
        self.assertEqual(sa.check_value("ecosystems", "all"), (True, "all"))

    def test_paths(self):
        for bad in ("D:\\clones", "d:/x", "\\\\server\\share", "//server/share", "/mnt/d/x", "/d/x", "a\x00b", "x" * 300):
            self.assertEqual(sa.check_value("workspace_root", bad), (False, "path"), bad)
        self.assertEqual(sa.check_value("workspace_root", "C:\\clones"), (True, "C:\\clones"))
        self.assertEqual(sa.check_value("sentinel.ci_red_file", "off"), (True, "off"))
        self.assertEqual(sa.check_value("sentinel.ci_red_file", ""), (True, ""))

    def test_an_empty_or_odd_request_is_refused(self):
        for request in (None, {}, [], "x", 3):
            self.assertEqual(sa.validate(request)[1], {"_": "request"})

    def test_every_setting_has_a_label_in_the_eight_languages(self):
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for key in sa.FIELDS:
                self.assertIn("cfg.f." + key, cat, f"{lang} {key}")
            for group in sa.GROUPS:
                self.assertIn("ui.cfg_g_" + group, cat, f"{lang} {group}")
            for reason in ("range", "type", "enum", "path", "text", "names", "ecosystems", "unknown", "request", "unreadable"):
                self.assertIn("ui.cfg_err_" + reason, cat, f"{lang} {reason}")


class SafeWrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "actions_monitor.json"
        self.original = {"refresh_seconds": 45, "webhook": {"enabled": False, "secret": "TOP-SECRET"}, "sentinel": {"enabled": True, "notify_command": ["echo", "hi"], "budget_per_hour": 600},
                         "unknown_key": {"keep": [1, 2]}}
        self.path.write_text(json.dumps(self.original), encoding="utf-8")
        self.old_backup = sa.BACKUP_DIR
        sa.BACKUP_DIR = Path(self.tmp.name) / "config_backups"

    def tearDown(self):
        sa.BACKUP_DIR = self.old_backup
        self.tmp.cleanup()

    def test_a_write_changes_only_the_asked_keys(self):
        result = sa.apply({"refresh_seconds": 90, "sentinel.budget_per_hour": 700, "outputs.prometheus.enabled": True}, self.path)
        self.assertTrue(result["ok"])
        self.assertEqual(sorted(result["changed"]), ["outputs.prometheus.enabled", "refresh_seconds", "sentinel.budget_per_hour"])
        self.assertEqual(result["restart"], ["refresh_seconds", "sentinel.budget_per_hour"])      # the output switch applies at once
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(written["refresh_seconds"], 90)
        self.assertEqual(written["sentinel"]["budget_per_hour"], 700)
        self.assertEqual(written["outputs"]["prometheus"]["enabled"], True)
        self.assertEqual(written["webhook"], self.original["webhook"])                              # the secret is untouched, byte for byte
        self.assertEqual(written["sentinel"]["notify_command"], ["echo", "hi"])
        self.assertEqual(written["unknown_key"], {"keep": [1, 2]})

    def test_a_backup_is_made_before_writing(self):
        sa.apply({"refresh_seconds": 90}, self.path)
        copies = list(sa.BACKUP_DIR.glob("actions_monitor-*.json"))
        self.assertEqual(len(copies), 1)
        self.assertEqual(json.loads(copies[0].read_text(encoding="utf-8")), self.original)

    def test_only_the_last_backups_are_kept(self):
        for n in range(sa.BACKUPS + 4):
            sa.apply({"refresh_seconds": 100 + n}, self.path)
        self.assertEqual(len(list(sa.BACKUP_DIR.glob("actions_monitor-*.json"))), sa.BACKUPS)

    def test_one_invalid_value_writes_nothing(self):
        before = self.path.read_text(encoding="utf-8")
        result = sa.apply({"refresh_seconds": 90, "sentinel.budget_per_hour": 99999}, self.path)
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"], {"sentinel.budget_per_hour": "range"})
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)
        self.assertFalse(sa.BACKUP_DIR.exists())

    def test_the_same_value_changes_nothing_and_makes_no_backup(self):
        result = sa.apply({"refresh_seconds": 45}, self.path)
        self.assertEqual(result, {"ok": True, "changed": [], "restart": [], "backup": False})
        self.assertFalse(sa.BACKUP_DIR.exists())

    def test_a_broken_file_is_never_overwritten(self):
        self.path.write_text("{not json", encoding="utf-8")
        result = sa.apply({"refresh_seconds": 90}, self.path)
        self.assertEqual(result, {"ok": False, "errors": {"_": "unreadable"}})
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{not json")

    def test_no_temporary_file_is_left(self):
        sa.apply({"refresh_seconds": 90}, self.path)
        self.assertEqual([p.name for p in Path(self.tmp.name).glob("*.tmp")], [])

    def test_the_description_never_carries_a_secret(self):
        text = json.dumps(sa.describe(self.path))
        self.assertNotIn("TOP-SECRET", text)
        self.assertNotIn("notify_command", text)
        described = {f["key"]: f for g in sa.describe(self.path)["groups"] for f in g["fields"]}
        self.assertEqual(described["refresh_seconds"]["value"], 45)
        self.assertEqual(described["refresh_seconds"]["min"], 10)
        self.assertTrue(described["refresh_seconds"]["restart"])
        self.assertFalse(described["outputs.prometheus.enabled"]["restart"])
        self.assertIs(described["outputs.prometheus.enabled"]["value"], False)


class Endpoints(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "actions_monitor.json"
        self.path.write_text(json.dumps({"refresh_seconds": 45, "webhook": {"secret": "TOP-SECRET"}}), encoding="utf-8")
        self.saved = (am.CONFIG_FILE, sa.BACKUP_DIR, sa.CONFIG_FILE)
        am.CONFIG_FILE, sa.BACKUP_DIR = self.path, Path(self.tmp.name) / "config_backups"
        import toolconfig
        self.saved_raw = toolconfig.CONFIG_FILE
        toolconfig.CONFIG_FILE = self.path
        toolconfig.forget()
        am.RESTART_PENDING.clear()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        import toolconfig
        self.server.shutdown()
        self.server.server_close()
        am.CONFIG_FILE, sa.BACKUP_DIR, sa.CONFIG_FILE = self.saved
        toolconfig.CONFIG_FILE = self.saved_raw
        toolconfig.forget()
        am.RESTART_PENDING.clear()
        self.tmp.cleanup()

    def call(self, path, body=None, host=None, origin=None, ctype="application/json", method=None):
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method or ("POST" if data is not None else "GET"))
        if data is not None and ctype:
            req.add_header("Content-Type", ctype)
        if host:
            req.remove_header("Host")
            req.add_unredirected_header("Host", host)
        if origin:
            req.add_header("Origin", origin)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers.get("Content-Type", ""), error.read()

    def test_get_settings(self):
        code, _, body = self.call("/api/settings")
        j = json.loads(body)
        self.assertEqual(code, 200)
        self.assertTrue(j["ok"])
        self.assertNotIn(b"TOP-SECRET", body)
        self.assertEqual({g["id"] for g in j["groups"]}, set(sa.GROUPS))

    def test_post_settings_saves_and_reports_the_restart(self):
        code, _, body = self.call("/api/settings", {"changes": {"refresh_seconds": 120, "outputs.json.enabled": True}})
        j = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(j["restart"], ["refresh_seconds"])
        self.assertEqual(j["restart_pending"], ["refresh_seconds"])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["refresh_seconds"], 120)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["webhook"]["secret"], "TOP-SECRET")
        _, _, again = self.call("/api/settings")
        self.assertEqual(json.loads(again)["restart_pending"], ["refresh_seconds"])

    def test_post_refuses_what_it_should(self):
        self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 1}})[0], 400)
        self.assertEqual(self.call("/api/settings", {"changes": {"webhook.secret": "x"}})[0], 400)
        self.assertEqual(self.call("/api/settings", {"nothing": 1})[0], 400)
        self.assertEqual(self.call("/api/settings", b"not json")[0], 400)
        self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 99}}, ctype="text/plain")[0], 415)
        self.assertEqual(self.call("/api/settings", b"x" * (sa.MAX_BODY + 1))[0], 413)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["refresh_seconds"], 45)

    def test_only_this_machine_may_ask(self):
        self.assertEqual(self.call("/api/settings", host="evil.example:80")[0], 403)
        self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 99}}, host="evil.example:80")[0], 403)
        self.assertEqual(self.call("/api/settings", {"changes": {"refresh_seconds": 99}}, origin="http://evil.example")[0], 403)
        self.assertEqual(self.call("/metrics", host="evil.example:80")[0], 403)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["refresh_seconds"], 45)

    def test_the_outputs_are_off_by_default_and_on_when_switched(self):
        for path in ("/metrics", "/api/outputs/grafana.json", "/api/outputs/dashboard.json"):
            self.assertEqual(self.call(path)[0], 404, path)
        self.call("/api/settings", {"changes": {"outputs.prometheus.enabled": True, "outputs.json.enabled": True, "outputs.dashboard.enabled": True}})
        code, ctype, body = self.call("/metrics")
        self.assertEqual(code, 200)
        self.assertIn("text/plain", ctype)
        self.assertIn(b"ghamon_info", body)
        code, _, body = self.call("/api/outputs/grafana.json")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["schema"], 1)
        self.assertIn(self.call("/api/outputs/dashboard.json")[0], (200, 503))


SNAP = {"generated": "2026-11-05T10:00:00Z", "enabled": True, "loading": "", "ecosystems": {"A-ONE": "armor", "A-TWO": "armor", "U-ONE": "urtc"},
        "a2": {"red": [{"repo": "A-ONE", "workflow": "ci.yml", "conclusion": "failure", "since": "2026-11-05T06:00:00Z", "streak": 3, "url": "u"},
                       {"repo": "U-ONE", "workflow": "build \"x\".yml", "conclusion": "timed_out", "since": "2026-11-05T09:00:00Z", "streak": 1, "url": "v"}]},
        "a5": {"pending_sign": [{"repo": "A-TWO", "workflow": "pkg.yml", "hours": 30.5, "state": "built_on_gha", "signature_kind": "none", "signature_verified": "unknown", "url": "w"}]},
        "a10": {"paused": {"remaining": 700, "needed": 2000}}, "api": {"calls_last_hour": 120, "budget_per_hour": 600}}
DATA = {"rate": {"remaining": 4000, "limit": 5000}, "repos": ["A-ONE", "A-TWO", "U-ONE"], "active": [{"stuck": True}, {"stuck": False}], "failing": [{}], "issues": [{}, {}], "paused_quota": False}
NOW = float(__import__("calendar").timegm((2026, 11, 5, 10, 0, 0)))   # 2026-11-05T10:00:00Z


class Metrics(unittest.TestCase):
    def lines(self, **kw):
        return outputs.metrics_text(SNAP, DATA, now=NOW, **kw).splitlines()

    def test_the_format(self):
        text = "\n".join(self.lines())
        for name in re.findall(r"^# TYPE (\S+) gauge$", text, re.M):
            self.assertTrue(name.startswith("ghamon_"))
            self.assertRegex(name, r"^[a-z_][a-z0-9_]*$")
            self.assertIn(f"# HELP {name} ", text)
        for line in self.lines():
            self.assertTrue(line.startswith("#") or re.match(r'^ghamon_[a-z0-9_]+(\{[^}]*\})? -?[0-9.]+$', line), line)
        self.assertTrue(outputs.metrics_text(SNAP, DATA).endswith("\n"))

    def test_the_figures(self):
        text = "\n".join(self.lines())
        self.assertIn("ghamon_red_workflows 2", text)
        self.assertIn("ghamon_red_repos 2", text)
        self.assertIn('ghamon_ecosystem_red_workflows{ecosystem="armor"} 1', text)
        self.assertIn('ghamon_ecosystem_red_workflows{ecosystem="urtc"} 1', text)
        self.assertIn('ghamon_workflow_red_streak{ecosystem="armor",repo="A-ONE",workflow="ci.yml"} 3', text)
        self.assertIn('ghamon_workflow_red_hours{ecosystem="armor",repo="A-ONE",workflow="ci.yml"} 4.0', text)
        self.assertIn("ghamon_pending_sign 1", text)
        self.assertIn("ghamon_pending_sign_hours_max 30.5", text)
        self.assertIn("ghamon_surface_paused 1", text)
        self.assertIn("ghamon_surface_paused_remaining 700", text)
        self.assertIn("ghamon_api_rate_remaining 4000", text)
        self.assertIn("ghamon_runs_stuck 1", text)
        self.assertIn("ghamon_snapshot_complete 1", text)

    def test_labels_are_escaped(self):
        self.assertIn('workflow="build \\"x\\".yml"', "\n".join(self.lines()))

    def test_per_repo_series_can_be_left_out(self):
        text = "\n".join(self.lines(per_repo=False))
        self.assertNotIn("ghamon_repo_red_workflows", text)
        self.assertNotIn("ghamon_workflow_red_streak", text)
        self.assertIn("ghamon_ecosystem_red_workflows", text)

    def test_an_incomplete_snapshot_says_so(self):
        text = outputs.metrics_text(dict(SNAP, loading="starting"), DATA, now=NOW)
        self.assertIn("ghamon_snapshot_complete 0", text)

    def test_nothing_known_gives_no_invented_zero(self):
        text = outputs.metrics_text(None, None)
        self.assertIn("ghamon_snapshot_complete 0", text)
        for name in ("red_workflows", "api_rate_remaining", "runs_active", "pending_sign"):
            self.assertNotIn("ghamon_" + name, text)

    def test_grafana_source_and_dashboard_document(self):
        g = outputs.grafana_json(SNAP, DATA)
        self.assertEqual(g["summary"]["red_workflows"], 2)
        self.assertEqual({r["repo"] for r in g["red"]}, {"A-ONE", "U-ONE"})
        self.assertEqual(g["pending_sign"][0]["hours"], 30.5)
        self.assertEqual({e["ecosystem"]: e["red_workflows"] for e in g["ecosystems"]}, {"armor": 1, "urtc": 1})
        self.assertEqual(json.loads(json.dumps(g)), g)
        self.assertEqual(outputs.dashboard_json(SNAP)["schema"], 2)
        self.assertIsNone(outputs.dashboard_json(None))
        self.assertIsNone(outputs.dashboard_json({"enabled": False}))

    def test_the_grafana_example_is_valid_and_points_at_the_documented_names(self):
        path = HERE / "docs" / "grafana" / "monitor_dashboard.json"
        board = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("panels", board)
        exprs = " ".join(t.get("expr", "") + t.get("url", "") for p in board["panels"] for t in p.get("targets", []))
        for name in ("ghamon_red_workflows", "ghamon_pending_sign", "ghamon_api_rate_remaining", "ghamon_surface_paused", "ghamon_snapshot_complete"):
            self.assertIn(name, exprs)


class Icons(unittest.TestCase):
    page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")

    def test_every_used_icon_exists_in_the_sprite(self):
        defined = set(re.findall(r'<symbol id="i-([a-z0-9]+)"', self.page))
        used = set(re.findall(r'href="#i-([a-z0-9]+)"', self.page))
        self.assertTrue(used)
        self.assertEqual(used - defined, set())

    def test_every_icon_is_decorative_and_its_button_has_a_name(self):
        for svg in re.findall(r"<svg class=\"ico\"[^>]*>", self.page):
            self.assertIn('aria-hidden="true"', svg)
        # a button or link that holds only an icon must carry its own accessible name and tooltip
        for tag in re.findall(r'<(?:button|a)\b[^>]*>(?:<svg class="ico"[^>]*><use [^>]*/></svg>)</(?:button|a)>', self.page):
            self.assertTrue(re.search(r'data-i18n-aria="|aria-label="', tag), tag[:120])
            self.assertTrue(re.search(r'data-i18n-title="|title="', tag) or "hotonly" in tag, tag[:120])
        hot = re.search(r'<button id="hotonly"[^>]*>', self.page).group(0)
        self.assertIn("ib", hot)

    def test_the_page_embeds_the_labels_of_the_settings(self):
        for lang in i18n.LANGS:
            embedded = i18n.ui_catalogues()[lang]
            for key in sa.FIELDS:
                self.assertIn("cfg.f." + key, embedded, f"{lang} {key}")

    def test_the_labels_of_the_icons_exist_in_the_eight_languages(self):
        keys = set(re.findall(r'data-i18n-(?:aria|title)="(ui\.ic_[a-z_]+)"', self.page)) | {"ui.ic_theme", "ui.ic_dense", "ui.ic_hotonly_on", "ui.ic_hotonly_off"}
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for key in keys:
                self.assertIn(key, cat, f"{lang} {key}")
                self.assertTrue(cat[key].strip())

    def test_the_buttons_have_the_relief_light_and_press_effects(self):
        self.assertRegex(self.page, r"button:hover\{[^}]*box-shadow")
        self.assertRegex(self.page, r"button:active[^{]*\{[^}]*translateY")
        self.assertIn("prefers-reduced-motion", self.page)

    def test_language_theme_and_density_live_in_the_settings_tab(self):
        cfg = self.page.split('id="t-cfg"', 1)[1].split("</main>", 1)[0]
        for ident in ('id="lang"', 'id="theme"', 'id="dense"'):
            self.assertIn(ident, cfg)
        header = self.page.split("<header>", 1)[1].split("</header>", 1)[0]
        for ident in ('id="lang"', 'id="theme"', 'id="dense"'):
            self.assertNotIn(ident, header)


class PageLife(unittest.TestCase):
    """1.5.0: the life of the page (animations that stop with prefers-reduced-motion, figures that count up, tooltips), the ordered unsigned figure and the issue suggestion."""
    page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")

    def test_every_animation_is_inside_the_no_preference_query_or_switched_off(self):
        marker = "@media (prefers-reduced-motion:"
        for match in re.finditer(r"animation:", self.page):
            start = self.page.rfind(marker, 0, match.start())
            self.assertGreaterEqual(start, 0, self.page[match.start() - 60:match.start() + 40])
            kind = self.page[start + len(marker):start + len(marker) + 13]
            self.assertTrue(kind == "no-preference" or self.page[match.start():match.start() + 14] == "animation:none", self.page[match.start() - 60:match.start() + 40])
        self.assertIn("@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}", self.page)

    def test_the_header_figures_count_up_unless_the_user_asks_for_less_motion(self):
        self.assertIn("function kSet(", self.page)
        self.assertIn("REDUCED.matches", self.page)
        self.assertIn("requestAnimationFrame", self.page)
        for ident in ("k-active", "k-queued", "k-fail", "k-ok", "k-issues", "k-min", "k-red", "k-sign"):
            self.assertIn(f'kSet("{ident}"', self.page)
            self.assertNotIn(f'$("{ident}").textContent=', self.page)

    def test_hovering_a_bar_highlights_it_and_gives_a_tooltip(self):
        self.assertIn(".rrow:hover .rbar", self.page)
        self.assertIn("function tipRows()", self.page)

    def test_the_unsigned_figure_is_ordered_by_the_longest_wait(self):
        self.assertIn("const signWait=", self.page)
        self.assertRegex(self.page, r"sort\(\(a,b\)=>\(w\[b\]\|\|0\)-\(w\[a\]\|\|0\)")
        for lang in i18n.LANGS:
            self.assertIn("{h}", i18n.catalogue(lang)["ui.k_sign_oldest"])

    def test_a_failure_issue_with_a_green_workflow_shows_the_command_to_copy_and_never_runs_it(self):
        self.assertIn('x.key==="issue_close"', self.page)
        self.assertIn('data-copy="${esc(m[3])}"', self.page)
        self.assertNotRegex(self.page, r"fetch\([^)]*issue[^)]*close")


if __name__ == "__main__":
    unittest.main()
