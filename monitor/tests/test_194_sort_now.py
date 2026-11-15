# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The order of the section "Happening now": seven orders (the ecosystem one is the default), the choice remembered for each user (the server in the team mode, the browser otherwise) and the order of
the configuration file for whoever has not chosen.

1. The closed list of orders is the same in the code, the settings, the page and the eight catalogues.
2. A user's order is kept in their record, only from the closed list, and one user never sees another's.
3. The page puts the runs in the order asked, the same runs and the same order giving the same result; the ecosystem order keeps its headings and the others have none.
4. The choice wins over the configuration file, which wins over the default; a wrong value falls back one step.
Nothing sleeps for real: the page test runs on virtual time and asks for the order of fixed data."""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
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
NOW = ordering.KINDS["now"]


class TheClosedList(unittest.TestCase):
    def test_the_default_is_the_ecosystem_order_that_the_page_always_had(self):
        self.assertEqual(ordering.DEFAULTS["now"], "ecosystem")
        self.assertEqual(am.DEFAULTS["ui"]["now_sort"], "ecosystem")
        self.assertEqual(ordering.configured({}, "now"), "ecosystem")

    def test_the_setting_accepts_exactly_the_orders_of_the_list_and_nothing_else(self):
        self.assertEqual(settings_api.FIELDS["ui.now_sort"][3], NOW)
        for key in NOW:
            self.assertEqual(settings_api.check_value("ui.now_sort", key), (True, key), key)
        for bad in ("", "Ecosystem", "newest ", "alerts", "age;", 3, None, ["age"]):
            self.assertFalse(settings_api.check_value("ui.now_sort", bad)[0], bad)

    def test_the_configuration_file_gives_the_order_and_a_wrong_one_is_the_default(self):
        self.assertEqual(ordering.configured({"ui": {"now_sort": "age"}}, "now"), "age")
        for wrong in ({"ui": {"now_sort": "nope"}}, {"ui": {"now_sort": 3}}, {"ui": "age"}, {"ui": None}, None):
            self.assertEqual(ordering.configured(wrong, "now"), "ecosystem", wrong)

    def test_the_page_lists_the_same_orders_in_its_code_its_select_and_the_eight_catalogues(self):
        listed = re.search(r'const SORTS=\{now:\[([^\]]*)\],alerts:', PAGE)
        self.assertIsNotNone(listed)
        self.assertEqual(re.findall(r'"([a-z]+)"', listed.group(1)), list(NOW))
        select = re.search(r'<select id="now-sort"[^>]*>(.*?)</select>', PAGE, re.S).group(1)
        self.assertEqual(re.findall(r'<option value="([a-z]+)"', select), list(NOW))
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.sort_by", "ui.sort_now_title", "ui.cfg_b_order", "cfg.f.ui.now_sort", "cfg.h.ui.now_sort") + tuple("ui.sort_now_" + k for k in NOW):
                self.assertTrue(catalogue.get(key), (lang, key))
            for key in NOW:
                self.assertIn(key, catalogue["cfg.h.ui.now_sort"], (lang, key))

    def test_the_guide_and_the_advanced_list_name_the_setting_and_the_route_in_the_eight_languages(self):
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            guide = (HERE / "docs" / f"SCREENS{tail}.md").read_text(encoding="utf-8")
            self.assertIn("`ui.now_sort`", guide, tail)
            self.assertIn("/api/auth/me/view", guide, tail)
            self.assertIn("`ui.now_sort`", (HERE / "docs" / f"ADVANCED{tail}.md").read_text(encoding="utf-8"), tail)

    def test_the_skills_know_the_route_and_the_setting(self):
        for kind in ("internal", "external"):
            api = (HERE / "skills" / kind / "references" / "api.md").read_text(encoding="utf-8")
            self.assertIn("/api/auth/me/view", api, kind)
            self.assertIn("ui.now_sort", (HERE / "skills" / kind / "references" / "settings.md").read_text(encoding="utf-8"), kind)


class WhatAUserKeeps(unittest.TestCase):
    start = ta.LiveTeam.start
    call = ta.LiveTeam.call
    make_admin = ta.LiveTeam.make_admin
    sign_in = ta.LiveTeam.sign_in
    add_user = ta.LiveTeam.add_user

    def team(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        admin = self.sign_in("root")
        self.add_user(admin, "vic", "viewer", ["alpha"])
        self.add_user(admin, "ann", "viewer", ["alpha"])
        return admin, self.sign_in("vic"), self.sign_in("ann")

    def test_a_user_keeps_their_order_and_another_user_does_not_see_it(self):
        _admin, vic, ann = self.team()
        self.assertEqual(self.call("/api/auth/me/view", headers=vic)[1], {"view": {}})
        status, body, _ = self.call("/api/auth/me/view", {"now": "age"}, vic)
        self.assertEqual((status, body), (200, {"ok": True, "view": {"now": "age"}}))
        self.assertEqual(self.call("/api/auth/me/view", headers=vic)[1], {"view": {"now": "age"}})
        self.assertEqual(self.call("/api/auth/me/view", headers=ann)[1], {"view": {}})
        self.assertEqual(self.storage.get_record("users", "vic")["view"], {"now": "age"})

    def test_what_is_not_in_the_closed_list_is_refused_and_nothing_is_kept(self):
        _admin, vic, _ann = self.team()
        for body, code in (({"now": "alerts"}, "order_invalid"), ({"now": 3}, "order_invalid"), ({"other": "age"}, "kind_invalid"), ({"now": "age", "x": "y"}, "kind_invalid")):
            status, answer, _ = self.call("/api/auth/me/view", body, vic)
            self.assertEqual((status, answer["code"]), (400, code), body)
        self.assertEqual(self.call("/api/auth/me/view", headers=vic)[1], {"view": {}})
        self.assertEqual(self.call("/api/auth/me/view", [1], vic)[0], 400)

    def test_an_empty_text_forgets_the_choice_and_a_stored_garbage_is_not_served(self):
        _admin, vic, _ann = self.team()
        self.call("/api/auth/me/view", {"now": "repo"}, vic)
        self.assertEqual(self.call("/api/auth/me/view", {"now": ""}, vic)[1]["view"], {})
        record = self.storage.get_record("users", "vic")
        record["view"] = {"now": "evil", "other": "age"}
        self.storage.put_record("users", "vic", record)
        self.assertEqual(self.call("/api/auth/me/view", headers=vic)[1], {"view": {}})

    def test_without_a_session_nothing_is_read_or_written_and_a_write_needs_the_csrf_token(self):
        _admin, vic, _ann = self.team()
        self.assertEqual(self.call("/api/auth/me/view")[0], 401)
        self.assertEqual(self.call("/api/auth/me/view", {"now": "age"})[0], 401)
        no_csrf = {"Cookie": vic["Cookie"]}
        self.assertEqual(self.call("/api/auth/me/view", {"now": "age"}, no_csrf)[0], 403)
        self.assertEqual(self.storage.get_record("users", "vic").get("view"), None)


class TheStorageRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = ta.new_storage(Path(self.tmp.name))
        self.addCleanup(self.storage.close)

    def test_an_unknown_user_gets_nothing_and_cannot_save(self):
        self.assertEqual(ordering.get_view(self.storage, "ghost"), {})
        self.assertEqual(ordering.set_view(self.storage, "ghost", {"now": "age"}), (None, "user_unknown"))
        self.assertEqual(ordering.set_view(self.storage, "ghost", "age"), (None, "body_invalid"))

    def test_the_view_keeps_only_known_lists_with_known_orders(self):
        self.assertEqual(ordering.clean_view({"now": "state", "alerts": "x", "other": "age"}), {"now": "state"})
        self.assertEqual(ordering.clean_view({"now": "state", "alerts": "streak"}), {"now": "state", "alerts": "streak"})
        for raw in (None, [], "now", 3):
            self.assertEqual(ordering.clean_view(raw), {})


PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    for(let i=0;i<200&&!DATA;i++)await wait(100);
    const run=(repo,o)=>Object.assign({repo:repo,name:"ci",event:"push",branch:"main",sha:"abc1234",actor:"x",status:"in_progress",conclusion:null,seconds:60,stuck:false,started:"2026-01-01T10:00:00Z",url:"https://github.com/o/r/actions/runs/1",jobs:[]},o||{});
    const runs=[run("zeta",{seconds:30,started:"2026-01-01T10:05:00Z",event:"schedule"}),run("alpha",{seconds:900,started:"2026-01-01T10:00:00Z"}),
      run("mid",{status:"queued",seconds:5,started:"2026-01-01T10:09:00Z",event:"pull_request"}),run("stuck",{stuck:true,seconds:100,started:"2026-01-01T10:02:00Z"}),
      run("bad",{seconds:200,started:"2026-01-01T10:03:00Z",jobs:[{name:"j",status:"completed",conclusion:"failure",steps_done:1,steps_total:1,seconds:3}]}),
      run("alpha",{status:"queued",seconds:1,started:"2026-01-01T10:11:00Z"})];
    const eco={zeta:"beta",alpha:"alpha",mid:"alpha",stuck:"beta",bad:"alpha"},r={orders:{},dom:{},heads:{}};
    SORTS.now.forEach(k=>{r.orders[k]=nowSorted(runs,k,eco).map(g=>g[0].repo+":"+g.length)});
    r.again=JSON.stringify(nowSorted(runs,"severity",eco))===JSON.stringify(nowSorted(runs,"severity",eco));
    r.input_kept=runs.map(x=>x.repo).join(",");
    r.unknown=nowSorted(runs,"nope",eco).map(g=>g[0].repo);
    DATA=Object.assign({},DATA,{active:runs,failing:[],ecosystems:eco,figures:undefined});
    FILTER.eco="";FILTER.state="";FILTER.q="";FILTER.list=null;
    const sel=document.getElementById("now-sort");
    r.options=[...sel.options].map(o=>o.value);r.labels_filled=[...sel.options].every(o=>o.textContent.length>2);
    r.first=sortGet("now");
    for(const k of SORTS.now){sel.value=k;sel.dispatchEvent(new Event("change"));
      r.dom[k]=[...document.querySelectorAll("#now [data-now-repo]")].map(e=>e.dataset.nowRepo);r.heads[k]=document.querySelectorAll("#now h3").length;r.kept=store.get("am-sort-now")}
    // the configuration file asks for an order; the user's choice wins; a wrong one falls back
    store.set("am-sort-now","");I18N.screens={now_sort:"repo"};r.cfg=sortGet("now");
    store.set("am-sort-now","age");r.mine=sortGet("now");
    store.set("am-sort-now","nope");r.wrong_mine=sortGet("now");
    store.set("am-sort-now","");I18N.screens={now_sort:"nope"};r.wrong_cfg=sortGet("now");I18N.screens={};r.none=sortGet("now");
    // team mode: the server keeps it
    const sent=[];window.fetch=async(u,o)=>{sent.push([String(u),o&&o.body]);return {ok:true,json:async()=>({view:{}})}};
    VIEWSRV.team=true;VIEWSRV.view={now:"newest"};r.team_get=sortGet("now");
    sortSet("now","state");r.team_set=sortGet("now");r.sent=sent;sortSet("now","bogus");r.after_bogus=sortGet("now");r.sent_n=sent.length;
    // expand all / collapse all, with any order, kept by a refresh and remembered like the order
    VIEWSRV.team=false;VIEWSRV.view={};store.set("am-sort-fold","");
    DATA=Object.assign({},DATA,{active:["one","two","three"].flatMap(n=>[run(n,{seconds:10}),run(n,{seconds:20})]),ecosystems:{one:"a",two:"a",three:"b"}});      // three repositories with two runs each: the ones that fold
    const openN=()=>[...document.querySelectorAll("#now details[data-now-details]")].filter(e=>e.open).length,allN=()=>document.querySelectorAll("#now details[data-now-details]").length;
    r.fold={};
    for(const k of ["ecosystem","severity","repo"]){sel.value=k;sel.dispatchEvent(new Event("change"));
      document.getElementById("now-open").click();const up=openN();now_(DATA);const kept=openN();
      document.getElementById("now-close").click();const down=openN();now_(DATA);
      r.fold[k]=[allN(),up,kept,down,openN()]}
    document.getElementById("now-open").click();r.fold_kept=store.get("am-sort-fold");
    document.querySelector("#now details[data-now-details]").open=false;await wait(50);now_(DATA);r.fold_one_shut=[allN(),openN()];
    document.getElementById("now-close").click();r.fold_back=store.get("am-sort-fold");
    store.set("am-sort-fold","nope");r.fold_wrong=sortGet("fold");store.set("am-sort-fold","");r.fold_default=sortGet("fold");
    const sent2=[];window.fetch=async(u,o)=>{sent2.push([String(u),o&&o.body]);return {ok:true,json:async()=>({view:{}})}};
    VIEWSRV.team=true;document.getElementById("now-open").click();r.fold_team=[sortGet("fold"),sent2];
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

    def test_each_order_puts_the_runs_where_it_says(self):
        o = self.found["orders"]
        self.assertEqual(o["ecosystem"], ["alpha:2", "mid:1", "bad:1", "zeta:1", "stuck:1"], "ecosystem, then the order the runs came in")
        self.assertEqual(o["severity"], ["stuck:1", "bad:1", "alpha:2", "zeta:1", "mid:1"], "stuck, failed job, running by age, queued")
        self.assertEqual(o["age"], ["alpha:2", "bad:1", "stuck:1", "zeta:1", "mid:1"])
        self.assertEqual(o["newest"], ["alpha:2", "mid:1", "zeta:1", "bad:1", "stuck:1"], "a repository counts by its newest run")
        self.assertEqual(o["repo"], ["alpha:2", "bad:1", "mid:1", "stuck:1", "zeta:1"])
        self.assertEqual(o["event"], ["mid:1", "alpha:2", "bad:1", "stuck:1", "zeta:1"], "pull_request, push, schedule")
        self.assertEqual(o["state"], ["alpha:2", "bad:1", "stuck:1", "zeta:1", "mid:1"], "running before queued")

    def test_the_same_runs_always_give_the_same_order_and_the_input_is_not_touched(self):
        self.assertTrue(self.found["again"])
        self.assertEqual(self.found["input_kept"], "zeta,alpha,mid,stuck,bad,alpha")
        self.assertEqual(self.found["unknown"], ["stuck", "bad", "alpha", "zeta", "mid"], "an order the page does not know is the severity one")

    def test_the_list_above_the_section_draws_the_section_in_that_order_and_remembers_it(self):
        f = self.found
        self.assertEqual(f["options"], list(NOW))
        self.assertTrue(f["labels_filled"])
        self.assertEqual(f["first"], "ecosystem")
        for key in NOW:
            self.assertEqual(f["dom"][key], [x.split(":")[0] for x in f["orders"][key]], key)
        self.assertEqual({k: v for k, v in f["heads"].items() if v}, {"ecosystem": 2}, "only the ecosystem order has headings")
        self.assertEqual(f["kept"], "state")

    def test_the_choice_wins_over_the_configuration_file_which_wins_over_the_default(self):
        f = self.found
        self.assertEqual((f["cfg"], f["mine"], f["wrong_mine"], f["wrong_cfg"], f["none"]), ("repo", "age", "repo", "ecosystem", "ecosystem"))

    def test_in_the_team_mode_the_server_keeps_it_and_a_wrong_order_is_not_sent(self):
        f = self.found
        self.assertEqual((f["team_get"], f["team_set"], f["after_bogus"]), ("newest", "state", "state"))
        self.assertEqual(f["sent"], [["/api/auth/me/view", '{"now":"state"}']])
        self.assertEqual(f["sent_n"], 1)

    def test_expand_all_and_collapse_all_work_with_any_order_survive_a_refresh_and_are_remembered(self):
        f = self.found
        for key, (total, up, kept, down, after) in f["fold"].items():
            self.assertEqual((total, up, kept, down, after), (3, 3, 3, 0, 0), key)
        self.assertEqual(f["fold_kept"], "open")
        self.assertEqual(f["fold_one_shut"], [3, 2], "a repository folded by hand stays folded while the rest is unfolded")
        self.assertEqual((f["fold_back"], f["fold_wrong"], f["fold_default"]), ("closed", "closed", "closed"))
        self.assertEqual(f["fold_team"], ["open", [["/api/auth/me/view", '{"fold":"open"}']]])


class TheFoldChoice(unittest.TestCase):
    def test_the_choice_is_a_closed_list_with_the_folded_default_and_the_buttons_are_in_the_catalogues_and_the_guides(self):
        self.assertEqual(ordering.KINDS["fold"], ("open", "closed"))
        self.assertEqual(ordering.DEFAULTS["fold"], "closed")
        self.assertEqual(ordering.clean_view({"fold": "open", "now": "age", "x": "y"}), {"fold": "open", "now": "age"})
        self.assertEqual(ordering.clean_view({"fold": "maybe"}), {})
        self.assertEqual(ordering.configured({"ui": {}}, "fold"), "closed")
        for tag in ('id="now-open"', 'id="now-close"'):
            self.assertIn(tag, PAGE)
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.fold_open_all", "ui.fold_close_all", "ui.fold_title"):
                self.assertTrue(catalogue.get(key), (lang, key))
        tails = dict(zip(i18n.LANGS, ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por")))
        for lang, tail in {"en": "", "es": "_spa", "de": "_deu", "fr": "_fra", "it": "_ita", "ja": "_jpn", "zh": "_zho", "pt": "_por"}.items():
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            guide = (HERE / "docs" / f"SCREENS{tail}.md").read_text(encoding="utf-8")
            self.assertIn("**" + catalogue["ui.fold_open_all"] + "**", guide, lang)
            self.assertIn("**" + catalogue["ui.fold_close_all"] + "**", guide, lang)
        self.assertEqual(len(tails), 8)

    def test_the_server_keeps_the_choice_in_the_record_of_the_user_next_to_the_order(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        storage = ta.new_storage(Path(tmp.name))
        self.addCleanup(storage.close)
        storage.put_record("users", "vic", {"role": "viewer"})
        self.assertEqual(ordering.set_view(storage, "vic", {"fold": "open"}), ({"fold": "open"}, ""))
        self.assertEqual(ordering.set_view(storage, "vic", {"now": "age"}), ({"fold": "open", "now": "age"}, ""))
        self.assertEqual(ordering.set_view(storage, "vic", {"fold": "maybe"}), (None, "order_invalid"))
        self.assertEqual(ordering.get_view(storage, "vic"), {"fold": "open", "now": "age"})
        self.assertEqual(ordering.set_view(storage, "vic", {"fold": ""}), ({"now": "age"}, ""))


if __name__ == "__main__":
    unittest.main()
