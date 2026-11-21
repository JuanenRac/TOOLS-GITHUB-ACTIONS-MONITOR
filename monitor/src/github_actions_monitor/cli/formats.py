# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The ways the command line writes an answer (`--format`): text (the lines each command has always written), table, plain, json and ndjson. No dependency on the rest of the monitor.

  text    what every command wrote before; the default
  table   columns aligned to the width of the terminal (wide characters of Japanese and Chinese count as two cells); no colour, so NO_COLOR is respected by construction
  plain   one record per line, fields separated by a tab, no header: stable for grep, cut and awk
  json    the document {"ok", "exit", "data"} (the same as --json)
  ndjson  one JSON object per line, one per record

A command that answers with a list gives its records (alerts, accounts, repositories, events, ...); a command that answers with one thing (status, health) gives a single record made of its plain
fields. The records are taken from the same document that --json prints, so the three structured formats never disagree.
"""
import json
import unicodedata

FORMATS = ("text", "table", "plain", "json", "ndjson")
DEFAULT_FORMAT = "text"

# command -> (key of the list in the answer, columns). A column is a key of the record or a tuple of alternatives (the first one that has a value).
LISTS = {
    "alerts": ("alerts", ("sentinel", "level", "code", "repo", "title", "muted_until")),
    "proposals": ("proposals", ("id", "status", "action", "repo", "command", "expires_in_s")),
    "accounts": ("accounts", ("id", "state", "repos", "running", "failing")),
    "team": ("ranking", ("state", "risk", "repo", "alerts", "red_workflows")),
    "live": ("events", ("at", "repo", ("name", "workflow", "event"), "status", "conclusion")),
    "lessons": ("categories", ("category", "n24", "n7", "trend")),
}
LIST_FALLBACKS = (("failures", ("category", "repo", "workflow", "root_cause")), ("repos", ("repo", "score", "letter", "runs", "state")), ("points", ("at", "score")))


def _cell(value):
    """One cell as one line of text: no tab, no line break; None is empty; True and False are words."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    from . import terminal      # text from GitHub may carry escape sequences: a cell never does
    return " ".join(terminal.clean(str(value)).replace("\t", " ").split())


def _pick(record, column):
    if isinstance(column, tuple):
        for name in column:
            if record.get(name) not in (None, ""):
                return name, record.get(name)
        return column[0], None
    return column, record.get(column)


def records(command, payload):
    """(columns, rows) of an answer: rows are dicts keyed by column. The list the command is known for, else the first list of records it has, else one record of its plain fields."""
    if not isinstance(payload, dict):
        return ["value"], [{"value": payload}]
    wanted = LISTS.get(command)
    for key, columns in ([wanted] if wanted else []) + list(LIST_FALLBACKS):
        rows = payload.get(key)
        if not isinstance(rows, list) or (not rows and not (wanted and key == wanted[0])):
            continue
        if not all(isinstance(row, dict) for row in rows):
            return ["value"], [{"value": row} for row in rows]
        return [c[0] if isinstance(c, tuple) else c for c in columns], [dict(_pick(row, c) for c in columns) for row in rows]
    flat = {k: v for k, v in payload.items() if not isinstance(v, (dict, list))}
    for key, inner in payload.items():      # one level down: allowance.remaining -> allowance_remaining
        if isinstance(inner, dict):
            for sub, value in inner.items():
                if not isinstance(value, (dict, list)):
                    flat[key + "_" + sub] = value
    return list(flat), [flat]


def width_of(text):
    """Cells a text takes in a terminal: wide and fullwidth characters count as two, combining marks as none."""
    total = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        total += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return total


def clip(text, cells):
    """The text cut to `cells` cells; a cut text ends in an ellipsis so that nobody reads half a word as a whole one."""
    if width_of(text) <= cells:
        return text
    out, used = "", 0
    for char in text:
        step = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in ("W", "F") else 1)
        if used + step > max(1, cells - 1):
            break
        out, used = out + char, used + step
    return out + "…"


def terminal_width(default=100):
    """Columns of the terminal; with none (a redirect, a pipe) COLUMNS or 80, so the same command writes the same table everywhere."""
    from . import terminal
    return terminal.width(default=terminal.DEFAULT_WIDTH if default == 100 else default)


def table(columns, rows, width=None, color=False):
    """The rows as aligned columns that fit `width` cells: the widest columns give way first, never below 8 cells. The header is the names of the columns."""
    width = width or terminal_width()
    cells = [[_cell(row.get(c)) for c in columns] for row in rows]
    sizes = [max([width_of(c)] + [width_of(line[i]) for line in cells]) for i, c in enumerate(columns)]
    gap = 2
    while sum(sizes) + gap * (len(sizes) - 1) > width and max(sizes) > 8:
        sizes[sizes.index(max(sizes))] -= 1

    def line(values):
        parts = []
        for value, size in zip(values, sizes):
            value = clip(value, size)
            parts.append(value + " " * (size - width_of(value)))
        return (" " * gap).join(parts).rstrip()
    from . import terminal
    return "\n".join([terminal.bold(line(columns), color), line(["-" * min(s, 20) for s in sizes])] + [line(r) for r in cells])


def plain(columns, rows):
    return "\n".join("\t".join(_cell(row.get(c)) for c in columns) for row in rows)


def ndjson(rows):
    return "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)


def document(code, payload, ascii_only=False):
    """The document of --json, written as it has always been."""
    return json.dumps({"ok": code == 0, "exit": code, "data": payload}, ensure_ascii=ascii_only, indent=1)


def render(fmt, command, payload, lines, code, ascii_only=False, width=None, color=False):
    """The text a command prints for the chosen format. An unknown format is the text of the command (never a traceback)."""
    if fmt == "json":
        return document(code, payload, ascii_only)
    if fmt == "text" or fmt not in FORMATS:
        return "\n".join(lines)
    from . import terminal
    columns, rows = records(command, payload)
    if fmt == "ndjson":
        return ndjson(rows)
    if fmt == "plain":
        return plain(columns, rows)
    return table(columns, rows, width, color) if rows else terminal.clean("\n".join(lines))


def choose(flag_format, flag_json, configured=None, env=None):
    """The format in force: --format, then --json, then `cli.default_format`, then text. NO_COLOR changes nothing because nothing here writes colour."""
    if flag_format in FORMATS:
        return flag_format
    if flag_json:
        return "json"
    if configured in FORMATS:
        return configured
    return DEFAULT_FORMAT


def configured_format(raw):
    """`cli.default_format` of the configuration (a dictionary), or text when it is missing or wrong."""
    value = ((raw or {}).get("cli") or {}).get("default_format") if isinstance(raw, dict) else None
    return value if value in FORMATS else DEFAULT_FORMAT
