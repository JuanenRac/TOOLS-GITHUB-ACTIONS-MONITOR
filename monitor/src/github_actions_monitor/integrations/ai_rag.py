# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Light retrieval (`ai.rag.enabled`, OFF): "alerts that look like this one" ranked by the embeddings of a model that runs ON THIS COMPUTER (the "embed" call of the API of Ollama). Only a loopback address is
accepted, so nothing leaves the computer; the index is a file in the data folder of the account with its own size limit, holds vectors and a hash of each text (never the text) and can be deleted at
any time (it is built again). Without a model, or when it does not answer, the deterministic similarity (similar_alerts) is used."""
import hashlib
import json
import math
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from github_actions_monitor.security import private_io, redactor
from github_actions_monitor.util import paths

INDEX_NAME = "ai_rag_index.json"
DEFAULTS = {"enabled": False, "model": "", "url": "http://127.0.0.1:11434", "max_mb": 200}
LOOPBACK = ("127.0.0.1", "localhost", "::1")
BATCH = 32
MAX_TEXT = 600
TIMEOUT = 60


class RagError(RuntimeError):
    """`code`: off, model, address, unreachable, answer."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def settings(raw):
    block = ((raw or {}).get("ai") or {}).get("rag") if isinstance((raw or {}).get("ai"), dict) else None
    block = block if isinstance(block, dict) else {}
    out = dict(DEFAULTS)
    out["enabled"] = block.get("enabled") is True
    for key in ("model", "url"):
        if isinstance(block.get(key), str):
            out[key] = block[key].strip()
    if isinstance(block.get("max_mb"), int) and 10 <= block["max_mb"] <= 100000:
        out["max_mb"] = block["max_mb"]
    return out


def local_url(url):
    parts = urlsplit(url.rstrip("/"))
    if parts.scheme not in ("http", "https") or parts.hostname not in LOOPBACK or parts.username or parts.query:
        raise RagError("address")
    return parts.geturl()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def embed(cfg, texts, opener=None):
    """One vector per text from the local model."""
    if not cfg["model"]:
        raise RagError("model")
    request = urllib.request.Request(local_url(cfg["url"]) + "/api" + "/embed", data=json.dumps({"model": cfg["model"], "input": texts}).encode("utf-8"), headers={"Content-Type": "application/json"})
    opener = opener or urllib.request.build_opener(_NoRedirect(), urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=TIMEOUT) as reply:
            vectors = json.loads(reply.read(32 << 20).decode("utf-8"))["embeddings"]
    except (urllib.error.URLError, OSError):
        raise RagError("unreachable") from None
    except (ValueError, KeyError, TypeError):
        raise RagError("answer") from None
    if not isinstance(vectors, list) or len(vectors) != len(texts) or not all(isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v) for v in vectors):
        raise RagError("answer")
    return vectors


def text_of(alert):
    return redactor.redact(" ".join(str(alert.get(k) or "") for k in ("code", "repo", "title", "cause")))[:MAX_TEXT]


def index_file():
    return paths.place(INDEX_NAME)


def load(model):
    try:
        data = json.loads(index_file().read_text(encoding="utf-8"))
        return data["items"] if data["model"] == model and isinstance(data["items"], dict) else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def save(model, items, max_mb):
    """Writes the index, dropping the oldest entries until it fits in `max_mb`."""
    keys = list(items)
    while True:
        text = json.dumps({"model": model, "items": {k: items[k] for k in keys}})
        if len(text) <= max_mb * 1024 * 1024 or not keys:
            break
        keys = keys[max(1, len(keys) // 10):]
    target = index_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    private_io.write_private(target, text)


def vectors_for(cfg, alerts, opener=None):
    """[vector] of each alert, asking the model only for the ones that are new or changed."""
    items = load(cfg["model"])
    texts = [text_of(a) for a in alerts]
    hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts]
    missing = {h: t for h, t in zip(hashes, texts) if h not in items}
    keys = list(missing)
    for start in range(0, len(keys), BATCH):
        chunk = keys[start:start + BATCH]
        for key, vector in zip(chunk, embed(cfg, [missing[k] for k in chunk], opener)):
            items[key] = [round(float(x), 5) for x in vector]
    if missing:
        save(cfg["model"], items, cfg["max_mb"])
    return [items.get(h) or [] for h in hashes]


def cosine(a, b):
    if not a or len(a) != len(b):
        return 0.0
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / norm if norm else 0.0


def rank(cfg, found, pool, count, opener=None):
    """The `count` alerts of `pool` closest to `found`, each with its `score` (0..1). RagError when the model cannot be used."""
    if not cfg["enabled"]:
        raise RagError("off")
    others = []
    seen = {found.get("id")}
    for alert in pool:
        if alert.get("id") not in seen:
            seen.add(alert.get("id"))
            others.append(alert)
    others = others[:500]
    if not others:
        return []
    vectors = vectors_for(cfg, [found] + others, opener)
    scored = sorted(zip(others, vectors[1:]), key=lambda pair: -cosine(vectors[0], pair[1]))
    return [dict(alert, score=round(cosine(vectors[0], vector), 3)) for alert, vector in scored[:count] if cosine(vectors[0], vector) > 0]
