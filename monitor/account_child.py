# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor of ONE account, started by the supervisor (accounts_supervisor.py) as its own process: `python account_child.py ACCOUNT_ID --port N`.

It is the same monitor as always, run with the files of one folder `accounts/<id>/`: before the monitor starts, the place of each state file is pointed at that folder, and the default
of the stores that were built with a fixed path (the cache of conditional reads, the history of analytics, the event feed, the cache of the AI) is pointed there too. Nothing else
changes, so every rule of the monitor (read only, the one-use token, the network mode) is the one it already had, per account.

The child listens on 127.0.0.1 only and never opens a browser: the supervisor is the one the person talks to. The lite edition never runs this.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))        # works also under `py -3 -I`, which does not put the folder of the script on the path

import accounts  # noqa: E402


def redirect(account_id, base=None):
    """Points every state file of the monitor at accounts/<id>/. Returns the folder. Must run BEFORE the monitor builds its stores."""
    import actions_monitor as am
    import ai_actions
    import analytics
    import etagcache
    import events
    import ghactions
    import sentinel_ai
    import settings_api
    import toolconfig
    import updatecheck
    for module in (ai_actions, ghactions, updatecheck):      # these load on demand inside the monitor: they must exist now, or their logs would stay next to the code, shared by every account
        sys.modules.setdefault(module.__name__, module)
    folder = accounts.account_dir(account_id, base)
    import sentinel_local            # the sentinel is part of the complete edition: its files are per account too
    import sentinel_collab           # and so are the files of the second one
    import alert_center              # and the silences of the alerts
    for module, attribute, relative in accounts.STATE_FILES:
        loaded = sys.modules.get(module)
        if loaded is not None and hasattr(loaded, attribute):
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            setattr(loaded, attribute, target)
    config = folder / accounts.CONFIG_NAME
    am.CONFIG_FILE = settings_api.CONFIG_FILE = toolconfig.CONFIG_FILE = config
    settings_api.BACKUP_DIR = folder / "config_backups"
    # the stores built with a fixed default path: the default is read when the function is defined, so the defaults are replaced
    for owner, name, attribute in ((etagcache.EtagCache, "__init__", "CACHE_FILE"), (analytics.Store, "__init__", "HISTORY_FILE"), (events.Feed, "__init__", None), (sentinel_ai.Store, "__init__", "CACHE_FILE"),
                                   (ai_actions.Actions, "__init__", "LOG_FILE")):
        function = getattr(owner, name)
        defaults = list(function.__defaults__ or ())
        if owner is events.Feed:
            defaults[0], defaults[1] = events.EVENTS_FILE, events.STATE_FILE
        else:
            defaults[0] = getattr(sys.modules[owner.__module__], attribute)
        function.__defaults__ = tuple(defaults)
    ai_actions.ACTIONS.log_file = Path(ai_actions.LOG_FILE)     # this one was built when the module loaded, with the old path already in it
    return folder


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("account")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)
    if not accounts.valid_id(args.account) or not accounts.config_path(args.account).is_file():
        print("unknown account")
        return 2
    folder = redirect(args.account)
    import actions_monitor as am
    sys.argv = ["actions_monitor.py", "--port", str(args.port), "--no-browser"]
    am.CHILD["account"] = args.account
    am.CHILD["folder"] = str(folder)
    return am.main()


if __name__ == "__main__":
    sys.exit(main())
