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
import threading
import urllib.request

REQUEST_TIMEOUT = 30        # seconds a connection may stay without sending or taking a byte (a request that is never completed must not keep a thread for ever)
MAX_CONNECTIONS = 256       # connections open at the same time on one server
MAX_PER_ADDRESS = 64        # ... and from one address (this computer and the reverse proxy it declared are not counted: they stand for many people)


class ExclusiveBind:
    """Mixin for an HTTP server: nobody else may bind the port this one binds (Windows)."""

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.allow_reuse_address = False
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class BoundedThreads:
    """Mixin for a threading HTTP server, placed before it: a ceiling of open connections (`max_connections`, and `max_per_address` for one address that is not this computer). The one that passes it is
    answered `503` and closed at once, so a client that opens connections and sends nothing cannot take every thread of the monitor. The connection is counted from its accept to the end of its thread."""

    max_connections = MAX_CONNECTIONS
    max_per_address = MAX_PER_ADDRESS
    _count_lock = threading.Lock()

    def _counts(self):
        return self.__dict__.setdefault("_open_counts", {"all": 0, "by_address": {}})

    @staticmethod
    def _address_of(client_address):
        return str(client_address[0]) if client_address else ""

    def _counted_for(self, address):
        return address not in ("127.0.0.1", "::1")

    def process_request(self, request, client_address):
        address = self._address_of(client_address)
        with self._count_lock:
            counts = self._counts()
            over = counts["all"] >= self.max_connections or (self._counted_for(address) and counts["by_address"].get(address, 0) >= self.max_per_address)
            if not over:
                counts["all"] += 1
                counts["by_address"][address] = counts["by_address"].get(address, 0) + 1
        if over:
            try:
                request.settimeout(1)
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nRetry-After: 5\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            except (OSError, ValueError):
                pass      # a TLS connection that has not shaken hands cannot be answered: it is closed
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:      # the thread could not start: the place is given back
            self._release(address)
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._release(self._address_of(client_address))

    def _release(self, address):
        with self._count_lock:
            counts = self._counts()
            counts["all"] = max(0, counts["all"] - 1)
            left = counts["by_address"].get(address, 0) - 1
            if left > 0:
                counts["by_address"][address] = left
            else:
                counts["by_address"].pop(address, None)


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
