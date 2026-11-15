# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The ports of the two editions are settings (`ports.complete`, `ports.lite`): one rule says which port an edition uses and the start, the doctor, the health check, the command line, the service and the
launchers follow it.

1. The order is --port, then MONITOR_PORT (complete only), then the file of the edition, then the file of the other edition, then the default; a wrong number is ignored.
2. The lite edition never takes the port of the complete one, and the Settings page refuses the same number for both.
3. The real programs read it: the doctor (a process), the health check against a server on the configured port, and the demo, which listens where the file says.
Every port is asked from the system (a free one), never a fixed number; the files live in a temporary folder."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.cli import doctor, healthcheck, monitor_cli  # noqa: E402
from github_actions_monitor.integrations import monitor_link  # noqa: E402
from github_actions_monitor.util import ports  # noqa: E402


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def two_free_ports():
    first = free_port()
    second = free_port()
    while second == first:
        second = free_port()
    return first, second


class TheRule(unittest.TestCase):
    def test_the_defaults_are_the_ones_it_always_had(self):
        self.assertEqual(ports.DEFAULTS, {"complete": 8765, "lite": 8766})
        self.assertEqual(ports.both(env={}, configs={}), {"complete": 8765, "lite": 8766})
        self.assertEqual(am.DEFAULTS["ports"], ports.DEFAULTS)
        self.assertEqual(monitor_cli.PORTS, ports.DEFAULTS)

    def test_the_file_of_the_edition_sets_its_port(self):
        a, b = two_free_ports()
        configs = {"complete": {"ports": {"complete": a}}, "lite": {"ports": {"lite": b}}}
        self.assertEqual(ports.both(env={}, configs=configs), {"complete": a, "lite": b})

    def test_one_menu_can_set_both_and_the_own_file_wins_when_it_says_something(self):
        a, b = two_free_ports()
        self.assertEqual(ports.both(env={}, configs={"complete": {"ports": {"complete": a, "lite": b}}, "lite": {}}), {"complete": a, "lite": b})
        c = free_port()
        mixed = {"complete": {"ports": {"complete": a, "lite": b}}, "lite": {"ports": {"lite": c}}}
        self.assertEqual(ports.resolve("lite", env={}, configs=mixed), c)

    def test_the_command_line_wins_then_the_service_variable_for_the_complete_edition_only(self):
        a, b, c = free_port(), free_port(), free_port()
        configs = {"complete": {"ports": {"complete": a}}}
        self.assertEqual(ports.resolve("complete", env={"MONITOR_PORT": str(b)}, configs=configs), b)
        self.assertEqual(ports.resolve("complete", flag=c, env={"MONITOR_PORT": str(b)}, configs=configs), c)
        self.assertEqual(ports.resolve("lite", env={"MONITOR_PORT": str(b)}, configs={}), 8766, "the variable of the service is the port of the complete edition")
        self.assertEqual(ports.from_argv(["--no-browser", "--port", str(c)], "complete", env={}, configs=configs), c)
        self.assertEqual(ports.from_argv(["--port", "x"], "complete", env={}, configs=configs), a)
        self.assertEqual(ports.from_argv([], "lite", env={}, configs=configs), 8766)

    def test_a_wrong_number_is_ignored_never_half_used(self):
        for wrong in ("8765", 80, 1023, 65536, 70000, 8.5, True, None, [], {}, -1):
            self.assertEqual(ports.resolve("complete", env={}, configs={"complete": {"ports": {"complete": wrong}}}), 8765, wrong)
        for text in ("", "abc", "80", "99999", " "):
            self.assertEqual(ports.resolve("complete", env={"MONITOR_PORT": text}, configs={}), 8765, text)
        for broken in (None, [], "x", {"ports": 3}, {"ports": []}):
            self.assertEqual(ports.resolve("lite", env={}, configs={"lite": broken, "complete": broken}), 8766)
        with self.assertRaises(ValueError):
            ports.resolve("other")

    def test_the_lite_edition_never_takes_the_port_of_the_complete_one(self):
        a = free_port()
        same = {"complete": {"ports": {"complete": a}}, "lite": {"ports": {"lite": a}}}
        self.assertEqual(ports.resolve("complete", env={}, configs=same), a)
        self.assertEqual(ports.resolve("lite", env={}, configs=same), 8766)
        self.assertEqual(ports.resolve("lite", env={}, configs={"complete": {"ports": {"complete": 8766}}}), 8767, "the complete edition took the default of the lite one")
        self.assertEqual(ports.resolve("lite", flag=a, env={}, configs=same), a, "what a person types is not second-guessed")

    def test_the_files_are_read_from_the_configuration_folder_and_a_damaged_one_is_empty(self):
        a, b = two_free_ports()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"MONITOR_CONFIG_DIR": tmp}), mock.patch.dict(os.environ, {"MONITOR_CONFIG": ""}):
            Path(tmp, "actions_monitor.json").write_text(json.dumps({"ports": {"complete": a}}), encoding="utf-8")
            Path(tmp, "actions_monitor_lite.json").write_text(json.dumps({"ports": {"lite": b}}), encoding="utf-8")
            self.assertEqual(ports.both(env={}), {"complete": a, "lite": b})
            Path(tmp, "actions_monitor.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(ports.both(env={}), {"complete": 8765, "lite": b})
            Path(tmp, "actions_monitor_lite.json").unlink()
            self.assertEqual(ports.both(env={}), ports.DEFAULTS)


class TheSettings(unittest.TestCase):
    def test_both_are_whole_ports_in_the_menu_of_the_two_editions(self):
        for key in ("ports.complete", "ports.lite"):
            self.assertEqual(settings_api.FIELDS[key][2], "int")
            self.assertIn(key, settings_api.LITE_KEYS)
            self.assertEqual(settings_api.check_value(key, 9000), (True, 9000))
            for bad in (80, 1023, 65536, "8765", 1.5, None, True):
                self.assertFalse(settings_api.check_value(key, bad)[0], (key, bad))

    def test_the_same_number_for_both_is_refused_and_two_different_ones_are_saved(self):
        a, b = two_free_ports()
        self.assertEqual(settings_api.validate({"ports.complete": a, "ports.lite": b}), ({"ports.complete": a, "ports.lite": b}, {}))
        clean, errors = settings_api.validate({"ports.complete": a, "ports.lite": a})
        self.assertEqual((clean, errors), ({}, {"ports.lite": "same_port"}))
        self.assertEqual(settings_api.validate({"ports.lite": a}, lite=True)[0], {"ports.lite": a})

    def test_the_texts_are_in_the_eight_languages(self):
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.cfg_b_ports", "ui.cfg_err_same_port", "cfg.f.ports.complete", "cfg.f.ports.lite", "cfg.h.ports.complete", "cfg.h.ports.lite"):
                self.assertTrue(catalogue.get(key), (lang, key))

    def test_the_guide_and_the_advanced_list_name_both_settings_in_the_eight_languages(self):
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"DEPLOYMENT{tail}.md").read_text(encoding="utf-8")
            for needle in ("`ports.complete`", "`ports.lite`", "MONITOR_PORT", "--port N"):
                self.assertIn(needle, text, (tail, needle))
            self.assertIn("`ports.lite`", (HERE / "docs" / f"ADVANCED{tail}.md").read_text(encoding="utf-8"), tail)


