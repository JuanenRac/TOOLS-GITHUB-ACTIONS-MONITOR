# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.6: the connection between the monitor and an AI tool. The brief and the feed follow every refresh of the alert centre, a red run carries its diagnosis, alerts that fall together are
grouped, a read-only stream and three MCP tools push the news, a heartbeat tells the bar at the foot of the page whether an AI is connected, the gate script is installed with a command (merging
the settings of the tool, with a backup) and every state file of the monitor is created readable by its owner only. Everything runs offline, in temporary folders."""
import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor  # noqa: E402
import ai_alerts  # noqa: E402
import ai_hook  # noqa: E402
import ai_hook_install  # noqa: E402
import alert_center  # noqa: E402
import mcp_server  # noqa: E402
import monitor_cli  # noqa: E402
import private_io  # noqa: E402
import settings_api  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
NOW = 1_800_000_000
POSIX = os.name != "nt"


def row(repo="repo-a", workflow="CI", run=101, conclusion="failure", streak=1):
    return {"repo": repo, "workflow": workflow, "conclusion": conclusion, "since": "t", "streak": streak, "url": f"https://github.com/o/{repo}/actions/runs/{run}"}


def fake_runner(log="2026-01-01T00:00:00Z ok\n2026-01-01T00:00:01Z Error: boom at step\n", step="Run tests", calls=None):
    def run(args, timeout=60):
        if calls is not None:
            calls.append(args)
        if args[0] == "api":
            return 0, json.dumps({"jobs": [{"name": "build", "steps": [{"name": "Checkout", "conclusion": "success"}, {"name": step, "conclusion": "failure"}]}]}), ""
        return 0, "\n".join(f"build\t{step}\t{line}" for line in log.splitlines()), ""
    return run


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.config = {"ai_alerts": {"enabled": True, "folder": str(self.folder)}}
        ai_alerts._BEAT.clear()
        ai_alerts.STREAMS[0] = 0
        self.addCleanup(lambda: ai_alerts.STREAMS.__setitem__(0, 0))

    def cfg(self, **blocks):
        return {"ai_alerts": {"enabled": True, "folder": str(self.folder), **blocks}}


class BriefFollowsTheCentre(Folder):
    def test_the_brief_and_the_feed_are_rewritten_at_every_refresh_of_the_centre(self):
        data = {"repos": ["repo-a"], "runs": [{}], "offline": {"offline": False}}
        rows = [[row("repo-a")]]
        with mock.patch.object(actions_monitor, "STATE", {"data": data}), mock.patch.object(actions_monitor, "LITE", {"on": False}), \
                mock.patch.object(actions_monitor, "red_rows", side_effect=lambda d: rows[0]), mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=self.config):
            actions_monitor.FEED_SYNC["at"] = 0.0
            actions_monitor.refresh_feed(self.config, min_gap=0)
            first = ai_alerts.read_brief(self.config)
            self.assertIn("1 real alert(s) open", first)
            rows[0] = [row("repo-a"), row("repo-b")]       # the sentinel now sees a second red workflow: the very next refresh shows it, not one cycle later
            actions_monitor.refresh_feed(self.config, min_gap=0)
            self.assertIn("2 real alert(s) open", ai_alerts.read_brief(self.config))
            rows[0] = []
            actions_monitor.refresh_feed(self.config, min_gap=0)
            self.assertIn("0 real alert(s) open", ai_alerts.read_brief(self.config))

    def test_nothing_is_resolved_while_the_data_has_not_loaded(self):
        ai_alerts.update(self.config, [row()], now=NOW)
        for data in ({}, {"loading": True, "repos": ["x"]}, {"repos": ["x"], "offline": {"offline": True}}):
            with mock.patch.object(actions_monitor, "STATE", {"data": data}), mock.patch.object(actions_monitor, "LITE", {"on": False}):
                actions_monitor.FEED_SYNC["at"] = 0.0
                self.assertIsNone(actions_monitor.refresh_feed(self.config, min_gap=0))
        self.assertEqual(len(ai_alerts.alerts(self.config, states=("open",))), 1)

    def test_the_alerts_endpoint_and_the_feed_endpoints_refresh_the_feed(self):
        with mock.patch.object(actions_monitor, "refresh_feed") as refresh, mock.patch.object(actions_monitor, "SENTINEL", {"registry": None, "obj": None, "error": None}):
            actions_monitor.alerts_payload({})
        refresh.assert_called()
        page = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        for needle in ('refresh_feed()      # the bar polls every 30 seconds', "refresh_feed()\n            answer = advanced_get(path"):
            self.assertIn(needle, page.replace("\r\n", "\n"))

    def test_the_brief_says_when_it_was_written_and_how_old_it_is(self):
        ai_alerts.update(self.config, [row()], now=NOW)
        text = ai_alerts.read_brief(self.config)
        self.assertIn("Updated: ", text)
        self.assertRegex(text, r"(?m)^updated_epoch: \d+$")
        info = ai_alerts.brief_info(self.config, now=NOW + 90)
        self.assertEqual(info["age_seconds"], 90 + (NOW - info["updated"]))
        self.assertTrue(info["updated_local"])
        empty = ai_alerts.brief_info(self.cfg(folder=str(self.folder / "none")), now=NOW)
        self.assertIsNone(empty["updated"])


class Diagnosis(Folder):
    def test_relevant_lines_drop_stamps_colours_and_groups(self):
        log = "build\tRun\t2026-01-01T00:00:00Z ##[group]Run tests\nbuild\tRun\t2026-01-01T00:00:01Z \x1b[31mError: boom\x1b[0m\nbuild\tRun\t2026-01-01T00:00:02Z done\n"
        self.assertEqual(ai_alerts.relevant_lines(log, 10), ["Error: boom"])
        self.assertEqual(ai_alerts.relevant_lines("a\nb\nc\nd", 2), ["c", "d"], "without a marker the last lines")
        many = "\n".join(f"error {i}" for i in range(30))
        self.assertEqual(len(ai_alerts.relevant_lines(many, 10)), 10)

    def test_a_diagnosis_has_the_first_failing_step_and_is_cleaned_and_bounded(self):
        secret = "ghp_" + "a" * 30
        log = f"Error: token {secret} rejected for dev@example.com from 10.1.2.3\n" + "\n".join(f"Error: line {i} " + "x" * 150 for i in range(20))
        result = ai_alerts.diagnose("o", "repo-a", row()["url"], fake_runner(log), count=10, max_bytes=900)
        self.assertEqual(result["step"], "build: Run tests")
        text = json.dumps(result)
        for leaked in (secret, "dev@example.com", "10.1.2.3"):
            self.assertNotIn(leaked, text)
        self.assertLessEqual(len(text.encode("utf-8")), 900)
        self.assertEqual(result["run"], 101)

    def test_no_run_or_no_answer_is_told_apart(self):
        self.assertIsNone(ai_alerts.diagnose("o", "r", "https://example.com/none", fake_runner()))
        down = ai_alerts.diagnose("o", "r", row()["url"], lambda args, timeout=60: (1, "", "no"))
        self.assertEqual(down, {"run": 101, "unavailable": True})

    def test_it_is_off_by_default_and_reads_nothing_then(self):
        calls = []
        ai_alerts.update(self.config, [row()], now=NOW, runner=fake_runner(calls=calls), owner="o")
        self.assertEqual(calls, [])
        self.assertFalse(ai_alerts.settings({})["diagnose"]["enabled"])
        self.assertIsNone(ai_alerts.alerts(self.config)[0]["diagnosis"])

    def test_with_the_switch_on_each_new_run_is_read_once_within_the_budget(self):
        calls = []
        config = self.cfg(diagnose={"enabled": True, "max_per_cycle": 2})
        rows = [row(f"repo-{i}", run=200 + i) for i in range(4)]
        ai_alerts.update(config, rows, now=NOW, runner=fake_runner(calls=calls), owner="o")
        self.assertEqual(sum(1 for c in calls if c[0] == "api"), 2, "two runs per cycle")
        done = [a for a in ai_alerts.alerts(config) if a["diagnosis"]]
        self.assertEqual(len(done), 2)
        ai_alerts.update(config, rows, now=NOW + 60, runner=fake_runner(calls=calls), owner="o")
        self.assertEqual(len([a for a in ai_alerts.alerts(config) if a["diagnosis"]]), 4, "the next cycle reads the rest")
        before = len(calls)
        ai_alerts.update(config, rows, now=NOW + 120, runner=fake_runner(calls=calls), owner="o")
        self.assertEqual(len(calls), before, "a run already read is not read again")
        line = json.loads((self.folder / "ai_alerts.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertIn("diagnosis", line)

    def test_a_log_that_says_it_was_infrastructure_makes_the_alert_transient(self):
        config = self.cfg(diagnose={"enabled": True})
        ai_alerts.update(config, [row()], now=NOW, runner=fake_runner(log="HTTP 503 Service Unavailable"), owner="o")
        self.assertEqual(ai_alerts.alerts(config)[0]["class"], "transient")

    def test_the_brief_shows_the_failing_step(self):
        config = self.cfg(diagnose={"enabled": True})
        ai_alerts.update(config, [row()], now=NOW, runner=fake_runner(), owner="o")
        self.assertIn("Failing step: build: Run tests | Error: boom at step", ai_alerts.read_brief(config))


class Cascades(Folder):
    def test_a_rule_groups_the_clients_under_the_red_base(self):
        config = self.cfg(cascade={"map": {"base-repo": ["client-1", "client-2"]}})
        ai_alerts.update(config, [row("base-repo"), row("client-1"), row("client-2"), row("other")], now=NOW)
        by = {a["repo"]: a for a in ai_alerts.alerts(config)}
        self.assertIsNone(by["base-repo"]["origin"])
        self.assertEqual(by["client-1"]["origin"]["repo"], "base-repo")
        self.assertIsNone(by["other"]["origin"])
        text = ai_alerts.read_brief(config)
        self.assertIn("Also red because of it (fix this one first): client-1 / CI, client-2 / CI", text)
        self.assertNotIn("- [high/real] client-1", text, "a consequence is not listed on its own line")
        self.assertIn("in 2 independent group(s)", text)

    def test_a_log_that_names_the_base_repository_is_enough(self):
        config = self.cfg(diagnose={"enabled": True})
        runner = fake_runner(log="Error: could not fetch base-repo/.github/workflows/build.yml")
        ai_alerts.update(config, [row("base-repo", run=1), row("client-1", run=2)], now=NOW, runner=lambda a, t=60: (0, json.dumps({"jobs": []}), "") if a[0] == "api" else runner(a, t), owner="o")
        by = {a["repo"]: a for a in ai_alerts.alerts(config)}
        self.assertEqual(by["client-1"]["origin"]["repo"], "base-repo")

    def test_two_repositories_that_name_each_other_have_no_origin_and_it_can_be_turned_off(self):
        config = self.cfg(cascade={"map": {"a-repo": ["b-repo"], "b-repo": ["a-repo"]}})
        ai_alerts.update(config, [row("a-repo"), row("b-repo")], now=NOW)
        self.assertEqual([a["origin"] for a in ai_alerts.alerts(config)].count(None), 2, "two that name each other have no origin and nothing loops")
        off = self.cfg(cascade={"enabled": False, "map": {"base-repo": ["client-1"]}})
        ai_alerts.update(off, [row("base-repo"), row("client-1")], now=NOW + 10)
        self.assertTrue(all(a["origin"] is None for a in ai_alerts.alerts(off)))


class Heartbeat(Folder):
    def test_a_read_is_noted_and_the_bar_says_so_for_the_window(self):
        self.assertFalse(ai_alerts.presence(self.config, now=NOW)["connected"])
        self.assertTrue(ai_alerts.touch(self.config, "mcp", "some client", now=NOW))
        seen = ai_alerts.presence(self.config, now=NOW + 60)
        self.assertEqual((seen["connected"], seen["via"], seen["age_seconds"], seen["client"]), (True, "mcp", 60, "some client"))
        self.assertFalse(ai_alerts.presence(self.config, now=NOW + 16 * 60)["connected"], "15 minutes by default")
        self.assertTrue(ai_alerts.presence(self.cfg(heartbeat={"window_minutes": 30}), now=NOW + 16 * 60)["connected"])
        self.assertFalse(ai_alerts.touch(self.config, "mcp", now=NOW + 1), "not more than every 5 seconds")
        self.assertFalse(ai_alerts.touch(self.config, "not-a-way", now=NOW + 99))

    def test_it_can_be_turned_off_and_a_damaged_file_is_ignored(self):
        off = self.cfg(heartbeat={"enabled": False})
        self.assertFalse(ai_alerts.touch(off, "hook", now=NOW))
        self.assertFalse(ai_alerts.presence(off)["enabled"])
        (self.folder / "ai_heartbeat.json").write_text("{not json", encoding="utf-8")
        self.assertFalse(ai_alerts.presence(self.config, now=NOW)["connected"])

    def test_an_open_stream_counts_as_connected_and_the_statusbar_carries_it(self):
        ai_alerts.STREAMS[0] = 1
        self.assertTrue(ai_alerts.presence(self.config, now=NOW)["connected"])
        with mock.patch.object(actions_monitor, "LITE", {"on": False}), mock.patch.object(actions_monitor, "LIVE_CONFIG", self.config):
            self.assertTrue(actions_monitor.statusbar_payload(8765)["ai"]["connected"])
        with mock.patch.object(actions_monitor, "LITE", {"on": True}):
            self.assertIsNone(actions_monitor.statusbar_payload(8766)["ai"], "the lite edition has no feed")

    def test_the_page_shows_it_in_the_bar(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('id="sb-ai"', "ui.sb_ai_on", "ui.sb_ai_off", "ui.sb_ai_stream", "SBINFO.ai"):
            self.assertIn(needle, page, needle)


class Stream(Folder):
    def frames(self, config, **kw):
        clock = {"t": 0.0}

        def sleep(seconds):
            clock["t"] += seconds
        return ai_alerts.stream_frames(config, clock=lambda: clock["t"], sleep=sleep, **kw), clock

    def test_hello_then_the_new_events_then_bye(self):
        config = self.cfg(stream={"enabled": True, "max_seconds": 60})
        ai_alerts.update(config, [row("old")], now=NOW)
        gen, _clock = self.frames(config)
        hello = next(gen)
        self.assertTrue(hello.startswith("event: hello"))
        self.assertEqual(json.loads(hello.split("data: ")[1])["open_real"], 1)
        ai_alerts.update(config, [row("old"), row("new")], now=NOW + 5)
        alert = next(gen)
        self.assertIn("event: alert", alert)
        self.assertIn("id: ", alert)
        self.assertEqual(json.loads(alert.split("data: ")[1])["repo"], "new")
        frames = list(gen)
        self.assertTrue(frames[-1].startswith("event: bye"))
        self.assertTrue(any(f.startswith(": keepalive") for f in frames))

    def test_only_real_resume_and_cleaning(self):
        config = self.cfg(stream={"enabled": True, "max_seconds": 60})
        ai_alerts.update(config, [], now=NOW)
        gen, _ = self.frames(config, offset=0, only_real=True)
        next(gen)
        secret = "ghp_" + "b" * 30
        ai_alerts.update(config, [row("real"), dict(row("flaky", conclusion="startup_failure")), dict(row("leak"), url="https://x/runs/9?t=" + secret)], now=NOW + 5)
        text = "".join(list(gen))
        self.assertIn('"repo": "real"', text)
        self.assertNotIn('"repo": "flaky"', text, "only_real leaves the transient ones out")
        self.assertNotIn(secret, text)
        self.assertTrue(all(ord(c) < 128 for c in text), "plain ASCII frames")

    def test_listeners_are_limited_and_released(self):
        config = self.cfg(stream={"enabled": True, "max_clients": 2})
        self.assertTrue(ai_alerts.stream_acquire(config))
        self.assertTrue(ai_alerts.stream_acquire(config))
        self.assertFalse(ai_alerts.stream_acquire(config))
        ai_alerts.stream_release()
        self.assertTrue(ai_alerts.stream_acquire(config))
        self.assertFalse(ai_alerts.settings({})["stream"]["enabled"], "off by default")

    def test_a_truncated_feed_is_read_again_from_the_start_and_stop_ends_it(self):
        config = self.cfg(stream={"enabled": True, "max_seconds": 600})
        ai_alerts.update(config, [row("a")], now=NOW)
        stop = {"v": False}
        gen, _ = self.frames(config, stop=lambda: stop["v"])
        next(gen)
        (self.folder / "ai_alerts.jsonl").write_text(json.dumps({"at": 1, "event": "opened", "repo": "z", "class": "real"}) + "\n", encoding="utf-8")
        self.assertIn('"repo": "z"', next(gen))
        stop["v"] = True
        self.assertIn("stopped", list(gen)[-1])

    def _serve(self, config):
        server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        patches = [mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config), mock.patch.object(actions_monitor, "LITE", {"on": False})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_the_endpoint_is_off_by_default_limited_and_streams_events(self):
        base = self._serve(self.config)
        with self.assertRaises(urllib.error.HTTPError) as off:
            urllib.request.urlopen(base + "/api/ai/stream", timeout=10)
        self.assertEqual(off.exception.code, 404)
        config = self.cfg(stream={"enabled": True, "max_clients": 1})
        base = self._serve(config)
        ai_alerts.update(config, [], now=NOW)
        answer = urllib.request.urlopen(base + "/api/ai/stream", timeout=10)
        self.assertIn("text/event-stream", answer.headers["Content-Type"])
        self.assertTrue(answer.readline().decode().startswith("event: hello"))
        with self.assertRaises(urllib.error.HTTPError) as full:
            urllib.request.urlopen(base + "/api/ai/stream", timeout=10)
        self.assertEqual(full.exception.code, 429)
        ai_alerts.update(config, [row("pushed")], now=NOW + 5)
        seen = ""
        for _ in range(20):
            line = answer.readline().decode()
            seen += line
            if '"pushed"' in line:
                break
        self.assertIn('"repo": "pushed"', seen)
        answer.close()

    def test_the_lite_edition_does_not_have_the_stream(self):
        self.assertTrue(any("/api/ai/stream".startswith(p) for p in actions_monitor.LITE_PATHS))


class McpTools(Folder):
    def setUp(self):
        super().setUp()
        ai_alerts.update(self.cfg(cascade={"map": {"base": ["client"]}}), [row("base"), row("client")], now=NOW)
        self.config = self.cfg(cascade={"map": {"base": ["client"]}})

    def test_alerts_open_lists_the_alerts_with_age_and_origin(self):
        data = json.loads(mcp_server.call("alerts_open", {}, self.config))
        self.assertEqual({a["repo"] for a in data["alerts"]}, {"base", "client"})
        self.assertIsNotNone(data["updated"])
        self.assertEqual([a["repo"] for a in json.loads(mcp_server.call("alerts_open", {"only_real": True}, self.config))["alerts"]][0], "base")
        self.assertEqual([a for a in data["alerts"] if a["repo"] == "client"][0]["origin"]["repo"], "base")

    def test_alert_diagnose_returns_the_kept_one_or_reads_the_log_without_writing(self):
        ident = ai_alerts.alert_id("base", "CI")
        calls = []
        out = json.loads(mcp_server.call("alert_diagnose", {"id": ident}, self.config, runner=fake_runner(calls=calls)))
        self.assertEqual(out["diagnosis"]["step"], "build: Run tests")
        self.assertTrue(calls and all(c[0] in ("api", "run") for c in calls), "only read calls")
        with self.assertRaises(ValueError):
            mcp_server.call("alert_diagnose", {"id": "nothing"}, self.config)

    def test_alert_ack_needs_the_switch_and_only_changes_local_state(self):
        ident = ai_alerts.alert_id("base", "CI")
        with self.assertRaises(ValueError):
            mcp_server.call("alert_ack", {"id": ident}, self.config)
        names = {t["name"] for t in mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, self.config)["result"]["tools"]}
        self.assertIn("alerts_open", names)
        self.assertNotIn("alert_ack", names)
        names = {t["name"] for t in mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, self.config, True)["result"]["tools"]}
        self.assertIn("alert_ack", names)
        self.assertEqual(mcp_server.call("alert_ack", {"id": ident}, self.config, True), "acknowledged")

    def test_it_tells_the_ai_when_it_connects_and_notes_the_heartbeat(self):
        init = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "an AI assistant"}}}, self.config)
        self.assertIn("2 real CI alert(s) open", init["result"]["instructions"])
        self.assertIn("logging", init["result"]["capabilities"])
        note = mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, self.config)
        self.assertEqual(note["method"], "notifications/message")
        self.assertEqual(ai_alerts.presence(self.config)["via"], "mcp")
        quiet = self.cfg()
        quiet["ai_alerts"]["folder"] = str(self.folder / "empty")
        self.assertIsNone(mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, quiet))


class GateScript(Folder):
    def setUp(self):
        super().setUp()
        self.conf = self.folder / "actions_monitor.json"
        ai_alerts.update(self.config, [row()], now=NOW)

    def run_hook(self, event, payload=None, now=None, extra=None, env=None, block=False):
        self.conf.write_text(json.dumps({"ai_alerts": {"folder": str(self.folder), "client_hook": {"block_on_stop": block, **(extra or {})}}}), encoding="utf-8")
        return ai_hook.run([event, "--config", str(self.conf)], json.dumps(payload or {}), now=now if now is not None else NOW + 60, env=env or {})

    def test_session_start_and_prompt_inject_the_summary_in_plain_ascii(self):
        for event in ("SessionStart", "UserPromptSubmit"):
            out = self.run_hook(event)
            self.assertTrue(all(ord(c) < 128 for c in out))
            data = json.loads(out)["hookSpecificOutput"]
            self.assertEqual(data["hookEventName"], event)
            self.assertIn("1 real red alert(s) open", data["additionalContext"])
            self.assertIn("repo-a / CI", data["additionalContext"])
        self.assertTrue(ai_alerts.presence(self.config, now=NOW + 60)["via"] == "hook")

    def test_the_event_comes_from_the_payload_or_the_argument_and_other_events_say_nothing(self):
        self.assertTrue(self.run_hook("x", {"hook_event_name": "SessionStart"}))
        self.assertEqual(self.run_hook("PreToolUse"), "")

    def test_stop_asks_nothing_by_default_and_when_on_only_once_per_cooldown(self):
        self.assertEqual(self.run_hook("Stop"), "", "off by default")
        first = self.run_hook("Stop", block=True)
        self.assertEqual(json.loads(first)["decision"], "block")
        self.assertEqual(self.run_hook("Stop", block=True, now=NOW + 120), "", "inside the cooldown")
        self.assertTrue(self.run_hook("Stop", block=True, now=NOW + 60 + 21 * 60))
        self.assertEqual(self.run_hook("Stop", {"stop_hook_active": True}, block=True, now=NOW + 99999), "", "never while the tool retries")
        self.assertTrue(self.run_hook("Stop", block=True, now=NOW + 99999 + 21 * 60, extra={"cooldown_minutes": 1}))

    def test_nothing_to_say_without_real_alerts_without_a_brief_or_when_disabled(self):
        ai_alerts.update(self.config, [], now=NOW + 10)
        self.assertEqual(self.run_hook("SessionStart"), "")
        ai_alerts.update(self.config, [row()], now=NOW + 20)
        self.assertEqual(self.run_hook("SessionStart", extra={"enabled": False}), "")
        (self.folder / "ALERTS_BRIEF.md").unlink()
        self.assertEqual(self.run_hook("SessionStart"), "")

    def test_an_old_brief_is_warned_about_and_the_language_follows_the_environment(self):
        out = json.loads(self.run_hook("SessionStart", now=NOW + 5 * 3600))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Warning: the brief is 5 h old", out)
        spanish = json.loads(self.run_hook("SessionStart", env={"LANG": "es_ES.UTF-8"}))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("alerta(s) roja(s)", spanish)
        for lang in LANGS:
            self.assertEqual(set(ai_hook.TEXTS[lang]), set(ai_hook.TEXTS["en"]), lang)
            japanese = ai_hook.TEXTS[lang]["head"]
            self.assertTrue(all(ord(c) < 128 for c in json.dumps(japanese)))

    def test_cursor_and_generic_formats_and_a_script_that_never_raises(self):
        self.conf.write_text(json.dumps({"ai_alerts": {"folder": str(self.folder)}}), encoding="utf-8")
        cursor = json.loads(ai_hook.run(["sessionStart", "--format", "cursor", "--config", str(self.conf)], "{}", now=NOW + 5, env={}))
        self.assertIn("additional_context", cursor)
        generic = json.loads(ai_hook.run(["SessionStart", "--format", "generic", "--config", str(self.conf)], "{}", now=NOW + 5, env={}))
        self.assertIn("text", generic)
        with mock.patch.object(ai_hook, "run", side_effect=RuntimeError("boom")), mock.patch("sys.stdin", io.StringIO("")), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(ai_hook.main(["Stop"]), 0)
        self.assertEqual(out.getvalue(), "")
        for bad in ("", "[]", "{broken"):
            self.assertEqual(ai_hook.run(["Stop"], bad, now=NOW, env={}), "", "a payload that is not an object is no reason to fail")

    def test_the_script_needs_nothing_but_the_standard_library(self):
        tree = (HERE / "ai_hook.py").read_text(encoding="utf-8")
        imports = set(re.findall(r"^(?:import|from) (\w+)", tree, re.M))
        self.assertTrue(imports <= {"json", "os", "re", "sys", "time", "pathlib"}, imports)


class Installer(Folder):
    PY, SCRIPT = "C:/Python/python.exe", "C:/monitor/ai_hook.py"

    def put(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_assistant_project_install_merges_backs_up_and_is_idempotent(self):
        target = self.folder / ".claude" / "settings.local.json"
        foreign = {"permissions": {"allow": ["Bash(ls)"]}, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool stop"}]}], "PreToolUse": [{"matcher": "Bash", "hooks": []}]}}
        self.put(target, foreign)
        report = ai_hook_install.install("assistant", "project", str(self.folder), python=self.PY, script=self.SCRIPT, now=NOW)
        self.assertEqual(report["action"], "installed")
        self.assertTrue(report["backup"] and Path(report["backup"]).is_file())
        saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(saved["permissions"], foreign["permissions"])
        self.assertEqual(saved["hooks"]["PreToolUse"], foreign["hooks"]["PreToolUse"])
        stop = [h["command"] for g in saved["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(stop[0], "other-tool stop")
        self.assertIn('"C:/monitor/ai_hook.py" Stop --format assistant', stop[1])
        self.assertEqual(set(saved["hooks"]), {"SessionStart", "UserPromptSubmit", "Stop", "PreToolUse"})
        self.assertTrue(all(ord(c) < 128 for c in target.read_text(encoding="utf-8")), "plain ASCII JSON")
        again = ai_hook_install.install("assistant", "project", str(self.folder), python=self.PY, script=self.SCRIPT, now=NOW + 1)
        self.assertEqual((again["action"], again["backup"]), ("unchanged", None))
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), saved)

    def test_a_new_file_is_created_a_broken_one_is_refused_untouched(self):
        report = ai_hook_install.install("assistant", "project", str(self.folder), python=self.PY, script=self.SCRIPT)
        self.assertEqual((report["action"], report["backup"]), ("installed", None))
        broken = self.folder / "other" / ".claude" / "settings.local.json"
        broken.parent.mkdir(parents=True)
        broken.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ai_hook_install.InstallError):
            ai_hook_install.install("assistant", "project", str(broken.parent.parent), python=self.PY, script=self.SCRIPT)
        self.assertEqual(broken.read_text(encoding="utf-8"), "{not json")
        self.put(broken, ["a list"])
        with self.assertRaises(ai_hook_install.InstallError):
            ai_hook_install.install("assistant", "project", str(broken.parent.parent), python=self.PY, script=self.SCRIPT)
        self.put(broken, {"hooks": "nope"})
        with self.assertRaises(ai_hook_install.InstallError):
            ai_hook_install.install("assistant", "project", str(broken.parent.parent), python=self.PY, script=self.SCRIPT)

    def test_user_scope_uses_the_home_folder_and_uninstall_removes_only_ours(self):
        home = self.folder / "home"
        self.put(home / ".claude" / "settings.json", {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool stop"}]}]}})
        ai_hook_install.install("assistant", "user", home=str(home), python=self.PY, script=self.SCRIPT, now=NOW)
        removed = ai_hook_install.uninstall("assistant", "user", home=str(home), now=NOW + 5)
        self.assertEqual((removed["action"], sorted(removed["events"])), ("removed", ["SessionStart", "Stop", "UserPromptSubmit"]))
        left = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(left, {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool stop"}]}]}})
        self.assertEqual(ai_hook_install.uninstall("assistant", "user", home=str(home))["action"], "absent")
        self.assertEqual(ai_hook_install.uninstall("assistant", "project", str(self.folder / "nowhere"))["action"], "absent")

    def test_only_the_last_three_backups_stay(self):
        target = self.folder / ".claude" / "settings.local.json"
        self.put(target, {"a": 1})
        for i in range(6):
            ai_hook_install.install("assistant", "project", str(self.folder), python=self.PY, script=f"C:/m{i}/ai_hook.py", now=NOW + i * 10)
        self.assertEqual(len(list(target.parent.glob("settings.local.json.monitor-backup-*"))), 3)

    def test_cursor_generic_and_dry_run(self):
        report = ai_hook_install.install("cursor", "project", str(self.folder), python=self.PY, script=self.SCRIPT)
        saved = json.loads((self.folder / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual((saved["version"], sorted(saved["hooks"])), (1, ["sessionStart", "stop"]))
        self.assertEqual(report["events"], ["sessionStart", "stop"])
        generic = ai_hook_install.install("generic", python=self.PY, script=self.SCRIPT)
        self.assertEqual((generic["action"], generic["file"]), ("printed", None))
        self.assertEqual(len(generic["commands"]), 3)
        dry = ai_hook_install.install("assistant", "project", str(self.folder / "dry"), python=self.PY, script=self.SCRIPT, dry_run=True)
        self.assertEqual(dry["action"], "would_installed")
        self.assertFalse((self.folder / "dry").exists())

    def test_status_finds_what_is_installed_and_what_rules_it(self):
        self.assertFalse(ai_hook_install.status(str(self.folder), str(self.folder / "h"), {})["installed"])
        ai_hook_install.install("assistant", "project", str(self.folder), python=sys.executable, script=str(HERE / "ai_hook.py"))
        report = ai_hook_install.status(str(self.folder), str(self.folder / "h"), {})
        self.assertTrue(report["installed"])
        row_ = [r for r in report["targets"] if r["target"] == "assistant" and r["scope"] == "project"][0]
        self.assertEqual((row_["events"], row_["script_ok"]), (["SessionStart", "Stop", "UserPromptSubmit"], True))
        self.assertFalse(report["settings"]["block_on_stop"], "conservative default")
        self.assertTrue(report["script_present"])

    def test_the_command_line_installs_reports_json_in_ascii_and_fails_cleanly(self):
        argv = ["ai-hook", "install", "--assistant", "--scope", "project", "--project-dir", str(self.folder), "--json"]
        with redirect_stdout(io.StringIO()) as out:
            code = monitor_cli.main(argv)
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertTrue(all(ord(c) < 128 for c in text))
        self.assertEqual(json.loads(text)["data"]["action"], "installed")
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(monitor_cli.main(["ai-hook", "status", "--project-dir", str(self.folder), "--json"]), 0)
        self.assertTrue(json.loads(out.getvalue())["data"]["installed"])
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(monitor_cli.main(["ai-hook", "uninstall", "--project-dir", str(self.folder)]), 0)
        (self.folder / ".claude" / "settings.local.json").write_text("{x", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(monitor_cli.main(["ai-hook", "install", "--project-dir", str(self.folder)]), monitor_cli.EXIT_USAGE)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(monitor_cli.main(["ai-hook", "install", "--generic"]), 0)
        self.assertIn("ai_hook.py", out.getvalue())


class TokenInTheCommandLine(unittest.TestCase):
    def test_the_flag_warns_the_environment_wins_and_a_file_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token.txt"
            path.write_text("from-file\nignored\n", encoding="utf-8")
            if POSIX:
                os.chmod(path, 0o600)
            with redirect_stderr(io.StringIO()) as err:
                self.assertEqual(monitor_cli.resolve_token(env={}, flag="from-flag"), "from-flag")
            self.assertIn("--token-file", err.getvalue())
            with redirect_stderr(io.StringIO()) as err:
                self.assertEqual(monitor_cli.resolve_token(env={}, token_file=str(path)), "from-file")
                self.assertEqual(monitor_cli.resolve_token(env={"MONITOR_ACCESS_TOKEN": "from-env"}, flag="from-flag", token_file=str(path)), "from-env")
            self.assertEqual(err.getvalue(), "", "no warning for a private file or the variable")
            if POSIX:
                os.chmod(path, 0o644)
                with redirect_stderr(io.StringIO()) as err:
                    monitor_cli.resolve_token(env={}, token_file=str(path))
                self.assertIn("chmod 600", err.getvalue())
            with self.assertRaises(monitor_cli.CliError):
                monitor_cli.resolve_token(env={}, token_file=str(Path(tmp) / "missing"))
            path.write_text("\n", encoding="utf-8")
            with self.assertRaises(monitor_cli.CliError):
                monitor_cli.resolve_token(env={}, token_file=str(path))


class PrivateFiles(unittest.TestCase):
    def test_every_helper_asks_for_mode_0600_and_0700(self):
        modes = []
        real = os.open

        def spy(path, flags, mode=0o777, *a, **k):
            modes.append(mode)
            return real(path, flags, mode, *a, **k)
        with tempfile.TemporaryDirectory() as tmp, mock.patch("os.open", spy):
            base = Path(tmp)
            private_io.write_private(base / "a.json", "x")
            private_io.write_tmp(base / "b.tmp", b"y")
            with private_io.open_append(base / "c.jsonl") as handle:
                handle.write("z\n")
            self.assertEqual((base / "a.json").read_text(), "x")
            self.assertEqual((base / "c.jsonl").read_text(), "z\n")
            self.assertEqual(set(modes), {0o600})

    @unittest.skipIf(not POSIX, "Windows has no file modes: chmod only knows the read-only flag and folders inherit their parent's permissions")
    def test_with_a_lax_umask_every_state_file_stays_private(self):
        old = os.umask(0)
        self.addCleanup(os.umask, old)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = {"ai_alerts": {"enabled": True, "folder": str(base / "feed")}}
            ai_alerts.update(config, [row()], now=NOW)
            ai_alerts.touch(config, "hook", now=NOW)
            ai_alerts.ack(config, ai_alerts.alert_id("repo-a", "CI"), now=NOW)
            with mock.patch.object(alert_center, "STATE_FILE", base / "alert_mutes.json"):
                alert_center.mute("alert", "a1", 1, now=NOW)
            ai_hook_install.install("assistant", "project", str(base / "proj"), python="p", script="s")
            (base / "proj" / ".claude" / "settings.local.json").chmod(0o666)
            ai_hook_install.install("assistant", "project", str(base / "proj"), python="p", script="s2")
            ai_hook.private_write(base / "feed" / "ai_hook_state.json", "{}")
            private_io.private_dir(base / "d1" / "d2")
            files = [p for p in base.rglob("*") if p.is_file()]
            self.assertGreaterEqual(len(files), 8)
            for path in files:
                self.assertEqual(path.stat().st_mode & 0o077, 0, path.name)
            self.assertEqual((base / "feed").stat().st_mode & 0o077, 0)
            self.assertEqual((base / "d1" / "d2").stat().st_mode & 0o077, 0)

    def test_no_module_writes_a_state_file_with_a_plain_write(self):
        allowed = {"actions_monitor.py": 2, "release_candidates.py": 1, "release_notes.py": 1, "tui.py": 99, "demo_mode.py": 99, "make_release.py": 99, "private_io.py": 99}
        for path in sorted(HERE.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            found = len(re.findall(r"\.write_text\(|\.write_bytes\(|open\([^)]*, \"[aw]\"", text))
            self.assertLessEqual(found, allowed.get(path.name, 0), f"{path.name} writes a file without private_io")


class TheFeedIsOffByDefault(Folder):
    def test_a_new_installation_has_it_off_and_writes_nothing(self):
        config = {"ai_alerts": {"folder": str(self.folder)}}
        cfg = ai_alerts.settings(config)
        self.assertEqual((cfg["enabled"], cfg["legacy"]), (False, False))
        self.assertEqual(ai_alerts.update(config, [row()], now=NOW)["alerts"], [])
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertFalse(actions_monitor.DEFAULTS["ai_alerts"]["enabled"])

    def test_an_installation_that_already_had_the_feed_keeps_it_and_is_told(self):
        ai_alerts.update(self.config, [row()], now=NOW)       # the feed exists in the folder (it was on by default before)
        silent = {"ai_alerts": {"folder": str(self.folder)}}
        cfg = ai_alerts.settings(silent)
        self.assertEqual((cfg["enabled"], cfg["legacy"]), (True, True))
        self.assertTrue(ai_alerts.update(silent, [row()], now=NOW + 5)["alerts"])

    def test_what_the_person_wrote_always_wins(self):
        ai_alerts.update(self.config, [row()], now=NOW)
        off = {"ai_alerts": {"enabled": False, "folder": str(self.folder)}}
        self.assertEqual((ai_alerts.settings(off)["enabled"], ai_alerts.settings(off)["legacy"]), (False, False))
        on = {"ai_alerts": {"enabled": True, "folder": str(self.folder / "fresh")}}
        self.assertEqual((ai_alerts.settings(on)["enabled"], ai_alerts.settings(on)["legacy"]), (True, False))

    def test_the_notice_exists_in_each_language_and_the_template_agrees(self):
        for lang in LANGS:
            cat = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("ai_alerts.enabled", cat["mon.ai_feed_legacy"], lang)
        example = json.loads((HERE / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertIs(example["ai_alerts"].get("enabled"), False)


class SettingsAndTexts(unittest.TestCase):
    KEYS = [f"ai_alerts.{k}" for k in ("diagnose.enabled", "diagnose.max_per_cycle", "diagnose.log_lines", "diagnose.max_bytes", "cascade.enabled", "stream.enabled", "stream.max_seconds",
                                      "stream.max_clients", "heartbeat.enabled", "heartbeat.window_minutes", "client_hook.enabled", "client_hook.block_on_stop", "client_hook.cooldown_minutes",
                                      "client_hook.stale_hours", "client_hook.max_lines", "client_hook.max_chars")]

    def test_every_setting_is_in_the_tab_with_a_conservative_default_and_a_text_in_each_language(self):
        defaults = actions_monitor.DEFAULTS["ai_alerts"]
        self.assertEqual((defaults["diagnose"]["enabled"], defaults["stream"]["enabled"], defaults["client_hook"]["block_on_stop"]), (False, False, False))
        for key in self.KEYS:
            self.assertIn(key, settings_api.META, key)
            for lang in LANGS:
                cat = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
                self.assertTrue(cat.get("cfg.f." + key) and cat.get("cfg.h." + key), (lang, key))
        for key in ("diagnose.enabled", "stream.enabled", "client_hook.block_on_stop"):
            self.assertTrue(settings_api.META["ai_alerts." + key]["secure"], key)

    def test_bad_values_fall_back_to_the_defaults(self):
        cfg = ai_alerts.settings({"ai_alerts": {"diagnose": {"enabled": "yes", "max_per_cycle": 999, "log_lines": True}, "stream": {"max_clients": 0}, "cascade": {"map": {"a": "no", "b": ["c", 4]}},
                                                "heartbeat": {"window_minutes": "x"}, "client_hook": {"cooldown_minutes": -1}}})
        self.assertEqual((cfg["diagnose"]["enabled"], cfg["diagnose"]["max_per_cycle"], cfg["diagnose"]["log_lines"]), (False, 3, 10))
        self.assertEqual((cfg["stream"]["max_clients"], cfg["heartbeat"]["window_minutes"], cfg["client_hook"]["cooldown_minutes"]), (3, 15, 20))
        self.assertEqual(cfg["cascade"]["map"], {"b": ["c"]})

    def test_the_new_command_line_texts_exist_in_the_eight_languages(self):
        for lang in LANGS:
            cat = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for action in ("installed", "updated", "unchanged", "printed", "removed", "absent", "would_installed", "would_updated", "would_remove"):
                self.assertTrue(cat.get("cli.aih_" + action), (lang, action))
            for key in ("cli.token_flag_warn", "cli.help_token_file", "mon.network_first_steps", "ui.sb_ai_on", "ui.sb_ai_off", "ui.sb_ai_stream", "ui.sb_ai_t"):
                self.assertTrue(cat.get(key), (lang, key))
            self.assertIn("listen.query_access", cat["cfg.h.listen.network"], lang)

    def test_state_files_of_the_feed_are_never_committed_or_packaged(self):
        if (HERE.parent / ".gitignore").is_file():                  # not inside the zip
            ignored = (HERE.parent / ".gitignore").read_text(encoding="utf-8")
            for name in ("monitor/ai_alerts.jsonl", "monitor/ai_heartbeat.json", "monitor/ai_hook_state.json"):
                self.assertIn(name, ignored)
        packaging = (HERE / "make_release.py").read_text(encoding="utf-8")
        for name in ("ai_alerts.jsonl", "ai_heartbeat.json", "ai_hook_state.json"):
            self.assertIn(f'"{name}"', packaging)


if __name__ == "__main__":
    unittest.main()
