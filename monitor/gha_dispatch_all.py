#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Fires, watches and closes a BATCH of GitHub Actions builds ("build in GitHub, sign here").

Nothing is compiled on this PC. The commands only talk to GitHub through `gh`:

  py -3 gha_dispatch_all.py plan     [--only NAME ... | --ecosystem E] [--json]
                                                             what would be built (no calls that change anything); --json = machine-readable
  py -3 gha_dispatch_all.py dispatch [--only NAME ... | --ecosystem E] --go
                                                             fires workflow_dispatch for each target (dry_run=true: artefacts + attestation, no draft)
  py -3 gha_dispatch_all.py status                           state of the last batch (runs, jobs, open build-failed/build-stuck issues)
  py -3 gha_dispatch_all.py finalize [--json] [--execute]    lists, per ready target, the exact local command that downloads, verifies,
                                                             signs and publishes (--execute runs them one by one, asking first)
  py -3 gha_dispatch_all.py hygiene [--write-candidates]     targets with a problem, build workflows no target covers, default branch that is not main;
                                                             --write-candidates PROPOSES the missing entries in targets.candidates.json (never touches targets.json)

  E = armor | urtc | hydra | eh3d (the targets of that ecosystem; EH3D has none today and says so).

The catalogue of targets is DATA: targets.json next to this file (this module only loads and validates it). The entry of a build the catalogue does
not know yet follows a CONVENTION (candidate_target: ecosystem prefix -> default signing tool, workflow in BUILD_WORKFLOWS); targets.json only
carries what differs from it (extra flags, finalize_flags, ...) and always wins. `plan` always ends with the section "Signature orphans"
(green CI + a known *-build.yml + no entry in targets.json).

Safety rules:
  * `dispatch` refuses a repository whose main has no green CI on its HEAD (the REQUIRED workflow files of dispatch.required_ci succeeded, nothing failed or waits for approval, the list of
    runs is complete), or whose local clone is not at origin/main after a `git fetch` that worked. A tool of the catalogue must be a plain file name inside the tools folder and `extra` may only
    hold `-f key=value` workflow inputs (never dry_run or ref).
  * `finalize` offers for signing only a run whose batch recorded that it was built on the commit that was checked; `finalize --accept-legacy` re-reads an older batch from GitHub first.
  * A workflow_dispatch that fails through the API is marked and retried ONCE at the end of the batch; the rest of the batch goes on.
  * Default is dry_run=true: the workflow builds, attests and uploads the artefact but creates NO draft release, so no approval in the
    `release` environment is needed. `--real` sets dry_run=false (creates the unsigned draft; the owner approves it on the run page).
  * Signing keys are never read here; `finalize --execute` only starts your own local signing tools, which read their keys from wherever
    you keep them and show what they will do. When one of them succeeds the batch file records signed_at/published_at,
    which the sentinel reads to lower the "green but unsigned" alert without waiting for GitHub.
Batches are recorded in <signed_dir>/batches/batch_<time>.json (see workspace.py; the records of versions before 1.5.0, <signed_dir>/lotes/lote_*.json, are still read).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # works also under `py -3 -I`
import i18n
import monitor_link
import platform_compat
import toolconfig
import workspace
from tool_version import TOOL_VERSION

t = i18n.t


def te(key, /, **values):
    """Text of a MACHINE-READ line (markers such as SKIP, DISPATCHED, READY, FAILED, Summary, BUILD ONLY): always English, whatever the language, because scripts parse them. The human phrases passed in as values stay translated."""
    return i18n.tl("en", key, **values)

HERE = Path(__file__).resolve().parent
ROOT = workspace.workspace_root_soft()  # the workspace with the repositories (MONITOR_ROOT, actions_monitor.json or a marker file; see workspace.py)
BATCH_DIR = workspace.signed_dir_soft() / "batches"
LEGACY_BATCH_DIR = workspace.signed_dir_soft() / "lotes"   # before 1.5.0
TOOLS_DIR = workspace.tools_dir()   # "tools_dir" in actions_monitor.json (or MONITOR_TOOLS_DIR); default: the tools folder next to this file
TARGETS_FILE = toolconfig.targets_path()   # "targets_file" in actions_monitor.json, default targets.json
BUILD_WORKFLOWS = ("firmware-build.yml", "package-build.yml", "apk-build.yml", "exe-build.yml", "site-build.yml", "binaries-build.yml",
                   "dist-build.yml", "release-files-build.yml")
# the ecosystems marked "external" in the ecosystems file are reported apart, never added (toolconfig.is_internal)
ECOSYSTEMS = tuple(toolconfig.ecosystem_names())
NAME_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
TOOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,98}\.py$")           # a plain file name: no folder, no drive, no "..", no leading dash
INPUT_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")             # the name of an input of a workflow
RESERVED_INPUTS = ("dry_run", "ref")                                    # decided by this program, never by the catalogue
FLAG_RE = re.compile(r"^--[a-z][a-z0-9-]{0,40}$")                       # a long flag of a signing tool (finalize_flags)
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
GIT_TIMEOUT = 60
CI_PAGES = 5                                                             # pages of 100 runs read before the sample counts as incomplete
DEFAULT_REQUIRED_CI = ("ci.yml",)                                        # the workflow file of the CI of a repository when nothing else is configured
TARGET_KEYS = {"workflow", "tool", "extra", "repo", "finalize_flags", "build_only", "reason"}
BAD_CONCLUSIONS = ("failure", "timed_out", "startup_failure", "action_required")   # the same family as redrule.BAD: a run waiting for an approval blocks too
PROFILES_FILE = toolconfig.profiles_path()   # "profiles_file" in actions_monitor.json, default profiles.json
DEFAULT_MIN_RATE = 1500   # `dispatch --go` refuses to start when the GitHub allowance left is below this (profiles.json min_rate_remaining or --min-rate)
CANARY_WAIT_SECONDS = 1800
CANDIDATES_FILE = HERE / "targets.candidates.json"
# convention: ecosystem prefix -> default signing tool, from the ecosystems file ("tool"; "firmware_tool" + "firmware_extra" for a firmware workflow that needs its own tool)


