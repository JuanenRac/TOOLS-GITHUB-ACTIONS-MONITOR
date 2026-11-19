# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The anonymous read of a public repository by the workflow linter (lint.anonymous_public, `--anon`): raw.githubusercontent.com, no credential, only the allowed hosts, a size limit, a refusal is never clean."""
import contextlib
import io
import json
import unittest
import urllib.error

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api
from github_actions_monitor.cli import lint_workflows
from github_actions_monitor.integrations import remote_workflows

BAD = "name: ci\non: push\njobs:\n  b:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"


class Answer:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return self.data if n < 0 else self.data[:n]


class Fake:
    """An opener that answers like GitHub and keeps every request it was given."""

    def __init__(self, files=None, listing=None, code=0):
        self.files, self.code, self.requests = files or {}, code, []
        self.listing = listing if listing is not None else [{"type": "file", "name": n, "sha": "s" + n, "size": len(t)} for n, t in self.files.items()]

    def __call__(self, request):
        self.requests.append(request)
        url = request.full_url
        if self.code:
            raise urllib.error.HTTPError(url, self.code, "x", {}, None)
        if url.startswith("https://api.github.com/"):
            return Answer(json.dumps(self.listing).encode())
        name = url.rsplit("/", 1)[1]
        return Answer(self.files[name].encode())


class AnonymousReader(unittest.TestCase):
    def test_it_is_off_by_default_and_a_setting(self):
        self.assertFalse(lint_workflows.anonymous_allowed({}))
        self.assertFalse(lint_workflows.anonymous_allowed({"lint": {"anonymous_public": "yes"}}))
        self.assertTrue(lint_workflows.anonymous_allowed({"lint": {"anonymous_public": True}}))
        self.assertTrue(settings_api.check_value("lint.anonymous_public", True)[0])

    def test_the_files_come_from_raw_and_the_request_carries_no_credential(self):
        fake = Fake({"ci.yml": BAD})
        reader = remote_workflows.Reader(remote_workflows.anonymous_reader(fake), lambda: "someone")
        reader.refresh("tool", 10)
        self.assertEqual(reader.texts("tool"), {"ci.yml": BAD})
        urls = [r.full_url for r in fake.requests]
        self.assertEqual(urls, ["https://api.github.com/repos/someone/tool/contents/.github/workflows", "https://raw.githubusercontent.com/someone/tool/HEAD/.github/workflows/ci.yml"])
        for request in fake.requests:
            self.assertFalse({k.lower() for k in request.headers} & {"authorization", "cookie", "x-github-token"})

    def test_a_file_that_did_not_change_is_not_read_again(self):
        fake = Fake({"ci.yml": BAD})
        reader = remote_workflows.Reader(remote_workflows.anonymous_reader(fake), lambda: "o")
        reader.refresh("r", 10)
        before = len(fake.requests)
        reader.refresh("r", 10)
        self.assertEqual(len(fake.requests) - before, 1)      # the listing again, no file

    def test_a_big_file_is_cut_and_a_listing_that_is_too_big_is_refused(self):
        read = remote_workflows.anonymous_reader(Fake({"a.yml": "x" * (remote_workflows.MAX_BYTES + 50)}))
        with self.assertRaises(RuntimeError):
            read("repos/o/r/contents/.github/workflows/a.yml")
        with self.assertRaises(RuntimeError):
            remote_workflows.anonymous_reader(lambda r: Answer(b"[" + b" " * remote_workflows.MAX_LIST_BYTES + b"]"))("repos/o/r/contents/.github/workflows")

    def test_it_asks_for_nothing_else(self):
        fake = Fake()
        read = remote_workflows.anonymous_reader(fake)
        for endpoint in ("repos/o/r", "repos/o/r/contents/README.md", "repos/o/r/contents/.github/workflows/../../x.yml", "user", "repos/o/r/contents/.github/workflows/a.sh", "../x"):
            with self.assertRaises(RuntimeError):
                read(endpoint)
        self.assertEqual(fake.requests, [])

    def test_a_refusal_is_a_reason_and_never_a_clean_one(self):
        for code, reason in ((404, "not_found"), (403, "rate_limited"), (429, "rate_limited")):
            reader = remote_workflows.Reader(remote_workflows.anonymous_reader(Fake(code=code)), lambda: "o")
            reader.refresh("r", 10)
            state = reader.state("r")
            if reason == "not_found":
                self.assertEqual(state["state"], "ok")      # a folder that is not there: no workflows
                self.assertEqual(state["files"], 0)
            else:
                self.assertEqual((state["state"], state["reason"]), ("not_evaluable", reason))


class Cli(unittest.TestCase):
    def run_lint(self, config, fake, extra=()):
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            result = lint_workflows.lint_remote_status("someone/tool", read=remote_workflows.anonymous_reader(fake), anon=True, config=config)
        return result, err.getvalue()

    def test_with_the_setting_off_nothing_is_read(self):
        fake = Fake({"ci.yml": BAD})
        (found, failure), err = self.run_lint({}, fake)
        self.assertEqual((found, failure), ([], "anon_off"))
        self.assertEqual(fake.requests, [])
        self.assertIn("lint.anonymous_public", err)

    def test_an_air_gapped_monitor_never_reads(self):
        fake = Fake({"ci.yml": BAD})
        (found, failure), _err = self.run_lint({"airgapped": True, "lint": {"anonymous_public": True}}, fake)
        self.assertEqual(failure, "airgapped")
        self.assertEqual(fake.requests, [])

    def test_with_the_setting_on_the_findings_come_back(self):
        fake = Fake({"ci.yml": BAD})
        (found, failure), _err = self.run_lint({"lint": {"anonymous_public": True}}, fake)
        self.assertIsNone(failure)
        self.assertTrue(found)
        self.assertTrue(all(r.full_url.startswith(("https://api.github.com/", "https://raw.githubusercontent.com/")) for r in fake.requests))


if __name__ == "__main__":
    unittest.main()
