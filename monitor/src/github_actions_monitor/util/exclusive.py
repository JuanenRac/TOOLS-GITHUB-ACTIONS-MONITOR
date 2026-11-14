# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One monitor for each port.

On Windows a socket that sets SO_REUSEADDR can be bound to a port another process already listens on, and the requests then fall on either of the two. The servers of the monitor therefore bind the
port for themselves alone (`ExclusiveBind`: SO_EXCLUSIVEADDRUSE on Windows; on the other systems the port of a listening socket is never shared, and SO_REUSEADDR only lets a restart skip the wait of
a closed one). And before anything starts, `monitor_on(port)` asks the port whether a monitor already answers there, so the second start says so and stops instead of looking for another port.
"""
import json
import os
import socket
import ssl
import urllib.request


class ExclusiveBind:
    """Mixin for an HTTP server: nobody else may bind the port this one binds (Windows)."""

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.allow_reuse_address = False
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def monitor_on(port, host="127.0.0.1", timeout=1.5):
    """True when a monitor answers on that port of this computer (its health route says what it is); False for a free port or for a program that is not the monitor. Sends one GET, nothing else."""
    if not (isinstance(port, int) and 0 < port < 65536):
        return False
    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE      # only to read the health route of a monitor with a certificate of its own: no data is sent or trusted
    for scheme in ("http", "https"):
        try:
            with urllib.request.urlopen(f"{scheme}://{host}:{port}/api/health", timeout=timeout, context=context if scheme == "https" else None) as answer:
                body = json.loads(answer.read(4096).decode("utf-8", "replace"))
        except Exception:       # noqa: BLE001 - not listening, not HTTP, not JSON: not a monitor
            continue
        if isinstance(body, dict) and "version" in body and "ok" in body:
            return True
    return False
