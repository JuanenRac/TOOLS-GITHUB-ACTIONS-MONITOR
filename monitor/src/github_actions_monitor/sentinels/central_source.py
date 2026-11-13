# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The central panel as a BASE LINE: a file `data/sentinel.json` of the profile repository `<owner>/<owner>`, refreshed every half hour by a workflow with ITS OWN token, so reading it spends none of your allowance.

  central.source          "off" (default) | "git" (git fetch of the local clone and `git show origin/main:data/sentinel.json`: no API call at all) | "http" (the raw file of the repository)
  central.max_age_minutes the file older than this (120) is "behind": it is shown as such and not trusted
  central.git_dir         the clone to read ("" = <workspace>/<owner>)

What it gives (the same keys the sentinel of the central panel writes): `asof`, `ci` {checked, red[], red_total}, `ecosystems`, `releases.candidates`, `signatures`, `hygiene`, `unpublished`, `compute`, `trend`. The monitor shows it as
"source: central panel, N min ago", uses it as the base line of reds / candidates / signatures / hygiene, and in Low mode asks the API live only for the repositories with a run in progress, an open red or a security
panel that the file does not carry. The rule of "red" is the one of the file: the same as redrule.py (the last completed run of each workflow on the default branch).
"""
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULTS = {"source": "off", "max_age_minutes": 120, "git_dir": ""}
SOURCES = ("off", "git", "http")
FILE = "data/sentinel.json"
_CACHE = {"at": 0.0, "key": None, "value": None}
TTL = 300      # seconds between two reads: the file changes every half hour


def settings(config):
    block = (config or {}).get("central") if isinstance((config or {}).get("central"), dict) else {}
    minutes = block.get("max_age_minutes")
    return {"source": block.get("source") if block.get("source") in SOURCES else "off",
            "max_age_minutes": minutes if isinstance(minutes, int) and not isinstance(minutes, bool) and 5 <= minutes <= 10080 else DEFAULTS["max_age_minutes"],
            "git_dir": block.get("git_dir") if isinstance(block.get("git_dir"), str) and len(block["git_dir"]) <= 260 and not any(ord(c) < 32 for c in block["git_dir"]) else ""}


def validate(data):
    """The file as a dict with the shape the monitor needs, or None (a file of another shape is as good as no file)."""
    if not isinstance(data, dict) or not isinstance(data.get("asof"), str):
        return None
    ci = data.get("ci")
    if not isinstance(ci, dict) or not isinstance(ci.get("red"), list):
        return None
    # the real rows are {"repo", "wf"} (the file name of the workflow); "workflow" is accepted too and both are kept under "wf"
    ci["red"] = [{**r, "wf": str(r.get("wf") or r.get("workflow") or "")} for r in ci["red"] if isinstance(r, dict) and isinstance(r.get("repo"), str)]
    rel = data.get("releases") if isinstance(data.get("releases"), dict) else {}
    rel["candidates"] = [c for c in (rel.get("candidates") or []) if isinstance(c, dict) and isinstance(c.get("repo"), str)]
    data["releases"] = rel
    return data


def age_seconds(data, now=None):
    try:
        asof = datetime.strptime(data["asof"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (KeyError, TypeError, ValueError):
        return None
    return max(0, int((time.time() if now is None else now) - asof))


def _git(args, cwd, runner):
    return runner(["git", *args], cwd)


def _run(args, cwd):
    done = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40, shell=False)
    return done.returncode, done.stdout, done.stderr


def read(config, owner, workspace="", runner=None, opener=None, now=None, force=False):
    """{"ok", "source", "asof", "age_seconds", "stale", "data", "error"}: the base line, or why there is none. Cached for TTL seconds; `runner(args, cwd)` and `opener(url)` are the seams of the tests."""
    cfg = settings(config)
    if cfg["source"] == "off":
        return {"ok": False, "source": "off", "error": "off"}
    now = time.time() if now is None else now
    key = (cfg["source"], owner, cfg["git_dir"], workspace)
    if not force and _CACHE["key"] == key and now - _CACHE["at"] < TTL and _CACHE["value"] is not None:
        return _CACHE["value"]
    out = {"ok": False, "source": cfg["source"]}
    try:
        if cfg["source"] == "git":
            folder = Path(cfg["git_dir"] or (Path(workspace) / owner if workspace else ""))
            if not str(folder) or not folder.is_dir():
                raise ValueError("no clone of the profile repository")
            run = runner or _run
            run(["git", "fetch", "origin", "main", "--quiet"], folder)      # no API call: a plain git transfer
            code, text, err = run(["git", "show", f"origin/main:{FILE}"], folder)
            if code != 0:
                raise ValueError("git show failed")
        else:
            url = f"https://raw.githubusercontent.com/{owner}/{owner}/main/{FILE}"
            if opener is not None:
                text = opener(url)
            else:
                from github_actions_monitor.security import netguard
                import urllib.request
                with netguard.open_url(urllib.request.Request(url, headers={"User-Agent": "github-actions-monitor"}), timeout=15) as answer:
                    text = answer.read(4_000_000).decode("utf-8", "replace")
        data = validate(json.loads(text))
        if data is None:
            raise ValueError("the file has not the shape of the central panel")
        age = age_seconds(data, now)
        out.update({"ok": True, "asof": data["asof"], "age_seconds": age, "stale": age is None or age > cfg["max_age_minutes"] * 60, "data": data})
    except Exception as error:   # noqa: BLE001 - a base line that cannot be read is "no base line", never a failure of the monitor
        out["error"] = str(error)[:160]
    _CACHE.update({"at": now, "key": key, "value": out})
    return out


def red_repos(result):
    """The repositories red on their default branch according to a base line that can be trusted (not behind); empty otherwise."""
    if not result or not result.get("ok") or result.get("stale"):
        return set()
    return {r["repo"] for r in result["data"]["ci"]["red"]}


def summary(result):
    """One line for the page and the brief: where the figures come from and how old they are."""
    if not result or result.get("source") == "off":
        return ""
    if not result.get("ok"):
        return f"central panel not readable ({result.get('error')})"
    minutes = (result.get("age_seconds") or 0) // 60
    base = f"source: central panel, {minutes} min ago: {len(result['data']['ci']['red'])} red, {len(result['data']['releases']['candidates'])} release candidate(s)"
    return base + (" - the central panel is behind: not trusted" if result.get("stale") else "")


def reset():
    _CACHE.update({"at": 0.0, "key": None, "value": None})
