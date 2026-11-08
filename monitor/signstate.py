# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Explicit state of every build target: built_on_gha -> signed_local (none | dev | release) -> published, plus the signing queue of the day.

Pure functions (no network, no writes) fed by data the sentinel already has:
  * the run cache of the monitor (last runs of the build workflows),
  * the latest release of each repository (GraphQL, already collected; its asset names when present),
  * the local records: <signed_dir>/batches/batch_*.json (what a batch dispatched, signed and published; the records of before 1.5.0, lotes/lote_*.json, are read too) and
    <signed_dir>/<REPO>/release-<version>/ (the signed set that the local tools leave on disk).

Rules
  built_on_gha  the last completed run of the build workflow on the default branch succeeded; last_build_at = its start.
  signed_local  a local record newer than that build: the batch file says signed_at, or release-<version>/ was written after the build.
                signature_kind = the manifest's signing_key_kind ("dev"/"release") when there is one, else "release" when signature files
                (.sig .sig2 .imgsig) or a signed APK are there, else "none". Only a "release" signature lowers the alert.
  published     the latest GitHub release is newer than the build, or the batch file says published_at at/after the build.
signature_verified  True | False | "unknown": the signed folder checked against the PUBLIC key the ecosystem pins (sigverify.py, read only, no
                network). Only signature_kind "release" with signature_verified True counts as trusted (`trusted`): that is what lowers the
                pending-signature alert (besides "published"). The build attestation needs the network and is not read here: the tools that
                sign verify it before they publish.
