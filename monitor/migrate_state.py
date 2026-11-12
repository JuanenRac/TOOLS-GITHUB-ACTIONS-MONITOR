#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Brings the files written by versions before 1.5.0 to the English names, without losing anything.

    python migrate_state.py             # dry run: says what it would do and changes nothing
    python migrate_state.py --apply     # copies the old files to the new names (the old ones stay where they are)
    python migrate_state.py --apply --move   # renames them instead of copying

What it looks at (only these, and never overwrites a file that already exists under the new name):
  events_monitor.jsonl, events_state.json   <- eventos_monitor.jsonl, eventos_estado.json   (next to this file)
  SENTINEL_REPORT_*.txt / .json             <- PARTE_CENTINELA_*.txt / .json                (the audit folder)
  RELEASE_CANDIDATES.txt                    <- CANDIDATAS_RELEASE.txt                       (the audit folder)
  <signed_dir>/batches/batch_*.json         <- <signed_dir>/lotes/lote_*.json
  report_history_days in actions_monitor.json <- parte_history_days (a copy of the file is kept before it is written)
The monitor still READS the old names, so this is optional: it only makes the history appear under the new names too.
Exit code: 0 when done (or nothing to do), 2 when it could not write something.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import i18n  # noqa: E402
import platform_compat  # noqa: E402
import workspace  # noqa: E402
import private_io


def plan(root=None, audit=None, signed=None):
    """[(old_path, new_path)] of the files that exist under an old name and not yet under the new one."""
    root = Path(root) if root else HERE
    audit = Path(audit) if audit else workspace.audit_dir_soft()
    signed = Path(signed) if signed else workspace.signed_dir_soft()
    pairs = [(root / "eventos_monitor.jsonl", root / "events_monitor.jsonl"), (root / "eventos_estado.json", root / "events_state.json"),
             (audit / "CANDIDATAS_RELEASE.txt", audit / "RELEASE_CANDIDATES.txt")]
    if audit.is_dir():
        for old in sorted(audit.glob("PARTE_CENTINELA_*")):
            if old.suffix in (".txt", ".json"):
                pairs.append((old, old.with_name(old.name.replace("PARTE_CENTINELA_DIA_", "SENTINEL_REPORT_DAY_", 1).replace("PARTE_CENTINELA_", "SENTINEL_REPORT_", 1))))
    old_dir = signed / "lotes"
    if old_dir.is_dir():
        for old in sorted(old_dir.glob("lote_*.json")):
            pairs.append((old, signed / "batches" / old.name.replace("lote_", "batch_", 1)))
    return [(o, n) for o, n in pairs if o.is_file()]


def config_rename(config_path):
    """True when actions_monitor.json still has parte_history_days and no report_history_days."""
    try:
        data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and "parte_history_days" in data and "report_history_days" not in data


def run(apply=False, move=False, root=None, audit=None, signed=None, config_path=None, out=print):
    t = i18n.t
    status = 0
    pairs = plan(root, audit, signed)
    config_path = Path(config_path) if config_path else HERE / "actions_monitor.json"
    todo = 0
    for old, new in pairs:
        if new.exists():
            out(t("mig.exists", old=old.name, new=new.name))
            continue
        todo += 1
        if not apply:
            out(t("mig.would", old=old.name, new=new.name))
            continue
        try:
            new.parent.mkdir(parents=True, exist_ok=True)
            (shutil.move if move else shutil.copy2)(str(old), str(new))
            out(t("mig.done_file", old=old.name, new=new.name))
        except OSError as error:
            out(t("mig.failed", old=old.name, error=error))
            status = 2
    if config_rename(config_path):
        todo += 1
        if not apply:
            out(t("mig.would_key"))
        else:
            try:
                backup = config_path.with_name(config_path.name + ".before_migration")
                shutil.copy2(str(config_path), str(backup))
                data = json.loads(config_path.read_text(encoding="utf-8"))
                data["report_history_days"] = data.pop("parte_history_days")
                private_io.write_private(config_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
                out(t("mig.done_key", backup=backup.name))
            except (OSError, ValueError) as error:
                out(t("mig.failed", old=config_path.name, error=error))
                status = 2
    if not todo:
        out(t("mig.nothing"))
    elif not apply:
        out(t("mig.dry_run", n=todo))
    return status


def main(argv=None):
    i18n.cli_language()
    platform_compat.console_utf8()
    parser = argparse.ArgumentParser(description=i18n.t("mig.description"))
    parser.add_argument("--apply", action="store_true", help=i18n.t("mig.help_apply"))
    parser.add_argument("--move", action="store_true", help=i18n.t("mig.help_move"))
    parser.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = parser.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    return run(apply=args.apply, move=args.move)


if __name__ == "__main__":
    sys.exit(main())
