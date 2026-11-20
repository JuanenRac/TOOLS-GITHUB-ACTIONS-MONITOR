# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The table of the network destinations (what the monitor can call, what fails if it is blocked) agrees with the code, and the sinks towards a SIEM are off by default, build the request each destination
takes, filter, keep a bounded queue, keep their secret out of the file and out of the errors, and do nothing in the offline mode."""
import base64
import io
import json
import re
import sys
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.integrations import siem  # noqa: E402
from github_actions_monitor.ops import egress  # noqa: E402


class Egress(unittest.TestCase):
    def test_a_plain_configuration_calls_github_and_the_updates_and_nothing_else(self):
        rows = {r["id"]: r for r in egress.table({})}
        self.assertTrue(rows["github_api"]["active"])
        self.assertTrue(rows["github_download"]["active"])
        for off in ("github_raw", "ntfy", "telegram", "chat_webhooks", "ai", "otlp", "siem"):
            self.assertFalse(rows[off]["active"], off)

    def test_what_is_switched_on_adds_its_hosts_and_the_offline_mode_removes_them_all(self):
        cfg = {"notify": {"channels": {"ntfy": {"enabled": True}}}, "ai": {"provider": "anthropic"}, "otlp": {"enabled": True, "endpoint": "https://otel.example.org:4318"},
               "lint": {"anonymous_public": True}, "updates": {"check": False},
               "siem": {"sinks": [{"type": "http", "enabled": True, "url": "https://siem.example.org/in"}]}}
        rows = {r["id"]: r for r in egress.table(cfg)}
        self.assertEqual([r for r in ("ntfy", "ai", "otlp", "github_raw", "siem") if rows[r]["active"]], ["ntfy", "ai", "otlp", "github_raw", "siem"])
        self.assertEqual(rows["ai"]["hosts"], ["api.anthropic.com"])
        self.assertEqual(rows["otlp"]["hosts"], ["otel.example.org"])
        self.assertEqual(rows["siem"]["hosts"], ["siem.example.org"])
        self.assertFalse(rows["github_download"]["active"])      # updates.check off
        self.assertFalse(any(r["active"] for r in egress.table(dict(cfg, airgapped=True))))

    def test_a_local_model_and_a_receiver_on_this_network_are_not_outside_hosts(self):
        rows = {r["id"]: r for r in egress.table({"ai": {"provider": "ollama", "base_url": "http://127.0.0.1:11434"}, "otlp": {"enabled": True, "endpoint": "http://192.168.1.5:4318"}})}
        self.assertFalse(rows["ai"]["active"])
        self.assertEqual(rows["otlp"]["hosts"], [])

    def test_the_table_does_not_lie_every_host_the_code_names_has_a_row_or_is_only_a_link(self):
        known = {h for row in egress.ROWS for h in row[1]} | egress.LINK_ONLY | egress.DYNAMIC_HOSTS
        presets = (HERE / "src" / "github_actions_monitor" / "sentinels" / "ai_presets.json").read_text(encoding="utf-8")
        known |= set(re.findall(r"https?://([A-Za-z0-9.-]+\.[a-z]{2,})", presets))
        missing = {}
        for path in (HERE / "src").rglob("*.py"):
            if path.name in ("egress.py",):
                continue
            for host in egress.HOST_RE.findall(path.read_text(encoding="utf-8")):
                if host not in known and not host.endswith((".invalid", ".example", ".org.example")) and not any(host.endswith("." + k) for k in known):
                    missing.setdefault(host, path.name)
        self.assertEqual(missing, {}, "a host the code names has no row in ops/egress.py")

    def test_every_row_says_what_it_is_for_and_what_fails_in_the_eight_languages(self):
        for row_id, _hosts, _rule in egress.ROWS:
            for lang in i18n.LANGS:
                for kind in ("use", "fail"):
                    key = f"egress.{kind}.{row_id}"
                    self.assertNotEqual(i18n.tl(lang, key), key, (key, lang))

    def test_the_text_for_the_console_names_the_hosts_and_the_setting(self):
        text = "\n".join(egress.lines({}, lambda key, **kw: i18n.tl("en", key).format(**kw) if kw else i18n.tl("en", key)))
        self.assertIn("api.github.com", text)
        self.assertIn("ntfy.sh", text)
        self.assertIn("notify.channels.ntfy.enabled", text)


class Command(unittest.TestCase):
    def test_doctor_egress_prints_the_table_without_running_a_single_check(self):
        import contextlib
        from github_actions_monitor.cli import monitor_cli
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = monitor_cli.main(["doctor", "--egress", "--json", "--lang", "en"])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())["data"]
        self.assertEqual([r["id"] for r in data["egress"]], [row[0] for row in egress.ROWS])
        text = io.StringIO()
        with contextlib.redirect_stdout(text):
            monitor_cli.main(["doctor", "--egress", "--lang", "es"])
        self.assertIn("api.github.com", text.getvalue())
        self.assertIn("Si se bloquea", text.getvalue())


class Sinks(unittest.TestCase):
    def setUp(self):
        siem.QUEUE.clear()
        siem.STATUS.update(sent=0, failed=0, dropped=0, last_error="")

    EVENT = {"kind": "red_new", "code": "ci.red", "level": "bad", "repo": "a/x", "text": "boom", "url": "https://github.com/a/x/actions/runs/1", "owner": "main", "token": "ghp_SECRET",
             "at": "2999-01-01T00:00:00Z"}

    def sink(self, **over):
        sink = dict(siem.DEFAULT_SINK, enabled=True, url="https://siem.example.org")
        sink.update(over)
        return sink

    def test_it_is_off_by_default_everywhere(self):
        self.assertEqual(actions_monitor.DEFAULTS["siem"], {"queue_max": 500, "sinks": []})
        self.assertEqual(siem.enqueue({}, [self.EVENT]), 0)
        self.assertEqual(siem.enqueue({"siem": {"sinks": [{"type": "http", "url": "https://x.example.org"}]}}, [self.EVENT]), 0)      # not enabled
        self.assertEqual(siem.QUEUE, [])
        self.assertIn("siem.queue_max", settings_api.FIELDS)

    def test_a_malformed_sink_is_left_out_and_the_secret_can_only_be_a_name(self):
        cfg = siem.settings({"siem": {"sinks": [{"type": "nope", "url": "https://a.org"}, {"type": "http", "url": "ftp://a.org"}, {"type": "loki", "url": "https://l.org", "token_env": "bad name; rm", "enabled": True},
                                                {"type": "loki", "url": "https://l.org", "token_env": "LOKI_TOKEN", "enabled": True, "from_minutes": 99999}]}})
        self.assertEqual(len(cfg["sinks"]), 2)
        self.assertEqual(cfg["sinks"][0]["token_env"], "")
        self.assertEqual((cfg["sinks"][1]["token_env"], cfg["sinks"][1]["from_minutes"]), ("LOKI_TOKEN", 5))

    def test_the_event_has_a_closed_list_of_fields(self):
        row = siem.shape(self.EVENT)
        self.assertNotIn("token", row)
        self.assertEqual(row["source"], "github-actions-monitor")
        self.assertEqual(len(siem.shape({"kind": "k", "text": "x" * 5000})["text"]), 500)

    def test_each_destination_gets_the_request_it_takes(self):
        rows = [siem.shape(self.EVENT)]
        url, headers, body = siem.request_for(self.sink(type="elasticsearch", index="gha"), rows, "KEY")
        self.assertEqual((url, headers["Authorization"]), ("https://siem.example.org/_bulk", "ApiKey KEY"))
        lines = body.decode().splitlines()
        self.assertEqual(json.loads(lines[0]), {"index": {"_index": "gha"}})
        self.assertEqual(json.loads(lines[1])["code"], "ci.red")
        url, headers, body = siem.request_for(self.sink(type="splunk_hec"), rows, "TOK", now=5)
        self.assertEqual((url, headers["Authorization"]), ("https://siem.example.org/services/collector/event", "Splunk TOK"))
        self.assertEqual(json.loads(body)["event"]["repo"], "a/x")
        url, headers, body = siem.request_for(self.sink(type="loki"), rows, "", now=5)
        self.assertEqual(url, "https://siem.example.org/loki/api/v1/push")
        doc = json.loads(body)
        self.assertEqual(doc["streams"][0]["stream"], {"job": "github-actions-monitor", "level": "bad"})
        self.assertEqual(json.loads(doc["streams"][0]["values"][0][1])["code"], "ci.red")
        key = base64.b64encode(b"k" * 32).decode()
        url, headers, body = siem.request_for(self.sink(type="sentinel", workspace_id="WS1", log_type="Gha"), rows, key, now=0)
        self.assertEqual((headers["Log-Type"], headers["x-ms-date"]), ("Gha", "Thu, 01 Jan 1970 00:00:00 GMT"))
        self.assertTrue(headers["Authorization"].startswith("SharedKey WS1:"))
        self.assertTrue(url.endswith("/api/logs?api-version=2016-04-01"))
        url, headers, body = siem.request_for(self.sink(type="bigquery", url="https://bq.example.org/insertAll"), rows, "T")
        self.assertEqual((url, headers["Authorization"], json.loads(body)["rows"][0]["json"]["kind"]), ("https://bq.example.org/insertAll", "Bearer T", "red_new"))
        url, headers, body = siem.request_for(self.sink(type="http"), rows, "")
        self.assertNotIn("Authorization", headers)
        self.assertEqual(json.loads(body.decode().splitlines()[0])["repo"], "a/x")

    def test_the_filters_of_the_sink(self):
        old = dict(self.EVENT, at="2000-01-01T00:00:00Z")
        self.assertTrue(siem.wanted(self.sink(), self.EVENT))
        self.assertFalse(siem.wanted(self.sink(), old), "older than from_minutes")
        self.assertFalse(siem.wanted(self.sink(levels=["warn"]), self.EVENT))
        self.assertTrue(siem.wanted(self.sink(repos_filter=["a/*"]), self.EVENT))
        self.assertFalse(siem.wanted(self.sink(repos_filter=["b/*"]), self.EVENT))

    def test_the_queue_is_bounded_and_a_failed_send_keeps_the_events_and_never_the_secret(self):
        config = {"siem": {"queue_max": 10, "sinks": [{"type": "http", "enabled": True, "url": "https://siem.example.org/in", "token_env": "SIEM_TOKEN"}]}}
        events = [dict(self.EVENT, code=f"c{i}") for i in range(14)]
        self.assertEqual(siem.enqueue(config, events), 14)
        self.assertEqual((len(siem.QUEUE), siem.STATUS["dropped"]), (10, 4))
        self.assertEqual(siem.QUEUE[0]["code"], "c4")      # the oldest went first

        def down(request, allow_private):
            raise OSError("connection refused with SIEM-SECRET-VALUE")
        self.assertEqual(siem.flush(config, post=down, env={"SIEM_TOKEN": "SIEM-SECRET-VALUE"}), 0)
        self.assertEqual(len(siem.QUEUE), 10)
        self.assertEqual(siem.STATUS["failed"], 1)
        self.assertNotIn("SIEM-SECRET-VALUE", siem.STATUS["last_error"])
        seen = []

        def up(request, allow_private):
            seen.append(request)
            return 200
        self.assertEqual(siem.flush(config, post=up, env={"SIEM_TOKEN": "SIEM-SECRET-VALUE"}), 1)
        self.assertEqual((siem.QUEUE, siem.STATUS["sent"]), ([], 10))
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer SIEM-SECRET-VALUE")
        self.assertIsInstance(seen[0], urllib.request.Request)

    def test_nothing_is_queued_in_the_offline_mode(self):
        config = {"airgapped": True, "siem": {"sinks": [{"type": "http", "enabled": True, "url": "https://siem.example.org"}]}}
        self.assertEqual(siem.enqueue(config, [self.EVENT]), 0)

    def test_a_private_receiver_is_refused_by_the_network_rules_unless_the_sink_allows_it(self):
        from github_actions_monitor.security import netguard
        with self.assertRaises(OSError):      # Refused is an OSError; urllib may wrap it in a URLError (also an OSError)
            siem._post(urllib.request.Request("http://127.0.0.1:9/in", data=b"{}", method="POST"), False)


if __name__ == "__main__":
    unittest.main()
