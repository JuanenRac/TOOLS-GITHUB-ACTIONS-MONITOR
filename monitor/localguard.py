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
import ssl
import threading
import time

LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
STATE = {"network": False, "host": "127.0.0.1", "token": "", "allowed": set(), "secure": False}
COOKIE = "monitor_access"
#: keys that can only be written from the same computer while the network mode is on
LOCAL_ONLY_PREFIXES = ("listen.", "github_token.", "act.", "github_actions.")


def host_ok(value):
    """True for the loopback address, a private (RFC 1918) or link-local IPv4 address or 0.0.0.0 ("every interface"). A public address is refused, and so is every IPv6 literal: the
    server is bound with IPv4 only, so an IPv6 address would be accepted by the settings and then never listen where the page says."""
    text = str(value or "").strip()
    if text in ("localhost", "0.0.0.0"):
        return True
    try:
        address = ipaddress.IPv4Address(text)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


def display_host(bound):
    """The address to write in the URL of the page for a server bound to `bound` (server.server_address[0]): the loopback address when it listens on every interface or on
    this computer's own loopback, else the very address it is bound to (a private address is not reachable as 127.0.0.1)."""
    text = str(bound or "")
    return "127.0.0.1" if text in ("", "0.0.0.0", "localhost") else text


def tls_settings(config):
    """{"cert", "key", "secure_cookie"} of the `listen` section: the certificate and the private key (PEM files YOU provide) for HTTPS served directly, and whether the access cookie
    is marked Secure because an HTTPS proxy sits in front. Empty strings = plain HTTP."""
    cfg = config.get("listen") if isinstance(config, dict) and isinstance(config.get("listen"), dict) else {}
    pick = lambda key: cfg.get(key).strip() if isinstance(cfg.get(key), str) and len(cfg.get(key)) <= 500 else ""
    return {"cert": pick("tls_cert_file"), "key": pick("tls_key_file"), "secure_cookie": cfg.get("secure_cookie") is True}


def tls_context(cert, key):
    """A server-side TLS context (TLS 1.2 or newer) from your certificate and key files. Raises OSError / ssl.SSLError when they cannot be used: the caller then does NOT fall back to HTTP."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert, keyfile=key)
    return context


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


def configure(network, host="127.0.0.1", token="", allowed=(), secure=False):
    """Sets the mode of the process. `secure` = the connection is HTTPS (direct TLS or a proxy in front): the cookie then carries Secure. Returns the state (the token is never part of it)."""
    STATE["network"] = bool(network)
    STATE["secure"] = bool(network and secure)
    STATE["host"] = host if network else "127.0.0.1"
    STATE["token"] = token if network else ""
    STATE["allowed"] = {str(a).lower() for a in allowed} | (own_addresses() if network and host == "0.0.0.0" else set())
    if network and host not in ("0.0.0.0", "127.0.0.1", "localhost"):
        STATE["allowed"].add(host.lower())
    return public_state()


def public_state():
    return {"network": STATE["network"], "host": STATE["host"], "token_required": STATE["network"], "secure": STATE["secure"]}


def cookie_header(token):
    """The Set-Cookie value that remembers the access token: HttpOnly, SameSite=Strict and, when the connection is HTTPS, Secure."""
    return f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict" + ("; Secure" if STATE["secure"] else "")


_lock = threading.Lock()
_failures = {}        # address -> times of its recent wrong tokens
_locked = {}          # address -> time until which it is refused
_hits = {}            # (bucket, address) -> times of the recent requests
LOCKOUT_SECONDS = 300
FAIL_WINDOW = 60


def max_failed(config):
    """Wrong access tokens from one address, within a minute, before that address is refused for five minutes (`listen.max_failed_attempts`, default 10)."""
    cfg = config.get("listen") if isinstance(config, dict) and isinstance(config.get("listen"), dict) else {}
    value = cfg.get("max_failed_attempts")
    return value if isinstance(value, int) and not isinstance(value, bool) and 3 <= value <= 100 else 10


def is_locked(address, now=None):
    now = time.time() if now is None else now
    with _lock:
        until = _locked.get(address, 0)
        if until and until <= now:
            _locked.pop(address, None)
            return False
        return bool(until)


def note_failure(address, limit, now=None):
    """Counts a wrong token from `address`; returns True when that address is now locked out. The token itself is never stored or logged."""
    now = time.time() if now is None else now
    with _lock:
        recent = [t for t in _failures.get(address, []) if t > now - FAIL_WINDOW] + [now]
        _failures[address] = recent
        if len(_failures) > 2000:
            for key in [k for k, v in _failures.items() if not v or v[-1] < now - FAIL_WINDOW][:1000]:
                _failures.pop(key, None)
        if len(recent) >= limit:
            _locked[address] = now + LOCKOUT_SECONDS
            _failures.pop(address, None)
            return True
        return False


def over_rate(bucket, address, per_minute, now=None):
    """True when `address` already made `per_minute` requests of this kind in the last minute; otherwise counts this one."""
    now = time.time() if now is None else now
    key = (bucket, address)
    with _lock:
        recent = [t for t in _hits.get(key, []) if t > now - 60]
        if len(recent) >= per_minute:
            _hits[key] = recent
            return True
        _hits[key] = recent + [now]
        if len(_hits) > 4000:
            for k in [k for k, v in _hits.items() if not v or v[-1] < now - 60][:2000]:
                _hits.pop(k, None)
        return False


def reset_limits():
    with _lock:
        _failures.clear(), _locked.clear(), _hits.clear()


def make_token():
    return secrets.token_urlsafe(24)


def local_request_ok(headers, port):
    """DNS-rebinding / cross-site guard: Host must be this server and Origin (if any) too. The Origin must carry the scheme of the session (https when the connection is HTTPS, direct TLS
    or a proxy with `secure_cookie`; http otherwise) and exactly one of our own host:port pairs; the other scheme, another host or port and a malformed value are refused."""
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"} | {f"{h}:{port}" for h in STATE["allowed"]}
    if (headers.get("Host") or "").lower() not in {h.lower() for h in allowed_hosts}:
        return False
    origin = headers.get("Origin")
    if origin is None:
        return True
    scheme = "https" if STATE["secure"] else "http"
    return origin.lower() in {f"{scheme}://{h.lower()}" for h in allowed_hosts}


def local_only_key(key):
    """True when changing this setting is an exposure decision: the fixed prefixes and EVERY key that the settings schema marks as `secure`. In network mode these can only be changed
    from the same computer. The list is read from the schema, so a new secure key is covered without anyone remembering it here."""
    name = str(key)
    if name.startswith(LOCAL_ONLY_PREFIXES):
        return True
    try:
        import settings_api
        meta = settings_api.META.get(name)
    except ImportError:
        meta = None
    return bool(meta and meta.get("secure"))


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
