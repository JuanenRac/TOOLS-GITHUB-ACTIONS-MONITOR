# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The check of release files adapts to the project: checksum and signature files can stop being required, a release without files can be accepted, tags with a prefix are compared and the
betas of one day of a calendar version are one version. Synthetic releases, no network."""
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api as sa  # noqa: E402
from github_actions_monitor.app import surface  # noqa: E402


def cfg(**release):
    base = surface.settings({})
    base["checks"]["release_assets"].update(release)
    return base


class Assets(unittest.TestCase):
    def test_defaults_ask_for_what_they_always_asked(self):
        self.assertEqual(surface.asset_template("firmware-build.yml", cfg()), ["sha256", "sig"])
        self.assertEqual(surface.asset_template("apk-build.yml", cfg()), ["sha256"])
        self.assertEqual(surface.missing_assets(None, ["sha256", "sig"]), ["assets"])
        self.assertEqual(surface.missing_assets({"sha256": True, "sig": False}, ["sha256", "sig"]), ["sig"])

    def test_no_signature_required(self):
        self.assertEqual(surface.asset_template("firmware-build.yml", cfg(require_signature=False)), ["sha256"])

    def test_no_checksum_required(self):
        self.assertEqual(surface.asset_template("firmware-build.yml", cfg(require_sha256=False)), ["sig"])
        self.assertEqual(surface.asset_template("apk-build.yml", cfg(require_sha256=False)), [])

    def test_a_project_that_asks_for_nothing_is_never_missing_anything(self):
        required = surface.asset_template("firmware-build.yml", cfg(require_sha256=False, require_signature=False))
        self.assertEqual(required, [])
        self.assertEqual(surface.missing_assets({"sha256": False, "sig": False}, required), [])
        self.assertEqual(surface.missing_assets(None, required), [])

    def test_a_release_without_files_can_be_accepted(self):
        self.assertEqual(surface.missing_assets(None, ["sha256", "sig"], allow_empty=True), [])
        self.assertEqual(surface.missing_assets({"sha256": True, "sig": False}, ["sha256", "sig"], allow_empty=True), ["sig"])      # a release WITH files still has to be complete

    def test_the_bad_types_of_a_configuration_keep_the_defaults(self):
        merged = surface.settings({"sentinel": {"surface": {"checks": {"release_assets": {"require_sha256": "no", "allow_empty": 1}, "tag_vs_version": {"prefixes": "cli-"}}}}})
        self.assertTrue(merged["checks"]["release_assets"]["require_sha256"])
        self.assertFalse(merged["checks"]["release_assets"]["allow_empty"])
        self.assertEqual(merged["checks"]["tag_vs_version"]["prefixes"], [])


class Tags(unittest.TestCase):
    def test_prefixes(self):
        self.assertEqual(surface.strip_tag_prefix("cli-v1.2.0", ["server-", "cli-"]), "v1.2.0")
        self.assertEqual(surface.strip_tag_prefix("v1.2.0", ["cli-"]), "v1.2.0")
        self.assertEqual(surface.strip_tag_prefix("cli-v1.2.0", []), "cli-v1.2.0")
        self.assertTrue(surface.is_version_tag(surface.strip_tag_prefix("cli-v1.2.0", ["cli-"])))
        self.assertFalse(surface.is_version_tag("cli-v1.2.0"))      # without the prefix named, it is not a version tag at all (nothing is compared)

    def test_calendar_betas_of_one_day_are_one_version(self):
        self.assertEqual(surface.compare_versions("2026.11.16-beta.2", "2026.11.16"), 1)      # the false alarm of "tag after manifest"
        self.assertEqual(surface.compare_versions(surface.release_part("2026.11.16-beta.2"), surface.release_part("2026.11.16")), 0)
        self.assertEqual(surface.release_part("v2026.11.16b3"), "2026.11.16")
        self.assertEqual(surface.release_part("1.2.3.4-rc1"), "1.2.3.4")
        self.assertEqual(surface.release_part("nightly"), "nightly")

    def snapshot_rows(self, tag, manifest, **tag_cfg):
        import test_surface
        case = test_surface.SurfaceInTheSnapshot("test_every_section_finds_its_case")
        inp = case.inp()
        inp["cfg"]["checks"]["tag_vs_version"].update(tag_cfg)
        inp["repo_info"]["R"]["release"]["tagName"] = tag
        inp["scans"]["R"]["manifest"]["version"] = manifest
        inp["scans"]["R"]["changelog_top"] = manifest
        return {s["key"]: s["rows"] for s in surface.build(inp)["sections"]}["tag_vs_version"]

    def test_in_the_panel(self):
        self.assertEqual(len(self.snapshot_rows("v2026.11.16-beta.2", "2026.11.16")), 1)      # default: reported
        self.assertEqual(self.snapshot_rows("v2026.11.16-beta.2", "2026.11.16", prerelease_ok=True), [])
        self.assertEqual(self.snapshot_rows("cli-v1.0.0", "1.0.0"), [])      # a prefixed tag is not compared by default
        self.assertEqual(len(self.snapshot_rows("cli-v2.0.0", "1.0.0", prefixes=["cli-"])), 1)
        self.assertEqual(self.snapshot_rows("cli-v1.0.0", "1.0.0", prefixes=["cli-"]), [])


class Page(unittest.TestCase):
    def test_the_settings_are_on_the_surface_tab(self):
        for key in ("release_assets.require_sha256", "release_assets.require_signature", "release_assets.allow_empty", "tag_vs_version.prefixes", "tag_vs_version.prerelease_ok"):
            full = "sentinel.surface.checks." + key
            self.assertEqual(sa.FIELDS[full][0], "surface", key)
        self.assertTrue(sa.check_value("sentinel.surface.checks.tag_vs_version.prefixes", ["cli-"])[0])
        self.assertFalse(sa.check_value("sentinel.surface.checks.tag_vs_version.prefixes", ["a b"])[0])
        self.assertFalse(sa.check_value("sentinel.surface.checks.release_assets.allow_empty", "yes")[0])


if __name__ == "__main__":
    unittest.main()
