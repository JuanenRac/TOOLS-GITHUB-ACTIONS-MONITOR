# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The read API for clients, version 1 (web, command line, phone web app, native app): the rules that all of them share, as pure functions.

  error envelope   {"error": slug, "code": "api.something", "message": text in the language asked}; the codes are stable and never translated
  paging           opaque, signed cursors that carry a fingerprint of the query and a time to live; `limit` has a default and a ceiling
  compact payloads `?fields=a,b` or `?profile=compact|mobile`; the compact field lists of each resource are part of the contract
  versioning       the header `X-API-Version` (and the prefix `/api/v1/`); a breaking change only comes with a major version of the product
  compression      gzip when the client accepts it and the body is large enough
  bearer clients   `Authorization: Bearer <token>` with the same roles and the same account scope as the dashboard
  the contract     CONTRACT lists the fields each endpoint promises; `check_payload` is what the contract tests use to fail when a promised field disappears

Nothing here reads the network, the disk or the clock: the secret of the cursors, the time and the role come from the caller."""
import base64
import gzip
import hashlib
import hmac
import json
import re

from github_actions_monitor.phase4 import msgs

API_VERSION = "1"
SUPPORTED_VERSIONS = ("1",)
VERSION_HEADER = "X-API-Version"
PREFIX = "/api/v1"
ROLES = ("viewer", "maintainer", "admin")
PROFILES = ("full", "compact", "mobile")
FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}\Z")
CURSOR_MAX_LENGTH = 512

ERROR_SLUGS = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "rate_limited", 500: "server_error"}

# What every endpoint promises. `required` fields are present in every item of the full payload; `compact` is the short list used by the phone and the native app (always a subset of
# the promised fields). A field may be added in a minor version, never removed or renamed.
CONTRACT = {
    "health": {"path": "/api/health", "kind": "object", "required": ["ok", "edition", "version"], "compact": ["ok", "version"], "min_role": "viewer"},
    "accounts": {"path": "/api/accounts", "kind": "list", "required": ["id", "label"], "compact": ["id", "label"], "min_role": "viewer"},
    "account_status": {"path": "/api/accounts/{id}/status", "kind": "object", "required": ["id", "level", "updated_at"], "compact": ["id", "level"], "min_role": "viewer"},
    "status": {"path": "/api/status", "kind": "object", "required": ["level", "updated_at"], "compact": ["level"], "min_role": "viewer"},
    "alerts": {"path": "/api/alerts", "kind": "list", "required": ["id", "code", "level", "sentinel", "account_id", "repo", "title", "created_at"],
               "compact": ["id", "code", "level", "repo", "created_at"], "min_role": "viewer", "filters": ["account", "sentinel", "level", "since"]},
    "events": {"path": "/api/events", "kind": "list", "required": ["id", "code", "at"], "compact": ["id", "code", "at"], "min_role": "viewer", "filters": ["account", "since"]},
    "live_events": {"path": "/api/live-events", "kind": "list", "required": ["id", "code", "at"], "compact": ["id", "code", "at"], "min_role": "viewer"},
    "live_status": {"path": "/api/live-status", "kind": "object", "required": ["enabled"], "compact": ["enabled"], "min_role": "viewer"},
    "score": {"path": "/api/score", "kind": "object", "required": ["account_id", "score"], "compact": ["account_id", "score"], "min_role": "viewer"},
    "repo_health": {"path": "/api/repos/{owner}/{repo}/health", "kind": "object", "required": ["repo", "level"], "compact": ["repo", "level"], "min_role": "viewer"},
    "team_health": {"path": "/api/team/health", "kind": "object", "required": ["level"], "compact": ["level"], "min_role": "viewer"},
}
for _name, _spec in CONTRACT.items():
    assert set(_spec["compact"]) <= set(_spec["required"]), _name


def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---- the error envelope ----------------------------------------------------------------------------------------------------------------------------

def error(status, code, lang="en", **values):
    """(status, body) of an error: {"error", "code", "message"}. `code` is the key of the message ("api.bad_cursor"); an unknown status becomes a 500."""
    slug = ERROR_SLUGS.get(status)
    if slug is None:
        status, slug = 500, "server_error"
    return status, {"error": slug, "code": code, "message": msgs.t(lang, code, **values)}


class ApiError(Exception):
    """Raised inside the helpers below; the server turns it into `error(...)`."""

    def __init__(self, status, code, **values):
        super().__init__(code)
        self.status, self.code, self.values = status, code, values

    def envelope(self, lang="en"):
        return error(self.status, self.code, lang, **self.values)


# ---- versioning ------------------------------------------------------------------------------------------------------------------------------------

def requested_version(headers, path=""):
    """The API version a request asks for: the `/api/v1/` prefix wins, then the header, else the current one. An unsupported one raises ApiError(400)."""
    version = API_VERSION
    match = re.match(r"^/api/v(\d{1,3})(/|\Z)", path or "")
    if match:
        version = match.group(1)
    else:
        for key, value in (headers or {}).items():
            if str(key).lower() == VERSION_HEADER.lower() and str(value).strip():
                version = str(value).strip()
    if version not in SUPPORTED_VERSIONS:
        raise ApiError(400, "api.version_unsupported", version=version[:10])
    return version


def strip_prefix(path):
    """`/api/v1/alerts` -> `/api/alerts`; any other path comes back as it is, so both spellings reach the same handler."""
    return "/api" + path[len(PREFIX):] if path == PREFIX or path.startswith(PREFIX + "/") else path


def response_headers(extra=None):
    headers = {VERSION_HEADER: API_VERSION, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    headers.update(extra or {})
    return headers


# ---- paging ----------------------------------------------------------------------------------------------------------------------------------------

def fingerprint(endpoint, filters):
    """A short, stable text for a query (endpoint and filters, without paging): a cursor made for one query is refused for another."""
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
    mac = _b64(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()[:16])
    return body + "." + mac


def read_cursor(secret, cursor, query_fp, now, ttl):
    """The key a cursor points after. Anything wrong (shape, signature, another query, too old) raises ApiError(400, api.bad_cursor)."""
    bad = ApiError(400, "api.bad_cursor")
    if not isinstance(cursor, str) or not cursor or len(cursor) > CURSOR_MAX_LENGTH or cursor.count(".") != 1:
        raise bad
    body, mac = cursor.split(".")
    want = _b64(hmac.new(secret, body.encode("ascii", "replace"), hashlib.sha256).digest()[:16])
    if not hmac.compare_digest(mac, want):
        raise bad
    try:
        data = json.loads(_unb64(body))
    except (ValueError, UnicodeDecodeError):
        raise bad from None
    if not isinstance(data, dict) or data.get("f") != query_fp or not isinstance(data.get("t"), int) or now - data["t"] > ttl or data["t"] > now + 60:
        raise bad
    return data.get("k")


def paginate(items, *, key, endpoint, filters, secret, now, cursor=None, limit=None, default_limit=50, max_limit=200, ttl=900, descending=True):
    """One page of `items` ordered by `key(item)` (unique and comparable; ties are not allowed): {"items", "next_cursor", "limit"}. Keyset paging: an item added between two requests
    never repeats or shifts a page."""
    size = parse_limit(limit, default_limit, max_limit)
    fp = fingerprint(endpoint, filters)
    ordered = sorted(items, key=key, reverse=descending)
    if cursor:
        after = read_cursor(secret, cursor, fp, now, ttl)
        ordered = [item for item in ordered if (key(item) < after if descending else key(item) > after)] if after is not None else ordered
    page = ordered[:size]
    more = len(ordered) > size
    return {"items": page, "next_cursor": make_cursor(secret, fp, key(page[-1]), now) if more and page else None, "limit": size}


# ---- compact payloads ------------------------------------------------------------------------------------------------------------------------------

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


def negotiate_profile(query, headers, mobile_default=True):
    """full | compact | mobile. `?profile=` wins; then the header `X-Client-Profile`; a phone client (header value `mobile`) gets compact by default when that is allowed."""
    asked = str((query or {}).get("profile") or "").strip().lower()
    if not asked:
        for key, value in (headers or {}).items():
            if str(key).lower() == "x-client-profile":
                asked = str(value).strip().lower()
    if asked not in PROFILES:
        return "full"
    if asked == "mobile" and not mobile_default:
        return "full"
    return asked


def project(item, endpoint, fields=None, profile="full"):
    """The item cut to `fields` (checked against the promised list) or to the compact list of the endpoint. A field outside the contract is refused rather than ignored."""
    spec = CONTRACT[endpoint]
    if fields:
        for field in fields:
            if field not in spec["required"]:
                raise ApiError(400, "api.unknown_field", field=field)
        keep = fields
    elif profile in ("compact", "mobile"):
        keep = spec["compact"]
    else:
        return item
    return {k: item[k] for k in keep if k in item}


# ---- compression -----------------------------------------------------------------------------------------------------------------------------------

def maybe_compress(body, accept_encoding, min_bytes=1024):
    """(body, headers): gzip when the client accepts it (and does not refuse it with q=0) and the body has at least `min_bytes`; `mtime=0` keeps the output reproducible."""
    accepted = False
    for part in str(accept_encoding or "").split(","):
        name, _, params = part.strip().partition(";")
        if name.strip().lower() in ("gzip", "x-gzip"):
            quality = re.search(r"q\s*=\s*([0-9.]+)", params)
            accepted = not quality or quality.group(1) not in ("0", "0.0", "0.00", "0.000")
    headers = {"Vary": "Accept-Encoding"}
    if not accepted or len(body) < min_bytes:
        return body, headers
    headers["Content-Encoding"] = "gzip"
    return gzip.compress(body, compresslevel=6, mtime=0), headers


# ---- bearer clients --------------------------------------------------------------------------------------------------------------------------------

def parse_bearer(header):
    """The token of `Authorization: Bearer <token>`, or None. Only the scheme and a token of printable characters without spaces are accepted."""
    match = re.match(r"^Bearer ([\x21-\x7e]{8,512})\Z", str(header or ""), re.I)
    return match.group(1) if match else None


def role_allows(role, needed):
    return role in ROLES and needed in ROLES and ROLES.index(role) >= ROLES.index(needed)


def authorize(principal, endpoint, account_id=None):
    """Raises ApiError(401/403) unless `principal` ({"role", "accounts"}; `accounts` None = all) may read `endpoint` and, when given, `account_id`. The same rule for a cookie and a Bearer token."""
    if not principal:
        raise ApiError(401, "api.unauthorized")
    if not role_allows(principal.get("role"), CONTRACT[endpoint]["min_role"]):
        raise ApiError(403, "api.forbidden")
    accounts = principal.get("accounts")
    if account_id and accounts is not None and account_id not in accounts:
        raise ApiError(404, "api.not_found")      # not 403: an account out of scope must not be told apart from one that does not exist


def scope_accounts(items, principal, field="account_id"):
    """The items whose account the principal may see (all of them when `accounts` is None)."""
    accounts = (principal or {}).get("accounts")
    return list(items) if accounts is None else [i for i in items if i.get(field) in accounts]


# ---- the contract, held by tests ------------------------------------------------------------------------------------------------------------------

def check_payload(endpoint, payload):
    """A list of problems (empty = fine) between a payload and what CONTRACT promises for `endpoint`."""
    spec = CONTRACT[endpoint]
    problems = []
    rows = payload if spec["kind"] == "list" else [payload]
    if spec["kind"] == "list" and not isinstance(payload, list):
        return ["{}: a list was promised".format(endpoint)]
    for number, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append("{}[{}]: an object was promised".format(endpoint, number))
            continue
        for field in spec["required"]:
            if field not in row:
                problems.append("{}[{}]: missing {}".format(endpoint, number, field))
    return problems


def openapi(version="1.0.0", title="GitHub Actions Monitor read API"):
    """A light OpenAPI 3.0 description built from CONTRACT: paths, the shared error envelope and the paging parameters. Only the promised fields are listed."""
    paths = {}
    for name, spec in CONTRACT.items():
        schema = {"type": "object", "required": spec["required"], "properties": {f: {} for f in spec["required"]}}
        body = {"type": "array", "items": schema} if spec["kind"] == "list" else schema
        params = [{"name": "fields", "in": "query", "schema": {"type": "string"}}, {"name": "profile", "in": "query", "schema": {"enum": list(PROFILES)}}]
        for pname in spec.get("filters", []):
            params.append({"name": pname, "in": "query", "schema": {"type": "string"}})
        if spec["kind"] == "list":
            params += [{"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1}}, {"name": "cursor", "in": "query", "schema": {"type": "string"}}]
        paths[PREFIX + spec["path"][4:]] = {"get": {"operationId": name, "parameters": params, "security": [{"cookie": []}, {"bearer": []}],
                                                    "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": body}}},
                                                                  "default": {"description": "error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}}}}
    return {"openapi": "3.0.3", "info": {"title": title, "version": version}, "paths": paths,
            "components": {"securitySchemes": {"cookie": {"type": "apiKey", "in": "cookie", "name": "session"}, "bearer": {"type": "http", "scheme": "bearer"}},
                           "schemas": {"Error": {"type": "object", "required": ["error", "code", "message"], "properties": {"error": {"type": "string"}, "code": {"type": "string"}, "message": {"type": "string"}}}}}}
