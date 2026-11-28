#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The checks that cut across the whole monitor, by area, so that a red one says which area it belongs to (the workflow cross-cutting.yml runs one job for each).

  py -3 tools/cross_cutting.py AREA     runs the test modules of one area
  py -3 tools/cross_cutting.py --list   prints the areas and their modules

It does not replace the suite: the same tests also run there."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "monitor" / "tests"
AREAS = {
    "isolation": ("test_compliance_guard", "test_194_accounts_scope", "test_i153_service_guards", "test_mon102_shared_files"),
    "network": ("test_netguard", "test_180_network", "test_178_proxy", "test_218_proxy_tunnel", "test_i551_552_egress_siem"),
    "webhook": ("test_215_webhook_skew", "test_289_webhook_size_first", "test_287_webhook_sender", "test_famf_webhook_receiver"),
    "export": ("test_compliance_export", "test_g3_export_workspaces", "test_g1_metrics"),
    "storage": ("test_compliance_records", "test_compliance_restore_tick", "test_storage_sqlite", "test_storage_migrate", "test_storage_retention", "test_timezone"),
    "full": ("test_compliance_guard", "test_182_service", "test_compliance_family"),
}


def main(argv):
    if argv == ["--list"]:
        for area, modules in AREAS.items():
            print(area, " ".join(modules))
        return 0
    if len(argv) != 1 or argv[0] not in AREAS:
        print("usage: cross_cutting.py " + "|".join(AREAS) + " | --list", file=sys.stderr)
        return 2
    code = 0
    for module in AREAS[argv[0]]:      # one process each, as the suite does: a module never sees what another one left
        print(f"== {argv[0]}: {module}", flush=True)
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(TESTS), "-p", module + ".py"], cwd=str(ROOT))
        if done.returncode:
            print(f"::error title=cross-cutting {argv[0]}::{module} failed", flush=True)
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
