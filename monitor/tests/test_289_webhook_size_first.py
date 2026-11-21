# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The incoming webhook judges the size of the body BEFORE anything else (413 even for a delivery id already seen), and the body the container audit sends to test that limit is over the real limit and
travels with an id of its own: the audit once sent 300 KB, under the default limit of 1 MiB, with the id of the first ping, and got a duplicate (202) instead of a refusal."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.security import webhook

ROOT = Path(__file__).resolve().parent.parent.parent
SECRET = "k" * 40
CONFIG = {"webhook": {"enabled": True}}
SEEN = "11111111-2222-3333-4444-555555555555"


class SizeFirst(unittest.TestCase):
    def setUp(self):
        webhook.reset()
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: SECRET})
        patch.start()
        self.addCleanup(patch.stop)

    def send(self, raw, delivery=SEEN):
        headers = {"X-GitHub-Event": "ping", "X-GitHub-Delivery": delivery, "X-Hub-Signature-256": webhook.sign(SECRET, raw)}
        return webhook.handle(CONFIG, raw, headers, ["R"])

    def test_a_big_body_is_refused_even_with_a_delivery_id_already_seen(self):
        small = json.dumps({"zen": "x", "repository": {"name": "R", "full_name": "o/R"}}).encode()
        self.assertEqual(self.send(small)[0], 200)
        self.assertEqual(self.send(small)[1].get("duplicate"), True)
        big = json.dumps({"repository": {"name": "R", "full_name": "o/R"}, "pad": "x" * (webhook.MAX_BODY + 10)}).encode()
        code, answer, _repo = self.send(big)
        self.assertEqual(code, 413, answer)
        self.assertNotIn("duplicate", answer)


@unittest.skipUnless((ROOT / "tools" / "docker_audit" / "e8_webhook.py").exists(), "the tools of the repository do not travel with the zip of the product")
class AuditScript(unittest.TestCase):
    def test_the_body_over_the_limit_is_over_the_limit_and_every_delivery_has_its_own_id(self):
        sys.path.insert(0, str(ROOT / "tools" / "docker_audit"))
        self.addCleanup(sys.path.remove, str(ROOT / "tools" / "docker_audit"))
        source = (ROOT / "tools" / "docker_audit" / "e8_webhook.py").read_text(encoding="utf-8")
        self.assertIn("BIG_PAD = ", source)
        namespace = {}
        for line in source.splitlines():
            if line.startswith("BIG_PAD = "):
                exec(line, {}, namespace)      # noqa: S102 - one constant of the script of the audit
        self.assertGreater(namespace["BIG_PAD"], webhook.MAX_BODY)
        self.assertNotIn('delivery="{rand}-{i}"', source.split("def body(s):")[1])      # a call that leaves the default id would share "{rand}-0" with the first ping
        for name in ("big", "other"):
            self.assertIn("delivery=\"" + name, source)
