# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The processes of test_compliance_restore_tick.py (not a test module). `tick ACCOUNT CALLS` is the monitor of one account that makes one refresh cycle; `gh CALLS ...` is the double of `gh`."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

AN_HOUR_AGO = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")      # a red run that is old is not red any more
RUN = {"id": 7001, "name": "CI", "path": ".github/workflows/ci.yml", "status": "completed", "conclusion": "failure", "event": "push", "head_branch": "main", "head_sha": "a" * 40, "run_number": 3,
       "run_attempt": 1, "created_at": AN_HOUR_AGO, "run_started_at": AN_HOUR_AGO, "updated_at": AN_HOUR_AGO, "html_url": "https://github.com/double-owner/demo-a/actions/runs/7001"}


def gh(calls, args):
    line = " ".join(args)
    with open(calls, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    if "/actions/runs?" in line:
        body = {"total_count": 1, "workflow_runs": [RUN]}
    elif "rate_limit" in line:
        core = {"limit": 5000, "remaining": 4999, "reset": 4102444800}
        body = {"resources": {"core": core, "graphql": core, "search": core}, "rate": core}
    elif args[:2] == ["repo", "list"]:
        body = [{"name": "demo-a", "isPrivate": False, "isArchived": False, "isFork": False, "isEmpty": False}]
    elif args[:2] in (["issue", "list"], ["release", "list"], ["pr", "list"]):
        body = []
    else:
        sys.stderr.write("HTTP 404: Not Found")
        return 1
    if "-i" in args or "--include" in args:
        sys.stdout.write("HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
    sys.stdout.write(json.dumps(body))
    return 0


def tick(account, calls):
    real = subprocess.Popen

    class Double(real):
        def __init__(self, args, *more, **kwargs):
            if isinstance(args, (list, tuple)) and args and args[0] == "gh":
                args = [sys.executable, str(Path(__file__).resolve()), "gh", calls, *args[1:]]
            super().__init__(args, *more, **kwargs)

    subprocess.Popen = Double
    from github_actions_monitor.accounts import account_child, accounts
    if not accounts.config_path(account).is_file():
        print("the restored account has no configuration")
        return 2
    folder = account_child.redirect(account)
    from github_actions_monitor.app import actions_monitor as am
    from github_actions_monitor.app import toolconfig
    am.CHILD["account"], am.CHILD["folder"] = account, str(folder)
    config = am.load_config()
    toolconfig.set_owner(config["github_owner"])
    am.LIVE_CONFIG.update(config)
    am.run_cycle(config, am.WATCH.generation)
    data = am.STATE["data"] or {}
    print(json.dumps({"owner": config["github_owner"], "repos": data.get("repos"), "runs": len(data.get("runs") or []), "failing": len(data.get("failing") or []), "errors": data.get("errors"),
                      "complete": am.STATE.get("complete") is True}))
    return 0


if __name__ == "__main__":
    sys.exit(gh(sys.argv[2], sys.argv[3:]) if sys.argv[1] == "gh" else tick(sys.argv[2], sys.argv[3]))
