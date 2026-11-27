# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""GitHub Actions Monitor: the importable package. The code lives here (src/); the examples, the page and the catalogues of languages are in assets/; the data of the person who runs it (actions_monitor.json, caches, logs, accounts/) stay in the product folder, never inside src/."""


def _arm_restrictions():
    """security.read_only_strict and security.egress_policy hold for every process of the monitor, whatever its entry point (security/compliance_guard.py). Nothing happens while both are at their defaults."""
    from github_actions_monitor.security import compliance_guard
    compliance_guard.arm_from_file()


_arm_restrictions()
