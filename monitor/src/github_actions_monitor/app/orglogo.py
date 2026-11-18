# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The logo of the organization that the wall screens may show (docs/SCREENS.md). One image, uploaded in Settings, kept in data/ of this computer and never in the configuration.

  kind_of(data)        'png', 'jpg', 'webp' or 'svg' from the first bytes of the file (the name and the content type that came with it are not believed)
  svg_problem(data)    why an SVG is refused (a script, an event handler, a link to somewhere else, an external resource, a document type), or None
  validate(data)       (kind, None) for a file the monitor accepts, (None, reason) for one it does not; at most 1 MB
  save(data) / remove() / load() / info()   the file org_logo.<kind> in data/, written atomically; only one exists at a time

The image is only ever sent back with its real type, `nosniff` and a content security policy that forbids everything, and the wall screens show it in an <img>, which never runs a script. Standard library only."""
import hashlib
import re
import struct
import threading
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.util import paths

MAX_BYTES = 1024 * 1024
TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "svg": "image/svg+xml"}
NAME = "org_logo"
MAX_PIXELS = 100_000_000      # a 10000 x 10000 picture would take a browser's memory to draw a corner of 160 x 64
LOCK = threading.Lock()
_SVG_BAD = (re.compile(rb"<\s*script", re.I), re.compile(rb"<\s*foreignObject", re.I), re.compile(rb"<\s*(iframe|object|embed|audio|video|canvas|link|meta|base|form|input|image\b[^>]*(href|src))", re.I),
            re.compile(rb"\bon[a-z]+\s*=", re.I), re.compile(rb"javascript\s*:", re.I), re.compile(rb"data\s*:\s*text/html", re.I), re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.I),
            re.compile(rb"<\?xml-stylesheet", re.I), re.compile(rb"@import", re.I), re.compile(rb"url\s*\(\s*(?!['\"]?\s*#)", re.I), re.compile(rb"expression\s*\(", re.I))
_HREF = re.compile(rb"(?:xlink:)?href\s*=\s*([\"'])(.*?)\1", re.I | re.S)


def kind_of(data):
    """The real type of a picture, from its first bytes; None when it is not one of the four."""
    head = bytes(data[:16])
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    text = bytes(data[:2048]).lstrip(b"\xef\xbb\xbf \t\r\n")
    if text.startswith((b"<svg", b"<?xml", b"<!--")) and re.search(rb"<svg[\s>]", bytes(data[:8192]), re.I):
        return "svg"
    return None


def svg_problem(data):
    """None for an SVG that holds only drawing, else a short word for what is wrong with it."""
    raw = bytes(data)
    if b"\x00" in raw:
        return "binary"
    for bad in _SVG_BAD:
        if bad.search(raw):
            return "active"
    for found in _HREF.finditer(raw):
        if not found.group(2).strip().startswith(b"#"):
            return "link"      # a picture that points at another file or address would load something the person never uploaded
    if not re.search(rb"<svg[\s>]", raw, re.I) or not re.search(rb"</svg\s*>\s*\Z", raw.rstrip() + b"\n", re.I | re.S):
        return "not_svg"
    return None


def _png_size(data):
    return struct.unpack(">II", data[16:24]) if len(data) >= 24 and data[12:16] == b"IHDR" else None


def _pixels(kind, data):
    """Width and height when they can be read cheaply; None when not (the byte limit still holds)."""
    try:
        if kind == "png":
            return _png_size(data)
        if kind == "webp" and data[12:16] == b"VP8X" and len(data) >= 30:
            return (1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little"))
        if kind == "jpg":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    return (struct.unpack(">H", data[i + 7:i + 9])[0], struct.unpack(">H", data[i + 5:i + 7])[0])
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    except (struct.error, IndexError):
        return None
    return None


def validate(data):
    """(kind, None) when the bytes are a logo the monitor accepts, else (None, reason): empty, too_big, type, active, link, not_svg, binary, pixels."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        return None, "empty"
    if len(data) > MAX_BYTES:
        return None, "too_big"
    kind = kind_of(data)
    if kind is None:
        return None, "type"
    if kind == "svg":
        problem = svg_problem(data)
        return (None, problem) if problem else (kind, None)
    size = _pixels(kind, bytes(data))
    if size is not None and (size[0] < 1 or size[1] < 1 or size[0] * size[1] > MAX_PIXELS):
        return None, "pixels"
    return kind, None


def _folder():
    return paths.folder("data")


def _files():
    base = _folder()
    return [base / f"{NAME}.{kind}" for kind in TYPES]


def remove():
    """Deletes the logo. True when there was one."""
    found = False
    with LOCK:
        for path in _files():
            try:
                path.unlink()
                found = True
            except FileNotFoundError:
                continue
            except OSError:
                continue
    return found


def save(data):
    """Keeps the logo (already validated by `validate`) and removes any other kind. Returns info()."""
    kind, reason = validate(data)
    if kind is None:
        raise ValueError(reason)
    base = _folder()
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{NAME}.{kind}"
    with LOCK:
        private_io.write_private(target, bytes(data))      # through a temporary file of its own, mode 0600
        for other in _files():
            if other != target:
                try:
                    other.unlink()
                except OSError:
                    pass
    return info()


def load():
    """(bytes, content type, tag) of the logo, or None. The tag is the start of the SHA-256 of the file (the address of the image carries it, so a new logo is never shown from the old cache)."""
    with LOCK:
        for kind, path in zip(TYPES, _files()):
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if len(data) <= MAX_BYTES and kind_of(data) == kind:      # a file put there by hand is checked again
                return data, TYPES[kind], hashlib.sha256(data).hexdigest()[:16]
    return None


def info():
    """What the page may know about the logo: {"present": bool, "kind", "bytes", "tag"}."""
    found = load()
    if not found:
        return {"present": False, "kind": None, "bytes": 0, "tag": ""}
    data, ctype, tag = found
    return {"present": True, "kind": [k for k, v in TYPES.items() if v == ctype][0], "bytes": len(data), "tag": tag}


def exists():
    return any(Path(p).is_file() for p in _files())
