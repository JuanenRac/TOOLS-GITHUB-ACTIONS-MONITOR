# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two guides of the connection with an AI tool and of the quota exist in the eight languages, are in the help index, and every setting they cite exists."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import modes  # noqa: E402
import settings_api  # noqa: E402

DOCS = HERE / "docs"
SUFFIXES = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por")
FILE_ENDINGS = (".md", ".json", ".jsonl", ".py", ".pem", ".txt", ".bat", ".sh")


def flatten(block, prefix=""):
    out = set()
    for key, value in block.items():
        name = f"{prefix}{key}"
        out.add(name)
        if isinstance(value, dict):
            out |= flatten(value, name + ".")
    return out


def known_keys():
    keys = set(settings_api.FIELDS) | flatten(am.DEFAULTS) | flatten(modes.DEFAULTS, "modes.")
    return keys | {k.split(".")[0] for k in keys}


def cited(text):
    for token in re.findall(r"`([^`\n]+)`", text):
        if " " in token or "/" in token or token.startswith(("-", "GET", "POST")) or token.endswith(FILE_ENDINGS) or "." not in token:
            continue
        if not re.fullmatch(r"[a-z_]+(?:\.[a-z_*]+)+", token):
            continue
        yield token


class Guides(unittest.TestCase):
    def test_every_guide_exists_in_the_eight_languages_and_in_the_help_index(self):
        index = json.loads((DOCS / "help_index.json").read_text(encoding="utf-8"))
        topics = {t.get("id") or t.get("key") or t.get("topic") for t in index["topics"] if isinstance(t, dict)}
        for base, topic in (("AI_CONNECTION", "ai_connection"), ("QUOTA", "quota")):
            for suffix in SUFFIXES:
                path = DOCS / f"{base}{suffix}.md"
                self.assertTrue(path.is_file(), path.name)
                self.assertGreater(len(path.read_text(encoding="utf-8")), 2000, path.name)
            self.assertIn(topic, topics, f"{topic} is not in the help index")

    def test_every_setting_a_guide_cites_exists(self):
        keys = known_keys()
        for base in ("AI_CONNECTION", "QUOTA"):
            for suffix in SUFFIXES:
                text = (DOCS / f"{base}{suffix}.md").read_text(encoding="utf-8")
                for token in cited(text):
                    probe = token[:-2] if token.endswith(".*") else token
                    ok = probe in keys or any(k.startswith(probe + ".") for k in keys)
                    self.assertTrue(ok, f"{base}{suffix}: `{token}` is not a setting of the monitor")

    def test_the_quota_guide_does_not_claim_what_is_not_there(self):
        for suffix in SUFFIXES:
            text = (DOCS / f"QUOTA{suffix}.md").read_text(encoding="utf-8")
            self.assertNotIn("network.graphql_batch", text)
            self.assertNotRegex(text, r"[A-Za-z]:\\Users|\\keys\\\\")      # no personal path


if __name__ == "__main__":
    unittest.main()
