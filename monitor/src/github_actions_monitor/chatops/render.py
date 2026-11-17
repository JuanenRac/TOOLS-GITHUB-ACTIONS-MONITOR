# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""How an answer is written for Slack and for Discord: every text that comes from somewhere else (a repository name, a workflow name, a code) goes through `clean` (one short line, no control
characters) and then through the escape of the platform, so a name can never become a mention, a link, a code block or a format. The answers carry no link at all. Standard library only."""
import re

MAX_TEXT = 1800                    # characters of one answer (both platforms accept more; a chat is not a report)
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f​-‏ -‮⁦-⁩﻿]")      # controls, zero-width and direction marks


def clean(value, limit=60):
    """One line of at most `limit` characters from any value: no control characters, spaces collapsed, cut with an ellipsis."""
    text = _CONTROL.sub(" ", str(value if value is not None else ""))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:max(0, limit - 1)] + "…"


def slack_escape(value, limit=60):
    """Slack: `&`, `<` and `>` are the only characters that make a mention, a channel or a link (`<@U1>`, `<!channel>`, `<http://x|y>`); the markup characters (`*`, `_`, `~`, the backtick and `|`) are dropped."""
    text = clean(value, limit)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"[*_~`|]", "", text)


def discord_escape(value, limit=60):
    """Discord: the markdown characters are escaped with a backslash and `@` is followed by a thin space (the answer also asks for no mentions at all)."""
    text = clean(value, limit)
    text = re.sub(r"([\\*_~`|>#\[\]()<:])", r"\\\1", text)
    return text.replace("@", "@ ")


def fit(lines, limit=MAX_TEXT):
    """The lines joined, cut at a line boundary below `limit` characters."""
    out, size = [], 0
    for line in lines:
        if size + len(line) + 1 > limit:
            break
        out.append(line)
        size += len(line) + 1
    return "\n".join(out)


def slack_reply(text):
    """An answer to a slash command that only the person who asked sees."""
    return {"response_type": "ephemeral", "text": text}


def discord_reply(text):
    """An answer to an interaction (type 4) that only the person who asked sees (flag 64) and that mentions nobody."""
    return {"type": 4, "data": {"content": text, "flags": 64, "allowed_mentions": {"parse": []}}}


LINK_RE = re.compile(r"^https://[A-Za-z0-9.-]{1,100}/[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}\Z")      # https://<host>/<owner>/<repository>: the only link an answer may carry


def link(url):
    """`<url>` (the form both platforms show as a link without a preview) when `url` is exactly the address of a repository, else ''. Nothing else is ever turned into a link."""
    if not isinstance(url, str) or not LINK_RE.match(url) or url.rsplit("/", 1)[1] in (".", ".."):
        return ""
    return "<" + url + ">"


ESCAPE = {"slack": slack_escape, "discord": discord_escape}
REPLY = {"slack": slack_reply, "discord": discord_reply}
