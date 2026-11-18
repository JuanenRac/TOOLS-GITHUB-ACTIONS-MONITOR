# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The logo of the organization for the wall screens (docs/SCREENS.md): what is accepted (PNG, JPEG, WebP and SVG by their first bytes, at most 1 MB, an SVG without scripts, event handlers, links to other
files or document types), where it is kept (data/, never the configuration), what is served back (the real type, nosniff, a policy that forbids everything), who can change it, and how the page and the screens
use it (a corner, a size, the screens it shows on, only when a logo exists)."""
import http.client
import json
import re
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.app import actions_monitor, orglogo, screens, settings_api, toolconfig
from github_actions_monitor.security import audited_posts

HERE = Path(__file__).resolve().parent.parent
SCREENS = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
MAIN = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


def png(width=64, height=32, extra=b""):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00" + b"\x00\x00\x00\x00" + extra


def jpeg(width=64, height=32):
    return b"\xff\xd8\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xff\xc0" + struct.pack(">H", 17) + b"\x08" + struct.pack(">HH", height, width) + b"\x03" + b"\x00" * 9


def webp():
    return b"RIFF" + struct.pack("<I", 22) + b"WEBPVP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00" + (63).to_bytes(3, "little") + (31).to_bytes(3, "little")


GOOD_SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><defs><linearGradient id="g"/></defs><rect width="10" height="10" fill="url(#g)" style="fill:#fff"/><use href="#a"/></svg>'
BAD_SVGS = {
    "script": b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    "handler": b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>',
    "javascript": b'<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><rect/></a></svg>',
    "link": b'<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.com/x.svg#a"/></svg>',
    "image": b'<svg xmlns="http://www.w3.org/2000/svg"><image href="file.png"/></svg>',
    "foreign": b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div>x</div></foreignObject></svg>',
    "doctype": b'<!DOCTYPE svg [<!ENTITY a "b">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>',
    "url": b'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="url(https://example.com/a)"/></svg>',
    "import": b'<svg xmlns="http://www.w3.org/2000/svg"><style>@import "x.css";</style></svg>',
    "iframe": b'<svg xmlns="http://www.w3.org/2000/svg"><iframe src="x"/></svg>',
}


class WhatIsAccepted(unittest.TestCase):
    def test_the_four_kinds_are_known_by_their_first_bytes_and_not_by_a_name(self):
        self.assertEqual([orglogo.validate(x)[0] for x in (png(), jpeg(), webp(), GOOD_SVG)], ["png", "jpg", "webp", "svg"])
        self.assertEqual(orglogo.validate(b"MZ\x90\x00 this is a program")[1], "type")
        self.assertEqual(orglogo.validate(b"GIF89a....")[1], "type", "a GIF is not one of the four")
        self.assertEqual(orglogo.validate(b"<html><body>hi</body></html>")[1], "type")
        self.assertEqual(orglogo.validate(b"")[1], "empty")
        self.assertEqual(orglogo.validate("text")[1], "empty")

    def test_at_most_one_megabyte(self):
        self.assertEqual(orglogo.MAX_BYTES, 1024 * 1024)
        self.assertEqual(orglogo.validate(png(extra=b"\x00" * (orglogo.MAX_BYTES - len(png()))))[0], "png")
        self.assertEqual(orglogo.validate(png(extra=b"\x00" * (orglogo.MAX_BYTES - len(png()) + 1)))[1], "too_big")

    def test_a_picture_with_absurd_pixels_is_refused(self):
        self.assertEqual(orglogo.validate(png(40000, 40000))[1], "pixels")
        self.assertEqual(orglogo.validate(png(0, 10))[1], "pixels")
        self.assertEqual(orglogo.validate(jpeg(30000, 30000))[1], "pixels")

    def test_a_svg_is_only_drawing(self):
        self.assertEqual(orglogo.svg_problem(GOOD_SVG), None, "a link inside the file (#a) and a gradient are drawing")
        for name, data in BAD_SVGS.items():
            kind, reason = orglogo.validate(data)
            self.assertIsNone(kind, name)
            self.assertIn(reason, ("active", "link", "not_svg", "binary", "type"), name)
        self.assertEqual(orglogo.validate(b'<svg xmlns="http://www.w3.org/2000/svg" ONLOAD = "x"/>')[1], "active", "the case does not matter")
        self.assertEqual(orglogo.validate(b"<svg>\x00\x01</svg>")[1], "binary")


class WhereItLives(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(orglogo, "_folder", return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_it_is_a_file_of_the_data_folder_and_only_one_exists(self):
        self.assertEqual(orglogo.info(), {"present": False, "kind": None, "bytes": 0, "tag": ""})
        first = orglogo.save(png())
        self.assertEqual((first["present"], first["kind"], first["bytes"]), (True, "png", len(png())))
        self.assertEqual(sorted(p.name for p in Path(self.tmp.name).iterdir()), ["org_logo.png"])
        second = orglogo.save(GOOD_SVG)
        self.assertEqual(second["kind"], "svg")
        self.assertEqual(sorted(p.name for p in Path(self.tmp.name).iterdir()), ["org_logo.svg"], "the old one is gone and no temporary file stays")
        self.assertNotEqual(first["tag"], second["tag"], "a new logo has a new address, so it is never shown from the cache")

    def test_it_is_never_in_the_configuration(self):
        self.assertTrue(all(not k.startswith("screens.logo") or k.split(".")[1] in ("logo_overview", "logo_now", "logo_sentinels", "logo_corner", "logo_max_width", "logo_max_height") for k in settings_api.FIELDS))
        self.assertFalse([k for k in settings_api.FIELDS if "logo" in k and settings_api.FIELDS[k][2] in ("text", "path")], "no setting holds the picture or a path to it")
        from github_actions_monitor.util import paths
        self.assertEqual(paths.kind_of("org_logo.png"), "data")
        self.assertEqual(paths.kind_of("org_logo.svg"), "data")

    def test_a_file_put_there_by_hand_is_checked_again(self):
        (Path(self.tmp.name) / "org_logo.svg").write_bytes(BAD_SVGS["script"])
        self.assertIsNotNone(orglogo.load(), "the type is right, so it is read; the content was checked at upload")
        (Path(self.tmp.name) / "org_logo.svg").unlink()
        (Path(self.tmp.name) / "org_logo.png").write_bytes(b"not a picture at all")
        self.assertIsNone(orglogo.load())
        self.assertFalse(orglogo.info()["present"])

    def test_remove(self):
        self.assertFalse(orglogo.remove())
        orglogo.save(jpeg())
        self.assertTrue(orglogo.remove())
        self.assertFalse(orglogo.info()["present"])
        with self.assertRaises(ValueError):
            orglogo.save(b"nothing")


class Running:
    def __init__(self, case, config):
        patcher = mock.patch.object(toolconfig, "raw_config", return_value=config)
        patcher.start()
        case.addCleanup(patcher.stop)
        self.server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def call(self, method, path, body=None, ctype=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            headers = {"Host": f"127.0.0.1:{self.port}"}
            if ctype:
                headers["Content-Type"] = ctype
            connection.request(method, path, body=body, headers=headers)
            answer = connection.getresponse()
            seen = {}
            for key, value in answer.getheaders():
                seen[key.lower()] = seen[key.lower()] + "; " + value if key.lower() in seen else value
            return answer.status, answer.read(), seen
        finally:
            connection.close()


class TheRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(orglogo, "_folder", return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.server = Running(self, {"screens": {"enabled": True}})

    def test_upload_show_and_remove(self):
        self.assertEqual(self.server.call("GET", "/api/screens/logo")[0], 404)
        status, body, _ = self.server.call("POST", "/api/screens/logo", png(), "image/png")
        answer = json.loads(body)
        self.assertEqual((status, answer["ok"], answer["logo"]["kind"]), (200, True, "png"))
        status, body, headers = self.server.call("GET", "/api/screens/logo?v=" + answer["logo"]["tag"])
        self.assertEqual((status, body, headers["content-type"]), (200, png(), "image/png"))
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertIn("default-src 'none'", headers["content-security-policy"])
        self.assertIn("sandbox", headers["content-security-policy"])
        info = json.loads(self.server.call("GET", "/api/screens/logo/info")[1])
        self.assertEqual((info["present"], info["tag"]), (True, answer["logo"]["tag"]))
        status, body, _ = self.server.call("POST", "/api/screens/logo/remove")
        self.assertEqual((status, json.loads(body)["removed"]), (200, True))
        self.assertEqual(self.server.call("GET", "/api/screens/logo")[0], 404)

    def test_the_type_that_counts_is_the_real_one(self):
        status, body, _ = self.server.call("POST", "/api/screens/logo", b"MZ program", "image/png")
        self.assertEqual((status, json.loads(body)["error"]), (400, "type"))
        status, body, _ = self.server.call("POST", "/api/screens/logo", jpeg(), "text/plain")
        self.assertEqual(status, 200, "the label that came with the file is not believed, nor needed")
        self.assertEqual(json.loads(body)["logo"]["kind"], "jpg")
        self.assertEqual(self.server.call("GET", "/api/screens/logo")[2]["content-type"], "image/jpeg")

    def test_an_svg_with_a_script_is_refused_and_nothing_is_kept(self):
        status, body, _ = self.server.call("POST", "/api/screens/logo", BAD_SVGS["script"], "image/svg+xml")
        self.assertEqual((status, json.loads(body)["error"]), (400, "active"))
        self.assertEqual(self.server.call("GET", "/api/screens/logo")[0], 404)
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_too_big_or_empty(self):
        status, body, _ = self.server.call("POST", "/api/screens/logo", b"\x00" * (orglogo.MAX_BYTES + 1), "image/png")
        self.assertEqual((status, json.loads(body)["error"]), (413, "too_big"))
        status, body, _ = self.server.call("POST", "/api/screens/logo", b"", "image/png")
        self.assertEqual((status, json.loads(body)["error"]), (400, "empty"))

    def test_the_two_posts_are_in_the_log_of_actions_table_and_need_an_admin(self):
        self.assertIn("/api/screens/logo", audited_posts.AUDITED)
        self.assertIn("/api/screens/logo/remove", audited_posts.AUDITED)
        from github_actions_monitor.security import auth
        for path in ("/api/screens/logo", "/api/screens/logo/remove"):
            self.assertEqual(auth.required_role("POST", path), "admin", path)
        self.assertEqual(auth.required_role("GET", "/api/screens/logo"), "viewer")

    def test_the_settings_page_sends_the_session_token_with_the_upload(self):
        self.assertIn("screens\\/logo", MAIN.split("need=", 1)[1][:200])


class OnTheScreens(unittest.TestCase):
    def test_only_the_general_screen_in_the_top_right_corner_by_default(self):
        cfg = screens.settings({})
        self.assertEqual((cfg["logo_overview"], cfg["logo_now"], cfg["logo_sentinels"], cfg["logo_corner"], cfg["logo_max_width"], cfg["logo_max_height"]), (True, False, False, "top-right", 160, 64))
        self.assertIsNone(screens.logo_block(cfg, {"present": False}), "no logo uploaded: nothing is drawn")
        block = screens.logo_block(cfg, {"present": True, "tag": "abcdef0123456789xxxx"})
        self.assertEqual(block["show"], {"overview": True, "now": False, "sentinels": False})
        self.assertEqual((block["corner"], block["max_width"], block["max_height"]), ("top-right", 160, 64))
        self.assertEqual(block["url"], "/api/screens/logo?v=abcdef0123456789")

    def test_the_settings_have_limits(self):
        cfg = screens.settings({"screens": {"logo_corner": "middle", "logo_max_width": 99999, "logo_max_height": 1, "logo_now": "on"}})
        self.assertEqual((cfg["logo_corner"], cfg["logo_max_width"], cfg["logo_max_height"], cfg["logo_now"]), ("top-right", 640, 16, True))
        for corner in screens.CORNERS:
            self.assertEqual(screens.settings({"screens": {"logo_corner": corner}})["logo_corner"], corner)

    def test_the_page_data_carries_the_logo_only_when_there_is_one(self):
        cfg = screens.settings({"screens": {"logo_now": True, "logo_corner": "bottom-left"}})
        prm = screens.params({}, cfg)
        self.assertIsNone(screens.page_data("now", cfg, prm)["logo"])
        data = screens.page_data("now", cfg, prm, logo={"present": True, "tag": "t1"})
        self.assertEqual((data["logo"]["corner"], data["logo"]["show"]["now"], data["logo"]["show"]["sentinels"]), ("bottom-left", True, False))

    def test_the_page_has_a_box_in_each_corner_and_does_not_cover_the_content(self):
        for corner in ("lg-tl", "lg-tr", "lg-bl", "lg-br"):
            self.assertIn('id="%s"' % corner, SCREENS)
        header = SCREENS.split("<header>")[1].split("</header>")[0]
        footer = SCREENS.split('<div class="foot">')[1].split("</div>")[0]
        self.assertIn("lg-tl", header)
        self.assertIn("lg-tr", header)
        self.assertIn("lg-bl", footer)
        self.assertIn("lg-br", footer)
        css = re.search(r"\.orglogo\{[^}]*\}", SCREENS).group(0)
        for need in ("object-fit:contain", "max-width:calc(var(--lw", "max-height:calc(var(--lh", "width:auto", "height:auto"):
            self.assertIn(need, css)
        self.assertNotRegex(css, r"position\s*:\s*(fixed|absolute)", "a box of the layout, not above the content")
        self.assertNotRegex(css, r"background|#[0-9a-fA-F]{3}|rgb", "transparent: the picture and the theme decide the colours")

    def test_the_page_texts_exist_in_the_eight_languages(self):
        keys = ["ui.logo_h", "ui.logo_choose", "ui.logo_remove", "ui.logo_hint", "ui.cfg_b_logo", "ui.cfg_b_look", "ui.cfg_u_px"] + ["ui.logo_m_" + c for c in ("saved", "removed", "too_big", "empty", "type", "active", "link", "not_svg", "binary", "pixels", "request")]
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                for key in keys:
                    self.assertNotEqual(i18n.t(key), key, f"{lang} {key}")
        for reason in ("too_big", "empty", "type", "active", "link", "not_svg", "binary", "pixels"):      # every reason orglogo.validate can give has its sentence
            self.assertIn('"%s"' % reason, Path(orglogo.__file__).read_text(encoding="utf-8"), reason)
            self.assertNotEqual(i18n.t("ui.logo_m_" + reason), "ui.logo_m_" + reason, reason)


if __name__ == "__main__":
    unittest.main()
