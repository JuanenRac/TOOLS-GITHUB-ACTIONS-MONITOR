# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The section "Compare periods" of the Charts tab and its texts: the section and its controls are in the page, hidden until the answer says the comparison is on, every text exists in the eight
languages (also the ones the page builds from a figure, a direction or a reason), and the read API v1 serves the route under its prefix."""
import json
import re
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.compare import compare_service as service, metrics  # noqa: E402
from github_actions_monitor.scoring import ledger as score_ledger  # noqa: E402
from github_actions_monitor.storage import file_storage, runtime  # noqa: E402
from test_compare_service import NOW, make_ledger  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


def catalogue(lang):
    return json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


class Page(unittest.TestCase):
    def test_the_section_and_its_controls_are_in_the_charts_tab(self):
        charts = PAGE[PAGE.index('id="t-charts"'):PAGE.index('id="t-repos"')]
        self.assertIn('id="cmp-sec" hidden', charts)      # hidden until the answer says the comparison is on
        for ident in ("cmp-window", "cmp-days", "cmp-base", "cmp-state", "cmp-rows", "cmp-alerts", "cmp-changes"):
            self.assertIn(f'id="{ident}"', charts)
        self.assertIn('if(t==="charts")cmpLoad();', PAGE)
        self.assertIn("if(!sec||LITE)return;", PAGE)      # the Lite edition has no such route

    def test_every_text_the_page_the_command_and_the_report_use_exists_in_the_eight_languages(self):
        names = ["ui.cmp_m_" + m for m in metrics.METRICS] + [f"ui.cmp_dir_{d}" for d in ("better", "worse", "same")] + [f"ui.cmp_reason_{r}" for r in ("no_history", "watched_briefly", "history_too_short", "before_history")]
        names += [f"ui.cmp_state_{s}" for s in ("calibrating", "baseline_unavailable")] + [f"ui.cmp_b_{b}" for b in ("previous", "year_ago")] + [f"ui.cmp_d_{d}" for d in ("all", "workdays", "weekend")]
        names += ["ui.cmp_w7", "ui.cmp_w30"] + sorted(n for n in set(re.findall(r'"(ui\.cmp_[a-z0-9_]+)"', PAGE)) if not n.endswith("_"))
        names += [f"cfg.f.compare.{k}" for k in ("enabled", "default_window_days", "default_days_filter", "workdays", "min_runs_per_window", "min_days_of_history", "min_resolved", "min_snapshots", "min_repo_runs", "top_changes", "include_in_report", "cache_seconds")]
        names += [n.replace("cfg.f.", "cfg.h.") for n in names if n.startswith("cfg.f.")] + ["ui.cfg_b_compare", "report.h_compare", "report.compare_line", "report.compare_none", "cli.compare_head", "cli.compare_off", "cli.compare_row", "cli.compare_row_none"]
        for lang in LANGS:
            cat = catalogue(lang)
            self.assertEqual([n for n in names if not cat.get(n, "").strip()], [], lang)
        english = catalogue("en")
        for lang in LANGS[1:]:
            cat = catalogue(lang)
            same = [n for n in names if cat[n] == english[n] and n not in ("cli.compare_row_none",)]
            self.assertEqual(same, [], f"{lang} has untranslated texts")

    def test_the_figures_the_page_formats_are_the_ones_the_service_gives(self):
        for name in metrics.METRICS:
            self.assertIn(f"{name}:", PAGE[PAGE.index("const CMP_FMT"):PAGE.index("async function cmpLoad")])


class ReadApiV1(unittest.TestCase):
    def test_the_route_is_served_under_the_prefix_when_the_api_is_on(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        storage = file_storage.FileStorage(Path(tmp.name))
        storage.save_doc("alpha", score_ledger.LEDGER_DOC, make_ledger())
        service.clear_cache()
        self.addCleanup(service.clear_cache)
        server = ThreadingHTTPServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        config = {"compare": {"enabled": True, "min_runs_per_window": 5}, "api": {"v1_enabled": True}}
        with mock.patch.object(runtime, "process_storage", return_value=(storage, "alpha")), mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config), \
                mock.patch("time.time", return_value=NOW), mock.patch.dict(actions_monitor.LITE, {"on": False}), mock.patch.dict(actions_monitor.DEMO, {"on": False}):
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/api/v1/compare?days=workdays", timeout=10) as answer:
                body = json.loads(answer.read())
                self.assertEqual((answer.status, answer.headers.get("X-API-Version")), (200, "1"))
        self.assertEqual((body["state"], body["days"], body["metrics"]["red_rate"]["now"]), ("compared", "workdays", 0.0))


if __name__ == "__main__":
    unittest.main()
