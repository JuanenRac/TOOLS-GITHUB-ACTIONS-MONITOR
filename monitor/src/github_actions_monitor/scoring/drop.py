# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The alert of a score that has dropped (`score.dropped`). Pure functions on a snapshot of the score.

A drop is seen when the account is scored and, against the window before it, either the score fell by at least `score.alert.drop_points` points or the letter went down to a lower one.
It is a WARNING, and CRITICAL when the letter is now E. The alert stays while the snapshot shows the drop and goes when the score recovers (like the alerts of the sentinels); a person can
silence it like any other. It shows in the panel (Alerts tab) by default; it goes out through the external notification channels only when `score.alert.notify_external` is on (off by default)
and only the moment it appears, not at every snapshot.
"""
import time

from github_actions_monitor import i18n
from github_actions_monitor.scoring import engine

CODE = "score.dropped"
RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}


def detect(snapshot, cfg):
    """None, or {"reasons": ["points", "letter"], "from_score", "to_score", "from_letter", "to_letter", "delta", "level"} when the snapshot shows a drop and the alert is on."""
    if not cfg["alert"]["enabled"] or not isinstance(snapshot, dict) or snapshot.get("state") != "scored":
        return None
    score, trend = snapshot.get("score"), snapshot.get("trend") or {}
    delta = trend.get("delta")
    if not engine._number(score) or not engine._number(delta) or snapshot.get("letter") not in RANK:
        return None
    before = round(score - delta, 1)
    before_letter = engine.letter(before, cfg["grades"])
    reasons = []
    if delta <= -cfg["alert"]["drop_points"]:
        reasons.append("points")
    if RANK[snapshot["letter"]] > RANK[before_letter]:
        reasons.append("letter")
    if not reasons:
        return None
    return {"reasons": reasons, "from_score": before, "to_score": score, "from_letter": before_letter, "to_letter": snapshot["letter"], "delta": delta,
            "level": "critical" if snapshot["letter"] == "E" else "warning"}


def title(drop):
    return i18n.t("score.alert_title", frm=drop["from_score"], to=drop["to_score"], from_letter=drop["from_letter"], to_letter=drop["to_letter"])


def alert(snapshot, drop, account=""):
    """The alert in the shape of the alerts of the sentinels (`sentinel: "system"`), ready for the Alerts tab."""
    at = snapshot.get("at")
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(at if isinstance(at, (int, float)) else 0))
    return {"id": f"{CODE}:{account or 'main'}", "code": CODE, "level": drop["level"], "sentinel": "system", "account_id": account or "", "repo": None, "title": title(drop),
            "details": {"from_score": drop["from_score"], "to_score": drop["to_score"], "from_letter": drop["from_letter"], "to_letter": drop["to_letter"], "delta": drop["delta"],
                        "reasons": drop["reasons"], "updated": created}, "created_at": created}


def event(drop):
    """The event of the feed (the notification channels hang on it)."""
    return {"kind": "score_dropped", "code": CODE, "level": "bad" if drop["level"] == "critical" else "warn", "repo": "", "owner": "main", "text": i18n.t("evt.score_dropped", frm=drop["from_score"], to=drop["to_score"],
            from_letter=drop["from_letter"], to_letter=drop["to_letter"]), "url": None,
            "args": {"from_score": drop["from_score"], "to_score": drop["to_score"], "from_letter": drop["from_letter"], "to_letter": drop["to_letter"], "reasons": drop["reasons"]}}
