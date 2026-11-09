# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract of a sentinel of the complete edition (1.7.1): what the monitor asks of every one of them, so that the second one (Collab, 1.7.2) and the next ones can live beside the
CI sentinel without the monitor knowing what each one does.

A sentinel is read only, has a cycle of its own (`refresh_seconds`, independent of the others), tells its state in plain serialisable data and its alerts in one shape (`Alert`), whose
`code` is stable and never depends on the language. The lite edition does not load this module.

`ctx` is what the monitor gives a sentinel today: the functions of the account it watches (`gh`, `repos_fn`, `runs_fn`, `data_fn`, `eco_fn`) and, since 1.7.1, `account_id` (empty for the
single account). When the monitor moves to several accounts inside one process this becomes an `AccountContext`; a sentinel keeps reading only what it is given.
"""
import threading
import time
from abc import ABC, abstractmethod
from typing import ClassVar, Literal, TypedDict

LEVELS = ("info", "warning", "error", "critical")


class Alert(TypedDict):
    id: str                    # stable for the same finding between two cycles: "ci.red:REPO:ci.yml"
    code: str                  # stable and independent of the language: "ci.red", "ci.stuck", "collab.issue.stale"...
    level: Literal["info", "warning", "error", "critical"]
    sentinel: str              # "ci", "collab"...: where the alert comes from
    account_id: str
    repo: str | None
    title: str                 # in the language of the page
    details: dict
    created_at: str            # ISO 8601, UTC


class BaseSentinel(ABC):
    name: ClassVar[str]        # "ci", "collab", "security"
    enabled = True             # a sentinel that can be switched off reads it from its configuration (the CI one makes it a property)

    def __init__(self, ctx, config):
        self.ctx, self.config = ctx, config
        self.last_tick = 0.0               # when the registry last ran `tick()` (0 = never)
        self._halt = threading.Event()

    @property
    @abstractmethod
    def refresh_seconds(self) -> int:
        """Seconds between two cycles of this sentinel; the others have their own."""

    @abstractmethod
    def tick(self):
        """One complete cycle: reads what it needs and updates its state. Calling it twice in a row changes nothing the second time that the first one did not."""

    @abstractmethod
    def get_status(self) -> dict:
        """Serialisable: whether it is on, whether it is still loading, its errors."""

    @abstractmethod
    def get_alerts(self) -> list:
        """The `Alert`s of the last cycle."""

    @abstractmethod
    def get_metrics(self) -> dict:
        """Flat numbers, for /metrics and for a score."""

    @abstractmethod
    def get_config_schema(self) -> dict:
        """The options this sentinel reads, with their types and defaults, for the Settings page."""

    def start(self) -> None:
        """Runs `tick()` in a thread of its own every `refresh_seconds`. A sentinel with a loop of its own (the CI one) overrides this."""
        threading.Thread(target=self.run_loop, daemon=True, name=f"sentinel-{self.name}").start()

    def stop(self) -> None:
        self._halt.set()

    def due(self, now=None) -> bool:
        now = time.time() if now is None else now
        return now - self.last_tick >= self.refresh_seconds

    def run_loop(self) -> None:
        while not self._halt.is_set():
            if self.due():
                try:
                    self.tick()
                except Exception:   # noqa: BLE001 - a failing sentinel never stops the monitor or the others
                    pass
                self.last_tick = time.time()
            self._halt.wait(min(5.0, max(1.0, float(self.refresh_seconds))))
