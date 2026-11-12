# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.4: the command line as a client of the monitor (every command, the stable exit codes, the lite limits, the three kinds of health), the bar at the foot of the page, the full screen
button, the sortable tables (the sorting logic is run for real with Node when it is installed), the changelogs in order in every language, and the new endpoint of the bar. Nothing here reaches
GitHub: the monitor of the CLI tests is a fake one on 127.0.0.1."""
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import monitor_cli as cli  # noqa: E402

ANSWERS = {}


class Fake(BaseHTTPRequestHandler):
    def do_GET(self):    # noqa: N802
        path = self.path.partition("?")[0]
        answer = ANSWERS.get(path)
        if answer is None:
            self.send_response(404)
            self.end_headers()
            return
        if isinstance(answer, int):
            self.send_response(answer)
            self.end_headers()
            return
        body = answer if isinstance(answer, bytes) else json.dumps(answer).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def data(**extra):
    base = {"repos": ["a", "b"], "figures": {"active": 1, "queued": 0, "fail24": 2, "ok24": 9, "red": 1}, "rate": {"remaining": 4000, "limit": 5000, "reset": "2026-01-01T00:00:00Z"}, "updated": "2026-01-01T00:00:00Z",
            "offline": {"offline": False}, "paused_quota": False}
    base.update(extra)
    return {"data": base, "error": None}


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Commands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        ANSWERS.clear()
        ANSWERS.update({"/api/health": {"ok": True, "version": "1.7.4", "lite": False, "uptime_seconds": 3700, "account": "personal"}, "/api/data": data()})

    def ask(self, *argv):
        return run(*argv, "--url", self.url, "--lang", "en")

    def test_status_says_the_figures_and_exits_zero(self):
        code, out, _ = self.ask("status")
        self.assertEqual(code, 0, out)
        for needle in ("1.7.4", "personal", "2 repositories", "4000 of 5000"):
            self.assertIn(needle, out)

    def test_json_is_one_document_with_the_exit_code_inside(self):
        code, out, _ = self.ask("status", "--json")
        document = json.loads(out)
        self.assertEqual((code, document["exit"], document["ok"]), (0, 0, True))
        self.assertEqual(document["data"]["repos"], 2)
        self.assertEqual(document["data"]["allowance"]["remaining"], 4000)

    def test_a_monitor_that_is_not_there_is_exit_two_and_the_json_says_so(self):
        code, _, err = run("status", "--url", "http://127.0.0.1:9", "--lang", "en", "--timeout", "1")
        self.assertEqual(code, 2)
        self.assertIn("cannot be reached", err)
        code, out, _ = run("health", "--url", "http://127.0.0.1:9", "--json", "--lang", "en", "--timeout", "1")
        self.assertEqual((code, json.loads(out)["exit"]), (2, 2))

    def test_a_refused_client_is_exit_three(self):
        ANSWERS["/api/health"] = 403
        code, _, err = self.ask("status")
        self.assertEqual(code, 3)
        self.assertIn("MONITOR_TOKEN", err)

    def test_the_three_kinds_of_health(self):
        code, out, _ = self.ask("health")
        self.assertEqual(code, 0, out)
        self.assertIn("credential answers", out)
        ANSWERS["/api/data"] = {"data": {"repos": [], "rate": {"remaining": 0, "limit": 5000}}, "error": None}
        code, out, _ = self.ask("check")                                 # alias
        self.assertEqual(code, 4)
        self.assertIn("allowance is exhausted", out)
        ANSWERS["/api/data"] = {"data": None, "error": "bad credentials", "hint": "auth"}
        code, out, _ = self.ask("health", "--json")
        self.assertEqual((code, json.loads(out)["data"]["github"]), (3, "credential_failed"))
        ANSWERS["/api/data"] = data(offline={"offline": True})
        self.assertEqual(self.ask("health")[0], 4)

    def test_alerts_filter_and_fail_on(self):
        ANSWERS["/api/alerts"] = {"alerts": [{"id": "a", "code": "ci.red", "sentinel": "ci", "level": "error", "repo": "r", "title": "red", "muted_until": None},
                                              {"id": "b", "code": "collab.pr.draft_old", "sentinel": "collab", "level": "info", "repo": "r", "title": "draft", "muted_until": None}]}
        code, out, _ = self.ask("alerts")
        self.assertEqual(code, 0)
        self.assertIn("ci.red", out)
        self.assertEqual(self.ask("alerts", "--fail-on", "error")[0], 5)
        ANSWERS["/api/alerts"]["alerts"][0]["muted_until"] = "2099-01-01T00:00:00Z"
        self.assertEqual(self.ask("alerts", "--fail-on", "error")[0], 0)      # a silenced alert does not fail a script
        ANSWERS["/api/alerts"] = {"alerts": []}
        self.assertEqual(self.ask("alerts", "--fail-on", "info")[0], 0)

    def test_accounts_and_live(self):
        ANSWERS["/api/accounts"] = {"accounts": [{"id": "personal", "state": "running", "repos": 3, "running": 1, "failing": 0}]}
        code, out, _ = self.ask("accounts")
        self.assertEqual(code, 0)
        self.assertIn("personal", out)
        ANSWERS["/api/live-events"] = {"events": [{"at": "t", "repo": "r", "name": "CI", "status": "completed", "conclusion": "success"}]}
        ANSWERS["/api/live-status"] = {"enabled": True, "active": True}
        code, out, _ = self.ask("live")
        self.assertEqual(code, 0)
        self.assertIn("1 events", out)

    def test_a_monitor_without_the_endpoint_is_degraded_not_down(self):
        self.assertEqual(self.ask("accounts")[0], 4)

    def test_an_answer_that_is_not_json_is_degraded(self):
        ANSWERS["/api/data"] = b"<html>"
        self.assertEqual(self.ask("status")[0], 4)


class Usage(unittest.TestCase):
    def test_a_wrong_use_is_exit_one_and_lite_has_the_short_list(self):
        self.assertEqual(run("nonsense")[0], 1)
        self.assertEqual(run("alerts", "--lite", "--lang", "en")[0], 1)
        self.assertEqual(run("accounts", "--lite", "--lang", "en")[0], 1)
        self.assertEqual(run("--version")[0], 0)

    def test_the_address_only_takes_http_and_https_and_drops_the_path(self):
        self.assertEqual(cli.base_url("http://127.0.0.1:1/x?y=1"), "http://127.0.0.1:1")
        self.assertEqual(cli.base_url("example.org:8765"), "http://example.org:8765")
        self.assertEqual(cli.base_url(None, lite=True, env={}), "http://127.0.0.1:8766")
        self.assertEqual(cli.base_url(None, env={"MONITOR_URL": "https://m.example"}), "https://m.example")
        for bad in ("file:///etc/passwd", "ftp://x", "javascript:alert(1)"):
            with self.assertRaises(cli.CliError):
                cli.base_url(bad)

    def test_every_text_of_the_cli_exists_in_the_eight_languages_and_the_help_runs_in_each(self):
        used = set(re.findall(r'i18n\.t\("(cli\.[a-z_]+)"', (HERE / "monitor_cli.py").read_text(encoding="utf-8")))
        used = {k for k in used if not k.endswith("_")} | {"cli.edition_complete", "cli.edition_lite", "cli.live_on", "cli.live_off"}
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            catalogue = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in used:
                self.assertTrue(catalogue.get(key), (lang, key))
            done = subprocess.run([sys.executable, "-I", str(HERE / "monitor_cli.py"), "--help", "--lang", lang], capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(done.returncode, 0, (lang, done.stderr))
            self.assertIn("health", done.stdout)

    def test_it_never_writes_to_github_or_runs_a_program(self):
        text = (HERE / "monitor_cli.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", '"POST"', "method=", "shell=True"):
            self.assertNotIn(forbidden, text, forbidden)


class Page(unittest.TestCase):
    def setUp(self):
        self.page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")

    def test_the_bar_at_the_foot_replaces_the_authorship_line_and_takes_the_six_banners(self):
        for needle in ('<footer id="statusbar"', 'id="sb-lamp"', 'id="sb-open"', 'id="notes-dlg"', "function readNotices", "NOTE_SRC", 'id="sb-clock"', 'id="sb-addr"', 'id="sb-conn-lamp"', "/api/statusbar"):
            self.assertIn(needle, self.page, needle)
        self.assertNotIn('<footer id="about"', self.page)
        for banner in ("err", "reduced", "offline", "hidden", "restartbar", "netbar"):
            self.assertIn(f'"{banner}"', self.page.split("const NOTE_SRC=", 1)[1].split("];", 1)[0], banner)
        self.assertIn("#err,#reduced,#offline,#hidden,#restartbar,#netbar{display:none!important}", self.page)

    def test_the_bar_is_outside_the_page_scroll_and_the_notices_list_is_sorted_by_time_with_a_level_filter(self):
        self.assertRegex(self.page, r"#statusbar\{flex:none;")
        self.assertIn(".slice().sort((a,b)=>b.at-a.at)", self.page)
        self.assertIn('id="notes-level"', self.page)
        self.assertLess(self.page.index('function renderBar'), self.page.index("</script>"))

    def test_the_full_screen_button_toggles_with_the_api_and_the_old_footer_text_is_gone(self):
        for needle in ('id="fs"', "requestFullscreen", "exitFullscreen", "fullscreenchange", "#i-fullx", "document.fullscreenEnabled"):
            self.assertIn(needle, self.page, needle)
        self.assertNotIn("getElementById(\"about\")", self.page)

    def test_the_two_tables_are_built_by_one_engine_with_the_columns_asked_for(self):
        self.assertIn('Table("repos"', self.page)
        self.assertIn('Table("hist"', self.page)
        repos = self.page.split('const REPO_TABLE=Table("repos",[', 1)[1].split("],()=>", 1)[0]
        hist = self.page.split('const HIST_TABLE=Table("hist",[', 1)[1].split("],()=>", 1)[0]
        for column in ("repo", "lastrun", "result", "ago", "lastok", "ok24", "min24", "now", "issues", "runno", "actor", "commit", "attempt", "queued", "branch", "visibility", "pushed", "prs"):
            self.assertIn(f'id:"{column}"', repos, column)
        for column in ("start", "repo", "workflow", "event", "branch", "result", "duration", "title", "runno", "actor", "commit", "attempt", "queued"):
            self.assertIn(f'id:"{column}"', hist, column)
        self.assertIn("e.shiftKey", self.page)
        self.assertIn("aria-sort", self.page)

    def test_the_server_sends_what_the_new_columns_need(self):
        import actions_monitor as am
        self.assertTrue(callable(am.repo_meta))
        meta = am.repo_meta(["x", "y"])
        self.assertEqual(set(meta), {"x", "y"})
        self.assertEqual(set(meta["x"]), {"private", "branch", "pushed", "prs"})
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('"number": run.get("run_number")', text)
        self.assertIn('"queued":', text)
        status = am.statusbar_payload(8765)
        for key in ("version", "edition", "port", "lan_address", "account", "sentinels", "uptime_seconds"):
            self.assertIn(key, status)
        lite = text.split("LITE_PATHS = (", 1)[1].split(")", 1)[0]
        self.assertNotIn("/api/statusbar", lite)                                  # the bar is also in the lite edition


@unittest.skipUnless(shutil.which("node"), "Node is not installed: the sorting logic is checked only where it is")
class SortingRunsForReal(unittest.TestCase):
    def evaluate(self, body):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        start = page.index("function jget(k,def)")
        end = page.index("const dash_=")
        script = ("const mem={};const store={get:k=>mem[k]??null,set:(k,v)=>{mem[k]=v}};const LOC=()=>'en-GB';const LANG='en';const T=k=>k;const esc=s=>String(s);\n"
                  + page[start:end] + "\n" + body)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sort_test.js"
            path.write_text(script, encoding="utf-8")
            done = subprocess.run(["node", str(path)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_click_cycles_up_down_none_and_shift_adds_a_second_key_and_empty_goes_last(self):
        result = self.evaluate("""