def extra_inputs(extra):
    """({input: value}, problems) from the `extra` list of a target. Only pairs `-f key=value` (inputs of the workflow) are accepted: no other option of `gh` (-R, --ref,
    --repo, the workflow name...), no input that this program decides (dry_run, ref), no repeated input. The arguments of the command are then BUILT from the dict."""
    inputs, problems = {}, []
    items = list(extra)
    if len(items) % 2:
        problems.append("odd number of arguments (use \"-f\", \"key=value\" pairs)")
    for i in range(0, len(items) - len(items) % 2, 2):
        flag, pair = items[i], items[i + 1]
        if flag != "-f":
            problems.append(f"only -f key=value is allowed, not {flag!r}")
            continue
        key, sep, value = pair.partition("=")
        if not sep or not INPUT_KEY_RE.match(key):
            problems.append(f"{pair!r} is not key=value with a plain input name")
        elif key in RESERVED_INPUTS:
            problems.append(f"the input {key} is reserved for the program")
        elif key in inputs:
            problems.append(f"the input {key} is repeated")
        elif len(value) > 300 or any(ord(c) < 32 for c in value):
            problems.append(f"the value of {key} is not plain text of at most 300 characters")
        else:
            inputs[key] = value
    return inputs, problems


def dispatch_args(workflow, repo, real, extra):
    """The argument list of `gh workflow run`, built from validated pieces (never from a free list). Raises ValueError for an `extra` that does not validate."""
    inputs, problems = extra_inputs(extra)
    if problems:
        raise ValueError("; ".join(problems))
    args = ["workflow", "run", workflow, "-R", f"{toolconfig.github_owner()}/{repo}", "--ref", "main", "-f", f"dry_run={'false' if real else 'true'}", "-f", "ref=main"]
    for key, value in inputs.items():
        args += ["-f", f"{key}={value}"]
    return args


def tool_path(tool, tools_dir=None):
    """The path of a signing tool INSIDE the tools folder, or None: the name must be a plain file name and, once symbolic links are resolved, the file must still sit in that folder."""
    if not (isinstance(tool, str) and TOOL_RE.match(tool) and ".." not in tool):
        return None
    base = Path(tools_dir or TOOLS_DIR)
    path = base / tool
    try:
        if path.exists() and path.resolve().parent != base.resolve():
            return None
    except OSError:
        return None
    return path


def validate_targets(data):
    """Problems of a targets catalogue (empty list = valid). Pure: no disk access."""
    if not isinstance(data, dict):
        return [t("val.catalogue_empty")]
    data = {k: v for k, v in data.items() if not str(k).startswith("_")}   # "_author", "_license", "_note": metadata, not targets
    if not data:
        return [t("val.catalogue_empty")]
    problems = []
    for name, target in data.items():
        if not NAME_RE.match(str(name)) or str(name).split(":")[0] in (".", "..") or str(name).startswith(("-", ":")):
            problems.append(t("val.bad_name", name=name))
        if not isinstance(target, dict):
            problems.append(t("val.not_object", name=name))
            continue
        for key in sorted(set(target) - TARGET_KEYS):
            problems.append(t("val.unknown_key", name=name, key=key))
        if target.get("workflow") not in BUILD_WORKFLOWS:
            problems.append(t("val.bad_workflow", name=name, workflow=repr(target.get("workflow"))))
        if target.get("build_only") is not None:   # a build that is labelled on purpose as "built on GitHub, no signing tool here" (with the reason)
            if target.get("build_only") is not True or not (isinstance(target.get("reason"), str) and target["reason"].strip()):
                problems.append(t("val.build_only_reason", name=name))
            if "tool" in target or ":" in name:
                problems.append(t("val.build_only_tool", name=name))
            continue
        if "reason" in target:
            problems.append(t("val.reason_only", name=name))
        if not (isinstance(target.get("tool"), str) and TOOL_RE.match(target["tool"]) and ".." not in target["tool"]):
            problems.append(t("val.tool_py", name=name))
        for key in ("extra", "finalize_flags"):
            value = target.get(key, [])
            if not (isinstance(value, list) and all(isinstance(x, str) for x in value)):
                problems.append(t("val.list_of_str", name=name, key=key))
        if isinstance(target.get("extra"), list) and all(isinstance(x, str) for x in target["extra"]):
            inputs, bad = extra_inputs(target["extra"])
            problems += [t("val.extra_bad", name=name, why=why) for why in bad]
        if isinstance(target.get("finalize_flags"), list):
            problems += [t("val.flag_bad", name=name, flag=repr(f)) for f in target["finalize_flags"] if not (isinstance(f, str) and FLAG_RE.match(f))]
        if "extra" not in target:
            problems.append(t("val.extra_required", name=name))
        if ":" in name:
            base = name.split(":")[0]
            if target.get("repo") != base:
                problems.append(t("val.part_repo", name=name, base=base))
            if base not in data:
                problems.append(t("val.part_base", name=name, base=base))
        elif "repo" in target:
            problems.append(t("val.repo_only_parts", name=name))
    return problems


def load_targets(path=TARGETS_FILE):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(t("gd.cannot_read_targets", path=path, error=error))
    problems = validate_targets(data)
    if problems:
        raise SystemExit(t("gd.targets_invalid") + "\n  - " + "\n  - ".join(problems))
    return {k: v for k, v in data.items() if not str(k).startswith("_")}


_CATALOGUE = load_targets()
TARGETS = {n: t for n, t in _CATALOGUE.items() if not t.get("build_only")}   # what the batch builds and signs
BUILD_ONLY = {n: t for n, t in _CATALOGUE.items() if t.get("build_only")}    # builds labelled on purpose: never dispatched, never an orphan


