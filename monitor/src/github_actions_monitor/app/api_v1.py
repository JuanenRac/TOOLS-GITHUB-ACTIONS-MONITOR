# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The read API for clients, version 1, as pure functions. Switched by `api.v1_enabled` ("auto" by default: on in the service mode, off for one person at one computer); read only; nothing here talks to the network, the disk or the clock.

  /api/v1/<route>     every read route that already exists, under the prefix `/api/v1/` (the same answer, the same roles, plus the header `X-API-Version: 1`)
  /api/v1/me          who is asking: the mode (individual or team), the user, the role and the accounts the session may see
  /api/v1/repos       the repositories the monitor watches, one line each, in pages (keyset cursor), with `fields=` and `profile=compact`
  /api/v1/openapi.json  a light OpenAPI 3 description of the two routes above

The two new routes answer errors in one envelope: {"error": slug, "code": "api.something", "message": text in the language asked}. The codes are stable and never translated; the message is.
A cursor is signed, carries the fingerprint of the query it was made for and a time to live: a cursor of another query, a forged one or an old one is refused (400 `api.bad_cursor`).
The shape of the answers is part of the contract (docs/schemas/api_contract.json, section `v1_endpoints`): a field may be added, never removed or renamed."""
import base64
import gzip
import hashlib
import hmac
import json
import re

from github_actions_monitor import i18n

API_VERSION = "1"
CONTRACT_VERSION = "1.0"      # grows with every key added to the frozen shape (minor); a key removed or renamed would be a new API version
PREFIX = "/api/v1"
VERSION_HEADER = "X-API-Version"
OWN_ROUTES = ("/api/v1/me", "/api/v1/repos", "/api/v1/openapi.json")
PROFILES = ("full", "compact")
FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}\Z")
VERSION_RE = re.compile(r"^/api/v(\d{1,3})(?:/|\Z)")
CURSOR_MAX_LENGTH = 512
ALPHABET_RE = re.compile(r"^[A-Za-z0-9_-]+\Z")
ERROR_SLUGS = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "rate_limited", 500: "server_error"}
MODES = ("auto", "on", "off")
DEFAULTS = {"v1_enabled": "auto", "default_limit": 50, "max_limit": 200, "cursor_ttl_seconds": 900, "gzip_min_bytes": 1024}
BOUNDS = {"default_limit": (1, 1000), "max_limit": (1, 1000), "cursor_ttl_seconds": (30, 86400), "gzip_min_bytes": (0, 10_000_000)}

#: what each own route promises. `required` is in every item of the full answer; `compact` is the short list of `profile=compact` (always a subset of `required`).
CONTRACT = {
    "me": {"path": "/api/v1/me", "kind": "object", "required": ["schema", "api_version", "contract", "version", "edition", "mode", "authenticated", "user", "role", "accounts", "capabilities", "limits"],
           "compact": ["mode", "authenticated", "user", "role"]},
    "repos": {"path": "/api/v1/repos", "kind": "list", "item": ["repo", "ecosystem", "state", "risk", "runs_24h", "failures_24h", "red_workflows", "stuck_runs", "alerts", "last_run_at"],
              "compact": ["repo", "state", "risk"], "filters": ["state", "ecosystem", "q"]},
}
for _name, _spec in CONTRACT.items():
    assert set(_spec["compact"]) <= set(_spec.get("item") or _spec["required"]), _name


def settings(config):
    """The `api` block of the configuration over DEFAULTS; a value of the wrong type or out of its bounds keeps the default (v1_enabled is read from `api.v1_enabled`)."""
    block = (config or {}).get("api")
    block = block if isinstance(block, dict) else {}
    out = dict(DEFAULTS)
    mode = block.get("v1_enabled")
    if isinstance(mode, bool):      # the old switch (true / false) keeps its meaning
        out["v1_enabled"] = "on" if mode else "off"
    elif isinstance(mode, str) and mode in MODES:
        out["v1_enabled"] = mode
    for key, (low, high) in BOUNDS.items():
        value = block.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    if out["default_limit"] > out["max_limit"]:
        out["default_limit"] = out["max_limit"]
    return out


def enabled(cfg, service):
    """Whether the prefix answers: `on` always, `off` never, `auto` (the default) when the monitor runs as a service (the process of an account, the image, the unit of systemd) and not for one person at one computer."""
    return cfg["v1_enabled"] == "on" or (cfg["v1_enabled"] == "auto" and bool(service))


# ---- the error envelope ---------------------------------------------------------------------------------------------------------------------

class ApiError(Exception):
    def __init__(self, status, code, **values):
        super().__init__(code)
        self.status, self.code, self.values = status, code, values

    def envelope(self):
        """(status, body) with the message in the language in use; a status that is not in the table becomes a 500."""
        status = self.status if self.status in ERROR_SLUGS else 500
        return status, {"error": ERROR_SLUGS[status], "code": self.code, "message": i18n.t(self.code, **self.values)}


def route_of(path):
    """(version, rest) for a path under `/api/v<N>/`, else (None, path). `rest` is the old route (`/api/v1/alerts` -> `/api/alerts`)."""
    match = VERSION_RE.match(path or "")
    if not match:
        return None, path
    return match.group(1), "/api/" + path[match.end():]


# ---- paging ---------------------------------------------------------------------------------------------------------------------------------

def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def fingerprint(endpoint, filters):
    """A short, stable text for a query (endpoint and filters, without the paging): a cursor made for one query is refused for another."""
    raw = json.dumps([endpoint, sorted((str(k), str(v)) for k, v in (filters or {}).items() if v not in (None, ""))], separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def parse_limit(value, default, maximum):
    if value in (None, ""):
        return default
    try:
        number = int(str(value))
    except ValueError:
        raise ApiError(400, "api.bad_limit", max=maximum) from None
    if not 1 <= number <= maximum:
        raise ApiError(400, "api.bad_limit", max=maximum)
    return number


def make_cursor(secret, query_fp, last_key, now):
    body = _b64(json.dumps({"f": query_fp, "k": last_key, "t": int(now)}, separators=(",", ":")).encode("utf-8"))
    return body + "." + _b64(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()[:16])


def read_cursor(secret, cursor, query_fp, now, ttl):
    """The key a cursor points after; anything wrong (shape, signature, another query, too old, from the future) raises ApiError(400, api.bad_cursor)."""
    bad = ApiError(400, "api.bad_cursor")
    if not isinstance(cursor, str) or not cursor or len(cursor) > CURSOR_MAX_LENGTH or cursor.count(".") != 1:
        raise bad
    body, mac = cursor.split(".")
    if not ALPHABET_RE.match(body) or not ALPHABET_RE.match(mac):      # a cursor is text of the url-safe alphabet; anything else (a letter that is not ASCII included) is a plain "no", never an exception
        raise bad
    if not hmac.compare_digest(mac.encode("ascii"), _b64(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()[:16]).encode("ascii")):
        raise bad
    try:
        data = json.loads(_unb64(body))
    except (ValueError, UnicodeDecodeError):
        raise bad from None
    if not isinstance(data, dict) or data.get("f") != query_fp or not isinstance(data.get("t"), int) or now - data["t"] > ttl or data["t"] > now + 60:
        raise bad
    return data.get("k")


def paginate(items, *, key, endpoint, filters, secret, now, cursor=None, limit=None, default_limit=50, max_limit=200, ttl=900):
    """One page of `items` in ascending order of `key(item)` (unique): {"items", "next_cursor", "limit"}. Keyset paging: an item added between two requests never repeats or shifts a page."""
    size = parse_limit(limit, default_limit, max_limit)
    fp = fingerprint(endpoint, filters)
    ordered = sorted(items, key=key)
    if cursor:
        after = read_cursor(secret, cursor, fp, now, ttl)
        ordered = [item for item in ordered if key(item) > after] if after is not None else ordered
    page = ordered[:size]
    more = len(ordered) > size
    return {"items": page, "next_cursor": make_cursor(secret, fp, key(page[-1]), now) if more and page else None, "limit": size}


# ---- compact answers ------------------------------------------------------------------------------------------------------------------------

def parse_fields(value):
    """`a,b,c` -> ["a","b","c"]; a field that is not a plain lower-case name raises ApiError(400, api.unknown_field)."""
    if value in (None, ""):
        return None
    out = []
    for field in str(value).split(","):
        field = field.strip()
        if not FIELD_RE.match(field):
            raise ApiError(400, "api.unknown_field", field=field[:40])
        if field not in out:
            out.append(field)
    return out


def project(item, name, fields=None, profile="full"):
    """`item` cut to `fields` (checked against the promised list of the route) or to the compact list; a field outside the contract is refused rather than ignored."""
    spec = CONTRACT[name]
    promised = spec.get("item") or spec["required"]
    if fields:
        for field in fields:
            if field not in promised:
                raise ApiError(400, "api.unknown_field", field=field)
        keep = fields
    elif profile == "compact":
        keep = spec["compact"]
    else:
        return item
    return {k: item[k] for k in keep if k in item}


def maybe_compress(body, accept_encoding, min_bytes=1024):
    """(body, headers): gzip when the client accepts it (and does not refuse it with q=0) and the body has at least `min_bytes` (0 = never); `mtime=0` keeps the output reproducible."""
    accepted = False
    for part in str(accept_encoding or "").split(","):
        name, _, params = part.strip().partition(";")
        if name.strip().lower() in ("gzip", "x-gzip"):
            quality = re.search(r"q\s*=\s*([0-9.]+)", params)
            accepted = not quality or quality.group(1) not in ("0", "0.0", "0.00", "0.000")
    headers = {"Vary": "Accept-Encoding"}
    if not accepted or not min_bytes or len(body) < min_bytes:
        return body, headers
    headers["Content-Encoding"] = "gzip"
    return gzip.compress(body, compresslevel=6, mtime=0), headers


# ---- the two routes -------------------------------------------------------------------------------------------------------------------------

def capabilities(mode, role):
    """What the session may do on the monitor as a whole (the prefix /api/v1/ itself is read only, whatever the role): `write` = the actions of the page (acknowledge, mute, change a setting that is not reserved),
    `admin` = users, credentials and the settings of the access. The individual mode has no roles: the person at the computer, or holding the access token, can do what the page does."""
    team = mode == "team"
    return {"read": True, "write": (role in ("maintainer", "admin")) if team else True, "admin": (role == "admin") if team else True, "v1_write": False}


def me_payload(*, version, edition, mode, authenticated, user, role, accounts, cfg):
    """Who is asking. `role` and `accounts` are None when there is no team session (the individual mode has no roles: the person at the computer or holding the access token can do what the page does)."""
    return {"schema": 1, "api_version": API_VERSION, "contract": CONTRACT_VERSION, "version": version, "edition": edition, "mode": mode, "authenticated": bool(authenticated), "user": user or None, "role": role,
            "accounts": list(accounts) if accounts is not None else None, "capabilities": capabilities(mode, role), "limits": {"default_limit": cfg["default_limit"], "max_limit": cfg["max_limit"]}}


def repo_item(view):
    """One line of /api/v1/repos from a health view (health/repo_view.py): only what the contract promises."""
    ci, alerts, activity = view.get("ci") or {}, view.get("alerts") or {}, view.get("activity") or {}
    return {"repo": view.get("repo"), "ecosystem": view.get("ecosystem") or "", "state": view.get("state") or "unknown", "risk": view.get("risk") or 0, "runs_24h": ci.get("runs_24h") or 0,
            "failures_24h": ci.get("failures_24h") or 0, "red_workflows": len(ci.get("red_workflows") or []), "stuck_runs": ci.get("stuck_runs") or 0, "alerts": alerts.get("total") or 0,
            "last_run_at": activity.get("last_run_at")}


def repos_payload(views, ask, *, secret, now, cfg, who=""):
    """The page of repositories asked for. `ask` = the query as a dict of text (state, ecosystem, q, limit, cursor, fields, profile). Raises ApiError for a bad parameter."""
    profile = ask.get("profile") or "full"
    if profile not in PROFILES:
        raise ApiError(400, "api.bad_profile")
    fields = parse_fields(ask.get("fields"))
    state, ecosystem, text = (ask.get("state") or "")[:20], (ask.get("ecosystem") or "")[:40], (ask.get("q") or "")[:80].lower()
    items = [repo_item(v) for v in views if v.get("repo") and (not state or v.get("state") == state) and (not ecosystem or v.get("ecosystem") == ecosystem) and (not text or text in v["repo"].lower())]
    page = paginate(items, key=lambda i: i["repo"], endpoint="repos", filters={"state": state, "ecosystem": ecosystem, "q": text, "who": who if who.strip("|") else ""}, secret=secret, now=now, cursor=ask.get("cursor"),
                    limit=ask.get("limit"), default_limit=cfg["default_limit"], max_limit=cfg["max_limit"], ttl=cfg["cursor_ttl_seconds"])
    return {"schema": 1, "api_version": API_VERSION, "total": len(items), "limit": page["limit"], "next_cursor": page["next_cursor"],
            "items": [project(i, "repos", fields, profile) for i in page["items"]]}


def openapi(version="1.0.0"):
    """A light OpenAPI 3.0 description of the own routes: paths, the shared error envelope and the paging parameters."""
    error = {"description": "error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
    paths = {
        "/api/v1/me": {"get": {"operationId": "me", "security": [{"cookie": []}, {"access": []}],
                               "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": {"type": "object", "required": CONTRACT["me"]["required"]}}}}, "default": error}}},
        "/api/v1/repos": {"get": {"operationId": "repos", "security": [{"cookie": []}, {"access": []}],
                                  "parameters": [{"name": n, "in": "query", "schema": {"type": "string"}} for n in CONTRACT["repos"]["filters"] + ["fields", "cursor"]]
                                  + [{"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1}}, {"name": "profile", "in": "query", "schema": {"enum": list(PROFILES)}}],
                                  "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": {"type": "object", "required": ["items", "next_cursor", "limit", "total"],
                                                                                                                         "properties": {"items": {"type": "array", "items": {"type": "object", "required": CONTRACT["repos"]["item"]}}}}}}},
                                                "default": error}}},
    }
    return {"openapi": "3.0.3", "info": {"title": "GitHub Actions Monitor read API", "version": version}, "paths": paths,
            "components": {"securitySchemes": {"cookie": {"type": "apiKey", "in": "cookie", "name": "session"}, "access": {"type": "apiKey", "in": "header", "name": "X-Monitor-Access"}},
                           "schemas": {"Error": {"type": "object", "required": ["error", "code", "message"], "properties": {"error": {"type": "string"}, "code": {"type": "string"}, "message": {"type": "string"}}}}}}
