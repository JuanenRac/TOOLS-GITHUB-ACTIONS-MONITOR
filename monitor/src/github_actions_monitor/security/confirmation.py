# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Confirmation BY ACTION for everything that does something outside the monitor (an action on GitHub, a local run of `act`).

The page first asks for a PLAN: the monitor checks the request, builds the exact description of what would happen (method, endpoint, command line) and keeps it under a random one-use
identifier for two minutes. Only a second request that names that identifier executes it, exactly as planned and exactly once; an identifier that expired, was used or never existed does
nothing. The plan is made by the monitor, so what the person confirms is what runs - the page cannot swap the command between the two steps. Nothing here is ever called by the AI assistant.
"""
import secrets
import threading
import time

TTL = 120
MAX_PENDING = 20


class Pending:
    def __init__(self, clock=time.time):
        self.clock, self.items, self.lock = clock, {}, threading.Lock()

    def add(self, kind, plan):
        with self.lock:
            now = self.clock()
            self.items = {k: v for k, v in self.items.items() if v[0] > now}
            while len(self.items) >= MAX_PENDING:
                self.items.pop(next(iter(self.items)))
            key = secrets.token_urlsafe(18)
            self.items[key] = (now + TTL, kind, plan)
            return key

    def take(self, key, kind):
        """The plan of that identifier, once; None when it expired, was used, is of another kind or never existed."""
        with self.lock:
            entry = self.items.pop(str(key or ""), None)
            if entry is None or entry[0] <= self.clock() or entry[1] != kind:
                return None
            return entry[2]