const cols=[{id:'name',label:'n',def:1,fixed:1,sort:r=>r.name,cell:r=>r.name},{id:'n',label:'n',def:1,sort:r=>r.n,cell:r=>r.n},{id:'x',label:'x',sort:r=>r.x,cell:r=>r.x}];
const tb=Table('t',cols,()=>{});const rows=[{name:'b',n:2,x:null},{name:'a',n:2,x:5},{name:'c',n:1,x:1},{name:'d',n:null,x:2}];
const names=()=>tb.sorted(rows).map(r=>r.name).join('');
const out={};
out.none=names();
tb.click('n',false);out.up=names();
tb.click('n',false);out.down=names();
tb.click('n',false);out.off=names()+tb.sort.length;
tb.click('n',false);tb.click('name',true);out.two=names();
tb.click('name',true);out.twoDesc=names();
tb.click('name',true);out.back=tb.sort.map(s=>s.c+s.d).join(',');
out.saved=JSON.parse(mem['am-sort-t']).length;
out.cols=tb.visible().map(c=>c.id).join(',');
console.log(JSON.stringify(out));""")
        self.assertEqual(result["none"], "bacd")
        self.assertEqual(result["up"], "cbad")           # 1, 2, 2 (stable: b before a), then the empty one last
        self.assertEqual(result["down"], "bacd")         # 2, 2 (stable), 1, and the empty one is still last
        self.assertEqual(result["off"], "bacd0")
        self.assertEqual(result["two"], "cabd")          # n up, then name up inside the ties
        self.assertEqual(result["twoDesc"], "cbad")
        self.assertEqual(result["back"], "n1")
        self.assertEqual(result["saved"], 1)
        self.assertEqual(result["cols"], "name,n")        # the optional column is hidden until chosen

    def test_a_saved_order_and_columns_are_restored_and_garbage_is_dropped(self):
        result = self.evaluate("""
