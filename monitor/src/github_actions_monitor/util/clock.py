# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Moments kept on disk, read back by a clock that may have been set back. Standard library only.

A computer without a battery clock can start with an old date after the monitor saved a good one, and a clock can be corrected by hand. A saved "last run" that lies in the future would then block
every pass (score, purge, report) until the clock catches up, days later. A stored moment that is more than `MARGIN` seconds ahead of now is not believed: the pass is due now and writes a good moment
(a start moment such as "first seen" is taken as now).
"""
MARGIN = 300.0      # seconds of difference between two clocks that are still the same moment


def in_future(stamp, now, margin=MARGIN):
    return isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and stamp > now + margin


def settle(stamp, now, margin=MARGIN):
    """`stamp` as it counts from `now`: unchanged, or `now` when it lies in the future by more than `margin`."""
    return now if in_future(stamp, now, margin) else stamp