class TheProgramsFollowIt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.complete, self.lite = two_free_ports()
        Path(self.tmp.name, "actions_monitor.json").write_text(json.dumps({"ports": {"complete": self.complete, "lite": self.lite}}), encoding="utf-8")
        patcher = mock.patch.dict(os.environ, {"MONITOR_CONFIG_DIR": self.tmp.name, "MONITOR_CONFIG": ""})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("MONITOR_PORT", None)
        os.environ.pop("MONITOR_URL", None)

    def test_the_command_line_talks_to_the_port_of_each_edition(self):
        self.assertEqual(monitor_cli.base_url(None, lite=False, env={}), f"http://127.0.0.1:{self.complete}")
        self.assertEqual(monitor_cli.base_url(None, lite=True, env={}), f"http://127.0.0.1:{self.lite}")
        self.assertEqual(monitor_cli.base_url("example.org:9", env={}), "http://example.org:9")

    def test_the_tool_that_tells_the_monitor_about_a_signed_release_looks_from_the_port_of_the_file(self):
        self.assertEqual(list(monitor_link.candidates()), list(range(self.complete, self.complete + 10)))
        asked = []

        def opener(request, timeout=0):
            asked.append(request.full_url)
            raise OSError("nobody here")
        self.assertIsNone(monitor_link.notify_refresh(["repo"], opener=opener))
        self.assertEqual(asked[0], f"http://127.0.0.1:{self.complete}/api/refresh-repos")

    def test_the_doctor_reports_the_ports_of_the_file(self):
        def runner(command):
            return 1, "", ""
        checks = doctor.run(runner=runner, config={})
        port = next(c for c in checks if c["id"] == "port")
        self.assertIn(str(self.complete), port["detail"])
        self.assertIn(str(self.lite), port["detail"])
        self.assertNotIn("8765", port["detail"])

    def test_the_health_check_asks_the_configured_port(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = json.dumps({"ok": True, "version": "test"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        server = ThreadingHTTPServer(("127.0.0.1", self.complete), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.assertEqual(healthcheck.main(["--timeout", "5"]), healthcheck.EXIT_OK)
        os.environ["MONITOR_PORT"] = str(free_port())
        self.assertEqual(healthcheck.main(["--timeout", "1"]), healthcheck.EXIT_DOWN, "MONITOR_PORT of the service wins over the file")

    def test_the_service_starts_the_monitor_on_the_port_of_the_file(self):
        from github_actions_monitor import service
        seen = {}
        with mock.patch.object(service, "prepare", return_value=0), mock.patch.object(service.paths, "ensure"), mock.patch.object(service.rootmigrate, "auto"), mock.patch.object(am, "main", side_effect=lambda: seen.setdefault("argv", list(sys.argv)) and 0), \
                mock.patch.object(sys, "argv", ["service"]):
            service.main([])
        self.assertEqual(seen["argv"][seen["argv"].index("--port") + 1], str(self.complete))


@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "starts a process: runs on your computer (or with MONITOR_BROWSER_TESTS=1)")
class TheRealStart(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.complete, self.lite = two_free_ports()
        Path(self.tmp.name, "actions_monitor.json").write_text(json.dumps({"ports": {"complete": self.complete, "lite": self.lite}}), encoding="utf-8")
        self.env = {**os.environ, "MONITOR_CONFIG_DIR": self.tmp.name, "MONITOR_DATA_DIR": str(Path(self.tmp.name, "data")), "PYTHONPATH": str(HERE / "src"), "PYTHONUTF8": "1"}
        for name in ("MONITOR_PORT", "MONITOR_CONFIG", "MONITOR_URL", "MONITOR_MODE"):
            self.env.pop(name, None)

    def run_main(self, *args):
        return subprocess.run([sys.executable, "-m", "github_actions_monitor", *args], capture_output=True, text=True, env=self.env, timeout=120, check=False)

    def test_the_doctor_of_a_real_start_names_the_ports_of_the_file(self):
        answer = self.run_main("--doctor", "--json", "--lang", "en")
        rows = json.loads(answer.stdout)
        detail = next(c for c in (rows["checks"] if isinstance(rows, dict) else rows) if c["id"] == "port")["detail"]
        self.assertIn(str(self.complete), detail)
        self.assertIn(str(self.lite), detail)

    def test_the_demo_listens_where_the_file_says_and_the_flag_wins(self):
        child = subprocess.Popen([sys.executable, "-m", "github_actions_monitor", "--demo", "--no-browser", "--lang", "en"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self.env)
        self.addCleanup(child.kill)
        self.assertTrue(self.listens(self.complete, child), "the demo did not listen on ports.complete")
        other = free_port()
        second = subprocess.Popen([sys.executable, "-m", "github_actions_monitor", "--demo", "--no-browser", "--port", str(other), "--lang", "en"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self.env)
        self.addCleanup(second.kill)
        self.assertTrue(self.listens(other, second), "--port did not win over the file")

    @staticmethod
    def listens(port, child, tries=300):
        for _ in range(tries):
            if child.poll() is not None:
                return False
            try:
                socket.create_connection(("127.0.0.1", port), 0.5).close()
                return True
            except OSError:
                time.sleep(0.1)
        return False


if __name__ == "__main__":
    unittest.main()