def repo_of(name):
    return TARGETS[name].get("repo", name)


def ecosystem_of(repo):
    return toolconfig.ecosystem_of(repo)


def finalize_command(name, run_id, targets=None):
    """The exact local command (argv list) that downloads, verifies, signs and publishes the build `run_id` of target `name`."""
    t = (targets or TARGETS)[name]
    path = tool_path(t["tool"])
    if path is None:
        raise ValueError(f"the tool of {name} is not a plain file name inside the tools folder")
    cmd = [*platform_compat.python_argv(), str(path), name, "--run", str(run_id)]
    if t["tool"] == "fetch_and_sign.py":   # the firmware tool signs as part of --publish
        return cmd + ["--publish"]
    if t["tool"] == "armor_fetch_and_sign.py":
        return cmd + ["--sign", "--publish"]
    return cmd + ["--sign", "--publish", *t.get("finalize_flags", [])]


def command_text(argv):
    return platform_compat.command_text(argv)


def gh(*args, check=True):
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=90)
    if check and result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip()[:300])
    return result.stdout


def ghj(*args):
    out = gh(*args)
    return json.loads(out) if out.strip() else None


def git_run(path, *args, timeout=GIT_TIMEOUT):
    """(returncode, stdout, stderr) of one git command in `path`, with a time limit. A command that cannot run or does not finish gives a non-zero code (fail closed)."""
    try:
        done = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return done.returncode, done.stdout.strip(), done.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except OSError as error:
        return 127, "", str(error)


def local_head(repo):
    """(origin/main sha, problem). The problem is "" only when the fetch WORKED and HEAD is origin/main; a failed fetch, a git that does not answer or a value that is not a
    commit id gives (None, why): an old origin/main already on disk is never taken as proof of what GitHub has now."""
    path = ROOT / repo
    if not path.exists():
        return None, t("gd.no_clone")
    code, _out, err = git_run(path, "fetch", "-q", "origin")
    if code != 0:
        return None, t("gd.fetch_failed", why=(err or f"code {code}")[:120])
    code_h, head, _e = git_run(path, "rev-parse", "HEAD")
    code_r, remote, _e = git_run(path, "rev-parse", "origin/main")
    if code_h != 0 or code_r != 0 or not SHA_RE.match(head) or not SHA_RE.match(remote):
        return None, t("gd.sha_unreadable")
    return remote, ("" if head == remote else t("gd.head_mismatch", head=head[:7], remote=remote[:7]))


def required_ci(repo, config=None, profile=None):
    """The workflow FILES whose run on the commit must have succeeded for the repository: `dispatch.required_ci_repos[repo]`, else the profile's `dispatch.required_ci_profiles[profile]`,
    else `dispatch.required_ci`, else the CI workflow (ci.yml). Never empty."""
    cfg = (config if config is not None else toolconfig.raw_config()).get("dispatch")
    cfg = cfg if isinstance(cfg, dict) else {}
    for scope, key in ((cfg.get("required_ci_repos"), repo), (cfg.get("required_ci_profiles"), profile), (cfg, "required_ci")):
        found = scope.get(key) if isinstance(scope, dict) and key else None
        if isinstance(found, list):
            names = [x for x in found if isinstance(x, str) and 0 < len(x) <= 100]
            if names:
                return names
    return list(DEFAULT_REQUIRED_CI)


ACTIVE = {"profile": None}   # the profile of the running dispatch (set by cmd_dispatch), for required_ci


def _run_file(run):
    return str(run.get("path") or "").split("@")[0].rsplit("/", 1)[-1].lower()


def ci_green(repo, sha, required=None, config=None):
    """(ok, bad, pending). FAIL CLOSED: green only when the REQUIRED workflows (required_ci) all have a completed successful run on that commit, none of the runs read is failed /
    timed out / startup failure / action_required (waiting for an approval), nothing is still running and the list of runs is complete. A list GitHub says is longer than what
    was read (more than CI_PAGES pages) is not green: `bad` then says so."""
    owner = toolconfig.github_owner()
    runs, total, truncated = [], None, False
    for page in range(1, CI_PAGES + 1):
        data = ghj("api", f"repos/{owner}/{repo}/actions/runs?head_sha={sha}&event=push&per_page=100&page={page}") or {}
        chunk = data.get("workflow_runs") or []
        runs += chunk
        if isinstance(data.get("total_count"), int):
            total = data["total_count"]
        if len(chunk) < 100 and (total is None or len(runs) >= total):
            break
    else:
        truncated = True
    if total is not None and len(runs) < total:
        truncated = True
    latest = {}
    for run in runs:   # one run per workflow file: the most recent one counts (a re-run keeps its id)
        key = _run_file(run) or str(run.get("name") or "").lower()
        if key not in latest or int(run.get("id") or 0) > int(latest[key].get("id") or 0):
            latest[key] = run
    done = [r for r in latest.values() if r.get("status") == "completed"]
    pending = [r for r in latest.values() if r.get("status") != "completed"]
    bad = [str(r.get("name") or _run_file(r)) for r in done if r.get("conclusion") in BAD_CONCLUSIONS]
    wanted = [w.lower() for w in (required or required_ci(repo, config, ACTIVE["profile"]))]
    missing = [w for w in wanted if not any(w in (key, str(r.get("name") or "").lower()) and r.get("status") == "completed" and r.get("conclusion") == "success"
                                            for key, r in latest.items())]
    still_running = [w for w in missing if any(w in (key, str(r.get("name") or "").lower()) and r.get("status") != "completed" for key, r in latest.items())]
    absent = [w for w in missing if w not in still_running and not any(w in (key, str(r.get("name") or "").lower()) for key, r in latest.items())]
    extra_bad = ([t("gd.ci_incomplete")] if truncated else []) + [t("gd.ci_required_missing", workflow=w) for w in absent]
    ok = not bad and not pending and not missing and not truncated
    return ok, bad + extra_bad, len(pending)


