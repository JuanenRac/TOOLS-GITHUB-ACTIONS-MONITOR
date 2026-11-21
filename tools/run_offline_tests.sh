#!/bin/sh
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# Runs the unit tests with the network CUT: a new network namespace that has only the loopback (the tests start servers on 127.0.0.1), as the user who called it.
# A test that needs the internet fails here, and that is the point: the monitor has an offline mode and its tests must not depend on a service outside the machine.
#   sudo sh tools/run_offline_tests.sh [unittest arguments]       (Linux; needs unshare, ip and setpriv, which any runner of GitHub has)
set -eu
if [ "$(id -u)" != 0 ]; then
  exec sudo env "PATH=$PATH" "HOME=$HOME" sh "$0" "$@"
fi
user_id="${SUDO_UID:-0}"; group_id="${SUDO_GID:-0}"
exec unshare --net -- sh -c '
  ip link set lo up
  u="$1"; g="$2"; shift 2
  if setpriv --reuid="$u" --regid="$g" --clear-groups python -c "import socket; socket.create_connection((\"1.1.1.1\", 53), timeout=3)" 2>/dev/null; then
    echo "the network is still reachable: the namespace did not cut it" >&2; exit 3
  fi
  exec setpriv --reuid="$u" --regid="$g" --clear-groups python -m unittest "$@"
' sh "$user_id" "$group_id" "$@"
