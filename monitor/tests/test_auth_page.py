# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The page in team mode: the box with the user and the role, the menu, the panel of users, and the wrapper of `fetch` that adds the CSRF token to every change, sends the person to /login when
the session is gone and does nothing at all in the individual mode or in the lite edition.

The wrapper is run for real in Node with a fake network (skipped where Node is not installed); the rest reads the source of the page and the eight catalogues."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
NODE = shutil.which("node")


def wrapper_source():
    start = PAGE.index("(function(){const raw=window.fetch.bind(window)")
    end = PAGE.index("return go(u,o,false)}})();", start) + len("return go(u,o,false)}})();")
    return PAGE[start:end]


HARNESS = r"""
const calls = [];
let script = null;
const window = {fetch: null};
const location = {href: "/"};
globalThis.window = window;
globalThis.location = location;
const reply = (body, status) => new Response(JSON.stringify(body), {status: status || 200, headers: {"Content-Type": "application/json"}});
const base = async (u, o) => {
  o = o || {};
  calls.push({url: String(u), method: o.method || "GET", headers: o.headers || {}});
  return script(String(u), o, calls.length);
};
(async () => {
  const out = {};
  const run = async (name, fn) => { window.fetch = base; eval(SOURCE); calls.length = 0; location.href = "/"; out[name] = await fn(); out[name + "_calls"] = calls.map(c => [c.method, c.url, c.headers["X-CSRF-Token"] || null, c.headers["X-Monitor-Token"] || null]); out[name + "_href"] = location.href; };
  const post = (u) => window.fetch(u, {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"});
  const me = (team) => (u) => u === "/api/auth/me" ? reply(team) : u === "/api/session-token" ? reply({token: "T1"}) : reply({ok: true});

  script = me({enabled: false, mode: "individual", authenticated: false});
  await run("individual", async () => (await post("/api/alerts/mute")).status);

  script = me({enabled: true, mode: "team", authenticated: true, csrf: "C1"});
  await run("team_post", async () => (await post("/api/alerts/mute")).status);
  await run("team_get", async () => (await window.fetch("/api/alerts")).status);
  await run("login_post", async () => (await post("/api/auth/login")).status);

  script = (u) => u === "/api/auth/me" ? new Response("nope", {status: 404}) : reply({ok: true});
  await run("lite_post", async () => (await post("/api/hot-only")).status);

  script = (u) => u === "/api/alerts" ? reply({ok: false, code: "auth_required"}, 401) : reply({});
  await run("expired", async () => (await window.fetch("/api/alerts")).status);

  let csrf = 0;
  script = (u, o) => {
    if (u === "/api/auth/me") return reply({enabled: true, mode: "team", authenticated: true, csrf: csrf === 0 ? "OLD" : "NEW"});
    if (u === "/api/hot-only") { if ((o.headers || {})["X-CSRF-Token"] === "NEW") return reply({ok: true}); csrf = 1; return reply({ok: false, code: "csrf"}, 403); }
    return reply({});
  };
  await run("csrf_retry", async () => (await post("/api/hot-only")).status);

  script = (u) => u === "/api/auth/me" ? reply({enabled: true, mode: "team", authenticated: true, csrf: "C"}) : reply({ok: false, code: "csrf"}, 403);
  await run("csrf_loop", async () => (await post("/api/hot-only")).status);
  console.log(JSON.stringify(out));
})();
"""


