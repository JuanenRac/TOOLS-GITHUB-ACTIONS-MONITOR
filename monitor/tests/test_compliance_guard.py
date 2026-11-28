# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The strict read-only mode and the network policy: what counts as reading, and that a process with the restriction really cannot write or reach out (checked in processes of their own, because a hook of
the interpreter cannot be removed). No test here opens a connection outside this computer: the refusals happen before anything leaves."""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import ghactions  # noqa: E402
from github_actions_monitor.security import compliance_guard as guard  # noqa: E402


class Reading(unittest.TestCase):
    def test_the_reading_commands_of_gh_are_reads(self):
        for line in ("api repos/o/r", "api -i rate_limit", "api -X GET search/issues -f q=x", "api --method=HEAD repos/o/r", "api graphql -f query=query{viewer{login}}", "auth status", "auth token",
                     "run list -R o/r", "run view 5 --log-failed -R o/r", "-R o/r pr list", "release download v1", "attestation verify f --repo o/r", "workflow view ci.yml", "--version"):
            self.assertTrue(guard.gh_is_read(line.split()), line)

    def test_everything_else_is_not_a_read(self):
        for line in ("api -X POST repos/o/r/issues/1/comments -f body=x", "api repos/o/r/issues -f title=x", "api --method DELETE repos/o/r/hooks/1", "api -XPATCH repos/o/r", "api repos/o/r --input body.json",
                     "api graphql -f query=mutation{x}", "api graphql -F query=@file.graphql", "run rerun 5", "run cancel 5", "workflow run ci.yml", "workflow disable ci.yml", "pr merge 1",
                     "issue close 1", "release create v1", "release upload v1 f", "secret set X", "variable set X", "auth login", "auth refresh", "webhook forward", "repo delete o/r", "alias set a b",
                     "unknowncommand thing", "cache delete 1"):
            self.assertFalse(guard.gh_is_read(line.split()), line)

    def test_every_action_the_monitor_can_confirm_on_github_is_refused_in_strict_mode(self):
        for name, spec in ghactions.ACTIONS.items():
            method, endpoint = spec[0], spec[1]
            self.assertFalse(guard.gh_is_read(["api", "-X", method, endpoint.format(owner="o", repo="r", id=1, workflow="w", number=1)]), name)

    def test_a_windows_command_line_is_split_as_the_c_runtime_does(self):
        line = subprocess.list2cmdline(["C:\\Program Files\\gh.exe", "api", "-f", 'body=say "hi" \\ there', "x\\"])
        self.assertEqual(guard.split_windows(line), ["C:\\Program Files\\gh.exe", "api", "-f", 'body=say "hi" \\ there', "x\\"])
        self.assertEqual(guard.program_of("C:\\Program Files\\GitHub CLI\\gh.EXE"), "gh")


class Policy(unittest.TestCase):
    def tearDown(self):
        guard.reset()

    def test_what_each_policy_lets_through(self):
        self.assertTrue(guard.host_allowed("example.org", "default", (), ""))
        for host in ("api.github.com", "uploads.github.com", "github.corp.example", "127.0.0.1", "localhost", "::1"):
            self.assertTrue(guard.host_allowed(host, "github_only", (), "github.corp.example"), host)
        for host in ("github.com", "example.org", "10.0.0.5", "169.254.169.254"):
            self.assertFalse(guard.host_allowed(host, "github_only", (), ""), host)
        self.assertTrue(guard.host_allowed("siem.corp.example", "github_only", ("*.corp.example",), ""))
        self.assertFalse(guard.host_allowed("api.github.com", "none", ("api.github.com",), ""))
        self.assertTrue(guard.host_allowed("127.0.0.1", "none", (), ""))

    def test_a_typo_in_a_restriction_does_not_open_the_network_and_the_restrictions_only_tighten(self):
        self.assertEqual(guard.wanted({"security": {"egress_policy": "git_only"}})[1], "none")
        self.assertEqual(guard.wanted({})[:2], (False, "default"))
        guard.configure({"security": {"read_only_strict": True, "egress_policy": "none"}})
        guard.configure({"security": {"read_only_strict": False, "egress_policy": "default"}})
        self.assertEqual((guard.STATE["strict"], guard.STATE["policy"]), (True, "none"))

    def test_the_network_programs_and_the_commands(self):
        guard.configure({"security": {"egress_policy": "github_only", "egress_allow": ["program:docker"]}})
        self.assertEqual(guard.command_refusal(["git", "status"]), "")
        self.assertEqual(guard.command_refusal(["git", "-C", "x", "fetch"]), "egress_policy")
        self.assertEqual(guard.command_refusal(["apprise", "-c", "f"]), "egress_policy")
        self.assertEqual(guard.command_refusal(["docker", "ps"]), "")
        self.assertEqual(guard.command_refusal(["gh", "api", "user"]), "")
        guard.configure({"security": {"egress_policy": "none"}})
        self.assertEqual(guard.command_refusal(["gh", "api", "user"]), "egress_policy")

    def test_the_configured_destinations_outside_the_policy_are_named(self):
        rows = [{"id": "ntfy", "hosts": ["ntfy.sh"], "active": True}, {"id": "github_api", "hosts": ["api.github.com"], "active": True}, {"id": "otlp", "hosts": ["o.example"], "active": False}]
        self.assertEqual(guard.violations({"security": {"egress_policy": "github_only"}}, rows), [("ntfy", "ntfy.sh")])
        self.assertEqual(guard.violations({}, rows), [])


CHILD = """
import json, socket, subprocess, sys, threading, urllib.request
sys.path.insert(0, {src!r})
import github_actions_monitor
from github_actions_monitor.security import compliance_guard as guard