mem['am-sort-t']=JSON.stringify([{c:'n',d:-1},{c:'zzz',d:1},{c:'name',d:7}]);mem['am-cols-t']=JSON.stringify(['x']);
const cols=[{id:'name',label:'n',def:1,fixed:1,sort:r=>r.name,cell:r=>r.name},{id:'n',label:'n',def:1,sort:r=>r.n,cell:r=>r.n},{id:'x',label:'x',sort:r=>r.x,cell:r=>r.x}];
const tb=Table('t',cols,()=>{});
console.log(JSON.stringify({sort:tb.sort,cols:tb.visible().map(c=>c.id)}));""")
        self.assertEqual(result["sort"], [{"c": "n", "d": -1}])
        self.assertEqual(result["cols"], ["name", "x"])          # the fixed column cannot be hidden


class Changelogs(unittest.TestCase):
    FILES = [p for p in ([ROOT / "CHANGELOG.md", HERE / "CHANGELOG.md"] + [HERE / "docs" / f"CHANGELOG_{s}.md" for s in ("spa", "deu", "fra", "ita", "jpn", "zho", "por")]) if p.is_file()]      # the zip of the package has no copy at the root

    @staticmethod
    def versions(path):
        return re.findall(r"^## \[(\d+\.\d+\.\d+(?:\.\d+)?)\]", path.read_text(encoding="utf-8"), re.M)

    def test_every_changelog_lists_its_versions_from_the_newest_to_the_oldest_with_none_repeated(self):
        for path in self.FILES:
            found = self.versions(path)
            keys = [tuple(int(x) for x in v.split(".")) for v in found]
            self.assertEqual(keys, sorted(keys, reverse=True), path.name)
            self.assertEqual(len(set(found)), len(found), path.name)

    def test_the_translations_have_the_same_versions_as_the_source_and_the_root_is_its_copy(self):
        self.assertGreaterEqual(len(self.FILES), 8)
        source = self.versions(HERE / "CHANGELOG.md")
        for path in self.FILES:
            self.assertEqual(self.versions(path), source, path.name)

    def test_the_readme_of_the_package_has_no_history_inside_and_points_to_the_changelog(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            text = (HERE / f"README_{lang}.txt").read_text(encoding="utf-8")
            self.assertEqual(re.findall(r"^\S.*\d\.\d\.\d.*CHANGELOG\.md[)）]\s*$", text, re.M), [], lang)
            self.assertIn("CHANGELOG", text, lang)


if __name__ == "__main__":
    unittest.main()
