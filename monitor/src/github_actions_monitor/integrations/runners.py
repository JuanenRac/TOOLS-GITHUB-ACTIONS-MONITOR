# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Self-hosted runners (`runners.enabled`, OFF by default): which of your runners are idle, busy or offline, and how loaded their machine is. Read only.

  * State: from the runners API of GitHub (`orgs/OWNER/actions/runners`, or `repos/OWNER/REPO/actions/runners` for each watched repository with `runners.scope = repos`): `busy` = a job
    is running on it, `idle` = online and free, `offline`. A personal account has no account-level list, so the repositories are used.
  * Disk and load: GitHub does not know them. The only source is an optional endpoint YOU run on the machine of the runner (a Prometheus node exporter, `/metrics`), named in
    `runners.metrics` as {runner name: address} - an address on this computer or a private one. The monitor reads `node_load1` and the free space of `/`; no agent is installed by the monitor.
"""
import ipaddress
import re
import urllib.error
import urllib.parse
import urllib.request

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
GROUP_MODES = ("none", "group", "label")
GENERIC_LABELS = frozenset({"self-hosted", "linux", "windows", "macos", "x64", "x86", "arm", "arm64"})      # the labels GitHub adds to every self-hosted runner: they tell nothing about which group it is
NO_GROUP = "(none)"


def group_mode(config):
    """`runners.group_by`: none (default), group (the runner group of the jobs) or label (the first label that is not a generic one)."""
    cfg = config.get("runners") if isinstance(config, dict) and isinstance(config.get("runners"), dict) else {}
    return cfg.get("group_by") if cfg.get("group_by") in GROUP_MODES else "none"


def custom_label(labels):
    """The first label of a runner or a job that is not one of the generic ones (case does not matter), else NO_GROUP."""
    for label in labels or []:
        text = str(label).strip().lower()
        if text and text not in GENERIC_LABELS:
            return text[:60]
    return NO_GROUP


def group_runners(runners, mode):
    """The runners of the list grouped by their custom label (`runners.group_by` = label): {"by", "available", "rows": [{"key", "runners", "idle", "busy", "offline"}]}. The list of GitHub does not say the
    runner group of a runner (only the jobs do), so with `group` the grouping is not available here and says so (`available` false), it is not guessed."""
    if mode == "group":
        return {"by": "group", "available": False, "rows": []}
    rows = {}
    for runner in runners:
        e = rows.setdefault(custom_label(runner.get("labels")), {"key": custom_label(runner.get("labels")), "runners": 0, "idle": 0, "busy": 0, "offline": 0})
        e["runners"] += 1
        e[runner.get("state") if runner.get("state") in ("idle", "busy", "offline") else "offline"] += 1
    return {"by": "label", "available": True, "rows": sorted(rows.values(), key=lambda r: r["key"])}


def settings(config):
    cfg = config.get("runners") if isinstance(config, dict) and isinstance(config.get("runners"), dict) else {}
    metrics = cfg.get("metrics") if isinstance(cfg.get("metrics"), dict) else {}
    return {"enabled": cfg.get("enabled") is True, "scope": cfg.get("scope") if cfg.get("scope") in ("owner", "repos") else "owner",
            "metrics": {k: v for k, v in metrics.items() if isinstance(k, str) and NAME_RE.match(k) and private_address(v)}}


def private_address(url):
    """True for an http(s) address whose host is this computer or a private address (the exporter of a runner in your own network). Never a public host."""
    try:
        parts = urllib.parse.urlsplit(str(url))
        host = parts.hostname or ""
        if parts.scheme not in ("http", "https") or parts.username or parts.password:
            return False
        if host == "localhost":
            return True
        address = ipaddress.ip_address(host)
        return address.is_loopback or address.is_private
    except ValueError:
        return False


def state_of(runner):
    if runner.get("status") != "online":
        return "offline"
    return "busy" if runner.get("busy") else "idle"


def clean(runner):
    labels = [str(x.get("name") if isinstance(x, dict) else x)[:40] for x in (runner.get("labels") or [])][:12]
    return {"id": runner.get("id"), "name": str(runner.get("name", ""))[:100], "os": str(runner.get("os", ""))[:20], "state": state_of(runner), "labels": labels}


def parse_node_metrics(text):
    """{"load1", "disk_free_percent"} from the text of a node exporter; keys missing when the exporter does not give them."""
    out, size, avail = {}, None, None
    for line in str(text).splitlines():
        if line.startswith("#"):
            continue
        match = re.match(r'^(node_load1|node_filesystem_size_bytes|node_filesystem_avail_bytes)(\{[^}]*\})?\s+([0-9.eE+-]+)', line)
        if not match:
            continue
        name, labels, value = match.group(1), match.group(2) or "", float(match.group(3))
        if name == "node_load1":
            out["load1"] = round(value, 2)
        elif 'mountpoint="/"' in labels:
            if name == "node_filesystem_size_bytes":
                size = value
            else:
                avail = value
    if size and avail is not None:
        out["disk_free_percent"] = round(100.0 * avail / size, 1)
    return out


MAX_REDIRECTS = 3
MAX_BYTES = 500_000


class PrivateRedirects(urllib.request.HTTPRedirectHandler):
    """An exporter may answer with a redirect, but only to an address that passes the same test as the one in the configuration (this computer or a private address, no credentials) and keeps
    the scheme; at most MAX_REDIRECTS hops. Anything else ends the read with no figures."""
    max_redirections = MAX_REDIRECTS
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urljoin(req.full_url, newurl)
        if not private_address(target) or urllib.parse.urlsplit(target).scheme != urllib.parse.urlsplit(req.full_url).scheme:
            raise urllib.error.URLError("redirect to a place that is not allowed")
        return super().redirect_request(req, fp, code, msg, headers, target)


def open_exporter(url, timeout=5):
    """The text of an exporter (at most MAX_BYTES), with no proxy and with every redirect judged again."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), PrivateRedirects())
    with opener.open(url, timeout=timeout) as answer:
        return answer.read(MAX_BYTES).decode("utf-8", "replace")


