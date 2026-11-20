# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The fleet view (`GET /api/team/fleet`): the same repository health as the team ranking, for accounts with hundreds of repositories. Pure functions, nothing is read here.

  * Grouping: by ecosystem (default), by label (a pattern of repository names -> a label, `fleet.labels`: this is how organisations or teams are told apart), by state, or not at all. Groups are ordered by their total risk.
  * Order inside a group: by risk (default), by name, by last run or by state. Filters are the ones of the team view (ecosystem, least severity, text) plus a label and the saved filters of `fleet.saved_filters`.
  * Pagination is done by the page, on the client, over the rows this view sends (at most `LIMIT`): the server never builds HTML and only one page of rows is drawn at a time.
"""
import fnmatch
import re

from github_actions_monitor.health import repo_view

GROUPS = ("ecosystem", "label", "state", "none")
SORTS = ("risk", "name", "last_run", "state")
DEFAULTS = {"page_size": 50, "group_by": "ecosystem", "sort": "risk", "show_all_active": True}
LIMIT = 5000
LABEL_RE = re.compile(r"^([A-Za-z0-9._*?-]{1,100})=([A-Za-z0-9._-]{1,40})\Z")      # pattern=label
FILTER_RE = re.compile(r"^([A-Za-z0-9._-]{1,30})=(|warn|bad|unknown|ok)\|([A-Za-z0-9._-]{0,40})\|([A-Za-z0-9._-]{0,40})\|([A-Za-z0-9._ -]{0,40})\Z")      # name=severity|ecosystem|label|text


def settings(config):
    cfg = config.get("fleet") if isinstance(config, dict) and isinstance(config.get("fleet"), dict) else {}
    size = cfg.get("page_size")
    labels = [x for x in cfg.get("labels") or [] if isinstance(x, str) and LABEL_RE.match(x)]
    saved = [x for x in cfg.get("saved_filters") or [] if isinstance(x, str) and FILTER_RE.match(x)]
    return {"page_size": size if isinstance(size, int) and not isinstance(size, bool) and 10 <= size <= 500 else DEFAULTS["page_size"],
            "group_by": cfg.get("group_by") if cfg.get("group_by") in GROUPS else DEFAULTS["group_by"],
            "sort": cfg.get("sort") if cfg.get("sort") in SORTS else DEFAULTS["sort"], "show_all_active": cfg.get("show_all_active") is not False, "labels": labels[:200], "saved_filters": saved[:50]}


def label_of(repo, labels):
    """The first label whose pattern fits the repository name ('' when none does)."""
    for item in labels or []:
        match = LABEL_RE.match(item)
        if match and fnmatch.fnmatchcase(repo.lower(), match.group(1).lower()):
            return match.group(2)
    return ""


def saved_filters(cfg):
    """[{"name", "severity", "ecosystem", "label", "q"}] from the settings."""
    out = []
    for item in cfg["saved_filters"]:
        match = FILTER_RE.match(item)
        out.append({"name": match.group(1), "severity": match.group(2), "ecosystem": match.group(3), "label": match.group(4), "q": match.group(5).strip()})
    return out


def group_of(view, by, labels):
    if by == "ecosystem":
        return view.get("ecosystem") or ""
    if by == "label":
        return label_of(view["repo"], labels)
    if by == "state":
        return view["state"]
    return ""


def _order(view, sort):
    if sort == "name":
        return (view["repo"].lower(),)
    if sort == "last_run":
        return (-(repo_view._ts(view["activity"]["last_run_at"]) or 0.0), view["repo"].lower())
    if sort == "state":
        return (-repo_view.STATES.index(view["state"]), -view["risk"], view["repo"].lower())
    return (-view["risk"], -repo_view.STATES.index(view["state"]), view["repo"].lower())


def fleet_view(views, config, ecosystem="", severity="", text="", label="", group="", sort="", saved="", limit=LIMIT):
    """Groups with their totals and the rows (one per repository, group by group). A saved filter fills the filters that were not given; a name that is not saved is ignored."""
    cfg = settings(config)
    chosen_saved = next((f for f in saved_filters(cfg) if f["name"] == saved), None) if saved else None
    if chosen_saved:
        ecosystem, severity, label, text = ecosystem or chosen_saved["ecosystem"], severity or chosen_saved["severity"], label or chosen_saved["label"], text or chosen_saved["q"]
    by = group if group in GROUPS else cfg["group_by"]
    order = sort if sort in SORTS else cfg["sort"]
    chosen = [v for v in views if repo_view.matches(v, ecosystem, severity, text)]
    if label:      # the label of the fleet (a pattern of names), not the label of the ecosystem
        chosen = [v for v in chosen if label_of(v["repo"], cfg["labels"]) == label]
    buckets = {}
    for v in chosen:
        buckets.setdefault(group_of(v, by, cfg["labels"]), []).append(v)
    groups = []
    for key, members in buckets.items():
        row = {"key": key, "repos": len(members), "risk": sum(m["risk"] for m in members)}
        for state in repo_view.STATES:
            row[state] = sum(1 for m in members if m["state"] == state)
        groups.append(row)
    groups.sort(key=lambda g: (-g["risk"], -g["bad"], g["key"] == "", g["key"]))
    rows = []
    for g in groups:
        for v in sorted(buckets[g["key"]], key=lambda x: _order(x, order)):
            rows.append({"repo": v["repo"], "group": g["key"], "label": label_of(v["repo"], cfg["labels"]), "ecosystem": v["ecosystem"], "state": v["state"], "risk": v["risk"],
                         "red_workflows": len(v["ci"]["red_workflows"]), "alerts": v["alerts"]["total"], "failures_24h": v["ci"]["failures_24h"], "last_run_at": v["activity"]["last_run_at"],
                         "not_fully_seen": v["not_fully_seen"], "running": (v["ci"].get("active") or {}).get("running", 0), "queued": (v["ci"].get("active") or {}).get("queued", 0)})
    totals = {s: sum(g[s] for g in groups) for s in repo_view.STATES}
    return {"schema": 1, "all": len(views), "shown": len(chosen), "truncated": len(rows) > limit, "page_size": cfg["page_size"], "group_by": by, "sort": order, "totals": totals,
            "groups": groups, "rows": rows[:limit], "saved_filters": [f["name"] for f in saved_filters(cfg)],
            "filters": {"ecosystem": ecosystem, "severity": severity, "q": text, "label": label, "saved": saved if chosen_saved else ""}}
