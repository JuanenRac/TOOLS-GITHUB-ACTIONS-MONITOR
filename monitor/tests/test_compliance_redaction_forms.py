# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two forms of text that the cleaner let through (a long internal host name that ends in `.local`, a piece of a private key without its header) and each layer of the cleaning of an alert on its
own: the four layers cover one another, so only a test of each one by itself says that none was removed."""
import json
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.integrations import ai_alerts
from github_actions_monitor.security import redactor

# built when the test runs, so that no file of the repository holds the shape of a key or of a token
BODY = "MII" + "EowIBAAKCAQEAxK1p0Yw8Vq3mZ2n7T9c4"
NEXT = "bR6sH1jL5dF8gW0uQeXyA3kPzNvMaaQ1"
END = "-----END " + "RSA PRIVATE KEY-----"
TOKEN = "gh" + "p_abcdefghijklmnopqrstuvwxyz0123456789"
MAIL = "victima.canario@corp-ejemplo.com"
ROW = {"repo": "r " + MAIL, "workflow": "CI " + TOKEN, "conclusion": "failure", "since": None, "streak": 1, "url": "https://evil.example/x?token=" + TOKEN}
DIRTY = {**ROW, "id": "abc", "severity": "high", "class": "real", "cause": MAIL, "action": TOKEN, "account_id": "", "first_seen": 5}


class TheFormsThatGotThrough(unittest.TestCase):
    def test_a_long_internal_host_name_goes_whole(self):
        for text in ("cannot resolve db-prod-01.intranet.empresa-cliente.local", "cannot resolve db-prod-01.intranet.local:5432", "cannot resolve a.corp.empresa-cliente.local"):
            self.assertEqual(redactor.redact(text), "cannot resolve [host]", text)

    def test_a_short_line_of_a_key_without_header_is_cleaned(self):
        for text in ("error " + BODY, BODY + "\n" + NEXT, "2026-01-01T00:00:00Z " + BODY):
            out = redactor.redact(text)
            self.assertNotIn(BODY[:20], out)
            self.assertNotIn(NEXT[:20], out)
            self.assertIn("[pem]", out)

    def test_a_log_that_begins_in_the_middle_of_a_key_loses_the_lines_above_the_end(self):
        out = redactor.redact("step 1\nfailed here:\n" + NEXT + "\nab12+/cd==\n" + END + "\nerror: exit 1")
        self.assertEqual(out, "step 1\nfailed here:\n[pem]\nerror: exit 1")

    def test_ordinary_text_is_left_alone(self):
        for text in ("see settings.local.json and .env.local", "MIIX is not a key", "Compiling\nLinking\nDone", "MIIA short"):
            self.assertEqual(redactor.redact(text), text)

    def test_the_diagnosis_cleans_its_lines_as_one_text(self):
        log = "\n".join("build\ttest\t2026-01-01T00:00:00.0000000Z " + line for line in ("error: " + BODY, "error " + NEXT, "error " + END))

        def runner(args, timeout=60):
            if args[0] == "api":
                return 0, json.dumps({"jobs": [{"name": "build", "steps": [{"name": "test", "conclusion": "failure"}]}]}), ""
            return 0, log, ""
        out = ai_alerts.diagnose("o", "r", "https://github.com/o/r/actions/runs/5", runner)
        self.assertNotIn(BODY, json.dumps(out))
        self.assertTrue(out["lines"])


class EveryLayerOnItsOwn(unittest.TestCase):
    def clean(self, text):
        for canary in (TOKEN, MAIL):
            self.assertNotIn(canary, text)

    def test_the_alert_is_built_clean(self):
        self.clean(json.dumps(ai_alerts.build_alert(ROW, [], "")))

    def test_the_line_of_the_feed_is_cleaned_when_it_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            ai_alerts._event(tmp, "opened", DIRTY, 1000)
            self.clean((Path(tmp) / ai_alerts.FEED).read_text(encoding="utf-8"))

    def test_the_state_file_is_cleaned_before_it_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = {"abc": {**DIRTY, "state": "resolved", "resolved_at": 999}}
            (Path(tmp) / ai_alerts.STATE).write_text(json.dumps(old), encoding="utf-8")
            ai_alerts.update({"ai_alerts": {"enabled": True, "folder": tmp}}, [], now=1000.0)
            text = (Path(tmp) / ai_alerts.STATE).read_text(encoding="utf-8")
        self.assertIn("abc", text)
        self.clean(text)

    def test_the_body_of_the_hook_is_cleaned(self):
        sent = []
        ai_alerts.Hook().send("http://127.0.0.1:9/h", DIRTY, 1000, opener=lambda request: sent.append(request.data.decode("utf-8")))
        self.assertTrue(sent)
        self.clean(sent[0])


if __name__ == "__main__":
    unittest.main()
