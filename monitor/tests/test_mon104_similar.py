# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Alerts that look alike, without a model: a stable ranking, an empty list with a reason when nothing is alike, no mixing of what is not handed over, and the line in the explanation of an alert only when
`ai.similar.enabled` is on (it is off by default)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.health import repo_view  # noqa: E402
from github_actions_monitor.integrations import assistant, similar_alerts  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ai  # noqa: E402

NOW = 1_800_000_000.0


def alert(repo, title, ident=None, code="ci.red", workflow="build", cause=""):
    return {"id": ident or f"{code}:{repo}", "repo": repo, "code": code, "workflow": workflow, "title": title, "cause": cause, "since": "2026-01-01T00:00:00Z", "state": "open"}


class Ranking(unittest.TestCase):
    TARGET = alert("r1", "npm ci failed ENOTFOUND registry.npmjs.org", "t")

    def test_the_most_alike_comes_first_and_the_unlike_is_left_out(self):
        pool = [alert("r2", "cache restore took forever", "u2", code="ci.slow", workflow="deploy"), alert("r3", "npm ci failed ENOTFOUND registry.npmjs.org timeout", "u3"),
                alert("r4", "npm ci failed ENOTFOUND", "u4", workflow="test")]
        found = similar_alerts.find(self.TARGET, pool, 5)
        self.assertEqual([f["id"] for f in found], ["u3", "u4"])
        self.assertGreater(found[0]["score"], found[1]["score"])

    def test_the_same_alert_is_never_its_own_neighbour(self):
        self.assertEqual(similar_alerts.find(self.TARGET, [self.TARGET], 5), [])

    def test_ties_break_by_repository_and_id_so_the_order_is_stable(self):
        pool = [alert("rb", "npm ci failed ENOTFOUND", "z"), alert("ra", "npm ci failed ENOTFOUND", "y"), alert("ra", "npm ci failed ENOTFOUND", "x")]
        first = [f["id"] for f in similar_alerts.find(self.TARGET, pool, 5)]
        self.assertEqual(first, ["x", "y", "z"])
        self.assertEqual([f["id"] for f in similar_alerts.find(self.TARGET, list(reversed(pool)), 5)], first)

    def test_nothing_alike_is_an_empty_list_and_the_limit_is_kept(self):
        self.assertEqual(similar_alerts.find(self.TARGET, [alert("r9", "lint warnings", "q", code="x", workflow="lint")], 5), [])
        self.assertEqual(similar_alerts.find(self.TARGET, [], 5), [])
        many = [alert(f"r{i:02d}", "npm ci failed ENOTFOUND", f"i{i}") for i in range(30)]
        self.assertEqual(len(similar_alerts.find(self.TARGET, many, 3)), 3)
        self.assertEqual(len(similar_alerts.find(self.TARGET, many, 500)), 20)

    def test_numbers_hashes_and_filler_do_not_make_two_alerts_alike(self):
        a = alert("r1", "run 1234 failed at 5f3c9a1b2d", "a", code="p", workflow="w1")
        b = alert("r2", "run 9876 failed at 0a1b2c3d4e", "b", code="q", workflow="w2")
        self.assertEqual(similar_alerts.find(a, [b], 5), [])

    def test_garbage_in_the_pool_is_ignored(self):
        self.assertEqual(similar_alerts.find(self.TARGET, [None, 5, "x", {}], 5), [])

    def test_the_feed_rows_are_read_in_the_shape_that_is_compared(self):
        rows = similar_alerts.from_feed([{"id": "k", "class": "real", "repo": "r", "workflow": "build", "cause": "dns", "since": "s", "state": "resolved"}, "junk"])
        self.assertEqual(rows[0]["code"], "real")
        self.assertEqual(len(rows), 1)


