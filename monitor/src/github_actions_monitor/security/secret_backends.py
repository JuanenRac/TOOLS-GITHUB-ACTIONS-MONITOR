# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Optional READ-ONLY places of the GitHub token kept by another program (secrets.backend): HashiCorp Vault (HTTP), a file encrypted with SOPS, Bitwarden Secrets Manager and the secret managers of AWS,
Azure and Google (through their own command line tools, with their own login). Nothing is ever written there. The settings name WHERE the secret is, never the secret; the token of the backend itself is
read from an environment variable and is never shown, logged or put in a metric. Errors say only a stable word (`BackendError.code`)."""
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit

BACKENDS = ("local", "vault", "sops", "bitwarden", "aws", "azure", "gcp")
KEY_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
VAULT_PATH_RE = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_./-]{0,200}\Z")
REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:@=+-]{0,300}\Z")
ENV_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")
MAX_ANSWER = 64 * 1024
TIMEOUT = 20


class BackendError(RuntimeError):
    """`code`: settings, address, no_token, refused, unreachable, answer, tool_missing, tool_failed."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def settings(config):
    from github_actions_monitor import families
    return families.block(config if isinstance(config, dict) else {}, "secrets")


def backend_of(config):
    name = settings(config).get("backend", "local")
    return name if name in BACKENDS else "local"


def vault_address(text):
    """The address of Vault: https, or http only to this computer."""
    parts = urlsplit(str(text or "").rstrip("/"))
    loopback = parts.hostname in ("127.0.0.1", "localhost", "::1")
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or (parts.scheme == "http" and not loopback):
        raise BackendError("address")
    return parts.geturl()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):      # the token of Vault never follows a redirect
        return None


def read_vault(cfg, environ, opener=None):
    vault = cfg.get("vault", {})
    address = vault_address(vault.get("addr"))
    path, key, name = str(vault.get("path") or ""), str(vault.get("key") or ""), str(vault.get("token_env") or "VAULT_TOKEN")
    if not VAULT_PATH_RE.match(path) or ".." in path.split("/") or not KEY_RE.match(key) or not ENV_RE.match(name):
        raise BackendError("settings")
    token = environ.get(name, "")
    if not token:
        raise BackendError("no_token")
    request = urllib.request.Request(f"{address}/v1/{path}", headers={"X-Vault-Token": token, "X-Vault-Request": "true", "User-Agent": "github-actions-monitor"})
    opener = opener or urllib.request.build_opener(_NoRedirect(), urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=TIMEOUT) as reply:
            body = json.loads(reply.read(MAX_ANSWER).decode("utf-8"))
        data = body["data"]
        data = data["data"] if isinstance(data.get("data"), dict) else data      # KV version 2 puts the values one level deeper
        return str(data[key])
    except urllib.error.HTTPError as error:
        raise BackendError("refused" if error.code in (401, 403) else "answer") from None
    except (urllib.error.URLError, OSError):
        raise BackendError("unreachable") from None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise BackendError("answer") from None


def tool_command(backend, cfg):
    """The fixed command (no shell) that prints the secret, for the backends that have a tool of their own."""
    if backend == "sops":
        sops = cfg.get("sops", {})
        path, key = str(sops.get("file") or ""), str(sops.get("key") or "")
        if not path or path.startswith("-") or len(path) > 260 or not KEY_RE.match(key):
            raise BackendError("settings")
        return ["sops", "--decrypt", "--extract", f'["{key}"]', path]
    section = cfg.get("bitwarden" if backend == "bitwarden" else "cloud", {})
    ref = str(section.get("secret_id" if backend == "bitwarden" else "ref") or "")
    if not REF_RE.match(ref):
        raise BackendError("settings")
    if backend == "bitwarden":
        return ["bws", "secret", "get", ref, "--output", "json"]
    if backend == "aws":
        return ["aws", "secretsmanager", "get-secret-value", "--secret-id", ref, "--query", "SecretString", "--output", "text"]
    if backend == "azure":
        return ["az", "keyvault", "secret", "show", "--id", ref, "--query", "value", "--output", "tsv"]
    return ["gcloud", "secrets", "versions", "access", "latest", "--secret=" + ref]


def _default_runner(command):
    found = shutil.which(command[0])
    if not found:
        raise BackendError("tool_missing")
    return subprocess.run([found, *command[1:]], capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT * 3, creationflags=0x08000000 if os.name == "nt" else 0)


def read(config, runner=None, environ=None, opener=None):
    """The secret of the backend of the configuration; "" for "local". BackendError says why not; what a tool printed is never repeated."""
    cfg = settings(config)
    backend = backend_of(config)
    if backend == "local":
        return ""
    if backend == "vault":
        return read_vault(cfg, os.environ if environ is None else environ, opener).strip()
    command = tool_command(backend, cfg)
    try:
        done = (runner or _default_runner)(command)
    except (OSError, subprocess.SubprocessError):
        raise BackendError("tool_failed") from None
    if done.returncode != 0:
        raise BackendError("tool_failed")
    out = (done.stdout or "")[:MAX_ANSWER]
    if backend == "bitwarden":
        try:
            out = str(json.loads(out)["value"])
        except (ValueError, KeyError, TypeError):
            raise BackendError("answer") from None
    return out.strip()
