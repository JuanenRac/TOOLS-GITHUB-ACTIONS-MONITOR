# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The score of the whole installation, for information only: what `GET /api/score/global` of the supervisor answers from the answers of /api/score of the accounts the asker may see.

There is no real "score of the installation": every account has its own. This is a mean of the scored accounts, weighted by the number of their repositories that have a number, and it always
carries who is in it (`accounts_scored` of `accounts_total`), the mean coverage and `informative: true`. An account without a number (calibrating, not enough data, off, unreachable) is listed with
its state and left out of the mean; an account whose snapshot is stale (no pass for hours) is left out too and counted in `accounts_stale`; with none in the mean there is no number, never a 100.
"""
from github_actions_monitor.scoring import engine

SCHEMA = 1


def _number(value):
    return engine._number(value)


def row(account, answer):
    """One line for one account from its /api/score answer (None when it could not be read)."""
    if not isinstance(answer, dict) or not isinstance(answer.get("state"), str):
        return {"account": account, "state": "unreachable", "score": None, "letter": None, "coverage": None, "repos": 0, "weight": 0, "missing": []}
    repos = [r for r in (answer.get("repos") or []) if isinstance(r, dict) and _number(r.get("score"))]
    scored = answer["state"] == "scored" and _number(answer.get("score"))
    return {"account": account, "state": answer["state"], "score": answer["score"] if scored else None, "letter": answer.get("letter") if scored else None,
            "coverage": answer.get("coverage") if _number(answer.get("coverage")) else None, "repos": len(repos), "weight": max(1, len(repos)) if scored and not answer.get("stale") else 0,
            "stale": bool(answer.get("stale")), "missing": [str(x) for x in (answer.get("missing_parts") or [])] if scored else []}


def combine(answers, cfg=None):
    """{"schema", "informative", "state", "score", "letter", "coverage", "accounts_scored", "accounts_total", "accounts": [rows]} from {account: answer or None}."""
    cfg = cfg or engine.settings({})
    rows = [row(account, answer) for account, answer in sorted(answers.items())]
    counted = [r for r in rows if r["weight"] > 0]
    total_weight = sum(r["weight"] for r in counted)
    out = {"schema": SCHEMA, "informative": True, "accounts_total": len(rows), "accounts_scored": len(counted), "accounts_stale": sum(1 for r in rows if r.get("stale") and r["state"] == "scored"),
           "accounts": rows, "score": None, "letter": None, "coverage": None}
    if counted and total_weight:
        out["score"] = round(sum(r["score"] * r["weight"] for r in counted) / total_weight, 1)
        out["letter"] = engine.letter(out["score"], cfg["grades"])
        coverages = [r["coverage"] for r in counted if r["coverage"] is not None]
        out["coverage"] = round(sum(coverages) / len(coverages), 3) if coverages else None
        out["state"] = "scored"
    elif any(r["state"] == "insufficient_data" for r in rows):
        out["state"] = "insufficient_data"
    elif rows and all(r["state"] == "off" for r in rows):
        out["state"] = "off"
    else:
        out["state"] = "calibrating"
    out["missing_parts"] = sorted({m for r in counted for m in r["missing"]})
    out["complete"] = bool(counted) and not out["missing_parts"]      # complete only when every account in the mean has all its parts
    return out
