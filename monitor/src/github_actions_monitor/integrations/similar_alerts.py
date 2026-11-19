# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Alerts that look alike, without a model and without embeddings: the same code of alert, the same repository, the same name of workflow and the same words of the title or cause, compared by a plain
overlap of words. It answers "this already happened in another repository (or before in this one), and this is what was seen then". Pure functions: the open alerts and the resolved ones come in, a ranked
list comes out; ties break by repository and id, so the same data always gives the same order. Only what the caller hands over is compared, so nothing crosses the scope of the person who asks."""
import re
import unicodedata

WORD = re.compile(r"[a-z][a-z0-9]{2,}")
NOISE = frozenset("the and for with from that this was were has have not are but failed failure error run runs workflow job step build check checks please when after before into over under".split())
THRESHOLD = 0.34


def words(*texts):
    """The words that carry meaning in the texts: lower case, plain letters, no numbers on their own, no hashes and no filler."""
    found = set()
    for text in texts:
        flat = unicodedata.normalize("NFKC", str(text or "")).lower()
        found |= {w for w in WORD.findall(flat) if w not in NOISE and not re.fullmatch(r"[0-9a-f]{7,}", w)}
    return found


def score(target, other):
    """0..1: the overlap of the words, plus a little for the same code, workflow and repository. 0 for the very same alert."""
    if target.get("id") and target.get("id") == other.get("id"):
        return 0.0
    a, b = words(target.get("title"), target.get("cause"), target.get("workflow")), words(other.get("title"), other.get("cause"), other.get("workflow"))
    overlap = len(a & b) / len(a | b) if a and b else 0.0
    bonus = 0.0
    if target.get("code") and target.get("code") == other.get("code"):
        bonus += 0.25
    if target.get("workflow") and target.get("workflow") == other.get("workflow"):
        bonus += 0.15
    if target.get("repo") and target.get("repo") == other.get("repo"):
        bonus += 0.05
    return round(min(1.0, overlap + bonus), 3) if (overlap or bonus >= 0.25) else 0.0


def find(target, pool, limit=5):
    """The `limit` most alike alerts of `pool` (dicts with id, repo, code, workflow, title, cause, since, state): [{..., "score"}] best first. Empty list when nothing reaches the threshold."""
    ranked = []
    for item in pool or []:
        if not isinstance(item, dict):
            continue
        value = score(target, item)
        if value >= THRESHOLD:
            ranked.append((-value, str(item.get("repo") or ""), str(item.get("id") or ""), item))
    ranked.sort(key=lambda r: r[:3])
    return [{**row[3], "score": -row[0]} for row in ranked[:max(1, min(20, int(limit)))]]


def from_feed(rows):
    """The resolved alerts of the feed of the AIs (ai_alerts.alerts) in the shape `find` compares."""
    return [{"id": r.get("id"), "repo": r.get("repo"), "code": r.get("class"), "workflow": r.get("workflow"), "title": r.get("workflow"), "cause": r.get("cause"), "since": r.get("since"),
             "state": r.get("state")} for r in rows or [] if isinstance(r, dict)]
