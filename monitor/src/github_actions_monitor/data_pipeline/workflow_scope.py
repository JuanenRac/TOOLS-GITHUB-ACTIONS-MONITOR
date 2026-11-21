# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Which workflows belong in the failure lists and which are only listed: reusable workflows and orphans. Pure functions: nothing is read from GitHub here.

  * `ci.reusable_out_of_rankings` (off): a workflow whose file only has `workflow_call` (and at most `workflow_dispatch`) is started by no event of its own, so it has no runs of its own and the
    runs that remain in the history of the repository (from the time the file had other triggers) say nothing about the present. With the switch on those runs leave the red list of A2 and the
    rankings of failures and of duration, and the sentinel says how many workflows were left out. It needs a scan of the workflow files (a clone or a reading through the API) that the sentinel
    already does; a repository without a scan is not touched.
  * `ci.orphan_workflows` (off): the workflows that GitHub still lists and whose file is not in the default branch any more, as an information list that is never red. It compares the list that the
    hygiene reading already makes with the workflow files of the scan; a repository with no scan, or one whose scan may be cut (60 files), is counted in `unverifiable`, not judged.
"""
import re

LISTED_MAX = 150
SCAN_CUT = 60
DIR = ".github/workflows/"


def settings(config):
    block = (config or {}).get("ci")
    block = block if isinstance(block, dict) else {}
    return {"reusable_out": block.get("reusable_out_of_rankings") is True, "orphans": block.get("orphan_workflows") is True}


def reusable_files(scans):
    """{repo: {file}}: the workflow files of the scans that only other workflows call (`callable_only`)."""
    out = {}
    for repo, scan in (scans or {}).items():
        files = {w["file"] for w in (scan or {}).get("workflows") or [] if isinstance(w, dict) and w.get("callable_only") and w.get("file")}
        if files:
            out[repo] = files
    return out


def base_name(run):
    return str(run.get("path") or "").split("@")[0].rsplit("/", 1)[-1]


def drop_runs(runs, files):
    """(kept runs, sorted names of the files that lost runs): the runs of the workflow files in `files` leave the list."""
    if not files:
        return list(runs), []
    kept, dropped = [], set()
    for run in runs:
        name = base_name(run)
        if name and name in files:
            dropped.add(name)
        else:
            kept.append(run)
    return kept, sorted(dropped)


def drop_all(runs_by_repo, reusables):
    """({repo: kept runs}, [{"repo", "workflow"}] of the workflows left out)."""
    out, left = {}, []
    for repo, runs in runs_by_repo.items():
        out[repo], names = drop_runs(runs, (reusables or {}).get(repo))
        left.extend({"repo": repo, "workflow": n} for n in names)
    return out, left


def drop_flat(runs, reusables):
    """The same over one flat list of runs that carry their `repo`."""
    if not reusables:
        return list(runs)
    return [r for r in runs if not (base_name(r) and base_name(r) in (reusables.get(r.get("repo")) or ()))]


def listed_entries(workflows):
    """What is kept of the list of workflows of GitHub for the orphan check: [[name, path], ...] without the workflows that GitHub makes for itself (`dynamic/...`), at most LISTED_MAX."""
    out = []
    for item in workflows or []:
        if isinstance(item, dict) and not str(item.get("path") or "").startswith("dynamic/"):
            out.append([re.sub(r"[\x00-\x1f]", " ", str(item.get("name") or ""))[:80], str(item.get("path") or "")[:160]])
    return out[:LISTED_MAX]


def orphans(perms, scans, enabled):
    """{"enabled", "rows": [{"repo", "workflow", "path", "reason"}], "unverifiable": n}. `reason` is `no_path` (GitHub lists it with no file) or `file_missing` (its file is not among the
    workflow files of the scan). Information only."""
    if not enabled:
        return {"enabled": False, "rows": [], "unverifiable": 0}
    rows, unverifiable = [], 0
    for repo, held in sorted((perms or {}).items()):
        listed = (held or {}).get("wf_listed")
        if not isinstance(listed, list):
            continue
        scan = (scans or {}).get(repo)
        files = {w["file"] for w in (scan or {}).get("workflows") or [] if isinstance(w, dict) and w.get("file")}
        complete = bool(scan) and len(files) < SCAN_CUT and len(listed) < LISTED_MAX
        cannot = False
        for name, path in listed:
            if not path:
                rows.append({"repo": repo, "workflow": name, "path": "", "reason": "no_path"})
            elif path.startswith(DIR):
                if complete:
                    if path.rsplit("/", 1)[-1] not in files:
                        rows.append({"repo": repo, "workflow": name, "path": path, "reason": "file_missing"})
                else:
                    cannot = True
        unverifiable += 1 if cannot else 0
    return {"enabled": True, "rows": rows[:200], "unverifiable": unverifiable}
