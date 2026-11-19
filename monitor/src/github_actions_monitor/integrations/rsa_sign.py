# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""RS256 with the standard library only: reads an RSA private key in PEM (PKCS#1 `RSA PRIVATE KEY` or PKCS#8 `PRIVATE KEY`, no passphrase) with a minimal ASN.1 reader and signs with
RSASSA-PKCS1-v1_5 and SHA-256 (RFC 8017, section 8.2), using the Chinese remainder theorem and checking the result with the public exponent before it is returned. It exists so that the GitHub App
keeps working on a computer without the `openssl` program in its PATH. The key is read into memory only for the signature: it is never printed, logged, copied or kept. Nothing here is used to
verify or to create keys."""
import base64
import hashlib
import re

MAX_KEY_BYTES = 20_000
#: DER of DigestInfo for SHA-256 up to the digest (RFC 8017, note 1)
SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
RSA_OID = bytes.fromhex("2a864886f70d010101")      # 1.2.840.113549.1.1.1


class KeyError_(ValueError):
    """The key cannot be read or is not one this signer takes (the text never holds a byte of the key)."""


def _tlv(data, at):
    """(tag, value start, value end) of the element that begins at `at`."""
    if at + 2 > len(data):
        raise KeyError_("truncated key")
    tag, first = data[at], data[at + 1]
    at += 2
    if first < 0x80:
        size = first
    else:
        count = first & 0x7F
        if count == 0 or count > 4 or at + count > len(data):
            raise KeyError_("bad length in the key")
        size = int.from_bytes(data[at:at + count], "big")
        at += count
    if at + size > len(data):
        raise KeyError_("truncated key")
    return tag, at, at + size


def _items(data, start, end):
    at, out = start, []
    while at < end:
        tag, begin, stop = _tlv(data, at)
        out.append((tag, begin, stop))
        at = stop
    return out


def _integers(data, node):
    tag, start, end = node
    if tag != 0x30:
        raise KeyError_("not an RSA key")
    items = _items(data, start, end)
    if any(t != 0x02 for t, _b, _e in items):
        raise KeyError_("not an RSA key")
    return [int.from_bytes(data[b:e], "big") for _t, b, e in items]


def parse_der(der):
    """(n, e, d, p, q, dp, dq, qinv) from the DER of an RSAPrivateKey (PKCS#1) or of a PrivateKeyInfo that holds one (PKCS#8)."""
    der = bytes(der)
    tag, start, end = _tlv(der, 0)
    if tag != 0x30 or end != len(der):
        raise KeyError_("not an RSA key")
    items = _items(der, start, end)
    if len(items) >= 3 and items[0][0] == 0x02 and items[1][0] == 0x30 and items[2][0] == 0x04:      # PKCS#8: version, AlgorithmIdentifier, OCTET STRING with the PKCS#1 key
        algorithm = _items(der, items[1][1], items[1][2])
        if not algorithm or algorithm[0][0] != 0x06 or der[algorithm[0][1]:algorithm[0][2]] != RSA_OID:
            raise KeyError_("the key is not an RSA key")
        inner = der[items[2][1]:items[2][2]]
        return parse_der(inner)
    numbers = _integers(der, (tag, start, end))
    if len(numbers) < 9 or numbers[0] != 0:
        raise KeyError_("not an RSA private key")
    _version, n, e, d, p, q, dp, dq, qinv = numbers[:9]
    if n.bit_length() < 512 or p * q != n:
        raise KeyError_("the key is inconsistent")
    return n, e, d, p, q, dp, dq, qinv


def parse_pem(text):
    """The numbers of the key in a PEM text. Keys with a passphrase and keys of another kind are refused with a plain reason."""
    text = text.replace("\r\n", "\n")
    if "ENCRYPTED" in text.split("-----END", 1)[0]:
        raise KeyError_("the key has a passphrase (not supported)")
    found = re.search(r"-----BEGIN (RSA PRIVATE KEY|PRIVATE KEY)-----\s*([A-Za-z0-9+/=\s]+?)\s*-----END \1-----", text)
    if not found:
        raise KeyError_("no RSA private key in the file")
    try:
        der = base64.b64decode("".join(found.group(2).split()), validate=True)
    except ValueError:
        raise KeyError_("the key is not valid base64") from None
    return parse_der(der)


def load(path):
    """The numbers of the key in the file `path` (at most 20 kB)."""
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_KEY_BYTES + 1)
    except OSError:
        raise KeyError_("the key file cannot be read") from None
    if len(raw) > MAX_KEY_BYTES:
        raise KeyError_("the key file is too large")
    return parse_pem(raw.decode("ascii", "ignore"))


def sign_numbers(data, key):
    """RSASSA-PKCS1-v1_5 / SHA-256 of `data` with the numbers of a key; the bytes of the signature."""
    n, e, d, p, q, dp, dq, qinv = key
    size = (n.bit_length() + 7) // 8
    digest_info = SHA256_PREFIX + hashlib.sha256(data).digest()
    if size < len(digest_info) + 11:
        raise KeyError_("the key is too short")
    message = int.from_bytes(b"\x00\x01" + b"\xff" * (size - len(digest_info) - 3) + b"\x00" + digest_info, "big")
    s1, s2 = pow(message, dp, p), pow(message, dq, q)
    signature = s2 + q * ((qinv * (s1 - s2)) % p)
    if pow(signature, e, n) != message:      # a fault in the CRT must never leave as a signature: the slow way, and checked again
        signature = pow(message, d, n)
        if pow(signature, e, n) != message:
            raise KeyError_("the key does not sign")
    return signature.to_bytes(size, "big")


def sign_file(data, path):
    return sign_numbers(data, load(path))
