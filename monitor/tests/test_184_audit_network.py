# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Outgoing requests and the page, kept inside their rules.

1. The OpenTelemetry export goes through the rule of netguard: a collector on this computer is called directly and never followed through a redirect; any other collector is refused when it,
   or a redirect, leads to a private address; no proxy of the environment is used.
2. The proxy of the environment is off by default and said to be a frontier of trust, in the code and in the help of the setting, in the eight languages.
3. The page puts no free text of the API into a markup string without `esc()`: the list of the few places that do (their value goes to textContent) is kept short and exact.
"""
import http.server
import re
import sys
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.integrations import otlp  # noqa: E402
from github_actions_monitor.security import netguard  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
DATA = {"runs": [{"repo": "r", "id": 1, "status": "completed", "name": "CI", "branch": "main", "event": "push", "conclusion": "success", "started": "2026-01-01T00:00:00Z", "seconds": 3}],
        "figures": {"active": 1}}


class Collector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hits = []
        test = cls

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                test.hits.append(self.path)
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                if self.path.startswith("/redirect"):
                    self.send_response(307)
                    self.send_header("Location", "/v1/other")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        otlp.STATE.update({"sent": set(), "total": 0, "last_ok": None, "last_error": "", "next": 0.0})
        del self.hits[:]

    def config(self, endpoint, **extra):
        return {"otlp": {"enabled": True, "endpoint": endpoint, "interval_seconds": 15}, **extra}

    def test_a_collector_on_this_computer_works(self):
        result = otlp.export(self.config(self.base), DATA, "1.8.1", now=1_800_000_000)
        self.assertEqual((result["sent_spans"], result["error"]), (1, ""))
        self.assertEqual(self.hits, ["/v1/traces", "/v1/metrics"])

    def test_a_redirect_of_a_collector_on_this_computer_is_not_followed(self):
        result = otlp.export(self.config(self.base + "/redirect"), DATA, "1.8.1", now=1_800_000_000)
        self.assertEqual(result["sent_spans"], 0)
        self.assertTrue(result["error"])
        self.assertEqual(self.hits, ["/redirect/v1/traces"], "nothing was sent to the place the redirect named")

    def test_a_collector_that_leads_to_a_private_address_is_refused_before_anything_is_sent(self):
        for endpoint in ("https://169.254.169.254", "https://10.0.0.5", "https://192.168.1.20:4318", "https://[::1]:4318"):
            otlp.STATE["next"] = 0.0
            result = otlp.export(self.config(endpoint), DATA, "1.8.1", now=1_800_000_000)
            self.assertEqual((result["sent_spans"], bool(result["error"])), (0, True), endpoint)

    def test_the_rule_and_the_setting_that_lifts_it(self):
        seen = {}

        def fake_open(request, timeout=8, allow_private=False, resolver=None, use_proxy=False):
            seen.update(allow_private=allow_private, use_proxy=use_proxy)
            return mock.Mock(read=lambda: b"")
        request = urllib.request.Request("https://collector.example.org/v1/traces", data=b"{}", method="POST")
        with mock.patch.object(netguard, "open_url", fake_open):
            otlp._send(request, {})
            self.assertEqual(seen, {"allow_private": False, "use_proxy": False})
            otlp._send(request, {"notify": {"allow_private_targets": True}})
            self.assertTrue(seen["allow_private"])
            otlp._send(request, {"notify": {"allow_private_targets": "yes"}})
            self.assertFalse(seen["allow_private"], "only a real true lifts it")


class ProxyIsAFrontierOfTrust(unittest.TestCase):
    def test_off_by_default(self):
        self.assertIs(am.DEFAULTS["network"]["use_proxy"], False)

    def test_the_code_and_the_help_of_the_setting_say_it_in_every_language(self):
        self.assertIn("FRONTIER OF TRUST", netguard.__doc__)
        self.assertIn("frontier of trust", i18n.tl("en", "cfg.h.network.use_proxy"))
        english = i18n.tl("en", "cfg.h.network.use_proxy")
        for lang in i18n.LANGS:
            text = i18n.tl(lang, "cfg.h.network.use_proxy")
            self.assertNotEqual(text, "cfg.h.network.use_proxy", lang)
            self.assertTrue(lang == "en" or text != english, lang)
            self.assertGreater(len(text), 120, lang)


class PageEscaping(unittest.TestCase):
    FREE_TEXT = "title|name|text|repo|message|branch|actor|workflow|step|label|labels|url|owner|sha|event|tag|command|error|detail|cause|reason|snippet|description|conclusion|status|ecosystem|scope|value|html"
    ALLOWED = {"${b.ecosystem}": "textContent", "${e.message}": "textContent"}      # the markup string is assigned to textContent, not innerHTML

    def test_no_free_text_of_the_api_goes_into_markup_without_esc(self):
        found = sorted({m.group(0) for m in re.finditer(r"\$\{\s*[A-Za-z_$][\w$]*(?:\.[\w$]+)*\.(?:%s)\s*\}" % self.FREE_TEXT, PAGE)})
        self.assertEqual(found, sorted(self.ALLOWED), "a field of free text must be written ${esc(x.field)}")

    def test_the_two_exceptions_are_text_not_markup(self):
        self.assertRegex(PAGE, r"bx\.textContent=T\(over\?\"ui\.bud_over\":\"ui\.bud_warn\"\)\+bud\.map\(b=>`\$\{b\.ecosystem\}")
        self.assertRegex(PAGE, r"errs\.push\(`\$\{e\.section\}: \$\{e\.message\}")
        self.assertRegex(PAGE, r"eb\.textContent=errs\.length")

    def test_the_helpers_that_make_markup_escape_or_check(self):
        self.assertIn('const esc=s=>String(s==null?"":s).replace(/[&<>"\']/g', PAGE)
        self.assertIn('const safeUrl=u=>typeof u==="string"&&u.startsWith("https://github.com/")?u:"#";', PAGE)
        self.assertIn("const link=(u,t)=>`<a href=\"${esc(safeUrl(u))}\" target=\"_blank\" rel=\"noopener\">${esc(t)}</a>`;", PAGE)

    def test_every_blank_target_has_noopener(self):
        for match in re.finditer(r"target=\\?\"_blank\\?\"[^>]*", PAGE):
            self.assertIn("noopener", match.group(0), match.group(0)[:80])

    def test_the_markdown_of_the_help_is_escaped_before_its_marks_are_added(self):
        from github_actions_monitor.ui import helpdocs
        html = helpdocs.render("# T\n\n<script>alert(1)</script> [x](javascript:alert(1)) [y](https://github.com/o/r) **b** ![i](x.png)\n", {})
        self.assertNotIn("<script", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn('href="https://github.com/o/r"', html)
        self.assertIn('rel="noopener noreferrer"', html)


if __name__ == "__main__":
    unittest.main()
