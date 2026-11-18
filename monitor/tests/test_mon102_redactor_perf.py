# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The cleaner of text answers in time that grows with the size of the text, not with its square: a long run of letters, dots, digits, dashes or underscores (the shapes that made the patterns with an open
prefix try every start position) is cleaned fast, and the secrets that sit at the end of such a run are still found."""
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.security import redactor  # noqa: E402

SHAPES = {"letters": "a", "dots": ".", "digits": "1", "dashes": "-", "underscores": "_", "dotted": "a.b.", "address": "1.2.3.", "words": "lorem ipsum "}
SIZE = 6000
#: the quadratic version took 2 to 6 seconds for this size on a quiet machine; the linear one takes a fraction of a second. The margin is wide so that a slow runner does not fail it.
LIMIT_SECONDS = 1.5


def shaped(piece, size=SIZE):
    return (piece * (size // len(piece) + 1))[:size]


class LongTexts(unittest.TestCase):
    def test_every_shape_is_cleaned_within_the_bound(self):
        slow = {}
        for name, piece in SHAPES.items():
            text = shaped(piece)
            start = time.perf_counter()
            out = redactor.redact(text)
            took = time.perf_counter() - start
            self.assertIsInstance(out, str)
            if took > LIMIT_SECONDS:
                slow[name] = round(took, 2)
        self.assertEqual(slow, {}, "the cleaner is not linear in the size of the text for these shapes (seconds)")

    def test_doubling_the_text_does_not_quadruple_the_time(self):
        text = shaped("a.b-", 4000)
        start = time.perf_counter()
        redactor.redact(text)
        small = time.perf_counter() - start
        start = time.perf_counter()
        redactor.redact(text * 4)
        big = time.perf_counter() - start
        self.assertLess(big, max(small * 12, 0.5), (small, big))      # linear = 4, quadratic = 16; the floor keeps a very fast machine from failing on noise

    def test_a_secret_after_a_long_run_is_still_found(self):
        run = shaped("x", 3000)
        token = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        for text, hidden in ((run + " password=hunter2secret", "hunter2secret"), (run + " " + token, token), (run + " user@example.com", "user@example.com"),
                             (run + " API_KEY=sk_live_abcdefghijklmnop", "abcdefghijklmnop"), (run + " https://bob:swordfish@host.example/x", "swordfish")):
            self.assertNotIn(hidden, redactor.redact(text), hidden)

    def test_the_usual_secrets_are_cleaned_as_before(self):
        for text, hidden in (("DB_PASSWORD=hunter2secret", "hunter2secret"), ("contact: someone@example.com", "someone@example.com"), ("host: build.corp.lan", "build.corp"),
                             ("x [at] example.com wrote", "example.com"), ("sentry_dsn=https://k@o.ingest.example/1", "ingest")):
            self.assertNotIn(hidden, redactor.redact(text), text)


if __name__ == "__main__":
    unittest.main()
