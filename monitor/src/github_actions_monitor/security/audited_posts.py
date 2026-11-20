# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Which POST routes of the monitor leave a line in the log of actions, and why each of the others does not.

Every route that accepts a POST is in exactly one of the two tables: AUDITED (a line is written for every request that reaches the handler, with the result and the status, and never the body) or EXEMPT (with
the reason). A test reads the handler and fails when a route is in neither, so a new action cannot be added without deciding whether it is recorded. Standard library only."""

#: route -> name of the action in the log (security/audit_log.py)
AUDITED = {
    "/api/gh-action/confirm": "github_action",          # a rerun, a cancel, a dispatch or a merge on GitHub (the target says which)
    "/api/act/confirm": "local_run",                    # a workflow run on this computer with `act`
    "/api/act/stop": "local_run_stop",
    "/api/github-token": "github_token",                # the token kept by the monitor is saved or deleted (the token itself never goes in)
    "/api/credential": "credential_change",             # the login of this account is replaced or read again
    "/api/mode": "mode_change",                         # the working mode (quota use) changes
    "/api/discovery/group": "discovery_group",          # a suggested group is added to the ecosystems file
    "/api/ai/lessons": "lesson_add",                    # a lesson is added to the library an AI reads
    "/api/ai/failures": "failures_import",              # lines of a book of failures from elsewhere
    "/api/report-files/run": "report_run",              # a report is written now
    "/api/report-files/summary": "report_summary",      # the summary of the next report is approved or removed (the action and its length, never the text)
    "/api/ops/backup": "backup_run",                    # a complete backup package is written now (the file, never its content)
    "/api/updates/check": "update_check",                # the published versions are read from GitHub on request
    "/api/updates/apply": "update_apply",                # an update of the monitor is started (the target, never a path)
    "/api/updates/rollback": "update_rollback",          # the way back to the version before the last update is started
    "/api/ops/purge": "purge_run",                      # the retention purge is run (or only planned) on demand
    "/api/ai/actions/confirm": "ai_action",             # an action proposed by the AI is run
    "/api/assistant/ask": "assistant_ask",              # a fixed question to the assistant (the action and the ids it read, never the text of the question or of the answer)
    "/api/ai/prompts/clear": "prompt_log_clear",        # the local record of prompts is emptied (how many lines, never their text)
    "/api/ai/actions/unlock": "ai_unlock",              # the actions of the AI are unlocked for a while
    "/api/screens/logo": "screens_logo_upload",                # the logo of the organization is uploaded (its kind and size go in, never its content)
    "/api/screens/logo/remove": "screens_logo_remove",         # the logo of the organization is removed
}

#: route -> why it is not in this table
EXEMPT = {
    "/api/updates/plan": "only reads: it downloads and checks the zip and says what an update would do; nothing is applied (the apply that follows is recorded)",
    "/api/access": "opens a session; the logins and refusals are in the audit of the accesses (auth.audit)",
    "/api/settings": "recorded by its own line (settings_change) with the names of the settings",
    "/api/alerts/mute": "recorded by its own line (alert_mute) once the silence exists",
    "/api/alerts/unmute": "recorded by its own line (alert_unmute) once the silence is gone",
    "/api/hot-only": "a display switch of this process; it changes no stored state",
    "/api/webhook": "a delivery from GitHub signed with the shared secret, not an action of a person",
    "/api/chatops/slack": "a signed command of the chat; every command that reaches the monitor leaves its own line (chatops_command) with the ids of the chat, and it only reads",
    "/api/chatops/discord": "a signed command of the chat; every command that reaches the monitor leaves its own line (chatops_command) with the ids of the chat, and it only reads",
    "/api/refresh-repos": "reads again the repositories that `finalize --execute` names; it writes nothing on GitHub",
    "/api/sentinel/parte/save": "writes a copy of the daily report in the audit folder; no setting, no GitHub",
    "/api/sentinel/ai": "asks the integrated assistant a question about the picture the monitor holds; changes nothing",
    "/api/ai/test": "tests the connection of the assistant; changes nothing",
    "/api/ai/models/refresh": "asks the provider for its list of models and keeps it; changes no setting and nothing on GitHub",
    "/api/ai/models/test": "tests one model of the provider with a short question; changes nothing",
    "/api/ai/models/data": "returns the table of data each model may see; read only",
    "/api/ai/doctor": "checks the configuration of the assistant and reports; changes nothing",
    "/api/notify/test": "sends a test message to one channel; changes nothing",
    "/api/ai/ack": "marks an alert as read by an AI; local state of the feed, no setting",
    "/api/welcome": "remembers that the welcome was seen",
    "/api/gh-action/plan": "only prepares what would be sent; nothing is sent until the confirmation, which is recorded",
    "/api/act/plan": "only prepares what would run; nothing runs until the confirmation, which is recorded",
}


def action_for(path):
    """The name of the action to record for a POST to `path`, or None."""
    return AUDITED.get(path)