def reader(history=None):
    open_alerts = [{"id": "ci.red:r1", "code": "ci.red", "level": "error", "sentinel": "ci", "repo": "r1", "title": "npm ci failed ENOTFOUND registry", "created_at": "2026-01-01T00:00:00Z"},
                   {"id": "ci.red:r2", "code": "ci.red", "level": "error", "sentinel": "ci", "repo": "r2", "title": "npm ci failed ENOTFOUND registry again", "created_at": "2026-01-02T00:00:00Z"}]
    views = [repo_view.repo_view(a["repo"], [], [{"repo": a["repo"], "workflow": "build"}], [], [a], None, {"ci": "healthy"}, "", NOW) for a in open_alerts]
    out = {"views": lambda: views, "score": lambda: {}}
    if history is not None:
        out["history"] = history
    return out


def ai_cfg(similar):
    return sentinel_ai.ai_config({"ai": {"provider": "ollama", "assistant": {"enabled": True}, "similar": similar}})


class InTheExplanation(unittest.TestCase):
    def ask(self, similar, history=None):
        seen = []
        out = assistant.ask("explain_alert", {"alert": "ci.red:r1", "repo": "r1"}, ai_cfg(similar), reader(history), lambda text: seen.append(text) or {"ok": True, "text": "x"})
        return out, seen[0]

    def test_off_by_default_nothing_is_added(self):
        self.assertEqual(sentinel_ai.ai_config({})["similar"], {"enabled": False, "max": 5})
        out, text = self.ask({})
        self.assertNotIn("SIMILAR", text)
        self.assertNotIn("similar", [s["tool"] for s in out["sources"]])

    def test_on_it_lists_the_neighbour_and_cites_it(self):
        out, text = self.ask({"enabled": True})
        self.assertIn("SIMILAR ALERTS (already seen):", text)
        self.assertIn("ci.red:r2", text)
        source = next(s for s in out["sources"] if s["tool"] == "similar")
        self.assertEqual(source["items"], ["ci.red:r2"])

    def test_it_also_reads_the_resolved_ones_the_feed_remembers(self):
        history = lambda: similar_alerts.from_feed([{"id": "old:1", "class": "ci.red", "repo": "r7", "workflow": "build", "cause": "npm ci failed ENOTFOUND registry", "since": "2025-12-01", "state": "resolved"}])      # noqa: E731
        out, text = self.ask({"enabled": True, "max": 5}, history)
        self.assertIn("old:1", text)
        self.assertIn("resolved", text)

    def test_a_history_that_breaks_never_stops_the_explanation(self):
        def broken():
            raise OSError("feed unreadable")
        out, text = self.ask({"enabled": True}, broken)
        self.assertTrue(out["ok"])
        self.assertIn("ci.red:r2", text)

    def test_nothing_alike_says_so(self):
        seen = []
        only = reader()
        only["views"] = lambda v=only["views"]: v()[:1]
        assistant.ask("explain_alert", {"alert": "ci.red:r1", "repo": "r1"}, ai_cfg({"enabled": True}), only, lambda text: seen.append(text) or {"ok": True, "text": "x"})
        self.assertIn("SIMILAR ALERTS: none", seen[0])

    def test_the_title_of_a_neighbour_is_data_between_marks(self):
        out, text = self.ask({"enabled": True})
        line = next(l for l in text.splitlines() if "ci.red:r2" in l and "title=" in l)
        self.assertRegex(line, r"title=\[\[DATA-[0-9a-f]{12}\]\].*\[\[/DATA-[0-9a-f]{12}\]\]")

    def test_the_limit_is_cleaned(self):
        self.assertEqual(assistant.similar_settings({"similar": {"enabled": "yes", "max": 99}}), {"enabled": False, "max": 5})
        self.assertEqual(assistant.similar_settings({"similar": {"enabled": True, "max": 7}}), {"enabled": True, "max": 7})


class TheTextsAndTheSkills(unittest.TestCase):
    def test_the_settings_exist_and_the_guide_and_the_skill_tell_it(self):
        from github_actions_monitor.app import settings_api
        for key in ("ai.similar.enabled", "ai.similar.max"):
            self.assertIn(key, settings_api.FIELDS)
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho"):
            self.assertIn("`ai.similar.enabled`", (HERE / "docs" / f"AI_CONNECTION{suffix}.md").read_text(encoding="utf-8"), suffix)
        self.assertIn("SIMILAR ALERTS", (HERE / "skills" / "internal" / "SKILL.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
