# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Read-only verification of release signatures against the PUBLIC keys pinned by the ecosystems (standard library only, no network).

It never reads or prints a private key. The public keys are read as text from the repositories that pin them (or from the sentinel
configuration, `signature_pubkeys`):

  urtc    URTC/tools/release_sign.py                                   PUBLIC_KEY_HEX       scheme  urtc-rel/1|<file name>|<sha256>
  armor   ARMOR-DEVOPS/scripts/armor_maintenance_agent.py              PACKAGE_PUBLIC_KEY   scheme  armor-pkg/1|<component>|<version>|<sha256>
  hydra   HYDRA-UMC-UPDATER/src/hydra_umc_updater/package_release.py   RELEASES_PUBLIC_KEY  scheme  hydra-pc-pkg/1|<name>|<version>|<sha256>

HYDRA binaries use a second format, the hydra-sign of HYDRA-UMC-TOOL-CLI: `FILE.sig` holds the Ed25519 signature of the BYTES OF THE FILE in base64
(88 characters), checked against the same pinned release key; it is recognised by its shape, so it can be definitive (the package scheme, a hex line, is not).
URTC images carry `X.imgsig` (152 hex digits and one line feed): only its FORMAT can be checked here (the signed message also needs the 28-byte header of
the build, which the signed folder does not carry), so a well-formed record stays "unknown" and a malformed one is False. ARMOR APKs are signed inside the
APK by apksigner (no .sig file): not checkable with the standard library, "unknown".

