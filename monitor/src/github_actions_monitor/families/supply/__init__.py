# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Supply chain of the monitor itself and its updates: keys, signatures, SBOM, attestations and the notice of a new version.

Everything this part adds to the monitor is declared in FAMILY (families/declare.py says what each field is). Its texts go in i18n/<language>.json and its page in page.js and page.css,
all inside this folder. The handlers and the commands import what they need when they run."""
from github_actions_monitor.families.declare import Command, Family, Option, Route, Setting


def update_notice(request):
    from github_actions_monitor.families.supply import notice
    return notice.state(request)


def update_dismiss(request):
    from github_actions_monitor.families.supply import notice
    return notice.dismiss(request)


def run_keyring(ctx):
    from github_actions_monitor.families.supply import commands
    return commands.keyring_command(ctx)


def run_verify_release(ctx):
    from github_actions_monitor.families.supply import commands
    return commands.verify_release_command(ctx)


FAMILY = Family(
    "supply",
    defaults={"updates": {"notify_window": True}},
    settings=(Setting("basic", "updates", "updates.notify_window", "bool", restart=False),),
    routes=(
        Route("GET", "/api/supply/update-notice", update_notice, "what the window that announces a newer version shows: the version, the summary of its changes in the language asked and whether to show it (setting updates.notify_window)"),
        Route("POST", "/api/supply/update-dismiss", update_dismiss, "do not announce one version again; body {version}", exempt="only records that the notice of one version was closed: nothing of the monitor or of GitHub changes"),
    ),
    commands=(
        Command("keyring", run_keyring, "cli.supply_help_keyring", words=("list", "add", "revoke", "verify"),
                options=(Option("--key-id", "cli.supply_help_key_id", {"metavar": "ID", "default": ""}),
                         Option("--public-key", "cli.supply_help_public_key", {"metavar": "HEX", "default": ""}),
                         Option("--key-scope", "cli.supply_help_key_scope", {"choices": ("release", "plugins", "federation", "packs"), "default": ""}),
                         Option("--expires", "cli.supply_help_expires", {"metavar": "DATE", "default": ""}),
                         Option("--document", "cli.supply_help_document", {"metavar": "FILE", "default": ""}))),
        Command("verify-release", run_verify_release, "cli.supply_help_verify_release",
                options=(Option("--folder", "cli.supply_help_folder", {"metavar": "DIR", "default": ""}),)),
    ),
)
