# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Help panel and the console help: they read docs/help_index.json (built from the real documents by tools/make_help_index.py) and answer from this computer, without Internet.

  topics(lang)            the list of documents with their title in the language (English when a document is not translated)
  topic(id, lang)         one document as safe HTML sections
  search(text, lang)      hits in the language, English for the documents that are not translated
  render(markdown)        a small, SAFE markdown to HTML: every character of the source is escaped first, nothing is executed, images are never loaded, only http(s) links and links to other
                          documents of the index are kept
  console(args, lang)     `--help-topics` / `--help-topics TOPIC` / `--help-topics --search WORDS`: plain text for the terminal
"""
import html
import json
import re
import threading
from pathlib import Path

from github_actions_monitor.util.paths import ROOT as HERE   # the product folder: the data of the person who runs the monitor stays there
INDEX_FILE = HERE / "docs" / "help_index.json"
TAB_TOPICS = {"now": "readme", "sent": "analytics", "charts": "analytics", "repos": "readme", "hist": "readme", "cfg": "settings", "about": "readme", "first": "first_steps", "lite": "lite"}
_lock = threading.Lock()
_cache = {"index": None}
LINK_RE = re.compile(r"\[([^\]]{1,200})\]\(([^)\s]{1,300})(?:\s+\"[^\"]*\")?\)")
MAX_HITS = 30                 # the most results a search ever returns (the page and the console)
CONSOLE_HITS = 20             # the console shows this many and says how many more there are
MAX_RENDER_CHARS = 150_000    # a section longer than this is cut (with a notice): a huge document can not hold the server thread
MAX_RENDER_LINES = 4000
URL_RE = re.compile(r"^https?://[^\s<>\"']{1,300}$")


def index():
    with _lock:
        if _cache["index"] is None:
            try:
                data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            _cache["index"] = data if isinstance(data, dict) and isinstance(data.get("topics"), list) else {"topics": [], "files": {}}
        return _cache["index"]


def _find(topic_id):
    for item in index()["topics"]:
        if item["id"] == topic_id:
            return item
    return None


def _lang_of(item, lang):
    return lang if lang in item["sections"] else "en"


def topics(lang):
    out = []
    for item in index()["topics"]:
        used = _lang_of(item, lang)
        out.append({"id": item["id"], "group": item["group"], "title": item["title"].get(used) or item["id"], "translated": (used == lang or lang == "en") and not (item.get("english_body") and lang != "en")})
    return out


def tab_topic(tab):
    topic = TAB_TOPICS.get(tab, "readme")
    return topic if _find(topic) else "readme"


# --- safe markdown -------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def _inline(text, files):
    """Escapes everything first; then `code`, **bold**, *italic* and the links that are allowed. Images become their alt text."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1), text.replace("\x00", ""))
    holders = []

    def keep(fragment):
        holders.append(fragment)
        return f"\x00{len(holders) - 1}\x00"
    text = re.sub(r"`([^`]+)`", lambda m: keep("<code>" + html.escape(m.group(1), quote=True) + "</code>"), text)

    def link(m):
        label, target = m.group(1), m.group(2)
        safe_label = html.escape(label, quote=True)
        if URL_RE.match(target):
            return keep(f'<a href="{html.escape(target, quote=True)}" target="_blank" rel="noopener noreferrer">{safe_label}</a>')
        name = target.split("#")[0].replace("\\", "/").rsplit("/", 1)[-1]
        if name in files:
            return keep(f'<a href="#help:{html.escape(files[name], quote=True)}" data-topic="{html.escape(files[name], quote=True)}">{safe_label}</a>')
        return safe_label
    text = LINK_RE.sub(link, text)
    text = html.escape(text, quote=True)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: holders[int(m.group(1))], text)


def render(markdown, files=None):
    files = files if files is not None else index().get("files", {})
    text = str(markdown)
    cut = len(text) > MAX_RENDER_CHARS
    if cut:
        text = text[:MAX_RENDER_CHARS]
    lines = text.replace("\r\n", "\n").split("\n")
    if len(lines) > MAX_RENDER_LINES:
        lines, cut = lines[:MAX_RENDER_LINES], True
    return _render_lines(lines, files) + ("<p class=\"cut\">...</p>" if cut else "")


def _render_lines(lines, files):
    out, i = [], 0
    paragraph, listing = [], None

    def flush():
        nonlocal paragraph, listing
        if paragraph:
            out.append("<p>" + _inline(" ".join(paragraph), files) + "</p>")
            paragraph = []
        if listing:
            out.append(f"</{listing}>")
            listing = None
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            flush()
            code, i = [], i + 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                code.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(code), quote=True) + "</code></pre>")
            i += 1
            continue
        if re.match(r"^\s*\|.*\|\s*$", line) and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush()
            cells = lambda row: [c.strip() for c in row.strip().strip("|").split("|")]   # noqa: E731
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append(cells(lines[i]))
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{_inline(c, files)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{_inline(c, files)}</td>" for c in row) + "</tr>" for row in rows) + "</tbody></table>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)
        item = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)$", line)
        if heading:
            flush()
            level = min(6, len(heading.group(1)) + 2)
            out.append(f"<h{level}>{_inline(heading.group(2), files)}</h{level}>")
        elif item:
            kind = "ol" if item.group(1)[0].isdigit() else "ul"
            if listing != kind:
                flush()
                out.append(f"<{kind}>")
                listing = kind
            out.append("<li>" + _inline(item.group(2), files) + "</li>")
        elif line.startswith(">"):
            flush()
            out.append("<blockquote>" + _inline(line.lstrip("> "), files) + "</blockquote>")
        elif re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            flush()
            out.append("<hr>")
        elif not line.strip():
            flush()
        else:
            if listing:
                flush()
            paragraph.append(line.strip())
        i += 1
    flush()
    return "".join(out)


