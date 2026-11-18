# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""How long the alerts took to resolve. The source is the ledger of the score (`collab`: id -> [opened, closed or None], the alerts of the collaboration sentinel followed from the moment they
appear to the moment they are gone). The definition is exact and short: an alert counts as resolved in a window when its closing falls inside it and on a day the filter keeps; its time is
closing minus opening. An alert that stays open, or that crosses the edge of the window, is counted apart and never given a time it does not have."""
from github_actions_monitor.compare import windows
from github_actions_monitor.data_pipeline.analytics import percentile


def summarize(collab, window, days, workdays, zone=None):
    start, end = window
    spans, opened, still_open = [], 0, 0
    for row in (collab or {}).values():
        if not (isinstance(row, list) and len(row) == 2 and isinstance(row[0], (int, float))):
            continue
        began, closed = row
        if start <= began < end and windows.day_matches(began, days, workdays, zone):
            opened += 1
        if closed is None or (isinstance(closed, (int, float)) and closed >= end):
            if began < end:
                still_open += 1
        elif isinstance(closed, (int, float)) and start <= closed < end and windows.day_matches(closed, days, workdays, zone):
            spans.append(max(0.0, closed - began))
    return {"median_seconds": percentile(spans, 50) if spans else None, "resolved": len(spans), "opened": opened, "open_at_end": still_open}
