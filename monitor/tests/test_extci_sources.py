# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The external CI sources against fake servers of this computer: what every service says becomes runs, the red follows the rule of Actions, a service that fails is degraded and never red, the reads
are safe (no private address by default, no redirect, limits), the logs are bounded, clean and redacted, and nothing happens while the feature is off. No request leaves this computer."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))

import _testenv  # noqa: F401,E402
import extci_fake_servers as fake  # noqa: E402
from github_actions_monitor import families  # noqa: E402
from github_actions_monitor.integrations.external_ci import extci_engine as engine  # noqa: E402
from github_actions_monitor.integrations.external_ci.extci_fetch import Failed, Reader  # noqa: E402
from github_actions_monitor.sentinels import alert_center  # noqa: E402


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = fake.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        engine.forget()
        self.addCleanup(engine.forget)
        del self.server.seen[:]

    def config(self, lines=None, **extra):
        block = {"enabled": True, "sources": fake.sources(self.base) if lines is None else lines, "allow_private_targets": True, "jenkins": {"enabled": True}, "azure": {"enabled": True}}
        block.update(extra)
        return {"external_ci": block}


class Reading(Base):
    def test_every_service_gives_its_red_and_unknown_states_do_not_decide(self):
        config = self.config()
        self.assertEqual(engine.refresh(config, now=1000.0), 4)
        rows = {row["repo"]: row for row in engine.red_rows(config)}
        self.assertEqual(sorted(rows), ["mirror-az", "mirror-bb", "mirror-gl", "mirror-jk"])
        self.assertEqual(rows["mirror-bb"]["workflow"], "linux (buildbot)")
        self.assertEqual(rows["mirror-gl"]["run_id"], 31)      # the unknown pipeline 28 is newer and does not hide it; the merge request does not decide
        self.assertEqual(rows["mirror-gl"]["streak"], 1)
        self.assertTrue(rows["mirror-gl"]["url"].endswith("/group/app/-/pipelines/31"))
        self.assertTrue(all(r["source"].startswith("external:") for r in engine.runs(config)))
        self.assertEqual({s["state"] for s in engine.status(config)["sources"]}, {"red"})
        self.assertEqual([s["experimental"] for s in engine.status(config)["sources"]], [False, False, True, True])

    def test_jenkins_and_azure_need_their_own_switch(self):
        config = self.config(jenkins={"enabled": False}, azure={"enabled": False})
        self.assertEqual([s["kind"] for s in engine.configured(config)], ["buildbot", "gitlab"])
        self.assertEqual({i["reason"] for i in engine.status(config)["invalid"]}, {"kind_off"})

    def test_no_read_before_the_interval_and_not_changed_keeps_what_was_read(self):
        config = self.config([fake.sources(self.base)[1]], refresh_seconds=600)
        self.assertEqual(engine.refresh(config, now=1000.0), 1)
        self.assertEqual(engine.refresh(config, now=1500.0), 0)
        self.assertEqual(engine.refresh(config, now=2000.0), 1)      # the server answers 304 now
        self.assertIn('"v1"', [headers.get("If-None-Match") for _path, headers in self.server.seen])
        self.assertEqual(len(engine.red_rows(config)), 1)

    def test_a_service_that_stops_answering_is_degraded_keeps_its_red_and_recovers(self):
        config = self.config([fake.sources(self.base)[1]], breaker={"failures": 2})
        engine.refresh(config, now=1000.0)

        def down(request, **_kwargs):
            raise OSError("refused")
        for now in (2000.0, 4000.0):
            engine.refresh(config, now=now, opener=down)
        status = engine.status(config)["sources"][0]
        self.assertEqual((status["state"], status["reason"]), ("degraded", "unreachable"))
        codes = sorted(a["code"] for a in engine.alerts(config))
        self.assertEqual(codes, ["ci.external.degraded", "ci.external.red"])
        self.assertTrue([a for a in engine.alerts(config) if a["code"] == "ci.external.red"][0]["details"]["stale"])
        engine.refresh(config, now=90000.0)
        self.assertEqual(engine.status(config)["sources"][0]["state"], "red")

    def test_a_failure_with_nothing_read_before_is_never_a_red(self):
        for case in ("404", "429", "500", "broken", "redirect", "html", "huge"):
            engine.forget()
            config = self.config([f"gitlab;repo=mirror;url={self.base}/fail/{case};project=group/app"], max_bytes=10000)
            engine.refresh(config, now=1000.0)
            self.assertEqual(engine.red_rows(config), [], case)
            self.assertEqual(engine.status(config)["sources"][0]["state"], "degraded", case)
        reasons = {case: engine.probe(self.config(), f"gitlab;repo=m;url={self.base}/fail/{case};project=a/b")["reason"] for case in ("429", "redirect", "html", "broken")}
        self.assertEqual(reasons, {"429": "rate_limited", "redirect": "redirect", "html": "not_json", "broken": "not_json"})

    def test_a_missing_builder_is_degraded_and_not_a_red(self):
        config = self.config([f"buildbot;repo=mirror;url={self.base};builders=docs+gone"])
        engine.refresh(config, now=1000.0)
        status = engine.status(config)["sources"][0]
        self.assertEqual((status["state"], status["reason"]), ("degraded", "missing builder:gone"))
        self.assertEqual(engine.red_rows(config), [])


