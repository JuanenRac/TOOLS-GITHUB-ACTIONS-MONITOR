# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Why a read of GitHub came back empty, and how much allowance an account will cost: the part of `--doctor` that helps an organization or a big personal account get started.

A 403 or a 404 from GitHub has a handful of different causes that look the same on the page ("no data"): the token is not authorised for an organization with SAML single sign-on, the token lacks a
scope or a permission, the repository is private and the token cannot see it, the allowance is spent, the login was refused. `diagnose()` tells them apart from the text of the error, and `probe()` asks
GitHub three small questions to find out which one applies to this login. `estimate()` is a local estimate (no call) of the reads per hour a number of repositories and workflows will need under the
current settings, against the allowance of the token. Nothing here writes to GitHub, and no token is ever read, printed or kept: the headers that are looked at are the answer's, not the request's."""
import json
import math
import re

CAUSES = ("sso", "rate_limited", "auth", "scope", "not_found", "forbidden", "network", "unknown")

#: documented minimum for a CLASSIC token: scope -> what needs it
CLASSIC_SCOPES = {"repo": "private repositories (reads of runs, contents, pull requests, issues, rulesets, alerts); public_repo is enough when every repository is public",
                  "read:org": "listing the repositories and teams of an organization",
                  "security_events": "optional: code scanning alerts (panel A3)", "read:project": "optional: the GitHub Projects boards (panel A9)"}
#: documented minimum for a FINE-GRAINED token (read only; the resource owner is ONE account or organization)
FINE_PERMISSIONS = ("Metadata", "Actions", "Contents", "Pull requests", "Issues", "Administration (rulesets and branch rules)", "Code scanning alerts", "Dependabot alerts", "Secret scanning alerts")

#: extra terms of the estimate other parts of the monitor can add: callables (config, repos, workflows) -> (label, calls per hour)
ESTIMATE_TERMS = []


def diagnose(message):
    """The cause of a failed read from the text of the error of `gh`: one of CAUSES. Pure."""
    low = str(message or "").lower()
    if "saml" in low or "sso" in low or "single sign-on" in low:
        return "sso"
    if "rate limit" in low or "secondary rate" in low:
        return "rate_limited"
    if "401" in low or "bad credentials" in low or "requires authentication" in low:
        return "auth"
    if "not accessible by" in low or "resource not accessible" in low or "required scope" in low or "scopes" in low and "403" in low:
        return "scope"
    if "404" in low or "not found" in low:
        return "not_found"
    if "403" in low or "forbidden" in low:
        return "forbidden"
    if any(w in low for w in ("timeout", "timed out", "could not resolve", "connection", "network")):
        return "network"
    return "unknown"


def parse_response(text):
    """(status, headers, body) of the output of `gh api -i`: the status number or None, the headers with lower-case names, the rest as text. Tolerates output without headers."""
    raw = str(text or "").replace("\r\n", "\n")
    head, _, body = raw.partition("\n\n")
    lines = head.split("\n")
    match = re.match(r"^HTTP/\S+\s+(\d{3})", lines[0].strip()) if lines else None
    if not match:
        return None, {}, raw
    headers = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        if value:
            headers[name.strip().lower()] = value.strip()
    return int(match.group(1)), headers, body


def scopes_of(headers):
    """The scopes of a classic token from the answer's `x-oauth-scopes`, or None when the answer has no such header (a fine-grained token or a GitHub App does not send it)."""
    value = (headers or {}).get("x-oauth-scopes")
    return None if value is None else sorted(s.strip() for s in value.split(",") if s.strip())


def sso_partial(headers):
    """True when GitHub says it left out the results of organizations the token is not authorised for (`x-github-sso: partial-results; organizations=...`)."""
    return "partial-results" in str((headers or {}).get("x-github-sso") or "")


def probe(runner, owner=""):
    """Three small reads, in order: who the login is (and its scopes), whether the account is visible and how many repositories it has, and whether the list of its repositories is complete.
    Returns {"cause": "" | one of CAUSES, "login", "scopes", "owner_kind", "repos", "partial", "stage"}. `runner(args)` = (code, stdout, stderr); the tests give a fake one."""
    out = {"cause": "", "login": "", "scopes": None, "owner_kind": "", "repos": None, "partial": False, "stage": "user"}
    code, stdout, stderr = runner(["gh", "api", "-i", "user"])
    status, headers, body = parse_response(stdout)
    if code != 0 or (status is not None and status >= 400):
        out["cause"] = diagnose(stderr or body or stdout)
        return out
    if status is None:      # an answer without headers (a runner that is not `gh`): nothing to judge
        out["cause"] = ""
        out["stage"] = "unchecked"
        return out
    try:
        data = json.loads(body)
        out["login"] = str(data.get("login") or "")[:60] if isinstance(data, dict) else ""
    except ValueError:
        pass
    out["scopes"] = scopes_of(headers)
    owner = owner or out["login"]
    if not owner:
        return out
    out["stage"] = "owner"
    for kind, endpoint in (("organization", f"orgs/{owner}"), ("user", f"users/{owner}")):
        code, stdout, stderr = runner(["gh", "api", "-i", endpoint])
        status, headers, body = parse_response(stdout)
        if code == 0 and (status is None or status < 400):
            out["owner_kind"] = kind
            try:
                info = json.loads(body)
            except ValueError:
                info = {}
            if isinstance(info, dict):
                total = (info.get("public_repos") or 0) + (info.get("total_private_repos") or info.get("owned_private_repos") or 0)
                out["repos"] = total if isinstance(total, int) and total >= 0 else None
            break
        cause = diagnose(stderr or body or stdout)
        if cause == "sso":
            out["cause"] = "sso"
            return out
        if kind == "user":
            out["cause"] = "not_found" if cause in ("not_found", "unknown") else cause
            return out
    out["stage"] = "repos"
    endpoint = f"orgs/{owner}/repos?type=all&per_page=1" if out["owner_kind"] == "organization" else f"users/{owner}/repos?per_page=1"
    code, stdout, stderr = runner(["gh", "api", "-i", endpoint])
    status, headers, body = parse_response(stdout)
    if code != 0 or (status is not None and status >= 400):
        out["cause"] = diagnose(stderr or body or stdout)
        return out
    out["partial"] = sso_partial(headers)
    if out["partial"]:
        out["cause"] = "sso"
    return out


