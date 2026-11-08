#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Builds a CLEAN, reproducible zip of the monitor + sentinel + batch tools with a SHA256SUMS next to it, behind a quality gate.

  py -3 make_release.py [--out DIR]        default: <signed_dir>/github_actions_monitor/ (see workspace.py; never on D:)

The zip carries: *.py, *.html, *.bat, *.sh, *.command, the data files (targets*.json, ecosystems*.json, profiles.json, locales/*.json), docs/*.md, CHANGELOG.md, the README_<lang>.txt
and QUICKSTART_<lang>.txt in the 8 languages (+ README.txt), LICENSE, NOTICE, AUTHORS, actions_monitor.example.json (the template; the tool copies it to
actions_monitor.json on first start) and tests/*.py. Every member has a fixed timestamp, so the same sources give the same bytes.

The gate (nothing is written unless ALL of it passes):
  1. the unit tests pass (python -I -m unittest discover -s tests);
  2. no __pycache__, .pyc, log, cache, history, event or local-configuration file is inside the zip;
  3. actions_monitor.example.json shows EVERY option the sentinel reads (sentinel_local.DEFAULTS) and the targets catalogue is valid;
  4. CHANGELOG.md (first version heading) and tool_version.py agree;
  5. every text file has the authorship header (copyright + GPL-3.0-or-later) and every JSON file the _author/_license fields; LICENSE, NOTICE and AUTHORS exist;
  6. nothing private travels (no absolute path of a person, no key folder, no foreign e-mail, no token); the 8 locales have exactly the same keys;
  7. after writing, the zip is opened again, its members re-checked (launchers keep the executable bit) and SHA256SUMS written from the bytes on disk;
  8. CLEAN INSTALL (before anything is left in the output folder): the zip is extracted into a new, empty temporary directory and, from THERE (python -I, nothing of
     this folder on the path), every member must be present, every module must compile, `read_report.py --version` must run and the whole test suite must pass.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # works also under `py -3 -I`
import workspace

HERE = Path(__file__).resolve().parent
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
STATE_KEYS = ("repos",)   # a saved list of repositories is session state: the template goes back to "all"
EXAMPLE = "actions_monitor.example.json"
# session state and local configuration: they must never travel
FORBIDDEN_NAMES = {"actions_monitor.json", "sentinel_cache.json", "sentinel_history.json", "events_monitor.jsonl", "events_state.json",
                   "ci_red.json", "actions_monitor_log.txt", "ai_cache.json", "targets.candidates.json", "targets.json", "ecosystems.json", "profiles.json",
                   "eventos_monitor.jsonl", "eventos_estado.json", "events_monitor.jsonl", "events_state.json", "etag_cache.json", "analytics_history.json", "ai_actions_log.jsonl", "sentinel_ai_cache.json"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp", ".jsonl")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
BRAND = "Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>"
LICENSE_LINE = "GPL-3.0-or-later"
LEGAL = ("LICENSE", "NOTICE", "AUTHORS")
DATA_JSON = ("targets.example.json", "ecosystems.example.json", "profiles.example.json")   # only the neutral examples travel: your own files stay outside the package
REQUIRED_MEMBERS = ("i18n.py", "toolconfig.py", "launcher_msg.py", "LICENSE", "NOTICE", "AUTHORS", "README.txt", "targets.example.json", "ecosystems.example.json",
                    *[f"locales/{l}.json" for l in LANGS], *[f"README_{l}.txt" for l in LANGS], *[f"QUICKSTART_{l}.txt" for l in LANGS], "gha_dispatch_all.py", "sentinel_local.py", "actions_monitor.py", "actions_monitor.html", "CHANGELOG.md",
                    "tool_version.py", "read_report.py", "platform_compat.py", "surface.py", "readiness.py", "profiles.example.json", "export_status.py", "webhook.py", "monitor_link.py", "release_notes.py",
                    "docs/CI_RED_SCHEMA.md", "MONITOR_GITHUB_ACTIONS.sh", "MONITOR_GITHUB_ACTIONS.bat", EXAMPLE)


class GateError(SystemExit):
    pass


def fail(message):
    raise GateError("QUALITY GATE FAILED: " + message)


def members():
    names = [p for p in sorted(HERE.glob("*.py")) + sorted(HERE.glob("*.html")) + sorted(HERE.glob("*.bat")) + sorted(HERE.glob("*.sh")) + sorted(HERE.glob("*.command"))]
    names += [HERE / n for n in DATA_JSON] + [HERE / n for n in LEGAL] + [HERE / "CHANGELOG.md", HERE / "README.txt"]
    names += sorted(HERE.glob("README_*.txt")) + sorted(HERE.glob("QUICKSTART_*.txt")) + sorted((HERE / "locales").glob("*.json"))
    names += sorted((HERE / "docs").glob("*.md"))
    names += sorted((HERE / "docs").rglob("*.json"))   # the example dashboard of Grafana
    names += sorted((HERE / "tests").glob("*.py")) + sorted((HERE / "tests" / "fixtures").glob("*.json"))
    return [p for p in names if p.is_file()]


def check_entries(names):
    """Names (as they will sit in the zip) that must not be there; empty list = clean."""
    bad = []
    for name in names:
        parts = name.split("/")
        base = parts[-1]
        if "__pycache__" in parts or base in FORBIDDEN_NAMES or base.endswith(FORBIDDEN_SUFFIXES) \
                or (base.endswith((".json", ".txt", ".db")) and ("cache" in base.lower() or "history" in base.lower())):   # session data, not code (report_history.py is code)
            bad.append(name)
    return sorted(bad)


def example_problems(example, defaults):
    """Sentinel options (keys of DEFAULTS) missing in the example, and example keys the sentinel does not know."""
    section = example.get("sentinel")
    if not isinstance(section, dict):
        return ["the example has no \"sentinel\" section"]
    problems = [f"the example lacks sentinel.{k}" for k in sorted(set(defaults) - set(section))]
    problems += [f"the example has sentinel.{k}, which the sentinel does not read" for k in sorted(set(section) - set(defaults))]
    return problems


def nested_problems(example, defaults, path="sentinel.surface"):
    """Same check as example_problems for the nested dictionaries (the surface layer): every key of the defaults must be in the example and vice versa."""
    if not isinstance(example, dict):
        return [f"the example lacks {path}"]
    problems = [f"the example lacks {path}.{k}" for k in sorted(set(defaults) - set(example))]
    problems += [f"the example has {path}.{k}, which the sentinel does not read" for k in sorted(set(example) - set(defaults))]
    for key, value in defaults.items():
        if isinstance(value, dict) and key in example and not all(isinstance(v, list) for v in value.values()):   # a map of lists is free-form (release_assets.required)
            problems += nested_problems(example[key], value, f"{path}.{key}")
    return problems


def authorship_problems(entries):
    """Members of the zip (name -> bytes) without the authorship: text files need the copyright line and the licence in the first lines, JSON files the
    _author/_license fields, and LICENSE / NOTICE / AUTHORS must exist (LICENSE is the full GPL text)."""
    problems = []
    for name in LEGAL:
        if not any(n.endswith("/" + name) for n in entries):
            problems.append(f"{name} is missing")
    for name, data in sorted(entries.items()):
        base = name.rsplit("/", 1)[-1]
        if base == "SHA256SUMS":
            continue
        text = data.decode("utf-8", errors="replace")
        if base == "LICENSE":
            if "GNU GENERAL PUBLIC LICENSE" not in text or "Version 3" not in text:
                problems.append("LICENSE is not the full GPL-3.0 text")
        elif base.endswith(".json"):
            try:
                meta = json.loads(text)
            except ValueError:
                problems.append(f"{name}: not valid JSON")
                continue
            if not (isinstance(meta, dict) and BRAND in str(meta.get("_author", "")) and LICENSE_LINE in str(meta.get("_license", ""))):
                problems.append(f"{name}: no _author/_license")
        else:
            head = "\n".join(text.splitlines()[:14])
            if base in ("NOTICE", "AUTHORS"):
                ok = "JuanenRac (Electro Hobby 3D)" in text and LICENSE_LINE in text or base == "AUTHORS" and "JuanenRac (Electro Hobby 3D)" in text
            else:
                ok = BRAND in head and LICENSE_LINE in head
            if not ok:
                problems.append(f"{name}: no authorship header")
    return sorted(problems)


PRIVATE = (re.compile(r"[A-Za-z]:[\\/]+Users[\\/]", re.I), re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/"), re.compile(r"~/\.[A-Za-z0-9_-]*(?:keys|armor)"), re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
           re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY"), re.compile("jua" + "ne(?!nrac)", re.I))
EMAIL = re.compile(r"[A-Za-z0-9._+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+")
OK_EMAILS = ("electrohobby3d@gmail.com", "noreply@github.com", "t@example.invalid")


def privacy_problems(entries):
    """Private things that must not travel to other people: absolute paths of a person, key folders, tokens, a foreign e-mail address."""
    problems = []
    for name, data in sorted(entries.items()):
        if name.endswith(".zip") or "/tests/" in name:
            continue
        text = data.decode("utf-8", errors="replace")
        for pattern in PRIVATE:
            found = pattern.search(text)
            if found:
                problems.append(f"{name}: {found.group(0)[:30]!r}")
        for mail in EMAIL.findall(text):
            if mail.lower() not in OK_EMAILS:
                problems.append(f"{name}: e-mail {mail}")
    return sorted(set(problems))


def locale_problems(entries):
    """The 8 catalogues must hold exactly the same keys, none empty, with the same {placeholders}."""
    cats = {}
    for lang in LANGS:
        key = next((n for n in entries if n.endswith(f"locales/{lang}.json")), None)
        if key is None:
            return [f"locales/{lang}.json is missing"]
        cats[lang] = {k: v for k, v in json.loads(entries[key].decode("utf-8")).items() if not k.startswith("_")}
    ph = re.compile(r"\{(\w+)(?:![rsa])?(?::[^}]*)?\}")
    problems = []
    for lang in LANGS[1:]:
        for k in sorted(set(cats["en"]) ^ set(cats[lang])):
            problems.append(f"{lang}: key {k} differs from en")
    for lang, cat in cats.items():
        for k, v in cat.items():
            if not str(v).strip():
                problems.append(f"{lang}: {k} is empty")
            elif k in cats["en"] and sorted(ph.findall(v)) != sorted(ph.findall(cats["en"][k])):
                problems.append(f"{lang}: {k} has other placeholders than en")
    return problems


def example_profiles_problems(here=HERE):
    """profiles.example.json checked against the NEUTRAL catalogues (targets.example.json, ecosystems.example.json), not the maintainer's: it must be valid and every
    profile must select at least one target. Empty list = coherent."""
    import gha_dispatch_all as gd
    import toolconfig
    try:
        profiles = json.loads((here / "profiles.example.json").read_text(encoding="utf-8"))
        targets = json.loads((here / "targets.example.json").read_text(encoding="utf-8"))
        ecosystems = json.loads((here / "ecosystems.example.json").read_text(encoding="utf-8")).get("ecosystems") or {}
    except (OSError, ValueError) as error:
        return [f"cannot read the examples: {error}"]
    catalogue = {n: v for n, v in targets.items() if not n.startswith("_") and isinstance(v, dict)}
    signed = {n: v for n, v in catalogue.items() if not v.get("build_only")}
    old_ecos, old_override = gd.ECOSYSTEMS, toolconfig._ecosystems_override["value"]
    try:
        toolconfig.set_ecosystems(ecosystems)
        gd.ECOSYSTEMS = tuple(toolconfig.ecosystem_names())
        problems = gd.validate_profiles(profiles, signed)
        for name in sorted(profiles.get("profiles") or {}):
            if not gd.profile_names(name, profiles, signed):
                problems.append(f"profile {name} selects no target of targets.example.json")
    finally:
        gd.ECOSYSTEMS = old_ecos
        toolconfig.set_ecosystems(old_override)
    for key in ("min_rate_remaining", "canary_wait_seconds"):
        if not isinstance(profiles.get(key), int) or isinstance(profiles.get(key), bool):
            problems.append(f"{key} must be a whole number")
    return problems


def changelog_version(text):
    match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.M)
    return match.group(1) if match else None


def template(here=HERE):
    data = json.loads((here / EXAMPLE).read_text(encoding="utf-8"))
    for key in STATE_KEYS:
        data[key] = "all"
    return json.dumps(data, indent=2) + "\n"


def run_tests():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-I", "-m", "unittest", "discover", "-s", "tests"], cwd=str(HERE), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=env)
    tail = (result.stderr or result.stdout).strip().splitlines()[-1:] or ["(no output)"]
    if result.returncode != 0:
        fail("the unit tests do not pass:\n" + (result.stderr or result.stdout)[-1500:])
    return tail[0]


def gate_static():
    """Checks that need no tests run: example complete, targets valid, version and changelog agree, required files present."""
    import gha_dispatch_all
    import sentinel_local
    import tool_version
    missing = [m for m in REQUIRED_MEMBERS if not (HERE / m).is_file()]
    if missing:
        fail("files missing: " + ", ".join(missing))
    problems = example_problems(json.loads(template()), sentinel_local.DEFAULTS)
    if problems:
        fail("; ".join(problems))
    import surface
    problems = nested_problems(json.loads(template())["sentinel"].get("surface"), surface.DEFAULTS)
    if problems:
        fail("; ".join(problems))
    problems = example_profiles_problems()
    if problems:
        fail("profiles.example.json: " + "; ".join(problems))
    for name in ("targets.example.json",):
        problems = gha_dispatch_all.validate_targets(json.loads((HERE / name).read_text(encoding="utf-8")))
        if problems:
            fail(f"{name}: " + "; ".join(problems))
    top = changelog_version((HERE / "CHANGELOG.md").read_text(encoding="utf-8"))
    if top != tool_version.TOOL_VERSION:
        fail(f"CHANGELOG.md says {top} but tool_version.py says {tool_version.TOOL_VERSION}")
    return tool_version.TOOL_VERSION


# File types Gmail refuses to receive, even inside a zip (list published by Google).
MAIL_BLOCKED = frozenset(".ade .adp .apk .appx .appxbundle .bat .cab .chm .cmd .com .cpl .diagcab .diagcfg .diagpkg .dll .dmg .ex .ex_ .exe .hta .img "
                         ".ins .iso .isp .jar .jnlp .js .jse .lib .lnk .mde .mjs .msc .msi .msix .msixbundle .msp .mst .nsh .pif .ps1 .scr .sct .shb "
                         ".sys .vb .vbe .vbs .vhd .vxd .wsc .wsf .wsh .xll".split())

MAIL_NOTE = """# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE

E-MAIL VERSION / VERSION PARA CORREO
Mail services (Gmail, among others) refuse files with the extension .bat, even inside a zip. In this zip the two Windows launchers are named *.bat.txt.
EN  Rename MONITOR_GITHUB_ACTIONS.bat.txt and BATCH_GITHUB_ACTIONS.bat.txt by removing the final ".txt" (or run: py -3 actions_monitor.py). Linux and macOS: use the .sh / .command files.
ES  Gmail y otros servicios rechazan los .bat. Quita el ".txt" final de MONITOR_GITHUB_ACTIONS.bat.txt y BATCH_GITHUB_ACTIONS.bat.txt (o ejecuta: py -3 actions_monitor.py). En Linux y macOS usa los .sh / .command.
DE  Mail-Dienste lehnen .bat ab. Entferne das ".txt" am Ende von MONITOR_GITHUB_ACTIONS.bat.txt und BATCH_GITHUB_ACTIONS.bat.txt (oder: py -3 actions_monitor.py). Unter Linux und macOS die .sh / .command verwenden.
FR  Gmail et d'autres services refusent les .bat. Retirez le ".txt" final de MONITOR_GITHUB_ACTIONS.bat.txt et BATCH_GITHUB_ACTIONS.bat.txt (ou lancez : py -3 actions_monitor.py). Sous Linux et macOS, utilisez les .sh / .command.
IT  Gmail e altri servizi rifiutano i .bat. Togli il ".txt" finale da MONITOR_GITHUB_ACTIONS.bat.txt e BATCH_GITHUB_ACTIONS.bat.txt (oppure esegui: py -3 actions_monitor.py). Su Linux e macOS usa i .sh / .command.
JA  Gmail などは .bat を拒否します。MONITOR_GITHUB_ACTIONS.bat.txt と BATCH_GITHUB_ACTIONS.bat.txt の末尾の「.txt」を削除してください（または py -3 actions_monitor.py を実行）。Linux と macOS では .sh / .command を使います。
ZH  Gmail 等邮件服务会拒收 .bat 文件。请删除 MONITOR_GITHUB_ACTIONS.bat.txt 和 BATCH_GITHUB_ACTIONS.bat.txt 末尾的“.txt”（或运行：py -3 actions_monitor.py）。Linux 和 macOS 请使用 .sh / .command 文件。
PT  O Gmail e outros serviços recusam ficheiros .bat. Retire o ".txt" final de MONITOR_GITHUB_ACTIONS.bat.txt e BATCH_GITHUB_ACTIONS.bat.txt (ou execute: py -3 actions_monitor.py). No Linux e no macOS use os ficheiros .sh / .command.
"""


def write_zip(target, entries):
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3   # Unix: unzip and the Linux/macOS file managers then honour the permission bits (the executable launchers)
            info.external_attr = (0o755 if name.endswith((".sh", ".command")) else 0o644) << 16   # launchers keep the executable bit on Linux and macOS
            z.writestr(info, entries[name])


def clean_install_check(archive, entries, python=None):
    """Extracts `archive` into a NEW EMPTY temporary directory and checks, from there and with `python -I`, that it works on its own: all members present,
    every module compiles, `read_report.py --version` runs and the whole suite passes. Returns a one-line summary; fails the release otherwise."""
    python = python or sys.executable
    with tempfile.TemporaryDirectory(prefix="monitor_clean_") as fresh:
        root = Path(fresh)
        if any(root.iterdir()):
            fail("clean install: the temporary directory is not empty")
        with zipfile.ZipFile(archive) as z:
            z.extractall(root)
        base = root / "github_actions_monitor"
        planned = {n.split("/", 1)[1] for n in entries}
        found = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
        if planned - found:
            fail("clean install: missing after extraction: " + ", ".join(sorted(planned - found)[:10]))
        lacking = [m for m in REQUIRED_MEMBERS if not (base / m).is_file()]
        if lacking:
            fail("clean install: required files missing: " + ", ".join(lacking))
        for path in sorted(base.rglob("*.py")):
            try:
                compile(path.read_bytes(), str(path), "exec")
            except (SyntaxError, ValueError) as error:
                fail(f"clean install: {path.relative_to(base).as_posix()} does not compile: {error}")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("MONITOR_", "JUANENRAC_"))}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        smoke = subprocess.run([python, "-I", "read_report.py", "--version"], cwd=str(base), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
        if smoke.returncode != 0 or not smoke.stdout.strip():
            fail("clean install: read_report.py --version does not run:\n" + (smoke.stderr or smoke.stdout)[-800:])
        suite = subprocess.run([python, "-I", "-m", "unittest", "discover", "-s", "tests"], cwd=str(base), capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env=env, timeout=1800)
        if suite.returncode != 0:
            fail("clean install: the suite fails from the extracted zip:\n" + (suite.stderr or suite.stdout)[-1500:])
        tail = (suite.stderr or suite.stdout).strip().splitlines()[-3:]
        return f"{len(found)} files, version {smoke.stdout.strip().splitlines()[0][:40]}, suite: {' '.join(tail)}"


def write_mail_variant(out, entries):
    """The same zip with the Windows launchers renamed to *.bat.txt (mail services refuse .bat, even inside a zip) and a note in 8 languages."""
    renamed = {}
    for name, data in entries.items():
        renamed[name + ".txt" if name.endswith(".bat") else name] = data
    renamed["github_actions_monitor/README_MAIL.txt"] = MAIL_NOTE.encode("utf-8")
    refused = sorted(n for n in renamed if "." + n.rsplit("/", 1)[-1].rsplit(".", 1)[-1].lower() in MAIL_BLOCKED and "." in n.rsplit("/", 1)[-1])
    if refused:
        fail("the e-mail variant holds file types that Gmail refuses: " + ", ".join(refused))
    target = out / "github_actions_monitor_mail.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(renamed):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o755 if name.endswith((".sh", ".command")) else 0o644) << 16
            z.writestr(info, renamed[name])
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            fail("the e-mail zip is corrupt")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out")
    args = parser.parse_args()
    version = gate_static()
    print("gate: example, targets and version ok (tool", version + ")")
    print("gate: unit tests:", run_tests())
    out = Path(args.out) if args.out else workspace.signed_dir() / "github_actions_monitor"
    if str(out).upper().startswith("D:"):
        raise SystemExit("never write on D:")
    entries = {f"github_actions_monitor/{p.relative_to(HERE).as_posix()}": p.read_bytes() for p in members()}
    entries[f"github_actions_monitor/{EXAMPLE}"] = template().encode("utf-8")
    missing_text = authorship_problems(entries)
    if missing_text:
        fail("authorship: " + "; ".join(missing_text))
    leaks = privacy_problems(entries)
    if leaks:
        fail("private data would travel: " + "; ".join(leaks))
    broken = locale_problems(entries)
    if broken:
        fail("locales: " + "; ".join(broken[:12]))
    crlf = [n for n, data in entries.items() if n.endswith((".sh", ".command")) and b"\r" in data]
    if crlf:
        fail("shell launchers with Windows line endings (they would not run on Linux or macOS): " + ", ".join(crlf))
    bad = check_entries(entries)
    if bad:
        fail("files that must not travel: " + ", ".join(bad))
    out.mkdir(parents=True, exist_ok=True)
    target = out / "github_actions_monitor.zip"
    with tempfile.TemporaryDirectory(prefix="monitor_install_") as scratch:   # the install gate runs BEFORE anything is left in the output folder
        trial = Path(scratch) / "github_actions_monitor.zip"
        write_zip(trial, entries)
        print("gate: clean install:", clean_install_check(trial, entries))
    write_zip(target, entries)
    with zipfile.ZipFile(target) as z:   # open it again: what is on disk is what is checked
        if z.testzip() is not None:
            fail("the written zip is corrupt")
        again = z.namelist()
        slow = [i.filename for i in z.infolist() if i.filename.endswith((".sh", ".command")) and (i.external_attr >> 16) & 0o111 != 0o111 or i.create_system != 3]
        if slow:
            fail("launchers without the executable bit in the zip: " + ", ".join(slow))
    if sorted(again) != sorted(entries) or check_entries(again):
        fail("the written zip does not hold what was planned")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(f"{digest}  {target.name}\n", encoding="ascii", newline="\n")
    if (out / "SHA256SUMS").read_text(encoding="ascii").split()[0] != hashlib.sha256(target.read_bytes()).hexdigest():
        fail("SHA256SUMS does not match the zip")
    print(f"{target} ({target.stat().st_size / 1024:.0f} KB, {len(entries)} files) tool {version} sha256 {digest[:16]}")
    mail = write_mail_variant(out, entries)
    mail_digest = hashlib.sha256(mail.read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(f"{digest}  {target.name}\n{mail_digest}  {mail.name}\n", encoding="ascii", newline="\n")
    print(f"{mail} ({mail.stat().st_size / 1024:.0f} KB) e-mail variant, sha256 {mail_digest[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
