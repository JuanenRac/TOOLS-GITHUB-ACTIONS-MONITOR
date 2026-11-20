# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""OpenTelemetry with the conventions of CI/CD and one span per job, several workspaces, the long windows of the comparison and the toolbox of the command line (events export). No network."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api, workspace  # noqa: E402
from github_actions_monitor.compare import compare_service, config as compare_config  # noqa: E402
from github_actions_monitor.integrations import event_export, otlp  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402

RUN = {"repo": "r", "id": 7, "name": "CI", "branch": "main", "event": "push", "conclusion": "failure", "started": "2026-01-01T00:00:00Z", "seconds": 90, "url": "https://github.com/o/r/actions/runs/7", "attempt": 2}


def job_record(**extra):
    base = {"event": "workflow_job", "status": "completed", "repo": "r", "run_id": 7, "job_id": 70, "job": "build", "workflow": "CI", "conclusion": "success", "attempt": 2, "labels": ["self-hosted", "gpu"],
            "runner_name": "box-1", "runner_group": "Default", "queue": 12, "job_started": "2026-01-01T00:00:10Z", "job_completed": "2026-01-01T00:01:10Z", "url": "https://github.com/o/r/actions/runs/7/job/70"}
    base.update(extra)
    return base


def names(span):
    return {a["key"]: a["value"].get("stringValue", a["value"].get("intValue")) for a in span["attributes"]}


