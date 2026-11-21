# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The wall screens: /screen/overview (the whole fleet in one view), /screen/now (what is happening this minute) and /screen/sentinels (one card per sentinel). They are pages for a monitor or a TV that
nobody touches, with no menu and no buttons that change anything. This module is the server side of them and holds no state:

  settings(config)            the block `screens` of the configuration, every value clamped to its range
  params(query, cfg, kind, global_theme)  what the address may change for one window (?monitor ?theme ?density ?refresh ?scale ?rotate ?jump ?blink ?sound): it can only make a window quieter or smaller than
                              the settings allow, never switch on what the settings keep off
  resolve_theme(cfg, kind, global_theme)  the theme of one screen: its own setting, else the one of all the screens, else the theme chosen in Settings for the whole product
  theme_css()                 the palettes of the sixteen themes of the main page, read from the page itself so that the two never differ
  logo_block(cfg, info)       what the page needs to show the logo of the organization (docs/SCREENS.md), or None
  page_data(kind, ...)        what is embedded in the page (language, texts, settings, parameters)
  build(kind, ...)            the payload of /api/screens/data: a closed list of fields made only from what the monitor already holds (the last cycle, the sentinel snapshot, the alerts, the score).
                              Nothing here reads GitHub, runs a command, opens a link or returns a title, a commit message, a URL, a job name or a user name.

