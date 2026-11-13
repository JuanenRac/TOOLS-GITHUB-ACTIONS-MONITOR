# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The team mode on the server: one gate in front of every route, and the endpoints of the login.

    GET  /login                   the page to sign in (and, the first time, to create the first administrator from this computer)
    GET  /api/auth/me             who you are: {"enabled", "authenticated", "mode", "user", "role", "accounts", "csrf", "bootstrap"}
    POST /api/auth/login          {"username", "password", "client": "web" | "api"}; "web" sets the cookie, "api" returns a Bearer token for scripts and apps
    POST /api/auth/logout         ends this session
    POST /api/auth/bootstrap      {"username", "password"}: the first administrator; only from this computer, only while there is no user, then closed for good
    POST /api/auth/password       {"current", "new"}: change your own password (your other sessions end)
    GET  /api/auth/users          (admin) the users; POST /api/auth/users (create), /api/auth/users/update, /api/auth/users/delete, /api/auth/users/revoke
    GET  /api/auth/audit          (admin) the last lines of the audit of the accesses

Read-only routes (they never change anything): every GET. Routes that change the state of the monitor (never GitHub, except the explicit actions): every POST, listed by role in
`auth.required_role`. Errors are JSON with a stable code: {"error": "<text in English>", "code": "<code>"}.

