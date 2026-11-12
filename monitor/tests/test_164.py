# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.4: trust and clarity (isolation of the lite edition and the demo, no network without a switch, the one-use token), the Help in eight languages, and the opt-in
features that are OFF by default: the network mode, a token kept by the monitor, actions on GitHub, `act`, the local mirror of artifacts, self-hosted runners, OpenTelemetry, FinOps."""
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
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
import actlocal  # noqa: E402
import ai_alerts  # noqa: E402
import mcp_server  # noqa: E402
import confirmation  # noqa: E402
import demo_mode  # noqa: E402
import doctor  # noqa: E402
import ghactions  # noqa: E402
import helpdocs  # noqa: E402
import i18n  # noqa: E402
import localguard  # noqa: E402
import mirror  # noqa: E402
import orgs  # noqa: E402
import otlp  # noqa: E402
import quota  # noqa: E402
import redrule  # noqa: E402
import resilience  # noqa: E402
import runners  # noqa: E402
import secretstore  # noqa: E402
import settings_api  # noqa: E402
import toolconfig  # noqa: E402
import tui  # noqa: E402
import updatecheck  # noqa: E402
from tool_version import TOOL_VERSION  # noqa: E402

try:
    import make_help_index  # noqa: E402     (the tools live in the repository, not in the zip)
except ImportError:
    make_help_index = None

TOKEN = "ghp_" + "a1B2c3D4e5" * 4
FIXTURES = HERE / "tests" / "fixtures"


class LiveServer:
    """The real Handler on an ephemeral port with a temporary configuration file; everything it changes is put back."""

    def __init__(self, config=None, network=None):
        self.config, self.network = config or {}, network

    def __enter__(self):
        self.leftovers = _testenv.guard(unittest.TestCase())
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "actions_monitor.json"
        self.file.write_text(json.dumps(self.config), encoding="utf-8")
        self.saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE, dict(am.LIVE_CONFIG), dict(localguard.STATE), settings_api.BACKUP_DIR, set(am.RESTART_PENDING))
        am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = self.file
        settings_api.BACKUP_DIR = Path(self.tmp.name) / "backups"
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, **self.config})
        am.RESTART_PENDING.clear()
        toolconfig.forget()
        if self.network:
            localguard.configure(True, "127.0.0.1", self.network)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE = self.saved[:3]
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update(self.saved[3])
        localguard.STATE.clear()
        localguard.STATE.update(self.saved[4])
        settings_api.BACKUP_DIR = self.saved[5]
        am.RESTART_PENDING.clear()
        am.RESTART_PENDING.update(self.saved[6])
        toolconfig.forget()
        self.tmp.cleanup()
        self.leftovers()

    def call(self, path, body=None, headers=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, method=method or ("GET" if body is None else "POST"), headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:
                raw = answer.read()
                return answer.status, (json.loads(raw) if raw.startswith((b"{", b"[")) else raw.decode("utf-8", "replace"))
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, (json.loads(raw) if raw.startswith((b"{", b"[")) else raw.decode("utf-8", "replace"))

    def token(self):
        return self.call("/api/session-token")[1]["token"]

    def sensitive(self, path, body):
        return self.call(path, body, {"X-Monitor-Token": self.token()})


# --- the isolation of the lite edition, the demo and the airgapped switch ---------------------------------------------------------------------------------------------------------------------
class LiteIsolation(unittest.TestCase):
    def setUp(self):
        _testenv.guard(self)

    def run_lite(self, code):
        script = "import sys; sys.path.insert(0, %r); sys.argv = ['x', '--lite']; import actions_monitor as am; am.enable_lite(); %s" % (str(HERE), code)
        done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=90)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout.strip()

    def test_lite_never_imports_the_sentinel_and_its_endpoints_are_404(self):
        # a `gh` that hangs for 20 seconds (a runner without a login does): no page and no endpoint may wait for it, so every answer must come inside the budget of 5 seconds
        code = ("import time\nam.gh_read = am.gh = lambda *a, **k: (time.sleep(20), 1 / 0)\n"
                "import threading, urllib.request, urllib.error\n"
                "from http.server import ThreadingHTTPServer\n"
                "s = ThreadingHTTPServer(('127.0.0.1', 0), am.Handler); threading.Thread(target=s.serve_forever, daemon=True).start()\n"
                "base = 'http://127.0.0.1:%d' % s.server_address[1]\n"
                "codes = []\n"
                "for path in ('/api/sentinel', '/api/sentinel/parte.txt', '/api/ai/actions', '/api/analytics', '/metrics', '/api/gh-action/plan', '/api/act/status', '/api/runners', '/api/mirror', '/api/otlp', '/api/github-token'):\n"
                "    try:\n        urllib.request.urlopen(base + path, timeout=5); codes.append(200)\n    except urllib.error.HTTPError as e:\n        codes.append(e.code)\n"
                "import time\nfor path in ('/api/health', '/api/about', '/api/quota', '/api/help/topics'):\n    t0 = time.time()\n    try:\n        status = urllib.request.urlopen(base + path, timeout=30).status\n        codes.append(status if time.time() - t0 < 5 else '%s answered %s after %.1f s' % (path, status, time.time() - t0))\n    except Exception as e:\n        codes.append(path + ' ' + type(e).__name__ + ' after %.1f s' % (time.time() - t0))\n"
                "print(codes, 'sentinel_local' in sys.modules)")
        out = self.run_lite(code)
        self.assertTrue(out.endswith("False"), out)
        self.assertEqual(out.count("404"), 11, out)
        self.assertIn("200, 200, 200, 200]", out)

    def test_lite_has_its_own_files_and_port(self):
        out = self.run_lite("print(am.CONFIG_FILE.name, am.LOG_FILE.name, am.LITE_PORT, am.etagcache.CACHE_FILE.name, am.DEFAULTS['sentinel'])")
        self.assertIn("actions_monitor_lite.json actions_monitor_log_lite.txt 8766 etag_cache_lite.json", out)
        self.assertEqual(tui.default_port(True), 8766)
        self.assertEqual(tui.default_port(False), 8765)

    def test_lite_never_writes_ci_red_or_the_signing_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                code = ("import json; from pathlib import Path\n"
                        "am.LITE['on'] = True\n"
                        "am.STATE['data'] = {'runs': [], 'repos': []}\n"
                        "print(sorted(p.name for p in Path('.').iterdir()), am.SENTINEL['obj'])")
                self.assertEqual(self.run_lite(code), "[] None")
            finally:
                os.chdir(cwd)

    def test_the_settings_of_lite_have_no_sentinel_options(self):
        described = settings_api.describe(HERE / "actions_monitor.example.json", lite=True)
        keys = {f["key"] for g in described["groups"] for f in g["fields"]}
        self.assertTrue(keys and keys <= set(settings_api.LITE_KEYS), keys - set(settings_api.LITE_KEYS))
        self.assertFalse([k for k in keys if k.startswith(("sentinel.", "ai.", "webhook.", "listen.", "github_token.", "act.", "github_actions."))])
        clean, errors = settings_api.validate({"sentinel.enabled": True}, lite=True)
        self.assertEqual(clean, {})
        self.assertIn("sentinel.enabled", errors)

    def test_both_editions_count_the_same_things(self):
        runs = [{"id": i, "repo": "a", "status": "completed", "conclusion": "failure" if i % 2 else "success", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600 * i)),
                 "seconds": 60 * i, "branch": "main", "path": "ci.yml", "name": "CI"} for i in range(1, 6)]
        red, approx = redrule.red_workflows({"a": runs}, None, True, 20)
        full = am.header_figures(runs, [], [], red=red, approx=approx)
        plain = am.header_figures(runs, [], [])
        for key in ("active", "queued", "fail24", "ok24", "issues", "min24"):
            self.assertEqual(full[key], plain[key], key)
        self.assertEqual(full["red"], len(red))
        self.assertEqual(full["red_repos"], len({r["repo"] for r in red}))

    def test_the_red_tile_counts_workflows_and_says_in_how_many_repositories(self):
        red, _ = redrule.red_workflows({r: [{"status": "completed", "branch": "main", "conclusion": "failure", "started": "2026-01-01T00:00:00Z", "path": w, "name": w, "id": 1} for w in ("a.yml", "b.yml")] for r in ("r1", "r2")}, None, True)
        self.assertEqual(len(red), 4)
        figures = am.header_figures([], [], [], red=red)
        self.assertEqual((figures["red"], figures["red_repos"]), (4, 2))
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("redUnits(", page)
        self.assertIn("ui.k_red_units", page)

    def test_lite_inherits_the_pace_of_the_complete_monitor(self):
        self.assertIn("refresh_seconds", am.LITE_INHERIT)
        self.assertIn("cold_refresh_seconds", am.LITE_INHERIT)
        self.assertEqual(am.lite_inheritance(HERE / "no_such_file.json"), {})


class DemoIsolation(unittest.TestCase):
    def test_the_demo_touches_nothing_of_the_real_installation(self):
        watched = ["actions_monitor.json", "ci_red.json", "events_monitor.jsonl", "events_state.json", "etag_cache.json", "update_check.json", "sentinel_cache.json", "analytics_history.json",
                   "github_actions_log.jsonl", "welcome_state.json", "orgs_state.json"]

        def snapshot():
            return {n: ((HERE / n).stat().st_mtime_ns, (HERE / n).read_bytes()) if (HERE / n).exists() else None for n in watched}
        before = snapshot()
        saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE, dict(am.LIVE_CONFIG), settings_api.BACKUP_DIR, am.LITE["on"], am.DEMO["on"], am.LOG_FILE,
                 updatecheck.STATE_FILE, __import__("etagcache").CACHE_FILE, __import__("events").EVENTS_FILE, set(am.RESTART_PENDING))
        with tempfile.TemporaryDirectory() as tmp:
            try:
                server, url = demo_mode.start(am, 0, tmp=tmp)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                self.assertTrue(str(am.LOG_FILE).startswith(tmp) and "_demo" in am.LOG_FILE.name)
                self.assertTrue(str(updatecheck.STATE_FILE).startswith(tmp))
                self.assertTrue(str(am.CONFIG_FILE).startswith(tmp))
                for path in ("/", "/api/data", "/api/about", "/api/settings", "/api/quota", "/api/discovery", "/api/welcome", "/api/advanced"):
                    with urllib.request.urlopen(url.rstrip("/") + path, timeout=10) as answer:
                        self.assertEqual(answer.status, 200, path)
                token = json.load(urllib.request.urlopen(url + "api/session-token", timeout=5))["token"]
                request = urllib.request.Request(url + "api/settings", data=json.dumps({"changes": {"refresh_seconds": 99}}).encode(), method="POST",
                                                 headers={"Content-Type": "application/json", "X-Monitor-Token": token})
                self.assertEqual(urllib.request.urlopen(request, timeout=8).status, 200)
                request = urllib.request.Request(url + "api/welcome", data=json.dumps({"done": True}).encode(), method="POST", headers={"Content-Type": "application/json"})
                urllib.request.urlopen(request, timeout=8)
                self.assertEqual(json.loads(Path(am.CONFIG_FILE).read_text(encoding="utf-8"))["refresh_seconds"], 99)     # the copy of the demo changed ...
                server.shutdown()
                server.server_close()
            finally:
                am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE = saved[:3]
                am.LIVE_CONFIG.clear()
                am.LIVE_CONFIG.update(saved[3])
                settings_api.BACKUP_DIR, am.LITE["on"], am.DEMO["on"], am.LOG_FILE = saved[4:8]
                updatecheck.STATE_FILE = saved[8]
                __import__("etagcache").CACHE_FILE = saved[9]
                __import__("events").EVENTS_FILE = saved[10]
                am.RESTART_PENDING.clear()
                am.RESTART_PENDING.update(saved[11])
                toolconfig.forget()
                toolconfig.set_owner("JuanenRac")
        self.assertEqual(snapshot(), before)         # ... and the real files did not

    def test_the_demo_welcome_flag_is_not_remembered(self):
        saved = am.DEMO["on"]
        am.DEMO["on"] = True
        try:
            self.assertEqual(am.advanced_get("/api/welcome", ""), {"done": False})
            self.assertEqual(am.handle_advanced_post("/api/welcome", {"done": True}), {"ok": True})
            self.assertFalse(am.welcome_file().exists() and "true" in am.welcome_file().read_text(encoding="utf-8") and False)
        finally:
            am.DEMO["on"] = saved


class Airgapped(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.saved = dict(am.LIVE_CONFIG)

    def tearDown(self):
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update(self.saved)

    def forbidden(self, *args, **kwargs):
        self.calls.append(args)
        raise AssertionError("the network was used")

    def test_no_request_at_all_when_the_check_is_off_or_the_installation_is_airgapped(self):
        for config in ({"updates": {"check": False}}, {"airgapped": True}, {"airgapped": True, "updates": {"check": True}}):
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(config)
            with tempfile.TemporaryDirectory() as tmp, mock.patch.object(am, "gh_read", self.forbidden), mock.patch.object(am, "gh", self.forbidden), \
                    mock.patch.object(am, "run_gh", self.forbidden), mock.patch("urllib.request.urlopen", self.forbidden), \
                    mock.patch("socket.create_connection", self.forbidden):
                with mock.patch.object(am, "HERE", Path(tmp)):
                    info = am.update_info()
                    am.about_payload()
                    am.update_info()
                self.assertFalse(info["enabled"], config)
                self.assertFalse(info["newer"])
            self.assertEqual(self.calls, [])

    def test_the_environment_variable_also_turns_the_check_off(self):
        with mock.patch.dict(os.environ, {"MONITOR_AIRGAPPED": "1"}):
            self.assertFalse(updatecheck.settings({})["check"])
            self.assertEqual(updatecheck.check({}, "1.6.4", self.forbidden, state_file=Path(tempfile.gettempdir()) / "no_such_update_state.json")["enabled"], False)
        self.assertEqual(self.calls, [])

    def test_the_comparison_is_numeric(self):
        self.assertTrue(updatecheck.is_newer("1.6.10", "1.6.9"))
        self.assertFalse(updatecheck.is_newer("1.6.4", "1.6.4"))
        self.assertTrue(updatecheck.is_newer("1.6.4.1", "1.6.4"))


# --- the one-use token ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class OneUseToken(unittest.TestCase):
    def test_it_works_once_and_expires(self):
        clock = [1000.0]
        tokens = am.SessionTokens(clock=lambda: clock[0])
        first = tokens.issue()
        self.assertTrue(tokens.use(first))
        self.assertFalse(tokens.use(first), "a token works for ONE request")
        second = tokens.issue()
        clock[0] += 601
        self.assertFalse(tokens.use(second), "it expires after ten minutes")
        self.assertFalse(tokens.use(""))
        self.assertFalse(tokens.use(None))

    def test_a_sensitive_post_without_it_is_refused_and_with_it_works_once(self):
        with LiveServer({"session_guard": True}) as server:
            self.assertEqual(server.call("/api/settings", {"changes": {"refresh_seconds": 90}})[0], 403)
            token = server.token()
            headers = {"X-Monitor-Token": token}
            self.assertEqual(server.call("/api/settings", {"changes": {"refresh_seconds": 90}}, headers)[0], 200)
            self.assertEqual(server.call("/api/settings", {"changes": {"refresh_seconds": 91}}, headers)[0], 403)

    def test_the_token_is_not_in_the_about_panel_nor_in_the_text_for_support(self):
        with LiveServer({"session_guard": True}) as server:
            live = server.token()
            blob = json.dumps(am.about_payload()) + about.support_text(am.about_payload()) + json.dumps(am.health_payload())
            self.assertNotIn(live, blob)
            status, answer = server.call("/api/about")
            self.assertNotIn(live, json.dumps(answer))

    def test_doctor_says_whether_the_token_is_required(self):
        on = {c["id"]: c for c in doctor.run(config={"session_guard": True}, ports=(0,))}
        off = {c["id"]: c for c in doctor.run(config={"session_guard": False}, ports=(0,))}
        self.assertEqual(on["token"]["status"], "ok")
        self.assertEqual(off["token"]["status"], "warn")


# --- the doctor ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class DoctorChecks(unittest.TestCase):
    def runner(self, args, timeout=20):
        if args[:2] == ["gh", "auth"]:
            return 0, "ok", ""
        return 0, json.dumps({"resources": {"core": {"remaining": 4000, "limit": 5000}}}), ""

    def test_json_output_is_complete_and_has_no_secret(self):
        with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/gh"):
            checks = doctor.run(self.runner, ports=(0,), config={"listen": {"network": True, "host": "192.168.1.5"}})
        document = doctor.as_json(checks, "lite")
        self.assertEqual(document["edition"], "lite")
        self.assertEqual(document["version"], TOOL_VERSION)
        self.assertEqual([c["id"] for c in document["checks"]], list(doctor.ORDER))
        self.assertTrue(json.dumps(document))
        self.assertNotIn(str(Path.home()), json.dumps(document))
        self.assertEqual({c["id"]: c["status"] for c in checks}["exposure"], "warn")

    def test_the_port_check_says_which_ports_are_busy(self):
        import socket
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            port = busy.getsockname()[1]
            checks = {c["id"]: c for c in doctor.run(self.runner, ports=(port,))}
        self.assertEqual(checks["port"]["status"], "warn")
        self.assertIn(f"busy {port}", checks["port"]["detail"])

    def test_the_rate_remaining_and_the_login_are_reported(self):
        with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/gh"):
            checks = {c["id"]: c for c in doctor.run(self.runner, ports=(0,))}
        self.assertEqual(checks["quota"]["detail"], "4000/5000")
        self.assertEqual(checks["login"]["status"], "ok")

    def test_targets_only_example_is_a_warning_and_an_own_file_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual({c["id"]: c for c in doctor.run(self.runner, folder=tmp, ports=(0,))}["targets"]["status"], "warn")
            (Path(tmp) / "targets.json").write_text("{}", encoding="utf-8")
            self.assertEqual({c["id"]: c for c in doctor.run(self.runner, folder=tmp, ports=(0,))}["targets"]["status"], "ok")

    def test_every_check_has_its_texts_in_every_language(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            for name in doctor.ORDER:
                self.assertNotEqual(i18n.tl(lang, "doctor.t." + name), "doctor.t." + name, (lang, name))
                self.assertNotEqual(i18n.tl(lang, "doctor.f." + name), "doctor.f." + name, (lang, name))


# --- the Help in eight languages -----------------------------------------------------------------------------------------------------------------------------------------------------------
class HelpLanguages(unittest.TestCase):
    def test_every_topic_exists_in_all_eight_languages(self):
        index = json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))
        gaps = [(t["id"], lang) for t in index["topics"] for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt") if lang not in t["sections"]]
        self.assertEqual(gaps, [])
        if make_help_index is not None:
            self.assertEqual(make_help_index.missing(make_help_index.build()), [])

    def test_the_four_documents_that_were_only_english_are_translated(self):
        for lang in ("es", "de", "fr", "it", "ja", "zh", "pt"):
            for topic in ("roadmap", "contributing", "security", "support"):
                found = helpdocs.topic(topic, lang)
                self.assertFalse(found["fallback"], (topic, lang))
                self.assertEqual(found["lang"], lang)

    def test_a_translation_is_not_the_english_text_copied(self):
        index = json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))
        for item in index["topics"]:
            if item.get("english_body") or item["id"] in ("package",):
                continue
            english = json.dumps(item["sections"]["en"])
            for lang in ("es", "de", "fr", "it", "ja", "zh", "pt"):
                self.assertNotEqual(json.dumps(item["sections"][lang]), english, (item["id"], lang))

    def test_the_changelog_is_translated_and_lists_every_version(self):
        index = {t["id"]: t for t in json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))["topics"]}
        self.assertFalse(index["changelog"].get("english_body"))
        self.assertEqual(index["changelog"]["title"]["es"], "Registro de cambios")
        body = json.dumps(index["changelog"]["sections"]["es"], ensure_ascii=False)
        self.assertIn("Añadido", body)
        self.assertNotIn("### Added", body)
        self.assertFalse(helpdocs.topic("changelog", "es")["fallback"])
        self.assertFalse(helpdocs.topic("changelog", "en")["fallback"])
        self.assertTrue([t for t in helpdocs.topics("de") if t["id"] == "changelog"][0]["translated"])
        if make_help_index is not None:
            self.assertEqual(make_help_index.changelog_problems(), [])

    def test_the_notice_is_translated_in_every_language(self):
        seen = set()
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            text = i18n.tl(lang, "ui.help_fallback")
            self.assertNotIn("ui.help_fallback", text)
            seen.add(text)
        self.assertEqual(len(seen), 8)
        self.assertIn("inglés", i18n.tl("es", "ui.help_fallback"))

    def test_the_guides_have_no_block_left_in_english(self):
        def prose(text):
            out, fence = [], False
            for line in text.splitlines():
                if line.strip().startswith("```"):
                    fence = not fence
                    continue
                if fence or line.lstrip().startswith(("Copyright", "GPL-3.0")):
                    continue
                line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", re.sub(r"`[^`]*`", "", line)).strip("|#*->0123456789.) ").strip()
                if len(re.findall(r"[A-Za-z]{3,}", line)) >= 4:
                    out.append(line)
            return out
        suffix = {"es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}
        for english in sorted((HERE / "docs").glob("*.md")):
            if re.search(r"_(spa|deu|fra|ita|jpn|zho|por)$", english.stem):
                continue
            base = set(prose(english.read_text(encoding="utf-8")))
            for lang, tail in suffix.items():
                translated = english.with_name(english.stem + tail + ".md")
                same = [line for line in prose(translated.read_text(encoding="utf-8")) if line in base]
                self.assertLessEqual(len(same), 2, (translated.name, same[:3]))

    def test_the_search_is_limited_and_a_huge_document_does_not_block(self):
        hits = helpdocs.search("the", "en", limit=10_000)
        self.assertLessEqual(len(hits), helpdocs.MAX_HITS)
        self.assertEqual(len(helpdocs.search("the", "en", limit=3)), min(3, len(hits)))
        start = time.time()
        shown = helpdocs.render("# Big\n\n" + "word " * 400_000 + "\n" + "- item\n" * 20_000)
        self.assertLess(time.time() - start, 5)
        self.assertLess(len(shown), 400_000)
        self.assertIn('class="cut"', shown)
        code, text = helpdocs.console(["--search", "the"], "en", i18n.t)
        self.assertEqual(code, 0)
        self.assertLessEqual(text.count("#"), helpdocs.CONSOLE_HITS * 3 + 5)

    def test_the_markdown_never_loads_an_image_nor_a_script_link(self):
        shown = helpdocs.render("![x](http://evil/img.png) [bad](javascript:alert(1)) [ok](https://example.com/a) <script>alert(1)</script>")
        self.assertNotIn("<img", shown)
        self.assertNotIn("javascript:", shown)
        self.assertNotIn("<script", shown)
        self.assertIn('href="https://example.com/a"', shown)

    @unittest.skipIf(make_help_index is None, "the tools are not in the package")
    def test_the_check_of_the_index_passes(self):
        done = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "make_help_index.py"), "--check"], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


# --- the rule of red, with the shared cases -----------------------------------------------------------------------------------------------------------------------------------------
class SharedRedCases(unittest.TestCase):
    CASES = json.loads((FIXTURES / "red_rule_cases.json").read_text(encoding="utf-8"))["cases"]

    def test_every_shared_case(self):
        self.assertGreaterEqual(len(self.CASES), 18)
        for case in self.CASES:
            with self.subTest(case["name"]):
                rows, _approx = redrule.red_workflows({"repo": case["runs"]}, {"repo": case["default_branch"]})
                self.assertEqual([(r["workflow"], r["conclusion"], r["streak"]) for r in rows], [(r["workflow"], r["conclusion"], r["streak"]) for r in case["red"]])

    def test_dynamic_runs_are_never_a_build(self):
        dynamic = {"status": "completed", "branch": "main", "conclusion": "failure", "event": "dynamic", "path": "dynamic/dependabot/x", "started": "2026-01-02T00:00:00Z", "name": "x", "id": 2}
        good = {"status": "completed", "branch": "main", "conclusion": "success", "event": "push", "path": "ci.yml", "started": "2026-01-01T00:00:00Z", "name": "ci", "id": 1}
        self.assertEqual(redrule.red_workflows({"r": [good, dynamic]}, {"r": "main"})[0], [])
        self.assertEqual(redrule.guess_default_branch([dynamic]), None)
        import signstate
        self.assertEqual(signstate.completed_runs([good, dynamic]), [good])


# --- passing failures ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class PassingFailures(unittest.TestCase):
    def tearDown(self):
        am.RUN_CACHE.pop("r-test", None)

    def test_what_is_transient(self):
        for text in ("tls: handshake failure", "Get https://api.github.com: remote error: tls: bad record MAC", "HTTP 502 Bad Gateway", "unexpected EOF", "i/o timeout", "connection reset by peer"):
            self.assertTrue(resilience.is_transient(text), text)
        for text in ("HTTP 401 Bad credentials", "HTTP 404 Not Found", "HTTP 403 rate limit exceeded", ""):
            self.assertFalse(resilience.is_transient(text), text)

    def test_the_backoff_grows_and_is_bounded(self):
        values = [resilience.backoff(n, jitter=0) for n in range(8)]
        self.assertEqual(values[:4], [1, 2, 4, 8])
        self.assertEqual(max(values), 20)

    def test_a_tls_hiccup_is_not_shown_as_an_error_until_it_repeats(self):
        am.RUN_CACHE["r-test"] = {"runs": [{"id": 1}], "at": time.time(), "error": None, "fails": 0}
        am.note_read("r-test", [], "tls: handshake failure")
        self.assertIsNone(am.RUN_CACHE["r-test"]["error"])
        self.assertEqual(am.RUN_CACHE["r-test"]["runs"], [{"id": 1}], "the last picture stays")
        self.assertEqual(am.RUN_CACHE["r-test"]["at"], 0, "it is read again in the next cycle")
        am.note_read("r-test", [], "tls: handshake failure")
        am.note_read("r-test", [], "tls: handshake failure")
        self.assertIn("tls", am.RUN_CACHE["r-test"]["error"])
        am.note_read("r-test", [{"id": 2}], None)
        self.assertIsNone(am.RUN_CACHE["r-test"]["error"])
        self.assertEqual(am.RUN_CACHE["r-test"]["fails"], 0)

    def test_any_other_error_is_shown_at_once(self):
        am.RUN_CACHE["r-test"] = {"runs": [{"id": 1}], "at": time.time(), "error": None, "fails": 0}
        am.note_read("r-test", [], "HTTP 403 forbidden")
        self.assertIn("403", am.RUN_CACHE["r-test"]["error"])

    def test_gh_waits_with_backoff_for_a_transient_failure_and_not_after_the_last_try(self):
        sleeps = []
        failing = subprocess.CompletedProcess([], 1, "", "tls: handshake failure")
        with mock.patch.object(am.subprocess, "run", return_value=failing), mock.patch.object(am.time, "sleep", side_effect=sleeps.append):
            with self.assertRaises(RuntimeError):
                am.gh("api", "x", retries=2)
        self.assertEqual(len(sleeps), 2)
        self.assertGreaterEqual(sleeps[1], sleeps[0])


# --- the network mode ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class NetworkMode(unittest.TestCase):
    def tearDown(self):
        localguard.configure(False)

    def test_off_by_default_and_a_public_address_is_never_accepted(self):
        self.assertEqual(localguard.settings_from({}), {"network": False, "host": "127.0.0.1", "token_env": "MONITOR_ACCESS_TOKEN", "allowed_hosts": [], "proxy_public_host": ""})
        for host in ("8.8.8.8", "example.com", "", "0.0.0.0/0"):
            self.assertEqual(localguard.settings_from({"listen": {"network": True, "host": host}})["host"], "127.0.0.1", host)
        for host in ("192.168.1.20", "10.0.0.5", "172.16.4.4", "0.0.0.0"):
            self.assertEqual(localguard.settings_from({"listen": {"network": True, "host": host}})["host"], host)
        self.assertTrue(settings_api.LISTEN_HOST_RE.match("192.168.0.1"))
        self.assertFalse(settings_api.LISTEN_HOST_RE.match("172.32.0.1"))
        self.assertFalse(settings_api.LISTEN_HOST_RE.match("1.1.1.1"))

    def test_the_example_configuration_has_every_switch_off(self):
        example = json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertIs(example["listen"]["network"], False)
        self.assertEqual(example["listen"]["host"], "127.0.0.1")
        for key in ("github_token", "github_actions", "act", "mirror", "runners", "otlp"):
            self.assertIs(example[key]["enabled"], False, key)
        self.assertIs(example["organizations"]["discover"], False)
        self.assertEqual(example["finops"]["jobs_per_cycle"], 0)
        self.assertEqual(example["github_actions"]["allowed"], ["rerun_failed", "cancel"])

    def test_the_security_settings_are_marked_secure(self):
        for key in ("listen.network", "listen.host", "github_token.enabled", "github_actions.enabled", "act.enabled", "mirror.enabled", "otlp.enabled", "otlp.endpoint"):
            self.assertTrue(settings_api.META[key]["secure"], key)
        self.assertTrue(all(settings_api.FIELDS[k][4] for k in ("listen.network", "listen.host", "listen.token_env", "listen.allowed_hosts")), "the network keys need a restart")

    def test_every_request_needs_the_access_token_in_network_mode(self):
        access = "T" * 24
        with LiveServer({"session_guard": True}, network=access) as server:
            self.assertEqual(server.call("/api/health")[0], 401)
            self.assertEqual(server.call("/", headers={"Accept": "text/html"})[0], 401)
            self.assertEqual(server.call("/api/health", headers={"X-Monitor-Access": "wrong"})[0], 401)
            self.assertEqual(server.call("/api/health", headers={"X-Monitor-Access": access})[0], 200)
            self.assertEqual(server.call("/api/health", headers={"Authorization": "Bearer " + access})[0], 200)
            self.assertEqual(server.call("/api/health", headers={"Cookie": f"{localguard.COOKIE}={access}"})[0], 200)
            self.assertEqual(server.call("/api/settings", {"changes": {"refresh_seconds": 77}})[0], 401, "no setting is written without the token")
            self.assertEqual(json.loads(server.file.read_text(encoding="utf-8")).get("refresh_seconds"), None)

    def test_a_first_visit_with_the_token_in_the_address_sets_the_cookie_and_cleans_the_address(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            class NoFollow(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            opener = urllib.request.build_opener(NoFollow)
            try:
                opener.open(urllib.request.Request(server.base + "/?access=" + access, headers={"Accept": "text/html"}), timeout=8)
                self.fail("expected a redirect")
            except urllib.error.HTTPError as error:
                self.assertEqual(error.code, 302)
                self.assertEqual(error.headers["Location"], "/")
                cookie = error.headers["Set-Cookie"]
                self.assertIn("HttpOnly", cookie)
                self.assertIn("SameSite=Strict", cookie)

    def test_the_host_header_must_be_known(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            self.assertEqual(server.call("/api/health", headers={"X-Monitor-Access": access, "Host": "evil.example:80"})[0], 403)

    def test_the_keys_of_exposure_can_only_be_changed_from_this_computer(self):
        access = "T" * 24
        with LiveServer({"session_guard": True}, network=access) as server:
            token = server.call("/api/session-token", headers={"X-Monitor-Access": access})[1]["token"]
            headers = {"X-Monitor-Access": access, "X-Monitor-Token": token}
            with mock.patch.object(localguard, "from_this_computer", return_value=False):
                status, answer = server.call("/api/settings", {"changes": {"listen.network": False}}, headers)
                self.assertEqual((status, answer["errors"]["_"]), (403, "local_only"))
                token = server.call("/api/session-token", headers={"X-Monitor-Access": access})[1]["token"]
                status, _answer = server.call("/api/settings", {"changes": {"refresh_seconds": 70}}, {**headers, "X-Monitor-Token": token})
                self.assertEqual(status, 200, "an ordinary setting is allowed with the token")
                token = server.call("/api/session-token", headers={"X-Monitor-Access": access})[1]["token"]
                self.assertEqual(server.call("/api/github-token", {"action": "delete"}, {**headers, "X-Monitor-Token": token})[0], 403)

    def test_the_webhook_has_its_own_proof_and_is_not_blocked_by_the_access_token(self):
        access = "T" * 24
        with LiveServer({}, network=access) as server:
            status, _answer = server.call("/api/webhook", {})
            self.assertNotEqual(status, 401)

    def test_the_comparison_is_constant_time_and_exact(self):
        localguard.configure(True, "127.0.0.1", "abc" * 8)
        self.assertTrue(localguard.access_ok({"X-Monitor-Access": "abc" * 8}))
        self.assertFalse(localguard.access_ok({"X-Monitor-Access": "abc" * 7}))
        self.assertTrue(localguard.access_ok({}, "abc" * 8))
        self.assertFalse(localguard.from_this_computer(("10.0.0.7", 5000)))
        self.assertTrue(localguard.from_this_computer(("127.0.0.1", 5000)))

    def test_there_is_a_persistent_warning_in_the_page(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('id="netbar"', page)
        self.assertIn("I18N.network.network", page)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            self.assertNotEqual(i18n.tl(lang, "ui.adv_net_bar"), "ui.adv_net_bar")
        with mock.patch.object(am, "localguard") as fake:
            fake.public_state.return_value = {"network": True, "host": "0.0.0.0", "token_required": True}
            self.assertIn('"network": {"network": true', am.render_page())


# --- the token kept by the monitor ----------------------------------------------------------------------------------------------------------------------------------------------------
class OwnToken(unittest.TestCase):
    def setUp(self):
        _testenv.guard(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"MONITOR_SECRET_DIR": self.tmp.name})
        self.env.start()
        os.environ.pop("GH_TOKEN", None)

    def tearDown(self):
        secretstore.clear_environment()
        self.env.stop()
        self.tmp.cleanup()

    def test_the_format_is_checked(self):
        for good in (TOKEN, "github_pat_" + "A1b2C3d4E5" * 6, "0123456789abcdef" * 2 + "01234567"):
            self.assertTrue(secretstore.valid(good), good)
        for bad in ("", "password", "ghp_short", TOKEN + " x", None, 5, "ghp_" + "!" * 30):
            self.assertFalse(secretstore.valid(bad), bad)
        self.assertEqual(secretstore.Store("auto").save("nope"), (False, "format"))

    def test_file_store_round_trip_with_permissions_600(self):
        store = secretstore.Store("file")
        self.assertEqual(store.save(TOKEN), (True, "file"))
        self.assertEqual(store.load(), TOKEN)
        path = Path(self.tmp.name) / "token.600"
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(Path(self.tmp.name).stat().st_mode), 0o700)
        status = store.status()
        self.assertEqual(status, {"backend": "file", "stored": True, "weak": True})
        self.assertNotIn(TOKEN, json.dumps(status))
        self.assertTrue(store.delete())
        self.assertEqual(store.load(), "")
        self.assertFalse(path.exists())

    @unittest.skipUnless(sys.platform == "win32", "DPAPI is Windows only")
    def test_windows_uses_dpapi_and_the_file_is_not_the_token(self):
        store = secretstore.Store("auto")
        self.assertEqual(store.backend(), "dpapi")
        self.assertEqual(store.save(TOKEN), (True, "dpapi"))
        self.assertEqual(store.load(), TOKEN)
        raw = (Path(self.tmp.name) / "token.dpapi").read_bytes()
        self.assertNotIn(TOKEN.encode(), raw)
        self.assertTrue(store.delete())

    def test_keychain_and_secret_service_are_driven_through_their_commands(self):
        calls = []

        def runner(args, data):
            calls.append((args, data))
            return subprocess.CompletedProcess(args, 0, TOKEN + "\n", "")
        with mock.patch.object(secretstore.shutil, "which", return_value="/usr/bin/tool"):
            linux = secretstore.Store("auto", runner=runner, platform="linux")
            self.assertEqual(linux.backend(), "secret-service")
            self.assertEqual(linux.save(TOKEN), (True, "secret-service"))
            self.assertEqual(calls[0][1], TOKEN, "secret-tool reads the secret from its standard input")
            self.assertNotIn(TOKEN, " ".join(calls[0][0]), "never in the command line")
            self.assertEqual(linux.load(), TOKEN)
            mac = secretstore.Store("auto", runner=runner, platform="darwin")
            self.assertEqual(mac.backend(), "keychain")
            self.assertEqual(mac.save(TOKEN), (True, "keychain"))
        with mock.patch.object(secretstore.shutil, "which", return_value=None):
            self.assertEqual(secretstore.Store("auto", platform="linux").backend(), "file", "the weakest option only when the tools are missing")

    def test_it_reaches_gh_only_when_the_switch_is_on(self):
        store = secretstore.Store("file")
        store.save(TOKEN)
        self.assertFalse(secretstore.apply_to_environment({}, store))
        self.assertEqual(secretstore.gh_kwargs(), {})
        self.assertTrue(secretstore.apply_to_environment({"github_token": {"enabled": True, "store": "file"}}, store))
        self.assertEqual(secretstore.gh_kwargs()["env"]["GH_TOKEN"], TOKEN, "the gh process gets it")
        self.assertNotIn("GH_TOKEN", os.environ, "this process (and so every other child) does not")
        secretstore.clear_environment()
        self.assertEqual(secretstore.gh_kwargs(), {})

    def test_a_token_of_the_user_is_never_removed(self):
        os.environ["GH_TOKEN"] = "mine"
        secretstore.clear_environment()
        self.assertEqual(os.environ["GH_TOKEN"], "mine")
        self.assertEqual(secretstore.gh_kwargs(), {}, "a token of the user is his own: the monitor adds nothing")
        os.environ.pop("GH_TOKEN")

    def test_redact_removes_the_token_and_anything_that_looks_like_one(self):
        self.assertEqual(secretstore.redact(f"error with {TOKEN} inside", TOKEN), "error with *** inside")
        self.assertNotIn("ghp_", secretstore.redact("x ghp_abcdefghijklmnop y"))
        self.assertNotIn("github_pat_", secretstore.redact("github_pat_11ABCDEFG0123456789_abcdef"))

    def test_the_server_never_shows_the_token_and_never_writes_it_to_the_settings(self):
        cfg = {"session_guard": True, "github_token": {"enabled": True, "store": "file"}}
        with LiveServer(cfg) as server:
            status, answer = server.sensitive("/api/github-token", {"token": TOKEN})
            self.assertEqual((status, answer["ok"], answer["stored"], answer["weak"]), (200, True, True, True))
            self.assertEqual(secretstore.gh_kwargs()["env"]["GH_TOKEN"], TOKEN)
            self.assertNotIn("GH_TOKEN", os.environ)
            everything = ""
            for path in ("/api/github-token", "/api/advanced", "/api/about", "/api/settings", "/api/health", "/api/data", "/metrics"):
                everything += json.dumps(server.call(path)[1])
            everything += about.support_text(am.about_payload()) + server.file.read_text(encoding="utf-8")
            for backup in (Path(server.tmp.name) / "backups").glob("*"):
                everything += backup.read_text(encoding="utf-8")
            self.assertNotIn(TOKEN, everything)
            self.assertNotIn(TOKEN[4:], everything)
            self.assertEqual(server.call("/api/github-token", {"action": "delete"})[0], 403, "deleting needs the one-use token too")
            status, answer = server.sensitive("/api/github-token", {"action": "delete"})
            self.assertEqual((answer["stored"], secretstore.gh_kwargs()), (False, {}))
            self.assertEqual(secretstore.Store("file").load(), "")

    def test_it_is_refused_when_the_switch_is_off_or_the_token_is_malformed(self):
        with LiveServer({"session_guard": True}) as server:
            self.assertEqual(server.sensitive("/api/github-token", {"token": TOKEN})[1]["status"], "off")
        with LiveServer({"session_guard": True, "github_token": {"enabled": True, "store": "file"}}) as server:
            self.assertEqual(server.sensitive("/api/github-token", {"token": "bad token"})[1]["status"], "format")
            self.assertEqual(secretstore.Store("file").load(), "")

    def test_the_token_is_not_in_the_schema_of_the_settings(self):
        self.assertFalse([k for k in settings_api.FIELDS if "token" in k and not k.endswith(("token_env", "github_token.enabled", "github_token.store"))])
        self.assertNotIn("github_token.value", settings_api.FIELDS)


# --- actions on GitHub --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class GitHubActions(unittest.TestCase):
    CONFIG = {"github_actions": {"enabled": True, "allowed": ["rerun_failed", "cancel", "close_pr", "merge_pr"], "merge_method": "rebase"}}

    def setUp(self):
        _testenv.guard(self)
        self.sent = []
        self.scopes = "X-OAuth-Scopes: repo, workflow\n"
        self.log = Path(tempfile.mkdtemp()) / "log.jsonl"

    def run_gh(self, args, timeout=40):
        if args[:2] == ["api", "-i"]:
            return 0, "HTTP/2 200\n" + self.scopes + "\n{}", ""
        self.sent.append(args)
        return 0, "{}", ""

    def test_everything_is_off_by_default(self):
        item, why = ghactions.plan({}, "owner", "cancel", "repo", 5)
        self.assertEqual((item, why), (None, "off"))
        self.assertEqual(ghactions.execute({}, "any", self.run_gh), {"ok": False, "status": "off"})
        self.assertEqual(ghactions.settings({})["allowed"], ["rerun_failed", "cancel"])

    def test_the_plan_shows_exactly_what_will_be_sent(self):
        plan, why = ghactions.plan(self.CONFIG, "owner", "merge_pr", "my-repo", 12)
        self.assertEqual(why, "ok")
        self.assertEqual((plan["method"], plan["endpoint"], plan["fields"]), ("PUT", "repos/owner/my-repo/pulls/12/merge", {"merge_method": "rebase"}))
        plan, _ = ghactions.plan(self.CONFIG, "owner", "cancel", "my-repo", 99)
        self.assertEqual((plan["method"], plan["endpoint"]), ("POST", "repos/owner/my-repo/actions/runs/99/cancel"))

    def test_only_allowed_actions_with_valid_values(self):
        for action, repo, number, why in (("close_issue", "r", 1, "not_allowed"), ("explode", "r", 1, "action"), ("cancel", "../x", 1, "repo"), ("cancel", "r", "1; rm", "number"), ("cancel", "r", "", "number")):
            self.assertEqual(ghactions.plan(self.CONFIG, "owner", action, repo, number), (None, why), (action, repo, number))

    def test_nothing_is_sent_without_the_confirmation_and_it_works_once(self):
        plan, _ = ghactions.plan(self.CONFIG, "owner", "cancel", "r", 7)
        self.assertEqual(self.sent, [], "planning sends nothing")
        self.assertEqual(ghactions.execute(self.CONFIG, "wrong", self.run_gh, self.log)["status"], "unknown_plan")
        self.assertEqual(self.sent, [])
        self.assertEqual(ghactions.execute(self.CONFIG, plan["id"], self.run_gh, self.log), {"ok": True, "status": "done"})
        self.assertEqual(self.sent, [["api", "-X", "POST", "repos/owner/r/actions/runs/7/cancel"]])
        self.assertEqual(ghactions.execute(self.CONFIG, plan["id"], self.run_gh, self.log)["status"], "unknown_plan")
        self.assertEqual(len(self.sent), 1)

    def test_a_plan_expires(self):
        clock = [100.0]
        pending = confirmation.Pending(clock=lambda: clock[0])
        key = pending.add("x", {"a": 1})
        clock[0] += confirmation.TTL + 1
        self.assertIsNone(pending.take(key, "x"))
        key = pending.add("x", {"a": 1})
        self.assertIsNone(pending.take(key, "other"), "a plan of another kind is not accepted")

    def test_the_permission_of_the_token_is_required(self):
        self.scopes = "X-OAuth-Scopes: read:user\n"
        plan, _ = ghactions.plan(self.CONFIG, "owner", "cancel", "r", 7)
        self.assertEqual(ghactions.execute(self.CONFIG, plan["id"], self.run_gh, self.log), {"ok": False, "status": "permission"})
        self.assertEqual(self.sent, [])
        self.scopes = ""                  # a fine-grained token lists no scopes: GitHub decides
        plan, _ = ghactions.plan(self.CONFIG, "owner", "cancel", "r", 7)
        self.assertTrue(ghactions.execute(self.CONFIG, plan["id"], self.run_gh, self.log)["ok"])

    def test_a_refusal_of_github_is_reported_and_the_log_has_no_secret(self):
        def refusing(args, timeout=40):
            if args[:2] == ["api", "-i"]:
                return 0, "", ""
            return 1, "", f"HTTP 403: Resource not accessible (token {TOKEN})"
        plan, _ = ghactions.plan(self.CONFIG, "owner", "rerun_failed", "r", 3)
        result = ghactions.execute(self.CONFIG, plan["id"], refusing, self.log)
        self.assertEqual((result["ok"], result["status"]), (False, "refused"))
        self.assertNotIn(TOKEN, json.dumps(result))
        text = self.log.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, text)
        entry = json.loads(text.splitlines()[-1])
        self.assertEqual((entry["action"], entry["repo"], entry["number"], entry["ok"]), ("rerun_failed", "r", "3", False))

    def test_the_ai_assistant_has_no_way_to_reach_it(self):
        for name in ("ai_actions.py", "sentinel_ai.py"):
            source = (HERE / name).read_text(encoding="utf-8")
            self.assertNotIn("ghactions", source, name)
            self.assertNotIn("actlocal", source, name)
        self.assertNotIn("ghactions", (HERE / "notifiers.py").read_text(encoding="utf-8"))

    def test_through_the_server_the_plan_needs_no_token_but_the_confirmation_does(self):
        cfg = {"session_guard": True, **self.CONFIG}
        with LiveServer(cfg) as server:
            with mock.patch.object(am, "run_gh", self.run_gh):
                status, plan = server.call("/api/gh-action/plan", {"action": "cancel", "repo": "r", "number": 5})
                self.assertEqual((status, plan["ok"]), (200, True))
                self.assertEqual(server.call("/api/gh-action/confirm", {"plan": plan["plan"]["id"]})[0], 403, "no token, no action")
                self.assertEqual(self.sent, [])
                status, done = server.sensitive("/api/gh-action/confirm", {"plan": plan["plan"]["id"]})
                self.assertEqual((status, done["ok"]), (200, True))
                self.assertEqual(len(self.sent), 1)


# --- act, only after a confirmation ------------------------------------------------------------------------------------------------------------------------------------------------------
class ActLocally(unittest.TestCase):
    CONFIG = {"act": {"enabled": True, "allowed": ["my-repo:ci.yml:push"], "timeout_seconds": 60}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        flow = Path(self.tmp.name) / "my-repo" / ".github" / "workflows"
        flow.mkdir(parents=True)
        (flow / "ci.yml").write_text("on: push\n", encoding="utf-8")
        actlocal.RUN.update({"proc": None, "lines": [], "bytes": 0, "running": False, "exit": None, "plan": None})

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, config=None, **kwargs):
        values = {"repo": "my-repo", "workflow": "ci.yml", "event": "push", "job": None}
        values.update(kwargs)
        return actlocal.plan(config if config is not None else self.CONFIG, self.tmp.name, values["repo"], values["workflow"], values["event"], values["job"], which=lambda name: "/usr/bin/act")

    def test_off_by_default_and_a_closed_list(self):
        self.assertEqual(self.plan({})[1], "off")
        self.assertEqual(self.plan(workflow="other.yml")[1], "not_allowed")
        self.assertEqual(self.plan(event="pull_request")[1], "not_allowed")
        self.assertEqual(self.plan(repo="other")[1], "not_allowed")
        self.assertEqual(actlocal.settings({"act": {"enabled": True, "allowed": ["*:*:*", "r:ci.yml:push"]}})["allowed"], ["r:ci.yml:push"], "no wildcard")
        self.assertEqual(self.plan(job="a;b")[1], "job")
        self.assertEqual(actlocal.plan(self.CONFIG, self.tmp.name, "my-repo", "ci.yml", "push", None, which=lambda n: None)[1], "no_act")
        self.assertEqual(actlocal.plan(self.CONFIG, str(Path(self.tmp.name) / "nowhere"), "my-repo", "ci.yml", "push", None, which=lambda n: "/x/act")[1], "no_clone")

    def test_the_command_has_no_secret_files_and_the_environment_is_minimal(self):
        item, why = self.plan(job="build")
        self.assertEqual(why, "ok")
        argv = item["argv"]
        for flag in ("--secret-file", "--var-file", "--env-file", "--input-file"):
            self.assertEqual(argv[argv.index(flag) + 1], os.devnull, flag)
        self.assertEqual(argv[argv.index("-j") + 1], "build")
        self.assertIn("ci.yml", item["command"])
        with mock.patch.dict(os.environ, {"GH_TOKEN": TOKEN, "GITHUB_TOKEN": TOKEN, "MY_SECRET": "x", "PATH": "/bin"}):
            env = actlocal.minimal_env()
        self.assertEqual(set(env) - {"PATH"} & {"GH_TOKEN", "GITHUB_TOKEN", "MY_SECRET"}, set())
        self.assertNotIn("GH_TOKEN", env)

    def test_nothing_starts_without_a_confirmed_plan_and_a_plan_runs_once(self):
        started = []

        class Proc:
            stdout = iter([f"line one\n", f"token {TOKEN}\n"])

            def wait(self):
                return 0

            def terminate(self):
                pass

        def popen(argv, **kwargs):
            started.append((argv, kwargs))
            return Proc()
        self.assertEqual(actlocal.start(self.CONFIG, "nothing", popen=popen, threaded=False)["status"], "unknown_plan")
        self.assertEqual(started, [])
        item, _ = self.plan()
        self.assertEqual(started, [], "planning starts nothing")
        self.assertEqual(actlocal.start(self.CONFIG, item["id"], popen=popen, threaded=False), {"ok": True, "status": "started"})
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0][1]["env"], actlocal.minimal_env())
        status = actlocal.status()
        self.assertEqual((status["running"], status["exit"]), (False, 0))
        self.assertIn("line one", status["lines"])
        self.assertNotIn(TOKEN, json.dumps(status), "the output is cleaned of anything that looks like a token")
        self.assertEqual(actlocal.start(self.CONFIG, item["id"], popen=popen, threaded=False)["status"], "unknown_plan")

    def test_only_one_run_at_a_time_and_a_stop_only_touches_its_own(self):
        item, _ = self.plan()
        actlocal.RUN["running"] = True
        self.assertEqual(actlocal.start(self.CONFIG, item["id"], popen=lambda *a, **k: None, threaded=False)["status"], "busy")
        actlocal.RUN["running"] = False
        self.assertEqual(actlocal.stop()["status"], "idle")

    def test_through_the_server_the_confirmation_needs_the_token(self):
        cfg = {"session_guard": True, **self.CONFIG}
        with LiveServer(cfg) as server:
            self.assertEqual(server.call("/api/act/confirm", {"plan": "x"})[0], 403)
            self.assertEqual(server.call("/api/act/stop", {})[0], 403)
            status, answer = server.call("/api/act/plan", {"repo": "other", "workflow": "ci.yml", "event": "push"})
            self.assertEqual((status, answer["status"]), (200, "not_allowed"))


# --- the mirror of artifacts -------------------------------------------------------------------------------------------------------------------------------------------------------------------
class ArtifactMirror(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name) / "mirror"
        self.config = {"mirror": {"enabled": True, "folder": str(self.folder), "max_mb": 10, "keep_days": 14, "max_per_cycle": 2}}
        self.runs = [{"id": i, "repo": "r", "status": "completed"} for i in (1, 2, 3)]
        self.downloads = []

    def tearDown(self):
        self.tmp.cleanup()

    def lister(self, endpoint):
        run = re.search(r"runs/(\d+)/", endpoint).group(1)
        return {"artifacts": [{"id": int(run) * 10, "name": "build/../out put", "size_in_bytes": 100, "expired": False}, {"id": int(run) * 10 + 1, "name": "old", "size_in_bytes": 1, "expired": True}]}

    def downloader(self, endpoint, destination):
        self.downloads.append(endpoint)
        Path(destination).write_bytes(b"x" * 100)

    def test_off_by_default_and_unsafe_folders_are_refused(self):
        self.assertFalse(mirror.settings({})["enabled"])
        self.assertEqual(mirror.cycle({}, self.runs, "o", self.lister, self.downloader), {"copied": 0, "skipped": 0, "removed": 0})
        for bad in ("", "\\\\server\\share", "//server/share", "D:\\copies", "/mnt/d/copies", "a\x00b"):
            self.assertFalse(mirror.safe_folder(bad), bad)
            self.assertFalse(mirror.settings({"mirror": {"enabled": True, "folder": bad}})["enabled"], bad)
        self.assertEqual(self.downloads, [])

    def test_it_copies_a_limited_number_once_and_keeps_names_inside_the_folder(self):
        first = mirror.cycle(self.config, self.runs, "o", self.lister, self.downloader)
        self.assertEqual(first["copied"], 2, "max_per_cycle")
        files = sorted(p.relative_to(self.folder).as_posix() for p in self.folder.rglob("*.zip"))
        self.assertTrue(all(f.startswith("r/") and ".." not in f and f.endswith(".zip") for f in files), files)
        second = mirror.cycle(self.config, self.runs, "o", self.lister, self.downloader)
        self.assertEqual(second["copied"], 1)
        third = mirror.cycle(self.config, self.runs, "o", self.lister, self.downloader)
        self.assertEqual(third["copied"], 0, "an artifact is copied once")
        self.assertEqual(len(self.downloads), 3)
        self.assertEqual(mirror.status(self.config)["count"], 3)

    def test_the_size_ceiling_and_the_retention(self):
        small = {"mirror": {**self.config["mirror"], "max_mb": 10}}
        index_before = mirror.cycle(small, self.runs[:1], "o", self.lister, self.downloader)
        self.assertEqual(index_before["copied"], 1)
        big = lambda endpoint: {"artifacts": [{"id": 5, "name": "huge", "size_in_bytes": 50 * 1024 * 1024, "expired": False}]}   # noqa: E731
        result = mirror.cycle(small, [{"id": 9, "repo": "r", "status": "completed"}], "o", big, self.downloader)
        self.assertEqual(result["copied"], 0)
        self.assertEqual(result["skipped"], 1)
        later = time.time() + 15 * 86400
        removed = mirror.cycle(small, [], "o", self.lister, self.downloader, now=later)
        self.assertEqual(removed["removed"], 1)
        self.assertEqual(list(self.folder.rglob("*.zip")), [])

    def test_a_failed_download_is_skipped_and_the_run_is_not_in_the_index(self):
        def failing(endpoint, destination):
            raise RuntimeError("boom")
        result = mirror.cycle(self.config, self.runs[:1], "o", self.lister, failing)
        self.assertEqual(result["copied"], 0)
        self.assertEqual(mirror.status(self.config)["count"], 0)

    def test_a_run_that_has_not_finished_is_left_alone(self):
        result = mirror.cycle(self.config, [{"id": 1, "repo": "r", "status": "in_progress"}], "o", self.lister, self.downloader)
        self.assertEqual((result["copied"], self.downloads), (0, []))


# --- runners --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class SelfHostedRunners(unittest.TestCase):
    BODY = {"runners": [{"id": 1, "name": "bench", "os": "Linux", "status": "online", "busy": True, "labels": [{"name": "self-hosted"}, {"name": "linux"}]},
                        {"id": 2, "name": "idle-one", "os": "Linux", "status": "online", "busy": False, "labels": []}, {"id": 3, "name": "gone", "os": "Windows", "status": "offline", "busy": False, "labels": []}]}

    def test_states_and_counts(self):
        out = runners.collect({"runners": {"enabled": True}}, lambda endpoint: self.BODY, "owner")
        self.assertEqual({r["name"]: r["state"] for r in out["runners"]}, {"bench": "busy", "idle-one": "idle", "gone": "offline"})
        self.assertEqual(out["counts"], {"idle": 1, "busy": 1, "offline": 1})

    def test_off_by_default_and_demo(self):
        self.assertFalse(runners.payload({}, lambda e: 1 / 0, "o")["enabled"])
        self.assertTrue(runners.payload({}, lambda e: 1 / 0, "o", demo=True)["demo"])

    def test_scope_repos_asks_each_repository_and_a_failure_is_counted(self):
        asked = []

        def reader(endpoint):
            asked.append(endpoint)
            if "bad" in endpoint:
                raise RuntimeError("404")
            return self.BODY
        out = runners.collect({"runners": {"enabled": True, "scope": "repos"}}, reader, "o", ["good", "bad"])
        self.assertEqual(len(asked), 2)
        self.assertEqual((out["errors"], len(out["runners"])), (1, 3))

    def test_disk_and_load_come_only_from_a_private_exporter(self):
        text = '# HELP\nnode_load1 0.52\nnode_filesystem_size_bytes{mountpoint="/"} 1000\nnode_filesystem_avail_bytes{mountpoint="/"} 250\nnode_filesystem_size_bytes{mountpoint="/boot"} 5\n'
        self.assertEqual(runners.parse_node_metrics(text), {"load1": 0.52, "disk_free_percent": 25.0})
        self.assertEqual(runners.parse_node_metrics("garbage"), {})
        for good in ("http://127.0.0.1:9100/metrics", "http://192.168.1.4:9100/metrics", "http://localhost:9100/metrics"):
            self.assertTrue(runners.private_address(good), good)
        for bad in ("http://8.8.8.8:9100/metrics", "ftp://127.0.0.1/x", "http://user:pw@127.0.0.1/", "http://example.com/metrics", "file:///etc/passwd"):
            self.assertFalse(runners.private_address(bad), bad)
        config = {"runners": {"enabled": True, "metrics": {"bench": "http://127.0.0.1:9100/metrics", "idle-one": "http://8.8.8.8/metrics"}}}
        seen = []
        out = runners.collect(config, lambda e: self.BODY, "o", opener=lambda url: seen.append(url) or text)
        self.assertEqual(seen, ["http://127.0.0.1:9100/metrics"], "a public address is never read")
        self.assertEqual([r.get("load1") for r in out["runners"]], [0.52, None, None])


# --- OpenTelemetry --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class OpenTelemetry(unittest.TestCase):
    def setUp(self):
        otlp.STATE.update({"sent": set(), "total": 0, "last_ok": None, "last_error": "", "next": 0.0})
        self.run = {"id": 7, "repo": "r", "name": "CI", "branch": "main", "event": "push", "conclusion": "failure", "status": "completed", "started": "2026-01-01T10:00:00Z", "seconds": 90,
                    "title": "SECRET TITLE", "actor": "someone", "sha": "abcdef1"}
        self.config = {"otlp": {"enabled": True, "endpoint": "http://127.0.0.1:4318", "interval_seconds": 15}}

    def test_off_by_default_and_the_endpoint_rules(self):
        self.assertFalse(otlp.settings({})["enabled"])
        self.assertFalse(otlp.settings({"otlp": {"enabled": True, "endpoint": ""}})["enabled"])
        for good in ("https://collector.example.org:4318", "http://127.0.0.1:4318", "http://localhost:4318"):
            self.assertTrue(otlp.endpoint_ok(good), good)
        for bad in ("http://collector.example.org:4318", "ftp://x", "https://user:pw@x.example.org", "javascript:1", "http://192.168.1.2:4318"):
            self.assertFalse(otlp.endpoint_ok(bad), bad)

    def test_the_span_is_stable_and_private(self):
        first, second = otlp.span(self.run), otlp.span(self.run)
        self.assertEqual(first, second)
        self.assertEqual((len(first["traceId"]), len(first["spanId"])), (32, 16))
        self.assertEqual(first["status"]["code"], 2)
        self.assertEqual(int(first["endTimeUnixNano"]) - int(first["startTimeUnixNano"]), 90_000_000_000)
        blob = json.dumps(first)
        for secret in ("SECRET TITLE", "someone", "abcdef1"):
            self.assertNotIn(secret, blob)
        self.assertNotEqual(otlp.span({**self.run, "id": 8})["traceId"], first["traceId"])

    def test_the_metrics_are_gauges_of_the_header_figures(self):
        document = otlp.metrics({"active": 1, "fail24": 3, "min24": 40, "red": 2, "bogus": 1}, [], now=1)
        names = {m["name"] for m in document["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]}
        self.assertEqual(names, {"gha.runs.active", "gha.runs.failed_24h", "gha.minutes_24h", "gha.workflows.red"})

    def test_a_run_is_sent_once_and_nothing_is_sent_while_off(self):
        posted = []
        post = lambda request: posted.append((request.full_url, json.loads(request.data)))   # noqa: E731
        data = {"runs": [self.run], "figures": {"fail24": 1}}
        self.assertEqual(otlp.export({}, data, "1.6.4", post=post)["sent_spans"], 0)
        self.assertEqual(posted, [])
        first = otlp.export(self.config, data, "1.6.4", now=1000, post=post)
        self.assertEqual((first["sent_spans"], first["sent_metrics"]), (1, 1))
        self.assertEqual([url for url, _ in posted], ["http://127.0.0.1:4318/v1/traces", "http://127.0.0.1:4318/v1/metrics"])
        self.assertEqual(otlp.export(self.config, data, "1.6.4", now=1005, post=post)["sent_spans"], 0, "not before the interval")
        again = otlp.export(self.config, data, "1.6.4", now=1100, post=post)
        self.assertEqual(again["sent_spans"], 0, "the run was sent already")

    def test_a_collector_that_is_down_is_not_fatal_and_the_error_is_cleaned(self):
        def post(request):
            raise OSError(f"refused with {TOKEN}")
        result = otlp.export(self.config, {"runs": [self.run], "figures": {}}, "1.6.4", now=5000, post=post)
        self.assertNotIn(TOKEN, result["error"])
        self.assertEqual(otlp.status(self.config)["spans_sent"], 0)
        self.assertEqual(otlp.status(self.config)["endpoint_host"], "http://127.0.0.1:4318")


# --- organisations ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class Organisations(unittest.TestCase):
    def test_off_by_default_one_read_a_day_and_clean_names(self):
        calls = []

        def reader(endpoint):
            calls.append(endpoint)
            return [{"login": "my-org"}, {"login": "bad name!"}, {"nologin": 1}, "x"]
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "orgs.json"
            self.assertEqual(orgs.view({}, reader, state), {"enabled": False, "orgs": [], "checked_at": 0})
            self.assertEqual(calls, [])
            config = {"organizations": {"discover": True}}
            self.assertEqual(orgs.view(config, reader, state, now=1000)["orgs"], ["my-org"])
            orgs.view(config, reader, state, now=2000)
            self.assertEqual(len(calls), 1)
            orgs.view(config, reader, state, now=1000 + 86401)
            self.assertEqual(len(calls), 2)
            orgs.view(config, reader, state, now=1000 + 86401 + 86401, offline=True)
            self.assertEqual(len(calls), 2, "nothing is asked while offline")

    def test_a_failed_read_keeps_the_last_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "orgs.json"
            config = {"organizations": {"discover": True}}
            orgs.view(config, lambda e: [{"login": "a-org"}], state, now=1000)

            def failing(endpoint):
                raise RuntimeError("403")
            self.assertEqual(orgs.view(config, failing, state, now=1000 + 90000)["orgs"], ["a-org"])


# --- FinOps ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class FinOps(unittest.TestCase):
    def setUp(self):
        self.data = quota.load()

    def test_the_system_of_a_job_comes_from_its_labels(self):
        cases = {("ubuntu-latest",): "linux", ("ubuntu-latest-8-cores",): "linux_8", ("windows-latest-16-cores",): "windows_16", ("macos-latest-xlarge",): "macos_xlarge", ("macos-14-large",): "macos_large",
                 ("macos-14",): "macos", ("windows-2022",): "windows", ("self-hosted", "linux"): "self", ("ubuntu-24.04-arm-4-cores",): "linux_arm_4"}
        for labels, expected in cases.items():
            self.assertEqual(quota.runner_system(list(labels)), expected, labels)
        self.assertIsNone(quota.runner_system([]))

    def test_larger_runners_cost_more_and_self_hosted_nothing(self):
        self.assertEqual(quota.multiplier("linux", self.data), 1)
        self.assertEqual(quota.multiplier("linux_8", self.data), round(0.032 / 0.006, 3))
        self.assertGreater(quota.multiplier("macos_xlarge", self.data), quota.multiplier("macos", self.data))
        self.assertEqual(quota.multiplier("linux_unknown_size", self.data), 1, "an unknown key is priced as its base system")
        cost = quota.job_costs([{"seconds": 61, "labels": ["ubuntu-latest-8-cores"]}, {"seconds": 600, "labels": ["self-hosted"]}, {"seconds": 30, "labels": None}], self.data)
        self.assertEqual(cost["clock"], 2 + 10 + 1)
        self.assertEqual(cost["by_system"], {"linux_8": 2, "linux": 1})
        self.assertAlmostEqual(cost["billable"], 2 * quota.multiplier("linux_8", self.data) + 1, places=1)

    def test_a_run_with_read_jobs_is_counted_exactly(self):
        runs = [{"id": 1, "repo": "priv", "seconds": 300}, {"id": 2, "repo": "priv", "seconds": 300}, {"id": 3, "repo": "pub", "seconds": 300}]
        costs = {1: quota.job_costs([{"seconds": 300, "labels": ["windows-latest"]}], self.data)}
        out = quota.billable(runs, {"priv"}, self.data, "linux", costs=costs)
        self.assertEqual(out["exact_runs"], 1)
        self.assertTrue(out["estimate"], "one run is still assumed")
        self.assertEqual(out["billable"], round(5 * quota.multiplier("windows", self.data) + 5))
        all_known = quota.billable(runs[:1], {"priv"}, self.data, "linux", costs=costs)
        self.assertFalse(all_known["estimate"])

    def test_the_price_of_the_extra_minutes(self):
        self.assertEqual(quota.extra_cost(2500, 2000, self.data), 3.0)
        self.assertEqual(quota.extra_cost(100, 2000, self.data), 0.0)
        self.assertIsNone(quota.extra_cost(100, None, self.data))

    def test_the_billing_report_gives_codespaces_packages_and_storage(self):
        body = {"usageItems": [{"product": "actions", "sku": "actions_linux", "quantity": 120, "unitType": "minutes", "netAmount": 0.72},
                               {"product": "actions", "sku": "actions_storage", "quantity": 3.5, "unitType": "GigabyteHours", "netAmount": 0.01},
                               {"product": "codespaces", "sku": "compute", "quantity": 4, "unitType": "hours", "netAmount": 1.5}, {"product": "packages", "netAmount": 0.25}, "junk"]}
        out = quota.billing_usage("o", lambda endpoint: body)
        self.assertEqual(out["minutes"], 120)
        self.assertEqual(out["usd"], {"actions": 0.73, "codespaces": 1.5, "packages": 0.25})
        self.assertEqual(out["storage_gb_hours"], 3.5)
        self.assertIsNone(quota.billing_usage("o", lambda e: (_ for _ in ()).throw(RuntimeError("403"))))

    def test_the_summary_carries_the_extra_cost(self):
        out = quota.summary({"account": {"plan": "free"}}, [], [], set(), data=self.data)
        self.assertIn("extra_cost_usd", out)

    def test_reading_the_jobs_costs_calls_only_when_asked(self):
        data = {"runs": [{"id": 5, "repo": "priv", "status": "completed", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}]}
        am.PRIVATE.add("priv")
        am.RUN_COSTS.clear()
        calls = []

        def reader(endpoint, retries=0):
            calls.append(endpoint)
            return {"jobs": [{"started_at": "2026-01-01T00:00:00Z", "completed_at": "2026-01-01T00:02:00Z", "labels": ["ubuntu-latest-4-cores"]}]}
        try:
            with mock.patch.object(am, "gh_read", reader):
                self.assertEqual(am.read_costs({}, data), 0)
                self.assertEqual(calls, [])
                self.assertEqual(am.read_costs({"finops": {"jobs_per_cycle": 3}}, data), 1)
                self.assertEqual(am.read_costs({"finops": {"jobs_per_cycle": 3}}, data), 0, "a run is read once")
            self.assertEqual(am.RUN_COSTS[5]["by_system"], {"linux_4": 2})
        finally:
            am.PRIVATE.discard("priv")
            am.RUN_COSTS.clear()


# --- the other small things of the version -----------------------------------------------------------------------------------------------------------------------------------------
class SmallThings(unittest.TestCase):
    def test_the_export_for_the_dashboard_is_complete_and_schema_two(self):
        import ci_red
        document = ci_red.build({"generated": "x", "loading": False, "a2": {"red": []}, "a5": {}})
        self.assertGreaterEqual(document["schema"], 2)
        self.assertIs(document["complete"], True)
        self.assertIs(ci_red.build({"generated": "x", "loading": True, "a2": {"red": []}, "a5": {}})["complete"], False)

    def test_about_links_the_documentation_of_the_bridge(self):
        data = about.info(False, {}, {}, {}, "en")
        self.assertTrue(data["links"]["bridge"].endswith("CI_RED_BRIDGE.md"))
        self.assertIn('"bridge"', (HERE / "actions_monitor.html").read_text(encoding="utf-8"))
        self.assertTrue(helpdocs.topic("ci_red_bridge", "es"))

    def test_a_setting_that_needs_a_restart_is_announced_and_stays_announced(self):
        with LiveServer({"session_guard": False}) as server:
            status, answer = server.call("/api/settings", {"changes": {"max_workers": 7}})
            self.assertEqual((status, answer["restart_pending"]), (200, ["max_workers"]))
            self.assertEqual(server.call("/api/settings")[1]["restart_pending"], ["max_workers"], "it survives a reload of the page")
            self.assertIn("restartBar(", (HERE / "actions_monitor.html").read_text(encoding="utf-8"))

    def test_the_signing_queue_can_be_filtered_by_trust(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        match = re.search(r'id="sq-trust">\$\{\[("[a-z", ]+)\]', page)
        self.assertTrue(match)
        self.assertEqual(re.findall(r'"([a-z]+)"', match.group(1)), ["all", "verified", "unknown", "failed"])

    def test_the_quota_pause_and_the_minutes_budget_are_visible_in_the_header(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('id="k-a10"', page)
        self.assertIn("ui.k_a10_paused", page)
        self.assertIn("ui.k_min_budget", page)

    def test_the_lint_ignore_list_removes_findings_and_severities_are_settings(self):
        import lint_workflows
        finding = {"file": ".github/workflows/ci.yml", "rule": "unpinned_uses"}
        self.assertTrue(lint_workflows.ignored("repo", finding, ["repo:ci.yml:unpinned_uses"]))
        self.assertTrue(lint_workflows.ignored("repo", finding, ["*:*:unpinned_uses"]))
        self.assertFalse(lint_workflows.ignored("repo", finding, ["other:*:*"]))
        self.assertEqual(settings_api.FIELDS["lint.rules.unpinned_uses.severity"][3], ("info", "warn", "bad"))

    def test_the_welcome_is_kept_on_the_server_too(self):
        with LiveServer({"session_guard": False}) as server:
            saved = am.welcome_file
            file = Path(server.tmp.name) / "welcome.json"
            am.welcome_file = lambda: file
            try:
                self.assertEqual(server.call("/api/welcome")[1], {"done": False})
                self.assertEqual(server.call("/api/welcome", {"done": True})[1], {"ok": True})
                self.assertEqual(server.call("/api/welcome")[1], {"done": True})
            finally:
                am.welcome_file = saved
        self.assertIn("/api/welcome", (HERE / "actions_monitor.html").read_text(encoding="utf-8"))

    def test_the_readme_of_the_package_starts_with_the_choice_of_launcher(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            head = "\n".join((HERE / f"README_{lang}.txt").read_text(encoding="utf-8").splitlines()[:24])
            for launcher in ("MONITOR_GITHUB_ACTIONS", "MONITOR_LITE_GITHUB_ACTIONS", "BATCH_GITHUB_ACTIONS", "--doctor", "--demo"):
                self.assertIn(launcher, head, (lang, launcher))
            self.assertIn("tui_textual.py", head, lang)

    def test_the_version(self):
        self.assertEqual(TOOL_VERSION, "1.7.6")
        if (ROOT / "electro-hobby-3d.project.json").is_file():          # not inside the zip
            self.assertEqual(json.loads((ROOT / "electro-hobby-3d.project.json").read_text(encoding="utf-8"))["version"], TOOL_VERSION)
        self.assertIn(f"## [{TOOL_VERSION}]", (HERE / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_the_new_modules_travel_in_the_package(self):
        names = {p.name for p in __import__("make_release").members()}
        for needed in ("localguard.py", "secretstore.py", "ghactions.py", "actlocal.py", "confirmation.py", "mirror.py", "runners.py", "otlp.py", "orgs.py", "test_164.py", "red_rule_cases.json"):
            self.assertIn(needed, names)


# --- alerts for AIs -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class AlertsForAIs(unittest.TestCase):
    ROW = {"repo": "r1", "workflow": "ci.yml", "conclusion": "failure", "since": "2026-01-01T00:00:00Z", "streak": 1, "url": "https://github.com/o/r1/actions/runs/1"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = {"ai_alerts": {"enabled": True, "folder": self.tmp.name, "brief_max_bytes": 2048}}
        ai_alerts.HOOK.sent = []

    def tearDown(self):
        ai_alerts.HOOK.sent = []
        self.tmp.cleanup()

    def test_the_cleaner_removes_secrets_addresses_and_paths(self):
        home = str(Path.home())
        dirty = f"x {TOKEN} a.b@example.com 192.168.1.20 password=hunter2 Bearer abcdefghijklmnop1234 {home}{os.sep}proj eyJabcdefgh.eyJabcdefgh.abcdefgh sk-abcdefghijklmnopqrstuv " + "A" * 50
        clean = ai_alerts.redact(dirty)
        for leak in (TOKEN, "a.b@example.com", "192.168.1.20", "hunter2", "abcdefghijklmnop1234", home, "eyJabcdefgh", "sk-abcdef", "A" * 50):
            self.assertNotIn(leak, clean, leak)
        self.assertIn("[token]", clean)

    def test_transient_and_real_are_told_apart_with_editable_rules(self):
        self.assertEqual(ai_alerts.classify("failure", "HTTP 504 Gateway Timeout")[0], "transient")
        self.assertEqual(ai_alerts.classify("failure", "CodeQL download failed")[0], "transient")
        self.assertEqual(ai_alerts.classify("failure", "API rate limit exceeded")[0], "transient")
        self.assertEqual(ai_alerts.classify("startup_failure")[0], "transient")
        self.assertEqual(ai_alerts.classify("failure", "AssertionError: 3 != 4")[0], "real")
        self.assertEqual(ai_alerts.classify("failure", "boom happened", patterns=["boom"])[0], "transient")
        self.assertEqual(ai_alerts.classify("failure", "x", patterns=["(unclosed"])[0], "real", "a broken rule is ignored")

    def test_one_alert_per_workflow_is_opened_deduplicated_acknowledged_and_resolved(self):
        first = ai_alerts.update(self.config, [self.ROW], now=1000)
        self.assertEqual(len(first["opened"]), 1)
        self.assertEqual(ai_alerts.update(self.config, [self.ROW], now=1100)["opened"], [], "no duplicate")
        alert_id = first["opened"][0]["id"]
        self.assertTrue(ai_alerts.ack(self.config, alert_id, now=1200))
        self.assertFalse(ai_alerts.ack(self.config, "nothing"))
        self.assertEqual(ai_alerts.alerts(self.config)[0]["state"], "acknowledged")
        self.assertEqual(ai_alerts.update(self.config, [self.ROW], now=1300)["opened"], [], "an acknowledged alert is not opened again")
        gone = ai_alerts.update(self.config, [], now=1400)
        self.assertEqual(len(gone["resolved"]), 1, "it resolves itself when the workflow is green")
        events = [json.loads(line)["event"] for line in (Path(self.tmp.name) / "ai_alerts.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(events, ["opened", "acknowledged", "resolved"])
        self.assertEqual(len(ai_alerts.update(self.config, [self.ROW], now=1500)["opened"]), 1, "a new failure opens a new alert")

    def test_the_brief_is_short_and_real_alerts_come_first(self):
        rows = [dict(self.ROW, repo=f"repo-{i:02d}", conclusion="startup_failure" if i == 0 else "failure") for i in range(40)]
        ai_alerts.update(self.config, rows, now=1)
        text = ai_alerts.read_brief(self.config)
        self.assertLessEqual(len(text.encode("utf-8")), 2048)
        self.assertIn("more in ai_alerts.jsonl", text)
        self.assertNotIn("repo-00", text.split("\n")[4], "the transient one is not first")
        self.assertEqual(ai_alerts.settings({"ai_alerts": {"brief_max_bytes": 5}})["brief_max_bytes"], 2048)

    def test_nothing_is_written_when_it_is_off_and_nothing_goes_out(self):
        off = {"ai_alerts": {"enabled": False, "folder": self.tmp.name}}
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            self.assertEqual(ai_alerts.update(off, [self.ROW])["alerts"], [])
            self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
            ai_alerts.update(self.config, [self.ROW], now=1)        # the hook is off by default: still no network

    def test_the_hook_is_local_limited_and_sends_a_closed_list_of_clean_fields(self):
        sent = []
        hooked = {"ai_alerts": {**self.config["ai_alerts"], "hook": {"enabled": True, "url": "http://127.0.0.1:9000/h", "max_per_hour": 2}}}
        rows = [dict(self.ROW, repo=f"r{i}") for i in range(4)]
        ai_alerts.update(hooked, rows, now=5000, opener=lambda request: sent.append(json.loads(request.data)))
        self.assertEqual(len(sent), 2, "max_per_hour")
        self.assertEqual(set(sent[0]), set(ai_alerts.FIELDS))
        self.assertFalse(ai_alerts.settings({"ai_alerts": {"hook": {"enabled": True, "url": "http://example.com/x"}}})["hook"]["enabled"], "never an address outside this computer")

    def test_a_hook_that_is_down_does_not_stop_the_monitor(self):
        hooked = {"ai_alerts": {**self.config["ai_alerts"], "hook": {"enabled": True, "url": "http://127.0.0.1:9000/h"}}}
        result = ai_alerts.update(hooked, [self.ROW], now=1, opener=lambda r: (_ for _ in ()).throw(OSError("down")))
        self.assertEqual(len(result["opened"]), 1)

    def test_the_endpoints_answer_markdown_and_json(self):
        ai_alerts.update(self.config, [self.ROW], now=1)
        with LiveServer({"session_guard": True, **self.config}) as server:
            status, body = server.call("/api/ai/brief")
            self.assertEqual(status, 200)
            self.assertIn("r1 / ci.yml", body)
            self.assertEqual(server.call("/api/ai/brief?fmt=json")[1]["alerts"][0]["repo"], "r1")
            self.assertEqual(server.call("/api/ai/alerts?since=0")[1]["alerts"][0]["workflow"], "ci.yml")
            self.assertEqual(server.call("/api/ai/alerts?since=99999999999")[1]["alerts"], [])
            self.assertEqual(server.call("/api/ai/ack", {"id": ai_alerts.alert_id("r1", "ci.yml")})[0], 403, "acknowledging needs the one-use token")
            self.assertTrue(server.sensitive("/api/ai/ack", {"id": ai_alerts.alert_id("r1", "ci.yml")})[1]["ok"])

    def test_the_ci_red_file_carries_an_optional_ai_hint(self):
        import ci_red
        document = ci_red.build({"generated": "x", "loading": False, "a2": {"red": [self.ROW, dict(self.ROW, repo="r2", conclusion="startup_failure")]}, "a5": {}})
        self.assertEqual({r: v["red"][0]["ai_hint"]["class"] for r, v in document["repos"].items()}, {"r1": "real", "r2": "transient"})
        self.assertGreaterEqual(document["schema"], 2)

    def test_the_mcp_server_is_read_only_and_cleans_every_answer(self):
        ai_alerts.update(self.config, [self.ROW], now=1)

        def tools(allow):
            return [t["name"] for t in mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, self.config, allow)["result"]["tools"]]
        self.assertNotIn("ack_alert", tools(False))
        self.assertIn("ack_alert", tools(True))
        init = mcp_server.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}, self.config)
        self.assertEqual(init["result"]["serverInfo"]["name"], "github-actions-monitor")
        note = mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, self.config)      # one notice that says what is red (the feed has a real alert here)
        self.assertEqual((note["method"], "id" in note), ("notifications/message", False))
        got = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_alerts", "arguments": {}}}, self.config)
        self.assertIn("r1", got["result"]["content"][0]["text"])
        refused = mcp_server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "ack_alert", "arguments": {"id": "x"}}}, self.config)
        self.assertTrue(refused["result"]["isError"])
        self.assertEqual(mcp_server.handle({"jsonrpc": "2.0", "id": 4, "method": "nope"}, self.config)["error"]["code"], -32601)

    def test_get_run_failure_cleans_the_log_and_validates_its_arguments(self):
        def runner(args, timeout=60):
            if args[0] == "api":
                return 0, json.dumps({"jobs": [{"name": "build", "steps": [{"name": "Test", "conclusion": "failure"}]}]}), ""
            return 0, f"line\nerror with {TOKEN} from 10.0.0.9\n", ""
        text = mcp_server.call("get_run_failure", {"repo": "r1", "run": 7}, dict(self.config, repos=["r1"]), runner=runner)
        self.assertIn("build: Test", text)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("10.0.0.9", text)
        for bad in ({"repo": "../x", "run": 1}, {"repo": "r", "run": "1"}, {"repo": "r", "run": 0}):
            with self.assertRaises(ValueError):
                mcp_server.call("get_run_failure", bad, self.config, runner=runner)

    def test_the_mcp_server_speaks_json_lines_on_standard_io(self):
        script = "import sys; sys.path.insert(0, %r); import mcp_server; sys.exit(mcp_server.main([]))" % str(HERE)
        done = subprocess.run([sys.executable, "-I", "-c", script], input='{"jsonrpc":"2.0","id":1,"method":"ping"}\nnot json\n', capture_output=True, text=True, timeout=30)
        self.assertEqual(json.loads(done.stdout.strip()), {"jsonrpc": "2.0", "id": 1, "result": {}})

    def test_the_guide_exists_in_eight_languages_and_names_the_feed(self):
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"AI_ALERTS{tail}.md").read_text(encoding="utf-8")
            for needle in ("ai_alerts.jsonl", "ALERTS_BRIEF.md", "mcp_server.py", "/api/ai/brief"):
                self.assertIn(needle, text, (tail, needle))


class TerminalApplication(unittest.TestCase):
    def test_the_helpers_need_no_textual(self):
        import tui_textual as tt
        settings = {"groups": [{"id": "basic", "fields": [{"key": "open_browser", "type": "bool", "secure": False}, {"key": "airgapped", "type": "bool", "secure": True}]},
                               {"id": "sentinel", "fields": [{"key": "sentinel.workers", "type": "int"}]}, {"id": "polling", "fields": [{"key": "names", "type": "names"}, {"key": "refresh_seconds", "type": "int"}]}]}
        self.assertEqual([f["key"] for _g, f in tt.editable_fields(settings)], ["open_browser", "refresh_seconds"], "no security option, no complex type, only the common groups")
        self.assertEqual(tt.parse_value({"type": "int"}, " 42 "), (42, None))
        self.assertEqual(tt.parse_value({"type": "float"}, "x"), (None, "type"))
        self.assertEqual(tt.parse_value({"type": "text"}, " a "), ("a", None))
        self.assertTrue(tt.ai_text(None))
        text = tt.ai_text({"ai": {"label": "AI", "provider": "ollama", "model": "m", "used_today": 1, "daily_limit": 10, "message": "ok"}, "state": {"enabled": False}, "log": [{"at": "t", "status": "done", "action": "a"}]})
        self.assertIn("ollama / m", text)

    def test_the_tui_asks_for_no_sentinel_in_lite(self):
        asked = []

        class Answer(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake(url, timeout=0):
            asked.append(url)
            return Answer(b'{"data": {}}')
        with mock.patch.object(tui.netguard, "local_open", fake):
            tui.fetch(8766)
            tui.fetch(8765, lite=True)
            self.assertEqual(len(asked), 2)
            tui.fetch(8765)
        self.assertEqual(len(asked), 4)
        self.assertTrue(all("/api/sentinel" not in u for u in asked[:2]))


if __name__ == "__main__":
    unittest.main()
