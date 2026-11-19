# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The air-gapped mode of the AI (`ai.airgapped`, off by default): with it on, the AI of the monitor talks only to a model that runs on this computer or on a private address the owner declared
(`ai.airgap_hosts`), never to the internet. Nothing is left to the provider: an address that is public, a provider that is a cloud service (Anthropic, Copilot), a name that is not declared and a
redirect to another host are all refused BEFORE a connection is opened, so no socket leaves. The general switch `airgapped` (and MONITOR_AIRGAPPED) turns this mode on too.

Standard library only; the check is a pure function over the configuration and an address, used by every place that reaches a provider (the chat, the list of models, the test of a model)."""
import ipaddress
import os
from urllib.parse import urlparse

from github_actions_monitor import i18n

CLOUD_ONLY = ("copilot",)      # a provider with no address of its own: a service of the internet by definition (the others are looked at by the address they will use)
PRIVATE_SUFFIXES = (".local", ".lan", ".internal", ".home.arpa", ".localdomain")
LOOPBACK_NAMES = ("localhost",)


def message(reason, host=""):
    """The sentence for a refusal, in the language of the monitor."""
    return i18n.t("ai.airgap_" + reason, host=host or "-") if reason in ("cloud_provider", "host_not_allowed", "no_address") else str(reason)


class Airgapped(RuntimeError):
    """The mode is on and the address (or the provider) is not on this computer or on a declared private address. Its text is the sentence for the person."""

    def __init__(self, reason, host=""):
        super().__init__(message(reason, host))
        self.reason = reason
        self.host = host


def on(ai_cfg, top=None):
    """True when the mode is on: `ai.airgapped`, the general `airgapped` of the configuration or the variable MONITOR_AIRGAPPED."""
    if isinstance(ai_cfg, dict) and ai_cfg.get("airgapped") is True:
        return True
    if isinstance(top, dict) and top.get("airgapped") is True:
        return True
    return os.environ.get("MONITOR_AIRGAPPED", "").strip().lower() in ("1", "true", "yes")


def hosts(ai_cfg):
    """The private addresses and names the owner declared (lower case, at most 50)."""
    raw = ai_cfg.get("airgap_hosts") if isinstance(ai_cfg, dict) else None
    return [h.strip().lower() for h in raw if isinstance(h, str) and h.strip()][:50] if isinstance(raw, list) else []


def _is_loopback(host):
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _is_private_name(host):
    try:
        address = ipaddress.ip_address(host)
        return address.is_private and not address.is_loopback and not address.is_unspecified and not address.is_multicast
    except ValueError:
        return "." not in host or host.endswith(PRIVATE_SUFFIXES)      # a name inside the local network, never a name of the internet


def allowed(host, declared):
    """True for a host on this computer, or a private address or local name that the owner declared."""
    host = (host or "").strip("[]").lower()
    if not host:
        return False
    return _is_loopback(host) or (host in declared and _is_private_name(host))


def problem(ai_cfg, url=None, provider=None, top=None):
    """'' when the call may go; otherwise the code of the refusal (`cloud_provider`, `host_not_allowed`, `no_address`). `url` is the address about to be opened; `provider` the kind of provider."""
    if not on(ai_cfg, top):
        return ""
    provider = provider or (ai_cfg.get("provider") if isinstance(ai_cfg, dict) else "")
    if provider in CLOUD_ONLY:
        return "cloud_provider"
    if url is None:
        return ""
    host = (urlparse(url).hostname or "")
    if not host:
        return "no_address"
    return "" if allowed(host, hosts(ai_cfg)) else "host_not_allowed"


def check(ai_cfg, url=None, provider=None, top=None):
    """Raises Airgapped when `problem` finds one."""
    why = problem(ai_cfg, url, provider, top)
    if why:
        raise Airgapped(why, (urlparse(url).hostname or "") if url else "")


def target(ai_cfg):
    """The address the configured provider would use (None for a provider that has none)."""
    provider = ai_cfg.get("provider") if isinstance(ai_cfg, dict) else ""
    if provider == "ollama":
        return ai_cfg.get("ollama_url") or None
    if provider == "openai-compatible":
        return ai_cfg.get("base_url") or None
    if provider == "anthropic":
        return ai_cfg.get("base_url") or "https://api.anthropic.com"
    return None


def report(ai_cfg, top=None):
    """What `doctor` and the page say: {on, provider, target, allowed_hosts, problem}. `problem` is '' when the configured provider may be called."""
    return {"on": on(ai_cfg, top), "provider": ai_cfg.get("provider", "none"), "target": target(ai_cfg), "allowed_hosts": hosts(ai_cfg),
            "problem": "" if ai_cfg.get("provider", "none") == "none" else problem(ai_cfg, target(ai_cfg), top=top)}
