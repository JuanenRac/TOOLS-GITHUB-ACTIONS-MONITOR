# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A bank of secrets in the shapes CI logs really carry them, and the guard that none of them reaches a model: the text of the AI (`sanitize_text`), the text of the assistant (`untrusted`) and the one cleaner
(`redactor.redact`) must hide every one. The fixtures are built here from pieces at run time so that no secret-shaped string sits in the source."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import assistant  # noqa: E402
from github_actions_monitor.security import redactor  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402

BODY = "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"      # 36 characters of the kind a token carries
PEM_BODY = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj"
SECRETS = {
    "github classic": "ghp_" + BODY,
    "github oauth": "gho_" + BODY,
    "github user-to-server": "ghu_" + BODY,
    "github server-to-server": "ghs_" + BODY,
    "github refresh": "ghr_" + BODY,
    "github fine grained": "github_pat_" + "11ABCDEFG0" + "abcdefghijklmnopqrstuv_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxy",
    "aws access key": "AKIA" + "IOSFODNN7EXAMPLE",
    "slack": "xoxb-" + "123456789012-1234567890123-" + "AbCdEfGhIjKlMnOpQrStUvWx",
    "jwt": "eyJ" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ" + "." + "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    "pem": "-----BEGIN " + "PRIVATE KEY-----\n" + PEM_BODY + "\n-----END " + "PRIVATE KEY-----",
    "basic auth in a url": "https://" + "deploy:" + "s3cr3tP4ssw0rd" + "@registry.internal.example/v2/",
    "bearer header": "Authorization: Bearer " + BODY + "ZZ",
    "password pair": "DB_PASSWORD=" + "hunter2hunter2",
    "token pair": "api_token: " + "abcd1234efgh5678",
}


def hidden(text, secret):
    """The sensitive part must be gone: the secret itself, and for the shapes with a prefix the body that follows it."""
    core = secret
    for prefix in ("Authorization: Bearer ", "DB_PASSWORD=", "api_token: "):
        core = core.replace(prefix, "")
    core = core.split("@")[0].split(":")[-1] if secret.startswith("https://") else core
    return core not in text and secret not in text


class EverySecretIsHidden(unittest.TestCase):
    def check(self, name, function):
        leaks = []
        for label, secret in SECRETS.items():
            out = function(f"step 4 failed\n{secret}\nexit code 1")
            if not hidden(out, secret):
                leaks.append(label)
        self.assertEqual(leaks, [], name)

    def test_the_cleaner_of_the_product(self):
        self.check("redactor.redact", redactor.redact)

    def test_the_text_that_goes_to_the_ai(self):
        self.check("sanitize_text", lambda t: sentinel_ai.sanitize_text(t, 4000, keep="head"))

    def test_the_text_of_a_third_party_in_the_assistant(self):
        self.check("assistant.untrusted", lambda t: assistant.untrusted(t, 4000, "w0rd"))

    def test_a_secret_cut_by_the_limit_is_not_left_half_visible(self):
        for label, secret in SECRETS.items():
            out = sentinel_ai.sanitize_text("x " * 20 + secret, 60, keep="head")
            self.assertNotIn(secret[:24], out, label)

    def test_a_secret_inside_a_long_text_is_found(self):
        for label, secret in SECRETS.items():
            out = sentinel_ai.sanitize_text(("noise line of a log " * 80 + "\n") + secret + ("\n" + "more noise " * 80), 20000, keep="head")
            self.assertTrue(hidden(out, secret), label)

    def test_a_secret_in_every_text_the_assistant_hands_over_stays_hidden(self):
        from github_actions_monitor.health import repo_view
        for label, secret in SECRETS.items():
            alert = {"id": "k:1", "code": "ci.red", "level": "error", "sentinel": "ci", "repo": "r", "title": "failed " + secret, "created_at": "2026-01-01T00:00:00Z"}
            views = [repo_view.repo_view("r", [], [], [], [alert], None, {"ci": "healthy"}, "", 1_800_000_000.0)]
            seen = []
            cfg = sentinel_ai.ai_config({"ai": {"provider": "ollama", "assistant": {"enabled": True}}})
            assistant.ask("summarize_week", {}, cfg, {"views": lambda v=views: v, "score": lambda: {}}, lambda text: seen.append(text) or {"ok": True, "text": "x"})
            self.assertTrue(hidden(seen[0], secret), label)


if __name__ == "__main__":
    unittest.main()
