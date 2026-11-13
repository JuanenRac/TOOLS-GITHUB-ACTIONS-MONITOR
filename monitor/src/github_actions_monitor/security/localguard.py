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
import re
import secrets
import socket
import ssl
import threading
import time

LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
STATE = {"network": False, "host": "127.0.0.1", "token": "", "allowed": set(), "secure": False, "proxy_host": "", "trusted_proxy": False, "behind_proxy": False}
#: the public name of an HTTPS proxy that forwards `Host` without a port (the proxy on port 443): a plain host name, never an address with a port, a path or a user
PROXY_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,98}[a-z0-9])?$")
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


def proxy_host_clean(value):
    """The public host name of the HTTPS proxy in lower case, or '' when it is empty or is not a plain host name (a port, a path, a user, a space or an IPv6 literal make it '')."""
    text = value.strip().lower() if isinstance(value, str) else ""
    return text if PROXY_HOST_RE.match(text) else ""


def configure(network, host="127.0.0.1", token="", allowed=(), secure=False, proxy_host="", trusted_proxy=False, behind_proxy=False):
    """Sets the mode of the process. `secure` = the connection is HTTPS (direct TLS or a proxy in front): the cookie then carries Secure. `proxy_host` = the public name of an HTTPS proxy that
    forwards `Host` and `Origin` without a port (a proxy on port 443); it only counts when the session is HTTPS. `behind_proxy` = the owner declared a reverse proxy in front (also
    implied by a public proxy name or by `trusted_proxy`): then a request that arrives over loopback is NOT "this computer", because the proxy sits on loopback and makes every client look
    local; the person at this computer uses the second, loopback-only port (`listen.local_port`). Returns the state (the token is never part of it)."""
    STATE["network"] = bool(network)
    STATE["secure"] = bool(network and secure)
    STATE["proxy_host"] = proxy_host_clean(proxy_host) if network and secure else ""
    STATE["trusted_proxy"] = bool(network and trusted_proxy)      # listen.trusted_proxy: off unless the owner says the proxy in front is theirs (see client_key)
    STATE["behind_proxy"] = bool(network and (behind_proxy or trusted_proxy or proxy_host_clean(proxy_host)))
    STATE["host"] = host if network else "127.0.0.1"
    STATE["token"] = token if network else ""
    STATE["allowed"] = {str(a).lower() for a in allowed} | (own_addresses() if network and host == "0.0.0.0" else set())
    if network and host not in ("0.0.0.0", "127.0.0.1", "localhost"):
        STATE["allowed"].add(host.lower())
    return public_state()


def public_state():
    return {"network": STATE["network"], "host": STATE["host"], "token_required": STATE["network"], "secure": STATE["secure"]}


def cookie_header(token, secure=None):
    """The Set-Cookie value that remembers the access token: HttpOnly, SameSite=Strict and, when the connection is HTTPS, Secure (`secure` overrides that: the local port is plain HTTP)."""
    return f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict" + ("; Secure" if (STATE["secure"] if secure is None else secure) else "")


_lock = threading.Lock()
_failures = {}        # address -> times of its recent wrong tokens
_locked = {}          # address -> time until which it is refused
_hits = {}            # (bucket, address) -> times of the recent requests
LOCKOUT_SECONDS = 300
FAIL_WINDOW = 60
MAX_LOCKED = 2000      # the list of refused addresses never grows without a limit, whatever the number of addresses that fail once


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
            for key in [k for k, until in _locked.items() if until <= now]:      # every lock that ended goes, not only the one of the address that asks
                _locked.pop(key, None)
            while len(_locked) >= MAX_LOCKED:      # still full: the lock that would end first goes
                _locked.pop(min(_locked, key=_locked.get), None)
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


def local_request_ok(headers, port, door=False):
    """DNS-rebinding / cross-site guard: Host must be this server and Origin (if any) too. The Origin must carry the scheme of the session (https when the connection is HTTPS, direct TLS
    or a proxy with `secure_cookie`; http otherwise) and exactly one of our own host:port pairs; the other scheme, another host or port and a malformed value are refused. The one
    exception is `listen.proxy_public_host`: an HTTPS proxy on the default port forwards `Host` and `Origin` without a port, so that one name, and only under an HTTPS session, is also
    accepted as it is (the host and the origin must both be exactly that name, never any other host without a port). `door` = the second port that only listens on loopback
    (`listen.local_port`, plain HTTP): only the loopback names of that port count."""
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if not door:
        allowed_hosts |= {f"{h}:{port}" for h in STATE["allowed"]}
        if STATE["secure"] and STATE.get("proxy_host"):
            allowed_hosts.add(STATE["proxy_host"])
    if (headers.get("Host") or "").lower() not in {h.lower() for h in allowed_hosts}:
        return False
    origin = headers.get("Origin")
    if origin is None:
        return True
    scheme = "https" if STATE["secure"] and not door else "http"
    return origin.lower() in {f"{scheme}://{h.lower()}" for h in allowed_hosts}


#: the ONLY settings a client of the network can change (the look and the pace of the page). Everything else - every channel of notifications, every path, every name of an environment
#: variable, the files the signing and dispatch flow trusts, the rules of the sentinel - is decided from the computer of the monitor. A setting that is added later is local-only until it
#: is listed here on purpose.
REMOTE_WRITABLE = frozenset({"language", "display.timezone", "display.blink_red_tiles", "refresh_seconds", "hot_hours", "cold_refresh_seconds", "runs_per_repo", "cold_runs_per_repo", "stuck_minutes",
                             "show_unclassified", "report_history_days", "quota.warn_percent", "quota.alert_percent", "alerts.mute_hours"})