Names of repositories follow `screens.show_repo_names`: `all`, `public` (a private repository is called private-N) or `none` (every repository is repo-N). Standard library only."""
import hashlib
import hmac
import re
import secrets
import time
from datetime import datetime, timezone

from github_actions_monitor import i18n
from github_actions_monitor.tool_version import TOOL_VERSION
from github_actions_monitor.util import paths

SCHEMA = 1
KINDS = ("overview", "fleet", "now", "sentinels")      # the four screens of the wall in the order they turn: Overview, Fleet, Right now, Sentinels (?monitor=1 to 4 only names the window)
PATH_RE = re.compile(r"^/screen/(overview|fleet|now|sentinels)/?\Z")
TRANSITIONS = ("none", "fade", "slide")
MIN_FONT_LOW, MIN_FONT_HIGH = 8, 32      # the smallest letter (screens.min_font_px) a screen may be asked to keep, in pixels
THEMES = ("dark", "light", "contrast")
#: the themes of the main page (the same names, in the same order as its list): `auto` follows the computer, the rest are fixed. A wall screen may also use `contrast`, white on black for a screen seen from far away.
STUDIO_THEMES = ("Armor", "Aqua", "Midnight", "Ember", "Forest", "Violet", "Solar", "Ice", "Crimson", "Mono", "High contrast", "Metallic", "Professional", "Videogame", "Terminal", "Blueprint")
GLOBAL_THEMES = ("auto", "light", "dark") + STUDIO_THEMES
SCREEN_THEMES = GLOBAL_THEMES + ("contrast",)
THEME_CHOICES = ("inherit",) + SCREEN_THEMES
MODES = ("three", "rotate")
CORNERS = ("top-right", "top-left", "bottom-right", "bottom-left")
DENSITIES = ("compact", "normal", "large")
MAX_SAFE = 10      # the most a television may cut from each edge that the screens keep clear (screens.safe_margin_percent, ?safe=), in percent of the window
NAMES = ("all", "public", "none")
DEFAULTS = {"enabled": False, "blink": True, "blink_calm_minutes": 30, "rotate_seconds": 0, "default_theme": "inherit", "default_density": "normal", "refresh_seconds": 10, "burn_in_protection": True,
            "night_dim": False, "night_dim_from_hour": 22, "night_dim_to_hour": 7, "show_repo_names": "public", "sound": False, "sound_voices": "", "sound_volume": 0,
            "theme_overview": "inherit", "theme_fleet": "inherit", "theme_now": "inherit", "theme_sentinels": "inherit", "mode": "three", "rotate_every_seconds": 20, "alert_hold_seconds": 30,
            "logo_overview": True, "logo_fleet": False, "logo_now": False, "logo_sentinels": False, "logo_corner": "top-right", "logo_max_width": 160, "logo_max_height": 64, "group_map": True,
            "menu": True, "menu_target": "new", "menu_max_windows": 4, "menu_rotate_seconds": 20, "menu_tv_scale": 1.5, "safe_margin_percent": 0,
            "life": True, "glance_seconds": 3, "transition": "fade", "hide_healthy": False, "idle_dim_minutes": 0, "min_font_px": 12}   # the five before the last belong to the Screens menu (screenmenu.py)
SENTINEL_KEY = re.compile(r"^ui\.a(1[0-2]|[1-9])\Z")
SENTINELS = tuple("a%d" % n for n in range(1, 13))
LEVELS = ("ok", "warn", "bad", "info", "unknown")
RED_CONCLUSIONS = ("failure", "timed_out", "startup_failure")
HEAT_ROWS, HEAT_BUCKETS = 12, 24
TOP_RED, EVENTS, ACTIVE_ROWS, FAILURES, TIMELINE, MERGES = 8, 10, 12, 8, 24, 6

#: why a tab has no wall screen: `people` (it names people, and a wall screen never shows a user name), `controls` (it is made of buttons and fields that change something, and a wall screen has none),
#: `reading` (it is made to be read, compared or saved, not to be seen from far away) and `text` (it is made of titles, causes and messages, which a wall screen never shows).
NO_SCREEN_REASONS = ("people", "controls", "reading", "text")
#: the decision of the wall screens, tab by tab (every tab of the page is here, and a test fails when a tab is added without its decision). A tab that is shown says on which screen and in which field of the
#: answer of /api/screens/data; a tab that is not shown says why. The map of the fleet by groups belongs to the overview (it is the Fleet tab at a glance).
TAB_DECISIONS = {
    "now": {"screen": "now", "field": "running"},
    "al": {"screen": "overview", "field": "alerts"},
    "charts": {"screen": "overview", "field": "trend24"},
    "sent": {"screen": "sentinels", "field": "cards"},
    "sci": {"screen": "sentinels", "field": "cards"},
    "scol": {"screen": "sentinels", "field": "cards"},
    "ssec": {"screen": "sentinels", "field": "cards"},
    "sdel": {"screen": "sentinels", "field": "cards"},
    "ssup": {"screen": "sentinels", "field": "cards"},
    "strend": {"screen": None, "reason": "reading"},
    "syvt": {"screen": None, "reason": "reading"},
    "team": {"screen": None, "reason": "people"},
    "fleet": {"screen": "fleet", "field": "groups"},
    "repos": {"screen": None, "reason": "controls"},
    "rep": {"screen": None, "reason": "reading"},
    "trep": {"screen": None, "reason": "reading"},
    "les": {"screen": None, "reason": "text"},
    "hist": {"screen": None, "reason": "text"},
    "upd": {"screen": None, "reason": "controls"},
    "cfg": {"screen": None, "reason": "controls"},
}


def tab_decisions():
    """The decision of the wall screens for every tab, as plain data: {tab: {"screen": kind or None, "field": the field that carries it, "reason": why it is not shown}}."""
    return {tab: {"screen": d["screen"], "field": d.get("field", ""), "reason": d.get("reason", "")} for tab, d in TAB_DECISIONS.items()}


def _int(value, low, high, default):
    if isinstance(value, bool):
        return default
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _scale(value, default):
    """A number from 0.5 to 3 (the size of the TV preset); the default when it is not a number."""
    return default if isinstance(value, bool) or not isinstance(value, (int, float)) else round(max(0.5, min(3.0, float(value))), 2)


def _flag(value, default):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "on", "yes"):
        return True
    if text in ("0", "false", "off", "no"):
        return False
    return default


def _choice(value, allowed, default):
    text = str(value).strip().lower() if value is not None else ""
    return text if text in allowed else default


def _theme(value, allowed, default):
    """A theme name from `allowed`, matched without regard to case (`high contrast` is `High contrast`); else the default."""
    text = str(value).strip().lower() if value is not None else ""
    for name in allowed:
        if name.lower() == text:
            return name
    return default


def _voices_text(value):
    """screens.sound_voices: the pairs `kind=sound` that name a kind of event and a sound of the library, as text (an invalid pair is left out)."""
    from github_actions_monitor.integrations import soundlib
    pairs = soundlib.parse_voices(value)
    return ",".join(f"{k}={v}" for k, v in pairs.items())


def settings(config):
    """The settings of the wall screens from the configuration, each one inside its range (a value that is not valid is the default)."""
    block = (config or {}).get("screens")
    block = block if isinstance(block, dict) else {}
    d = DEFAULTS
    return {"enabled": _flag(block.get("enabled"), d["enabled"]), "blink": _flag(block.get("blink"), d["blink"]), "blink_calm_minutes": _int(block.get("blink_calm_minutes"), 0, 1440, d["blink_calm_minutes"]),
            "rotate_seconds": _int(block.get("rotate_seconds"), 0, 3600, d["rotate_seconds"]), "default_theme": _theme(block.get("default_theme"), THEME_CHOICES, d["default_theme"]),
            "default_density": _choice(block.get("default_density"), DENSITIES, d["default_density"]), "refresh_seconds": _int(block.get("refresh_seconds"), 5, 120, d["refresh_seconds"]),
            "burn_in_protection": _flag(block.get("burn_in_protection"), d["burn_in_protection"]), "night_dim": _flag(block.get("night_dim"), d["night_dim"]),
            "night_dim_from_hour": _int(block.get("night_dim_from_hour"), 0, 23, d["night_dim_from_hour"]), "night_dim_to_hour": _int(block.get("night_dim_to_hour"), 0, 23, d["night_dim_to_hour"]),
            "show_repo_names": _choice(block.get("show_repo_names"), NAMES, d["show_repo_names"]), "sound": _flag(block.get("sound"), d["sound"]),
            "sound_voices": _voices_text(block.get("sound_voices")), "sound_volume": _int(block.get("sound_volume"), 0, 100, d["sound_volume"]),
            "theme_overview": _theme(block.get("theme_overview"), THEME_CHOICES, d["theme_overview"]), "theme_fleet": _theme(block.get("theme_fleet"), THEME_CHOICES, d["theme_fleet"]), "theme_now": _theme(block.get("theme_now"), THEME_CHOICES, d["theme_now"]),
            "theme_sentinels": _theme(block.get("theme_sentinels"), THEME_CHOICES, d["theme_sentinels"]), "mode": _choice(block.get("mode"), MODES, d["mode"]),
            "rotate_every_seconds": _int(block.get("rotate_every_seconds"), 5, 300, d["rotate_every_seconds"]), "alert_hold_seconds": _int(block.get("alert_hold_seconds"), 5, 600, d["alert_hold_seconds"]),
            "logo_overview": _flag(block.get("logo_overview"), d["logo_overview"]), "logo_fleet": _flag(block.get("logo_fleet"), d["logo_fleet"]), "logo_now": _flag(block.get("logo_now"), d["logo_now"]), "logo_sentinels": _flag(block.get("logo_sentinels"), d["logo_sentinels"]),
            "logo_corner": _choice(block.get("logo_corner"), CORNERS, d["logo_corner"]), "logo_max_width": _int(block.get("logo_max_width"), 16, 640, d["logo_max_width"]),
            "logo_max_height": _int(block.get("logo_max_height"), 16, 320, d["logo_max_height"]), "group_map": _flag(block.get("group_map"), d["group_map"]),
            "menu": _flag(block.get("menu"), d["menu"]), "menu_target": _choice(block.get("menu_target"), ("new", "same"), d["menu_target"]), "menu_max_windows": _int(block.get("menu_max_windows"), 1, 9, d["menu_max_windows"]),
            "menu_rotate_seconds": _int(block.get("menu_rotate_seconds"), 5, 300, d["menu_rotate_seconds"]), "menu_tv_scale": _scale(block.get("menu_tv_scale"), d["menu_tv_scale"]),
            "safe_margin_percent": _int(block.get("safe_margin_percent"), 0, MAX_SAFE, d["safe_margin_percent"]),
            "life": _flag(block.get("life"), d["life"]), "glance_seconds": _int(block.get("glance_seconds"), 0, 30, d["glance_seconds"]), "transition": _choice(block.get("transition"), TRANSITIONS, d["transition"]),
            "hide_healthy": _flag(block.get("hide_healthy"), d["hide_healthy"]), "idle_dim_minutes": _int(block.get("idle_dim_minutes"), 0, 1440, d["idle_dim_minutes"]),
            "min_font_px": _int(block.get("min_font_px"), MIN_FONT_LOW, MIN_FONT_HIGH, d["min_font_px"])}


def global_theme(config):
    """The theme chosen in Settings for the whole product (`ui.theme`): auto, light, dark or one of the sixteen; auto when it is missing or not one of them."""
    ui = (config or {}).get("ui")
    return _theme(ui.get("theme") if isinstance(ui, dict) else None, GLOBAL_THEMES, "auto")


def resolve_theme(cfg, kind=None, global_name="auto"):
    """The theme of one screen: its own setting; when that is `inherit`, the one of all the screens; when that is `inherit` too, the theme of the whole product."""
    for choice in (cfg.get("theme_" + kind) if kind in KINDS else None, cfg.get("default_theme")):
        if choice in SCREEN_THEMES:
            return choice
    return global_name if global_name in GLOBAL_THEMES else "auto"


def enabled(config):
    return settings(config)["enabled"]


def kind_of(path):
    """'overview', 'now' or 'sentinels' for the address of a screen, else None."""
    found = PATH_RE.match(path or "")
    return found.group(1) if found else None


REPO_FILTER_MAX = 80
REPO_FILTER_WORDS = 8


def clean_repo_filter(value):
    """The repository filter of an address (`?repo=`): letters, digits and `. _ - /`, words separated by commas, at most 80 characters; anything else is left out (an empty text means no filter)."""
    text = str(value or "").strip()[:REPO_FILTER_MAX]
    words = [w for w in (part.strip() for part in text.split(",")) if w and all(c.isalnum() or c in "._-/" for c in w)]
    return ",".join(words[:REPO_FILTER_WORDS])


def repo_words(text):
    """The words of a clean filter, in lower case: a repository is kept when its name holds any of them."""
    return [w.lower() for w in clean_repo_filter(text).split(",") if w]


def params(query, cfg, kind=None, global_name="auto"):
    """What the address of one window asks for, checked. `query` is {name: first value}. A window may blink less, sound less and rotate on its own; it can never turn on blinking or sound that the
    settings turned off, and the refresh stays between 5 and 120 seconds. With `screens.mode` = rotate the window turns through the three screens every `rotate_every_seconds` and jumps to the screen
    of a new red (`jump`); ?rotate= changes the pace of one window (0 = this window stays where it is) and ?jump=off keeps the turning without the jumps. A ?theme= is kept for every screen of the
    window (`theme_locked`); without it each screen has the theme the settings give it (see resolve_theme)."""
    monitor = _int(query.get("monitor"), 1, 9, 1)
    turning = cfg.get("mode") == "rotate"
    rotate = _int(query.get("rotate"), 0, 3600, cfg["rotate_every_seconds"] if turning else cfg["rotate_seconds"])
    rotate = 0 if rotate < 5 else rotate      # a turn every second would be a strobe: below 5 seconds is no rotation
    scale = 1.0
    try:
        scale = max(0.5, min(3.0, float(str(query.get("scale", "1")).replace(",", "."))))
    except ValueError:
        pass
    asked = _theme(query.get("theme"), SCREEN_THEMES, None)
    return {"monitor": monitor, "theme": asked or resolve_theme(cfg, kind, global_name), "theme_locked": asked is not None, "density": _choice(query.get("density"), DENSITIES, cfg["default_density"]),
            "refresh": _int(query.get("refresh"), 5, 120, cfg["refresh_seconds"]), "scale": scale, "safe": _int(query.get("safe"), 0, MAX_SAFE, cfg["safe_margin_percent"]), "rotate": rotate, "mode": cfg.get("mode", "three"),
            "jump": turning and rotate > 0 and _flag(query.get("jump"), True), "hold": cfg["alert_hold_seconds"],
            "blink": cfg["blink"] and _flag(query.get("blink"), True), "sound": cfg["sound"] and _flag(query.get("sound"), False), "repo": clean_repo_filter(query.get("repo"))}


_THEME_RULE = re.compile(r'(:root\[data-theme="(?:' + "|".join(re.escape(n) for n in STUDIO_THEMES) + r')"\]\{[^{}]*\})')
_theme_cache = {}


def theme_css():
    """The palettes of the sixteen themes of the main page, as CSS: they are read from the page itself (assets/static/actions_monitor.html), so a colour changed there changes on the screens too."""
    path = paths.STATIC / "actions_monitor.html"
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return ""
    if _theme_cache.get("stamp") != stamp:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        _theme_cache.update(stamp=stamp, css="\n".join(_THEME_RULE.findall(text)))
    return _theme_cache.get("css", "")


def logo_block(cfg, info):
    """What the page needs for the logo: the address of the image (it carries the tag of the file, so a new logo is never shown from the cache), the corner, the largest size in pixels at 1920 x 1080
    (the page scales it with the screen) and on which screens it shows. None when no logo was uploaded."""
    if not isinstance(info, dict) or not info.get("present"):
        return None
    return {"url": "/api/screens/logo?v=" + str(info.get("tag") or "")[:16], "corner": cfg["logo_corner"], "max_width": cfg["logo_max_width"], "max_height": cfg["logo_max_height"],
            "show": {k: bool(cfg["logo_" + k]) for k in KINDS}}


def page_keys():
    """The catalogue keys the page needs: the texts of the screens, the names of the sentinels and the words of the levels."""
    return sorted({k for k in i18n.catalogue_keys() if k.startswith(("ui.scr_", "ui.lv_")) or SENTINEL_KEY.match(k)})


def page_data(kind, cfg, prm, lang=None, logo=None, global_name="auto"):
    """The object embedded in the page: language, texts of this language, the settings that matter to the page, the parameters of the window, the theme of each screen and the logo."""
    return {"screen": kind, "kinds": list(KINDS), "lang": lang or i18n.language(), "html_lang": i18n.HTML_LANG.get(lang or i18n.language(), "en"), "locale": i18n.BROWSER_LOCALE.get(lang or i18n.language(), "en-GB"),
            "texts": {k: i18n.t(k) for k in page_keys()}, "version": TOOL_VERSION,
            "settings": {k: cfg[k] for k in ("blink", "blink_calm_minutes", "burn_in_protection", "night_dim", "night_dim_from_hour", "night_dim_to_hour", "life", "glance_seconds", "transition", "hide_healthy", "idle_dim_minutes", "min_font_px")}, "params": prm,
            "themes": {k: resolve_theme(cfg, k, global_name) for k in KINDS}, "logo": logo_block(cfg, logo)}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# names
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

KEY_FILE = "screens.key"
_KEY = [None]


def installation_key():
    """The secret of this installation that orders the hidden names (private-1, private-2...): made once, kept in a file of the data folder with mode 0600 (never in the configuration, never shown),
    and read again at every start. Where the file cannot be kept (a read-only folder) the key lives in memory for this run."""
    if _KEY[0]:
        return _KEY[0]
    try:
        from github_actions_monitor.security import private_io
        from github_actions_monitor.util import paths
        path = paths.folder("data") / KEY_FILE
        try:
            value = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            value = ""
        if len(value) < 32 or not re.fullmatch(r"[0-9a-f]+", value):
            value = secrets.token_hex(32)
            private_io.write_private(path, value + "\n")
        _KEY[0] = value
    except Exception:   # noqa: BLE001 - without a place to keep it the key only lasts this run
        _KEY[0] = secrets.token_hex(32)
    return _KEY[0]


class Names:
    """What a repository is called on a screen. `meta` is the repo_meta of the cycle ({repo: {"private": True, False or None}}). The numbers of the hidden names are given to the hidden repositories
    ONLY, in the order of an HMAC of the name with the key of the installation: nobody who looks at the screen can tell where a hidden repository falls among the public ones, how many repositories
    there are, or what a hidden name starts with."""

    def __init__(self, repos, meta, mode, key=None):
        self.mode = mode if mode in NAMES else "public"
        self.meta = meta or {}
        self.key = key
        self.repos = sorted(set(repos or []) | set(self.meta))
        self._index = None

    @property
    def index(self):
        if self._index is None:
            key = (self.key or installation_key()).encode("utf-8")
            hidden = sorted((r for r in self.repos if self.hidden(r)), key=lambda r: hmac.new(key, r.encode("utf-8"), hashlib.sha256).digest())
            self._index = {repo: i + 1 for i, repo in enumerate(hidden)}
        return self._index

    def hidden(self, repo):
        if self.mode == "all":
            return False
        if self.mode == "none":
            return True
        return (self.meta.get(repo) or {}).get("private") is not False      # only a visibility that was READ as public shows the name: missing or unknown = private

    def name(self, repo):
        if not self.hidden(repo):
            return repo
        return ("repo-%d" if self.mode == "none" else "private-%d") % self.index.get(repo, 0)


def _parse(stamp):
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _number(value, default=0):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _d(value):
    return value if isinstance(value, dict) else {}


def _l(value):
    return value if isinstance(value, list) else []


def _level(value):
    return value if value in LEVELS else "unknown"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# the common part
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _meta(state, now, refresh, edition):
    data = state or {}
    updated = _parse(data.get("updated"))
    rate = data.get("rate") if isinstance(data.get("rate"), dict) else {}
    reset = _parse(rate.get("reset"))
    remaining, limit = rate.get("remaining"), rate.get("limit")
    low = isinstance(remaining, (int, float)) and isinstance(limit, (int, float)) and limit > 0 and remaining / limit < 0.1
    return {"edition": edition, "have_data": bool(state), "age_seconds": None if updated is None else max(0, int(now - updated)), "refresh_seconds": _int(data.get("refresh_seconds"), 1, 3600, refresh),
            "loading": bool(data.get("loading")), "repos": len(data.get("repos") or []), "paused": bool(data.get("paused_quota")), "offline": bool((data.get("offline") or {}).get("offline")) if isinstance(data.get("offline"), dict) else False,
            "api": {"remaining": remaining if isinstance(remaining, (int, float)) else None, "limit": limit if isinstance(limit, (int, float)) else None,
                    "reset_seconds": None if reset is None else max(0, int(reset - now)), "low": bool(low)}}


def _default_branches(state):
    return {repo: (m or {}).get("branch") for repo, m in (state.get("repo_meta") or {}).items() if isinstance(m, dict)}


def _is_red(run):
    return run.get("status") == "completed" and run.get("conclusion") in RED_CONCLUSIONS


def _red_repos(state, snapshot):
    """Repository -> list of red workflow rows: the sentinel's red list when there is one, else the failures the cycle found."""
    rows = _d(_d(snapshot).get("a2")).get("red")
    if not isinstance(rows, list):
        rows = [{"repo": r.get("repo"), "workflow": r.get("name"), "since": r.get("started"), "streak": 1} for r in (state.get("failing") or []) if isinstance(r, dict)]
    out = {}
    for row in rows:
        if isinstance(row, dict) and row.get("repo"):
            out.setdefault(row["repo"], []).append(row)
    return out


