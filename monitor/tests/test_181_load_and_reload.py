# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The box "loading repositories" leaves when the last repository is read, and a reload of the page (F5) gets its data in seconds. Three causes are covered: the upkeep that runs after the reading
of the repositories (the brief for the AI tools) could spin forever on a long list of Sentinel panels and kept the page on the last partial picture ("131/131") while it starved the server of
processor time; the finished picture waited for that upkeep before it reached the page; and /api/data wrote to the connection with the global lock held, so one stalled connection froze every
other page and the cycle itself. Everything runs offline; the browser test is skipped when there is no Edge, Chrome or Chromium."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.integrations import ai_alerts  # noqa: E402

try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None


def panels(count):
    return [{"id": f"a{i}", "title": f"Panel {i}", "level": "bad", "summary": "x" * 40,
             "rows": [{"level": "bad", "repo": f"repo-{i}-{j}", "text": "something is wrong here", "url": ""} for j in range(12)]} for i in range(count)]


class BriefEnds(unittest.TestCase):
    def test_a_long_list_of_panels_is_cut_to_the_limit_and_the_function_returns(self):
        box = {}

        def work():
            box["text"] = ai_alerts.brief([], 2048, now=1, panels=panels(20))

        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        worker.join(15)
        self.assertFalse(worker.is_alive(), "the brief spins forever when the panels do not fit")
        self.assertLessEqual(len(box["text"].encode("utf-8")), 2048 + 200)
        self.assertIn("more in ai_alerts.jsonl", box["text"])
        self.assertIn("## Sentinel panels", box["text"])


class FinishedPictureAndLock(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.object(am, "LOG_FILE", Path(tempfile.gettempdir()) / "ghamon_181_log.txt"),
                   mock.patch.dict(am.STATE, {"data": None, "error": None, "hint": None}, clear=False),
                   mock.patch.object(am, "SENTINEL", {"obj": None, "registry": None, "error": None}),
                   mock.patch.object(am, "brief_status", lambda *a, **k: None),
                   mock.patch.object(am, "write_cycle_log", lambda data: None)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        am.STATE.pop("complete", None)
        am.WATCH.reset()
        self.addCleanup(lambda: am.WATCH.new_generation())

    def test_the_finished_picture_reaches_the_page_before_the_upkeep_ends(self):
        release = threading.Event()
        self.addCleanup(release.set)
        entered = threading.Event()

        def maintain(config, data):
            entered.set()
            release.wait(30)

        partial = {"updated": "x", "repos": ["a"], "loading": "131/131"}
        full = {"updated": "y", "repos": ["a"], "loading": "", "offline": {"offline": False}}

        def collect(config, publish=None):
            publish(partial)
            return full

        config = dict(am.DEFAULTS)
        with mock.patch.object(am, "collect", collect), mock.patch.object(am, "maintain", maintain):
            worker = threading.Thread(target=lambda: am.run_cycle(config, am.WATCH.generation), daemon=True)
            worker.start()
            self.assertTrue(entered.wait(10))
            self.assertEqual(am.STATE["data"]["loading"], "", "the box 'loading repositories' stays while the upkeep runs")
            release.set()
            worker.join(10)

    def test_a_stalled_connection_does_not_freeze_the_other_pages(self):
        gate = threading.Event()
        self.addCleanup(gate.set)
        real = am.Handler.reply
        first = {"n": 0}

        def reply(handler, *args, **kwargs):
            if handler.path.startswith("/api/data"):
                first["n"] += 1
                if first["n"] == 1:      # the first page never reads its answer
                    gate.wait(30)
            return real(handler, *args, **kwargs)

        am.STATE["data"] = {"updated": "z", "loading": "", "repos": []}
        server = am.QuietServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        with mock.patch.object(am.Handler, "reply", reply):
            threading.Thread(target=lambda: urllib.request.urlopen(base + "/api/data", timeout=40).read(), daemon=True).start()
            for _ in range(100):
                if first["n"]:
                    break
                time.sleep(0.05)
            started = time.time()
            body = json.loads(urllib.request.urlopen(base + "/api/data", timeout=10).read())
            self.assertLess(time.time() - started, 5, "a reload waits for the stalled connection of the previous page")
            self.assertEqual(body["data"]["updated"], "z")
        self.assertTrue(am.LOCK.acquire(timeout=1), "the lock is held by a stalled connection")
        am.LOCK.release()


HOOK = r"""<script>
(function(){var orig=window.fetch.bind(window);window.__fake="loading";
window.fetch=function(u,o){if(String(u).indexOf("/api/data")===0){return orig(u,o).then(function(r){return r.json()}).then(function(j){
 if(j.data){j.data.loading=window.__fake==="loading"?"131/131":""}
 return new Response(JSON.stringify(j),{status:200,headers:{"Content-Type":"application/json"}})})}
 return orig(u,o)}})();
</script>"""

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  const shown=id=>{const e=document.getElementById(id);return !!e&&!e.hidden&&getComputedStyle(e).display!=="none"&&e.getBoundingClientRect().height>0};
  try{
    const r={};
    window.__fake="loading";await wait(500);await tick(true);await wait(300);r.shown_while_loading=shown("kt-loading");r.text=document.getElementById("tv-load").textContent;
    window.__fake="done";await tick(true);await wait(300);r.gone_when_done=!shown("kt-loading");
    r.first_paint_ok=!!DATA;
    out.textContent=JSON.stringify({ok:true,found:r});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:{}})}
})();
</script>
"""


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class LoadingBoxInABrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]
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
        cls.relay = check_overflow.relay(cls.port, probe=PROBE, head=HOOK.encode("utf-8"))
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.relay.shutdown()
        cls.demo.terminate()

    def test_the_box_shows_while_loading_and_leaves_with_the_last_repository(self):
        found = check_overflow.measure(check_overflow.edge(), f"{self.base}?lang=en&nowizard=1", check_overflow.SIZES["desktop"])
        self.assertTrue(found["shown_while_loading"], found)
        self.assertIn("131", found["text"])
        self.assertTrue(found["gone_when_done"], found)
        self.assertTrue(found["first_paint_ok"], found)


if __name__ == "__main__":
    unittest.main()