def local_only_key(key):
    """True when this setting cannot be changed by a client of the network: in network mode only REMOTE_WRITABLE (a short allow list) may be written from another computer; the keys
    of the fixed prefixes and every key the schema marks as `secure` are local-only in any case."""
    name = str(key)
    if name.startswith(LOCAL_ONLY_PREFIXES):
        return True
    try:
        from github_actions_monitor.app import settings_api
        meta = settings_api.META.get(name)
    except ImportError:
        meta = None
    if meta and meta.get("secure"):
        return True
    return name not in REMOTE_WRITABLE


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


def client_key(client_address, headers=None):
    """The address a failed attempt and a lock are counted against. By default the TCP peer. With `listen.trusted_proxy` ON, a request whose peer is THIS computer (the reverse proxy the owner put in
    front) is counted against the LAST address of `X-Forwarded-For` (the one the proxy itself appended: an earlier one can be written by the client), so that one person's wrong tokens do not lock
    everybody out of the same proxy. It only changes the counting: a request that carries a forwarding header is still never "this computer" (is_this_computer), whatever it says."""
    peer = str(client_address[0])
    if not (STATE.get("trusted_proxy") and headers is not None and from_this_computer(client_address)):
        return peer
    forwarded = headers.get("X-Forwarded-For") or ""
    last = forwarded.split(",")[-1].strip()
    try:
        return "fwd:" + str(ipaddress.ip_address(last.split("%")[0]))
    except ValueError:
        return peer      # a header that is not an address is ignored: the peer is counted


#: the failures of a trusted proxy that the proxy itself cannot tell apart are counted here as well, with a looser limit (see note_proxy_failure)
PROXY_KEY = "proxy:all"
PROXY_FACTOR = 3


def is_locked_out(client_address, headers=None):
    """True when the address of this request (client_key) is locked, or, with `listen.trusted_proxy`, when the clients of the proxy as a whole have failed too often (a proxy that does not
    ADD `X-Forwarded-For` lets the client choose its own address, and rotating it must not turn the lock into nothing)."""
    if is_locked(client_key(client_address, headers)):
        return True
    return bool(STATE.get("trusted_proxy") and headers is not None and from_this_computer(client_address) and is_locked(PROXY_KEY))


def note_proxy_failure(client_address, headers, limit):
    """Counts a wrong token against all the clients of the trusted proxy together (PROXY_FACTOR times the limit of one address)."""
    if STATE.get("trusted_proxy") and headers is not None and from_this_computer(client_address):
        note_failure(PROXY_KEY, limit * PROXY_FACTOR)


FORWARD_HEADERS = ("Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Forwarded-Port", "X-Real-IP", "Via")


def is_this_computer(client_address, headers=None, door=False):
    """True when the request really comes from a person on this computer: the TCP peer is loopback AND the request does not come through a reverse proxy on the same machine (a proxy
    makes every client look like 127.0.0.1). A request that carries a forwarding header, or whose Host is the public name of the proxy (`listen.proxy_public_host`), is never "this computer".
    With a proxy DECLARED (`proxy_public_host`, `secure_cookie` or `trusted_proxy`) nothing that arrives over loopback counts, whatever its headers say (a proxy that forgets to add them would
    make every client of the internet look local): the person at this computer comes in by the second port that only listens on loopback (`listen.local_port`), which is `door`."""
    if not from_this_computer(client_address):
        return False
    if STATE.get("behind_proxy") and not door:
        return False
    if headers is None:
        return True
    if any(headers.get(name) for name in FORWARD_HEADERS):
        return False
    proxy = STATE.get("proxy_host")
    return not (proxy and (headers.get("Host") or "").lower() == str(proxy).lower())


def query_access_allowed(config):
    """True while the deprecated `?access=` address may open the session (`listen.query_access`, default on so that nothing already set up breaks). The token in an address ends up in the
    history, the logs and the Referer: turn it off and the session is opened by `POST /api/access` (the token in the body) or by the header."""
    cfg = config.get("listen") if isinstance(config, dict) and isinstance(config.get("listen"), dict) else {}
    return cfg.get("query_access") is not False


def query_token_counts(command, path, config):
    """The `?access=` token is honoured only on a GET (never on another verb, where it would sit in the address of a request that changes something) and only while
    `listen.query_access` is on. It opens the session once: the answer sets the cookie and goes to the clean address."""
    return command == "GET" and query_access_allowed(config)


def settings_from(config):
    """{"network": bool, "host": str, "token_env": str, "allowed_hosts": [...], "proxy_public_host": str, "trusted_proxy": bool, "local_port": int} from the configuration, with the conservative default."""
    cfg = config.get("listen") if isinstance(config, dict) and isinstance(config.get("listen"), dict) else {}
    host = cfg.get("host") if isinstance(cfg.get("host"), str) and host_ok(cfg.get("host")) else "127.0.0.1"
    door = cfg.get("local_port")
    door = door if isinstance(door, int) and not isinstance(door, bool) and 1024 <= door <= 65535 else 0
    network = cfg.get("network") is True
    env = cfg.get("token_env") if isinstance(cfg.get("token_env"), str) else "MONITOR_ACCESS_TOKEN"
    allowed = [h for h in (cfg.get("allowed_hosts") or []) if isinstance(h, str) and 0 < len(h) <= 100]
    return {"network": network, "host": host if network else "127.0.0.1", "token_env": env or "MONITOR_ACCESS_TOKEN", "allowed_hosts": allowed,
            "proxy_public_host": proxy_host_clean(cfg.get("proxy_public_host")), "trusted_proxy": cfg.get("trusted_proxy") is True, "local_port": door}
