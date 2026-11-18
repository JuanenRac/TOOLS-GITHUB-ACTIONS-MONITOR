# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Sealing a backup package with a key that comes from an environment variable (optional).

The core of the monitor is the standard library alone, so the cipher (AES-256-GCM) is used ONLY when the optional library `cryptography` is installed. When it is not, or when the variable that
holds the key is missing or too short, sealing is REFUSED with a clear code: a package is never "sealed" with something weaker, and a person is never told a copy is encrypted when it is not.

A sealed file is  MAGIC (8) | iterations (4, big endian) | salt (16) | nonce prefix (8) | key check (16) | chunks  and every chunk is `CHUNK` bytes of the package sealed with AES-GCM (16 bytes of tag more); the key is
PBKDF2-HMAC-SHA256 of the passphrase with the salt; the nonce of a chunk is the prefix and the number of the chunk; the associated data are the header and a final-chunk flag, so a cut, a reordered
chunk or a changed header is found when it is opened. The passphrase is never written anywhere.
"""
import hashlib
import os
import re
from pathlib import Path

MAGIC = b"GHAMBK1\n"
ITERATIONS = 600000
MIN_ITERATIONS, MAX_ITERATIONS = 1000, 5000000
CHUNK = 1024 * 1024
MIN_PASSPHRASE = 12
HEADER = len(MAGIC) + 4 + 16 + 8 + 16
ENV_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}\Z")


class SealError(Exception):
    """`code` is stable: library_missing, key_missing, key_weak, bad_key, damaged, not_sealed."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _aead():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return None
    return AESGCM


def available():
    """True when the optional library is installed."""
    return _aead() is not None


def passphrase(name, env=None):
    """The passphrase held by the environment variable `name`. Raises SealError: key_missing (no name, or the variable is empty) or key_weak (shorter than MIN_PASSPHRASE)."""
    env = os.environ if env is None else env
    if not isinstance(name, str) or not ENV_RE.match(name):
        raise SealError("key_missing")
    value = env.get(name) or ""
    if not value.strip():
        raise SealError("key_missing")
    if len(value) < MIN_PASSPHRASE:
        raise SealError("key_weak")
    return value


def is_sealed(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def _key(secret, salt, iterations):
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations, dklen=32)


def _check(key):
    """16 bytes that tell a wrong key from a damaged file without opening anything (a hash of the derived key, not the key)."""
    return hashlib.sha256(b"ghamon-key-check" + key).digest()[:16]


def check_ready(name, env=None):
    """Raises SealError unless a package can be sealed right now (the library is there and the variable holds a good passphrase). Returns the passphrase."""
    if not available():
        raise SealError("library_missing")
    return passphrase(name, env)


def seal(source, dest, secret, iterations=None):
    """Seals the file `source` into `dest` (replaced atomically). Raises SealError('library_missing') without the library."""
    aead = _aead()
    if aead is None:
        raise SealError("library_missing")
    iterations = ITERATIONS if iterations is None else iterations
    salt, prefix = os.urandom(16), os.urandom(8)
    key = _key(secret, salt, iterations)
    header = MAGIC + iterations.to_bytes(4, "big") + salt + prefix + _check(key)
    cipher = aead(key)
    dest = Path(dest)
    tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
    try:
        with open(source, "rb") as src, open(tmp, "wb") as out:
            out.write(header)
            counter = 0
            current = src.read(CHUNK)
            while True:
                following = src.read(CHUNK) if len(current) == CHUNK else b""
                final = not following
                out.write(cipher.encrypt(prefix + counter.to_bytes(4, "big"), current, header + (b"\x01" if final else b"\x00")))
                if final:
                    break
                current, counter = following, counter + 1
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, dest)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def unseal(source, dest, secret):
    """Opens the sealed file `source` into `dest` (replaced atomically). Raises SealError: not_sealed, library_missing, bad_key (the key does not open it) or damaged."""
    aead = _aead()
    with open(source, "rb") as src:
        header = src.read(HEADER)
        if len(header) < HEADER or header[:len(MAGIC)] != MAGIC:
            raise SealError("not_sealed")
        if aead is None:
            raise SealError("library_missing")
        iterations = int.from_bytes(header[len(MAGIC):len(MAGIC) + 4], "big")
        if not MIN_ITERATIONS <= iterations <= MAX_ITERATIONS:
            raise SealError("damaged")
        salt, prefix, check = header[len(MAGIC) + 4:len(MAGIC) + 20], header[len(MAGIC) + 20:len(MAGIC) + 28], header[len(MAGIC) + 28:]
        key = _key(secret, salt, iterations)
        if _check(key) != check:
            raise SealError("bad_key")
        cipher = aead(key)
        dest = Path(dest)
        tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
        try:
            with open(tmp, "wb") as out:
                counter = 0
                current = src.read(CHUNK + 16)
                if not current:
                    raise SealError("damaged")
                while True:
                    following = src.read(CHUNK + 16) if len(current) == CHUNK + 16 else b""
                    final = not following
                    try:
                        out.write(cipher.decrypt(prefix + counter.to_bytes(4, "big"), current, header + (b"\x01" if final else b"\x00")))
                    except Exception:      # noqa: BLE001 - the library raises InvalidTag: the key was already checked, so this is a damaged or cut file
                        raise SealError("damaged") from None
                    if final:
                        break
                    current, counter = following, counter + 1
            os.replace(tmp, dest)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
