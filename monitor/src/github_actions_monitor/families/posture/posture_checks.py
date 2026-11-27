# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What each answer of GitHub means. Every function takes a reader `get(endpoint)` (GET only) that raises Unread when GitHub does not answer, and returns the findings {"check", "item", "detail"}.
A read that is not allowed or fails is never "fine": the group is listed as not checked."""
import calendar
import fnmatch
import re
import time
import urllib.parse


class Unread(Exception):
    """A read without an answer. `reason`: missing (404), forbidden (403), rate_limited, failed."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def finding(check, item="", detail=""):
    return {"check": check, "item": str(item)[:140], "detail": str(detail)[:200]}


def epoch(text):
    try:
        return calendar.timegm(time.strptime(str(text)[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return 0


def _dicts(value):
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _dict(value):
    return value if isinstance(value, dict) else {}


def _optional(get, endpoint):
    """The answer, or None when there is no such thing (404). Any other refusal is still Unread."""
    try:
        return get(endpoint)
    except Unread as error:
        if error.reason == "missing":
            return None
        raise


def hooks(get, base, ctx):
    out = []
    for hook in _dicts(get(f"{base}/hooks?per_page=100")):
        if hook.get("active") is False:
            continue
        cfg = _dict(hook.get("config"))
        host = urllib.parse.urlsplit(str(cfg.get("url") or "")).hostname or "?"      # only the host: the address of a hook often carries a token
        if not cfg.get("secret"):
            out.append(finding("webhook.no_secret", host))
        if str(cfg.get("url") or "").lower().startswith("http://"):
            out.append(finding("webhook.plain_http", host))
        if str(cfg.get("insecure_ssl", "0")) == "1":
            out.append(finding("webhook.tls_off", host))
    return out


def actions(get, base, ctx):
    out = []
    perms = _dict(get(f"{base}/actions/permissions"))
    if perms.get("enabled") is False:
        return out
    if perms.get("allowed_actions") == "all":
        out.append(finding("actions.all_allowed"))
    if perms.get("sha_pinning_required") is False:
        out.append(finding("actions.sha_not_required"))
    workflow = _dict(get(f"{base}/actions/permissions/workflow"))
    if workflow.get("default_workflow_permissions") == "write":
        out.append(finding("actions.token_write"))
    if workflow.get("can_approve_pull_request_reviews") is True:
        out.append(finding("actions.approves_prs"))
    if ctx["repo_info"].get("private") is not True:
        approval = _optional(get, f"{base}/actions/permissions/fork-pr-contributor-approval")
        if _dict(approval).get("approval_policy") == "first_time_contributors_new_to_github":
            out.append(finding("actions.fork_approval", detail="first_time_contributors_new_to_github"))
    return out


def scan(get, base, ctx):
    out = []
    info = ctx["repo_info"]
    analysis = info.get("security_and_analysis")
    if isinstance(analysis, dict):      # only people with admin rights get this block: without it nothing is said
        for key, check in (("secret_scanning", "scan.no_credentials"), ("secret_scanning_push_protection", "scan.no_push_protection")):
            if _dict(analysis.get(key)).get("status") == "disabled":
                out.append(finding(check))
    else:
        raise Unread("forbidden")
    try:
        get(f"{base}/vulnerability-alerts")
    except Unread as error:
        if error.reason != "missing":
            raise
        out.append(finding("scan.no_dependency_alerts"))
    setup = _optional(get, f"{base}/code-scanning/default-setup")
    if _dict(setup).get("state") != "configured" and not _optional(get, f"{base}/code-scanning/analyses?per_page=1"):
        out.append(finding("scan.no_code"))
    return out


def _exists(get, base, paths_):
    return any(_optional(get, f"{base}/contents/{path}") is not None for path in paths_)


def files(get, base, ctx):
    out = []
    profile = _dict(_optional(get, f"{base}/community/profile"))
    listed = _dict(profile.get("files"))
    if not listed.get("security") and not _exists(get, base, ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md")):
        out.append(finding("repo.no_policy"))
    if not _exists(get, base, (".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json", ".github/renovate.json", ".renovaterc.json")):
        out.append(finding("repo.no_update_tool"))
    return out


def _protection(get, base, branch):
    """What protects a branch: (protected, reviews asked, who can skip them)."""
    name = urllib.parse.quote(branch, safe="")
    protected, reviews, bypass = False, 0, []
    rules = _dicts(_optional(get, f"{base}/rules/branches/{name}"))
    for rule in rules:
        protected = True
        if rule.get("type") == "pull_request":
            reviews = max(reviews, _dict(rule.get("parameters")).get("required_approving_review_count") or 0)
    for ruleset in sorted({r.get("ruleset_id") for r in rules if isinstance(r.get("ruleset_id"), int)})[:5]:
        detail = _dict(_optional(get, f"{base}/rulesets/{ruleset}"))
        actors = _dicts(detail.get("bypass_actors"))
        if actors:
            bypass.append(f"ruleset {detail.get('name') or ruleset}: " + ", ".join(sorted({str(a.get('actor_type')) for a in actors})))
    classic = _dict(_optional(get, f"{base}/branches/{name}/protection"))
    if classic:
        protected = True
        required = _dict(classic.get("required_pull_request_reviews"))
        reviews = max(reviews, required.get("required_approving_review_count") or 0)
        allowed = _dict(required.get("bypass_pull_request_allowances"))
        skippers = [f"{kind}: {len(allowed.get(kind) or [])}" for kind in ("users", "teams", "apps") if allowed.get(kind)]
        if skippers:
            bypass.append("reviews: " + ", ".join(skippers))
        if required and _dict(classic.get("enforce_admins")).get("enabled") is False:
            bypass.append("administrators")
    return protected, reviews, bypass


def branch(get, base, ctx):
    out = []
    default = ctx["repo_info"].get("default_branch") or "main"
    protected, reviews, bypass = _protection(get, base, default)
    if not protected:
        out.append(finding("branch.unprotected", default))
    else:
        if not reviews:
            out.append(finding("branch.no_review", default))
        if bypass:
            out.append(finding("branch.bypass", default, "; ".join(bypass)))
    patterns = ctx["cfg"].get("release_branches") or []
    if patterns:
        names = [b.get("name") for b in _dicts(get(f"{base}/branches?per_page=100"))]
        for name in [n for n in names if isinstance(n, str) and n != default and any(fnmatch.fnmatchcase(n, p) for p in patterns)][:10]:
            if not _protection(get, base, name)[0]:
                out.append(finding("branch.release_unprotected", name))
    return out


def reviews(get, base, ctx):
    out = []
    sample = ctx["cfg"].get("review_sample") or 0
    if not sample:
        return out
    default = urllib.parse.quote(ctx["repo_info"].get("default_branch") or "main", safe="")
    pulls = _dicts(get(f"{base}/pulls?state=closed&base={default}&sort=updated&direction=desc&per_page={min(100, sample * 2)}"))
    for pull in [p for p in pulls if p.get("merged_at")][:sample]:
        found = _dicts(get(f"{base}/pulls/{int(pull.get('number') or 0)}/reviews?per_page=50"))
        if not any(r.get("state") == "APPROVED" for r in found):
            out.append(finding("branch.merged_unreviewed", f"#{pull.get('number')}"))
    return out


def deploy(get, base, ctx):
    out = []
    limit = ctx["cfg"]["deploy_max_days"] * 86400
    for key in _dicts(get(f"{base}/keys?per_page=100")):
        title = key.get("title") or key.get("id")
        if key.get("read_only") is False:
            out.append(finding("deploy.write", title))
        created = epoch(key.get("created_at"))
        if created and ctx["now"] - created > limit:
            out.append(finding("deploy.old", title, f"{int((ctx['now'] - created) / 86400)} d"))
    return out


def _old_names(answer, ctx, scope):
    """Names and dates only: GitHub never gives a value and none is asked for."""
    limit = ctx["cfg"]["stored_max_days"] * 86400
    out = []
    for row in _dicts(_dict(answer).get("secrets")):
        changed = epoch(row.get("updated_at") or row.get("created_at"))
        if changed and ctx["now"] - changed > limit:
            out.append(finding("stored.old", f"{scope}{row.get('name')}", f"{int((ctx['now'] - changed) / 86400)} d"))
    return out


def stored(get, base, ctx):
    return _old_names(get(f"{base}/actions/secrets?per_page=100"), ctx, "")


def releases(get, base, ctx):
    """Compares the published releases with what was seen before (ctx["memory"], kept between reads): an asset that changed or went away, a tag that points elsewhere, a publication outside the window."""
    out = []
    seen = ctx["memory"].setdefault("releases", {})
    first = not seen.get("_read")
    for release in _dicts(get(f"{base}/releases?per_page=10")):
        tag = release.get("tag_name")
        if release.get("draft") or not isinstance(tag, str):
            continue
        ref = _optional(get, f"{base}/git/ref/tags/{urllib.parse.quote(tag, safe='')}")
        sha = _dict(_dict(ref).get("object")).get("sha") or ""
        assets = {str(a.get("name")): f"{a.get('id')}:{a.get('size')}:{a.get('digest') or ''}" for a in _dicts(release.get("assets"))}
        before = seen.get(tag)
        if before:
            if sha and before["sha"] and sha != before["sha"]:
                before["moved"] = sha[:12]
            for name, mark in before["assets"].items():
                if name not in assets:
                    before.setdefault("removed", {})[name] = True
                elif assets[name] != mark:
                    before.setdefault("replaced", {})[name] = True
            before["assets"].update(assets)
        else:
            outside = not first and not in_window(ctx["cfg"].get("release_window"), epoch(release.get("published_at")))
            before = seen[tag] = {"sha": sha, "assets": assets, "outside": outside}
        if before.get("moved"):
            out.append(finding("release.tag_moved", tag, before["moved"]))
        out.extend(finding("release.asset_replaced", f"{tag} {name}") for name in before.get("replaced", {}))
        out.extend(finding("release.asset_removed", f"{tag} {name}") for name in before.get("removed", {}))
        if before.get("outside"):
            out.append(finding("release.outside_window", tag, release.get("published_at")))
    seen["_read"] = True
    for old in [t for t in seen if t != "_read"][:-30]:
        del seen[old]
    return out


def in_window(window, moment):
    """True when there is no window, or the moment (UTC) is inside "D-D HH-HH" (1 = Monday), for example "1-5 07-19"."""
    match = re.match(r"^([1-7])-([1-7]) ([01]\d|2[0-4])-([01]\d|2[0-4])$", str(window or "").strip())
    if not match or not moment:
        return True
    first, last, start, end = (int(g) for g in match.groups())
    when = time.gmtime(moment)
    return first <= when.tm_wday + 1 <= last and start <= when.tm_hour < end


HARDENERS = ("harden runner", "harden-runner", "step-security")


def runner(get, base, ctx):
    """Coverage of a hardening step by what RAN (the steps of the jobs of the last runs), not by what the YAML says."""
    out = []
    count = ctx["cfg"].get("runner_runs") or 0
    if not count:
        return out
    covered = {}
    for run in _dicts(_dict(get(f"{base}/actions/runs?status=completed&per_page={count}")).get("workflow_runs")):
        name = str(run.get("name") or run.get("path"))
        if name in covered:
            continue
        jobs = _dicts(_dict(get(f"{base}/actions/runs/{int(run.get('id') or 0)}/jobs?per_page=50")).get("jobs"))
        hosted = [j for j in jobs if j.get("steps")]
        if hosted:
            covered[name] = all(any(h in str(s.get("name", "")).lower() for s in _dicts(j.get("steps")) for h in HARDENERS) for j in hosted)
    before = ctx["memory"].get("hardened", {})
    for name, yes in covered.items():
        if not yes:
            out.append(finding("runner.coverage_lost" if before.get(name) else "runner.not_hardened", name))
    ctx["memory"]["hardened"] = {name: yes or bool(before.get(name)) for name, yes in covered.items()}
    return out


REPO_GROUPS = {"hooks": hooks, "actions": actions, "scan": scan, "files": files, "branch": branch, "reviews": reviews, "deploy": deploy, "stored": stored, "runner": runner, "releases": releases}


def org_settings(get, base, ctx):
    info = _dict(get(base))
    out = []
    if "two_factor_requirement_enabled" not in info:
        raise Unread("forbidden")
    if info.get("two_factor_requirement_enabled") is False:
        out.append(finding("org.no_two_factor"))
    if info.get("default_repository_permission") in ("write", "admin"):
        out.append(finding("org.default_write", info.get("default_repository_permission")))
    if info.get("members_can_create_public_repositories") is True:
        out.append(finding("org.public_creation"))
    return out


def org_hooks(get, base, ctx):
    return hooks(get, base, ctx)


def org_stored(get, base, ctx):
    return _old_names(get(f"{base}/actions/secrets?per_page=100"), ctx, "org: ")


BROAD = ("administration", "contents", "workflows", "secrets", "organization_administration", "members")


def _writes(permissions):
    return sorted(k for k, v in _dict(permissions).items() if v in ("write", "admin"))


def pats(get, base, ctx):
    """Fine-grained personal access tokens with access to the organization that can write to the organization or to all its repositories. GitHub only answers this to a GitHub App; with a personal
    token the group is listed as not checked. Names and permissions only: a token itself is never in the answer."""
    answer = get(f"{base}/personal-access-tokens?per_page=100")
    if not isinstance(answer, list):
        raise Unread("failed")
    out = []
    for row in _dicts(answer):
        if row.get("token_expired") is True:
            continue
        granted = _dict(row.get("permissions"))
        broad = _writes(granted.get("organization"))
        if row.get("repository_selection") == "all":
            broad += _writes(granted.get("repository"))
        if broad:
            detail = ", ".join(broad[:6]) + ("" if row.get("token_expires_at") else "; no expiry")
            out.append(finding("org.pat_broad", f"{_dict(row.get('owner')).get('login', '?')}: {row.get('token_name') or '?'}", detail))
    return out[:50]


def upstream(get, base, ctx):
    """For a fork: what its public original does not have (security policy, update tool). A signal about where the code comes from, not about the fork."""
    parent = str(_dict(ctx["repo_info"].get("parent")).get("full_name") or "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}/[A-Za-z0-9._-]{1,100}", parent) or ".." in parent:
        return []
    found = files(get, f"repos/{parent}", ctx)
    if not found:
        return []
    return [finding("original.weak", parent, ", ".join(sorted(f["check"].split(".", 1)[1] for f in found)))]


def apps(get, base, ctx):
    """Apps of the organization that can WRITE something sensitive in all its repositories."""
    out = []
    for app in _dicts(_dict(get(f"{base}/installations?per_page=100")).get("installations")):
        writes = sorted(k for k, v in _dict(app.get("permissions")).items() if k in BROAD and v in ("write", "admin"))
        if writes and app.get("repository_selection") == "all":
            out.append(finding("org.app_broad", app.get("app_slug"), ", ".join(writes)))
    return out


AUDIT_ACTIONS = ("hook.", "protected_branch.destroy", "protected_branch.policy_override", "repository_ruleset.destroy", "repository_ruleset.update", "repo.access", "org.update_default_repository_permission",
                 "org.disable_two_factor_requirement", "org.add_member", "integration_installation.create", "org.add_outside_collaborator")


def audit(get, base, ctx):
    """Changes of settings in the audit log of the organization (GitHub Enterprise) in the last 7 days."""
    if not ctx["cfg"].get("audit_log"):
        return []
    out = []
    for row in _dicts(get(f"{base}/audit-log?per_page=100&order=desc")):
        action = str(row.get("action") or "")
        when = (row.get("@timestamp") or row.get("created_at") or 0)
        when = when / 1000 if isinstance(when, (int, float)) else epoch(when)
        if action.startswith(AUDIT_ACTIONS) and ctx["now"] - when < 7 * 86400:
            out.append(finding("org.settings_changed", f"{action} {row.get('repo') or ''}".strip(), row.get("actor")))
    return out[:20]


ORG_GROUPS = {"org": org_settings, "hooks": org_hooks, "stored": org_stored, "apps": apps, "audit": audit, "pats": pats}
