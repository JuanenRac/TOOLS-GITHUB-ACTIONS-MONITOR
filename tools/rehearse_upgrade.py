#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Rehearses an update from the published release to the version of this checkout, with real processes, and the update after it with the signature required. It publishes nothing.

  python tools/rehearse_upgrade.py --old FOLDER --work FOLDER [--only NAME,NAME]

FOLDER of --old holds the files of the published release (github_actions_monitor.zip, SHA256SUMS, monitor_updater.py). The candidate is built from this checkout into --work with the version bumped
there and nowhere else. The signed cases use an Ed25519 key made here with openssl, thrown away with the folder, and anchored ONLY in copies built for the rehearsal; no real key is read.

It starts and stops monitors on this computer, so it runs on a runner of GitHub Actions (or with --allow-local on a machine where nothing else listens on the ports it uses).
No call leaves the machine: every `gh` a monitor starts is the stand-in of the container test (deploy/test/fake_gh.py), and any other call meets a proxy that does not answer. Exit codes: 0 all passed, 1 something failed, 2 usage.
"""
import argparse
import base64
import functools
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRODUCT = REPO / "monitor"
NEW, NEXT = "2.2.0", "2.2.1"
ZIP, SUMS, SIG = "github_actions_monitor.zip", "SHA256SUMS", "SHA256SUMS.ed25519.sig"
NOWHERE = "http://127.0.0.1:9"      # the discard port: a call that tries to leave the machine fails at once
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
RESULTS = []      # (scenario, check, passed, detail)
CURRENT = ["setup"]
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def check(name, passed, detail=""):
    RESULTS.append((CURRENT[0], name, bool(passed), "" if passed else str(detail)[:1500]))
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + ("" if passed else f": {str(detail)[:1500]}"), flush=True)
    return bool(passed)


def need(name, passed, detail=""):
    if not check(name, passed, detail):
        raise RuntimeError("cannot go on: " + name)


#: loaded by every Python process of the rehearsal (it is on PYTHONPATH): `gh` becomes the stand-in, on Windows and Linux alike
STAND_IN = """import os, subprocess, sys
_start = subprocess.Popen.__init__
def _with_stand_in(self, args, *rest, **kw):
    if isinstance(args, (list, tuple)) and args and os.path.basename(str(args[0])).lower() in ("gh", "gh.exe"):
        args = [sys.executable, os.environ["REHEARSAL_GH"], *args[1:]]
        kw.pop("executable", None)
    _start(self, args, *rest, **kw)
