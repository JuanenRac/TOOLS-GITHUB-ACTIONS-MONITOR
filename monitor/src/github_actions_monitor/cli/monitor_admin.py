# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What `monitor_cli.py` needs to talk to a monitor on ANOTHER computer and to ask it to change its own login: the headers of a request (the access token of the network mode and the Bearer session of
the team mode), the opener that trusts a certificate authority of your own, and the one request with a body that this command line makes. It is a request to the monitor, never to GitHub: the monitor
checks the new token with GitHub itself, before it keeps it."""
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from github_actions_monitor.security import netguard
from github_actions_monitor.tool_version import TOOL_VERSION

#: what the command line knows about the monitor it talks to besides the address: the session of the team mode (a Bearer token) and the authority that signed its certificate
CLIENT = {"session": "", "ca": ""}


class Unreachable(Exception):
    """Nothing answered."""


class BadCertificate(Unreachable):
    """Something answered, but its HTTPS certificate is not trusted (no --ca-file, or another authority)."""


def request_headers(token="", extra=None):
    """The headers of every request: the access token of the network mode, the session of the team mode (a Bearer token), and what the call adds."""
    headers = {"Accept": "application/json", "User-Agent": f"monitor_cli/{TOOL_VERSION}"}
    if token:
        headers["X-Monitor-Access"] = token
    if CLIENT["session"]:
        headers["Authorization"] = "Bearer " + CLIENT["session"]
    headers.update(extra or {})
    return headers


def is_loopback(url):
    """True for an address of this computer: such a request never goes through a proxy of the environment."""
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host in ("127.0.0.1", "::1", "localhost")


def open_url(request, timeout):
    """urlopen for the monitor: no redirect is followed (an answer with a secret goes nowhere else) and, with a certificate authority of your own (--ca-file), HTTPS is checked against it. An address of this
    computer never goes through the proxy of the environment, with or without --ca-file."""
    if CLIENT["ca"] and request.full_url.lower().startswith("https://"):
        context = ssl.create_default_context(cafile=CLIENT["ca"])
        handlers = [urllib.request.HTTPSHandler(context=context), netguard.NoRedirect()]
        if is_loopback(request.full_url):
            handlers.insert(0, urllib.request.ProxyHandler({}))
        return urllib.request.build_opener(*handlers).open(request, timeout=timeout)
    return netguard.local_open(request, timeout=timeout, follow_redirects=False)


def certificate_problem(error):
    """True when a failure to connect is the certificate of the monitor being refused (not a monitor that is down): the CLI says so instead of 'cannot be reached'."""
    reason = getattr(error, "reason", error)
    return isinstance(reason, ssl.SSLError) or isinstance(error, ssl.SSLError)


def session_token(base, token=""):
    """The one-use token the monitor asks for before a write (`session_guard`, on by default); '' when it asks for none or cannot be read."""
    request = urllib.request.Request(base + "/api/session-token", headers=request_headers(token))
    try:
        with open_url(request, 8) as answer:     # noqa: S310 - http/https only, checked by base_url
            document = json.loads(answer.read(100_000).decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return ""
    return str(document.get("token") or "") if isinstance(document, dict) else ""


def send_json(base, path, payload, timeout=8, token="", guarded=False):
    """(status, document) of one request with a JSON body. An answer with an error status still comes back (the caller tells what it means); Unreachable when nothing answers, BadCertificate when its
    certificate is refused. `guarded` asks first for the one-use token of the monitor and sends it (what the page does before a write)."""
    extra = {"Content-Type": "application/json"}
    if guarded:
        once = session_token(base, token)
        if once:
            extra["X-Monitor-Token"] = once
    request = urllib.request.Request(base + path, data=json.dumps(payload).encode("utf-8"), method="POST", headers=request_headers(token, extra))
    try:
        with open_url(request, timeout) as answer:     # noqa: S310 - http/https only, checked by base_url
            status, body = answer.status, answer.read(1_000_000)
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read(1_000_000)
        error.close()
    except (urllib.error.URLError, OSError, ValueError) as error:
        if certificate_problem(error):
            raise BadCertificate(base) from None
        raise Unreachable(base) from None
    try:
        document = json.loads(body.decode("utf-8"))
    except ValueError:
        document = {}
    return status, document if isinstance(document, dict) else {}