Result of a signed set (`verify_dir`): True (at least one signature checked and none failed), False (a signature that must verify does not)
or "unknown" (no key, a format this module does not check - .sig2/.hdr2/APK - or nothing to check). URTC `.sig` files, ARMOR `.tgz` packages and
HYDRA hydra-sign files (base64 line) are definitive and can give False; a HYDRA `.sig` in the package format (hex) that does not match stays "unknown". The tools that sign verify everything before they publish; this is the second, independent look.
"""
import base64
import binascii
import hashlib
import re
from pathlib import Path

UNKNOWN = "unknown"
MAX_BYTES = 512 * 1024 * 1024   # a bigger file is not hashed here (it stays "unknown")
MAX_FILES = 60

KEY_FILES = {
    "urtc": ("URTC/tools/release_sign.py", r'^PUBLIC_KEY_HEX\s*=\s*"([0-9a-fA-F]{64})"'),
    "armor": ("ARMOR-DEVOPS/scripts/armor_maintenance_agent.py", r'^PACKAGE_PUBLIC_KEY\s*=\s*"([0-9a-fA-F]{64})"'),
    "hydra": ("HYDRA-UMC-UPDATER/src/hydra_umc_updater/package_release.py", r'^RELEASES_PUBLIC_KEY\s*=\s*"([0-9a-fA-F]{64})"'),
}

# --- Ed25519 verification (RFC 8032, standard library) ---------------------------------------------------------------------------
_P = 2 ** 255 - 19
_Q = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _add(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    pa, pb = (y1 - x1) * (y2 - x2) % _P, (y1 + x1) * (y2 + x2) % _P
    pc, pd = 2 * t1 * t2 * _D % _P, 2 * z1 * z2 % _P
    e, f, g, h = pb - pa, pd - pc, pd + pc, pb + pa
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(scalar, point):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _same(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _x_of(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _I % _P
    if (x * x - x2) % _P:
        return None
    return _P - x if (x & 1) != sign else x


def _decompress(data):
    y = int.from_bytes(data, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    x = _x_of(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _compress(point):
    zinv = pow(point[2], _P - 2, _P)
    x, y = point[0] * zinv % _P, point[1] * zinv % _P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


_BY = 4 * pow(5, _P - 2, _P) % _P
_BX = _x_of(_BY, 0)
BASE = (_BX, _BY, 1, _BX * _BY % _P)


def ed25519_verify(public, message, signature):
    """True only for a valid signature. Never raises on malformed input."""
    try:
        if len(public) != 32 or len(signature) != 64:
            return False
        digest = hashlib.sha512(signature[:32] + public)
        digest.update(message)
        return _check(public, signature, digest)
    except (ValueError, TypeError):
        return False


def ed25519_verify_file(public, path, signature):
    """Same as ed25519_verify for a message that is the content of a file (read in blocks: a big binary is never held in memory)."""
    try:
        if len(public) != 32 or len(signature) != 64:
            return False
        digest = hashlib.sha512(signature[:32] + public)
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        return _check(public, signature, digest)
    except (ValueError, TypeError, OSError):
        return False


def _check(public, signature, digest):
    a, r = _decompress(public), _decompress(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if a is None or r is None or s >= _Q:
        return False
    h = int.from_bytes(digest.digest(), "little") % _Q
    return _same(_mul(s, BASE), _add(r, _mul(h, a)))


# --- keys and schemes ------------------------------------------------------------------------------------------------------------
def ecosystem_of(repo):
    if repo.startswith("ARMOR-"):
        return "armor"
    if repo.startswith("URTC"):
        return "urtc"
    if repo.startswith("HYDRA-UMC"):
        return "hydra"
    return "other"


def pinned_keys(root, overrides=None):
    """ecosystem -> public key (64 hex digits) read from the repositories of the workspace; `overrides` ({eco: hex}) wins. Missing ones are left out."""
    keys = {}
    for eco, (relative, pattern) in KEY_FILES.items():
        try:
            match = re.search(pattern, (Path(root) / relative).read_text(encoding="utf-8"), re.M)
        except OSError:
            continue
        if match:
            keys[eco] = match.group(1).lower()
    for eco, value in (overrides or {}).items():
        if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
            keys[str(eco)] = value.lower()
    return keys


def _messages(eco, name, digest):
    """(message, definitive) candidates for one signed file. definitive = a failure of this scheme means the file is NOT validly signed."""
    if eco == "urtc":
        return [(f"urtc-rel/1|{name}|{digest}".encode(), True)]
    if eco == "armor":
        match = re.fullmatch(r"armor-(.+)-(\d+(?:\.\d+)+)\.tgz", name)
        return [(f"armor-pkg/1|{match.group(1)}|{match.group(2)}|{digest}".encode(), True)] if match else []
    if eco == "hydra":
        match = re.fullmatch(r"(.+?)-(\d+(?:\.\d+)+)(?:\.[A-Za-z0-9.]+)?", name)
        return [(f"hydra-pc-pkg/1|{match.group(1)}|{match.group(2)}|{digest}".encode(), False)] if match else []
    return []


def is_hydra_sign(text):
    """True for the shape of a hydra-sign signature: base64 (standard alphabet, padded) of exactly 64 bytes, on one line."""
    if len(text) != 88 or not re.fullmatch(r"[A-Za-z0-9+/]{86}==", text):
        return False
    try:
        return len(base64.b64decode(text, validate=True)) == 64
    except (binascii.Error, ValueError):
        return False


def imgsig_format(path):
    """URTC `.imgsig`: True when it is exactly 152 hex digits and one line feed (the strict format of urtc_common.image_sig), False when it is not, None when unreadable."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    return re.fullmatch(rb"[0-9a-fA-F]{152}\n?", data) is not None


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file(path, eco, key_hex, digest=None):
    """True / False / "unknown" for <path> and <path>.sig."""
    path = Path(path)
    sig_path = Path(str(path) + ".sig")
    if not key_hex or not sig_path.is_file() or not path.is_file():
        return UNKNOWN
    try:
        if path.stat().st_size > MAX_BYTES:
            return UNKNOWN
        text = sig_path.read_text(encoding="ascii").strip()
        if eco == "hydra" and is_hydra_sign(text):
            return ed25519_verify_file(bytes.fromhex(key_hex), path, base64.b64decode(text, validate=True))
        digest = digest or sha256_of(path)
    except (OSError, UnicodeDecodeError, ValueError):
        return UNKNOWN
    candidates = _messages(eco, path.name, digest)
    if not candidates:
        return UNKNOWN
    try:
        signature = bytes.fromhex(text)
    except ValueError:
        signature = b""
    public = bytes.fromhex(key_hex)
    for message, _ in candidates:
        if ed25519_verify(public, message, signature):
            return True
    return False if any(definitive for _, definitive in candidates) else UNKNOWN


def verify_dir(folder, eco, keys):
    """True / False / "unknown" for a signed set: every `X.sig` that sits next to `X` is checked against the pinned key of the ecosystem."""
    key = (keys or {}).get(eco)
    if not key:
        return UNKNOWN
    try:
        files = sorted(p for p in Path(folder).iterdir() if p.is_file() and not p.name.endswith((".sig", ".imgsig")))
    except OSError:
        return UNKNOWN
    results = []
    for path in files:
        if len(results) >= MAX_FILES:
            break
        if Path(str(path) + ".sig").is_file():
            results.append(verify_file(path, eco, key))
        if eco == "urtc" and Path(str(path) + ".imgsig").is_file() and imgsig_format(Path(str(path) + ".imgsig")) is False:
            results.append(False)
    if any(r is False for r in results):
        return False
    return True if results and all(r is True for r in results) else UNKNOWN