class Spans(unittest.TestCase):
    def setUp(self):
        otlp.JOBS.clear()
        otlp.STATE.update({"sent": set(), "total": 0, "last_ok": None, "last_error": "", "next": 0.0})

    def test_the_default_span_is_what_it_was(self):
        span = otlp.span(RUN)
        self.assertEqual(span["name"], "gha.run")
        self.assertFalse(any(k.startswith(("cicd.", "vcs.")) for k in names(span)))

    def test_the_conventions_of_cicd_add_attributes_and_the_name(self):
        span = otlp.span(RUN, cicd=True)
        attrs = names(span)
        self.assertEqual(span["name"], "RUN CI")
        self.assertEqual((attrs["cicd.pipeline.name"], attrs["cicd.pipeline.run.id"], attrs["cicd.pipeline.result"], attrs["cicd.pipeline.run.attempt"]), ("CI", "7", "failure", "2"))
        self.assertEqual((attrs["vcs.repository.name"], attrs["vcs.repository.ref.name"], attrs["vcs.repository.ref.type"]), ("r", "main", "branch"))
        self.assertIn("gha.repo", attrs)      # the old attributes stay
        self.assertEqual(otlp.span({**RUN, "conclusion": "cancelled"}, cicd=True)["attributes"][-1]["key"] in ("cicd.pipeline.run.attempt",), True)
        self.assertEqual(names(otlp.span({**RUN, "conclusion": "cancelled"}, cicd=True))["cicd.pipeline.result"], "cancellation")

    def test_a_job_span_is_the_child_of_the_span_of_its_run_in_the_same_trace(self):
        run, job = otlp.span(RUN), otlp.job_span(job_record())
        self.assertEqual(job["traceId"], run["traceId"])
        self.assertEqual(job["parentSpanId"], run["spanId"])
        self.assertNotEqual(job["spanId"], run["spanId"])
        self.assertEqual(job["spanId"], otlp.job_span(job_record())["spanId"])      # a job keeps its identifier
        self.assertEqual(int(job["endTimeUnixNano"]) - int(job["startTimeUnixNano"]), 60 * 10**9)
        attrs = names(job)
        self.assertEqual((attrs["gha.runner"], attrs["gha.labels"], attrs["gha.queue_seconds"]), ("box-1", "self-hosted,gpu", "12"))
        self.assertEqual(names(otlp.job_span(job_record(), cicd=True))["cicd.pipeline.task.name"], "build")

    def test_only_a_finished_job_with_its_times_is_kept(self):
        self.assertTrue(otlp.note_job(job_record()))
        self.assertFalse(otlp.note_job(job_record(status="in_progress")))
        self.assertFalse(otlp.note_job(job_record(job_started="")))
        self.assertFalse(otlp.note_job({"event": "workflow_run"}))
        self.assertEqual(len(otlp.JOBS), 1)
        for i in range(otlp.MAX_JOBS + 10):
            otlp.note_job(job_record(job_id=i))
        self.assertEqual(len(otlp.JOBS), otlp.MAX_JOBS)

    def export(self, cfg):
        sent = []
        otlp.note_job(job_record())
        data = {"runs": [dict(RUN, status="completed")], "figures": {"active": 1}}
        result = otlp.export({"otlp": {"enabled": True, "endpoint": "http://127.0.0.1:4318", **cfg}}, data, "2.1.7", now=1000.0, post=lambda request: sent.append(json.loads(request.data)))
        return result, sent

    def test_the_jobs_travel_only_when_asked_and_only_once(self):
        result, sent = self.export({})
        self.assertEqual(result["sent_spans"], 1)      # the run only
        otlp.STATE["sent"].clear()
        otlp.STATE["next"] = 0.0
        result, sent = self.export({"job_spans": True, "cicd_conventions": True})
        spans = sent[0]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        self.assertEqual((result["sent_spans"], sorted(s["name"] for s in spans)), (2, ["RUN CI", "TASK build"]))
        otlp.STATE["next"] = 0.0
        again = otlp.export({"otlp": {"enabled": True, "endpoint": "http://127.0.0.1:4318", "job_spans": True}}, {"runs": [dict(RUN, status="completed")], "figures": {}}, "2.1.7", now=2000.0, post=lambda r: sent.append(1))
        self.assertEqual(again["sent_spans"], 0)

    def test_the_webhook_gives_the_fields_of_a_job(self):
        body = json.dumps({"repository": {"name": "r", "full_name": "o/r"}, "workflow_job": {"id": 70, "run_id": 7, "name": "build", "workflow_name": "CI", "status": "completed", "conclusion": "success",
                           "created_at": "2026-01-01T00:00:00Z", "started_at": "2026-01-01T00:00:10Z", "completed_at": "2026-01-01T00:01:10Z", "labels": ["self-hosted"], "runner_name": "box-1"}}).encode()
        record = webhook.parse_event("workflow_job", body)
        self.assertEqual((record["job_started"], record["job_completed"]), ("2026-01-01T00:00:10Z", "2026-01-01T00:01:10Z"))
        self.assertNotIn("job_started", webhook.LIVE_FIELDS)
        self.assertTrue(otlp.note_job(record))

    def test_the_settings_are_checked(self):
        self.assertEqual((otlp.settings({"otlp": {"job_spans": "yes"}})["job_spans"], otlp.settings({"otlp": {"cicd_conventions": True}})["cicd_conventions"]), (False, True))


class Workspaces(unittest.TestCase):
    CFG = {"workspaces": {"list": ["work=/data/work", "home=/data/home", "bad entry", "net=//server/share", "url=https://x/y", "work=/other"], "active": "home"}}

    def test_only_a_folder_of_this_computer_is_a_workspace(self):
        found = workspace.named_workspaces(self.CFG)
        self.assertEqual(sorted(found), ["home", "work"])
        self.assertEqual(found["work"], Path("/data/work"))      # the first of a repeated name wins

    def test_the_active_one_and_a_name_that_is_not_in_the_list(self):
        self.assertEqual(workspace.active_workspace(self.CFG)[0], "home")
        self.assertIsNone(workspace.active_workspace({"workspaces": {"list": ["a=/x"], "active": "b"}}))
        self.assertIsNone(workspace.active_workspace({}))

    def test_the_root_follows_the_active_workspace_unless_the_environment_says_otherwise(self):
        with mock.patch.object(workspace, "_raw_config", return_value=self.CFG), mock.patch.dict("os.environ", {}, clear=False):
            for name in ("MONITOR_ROOT", "JUANENRAC_ROOT"):
                __import__("os").environ.pop(name, None)
            self.assertEqual(workspace.workspace_root(), Path("/data/home"))
            with mock.patch.dict("os.environ", {"MONITOR_ROOT": "/env/root"}):
                self.assertEqual(workspace.workspace_root(), Path("/env/root"))

    def test_describe_says_which_folders_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = workspace.describe({"workspaces": {"list": [f"here={tmp}", "gone=/no/such/folder/ever"], "active": "here"}})
        self.assertEqual({w["name"]: (w["folder_exists"], w["active"]) for w in info["workspaces"]}, {"here": (True, True), "gone": (False, False)})

    def test_the_settings_refuse_a_network_address(self):
        self.assertTrue(settings_api.check_value("workspaces.list", ["a=/x/y", "b=C:/clones"])[0])
        self.assertFalse(settings_api.check_value("workspaces.list", ["a=//server/share"])[0])
        self.assertTrue(settings_api.check_value("workspaces.active", "home")[0])
        self.assertFalse(settings_api.check_value("workspaces.active", "no good!")[0])
        self.assertTrue(settings_api.WORKSPACE_RE.match("a=/x/y"))
        for bad in ("a=//server/share", "a=\\\\server\\share", "a=https://x", "=x", "a b=/x"):
            self.assertFalse(settings_api.WORKSPACE_RE.match(bad), bad)