@unittest.skipUnless(NODE, "Node is not installed")
class Wrapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "run.js"
            script.write_text("const SOURCE = " + json.dumps(wrapper_source()) + ";\n" + HARNESS, encoding="utf-8")
            done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=60, cwd=tmp)
        if done.returncode != 0:
            raise AssertionError(done.stderr[-800:])
        cls.out = json.loads(done.stdout.strip().splitlines()[-1])

    def urls(self, name):
        return [c[1] for c in self.out[name + "_calls"]]

    def test_the_individual_mode_gets_no_csrf_header(self):
        self.assertEqual(self.out["individual"], 200)
        self.assertTrue(all(c[2] is None for c in self.out["individual_calls"]))
        self.assertEqual([c for c in self.out["individual_calls"] if c[1] == "/api/alerts/mute"][0][3], "T1", "the one-use token of the page still travels")

    def test_a_signed_in_person_sends_the_csrf_token_on_every_change_only(self):
        mute = [c for c in self.out["team_post_calls"] if c[1] == "/api/alerts/mute"][0]
        self.assertEqual((mute[2], mute[3]), ("C1", "T1"))
        self.assertEqual(self.urls("team_get"), ["/api/alerts"], "a read asks nothing more and adds nothing")

    def test_the_login_itself_carries_no_csrf_token_and_asks_nothing(self):
        self.assertEqual(self.urls("login_post"), ["/api/auth/login"])

    def test_a_monitor_without_the_endpoint_counts_as_individual(self):
        self.assertEqual(self.out["lite_post"], 200)
        self.assertTrue(all(c[2] is None for c in self.out["lite_post_calls"]))

    def test_an_expired_session_sends_the_person_to_the_login(self):
        self.assertEqual((self.out["expired"], self.out["expired_href"]), (401, "/login"))

    def test_a_wrong_csrf_token_is_renewed_and_tried_once(self):
        self.assertEqual(self.out["csrf_retry"], 200)
        sent = [c[2] for c in self.out["csrf_retry_calls"] if c[1] == "/api/hot-only"]
        self.assertEqual(sent, ["OLD", "NEW"])

    def test_it_never_retries_more_than_once(self):
        self.assertEqual(self.out["csrf_loop"], 403)
        self.assertEqual(len([c for c in self.out["csrf_loop_calls"] if c[1] == "/api/hot-only"]), 2)


class Source(unittest.TestCase):
    def test_the_box_the_menu_and_the_panel_are_in_the_page(self):
        for needle in ('id="auth-box"', 'id="auth-btn"', 'id="auth-menu"', 'id="auth-panel"', "async function authUsers", "function authPassword", "authInit();", "X-CSRF-Token", 'location.href="/login"'):
            self.assertIn(needle, PAGE, needle)

    def test_nothing_is_drawn_unless_the_team_mode_is_on(self):
        body = PAGE[PAGE.index("function authRender()"):PAGE.index("function authClose()")]
        self.assertIn("LITE||!m||!m.enabled", body, "the lite edition and the individual mode keep the box hidden")
        self.assertIn('m.mode!=="team"', body)
        self.assertIn("if(LITE)return", PAGE[PAGE.index("async function authInit()"):PAGE.index("function authRender()")], "the lite edition asks nothing")

    def test_no_data_goes_through_innerhtml_in_the_new_code(self):
        new = PAGE[PAGE.index("let AUTHME=null;"):PAGE.index("applyStatic();fillThemes();applyTheme(theme);applySide();applyGroups();setViewTitle();applyDense(DENSE);cfgLoad();")]
        self.assertNotIn("innerHTML", new)

    def test_every_text_the_new_code_uses_exists_in_the_eight_catalogues(self):
        new = PAGE[PAGE.index("let AUTHME=null;"):PAGE.index("applyStatic();fillThemes();applyTheme(theme);applySide();applyGroups();setViewTitle();applyDense(DENSE);cfgLoad();")]
        keys = {k for k in re.findall(r'T\("(ui\.auth_[a-z_]+)"', new) if not k.endswith("_")} | {"ui.auth_role_" + r for r in ("viewer", "maintainer", "admin")}
        self.assertGreaterEqual(len(keys), 20)
        for lang in i18n.LANGS:
            for key in sorted(keys):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        self.assertIn("{user}", i18n.tl("en", "ui.auth_confirm_delete"))
        self.assertEqual(i18n.tl("pt", "ui.auth_logout"), "Terminar sessão")


if __name__ == "__main__":
    unittest.main()