def pick(only, ecosystem=None, profile=None):
    if profile:
        return profile_names(profile)
    names = list(only) if only else list(TARGETS)
    unknown = [n for n in names if n not in TARGETS]
    if unknown:
        sys.exit(t("gd.unknown_targets", names=", ".join(unknown)) + "\n" + t("gd.known", names=", ".join(TARGETS)))
    if ecosystem:
        names = [n for n in names if ecosystem_of(repo_of(n)) == ecosystem]
        if not names:
            sys.exit(t("gd.no_targets_external", eco=ecosystem) if toolconfig.is_external(ecosystem) else t("gd.no_targets", eco=ecosystem))
    return names


def load_profiles(path=PROFILES_FILE):
    """profiles.json: {"min_rate_remaining", "canary_wait_seconds", "profiles": {name: {"description", "workflows"|"names", "ecosystems", "canary"}}}.
    A missing or broken file gives no profiles (the rest of the batch tool is not affected)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"profiles": {}}
    return data if isinstance(data, dict) and isinstance(data.get("profiles"), dict) else {"profiles": {}}


def validate_profiles(data, targets=None):
    """Problems of a profiles catalogue (empty = valid): every selector must be known and every profile must select something."""
    targets = TARGETS if targets is None else targets
    problems = []
    for name, p in (data.get("profiles") or {}).items():
        if not isinstance(p, dict):
            problems.append(t("val.profile_object", name=name))
            continue
        for key in sorted(set(p) - {"description", "workflows", "names", "ecosystems", "canary"}):
            problems.append(t("val.profile_unknown_key", name=name, key=key))
        for w in p.get("workflows", []):
            if w not in BUILD_WORKFLOWS:
                problems.append(t("val.profile_workflow", name=name, item=repr(w)))
        for n in p.get("names", []):
            if n not in targets:
                problems.append(t("val.profile_target", name=name, item=repr(n)))
        for e in p.get("ecosystems", []):
            if e not in ECOSYSTEMS:
                problems.append(t("val.profile_ecosystem", name=name, item=repr(e)))
        if not (p.get("workflows") or p.get("names")):
            problems.append(t("val.profile_empty", name=name))
        if "canary" in p and not isinstance(p["canary"], bool):
            problems.append(t("val.profile_canary", name=name))
    return problems


def profile_names(profile, data=None, targets=None):
    """Target names a profile selects, ordered by ecosystem (armor, urtc, hydra) and name: the FIRST one is the canary."""
    data = load_profiles() if data is None else data
    targets = TARGETS if targets is None else targets
    p = (data.get("profiles") or {}).get(profile)
    if p is None:
        sys.exit(t("gd.unknown_profile", profile=profile, known=', '.join(sorted(data.get('profiles') or {})) or t("gd.no_profiles")))
    ecos = p.get("ecosystems") or [e for e in ECOSYSTEMS if not toolconfig.is_external(e)]
    wanted = set(p.get("names") or [])
    names = [n for n, t in targets.items() if (n in wanted or (not wanted and t["workflow"] in set(p.get("workflows") or [])))
             and ecosystem_of(t.get("repo", n)) in ecos]
    order = {e: i for i, e in enumerate(ECOSYSTEMS)}
    return sorted(names, key=lambda n: (order.get(ecosystem_of(targets[n].get("repo", n)), 9), ":" in n, n))


def rate_remaining():
    """REST allowance left, from `gh api rate_limit` (that call does not count against the allowance). None when it cannot be read."""
    try:
        return int(ghj("api", "rate_limit")["resources"]["core"]["remaining"])
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
        return None


def quota_gate(minimum, remaining_fn=None):
    """(ok, text). Fails CLOSED: an allowance that cannot be read blocks the dispatch. minimum 0 switches the gate off."""
    if minimum <= 0:
        return True, ""
    left = (remaining_fn or rate_remaining)()
    if left is None:
        return False, t("gd.quota_unreadable")
    if left < minimum:
        return False, t("gd.quota_low", left=left, minimum=minimum)
    return True, t("gd.quota_ok", left=left)


def wait_canary(repo, run_id, timeout=CANARY_WAIT_SECONDS, state_fn=None, sleep_fn=None, clock=None):
    """Polls the run of the canary until it finishes. Returns its conclusion, or 'timeout'. Polls every 30 s (the allowance is shared)."""
    state_fn, sleep_fn, clock = state_fn or run_state, sleep_fn or time.sleep, clock or time.time
    end = clock() + timeout
    while clock() < end:
        status, conclusion, _url, _bad = state_fn(repo, run_id)
        if status == "completed":
            return conclusion
        sleep_fn(30)
    return "timeout"


def run_with_canary(names, real, go, canary=True, wait_fn=None, **fns):
    """The first target goes alone; the rest only if its build finished green. Returns (batch, note). `fns` are run_batch's *_fn arguments."""
    if not canary or not go or len(names) < 2:
        return run_batch(names, real, go, **fns), ""
    batch = run_batch(names[:1], real, go, **fns)
    info = batch["targets"].get(names[0]) or {}
    if not info.get("run"):
        return batch, t("gd.canary_not_started", name=names[0], why=info.get('skipped') or info.get('failed') or t("gd.no_run_found"))
    conclusion = (wait_fn or wait_canary)(repo_of(names[0]), info["run"])
    if conclusion != "success":
        return batch, t("gd.canary_finished", name=names[0], conclusion=conclusion, n=len(names) - 1)
    rest = run_batch(names[1:], real, go, **fns)
    batch["targets"].update(rest["targets"])
    return batch, ""


