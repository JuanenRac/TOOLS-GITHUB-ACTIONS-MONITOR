# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The closed list of posture checks: for each one its level, the profile that asks for it, the group of reads it needs, and where it sits in the OWASP Top 10 CI/CD risks and in the
CIS Software Supply Chain Security guide. The mapping is a guide to read the findings, not a certification and not a claim that a standard is met."""

# id: (level, "basic" | "strict", group, OWASP CICD-SEC number, CIS section)
CHECKS = {
    "webhook.no_secret": ("error", "basic", "hooks", 8, "2.4"),
    "webhook.plain_http": ("warning", "basic", "hooks", 9, "2.4"),
    "webhook.tls_off": ("warning", "basic", "hooks", 9, "2.4"),
    "actions.token_write": ("warning", "basic", "actions", 5, "2.1"),
    "actions.approves_prs": ("warning", "basic", "actions", 1, "2.1"),
    "actions.all_allowed": ("warning", "basic", "actions", 3, "2.4"),
    "actions.sha_not_required": ("info", "strict", "actions", 9, "2.4"),
    "actions.fork_approval": ("warning", "basic", "actions", 4, "2.1"),
    "scan.no_code": ("info", "strict", "scan", 7, "1.5"),
    "scan.no_credentials": ("warning", "basic", "scan", 6, "1.5"),
    "scan.no_push_protection": ("warning", "basic", "scan", 6, "1.5"),
    "scan.no_dependency_alerts": ("warning", "basic", "scan", 3, "3.2"),
    "repo.no_policy": ("info", "basic", "files", 10, "1.2"),
    "repo.no_update_tool": ("info", "basic", "files", 3, "3.1"),
    "branch.unprotected": ("error", "basic", "branch", 1, "1.1"),
    "branch.no_review": ("warning", "strict", "branch", 1, "1.1"),
    "branch.bypass": ("warning", "basic", "branch", 1, "1.1"),
    "branch.release_unprotected": ("warning", "basic", "branch", 1, "1.1"),
    "branch.merged_unreviewed": ("warning", "basic", "reviews", 1, "1.1"),
    "deploy.write": ("warning", "basic", "deploy", 2, "5.1"),
    "deploy.old": ("info", "basic", "deploy", 6, "5.1"),
    "stored.old": ("info", "basic", "stored", 6, "2.3"),
    "org.no_two_factor": ("error", "basic", "org", 2, "1.3"),
    "org.default_write": ("warning", "basic", "org", 2, "1.3"),
    "org.public_creation": ("info", "strict", "org", 2, "1.2"),
    "org.app_broad": ("warning", "basic", "apps", 8, "1.4"),
    "org.settings_changed": ("warning", "basic", "audit", 10, "5.2"),
    "org.pat_broad": ("warning", "basic", "pats", 2, "1.4"),
    "upstream.weak": ("info", "basic", "upstream", 3, "3.1"),
    "runner.not_hardened": ("info", "strict", "runner", 7, "2.2"),
    "runner.coverage_lost": ("warning", "basic", "runner", 7, "2.2"),
    "release.asset_replaced": ("error", "basic", "releases", 9, "4.1"),
    "release.asset_removed": ("warning", "basic", "releases", 9, "4.1"),
    "release.tag_moved": ("error", "basic", "releases", 9, "4.1"),
    "release.outside_window": ("warning", "basic", "releases", 1, "4.1"),
}

OWASP = {1: "Insufficient Flow Control Mechanisms", 2: "Inadequate Identity and Access Management", 3: "Dependency Chain Abuse", 4: "Poisoned Pipeline Execution", 5: "Insufficient Pipeline-Based Access Controls",
         6: "Insufficient Credential Hygiene", 7: "Insecure System Configuration", 8: "Ungoverned Usage of 3rd Party Services", 9: "Improper Artifact Integrity Validation", 10: "Insufficient Logging and Visibility"}

#: the permission of a fine-grained token or of a GitHub App that each group of reads needs (read only in every case)
PERMISSIONS = {"hooks": "Webhooks: read", "actions": "Administration: read", "scan": "Administration: read; Code scanning alerts: read", "files": "Contents: read", "branch": "Administration: read; Metadata: read",
               "reviews": "Pull requests: read", "deploy": "Administration: read", "stored": "Secrets: read (names and dates only)", "org": "Organization administration: read", "apps": "Organization administration: read",
               "audit": "Organization administration: read (audit log, GitHub Enterprise)", "pats": "Organization personal access tokens: read (only a GitHub App can ask)", "upstream": "Contents: read (the public original of a fork)", "runner": "Actions: read", "releases": "Contents: read"}

#: the kinds of project and the checks each one does not ask for
TYPES = {"standard": (), "library": ("runner.not_hardened",), "internal": ("repo.no_policy", "scan.no_code", "org.public_creation"),
         "sandbox": ("repo.no_policy", "repo.no_update_tool", "scan.no_code", "branch.no_review", "branch.unprotected", "branch.release_unprotected", "branch.merged_unreviewed", "runner.not_hardened")}


def wanted(check, profile="basic", kind="standard", skip=()):
    level_of = CHECKS.get(check)
    if level_of is None or check in skip or check in TYPES.get(kind, ()):
        return False
    return profile == "strict" or level_of[1] == "basic"


#: group of reads -> the permission of a GitHub App that unlocks it (its name in the answer of the installation)
APP_PERMISSIONS = {"hooks": "repository_hooks", "actions": "administration", "scan": "administration", "files": "contents", "branch": "administration", "reviews": "pull_requests", "deploy": "administration",
                   "stored": "secrets", "org": "organization_administration", "apps": "organization_administration", "audit": "organization_administration",
                   "pats": "organization_personal_access_tokens", "runner": "actions", "releases": "contents", "upstream": "contents"}


def matrix(unread=(), granted=None):
    """permission -> the checks that need it; `unread` is the set of groups GitHub refused to answer."""
    rows = []
    for group, permission in PERMISSIONS.items():
        rows.append({"group": group, "permission": permission, "checks": [c for c, v in CHECKS.items() if v[2] == group], "refused": group in unread,
                     "app_permission": APP_PERMISSIONS[group], "granted": "unknown" if granted is None else str(granted.get(APP_PERMISSIONS[group]) or "unknown")})
    return rows