def _stuck_repos(state, snapshot):
    found = {r.get("repo") for r in _l(_d(_d(snapshot).get("a1")).get("stuck")) if isinstance(r, dict)}
    found |= {r.get("repo") for r in (state.get("active") or []) if isinstance(r, dict) and r.get("stuck")}
    found.discard(None)
    return found


def _waiting_repos(state):
    found = {r.get("repo") for r in (state.get("active") or []) if isinstance(r, dict) and r.get("status") in ("queued", "waiting", "pending")}
    found |= {r.get("repo") for r in (state.get("runs") or []) if isinstance(r, dict) and r.get("conclusion") == "action_required"}
    found.discard(None)
    return found


def _progress(run):
    """0..1 from the steps of the jobs of a running run (a finished job counts as done); None when the jobs are not known."""
    jobs = [j for j in (run.get("jobs") or []) if isinstance(j, dict)]
    total = sum(_number(j.get("steps_total")) for j in jobs)
    if not jobs or total <= 0:
        return None
    done = sum(_number(j.get("steps_total")) if j.get("status") == "completed" else _number(j.get("steps_done")) for j in jobs)
    return round(max(0.0, min(1.0, done / total)), 3)


def _kind_of_run(run):
    if run.get("status") != "completed":
        return "run" if run.get("status") == "in_progress" else "wait"
    conclusion = run.get("conclusion")
    if conclusion in RED_CONCLUSIONS:
        return "bad"
    if conclusion == "success":
        return "ok"
    return "skip"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# overview
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _fleet(state, snapshot):
    repos = list(state.get("repos") or [])
    red, stuck, waiting = set(_red_repos(state, snapshot)), _stuck_repos(state, snapshot), _waiting_repos(state)
    seen = {r.get("repo") for r in (state.get("runs") or []) if isinstance(r, dict)}
    counts = {"total": len(repos), "red": 0, "stuck": 0, "waiting": 0, "green": 0, "idle": 0}
    for repo in repos:
        if repo in red:
            counts["red"] += 1
        elif repo in stuck:
            counts["stuck"] += 1
        elif repo in waiting:
            counts["waiting"] += 1
        elif repo in seen:
            counts["green"] += 1
        else:
            counts["idle"] += 1
    return counts


