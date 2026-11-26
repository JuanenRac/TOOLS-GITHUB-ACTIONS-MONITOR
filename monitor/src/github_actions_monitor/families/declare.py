# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What a part of the monitor can declare, so that it plugs into the server, the settings, the command line and the page without editing the big shared files (standard library only).

A part lives in families/<name>/. Its __init__.py builds one `Family`. The folder may also hold:

  i18n/<language>.json   its texts, the eight languages with the same keys ({"_author", "_license", "key": "text"}). Allowed keys: <ns>.<name>.* (ui.extci.title, cli.extci.help_probe),
                         cfg.f / cfg.h / cfg.t of its own settings, ui.cfg_b_<block> and ui.cfg_g_<tab> of its own blocks and tabs, egress.use.<id> and egress.fail.<id> of its own destinations.
  page.js / page.css     added to the page after its own script (complete edition only); page.js uses window.FAM (families/page.js)

Importing a part must be cheap and free of side effects: a handler, a command or a tick imports what it needs inside its body (the settings and the command line import every part at start).
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Setting:
    """One row of the Settings page; the same arguments as settings_api._f. `default` is not given here: it is in Family.defaults. `lite` also shows it in the lite edition."""
    tab: str
    block: str
    key: str
    kind: str                 # bool | int | float | enum | text | path | names | ... (settings_api.check_value)
    bounds: object = None     # int/float: (low, high); enum: the tuple of values; text and names: a compiled regular expression
    restart: bool = True
    secure: bool = False
    unit: str = None
    label: list = None
    help: str = None
    lite: bool = False


@dataclass(frozen=True)
class Request:
    """What a handler of a route receives. `query` is {name: first value}; `body` is the JSON object of a POST ({} when there is none); `config` is the configuration file as it is now."""
    method: str
    path: str
    query: dict
    body: dict
    user: str
    config: dict


@dataclass(frozen=True)
class Route:
    """GET or POST /api/... of a part. `handler(request)` returns the JSON answer, or (status, answer). The server does the checks before it: the access token of the network mode, the session and `role`
    of the team mode, the Host and Origin guard, `this_computer`, the one-use token of the page and the size of the body. A POST says either `audit` (the name of the line in the log of actions) or `exempt`
    (why it leaves none). `note` describes the route for the AIs (the references of the skills are generated from it)."""
    method: str
    path: str
    handler: object
    note: str
    role: str = ""            # viewer | maintainer | admin; "" = viewer for a GET, admin for a POST
    this_computer: bool = False
    token: bool = True        # POST only: the one-use token of the page (header X-Monitor-Token)
    lite: bool = False
    audit: str = ""
    exempt: str = ""
    max_body: int = 4096


@dataclass(frozen=True)
class Option:
    """An option of the command line (`--name`): `help` is a key of the texts, `kwargs` goes to argparse (action, choices, type, default, metavar)."""
    flag: str
    help: str
    kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Command:
    """A command of bin/monitor_cli.py. `run(ctx)` returns (payload, lines, exit code) like the commands of monitor_cli; ctx["action"] is the word after the command and ctx["args"] every parsed option.
    `words` are the words it accepts after its name."""
    name: str
    run: object
    help: str                 # a key of the texts: one line that says what the command does
    words: tuple = ()
    options: tuple = ()
    lite: bool = False


@dataclass(frozen=True)
class Egress:
    """A network destination (ops/egress.py): a row of `doctor --egress`. `hosts` are the fixed ones, `setting` the switch that makes it a destination, `hosts_from(config)` the hosts that come from the
    configuration and `active(config)` replaces the reading of the switch when it is not a simple boolean."""
    id: str
    hosts: tuple = ()
    setting: str = None
    hosts_from: object = None
    active: object = None


@dataclass(frozen=True)
class Family:
    name: str
    defaults: dict = field(default_factory=dict)      # merged into actions_monitor.DEFAULTS; it may add keys inside a block that exists, never change one
    settings: tuple = ()          # Setting
    settings_tabs: tuple = ()     # (new tab of Settings, the tab it goes after); its name is the text ui.cfg_g_<tab>
    routes: tuple = ()            # Route
    commands: tuple = ()          # Command
    ticks: tuple = ()             # tick(config, data): after each cycle of the complete edition; a failure is noted and never stops the loop
    egress: tuple = ()            # Egress