def preflight(names, workflows=True):
    """Problems that would break a batch halfway: a signing tool that is not on disk, a clone without the workflow file. Fail early, in clear."""
    problems = []
    for name in names:
        target = TARGETS[name]
        path = tool_path(target["tool"])
        if path is None:
            problems.append(t("gd.tool_outside", name=name, tool=target["tool"], dir=TOOLS_DIR))
        elif not path.is_file():
            problems.append(t("gd.tool_missing", name=name, tool=target['tool'], dir=TOOLS_DIR))
        if workflows:
            clone = ROOT / repo_of(name)
            if clone.is_dir() and not (clone / ".github" / "workflows" / target["workflow"]).is_file():
                problems.append(t("gd.workflow_missing", name=name, repo=repo_of(name), workflow=target['workflow']))
    return problems


def candidate_target(repo, workflow, override=None):
    """The target that the CONVENTION gives to (repo, workflow), updated with `override` (the targets.json entry, if any). None when the convention
    knows no signing tool for the repository (EH3D, other) or the workflow is not a known build workflow."""
    if workflow not in BUILD_WORKFLOWS:
        return None
    eco = next((item for item in toolconfig.ecosystems().values() if repo.startswith(tuple(item["prefixes"])) and not item["external"]), None)
    tool = eco["tool"] if eco else ""
    if not tool:
        return None
    target = {"workflow": workflow, "tool": tool, "extra": []}
    if eco["firmware_tool"] and workflow == "firmware-build.yml":
        target.update({"tool": eco["firmware_tool"], "extra": list(eco["firmware_extra"])})
    target.update({k: v for k, v in (override or {}).items() if k != "repo"})
    return target


def tool_mentions(repo, tool, tools_dir=None):
    """Advisory: does the signing tool's source name the repository at all? (False = it probably does not support it yet; None = tool not on disk)."""
    try:
        text = (Path(tools_dir or TOOLS_DIR) / tool).read_text(encoding="utf-8", errors="replace")
        return re.search(r"(?<![A-Za-z0-9-])" + re.escape(repo) + r"(?![A-Za-z0-9-])", text) is not None
    except OSError:
        return None


def candidate_name(repo, workflow, targets=None):
    """The catalogue name for a build: the repository itself, or REPO:part (part = the workflow's prefix) when the repository already has another target."""
    targets = TARGETS if targets is None else targets
    if repo not in targets:
        return repo
    return f"{repo}:{workflow.replace('-build.yml', '')}"


def uncovered_builds(root=None, targets=None):
    """[(clone name, workflow file)] of every known *-build.yml in a local clone that no target covers. Coverage is by (repository, workflow)."""
    root = ROOT if root is None else Path(root)
    targets = TARGETS if targets is None else targets
    covered = {(t.get("repo", n), t.get("workflow")) for n, t in targets.items()}
    if targets is TARGETS:
        covered |= {(t.get("repo", n), t.get("workflow")) for n, t in BUILD_ONLY.items()}
    out = []
    for clone in sorted(root.iterdir()) if root.is_dir() else []:
        workflows = clone / ".github" / "workflows"
        if not (clone / ".git").exists() or not workflows.is_dir():
            continue
        out += [(clone.name, w) for w in sorted(x.name for x in workflows.glob("*-build.yml") if x.name in BUILD_WORKFLOWS) if (clone.name, w) not in covered]
    return out


def hygiene():
    """(targets with a problem, repositories with a build workflow that no target covers, EH3D ones, repositories whose origin/HEAD is not main)."""
    broken = validate_targets(TARGETS) + preflight(list(TARGETS))
    uncovered, eh3d, odd_branch = [], [], []
    grouped = {}
    for repo, workflow in uncovered_builds():
        grouped.setdefault(repo, []).append(workflow)
    for repo, builds in grouped.items():
        (uncovered if toolconfig.is_internal(repo) else eh3d).append(f"{repo}: {', '.join(builds)}")
    for clone in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        workflows = clone / ".github" / "workflows"
        if not (clone / ".git").exists() or not workflows.is_dir():
            continue
        head = subprocess.run(["git", "-C", str(clone), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], capture_output=True, text=True).stdout.strip()
        if head and head != "origin/main" and toolconfig.is_internal(clone.name):
            odd_branch.append(t("gd.odd_head", name=clone.name, head=head))
    return broken, uncovered, eh3d, odd_branch


def candidate_proposals(builds=None, targets=None):
    """{name: target} that the convention proposes for the builds no target covers (only ecosystems the convention knows)."""
    targets = TARGETS if targets is None else targets
    proposals = {}
    for repo, workflow in (uncovered_builds(targets=targets) if builds is None else builds):
        target = candidate_target(repo, workflow)
        if target:
            known = {**targets, **proposals}
            name = candidate_name(repo, workflow, known)
            proposals[name] = {**target, **({"repo": repo} if ":" in name else {})}
    return proposals


def write_candidates(path=CANDIDATES_FILE):
    """Writes the PROPOSED entries (never targets.json). Returns the proposals; an empty one writes nothing."""
    proposals = candidate_proposals()
    if proposals:
        Path(path).write_text(json.dumps(proposals, indent=2) + "\n", encoding="utf-8", newline="\n")
    return proposals


def cmd_hygiene(args):
    broken, uncovered, eh3d, odd_branch = hygiene()
    if getattr(args, "write_candidates", False):
        proposals = write_candidates()
        print(t("gd.proposed", n=len(proposals)) + (t("gd.proposed_written", file=CANDIDATES_FILE.name) if proposals else ""))
        for name, target in proposals.items():
            print("  +", name, json.dumps(target))
    print(te("gd.workspace", root=ROOT) + "\n" + te("gd.targets_count", n=len(TARGETS)))
    for title, rows in ((te("gd.h_broken"), broken), (te("gd.h_uncovered"), uncovered), (te("gd.h_external"), eh3d), (te("gd.h_branch"), odd_branch)):
        print(f"\n{title}: {len(rows)}")
        for row in rows:
            print("  -", row)
    return 1 if (broken or uncovered or odd_branch) else 0


