# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two restrictions an installation can prove: the strict read-only mode (`security.read_only_strict`) and the network policy (`security.egress_policy`). Standard library only.

Both are enforced in ONE place, below every part of the monitor: an audit hook of Python (`sys.addaudithook`), which sees every program started and every connection opened by this process and cannot
be removed once added. With both settings at their defaults the hook is not even installed.

  read_only_strict   no command that writes to GitHub is started (only the read commands of `gh` are let through; anything not known to be a read is refused), no `git push`, no `act`, and no request to
                     the API of GitHub with a method other than GET or HEAD. It does not matter which edition runs or what other settings say.
  egress_policy      default | github_only | none. `github_only` lets the process reach the API of GitHub (and the GitHub Enterprise host that is configured) and what `security.egress_allow` names;
                     `none` lets it reach this computer only. Programs that open the network on their own (git, apprise, curl, docker...) are not started; `gh` is not started with `none`.

A refusal is an OSError (`Blocked`) whose text says which setting refused it, so the part that asked fails like a network that is down, with a reason. The restrictions are only ever tightened while
the process runs: relaxing them needs a restart, and neither can be changed from the network. This is not a firewall: it covers this process and the programs it starts by name, not what those
programs do on their own."""
import ipaddress
import json
import os
import re
import socket
import sys
from fnmatch import fnmatchcase
from urllib.parse import urlsplit

POLICIES = ("default", "github_only", "none")
GITHUB_HOSTS = ("api.github.com", "uploads.github.com")
NETWORK_PROGRAMS = frozenset({"git", "apprise", "curl", "wget", "ssh", "scp", "sftp", "docker", "podman", "act", "vault", "bw", "aws", "az", "gcloud", "cosign", "pip", "pip3", "npm", "claude"})
GIT_NETWORK = frozenset({"fetch", "pull", "push", "clone", "ls-remote", "remote", "submodule", "archive"})
#: gh subcommand -> the words after it that only read (None = every word reads)
GH_READS = {"auth": ("status", "token"), "run": ("list", "view", "download", "watch"), "workflow": ("list", "view"), "pr": ("list", "view", "status", "checks", "diff"),
            "issue": ("list", "view", "status"), "release": ("list", "view", "download", "verify", "verify-asset"), "repo": ("list", "view", "clone"), "label": ("list",), "secret": ("list",),
            "variable": ("list", "get"), "ruleset": ("list", "view", "check"), "cache": ("list",), "attestation": ("verify", "download", "trusted-root", "inspect"), "config": ("get", "list"),
            "extension": ("list",), "ssh-key": ("list",), "gpg-key": ("list",), "gist": ("list", "view"), "org": ("list",), "project": ("list", "view", "field-list", "item-list"),
            "search": None, "status": None, "version": None, "help": None}
EVENTS = frozenset({"subprocess.Popen", "os.system", "socket.getaddrinfo", "socket.gethostbyname", "socket.connect", "socket.sendto", "urllib.Request"})
MUTATION_RE = re.compile(r"\bmutation\b")
#: the POST routes of the page whose effect is a write on GitHub or a program that runs: in strict read-only mode they answer 403 with the reason, before anything is prepared
WRITE_ROUTES = ("/api/gh-action/confirm", "/api/ai/actions/confirm", "/api/act/confirm", "/api/webhook/redeliver")

STATE = {"installed": False, "strict": False, "policy": "default", "allow": (), "ghe": "", "addresses": set(), "blocked": 0, "last": ""}


class Blocked(PermissionError):
    """Refused by security.read_only_strict or security.egress_policy."""


def wanted(config):
    """(strict, policy, allow list, GitHub Enterprise host) as the configuration asks; a value that cannot be understood restricts MORE for the policy that was clearly meant to restrict, and a value
    of the wrong type for the switch reads as off."""
    config = config if isinstance(config, dict) else {}
    block = config.get("security") if isinstance(config.get("security"), dict) else {}
    strict = block.get("read_only_strict") is True
    policy = block.get("egress_policy", "default")
    if policy not in POLICIES:
        policy = "none" if policy not in (None, "") else "default"      # a typo in a restriction must not open the network
    allow = tuple(str(x).strip().lower()[:253] for x in block.get("egress_allow") if isinstance(x, str) and x.strip()) if isinstance(block.get("egress_allow"), list) else ()
    host = os.environ.get("GH_HOST", "").strip().lower()
    return strict, policy, allow[:100], "" if host == "github.com" else host


def configure(config):
    """Takes the restrictions of `config`. They are only tightened: a switch that is on stays on and a policy never becomes more open."""
    strict, policy, allow, ghe = wanted(config)
    was = STATE["policy"]
    STATE["strict"] = STATE["strict"] or strict
    if POLICIES.index(policy) > POLICIES.index(was):
        STATE["policy"], STATE["allow"] = policy, allow
    elif policy == was:
        STATE["allow"] = allow if was == "default" else tuple(a for a in STATE["allow"] if a in allow)
    STATE["ghe"] = STATE["ghe"] or ghe
    return STATE["strict"] or STATE["policy"] != "default"


def route_refused(path, config=None):
    """True when a POST to `path` must be refused because of the strict read-only mode (in force in this process, or already set in the configuration)."""
    return path in WRITE_ROUTES and (STATE["strict"] or wanted(config)[0])


def restricted():
    return STATE["strict"] or STATE["policy"] != "default"


def arm(config):
    """Takes the restrictions and installs the hook when there is one to enforce. Returns True when something is restricted."""
    if configure(config):
        install()
        return True
    return False


def arm_from_file():
    """At the start of every process of the monitor (the import of the package): the restrictions of the configuration file."""
    from github_actions_monitor.util import paths
    try:
        config = json.loads(paths.config_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return arm(config)


def reset():
    """Tests only (a hook cannot be removed: with nothing restricted it returns at once)."""
    STATE.update(strict=False, policy="default", allow=(), ghe="", blocked=0, last="")
    STATE["addresses"].clear()


# --- what is allowed -------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _literal(host):
    try:
        return ipaddress.ip_address(str(host).strip("[]").split("%")[0])
    except ValueError:
        return None


def is_local(host):
    """This computer: the name localhost, its own name, a loopback or unspecified address."""
    host = str(host or "").lower().rstrip(".")
    if host in ("", "localhost", "ip6-localhost"):
        return True
    address = _literal(host)
    if address is not None:
        mapped = getattr(address, "ipv4_mapped", None)
        address = mapped or address
        return address.is_loopback or address.is_unspecified
    return host == socket.gethostname().lower()


def host_allowed(host, policy=None, allow=None, ghe=None):
    """Whether the policy lets the monitor reach `host`."""
    policy = STATE["policy"] if policy is None else policy
    allow = STATE["allow"] if allow is None else allow
    ghe = STATE["ghe"] if ghe is None else ghe
    if policy == "default" or is_local(host):
        return True
    if policy == "none":
        return False
    host = str(host).lower().rstrip(".")
    return host in GITHUB_HOSTS or (bool(ghe) and host == ghe) or any(fnmatchcase(host, pattern) for pattern in allow)


def split_windows(line):
    """A Windows command line as its arguments (the rules of the C runtime), for the audit event, which gives the line and not the list."""
    out, current, quoted, slashes, started = [], [], False, 0, False
    for char in line:
        if char == "\\":
            slashes += 1
            started = True
            continue
        if char == '"':
            current.append("\\" * (slashes // 2))
            if slashes % 2:
                current.append('"')
            else:
                quoted = not quoted
            slashes, started = 0, True
            continue
        current.append("\\" * slashes)
        slashes = 0
        if char in " \t" and not quoted:
            if started:
                out.append("".join(current))
            current, started = [], False
            continue
        current.append(char)
        started = True
    current.append("\\" * slashes)
    if started:
        out.append("".join(current))
    return out


def program_of(path):
    name = str(path or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (".exe", ".cmd", ".bat", ".com"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def _words(args):
    """The arguments of a gh command without the options that choose where it runs."""
    out, skip = [], False
    for item in args:
        if skip:
            skip = False
            continue
        if item in ("-R", "--repo", "--hostname"):
            skip = True
            continue
        if item.startswith(("--repo=", "--hostname=")):
            continue
        out.append(item)
    return out


def gh_is_read(args):
    """Whether `gh <args>` only reads. Anything that is not known to be a read is not one."""
    words = _words([str(a) for a in args])
    if not words:
        return True
    if words[0] in ("--version", "--help", "-h"):
        return True
    group, rest = words[0], words[1:]
    if group == "api":
        return _api_is_read(rest)
    if group not in GH_READS:
        return False
    verbs = GH_READS[group]
    if verbs is None or "--help" in rest:
        return True
    return bool(rest) and rest[0] in verbs


def _api_is_read(rest):
    method, fields, opaque, endpoint, texts = "", False, False, "", []
    index = 0
    value_options = ("-H", "--header", "-q", "--jq", "-t", "--template", "--cache", "-p", "--preview")
    while index < len(rest):
        item = rest[index]
        following = rest[index + 1] if index + 1 < len(rest) else ""
        if item in ("-X", "--method"):
            method, index = following.upper(), index + 2
            continue
        if item.startswith("--method=") or (item.startswith("-X") and len(item) > 2):
            method = item.split("=", 1)[1].upper() if "=" in item else item[2:].upper()
        elif item in ("-f", "-F", "--field", "--raw-field"):
            fields = True
            texts.append(following)
            index += 2
            continue
        elif item.startswith(("--field=", "--raw-field=")) or (item[:2] in ("-f", "-F") and len(item) > 2):
            fields = True
            texts.append(item.split("=", 1)[1] if item.startswith("--") else item[2:])
        elif item == "--input" or item.startswith("--input="):
            fields = opaque = True
            if item == "--input":
                index += 2
                continue
        elif item in value_options:
            index += 2
            continue
        elif not item.startswith("-") and not endpoint:
            endpoint = item
        index += 1
    if endpoint.strip("/").lower() == "graphql":
        # a query of GraphQL travels as a POST: it is a read unless it holds a mutation; a text taken from a file cannot be looked at
        return not opaque and not any(MUTATION_RE.search(t) or t.split("=", 1)[-1].startswith("@") for t in texts)
    method = method or ("POST" if fields else "GET")
    return method in ("GET", "HEAD")


def command_refusal(argv):
    """Why this program may not be started now ("" when it may)."""
    if not argv:
        return ""
    program, rest = program_of(argv[0]), [str(a) for a in argv[1:]]
    if STATE["strict"]:
        if program == "gh" and not gh_is_read(rest):
            return "read_only_strict"
        if program == "git" and "push" in rest:
            return "read_only_strict"
        if program == "act" and not any(a in ("-l", "--list", "-n", "--dryrun", "--version", "--help") for a in rest):
            return "read_only_strict"
    if STATE["policy"] != "default":
        if program == "gh" and STATE["policy"] == "none" and rest[:1] not in (["--version"], ["version"]) and rest[:2] != ["auth", "token"]:
            return "egress_policy"
        if program == "git" and not GIT_NETWORK.intersection(rest):
            return ""
        if program in NETWORK_PROGRAMS and not any(a in ("--version", "version") for a in rest) and f"program:{program}" not in STATE["allow"]:
            return "egress_policy"
    return ""


def request_refusal(url, method):
    """Why this HTTP request may not be sent now ("" when it may)."""
    try:
        parts = urlsplit(str(url))
        host = (parts.hostname or "").lower()
    except ValueError:
        return "egress_policy" if restricted() else ""
    if not host:
        return ""
    if STATE["strict"] and (host in GITHUB_HOSTS or (STATE["ghe"] and host == STATE["ghe"])) and str(method or "GET").upper() not in ("GET", "HEAD"):
        path = parts.path.rstrip("/")
        if not (path.endswith("/access_tokens") or path.endswith("/graphql")):      # a token that only reads, and a query of GraphQL (a mutation is refused by the token and by gh_is_read)
            return "read_only_strict"
    if STATE["policy"] != "default" and not host_allowed(host):
        return "egress_policy"
    return ""


# --- the hook --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _refuse(reason, what):
    STATE["blocked"] += 1
    STATE["last"] = f"{reason}: {what}"[:160]
    raise Blocked(f"blocked by security.{reason} ({what[:80]})")


def _text(value):
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def _hook(event, args):
    if event not in EVENTS or not restricted():
        return
    if event == "subprocess.Popen":
        executable, line = args[0], args[1]
        if isinstance(line, (str, bytes)):
            argv = split_windows(_text(line))
        else:
            argv = [str(_text(a)) for a in line]
        if executable and argv and program_of(executable) != program_of(argv[0]):
            argv = [str(_text(executable))] + argv[1:]
        reason = command_refusal(argv)
        if reason:
            _refuse(reason, " ".join([program_of(argv[0])] + argv[1:3]))
    elif event == "os.system":
        reason = command_refusal(str(_text(args[0])).split())
        if reason:
            _refuse(reason, str(_text(args[0]))[:40])
    elif event == "urllib.Request":
        reason = request_refusal(args[0], args[3] if len(args) > 3 else "GET")
        if reason:
            _refuse(reason, urlsplit(str(args[0])).hostname or "request")
    elif STATE["policy"] == "default":
        return
    elif event in ("socket.getaddrinfo", "socket.gethostbyname"):
        host = _text(args[0])
        if host is not None and _literal(host) is None and not host_allowed(host):      # an address is judged when it is connected to
            _refuse("egress_policy", str(host))
    else:      # socket.connect, socket.sendto
        sock, address = args[0], args[-1]
        if not isinstance(address, tuple) or not address:
            return      # a local socket of the system (a path)
        host = str(_text(address[0]))
        if is_local(host) or host in STATE["addresses"] or (STATE["policy"] == "github_only" and any(fnmatchcase(host, p) for p in STATE["allow"])):
            return
        if getattr(sock, "type", None) == socket.SOCK_DGRAM and host.startswith("192.0.2."):
            return      # a documentation address that is never routed: how the address of this computer in the local network is found, nothing is sent
        _refuse("egress_policy", host)


def _remember(real):
    """getaddrinfo that notes the addresses of the names that are allowed, so that the connection to one of them is allowed too."""
    def getaddrinfo(host, port, *args, **kwargs):
        found = real(host, port, *args, **kwargs)
        name = _text(host)
        if STATE["policy"] == "github_only" and name is not None and _literal(name) is None and host_allowed(name):
            STATE["addresses"].update(str(item[4][0]) for item in found)
        return found
    return getaddrinfo


def install():
    """Adds the hook once for the whole life of the process."""
    if not STATE["installed"]:
        socket.getaddrinfo = _remember(socket.getaddrinfo)
        sys.addaudithook(_hook)
        STATE["installed"] = True


def status():
    return {"read_only_strict": STATE["strict"], "egress_policy": STATE["policy"], "egress_allow": len(STATE["allow"]), "blocked": STATE["blocked"], "last_blocked": STATE["last"], "enforced": STATE["installed"] and restricted()}


def violations(config, rows):
    """The destinations that are configured (`ops/egress.table`: rows with "active") and that the policy of `config` does not let through: [(row id, host)]."""
    _strict, policy, allow, ghe = wanted(config)
    return [(row["id"], host) for row in rows if row["active"] for host in row["hosts"] if not host_allowed(host, policy, allow, ghe)]