class Safety(Base):
    def test_private_addresses_are_refused_by_default(self):
        config = self.config(allow_private_targets=False)
        for url in (self.base, "http://169.254.169.254", "http://10.0.0.7", "http://[::1]:80"):
            out = engine.probe(config, f"gitlab;repo=m;url={url};project=a/b")
            self.assertEqual(out["reason"], "private_target", url)
        self.assertEqual(self.server.seen, [])

    def test_bad_addresses_and_lines_are_refused(self):
        reader = Reader({"kind": "gitlab", "url": "file:///etc/passwd"}, engine.settings(self.config()))
        with self.assertRaises(Failed):
            reader.url("/x")
        for line in ("gitlab;repo=m", "other;repo=m;url=http://x", "gitlab;repo=m;url=http://x", "gitlab;repo=m;url=http://x;project=a;token=abc", "jenkins;repo=m;url=http://x;job=a;token_env=no-dash"):
            self.assertEqual(engine.parse(line)[0], None, line)
        self.assertFalse(engine.probe(self.config(), "nonsense")["ok"])

    def test_a_token_comes_from_the_environment_and_only_its_name_is_configured(self):
        line = f"gitlab;repo=m;url={self.base};project=group/app;token_env=EXTCI_TEST_VALUE"
        with mock.patch.dict(os.environ, {"EXTCI_TEST_VALUE": ""}):
            self.assertEqual(engine.probe(self.config(), line)["reason"], "token_missing")
        sample = "abc" + "123sample"
        with mock.patch.dict(os.environ, {"EXTCI_TEST_VALUE": sample}):
            self.assertTrue(engine.probe(self.config(), line)["ok"])
            self.assertEqual(self.server.seen[-1][1].get("Private-Token") or self.server.seen[-1][1].get("PRIVATE-TOKEN"), sample)
            clear = f"gitlab;repo=m;url=http://ci.example.org;project=a/b;token_env=EXTCI_TEST_VALUE"
            self.assertEqual(engine.probe(self.config(allow_private_targets=False), clear)["reason"], "token_clear")
            self.assertNotIn(sample, json.dumps(engine.status(self.config([line]))))

    def test_off_means_no_request_at_all(self):
        for config in ({}, self.config(enabled=False), dict(self.config(), airgapped=True)):
            self.assertEqual(engine.refresh(config, now=1000.0), 0)
            self.assertIsNone(engine.tick(config, {}))
            self.assertEqual((engine.red_rows(config), engine.alerts(config), engine.runs(config)), ([], [], []))
        self.assertEqual(self.server.seen, [])
        self.assertFalse(families.block({}, "external_ci")["logs"]["enabled"])

    def test_importing_the_family_does_not_load_the_package(self):
        code = "import sys; sys.path.insert(0, sys.argv[1]); from github_actions_monitor import families; families.all_families(); print(any('external_ci' in m for m in sys.modules))"
        done = subprocess.run([sys.executable, "-c", code, str(HERE / "src")], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.stdout.strip(), "False", done.stderr)


class Logs(Base):
    def test_logs_are_off_by_default_and_no_log_address_is_asked(self):
        engine.refresh(self.config(), now=1000.0)
        self.assertFalse([p for p, _h in self.server.seen if "trace" in p or "console" in p or "/logs" in p or "steps" in p])

    def test_the_tail_is_clean_and_bounded_for_every_service(self):
        config = self.config(logs={"enabled": True, "tail_lines": 10})
        engine.refresh(config, now=1000.0)
        for source in engine.status(config)["sources"]:
            self.assertTrue(source["logs"], source["kind"])
            with mock.patch.object(engine.time, "time", return_value=1001.0):
                found = engine.log_of(config, source["id"], source["logs"][0])
            self.assertIn("FAILED: the answer was 41", found["text"], source["kind"])
            self.assertNotIn("\x1b", found["text"])
        text = engine.clean_log("a\x00b\nkey " + "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8" + "\nlast", 2)
        self.assertNotIn("A1b2C3d4", text)
        self.assertTrue(text.endswith("last"))
        reader = Reader({"kind": "jenkins", "url": self.base}, engine.settings(config))
        text, cut = reader.tail("/job/folder/job/app/12/consoleText", 10)
        self.assertEqual((len(text), cut), (10, True))


class Alerts(Base):
    def test_a_silenced_rule_silences_the_red_and_nothing_of_security(self):
        config = self.config([fake.sources(self.base)[0]])
        engine.refresh(config, now=1000.0)
        red = engine.alerts(config)[0]
        self.assertEqual((red["code"], red["level"], red["sentinel"]), ("ci.external.red", "error", "ci"))
        silence = [{"scope": "code", "value": "ci.external.red", "until": "2999-01-01T00:00:00Z", "until_ts": 2 ** 40}]
        self.assertTrue(alert_center.covering(red, silence))
        self.assertFalse(alert_center.covering({"id": "security.x:mirror-bb", "code": "security.x", "sentinel": "security"}, silence))
        self.assertEqual(engine.alerts(self.config([fake.sources(self.base)[0]], alert={"enabled": False})), [])


if __name__ == "__main__":
    unittest.main()