def plan_rows(names, head=None):
    """One dict per target for `plan` (human and --json). `head` = function repo -> (sha, problem); default: the local clone."""
    head = head or local_head
    rows = []
    for name in names:
        target = TARGETS[name]
        sha, why = head(repo_of(name))
        rows.append({"name": name, "repo": repo_of(name), "ecosystem": ecosystem_of(repo_of(name)), "workflow": target["workflow"], "tool": target["tool"],
                     "main_sha": sha, "clone_problem": why or ""})
    return rows


def orphan_rows(builds=None, head=None, green=None, targets=None):
    """Signature orphans: a known *-build.yml of a repository of the three ecosystems whose CI is green on main and that has NO entry in targets.json.
    `head(repo)` -> (sha, problem) and `green(repo, sha)` -> (ok, bad, pending) are the functions the batch uses (the tests pass fixed ones)."""
    head, green = head or local_head, green or ci_green
    rows = []
    for repo, workflow in (uncovered_builds(targets=targets) if builds is None else builds):
        if not toolconfig.is_internal(repo):
            continue
        try:
            sha, why = head(repo)
            ok, bad, pending = green(repo, sha) if sha else (False, [], 0)
        except (RuntimeError, OSError, subprocess.SubprocessError) as error:
            sha, why, ok, bad, pending = None, str(error)[:120], False, [], 0
        rows.append({"repo": repo, "workflow": workflow, "main_sha": sha, "ci_green": bool(ok),
                     "ci_note": why or ("" if ok else t("gd.ci_note", bad=bad or t("gd.none_word"), pending=pending)),
                     "proposed_name": candidate_name(repo, workflow, targets), "proposed": (proposal := candidate_target(repo, workflow)),
                     "tool_mentions_repo": tool_mentions(repo, proposal["tool"]) if proposal else None})
    return rows


def profile_arg(args):
    value = getattr(args, "profile", None)
    return value if isinstance(value, str) and value else None


def cmd_plan(args):
    names = pick(args.only, getattr(args, "ecosystem", None), profile_arg(args))
    rows = plan_rows(names)
    problems = preflight(names)
    whole = not args.only and not getattr(args, "ecosystem", None) and not profile_arg(args)
    orphans = orphan_rows() if whole else []   # a whole-catalogue plan always shows what the batch does NOT know yet
    if getattr(args, "json", False):
        print(json.dumps({"targets": rows, "orphans": orphans, "build_only": BUILD_ONLY, "preflight": problems}, indent=2, ensure_ascii=False))
        return 2 if problems else 0
    for r in rows:
        print(f"{r['name']:30} {r['workflow']:24} {r['tool']:26} main={r['main_sha'] and r['main_sha'][:7]} {r['clone_problem']}")
    if whole:
        print("\n" + te("gd.orphans", n=len(orphans)))
        for o in orphans:
            tool = o["proposed"]["tool"] if o["proposed"] else t("gd.no_tool")
            ci = te("gd.ci_green") if o['ci_green'] else te("gd.ci_not_green", note=o['ci_note'])
            print(f"  - {o['repo']}: {o['workflow']}  CI {ci}  -> " + te("gd.would_be", name=o['proposed_name'], tool=tool)
                  + ("  " + t("gd.tool_no_repo") if o["tool_mentions_repo"] is False else ""))
        if not orphans:
            print("  " + te("gd.none"))
        print("\n" + te("gd.build_only", n=len(BUILD_ONLY)))
        for name, target in BUILD_ONLY.items():
            print(f"  - {name}: {target['workflow']} - {target['reason']}")
        if not BUILD_ONLY:
            print("  " + te("gd.none"))
    if problems:
        print("\n" + te("gd.preflight_problems"))
        for row in problems:
            print("  -", row)
        return 2
    return 0


