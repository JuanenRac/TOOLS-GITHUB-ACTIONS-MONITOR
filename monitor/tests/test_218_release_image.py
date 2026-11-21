# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The image is published only from the tag of the version (a manual run with `push` on from a branch stops), the base images are pinned by digest, the secret of the webhook can be a file and Caddy
sends HSTS. The files live in the repository, not in the zip of the monitor."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

ROOT = HERE.parent
DEPLOY = ROOT / "deploy"
WORKFLOW = ROOT / ".github" / "workflows" / "release-image.yml"


def need(path):
    if not path.is_file():
        raise unittest.SkipTest("the files of deploy/ and the workflows live in the repository, not in the zip of the monitor")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


class ReleaseImage(unittest.TestCase):
    def test_push_on_outside_the_tag_of_the_version_stops_before_any_login_or_push(self):
        text = need(WORKFLOW)
        self.assertIn("REF_TYPE: ${{ github.ref_type }}", text)
        guard = re.search(r'if \[ "\$PUBLISH" = "true" \] && \{ \[ "\$REF_TYPE" != "tag" \] \|\| \[ "\$TAG" != "v\$\{version\}" \]; \}; then\n(.*?)\n\s+fi', text, re.S)
        self.assertTrue(guard, "a guard on PUBLISH, the type of the ref and the version")
        self.assertIn("exit 1", guard.group(1))
        self.assertIn("images are published only from that tag", guard.group(1), "a message that says what to do")
        self.assertLess(text.index('"$REF_TYPE" != "tag"'), text.index("docker login"), "the guard runs before the login")
        self.assertLess(text.index('"$REF_TYPE" != "tag"'), text.index("--push"), "and before the push")

    def test_the_base_images_are_pinned_by_digest(self):
        docker = need(DEPLOY / "Dockerfile")
        self.assertRegex(docker, r"(?m)^ARG PYTHON_DIGEST=sha256:[0-9a-f]{64}$")
        froms = re.findall(r"(?m)^FROM (\S+)", docker)
        self.assertEqual(len(froms), 3)
        for ref in froms:
            self.assertTrue(ref.endswith("@${PYTHON_DIGEST}"), ref)
        self.assertRegex(need(DEPLOY / "compose.yaml"), r"image: caddy:[\w.-]+@sha256:[0-9a-f]{64}")

    def test_the_secret_of_the_webhook_can_be_a_file_and_the_compose_file_alone_is_unchanged(self):
        extra = need(DEPLOY / "compose.webhook.yaml")
        self.assertIn("MONITOR_WEBHOOK_SECRET_FILE: /run/secrets/webhook_secret", extra)
        self.assertRegex(extra, r"(?s)secrets:\n\s+webhook_secret:\n\s+file: \./webhook_secret\.txt")
        self.assertNotIn("webhook_secret", need(DEPLOY / "compose.yaml").replace("deploy/webhook_secret.txt", "").replace("compose.webhook.yaml", ""), "the main file asks for nothing that may not exist")

    def test_caddy_sends_hsts(self):
        self.assertRegex(need(DEPLOY / "Caddyfile"), r'Strict-Transport-Security\s+"max-age=\d{7,}')


if __name__ == "__main__":
    unittest.main()
