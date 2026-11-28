# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A digest that two readers can compare to know that a report or a brief says the same thing: SHA-256 over the facts in one fixed form, the version of the monitor that wrote them, the version of the
rules and the verdict. What changes with the clock alone (when it was generated) is left out. It is a fingerprint, not a signature: it does not prove who wrote it."""
import hashlib
import json

from github_actions_monitor.tool_version import TOOL_VERSION

RULES_VERSION = 1      # grows when the meaning of a verdict changes
VOLATILE = ("generated_at", "generated_epoch", "report_digest")


def normalized(value):
    if isinstance(value, dict):
        return {str(k): normalized(v) for k, v in value.items() if str(k) not in VOLATILE}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    return value


def digest(facts, verdict=None, engine=None):
    """"sha256:<hex>" of the facts, the engine, the rules and the verdict."""
    body = {"facts": normalized(facts), "engine": engine or TOOL_VERSION, "rules": RULES_VERSION, "verdict": verdict}
    return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("ascii")).hexdigest()