The gate (`gate`) answers False after it has answered the request; True means "go on". It does nothing at all (True) in the lite edition, in an account child process, when `auth.enabled`
is off, and while no user exists: the individual mode is the same monitor as before. The access token of the network mode is checked BEFORE this gate (localguard); the one-use token of a
POST (session_guard) is still checked by the route itself.
"""
import hmac
import json
import os
import time

from github_actions_monitor import i18n
from github_actions_monitor.security import auth, localguard

MAX_BODY = 4096
CHILD_ENV = "MONITOR_AUTH_CHILD"      # set by the supervisor for the monitors of each account: they answer to the supervisor on this computer, which is the one that asks for the login
MESSAGES = {"auth_required": "sign in first", "forbidden_role": "your role cannot do this", "account_scope": "this account is not yours", "csrf": "missing or wrong CSRF token",
            "invalid_credentials": "wrong user name or password", "locked": "too many attempts, try later", "rate": "too many requests", "bootstrap_closed": "the first administrator already exists",
            "bootstrap_local_only": "the first administrator can only be created from this computer", "auth_disabled": "the team mode is off", "request": "bad request",
            "user_unknown": "unknown user", "user_exists": "that user already exists", "last_admin": "there must always be an active administrator", "role_invalid": "unknown role",
            "username_invalid": "the user name must be 2-40 characters: a-z, 0-9, dot, dash, underscore", "accounts_invalid": "invalid list of accounts", "active_invalid": "active must be true or false",
            "password_missing": "password missing", "password_short": "password too short", "password_too_long": "password too long", "password_weak": "password too weak",
            "bearer_off": "tokens for scripts are turned off", "not_found": "not found"}
_cache = {"at": 0.0, "exist": False}


def _send(handler, payload, code=200, headers=None, text=None, kind="application/json; charset=utf-8"):
    body = (text if text is not None else json.dumps(payload)).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", kind)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    for name, value in (headers or {}).items():
        handler.send_header(name, value)
    try:
        handler.end_headers()
        handler.wfile.write(body)
    except (ConnectionError, OSError):
        pass


def fail(handler, code, status, headers=None):
    _send(handler, {"ok": False, "error": MESSAGES.get(code, code), "code": code}, status, headers)
    return False


def _read_json(handler):
    try:
        size = int(handler.headers.get("Content-Length") or 0)
        if "application/json" not in (handler.headers.get("Content-Type") or "").lower() or not 0 < size <= MAX_BODY:
            return None
        body = json.loads(handler.rfile.read(size))
        return body if isinstance(body, dict) else None
    except (ValueError, TypeError, OSError):
        return None


def _cookie_value(headers):
    for part in (headers.get("Cookie") or "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == auth.SESSION_COOKIE:
            return value
    return ""


def presented_token(headers, cfg):
    """(token, kind): the cookie of the browser, or a Bearer token / X-Monitor-Session header of a script (only while auth.allow_bearer is on)."""
    if cfg["allow_bearer"]:
        bearer = headers.get("Authorization") or ""
        if bearer.lower().startswith("bearer ") and bearer[7:].strip().startswith(auth.TOKEN_PREFIX):
            return bearer[7:].strip(), "bearer"
        if (headers.get("X-Monitor-Session") or "").strip():
            return headers.get("X-Monitor-Session").strip(), "bearer"
    return _cookie_value(headers), "cookie"


def session_cookie(token, cfg, clear=False):
    base = f"{auth.SESSION_COOKIE}={'' if clear else token}; Path=/; HttpOnly; SameSite=Strict"
    base += "; Max-Age=0" if clear else f"; Max-Age={cfg['session_hours'] * 3600}"
    return base + ("; Secure" if localguard.STATE["secure"] else "")


def _users_exist(storage):
    now = time.time()
    if now - _cache["at"] > 1.0:
        _cache["exist"], _cache["at"] = auth.users_exist(storage), now
    return _cache["exist"]


def forget_cache():
    _cache["at"] = 0.0


def _address(handler):
    return localguard.client_key(handler.client_address, handler.headers)


USER_HEADER = "X-Monitor-User"       # the supervisor tells the monitor of an account who is acting (the child trusts it only when it is an account child)


def acting_user(handler):
    """The name of the person behind a request ('' in the individual mode): the session of the gate, or the header the supervisor adds for an account child."""
    context = getattr(handler, "auth_user", None)
    if context:
        return context["user"]
    if os.environ.get(CHILD_ENV):
        return auth.clean_username(handler.headers.get(USER_HEADER))
    return ""


def visible_accounts(handler, ids):
    """The account ids this request may see: all of them without a session (individual mode) or for an admin, else only the ones assigned to the user."""
    context = getattr(handler, "auth_user", None)
    if not context:
        return list(ids)
    return [i for i in ids if auth.can_see_account(context["accounts"], i)]


def requested_account(handler):
    """The account a request is for: ?account=<id> or the header X-Account-Id, else the default one."""
    from urllib.parse import parse_qs
    asked = (parse_qs(handler.path.partition("?")[2]).get("account") or [""])[0] or handler.headers.get("X-Account-Id") or ""
    return asked.strip().lower() or "default"


def active(config, lite=False):
    """True when requests must carry a session: team mode on, not lite, not an account child, and at least one user exists."""
    if lite or os.environ.get(CHILD_ENV):
        return False
    cfg = auth.settings(config)
    return cfg["enabled"] and _users_exist(auth.get_storage(config))


def gate(handler, config, lite=False):
    """True = the request goes on. False = it has been answered (401, 403, 429, a redirect, or an endpoint of /api/auth)."""
    if lite or os.environ.get(CHILD_ENV):
        return True
    cfg = auth.settings(config)
    path = handler.path.split("?")[0]
    method = handler.command
    if path == "/login" or path.startswith("/api/auth/"):
        return _endpoint(handler, config, cfg, method, path)
    if not cfg["enabled"]:
        return True
    storage = auth.get_storage(config)
    if not _users_exist(storage):
        return True      # nobody has been created yet: the individual mode, exactly as before
    needed = auth.required_role(method, path)
    if needed is None:
        return True
    is_page = method == "GET" and path in ("/", "/index.html")
    token, kind = presented_token(handler.headers, cfg)
    context = auth.find_session(storage, token) if token else None
    if context is None:
        auth.audit(cfg, "denied", address=_address(handler), path=path, result="denied", code="auth_required")
        if is_page and "text/html" in (handler.headers.get("Accept") or "text/html"):
            _send(handler, None, 302, {"Location": "/login"}, text="")
            return False
        return fail(handler, "auth_required", 401)
    if not auth.allows(context["role"], needed):
        auth.audit(cfg, "denied", context["user"], context["role"], _address(handler), path, "denied", "forbidden_role")
        return fail(handler, "forbidden_role", 403)
    listing = path == "/api/accounts" or path.startswith("/api/accounts/")      # the supervisor filters these by user itself
    if not listing and not path.startswith("/api/auth/") and not auth.can_see_account(context["accounts"], requested_account(handler)):
        auth.audit(cfg, "denied", context["user"], context["role"], _address(handler), path, "denied", "account_scope")
        return fail(handler, "account_scope", 403)
    if method not in ("GET", "HEAD") and kind == "cookie" and not hmac.compare_digest((handler.headers.get("X-CSRF-Token") or "").encode(), context["csrf"].encode()):
        auth.audit(cfg, "denied", context["user"], context["role"], _address(handler), path, "denied", "csrf")
        return fail(handler, "csrf", 403)
    handler.auth_user = context
    return True


def _me(handler, config, cfg):
    storage = auth.get_storage(config)
    exist = _users_exist(storage) if cfg["enabled"] else False
    base = {"enabled": cfg["enabled"], "mode": "team" if (cfg["enabled"] and exist) else "individual", "authenticated": False, "bootstrap": bool(cfg["enabled"] and not exist)}
    token, _ = presented_token(handler.headers, cfg)
    context = auth.find_session(storage, token) if (token and cfg["enabled"]) else None
    if context:
        base.update({"authenticated": True, "user": context["user"], "role": context["role"], "accounts": context["accounts"], "csrf": context["csrf"]})
    _send(handler, base)


def _endpoint(handler, config, cfg, method, path):
    if path == "/login":
        if method != "GET":
            return fail(handler, "not_found", 404)
        if not localguard.local_request_ok(handler.headers, handler.server.server_address[1]):
            return fail(handler, "forbidden", 403)
        _send(handler, None, 200, {"Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"}, text=login_page(), kind="text/html; charset=utf-8")
        return False
    if path == "/api/auth/me" and method == "GET":
        _me(handler, config, cfg)
        return False
    if not cfg["enabled"]:
        return fail(handler, "auth_disabled", 404)
    if not localguard.local_request_ok(handler.headers, handler.server.server_address[1]):
        return fail(handler, "forbidden", 403)
    storage = auth.get_storage(config)
    address = _address(handler)
    if method == "GET":
        if path in ("/api/auth/users", "/api/auth/audit"):
            context = _require(handler, storage, cfg, "admin")
            if context is None:
                return False
            _send(handler, {"users": auth.list_users(storage)} if path.endswith("users") else {"audit": auth.read_audit()})
            return False
        return fail(handler, "not_found", 404)
    if method != "POST":
        return fail(handler, "not_found", 404)
    if localguard.over_rate("auth", address, 60):
        return fail(handler, "rate", 429)
    body = _read_json(handler)
    if body is None:
        return fail(handler, "request", 400)
    if path == "/api/auth/bootstrap":
        return _bootstrap(handler, storage, cfg, body, address)
    if path == "/api/auth/login":
        return _login(handler, storage, cfg, body, address)
    if path == "/api/auth/logout":
        token, _ = presented_token(handler.headers, cfg)
        context = auth.find_session(storage, token) if token else None
        auth.end_session(storage, token)
        auth.audit(cfg, "logout", (context or {}).get("user", ""), (context or {}).get("role", ""), address, path)
        _send(handler, {"ok": True}, headers={"Set-Cookie": session_cookie("", cfg, clear=True)})
        return False
    context = _require(handler, storage, cfg, "viewer", csrf=True)
    if context is None:
        return False
    if path == "/api/auth/password":
        token, _ = presented_token(handler.headers, cfg)
        code = auth.change_own_password(storage, context["user"], body.get("current"), body.get("new"), cfg, keep_token=token)
        auth.audit(cfg, "password", context["user"], context["role"], address, path, "ok" if not code else "denied", code)
        if code:
            return fail(handler, code, 400 if code != "invalid_credentials" else 403)
        _send(handler, {"ok": True})
        return False
    if path.startswith("/api/auth/users"):
        if context["role"] != "admin":
            auth.audit(cfg, "denied", context["user"], context["role"], address, path, "denied", "forbidden_role")
            return fail(handler, "forbidden_role", 403)
        return _users(handler, storage, cfg, context, body, path, address)
    return fail(handler, "not_found", 404)


def _require(handler, storage, cfg, role, csrf=False):
    """The context of a valid session with at least `role` (answers 401/403 and returns None otherwise)."""
    token, kind = presented_token(handler.headers, cfg)
    context = auth.find_session(storage, token) if token else None
    if context is None:
        fail(handler, "auth_required", 401)
        return None
    if not auth.allows(context["role"], role):
        auth.audit(cfg, "denied", context["user"], context["role"], _address(handler), handler.path, "denied", "forbidden_role")
        fail(handler, "forbidden_role", 403)
        return None
    if csrf and kind == "cookie" and not hmac.compare_digest((handler.headers.get("X-CSRF-Token") or "").encode(), context["csrf"].encode()):
        fail(handler, "csrf", 403)
        return None
    return context


def _bootstrap(handler, storage, cfg, body, address):
    if _users_exist(storage):
        return fail(handler, "bootstrap_closed", 409)
    if not localguard.is_this_computer(handler.client_address, handler.headers):
        auth.audit(cfg, "bootstrap", address=address, result="denied", code="bootstrap_local_only")
        return fail(handler, "bootstrap_local_only", 403)
    user, code = auth.bootstrap_admin(storage, body.get("username"), body.get("password"), cfg["min_length"])
    forget_cache()
    auth.audit(cfg, "bootstrap", (user or {}).get("username", ""), "admin" if user else "", address, handler.path, "ok" if user else "denied", code)
    if code:
        return fail(handler, code, 409 if code == "bootstrap_closed" else 400)
    _send(handler, {"ok": True, "user": user})
    return False


def _login(handler, storage, cfg, body, address):
    kind = "bearer" if body.get("client") == "api" else "cookie"
    if kind == "bearer" and not cfg["allow_bearer"]:
        return fail(handler, "bearer_off", 403)
    if localguard.is_locked(address):
        return fail(handler, "locked", 429)
    if not _users_exist(storage):
        return fail(handler, "invalid_credentials", 401)
    session, code = auth.login(storage, body.get("username"), body.get("password"), cfg, kind)
    name = auth.clean_username(body.get("username"))
    if session is None:
        if code == "invalid_credentials":
            localguard.note_failure(address, max(cfg["max_failed_logins"] * 4, 20))
        auth.audit(cfg, "login", name, "", address, handler.path, "locked" if code == "locked" else "denied", code)
        headers = {"Retry-After": str(auth.locked_for(storage, name))} if code == "locked" else None
        return fail(handler, code, 429 if code == "locked" else 401, headers)
    auth.audit(cfg, "login", session["user"], session["role"], address, handler.path, "ok", kind)
    answer = {"ok": True, "user": session["user"], "role": session["role"], "csrf": session["csrf"], "expires": session["expires"]}
    headers = {}
    if kind == "bearer":
        answer["token"] = session["token"]
    else:
        headers["Set-Cookie"] = session_cookie(session["token"], cfg)
    _send(handler, answer, headers=headers)
    return False


def _users(handler, storage, cfg, context, body, path, address):
    sub = path[len("/api/auth/users"):].strip("/")
    minimum = cfg["min_length"]
    result, code, action = None, "", sub or "create"
    if sub == "":
        result, code = auth.create_user(storage, body.get("username"), body.get("password"), body.get("role", "viewer"), body.get("accounts"), minimum)
    elif sub == "update":
        if body.get("username") == context["user"] and (body.get("active") is False or body.get("role") not in (None, context["role"])):
            code = "last_admin"      # nobody takes their own admin away: another admin does it
        else:
            result, code = auth.update_user(storage, body.get("username"), body.get("role"), body.get("active"), body.get("accounts"), body.get("password"), minimum)
    elif sub == "delete":
        code = "last_admin" if body.get("username") == context["user"] else auth.delete_user(storage, body.get("username"))
    elif sub == "revoke":
        name = auth.clean_username(body.get("username"))
        if not name or storage.get_record("users", name) is None:
            code = "user_unknown"
        else:
            result = {"revoked": auth.revoke_sessions(storage, name)}
    else:
        return fail(handler, "not_found", 404)
    forget_cache()
    auth.audit(cfg, "user_" + action, context["user"], context["role"], address, path, "denied" if code else "ok", code)
    if code:
        return fail(handler, code, 404 if code == "user_unknown" else 409 if code in ("user_exists", "last_admin") else 400)
    _send(handler, {"ok": True, "user": result} if sub in ("", "update") else {"ok": True, **(result or {})})
    return False


def login_page():
    """The sign-in page: plain HTML and a few lines of script, texts in the language of the page (the eight languages of the product)."""
    t = i18n.t
    texts = {k: t("auth." + k) for k in ("title", "user", "password", "sign_in", "bootstrap_note", "create_admin", "wrong", "locked", "failed", "rate")}
    from html import escape
    e = {k: escape(v, quote=True) for k, v in texts.items()}
    texts_json = json.dumps(texts).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{escape(i18n.language())}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e['title']}</title>
<style>
:root{{--bg:#0f1720;--fg:#e6edf3;--card:#17212b;--line:#2c3b4a;--acc:#3fb950;--bad:#f85149}}
@media (prefers-color-scheme:light){{:root{{--bg:#f4f6f8;--fg:#1b2733;--card:#fff;--line:#c9d3dc;--acc:#1a7f37;--bad:#cf222e}}}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--fg);font:16px system-ui,sans-serif}}
form{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:24px;width:min(340px,86vw);display:grid;gap:12px}}
h1{{font-size:18px;margin:0}}label{{display:grid;gap:4px;font-size:14px}}
input{{padding:9px;border:1px solid var(--line);border-radius:6px;background:transparent;color:inherit;font:inherit}}
button{{padding:10px;border:0;border-radius:6px;background:var(--acc);color:#fff;font:inherit;cursor:pointer}}
#msg{{min-height:1.2em;font-size:14px;color:var(--bad)}}#note{{font-size:13px;opacity:.8}}
</style></head><body>
<form id="f" autocomplete="on"><h1>{e['title']}</h1><div id="note" hidden>{e['bootstrap_note']}</div>
<label>{e['user']}<input id="u" name="username" autocomplete="username" required maxlength="40"></label>
<label>{e['password']}<input id="p" name="password" type="password" autocomplete="current-password" required maxlength="200"></label>
<div id="msg" role="alert"></div><button id="b" type="submit">{e['sign_in']}</button></form>
<script>
const T={texts_json};
const f=document.getElementById('f'),m=document.getElementById('msg');let boot=false;
fetch('/api/auth/me',{{credentials:'same-origin'}}).then(r=>r.json()).then(s=>{{if(s.authenticated){{location.href='/';return}}
 boot=!!s.bootstrap;if(boot){{document.getElementById('note').hidden=false;document.getElementById('b').textContent=T.create_admin;document.getElementById('p').autocomplete='new-password'}}}}).catch(()=>{{}});
f.addEventListener('submit',async ev=>{{ev.preventDefault();m.textContent='';
 const body=JSON.stringify({{username:f.u.value,password:f.p.value,client:'web'}});
 const send=(url)=>fetch(url,{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body}});
 try{{let r=await send(boot?'/api/auth/bootstrap':'/api/auth/login');
  if(boot&&r.ok)r=await send('/api/auth/login');
  if(r.ok){{location.href='/';return}}
  const j=await r.json().catch(()=>({{}}));m.textContent=r.status===429?(j.code==='rate'?T.rate:T.locked):(j.code==='invalid_credentials'?T.wrong:T.failed+(j.code?' ('+j.code+')':''))}}
 catch(x){{m.textContent=T.failed}}}});
</script></body></html>"""
