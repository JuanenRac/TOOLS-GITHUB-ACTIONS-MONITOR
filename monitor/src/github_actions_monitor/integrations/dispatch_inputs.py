# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The inputs a workflow asks for when it is fired by hand (`on: workflow_dispatch: inputs:`), listed from the text of the workflow file. Nothing is run and nothing is sent: `plan --inputs` of the
batch dispatcher reads the file of the commit that is checked out (`git show`), and this module only reads its text.

A small reader for the shape GitHub documents, with the standard library only (no YAML package): a block `inputs:` under `workflow_dispatch:` under `on:`, each input with `description`, `required`,
`default`, `type` (string, boolean, choice, number, environment) and, for a choice, `options`. A flow style (`inputs: {a: {...}}`) or an anchor is not read: the answer is then `None` ("could not be
read"), never a guess, so a caller can tell "no inputs" (`[]`) from "unknown" (`None`).
"""
import re

KEY_RE = re.compile(r"^(\s*)(?:\"([^\"]+)\"|'([^']+)'|([A-Za-z0-9_.-]+))\s*:\s*(.*?)\s*$")
TYPES = ("string", "boolean", "choice", "number", "environment")
MAX_INPUTS = 25      # GitHub allows 25 inputs


def _clean(value):
    value = re.sub(r"\s+#.*$", "", value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value[:200]


def _lines(text):
    for raw in str(text).replace("\r\n", "\n").split("\n"):
        if raw.strip() and not raw.lstrip().startswith("#"):
            yield raw.rstrip()


def _key(line):
    m = KEY_RE.match(line)
    if not m:
        return None
    return len(m.group(1)), m.group(2) or m.group(3) or m.group(4), m.group(5)


def parse(text):
    """[{"name", "type", "required", "default", "description", "options"}] for the manual inputs of the workflow; [] when it takes none or is not fired by hand; None when it could not be read."""
    lines = list(_lines(text))
    start = next((i for i, ln in enumerate(lines) if (_key(ln) or (0, "", ""))[1] == "on" and _key(ln)[0] == 0), None)
    if start is None:
        return []
    head = _key(lines[start])
    if head[2] and head[2] != "":      # `on: push` or `on: [push, workflow_dispatch]` or a flow mapping: no block of inputs to read
        return None if "{" in head[2] and "workflow_dispatch" in head[2] else []
    block = []
    for ln in lines[start + 1:]:
        k = _key(ln)
        if k is None and not ln.startswith(" "):
            break
        if ln and not ln.startswith((" ", "\t")):
            break
        block.append(ln)
    dispatch = next((i for i, ln in enumerate(block) if (_key(ln) or (0, "", ""))[1] == "workflow_dispatch"), None)
    if dispatch is None:
        return []
    base = _key(block[dispatch])[0]
    if _key(block[dispatch])[2] not in ("", "~", "null"):
        return None if "{" in _key(block[dispatch])[2] else []
    inner = []
    for ln in block[dispatch + 1:]:
        k = _key(ln)
        if (k and k[0] <= base) or (not k and len(ln) - len(ln.lstrip()) <= base):
            break
        inner.append(ln)
    at = next((i for i, ln in enumerate(inner) if (_key(ln) or (0, "", ""))[1] == "inputs"), None)
    if at is None:
        return []
    ibase = _key(inner[at])[0]
    if _key(inner[at])[2] not in ("", "~"):
        return None
    inputs, current, options_for = [], None, None
    for ln in inner[at + 1:]:
        k = _key(ln)
        indent = len(ln) - len(ln.lstrip())
        if indent <= ibase:
            break
        if k is None:
            item = ln.strip()
            if options_for is not None and item.startswith("- "):
                options_for["options"].append(_clean(item[2:]))
            continue
        level, name, value = k
        if current is None or level <= current["_level"]:
            if current is not None and level < current["_level"]:
                break
            current = {"name": name[:100], "type": "string", "required": False, "default": None, "description": "", "options": [], "_level": level}
            inputs.append(current)
            options_for = None
            if value:
                return None      # `name: {…}` in flow style
            continue
        value = _clean(value)
        if name == "type":
            current["type"] = value if value in TYPES else "string"
        elif name == "required":
            current["required"] = value.lower() == "true"
        elif name == "default":
            current["default"] = value
        elif name == "description":
            current["description"] = value
        elif name == "options":
            options_for = current
            if value.startswith("["):
                current["options"] = [_clean(x) for x in value.strip("[]").split(",") if x.strip()]
                options_for = None
    for item in inputs:
        item.pop("_level", None)
        item["options"] = item["options"][:50]
    return inputs[:MAX_INPUTS]


def describe(item, required_word="required", optional_word="optional"):
    """One line for the screen: `name (type, required) default=x [options] - description`; the two words are passed in so the caller can translate them."""
    extra = f" [{', '.join(item['options'])}]" if item.get("options") else ""
    default = f" default={item['default']}" if item.get("default") not in (None, "") else ""
    text = f" - {item['description']}" if item.get("description") else ""
    return f"{item['name']} ({item['type']}, {required_word if item.get('required') else optional_word}){default}{extra}{text}"
