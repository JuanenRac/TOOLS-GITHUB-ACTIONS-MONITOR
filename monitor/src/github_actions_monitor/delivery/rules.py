# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The delivery signals of a repository: what its tags, releases, CHANGELOG and version files say about whether what was built was also delivered.

Pure functions over data the sentinel already read (`delivery/reader.py`); nothing here touches the network or the disk. Signals (the code of the alert is `release.<name>`):

  release.unreleased_pending     the CHANGELOG has entries under [Unreleased] and the latest published release is older than `unreleased_days`
  release.tag_without_release    a version tag newer than the latest published release that has no release of its own
  release.release_without_notes  the latest published release has an empty body
  release.version_mismatch       the version files declared in `version_files` (and the first versioned heading of the CHANGELOG) do not all say the same version
  release.ecosystem_drift        a repository pins an older version of the repository that provides a shared contract (the pin tables of `sentinel.readiness.pins.sources`)
  release.assets_missing         the latest published release has no file for one of the patterns of `expected_assets`

A repository with no published release at all is not judged by the first three and the last one: it does not use releases. Frontier with the readiness panel (A11): the panel is ONE row per
repository drawn from clones; these are alerts with a stable id, their own cycle, silences and events, read through the API without clones.
"""
import fnmatch
import json
import re
from datetime import datetime, timezone

from github_actions_monitor.delivery import mainsource

SIGNALS = ("unreleased_pending", "tag_without_release", "release_without_notes", "version_mismatch", "ecosystem_drift", "assets_missing")
CODES = {name: "release." + name for name in SIGNALS}
SIGNAL_OF = {code: name for name, code in CODES.items()}
LEVELS = ("info", "warning", "error", "critical")
DEFAULT_LEVEL = {"unreleased_pending": "info", "tag_without_release": "warning", "release_without_notes": "info", "version_mismatch": "warning", "ecosystem_drift": "info", "assets_missing": "warning"}
REPO_SIGNALS = tuple(s for s in SIGNALS if s != "ecosystem_drift")      # the ones read from one repository alone
MAX_LISTED = 5      # what an alert lists of tags, patterns and versions (the numbers carry the rest)
VERSION_TAG_RE = re.compile(r"^[vV]?\d+(\.\d+)*([-+.][0-9A-Za-z.-]+)?\Z")
FILE_VERSION_RE = re.compile(r"""(?im)^\s*(?:__version__|version|VERSION|tool_version)\s*[:=]\s*["']?(\d[0-9A-Za-z.+_-]*)""")


def unreleased_count(text):
    """Number of list entries under `## [Unreleased]` of a CHANGELOG text: the one function of the monitor (`delivery/mainsource.py`)."""
    return mainsource.unreleased_count(text)


def version_key(text):
    """Comparable tuple of the numbers of a version ("v0.8.0.7" -> (0, 8, 0, 7)) without trailing zeros (1.2 == 1.2.0); None when there is no number."""
    nums = [int(n) for n in re.findall(r"\d+", str(text or ""))]
    while len(nums) > 1 and nums[-1] == 0:
        nums.pop()
    return tuple(nums) if nums else None


def older(a, b):
    ka, kb = version_key(a), version_key(b)
    return ka is not None and kb is not None and ka < kb


def changelog_version(text):
    """First versioned heading of a CHANGELOG ("## [1.2.3]"), never Unreleased; "" when there is none."""
    m = re.search(r"^## \[(\d[^\]]*)\]", str(text or "").replace("\r\n", "\n"), re.M)
    return m.group(1) if m else ""


def file_version(path, text):
    """The version a file declares: a `version` key of a JSON file, else the first `version = "x"` / `version: x` / `__version__ = "x"` line; "" when none says."""
    text = str(text or "")
    if str(path).lower().endswith(".json"):
        try:
            data = json.loads(text)
        except ValueError:
            return ""
        value = data.get("version") if isinstance(data, dict) else None
        return value if isinstance(value, str) and version_key(value) else ""
    m = FILE_VERSION_RE.search(text)
    return m.group(1) if m and version_key(m.group(1)) else ""


def parse_time(text):
    """Epoch seconds of an ISO 8601 time of GitHub ("2026-01-02T03:04:05Z"); None when it cannot be read."""
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
    except (ValueError, TypeError):
        return None


def published(releases):
    """The published (not draft, not pre-release) releases of the answer of the API, newest first."""
    rows = [r for r in releases or [] if isinstance(r, dict) and not r.get("draft") and not r.get("prerelease") and isinstance(r.get("tag_name"), str)]
    return sorted(rows, key=lambda r: parse_time(r.get("published_at") or r.get("created_at")) or 0, reverse=True)



