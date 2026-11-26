# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Packages of plugins of other people: a zip with plugin.json at its top and a detached Ed25519 signature next to it (<package>.ed25519.sig), checked against a key of YOUR keyring with the scope
`plugins`. Nothing is copied before the signature and the names of the files are checked; the monitor keeps the signed zip itself and checks it again every time it runs it. The monitor never signs.

    pack(folder, out)            a reproducible zip of a plugin folder (the author signs it with the tools of their own)
    inspect(package, keys)       what a package declares and who signed it
    install / uninstall / set_enabled / audit
"""
import ast
import contextlib
import hashlib
import io
import json
import shutil
import stat
import time
import zipfile
from pathlib import Path

from github_actions_monitor.plugins import plugin_manifest as manifests
from github_actions_monitor.security import keyring, private_io
from github_actions_monitor.util import paths

MAX_ZIP = 2 * 1024 * 1024
MAX_FILES = 100
MAX_UNPACKED = 8 * 1024 * 1024
PACKAGE_NAME = "package.zip"
REGISTRY_NAME = "plugins_registry.json"
INSTALL_FOLDER = "plugins_installed"
SCOPE = "plugins"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ENTRY_POINT_GROUP = "gha_monitor.plugins"
ENTRY_POINT_SUFFIX = ".plugin.zip"
SKIPPED = ("__pycache__", ".git", ".DS_Store")
NOTICED = ("socket", "subprocess", "urllib", "http", "ctypes", "multiprocessing", "ftplib", "smtplib")


class PackageError(ValueError):
    """`code`: absent, size, zip, path, link, manifest, official, unsigned, signature, revoked, expired, unknown_key, fingerprint, not_installed, files."""

    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code


def safe_name(name):
    parts = name.split("/")
    return bool(name) and len(name) <= 150 and "\\" not in name and ":" not in name and not name.startswith("/") and all(p not in ("", ".", "..") and p.isprintable() for p in parts)


def members(blob):
    """{name: bytes} of a package, after every check of names, kinds and sizes."""
    if len(blob) > MAX_ZIP:
        raise PackageError("size", "the package is bigger than 2 MB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(blob))
    except (zipfile.BadZipFile, OSError):
        raise PackageError("zip") from None
    out, total = {}, 0
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise PackageError("size", "too many files")
        for info in infos:
            name = info.filename
            if info.is_dir():
                name = name.rstrip("/")
            if not safe_name(name):
                raise PackageError("path", "a file name leaves the folder of the plugin: " + info.filename[:80])
            if stat.S_ISLNK(info.external_attr >> 16):
                raise PackageError("link", "symbolic links are not accepted")
            if info.is_dir():
                continue
            total += info.file_size
            if total > MAX_UNPACKED or name in out:
                raise PackageError("size", "too big once unpacked, or a name twice")
            try:
                with archive.open(info) as handle:
                    data = handle.read(info.file_size + 1)
            except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
                raise PackageError("zip") from None
            if len(data) > info.file_size:
                raise PackageError("size")
            out[name] = data
    return out


def manifest_of(files):
    if manifests.MANIFEST_NAME not in files:
        raise PackageError("manifest", "there is no plugin.json at the top of the package")
    try:
        manifest = manifests.parse(files[manifests.MANIFEST_NAME])
    except manifests.ManifestError as error:
        raise PackageError("manifest", f"{error.code}: {error}") from None
    if manifest["entry"] not in files:
        raise PackageError("manifest", "the entry file is not in the package")
    return manifest


def extract(files, folder):
    for name, data in files.items():
        target = Path(folder) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        private_io.write_tmp(target, data)


def signature_check(blob, signature_text, keys):
    """(key entry, fingerprint) of a good signature of the bytes; PackageError otherwise. Only keys with the scope `plugins` count."""
    result, key_id = keyring.verify(blob, signature_text, scope=SCOPE, keys=keys)
    if result == keyring.VALID:
        entry = next(k for k in keys if k["id"] == key_id)
        return entry, keyring.fingerprint(entry["public"])
    code = {"absent": "unsigned", "invalid": "signature"}.get(result, result)
    raise PackageError(code, {"unsigned": "the package has no signature", "signature": "the signature does not match the package", "unknown_key": "no key of your keyring may sign plugins"}.get(code, "the key is " + code))


def _read(package):
    package = Path(package)
    if not package.is_file():
        raise PackageError("absent", "there is no such package")
    if package.stat().st_size > MAX_ZIP:
        raise PackageError("size", "the package is bigger than 2 MB")
    signature = package.with_name(package.name + keyring.SIGNATURE_SUFFIX)
    try:
        text = signature.read_text(encoding="ascii") if signature.is_file() and signature.stat().st_size < 1024 else None
    except (OSError, UnicodeDecodeError):
        text = "?"
    return package.read_bytes(), text


def inspect(package, keys):
    """What a package of another person declares and who signed it. PackageError when it cannot be accepted."""
    blob, signature = _read(package)
    entry, print_ = signature_check(blob, signature, keys)
    manifest = manifest_of(members(blob))
    if manifest["trust"] != "third_party":
        raise PackageError("official", "official plugins travel inside the monitor, a package cannot claim to be one")
    return {"manifest": manifest, "key_id": entry["id"], "fingerprint": print_, "sha256": hashlib.sha256(blob).hexdigest()}


# --- the installed ones ---------------------------------------------------------------------------------------------------------------------------------------------------------------

def registry_file():
    return paths.place(REGISTRY_NAME)


def install_folder():
    return paths.place(INSTALL_FOLDER)


def registry():
    """{name: row} of what is installed ({} when there is nothing or the file cannot be read)."""
    try:
        data = json.loads(registry_file().read_text(encoding="utf-8"))
        return {name: row for name, row in data["plugins"].items() if manifests.NAME_RE.match(name) and isinstance(row, dict)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def save_registry(rows):
    target = registry_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = private_io.unique_tmp(target)
    private_io.write_tmp(temporary, json.dumps({"plugins": rows}, indent=2) + "\n")
    private_io.replace_with_retry(temporary, target)


def install(package, keys, fingerprint, now=None):
    """Installs a package AFTER the person confirmed the fingerprint of its key. It arrives switched off; an update signed by the same key keeps the decision of the person."""
    found = inspect(package, keys)
    if str(fingerprint or "").replace(":", "").strip().lower() != found["fingerprint"]:
        raise PackageError("fingerprint", "the fingerprint given is not the one of the key that signed the package")
    name = found["manifest"]["name"]
    blob, signature = _read(package)
    if hashlib.sha256(blob).hexdigest() != found["sha256"]:
        raise PackageError("files", "the package changed while it was read")
    folder = install_folder() / name
    folder.mkdir(parents=True, exist_ok=True)
    private_io.write_tmp(folder / PACKAGE_NAME, blob)
    private_io.write_tmp(folder / (PACKAGE_NAME + keyring.SIGNATURE_SUFFIX), signature)
    rows = registry()
    previous = rows.get(name) or {}
    same_key = previous.get("fingerprint") == found["fingerprint"]
    rows[name] = {"version": found["manifest"]["version"], "key_id": found["key_id"], "fingerprint": found["fingerprint"], "sha256": found["sha256"], "enabled": bool(same_key and previous.get("enabled")),
                  "installed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}
    save_registry(rows)
    return dict(rows[name], name=name, manifest=found["manifest"])


def load_installed(name, keys, row=None):
    """(manifest, {file: bytes}) of an installed plugin, checking again the signature and that the zip is the one that was confirmed."""
    row = row or registry().get(name)
    if not row or not manifests.NAME_RE.match(str(name)):
        raise PackageError("not_installed", "that plugin is not installed")
    blob, signature = _read(install_folder() / name / PACKAGE_NAME)
    if hashlib.sha256(blob).hexdigest() != row.get("sha256"):
        raise PackageError("files", "the installed package is not the one that was confirmed")
    _entry, print_ = signature_check(blob, signature, keys)
    if print_ != row.get("fingerprint"):
        raise PackageError("fingerprint", "signed by another key than the one that was confirmed")
    files = members(blob)
    manifest = manifest_of(files)
    if manifest["name"] != name or manifest["trust"] != "third_party":
        raise PackageError("manifest", "the manifest does not match what was installed")
    return manifest, files


def set_enabled(name, enabled):
    rows = registry()
    if name not in rows:
        raise PackageError("not_installed", "that plugin is not installed")
    rows[name]["enabled"] = bool(enabled)
    save_registry(rows)
    return dict(rows[name], name=name)


def uninstall(name):
    """Removes the files and the row of a plugin."""
    rows = registry()
    if name not in rows or not manifests.NAME_RE.match(str(name)):
        raise PackageError("not_installed", "that plugin is not installed")
    shutil.rmtree(install_folder() / name, ignore_errors=True)
    del rows[name]
    save_registry(rows)
    left = (install_folder() / name).exists()
    return {"name": name, "removed": not left}


def audit(keys):
    """[{name, version, fingerprint, enabled, state}] of the installed plugins: state is "ok" or the code of what is wrong (revoked, files, signature...)."""
    out = []
    for name, row in sorted(registry().items()):
        try:
            load_installed(name, keys, row)
            state = "ok"
        except PackageError as error:
            state = error.code
        out.append({"name": name, "version": row.get("version", ""), "key_id": row.get("key_id", ""), "fingerprint": row.get("fingerprint", ""), "enabled": row.get("enabled") is True, "state": state})
    return out


# --- the tools of an author -----------------------------------------------------------------------------------------------------------------------------------------------------------

def folder_files(folder):
    folder = Path(folder)
    out = {}
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder).as_posix()
        if any(part in SKIPPED for part in relative.split("/")) or relative.endswith((".pyc", ".zip", keyring.SIGNATURE_SUFFIX)):
            continue
        if path.is_symlink():
            raise PackageError("link", "symbolic links are not accepted: " + relative)
        if path.is_file():
            out[relative] = path.read_bytes()
        if len(out) > MAX_FILES or sum(len(v) for v in out.values()) > MAX_UNPACKED:
            raise PackageError("size", "the folder is too big for a plugin")
    return out


def used_methods(source):
    """The methods of ctx and the modules of the network or of processes that a source file names: ({methods}, {modules}). SyntaxError goes to the caller."""
    methods, modules = set(), set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "ctx" and node.attr in manifests.METHOD_PERMISSION:
            methods.add(node.attr)
        elif isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return methods, modules & set(NOTICED)


def validate(folder):
    """{"ok", "manifest", "errors": [..], "warnings": [..]} of a plugin folder: its manifest, its entry file, its syntax and the permissions its code uses without declaring them. Nothing is run."""
    out = {"ok": False, "manifest": None, "errors": [], "warnings": []}
    try:
        files = folder_files(folder)
        manifest = out["manifest"] = manifest_of(files)
    except (PackageError, OSError) as error:
        out["errors"].append(str(error))
        return out
    for name, data in files.items():
        if not name.endswith(".py") or name.startswith("test"):
            continue
        try:
            methods, modules = used_methods(data)
        except (SyntaxError, ValueError):
            out["errors"].append(f"{name}: not valid Python")
            continue
        for method in sorted(methods):
            if manifests.METHOD_PERMISSION[method] not in manifest["permissions"]:
                out["errors"].append(f"{name}: ctx.{method} needs the permission {manifests.METHOD_PERMISSION[method]}")
        if modules:
            out["warnings"].append(f"{name}: imports {', '.join(sorted(modules))} (the isolation may not stop it: see PLUGINS.md)")
    entry = files.get(manifest["entry"], b"")
    with contextlib.suppress(SyntaxError, ValueError):
        if not any(isinstance(node, ast.FunctionDef) and node.name == "run" for node in ast.parse(entry).body):
            out["errors"].append(f"{manifest['entry']}: there is no function run(ctx)")
    out["ok"] = not out["errors"]
    return out


def pack(folder, out):
    """Writes the zip of a plugin folder that passes validate(); the same folder gives the same bytes. Returns the SHA-256."""
    report = validate(folder)
    if not report["ok"]:
        raise PackageError("manifest", "; ".join(report["errors"][:5]))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in sorted(folder_files(folder).items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED      # no compression: the same bytes with every version of zlib
            archive.writestr(info, data)
    blob = buffer.getvalue()
    if len(blob) > MAX_ZIP:
        raise PackageError("size", "the package is bigger than 2 MB")
    private_io.write_tmp(Path(out), blob)
    return hashlib.sha256(blob).hexdigest()


def entry_point_candidates(entry_points=None):
    """[{"distribution", "name", "package"}] of packages installed with pip that declare the group gha_monitor.plugins and carry a <something>.plugin.zip. Their code is NEVER imported: a candidate is installed
    like any other package, with its signature and the confirmation of the person."""
    if entry_points is None:
        from importlib import metadata
        entry_points = metadata.entry_points(group=ENTRY_POINT_GROUP)
    out = []
    for point in entry_points:
        dist = getattr(point, "dist", None)
        packages = [f for f in (getattr(dist, "files", None) or []) if str(f).endswith(ENTRY_POINT_SUFFIX)]
        found = str(packages[0].locate()) if packages else ""
        out.append({"distribution": str(getattr(dist, "name", ""))[:100], "name": str(point.name)[:60], "package": found})
    return out
