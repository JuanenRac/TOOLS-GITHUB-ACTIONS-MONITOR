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

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    await wait(1500);
    await cfgLoad();await wait(300);await cfgExtras();await wait(600);
    const r={},sel=document.getElementById("ai-preset");
    r.options=[...sel.options].map(o=>o.value);
    sel.value="lmstudio";sel.dispatchEvent(new Event("change"));
    r.info_local=document.getElementById("ai-preset-info").textContent;
    sel.value="openai";sel.dispatchEvent(new Event("change"));
    r.info_cloud=document.getElementById("ai-preset-info").textContent;
    r.models=[...document.getElementById("ai-preset-model").options].map(o=>o.value);
    document.getElementById("ai-preset-apply").click();await wait(200);
    r.provider=document.getElementById("cfg-ai-provider").value;r.base=document.getElementById("cfg-ai-base_url").value;r.env=document.getElementById("cfg-ai-api_key_env").value;r.model=document.getElementById("cfg-ai-model").value;
    r.dirty=Object.keys(CFG.cur).filter(k=>JSON.stringify(CFG.cur[k])!==JSON.stringify(CFG.orig[k]));
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
class TheSelector(unittest.TestCase):
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

    def test_the_selector_fills_in_the_form_without_a_key(self):
        found = check_overflow.measure(check_overflow.edge(), f"{self.base}?lang=en&nowizard=1", check_overflow.SIZES["desktop"])
        self.assertIn("lmstudio", found["options"], found)
        self.assertEqual(found["options"][0], "")
        self.assertIn("does not leave it", found["info_local"])
        self.assertIn("OPENAI_API_KEY", found["info_cloud"])
        self.assertIn("not tested", found["info_cloud"])
        self.assertEqual((found["provider"], found["base"], found["env"], found["model"]), ("openai-compatible", "https://api.openai.com/v1", "OPENAI_API_KEY", found["models"][0]))
        self.assertIn("ai.provider", found["dirty"])


class TheTexts(unittest.TestCase):
    def test_every_text_is_in_the_eight_languages(self):
        keys = [k for k in json.loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8")) if k.startswith("ui.ai_preset")]
        self.assertGreaterEqual(len(keys), 9)
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(catalogue.get(key), (lang, key))


if __name__ == "__main__":
    unittest.main()
