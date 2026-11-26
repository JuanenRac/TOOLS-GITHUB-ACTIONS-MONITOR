# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The keyring of trusted PUBLIC keys and the verification of detached signatures (standard library only, no network).

One place for every signature the monitor checks: the releases of the project (scope `release`, whose key travels inside the product and cannot be changed by the person) and, later, signed data of other
origins (scopes `plugins`, `federation`, `packs`) whose public keys the person adds to a keyring file of their own. This module never holds, reads, creates or accepts a private key: a value that looks
like one is refused.

  entry      {"id": "name", "algorithm": "ed25519", "public": 64 hex digits, "scopes": ["release", ...], "added": "", "expires": "" or YYYY-MM-DD, "revoked": false}
  signature  one line of base64 (88 characters) holding the 64 bytes of an Ed25519 signature of the BYTES of the document
  result     "valid" | "invalid" | "absent" | "expired" | "revoked" | "unknown_key" (no trusted key of that scope)
"""
import base64
import binascii
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from github_actions_monitor.security import private_io, sigverify

SCOPES = ("release", "plugins", "federation", "packs")
#: the keys of the project: what signs a release of the monitor. The same value is written in tools/monitor_updater.py (a single file that needs no package); a test keeps them equal.
RELEASE_KEYS = ({"id": "monitor-release-1", "algorithm": "ed25519", "public": "380c75210e444f71bc4fe4b9aa7cb451aad5ef2592711f7dc6ba2fd7adc3d272",
                 "scopes": ["release"], "added": "", "expires": "", "revoked": False},)
VALID, INVALID, ABSENT, EXPIRED, REVOKED, UNKNOWN_KEY = "valid", "invalid", "absent", "expired", "revoked", "unknown_key"
SIGNATURE_SUFFIX = ".ed25519.sig"
MAX_KEYRING_BYTES = 256 * 1024
MAX_KEYS = 200
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
HEX_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
PRIVATE_WORDS = ("PRIVATE KEY", "BEGIN OPENSSH", "private", "secret", "seed")


class KeyringError(ValueError):
    """`code` is a short word a caller can translate: private_value, bad_id, bad_key, bad_scope, bad_date, duplicate, unknown, builtin, bad_file."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def fingerprint(public_hex):
    """The SHA-256 of the 32 bytes of the public key, in hex: what a person compares by eye."""
    return hashlib.sha256(bytes.fromhex(public_hex)).hexdigest()


def clean_entry(raw, scope_required=True):
    """A validated copy of a keyring entry; KeyringError when it is not one (or when it carries anything that looks like a private key)."""
    if not isinstance(raw, dict):
        raise KeyringError("bad_file", "a key entry is an object")
    for key, value in raw.items():
        if key != "id" and any(word in str(key).lower() for word in ("private", "secret", "seed")):
            raise KeyringError("private_value", "a keyring holds public keys only")
        if isinstance(value, str) and "PRIVATE KEY" in value.upper():
            raise KeyringError("private_value", "a keyring holds public keys only")
    key_id, public = str(raw.get("id") or ""), str(raw.get("public") or "").strip()
    if not ID_RE.match(key_id):
        raise KeyringError("bad_id", "the id is 1 to 64 letters, digits, dot, dash or underscore")
    if raw.get("algorithm", "ed25519") != "ed25519" or not HEX_RE.match(public) or sigverify._decompress(bytes.fromhex(public)) is None:
        raise KeyringError("bad_key", "the public key is an Ed25519 point written as 64 hex digits")
    scopes = raw.get("scopes")
    if not isinstance(scopes, list) or (scope_required and not scopes) or any(s not in SCOPES for s in scopes):
        raise KeyringError("bad_scope", "scopes are a list taken from " + ", ".join(SCOPES))
    expires = str(raw.get("expires") or "")
    if expires and not (DATE_RE.match(expires) and _date(expires)):
        raise KeyringError("bad_date", "expires is empty or YYYY-MM-DD")
    return {"id": key_id, "algorithm": "ed25519", "public": public.lower(), "scopes": sorted(set(scopes)), "added": str(raw.get("added") or "")[:10], "expires": expires, "revoked": raw.get("revoked") is True}


def _date(text):
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def builtin_keys():
    return [clean_entry(dict(entry)) for entry in RELEASE_KEYS]


def load_user_keys(path):
    """The keys of the person's keyring file ([] when there is no file). The `release` scope of a user file is ignored: only the product says who signs the product."""
    path = Path(path)
    if not path.is_file():
        return []
    if path.stat().st_size > MAX_KEYRING_BYTES:
        raise KeyringError("bad_file", "the keyring file is too big")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise KeyringError("bad_file", "the keyring file cannot be read: " + str(error)[:80]) from None
    items = data.get("keys") if isinstance(data, dict) else None
    if not isinstance(items, list) or len(items) > MAX_KEYS:
        raise KeyringError("bad_file", "the keyring file has no list of keys")
    out = []
    for raw in items:
        entry = clean_entry(raw)
        entry["scopes"] = [s for s in entry["scopes"] if s != "release"]
        out.append(entry)
    return out


