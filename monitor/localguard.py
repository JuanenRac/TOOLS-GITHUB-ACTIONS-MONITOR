# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Who may talk to the page. Small on purpose: the lite edition loads it without loading the sentinel.

  * By default only this computer: the `Host` must be `127.0.0.1:PORT` or `localhost:PORT` and an `Origin`, if there is one, the same (DNS-rebinding and cross-site guard).
  * Network mode (`listen.network`, OFF by default, restart needed): the monitor also listens on the address you chose (`listen.host`: a private address of this computer or `0.0.0.0`).
    Then EVERY request must carry the access token (cookie `monitor_access`, header `X-Monitor-Access` or `Authorization: Bearer`), the `Host` must be one of the names you listed in
    `listen.allowed_hosts` (or an address of this computer), a page request can only open a session with `?access=TOKEN`, and the keys that decide exposure, the token of GitHub, the
    local runs of `act` and the actions on GitHub can only be changed from the same computer. The token comes from the environment variable NAMED in `listen.token_env`; without one a random
    token is made at each start and printed once in the console (never written to a file or a log).
"""
import hmac
import ipaddress
import secrets
import socket

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "[::1]")
STATE = {"network": False, "host": "127.0.0.1", "token": "", "allowed": set()}
COOKIE = "monitor_access"
#: keys that can only be written from the same computer while the network mode is on
LOCAL_ONLY_PREFIXES = ("listen.", "github_token.", "act.", "github_actions.")


def host_ok(value):
    """True for the loopback address, a private (RFC 1918 / unique-local / link-local) address or 0.0.0.0 ("every interface"). A public address is refused."""
    text = str(value or "").strip()
    if text in ("localhost", "0.0.0.0"):
        return True
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


def own_addresses():
    """The names this computer answers to (best effort, no network traffic)."""
    out = set()
    try:
        name = socket.gethostname()
        out.add(name.lower())
        out.update(socket.gethostbyname_ex(name)[2])
    except OSError:
        pass
    return out


def configure(network, host="127.0.0.1", token="", allowed=()):
    """Sets the mode of the process. Returns the state (the token is never part of it)."""
    STATE["network"] = bool(network)
    STATE["host"] = host if network else "127.0.0.1"
    STATE["token"] = token if network else ""
    STATE["allowed"] = {str(a).lower() for a in allowed} | (own_addresses() if network and host == "0.0.0.0" else set())
    if network and host not in ("0.0.0.0", "127.0.0.1", "localhost"):
        STATE["allowed"].add(host.lower())
    return public_state()


def public_state():
    return {"network": STATE["network"], "host": STATE["host"], "token_required": STATE["network"]}


def make_token():
    return secrets.token_urlsafe(24)


def local_request_ok(headers, port):
    """DNS-rebinding / cross-site guard: Host must be this server and Origin (if any) too."""
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"} | {f"{h}:{port}" for h in STATE["allowed"]}
    if (headers.get("Host") or "").lower() not in {h.lower() for h in allowed_hosts}:
        return False
    origin = headers.get("Origin")
    return origin is None or origin.lower() in {f"http://{h.lower()}" for h in allowed_hosts}


def presented(headers):
    """The access token the request carries (cookie, header or bearer), or ''."""
    cookie = headers.get("Cookie") or ""
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE:
            return value
    bearer = headers.get("Authorization") or ""
    if bearer.lower().startswith("bearer "):
        return bearer[7:].strip()
    return (headers.get("X-Monitor-Access") or "").strip()


def access_ok(headers, query_token=""):
    """True when no access token is needed (loopback mode) or the request proves it knows it. Constant-time comparison."""
    if not STATE["network"]:
        return True
    wanted = STATE["token"].encode()
    for candidate in (presented(headers), query_token):
        if candidate and hmac.compare_digest(str(candidate).encode(), wanted):
            return True
    return False


def from_this_computer(client_address):
    """True when the TCP peer is this computer (the only origin allowed to change the keys of LOCAL_ONLY_PREFIXES in network mode)."""
    try:
        return ipaddress.ip_address(str(client_address[0]).split("%")[0]).is_loopback
    except (ValueError, IndexError, TypeError):
        return False


def settings_from(config):
    """{"network": bool, "host": str, "token_env": str, "allowed_hosts": [...]} from the configuration, with the conservative default."""
    cfg = config.get("listen") if isinstance(config, dict) and isinstance(config.get("listen"), dict) else {}
    host = cfg.get("host") if isinstance(cfg.get("host"), str) and host_ok(cfg.get("host")) else "127.0.0.1"
    network = cfg.get("network") is True
    env = cfg.get("token_env") if isinstance(cfg.get("token_env"), str) else "MONITOR_ACCESS_TOKEN"
    allowed = [h for h in (cfg.get("allowed_hosts") or []) if isinstance(h, str) and 0 < len(h) <= 100]
    return {"network": network, "host": host if network else "127.0.0.1", "token_env": env or "MONITOR_ACCESS_TOKEN", "allowed_hosts": allowed}
