# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What GitHub does not answer is told apart: a check that the plan of the account does not have is N/A (plan), a refusal is N/A (no access), a feature that is off is N/A (off) - none of them a finding and none a
clean bill of health; and the actions of another private organisation that cannot be judged are left out of the supply chain findings and counted apart."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.delivery import supply  # noqa: E402
from github_actions_monitor.sentinels import sentinel_security as sec  # noqa: E402
from github_actions_monitor.sentinels import sentinel_supply as ss  # noqa: E402
from test_191_sentinel import NOW, build, quiet_repo  # noqa: E402

PLAN = {"message": "Upgrade to GitHub Pro or make this repository public to enable this feature."}
LOOSE = "name: ci\non: push\npermissions:\n  contents: read\njobs:\n  t:\n    runs-on: x\n    steps:\n      - uses: actions/checkout@v4\n      - uses: other-org/private-action@main\n      - uses: other-org/tools/.github/workflows/x.yml@v2\n"


class Registry:
    def __init__(self, sentinel):
        self.sentinel = sentinel

    def get(self, name):
        return self.sentinel if name == "security" else None


class WhyIsToldApart(unittest.TestCase):
    def test_the_three_reasons(self):
        self.assertEqual(sec.why_of(403, PLAN["message"]), "plan")
        self.assertEqual(sec.why_of(403, "Advanced Security must be enabled for this repository to use code scanning."), "plan")
        self.assertEqual(sec.why_of(403, "Resource not accessible by integration"), "permission")
        self.assertEqual(sec.why_of(403), "permission")
        self.assertEqual(sec.why_of(404, "Not Found"), "off")
        self.assertEqual(sec.why_of(451), "off")

    def test_the_plan_is_left_out_of_the_coverage_and_counted_apart_and_never_clean(self):
        sentinel, fake, _ = build(self, repos=("r1", "r2"))
        quiet_repo(fake)
        fake.set("code-scanning/alerts", 403, PLAN)
        fake.set("secret-scanning/alerts", 403, {"message": "Resource not accessible"})
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual((status["sources_readable"], status["sources_total"], status["sources_na_plan"]), (2, 4, 2))
        self.assertEqual(status["unavailable_why"], {"plan": {"code_scanning": 2}, "permission": {"secret": 2}})
        self.assertEqual(status["unavailable"]["code_scanning"], 2)
        self.assertEqual(sentinel.get_metrics()["security_sources_na_plan"], 2)

    def test_with_the_setting_off_the_plan_counts_as_a_source_that_could_not_be_read(self):
        sentinel, fake, _ = build(self, config={"plan_na": False}, repos=("r1", "r2"))
        quiet_repo(fake)
        fake.set("code-scanning/alerts", 403, PLAN)
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual((status["sources_readable"], status["sources_total"], status["sources_na_plan"]), (4, 6, 0))
        self.assertEqual(status["unavailable_why"], {"plan": {"code_scanning": 2}})

    def test_when_the_plan_has_none_of_what_weighs_the_level_is_unknown_and_the_score_has_no_part(self):
        sentinel, fake, _ = build(self, repos=("r1", "r2"))
        quiet_repo(fake)
        for fragment in ("dependabot/alerts", "code-scanning/alerts", "secret-scanning/alerts"):
            fake.set(fragment, 403, PLAN)
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual((status["sources_total"], status["sources_na_plan"]), (0, 6))
        self.assertEqual(status["level"], "unknown")
        self.assertIsNone(actions_monitor.score_security(Registry(sentinel), {}))

    def test_a_source_that_answers_again_forgets_its_reason(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("code-scanning/alerts", 403, PLAN)
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["unavailable_why"], {"plan": {"code_scanning": 1}})
        quiet_repo(fake)
        sentinel.tick(NOW + 10 ** 6)
        self.assertEqual(sentinel.get_status()["unavailable_why"], {})

    def test_the_setting_is_on_by_default_and_is_on_the_settings_page(self):
        self.assertTrue(sec.settings({})["plan_na"])
        self.assertFalse(sec.settings({"sentinels": {"security": {"plan_na": False}}})["plan_na"])
        self.assertTrue(sec.settings({"sentinels": {"security": {"plan_na": "no"}}})["plan_na"])
        self.assertIn("sentinels.security.plan_na", {row[2] for row in settings_api.ROWS})


class ActionsThatCannotBeJudged(unittest.TestCase):
    def test_the_matching_actions_are_left_out_and_counted(self):
        left = []
        found = supply.findings("r", {"x.yml": LOOSE}, None, "acme", (), ["other-org/*"], left)
        self.assertEqual(sorted(f["signal"] for f in found), ["unpinned"])      # only actions/checkout@v4 is reported
        self.assertEqual(sorted(x["detail"] for x in left), ["other-org/private-action@main", "other-org/tools/.github/workflows/x.yml@v2"])

    def test_nothing_is_left_out_without_the_setting_and_the_match_is_by_owner_and_repo(self):
        self.assertEqual(sorted(f["signal"] for f in supply.findings("r", {"x.yml": LOOSE}, None, "acme")), ["mutable_ref", "unpinned", "unpinned"])
        self.assertTrue(supply.left_out("Other-Org/Private-Action@main", ["other-org/private-*"]))
        self.assertFalse(supply.left_out("other-org2/private-action@main", ["other-org/*"]))
        self.assertFalse(supply.left_out("docker://alpine:3", ["other-org/*"]))

    def test_the_setting_takes_only_owner_slash_repo_patterns(self):
        self.assertEqual(ss.settings({"sentinels": {"supply": {"ignore_uses": ["a/b", "x", "a b/c", 3, "o/*"]}}})["ignore_uses"], ["a/b", "o/*"])
        self.assertEqual(ss.settings({})["ignore_uses"], [])
        self.assertTrue(settings_api.check_value("sentinels.supply.ignore_uses", ["org/*"])[0])
        self.assertFalse(settings_api.check_value("sentinels.supply.ignore_uses", ["no slash"])[0])


if __name__ == "__main__":
    unittest.main()
