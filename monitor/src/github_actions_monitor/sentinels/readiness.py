#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A11 of the sentinel: release readiness, ecosystem health and dependency pins. Read only; every number comes from data the sentinel already has
(runs, alerts, pull requests, signing records, CHANGELOG, version files, pin files of the local clones). Nothing is estimated and nothing is invented:
what cannot be known is shown as "unknown" and a score is withheld when too few repositories have data.

  Release readiness     one row per repository with entries in CHANGELOG [Unreleased]: CI of the default branch (and the commit it was run on), whether the
                        version is already higher than the last release, whether a build exists after that release, whether it is signed, and the next step.
  Ecosystem health      per ecosystem: 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, old Dependabot pull requests,
                        builds waiting to be signed and hygiene problems. The weights are `sentinel.readiness.health.weights`; the parts are shown.
  Dependency pins       repositories that pin an older version of the repository that provides a shared contract or library, read from the files the clones
                        really contain (a pin table or lock files, described in `sentinel.readiness.pins.sources`). An ecosystem without such files is
                        listed as having no source; nothing is guessed.

The functions are pure (the tests call them directly); `read_pins` and `local_version` are the only ones that read files.
"""
import copy
import json
import re
from pathlib import Path

import sys as _sys
from github_actions_monitor import i18n
from github_actions_monitor.sentinels import signstate
from github_actions_monitor.app import toolconfig

DEFAULTS = {
    "enabled": True,
    "min_coverage": 0.5,          # a score is shown only when at least this share of the repositories of the ecosystem has run data and alerts
    "warn_below": 70,             # the report warns about an ecosystem whose score is below this
    "health": {"weights": {"red": 15, "stuck": 10, "secret": 25, "high_alert": 8, "alert": 2, "stale_pr": 2, "unsigned": 3, "hygiene": 1}},
    # pins: where the pins live. A source is {"ecosystem": key, "kind": "pin_table", "provider": REPO, "file": "path/in/provider.json", "key": "consumers"}
    # (a JSON object repo -> version pinned) or {"ecosystem": key, "kind": "lock_files", "provider": REPO, "lock_name": "x.lock.json", "version_key": "field"}
    # (every consumer clone is searched for files of that name; the OLDEST version found counts). The provider's own version is read from its clone.
    "pins": {"refresh_seconds": 600, "max_depth": 5, "skip_dirs": ["node_modules", ".git", "target", "dist", "build", "__pycache__", ".venv", ".mypy_cache", ".ruff_cache"],
             "sources": []},
}
COLUMNS = {
    "readiness": ("repo", "entries", "ci", "version", "build", "signing", "next"),
    "health": ("ecosystem", "score", "coverage", "penalties"),
    "pins": ("repo", "source", "pinned", "current", "where"),
}
NEXT_FOR_CI = {"red": "fix_ci", "unknown": "wait_data"}


def t(key, /, **values):
    return i18n.t(key, **values)


def settings(config):
    """`sentinel.readiness` of the configuration merged over DEFAULTS (unknown keys dropped; a value of the wrong type keeps the default)."""
    merged = copy.deepcopy(DEFAULTS)
    user = ((config or {}).get("sentinel") or {}).get("readiness") if isinstance((config or {}).get("sentinel"), dict) else None
    if not isinstance(user, dict):
        return merged
    for key in ("enabled", "min_coverage", "warn_below"):
        v = user.get(key)
        if isinstance(v, type(DEFAULTS[key])) and (isinstance(v, bool) == isinstance(DEFAULTS[key], bool)):
            merged[key] = v
        elif key == "min_coverage" and isinstance(v, int) and not isinstance(v, bool):
            merged[key] = float(v)
    weights = (user.get("health") or {}).get("weights") if isinstance(user.get("health"), dict) else None
    if isinstance(weights, dict):
        for name, base in DEFAULTS["health"]["weights"].items():
            v = weights.get(name)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
                merged["health"]["weights"][name] = v
    pins = user.get("pins")
    if isinstance(pins, dict):
        for key in ("refresh_seconds", "max_depth"):
            if isinstance(pins.get(key), int) and not isinstance(pins.get(key), bool) and pins[key] > 0:
                merged["pins"][key] = pins[key]
        if isinstance(pins.get("skip_dirs"), list):
            merged["pins"]["skip_dirs"] = [str(x) for x in pins["skip_dirs"] if isinstance(x, str)]
        if isinstance(pins.get("sources"), list):
            merged["pins"]["sources"] = [s for s in pins["sources"] if isinstance(s, dict) and s.get("kind") in ("pin_table", "lock_files")
                                         and isinstance(s.get("ecosystem"), str) and isinstance(s.get("provider"), str)]
    return merged


def version_key(text):
    """Comparable tuple of the numbers of a version string ("v0.8.0.7" -> (0, 8, 0, 7)); None when there is no number."""
    nums = re.findall(r"\d+", str(text or ""))
    return tuple(int(n) for n in nums) if nums else None


def older(a, b):
    """True when version a is lower than version b (trailing zeros do not count: 1.2 == 1.2.0); False when either cannot be read."""
    ka, kb = version_key(a), version_key(b)
    if ka is None or kb is None:
        return False
    n = max(len(ka), len(kb))
    return ka + (0,) * (n - len(ka)) < kb + (0,) * (n - len(kb))


# ---------- local files ----------

def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def changelog_version(text):
    """First versioned heading of a CHANGELOG ("## [1.2.3]"), never Unreleased; "" when there is none."""
    m = re.search(r"^## \[(\d[^\]]*)\]", (text or "").replace("\r\n", "\n"), re.M)
    return m.group(1) if m else ""


def local_version(clone):
    """The version a local clone declares: its *.project.json, else pyproject.toml, else the first heading of its CHANGELOG; "" when none says."""
    clone = Path(clone)
    try:
        for path in sorted(clone.glob("*.project.json")):
            try:
                v = json.loads(path.read_text(encoding="utf-8")).get("version")
            except (OSError, ValueError, AttributeError):
                continue
            if isinstance(v, str) and version_key(v):
                return v
    except OSError:
        pass
    m = re.search(r'^version\s*=\s*"([^"]+)"', _read(clone / "pyproject.toml"), re.M)
    if m and version_key(m.group(1)):
        return m.group(1)
    return changelog_version(_read(clone / "CHANGELOG.md"))


def _find_files(base, name, max_depth, skip):
    out, stack = [], [(Path(base), 0)]
    while stack:
        folder, depth = stack.pop()
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir():
                    if depth < max_depth and entry.name not in skip:
                        stack.append((entry, depth + 1))
                elif entry.name == name:
                    out.append(entry)
            except OSError:
                continue
    return sorted(out)


def read_pins(root, repo_names, eco_of, cfg):
    """Reads the pin sources from the local clones under `root`. Returns {"rows": [...every pin read...], "checked": n, "sources": [...],
    "no_source": [ecosystem keys without any source], "missing": [providers that are not cloned]}; rows hold repo, ecosystem, provider, pinned, current,
    where, behind (bool)."""
    cfg = cfg or DEFAULTS["pins"]
    root = Path(root) if root else None
    rows, sources, missing = [], [], []
    names = set(repo_names)
    pinned_eco = set()
    for src in cfg.get("sources") or []:
        eco, provider = src["ecosystem"], src["provider"]
        pinned_eco.add(eco)
        if root is None or not (root / provider).is_dir():
            missing.append(provider)
            continue
        current = local_version(root / provider)
        if not version_key(current):
            missing.append(provider)
            continue
        found = 0
        if src["kind"] == "pin_table":
            try:
                data = json.loads(_read(root / provider / str(src.get("file") or "")) or "{}")
            except ValueError:
                data = {}
            table = data.get(str(src.get("key") or "consumers")) if isinstance(data, dict) else None
            for repo, pin in sorted((table or {}).items()):
                if repo in names and isinstance(pin, str) and version_key(pin):
                    found += 1
                    rows.append({"repo": repo, "ecosystem": eco, "provider": provider, "pinned": pin, "current": current,
                                 "where": str(src.get("file") or ""), "behind": older(pin, current)})
        else:
            lock, field = str(src.get("lock_name") or ""), str(src.get("version_key") or "")
            for repo in sorted(r for r in names if eco_of(r) == eco and r != provider):
                oldest = None
                for path in _find_files(root / repo, lock, int(cfg.get("max_depth") or 5), set(cfg.get("skip_dirs") or [])):
                    try:
                        v = json.loads(path.read_text(encoding="utf-8")).get(field)
                    except (OSError, ValueError, AttributeError):
                        continue
                    if isinstance(v, str) and version_key(v) and (oldest is None or older(v, oldest[0])):
                        oldest = (v, path.relative_to(root / repo).as_posix())
                if oldest:
                    found += 1
                    rows.append({"repo": repo, "ecosystem": eco, "provider": provider, "pinned": oldest[0], "current": current,
                                 "where": oldest[1], "behind": older(oldest[0], current)})
        sources.append({"ecosystem": eco, "provider": provider, "kind": src["kind"], "current": current, "pins": found})
    no_source = [k for k in toolconfig.ecosystem_names() if k not in pinned_eco and not toolconfig.is_external(k)]
    return {"rows": rows, "checked": len(rows), "sources": sources, "no_source": no_source, "missing": sorted(set(missing)), "at": None}


# ---------- pure rules ----------

def ci_state(repo, runs, branch, red_by_repo, unchecked, inconclusive):
    """(state, sha, partial): red | green | unknown. Red when the last run of any workflow of the default branch failed (the single definition of
    the sentinel, handed in as `red_by_repo`); unknown when the repository was not checked at all; green carries `partial` when the run sample
    is full and may hide an older workflow."""
    if repo in red_by_repo:
        return "red", (red_by_repo[repo][0].get("sha") or ""), False
    done = signstate.completed_runs(runs or [], branch)
    if repo in unchecked or not done:
        return "unknown", "", False
    last = max(done, key=lambda r: r.get("started") or "")
    return "green", (last.get("sha") or ""), repo in inconclusive


def needs_signature(workflow):
    """True when the release of this build workflow is published with a signature (every workflow but the ones the release-assets check lists without `sig`)."""
    from github_actions_monitor.app import surface
    return "sig" in surface.asset_template(workflow or "", surface.settings({}))


def release_rows(inp):
    """Rows for the repositories with at least `min_entries` entries in [Unreleased]. Keys of `inp`: unreleased (repo -> n), min_entries, releases
    (repo -> {tagName, publishedAt}), runs, branches, red (A2 rows), unchecked, inconclusive, states (A5 target states), local_versions (repo -> version),
    eco_of."""
    unreleased, releases, runs = inp["unreleased"], inp["releases"], inp["runs"]
    red_by_repo = {}
    for r in inp.get("red") or []:
        red_by_repo.setdefault(r["repo"], []).append(r)
    states_by_repo = {}
    for s in inp.get("states") or []:
        states_by_repo.setdefault(s["repo"], []).append(s)
    rows = []
    for repo, entries in sorted(unreleased.items(), key=lambda kv: (-kv[1], kv[0])):
        if entries < inp["min_entries"] or toolconfig.is_external(inp["eco_of"](repo)):
            continue
        ci, sha, partial = ci_state(repo, runs.get(repo), (inp.get("branches") or {}).get(repo) or "main", red_by_repo, set(inp.get("unchecked") or []), set(inp.get("inconclusive") or []))
        tag = (releases.get(repo) or {}).get("tagName") or ""
        local = (inp.get("local_versions") or {}).get(repo) or ""
        bumped = (True if older(tag, local) else (False if tag and version_key(local) else None)) if tag else (True if version_key(local) else None)
        states = states_by_repo.get(repo) or []
        if not states:
            build, signing = "no_build", "na"
        elif any(s["state"] in ("built_on_gha", "signed_local") for s in states):
            build = "built"
            signing = "signed" if all(s["state"] == "signed_local" and s.get("trusted") for s in states if s["state"] != "published") else "unsigned"
        else:
            build, signing = "build_needed", "na"
        if ci != "green":
            nxt = NEXT_FOR_CI[ci]
        elif bumped is not True:
            nxt = "bump"
        elif build == "build_needed":
            nxt = "build_sign" if any(needs_signature(s.get("workflow")) for s in states) else "build"
        elif build == "built":
            nxt = "publish" if signing == "signed" else "sign"
        else:
            nxt = "cut"
        rows.append({"repo": repo, "entries": entries, "ci": ci, "ci_sha": sha[:7], "ci_partial": partial, "version": local, "tag": tag, "bumped": bumped,
                     "build": build, "signing": signing, "next": nxt, "ready": ci == "green"})
    return rows


def _penalty_text(parts):
    return ", ".join(f"{t('rd.p.' + name)} {n} (-{pen:g})" for name, n, pen in parts) or t("rd.p.none")


def health(s, eco, alerts, runs_by_repo, info, cfg):
    """One row per ecosystem from the finished snapshot `s` (A1-A6). Score = 100 - sum(weight x count), at least 0, shown only when the share of the
    ecosystem's repositories that have run data AND alerts read is at least `min_coverage`; otherwise None (unknown). Returns a list of rows."""
    weights = cfg["health"]["weights"]
    stale = s["a4"]["stale_days"]
    keys = toolconfig.ecosystem_names()
    rows = []
    for key in keys:
        repos = sorted(r for r, e in eco.items() if e == key)
        if not repos:
            continue
        mine = set(repos)
        counts = {
            "red": sum(1 for r in s["a2"]["red"] if r["repo"] in mine),
            "stuck": sum(1 for r in s["a1"]["stuck"] if r["repo"] in mine),
            "secret": sum((r.get("secret") or 0) for r in s["a3"]["rows"] if r["repo"] in mine),
            "high_alert": sum((r["sev"].get("critical", 0) + r["sev"].get("high", 0)) for r in s["a3"]["rows"] if r["repo"] in mine),
            "alert": 0,
            "stale_pr": sum(1 for p in s["a4"]["dependabot"] if p["repo"] in mine and (p.get("age_days") or 0) > stale),
            "unsigned": sum(1 for p in s["a5"]["pending_sign"] if p["repo"] in mine),
            "hygiene": sum(1 for r in s["a6"]["rows"] if r["repo"] in mine and r["problems"]),
        }
        total_alerts = sum((r.get("codeql") or 0) + (r.get("dependabot") or 0) for r in s["a3"]["rows"] if r["repo"] in mine)
        counts["alert"] = max(0, total_alerts - counts["high_alert"])   # serious ones are counted once, in their own line
        covered = sum(1 for r in repos if runs_by_repo.get(r) and (alerts.get(r) or {}).get("at") and r in info)
        coverage = covered / len(repos)
        parts = [(name, counts[name], round(weights[name] * counts[name], 2)) for name in ("red", "stuck", "secret", "high_alert", "alert", "stale_pr", "unsigned", "hygiene") if counts[name]]
        score = None if coverage < cfg["min_coverage"] else max(0, round(100 - sum(p for _, _, p in parts)))
        rows.append({"ecosystem": key, "score": score, "coverage": round(coverage, 2), "repos": len(repos), "parts": [{"name": n, "count": c, "penalty": p} for n, c, p in parts],
                     "external": toolconfig.is_external(key)})
    return rows