def _series(runs, now, buckets, width):
    """[{"ago": n, "ok": n, "bad": n}] oldest first: the completed runs of the last `buckets` periods of `width` seconds."""
    rows = [{"ago": buckets - 1 - i, "ok": 0, "bad": 0} for i in range(buckets)]
    for run in runs:
        when = _parse(run.get("started"))
        if when is None or run.get("status") != "completed":
            continue
        ago = int((now - when) // width)
        if 0 <= ago < buckets:
            row = rows[buckets - 1 - ago]
            if run.get("conclusion") == "success":
                row["ok"] += 1
            elif run.get("conclusion") in RED_CONCLUSIONS:
                row["bad"] += 1
    return rows


def _heat(runs, now, names, red_repos):
    """The map of heat: a row for each of the busiest repositories (the red ones first), a cell for each hour of the last day: 0 nothing, 1 green, 2 mixed, 3 red."""
    cells = {}
    for run in runs:
        when = _parse(run.get("started"))
        if when is None or run.get("status") != "completed":
            continue
        ago = int((now - when) // 3600)
        if not 0 <= ago < HEAT_BUCKETS:
            continue
        row = cells.setdefault(run.get("repo"), [[0, 0] for _ in range(HEAT_BUCKETS)])[HEAT_BUCKETS - 1 - ago]
        if run.get("conclusion") == "success":
            row[0] += 1
        elif run.get("conclusion") in RED_CONCLUSIONS:
            row[1] += 1
    ranked = sorted(cells, key=lambda r: (r not in red_repos, -sum(a + b for a, b in cells[r]), str(r)))[:HEAT_ROWS]
    out = []
    for repo in ranked:
        out.append({"repo": names.name(repo), "red": repo in red_repos, "cells": [0 if not (a or b) else (3 if b and not a else 2 if b else 1) for a, b in cells[repo]]})
    return out


def _top_red(state, snapshot, names, now):
    rows = []
    for repo, found in _red_repos(state, snapshot).items():
        for row in found:
            since = _parse(row.get("since"))
            rows.append({"repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(row.get("workflow") or "")[:60], "seconds": None if since is None else max(0, int(now - since)),
                         "streak": _int(row.get("streak"), 0, 9999, 1)})
    rows.sort(key=lambda r: (-(r["seconds"] if r["seconds"] is not None else -1), r["repo"]))
    return rows[:TOP_RED]


def _events(state, names, now, limit=EVENTS):
    runs = [r for r in (state.get("runs") or []) if isinstance(r, dict) and _parse(r.get("started")) is not None]
    runs.sort(key=lambda r: _parse(r["started"]), reverse=True)
    out = []
    for run in runs[:limit]:
        repo = run.get("repo")
        out.append({"ago": max(0, int(now - _parse(run["started"]))), "kind": _kind_of_run(run), "repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(run.get("name") or "")[:60],
                    "seconds": _int(run.get("seconds"), 0, 10 ** 7, 0)})
    return out


def _queue(state, snapshot):
    active = [r for r in (state.get("active") or []) if isinstance(r, dict)]
    minutes = sum(_number(r.get("min24")) for r in _l(_d(_d(snapshot).get("a7")).get("rows")) if isinstance(r, dict))
    minutes7 = sum(_number(r.get("min7d")) for r in _l(_d(_d(snapshot).get("a7")).get("rows")) if isinstance(r, dict))
    approval = sum(1 for r in (state.get("runs") or []) if isinstance(r, dict) and r.get("conclusion") == "action_required")
    return {"running": sum(1 for r in active if r.get("status") == "in_progress"), "queued": sum(1 for r in active if r.get("status") in ("queued", "waiting", "pending")), "approval": approval,
            "minutes24": round(minutes), "minutes7d": round(minutes7)}


def _score(score):
    if not isinstance(score, dict) or not score.get("enabled", True):
        return {"state": "off", "value": None, "letter": None, "trend": None}
    value = score.get("score")
    return {"state": str(score.get("state") or "calibrating")[:20], "value": value if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
            "letter": score.get("letter") if isinstance(score.get("letter"), str) else None, "trend": score.get("trend") if isinstance(score.get("trend"), (int, float)) and not isinstance(score.get("trend"), bool) else None}


def _alert_summary(alerts):
    summary = (alerts or {}).get("summary") if isinstance(alerts, dict) else None
    summary = summary if isinstance(summary, dict) else {}
    by_level = summary.get("by_level") if isinstance(summary.get("by_level"), dict) else {}
    return {"total": _int(summary.get("total"), 0, 10 ** 6, 0), "by_level": {k: _int(by_level.get(k), 0, 10 ** 6, 0) for k in ("critical", "error", "warning", "info")}}


GROUPS_SHOWN = 12
GROUP_BY = ("ecosystem", "label", "state", "none")


def group_map(view, labels=None):
    """The map of the fleet by groups for the overview: the groups of the fleet view (`health/fleet.py`, the same grouping and the same order: the riskiest first) with how many of their repositories are
    bad, warn, ok or unknown. Only the name of a group and numbers: no repository is named here, so `screens.show_repo_names` has nothing to hide. None when there is no view."""
    if not isinstance(view, dict) or not isinstance(view.get("groups"), list):
        return None
    labels = labels if isinstance(labels, dict) else {}
    by = view.get("group_by") if view.get("group_by") in GROUP_BY else "ecosystem"
    rows = []
    for group in view["groups"]:
        if not isinstance(group, dict):
            continue
        key = str(group.get("key") or "")[:40]
        rows.append({"key": key, "label": str(labels.get(key, key) if by == "ecosystem" else key)[:40], "repos": _int(group.get("repos"), 0, 10 ** 6, 0), "bad": _int(group.get("bad"), 0, 10 ** 6, 0),
                     "warn": _int(group.get("warn"), 0, 10 ** 6, 0), "ok": _int(group.get("ok"), 0, 10 ** 6, 0), "unknown": _int(group.get("unknown"), 0, 10 ** 6, 0)})
    return {"by": by, "groups": rows[:GROUPS_SHOWN], "more": max(0, len(rows) - GROUPS_SHOWN)}


FLEET_GROUPS, FLEET_TILES = 8, 60
STATE_ORDER = {"bad": 0, "warn": 1, "unknown": 2, "ok": 3}


def build_fleet(state, snapshot, alerts, score, names, now, view=None, labels=None):
    """The Fleet screen: the repositories of the fleet by group, each one a tile with its state (the grouping and the order of the Fleet tab: the riskiest group first). A group keeps its first `FLEET_TILES`
    tiles, worst first, and says how many it left out; the screen keeps the first `FLEET_GROUPS` groups and says how many more there are. A repository is named as the rest of the screens name it
    (`screens.show_repo_names`): a hidden one is private-N and nothing more. None for `groups` when the fleet view is not there."""
    out = {"fleet": _fleet(state, snapshot), "groups": None, "totals": {k: 0 for k in STATE_ORDER}, "alerts": _alert_summary(alerts), "by": "ecosystem", "more_groups": 0, "tiles_shown": FLEET_TILES}
    if not isinstance(view, dict) or not isinstance(view.get("groups"), list):
        return out
    labels = labels if isinstance(labels, dict) else {}
    by = view.get("group_by") if view.get("group_by") in GROUP_BY else "ecosystem"
    rows = {}
    for row in view.get("rows") or []:
        if isinstance(row, dict) and isinstance(row.get("repo"), str):
            rows.setdefault(str(row.get("group") or ""), []).append(row)
    groups = []
    for group in view["groups"]:
        if not isinstance(group, dict):
            continue
        key = str(group.get("key") or "")[:40]
        members = sorted(rows.get(key, []), key=lambda r: (STATE_ORDER.get(r.get("state"), 2), -_int(r.get("risk"), 0, 10 ** 9, 0)))
        tiles = [{"name": names.name(r["repo"])[:60], "state": r.get("state") if r.get("state") in STATE_ORDER else "unknown", "running": _int(r.get("running"), 0, 10 ** 4, 0), "red": _int(r.get("red_workflows"), 0, 10 ** 4, 0)}
                 for r in members[:FLEET_TILES]]
        groups.append({"key": key, "label": str(labels.get(key, key) if by == "ecosystem" else key)[:40], "repos": _int(group.get("repos"), 0, 10 ** 6, 0), "bad": _int(group.get("bad"), 0, 10 ** 6, 0),
                       "warn": _int(group.get("warn"), 0, 10 ** 6, 0), "ok": _int(group.get("ok"), 0, 10 ** 6, 0), "unknown": _int(group.get("unknown"), 0, 10 ** 6, 0), "tiles": tiles,
                       "hidden": max(0, len(members) - FLEET_TILES)})
    out.update(groups=groups[:FLEET_GROUPS], by=by, more_groups=max(0, len(groups) - FLEET_GROUPS), totals={k: sum(g[k] for g in groups) for k in STATE_ORDER})
    return out


def build_overview(state, snapshot, alerts, score, names, now, groups=None):
    runs = [r for r in (state.get("runs") or []) if isinstance(r, dict)]
    red = _red_repos(state, snapshot)
    return {"groups": groups, "score": _score(score), "fleet": _fleet(state, snapshot), "trend24": _series(runs, now, 24, 3600), "trend7d": _series(runs, now, 7, 86400), "heat": _heat(runs, now, names, set(red)),
            "top_red": _top_red(state, snapshot, names, now), "queue": _queue(state, snapshot), "events": _events(state, names, now), "alerts": _alert_summary(alerts)}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# now
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def build_now(state, snapshot, alerts, score, names, now):
    active = [r for r in (state.get("active") or []) if isinstance(r, dict)]
    runs = [r for r in (state.get("runs") or []) if isinstance(r, dict)]
    branches = _default_branches(state)

    def row(run):
        repo = run.get("repo")
        started = _parse(run.get("started"))
        return {"repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(run.get("name") or "")[:60], "event": str(run.get("event") or "")[:20],
                "state": "queued" if run.get("status") in ("queued", "waiting", "pending") else "running", "seconds": _int(run.get("seconds"), 0, 10 ** 7, 0) if started is None else max(0, int(now - started)),
                "progress": _progress(run), "stuck": bool(run.get("stuck")), "jobs": len(run.get("jobs") or [])}
    running = sorted((row(r) for r in active if r.get("status") == "in_progress"), key=lambda r: (not r["stuck"], -r["seconds"]))[:ACTIVE_ROWS]
    queued = sorted((row(r) for r in active if r.get("status") in ("queued", "waiting", "pending")), key=lambda r: -r["seconds"])[:ACTIVE_ROWS]
    approval = []
    for run in runs:
        if run.get("conclusion") == "action_required":
            started = _parse(run.get("started"))
            approval.append({"repo": names.name(run.get("repo")), "ago": None if started is None else max(0, int(now - started))})
    recent_bad = []
    for run in sorted(runs, key=lambda r: _parse(r.get("started")) or 0, reverse=True):
        started = _parse(run.get("started"))
        if _is_red(run) and started is not None and now - started < 6 * 3600:
            repo = run.get("repo")
            recent_bad.append({"repo": names.name(repo), "workflow": "" if names.hidden(repo) else str(run.get("name") or "")[:60], "ago": max(0, int(now - started)), "attempt": _int(run.get("attempt"), 1, 99, 1)})
    merges = []
    for run in sorted(runs, key=lambda r: _parse(r.get("started")) or 0, reverse=True):
        repo = run.get("repo")
        if run.get("status") == "completed" and run.get("conclusion") == "success" and run.get("event") in ("push", "merge_group") and branches.get(repo) and run.get("branch") == branches.get(repo):
            started = _parse(run.get("started"))
            merges.append({"repo": names.name(repo), "release": bool(re.search(r"release", str(run.get("name") or ""), re.I)), "ago": None if started is None else max(0, int(now - started))})
        if len(merges) >= MERGES:
            break
    candidates = [{"repo": names.name(c.get("repo")), "entries": _int(c.get("entries"), 0, 9999, 0), "age_days": round(_number(c.get("age_days")), 1)}
                  for c in _l(_d(_d(snapshot).get("a5")).get("candidates")) if isinstance(c, dict)][:MERGES]
    pending = [{"repo": names.name(c.get("repo")), "hours": round(_number(c.get("hours")), 1)} for c in _l(_d(_d(snapshot).get("a5")).get("pending_sign")) if isinstance(c, dict)][:MERGES]
    timeline = _events(state, names, now, TIMELINE)
    return {"running": running, "queued": queued, "approval": approval[:ACTIVE_ROWS], "failures": recent_bad[:FAILURES], "merges": merges, "next_releases": candidates, "pending_sign": pending,
            "timeline": timeline, "totals": {"running": len([r for r in active if r.get("status") == "in_progress"]), "queued": len([r for r in active if r.get("status") in ("queued", "waiting", "pending")]),
                                              "approval": len(approval), "failures": len(recent_bad)}}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# sentinels
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _count(snapshot, key):
    """How many open findings a sentinel panel holds, from the lists the snapshot already carries."""
    panel = (snapshot or {}).get(key)
    if not isinstance(panel, dict):
        return None
    def size(name):
        value = panel.get(name)
        return len(value) if isinstance(value, list) else 0
    if key == "a1":
        return size("stuck") + size("issues")
    if key == "a2":
        return size("red")
    if key == "a3":
        return _int(panel.get("codeql_total"), 0, 10 ** 6, 0) + _int(panel.get("dependabot_total"), 0, 10 ** 6, 0) + _int(panel.get("secret_total"), 0, 10 ** 6, 0)
    if key == "a4":
        return size("dependabot")
    if key == "a5":
        return size("candidates") + size("pending_sign")
    if key == "a6":
        return sum(len(r.get("problems") or []) for r in (panel.get("rows") or []) if isinstance(r, dict))
    if key == "a8":
        return size("files")
    if key == "a9":
        return size("boards")
    if key in ("a10", "a11"):
        return sum(_int(s.get("count"), 0, 10 ** 6, 0) for s in (panel.get("sections") or []) if isinstance(s, dict))
    return 0


def build_sentinels(state, snapshot, alerts, score, names, now, refresh):
    snap = snapshot if isinstance(snapshot, dict) else None
    broken = {str(e.get("section")) for e in ((snap or {}).get("errors") or []) if isinstance(e, dict)}
    generated = _parse((snap or {}).get("generated"))
    age = None if generated is None else max(0, int(now - generated))
    cache = (snap or {}).get("cache_age_seconds")
    age = age if cache is None else max(age or 0, int(_number(cache)))
    cycle = max(5, _int((state or {}).get("refresh_seconds"), 1, 3600, refresh))
    cards = []
    for key in SENTINELS:
        panel = (snap or {}).get(key) if snap else None
        level = _level((panel or {}).get("level")) if isinstance(panel, dict) else "unknown"
        cards.append({"id": key, "level": level, "open": _count(snap, key), "readable": bool(isinstance(panel, dict) and key not in broken and level != "unknown")})
    totals = (snap or {}).get("totals") if snap else None
    totals = totals if isinstance(totals, dict) else {}
    by_sentinel = _d(_d(alerts).get("summary")).get("by_sentinel")
    return {"enabled": bool(snap and snap.get("enabled", True)), "level": _level((snap or {}).get("level")), "loading": bool(snap and snap.get("loading")), "sweep": {"age_seconds": age, "cycle_seconds": cycle,
            "progress": None if age is None else round(max(0.0, min(1.0, age / cycle)), 3)}, "cards": cards,
            "totals": {k: _int(totals.get(k), 0, 10 ** 6, 0) for k in ("red", "stuck", "new_alerts", "candidates", "prs", "codeql", "dependabot", "secret")},
            "alerts": {**_alert_summary(alerts), "by_sentinel": {str(k)[:20]: _int(v, 0, 10 ** 6, 0) for k, v in (by_sentinel or {}).items()} if isinstance(by_sentinel, dict) else {}}}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# the payload
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _only(obj, keep):
    """A copy of a part of the cycle or of the snapshot without the rows of the repositories that are not kept (a list of rows that name a repository, at any depth)."""
    if isinstance(obj, dict):
        return {k: _only(v, keep) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_only(v, keep) for v in obj if not (isinstance(v, dict) and isinstance(v.get("repo"), str) and v["repo"] not in keep)]
    return obj


def narrow(data, snapshot, alerts, names, words):
    """What the Overview and Right now screens show for a repository filter: only the repositories whose name is SHOWN on the screen and holds one of the words. A hidden repository (private, or any when
    `screens.show_repo_names` is none) is never kept, so that the filter cannot be used to find out what a hidden name contains. The figures that are counted from rows (red, stuck, queued, alerts) follow the
    rows that are kept. Returns (data, snapshot, alerts)."""
    keep = {r for r in set(data.get("repos") or []) | set(data.get("repo_meta") or {}) if not names.hidden(r) and any(w in r.lower() for w in words)}
    data = {k: (sorted(r for r in v if r in keep) if k == "repos" and isinstance(v, list) else {r: m for r, m in v.items() if r in keep} if k == "repo_meta" and isinstance(v, dict) else _only(v, keep)) for k, v in data.items()}
    snapshot = _only(snapshot, keep) if isinstance(snapshot, dict) else snapshot
    if isinstance(alerts, dict):
        rows = [a for a in (alerts.get("alerts") or []) if isinstance(a, dict) and a.get("repo") in keep]
        levels = {}
        for row in rows:
            levels[row.get("level")] = levels.get(row.get("level"), 0) + 1
        by_sentinel = {}
        for row in rows:
            by_sentinel[row.get("sentinel")] = by_sentinel.get(row.get("sentinel"), 0) + 1
        alerts = {**alerts, "alerts": rows, "summary": {**_d(alerts.get("summary")), "total": len(rows), "by_level": levels, "by_sentinel": {str(k): v for k, v in by_sentinel.items() if k}}}
    return data, snapshot, alerts


def build(kind, state, snapshot, alerts, score, cfg, edition="complete", now=None, fleet_view=None, labels=None, repo=""):
    """The answer of /api/screens/data for one screen, from what the monitor holds. `state` is the last cycle (STATE["data"], or None before the first), `snapshot` the sentinel snapshot (or None),
    `alerts` the alerts payload, `score` the latest score, `fleet_view` the answer of the fleet view for the map of groups of the overview (and `labels` the names of the ecosystems). Never raises for missing parts: a part that is not there is empty and `meta.have_data` says so."""
    if kind not in KINDS:
        raise ValueError("unknown screen")
    now = time.time() if now is None else now
    data = state if isinstance(state, dict) else {}
    names = Names(data.get("repos"), data.get("repo_meta"), cfg["show_repo_names"])
    words = repo_words(repo) if kind in ("overview", "now") else []
    if words:
        data, snapshot, alerts = narrow(data, snapshot, alerts, names, words)
        names = Names(data.get("repos"), data.get("repo_meta"), cfg["show_repo_names"], names.key)
        score, fleet_view = None, None      # the score and the map of groups are of the whole fleet: with a filter they are not shown
    out = {"schema": SCHEMA, "screen": kind, "version": TOOL_VERSION, "epoch": int(now), "names": cfg["show_repo_names"], "meta": _meta(state, now, cfg["refresh_seconds"], edition)}
    if words:
        out["meta"]["repos"] = len(data.get("repos") or [])
    if kind == "overview":
        out.update(build_overview(data, snapshot, alerts, score, names, now, group_map(fleet_view, labels) if cfg.get("group_map", True) else None))
    elif kind == "fleet":
        out.update(build_fleet(data, snapshot, alerts, score, names, now, fleet_view, labels))
    elif kind == "now":
        out.update(build_now(data, snapshot, alerts, score, names, now))
    else:
        out.update(build_sentinels(data, snapshot, alerts, score, names, now, cfg["refresh_seconds"]))
    return out
