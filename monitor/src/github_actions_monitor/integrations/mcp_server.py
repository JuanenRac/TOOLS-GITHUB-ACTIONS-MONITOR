#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A local MCP server (Model Context Protocol over standard input and output) so that an AI tool - an assistant in a terminal or an editor - can ask the monitor what is red.

    python bin/mcp_server.py [--allow-ack]

Read only by default. Tools: get_alerts (the open alerts of the feed), get_red_repos, get_run_failure(repo, run) (the failed steps of a run and a short, cleaned fragment of its log),
get_quota (the allowance and the minutes, from a running monitor), alerts_open (the open alerts with their age, diagnosis and the origin they fall together under), alert_diagnose(id) (the failing
step and the last relevant lines of the log of that alert; read only calls to `gh` when the feed has none yet) and - only with --allow-ack - ack_alert(id) / alert_ack(id), which change the local state
of the feed and nothing else. When it starts it tells the AI, in its `instructions` and with one notification, how many real alerts are open, and it notes in the heartbeat file that an AI is
connected (the status bar of the monitor shows it). Nothing here writes to
GitHub, runs a workflow or sends anything out: every answer goes through ai_alerts.redact() (no token, key, e-mail, IP or home folder). It speaks JSON, one message per line.
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from github_actions_monitor.integrations import ai_alerts  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402
from github_actions_monitor.tool_version import TOOL_VERSION  # noqa: E402
from github_actions_monitor.security import netguard

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
TOOLS = [
    {"name": "get_alerts", "description": "Open CI alerts of the monitor (real ones first), with probable cause and suggested action.", "inputSchema": {"type": "object", "properties": {"include_resolved": {"type": "boolean"}}}},
    {"name": "get_red_repos", "description": "Repositories with a workflow that is red on its default branch.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_run_failure", "description": "The failed steps of one run and a short cleaned fragment of its log.", "inputSchema": {"type": "object", "properties": {"repo": {"type": "string"}, "run": {"type": "integer"}}, "required": ["repo", "run"]}},
    {"name": "sentinel_panels", "description": "The panels A1..A13 and the second sentinel of the Sentinel tab as data: level (bad = act, warn = keep an eye on it), one line and the rows to act on, with repository and link. Read only.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "monitor_state", "description": "Everything the monitor says, as signals (level act / watch / info, rows with repository, link, age and next step), plus the edition (lite or complete) and the panels that do not exist in it. Read only.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "signals", "description": "The signals of one panel (now, alerts, repos, health, a1..a13, collab) or of all of them, optionally only the ones that need action.", "inputSchema": {"type": "object", "properties": {"panel": {"type": "string"}, "only_act": {"type": "boolean"}}}},
    {"name": "diagnose", "description": "The failing step and the last lines of the log of one alert (by id); same as alert_diagnose.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "act", "description": "Acknowledge an alert (local state only; needs --allow-ack); same as alert_ack.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "get_quota", "description": "GitHub allowance and Actions minutes, from the running monitor.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "alerts_open", "description": "Open CI alerts of the monitor, real ones first: age of the feed, failing step, last log lines and the red repository they fall together under.", "inputSchema": {"type": "object", "properties": {"only_real": {"type": "boolean"}}}},
    {"name": "alert_diagnose", "description": "The failing step and the last relevant lines of the log of one alert (by id); reads the log from GitHub only when the feed has no diagnosis yet.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "alert_ack", "description": "Acknowledge an alert (local state only; needs --allow-ack).", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "ack_alert", "description": "Acknowledge an alert (local state only; needs --allow-ack).", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]


def watched(config, repo):
    """True when the AI may ask for the log of a run of `repo`: a repository the monitor watches (the configuration, or an open alert of the feed). When `ai.allowed_repos` lists
    repositories, only those. The log of any other repository of the account (a private one the monitor does not look at) is not for an AI tool to read through this server."""
    allowed = ((config or {}).get("ai") or {}).get("allowed_repos") if isinstance((config or {}).get("ai"), dict) else None
    if isinstance(allowed, list) and allowed:
        return repo in [x for x in allowed if isinstance(x, str)]
    listed = (config or {}).get("repos")
    if isinstance(listed, list) and repo in [x for x in listed if isinstance(x, str)]:
        return True
    return repo in {a["repo"] for a in ai_alerts.alerts(config, states=("open", "acknowledged"))}


def open_summary(config):
    """One short text: how many real alerts are open (and how old the brief is), or '' when none is."""
    rows = [a for a in ai_alerts.alerts(config, states=("open",)) if a["class"] == "real"]
    if not rows:
        return ""
    info = ai_alerts.brief_info(config)
    first = "; ".join(f"{a['repo']} / {a['workflow']}" for a in rows[:5])
    return ai_alerts.redact(f"{len(rows)} real CI alert(s) open (brief updated {info['updated_local']}): {first}. Use alerts_open and alert_diagnose.", 600)


def local_get(path, port=8765):
    with netguard.local_open(f"http://127.0.0.1:{port}{path}", timeout=10) as answer:
        return json.load(answer)


def run_gh(args, timeout=60):
    done = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return done.returncode, done.stdout, done.stderr


def call(name, arguments, config, allow_ack=False, runner=run_gh, getter=local_get):
    """The text a tool answers (already cleaned). Raises ValueError for a bad request."""
    if name == "get_alerts":
        states = None if arguments.get("include_resolved") else ("open", "acknowledged")
        return ai_alerts.redact_json(ai_alerts.alerts(config, states=states), indent=1)
    if name == "alerts_open":
        rows = [a for a in ai_alerts.alerts(config, states=("open", "acknowledged")) if not arguments.get("only_real") or a["class"] == "real"]
        rows.sort(key=lambda a: (a["state"] == "acknowledged", a["class"] != "real", a["repo"], a["workflow"]))
        info = ai_alerts.brief_info(config)
        return ai_alerts.redact_json({"updated": info["updated"], "updated_local": info["updated_local"], "age_seconds": info["age_seconds"], "alerts": rows}, indent=1)
    if name in ("alert_diagnose", "diagnose"):
        wanted = str(arguments.get("id", ""))
        found = [a for a in ai_alerts.alerts(config, states=("open", "acknowledged")) if a["id"] == wanted]
        if not found:
            raise ValueError("no such open alert")
        item = found[0]
        diagnosis = item.get("diagnosis")
        if not diagnosis or diagnosis.get("unavailable"):
            cfg = ai_alerts.settings(config)["diagnose"]
            diagnosis = ai_alerts.diagnose(toolconfig.github_owner(config), item["repo"], item.get("url"), runner, cfg["log_lines"], cfg["max_bytes"])
            if not diagnosis:
                raise ValueError("this alert has no run to read")
        return ai_alerts.redact_json({"id": wanted, "repo": item["repo"], "workflow": item["workflow"], "diagnosis": diagnosis, "origin": item.get("origin")}, indent=1)
    if name == "get_red_repos":
        rows = [a for a in ai_alerts.alerts(config, states=("open", "acknowledged")) if a.get("conclusion") != "panel"]
        return ai_alerts.redact_json(sorted({a["repo"] for a in rows}))
    if name == "monitor_state":
        return ai_alerts.redact_json(getter("/api/ai/state"), 20000)
    if name == "signals":
        doc = getter("/api/ai/state")
        rows = [s for s in doc.get("signals", []) if (not arguments.get("panel") or s.get("panel") == arguments["panel"] or s["id"].split(".")[0] == arguments["panel"]) and (not arguments.get("only_act") or s.get("level") == "act")]
        return ai_alerts.redact_json({"edition": doc.get("edition"), "signals": rows}, 16000)
    if name == "sentinel_panels":
        return ai_alerts.redact_json(getter("/api/sentinel/panels"), 12000)
    if name == "get_run_failure":
        repo, run = str(arguments.get("repo", "")), arguments.get("run")
        if not NAME_RE.match(repo) or not isinstance(run, int) or isinstance(run, bool) or run <= 0:
            raise ValueError("repo and run are required")
        if not watched(config, repo):
            raise ValueError("that repository is not watched (it is not in the configuration, in ai.allowed_repos or in an open alert)")
        owner = toolconfig.github_owner(config)
        code, out, err = runner(["api", f"repos/{owner}/{repo}/actions/runs/{run}/jobs?per_page=30"])
        if code != 0:
            raise ValueError(ai_alerts.redact(err.strip()[:200]) or "gh failed")
        steps = [f"{job.get('name')}: {step.get('name')}" for job in (json.loads(out).get("jobs") or []) for step in (job.get("steps") or []) if step.get("conclusion") == "failure"]
        code, log, _err = runner(["run", "view", str(run), "--repo", f"{owner}/{repo}", "--log-failed"], 90)
        fragment = "\n".join((log or "").splitlines()[-40:]) if code == 0 else ""
        return ai_alerts.redact("Failed steps:\n" + ("\n".join(steps) or "(none listed)") + "\n\nEnd of the failed log:\n" + fragment, 4000)
    if name == "get_quota":
        return ai_alerts.redact_json(getter("/api/quota"), 3000)
    if name in ("ack_alert", "alert_ack", "act"):
        if not allow_ack:
            raise ValueError("acknowledging is off: start the server with --allow-ack")
        return "acknowledged" if ai_alerts.ack(config, arguments.get("id")) else "no such open alert"
    raise ValueError("unknown tool")


MAX_LINE = 65536     # one JSON message per line; a longer line is refused, not buffered
INVALID = {"code": -32600, "message": "invalid request"}


def error_reply(ident, error):
    return {"jsonrpc": "2.0", "id": ident if isinstance(ident, (str, int)) and not isinstance(ident, bool) else None, "error": dict(error)}


def valid_shape(message):
    """True when the message is a JSON-RPC request or notification of the shape this server reads: an object whose method is text, whose id (if any) is text or a whole number and whose
    params (if any) is an object - and, for tools/call, whose name is text and whose arguments (if any) is an object."""
    if not isinstance(message, dict) or not isinstance(message.get("method"), str):
        return False
    ident = message.get("id")
    if "id" in message and ident is not None and (isinstance(ident, bool) or not isinstance(ident, (str, int))):
        return False
    params = message.get("params")
    if params is not None and not isinstance(params, dict):
        return False
    if message["method"] == "tools/call":
        arguments = (params or {}).get("arguments")
        if not isinstance((params or {}).get("name"), str) or (arguments is not None and not isinstance(arguments, dict)):
            return False
    return True


def handle(message, config, allow_ack=False, **kwargs):
    """The answer to one JSON-RPC message, or None for a notification. A message that is not shaped as expected gets an "invalid request" error, never an exception."""
    if not valid_shape(message):
        return error_reply(message.get("id") if isinstance(message, dict) else None, INVALID)
    method, ident = message.get("method"), message.get("id")
    if method == "initialize":
        version = (message.get("params") or {}).get("protocolVersion", "2024-11-05")
        result = {"protocolVersion": version if isinstance(version, str) and len(version) <= 20 else "2024-11-05", "capabilities": {"tools": {}, "logging": {}},
                  "serverInfo": {"name": "github-actions-monitor", "version": TOOL_VERSION}}
        note = open_summary(config)
        if note:
            result["instructions"] = note
        ai_alerts.touch(config, "mcp", str(((message.get("params") or {}).get("clientInfo") or {}).get("name") or "mcp") if isinstance((message.get("params") or {}).get("clientInfo"), dict) else "mcp")
    elif method == "tools/list":
        result = {"tools": [t for t in TOOLS if allow_ack or t["name"] not in ("ack_alert", "alert_ack")]}
    elif method == "tools/call":
        params = message.get("params") or {}
        ai_alerts.touch(config, "mcp", "mcp")
        try:
            text = call(params["name"], params.get("arguments") or {}, config, allow_ack, **kwargs)
            result = {"content": [{"type": "text", "text": text}]}
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            result = {"content": [{"type": "text", "text": ai_alerts.redact(str(error))[:300]}], "isError": True}
    elif method == "ping":
        result = {}
    elif method == "notifications/initialized":      # the tool is ready: one notification says what is red (nothing when nothing is)
        note = open_summary(config)
        return {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "warning", "logger": "github-actions-monitor", "data": note}} if note else None
    elif ident is None:
        return None
    else:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "method not found"}}
    return None if ident is None else {"jsonrpc": "2.0", "id": ident, "result": result}


def serve_line(line, config, allow_ack=False, **kwargs):
    """The reply (a dict) to one input line, or None. Whatever happens inside, the loop of the server goes on: a bad line is an error reply for that line only."""
    try:
        message = json.loads(line)
    except ValueError:
        return None      # text that is not JSON is noise on the line, not a request: it is skipped as it always was
    try:
        return handle(message, config, allow_ack, **kwargs)
    except Exception:      # a defect in one tool never ends the server
        return error_reply(message.get("id") if isinstance(message, dict) else None, {"code": -32603, "message": "internal error"})


def main(argv=None, stdin=None, stdout=None):
    argv = sys.argv[1:] if argv is None else argv
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    config = toolconfig.raw_config()
    while True:
        line = stdin.readline(MAX_LINE + 1)
        if not line:
            break
        if len(line) > MAX_LINE and not line.endswith("\n"):        # too long: skip the rest of the line without keeping it
            while line and not line.endswith("\n"):
                line = stdin.readline(MAX_LINE)
            answer = error_reply(None, {"code": -32600, "message": "request too large"})
        elif not line.strip():
            continue
        else:
            answer = serve_line(line, config, "--allow-ack" in argv)
        if answer is not None:
            stdout.write(json.dumps(answer) + "\n")
            stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