def topic(topic_id, lang):
    """{"id", "title", "lang", "fallback", "plain", "sections": [{"id", "title", "html"}]} or None."""
    item = _find(topic_id)
    if item is None:
        return None
    used = _lang_of(item, lang)
    files = index().get("files", {})
    sections = []
    for slug, title, body in item["sections"][used]:
        if not title and not item.get("plain"):
            body = re.sub(r"\A\s*#\s+[^\n]*\n", "", body, count=1)      # the heading of the document is already the title of the panel
        shown = f"<pre class=\"plain\">{html.escape(body, quote=True)}</pre>" if item.get("plain") else render(body, files)
        sections.append({"id": slug, "title": title, "html": shown})
    return {"id": item["id"], "title": item["title"].get(used) or item["id"], "lang": used, "fallback": used != lang or (bool(item.get("english_body")) and lang != "en"), "plain": bool(item.get("plain")), "sections": sections}


def _snippet(text, words):
    flat = re.sub(r"[#*`|>\[\]()]+", " ", text)
    flat = re.sub(r"\s+", " ", flat).strip()
    low = flat.lower()
    where = min([low.find(w) for w in words if low.find(w) >= 0] or [0])
    start = max(0, where - 50)
    return ("…" if start else "") + flat[start:start + 170] + ("…" if start + 170 < len(flat) else "")


def search(text, lang, limit=MAX_HITS):
    limit = max(1, min(int(limit) if isinstance(limit, int) else MAX_HITS, MAX_HITS))
    words = [w for w in re.split(r"\s+", str(text or "").lower().strip()) if w][:6]
    if not words or max(len(w) for w in words) < 2:
        return []
    hits = []
    for item in index()["topics"]:
        used = _lang_of(item, lang)
        for slug, title, body in item["sections"][used]:
            hay = (title + "\n" + body).lower()
            if not all(w in hay for w in words):
                continue
            score = sum(10 for w in words if w in title.lower()) + sum(min(hay.count(w), 5) for w in words) + (6 if all(w in item["title"].get(used, "").lower() for w in words) else 0)
            hits.append((score, {"topic": item["id"], "section": slug, "topic_title": item["title"].get(used) or item["id"], "title": title or item["title"].get(used) or "", "snippet": _snippet(body, words),
                                 "fallback": used != lang}))
    hits.sort(key=lambda pair: -pair[0])
    return [hit for _score, hit in hits[:limit]]


def plain_text(topic_id, lang):
    item = _find(topic_id)
    if item is None:
        return None
    used = _lang_of(item, lang)
    parts = [item["title"].get(used) or item["id"], "=" * 40]
    for _slug, title, body in item["sections"][used]:
        if title:
            parts += ["", title, "-" * min(len(title), 40)]
        parts += ["", body]
    return "\n".join(parts).strip() + "\n"


def console(args, lang, translate):
    """Text for `--help-topics [TOPIC | --search WORDS]` (returns (exit code, text))."""
    args = [a for a in args if a]
    if args[:1] == ["--search"]:
        hits = search(" ".join(args[1:]), lang)
        if not hits:
            return 1, translate("help.none") + "\n"
        shown = "\n".join(f"{h['topic']}#{h['section']}  {h['topic_title']} / {h['title']}\n    {h['snippet']}" for h in hits[:CONSOLE_HITS]) + "\n"
        return 0, shown + (translate("help.more", n=len(hits) - CONSOLE_HITS) + "\n" if len(hits) > CONSOLE_HITS else "")
    if args:
        name = args[0].lower().replace("-", "_")
        text = plain_text(name, lang)
        if text is None:
            hits = search(" ".join(args), lang, 8)
            if not hits:
                return 1, translate("help.unknown", topic=args[0]) + "\n"
            return 0, "\n".join(f"{h['topic']}#{h['section']}  {h['topic_title']} / {h['title']}" for h in hits) + "\n"
        found = _find(name)
        used = _lang_of(found, lang)
        return 0, (translate("help.fallback") + "\n\n" if used != lang or (found.get("english_body") and lang != "en") else "") + text
    rows = [f"  {t['id']:<16} {t['title']}" for t in topics(lang)]
    return 0, translate("help.list_head") + "\n" + "\n".join(rows) + "\n\n" + translate("help.list_tail") + "\n"