def fire(name, repo, sha, real):
    """Fires the workflow of one target and finds the run it created. Raises RuntimeError when the API refuses the dispatch."""
    target = TARGETS[name]
    before = time.time()
    try:
        args = dispatch_args(target["workflow"], repo, real, target["extra"])
    except ValueError as error:
        raise RuntimeError(f"extra of {name} refused: {error}"[:200]) from None
    gh(*args)
    run_id, matched = None, False
    for _ in range(10):  # the run appears a moment later
        time.sleep(3)
        runs = ghj("run", "list", "-R", f"{toolconfig.github_owner()}/{repo}", "--workflow", target["workflow"], "--event", "workflow_dispatch", "-L", "5", "--json", "databaseId,createdAt,headSha,event")
        fresh = [r for r in runs or [] if r.get("event") == "workflow_dispatch"
                 and datetime.strptime(r["createdAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() >= before - 5]
        exact = [r for r in fresh if r.get("headSha") == sha]   # the run must be on the commit we checked, not another concurrent one
        if exact or fresh:
            chosen = (exact or fresh)[0]
            run_id, matched = chosen["databaseId"], bool(exact)
            break
    if run_id and not matched:
        print(te("gd.warn_other_sha", name=name, sha=sha[:7]))
    print(te("gd.dispatched", name=name, run=run_id))
    return {"workflow": target["workflow"], "run": run_id, "sha": sha, "event": "workflow_dispatch", "sha_matched": matched,
            "dispatched_at": datetime.fromtimestamp(before, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def run_batch(names, real, go, fire_fn=None, head_fn=None, green_fn=None, sleep_fn=None):
    """The dispatch loop. Returns the batch dict. A dispatch the API refuses is marked ('retry') and retried once at the end;
    the rest of the batch is never aborted. The *_fn arguments are for the tests."""
    fire_fn, head_fn, green_fn, sleep_fn = fire_fn or fire, head_fn or local_head, green_fn or ci_green, sleep_fn or time.sleep
    batch = {"created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "dry_run": not real, "targets": {}}
    retry = []
    for name in names:
        target = TARGETS[name]
        repo = repo_of(name)
        sha, why = head_fn(repo)
        if why:
            print(te("gd.skip", name=name, why=why))
            batch["targets"][name] = {"skipped": why}
            continue
        green, bad, pending = green_fn(repo, sha)
        if not green:
            reason = t("gd.ci_not_green_on", sha=sha[:7], bad=bad or t("gd.none_word"), pending=pending)
            print(te("gd.skip", name=name, why=reason))
            batch["targets"][name] = {"skipped": reason}
            continue
        if not go:
            print(te("gd.would_dispatch", name=name, workflow=target['workflow'], sha=sha[:7], dry=not real))
            continue
        try:
            batch["targets"][name] = fire_fn(name, repo, sha, real)
        except (RuntimeError, OSError, subprocess.SubprocessError) as error:
            print(te("gd.retry_later", name=name, error=str(error)[:160]))
            batch["targets"][name] = {"retry": True, "error": str(error)[:200], "sha": sha}
            retry.append((name, repo, sha))
    if retry:
        sleep_fn(10)
        print(t("gd.retrying", n=len(retry)))
        for name, repo, sha in retry:
            try:
                batch["targets"][name] = {**fire_fn(name, repo, sha, real), "retried": True}
            except (RuntimeError, OSError, subprocess.SubprocessError) as error:
                print(te("gd.failed", name=name, error=str(error)[:160]))
                batch["targets"][name] = {"failed": str(error)[:200], "sha": sha, "retried": True}
    return batch


def cmd_dispatch(args):
    profile = profile_arg(args)
    ACTIVE["profile"] = profile
    names = pick(args.only, getattr(args, "ecosystem", None), profile)
    problems = preflight(names)
    if problems and args.go:
        print(t("gd.nothing_fired_fix"))
        for row in problems:
            print("  -", row)
        return 2
    data = load_profiles()
    minimum = args.min_rate if getattr(args, "min_rate", None) is not None else int(data.get("min_rate_remaining", DEFAULT_MIN_RATE))
    if args.go:
        ok, text = quota_gate(minimum)
        if not ok:
            print(t("gd.nothing_fired", why=text))
            return 3
    canary = bool(profile and (data["profiles"][profile].get("canary", True)) and not getattr(args, "no_canary", False))
    batch, note = run_with_canary(names, args.real, args.go, canary=canary, wait_fn=(lambda repo, run: wait_canary(repo, run, int(data.get("canary_wait_seconds", CANARY_WAIT_SECONDS)))))
    if note:
        print(te("gd.canary", note=note))
        batch["canary_note"] = note
    if args.go:
        BATCH_DIR.mkdir(parents=True, exist_ok=True)
        path = BATCH_DIR / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(batch, indent=2), encoding="utf-8")
        print(t("gd.batch_recorded", path=path))
        failed = [n for n, i in batch["targets"].items() if "failed" in i]
        if failed:
            print(te("gd.dispatch_failed_after", names=", ".join(failed)))
            return 1
        if note:
            return 1


def last_batch():
    files = sorted([*(BATCH_DIR.glob("batch_*.json") if BATCH_DIR.exists() else []), *(LEGACY_BATCH_DIR.glob("lote_*.json") if LEGACY_BATCH_DIR.exists() else [])],
                   key=lambda p: p.stem.split("_", 1)[-1])
    if not files:
        sys.exit(t("gd.no_batch"))
    return files[-1], json.loads(files[-1].read_text(encoding="utf-8"))


def run_state(name, run_id):
    data = ghj("api", f"repos/{toolconfig.github_owner()}/{name}/actions/runs/{run_id}")
    jobs = ghj("api", f"repos/{toolconfig.github_owner()}/{name}/actions/runs/{run_id}/jobs?per_page=30") or {}
    bad = [j["name"] for j in jobs.get("jobs", []) if j.get("conclusion") in ("failure", "timed_out", "cancelled")]
    return data["status"], data.get("conclusion"), data["html_url"], bad


def cmd_status(args):
    path, batch = last_batch()
    print(t("gd.batch_head", name=path.name, dry=batch["dry_run"]))
    counts = {"ok": 0, "running": 0, "failed": 0, "skipped": 0}
    for name, info in batch["targets"].items():
        if "skipped" in info:
            counts["skipped"] += 1
            print("  " + te("gd.st_skipped", name=name, why=info['skipped']))
            continue
        if "failed" in info or info.get("retry"):
            counts["failed"] += 1
            print("  " + te("gd.st_dispatch_failed", name=name, why=info.get('failed') or info.get('error')))
            continue
        if not info.get("run"):
            counts["failed"] += 1
            print("  " + te("gd.st_no_run", name=name))
            continue
        status, conclusion, url, bad = run_state(repo_of(name), info["run"])
        key = "running" if status != "completed" else ("ok" if conclusion == "success" else "failed")
        counts[key] += 1
        print(f"  {te('gd.sl_' + key):8} {name:30} {status}/{conclusion} {(te('gd.failed_jobs') + ', '.join(bad)) if bad else ''} {url}")
    print(te("gd.summary"), counts)


def run_sha(repo, run_id):
    """The commit a run was built on, read from GitHub (used to re-check a batch recorded before the SHA was matched)."""
    data = ghj("api", f"repos/{toolconfig.github_owner()}/{repo}/actions/runs/{run_id}") or {}
    return str(data.get("head_sha") or "")


def finalize_rows(batch, state_fn=None, legacy=False, sha_fn=None):
    """One dict per target of the batch with a run: state ready|not_ready, the run, the url and the exact command. `state_fn(repo, run)` -> (status, conclusion, url, bad).

    STRICT by default: a run is offered for signing only when the batch RECORDS that it was built on the commit that was checked (`sha_matched` is true). A batch without that
    field (written before the check existed) is `not_ready` with reason `needs_review`. With `legacy=True` such a batch is accepted only after its run is read again from GitHub
    (`sha_fn(repo, run)`) and its commit equals the one recorded in the batch; then the row says `legacy: true` so the caller can warn and ask again."""
    state_fn = state_fn or run_state
    sha_fn = sha_fn or run_sha
    rows = []
    for name, info in sorted(batch["targets"].items(), key=lambda item: ":" in item[0]):   # parts after the packages they ride on
        if "skipped" in info or "failed" in info or info.get("retry") or not info.get("run") or name not in TARGETS:
            continue
        status, conclusion, url, bad = state_fn(repo_of(name), info["run"])
        row = {"name": name, "repo": repo_of(name), "run": info["run"], "url": url, "status": status, "conclusion": conclusion}
        matched = info.get("sha_matched")
        if matched is False:   # the run found was on another commit than the one checked: never offered for signing (fire() records it)
            row.update({"state": "not_ready", "failed_jobs": [], "reason": "sha_mismatch", "sha": str(info.get("sha", ""))[:7]})
        elif matched is not True and not (legacy and _recheck(name, info, sha_fn)):
            row.update({"state": "not_ready", "failed_jobs": [], "reason": "needs_review", "sha": str(info.get("sha", ""))[:7]})
        elif status == "completed" and conclusion == "success":
            try:
                argv = finalize_command(name, info["run"])
            except ValueError:
                row.update({"state": "not_ready", "failed_jobs": [], "reason": "bad_tool"})
            else:
                row.update({"state": "ready", "argv": argv, "command": command_text(argv)})
                if matched is not True:
                    row["legacy"] = True
        else:
            row.update({"state": "not_ready", "failed_jobs": bad})
        rows.append(row)
    return rows


def _recheck(name, info, sha_fn):
    """True when the run of a batch without `sha_matched` was built on exactly the commit the batch recorded (read now from GitHub). Anything unreadable is False."""
    expected = str(info.get("sha") or "")
    if not SHA_RE.match(expected):
        return False
    try:
        return sha_fn(repo_of(name), info["run"]) == expected
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError):
        return False


def mark_batch(path, batch, name, **fields):
    """Records on the batch file what the local tools did (signed_at / published_at); atomic, never raises."""
    try:
        batch["targets"][name].update(fields)
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(json.dumps(batch, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as error:
        print(t("gd.warn_record", name=name, file=Path(path).name, error=error))


def cmd_finalize(args):
    path, batch = last_batch()
    problems = preflight([n for n, i in batch["targets"].items() if "skipped" not in i and n in TARGETS], workflows=False)
    if problems:
        print(t("gd.cannot_finalize"))
        for row in problems:
            print("  -", row)
        return 2
    legacy = bool(getattr(args, "accept_legacy", False))
    rows = finalize_rows(batch, legacy=legacy)
    if getattr(args, "json", False):
        print(json.dumps({"batch": path.name, "dry_run": batch.get("dry_run"), "targets": rows}, indent=2, ensure_ascii=False))
        return 0
    ready = [r for r in rows if r["state"] == "ready"]
    print(t("gd.finalize_head", name=path.name, ready=len(ready), not_ready=len(rows) - len(ready)))
    for r in rows:
        if r["state"] == "not_ready":
            print(te("gd.not_ready", name=r['name'], status=r['status'], conclusion=r['conclusion'], url=r['url']))
            if r.get("reason") == "sha_mismatch":
                print("    " + t("gd.sha_mismatch", name=r['name'], run=r['run'], sha=r.get("sha", "")))
    for r in ready:
        print(te("gd.ready", name=r['name'], run=r['run']) + f"\n    $ {r['command']}")
        if args.execute and input(t("gd.ask_run", name=r['name'])).strip().lower() == "y":
            if subprocess.run(r["argv"]).returncode == 0:
                stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                mark_batch(path, batch, r["name"], signed_at=stamp, published_at=stamp)
                port = monitor_link.notify_refresh([r["repo"]])   # the running monitor refreshes just this repository and rewrites ci_red.json
                if port:
                    print("    " + t("gd.monitor_told", port=port, repo=r['repo']))
    if ready and not args.execute:
        print("\n" + t("gd.nothing_run"))
    return 0


def main():
    i18n.cli_language()
    platform_compat.console_utf8()
    workspace.workspace_root()   # clear message here if the workspace cannot be found (the import itself never stops)
    parser = argparse.ArgumentParser(description=t("gd.description"), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lang", metavar="CODE", help=t("cli.help_lang"))
    parser.add_argument("--version", action="version", version=f"github_actions_monitor {TOOL_VERSION}\n{i18n.about_line()}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "dispatch"):
        p = sub.add_parser(name)
        group = p.add_mutually_exclusive_group()
        group.add_argument("--only", nargs="*")
        group.add_argument("--ecosystem", choices=ECOSYSTEMS, help=t("gd.help_ecosystem"))
        group.add_argument("--profile", help=t("gd.help_profile"))
        if name == "plan":
            p.add_argument("--json", action="store_true", help=t("gd.help_plan_json"))
        if name == "dispatch":
            p.add_argument("--go", action="store_true", help=t("gd.help_go"))
            p.add_argument("--real", action="store_true", help=t("gd.help_real"))
            p.add_argument("--min-rate", type=int, default=None, help=t("gd.help_min_rate"))
            p.add_argument("--no-canary", action="store_true", help=t("gd.help_no_canary"))
    sub.add_parser("status")
    h = sub.add_parser("hygiene", help=t("gd.help_hygiene"))
    h.add_argument("--write-candidates", action="store_true", help=t("gd.help_write_candidates"))
    f = sub.add_parser("finalize")
    f.add_argument("--execute", action="store_true", help=t("gd.help_execute"))
    f.add_argument("--json", action="store_true", help=t("gd.help_finalize_json"))
    f.add_argument("--accept-legacy", action="store_true", help=t("gd.help_accept_legacy"))
    args = parser.parse_args()
    return {"plan": cmd_plan, "dispatch": cmd_dispatch, "status": cmd_status, "finalize": cmd_finalize, "hygiene": cmd_hygiene}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
