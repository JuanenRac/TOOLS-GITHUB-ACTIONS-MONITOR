# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The ONE cleaner of text that leaves the monitor towards an AI, a feed, an endpoint, a hook or a provider: tokens, keys, credentials in addresses, e-mail addresses, IP addresses,
the home folder of a person and long opaque strings. By pattern: it lowers the risk, it is not a guarantee. Every output that an AI can read goes through `redact()`, `redact_data()` or
`redact_json()`; nothing else in the product defines its own list of secret patterns."""
import json
import re
from pathlib import Path

_SECRETS = [
    (re.compile(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"), "[pem]"),
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@"), r"\1[credentials]@"),      # user:password@host in an address
    (re.compile(r"(?i)\bhooks\.slack\.com/services/[A-Za-z0-9/_-]+"), "hooks.slack.com/services/[webhook]"),
    (re.compile(r"(?i)\bdiscord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9._-]+"), "discord.com/api/webhooks/[webhook]"),
    (re.compile(r"\bbot\d{6,}:[A-Za-z0-9_-]{20,}"), "bot[token]"),
    (re.compile(r"""(?i)(x-monitor-access|monitor_access)(["']?\s*[:=]\s*)(?:"[^"\n]{0,300}"|'[^'\n]{0,300}'|["']?[^\s"',;]+)"""), r"\1\2[secret]"),
    (re.compile(r"(?<![A-Za-z0-9])(?:glpat-[A-Za-z0-9_-]{10,}|npm_[A-Za-z0-9]{16,}|pypi-[A-Za-z0-9_-]{16,})"), "[token]"),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,})"), "[token]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{12,}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,})"), "[key]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "[jwt]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 [secret]"),
    (re.compile(r"""(?i)([A-Za-z0-9_.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|authorization)[A-Za-z0-9_.-]*)(["']?\s*[:=]\s*)(?:"[^"\n]{0,300}"|'[^'\n]{0,300}'|["']?[^\s"',;]+)"""), r"\1\2[secret]"),      # DB_PASSWORD=, AWS_SECRET_ACCESS_KEY=, MYSQL_PWD=
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[ip]"),
    (re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}\b"), "[ip]"),
    (re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s]+"), "~"),
    (re.compile(r"/(?:home|Users)/[^/\s]+"), "~"),
    (re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,}(?![0-9A-Fa-f])"), "[hex]"),
    (re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}"), "[blob]"),
]


# The address of a page of GitHub (a repository, a run, a commit, an issue, a file): public, it carries no secret and the AI needs it whole. Only a closed list of SHAPES passes untouched and the
# address is cut at the first character outside [A-Za-z0-9._/-]: what follows (a query, a fragment, an encoded character, a colon, a comma...) is cleaned like any other text.
_GITHUB_URL = re.compile(r"https://(?P<api>api\.)?github\.com(?![A-Za-z0-9@:-]|\.[A-Za-z0-9])(?P<path>(?:/[A-Za-z0-9._-]*)*)")
_SEG = r"[A-Za-z0-9._-]*[A-Za-z0-9_-]"
_GITHUB_SHAPE = re.compile(
    rf"(?:/repos)?/{_SEG}(?:/{_SEG}(?:/actions/runs/\d+(?:/job/\d+|/attempts/\d+)?|/commit/[0-9A-Fa-f]{{40}}|/(?:issues|pull)/\d+|/(?:blob|tree)(?=/)(?:/{_SEG})*)?)?(?![A-Za-z0-9_-])")
_OPAQUE_SEGMENT = re.compile(r"[0-9A-Fa-f]{32,}|[A-Za-z0-9_-]{40,}")      # what the rules of the text turn into [hex] and [blob]


def _github_safe(match):
    """The part of a github.com address that may pass untouched: the host and the longest prefix of the path that has one of the shapes of the list, with no segment that looks like a secret."""
    path = match.group("path") or ""
    shape = _GITHUB_SHAPE.match(path)
    if not shape or not path.startswith("/"):
        return "https://" + ("api." if match.group("api") else "") + "github.com"
    kept = shape.group(0)
    parts = kept.split("/")
    for index, part in enumerate(parts):
        if index and _OPAQUE_SEGMENT.search(part) and not (index >= 2 and parts[index - 1] == "commit"):      # the 40 hexadecimal digits of a commit are public; any other opaque segment is not
            kept = "/".join(parts[:index])
            break
    return "https://" + ("api." if match.group("api") else "") + "github.com" + kept


def redact(text, limit=None):
    """The text without tokens, keys, e-mail addresses, IP addresses, the home folder of a person and long opaque strings. The addresses of github.com that have the shape of a repository, a run,
    a commit, an issue, a pull request or a file pass untouched (a run link is longer than the 40 characters of an opaque string and used to be cut to [blob]); nothing after the first character
    outside [A-Za-z0-9._/-] does."""
    out = str(text or "").replace("\ue000", "").replace("\ue001", "")      # the marks below belong to this function only
    home = str(Path.home())
    for variant in {home, home.replace("\\", "/")}:
        if len(variant) > 3:
            out = out.replace(variant, "~")
    kept = []

    def keep(match):
        url = _github_safe(match)
        if match.string[match.end():match.end() + 1] == "@" or any(pattern.search(url) for pattern, replacement in _SECRETS if replacement not in ("[hex]", "[blob]")):      # an address that goes on as an e-mail, or that itself holds a token, a key, a home folder...: it is cleaned like any text
            return match.group(0)
        kept.append(url)
        return f"\ue000{len(kept) - 1}\ue001" + match.group(0)[len(url):]
    out = _GITHUB_URL.sub(keep, out)
    for pattern, replacement in _SECRETS:
        out = pattern.sub(replacement, out)
    for index, url in enumerate(kept):
        out = out.replace(f"\ue000{index}\ue001", url)
    return out[:limit] if limit else out


def redact_data(value, limit=None):
    """The same cleaning for a structure (dict, list, text): every text inside is cleaned ON ITS OWN, keys included, and the structure is serialised afterwards. Never clean a JSON that is already
    written: a value that ends at the quote of its string would take the quote with it and break the document."""
    if isinstance(value, str):
        return redact(value, limit)
    if isinstance(value, dict):
        return {(redact(k) if isinstance(k, str) else k): redact_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_data(v) for v in value]
    return value


def redact_json(value, limit=None, **dumps):
    """JSON of `value` with every text cleaned (see redact_data); `limit` cuts the written text."""
    text = json.dumps(redact_data(value), **({"ensure_ascii": False} | dumps))
    return text[:limit] if limit else text
