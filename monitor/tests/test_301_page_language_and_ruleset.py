# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Two things seen on a real monitor: texts the monitor translates for each request were asked for without the language of the page, and a branch protected by a ruleset stayed "unprotected"
after an update, because the ETags of its reads were kept when their answers were dropped and every "304 unchanged" was then read as "no"."""
import json
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from test_191_sentinel import NOW, build, quiet_repo  # noqa: E402

from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.families.posture import posture_engine  # noqa: E402
from github_actions_monitor.sentinels import sentinel_security as ss  # noqa: E402

MONITOR = Path(__file__).resolve().parents[1]
HEADERS = ('If-None-Match: "m1"', 'If-None-Match: "r1"')


def github_like(fake, rules=({"type": "deletion"}, {"type": "non_fast_forward"}), protected=True):
    """A branch protected only by a ruleset, as GitHub answers it: no classic protection, `protected` true and the active rules."""
    quiet_repo(fake)
    fake.answers = {"/protection": (404, {"message": "Branch not protected"}, ""), "rules/branches/": (200, list(rules), '"r1"'), "/branches/main": (200, {"protected": protected}, '"m1"'), **fake.answers}


def kept(folder, logic, facts):
    """The state left on disk: an open "unprotected" alert and the ETags of the two reads."""
    record = {"scanned": NOW - 10 ** 6, "etag": {"branch_meta": '"m1"', "branch_rules": '"r1"'}, "facts": dict({"default_branch": "main", "archived": False}, **facts), "unavailable": {}}
    if logic is not None:
        record["logic"] = logic
    stale = {"id": "security.branch_unprotected:r", "code": "security.branch_unprotected", "level": "warning", "repo": "r", "detail": {"branch": "main"}, "created_at": "x"}
    (folder / "security_state.json").write_text(json.dumps({"alerts": {stale["id"]: stale}, "per_repo": {"r": record}, "last_full_scan": None}), encoding="utf-8")


class ProtectedByARuleset(unittest.TestCase):
    def after_update(self, logic, facts):
        sentinel, fake, folder = build(self)
        github_like(fake)
        kept(folder, logic, facts)
        sentinel.state = ss.load_state(folder / "security_state.json")
        sentinel.tick(NOW)
        return sentinel, fake

    def test_the_state_of_the_published_version_is_read_again_in_full(self):
        # logic 2 is what 2.1.8 left on disk (judged "unprotected", the ETags kept and neither answer); no logic is what 2.1.7 left
        for logic, facts in ((2, {"branch_protected": False}), (None, {"branch_protected": True, "branch_rules": ["deletion"]})):
            sentinel, fake = self.after_update(logic, facts)
            self.assertEqual(sentinel.get_alerts(), [], logic)
            self.assertTrue(sentinel.state["per_repo"]["r"]["facts"]["branch_protected"], logic)
            self.assertFalse(any(h in call for call in fake.calls for h in HEADERS), logic)

    def test_an_etag_without_its_answer_is_not_sent(self):
        sentinel, fake = self.after_update(ss.BRANCH_LOGIC, {})
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertFalse(any(h in call for call in fake.calls for h in HEADERS))

    def test_unchanged_answers_keep_the_branch_protected(self):
        sentinel, fake, _ = build(self)
        github_like(fake)
        for round_ in range(3):
            sentinel.tick(NOW + round_ * 2000)
            self.assertEqual(sentinel.get_alerts(), [], round_)
        self.assertTrue(any('If-None-Match: "r1"' in call for call in fake.calls))

    def test_a_removed_ruleset_is_still_seen(self):
        sentinel, fake, _ = build(self)
        github_like(fake, protected=False)
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_alerts(), [])
        fake.set("rules/branches/", 200, [], '"r2"')
        sentinel.tick(NOW + 2000)
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["security.branch_unprotected"])

    def test_an_unarchived_repository_is_read_in_full(self):
        sentinel, fake, _ = build(self)
        github_like(fake)
        sentinel.tick(NOW)
        fake.set("repos/acme/r", 200, {"default_branch": "main", "archived": True}, '"repo2"')
        sentinel.tick(NOW + 2000)
        self.assertEqual(set(sentinel.state["per_repo"]["r"]["etag"]), {"repo"})


class TheLanguageOfThePage(unittest.TestCase):
    def test_the_requests_for_translated_texts_say_the_language_of_the_page(self):
        page = (MONITOR / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        posture = (MONITOR / "src" / "github_actions_monitor" / "families" / "posture" / "page.js").read_text(encoding="utf-8")
        self.assertIn('fetch("/api/alerts?"+qlang()', page)
        self.assertIn('/health?"+qlang()', page)
        self.assertIn("alertsTick();if(CFG.groups.length)", page)      # asked again when the language is changed
        self.assertIn('fetch("/api/posture?"+qlang())', posture)
        self.assertIn("drawn===LANG", posture)

    def test_the_posture_titles_are_those_of_the_language_of_the_request(self):
        item = {"check": "branch.unprotected", "item": "main"}
        with i18n.use_language("es"):
            self.assertEqual(posture_engine.describe(item)["title"], i18n.tl("es", "ui.posture.c.branch_unprotected"))
        self.assertNotEqual(i18n.tl("es", "ui.posture.c.branch_unprotected"), i18n.tl("en", "ui.posture.c.branch_unprotected"))


if __name__ == "__main__":
    unittest.main()
