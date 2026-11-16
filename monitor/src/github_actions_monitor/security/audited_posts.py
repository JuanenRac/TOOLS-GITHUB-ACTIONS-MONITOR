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
    "/api/ai/actions/confirm": "ai_action",             # an action proposed by the AI is run
    "/api/ai/actions/unlock": "ai_unlock",              # the actions of the AI are unlocked for a while
}

#: route -> why it is not in this table
EXEMPT = {
    "/api/access": "opens a session; the logins and refusals are in the audit of the accesses (auth.audit)",
    "/api/settings": "recorded by its own line (settings_change) with the names of the settings",
    "/api/alerts/mute": "recorded by its own line (alert_mute) once the silence exists",
    "/api/alerts/unmute": "recorded by its own line (alert_unmute) once the silence is gone",
    "/api/hot-only": "a display switch of this process; it changes no stored state",
    "/api/webhook": "a delivery from GitHub signed with the shared secret, not an action of a person",
    "/api/refresh-repos": "reads again the repositories that `finalize --execute` names; it writes nothing on GitHub",
    "/api/sentinel/parte/save": "writes a copy of the daily report in the audit folder; no setting, no GitHub",
    "/api/sentinel/ai": "asks the integrated assistant a question about the picture the monitor holds; changes nothing",
    "/api/ai/test": "tests the connection of the assistant; changes nothing",
    "/api/notify/test": "sends a test message to one channel; changes nothing",
    "/api/ai/ack": "marks an alert as read by an AI; local state of the feed, no setting",
    "/api/welcome": "remembers that the welcome was seen",
    "/api/gh-action/plan": "only prepares what would be sent; nothing is sent until the confirmation, which is recorded",
    "/api/act/plan": "only prepares what would run; nothing runs until the confirmation, which is recorded",
}


def action_for(path):
    """The name of the action to record for a POST to `path`, or None."""
    return AUDITED.get(path)
