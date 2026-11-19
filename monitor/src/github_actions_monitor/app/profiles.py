# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Profiles: a few ready-made groups of settings for the three usual ways of using the monitor, chosen in Settings > Basic and in the first-start guide.

  owner_team        the account of a person or a team that sets its own conventions: the strict, original rules (every setting of the profiles back to its default)
  open_source_org   an open-source organisation: protection judged by the rules in force, files provided by the community profile and the `.github` repository, forks and archived repositories
                    only when they are maintained, Renovate counts, releases may live in a package registry, bots counted apart
  solo_developer    one person with a few repositories: the same, plus the checks that need a team switched off

A profile is only a list of values for settings that exist; applying one writes them through the same checked path as the Settings page (nothing outside the schema, every value validated, a backup of the
previous file). A setting that this version does not have is left out of the list, so a profile never fails because of a missing key. Nothing changes until a profile is chosen.
"""
from github_actions_monitor.app import settings_api

ORDER = ("owner_team", "open_source_org", "solo_developer")

_STRICT = {
    "sentinel.hygiene.ruleset_mode": "name", "sentinel.hygiene.skip": [], "sentinel.hygiene.community_fallback": False,
    "discovery.skip_archived": True, "discovery.fork_policy": "show",
    "lint.unpinned_own": "same", "lint.rules.no_timeout.enabled": False, "lint.rules.secrets_inherit.enabled": False, "lint.rules.own_action_main.enabled": False, "lint.rules.permissions_top.enabled": False,
    "sentinel.surface.checks.release_assets.require_sha256": True, "sentinel.surface.checks.release_assets.require_signature": True, "sentinel.surface.checks.release_assets.allow_empty": False,
    "sentinel.surface.checks.tag_vs_version.prerelease_ok": False,
    "sentinel.bots_apart": False,
}

PRESETS = {
    "owner_team": dict(_STRICT),
    "open_source_org": {
        **_STRICT,
        "sentinel.hygiene.ruleset_mode": "effective", "sentinel.hygiene.skip": ["label"], "sentinel.hygiene.community_fallback": True,
        "discovery.fork_policy": "auto",
        "lint.unpinned_own": "info", "lint.rules.no_timeout.enabled": True, "lint.rules.secrets_inherit.enabled": True, "lint.rules.own_action_main.enabled": True, "lint.rules.permissions_top.enabled": True,
        "sentinel.surface.checks.release_assets.require_signature": False, "sentinel.surface.checks.release_assets.allow_empty": True,
        "sentinel.surface.checks.tag_vs_version.prerelease_ok": True,
        "sentinel.bots_apart": True,
    },
    "solo_developer": {
        **_STRICT,
        "sentinel.hygiene.ruleset_mode": "effective", "sentinel.hygiene.skip": ["label", "schedule"], "sentinel.hygiene.community_fallback": True,
        "discovery.fork_policy": "skip_unless_ci",
        "lint.unpinned_own": "info",
        "sentinel.surface.checks.release_assets.require_signature": False, "sentinel.surface.checks.release_assets.allow_empty": True,
        "sentinel.surface.checks.tag_vs_version.prerelease_ok": True,
        "sentinel.bots_apart": True,
    },
}


def changes(profile):
    """{key: value} of one profile limited to the settings this version has and accepts; None for a name that is not a profile."""
    wanted = PRESETS.get(profile)
    if wanted is None:
        return None
    return {key: value for key, value in wanted.items() if key in settings_api.FIELDS and settings_api.check_value(key, value)[0]}


def listing(lite=False):
    """What the page needs: [{"id", "settings": {key: value}}] in order. The short page of the Lite edition has no profiles."""
    if lite:
        return []
    return [{"id": name, "settings": changes(name)} for name in ORDER]
