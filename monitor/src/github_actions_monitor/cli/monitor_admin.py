# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What `monitor_cli.py` needs to talk to a monitor on ANOTHER computer and to ask it to change its own login: the headers of a request (the access token of the network mode and the Bearer session of
the team mode), the opener that trusts a certificate authority of your own, and the one request with a body that this command line makes. It is a request to the monitor, never to GitHub: the monitor
checks the new token with GitHub itself, before it keeps it."""
import json
import ssl
import urllib.error
import urllib.request

from github_actions_monitor.security import netguard
from github_actions_monitor.tool_version import TOOL_VERSION

#: what the command line knows about the monitor it talks to besides the address: the session of the team mode (a Bearer token) and the authority that signed its certificate
CLIENT = {"session": "", "ca": ""}


class Unreachable(Exception):
    """Nothing answered."""


def request_headers(token="", extra=None):
    """The headers of every request: the access token of the network mode, the session of the team mode (a Bearer token), and what the call adds."""
    headers = {"Accept": "application/json", "User-Agent": f"monitor_cli/{TOOL_VERSION}"}
    if token:
        headers["X-Monitor-Access"] = token
    if CLIENT["session"]:
        headers["Authorization"] = "Bearer " + CLIENT["session"]
    headers.update(extra or {})
    return headers


def open_url(request, timeout):
    """urlopen for the monitor: no redirect is followed (an answer with a secret goes nowhere else) and, with a certificate authority of your own (--ca-file), HTTPS is checked against it."""
    if CLIENT["ca"] and request.full_url.lower().startswith("https://"):
        context = ssl.create_default_context(cafile=CLIENT["ca"])
        return urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), netguard.NoRedirect()).open(request, timeout=timeout)
    return netguard.local_open(request, timeout=timeout, follow_redirects=False)


def send_json(base, path, payload, timeout=8, token=""):
    """(status, document) of one request with a JSON body. An answer with an error status still comes back (the caller tells what it means); Unreachable when nothing answers."""
    request = urllib.request.Request(base + path, data=json.dumps(payload).encode("utf-8"), method="POST", headers=request_headers(token, {"Content-Type": "application/json"}))
    try:
        with open_url(request, timeout) as answer:     # noqa: S310 - http/https only, checked by base_url
            status, body = answer.status, answer.read(1_000_000)
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read(1_000_000)
        error.close()
    except (urllib.error.URLError, OSError, ValueError):
        raise Unreachable(base) from None
    try:
        document = json.loads(body.decode("utf-8"))
    except ValueError:
        document = {}
    return status, document if isinstance(document, dict) else {}
