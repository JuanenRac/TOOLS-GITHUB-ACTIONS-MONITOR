# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two secrets of the environment (the key of the supervisor and the access token) leave it before the first program is started, in every process, so that nothing a process of an account
starts inherits them."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.security import envguard  # noqa: E402

SECRETS = {"MONITOR_SUPERVISOR_KEY": "key-of-the-supervisor", "MONITOR_ACCESS_TOKEN": "token-of-the-network", "MY_OWN_TOKEN_NAME": "another-name-for-the-token"}

#: runs main() of the monitor with a `gh` that is never found: the recorder takes the place of subprocess.run and says which of the secrets the program would have inherited
CHILD = r"""
import json, os, subprocess, sys
sys.path.insert(0, os.environ["SRC"])
from github_actions_monitor.app import actions_monitor as am
seen = {}
def recorder(args, *a, **k):
    env = k.get("env") if k.get("env") is not None else os.environ
    seen[" ".join(map(str, args))[:40]] = sorted(n for n in ("MONITOR_SUPERVISOR_KEY", "MONITOR_ACCESS_TOKEN", "MY_OWN_TOKEN_NAME") if n in env)
    open(os.environ["OUT"], "w").write(json.dumps(seen))
    raise SystemExit(0)
subprocess.run = recorder
am.platform_compat.gh_available = lambda: True
sys.argv = ["monitor", "--no-browser", "--port", "18861"]
try:
    am.main()
except SystemExit:
    pass
"""


class BeforeTheFirstProgram(unittest.TestCase):
    def run_child(self, config):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        (folder / "config").mkdir()
        (folder / "config" / "actions_monitor.json").write_text(json.dumps(config), encoding="utf-8")
        script = folder / "child.py"
        script.write_text(CHILD, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in SECRETS}
        env.update(SECRETS)
        env.update({"SRC": str(HERE / "src"), "OUT": str(folder / "out.json"), "MONITOR_CONFIG_DIR": str(folder / "config"), "MONITOR_CONFIG": str(folder / "config" / "actions_monitor.json"),
                    "MONITOR_DATA_DIR": str(folder / "data"), "CI": "true", "PYTHONDONTWRITEBYTECODE": "1"})
        subprocess.run([sys.executable, "-I", str(script)], env=env, cwd=str(folder), capture_output=True, timeout=120)
        out = folder / "out.json"
        self.assertTrue(out.is_file(), "the first program was never started")
        return json.loads(out.read_text(encoding="utf-8"))

    def test_the_first_gh_of_an_account_that_does_not_listen_on_the_network_gets_none_of_them(self):
        seen = self.run_child({})
        self.assertTrue(seen)
        for program, inherited in seen.items():
            self.assertEqual([n for n in inherited if n != "MY_OWN_TOKEN_NAME"], [], program)      # the third name is nobody's secret unless the configuration says so

    def test_an_access_token_under_another_name_is_also_gone(self):
        seen = self.run_child({"listen": {"network": True, "token_env": "MY_OWN_TOKEN_NAME"}})
        for program, inherited in seen.items():
            self.assertEqual(inherited, [], program)

    def test_the_values_are_still_there_for_the_process_that_needs_them(self):
        saved = {k: os.environ.get(k) for k in SECRETS}
        try:
            os.environ.update(SECRETS)
            envguard.hold("MY_OWN_TOKEN_NAME")
            for name, value in SECRETS.items():
                self.assertNotIn(name, os.environ)
                self.assertEqual(envguard.get(name), value)
            self.assertEqual(envguard.for_account_process()["MONITOR_SUPERVISOR_KEY"], SECRETS["MONITOR_SUPERVISOR_KEY"], "the supervisor still hands the key to the process of an account")
            self.assertFalse([n for n in SECRETS if n in envguard.clean_environment()])
        finally:
            for name, value in saved.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ[name] = value
            for name in SECRETS:
                envguard.HELD.pop(name, None)
            envguard.NAMES.discard("MY_OWN_TOKEN_NAME")


if __name__ == "__main__":
    unittest.main()
