# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Plugins, their authoring tools, the skills that are published and the extra stores of secrets (plugins/, security/secret_backends.py do the work).

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder."""
import re
from urllib.parse import urlsplit

from github_actions_monitor.families.declare import Command, Egress, Family, Option, Route, Setting
from github_actions_monitor.security import envguard


def _api():
    from github_actions_monitor.plugins import plugin_api
    return plugin_api


def _catalog(request):
    return _api().catalogue(request)


def _enable(request):
    return _api().enable(request)


def _uninstall(request):
    return _api().uninstall(request)


def _inspect(request):
    return _api().inspect(request)


def _install(request):
    return _api().install(request)


def _cli(ctx):
    from github_actions_monitor.plugins import plugin_cli
    return plugin_cli.run(ctx)


def _tick(config, data):
    if ((config or {}).get("plugins") or {}).get("enabled") is True:
        from github_actions_monitor.plugins import plugin_host
        plugin_host.tick(config, data)


def _vault_hosts(config):
    block = (config or {}).get("secrets") or {}
    host = urlsplit(str((block.get("vault") or {}).get("addr") or "")).hostname
    return [host] if host else []


def _backend_is(*names):
    return lambda config: ((config or {}).get("secrets") or {}).get("backend") in names


def _p(key, kind, bounds=None, secure=False, unit=None):
    return Setting("plugins", "plugins", "plugins." + key, kind, bounds=bounds, restart=False, secure=secure, unit=unit)


def _s(key, kind, bounds=None, unit=None):
    return Setting("plugins", "secrets", "secrets." + key, kind, bounds=bounds, restart=True, secure=True, unit=unit)


def _text(pattern):
    return re.compile(pattern)


def _env_name():
    """The name of a variable of the person: never one of the system or a secret of the monitor (security/envguard.py); empty means none."""
    barred = "|".join(re.escape(name) for name in envguard.SYSTEM_NAMES + envguard.SECRET_NAMES)
    return re.compile(rf"^(?!(?:{barred})\Z)(?:[A-Z_][A-Z0-9_]{{0,63}})?\Z")


FAMILY = Family(
    "plugins",
    defaults={"plugins": {"enabled": False, "official": {"discussions": {"enabled": False, "days": 7}, "packages": {"enabled": False, "max_versions": 50, "types": ["container"]}},
                          "third_party": {"enabled": False}, "worker": {"timeout_s": 20, "max_output_kb": 256, "memory_mb": 256, "platforms_ok": ["linux", "windows", "darwin"]},
                          "official_timeout_s": 300, "alert_title_max": 120, "breaker": {"failures": 3}, "reverify_on_start": True, "entry_points": False},
              "secrets": {"backend": "local", "reload_on_rotate": True, "reload_seconds": 900, "vault": {"addr": "", "path": "", "field": "token", "token_env": "VAULT_TOKEN"},
                          "sops": {"file": "", "field": "token"}, "bitwarden": {"item": ""}, "cloud": {"ref": ""}}},
    settings=(_p("enabled", "bool", secure=True), _p("official.discussions.enabled", "bool"), _p("official.discussions.days", "int", (1, 365)), _p("official.packages.enabled", "bool"),
              _p("official.packages.max_versions", "int", (1, 10000)), _p("official.packages.types", "names", _text(r"^(container|npm)\Z")), _p("third_party.enabled", "bool", secure=True),
              _p("worker.timeout_s", "int", (1, 300), secure=True, unit="s"), _p("worker.max_output_kb", "int", (16, 4096), secure=True), _p("worker.memory_mb", "int", (64, 4096), secure=True),
              _p("worker.platforms_ok", "names", _text(r"^(linux|windows|darwin)\Z"), secure=True), _p("official_timeout_s", "int", (10, 3600), unit="s"), _p("alert_title_max", "int", (40, 400)),
              _p("breaker.failures", "int", (1, 50)), _p("reverify_on_start", "bool", secure=True), _p("entry_points", "bool", secure=True),
              _s("backend", "enum", ("local", "vault", "sops", "bitwarden", "aws", "azure", "gcp")), _s("reload_on_rotate", "bool"), _s("reload_seconds", "int", (60, 86400), unit="s"),
              _s("vault.addr", "text", _text(r"^(https?://[^\s]{1,200})?\Z")), _s("vault.path", "text", _text(r"^[A-Za-z0-9_./-]{0,200}\Z")),
              _s("vault.field", "text", _text(r"^[A-Za-z0-9_.-]{1,100}\Z")), _s("vault.token_env", "text", _env_name()),
              _s("sops.file", "text", _text(r"^[^\x00-\x1f]{0,260}\Z")), _s("sops.field", "text", _text(r"^[A-Za-z0-9_.-]{1,100}\Z")),
              _s("bitwarden.item", "text", _text(r"^[A-Za-z0-9-]{0,100}\Z")), _s("cloud.ref", "text", _text(r"^[A-Za-z0-9_./:@=+-]{0,300}\Z"))),
    settings_tabs=(("plugins", "outputs"),),
    routes=(
        Route("GET", "/api/plugins/catalog", _catalog, "the plugins that exist here: permissions, key, fingerprint, state and what is isolated", role="admin"),
        Route("POST", "/api/plugins/enable", _enable, "switch an installed plugin of another person on or off, or resume a paused one; body {name, enabled}", this_computer=True, audit="plugin_enable"),
        Route("POST", "/api/plugins/uninstall", _uninstall, "remove an installed plugin; body {name}", this_computer=True, audit="plugin_uninstall"),
        Route("POST", "/api/plugins/inspect", _inspect, "what a package on this computer declares and who signed it, nothing is installed; body {path}", this_computer=True,
              exempt="reads a package and says what it declares: nothing of the monitor or of GitHub changes"),
        Route("POST", "/api/plugins/install", _install, "install a signed package after confirming the fingerprint of its key; it arrives switched off; body {path, fingerprint}", this_computer=True,
              audit="plugin_install"),
    ),
    commands=(Command("plugin", _cli, "cli.plugins.help", words=("list", "validate", "pack", "verify", "init", "install", "enable", "disable", "uninstall", "audit"),
                      options=(Option("--path", "cli.plugins.help_path", {"metavar": "PATH", "default": ""}), Option("--name", "cli.plugins.help_name", {"metavar": "NAME", "default": ""}),
                               Option("--fingerprint", "cli.plugins.help_fingerprint", {"metavar": "HEX", "default": ""}), Option("--keyring", "cli.plugins.help_keyring", {"metavar": "FILE", "default": ""}),
                               Option("--out", "cli.plugins.help_out", {"metavar": "FILE", "default": ""}))),),
    ticks=(_tick,),
    egress=(Egress("secrets_vault", (), "secrets.backend", hosts_from=_vault_hosts, active=_backend_is("vault")),
            Egress("secrets_tool", (), "secrets.backend", active=_backend_is("sops", "bitwarden", "aws", "azure", "gcp"))),
)
