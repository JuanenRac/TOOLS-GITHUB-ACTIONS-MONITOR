# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the MCP server adds beyond plain tools: guided PROMPTS, a self-description, deep links and governed writes.

  * Prompts (`mcp.prompts`, on): `prompts/list` and `prompts/get` give the AI a step-by-step plan to follow instead of improvising it: `am_i_affected` (is an incident or a package present in my
    repositories?), `investigate_red` (why is this repository red?) and `weekly_review` (what needs a person this week?). A prompt is text: it runs nothing.
  * `describe_capabilities`, `ping` and `whoami`: what the server can do and with which switches, that it answers, and which account and mode it works for. Read only.
  * `dashboard_url` in the answers about alerts, quota and diagnoses: the address of the page of the monitor that shows the same thing.
  * Writes (`mcp.write_tools`, OFF): the single tool `gh_action` plans an action on GitHub and shows what it would send (the preview: method, endpoint, repository, number, reason); nothing is sent
    until the same call comes back with `confirm: true` and the `plan_id` of the preview. It goes through the same module as the page (`integrations/ghactions`), so it needs `github_actions.enabled`,
    a reason, an operator (here `mcp`), the permission of the credential and the single writer; every attempt is written in the log of actions. With `mcp.write_tools` off the tool does not even exist."""
import json

from github_actions_monitor.util import ports

DEFAULTS = {"prompts": True, "write_tools": False}

PROMPTS = {
    "am_i_affected": {
        "description": "A reproducible plan to find out whether an incident, a vulnerable package or a compromised action is present in the repositories that are watched.",
        "arguments": [{"name": "subject", "description": "the package, action or incident to look for (for example tj-actions/changed-files)", "required": True}],
        "steps": ["Call get_alerts and read the open alerts; note any that already name {subject}.",
                  "Call monitor_state and look at the signals of the panels a10 (releases), a4 (hygiene) and supply for {subject}.",
                  "Call sentinel_panels and list every repository whose rows mention {subject}, with the file and the line when the row has them.",
                  "For each repository found call get_run_failure only if a run of it is red, to see whether {subject} is in the failed step.",
                  "Answer with: the repositories affected (or 'none found'), the evidence for each (panel, row), what could NOT be checked and why, and the next step for a person. Do not guess."],
    },
    "investigate_red": {
        "description": "Why is a repository red? The same order every time: alert, failing step, log, similar failures, next step.",
        "arguments": [{"name": "repo", "description": "the repository", "required": True}],
        "steps": ["Call alerts_open and find the alerts of {repo}.", "For each one call diagnose with its id to get the failing step and the last lines of the log.",
                  "Call lessons_apply with {repo} and the failing text to see whether the book of failures already knows it.",
                  "Say in one sentence what failed, in one what probably caused it, and give the single next step. Say 'not enough evidence' instead of guessing."],
    },
    "weekly_review": {
        "description": "What needs a person this week: reds, stuck builds, releases waiting and the allowance.",
        "arguments": [],
        "steps": ["Call monitor_state with only the signals that need action.", "Call get_quota and say how much of the allowance is left.", "Call get_score and name the part that pulls it down.",
                  "Write a list ordered by urgency: what to do, where (the dashboard_url), and what can wait."],
    },
}


def settings(config):
    block = config.get("mcp") if isinstance(config, dict) and isinstance(config.get("mcp"), dict) else {}
    return {"prompts": block.get("prompts") is not False, "write_tools": block.get("write_tools") is True}


def prompt_list(config):
    if not settings(config)["prompts"]:
        return {"prompts": []}
    return {"prompts": [{"name": n, "description": p["description"], "arguments": p["arguments"]} for n, p in PROMPTS.items()]}


def prompt_get(config, name, arguments):
    """{"description", "messages"} for a prompt; ValueError for an unknown one or a missing argument. The arguments are cut and cleaned: they are text for the plan, never commands."""
    if not settings(config)["prompts"] or name not in PROMPTS:
        raise ValueError("unknown prompt")
    spec, given = PROMPTS[name], arguments if isinstance(arguments, dict) else {}
    values = {}
    for arg in spec["arguments"]:
        text = " ".join(str(given.get(arg["name"], "")).split())[:100]
        if arg["required"] and not text:
            raise ValueError("missing argument: " + arg["name"])
        values[arg["name"]] = "".join(c for c in text if c.isalnum() or c in "/._-@: ")
    steps = "\n".join(f"{i}. {step.format(**values)}" for i, step in enumerate(spec["steps"], 1))
    return {"description": spec["description"], "messages": [{"role": "user", "content": {"type": "text", "text": f"Follow these steps in order and report what you find.\n{steps}"}}]}


def dashboard_url(tab=""):
    return f"http://127.0.0.1:{ports.resolve('complete')}/" + (f"?tab={tab}" if tab else "")


def with_link(text, tab=""):
    """The JSON object in `text` with `dashboard_url`; any other text (a list, plain text) is returned as it is."""
    try:
        doc = json.loads(text)
    except ValueError:
        return text
    if isinstance(doc, dict):
        doc["dashboard_url"] = dashboard_url(tab)
        return json.dumps(doc, indent=1, ensure_ascii=False)
    return text


def describe(config, allow_ack, allow_lessons, tools):
    cfg = settings(config)
    from github_actions_monitor.integrations import ghactions
    gh = ghactions.settings(config)
    return {"read": [t["name"] for t in tools if not t.get("write")], "writes": {"ack_alert": allow_ack, "lessons": allow_lessons, "gh_action": cfg["write_tools"] and gh["enabled"]},
            "prompts": list(PROMPTS) if cfg["prompts"] else [], "switches": {"mcp.prompts": cfg["prompts"], "mcp.write_tools": cfg["write_tools"], "github_actions.enabled": gh["enabled"],
                                                                           "github_actions.require_reason": gh["require_reason"]},
            "notes": "Read only unless a switch above is on. Every answer is cleaned of tokens, keys, e-mails, IPs and home folders.", "dashboard_url": dashboard_url()}


def whoami(config):
    from github_actions_monitor.app import toolconfig
    return {"account": toolconfig.github_owner(config) or "", "mode": "mcp over standard input and output (this computer)", "dashboard_url": dashboard_url()}


WRITE_TOOL = {"name": "gh_action", "write": True, "description": "Plan an action on GitHub (rerun_failed, cancel, close_issue, close_pr, merge_pr) and see what it would send; nothing is sent until the same call comes back with confirm true and the plan_id. Needs mcp.write_tools and github_actions.enabled; a reason is required.",
              "inputSchema": {"type": "object", "properties": {"action": {"type": "string"}, "repo": {"type": "string"}, "number": {"type": "integer"}, "reason": {"type": "string"}, "confirm": {"type": "boolean"}, "plan_id": {"type": "string"}},
                              "required": ["action", "repo", "number", "reason"]}}
EXTRA_TOOLS = [{"name": "describe_capabilities", "description": "What this server can do, with which switches on, and the address of the dashboard.", "inputSchema": {"type": "object", "properties": {}}},
               {"name": "ping", "description": "Answers pong: the server is alive.", "inputSchema": {"type": "object", "properties": {}}},
               {"name": "whoami", "description": "The account and the mode this server works for.", "inputSchema": {"type": "object", "properties": {}}}]


def governed_write(config, arguments, runner):
    """The preview, or the result of a confirmed action. Raises ValueError when writes are off or the request is not valid; a refusal of the module of the actions is told as it is."""
    from github_actions_monitor.app import toolconfig
    from github_actions_monitor.integrations import ghactions
    if not settings(config)["write_tools"]:
        raise ValueError("writing is off: turn on mcp.write_tools")
    if arguments.get("confirm") is True:
        plan_id = str(arguments.get("plan_id") or "")
        if not plan_id:
            raise ValueError("confirm needs the plan_id of the preview")
        return json.dumps(ghactions.execute(config, plan_id, runner), ensure_ascii=False)
    item, why = ghactions.plan(config, toolconfig.github_owner(config), arguments.get("action"), arguments.get("repo"), arguments.get("number"), reason=arguments.get("reason") or "", operator="mcp", run_gh=runner)
    if item is None:
        raise ValueError("refused: " + why)
    preview = {k: item[k] for k in ("action", "method", "endpoint", "repo", "number", "reason", "operator")}
    return json.dumps({"preview": preview, "touches": 1, "plan_id": item["id"], "to_confirm": "call gh_action again with confirm true and this plan_id", "dashboard_url": dashboard_url()}, ensure_ascii=False)
