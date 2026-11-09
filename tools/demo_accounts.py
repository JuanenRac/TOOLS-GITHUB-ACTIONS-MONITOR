#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/demo_accounts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The complete edition with SEVERAL accounts and invented data, for the pictures of the documentation.

    python tools/demo_accounts.py [PORT]      # default 18766; runs until it is stopped

It starts the real supervisor (accounts_supervisor.py) on 127.0.0.1 with three invented accounts in a temporary folder, and every account is the demo monitor of tools/demo_monitor.py, so nothing
is read from GitHub and nothing is written outside the temporary folder. The page, the switcher, the page of all accounts and the views are the real ones.
"""
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "monitor"
sys.path.insert(0, str(ROOT))
NAMES = (("personal", "demo-owner"), ("org-acme", "acme-demo"), ("client-labs", "labs-demo"))


def main():
    port = int(next((a for a in sys.argv[1:] if a.isdigit()), "18766"))
    folder = Path(tempfile.mkdtemp(prefix="ghamon_demo_accounts_"))
    import os
    os.environ["MONITOR_ACCOUNTS_DIR"] = str(folder / "accounts")
    import accounts
    import accounts_supervisor as supervisor
    for account_id, owner in NAMES:
        accounts.create_account(account_id, owner)
    (folder / "accounts" / accounts.GLOBAL_NAME).write_text('{"default_account": "personal", "enabled_accounts": "all"}', encoding="utf-8")
    demo = Path(__file__).resolve().parent / "demo_monitor.py"
    sup = supervisor.Supervisor(command_for=lambda account_id, child_port: [sys.executable, "-I", str(demo), str(child_port)])
    sup.sync()
    for _ in range(80):
        sup.check()
        if all(c.health is not None for c in sup.children.values()):
            break
        time.sleep(0.5)
    sup.run()
    supervisor.SUPERVISOR["obj"] = sup
    server = supervisor.ThreadingHTTPServer(("127.0.0.1", port), supervisor.Handler)
    print("demo accounts on", port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sup.stop()


if __name__ == "__main__":
    main()
