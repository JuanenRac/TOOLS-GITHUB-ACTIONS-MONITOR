# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The order of the list of the Alerts tab: nine orders (as the monitor sends them is the default), the choice remembered for each user like the order of Happening now, and the order of the configuration
file for whoever has not chosen.

1. The closed list of orders is the same in the code, the settings, the page and the eight catalogues.
2. The server keeps the order of the alerts of a user next to the one of Happening now, from the closed list only.
3. The page puts the alerts in the order asked: severity, streak, class (real before watch), age, newest, repository, origin, state; ties keep the order the monitor sent; an alert without a date goes last.
4. The choice wins over the configuration file, which wins over the default.
The page test runs on virtual time with fixed data: nothing sleeps for real and nothing depends on the clock."""
import json
import os
import re
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
import test_auth as ta  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.ui import ordering  # noqa: E402

try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
ALERTS = ordering.KINDS["alerts"]


class TheClosedList(unittest.TestCase):
    def test_the_default_keeps_the_order_the_monitor_sends(self):
        self.assertEqual(ordering.DEFAULTS["alerts"], "server")
        self.assertEqual(am.DEFAULTS["ui"]["alerts_sort"], "server")
        self.assertEqual(ordering.configured({}, "alerts"), "server")
        self.assertEqual(ordering.configured({"ui": {"alerts_sort": "streak"}}, "alerts"), "streak")
        for wrong in ({"ui": {"alerts_sort": "age "}}, {"ui": {"alerts_sort": None}}, {"ui": 1}):
            self.assertEqual(ordering.configured(wrong, "alerts"), "server")

    def test_the_setting_accepts_exactly_the_orders_of_the_list(self):
        self.assertEqual(settings_api.FIELDS["ui.alerts_sort"][3], ALERTS)
        for key in ALERTS:
            self.assertEqual(settings_api.check_value("ui.alerts_sort", key), (True, key))
        for bad in ("", "level", "Severity", 1, None, ["age"]):
            self.assertFalse(settings_api.check_value("ui.alerts_sort", bad)[0], bad)

    def test_the_page_lists_the_same_orders_in_its_code_its_select_and_the_eight_catalogues(self):
        listed = re.search(r'alerts:\[([^\]]*)\],fold:', PAGE)
        self.assertIsNotNone(listed)
        self.assertEqual(re.findall(r'"([a-z]+)"', listed.group(1)), list(ALERTS))
        select = re.search(r'<select id="al-sort"[^>]*>(.*?)</select>', PAGE, re.S).group(1)
        self.assertEqual(re.findall(r'<option value="([a-z]+)"', select), list(ALERTS))
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.sort_al_title", "cfg.f.ui.alerts_sort", "cfg.h.ui.alerts_sort") + tuple("ui.sort_al_" + k for k in ALERTS):
                self.assertTrue(catalogue.get(key), (lang, key))
            for key in ALERTS:
                self.assertIn(key, catalogue["cfg.h.ui.alerts_sort"], (lang, key))

    def test_the_guide_the_advanced_list_and_the_skills_say_so(self):
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            self.assertIn("`ui.alerts_sort`", (HERE / "docs" / f"SCREENS{tail}.md").read_text(encoding="utf-8"), tail)
            self.assertIn("`ui.alerts_sort`", (HERE / "docs" / f"ADVANCED{tail}.md").read_text(encoding="utf-8"), tail)
        for kind in ("internal", "external"):
            self.assertIn("ui.alerts_sort", (HERE / "skills" / kind / "references" / "settings.md").read_text(encoding="utf-8"), kind)


class WhatAUserKeeps(unittest.TestCase):
    start = ta.LiveTeam.start
    call = ta.LiveTeam.call
    make_admin = ta.LiveTeam.make_admin
    sign_in = ta.LiveTeam.sign_in
    add_user = ta.LiveTeam.add_user

    def test_the_two_orders_of_a_user_are_kept_apart_and_one_does_not_undo_the_other(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        admin = self.sign_in("root")
        self.add_user(admin, "vic", "viewer", ["alpha"])
        vic = self.sign_in("vic")
        self.assertEqual(self.call("/api/auth/me/view", {"alerts": "streak"}, vic)[1]["view"], {"alerts": "streak"})
        self.assertEqual(self.call("/api/auth/me/view", {"now": "age"}, vic)[1]["view"], {"alerts": "streak", "now": "age"})
        self.assertEqual(self.call("/api/auth/me/view", {"alerts": ""}, vic)[1]["view"], {"now": "age"})
        status, answer, _ = self.call("/api/auth/me/view", {"alerts": "ecosystem"}, vic)
        self.assertEqual((status, answer["code"]), (400, "order_invalid"), "an order of the other list is not accepted")
        self.assertEqual(self.call("/api/auth/me/view", headers=vic)[1], {"view": {"now": "age"}})


PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    for(let i=0;i<200&&!DATA;i++)await wait(100);
    const al=(id,o)=>Object.assign({id:id,code:"ci.red",level:"warning",sentinel:"ci",account_id:"default",repo:"r"+id,title:"title "+id,details:{},created_at:"2026-01-01T10:00:00Z"},o||{});
    const rows=[al("a1",{repo:"zed",details:{streak:5}}),al("a2",{level:"error",sentinel:"collab",repo:"alp",details:{streak:2},created_at:"2026-01-01T10:05:00Z"}),
      al("a3",{level:"info",repo:"mid",created_at:"2026-01-01T10:03:00Z"}),al("a4",{level:"critical",sentinel:"system",repo:"alp",created_at:"",muted_until:"2026-01-02T00:00:00Z",details:{streak:1}}),
      al("a5",{level:"error",repo:"bee",details:{streak:9},created_at:"2026-01-01T10:01:00Z"})];
    const r={orders:{},dom:{}},ids=l=>l.map(a=>a.id).join(" ");
    SORTS.alerts.forEach(k=>{r.orders[k]=ids(alertsSorted(rows,k))});
    r.unknown=ids(alertsSorted(rows,"nope"));r.input_kept=ids(rows);
    ALERTS={alerts:rows,summary:{total:5,muted:1,by_sentinel:{ci:3,collab:1,system:1},by_level:{}},sentinels:["ci","collab","system"],mutes:[],history:[],mute_hours:24};
    ALF.s="";ALF.l="";ALF.m=true;
    const sel=document.getElementById("al-sort");r.options=[...sel.options].map(o=>o.value);r.first=sortGet("alerts");
    for(const k of SORTS.alerts){sel.value=k;sel.dispatchEvent(new Event("change"));
      r.dom[k]=[...document.querySelectorAll("#al-list .alrow")].map(row=>row.querySelector("button[data-v]").dataset.v).join(" ");r.kept=store.get("am-sort-alerts")}
    const chips=id=>[...document.querySelectorAll("#al-list .alrow")].filter(row=>row.querySelector("button[data-v]").dataset.v===id).map(row=>[...row.querySelectorAll(".chip")].map(c=>c.textContent).filter(t=>t.startsWith("×")));
    r.chips={a1:chips("a1"),a2:chips("a2"),a3:chips("a3"),a4:chips("a4")};
    store.set("am-sort-alerts","");I18N.screens={alerts_sort:"streak"};r.cfg=sortGet("alerts");
    store.set("am-sort-alerts","age");r.mine=sortGet("alerts");
    store.set("am-sort-alerts","ecosystem");r.other_list=sortGet("alerts");
    store.set("am-sort-alerts","");I18N.screens={alerts_sort:"nope"};r.wrong_cfg=sortGet("alerts");
    const sent=[];window.fetch=async(u,o)=>{sent.push([String(u),o&&o.body]);return {ok:true,json:async()=>({view:{}})}};
    VIEWSRV.team=true;VIEWSRV.view={};sortSet("alerts","class");r.team=sortGet("alerts");r.sent=sent;
    out.textContent=JSON.stringify({ok:true,found:r});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:{}})}
})();
</script>
"""


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class InTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = check_overflow.free_port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        cls.saved = check_overflow.PROBE
        check_overflow.PROBE = PROBE
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.relay = check_overflow.relay(cls.port)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}/"
        cls.found = check_overflow.measure(check_overflow.edge(), f"{cls.base}?lang=en&nowizard=1", check_overflow.SIZES["desktop"])

    @classmethod
    def tearDownClass(cls):
        check_overflow.PROBE = cls.saved
        cls.relay.shutdown()
        cls.demo.terminate()

    def test_each_order_puts_the_alerts_where_it_says(self):
        o = self.found["orders"]
        self.assertEqual(o["server"], "a1 a2 a3 a4 a5")
        self.assertEqual(o["severity"], "a4 a2 a5 a1 a3", "critical, error (as sent), warning, info")
        self.assertEqual(o["streak"], "a5 a1 a2 a4 a3", "the longest streak first; no streak ties by severity")
        self.assertEqual(o["class"], "a4 a2 a5 a1 a3", "real (error or critical) before watch")
        self.assertEqual(o["age"], "a1 a5 a3 a2 a4", "oldest first, the one without a date last")
        self.assertEqual(o["newest"], "a2 a3 a5 a1 a4", "newest first, the one without a date last")
        self.assertEqual(o["repo"], "a2 a4 a5 a3 a1")
        self.assertEqual(o["origin"], "a1 a3 a5 a2 a4")
        self.assertEqual(o["state"], "a1 a2 a3 a5 a4", "open before silenced")
        self.assertEqual(self.found["unknown"], "a1 a2 a3 a4 a5", "an order the page does not know is the order of the monitor")
        self.assertEqual(self.found["input_kept"], "a1 a2 a3 a4 a5")

    def test_the_list_above_the_alerts_draws_them_in_that_order_and_remembers_it(self):
        f = self.found
        self.assertEqual(f["options"], list(ALERTS))
        self.assertEqual(f["first"], "server")
        for key in ALERTS:
            self.assertEqual(f["dom"][key], f["orders"][key], key)
        self.assertEqual(f["kept"], "state")

    def test_an_alert_that_failed_several_times_shows_its_streak(self):
        self.assertEqual(self.found["chips"], {"a1": [["×5"]], "a2": [["×2"]], "a3": [[]], "a4": [[]]}, "a streak of one is not shown")

    def test_the_choice_wins_over_the_configuration_file_and_the_order_of_the_other_list_is_not_used(self):
        f = self.found
        self.assertEqual((f["cfg"], f["mine"], f["other_list"], f["wrong_cfg"]), ("streak", "age", "streak", "server"))

    def test_in_the_team_mode_the_server_keeps_it(self):
        self.assertEqual(self.found["team"], "class")
        self.assertEqual(self.found["sent"], [["/api/auth/me/view", '{"alerts":"class"}']])


if __name__ == "__main__":
    unittest.main()