class Progressive(unittest.TestCase):
    def test_the_defaults_and_the_bounds(self):
        self.assertEqual((compare_config.settings({})["progressive"], compare_config.settings({})["progressive_days"]), (False, 7))
        self.assertEqual(compare_config.settings({"compare": {"progressive": True, "progressive_days": 99}})["progressive_days"], 7)
        self.assertEqual(compare_config.settings({"compare": {"progressive": True, "progressive_days": 3}})["progressive_days"], 3)

    def test_a_long_window_is_answered_at_once_and_finished_in_the_background(self):
        cfg = {"compare": {"enabled": True, "progressive": True, "progressive_days": 7}}
        calls = []

        def fake(storage, account, raw, ask, now, zone):
            calls.append(dict(ask))
            return {"state": "compared", "ask": dict(ask)}
        compare_service.clear_cache()
        with mock.patch.object(compare_service, "_compute", side_effect=fake):
            first = compare_service.build(object(), "acc", cfg, {"window": "30d"})
            self.assertEqual(first["ask"]["window"], "7d")
            self.assertEqual(first["partial"], {"requested_days": 30, "shown_days": 7, "completing": True})
            for _ in range(100):
                if not compare_service._COMPLETING:
                    break
                time.sleep(0.02)
            second = compare_service.build(object(), "acc", cfg, {"window": "30d"})
        self.assertNotIn("partial", second) if second.get("ask", {}).get("window") == "30d" else None
        self.assertIn({"window": "30d"}, calls)      # the whole window was computed in the background
        compare_service.clear_cache()

    def test_a_short_window_or_a_range_is_never_split(self):
        cfg = compare_config.settings({"compare": {"progressive": True, "progressive_days": 7}})
        self.assertIsNone(compare_service._long_window({"window": "7d"}, cfg))
        self.assertIsNone(compare_service._long_window({"from": "1", "to": "2", "window": "30d"}, cfg))
        self.assertEqual(compare_service._long_window({"window": "30"}, cfg), 30)
        self.assertIsNone(compare_service._long_window({"window": "30d"}, compare_config.settings({})))