def repo_findings(facts, cfg, now):
    """{signal: detail} of one repository. `facts` = {"releases": [...] | None, "tags": [names] | None, "changelog": text | None, "versions": {path: text}}; a None means the signals that need it are
    skipped (it was not read). `cfg` = the settings of the sentinel. Pure."""
    out = {}
    releases = published(facts.get("releases")) if facts.get("releases") is not None else None
    latest = releases[0] if releases else None
    # 1. unreleased entries on top of an old release
    changelog = facts.get("changelog")
    if latest is not None and changelog is not None:
        entries = unreleased_count(changelog)
        when = parse_time(latest.get("published_at") or latest.get("created_at"))
        if when is not None and entries >= cfg["unreleased_min_entries"] and now - when >= cfg["unreleased_days"] * 86400:
            out["unreleased_pending"] = {"entries": entries, "days": int((now - when) // 86400), "tag": latest["tag_name"]}
    # 2. a version tag newer than the latest release, without a release
    tags = facts.get("tags")
    if latest is not None and tags is not None:
        released = {r.get("tag_name") for r in (facts.get("releases") or []) if isinstance(r, dict) and not r.get("draft")}
        newer = sorted((t for t in tags if isinstance(t, str) and VERSION_TAG_RE.match(t) and t not in released
                        and version_key(t) is not None and (version_key(latest["tag_name"]) is None or version_key(t) > version_key(latest["tag_name"]))), key=version_key, reverse=True)
        if newer:
            out["tag_without_release"] = {"n": len(newer), "tags": newer[:MAX_LISTED]}
    # 3. notes of the latest release
    if latest is not None and not str(latest.get("body") or "").strip():
        out["release_without_notes"] = {"tag": latest["tag_name"]}
    # 4. the assets the owner expects in the latest release
    patterns = cfg["expected_assets"]
    if latest is not None and patterns and isinstance(latest.get("assets"), list):
        names = [str(a.get("name") or "") for a in latest["assets"] if isinstance(a, dict)]
        missing = [p for p in patterns if not any(fnmatch.fnmatchcase(n.lower(), p.lower()) for n in names)]
        if missing:
            out["assets_missing"] = {"tag": latest["tag_name"], "n": len(missing), "missing": missing[:MAX_LISTED]}
    # 5. the versions the repository declares in more than one place
    versions = {}
    for path, text in sorted((facts.get("versions") or {}).items()):
        found = file_version(path, text)
        if found:
            versions[path] = found
    if changelog is not None and changelog_version(changelog):
        versions["CHANGELOG"] = changelog_version(changelog)
    if len({version_key(v) for v in versions.values()}) > 1:
        out["version_mismatch"] = {"n": len({version_key(v) for v in versions.values()}), "versions": dict(list(versions.items())[:MAX_LISTED + 1])}
    return out


def drift_rows(source, current, table, repos):
    """[{"repo", "provider", "pinned", "current", "where"}] of the repositories of `repos` that pin a version older than `current` in the pin table `table` ({repo: version})."""
    rows = []
    for repo, pin in sorted((table or {}).items()):
        if repo in repos and isinstance(pin, str) and older(pin, current):
            rows.append({"repo": repo, "provider": source["provider"], "pinned": pin, "current": current, "where": str(source.get("file") or "")})
    return rows


def evaluate(repo, detail_by_signal, signals, known=None, stamp=""):
    """{alert id: alert} of one repository from `repo_findings(...)`; `signals` = {signal: {"enabled", "level"}}. One alert per repository and signal. `known` are the alerts already open (they keep
    their `created_at`)."""
    known, alerts = known or {}, {}
    for signal in SIGNALS:
        detail = detail_by_signal.get(signal)
        rule = signals.get(signal) or {}
        if not detail or not rule.get("enabled", True):
            continue
        key = f"{CODES[signal]}:{repo}"
        alerts[key] = {"id": key, "code": CODES[signal], "level": rule.get("level") or DEFAULT_LEVEL[signal], "repo": repo, "created_at": (known.get(key) or {}).get("created_at") or stamp, "detail": detail}
    return alerts


def drift_alerts(rows, signal_rule, known=None, stamp=""):
    """{alert id: alert} for the repositories behind in a pin table; one per repository, listing up to three providers."""
    known, alerts, by_repo = known or {}, {}, {}
    if not (signal_rule or {}).get("enabled", True):
        return alerts
    for row in rows:
        by_repo.setdefault(row["repo"], []).append(row)
    for repo, mine in sorted(by_repo.items()):
        key = f"{CODES['ecosystem_drift']}:{repo}"
        alerts[key] = {"id": key, "code": CODES["ecosystem_drift"], "level": (signal_rule or {}).get("level") or DEFAULT_LEVEL["ecosystem_drift"], "repo": repo,
                       "created_at": (known.get(key) or {}).get("created_at") or stamp,
                       "detail": {"n": len(mine), "provider": mine[0]["provider"], "pinned": mine[0]["pinned"], "current": mine[0]["current"], "where": mine[0]["where"],
                                  "behind": [f"{m['provider']} {m['pinned']} -> {m['current']}" for m in mine[:3]]}}
    return alerts
