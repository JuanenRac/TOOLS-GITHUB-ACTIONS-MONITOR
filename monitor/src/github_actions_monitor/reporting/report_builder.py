# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The content of a report, as plain data: the score of the account, the team's repositories that need a person, the open alerts and what changed since the last report. Pure functions: the data go in, a document comes out; nothing is read or written here. No secret can be in it, because none of the inputs holds one (it takes the snapshots and the lists the page already shows) and every text is cut to a fixed length."""
from datetime import datetime, timezone

from github_actions_monitor.security.redactor import redact

LEVELS = ("critical", "error", "warning", "info")
CUT = 160


def _cut(value, size=CUT):
    return redact(str(value or ""))[:size]      # the title of an alert can be the title of an issue that a stranger wrote: tokens, addresses and the like are cleaned before the file exists


def _iso(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def score_part(snapshot):
    """What of the score goes in the report: the state always, the number and the parts only when there is a number (never a number the engine would not show)."""
    snap = snapshot if isinstance(snapshot, dict) else {}
    state = snap.get("state") or "off"
    out = {"state": state, "score": None, "letter": None, "trend": None, "coverage": snap.get("coverage"), "missing_parts": list(snap.get("missing_parts") or []), "parts": []}
    if state == "scored" and isinstance(snap.get("score"), (int, float)):
        out["score"], out["letter"] = snap["score"], snap.get("letter")
        trend = snap.get("trend") if isinstance(snap.get("trend"), dict) else {}
        out["trend"] = {"direction": trend.get("direction"), "delta": trend.get("delta")}
        out["parts"] = [{"part": p.get("part"), "score": p.get("score"), "weight": p.get("weight")} for p in snap.get("parts") or [] if isinstance(p, dict)]
    return out


def alerts_part(alerts, top):
    """The open alerts counted by level and the worst `top` of them. A silenced alert is not open."""
    mine = [a for a in alerts if isinstance(a, dict) and not a.get("muted_until")]
    by_level = {}
    for a in mine:
        by_level[a.get("level", "")] = by_level.get(a.get("level", ""), 0) + 1
    ordered = sorted(mine, key=lambda a: (LEVELS.index(a["level"]) if a.get("level") in LEVELS else 9, str(a.get("repo")), str(a.get("id"))))
    items = [{"id": _cut(a.get("id"), 120), "level": a.get("level"), "sentinel": a.get("sentinel"), "repo": _cut(a.get("repo"), 100), "title": _cut(a.get("title"))} for a in ordered[:top]]
    return {"total": len(mine), "by_level": by_level, "items": items}


def team_part(team, top):
    """The totals and the first `top` repositories of the ranking of `health.repo_view.team_view`."""
    team = team if isinstance(team, dict) else {}
    ranking = [{"repo": _cut(r.get("repo"), 100), "state": r.get("state"), "risk": r.get("risk"), "alerts": r.get("alerts"), "red": r.get("red_workflows")} for r in (team.get("ranking") or [])[:top]
               if isinstance(r, dict)]
    return {"all": team.get("all", 0), "totals": dict(team.get("totals") or {}), "ranking": ranking}


def changes(score, alert_ids, previous):
    """What is different from the last report: the score against the number that report carried, the alerts that are new and the number of those that are gone. With no previous report there is nothing to compare and it says so."""
    if not isinstance(previous, dict):
        return {"first": True, "score_delta": None, "new_alerts": [], "gone_alerts": 0}
    before = previous.get("score")
    delta = round(score["score"] - before, 1) if isinstance(score.get("score"), (int, float)) and isinstance(before, (int, float)) else None
    old = set(previous.get("alert_ids") or [])
    new = sorted(set(alert_ids) - old)
    return {"first": False, "score_delta": delta, "new_alerts": new[:50], "gone_alerts": len(old - set(alert_ids))}


def compare_part(answer):
    """A short summary of the comparison with the period before (`compare.compare_service.build`): its state and one line per figure. None while the comparison was not asked for."""
    if not isinstance(answer, dict) or not answer.get("enabled"):
        return None
    rows = [{"metric": _cut(name, 30), "now": e.get("now"), "base": e.get("base"), "direction": e.get("direction"), "state": e.get("state")} for name, e in (answer.get("metrics") or {}).items() if isinstance(e, dict)]
    reasons = (answer.get("data_quality") or {}).get("reasons") or []
    return {"state": answer.get("state"), "reason": _cut(reasons[0], 40) if reasons else "", "days": (answer.get("windows") or {}).get("days"), "rows": rows}


def build(account, snapshot, alerts, team, now, previous=None, top=10, compare=None):
    """The whole document. `previous` is the small memory the service keeps of the last report ({"score", "alert_ids"})."""
    top = max(1, min(50, int(top)))
    score = score_part(snapshot)
    alert = alerts_part(alerts, top)
    ids = [_cut(a.get("id"), 120) for a in alerts if isinstance(a, dict) and not a.get("muted_until")]
    doc = {"schema": 1, "generated_at": _iso(now), "account": _cut(account, 60), "score": score, "team": team_part(team, top), "alerts": alert, "changes": changes(score, ids, previous)}
    part = compare_part(compare)
    if part is not None:      # only when the person asked for it (compare.include_in_report): a report without it is the same as before
        doc["compare"] = part
    return doc


def memory(doc, alerts):
    """The little that the next report needs to say what changed."""
    return {"score": doc["score"]["score"], "alert_ids": [_cut(a.get("id"), 120) for a in alerts if isinstance(a, dict) and not a.get("muted_until")][:2000]}
