#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Builds a CLEAN, reproducible zip of the monitor + sentinel + batch tools with a SHA256SUMS next to it, behind a quality gate.

  py -3 tools/make_release.py [--out DIR]   default: <signed_dir>/github_actions_monitor/ (see workspace.py; never on D:)

The zip (folder github_actions_monitor/) carries: the launchers (*.bat, *.sh, *.command) in its root, the tiny entry points (bin/*.py), the package src/github_actions_monitor/**, assets/ (examples/ with the neutral
*.example.json and quotas.json, static/ with the page, locales/*.json, ai/ with the guide for AI tools), tools/*.py, docs/*.md, CHANGELOG.md, docs/README_<lang>.txt
and docs/QUICKSTART_<lang>.txt in the 8 languages (+ README.txt), LICENSE, NOTICE, AUTHORS, assets/examples/actions_monitor.example.json (the template; the tool copies it to
actions_monitor.json on first start) and tests/*.py. Every member has a fixed timestamp, so the same sources give the same bytes.

The gate (nothing is written unless ALL of it passes):
  1. the unit tests pass (python -I -m unittest discover -s tests);
  2. no __pycache__, .pyc, log, cache, history, event or local-configuration file is inside the zip;
  3. actions_monitor.example.json shows EVERY option the sentinel reads (sentinel_local.DEFAULTS) and the targets catalogue is valid;
  4. CHANGELOG.md (first version heading) and tool_version.py agree, and each translated history (docs/CHANGELOG_<lang>.md) lists the same versions;
  5. every text file has the authorship header (copyright + GPL-3.0-or-later) and every JSON file the _author/_license fields; LICENSE, NOTICE and AUTHORS exist;
  6. nothing private travels (no absolute path of a person, no key folder, no foreign e-mail, no token); the 8 locales have exactly the same keys;
  7. after writing, the zip is opened again, its members re-checked (launchers keep the executable bit) and SHA256SUMS written from the bytes on disk;
  8. CLEAN INSTALL (before anything is left in the output folder): the zip is extracted into a new, empty temporary directory and, from THERE (python -I, nothing of
     this folder on the path), every member must be present, every module must compile, `bin/read_report.py --version` and `python -m github_actions_monitor.lite --help` (with src/ on the path) must run and the whole test suite must pass.
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

HERE = Path(__file__).resolve().parent.parent      # the product folder (the one that holds the launchers, src/, assets/, docs/, tests/ and tools/)
sys.path.insert(0, str(HERE / "src"))                # works also under `py -3 -I`
from github_actions_monitor.app import workspace   # noqa: E402
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
STATE_KEYS = ("repos",)   # a saved list of repositories is session state: the template goes back to "all"
EXAMPLE = "actions_monitor.example.json"
EXAMPLES_DIR = "assets/examples"          # where the neutral examples live inside the product folder and the zip
# session state and local configuration: they must never travel
FORBIDDEN_NAMES = {"actions_monitor.json", "sentinel_cache.json", "sentinel_history.json", "events_monitor.jsonl", "events_state.json",
                   "ci_red.json", "actions_monitor_log.txt", "ai_cache.json", "targets.candidates.json", "targets.json", "ecosystems.json", "profiles.json",
                   "eventos_monitor.jsonl", "eventos_estado.json", "events_monitor.jsonl", "events_state.json", "etag_cache.json", "analytics_history.json", "ai_actions_log.jsonl", "sentinel_ai_cache.json", "collab_state.json", "alert_mutes.json", "ai_alerts_state.json", "ALERTS_BRIEF.md", "ai_alerts.jsonl", "ai_heartbeat.json", "ai_hook_state.json"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp", ".jsonl")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
BRAND = "Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>"
LICENSE_LINE = "GPL-3.0-or-later"
LEGAL = ("LICENSE", "NOTICE", "AUTHORS")
DATA_JSON = ("targets.example.json", "ecosystems.example.json", "profiles.example.json", "quotas.json")   # only the neutral examples travel: your own files stay outside the package
PKG = "src/github_actions_monitor"
REQUIRED_MEMBERS = (f"{PKG}/i18n/__init__.py", f"{PKG}/app/toolconfig.py", f"{PKG}/cli/launcher_msg.py", "LICENSE", "NOTICE", "AUTHORS", "README.txt", f"{EXAMPLES_DIR}/targets.example.json", f"{EXAMPLES_DIR}/ecosystems.example.json",
                    *[f"assets/locales/{l}.json" for l in LANGS], *[f"docs/README_{l}.txt" for l in LANGS], *[f"docs/QUICKSTART_{l}.txt" for l in LANGS], f"{PKG}/cli/gha_dispatch_all.py", f"{PKG}/sentinels/sentinel_local.py",
                    f"{PKG}/app/actions_monitor.py", "assets/static/actions_monitor.html", "CHANGELOG.md",
                    f"{PKG}/tool_version.py", f"{PKG}/cli/read_report.py", f"{PKG}/util/platform_compat.py", f"{PKG}/app/surface.py", f"{PKG}/sentinels/readiness.py", f"{EXAMPLES_DIR}/profiles.example.json",
                    f"{PKG}/cli/export_status.py", f"{PKG}/security/webhook.py", f"{PKG}/integrations/monitor_link.py", f"{PKG}/cli/release_notes.py", f"{PKG}/__main__.py", f"{PKG}/lite.py", f"{PKG}/util/paths.py",
                    "docs/CI_RED_SCHEMA.md", "MONITOR_GITHUB_ACTIONS.sh", "MONITOR_GITHUB_ACTIONS.bat", "bin/read_report.py", "bin/actions_monitor.py", "bin/ai_hook.py", "assets/ai/README.md", f"{PKG}/util/rootmigrate.py", "tools/make_release.py", "tools/migrate_layout.py", f"{EXAMPLES_DIR}/{EXAMPLE}")


class GateError(SystemExit):
    pass


def fail(message):
    raise GateError("QUALITY GATE FAILED: " + message)


def members():
    names = [p for p in sorted(HERE.glob("*.bat")) + sorted(HERE.glob("*.sh")) + sorted(HERE.glob("*.command")) + sorted((HERE / "bin").glob("*.py"))]   # the launchers of the product folder and the tiny entry points of bin/
    names += sorted(p for p in (HERE / "src").rglob("*.py") if "__pycache__" not in p.parts)                                                      # the importable package
    names += sorted((HERE / "tools").glob("*.py"))
    names += [HERE / "assets" / "examples" / n for n in DATA_JSON] + [HERE / "assets" / "static" / "actions_monitor.html"]
    names += [HERE / n for n in LEGAL] + [HERE / "CHANGELOG.md", HERE / "README.txt"]
    names += sorted((HERE / "docs").glob("README_*.txt")) + sorted((HERE / "docs").glob("QUICKSTART_*.txt")) + sorted((HERE / "assets" / "locales").glob("*.json")) + sorted((HERE / "assets" / "ai").glob("*.md"))
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
    from github_actions_monitor.cli import gha_dispatch_all as gd
    from github_actions_monitor.app import toolconfig
    try:
        profiles = json.loads((here / EXAMPLES_DIR / "profiles.example.json").read_text(encoding="utf-8"))
        targets = json.loads((here / EXAMPLES_DIR / "targets.example.json").read_text(encoding="utf-8"))
        ecosystems = json.loads((here / EXAMPLES_DIR / "ecosystems.example.json").read_text(encoding="utf-8")).get("ecosystems") or {}
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


def changelog_translation_problems(here=HERE):
    """The translated histories (docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md) must list the same versions, in the same order, as CHANGELOG.md."""
    pattern = re.compile(r"^## \[([^\]]+)\]", re.M)
    want = pattern.findall((here / "CHANGELOG.md").read_text(encoding="utf-8"))
    out = []
    for tail in ("spa", "deu", "fra", "ita", "jpn", "zho", "por"):
        path = here / "docs" / f"CHANGELOG_{tail}.md"
        if not path.is_file():
            out.append(f"docs/CHANGELOG_{tail}.md is missing")
            continue
        have = pattern.findall(path.read_text(encoding="utf-8"))
        if have != want:
            lacking = [v for v in want if v not in have]
            out.append(f"docs/CHANGELOG_{tail}.md does not list the versions of CHANGELOG.md" + (f" (missing: {', '.join(lacking[:5])})" if lacking else " (order or extra versions)"))
    return out


def template(here=HERE):
    data = json.loads((here / EXAMPLES_DIR / EXAMPLE).read_text(encoding="utf-8"))
    for key in STATE_KEYS:
        data[key] = "all"
    return json.dumps(data, indent=2) + "\n"


TEST_TIMEOUT = 3600           # seconds for the ordinary suite (the default; MONITOR_RELEASE_TEST_TIMEOUT raises or lowers it: the suite takes 40 minutes and more on a loaded computer)
CLEAN_INSTALL_TIMEOUT = 3600  # seconds for the suite run from the extracted zip (the default; MONITOR_RELEASE_CLEAN_TIMEOUT)


def limit(variable, default, env=None):
    """The time limit in seconds: the environment variable `variable` when it holds a whole number of seconds from 60 to 86400, else `default`. Read when it is needed, not when the module loads."""
    text = str((os.environ if env is None else env).get(variable, "")).strip()
    return int(text) if text.isdigit() and 60 <= int(text) <= 86400 else default


def test_timeout(env=None):
    return limit("MONITOR_RELEASE_TEST_TIMEOUT", TEST_TIMEOUT, env)


def clean_install_timeout(env=None):
    return limit("MONITOR_RELEASE_CLEAN_TIMEOUT", CLEAN_INSTALL_TIMEOUT, env)


def run_tests(timeout=None):
    """Stage 1 of the gate: the ordinary suite, ONCE, with a time limit. The nested "clean folder" test is switched off here (MONITOR_NO_NESTED): the clean install is its own stage
    (clean_install_check), so the suite never runs twice inside one command."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MONITOR_NO_NESTED="1")
    timeout = test_timeout() if timeout is None else timeout      # read when called, so a variable set after the import still counts
    try:
        result = subprocess.run([sys.executable, "-I", "-m", "unittest", "discover", "-s", "tests"], cwd=str(HERE), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail(f"the unit tests did not finish in {timeout} s")
    tail = (result.stderr or result.stdout).strip().splitlines()[-1:] or ["(no output)"]
    if result.returncode != 0:
        fail("the unit tests do not pass:\nstdout:\n" + result.stdout[-1000:] + "\nstderr:\n" + result.stderr[-1500:])
    return tail[0]


def gate_static():
    """Checks that need no tests run: example complete, targets valid, version and changelog agree, required files present."""
    from github_actions_monitor.cli import gha_dispatch_all
    from github_actions_monitor.sentinels import sentinel_local
    from github_actions_monitor import tool_version
    missing = [m for m in REQUIRED_MEMBERS if not (HERE / m).is_file()]
    if missing:
        fail("files missing: " + ", ".join(missing))
    problems = example_problems(json.loads(template()), sentinel_local.DEFAULTS)
    if problems:
        fail("; ".join(problems))
    from github_actions_monitor.app import surface
    problems = nested_problems(json.loads(template())["sentinel"].get("surface"), surface.DEFAULTS)
    if problems:
        fail("; ".join(problems))
    problems = example_profiles_problems()
    if problems:
        fail("profiles.example.json: " + "; ".join(problems))
    for name in ("targets.example.json",):
        problems = gha_dispatch_all.validate_targets(json.loads((HERE / EXAMPLES_DIR / name).read_text(encoding="utf-8")))
        if problems:
            fail(f"{name}: " + "; ".join(problems))
    top = changelog_version((HERE / "CHANGELOG.md").read_text(encoding="utf-8"))
    if top != tool_version.TOOL_VERSION:
        fail(f"CHANGELOG.md says {top} but tool_version.py says {tool_version.TOOL_VERSION}")
    problems = changelog_translation_problems()
    if problems:
        fail("; ".join(problems))
    return tool_version.TOOL_VERSION


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
        env["MONITOR_NO_NESTED"] = "1"      # the suite of the extracted copy must not start a third one
        smoke = subprocess.run([python, "-I", "bin/read_report.py", "--version"], cwd=str(base), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
        if smoke.returncode != 0 or not smoke.stdout.strip():
            fail("clean install: bin/read_report.py --version does not run:\n" + (smoke.stderr or smoke.stdout)[-800:])
        lite = subprocess.run([python, "-I", "-c", "import sys; sys.path.insert(0, 'src'); from github_actions_monitor import lite; sys.exit(lite.main(['--help']))"], cwd=str(base), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env, timeout=120)
        if lite.returncode != 0 or "--port" not in lite.stdout:
            fail("clean install: python -m github_actions_monitor.lite does not start:\n" + (lite.stderr or lite.stdout)[-800:])
        try:
            suite = subprocess.run([python, "-I", "-m", "unittest", "discover", "-s", "tests"], cwd=str(base), capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   env=env, timeout=clean_install_timeout())
        except subprocess.TimeoutExpired:
            fail(f"clean install: the suite from the extracted zip did not finish in {clean_install_timeout()} s")
        if suite.returncode != 0:
            fail("clean install: the suite fails from the extracted zip:\nstdout:\n" + suite.stdout[-1000:] + "\nstderr:\n" + suite.stderr[-1500:])
        tail = (suite.stderr or suite.stdout).strip().splitlines()[-3:]
        return f"{len(found)} files, version {smoke.stdout.strip().splitlines()[0][:40]}, suite: {' '.join(tail)}"


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
    entries[f"github_actions_monitor/{EXAMPLES_DIR}/{EXAMPLE}"] = template().encode("utf-8")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
