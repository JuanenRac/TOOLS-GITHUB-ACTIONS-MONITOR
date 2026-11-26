# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# Test of the example plugin with a ctx of its own: python -m unittest test_plugin
import unittest

import plugin


class Ctx:
    owner, now = "owner", 0

    def repos(self):
        return ["with", "without"]

    def get(self, path):
        return [] if "without" in path else [{"name": "bug"}]


class Plugin(unittest.TestCase):
    def test_only_the_repository_without_labels_is_reported(self):
        self.assertEqual([a["repo"] for a in plugin.run(Ctx())["alerts"]], ["without"])


if __name__ == "__main__":
    unittest.main()
