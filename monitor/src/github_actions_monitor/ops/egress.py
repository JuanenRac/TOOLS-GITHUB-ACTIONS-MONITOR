# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The table of the network destinations of the monitor: every host it can call with the CURRENT configuration, what for, the setting that makes it a destination and WHAT FAILS if it is blocked.

  py -3 bin/monitor_cli.py doctor --egress [--json]

For a computer behind a strict outbound policy: open exactly the hosts of the rows marked `active` and nothing else. The monitor has an offline mode (`airgapped`), and then no row is active.
A test compares this table with the hosts the code names, so a new destination cannot be added without a row. Read only: it changes nothing and calls nothing."""
import re
from urllib.parse import urlsplit

from github_actions_monitor import families

#: id -> (hosts that do not depend on the configuration, setting that makes the row active (None = always), kind of the consequence text)
ROWS = (
    ("github_api", ("api.github.com",), None),
    ("github_download", ("github.com", "objects.githubusercontent.com"), "updates.check"),
    ("github_raw", ("raw.githubusercontent.com",), "lint.anonymous_public"),
    ("github_status", ("www.githubstatus.com",), "github_status.enabled"),
    ("ntfy", ("ntfy.sh",), "notify.channels.ntfy.enabled"),
    ("telegram", ("api.telegram.org",), "notify.channels.telegram.enabled"),
    ("chat_webhooks", ("discord.com", "hooks.slack.com", "webhook.office.com"), "notify.channels.discord.enabled|notify.channels.slack.enabled|notify.channels.teams.enabled"),
    ("ai", (), "ai.provider"),
    ("otlp", (), "otlp.enabled"),
    ("siem", (), "siem.sinks"),
) + tuple((row.id, tuple(row.hosts), row.setting) for row in families.egress())      # the destinations of the parts (families/)
LINK_ONLY = frozenset({"github.com", "www.python.org", "docs.anthropic.com", "platform.openai.com", "ollama.com", "localai.io", "lmstudio.ai", "jan.ai", "docs.x.ai", "docs.vllm.ai", "docs.together.ai",
                       "docs.perplexity.ai", "docs.mistral.ai", "docs.fireworks.ai", "docs.cohere.com", "console.groq.com", "api-docs.deepseek.com", "ai.google.dev", "example.invalid", "openrouter.ai", "owasp.org", "scorecard.dev", "www.w3.org", "adaptivecards.io"})
DYNAMIC_HOSTS = frozenset({"api.anthropic.com", "api.openai.com"})      # hosts of the AI provider rows that are named in the code as the default of a provider
HOST_RE = re.compile(r"https?://([A-Za-z0-9.-]+\.[a-z]{2,})")


def _get(config, dotted):
    node = config
    for part in dotted.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def _host(url):
    try:
        return (urlsplit(str(url)).hostname or "").lower()
    except ValueError:
        return ""


def _is_remote(host):
    return bool(host) and host not in ("localhost", "127.0.0.1", "::1") and not host.startswith(("10.", "192.168.", "172.16.", "172.17."))


def _declared(row_id):
    return next((row for row in families.egress() if row.id == row_id), None)


def _dynamic_hosts(row_id, config):
    """The hosts that come from the configuration (the provider of the AI, the endpoint of OTLP, the sinks of the SIEM)."""
    part = _declared(row_id)
    if part is not None and part.hosts_from is not None:
        return sorted({h for h in part.hosts_from(config) if _is_remote(h)})
    if row_id == "ai":
        provider = _get(config, "ai.provider")
        base = _get(config, "ai.base_url")
        if base:
            return [h for h in [_host(base)] if _is_remote(h)]
        return {"anthropic": ["api.anthropic.com"], "openai-compatible": ["api.openai.com"], "copilot": ["api.github.com"]}.get(provider, [])
    if row_id == "otlp":
        return [h for h in [_host(_get(config, "otlp.endpoint"))] if _is_remote(h)]
    if row_id == "siem":
        sinks = _get(config, "siem.sinks")
        return sorted({h for s in (sinks if isinstance(sinks, list) else []) if isinstance(s, dict) and s.get("enabled") is True for h in [_host(s.get("url"))] if _is_remote(h)})
    return []


def _active(config, rule):
    if rule is None:
        return True
    for key in rule.split("|"):
        value = _get(config, key)
        if key == "ai.provider":
            if value in ("anthropic", "openai-compatible", "copilot") or (value == "ollama" and _is_remote(_host(_get(config, "ai.base_url")))):
                return True
        elif key == "siem.sinks":
            if _dynamic_hosts("siem", config):
                return True
        elif key == "updates.check":
            if value is not False:
                return True
        elif value is True:
            return True
    return False


def table(config):
    """[{"id", "hosts", "active", "setting", "airgapped"}] for the configuration (a dictionary). In the offline mode nothing is active."""
    config = config if isinstance(config, dict) else {}
    airgapped = config.get("airgapped") is True
    rows = []
    for row_id, hosts, rule in ROWS:
        found = sorted(set(hosts) | set(_dynamic_hosts(row_id, config)))
        part = _declared(row_id)
        on = part.active(config) is True if part is not None and part.active is not None else _active(config, rule)
        active = (not airgapped) and on and bool(found)
        rows.append({"id": row_id, "hosts": found, "active": active, "setting": rule or "", "airgapped": airgapped})
    return rows


def lines(config, translate):
    """The table as text for the console, in the language of `translate` (a function key -> text)."""
    out = []
    for row in table(config):
        mark = translate("egress.active") if row["active"] else translate("egress.inactive")
        out.append(f"[{mark}] {', '.join(row['hosts']) or '-'}")
        out.append("    " + translate("egress.use." + row["id"]))
        out.append("    " + translate("egress.fail." + row["id"]))
        if row["setting"] and not row["active"]:
            out.append("    " + translate("egress.when", setting=row["setting"].replace("|", " / ")))
    return out