def result(found):
    """(status, detail) for the doctor from a `probe()`: ok / warn / fail, and a short detail made of facts (the cause, the login, the scopes), not prose."""
    cause = found["cause"]
    who = found["login"] or "?"
    if found["stage"] == "unchecked":
        return "ok", "not checked"
    if cause in ("auth",):
        return "fail", cause
    if cause:
        return "warn", f"{cause} ({found['stage']})" + (" - private repositories of the organization are hidden" if found["partial"] else "")
    scopes = found["scopes"]
    if scopes is None:
        return "ok", f"{who}: fine-grained or app token (scopes cannot be read)"
    missing = [s for s in ("repo", "read:org") if s not in scopes and not (s == "read:org" and "admin:org" in scopes)]
    if missing and found["owner_kind"] == "organization":
        return "warn", f"{who}: missing scope {', '.join(missing)}"
    if "repo" in missing:
        return "warn", f"{who}: missing scope repo (only public repositories)"
    return "ok", f"{who}: {', '.join(scopes) or 'no scopes'}"


def _defaults():
    from github_actions_monitor.util import paths
    try:
        return json.loads((paths.EXAMPLES / "actions_monitor.example.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _number(config, defaults, *keys, floor=1):
    for source in (config, defaults):
        value = source
        for key in keys:
            value = value.get(key) if isinstance(value, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= floor:
            return value
    return floor


def estimate(config, repos, workflows=None, limit=5000):
    """A rough estimate, with no call, of the reads per hour of the monitor for `repos` repositories (and `workflows` workflow files in all; 4 per repository when unknown) under `config`.
    {"repos", "workflows", "calls_per_hour", "limit", "percent", "level": ok | tight | over, "terms": [(label, calls)]}. It counts the polling of the runs (hot repositories every `refresh_seconds`, the rest
    every `cold_refresh_seconds`, a tenth of them hot), the Sentinel (its hourly budget at most), the reading of workflow files without a clone when `lint.source` is `auto`, and the terms other parts add."""
    config = config if isinstance(config, dict) else {}
    defaults = _defaults()
    repos = max(0, int(repos or 0))
    workflows = int(workflows) if workflows else repos * 4
    hot = math.ceil(repos * 0.1) if repos else 0
    refresh = _number(config, defaults, "refresh_seconds", floor=10)
    cold = _number(config, defaults, "cold_refresh_seconds", floor=30)
    terms = [("runs", round(hot * 3600 / refresh + (repos - hot) * 3600 / cold))]
    if (config.get("sentinel") or {}).get("enabled", True) is not False:
        terms.append(("sentinel", int(min(_number(config, defaults, "sentinel", "budget_per_hour", floor=1), 600 + repos))))
    lint = config.get("lint") if isinstance(config.get("lint"), dict) else {}
    if lint.get("source") == "auto":
        api = lint.get("api") if isinstance(lint.get("api"), dict) else {}
        every = api.get("refresh_seconds") if isinstance(api.get("refresh_seconds"), int) and api.get("refresh_seconds") >= 600 else 21600
        wanted = (repos + workflows) * 3600 / every      # the list of every repository and, at worst, every file once per refresh
        cap = (api.get("max_calls_per_tick") if isinstance(api.get("max_calls_per_tick"), int) else 20) * 3600 / max(30, _number(config, defaults, "sentinel", "refresh_seconds", floor=30))
        terms.append(("workflow files", round(min(wanted, cap))))
    for extra in ESTIMATE_TERMS:
        try:
            label, calls = extra(config, repos, workflows)
            terms.append((str(label), int(calls)))
        except Exception:   # noqa: BLE001 - an extra term never stops the estimate
            continue
    total = sum(calls for _, calls in terms)
    percent = round(100 * total / limit) if limit else 0
    return {"repos": repos, "workflows": workflows, "calls_per_hour": total, "limit": limit, "percent": percent, "level": "over" if percent > 100 else ("tight" if percent > 60 else "ok"), "terms": terms}


def estimate_result(found, config):
    """(status, detail) of the estimate for the doctor, from the number of repositories the probe found; ok with a hint when the number is unknown."""
    repos = found.get("repos")
    if not isinstance(repos, int):
        return "ok", "repositories unknown"
    figures = estimate(config, repos)
    detail = f"{repos} repositories, about {figures['calls_per_hour']} reads an hour of {figures['limit']} ({figures['percent']}%)"
    return ("ok" if figures["level"] == "ok" else "warn"), detail