def build(inp, s, cfg):
    """The A11 block. `inp` is the snapshot input, `s` the snapshot built so far (a1-a6, a2 red rows...), `cfg` the merged `readiness` settings."""
    if not cfg.get("enabled", True):
        return {"enabled": False, "level": "unknown", "sections": [], "ready": 0, "behind": 0, "health": [], "pins": {}, "note": t("rd.off")}
    eco = inp["eco"]
    eco_of = lambda repo: eco.get(repo) or toolconfig.ecosystem_of(repo)   # noqa: E731
    releases = {r: i.get("release") for r, i in inp["repo_info"].items() if i.get("release")}
    rr = release_rows({"unreleased": {r: n for r, n in inp["unreleased"].items() if r in inp["repo_info"]}, "min_entries": inp["cfg"]["candidate_min_entries"],
                       "releases": releases, "runs": inp["runs"], "branches": {r: i.get("branch") for r, i in inp["repo_info"].items()}, "red": s["a2"]["red"],
                       "unchecked": s["a2"]["unchecked"], "inconclusive": s["a2"]["inconclusive"], "states": s["a5"]["states"],
                       "local_versions": inp.get("local_versions"), "eco_of": eco_of})
    hl = health(s, eco, inp["alerts"], inp["runs"], inp["repo_info"], cfg)
    pins = inp.get("pins") or {"rows": [], "checked": 0, "sources": [], "no_source": [], "missing": []}
    behind = [p for p in pins["rows"] if p.get("behind")]

    def cell_ci(r):
        base = t("rd.v." + r["ci"] + ("_partial" if r["ci_partial"] else ""))
        return f"{base} · {r['ci_sha']}" if r["ci_sha"] else base

    def cell_version(r):
        if r["bumped"] is True:
            return t("rd.v.bumped", version=r["version"], tag=r["tag"] or t("rd.v.no_release"))
        if r["bumped"] is False:
            return t("rd.v.not_bumped", version=r["version"])
        return t("rd.v.unknown")

    ready_rows = [[r["repo"], r["entries"], cell_ci(r), cell_version(r), t("rd.v." + r["build"]), t("rd.v.sign_" + r["signing"]), t("rd.n." + r["next"])] for r in rr]
    health_rows = [[toolconfig.label_of(h["ecosystem"]) + (" *" if h["external"] else ""), ("?" if h["score"] is None else str(h["score"])),
                    f"{round(h['coverage'] * 100)}%", _penalty_text([(p["name"], p["count"], p["penalty"]) for p in h["parts"]])] for h in hl]
    pin_rows = [[p["repo"], p["provider"], p["pinned"], p["current"], p["where"]] for p in behind]
    weights = ", ".join(f"{k} {v:g}" for k, v in cfg["health"]["weights"].items())
    notes_pins = []
    if pins.get("sources"):
        notes_pins.append(t("rd.note.pins_read", n=pins.get("checked", 0), list=", ".join(f"{x['provider']} {x['current']}" for x in pins["sources"])))
    if pins.get("missing"):
        notes_pins.append(t("rd.note.pins_missing", list=", ".join(pins["missing"])))
    if pins.get("no_source"):
        notes_pins.append(t("rd.note.pins_none", list=", ".join(toolconfig.label_of(k) for k in pins["no_source"])))
    if inp.get("reduced"):
        notes_pins = [t("rd.note.no_workspace")]
    sections = [
        {"key": "readiness", "title": t("rd.t.readiness"), "cols": [t("rd.c." + c) for c in COLUMNS["readiness"]], "rows": ready_rows, "count": len(ready_rows), "copy": [],
         "note": t("rd.note.readiness", min=inp["cfg"]["candidate_min_entries"]), "level": "info" if rr else "ok"},
        {"key": "health", "title": t("rd.t.health"), "cols": [t("rd.c." + c) for c in COLUMNS["health"]], "rows": health_rows, "count": len(health_rows), "copy": [],
         "note": t("rd.note.health", weights=weights, pct=round(cfg["min_coverage"] * 100)),
         "level": "warn" if any(h["score"] is not None and h["score"] < cfg["warn_below"] for h in hl) else ("unknown" if any(h["score"] is None for h in hl) else "ok")},
        {"key": "pins", "title": t("rd.t.pins"), "cols": [t("rd.c." + c) for c in COLUMNS["pins"]], "rows": pin_rows, "count": len(pin_rows), "copy": [],
         "note": " ".join(notes_pins), "level": "info" if behind else "ok"},
    ]
    levels = [x["level"] for x in sections]
    level = "warn" if "warn" in levels else ("info" if "info" in levels else ("unknown" if inp.get("loading") else "ok"))
    low = [h for h in hl if h["score"] is not None and h["score"] < cfg["warn_below"]]
    return {"enabled": True, "level": level, "sections": sections, "ready": sum(1 for r in rr if r["ready"]), "behind": len(behind), "rows": rr, "health": hl,
            "pins": {"checked": pins.get("checked", 0), "sources": pins.get("sources", []), "no_source": pins.get("no_source", []), "missing": pins.get("missing", [])},
            "low_health": [{"ecosystem": h["ecosystem"], "score": h["score"]} for h in low], "warn_below": cfg["warn_below"], "behind_repos": [p["repo"] for p in behind]}
