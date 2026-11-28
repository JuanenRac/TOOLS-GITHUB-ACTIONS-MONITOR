# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Posture of the repositories and of the organization: which are read and when (a few per cycle, each at most every posture.refresh_hours), what is kept (data/state/posture.json: findings, what the
releases looked like, one line per day of history) and what comes out: the report, the alerts and the level of maturity. Read only: nothing is ever changed on GitHub."""
import fnmatch
import json
import re
import threading
import time

from github_actions_monitor import families, i18n
from github_actions_monitor.families.posture import posture_catalogue as catalogue
from github_actions_monitor.families.posture import posture_checks
from github_actions_monitor.families.posture.posture_checks import ORG_GROUPS, REPO_GROUPS, Unread
from github_actions_monitor.storage import state_io
from github_actions_monitor.util import paths

LOCK = threading.RLock()
RUNNING = {"on": False}
HISTORY_DAYS = 180
MATURITY = (("scan.no_dependency_alerts", "scan"), ("scan.no_credentials", "scan"), ("scan.no_push_protection", "scan"), ("scan.no_code", "scan"), ("repo.no_update_tool", "files"), ("repo.no_policy", "files"))
REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")


def settings(config):
    return families.block(config if isinstance(config, dict) else {}, "posture")


def active(config):
    config = config if isinstance(config, dict) else {}
    return settings(config)["enabled"] is True and config.get("airgapped") is not True


def state_file(account=""):
    suffix = "_" + re.sub(r"[^A-Za-z0-9_-]", "", account) if account else ""
    return paths.place("state") / f"posture{suffix}.json"


def load(account=""):
    try:
        data = state_io.load_json(state_file(account))
        if isinstance(data, dict) and isinstance(data.get("repos"), dict):
            data.setdefault("org", {})
            data.setdefault("history", [])
            return data
    except (OSError, ValueError):
        pass
    return {"repos": {}, "org": {}, "history": []}


def save(data, account=""):
    target = state_file(account)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        state_io.save_text(target, json.dumps(data, ensure_ascii=False))
        return True
    except OSError:
        return False


def kind_of(repo, cfg):
    for entry in cfg.get("types") or []:
        pattern, _eq, kind = str(entry).partition("=")
        if kind in catalogue.TYPES and fnmatch.fnmatchcase(repo.lower(), pattern.lower()):
            return kind
    return "standard"


def reader():
    """The GET of the monitor (conditional reads, retries). Every refusal becomes Unread."""
    from github_actions_monitor.app import actions_monitor

    def get(endpoint):
        try:
            return actions_monitor.gh_read(endpoint, retries=1)
        except Exception as error:      # noqa: BLE001 - whatever gh says, the group is "not checked"
            text = str(error).lower()
            if "rate limit" in text:
                raise Unread("rate_limited") from None
            if "404" in text:
                raise Unread("missing") from None
            if "403" in text or "401" in text or "must have admin" in text:
                raise Unread("forbidden") from None
            raise Unread("failed") from None
    return get


def read_groups(get, base, groups, ctx, wanted_groups):
    """(findings, {group: reason} of what could not be checked). A rate limit stops everything (Unread goes up)."""
    findings, unread = [], {}
    for name, function in groups.items():
        if name not in wanted_groups:
            continue
        try:
            findings.extend(function(get, base, ctx))
        except Unread as error:
            if error.reason == "rate_limited":
                raise
            unread[name] = error.reason
            findings.extend(error.partial)
        except (AttributeError, KeyError, TypeError, ValueError):
            unread[name] = "failed"
    return findings, unread


def _filtered(findings, cfg, kind):
    return [f for f in findings if catalogue.wanted(f["check"], cfg["profile"], kind, cfg.get("skip") or ())]


def _groups(cfg, kind, available):
    off = _switched_off(cfg)
    return {name for name in available if name not in off and any(v[2] == name and catalogue.wanted(c, cfg["profile"], kind, cfg.get("skip") or ()) for c, v in catalogue.CHECKS.items())}


def _switched_off(cfg):
    """Groups whose own setting says "do not look": they are not read, so they are never reported as looked at."""
    switches = {"releases": cfg.get("releases"), "reviews": cfg.get("review_sample"), "runner": cfg.get("runner_runs"), "audit": cfg.get("audit_log")}
    return {name for name, on in switches.items() if not on}


def _evaluated(cfg, kind, checked):
    """The checks that were really looked at: their group was read and neither the profile, the kind of project nor posture.skip leaves them out."""
    return sorted(c for c, v in catalogue.CHECKS.items() if v[2] in checked and catalogue.wanted(c, cfg["profile"], kind, cfg.get("skip") or ()))


def check_repo(get, owner, repo, cfg, entry, now):
    kind = kind_of(repo, cfg)
    base = f"repos/{owner}/{repo}"
    info = get(base)
    info = info if isinstance(info, dict) else {}
    if info.get("fork") is True and info.get("archived") is not True and cfg.get("upstream") is True:      # a fork is not judged itself; with posture.upstream its original is looked at
        ctx = {"cfg": cfg, "now": now, "repo_info": info, "memory": entry.setdefault("memory", {})}
        findings, unread = read_groups(get, base, {"upstream": posture_checks.upstream}, ctx, {"upstream"})
        checked = sorted({"upstream"} - set(unread))
        entry.update(at=now, kind=kind, findings=_filtered(findings, cfg, kind), unread=unread, checked=checked, evaluated=_evaluated(cfg, kind, checked), skipped="fork")
        return entry
    if info.get("archived") is True or info.get("fork") is True:
        entry.update(at=now, kind=kind, findings=[], unread={}, checked=[], evaluated=[], skipped="archived" if info.get("archived") else "fork")
        return entry
    ctx = {"cfg": cfg, "now": now, "repo_info": info, "memory": entry.setdefault("memory", {})}
    groups = _groups(cfg, kind, REPO_GROUPS)
    findings, unread = read_groups(get, base, REPO_GROUPS, ctx, groups)
    for name in unread:      # what could not be read now is not taken as solved
        have = {(f["check"], f["item"]) for f in findings}
        findings.extend(f for f in entry.get("findings", []) if catalogue.CHECKS.get(f["check"], ("", "", ""))[2] == name and (f["check"], f["item"]) not in have)
    checked = sorted(groups - set(unread))
    entry.update(at=now, kind=kind, findings=_filtered(findings, cfg, kind), unread=unread, checked=checked, evaluated=_evaluated(cfg, kind, checked), skipped="")
    return entry


def check_org(get, owner, cfg, entry, now):
    ctx = {"cfg": cfg, "now": now, "repo_info": {}, "memory": entry.setdefault("memory", {})}
    try:
        get(f"orgs/{owner}")
    except Unread as error:
        if error.reason == "missing":      # a personal account: there is no organization to look at
            entry.update(at=now, kind="user", findings=[], unread={}, checked=[], evaluated=[])
            return entry
        raise
    groups = set(ORG_GROUPS) - _switched_off(cfg)
    findings, unread = read_groups(get, f"orgs/{owner}", ORG_GROUPS, ctx, groups)
    checked = sorted(groups - set(unread))
    entry.update(at=now, kind="organization", findings=_filtered(findings, cfg, "standard"), unread=unread, checked=checked, evaluated=_evaluated(cfg, "standard", checked))
    return entry


def names_of(data):
    out = []
    for item in (data or {}).get("repos") or []:
        name = item.get("name") if isinstance(item, dict) else item
        name = str(name or "").split("/")[-1]
        if REPO_RE.match(name) and name not in (".", "..") and name not in out:
            out.append(name)
    return out


def refresh(config, owner, repos, get=None, now=None, account=""):
    """Reads the organization (when its turn has come) and at most posture.repos_per_cycle repositories whose turn has come, the longest waiting first. Returns how many were read."""
    if not active(config) or not owner or not REPO_RE.match(str(owner)):
        return 0
    cfg = settings(config)
    now = time.time() if now is None else now
    get = get or reader()
    every = cfg["refresh_hours"] * 3600
    done = 0
    with LOCK:
        data = load(account)
        for gone in set(data["repos"]) - set(repos):
            if repos:
                del data["repos"][gone]
        due = sorted((r for r in repos if now - data["repos"].get(r, {}).get("at", 0) >= every), key=lambda r: data["repos"].get(r, {}).get("at", 0))
        try:
            if not cfg["org_checks"]:
                data["org"] = {}
            elif now - data["org"].get("at", 0) >= every:
                try:
                    check_org(get, owner, cfg, data["org"], now)
                except Unread as error:      # a refused organization (single sign-on, no rights) never stops the repositories
                    if error.reason == "rate_limited":
                        raise
                    data["org"].update(at=now, unread={"organization": error.reason}, checked=[], evaluated=[])
            for repo in due[:cfg["repos_per_cycle"]]:
                entry = data["repos"].get(repo, {})
                try:
                    data["repos"][repo] = check_repo(get, owner, repo, cfg, entry, now)
                except Unread as error:
                    if error.reason == "rate_limited":
                        raise
                    entry.update(at=now, unread={"repository": error.reason})
                    data["repos"][repo] = entry
                done += 1
        except Unread:
            pass      # the allowance is gone: what was not read waits for the next cycle
        granted = app_permissions(config)
        if granted is not None:
            data["app_permissions"] = granted
        if repos:
            data["pending"] = sum(1 for repo in repos if not data["repos"].get(repo, {}).get("at"))
        _history(data, now)
        save(data, account)
    return done


def app_permissions(config):
    """The permissions the installed GitHub App has (names and levels only), or None when no App is configured or it cannot be asked."""
    block = config.get("github_app") if isinstance(config.get("github_app"), dict) else {}
    if block.get("enabled") is not True:
        return None
    try:
        from github_actions_monitor.integrations import github_app
        found = github_app.status(config)
    except Exception:      # noqa: BLE001 - the matrix then says "unknown"
        return None
    granted = found.get("permissions") if isinstance(found, dict) and found.get("ok") else None
    return {str(k): str(v) for k, v in granted.items()} if isinstance(granted, dict) else None


def _history(data, now):
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    counts = {"day": day, "error": 0, "warning": 0, "info": 0, "repos": len(data["repos"])}
    for entry in list(data["repos"].values()) + [data["org"]]:
        for item in entry.get("findings", []):
            counts[catalogue.CHECKS.get(item["check"], ("info",))[0]] += 1
    data["history"] = [h for h in data["history"] if h.get("day") != day][-(HISTORY_DAYS - 1):] + [counts]


def _looked_at(entry):
    if "evaluated" in entry:
        return set(entry["evaluated"])
    return {c for c, v in catalogue.CHECKS.items() if v[2] in (entry.get("checked") or [])}      # a state kept by an earlier build


def maturity(entry):
    """How much of the security pipeline of a repository is in place: passed / checked of six things, None when none of them could be looked at."""
    looked = _looked_at(entry)
    found = {f["check"] for f in entry.get("findings", [])}
    rows = [check for check, _group in MATURITY if check in looked]
    if not rows:
        return None
    return {"passed": sum(1 for check in rows if check not in found), "checked": len(rows), "missing": [check for check in rows if check in found]}


def compliance(data):
    """What was found against each risk of the OWASP Top 10 CI/CD and each section of the CIS Software Supply Chain guide that the checks map to. status: "findings", "no_findings" (everything it maps
    to was looked at and nothing was found), "partly" (nothing found but some of it was not looked at: refused, switched off, left out by the profile, or repositories still waiting) or
    "not_checked". It is a reading aid: not a certification, and not a statement that a standard is met."""
    entries = list(data["repos"].values()) + [data["org"]]
    looked = set().union(*(_looked_at(entry) for entry in entries))
    refused = {group for entry in entries for group in (entry.get("unread") or {})}
    waiting = bool(data.get("pending")) or bool(refused & {"repository", "organization"})
    # what does not apply is not "missing": an account that is a person has no organization, and the original of a fork is only looked at when asked
    absent = {c for c, v in catalogue.CHECKS.items() if c not in looked and (v[2] == "upstream" or data["org"].get("kind") == "user" and c.startswith("org."))}
    found = [f["check"] for entry in entries for f in entry.get("findings", []) if f["check"] in catalogue.CHECKS]

    def row(ident, name, checks):
        groups = {catalogue.CHECKS[c][2] for c in checks}
        count = sum(1 for c in found if c in checks)
        missing = checks - looked - absent
        not_read = {catalogue.CHECKS[c][2] for c in missing} | groups & refused
        status = "findings" if count else "not_checked" if not checks & looked else "partly" if not_read or waiting else "no_findings"
        return {"id": ident, "name": name, "findings": count, "checks": sorted(checks), "not_read": sorted(not_read), "status": status}
    owasp = [row(f"CICD-SEC-{n}", name, {c for c, v in catalogue.CHECKS.items() if v[3] == n}) for n, name in sorted(catalogue.OWASP.items())]
    sections = sorted({v[4] for v in catalogue.CHECKS.values()})
    cis = [row(section, "", {c for c, v in catalogue.CHECKS.items() if v[4] == section}) for section in sections]
    return {"owasp": owasp, "cis": cis}


def trend(history):
    """Errors and warnings of the newest day against the newest day at least a week older: "better", "worse", "same" or "unknown" (not a week of history yet)."""
    if not history:
        return {"direction": "unknown", "since": "", "delta": 0}
    newest = history[-1]
    week = time.strftime("%Y-%m-%d", time.gmtime(checks_epoch(newest["day"]) - 7 * 86400))
    older = [h for h in history if h["day"] <= week]
    if not older:
        return {"direction": "unknown", "since": "", "delta": 0}
    delta = newest["error"] + newest["warning"] - older[-1]["error"] - older[-1]["warning"]
    return {"direction": "better" if delta < 0 else "worse" if delta > 0 else "same", "since": older[-1]["day"], "delta": delta}


def checks_epoch(day):
    return posture_checks.epoch(day + "T12:00:00")


def markdown(out):
    """The compliance report as a Markdown document (`posture report`)."""
    lines = ["# " + i18n.t("ui.posture.report_title"), "", i18n.t("ui.posture.report_note"), ""]
    for title, rows in (("OWASP Top 10 CI/CD", out["compliance"]["owasp"]), ("CIS Software Supply Chain", out["compliance"]["cis"])):
        lines += [f"## {title}", "", f"| id | {i18n.t('ui.posture.col_finding')} | {i18n.t('ui.posture.col_level')} |", "|---|---|---|"]
        lines += [f"| {r['id']} {r['name']} | {r['findings']} | {i18n.t('ui.posture.status_' + r['status'])} |" for r in rows]
        lines.append("")
    lines += [f"## {i18n.t('ui.posture.learn_title')}", ""]
    for r in out["compliance"]["owasp"]:
        if r["findings"]:
            lines += [f"- **{r['id']}**: " + i18n.t("ui.posture.learn_" + r["id"].rsplit("-", 1)[1])]
    return lines


def describe(item):
    level, profile, group, owasp, cis = catalogue.CHECKS[item["check"]]
    return dict(item, level=level, title=i18n.t("ui.posture.c." + item["check"].replace(".", "_")), owasp=f"CICD-SEC-{owasp}", cis=cis)


def report(config, account=""):
    """Everything that was found, what could not be checked, the standards and the permissions."""
    cfg = settings(config)
    data = load(account)
    repos, refused, by_owasp = [], set(), {}
    for name, entry in sorted(data["repos"].items()):
        refused.update(k for k, v in (entry.get("unread") or {}).items() if v == "forbidden")
        repos.append({"repo": name, "kind": entry.get("kind", "standard"), "at": entry.get("at", 0), "skipped": entry.get("skipped", ""), "unread": entry.get("unread") or {},
                      "findings": [describe(f) for f in entry.get("findings", []) if f["check"] in catalogue.CHECKS], "maturity": maturity(entry)})
    org = data["org"]
    refused.update(k for k, v in (org.get("unread") or {}).items() if v == "forbidden")
    organization = {"kind": org.get("kind", ""), "unread": org.get("unread") or {}, "findings": [describe(f) for f in org.get("findings", []) if f["check"] in catalogue.CHECKS]}
    for item in [f for r in repos for f in r["findings"]] + organization["findings"]:
        row = by_owasp.setdefault(item["owasp"], {"id": item["owasp"], "name": catalogue.OWASP[int(item["owasp"].rsplit("-", 1)[1])], "findings": 0})
        row["findings"] += 1
    return {"ok": True, "enabled": cfg["enabled"] is True, "profile": cfg["profile"], "repos": repos, "org": organization, "history": data["history"][-90:],
            "owasp": sorted(by_owasp.values(), key=lambda r: int(r["id"].rsplit("-", 1)[1])), "permissions": catalogue.matrix(refused, data.get("app_permissions")),
            "compliance": compliance(data), "trend": trend(data["history"]), "learn": {f"CICD-SEC-{n}": i18n.t(f"ui.posture.learn_{n}") for n in catalogue.OWASP},
            "not_checked": sum(len(r["unread"]) for r in repos) + len(organization["unread"])}


def text_lines(out):
    lines = []
    for row in [{"repo": "(organization)", **out["org"]}] + out["repos"]:
        for item in row["findings"]:
            lines.append(f"{item['level']:<8} {row['repo']:<30} {item['check']:<28} {item['item']} [{item['owasp']}, CIS {item['cis']}]".rstrip())
        lines.extend(f"unchecked {row['repo']:<30} {group} ({why})" for group, why in row["unread"].items())
    return lines


def alerts(config, account=""):
    """One alert per check and repository (the items are inside), in the shape of the alerts of the sentinels."""
    if not active(config) or not settings(config)["alerts"]:
        return []
    data = load(account)
    out = []
    for repo, entry in [(None, data["org"])] + sorted(data["repos"].items()):
        grouped = {}
        for item in entry.get("findings", []):
            if item["check"] in catalogue.CHECKS:
                grouped.setdefault(item["check"], []).append(item["item"])
        for check, items in grouped.items():
            code = "posture." + check
            title = i18n.t("ui.posture.c." + check.replace(".", "_"))
            out.append({"id": f"{code}:{repo or 'org'}", "code": code, "level": catalogue.CHECKS[check][0], "sentinel": "security", "account_id": account, "repo": repo, "title": title,
                        "details": {"items": [i for i in items if i][:20], "count": len(items)}, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(entry.get("at", 0)))})
    return out


def tick(config, data=None, account=""):
    if not active(config) or RUNNING["on"]:
        return None
    from github_actions_monitor.app import toolconfig
    owner, repos = toolconfig.github_owner(config), names_of(data)
    RUNNING["on"] = True

    def work():
        try:
            refresh(config, owner, repos, account=account)
        finally:
            RUNNING["on"] = False
    thread = threading.Thread(target=work, name="posture", daemon=True)
    thread.start()
    return thread