def read_metrics(url, opener=None, timeout=5):
    try:
        if opener is None and not private_address(url):
            return {}
        return parse_node_metrics((opener or (lambda u: open_exporter(u, timeout)))(url))
    except Exception:   # noqa: BLE001 - an exporter that does not answer just has no figures
        return {}


def collect(config, reader, owner, repos=(), opener=None):
    """{"runners": [...], "counts": {"idle", "busy", "offline"}, "errors": n} - `reader(endpoint)` returns the JSON of the API."""
    cfg = settings(config)
    endpoints = [f"orgs/{owner}/actions/runners?per_page=100"] if cfg["scope"] == "owner" else [f"repos/{owner}/{r}/actions/runners?per_page=100" for r in list(repos)[:30] if NAME_RE.match(r)]
    found, errors, seen, unchecked = [], 0, set(), []
    names = [None] if cfg["scope"] == "owner" else [r for r in list(repos)[:30] if NAME_RE.match(r)]
    if cfg["scope"] != "owner":
        unchecked.extend(r for r in list(repos)[30:] if NAME_RE.match(r))      # the read stops at 30 repositories: the others are named, not shown as having no runners
    for name, endpoint in zip(names, endpoints, strict=True):
        try:
            body = reader(endpoint)
        except Exception:   # noqa: BLE001 - not an organisation, no permission, offline
            errors += 1
            if name:
                unchecked.append(name)      # this one could not be read: named as not checked
            continue
        for item in (body or {}).get("runners") or []:
            if isinstance(item, dict) and item.get("id") not in seen:
                seen.add(item.get("id"))
                row = clean(item)
                url = cfg["metrics"].get(row["name"])
                if url:
                    row.update(read_metrics(url, opener))
                found.append(row)
    counts = {k: sum(1 for r in found if r["state"] == k) for k in ("idle", "busy", "offline")}
    out = {"runners": found, "counts": counts, "errors": errors, "unchecked": sorted(unchecked)[:50]}
    mode = group_mode(config)
    if mode != "none":      # runners.group_by: only what was read is grouped, no call is added
        out["groups"] = group_runners(found, mode)
    return out


def payload(config, reader, owner, demo=False, repos=()):
    cfg = settings(config)
    if demo:
        return {"enabled": True, "demo": True, "runners": [{"id": 1, "name": "demo-runner", "os": "Linux", "state": "busy", "labels": ["self-hosted", "linux"], "load1": 0.8, "disk_free_percent": 61.0}],
                "counts": {"idle": 0, "busy": 1, "offline": 0}, "errors": 0, "unchecked": []}
    if not cfg["enabled"]:
        return {"enabled": False, "runners": [], "counts": {"idle": 0, "busy": 0, "offline": 0}, "errors": 0, "unchecked": []}
    return {"enabled": True, **collect(config, reader, owner, repos)}
