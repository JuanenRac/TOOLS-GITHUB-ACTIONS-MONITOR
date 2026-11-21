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


LIFECYCLES = ("healthy", "degraded", "paused", "error", "off")


def round_deadline(seconds):
    """The moment (monotonic) a round must stop starting new repositories, or None when the sentinel has no ceiling (`deadline_s` = 0)."""
    return time.monotonic() + seconds if seconds else None


def expired(deadline):
    return deadline is not None and time.monotonic() > deadline


def unchecked(repos, per_repo, limit=20):
    """The names of the repositories in scope that have never been read (a round that ran out of time leaves them for the next one): shown by name instead of as zero alerts."""
    return [r for r in repos if not (per_repo.get(r) or {}).get("scanned")][:limit]


def guarded(errors, key, fn, *args, now=None, default=None, **kwargs):
    """Runs one element of a round (a repository, a file, a stage, a channel) inside its own try: whatever it raises is written down in `errors[key]` with its cause and `default` comes back, so
    one bad element never knocks down the rest of the round and is never left without a record. The caller keeps what it knew about the element (it is not closed as fixed by not looking: see
    `HOLD_WHEN_UNREAD`). A success clears the record of the key."""
    try:
        value = fn(*args, **kwargs)
    except Exception as error:   # noqa: BLE001 - this is the point of the function
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if now is None else now))
        errors[key] = {"message": str(error)[:80], "at": stamp}
        return default
    errors.pop(key, None)
    return value


def forget_errors(errors, repos, keep=("search",)):
    """Drops the records of the repositories that left the scope (`errors` is keyed by `repo` or `repo:part`; `keep` names the keys that belong to no repository)."""
    scope = set(repos)
    for key in [k for k in errors if k not in keep and str(k).split(":", 1)[0] not in scope]:
        errors.pop(key, None)


# What every sentinel with a loop over repositories owes (a test of contract, test_216_sentinel_contract, fails for one that does not keep it):
#   1. ISOLATION: each repository, file, item and stage of a round has its own try; a bad one is recorded in `errors` and the rest of the round goes on;
#   2. HOLD_WHEN_UNREAD: what was known about an element that could not be read now is kept (marked unread), not closed as fixed and not counted as checked; a repository that never
#      was read is listed as not checked (`unchecked`), never as zero alerts;
#   3. SCOPE: an element that left the scope (a repository that is no longer listed) is dropped, with its alerts, at the end of the round.
HOLD_WHEN_UNREAD = True


def lifecycle(status):
    """Where a sentinel stands, from its status: `off` (not switched on), `paused` (waiting for allowance), `error` (it fails and has read nothing yet), `degraded` (some reads fail, a source
    cannot be read, or it has not finished its first look) or `healthy`. "No alerts" only means something when this is `healthy`: a sentinel that could not look has no alerts either."""
    if not isinstance(status, dict) or not status.get("enabled", True) or status.get("level") == "off":
        return "off"
    if status.get("paused"):
        return "paused"
    errors = status.get("errors") or []
    if errors and not status.get("repos_checked") and status.get("level") in (None, "unknown"):
        return "error"
    if errors or status.get("unavailable") or status.get("loading") or status.get("level") == "unknown":
        return "degraded"
    return "healthy"


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
