#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A local MCP server (Model Context Protocol over standard input and output) so that an AI tool - Claude Code, Gemini CLI, Codex, GitHub Copilot in VS Code - can ask the monitor what is red.

    python mcp_server.py [--allow-ack]

Read only by default. Tools: get_alerts (the open alerts of the feed), get_red_repos, get_run_failure(repo, run) (the failed steps of a run and a short, cleaned fragment of its log),
get_quota (the allowance and the minutes, from a running monitor) and - only with --allow-ack - ack_alert(id), which changes the local state of the feed and nothing else. Nothing here writes to
GitHub, runs a workflow or sends anything out: every answer goes through ai_alerts.redact() (no token, key, e-mail, IP or home folder). It speaks JSON, one message per line.
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_alerts  # noqa: E402
import toolconfig  # noqa: E402
from tool_version import TOOL_VERSION  # noqa: E402

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
TOOLS = [
    {"name": "get_alerts", "description": "Open CI alerts of the monitor (real ones first), with probable cause and suggested action.", "inputSchema": {"type": "object", "properties": {"include_resolved": {"type": "boolean"}}}},
    {"name": "get_red_repos", "description": "Repositories with a workflow that is red on its default branch.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_run_failure", "description": "The failed steps of one run and a short cleaned fragment of its log.", "inputSchema": {"type": "object", "properties": {"repo": {"type": "string"}, "run": {"type": "integer"}}, "required": ["repo", "run"]}},
    {"name": "get_quota", "description": "GitHub allowance and Actions minutes, from the running monitor.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "ack_alert", "description": "Acknowledge an alert (local state only; needs --allow-ack).", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]


def local_get(path, port=8765):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as answer:
        return json.load(answer)


def run_gh(args, timeout=60):
    done = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return done.returncode, done.stdout, done.stderr


def call(name, arguments, config, allow_ack=False, runner=run_gh, getter=local_get):
    """The text a tool answers (already cleaned). Raises ValueError for a bad request."""
    if name == "get_alerts":
        states = None if arguments.get("include_resolved") else ("open", "acknowledged")
        return ai_alerts.redact(json.dumps(ai_alerts.alerts(config, states=states), ensure_ascii=False, indent=1))
    if name == "get_red_repos":
        rows = ai_alerts.alerts(config, states=("open", "acknowledged"))
        return ai_alerts.redact(json.dumps(sorted({a["repo"] for a in rows})))
    if name == "get_run_failure":
        repo, run = str(arguments.get("repo", "")), arguments.get("run")
        if not NAME_RE.match(repo) or not isinstance(run, int) or isinstance(run, bool) or run <= 0:
            raise ValueError("repo and run are required")
        owner = toolconfig.github_owner(config)
        code, out, err = runner(["api", f"repos/{owner}/{repo}/actions/runs/{run}/jobs?per_page=30"])
        if code != 0:
            raise ValueError(ai_alerts.redact(err.strip()[:200]) or "gh failed")
        steps = [f"{job.get('name')}: {step.get('name')}" for job in (json.loads(out).get("jobs") or []) for step in (job.get("steps") or []) if step.get("conclusion") == "failure"]
        code, log, _err = runner(["run", "view", str(run), "--repo", f"{owner}/{repo}", "--log-failed"], 90)
        fragment = "\n".join((log or "").splitlines()[-40:]) if code == 0 else ""
        return ai_alerts.redact("Failed steps:\n" + ("\n".join(steps) or "(none listed)") + "\n\nEnd of the failed log:\n" + fragment, 4000)
    if name == "get_quota":
        return ai_alerts.redact(json.dumps(getter("/api/quota"), ensure_ascii=False)[:3000])
    if name == "ack_alert":
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
        result = {"protocolVersion": version if isinstance(version, str) and len(version) <= 20 else "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "github-actions-monitor", "version": TOOL_VERSION}}
    elif method == "tools/list":
        result = {"tools": [t for t in TOOLS if allow_ack or t["name"] != "ack_alert"]}
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            text = call(params["name"], params.get("arguments") or {}, config, allow_ack, **kwargs)
            result = {"content": [{"type": "text", "text": text}]}
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            result = {"content": [{"type": "text", "text": ai_alerts.redact(str(error))[:300]}], "isError": True}
    elif method == "ping":
        result = {}
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