class Toolbox(unittest.TestCase):
    def events(self, folder):
        path = Path(folder) / "events.jsonl"
        rows = [{"at": "2026-01-01T10:00:00Z", "kind": "red_new", "repo": "a", "text": "x", "owner": "main"}, {"at": "2026-01-02T10:00:00Z", "kind": "resolved", "repo": "a"},
                {"at": "2026-01-02T11:00:00Z", "kind": "red_new", "repo": "b"}]
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n[1]\n", encoding="utf-8")
        return path

    def test_reading_skips_junk_and_summary_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = event_export.read_events(self.events(tmp))
            self.assertEqual(len(rows), 3)
            self.assertEqual(len(event_export.read_events(self.events(tmp), since="2026-01-02")), 2)
        report = event_export.summary(rows)
        self.assertEqual((report["events"], report["by_kind"], report["by_repo"], report["by_day"]), (3, {"red_new": 2, "resolved": 1}, {"a": 2, "b": 1}, {"2026-01-01": 1, "2026-01-02": 2}))
        self.assertEqual(event_export.read_events("/no/such/file"), [])

    def test_jsonl_and_csv_are_written_with_the_same_columns_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = event_export.read_events(self.events(tmp))
            done = event_export.write(rows, Path(tmp) / "out.csv", "csv")
            self.assertEqual((done["rows"], done["format"]), (3, "csv"))
            lines = (Path(tmp) / "out.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], ",".join(event_export.COLUMNS))
            self.assertEqual(len(lines), 4)
            event_export.write(rows, Path(tmp) / "out.jsonl", "jsonl")
            self.assertEqual(json.loads((Path(tmp) / "out.jsonl").read_text(encoding="utf-8").splitlines()[0])["repo"], "a")
            with self.assertRaises(event_export.ExportError) as error:
                event_export.write(rows, Path(tmp) / "out.csv", "csv")
            self.assertEqual(str(error.exception), "exists")

    def test_the_destination_is_checked(self):
        for bad, why in (("//server/share/x.csv", "network_path"), ("https://x/y.csv", "network_path"), ("/no/such/folder/x.csv", "no_folder")):
            with self.assertRaises(event_export.ExportError) as error:
                event_export.check_destination(bad)
            self.assertEqual(str(error.exception), why)
        with self.assertRaises(event_export.ExportError):
            event_export.write([], "x.xml", "xml")

    def test_a_missing_package_is_said_not_raised_as_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fmt, package in (("parquet", "pyarrow"), ("duckdb", "duckdb")):
                try:
                    __import__(package)
                except ImportError:
                    with self.assertRaises(event_export.ExportError) as error:
                        event_export.write([], Path(tmp) / f"x.{fmt}", fmt)
                    self.assertEqual(str(error.exception), "missing_package:" + package)
                    self.assertFalse((Path(tmp) / f"x.{fmt}").exists())

    def test_the_command_exists_in_the_parser_and_runs_offline(self):
        from github_actions_monitor.cli import monitor_cli
        self.assertIn("toolbox", monitor_cli.COMMANDS)
        parser = monitor_cli.build_parser()
        for action in monitor_cli.TOOLBOX_ACTIONS:
            self.assertEqual(parser.parse_args(["toolbox", action]).action, action)
        with tempfile.TemporaryDirectory() as tmp:
            events = self.events(tmp)
            from github_actions_monitor.data_pipeline import events as events_mod
            with mock.patch.object(events_mod, "EVENTS_FILE", events), mock.patch.object(monitor_cli, "toolconfig", create=True):
                ctx = {"action": "summary", "file": "", "force": False}
                payload, lines, code = monitor_cli.cmd_toolbox(ctx)
                self.assertEqual((payload["events"], code), (3, monitor_cli.EXIT_OK))
                payload, lines, code = monitor_cli.cmd_toolbox({"action": "export-events", "file": str(Path(tmp) / "all.csv"), "force": False})
                self.assertEqual((payload["rows"], payload["format"]), (3, "csv"))
                with self.assertRaises(monitor_cli.CliError):
                    monitor_cli.cmd_toolbox({"action": "export-events", "file": str(Path(tmp) / "all.xml"), "force": False})
                with self.assertRaises(monitor_cli.CliError):
                    monitor_cli.cmd_toolbox({"action": "nonsense", "file": "", "force": False})
                payload, lines, code = monitor_cli.cmd_toolbox({"action": "limits", "file": "50", "force": False})
                self.assertEqual(code, monitor_cli.EXIT_OK)
                self.assertTrue(any("repos_listed" in line for line in lines))
                payload, lines, code = monitor_cli.cmd_toolbox({"action": "workspaces", "file": "", "force": False})
                self.assertEqual(code, monitor_cli.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
