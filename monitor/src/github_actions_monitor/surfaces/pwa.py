# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor as an installable app on a phone, a tablet or a computer (PWA): the manifest, the service worker, the icons and the page that is shown when the monitor cannot be reached.

Everything is opt-in (`pwa.enabled`, off by default) and nothing here reads GitHub or writes anything. What the service worker keeps is only the offline page and the icons: NEVER the page of the monitor
or any answer of the API, so what the monitor knows about the repositories is never left in the cache of a phone. A page that is not reachable shows the offline page with a button to try again; when the
app comes back to the front, or the network returns, the page asks the monitor for fresh data at once (`pwa.refresh_on_return`, on).

  settings(raw)            the `pwa` block with every value in its range
  manifest(lang, theme)    the web app manifest (dict)
  service_worker(version)  the text of /sw.js (the name of its cache carries the version of the monitor, so an update drops the old one)
  icon(size)               the PNG of the icon, drawn here (no file to ship)
  head(cfg)                the tags the page needs in its <head> (manifest, theme colour, icons for Apple); '' while the PWA is off
"""
import struct
import zlib
from functools import lru_cache

DEFAULTS = {"enabled": False, "refresh_on_return": True}
SIZES = (192, 512)
THEME = "#0d1117"
ACCENT = "#2f81f7"


def settings(raw):
    block = (raw or {}).get("pwa") if isinstance(raw, dict) else None
    block = block if isinstance(block, dict) else {}
    return {"enabled": block.get("enabled") is True, "refresh_on_return": block.get("refresh_on_return") is not False}


def manifest(lang="en", name="GitHub Actions Monitor", short="Actions"):
    return {"name": name, "short_name": short, "description": name, "lang": lang, "start_url": "/?source=pwa", "scope": "/", "id": "/", "display": "standalone",
            "orientation": "any", "background_color": THEME, "theme_color": THEME,
            "icons": [{"src": f"/pwa/icon-{size}.png", "sizes": f"{size}x{size}", "type": "image/png", "purpose": "any maskable"} for size in SIZES]}


def service_worker(version):
    """The worker: it takes the offline page and the icons when it is installed and answers a navigation that fails with the offline page. Anything of the API, any other file and any request that is not a
    plain GET of this address goes to the network untouched and is never stored."""
    return """// service worker of the monitor %(v)s: keeps only the offline page and the icons, never data
const CACHE = "ghamon-%(v)s";
const KEEP = ["/pwa/offline", "/pwa/icon-192.png", "/pwa/icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(KEEP)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== self.location.origin) return;
  if (KEEP.includes(u.pathname)) { e.respondWith(caches.match(r).then(hit => hit || fetch(r))); return; }
  if (r.mode === "navigate") { e.respondWith(fetch(r).catch(() => caches.match("/pwa/offline").then(hit => hit || new Response("offline", {status: 503})))); }
});
""" % {"v": version}


def offline_page(title, text, retry, lang="en"):
    """The page of a monitor that cannot be reached: plain, no script from outside, one button."""
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")      # noqa: E731
    return ('<!doctype html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>%s</title>'
            '<style>:root{color-scheme:dark light}body{margin:0;min-height:100vh;display:grid;place-items:center;font:16px system-ui,sans-serif;background:%s;color:#e6edf3;text-align:center;padding:24px}'
            'button{margin-top:16px;padding:12px 24px;min-height:44px;font:inherit;border:0;border-radius:8px;background:%s;color:#fff}</style></head>'
            '<body><main><h1>%s</h1><p>%s</p><button type="button" onclick="location.href=\'/\'">%s</button></main></body></html>') % (esc(lang), esc(title), THEME, ACCENT, esc(title), esc(text), esc(retry))


def _chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


@lru_cache(maxsize=4)
def icon(size):
    """A square icon: a rounded dark tile with a blue ring and a white check mark, as a PNG (RGBA), drawn pixel by pixel."""
    size = int(size)
    bg = (13, 17, 23, 255)
    blue = (47, 129, 247, 255)
    white = (255, 255, 255, 255)
    radius = size * 0.18
    centre = (size - 1) / 2
    ring_out, ring_in = size * 0.34, size * 0.28

    def inside_tile(x, y):
        dx = max(abs(x - centre) - (size / 2 - radius), 0)
        dy = max(abs(y - centre) - (size / 2 - radius), 0)
        return dx * dx + dy * dy <= radius * radius

    def near(x, y, a, b, width):
        (x1, y1), (x2, y2) = a, b
        px, py = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * px + (y - y1) * py) / (px * px + py * py)))
        return (x - (x1 + t * px)) ** 2 + (y - (y1 + t * py)) ** 2 <= (width / 2) ** 2
    a, b, c = (size * 0.35, size * 0.52), (size * 0.46, size * 0.64), (size * 0.66, size * 0.38)
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            if not inside_tile(x, y):
                pixel = (0, 0, 0, 0)
            elif near(x, y, a, b, size * 0.07) or near(x, y, b, c, size * 0.07):
                pixel = white
            else:
                dist = ((x - centre) ** 2 + (y - centre) ** 2) ** 0.5
                pixel = blue if ring_in <= dist <= ring_out else bg
            raw.extend(pixel)
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")


def head(cfg):
    """The tags of the page for the app: the manifest (sent with the cookie, because the network mode asks for the access token on every request), the colour of the bar and the icon for Apple."""
    if not cfg.get("enabled"):
        return ""
    return ('<link rel="manifest" href="/manifest.webmanifest" crossorigin="use-credentials"><meta name="theme-color" content="%s">'
            '<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><link rel="apple-touch-icon" href="/pwa/icon-192.png">' % THEME)


REGISTER_JS = ('if("serviceWorker" in navigator){window.addEventListener("load",()=>{navigator.serviceWorker.register("/sw.js",{scope:"/"}).catch(()=>{})})}')
