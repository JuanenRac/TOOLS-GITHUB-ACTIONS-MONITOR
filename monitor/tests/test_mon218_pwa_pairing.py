# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor as an app on a phone: the installable app (manifest, service worker that keeps no data, icons, offline page), the compact view, the pairing of a phone with a one-use QR code (a token of its
own, taken away alone, never the access token) and the palette. Everything is off or harmless by default and refuses without its switch and without the network mode."""
import json
import struct
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zlib
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api, toolconfig  # noqa: E402
from github_actions_monitor.security import devices, localguard  # noqa: E402
from github_actions_monitor.surfaces import pwa  # noqa: E402
from github_actions_monitor.util import qrcode  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
EXTRAS = (HERE / "assets" / "static" / "ui_extras.js").read_text(encoding="utf-8")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
CFG = {"enabled": True, "code_minutes": 5, "max_devices": 2, "device_days": 90}


class Qr(unittest.TestCase):
    def test_the_size_grows_with_the_text_and_the_finders_are_where_they_belong(self):
        small, big = qrcode.matrix("http://192.168.0.5:8765/pair?c=ABCDEFGHJKLM"), qrcode.matrix("x" * 150)
        self.assertEqual(len(small) % 4, 1)
        self.assertGreater(len(big), len(small))
        for rows in (small, big):
            size = len(rows)
            for ox, oy in ((0, 0), (size - 7, 0), (0, size - 7)):
                ring = [rows[oy + i][ox + j] for i in range(7) for j in range(7) if max(abs(i - 3), abs(j - 3)) == 3]
                self.assertTrue(all(ring))
                self.assertTrue(rows[oy + 3][ox + 3])
                self.assertFalse(rows[oy + 1][ox + 1])      # the white ring inside the finder
            self.assertTrue(rows[size - 8][8])      # the dark module

    def test_the_format_information_is_a_valid_code_word_twice(self):
        rows = qrcode.matrix("http://192.168.0.5:8765/pair?c=ABCDEFGHJKLM")
        size = len(rows)
        first = [rows[i][8] for i in range(6)] + [rows[7][8], rows[8][8], rows[8][7]] + [rows[8][14 - i] for i in range(9, 15)]
        second = [rows[8][size - 1 - i] for i in range(8)] + [rows[size - 15 + i][8] for i in range(8, 15)]
        self.assertEqual(first, second)
        word = sum(int(bit) << i for i, bit in enumerate(first)) ^ 0x5412
        self.assertEqual(qrcode._bch(word >> 10, 0x537, 15, 10), word & 0x3FF)      # the BCH remainder fits: nothing was written in the wrong place
        self.assertEqual((word >> 13) & 3, 0)      # level M

    def test_it_is_deterministic_and_refuses_a_text_that_does_not_fit(self):
        self.assertEqual(qrcode.matrix("abc"), qrcode.matrix("abc"))
        with self.assertRaises(ValueError):
            qrcode.matrix("x" * 300)

    def test_the_svg_is_dark_on_white_with_a_quiet_zone(self):
        svg = qrcode.svg("abc", label="a < b")
        self.assertIn('fill="#fff"', svg)
        self.assertTrue(svg.startswith("<svg"))


class Devices(unittest.TestCase):
    def tearDown(self):
        devices.close()
        for device in devices.list_devices():
            devices.revoke(device["id"])

    def setUp(self):
        _testenv.guard(self)
        devices.close()
        for device in devices.list_devices():
            devices.revoke(device["id"])

    def test_it_is_off_by_default_and_every_value_is_inside_its_range(self):
        self.assertFalse(devices.settings({})["enabled"])
        self.assertEqual(devices.settings({"pairing": {"enabled": True, "code_minutes": 999, "max_devices": 0, "device_days": -3}}),
                         {"enabled": True, "code_minutes": 5, "max_devices": 10, "device_days": 90})

    def test_a_code_works_once_and_a_new_code_cancels_the_old_one(self):
        first = devices.start(CFG)["code"]
        second = devices.start(CFG)["code"]
        self.assertEqual(devices.redeem(CFG, first)[1], "wrong")
        token, device = devices.redeem(CFG, second, "Mozilla/5.0 (Linux; Android 14)")
        self.assertTrue(token.startswith("dev_"))
        self.assertEqual(device["name"], "Android device")
        self.assertEqual(devices.redeem(CFG, second)[1], "closed")

    def test_a_wrong_guess_does_not_spend_the_open_code_but_an_expired_one_is_closed(self):
        code = devices.start(CFG, now=1000)["code"]
        self.assertEqual(devices.redeem(CFG, "AAAAAAAAAAAA", now=1001)[1], "wrong")
        self.assertTrue(devices.is_open(now=1002))
        self.assertEqual(devices.redeem(CFG, code, now=1000 + 5 * 60 + 1)[1], "closed")
        self.assertFalse(devices.is_open(now=1000 + 5 * 60 + 2))

    def test_only_the_hash_is_kept_and_a_revoked_device_stops_working_at_once(self):
        token, device = devices.redeem(CFG, devices.start(CFG)["code"])
        text = (Path(devices._path())).read_text(encoding="utf-8")
        self.assertNotIn(token, text)
        self.assertNotIn("token", text.replace("last_seen", ""))
        self.assertTrue(devices.valid(token, CFG))
        self.assertFalse(devices.valid(token + "x", CFG))
        self.assertFalse(devices.valid("msn_" + token[4:], CFG))
        self.assertTrue(devices.revoke(device["id"]))
        self.assertFalse(devices.valid(token, CFG))
        self.assertFalse(devices.revoke(device["id"]))

    def test_the_list_is_limited_and_a_device_expires(self):
        a = devices.redeem(CFG, devices.start(CFG)["code"])[0]
        devices.redeem(CFG, devices.start(CFG)["code"])
        self.assertEqual(devices.redeem(CFG, devices.start(CFG)["code"])[1], "full")
        self.assertTrue(devices.valid(a, CFG))
        self.assertFalse(devices.valid(a, CFG, now=time.time() + 91 * 86400))
        self.assertTrue(devices.valid(a, {**CFG, "device_days": 0}, now=time.time() + 400 * 86400))


class App(unittest.TestCase):
    def test_off_by_default_and_the_head_is_empty(self):
        self.assertEqual(pwa.settings({}), {"enabled": False, "refresh_on_return": True})
        self.assertEqual(pwa.head({"enabled": False}), "")
        self.assertIn('rel="manifest"', pwa.head({"enabled": True}))
        self.assertIn("use-credentials", pwa.head({"enabled": True}))

    def test_the_manifest_can_be_installed(self):
        m = pwa.manifest("es", "Monitor", "Acciones")
        self.assertEqual((m["display"], m["scope"], m["lang"]), ("standalone", "/", "es"))
        self.assertEqual(sorted(i["sizes"] for i in m["icons"]), ["192x192", "512x512"])

    def test_the_worker_keeps_the_offline_page_and_the_icons_and_never_the_data(self):
        text = pwa.service_worker("9.9.9")
        self.assertIn('"ghamon-9.9.9"', text)
        self.assertIn("/pwa/offline", text)
        self.assertNotIn("/api/", text)      # nothing of the API is touched, so nothing of the data is kept
        self.assertNotIn("cache.put", text)
        self.assertIn('r.method !== "GET"', text)

    def test_the_icon_is_a_real_png_of_the_size_asked(self):
        data = pwa.icon(192)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (192, 192))
        at = 8
        while at < len(data):
            length = struct.unpack(">I", data[at:at + 4])[0]
            kind, body = data[at + 4:at + 8], data[at + 8:at + 8 + length]
            self.assertEqual(struct.unpack(">I", data[at + 8 + length:at + 12 + length])[0], zlib.crc32(kind + body) & 0xFFFFFFFF)
            at += 12 + length
        self.assertEqual(at, len(data))

    def test_the_offline_page_escapes_its_text(self):
        page = pwa.offline_page("<b>x</b>", "a & b", "again", "en")
        self.assertNotIn("<b>x</b>", page)
        self.assertIn("a &amp; b", page)


class Settings(unittest.TestCase):
    def test_every_new_setting_has_a_default_a_place_and_its_words_in_the_eight_languages(self):
        keys = ("pwa.enabled", "pwa.refresh_on_return", "pairing.enabled", "pairing.code_minutes", "pairing.max_devices", "pairing.device_days", "ui.compact", "ui.palette")
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        for key in keys:
            self.assertIn(key, settings_api.META, key)
            node = example
            for part in key.split("."):
                node = node[part]
            for lang in LANGS:
                self.assertTrue(LOCALES[lang].get("cfg.f." + key) and LOCALES[lang].get("cfg.h." + key), (lang, key))
        self.assertIs(am.DEFAULTS["pwa"]["enabled"], False)
        self.assertIs(am.DEFAULTS["pairing"]["enabled"], False)
        self.assertEqual(am.DEFAULTS["ui"]["compact"], "auto")
        self.assertTrue(settings_api.META["pairing.enabled"]["secure"])      # decided from this computer only in the network mode

    def test_the_words_of_the_extras_exist_in_the_eight_languages(self):
        import re
        used = set(re.findall(r'"(ui\.(?:pair|pal|sc|pwa)_[a-z_]+)"', EXTRAS + PAGE + (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")))
        used.discard("ui.pair_err_")
        used |= {"ui.pair_err_" + k for k in ("closed", "wrong", "full", "locked", "off", "not_network")}
        for lang in LANGS:
            self.assertEqual([k for k in sorted(used) if not LOCALES[lang].get(k)], [], lang)

    def test_the_page_has_the_marker_the_extras_and_the_compact_rules(self):
        self.assertIn("/*EXTRAS_JS*/", PAGE)
        self.assertIn(":root.compact .shell", PAGE)
        self.assertIn("pointer:coarse", PAGE)
        self.assertIn("min-height:44px", PAGE)
        self.assertIn('"Escape"', EXTRAS)
        self.assertIn('role="listbox"', EXTRAS)
        self.assertNotIn("innerHTML=q", EXTRAS)


class Server(unittest.TestCase):
    """The real handler on an ephemeral port."""
    token = "t" * 24

    def start(self, config, network=True):
        self.guard = _testenv.guard(unittest.TestCase())
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "actions_monitor.json"
        self.file.write_text(json.dumps(config), encoding="utf-8")
        self.saved = (am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE, dict(am.LIVE_CONFIG), dict(localguard.STATE), settings_api.BACKUP_DIR)
        am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = self.file
        settings_api.BACKUP_DIR = Path(self.tmp.name) / "backups"
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, **config})
        toolconfig.forget()
        if network:
            localguard.configure(True, "127.0.0.1", self.token)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        devices.close()
        for device in devices.list_devices():
            devices.revoke(device["id"])

    def tearDown(self):
        if getattr(self, "server", None):
            self.server.shutdown()
            self.server.server_close()
            am.CONFIG_FILE, settings_api.CONFIG_FILE, toolconfig.CONFIG_FILE = self.saved[:3]
            am.LIVE_CONFIG.clear()
            am.LIVE_CONFIG.update(self.saved[3])
            localguard.STATE.clear()
            localguard.STATE.update(self.saved[4])
            settings_api.BACKUP_DIR = self.saved[5]
            toolconfig.forget()
            for device in devices.list_devices():
                devices.revoke(device["id"])
            self.tmp.cleanup()
            self.guard()

    def call(self, path, body=None, headers=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, method=method or ("GET" if body is None else "POST"), headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:
                raw = answer.read()
                return answer.status, raw, answer.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read(), error.headers

    def j(self, *args, **kwargs):
        status, raw, headers = self.call(*args, **kwargs)
        return status, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw.decode("utf-8", "replace")), headers

    def sensitive(self, path, body=None, headers=None):
        key = {"X-Monitor-Access": self.token, **(headers or {})}
        status, answer, _ = self.j("/api/session-token", headers=key)
        return self.j(path, body if body is not None else {}, {**key, "X-Monitor-Token": answer["token"]})

    def test_with_everything_off_there_is_no_app_and_no_pairing(self):
        self.start({})
        for path in ("/manifest.webmanifest", "/sw.js", "/pwa/offline", "/pwa/icon-192.png"):
            self.assertEqual(self.call(path, headers={"X-Monitor-Access": self.token})[0], 404, path)
        self.assertEqual(self.sensitive("/api/pair/start")[0], 404)
        self.assertEqual(self.call("/pair?c=ABC")[0], 404)
        status, page, _ = self.j("/", headers={"X-Monitor-Access": self.token})
        self.assertEqual(status, 200)
        self.assertNotIn('rel="manifest"', page)

    def test_with_the_switch_on_the_app_files_are_served_behind_the_access_token(self):
        self.start({"pwa": {"enabled": True}})
        self.assertEqual(self.call("/manifest.webmanifest")[0], 401)      # the access token is asked for as for every page
        key = {"X-Monitor-Access": self.token}
        status, manifest, headers = self.j("/manifest.webmanifest", headers=key)
        self.assertEqual(status, 200)
        self.assertIn("manifest+json", headers["Content-Type"])
        self.assertEqual(manifest["display"], "standalone")
        status, worker, headers = self.j("/sw.js", headers=key)
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertIn(am.TOOL_VERSION, worker)
        status, png, _ = self.call("/pwa/icon-512.png", headers=key)
        self.assertEqual((status, png[:4]), (200, b"\x89PNG"))
        status, offline, _ = self.j("/pwa/offline", headers=key)
        self.assertEqual(status, 200)
        self.assertIn("<button", offline)
        status, page, _ = self.j("/", headers=key)
        self.assertIn('rel="manifest"', page)
        self.assertIn("serviceWorker", page)

    def test_pairing_needs_its_switch_the_network_mode_and_the_one_use_token(self):
        self.start({"pairing": {"enabled": True}}, network=False)
        self.assertIn(self.j("/api/pair/start", {})[0], (403, 409))      # the network mode is off: nothing to pair with
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self.tearDown()
        self.start({"pairing": {"enabled": True}})
        key = {"X-Monitor-Access": self.token}
        self.assertEqual(self.j("/api/pair/start", {}, key)[0], 403)      # no one-use token
        status, started, _ = self.sensitive("/api/pair/start")
        self.assertEqual(status, 200)
        self.assertTrue(started["ok"] and started["svg"].startswith("<svg") and "/pair?c=" + started["code"] in started["url"])
        self.assertNotIn("127.0.0.1", started["url"])      # a phone cannot reach the loopback address: the address of the computer on the network is given

    def test_a_phone_pairs_with_the_code_and_then_goes_in_with_its_own_token_until_it_is_taken_away(self):
        self.start({"pairing": {"enabled": True}})
        key = {"X-Monitor-Access": self.token}
        code = self.sensitive("/api/pair/start")[1]["code"]
        status, page, _ = self.j("/pair?c=" + code)      # no access token: the code is the proof
        self.assertEqual(status, 200)
        self.assertIn('id="go"', page)
        self.assertEqual(self.j("/api/data")[0], 401)      # nothing else opens without a token
        status, _, _ = self.j("/api/pair/redeem", {"code": "WRONGWRONGWR"})
        self.assertEqual(status, 403)
        status, answer, headers = self.j("/api/pair/redeem", {"code": code})
        self.assertEqual(status, 200, answer)
        cookie = headers["Set-Cookie"]
        self.assertIn("monitor_access=dev_", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Max-Age=", cookie)
        token = cookie.split("monitor_access=")[1].split(";")[0]
        self.assertNotEqual(token, self.token)
        self.assertEqual(self.j("/api/pair/redeem", {"code": code})[0], 403)      # one use
        phone = {"Cookie": "monitor_access=" + token}
        self.assertEqual(self.j("/api/health", headers=phone)[0], 200)
        self.assertEqual(self.j("/api/data", headers=phone)[0], 200)
        status, listing, _ = self.j("/api/devices", headers=key)
        self.assertEqual(len(listing["devices"]), 1)
        self.assertNotIn("hash", json.dumps(listing))
        self.assertEqual(self.sensitive("/api/devices/revoke", {"id": "nope"})[0], 404)
        self.assertEqual(self.sensitive("/api/devices/revoke", {"id": listing["devices"][0]["id"]})[0], 200)
        self.assertEqual(self.j("/api/data", headers=phone)[0], 401)      # taken away: its token is dead, the access token of the monitor still works
        self.assertEqual(self.j("/api/health", headers=key)[0], 200)

    def test_pairing_switched_off_later_closes_the_paired_devices_too(self):
        self.start({"pairing": {"enabled": True}})
        code = self.sensitive("/api/pair/start")[1]["code"]
        token = self.j("/api/pair/redeem", {"code": code})[2]["Set-Cookie"].split("monitor_access=")[1].split(";")[0]
        phone = {"Cookie": "monitor_access=" + token}
        self.assertEqual(self.j("/api/data", headers=phone)[0], 200)
        am.LIVE_CONFIG["pairing"] = {"enabled": False}
        self.assertEqual(self.j("/api/data", headers=phone)[0], 401)

    def test_wrong_codes_count_against_the_address(self):
        self.start({"pairing": {"enabled": True, "max_devices": 5}})
        self.sensitive("/api/pair/start")
        localguard.reset_limits()
        seen = set()
        for _ in range(am.DEFAULTS["listen"]["max_failed_attempts"] + 3):
            seen.add(self.j("/api/pair/redeem", {"code": "WRONGWRONGWR"})[0])
        self.assertTrue(seen <= {403, 429})


if __name__ == "__main__":
    unittest.main()
