# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The dialog that asks before an update, in a real browser: it says what will happen and that the trust in the SHA-256 rests on GitHub, in two languages; and a person without the right to apply
(not at the computer of the monitor, a service, a container, the Lite edition) is shown the reason and no button that applies. The Updates menu is given a made-up state and a made-up answer of the
routes: nothing is downloaded, applied or written."""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402

try:
    import check_overflow as co  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    co = None
try:
    import check_page  # noqa: E402
except ImportError:
    check_page = None

NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))

PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out={steps:{}};
  try{
    await wait(1500);
    const base={installed:"2.1.3",available:"2.1.4",check:true,offline:false,newer:true,can_go_back:false,progress:{running:false}};
    UPD.st={...base,can_apply:false,blocked_by:"need_local"};updTop();
    out.steps.blocked={latest:document.querySelectorAll("#upd-top [data-upd]").length,text:$("upd-top").textContent,reason:T("ui.upd_blocked_need_local")};
    UPD.st={...base,can_apply:true,blocked_by:""};updTop();
    out.steps.allowed={latest:document.querySelectorAll("#upd-top [data-upd]").length};
    const calls=[];let shown="";
    window.updJ=async(kind)=>{calls.push(kind);if(kind==="plan")return {ok:true,plan:{blocked:false,installed:"2.1.3",target:"2.1.4",verified:true,backups:"BACKUPS",config:[{changes:[1,2]}],checks:[]}};return {ok:true}};
    window.askConfirm=async(t)=>{shown=t;return false};
    await updApply("2.1.4");
    out.steps.dialog={text:shown,calls:calls,trust:T("ui.upd_trust"),sums:T("ui.upd_verified_yes")};
  }catch(e){out.error=String(e&&e.stack||e).slice(0,400)}
  out.errors=(window.__smoke&&window.__smoke.errors||[]).slice(0,10);
  const pre=document.createElement("pre");pre.id="dlg-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>"""


class TheDialogInABrowser(unittest.TestCase):
    reports = {}

    @classmethod
    def setUpClass(cls):
        import socket
        import subprocess
        import time
        if co is None or check_page is None or not co.edge():
            return
        port = co.free_port()
        demo = subprocess.Popen([sys.executable, "-I", str(HERE.parent / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        server = None
        try:
            for _ in range(80):
                try:
                    socket.create_connection(("127.0.0.1", port), 0.5).close()
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("the demo monitor did not start")
            server = co.relay(port, probe=PROBE, head=check_page.HEAD.encode("utf-8"))
            for lang in ("en", "zh"):      # one browser at a time
                cls.reports[lang] = co.measure(co.edge(), f"http://127.0.0.1:{server.server_address[1]}/?lang={lang}&nowizard=1", co.SIZES["desktop"], report="dlg-report")
        finally:
            if server:
                server.shutdown()
                server.server_close()
            demo.terminate()
            try:
                demo.wait(timeout=15)
            except subprocess.TimeoutExpired:
                demo.kill()

    def need(self, lang):
        report = self.reports.get(lang)
        if report is None:
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        self.assertNotIn("error", report)
        return report

    def test_the_dialog_says_what_will_happen_and_where_the_trust_rests(self):
        for lang in ("en", "zh"):
            report = self.need(lang)
            dialog = report["steps"]["dialog"]
            self.assertEqual(dialog["calls"], ["plan"], lang)      # the person said no: nothing was applied
            self.assertIn(dialog["trust"], dialog["text"], lang)
            self.assertIn("SHA256SUMS", dialog["text"], lang)
            self.assertIn("2.1.4", dialog["text"], lang)
            self.assertIn("BACKUPS", dialog["text"], lang)
        self.assertIn("GitHub", self.need("en")["steps"]["dialog"]["trust"])

    def test_without_the_right_to_apply_there_is_the_reason_and_no_button(self):
        for lang in ("en", "zh"):
            report = self.need(lang)
            blocked, allowed = report["steps"]["blocked"], report["steps"]["allowed"]
            self.assertEqual(blocked["latest"], 0, lang)
            self.assertIn(blocked["reason"], blocked["text"], lang)
            self.assertEqual(allowed["latest"], 1, lang)
            self.assertEqual(report["errors"], [], lang)


if __name__ == "__main__":
    unittest.main()
