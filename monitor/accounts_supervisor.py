# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The supervisor of the complete edition when there are several accounts: one small process that starts one monitor per account (account_child.py), keeps them apart, and gives the page
and the tools a single address.

  * Every account is a separate process with its own folder, its own port (on 127.0.0.1 only) and its own GitHub allowance reading, so a crash, a slow account or a rate limit of one never
    touches another: the supervisor notices (a dead process or a failed health check), starts it again with a growing wait, and says so in the summary.
  * It reads nothing from GitHub and writes nothing: it forwards what the children already say. `GET /api/accounts` is the summary, `GET /api/accounts/<id>/status` one account, and every
    other `/api/...` request is forwarded to the account asked for with `?account=<id>` or the header `X-Account-Id` (the default account when none is given).
  * The page itself (`/`) is the same page: the supervisor serves it from the default account and adds the selector.

The supervisor keeps the rules of the monitor: the same host and origin guard, the same access token in the network mode (see localguard.py); it never listens beyond 127.0.0.1 unless the
network mode is on, exactly like a single monitor. The lite edition never runs this.
"""
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))        # works also under `py -3 -I`

import accounts  # noqa: E402
import netguard
CHILD_PORT_START = 18800          # the children listen on 127.0.0.1 from here; the supervisor asks the system for a free one when it is taken
HEALTH_EVERY = 5.0
BACKOFF = (2, 5, 15, 30, 60, 120)  # seconds to wait before starting a dead account again, growing; the last value repeats
FORWARD_TIMEOUT = 30
MAX_BODY = 1_048_576


def free_port(start=CHILD_PORT_START, taken=()):
    """A free TCP port on 127.0.0.1, from `start` upwards, never one of `taken`: a child that was given its port but has not started yet has not bound it, so the system alone cannot tell it is spoken for."""
    import socket
    for port in range(start, start + 400):
        if port in taken:
            continue
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise OSError("no free port")


class Child:
    """One account: its process, its port and what the supervisor knows about it."""

    def __init__(self, account_id, port, command=None):
        self.id, self.port, self.proc = account_id, port, None
        self.command = command or [sys.executable, "-I", str(HERE / "account_child.py"), account_id, "--port", str(port)]
        self.started = 0.0
        self.failures = 0              # starts in a row that did not get healthy
        self.next_start = 0.0
        self.health = None             # the last answer of /api/health, or None
        self.error = ""
        self.restarts = 0

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        try:
            own_group = {"start_new_session": True} if sys.platform != "win32" else {}       # a group of its own, so that stopping it reaches everything it started
            self.proc = subprocess.Popen(self.command, cwd=str(HERE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, **own_group)
            self.started, self.error = time.time(), ""
        except OSError as error:
            self.proc, self.error = None, str(error)[:120]

    def stop(self):
        """Ends the monitor of this account and everything it started: on Windows the interpreter of a virtual environment is a launcher with a child of its own, so `terminate()` alone leaves
        the real monitor running; `taskkill /T` on its own PID ends the whole tree (and only this tree). Elsewhere the process group is ended."""
        proc, self.proc = self.proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=15, stdin=subprocess.DEVNULL)
            else:
                import os
                import signal
                os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, subprocess.SubprocessError, ProcessLookupError):
            proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"


def fetch(url, timeout=6, data=None, headers=None, method=None):
    """(status, body bytes, headers dict) of one local request; (0, b'', {}) when the child does not answer. Never raises."""
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method or ("POST" if data is not None else "GET"))
    try:
        with netguard.local_open(request, timeout=timeout) as answer:
            return answer.status, answer.read(MAX_BODY * 8), dict(answer.headers)
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.read(MAX_BODY), dict(error.headers)
        except OSError:
            return error.code, b"", {}
    except (urllib.error.URLError, OSError, ValueError):
        return 0, b"", {}


class Supervisor:
    def __init__(self, base=None, command_for=None):
        self.base = base
        self.lock = threading.Lock()
        self.children = {}
        self.command_for = command_for          # tests pass their own command (a stub); None = account_child.py
        self.stopping = False
        self.thread = None

    def sync(self):
        """Makes the set of children match the enabled accounts: starts the new ones, stops the ones that were switched off or deleted."""
        wanted = accounts.enabled_accounts(self.base)
        with self.lock:
            for account_id in [a for a in self.children if a not in wanted]:
                self.children.pop(account_id).stop()
            for account_id in wanted:
                if account_id not in self.children:
                    port = free_port(CHILD_PORT_START, {c.port for c in self.children.values()})
                    command = self.command_for(account_id, port) if self.command_for else None
                    self.children[account_id] = Child(account_id, port, command)
        return wanted

    def check(self, now=None):
        """One round of supervision: start what must run, look at the health of what runs, and schedule a new start (with a growing wait) for what died or never became healthy."""
        now = time.time() if now is None else now
        with self.lock:
            children = list(self.children.values())
        for child in children:
            if not child.alive():
                if child.proc is not None:
                    child.failures += 1
                    child.error = child.error or "stopped"
                    child.proc = None
                    child.next_start = now + BACKOFF[min(child.failures - 1, len(BACKOFF) - 1)]
                if now >= child.next_start:
                    child.restarts += 1 if child.started else 0
                    child.start()
                child.health = None
                continue
            status, body, _ = fetch(child.url("/api/health"), timeout=4)
            try:
                child.health = json.loads(body) if status == 200 else None
            except ValueError:
                child.health = None
            if child.health is not None:
                child.failures, child.error = 0, ""
            elif now - child.started > 60:          # alive for a minute and still not answering: it is stuck, start it again
                child.error = "not answering"
                child.stop()
                child.failures += 1
                child.next_start = now + BACKOFF[min(child.failures - 1, len(BACKOFF) - 1)]

    def run(self):
        def loop():
            while not self.stopping:
                try:
                    self.sync()
                    self.check()
                except Exception as error:      # noqa: BLE001 - the supervisor itself must never stop
                    print("supervisor:", str(error)[:120], flush=True)
                time.sleep(HEALTH_EVERY)
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stopping = True
        with self.lock:
            for child in self.children.values():
                child.stop()

    def child(self, account_id):
        with self.lock:
            return self.children.get(account_id)


    def summary(self):
        """The document of GET /api/accounts: one entry per account with the figures its monitor already computes (nothing is read from GitHub here)."""
        out = []
        for account_id in accounts.enabled_accounts(self.base):
            child = self.child(account_id)
            entry = {"id": account_id, "state": "starting", "port": child.port if child else 0, "restarts": child.restarts if child else 0, "error": child.error if child else ""}
            if child is not None and child.health is not None:
                entry["state"] = "ok" if not child.health.get("offline") else "offline"
                entry["version"] = child.health.get("version")
                entry["loaded"] = bool(child.health.get("loaded"))
                status, body, _ = fetch(child.url("/api/data"), timeout=5)
                try:
                    data = (json.loads(body).get("data") or {}) if status == 200 else {}
                except ValueError:
                    data = {}
                figures = data.get("figures") or {}
                entry.update({"owner": data.get("owner") or "", "repos": len(data.get("repos") or []), "running": len(data.get("active") or []), "failing": len(data.get("failing") or []),
                              "fail24": figures.get("fail24", 0), "ok24": figures.get("ok24", 0), "rate": data.get("rate") or {}})
            elif child is not None and child.failures:
                entry["state"] = "down"
            out.append(entry)
        return {"accounts": out, "default": accounts.default_account(self.base), "layout": "accounts"}

    def status(self, account_id):
        """One account: its entry of the summary plus its own status document; None for an account that is not enabled."""
        if account_id not in accounts.enabled_accounts(self.base):
            return None
        entry = next((e for e in self.summary()["accounts"] if e["id"] == account_id), None)
        child = self.child(account_id)
        extra = {}
        if child is not None and child.health is not None:
            status, body, _ = fetch(child.url("/api/data"), timeout=6)
            try:
                extra = json.loads(body) if status == 200 else {}
            except ValueError:
                extra = {}
        return {**(entry or {}), "data": extra.get("data"), "error": extra.get("error")}


def account_of(path, headers, base=None):
    """The account a request is for: `?account=<id>` or the header X-Account-Id, else the default; None for one that is not enabled (the answer is then 404)."""
    query = path.partition("?")[2]
    asked = ""
    for part in query.split("&"):
        key, _, value = part.partition("=")
        if key == "account":
            asked = value
    asked = asked or (headers.get("X-Account-Id") if headers else "") or ""
    chosen = asked or accounts.default_account(base)
    return chosen if chosen in accounts.enabled_accounts(base) else None


def account_of_event(body, base=None):
    """The account that watches the repository named in a webhook payload (`repository.full_name`): the one whose `github_owner` is the owner of the repository, found in the configuration of
    every enabled account. None when the payload is not readable or no account watches that owner. Reads only the owner and never trusts the payload for anything else: the child that gets
    the event checks the signature with its own secret before it does anything."""
    try:
        full = json.loads(body)["repository"]["full_name"]
        owner = full.split("/", 1)[0].lower()
    except (ValueError, KeyError, TypeError, AttributeError, IndexError):
        return None
    for account_id in accounts.enabled_accounts(base):
        try:
            wanted = json.loads(accounts.config_path(account_id, base).read_text(encoding="utf-8")).get("github_owner")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(wanted, str) and wanted.lower() == owner:
            return account_id
    return None


def strip_account(path):
    """The path without the `account=` parameter, so the child sees the request as if it were alone."""
    route, _, query = path.partition("?")
    kept = [p for p in query.split("&") if p and not p.startswith("account=")]
    return route + ("?" + "&".join(kept) if kept else "")


# --- the HTTP face of the supervisor ---------------------------------------------------------------------------------------------------------------------------------------------------
import localguard  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

SUPERVISOR = {"obj": None}
#: what the supervisor answers itself; everything else under /api/ goes to the account asked for
OWN_PATHS = ("/api/accounts", "/api/health")
NO_FORWARD = ("host", "connection", "content-length", "transfer-encoding", "accept-encoding", "x-account-id")
#: the headers of a child's answer that are passed on
PASS_BACK = ("content-type", "set-cookie", "cache-control", "location", "referrer-policy")


class Handler(BaseHTTPRequestHandler):
    server_version = "GhaMonitorSupervisor"

    def log_message(self, *args):
        pass

    def reply(self, code, body, kind="application/json; charset=utf-8", extra=None):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (extra or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)
        except (ConnectionError, OSError):
            pass

    def json(self, payload, code=200):
        self.reply(code, json.dumps(payload))

    def gate(self):
        """The rules of a single monitor, unchanged: the Host and Origin must be ours, and in the network mode every request carries the access token (cookie, header or bearer)."""
        if not localguard.local_request_ok(self.headers, self.server.server_address[1]):
            self.json({"error": "forbidden"}, 403)
            return False
        if localguard.STATE["network"]:
            peer = str(self.client_address[0])
            if localguard.is_locked(peer):
                self.json({"error": "locked"}, 429)
                return False
            if not localguard.access_ok(self.headers, ""):
                localguard.note_failure(peer, 10)
                self.json({"error": "access"}, 401)
                return False
        return True

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def webhook(self, sup):
        """POST /api/webhook, one address for the whole installation. Like in a single monitor it has no Host check (a tunnel or a proxy changes it) and no access token: its proof is the HMAC of
        GitHub, which the account that receives the event verifies with its own secret. The supervisor only chooses the account by the owner of the repository in the payload."""
        if localguard.STATE["network"] and localguard.over_rate("webhook", str(self.client_address[0]), 120):
            self.json({"ok": False, "error": "rate"}, 429)
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            size = -1
        if not 0 <= size <= MAX_BODY:
            self.json({"ok": False}, 413)
            return
        body = self.rfile.read(size)
        account_id = account_of(self.path, self.headers, sup.base) if ("account=" in self.path or self.headers.get("X-Account-Id")) else account_of_event(body, sup.base)
        child = sup.child(account_id) if account_id else None
        if child is None:
            self.json({"ok": True, "ignored": True}, 202)          # no account watches that owner: answered, never acted on (what a single monitor says for a repository it does not watch)
            return
        if child.health is None:
            self.json({"ok": False, "error": "account not ready"}, 503)
            return
        headers = {k: v for k, v in self.headers.items() if k.lower() in ("content-type", "x-hub-signature-256", "x-github-event", "x-github-delivery", "user-agent")}
        headers["Host"] = f"127.0.0.1:{child.port}"
        status, data, back = fetch(child.url("/api/webhook"), timeout=FORWARD_TIMEOUT, data=body, headers=headers, method="POST")
        self.reply(status or 502, data if status else b'{"ok": false}', back.get("Content-Type", "application/json"))

    def route(self, method):
        sup = SUPERVISOR["obj"]
        route = self.path.split("?")[0]
        if method == "POST" and route == "/api/webhook" and sup is not None:
            self.webhook(sup)
            return
        if not self.gate():
            return
        if sup is None:
            self.json({"error": "not ready"}, 503)
            return
        asked = "account=" in self.path or self.headers.get("X-Account-Id")
        if method == "GET" and route == "/api/health" and not asked:       # with an account asked for, health is the one of that account
            self.json({"ok": True, "supervisor": True, "accounts": len(sup.children), "default": accounts.default_account(sup.base)})
            return
        if method == "GET" and route == "/api/accounts":
            self.json(sup.summary())
            return
        if method == "GET" and route in ("/", "/index.html"):
            self.page(sup)
            return
        if method == "GET" and route.startswith("/api/accounts/") and route.endswith("/status"):
            account_id = route[len("/api/accounts/"):-len("/status")]
            result = sup.status(account_id) if accounts.valid_id(account_id) else None
            self.json(result if result is not None else {"error": "unknown account"}, 200 if result is not None else 404)
            return
        self.forward(sup, method, route)


    def page(self, sup):
        """The page of the monitor of the account asked for (the default one without `?account=`), with the list of accounts embedded so the selector is there from the first paint. The page is the
        one of the child: the supervisor only adds `accounts` to its data, never a secret."""
        wants_all = "account=all" in self.path.partition("?")[2].split("&")        # the page of all accounts is the page of the default one with the grid of accounts on top of it
        account_id = accounts.default_account(sup.base) if wants_all else account_of(self.path, self.headers, sup.base)
        child = sup.child(account_id) if account_id else None
        if child is None or child.health is None:
            self.reply(503, "<!doctype html><meta charset=utf-8><title>GitHub Actions</title><p>Starting... reload in a few seconds.</p>", "text/html; charset=utf-8")
            return
        headers = {k: v for k, v in self.headers.items() if k.lower() in ("accept-language", "cookie", "x-monitor-access")}
        headers["Host"] = f"127.0.0.1:{child.port}"
        status, data, _ = fetch(child.url("/" + ("?" + strip_account(self.path).partition("?")[2] if "?" in self.path else "")), timeout=FORWARD_TIMEOUT, headers=headers)
        if status != 200:
            self.json({"error": "account not answering", "account": account_id}, 502)
            return
        page = data.decode("utf-8", "replace")
        info = json.dumps({"current": account_id, "default": accounts.default_account(sup.base), "accounts": [a["id"] for a in sup.summary()["accounts"]]}).replace("</", "<\\/")
        self.reply(200, page.replace("/*ACCOUNTS_DATA*/null", info, 1), "text/html; charset=utf-8")

    def forward(self, sup, method, route):
        account_id = account_of(self.path, self.headers, sup.base)
        if account_id is None:
            self.json({"error": "unknown account"}, 404)
            return
        child = sup.child(account_id)
        if child is None or child.health is None:
            self.json({"error": "account not ready", "account": account_id}, 503)
            return
        body = None
        if method == "POST":
            try:
                size = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                size = -1
            if not 0 <= size <= MAX_BODY:
                self.json({"error": "size"}, 413)
                return
            body = self.rfile.read(size)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in NO_FORWARD}
        headers["Host"] = f"127.0.0.1:{child.port}"           # the child answers to its own address: the supervisor already checked the one the browser used
        if "Origin" in headers:
            headers["Origin"] = f"http://127.0.0.1:{child.port}"
        status, data, back = fetch(child.url(strip_account(self.path)), timeout=FORWARD_TIMEOUT, data=body, headers=headers, method=method)
        if status == 0:
            self.json({"error": "account not answering", "account": account_id}, 502)
            return
        extra = {k: v for k, v in back.items() if k.lower() in PASS_BACK and k.lower() not in ("content-type", "cache-control")}
        self.reply(status, data, back.get("Content-Type", "application/json"), extra)


def serve(port, host="127.0.0.1", base=None):
    """Starts the supervisor and its server; returns (server, supervisor). The caller runs `server.serve_forever()`."""
    sup = Supervisor(base)
    sup.run()
    SUPERVISOR["obj"] = sup
    server = ThreadingHTTPServer((host, port), Handler)
    return server, sup
