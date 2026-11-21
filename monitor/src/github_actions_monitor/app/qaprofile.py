# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The profile `qa`: a second monitor for tests that must never disturb the real one.

`--profile qa` (or `MONITOR_PROFILE=qa`) starts the monitor as an observer on the same account:

  * it is always an observer (`github_actions.writer_lock`, integrations/ghactions.py): it refuses every action on GitHub, whatever the configuration says;
  * it listens on another port: the one the editions would use plus 100 (or minus 100 when that would pass 65535), unless `--port` is given, so it never takes the port of the real one;
  * its ETag cache is a temporary file that is deleted when it ends, so its answers never mix with the cache of the real monitor and nothing of a test stays behind.

Pure functions: the environment is given by the caller.
"""
import os
import tempfile
from pathlib import Path

ENV = "MONITOR_PROFILE"
PROFILES = ("qa",)
PORT_OFFSET = 100
HIGH = 65535


def active(env=None):
    """True when the profile is `qa` (the variable is read without caring for case or blanks)."""
    env = os.environ if env is None else env
    return str(env.get(ENV, "")).strip().lower() == "qa"


def shift_port(port):
    """The port of the profile for the port of the real monitor: +100, or -100 when that is past 65535."""
    return port + PORT_OFFSET if port + PORT_OFFSET <= HIGH else port - PORT_OFFSET


def etag_file(pid=None):
    """The temporary file of the ETag cache of this process: one for each process, in the temporary folder of the system."""
    return Path(tempfile.gettempdir()) / ("gha_monitor_qa_etag_%d.json" % (os.getpid() if pid is None else pid))


def forget(path):
    """Deletes the temporary cache (and its half-written copy); never raises."""
    for name in (Path(path), Path(str(path) + ".tmp")):
        try:
            name.unlink()
        except OSError:
            pass
