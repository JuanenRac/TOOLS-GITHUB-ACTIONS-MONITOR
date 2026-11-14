# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A limit of time for a test that measures real time: the limit is what a normal computer needs times how much slower THIS computer is right now.

A test that says 'this read must not take 2 seconds' fails on a runner that is busy with ten other jobs although nothing waited for a lock. `limit(seconds)` measures how long a fixed piece of work takes
now (the best of five tries, so a short stall does not count but a loaded machine does) and stretches the limit by that factor, between 1 and 20. It never makes a limit shorter."""
import time

NORMAL = 0.02      # seconds the probe takes on a computer that is not busy
CAP = 20.0


def slowdown():
    best = 1e9
    for _ in range(5):
        start = time.perf_counter()
        sum(i * i for i in range(200_000))
        best = min(best, time.perf_counter() - start)
    return max(1.0, min(CAP, best / NORMAL))


def limit(seconds):
    return seconds * slowdown()
