# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The phone web app (PWA) of the monitor, as text the server can serve: the web app manifest, the small service worker and the `?view=` parameters.

The service worker caches only the static shell (the page, its script and style, the icons): never an answer of `/api/` and never anything under `/auth/`, so no data of the monitor and no token
stays in a cache of the phone. A network error on the shell falls back to the cached copy; an error on data is left to the page, which shows its own "offline" state. No GitHub token is ever
stored on the device: the only secret the phone holds is the token of the monitor, in the page's own storage, and this module never sees it."""
import json
import re

VIEWS = ("now", "alerts", "live")
DEFAULT_VIEW = "now"
SHELL_PATHS = ("/", "/static/actions_monitor.html", "/manifest.webmanifest", "/static/icon-192.png", "/static/icon-512.png")
NEVER_CACHE_PREFIXES = ("/api/", "/auth/", "/metrics", "/sw.js")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}\Z")
CACHE_RE = re.compile(r"^[a-z][a-z0-9-]{2,30}\Z")


def parse_view(query):
    """(view, chrome): `?view=now|alerts|live` (anything else = now) and `?chrome=0` to hide the page's frame on a small screen."""
    view = str((query or {}).get("view") or "").strip().lower()
    chrome = str((query or {}).get("chrome") or "1").strip() != "0"
    return (view if view in VIEWS else DEFAULT_VIEW), chrome


def manifest(cfg, lang="en"):
    """The `manifest.webmanifest` (a dict): standalone display, the start URL on the `now` view and the icons of the static folder. Bad colours or names in `cfg` are replaced by the defaults."""
    from github_actions_monitor.phase4 import DEFAULTS
    base = DEFAULTS["pwa"]
    name = cfg.get("name") if isinstance(cfg.get("name"), str) and 0 < len(cfg["name"]) <= 45 else base["name"]
    short = cfg.get("short_name") if isinstance(cfg.get("short_name"), str) and 0 < len(cfg["short_name"]) <= 12 else base["short_name"]
    theme = cfg.get("theme_color") if COLOR_RE.match(str(cfg.get("theme_color"))) else base["theme_color"]
    back = cfg.get("background_color") if COLOR_RE.match(str(cfg.get("background_color"))) else base["background_color"]
    return {
        "name": name, "short_name": short, "lang": {"zh": "zh-CN", "pt": "pt-PT"}.get(lang, lang), "start_url": "/?view=now&chrome=0", "scope": "/", "display": "standalone",
        "orientation": "any", "theme_color": theme, "background_color": back,
        "icons": [{"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                  {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
        "shortcuts": [{"name": v, "url": "/?view={}&chrome=0".format(v)} for v in VIEWS],
    }


def manifest_json(cfg, lang="en"):
    return json.dumps(manifest(cfg, lang), ensure_ascii=False, indent=2, sort_keys=True)


def service_worker(cfg, build):
    """The JavaScript of `/sw.js`. `build` (the product version) is part of the cache name, so a new version drops the old shell. The worker answers a navigation or a shell file from the network first
    and falls back to the cache; every path under NEVER_CACHE_PREFIXES goes straight to the network and is never stored."""
    cache = cfg.get("cache_name") if CACHE_RE.match(str(cfg.get("cache_name"))) else "gam-shell"
    key = "{}-{}".format(cache, re.sub(r"[^0-9A-Za-z.-]", "", str(build))[:20] or "0")
    return (
        "'use strict';\n"
        "const CACHE = @CACHE@;\nconst SHELL = @SHELL@;\nconst NEVER = @NEVER@;\n"
        "self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });\n"
        "self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });\n"
        "self.addEventListener('fetch', e => {\n"
        "  const req = e.request; const url = new URL(req.url);\n"
        "  if (req.method !== 'GET' || url.origin !== self.location.origin) return;\n"
        "  if (NEVER.some(p => url.pathname.startsWith(p))) return;\n"
        "  const shell = req.mode === 'navigate' || SHELL.includes(url.pathname);\n"
        "  if (!shell) return;\n"
        "  e.respondWith(fetch(req).then(r => { if (r.ok && r.type === 'basic') { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req.mode === 'navigate' ? '/' : url.pathname, copy)); } return r; })\n"
        "    .catch(() => caches.match(req.mode === 'navigate' ? '/' : url.pathname)));\n"
        "});\n"
    ).replace("@CACHE@", json.dumps(key)).replace("@SHELL@", json.dumps(list(SHELL_PATHS))).replace("@NEVER@", json.dumps(list(NEVER_CACHE_PREFIXES)))


def page_head_links():
    """The two lines the page needs in its <head> to be installable (the page itself is a common file: see the integration notes)."""
    return ['<link rel="manifest" href="/manifest.webmanifest">', '<meta name="theme-color" content="#0d1117">']


def refresh_plan(view, endpoints):
    """What a pull-to-refresh does: the list of API calls to repeat for the view (never a scrape of the page). `endpoints` is the map view -> list of paths the page uses."""
    return list(endpoints.get(view) or endpoints.get(DEFAULT_VIEW) or [])


VIEW_ENDPOINTS = {"now": ["/api/v1/status", "/api/v1/alerts?profile=mobile&limit=20"], "alerts": ["/api/v1/alerts?profile=mobile"], "live": ["/api/v1/live-events?profile=mobile", "/api/v1/live-status"]}
