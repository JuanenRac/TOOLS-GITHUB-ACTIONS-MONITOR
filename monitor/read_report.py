#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Prints, as short plain text, what the running monitor/sentinel says right now (report, red CI, builds stuck, unchecked repos, Dependabot count).

  py -3 read_report.py [--port 8765] [--json] [--lang CODE]

Reads http://127.0.0.1:<port>/api/sentinel (local only, no GitHub calls: it costs no API quota). If the monitor is not running it says so.
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # works also under `py -3 -I`
import export_status
import i18n
import platform_compat
from tool_version import TOOL_VERSION  # noqa: E402


def main():
    i18n.cli_language()
    platform_compat.console_utf8()
    ap = argparse.ArgumentParser(description=i18n.t("lp.description"))
    ap.add_argument("--port", type=int, default=8765, help=i18n.t("lp.help_port"))
    ap.add_argument("--json", action="store_true", help=i18n.t("lp.help_json"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("lp.help_lang"))
    ap.add_argument("--version", action="store_true", help=i18n.t("lp.help_version"))
    ap.add_argument("--export-status", metavar="DIR", help=i18n.t("lp.help_export_status"))
    ap.add_argument("--export-sign-queue", metavar="FILE", help=i18n.t("lp.help_export_queue"))
    ap.add_argument("--sign-trust", choices=("all", "verified", "unknown", "failed"), default="all", help=i18n.t("lp.help_sign_trust"))
    args = ap.parse_args()
    if args.lang:
        i18n.set_language(args.lang)
    if args.version:
        print(f"github_actions_monitor {TOOL_VERSION}")
        print(i18n.about_line())
        return 0
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/sentinel?lang={i18n.language()}", timeout=8) as r:
            payload = json.load(r)
    except Exception as exc:  # noqa: BLE001
        print(f"MONITOR_NO_RESPONDE: {exc}")   # fixed machine-readable prefix, then the reason
        print(i18n.t("lp.not_running", port=args.port))
        return 2
    s = payload.get("data") or {}
    if args.export_status or args.export_sign_queue:
        if not s or s.get("loading"):
            print(export_status.TEXT["no_data"])
            return 3
        code = 0
        if args.export_status:
            written = export_status.write_public_status(s, args.export_status)
            for path in written:
                print(export_status.TEXT["wrote"] + str(path))
            if not written:
                print(export_status.TEXT["refused"])
            code = 0 if written else 4
        if args.export_sign_queue:
            target = export_status.write_sign_queue(s, args.export_sign_queue, args.sign_trust)
            print(export_status.TEXT["wrote"] + str(target) if target else export_status.TEXT["refused"])
            code = code or (0 if target else 4)
        return code
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    print(i18n.t("lp.header", tool=s.get("tool_version") or i18n.t("lp.old_version"), copy=TOOL_VERSION, level=s.get("level"), generated=s.get("generated"), rate=s.get("rate"), loading=s.get("loading")))
    for line in s.get("parte") or []:
        print(f"[{line.get('level')}] {line.get('text')}")
    for key, row in (s.get("by_ecosystem") or {}).items():
        print(i18n.t("lp.ecosystem", key=key, repos=row["repos"], red=row["red"], stuck=row["stuck"], alerts=row["alerts"], prs=row["prs"], candidates=row["candidates"],
                     unsigned=row["pending_sign"], hygiene=row["hygiene"], dep_off=row.get("dep_off", 0)))
    a1, a2 = s.get("a1") or {}, s.get("a2") or {}
    for row in a1.get("stuck") or []:
        print(i18n.t("lp.a1_stuck", repo=row.get("repo"), name=row.get("name"), seconds=row.get("seconds")))
    for row in a2.get("red") or []:
        print(i18n.t("lp.a2_red", repo=row.get("repo"), workflow=row.get("workflow"), streak=row.get("streak"), since=row.get("since"), url=row.get("url")))
    for row in (s.get("a5") or {}).get("pending_sign") or []:
        print(i18n.t("lp.a5_unsigned", repo=row.get("repo"), hours=row.get("hours"), url=row.get("url")))
    import signstate
    for i, row in enumerate(signstate.filter_queue((s.get("a5") or {}).get("sign_queue") or [], args.sign_trust), 1):
        print(i18n.t("lp.a5_queue", n=i, name=row.get("name"), hours=row.get("hours"), step=row.get("step"), command=row.get("command") or i18n.t("lp.no_command"))
              + f" [{i18n.t('ui.trust_' + signstate.trust_of(row))}]")
    for row in ((s.get("a7") or {}).get("budget") or []):
        print(i18n.t("lp.a7_budget", eco=row.get("ecosystem"), used=row.get("used"), limit=row.get("limit"), pct=row.get("pct"), period=row.get("period"), level=row.get("level")))
    if a2.get("unchecked"):
        print(i18n.t("lp.a2_unchecked", list=", ".join(a2["unchecked"])))
    for sec in (s.get("a10") or {}).get("sections") or []:
        if sec.get("count") and sec.get("level") in ("bad", "warn", "info"):
            print(i18n.t("lp.a10", title=sec["title"], n=sec["count"], level=sec["level"]))
    for key in ("a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10"):
        sec = s.get(key) or {}
        print(i18n.t("lp.level", key=key.upper(), level=sec.get("level")))
    for err in s.get("errors") or []:
        print(i18n.t("lp.monitor_error", error=str(err)[:200]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