def all_keys(user_path=None):
    """The built-in release keys plus the person's own (which can neither replace a built-in id nor sign releases)."""
    keys = builtin_keys()
    if user_path:
        taken = {k["id"] for k in keys}
        keys += [k for k in load_user_keys(user_path) if k["id"] not in taken]
    return keys


def save_user_keys(path, entries):
    body = {"_author": "Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>", "_license": "GPL-3.0-or-later - see LICENSE", "keys": entries}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = private_io.unique_tmp(path)
    private_io.write_tmp(temporary, json.dumps(body, indent=2) + "\n")
    private_io.replace_with_retry(temporary, path)


def add_key(path, key_id, public_hex, scopes, expires="", added=""):
    """Adds a public key to the person's file and returns the entry."""
    entry = clean_entry({"id": key_id, "public": public_hex, "scopes": list(scopes), "expires": expires, "added": added})
    if "release" in entry["scopes"]:
        raise KeyringError("builtin", "the release keys come with the product and cannot be added")
    current = load_user_keys(path)
    if any(k["id"] == entry["id"] for k in current + builtin_keys()):
        raise KeyringError("duplicate", "that id is already in the keyring")
    save_user_keys(path, current + [entry])
    return entry


def revoke_key(path, wanted):
    """Marks as revoked the key of the person's file with that id or fingerprint (a revoked key keeps its entry: its signatures are answered `revoked`)."""
    current = load_user_keys(path)
    for entry in current:
        if wanted in (entry["id"], fingerprint(entry["public"])):
            entry["revoked"] = True
            save_user_keys(path, current)
            return entry
    if any(wanted in (k["id"], fingerprint(k["public"])) for k in builtin_keys()):
        raise KeyringError("builtin", "a release key is revoked by a new release, not in this file")
    raise KeyringError("unknown", "no key with that id or fingerprint")


def expiring(keys, today, days=60):
    """[(id, days left)] of the keys that are not revoked and expire within `days` (negative: already expired): the warning that comes before a rotation."""
    out = []
    for entry in keys:
        end = _date(entry["expires"]) if entry.get("expires") else None
        if end and not entry.get("revoked") and (end - today).days <= days:
            out.append((entry["id"], (end - today).days))
    return out


ROTATION_SUFFIX = ".new" + SIGNATURE_SUFFIX


def verify_rotation(path, keys=None, today=None):
    """{"result", "new", "replaces"} of an announcement of a new release key: a JSON {"new": entry, "replaces": id} signed by the key it replaces (<path>.ed25519.sig) AND by the new key itself
    (<path>.new.ed25519.sig). The announcement only informs: the product trusts a new key when a release that carries it is installed."""
    report = {"result": INVALID, "new": "", "replaces": ""}
    path = Path(path)
    try:
        if path.stat().st_size > MAX_KEYRING_BYTES:
            return report
        data = json.loads(path.read_text(encoding="utf-8"))
        new = clean_entry(data["new"])
        replaces = str(data["replaces"])
    except (OSError, ValueError, KeyError, TypeError):
        return report
    report.update(new=new["id"], replaces=replaces)
    old = [k for k in (builtin_keys() if keys is None else keys) if k["id"] == replaces and "release" in k["scopes"]]
    if not old:
        report["result"] = UNKNOWN_KEY
        return report
    first, _ = verify_file(path, scope="release", keys=old, today=today)
    second, _ = verify_file(path, signature_path=path.with_name(path.name + ROTATION_SUFFIX), scope="release", keys=[dict(new, scopes=["release"])], today=today)
    report["result"] = first if first != VALID else second
    return report


def parse_signature(text):
    """The 64 bytes of a detached signature file, or None when the text is not one."""
    text = str(text or "").strip()
    if not sigverify.is_hydra_sign(text):
        return None
    try:
        return base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return None


def verify(data, signature_text, scope="release", keys=None, today=None):
    """(result, key id or None) for the detached signature of `data` (bytes) against the keys of `scope`."""
    if signature_text is None or not str(signature_text).strip():
        return ABSENT, None
    signature = parse_signature(signature_text)
    if signature is None:
        return INVALID, None
    candidates = [k for k in (builtin_keys() if keys is None else keys) if scope in k["scopes"]]
    if not candidates:
        return UNKNOWN_KEY, None
    today = today or date.today()
    for entry in candidates:
        if sigverify.ed25519_verify(bytes.fromhex(entry["public"]), data, signature):
            if entry.get("revoked"):
                return REVOKED, entry["id"]
            if entry.get("expires") and _date(entry["expires"]) < today:
                return EXPIRED, entry["id"]
            return VALID, entry["id"]
    return INVALID, None


def verify_file(path, signature_path=None, scope="release", keys=None, today=None):
    """verify() for a document on disk; the signature is `<path>.ed25519.sig` unless another one is named. An unreadable document is `invalid`."""
    path = Path(path)
    signature_path = Path(signature_path) if signature_path else path.with_name(path.name + SIGNATURE_SUFFIX)
    try:
        text = signature_path.read_text(encoding="ascii") if signature_path.is_file() else None
        if text is None:
            return ABSENT, None
        data = path.read_bytes()
    except (OSError, UnicodeDecodeError):
        return INVALID, None
    return verify(data, text, scope, keys, today)