subprocess.Popen.__init__ = _with_stand_in
"""


def isolated_env(work):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MONITOR_", "JUANENRAC_", "GH_", "GITHUB_TOKEN")) and k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "PYTHONPATH")}
    shim = work / "shim"
    shim.mkdir(parents=True, exist_ok=True)
    (shim / "sitecustomize.py").write_text(STAND_IN, encoding="utf-8")
    shutil.copyfile(REPO / "deploy" / "test" / "fake_gh.py", shim / "fake_gh.py")
    (shim / "good").write_text("rehearsal-not-a-token\n", encoding="ascii")
    env.update(PYTHONPATH=str(shim), REHEARSAL_GH=str(shim / "fake_gh.py"), FAKE_GH_GOOD=str(shim / "good"), FAKE_GH_LOGIN="rehearsal-owner")
    env.update(GH_TOKEN="rehearsal-not-a-token", GH_CONFIG_DIR=str(work / "gh-config"), HTTPS_PROXY=NOWHERE, HTTP_PROXY=NOWHERE, NO_PROXY="127.0.0.1,localhost", PYTHONDONTWRITEBYTECODE="1")
    return env


def run(command, env, cwd=None, timeout=900):
    done = subprocess.run([str(c) for c in command], env=env, cwd=str(cwd) if cwd else None, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    return done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")


def last_json(text):
    start = text.find("{")
    try:
        return json.loads(text[start:]) if start >= 0 else {}
    except ValueError:
        return {}


# --- the files of a release ----------------------------------------------------------------------------------------------------------------------
def copy_product(dest):
    shutil.copytree(PRODUCT, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def replace_once(path, pattern, new):
    text = path.read_bytes().decode("utf-8")
    text, count = re.subn(pattern, lambda _m: new, text, count=1, flags=re.M)
    if count != 1:
        raise RuntimeError(f"{path.name}: {pattern!r} not found")
    path.write_bytes(text.encode("utf-8"))


def set_version(source, version):
    replace_once(source / "src" / "github_actions_monitor" / "tool_version.py", r'^TOOL_VERSION\s*=\s*"[^"]+"', f'TOOL_VERSION = "{version}"')


def anchor_key(source, public_hex):
    """Only for a copy of the rehearsal: the key made here takes the place of the key of the project, in the updater and in the keyring."""
    replace_once(source / "tools" / "monitor_updater.py", r"^RELEASE_KEYS = \([^\n]*\)", f'RELEASE_KEYS = ("{public_hex}",)')
    replace_once(source / "src" / "github_actions_monitor" / "security" / "keyring.py", r'"public": "[0-9a-f]{64}"', f'"public": "{public_hex}"')


def build_release(source, out, env):
    """The same files make_release.py leaves, without its gate (the version of the copy has no history to promote)."""
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import make_release as m\n"
            "from pathlib import Path\n"
            "e = {'github_actions_monitor/' + p.relative_to(m.HERE).as_posix(): m.line_endings_for_zip(p.name, m.lf_for_scripts(p.read_bytes())) for p in m.members()}\n"
            "e['github_actions_monitor/' + m.EXAMPLES_DIR + '/' + m.EXAMPLE] = m.template().encode('utf-8')\n"
            "out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True); target = out / 'github_actions_monitor.zip'\n"
            "m.write_zip(target, e); m.write_release_files(out, sys.argv[3], target, e)\n"
            "print(len(e))\n")
    version = re.search(r'"([^"]+)"', (source / "src" / "github_actions_monitor" / "tool_version.py").read_text(encoding="utf-8").split("TOOL_VERSION", 1)[1]).group(1)
    status, said, errors = run([sys.executable, "-c", code, source / "tools", out, version], env)
    if status != 0:
        raise RuntimeError("the release of " + version + " was not built: " + errors[-1500:])
    return out


def make_key(folder):
    """(path of a new private key, its public key in hex). The key lives in the work folder of the rehearsal and nowhere else."""
    folder.mkdir(parents=True, exist_ok=True)
    openssl = shutil.which("openssl") or r"C:\Program Files\Git\usr\bin\openssl.exe"
    key = folder / "rehearsal_key.pem"
    subprocess.run([openssl, "genpkey", "-algorithm", "ed25519", "-out", str(key)], check=True, capture_output=True, creationflags=NO_WINDOW)
    der = subprocess.run([openssl, "pkey", "-in", str(key), "-pubout", "-outform", "DER"], check=True, capture_output=True, creationflags=NO_WINDOW).stdout
    return openssl, key, der[-32:].hex()


def sign(source, folder, key, openssl, env):
    """The signing tool of the product itself, the one the release workflow runs."""
    status, said, errors = run([sys.executable, source / "tools" / "sign_release.py", "sign", folder, "--key", key], dict(env, PATH=str(Path(openssl).parent) + os.pathsep + env.get("PATH", "")))
    check(f"sign_release.py signs and verifies {folder.name}", status == 0 and "VERIFY=PASS" in said, said[-600:] + errors[-900:])


def variant(src, dest, drop=()):
    shutil.copytree(src, dest)
    for name in drop:
        for path in dest.glob(name):
            path.unlink()
    return dest


# --- an installation and its monitor -------------------------------------------------------------------------------------------------------------
class Install:
    def __init__(self, work, name, old, env, ports=None):
        self.base = work / "installs" / name
        shutil.rmtree(self.base, ignore_errors=True)
        with zipfile.ZipFile(old / ZIP) as z:
            z.extractall(self.base)
        self.root = self.base / "github_actions_monitor"
        self.env = env
        self.ports = ports or (8765, 8766)
        self.lite = False
        self.proc = None

    @property
    def port(self):
        return self.ports[1 if self.lite else 0]

    def updater(self, *args, tool=None, timeout=900):
        status, said, errors = run([sys.executable, tool or self.root / "tools" / "monitor_updater.py", "--dir", self.root, "--no-gh", "--lang", "en", *args], self.env, cwd=self.base, timeout=timeout)
        return status, last_json(said), (said[-1200:] + errors[-1200:])

    def version(self):
        found = re.search(r'TOOL_VERSION\s*=\s*"([^"]+)"', (self.root / "src" / "github_actions_monitor" / "tool_version.py").read_text(encoding="utf-8"))
        return found.group(1) if found else None

    def start(self):
        module = "github_actions_monitor.lite" if self.lite else "github_actions_monitor"
        logs = self.base / "run.log"
        with open(logs, "ab") as log:
            self.proc = subprocess.Popen([sys.executable, "-m", module, "--no-browser", "--port", str(self.port)], cwd=str(self.root), env=dict(self.env, PYTHONPATH=str(self.root / "src") + os.pathsep + self.env["PYTHONPATH"]),
                                         stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=(0x00000200 | 0x08000000) if os.name == "nt" else 0, start_new_session=os.name != "nt")

    def health(self, seconds=90):
        deadline = time.time() + seconds
        last = "no answer"
        while time.time() < deadline:
            try:
                with OPENER.open(f"http://127.0.0.1:{self.port}/api/health", timeout=5) as reply:
                    return json.loads(reply.read())
            except (OSError, ValueError) as error:
                last = str(error)
            if self.proc is not None and self.proc.poll() is not None:
                last = f"the process ended with {self.proc.returncode}"
                break
            time.sleep(1)
        return {"ok": False, "error": last, "log": self.log_tail()}

    def page(self):
        try:
            with OPENER.open(f"http://127.0.0.1:{self.port}/", timeout=30) as reply:
                return reply.status, len(reply.read())
        except (OSError, urllib.error.URLError) as error:
            return 0, str(error)

    def log_tail(self, lines=40):
        text = ""
        for path in (self.base / "run.log", self.root / "logs" / "updater_start.log"):
            if path.is_file():
                text += f"\n--- {path.name}\n" + "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
        return text

    def tracebacks(self):
        found = []
        for path in (self.base / "run.log", self.root / "logs" / "updater_start.log"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                if "Traceback (most recent call last)" in text:
                    found.append(text[text.index("Traceback (most recent call last)"):][:1200])
        return found

    def serving(self, version, label):
        health = self.health()
        need(f"{label}: /api/health answers {version}", health.get("ok") and health.get("version") == version and bool(health.get("lite")) == self.lite, health)
        time.sleep(8)      # a first cycle, with GitHub out of reach, must leave the monitor standing
        again = self.health(20)
        check(f"{label}: still answers after its first cycle", again.get("ok") and again.get("version") == version, again)
        status, size = self.page()
        check(f"{label}: the page is served", status == 200, (status, size))
        check(f"{label}: no traceback in its log", not self.tracebacks(), self.tracebacks()[:1])

    def pids(self):
        """The processes that are a monitor of THIS installation or of its ports (also one the updater started)."""
        found = []
        marks = [f"--port {p}" for p in self.ports]
        if os.name == "nt":
            script = "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"
            said = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, creationflags=NO_WINDOW, timeout=120).stdout
            for line in said.splitlines():
                pid, _, command = line.partition("\t")
                if pid.strip().isdigit() and "github_actions_monitor" in command and any(m in command + " " for m in marks):
                    found.append(int(pid))
        else:
            for entry in Path("/proc").iterdir():
                if entry.name.isdigit():
                    try:
                        command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace") + " "
                    except OSError:
                        continue
                    if "-m github_actions_monitor" in command and any(m + " " in command for m in marks):
                        found.append(int(entry.name))
        return found

    def stop(self):
        for pid in self.pids():
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
            else:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
        if self.proc is not None:
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
        deadline = time.time() + 30
        while self.pids() and time.time() < deadline:
            time.sleep(0.5)

    def snapshot(self, areas=("product", "config")):
        """{relative path: SHA-256} of what an update must be able to bring back."""
        out = {}
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root).as_posix()
            if not path.is_file() or "__pycache__" in rel or rel.endswith((".pyc", ".lock")):
                continue
            top = rel.split("/")[0]
            area = "config" if top == "config" else ("state" if top in ("data", "logs", "ai", "backups", "update_backups") else "product")
            if area in areas:
                out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        return out

    def config(self, name="actions_monitor.json"):
        path = self.root / "config" / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def differences(before, after):
    changed = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
    return {k: v[:12] for k, v in (("changed", changed), ("missing", sorted(before.keys() - after.keys())), ("extra", sorted(after.keys() - before.keys()))) if v}


def lost_settings(before, after, trail=""):
    """The settings the person had that are not there, or are not the same, after the migration."""
    out = []
    for key, value in (before or {}).items():
        if key.startswith("_"):
            continue
        name = trail + key
        if not isinstance(after, dict) or key not in after:
            out.append(name + ": gone")
        elif isinstance(value, dict):
            out += lost_settings(value, after[key], name + ".")
        elif after[key] != value:
            out.append(f"{name}: {value!r} -> {after[key]!r}")
    return out


def enabled_new_switches(work_release, after):
    """The switches that 2.2.0 adds and that the migration left turned on."""
    with zipfile.ZipFile(work_release / ZIP) as z:
        record = json.loads(z.read(f"github_actions_monitor/assets/migrations/{NEW}.json"))
    on = []
    for entry in record["settings"]["added"]:
        node = after
        for part in entry["key"].split("."):
            node = node.get(part) if isinstance(node, dict) else None
        if entry.get("kind") == "bool" and node is not None and node != entry.get("default"):
            on.append(entry["key"])
    return on


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base


def customised_config(install):
    """A configuration of the published version the way a person who uses it has it: the example, with many things changed."""
    example = json.loads((install.root / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
    cfg = merge(example, {
        "github_owner": "rehearsal-owner", "language": "es", "refresh_seconds": 300, "cold_refresh_seconds": 2400, "exclude": ["rehearsal-owner/old-repo"], "stuck_minutes": 45, "runs_per_repo": 30,
        "open_browser": False, "ports": {"complete": install.ports[0], "lite": install.ports[1]}, "startup": {"resume_max_age_hours": 24},
        "sentinel": {"enabled": True, "refresh_seconds": 1200}, "sentinels": {"security": {"enabled": True, "refresh_seconds": 3600}},
        "ai": {"daily_limit": 5}, "kiosk": {"font_scale_percent": 175}, "report_history_days": 60, "sound": {"enabled": False, "volume": 10},
        "retention": {"events_days": 30}, "audit_log": {"max_mb": 20}, "updates": {"check": False}, "display": {"density": "dense"},
    })
    write_json(install.root / "config" / "actions_monitor.json", cfg)
    shutil.copyfile(install.root / "assets" / "examples" / "targets.example.json", install.root / "config" / "targets.json")
    shutil.copyfile(install.root / "assets" / "examples" / "profiles.example.json", install.root / "config" / "profiles.json")
    cfg.update(targets_file="targets.json", profiles_file="profiles.json")
    write_json(install.root / "config" / "actions_monitor.json", cfg)
    return cfg


# --- a release server on this computer, so that the real downloader of the installed updater does the download --------------------------------------
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Server:
    def __init__(self, folder):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(folder)))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def drive(root, url, listing, target):
    """Runs in its own process: the engine of the installed updater with its own GitHubSource; only the list of releases and the allowed host are of the rehearsal."""
    spec = importlib.util.spec_from_file_location("installed_updater", Path(root) / "tools" / "monitor_updater.py")
    mu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mu)
    mu.host_ok = lambda address: address.startswith(url + "/")
    items = json.loads(Path(listing).read_text(encoding="utf-8"))

    class Local(mu.GitHubSource):
        def _page(self, page):
            return items if page == 1 else []

    report = mu.Updater(Path(root), Local(prefer_gh=False)).apply(target, {"start": True}, None)
    print(json.dumps({k: v for k, v in report.items() if k != "plan"} | {"signature": (report.get("plan") or {}).get("signature"), "verified": (report.get("plan") or {}).get("verified"),
                                                                         "checks": [c["code"] for c in (report.get("plan") or {}).get("checks", [])]}, default=str))
    return 0


def download_apply(install, work, version, folder):
    """apply of `version` whose files are in `folder`, downloaded over HTTP."""
    server = Server(folder)
    try:
        assets = [{"name": p.name, "size": p.stat().st_size, "browser_download_url": f"{server.url}/{p.name}"} for p in folder.iterdir() if p.is_file()]
        listing = work / f"listing_{folder.name}_{version}.json"
        write_json(listing, [{"tag_name": "v" + version, "name": "Monitor " + version, "published_at": "2026-01-01T00:00:00Z", "body": "", "assets": assets, "draft": False, "prerelease": False}])
        status, said, errors = run([sys.executable, Path(__file__).resolve(), "--drive", install.root, server.url, listing, version], install.env, cwd=install.base)
        return last_json(said), (said[-1200:] + errors[-1500:])
    finally:
        server.close()



# --- the scenarios ---------------------------------------------------------------------------------------------------------------------------------
def go_back(install, old_version, before, label, restore="auto", areas=("product", "config")):
    install.stop()
    status, report, said = install.updater("--yes", "--json", "--restore-data", restore, "rollback")
    need(f"{label}: rollback succeeds", status == 0 and report.get("ok"), said)
    check(f"{label}: the version is {old_version} again", install.version() == old_version, install.version())
    check(f"{label}: program and configuration are byte for byte as before", not differences(before, install.snapshot(areas)), differences(before, install.snapshot(areas)))
    install.start()
    install.serving(old_version, label + " after the rollback")
    install.stop()


def upgrade(install, release, label, extra=()):
    status, report, said = install.updater("--yes", "--json", "--start", "--zip", release / ZIP, *extra, "apply")
    need(f"{label}: apply with the updater of the installation succeeds", status == 0 and report.get("ok") and not report.get("rolled_back"), said + install.log_tail())
    return report


def scenario_fresh(ctx):
    install = Install(ctx["work"], "fresh", ctx["old"], ctx["env"])
    try:
        install.start()
        install.serving(ctx["old_version"], "published version, first start")
        install.stop()
        had = install.config()
        before = install.snapshot()
        status, plan, said = install.updater("--json", "--zip", ctx["rel"] / ZIP, "plan")
        need("plan: nothing blocks", status == 0 and not plan.get("blocked"), said)
        # the published updater calls "unknown" the keys of its own template that the settings page does not describe (fixed in the updater of the candidate); any other problem is one
        odd = [i for f in plan.get("config", []) for i in f.get("issues", []) if i != "unknown_key"]
        check("plan: no problem with the configuration beyond the known warnings", not odd, plan.get("config"))
        upgrade(install, ctx["rel"], "upgrade")
        install.serving(NEW, "after the upgrade")
        install.stop()
        check("upgrade: every setting is kept", not lost_settings(had, install.config()), lost_settings(had, install.config())[:20])
        check("upgrade: nothing new is turned on", not enabled_new_switches(ctx["rel"], install.config()), enabled_new_switches(ctx["rel"], install.config()))
        install.start()
        install.serving(NEW, "second start of the new version")
        go_back(install, ctx["old_version"], before, "way back")
    finally:
        install.stop()


def scenario_custom_download(ctx):
    install = Install(ctx["work"], "custom", ctx["old"], ctx["env"], ports=(8871, 8872))
    try:
        had = customised_config(install)
        install.start()
        install.serving(ctx["old_version"], "customised published version")
        install.stop()
        had = install.config() or had
        before = install.snapshot()
        report, said = download_apply(install, ctx["work"], NEW, ctx["rel"])
        need("download: apply through the downloader succeeds and starts", report.get("ok") and report.get("verified") == "sums", said + install.log_tail())
        install.serving(NEW, "downloaded upgrade")
        install.stop()
        check("download: every setting of the person is kept", not lost_settings(had, install.config()), lost_settings(had, install.config())[:20])
        check("download: nothing new is turned on", not enabled_new_switches(ctx["rel"], install.config()), enabled_new_switches(ctx["rel"], install.config()))
        status, said_cli, errors = run([sys.executable, install.root / "bin" / "monitor_cli.py", "doctor"], install.env, cwd=install.root)
        check("download: doctor of the new version runs without a traceback", "Traceback" not in said_cli + errors, (said_cli + errors)[-900:])
        go_back(install, ctx["old_version"], before, "way back with the data", restore="yes")
    finally:
        install.stop()


def scenario_lite(ctx):
    install = Install(ctx["work"], "lite", ctx["old"], ctx["env"], ports=(8873, 8874))
    install.lite = True
    try:
        write_json(install.root / "config" / "actions_monitor_lite.json", {"github_owner": "rehearsal-owner", "language": "pt", "refresh_seconds": 300, "ports": {"complete": 8873, "lite": 8874}})
        write_json(install.root / "config" / "actions_monitor.json", {"ports": {"complete": 8873, "lite": 8874}, "open_browser": False})
        install.start()
        install.serving(ctx["old_version"], "lite published version")
        install.stop()
        had = install.config("actions_monitor_lite.json")
        before = install.snapshot()
        upgrade(install, ctx["rel"], "lite upgrade", ("--edition", "lite"))
        install.serving(NEW, "lite after the upgrade")
        install.stop()
        check("lite: every setting is kept", not lost_settings(had, install.config("actions_monitor_lite.json")), lost_settings(had, install.config("actions_monitor_lite.json")))
        go_back(install, ctx["old_version"], before, "lite way back")
    finally:
        install.stop()


def handover(install, args, label, expect_status):
    """What the page does: the monitor that is running starts the updater and stops by itself."""
    install.start()
    need(f"{label}: the monitor that asks is running", install.health().get("ok"), install.log_tail())
    old = install.proc
    status_file = install.base / f"status_{label.replace(' ', '_')}.json"
    output = install.base / f"handover_{label.replace(' ', '_')}.log"
    with open(output, "ab") as log:
        child = subprocess.Popen([sys.executable, str(install.root / "tools" / "monitor_updater.py"), "--dir", str(install.root), "--no-gh", "--yes", "--handover", "--status-file", str(status_file), *[str(a) for a in args]],
                                 cwd=str(install.base), env=install.env, stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    time.sleep(4)
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(old.pid)], capture_output=True, creationflags=NO_WINDOW)
    else:
        old.terminate()
    old.wait(30)
    install.proc = None
    code = child.wait(600)
    check(f"{label}: the updater ends with {expect_status}", code == expect_status, f"code {code}\n" + output.read_text(encoding="utf-8", errors="replace")[-1500:] + install.log_tail())
    check(f"{label}: the progress file is written", status_file.is_file(), status_file)


def scenario_handover(ctx):
    install = Install(ctx["work"], "handover", ctx["old"], ctx["env"], ports=(8875, 8876))
    try:
        customised_config(install)
        before = install.snapshot()
        handover(install, ["--zip", ctx["rel"] / ZIP, "--start", "apply"], "page update", 0)
        install.serving(NEW, "page update")
        need("page update: version on disk", install.version() == NEW, install.version())
        # the way back asked from the new page
        install.stop()
        handover(install, ["rollback"], "page way back", 0)
        install.serving(ctx["old_version"], "page way back")
        install.stop()
        after = install.snapshot()
        changed = differences(before, after)
        check("page way back: program is as before", not any(not k.startswith("config/") for names in changed.values() for k in names), changed)
    finally:
        install.stop()


def scenario_broken_candidate(ctx):
    """A new version that does not start: the previous one must come back and run."""
    broken = variant(ctx["rel"], ctx["work"] / "rel_broken", drop=(SUMS,))
    with zipfile.ZipFile(ctx["rel"] / ZIP) as source, zipfile.ZipFile(broken / ZIP, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info)
            if info.filename.endswith("src/github_actions_monitor/__main__.py"):
                data = b"raise SystemExit('rehearsal: this version does not start')\n"
            target.writestr(info, data)
    install = Install(ctx["work"], "broken", ctx["old"], ctx["env"], ports=(8877, 8878))
    try:
        customised_config(install)
        before = install.snapshot()
        handover(install, ["--zip", broken / ZIP, "--start", "apply"], "failed start", 5)
        install.serving(ctx["old_version"], "after a version that does not start")
        install.stop()
        changed = differences(before, install.snapshot())
        check("failed start: program is as before", not any(not k.startswith("config/") for names in changed.values() for k in names), changed)
    finally:
        install.stop()


def refused(install, tool, release, code_wanted, label, extra=()):
    before = install.snapshot(("product", "config"))
    _status, plan, _said = install.updater("--json", "--zip", release / ZIP, *extra, "plan", tool=tool)
    blocks = [c["code"] for c in plan.get("checks", []) if c.get("severity") == "block"]      # the report of `apply --json` does not carry the plan
    status, report, said = install.updater("--yes", "--json", "--zip", release / ZIP, *extra, "apply", tool=tool)
    check(f"{label}: refused ({code_wanted})", status != 0 and not report.get("ok") and code_wanted in blocks, f"status {status}, blocks {blocks}, {said[-600:]}")
    check(f"{label}: nothing changed", not differences(before, install.snapshot(("product", "config"))), differences(before, install.snapshot(("product", "config"))))


def scenario_new_updater_on_old(ctx):
    """The stand-alone updater of the new release, on the published installation: it must ask for the signature (the candidate has none, or one of a key it does not hold)."""
    install = Install(ctx["work"], "standalone", ctx["old"], ctx["env"], ports=(8879, 8880))
    tool = ctx["rel"] / "monitor_updater.py"
    refused(install, tool, ctx["rel"], "sig_missing", "new stand-alone updater, unsigned candidate")
    other = variant(ctx["rel"], ctx["work"] / "rel_testsigned")
    sign(ctx["src_test"], other, ctx["key"], ctx["openssl"], ctx["env"])
    refused(install, tool, other, "sig_bad", "new stand-alone updater, candidate signed with another key")


def scenario_signed_next(ctx):
    work = ctx["work"]
    signed = ctx["rel221"]
    unsigned = variant(signed, work / "next_unsigned", drop=("*.ed25519.sig",))
    other_openssl, other_key, _ = make_key(work / "other-key")
    other = variant(signed, work / "next_other_key", drop=("*.ed25519.sig",))
    done = subprocess.run([other_openssl, "pkeyutl", "-sign", "-inkey", str(other_key), "-rawin", "-in", str(other / SUMS)], capture_output=True, creationflags=NO_WINDOW)
    (other / SIG).write_bytes(base64.b64encode(done.stdout) + b"\n")
    tampered_zip = variant(signed, work / "next_tampered_zip")
    with zipfile.ZipFile(tampered_zip / ZIP, "a") as z:
        z.writestr("github_actions_monitor/tools/added.py", "# added after the signature\n")
    tampered_sums = variant(tampered_zip, work / "next_tampered_sums")
    lines = (tampered_sums / SUMS).read_text(encoding="ascii").splitlines()
    lines[0] = f"{hashlib.sha256((tampered_sums / ZIP).read_bytes()).hexdigest()}  {ZIP}"
    (tampered_sums / SUMS).write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")

    install = Install(work, "signed", ctx["old"], ctx["env"], ports=(8881, 8882))
    try:
        had = customised_config(install)
        upgrade(install, ctx["rel_test"], "published version to the rehearsal build of " + NEW)
        install.serving(NEW, "rehearsal build")
        install.stop()
        had = install.config()
        refused(install, None, unsigned, "sig_missing", "next version without signature")
        refused(install, None, other, "sig_bad", "next version signed with another key")
        refused(install, None, tampered_zip, "sha", "next version with a zip changed after signing")
        refused(install, None, tampered_sums, "sig_bad", "next version with zip and SHA256SUMS changed after signing")
        report, said = download_apply(install, work, NEXT, ctx["rel_test"])
        check("an older signed zip offered as the next version is refused", not report.get("ok") and "sig_version" in report.get("checks", []) and install.version() == NEW, said)
        report, said = download_apply(install, work, NEXT, unsigned)
        check("download without the signature is refused", not report.get("ok") and "sig_missing" in report.get("checks", []) and install.version() == NEW, said)

        before = install.snapshot()
        status, plan, said = install.updater("--json", "--zip", signed / ZIP, "plan")
        need("signed next version: the plan says the signature is valid and nothing blocks", status == 0 and plan.get("signature") == "valid" and not plan.get("blocked"), said)
        check("the updater of the candidate finds no problem in a configuration made from its own example", not any(f.get("issues") for f in plan.get("config", [])), plan.get("config"))
        upgrade(install, signed, "signed next version")
        install.serving(NEXT, "signed next version")
        install.stop()
        check("signed next version: every setting is kept", not lost_settings(had, install.config()), lost_settings(had, install.config())[:20])
        status, said_cli, errors = run([sys.executable, install.root / "bin" / "monitor_cli.py", "verify-release", "--folder", signed], install.env, cwd=install.root)
        check("verify-release of the installed version accepts the signed set", status == 0, (said_cli + errors)[-900:])
        go_back(install, NEW, before, "way back from the signed version")

        report, said = download_apply(install, work, NEXT, signed)
        need("signed next version through the downloader", report.get("ok") and report.get("signature") == "valid", said + install.log_tail())
        install.serving(NEXT, "signed download")
        go_back(install, NEW, before, "way back from the signed download", restore="yes")

        # going down to a release that was never signed: refused unless asked for, and then said
        refused(install, None, ctx["old"], "downgrade", "downgrade not asked for")
        status, plan, said = install.updater("--json", "--allow-downgrade", "--zip", ctx["old"] / ZIP, "plan")
        codes = {c["code"]: c["severity"] for c in plan.get("checks", [])}
        check("downgrade to an unsigned release is allowed with a warning", status == 0 and codes.get("sig_unsigned") == "warn" and not plan.get("blocked"), said)
        status, report, said = install.updater("--yes", "--json", "--allow-downgrade", "--start", "--zip", ctx["old"] / ZIP, "apply")
        need("downgrade to the published version succeeds", status == 0 and report.get("ok"), said + install.log_tail())
        install.serving(ctx["old_version"], "downgraded")
    finally:
        install.stop()


def scenario_real_anchor(ctx):
    """The candidate as it would be published (the key of the project anchored): a release signed with any other key is not accepted."""
    install = Install(ctx["work"], "anchor", ctx["old"], ctx["env"], ports=(8883, 8884))
    try:
        upgrade(install, ctx["rel"], "published version to the candidate")
        install.stop()
        refused(install, None, ctx["rel221"], "sig_bad", "candidate offered a next version signed with a test key")
    finally:
        install.stop()


SCENARIOS = {"fresh": scenario_fresh, "custom-download": scenario_custom_download, "lite": scenario_lite, "page-handover": scenario_handover, "broken-candidate": scenario_broken_candidate,
             "new-updater-on-old": scenario_new_updater_on_old, "signed-next": scenario_signed_next, "real-anchor": scenario_real_anchor}


def prepare(work, old):
    env = isolated_env(work)
    sums = dict(reversed(line.split(None, 1)) for line in (old / SUMS).read_text(encoding="ascii").splitlines() if line.strip())
    if sums.get(ZIP) != hashlib.sha256((old / ZIP).read_bytes()).hexdigest():
        raise SystemExit("the published zip does not match its SHA256SUMS")
    with zipfile.ZipFile(old / ZIP) as z:
        old_version = re.search(r'TOOL_VERSION\s*=\s*"([^"]+)"', z.read("github_actions_monitor/src/github_actions_monitor/tool_version.py").decode("utf-8")).group(1)
    openssl, key, public = make_key(work / "key")
    candidate = copy_product(work / "src_candidate")
    set_version(candidate, NEW)
    anchored = copy_product(work / "src_anchored")
    set_version(anchored, NEW)
    anchor_key(anchored, public)
    following = work / "src_next"
    shutil.copytree(anchored, following)
    set_version(following, NEXT)
    record = json.loads((following / "assets" / "migrations" / f"{NEW}.json").read_text(encoding="utf-8"))
    record.update(version=NEXT, previous=NEW, settings={k: [] for k in record["settings"]})
    record.pop("manual", None)
    record.pop("notices", None)
    write_json(following / "assets" / "migrations" / f"{NEXT}.json", record)
    ctx = {"work": work, "old": old, "env": env, "old_version": old_version, "openssl": openssl, "key": key, "src_test": anchored,
           "rel": build_release(candidate, work / "rel_candidate", env), "rel_test": build_release(anchored, work / "rel_anchored", env), "rel221": build_release(following, work / "rel_next", env)}
    sign(anchored, ctx["rel_test"], key, openssl, env)
    sign(following, ctx["rel221"], key, openssl, env)
    print(f"published {old_version}; candidate {NEW} and {NEXT} built from this checkout", flush=True)
    return ctx


def summary(path):
    lines = ["| scenario | checks | failed |", "|---|---|---|"]
    for name in dict.fromkeys(r[0] for r in RESULTS):
        rows = [r for r in RESULTS if r[0] == name]
        lines.append(f"| {name} | {len(rows)} | {sum(not r[2] for r in rows)} |")
    for scenario, name, passed, detail in RESULTS:
        if not passed:
            lines.append(f"\n**{scenario}: {name}**\n```\n{detail}\n```")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"### Upgrade rehearsal ({sys.platform})\n" + "\n".join(lines) + "\n")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--drive"]:
        return drive(*argv[1:5])
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--only", default="")
    parser.add_argument("--allow-local", action="store_true")
    args = parser.parse_args(argv)
    if os.environ.get("GITHUB_ACTIONS") != "true" and not args.allow_local:
        parser.error("this starts and stops monitors: it runs on a runner of GitHub Actions (or --allow-local)")
    wanted = [n for n in args.only.split(",") if n] or list(SCENARIOS)
    if [n for n in wanted if n not in SCENARIOS]:
        parser.error("unknown scenario; there are: " + ", ".join(SCENARIOS))
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    ctx = prepare(work, Path(args.old).resolve())
    for name in wanted:
        CURRENT[0] = name
        print(f"== {name}", flush=True)
        try:
            SCENARIOS[name](ctx)
        except Exception as error:      # noqa: B902 - one scenario that breaks does not hide the others
            check("the scenario runs to its end", False, f"{error}\n{traceback.format_exc()[-900:]}")
    failed = [r for r in RESULTS if not r[2]]
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        summary(os.environ["GITHUB_STEP_SUMMARY"])
    print(f"REHEARSAL={'FAIL' if failed else 'PASS'} checks={len(RESULTS)} failed={len(failed)}")
    for scenario, name, _passed, _detail in failed:
        print(f"  {scenario}: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
