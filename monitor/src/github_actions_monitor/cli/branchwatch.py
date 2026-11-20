# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`watch branch`: watches the workflows of the commit you just pushed, from the folder you are in. `git push && monitor_cli.py watch branch` waits until the runs of that commit finish and ends
with 0 when they all passed and 1 when one failed (or when they did not finish in time).

What it does: asks git (a fixed list of arguments, no shell, no window) which repository (`origin`), branch and commit the current folder is on, then reads the runs the monitor already holds
(`/api/data`, never GitHub, so it spends no allowance) and keeps the ones of that repository, branch and commit. `--repo NAME` and `--branch NAME` replace what git says; with `--branch` and no
commit it follows the newest run of each workflow of that branch. It never prints the address of the remote (it may hold a token), only owner/name. Standard library only."""
import re
import subprocess
import sys

REMOTE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://(?:[^@/\s]+@)?[^/:\s]+(?::[0-9]{1,5})?/|[^@/\s]+@[^:/\s]+:)([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?\Z")
GOOD = ("success", "skipped", "neutral")
BAD = ("failure", "timed_out", "cancelled", "startup_failure", "action_required", "stale")
STATES = ("waiting", "running", "passed", "failed")


def parse_remote(url):
    """(owner, name) of the address of a remote (https, ssh:// or the scp form git@host:owner/name), else None. The address itself is never kept."""
    found = REMOTE.match(str(url or "").strip())
    return (found.group(1), found.group(2)) if found else None


def _git(args, cwd, runner=None):
    """The one-line answer of a git command, '' when it fails. A fixed list of arguments, never a shell, never a window."""
    runner = runner or subprocess.run
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        done = runner(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, creationflags=flags, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (done.stdout or "").strip().splitlines()[0].strip() if done.returncode == 0 and (done.stdout or "").strip() else ""


def git_context(cwd=None, runner=None):
    """{"owner", "name", "branch", "sha"} of the folder (empty text for what git does not say). Never raises."""
    remote = parse_remote(_git(["remote", "get-url", "origin"], cwd, runner))
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd, runner)
    sha = _git(["rev-parse", "HEAD"], cwd, runner)
    return {"owner": remote[0] if remote else "", "name": remote[1] if remote else "", "branch": "" if branch == "HEAD" else branch, "sha": sha if re.fullmatch(r"[0-9a-f]{7,64}", sha) else ""}


def valid_branch(text):
    return bool(re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", str(text or ""))) and ".." not in str(text)


def valid_repo(text):
    return bool(re.fullmatch(r"([A-Za-z0-9._-]{1,100}/)?[A-Za-z0-9._-]{1,100}", str(text or "")))


def _same_repo(run_repo, owner, name):
    run_repo = str(run_repo or "").lower()
    return run_repo == (name or "").lower() or bool(owner) and run_repo == (owner + "/" + name).lower()


def evaluate(runs, owner, name, branch, sha):
    """The state of the runs of a repository and branch (of one commit when `sha` is given, else the newest run of each workflow): {"state", "runs": [...], "done", "passed", "running", "failed"}.
    waiting = no run yet; running = one is not finished; passed = all finished well; failed = one finished badly."""
    short = (sha or "")[:7]
    mine = [r for r in (runs or []) if isinstance(r, dict) and _same_repo(r.get("repo"), owner, name) and r.get("branch") == branch and (not short or str(r.get("sha") or "")[:7] == short)]
    newest = {}
    for run in mine:
        key = run.get("name") or run.get("path") or str(run.get("id"))
        if key not in newest or (run.get("number") or 0, str(run.get("started") or "")) >= (newest[key].get("number") or 0, str(newest[key].get("started") or "")):
            newest[key] = run
    rows = [{"workflow": str(k), "status": str(r.get("status") or ""), "conclusion": r.get("conclusion") or None, "seconds": r.get("seconds")} for k, r in sorted(newest.items())]
    running = sum(1 for r in rows if r["status"] != "completed")
    failed = sum(1 for r in rows if r["status"] == "completed" and r["conclusion"] not in GOOD)
    passed = sum(1 for r in rows if r["status"] == "completed" and r["conclusion"] in GOOD)
    state = "waiting" if not rows else "running" if running else "failed" if failed else "passed"
    return {"state": state, "runs": rows, "done": state in ("passed", "failed"), "passed": passed, "running": running, "failed": failed}


def exit_code(state):
    """0 when everything passed; 1 for a failure and for anything that is not finished (a single read cannot wait)."""
    return 0 if state == "passed" else 1
