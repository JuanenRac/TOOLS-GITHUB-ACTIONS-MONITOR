# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Reads the source of the page as text and says what is defined twice. A second definition silently replaces the first one (the box of the Quota tab was replaced by the async box of the Basic tab
and Settings stopped drawing), whatever the form it takes: a declaration with an indent, a declaration with `async`, or an assignment to the name of a function (a `const` with that name does not even parse: the browser test catches it)."""
import re

#: the one assignment to a declared function that is deliberate: the page wraps renderSent to refresh the figures after it
WRAPPERS = frozenset({"renderSent"})
DECLARATION = re.compile(r"(?m)^[ \t]*(?:async[ \t]+)?function[ \t]+([A-Za-z_$][\w$]*)")
ASSIGNMENT = re.compile(r"(?:^|[;{}(,\s])(?:window\.|globalThis\.|self\.)?([A-Za-z_$][\w$]*)[ \t]*=[ \t]*(?:async\b|function\b|\([^()]*\)[ \t]*=>|[A-Za-z_$][\w$]*[ \t]*=>)", re.M)


def duplicates(page):
    """Sorted list of what is wrong: 'name (declared N times)', or 'name (assigned again)'."""
    names = DECLARATION.findall(page)
    declared = set(names)
    found = [f"{n} (declared {names.count(n)} times)" for n in sorted(declared) if names.count(n) > 1]
    found += [f"{n} (assigned again)" for n in sorted({m.group(1) for m in ASSIGNMENT.finditer(page)} & declared - WRAPPERS)]
    return found