"""
import json
import re
import sigverify
from datetime import datetime, timezone
from pathlib import Path

SIG_SUFFIXES = (".sig", ".sig2", ".imgsig")
IGNORED_DIRS = ("batches", "lotes", "github_actions_monitor", "github_actions_monitor")
IGNORED = ("cancelled", "skipped", "neutral", "stale")
ECO_RANK = {"armor": 0, "urtc": 1, "hydra": 2, "eh3d": 3}
KIND_RANK = {"none": 0, "dev": 1, "release": 2}


def parse_time(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if text else None
    except (ValueError, TypeError):
        return None


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _version_key(name):
    return tuple(int(n) for n in re.findall(r"\d+", name))


def signature_kind(names, manifest_kinds=()):
    """none | dev | release for the files of one signed set."""
    kinds = {k for k in manifest_kinds if k in ("dev", "release")}
    if "release" in kinds:
        return "release"
    if "dev" in kinds:
        return "dev"
    if any(n.endswith(SIG_SUFFIXES) for n in names) or any(n.lower().endswith(".apk") for n in names):
        return "release"
    return "none"


def completed_runs(runs, branch="main", workflow=None):
    """THE definition of "the runs that count": completed, on the default branch, not cancelled/skipped/neutral/stale (and of one workflow file
    when `workflow` is given). Red (A2), green-without-release (A5) and the target states all start from this list."""
    return [r for r in runs if r.get("status") == "completed" and r.get("branch") == branch and r.get("conclusion") not in IGNORED
            and (workflow is None or r.get("path") == workflow)]


def local_signed_index(signed_dir, keys=None):
    """repo -> {version, kind, verified, signed_at, files} of the newest release-<version> folder. Missing folder -> {}.
    `keys` = {ecosystem: public key hex} (sigverify.pinned_keys); without it verified is "unknown"."""
    out = {}
    try:
        repos = [d for d in Path(signed_dir).iterdir() if d.is_dir() and d.name not in IGNORED_DIRS]
    except OSError:
        return out
    for repo_dir in repos:
        try:
            releases = [d for d in repo_dir.iterdir() if d.is_dir() and d.name.startswith("release-")]
            if not releases:
                continue
            newest = max(releases, key=lambda d: _version_key(d.name))
            files = [f for f in newest.iterdir() if f.is_file()]
            if not files:
                continue
            kinds = []
            for f in files:
                if f.name.endswith(".manifest.json") and f.stat().st_size < 65536:
                    try:
                        kinds.append(str(json.loads(f.read_text(encoding="utf-8")).get("signing_key_kind", "")))
                    except (OSError, ValueError, AttributeError):
                        pass
            kind = signature_kind([f.name for f in files], kinds)
            verified = verified_cached(newest, files, sigverify.ecosystem_of(repo_dir.name), keys) if kind != "none" else sigverify.UNKNOWN
            out[repo_dir.name] = {"version": newest.name[len("release-"):], "kind": kind, "verified": verified,
                                  "signed_at": iso(max(f.stat().st_mtime for f in files)), "files": len(files)}
        except OSError:
            continue
    return out


_VERIFIED = {}   # (folder, file names, sizes, mtimes, key) -> result: a signed set that did not change is not hashed again


def verified_cached(folder, files, eco, keys):
    key = (keys or {}).get(eco)
    if not key:
        return sigverify.UNKNOWN
    stamp = (str(folder), key, tuple(sorted((f.name, f.stat().st_size, f.stat().st_mtime_ns) for f in files)))
    if stamp not in _VERIFIED:
        if len(_VERIFIED) > 64:
            _VERIFIED.clear()
        _VERIFIED[stamp] = sigverify.verify_dir(folder, eco, keys)
    return _VERIFIED[stamp]


def batch_index(batch_dir, legacy_dir=None):
    """target name -> {run, dispatched_at, signed_at, published_at, batch}: the newest dispatch and the latest signed/published marks of all batches."""
    out = {}
    try:
        files = sorted([*Path(batch_dir).glob("batch_*.json"), *(Path(legacy_dir).glob("lote_*.json") if legacy_dir else [])], key=lambda p: p.stem.split("_", 1)[-1])
    except OSError:
        return out
    for path in files:
        try:
            batch = json.loads(path.read_text(encoding="utf-8"))
            targets = batch.get("targets") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for name, info in targets.items():
            if not isinstance(info, dict):
                continue
            row = out.setdefault(name, {"run": None, "dispatched_at": None, "signed_at": None, "published_at": None, "batch": path.name})
            if info.get("run"):
                row.update({"run": info["run"], "dispatched_at": info.get("dispatched_at"), "batch": path.name})
            for key in ("signed_at", "published_at"):
                if info.get(key) and (not row[key] or info[key] > row[key]):
                    row[key] = info[key]
    return out


def local_records(signed_root, keys=None):
    """Both local indexes from the signing folder (signed_dir) (file reads; the signature check is cached while the folder does not change)."""
    root = Path(signed_root)
    return {"signed": local_signed_index(root, keys), "batches": batch_index(root / "batches", root / "lotes")}


def asset_flags(names):
    """Which signature files the published release carries (from the asset names the GraphQL pass already reads). None = no assets known."""
    names = [str(n) for n in names or []]
    if not names:
        return None
    return {"sig": any(n.endswith(".sig") for n in names), "sig2": any(n.endswith(".sig2") for n in names),
            "sha256": any(n.endswith(".sha256") or n.upper() == "SHA256SUMS" for n in names), "imgsig": any(n.endswith(".imgsig") for n in names), "assets": len(names)}


def _asset_flags(release):
    return (release or {}).get("asset_flags")


def target_states(targets, runs_by_repo, releases, eco, local, now, default_branches=None, finalize_fn=None, require_verified=True):
    """One row per target that has at least one completed run of its build workflow on the default branch."""
    local = local or {}
    signed, lotes = local.get("signed") or {}, local.get("batches") or local.get("lotes") or {}
    rows = []
    for name, target in targets.items():
        repo, workflow = target.get("repo", name), target.get("workflow", "")
        branch = (default_branches or {}).get(repo) or "main"
        runs = completed_runs(runs_by_repo.get(repo, []), branch, workflow)
        if not runs:
            continue
        last = max(runs, key=lambda r: r.get("started") or "")
        built = last.get("conclusion") == "success"
        greens = [r for r in runs if r.get("conclusion") == "success"]
        last_ok = max(greens, key=lambda r: r.get("started") or "") if greens else None
        build_at = parse_time(last_ok.get("started")) if last_ok else None
        rel = releases.get(repo) or {}
        published_gh = bool(built and build_at and rel.get("publishedAt") and (parse_time(rel["publishedAt"]) or build_at) > build_at)
        lote, loc = lotes.get(name) or {}, signed.get(repo) or {}
        lote_pub = parse_time(lote.get("published_at"))
        published_lote = bool(built and build_at and lote_pub and lote_pub >= build_at)
        # latest local signing record, any age; "current" = made after this build
        candidates = [(t, k) for t, k in ((parse_time(lote.get("signed_at")), "release"), (parse_time(loc.get("signed_at")), loc.get("kind", "none"))) if t]
        signed_at, kind = max(candidates, key=lambda c: (c[0], KIND_RANK.get(c[1], 0))) if candidates else (None, "none")
        current = bool(built and build_at and signed_at and signed_at >= build_at and kind != "none")
        folder_at = parse_time(loc.get("signed_at"))
        # verified only speaks about the signed folder, and only when that folder is the one made after this build
        verified = loc.get("verified", sigverify.UNKNOWN) if (current and folder_at and folder_at >= build_at) else sigverify.UNKNOWN
        trusted = bool(current and kind == "release" and (verified is True or not require_verified))
        published = published_gh or published_lote
        state = "published" if published else ("signed_local" if current else ("built_on_gha" if built else "none"))
        hours = round((now - build_at).total_seconds() / 3600, 1) if (built and build_at and not published) else None
        rows.append({
            "name": name, "repo": repo, "ecosystem": eco.get(repo) or "other", "workflow": workflow, "built_on_gha": built,
            "last_build_at": last_ok.get("started") if last_ok else None, "run_id": last_ok.get("id") if last_ok else None,
            "url": last_ok.get("url") if last_ok else None, "signature_kind": kind,
            "signature_verified": verified, "trusted": trusted, "last_signed_at": signed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if signed_at else None, "signed_current": current,
            "published": published, "published_by": "github" if published_gh else ("batch" if published_lote else ""),
            "state": state, "hours": hours, "pending_sign_hours": hours,
            "release_assets": _asset_flags(rel),
        })
    return sorted(rows, key=lambda r: (r["repo"], r["name"]))


def sign_queue(states, finalize_fn=None):
    """Targets built on GitHub and not published yet, most urgent first (hours waiting desc, then ecosystem, then name).
    step = sign (nothing real-signed yet) or publish (release-signed, waiting for the publication)."""
    queue = []
    for s in states:
        if s["state"] not in ("built_on_gha", "signed_local"):
            continue
        step = "publish" if (s["state"] == "signed_local" and s["signature_kind"] == "release" and s.get("trusted", True)) else "sign"
        argv = []
        if finalize_fn and s.get("run_id"):
            try:
                argv = [str(x) for x in finalize_fn(s["name"], s["run_id"])]
            except (KeyError, OSError):
                argv = []
        queue.append({"name": s["name"], "repo": s["repo"], "ecosystem": s["ecosystem"], "hours": s["hours"] or 0.0, "step": step, "run_id": s["run_id"],
                      "last_build_at": s["last_build_at"], "signature_kind": s["signature_kind"], "signature_verified": s.get("signature_verified", sigverify.UNKNOWN), "url": s["url"], "argv": argv,
                      "command": subprocess_cmdline(argv)})
        queue[-1]["trust"] = trust_of(queue[-1])
    return sorted(queue, key=lambda q: (-q["hours"], ECO_RANK.get(q["ecosystem"], 9), q["name"]))


TRUST_VALUES = ("verified", "unknown", "failed")


def trust_of(row):
    """The signature of a queue row as one of verified | unknown | failed (a signature that was checked and did not match is "failed", never "unknown")."""
    value = row.get("signature_verified", sigverify.UNKNOWN)
    return "verified" if value is True else ("failed" if value is False else "unknown")


def filter_queue(queue, trust="all"):
    """The queue rows whose signature is `trust` (verified | unknown | failed); "all" or anything else keeps every row."""
    if trust not in TRUST_VALUES:
        return list(queue)
    return [q for q in queue if trust_of(q) == trust]


def subprocess_cmdline(argv):
    import subprocess
    return subprocess.list2cmdline(argv) if argv else ""
