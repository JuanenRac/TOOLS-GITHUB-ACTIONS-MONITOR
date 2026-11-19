# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A safe way for the owner to describe what the AI must never see: patterns made only of letters and three wildcards, matched by a plain loop that cannot backtrack catastrophically.

`*` is any run of characters of a word (also none), `?` is one character of a word and `#` is one digit. A pattern describes a WHOLE WORD (a run of characters without spaces): `deploy-*` hides
`deploy-prod-7` and `*.corp-name` hides `db1.corp-name`. It is NOT a regular expression: there are no groups, no alternatives and no nested repeats, so a pattern of the owner cannot make the
monitor hang. The cost is bounded three ways: a pattern is at most 80 characters with at least 3 literal ones and at most 4 stars, a word is looked at up to 2000 characters, and one call
spends at most `STEP_BUDGET` steps; when the budget runs out the rest of the text is hidden (the safe side), never left unchecked."""
import re

MAX_PATTERN = 80
MIN_LITERALS = 3
MAX_STARS = 4
MAX_PATTERNS = 50
WORD_LIMIT = 2000
STEP_BUDGET = 400000
_ALLOWED = re.compile(r"[\w.:/@*?#-]+")
_WORD = re.compile(r"[^\s\"'()\[\]{}<>,;!?]+")      # a word ends at a space, a quote, a bracket or a comma, so "falcon," and (falcon) are the word falcon


def valid(pattern):
    """True when `pattern` is accepted: text of 3 to 80 characters, no spaces, at least 3 literal characters and at most 4 stars."""
    if not isinstance(pattern, str) or not 3 <= len(pattern.strip()) <= MAX_PATTERN or re.search(r"\s", pattern.strip()):
        return False
    pattern = pattern.strip()
    if not _ALLOWED.fullmatch(pattern):      # no brackets, bars, plus signs or dollar signs: a regular expression is refused where it is written, not matched as if it were text
        return False
    return pattern.count("*") <= MAX_STARS and sum(1 for ch in pattern if ch not in "*?#") >= MIN_LITERALS


def clean_list(items):
    """The patterns of a setting that are valid, in lower case, without repeats, at most 50."""
    if not isinstance(items, list):
        return []
    return list(dict.fromkeys(p.strip().lower() for p in items if valid(p)))[:MAX_PATTERNS]


def _same(pc, ch):
    return pc == "?" or (pc == "#" and ch.isdigit()) or pc == ch


def matches(pattern, word, budget):
    """(matched, steps used): the classic two-pointer match with one place to go back to (the last star), so it takes at most len(pattern) * len(word) steps."""
    p = s = 0
    star = -1
    mark = 0
    steps = 0
    n, m = len(pattern), len(word)
    while s < m:
        steps += 1
        if steps > budget:
            return True, steps      # out of budget: treat it as a match (hide), never as safe
        if p < n and pattern[p] != "*" and _same(pattern[p], word[s]):
            p += 1
            s += 1
        elif p < n and pattern[p] == "*":
            star, mark = p, s
            p += 1
        elif star >= 0:
            p = star + 1
            mark += 1
            s = mark
        else:
            return False, steps
    while p < n and pattern[p] == "*":
        p += 1
    return p == n, steps


def hide(text, patterns, mark="[hidden]"):
    """`text` with every word that fits one of the patterns replaced by `mark`. Case does not matter. Out of budget, the words not yet looked at are hidden."""
    patterns = clean_list(list(patterns or ()))
    text = str(text or "")
    if not patterns:
        return text
    budget = STEP_BUDGET
    out = []
    last = 0
    for found in _WORD.finditer(text):
        word = found.group(0).rstrip(".:")      # the full stop that ends a sentence is not part of the word
        if not word:
            continue
        hit = budget <= 0
        if not hit:
            low = word[:WORD_LIMIT].lower()
            for pattern in patterns:
                matched, used = matches(pattern, low, budget)
                budget -= used
                if matched:
                    hit = True
                    break
                if budget <= 0:
                    hit = True
                    break
        out.append(text[last:found.start()])
        out.append(mark if hit else word)
        last = found.start() + len(word)
    out.append(text[last:])
    return "".join(out)
