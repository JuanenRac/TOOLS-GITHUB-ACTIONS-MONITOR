# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Who sent a webhook request, when the process of an account is spoken to by the supervisor of the accounts: a valid key says "via:<address>", a wrong or missing key falls back to the peer. The
module used a module (hmac) it never imported, so every delivery that came through the supervisor answered 400. A static check also looks, in the whole package, for a standard module used as
`name.attr` in a function without being imported at the top of the file or in that function."""
import ast
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.security import auth_http, envguard  # noqa: E402

KEY = "k" * 40


def sender(headers, env=True):
    handler = SimpleNamespace(headers=headers, client_address=("203.0.113.9", 4000))
    values = {auth_http.CHILD_ENV: "1", envguard.SUPERVISOR_KEY_ENV: KEY} if env else {}
    with mock.patch.dict(os.environ, values):
        return actions_monitor.Handler.webhook_sender(handler)


class TheSenderOfAWebhookThroughTheSupervisor(unittest.TestCase):
    def test_a_valid_key_takes_the_address_the_supervisor_gives(self):
        self.assertEqual(sender({auth_http.SUPERVISOR_KEY_HEADER: KEY, auth_http.WEBHOOK_PEER_HEADER: "198.51.100.7"}), "via:198.51.100.7")

    def test_a_wrong_key_or_no_key_falls_back_to_the_peer(self):
        direct = sender({}, env=False)
        self.assertEqual(sender({auth_http.SUPERVISOR_KEY_HEADER: "x" * 40, auth_http.WEBHOOK_PEER_HEADER: "198.51.100.7"}), direct)
        self.assertEqual(sender({auth_http.WEBHOOK_PEER_HEADER: "198.51.100.7"}), direct)
        self.assertFalse(direct.startswith("via:"))

    def test_an_empty_or_huge_address_is_not_believed(self):
        direct = sender({}, env=False)
        self.assertEqual(sender({auth_http.SUPERVISOR_KEY_HEADER: KEY, auth_http.WEBHOOK_PEER_HEADER: ""}), direct)
        self.assertEqual(sender({auth_http.SUPERVISOR_KEY_HEADER: KEY, auth_http.WEBHOOK_PEER_HEADER: "a" * 81}), direct)

    def test_no_account_process_means_no_trust_in_the_header(self):
        self.assertFalse(sender({auth_http.SUPERVISOR_KEY_HEADER: KEY, auth_http.WEBHOOK_PEER_HEADER: "198.51.100.7"}, env=False).startswith("via:"))


class NoModuleIsUsedWithoutBeingImported(unittest.TestCase):
    def test_every_standard_module_used_in_a_function_is_imported_at_the_top_or_in_that_function(self):
        stdlib = set(sys.stdlib_module_names)
        problems = []
        for path in sorted((HERE / "src" / "github_actions_monitor").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            module_level = set()
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module_level.update((a.asname or a.name).split(".")[0] for a in node.names)
                elif isinstance(node, ast.Try) or isinstance(node, ast.If):
                    for sub in ast.walk(node):
                        if isinstance(sub, (ast.Import, ast.ImportFrom)):
                            module_level.update((a.asname or a.name).split(".")[0] for a in sub.names)
            parent = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

            def bound_in(func):
                names = {a.arg for a in func.args.args + func.args.kwonlyargs + func.args.posonlyargs}
                for sub in ast.walk(func):
                    if isinstance(sub, (ast.Import, ast.ImportFrom)):
                        names.update((a.asname or a.name).split(".")[0] for a in sub.names)
                    elif isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                        names.add(sub.id)
                return names

            for func in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
                own, outer = bound_in(func), parent.get(func)
                while outer is not None:      # a function defined inside another sees what the other one imported
                    if isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        own |= bound_in(outer)
                    outer = parent.get(outer)
                for sub in ast.walk(func):
                    if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id in stdlib and sub.value.id not in own | module_level:
                        problems.append(f"{path.relative_to(HERE)}:{sub.lineno} {func.name}() uses {sub.value.id}.{sub.attr} without importing {sub.value.id}")
        self.assertEqual(problems, [], "\n".join(problems[:20]))


if __name__ == "__main__":
    unittest.main()