def attempt(call):
    try:
        call()
        return "done"
    except guard.Blocked as error:
        return "blocked"
    except urllib.error.URLError as error:
        return "blocked" if isinstance(error.reason, guard.Blocked) else "failed"
    except Exception as error:
        return "failed " + type(error).__name__

out = {{"state": guard.status()}}
{body}
print(json.dumps(out))
"""


def run_child(config, body):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        path = Path(folder) / "actions_monitor.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        env = dict(os.environ, MONITOR_CONFIG=str(path))
        env.pop("GH_HOST", None)
        done = subprocess.run([sys.executable, "-c", CHILD.format(src=str(HERE / "src"), body=textwrap.dedent(body))], capture_output=True, text=True, timeout=60, env=env)
        if done.returncode:
            raise AssertionError(done.stderr[-2000:])
        return json.loads(done.stdout.strip().splitlines()[-1])


class InARealProcess(unittest.TestCase):
    def test_nothing_is_installed_with_the_defaults(self):
        out = run_child({}, "out['installed'] = guard.STATE['installed']\n")
        self.assertFalse(out["installed"])
        self.assertFalse(out["state"]["enforced"])

    def test_strict_mode_refuses_to_start_a_write_even_when_everything_else_allows_it(self):
        out = run_child({"security": {"read_only_strict": True}, "github_actions": {"enabled": True}}, """
            for name, argv in (("rerun", ["gh", "run", "rerun", "1", "-R", "o/r"]), ("comment", ["gh", "api", "-X", "POST", "repos/o/r/issues/1/comments", "-f", "body=x"]), ("push", ["git", "push"])):
                out[name] = attempt(lambda: subprocess.run(argv, capture_output=True, timeout=10))
            out["post"] = attempt(lambda: urllib.request.urlopen(urllib.request.Request("https://api.github.com/repos/o/r/issues", data=b"{}", method="POST"), timeout=5))
            out["other"] = attempt(lambda: subprocess.run([sys.executable, "-c", "pass"], check=True, timeout=30))
            """)
        self.assertEqual({k: out[k] for k in ("rerun", "comment", "push", "post", "other")}, {"rerun": "blocked", "comment": "blocked", "push": "blocked", "post": "blocked", "other": "done"})
        self.assertTrue(out["state"]["read_only_strict"] and out["state"]["enforced"])

    def test_with_none_no_connection_leaves_and_this_computer_still_works(self):
        out = run_child({"security": {"egress_policy": "none"}}, """
            out["name"] = attempt(lambda: urllib.request.urlopen("http://example.org/", timeout=5))
            out["address"] = attempt(lambda: socket.create_connection(("93.184.216.34", 80), timeout=5))
            out["udp"] = attempt(lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"x", ("93.184.216.34", 9)))
            out["gh"] = attempt(lambda: subprocess.run(["gh", "api", "user"], capture_output=True, timeout=10))
            server = socket.socket(); server.bind(("127.0.0.1", 0)); server.listen(1)
            out["local"] = attempt(lambda: socket.create_connection(("127.0.0.1", server.getsockname()[1]), timeout=5).close())
            out["blocked"] = guard.status()["blocked"]
            out["last"] = guard.status()["last_blocked"]
            """)
        self.assertEqual({k: out[k] for k in ("name", "address", "udp", "gh", "local")}, {"name": "blocked", "address": "blocked", "udp": "blocked", "gh": "blocked", "local": "done"})
        self.assertGreaterEqual(out["blocked"], 4)
        self.assertIn("egress_policy", out["last"])

    def test_with_github_only_other_names_are_refused_before_they_are_resolved(self):
        out = run_child({"security": {"egress_policy": "github_only"}}, """
            out["other"] = attempt(lambda: socket.getaddrinfo("example.org", 443))
            out["notifier"] = attempt(lambda: urllib.request.urlopen("https://ntfy.sh/x", timeout=5))
            out["address"] = attempt(lambda: socket.create_connection(("93.184.216.34", 443), timeout=5))
            """)
        self.assertEqual((out["other"], out["notifier"], out["address"]), ("blocked", "blocked", "blocked"))


if __name__ == "__main__":
    unittest.main()
