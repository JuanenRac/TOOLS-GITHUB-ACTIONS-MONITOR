# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Lists of GitHub read page by page, and honest about what was cut. Standard library only (block `pagination`).

A list of 100 is a page, not the whole list: a repository can have 148 or 348 workflows, a matrix of 200 jobs, hundreds of open pull requests. Each read here follows the next pages while
the last page was full and the limit of pages has not been reached; the answer says how many it saw (`seen`), how many GitHub says there are when it says so (`total`) and whether
something was left out (`cut`), so the page can write "seen 100 of 348" instead of looking complete. A first page that is not full costs no extra request, so a small repository spends
exactly what it spent before.
"""

DEFAULTS = {"workflow_pages": 3, "job_pages": 2, "collab_pages": 3}
BOUNDS = {"workflow_pages": (1, 20), "job_pages": (1, 20), "collab_pages": (1, 20)}


def settings(config):
    block = config.get("pagination") if isinstance(config, dict) and isinstance(config.get("pagination"), dict) else {}
    out = {}
    for key, default in DEFAULTS.items():
        value, (low, high) = block.get(key), BOUNDS[key]
        out[key] = value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default
    return out


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def read_pages(read, path, key, per_page, max_pages):
    """{"items", "seen", "total", "cut", "pages"}: `read(path_with_page)` gives the parsed answer; the list is the value of `key` in an object, or the answer itself when `key` is None.
    Stops at a page that is not full, when `total_count` is reached or after `max_pages`. `cut` = the pages ran out while more was there (or may be there)."""
    items, total, pages, last_full, error = [], None, 0, False, None
    joiner = "&" if "?" in path else "?"
    for page in range(1, max(1, int(max_pages)) + 1):
        try:
            data = read(f"{path}{joiner}per_page={per_page}&page={page}")
        except Exception as failure:      # noqa: BLE001 - a page after the first that fails: what was read is kept and the list is said to be cut
            if page == 1:
                raise
            error = str(failure)[:200]
            last_full = True
            break
        pages += 1
        chunk = (data.get(key) if isinstance(data, dict) else None) if key else data
        chunk = chunk if isinstance(chunk, list) else []
        if isinstance(data, dict) and _count(data.get("total_count")) is not None:
            total = _count(data.get("total_count"))
        items.extend(chunk)
        last_full = len(chunk) >= per_page
        if not last_full or (total is not None and len(items) >= total):
            break
    cut = bool(total is not None and len(items) < total) or (total is None and last_full)
    out = {"items": items, "seen": len(items), "total": total, "cut": cut, "pages": pages}
    if error:
        out["error"] = error
    return out
