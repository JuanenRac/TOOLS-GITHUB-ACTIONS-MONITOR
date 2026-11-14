# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The panel where each user of the team mode sets how and when they are told (menu of the signed-in user, "Notifications"): it reads and saves the preferences through /api/auth/me/notify, shows a stored
secret as stored (never its value) and sends a secret only when one is typed. Runs in a headless browser with the answers of the server replaced; skipped when there is none (and on a CI runner unless
MONITOR_BROWSER_TESTS=1)."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(TOOLS))
import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402

try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

KEYS = ("ui.auth_notify", "ui.nt_off_server", "ui.nt_unseen", "ui.nt_enabled", "ui.nt_channels", "ui.nt_ntfy_topic", "ui.nt_ntfy_token", "ui.nt_teams_webhook", "ui.nt_email_address", "ui.nt_secret_kept",
        "ui.nt_sentinels", "ui.nt_sent_ci", "ui.nt_sent_collab", "ui.nt_min_level", "ui.nt_level_info", "ui.nt_level_warn", "ui.nt_level_bad", "ui.nt_system", "ui.nt_digest", "ui.nt_digest_off",
        "ui.nt_digest_hourly", "ui.nt_digest_daily", "ui.nt_save", "ui.nt_test", "ui.nt_seen", "ui.nt_saved", "ui.nt_failed", "ui.nt_test_ok", "ui.nt_test_fail", "ui.nt_seen_done")

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    await wait(1200);
    const sent=[];
    window.fetch=async(u,o)=>{const s=String(u);if(o&&o.method==="POST"){sent.push([s,JSON.parse(o.body||"{}")]);return {ok:true,json:async()=>({ok:true,prefs:{}})}}
      return {ok:true,json:async()=>({enabled:false,unseen:3,prefs:{enabled:true,channels:["ntfy"],sentinels:["ci"],min_level:"warn",system:false,digest:"hourly",destinations:{ntfy:{topic:"mine"}},secrets:{ntfy:true,teams:false},role:"admin",families:["ci","release","system"]}})}};
    await authNotify();await wait(200);
    const p=document.getElementById("auth-panel"),r={};
    r.texts=p.textContent;
    r.checked=[...p.querySelectorAll("input[type=checkbox]")].map(e=>e.checked);
    r.topic=[...p.querySelectorAll("input[type=text]")].map(e=>e.value);
    r.placeholders=[...p.querySelectorAll("input[type=password]")].map(e=>e.placeholder);
    r.pw_values=[...p.querySelectorAll("input[type=password]")].map(e=>e.value);
    const w=p.querySelectorAll("input[type=password]")[1];w.value="https://example.invalid/hook";
    [...p.querySelectorAll("button.authact")][0].click();await wait(200);
    r.sent=sent;
    out.textContent=JSON.stringify({ok:true,found:r});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:{}})}
})();
</script>
"""


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class ThePanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.saved = check_overflow.PROBE
        check_overflow.PROBE = PROBE
        cls.relay = check_overflow.relay(cls.port)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        check_overflow.PROBE = cls.saved
        cls.relay.shutdown()
        cls.demo.terminate()

    def test_it_shows_the_preferences_hides_the_secret_and_saves_only_what_was_typed(self):
        found = check_overflow.measure(check_overflow.edge(), f"{self.base}?lang=en&nowizard=1", check_overflow.SIZES["desktop"])
        self.assertIn("The administrator has not turned on notifications", found["texts"])
        self.assertIn("Alerts you have not seen: 3", found["texts"])
        self.assertEqual(found["checked"], [True, True, False, False, True, False, False], found)      # enabled; ntfy, teams, email; CI, collaboration; system
        self.assertEqual(found["topic"][0], "mine")
        self.assertTrue(all(v == "" for v in found["pw_values"]), "a stored secret is never put back in the page")
        self.assertIn("stored", found["placeholders"][0])
        (path, body), = found["sent"]
        self.assertEqual(path, "/api/auth/me/notify")
        self.assertEqual(body["secrets"], {"teams": "https://example.invalid/hook"}, "only the typed secret is sent")
        self.assertEqual((body["channels"], body["sentinels"], body["min_level"], body["digest"]), (["ntfy"], ["ci"], "warn", "hourly"))


class TheTexts(unittest.TestCase):
    def test_every_text_is_in_the_eight_languages(self):
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in KEYS:
                self.assertTrue(catalogue.get(key), (lang, key))
        en = json.loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8"))
        self.assertIn("{n}", en["ui.nt_unseen"])

    def test_the_menu_has_the_entry_for_every_user_and_the_panel_uses_the_three_routes(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('item("ui.auth_notify",authNotify)', page)
        for route in ("/api/auth/me/notify", "/api/auth/me/notify/test", "/api/auth/me/notify/seen"):
            self.assertIn(route, page)


if __name__ == "__main__":
    unittest.main()
