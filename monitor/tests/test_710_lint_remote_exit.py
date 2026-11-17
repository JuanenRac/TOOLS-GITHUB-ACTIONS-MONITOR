# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`lint_workflows.py --remote`: a repository that could not be read must not end like a clean one (exit code 2, a reason on the standard error), and "." / ".." are not repository names.
Synthetic repositories and a fake reader: no network, no `gh`."""
import contextlib
import io
import json
import unittest
from unittest import mock

import _testenv  # noqa: F401
from test_lint_without_clone import BAD, GOOD, Api  # noqa: E402

from github_actions_monitor.cli import lint_workflows  # noqa: E402
from github_actions_monitor.integrations import remote_workflows as rw  # noqa: E402


class Api2(Api):
    """The same fake, plus the repository itself (`repos/OWNER/REPO`), which exists only for the names in `known`."""

    def __init__(self, repos, fail=None, known=()):
        super().__init__(repos, fail)
        self.known = set(known)

    def read(self, endpoint):
        if endpoint.count("/") == 2 and endpoint.startswith("repos/"):
            self.calls.append(endpoint)
            for needle, error in self.fail.items():
                if needle in endpoint:
                    raise RuntimeError(error)
            if endpoint.split("/")[2] not in self.known:
                raise RuntimeError("gh: Not Found (HTTP 404)")
            return {"name": endpoint.split("/")[2]}
        return super().read(endpoint)


def run(api, *argv):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(rw, "gh_read", api.read), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = lint_workflows.main(["--fail-on", "info", *argv])
    return code, out.getvalue(), err.getvalue()


class RemoteExit(unittest.TestCase):
    def test_a_repository_that_was_read_keeps_its_old_exit_codes(self):
        clean = Api2({"ok": {"ci.yml": GOOD}}, known=["ok"])
        self.assertEqual(run(clean, "--remote", "acme/ok")[0], 0)
        dirty = Api2({"bad": {"ci.yml": BAD}}, known=["bad"])
        self.assertEqual(run(dirty, "--remote", "acme/bad")[0], 1)

    def test_a_repository_without_workflows_is_clean_when_it_exists(self):
        api = Api2({"empty": {}}, known=["empty"])
        code, _, err = run(api, "--remote", "acme/empty")
        self.assertEqual((code, err), (0, ""))

    def test_a_repository_that_does_not_exist_is_not_clean(self):
        api = Api2({"gone": {}}, known=[])
        code, out, err = run(api, "--remote", "acme/gone")
        self.assertEqual(code, lint_workflows.EXIT_NOT_READ)
        self.assertIn("acme/gone", err)

    def test_sso_without_access_and_no_network_are_not_clean(self):
        for error in ("HTTP 403 SAML enforcement: sso", "HTTP 403 Forbidden", "dial tcp: no such host"):
            with self.subTest(error=error):
                api = Api2({"r": {"ci.yml": GOOD}}, fail={"contents": error}, known=["r"])
                code, _, err = run(api, "--remote", "acme/r")
                self.assertEqual(code, lint_workflows.EXIT_NOT_READ)
                self.assertTrue(err.strip())

    def test_a_name_that_is_not_owner_slash_repo_is_not_clean(self):
        api = Api2({}, known=[])
        for name in ("demo-owner", "../x", "./x", "a/..", "a/b/c"):
            with self.subTest(name=name):
                code, _, err = run(api, "--remote", name)
                self.assertEqual(code, lint_workflows.EXIT_NOT_READ)
                self.assertTrue(err.strip())
        self.assertEqual(api.calls, [])      # nothing was asked for those names

    def test_json_stays_a_list_and_the_code_still_tells(self):
        api = Api2({"gone": {}}, known=[])
        code, out, _ = run(api, "--json", "--remote", "acme/gone")
        self.assertEqual(json.loads(out), [])
        self.assertEqual(code, lint_workflows.EXIT_NOT_READ)

    def test_a_finding_wins_over_an_unread_repository(self):
        api = Api2({"bad": {"ci.yml": BAD}, "gone": {}}, known=["bad"])
        self.assertEqual(run(api, "--remote", "acme/bad", "--remote", "acme/gone")[0], 1)

    def test_dot_names_are_not_repository_names(self):
        self.assertFalse(rw.NAME_RE.match("."))
        self.assertFalse(rw.NAME_RE.match(".."))
        self.assertTrue(rw.NAME_RE.match(".github"))
        self.assertTrue(rw.NAME_RE.match("a.b"))


if __name__ == "__main__":
    unittest.main()
