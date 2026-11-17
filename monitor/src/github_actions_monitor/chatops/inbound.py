# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Read only commands from Slack and from Discord (OFF by default).

It only exists when `chatops.enabled` and the switch of the platform are on AND the proof of the platform is in the environment: the signing secret of the Slack app (the variable named by
`chatops.slack.signing_secret_env`) or the public key of the Discord app (`chatops.discord.public_key_env`). The settings keep the NAME of the variable, never the value; the value is never
written, shown or logged. Every request is checked BEFORE anything of it is read:

  * Slack: `X-Slack-Signature: v0=<hmac>` is the HMAC-SHA256 of `v0:<timestamp>:<body>`, `X-Slack-Request-Timestamp` is at most `chatops.max_age_seconds` old (five minutes at most), the comparison
    takes the same time whatever the signature is.
  * Discord: `X-Signature-Ed25519` is an Ed25519 signature of `<timestamp><body>` made with the key of the app (the check is the RFC 8032 one of security/sigverify.py, standard library), and
    `X-Signature-Timestamp` is at most `chatops.max_age_seconds` old.
  * A signature that was already accepted is never accepted again (a bounded memory), the body has a ceiling, and the requests are counted per address, per user, per channel and per minute.

What a valid request can do is small and closed: answer the challenge of the platform (Slack `url_verification`, Discord `PING`), or run one command of the closed list of commands.py for a person
whose team, channel and user are in the lists of allowed ones (the lists are required: with none of them no command runs). The answer is seen only by the person who asked, carries no link and
no mention, and every text that is not ours is cleaned and escaped (render.py). Nothing here writes on GitHub, runs an action, changes a setting or reads a secret. Standard library only."""
import collections
import hashlib
import hmac
import json
import re
import threading
import time
from urllib.parse import parse_qs

from github_actions_monitor import i18n
from github_actions_monitor.chatops import commands, render
from github_actions_monitor.security import envguard, localguard, sigverify

PROVIDERS = ("slack", "discord")
MAX_BODY = 16384                   # a slash command or an interaction is a few hundred bytes
MAX_AGE = 300                      # Slack's own window: the setting can only make it shorter
MAX_REMEMBERED = 2000              # accepted signatures kept for the replay check (the oldest fall out first)
ANSWER_SECONDS = 2.5               # both platforms give up after 3 seconds
MAX_BUSY = 4                       # commands being answered at the same time
MIN_SLACK_SECRET = 16
ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}\Z")
ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}\Z")
SNOWFLAKE_RE = re.compile(r"^[0-9]{1,25}\Z")
HEX_RE = re.compile(r"^[0-9a-f]+\Z")
CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,200}\Z")
COMMAND_NAME_RE = re.compile(r"^/?[A-Za-z0-9_-]{1,32}\Z")
DEFAULT_ENV = {"slack": "MONITOR_SLACK_SIGNING_SECRET", "discord": "MONITOR_DISCORD_PUBLIC_KEY"}
NAMES = ("all", "public", "none")

DEFAULTS = {"enabled": False, "slack": {"enabled": False, "signing_secret_env": DEFAULT_ENV["slack"]}, "discord": {"enabled": False, "public_key_env": DEFAULT_ENV["discord"]},
            "allowed_teams": [], "allowed_channels": [], "allowed_users": [], "allowed_words": list(commands.COMMANDS), "max_rows": 8, "show_repo_names": "all", "links": True, "max_age_seconds": MAX_AGE,
            "rate_per_user_per_minute": 6, "rate_per_channel_per_minute": 20, "rate_per_minute": 60}

_lock = threading.Lock()
_seen = collections.OrderedDict()     # accepted signature -> time (signature already verified)
_busy = threading.BoundedSemaphore(MAX_BUSY)
STATS = {}                            # (provider, outcome) -> count, for the Live view; nothing of a request is kept


def reset():
    """Forgets the remembered signatures and the counts (tests)."""
    with _lock:
        _seen.clear()
        STATS.clear()


def count(provider, outcome):
    with _lock:
        STATS[(provider, outcome)] = STATS.get((provider, outcome), 0) + 1


def stats():
    with _lock:
        return {f"{p}.{o}": n for (p, o), n in sorted(STATS.items())}


def _number(block, key, low, high, default):
    value = block.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def _ids(value, pattern):
    return [v for v in value if isinstance(v, str) and pattern.match(v)][:200] if isinstance(value, list) else []


def _env_name(block, key, default):
    name = block.get(key) if isinstance(block, dict) else None
    return name if isinstance(name, str) and ENV_NAME_RE.match(name) else default


def settings(config):
    """The settings with their defaults; anything of the wrong type or out of range is replaced by the default (the conservative one)."""
    cfg = (config or {}).get("chatops")
    cfg = cfg if isinstance(cfg, dict) else {}
    slack = cfg.get("slack") if isinstance(cfg.get("slack"), dict) else {}
    discord = cfg.get("discord") if isinstance(cfg.get("discord"), dict) else {}
    chosen = cfg.get("allowed_words")
    allowed = [c for c in commands.COMMANDS if isinstance(chosen, list) and c in chosen] if isinstance(chosen, list) else list(commands.COMMANDS)
    names = cfg.get("show_repo_names")
    return {"enabled": cfg.get("enabled") is True,
            "slack": {"enabled": slack.get("enabled") is True, "env": _env_name(slack, "signing_secret_env", DEFAULT_ENV["slack"])},
            "discord": {"enabled": discord.get("enabled") is True, "env": _env_name(discord, "public_key_env", DEFAULT_ENV["discord"])},
            "allowed_teams": _ids(cfg.get("allowed_teams"), ID_RE), "allowed_channels": _ids(cfg.get("allowed_channels"), ID_RE), "allowed_users": _ids(cfg.get("allowed_users"), ID_RE),
            "allowed_words": allowed, "links": cfg.get("links") is not False, "max_rows": _number(cfg, "max_rows", 1, 25, DEFAULTS["max_rows"]), "show_repo_names": names if names in NAMES else DEFAULTS["show_repo_names"],
            "max_age_seconds": _number(cfg, "max_age_seconds", 30, MAX_AGE, MAX_AGE), "rate_per_user_per_minute": _number(cfg, "rate_per_user_per_minute", 1, 600, DEFAULTS["rate_per_user_per_minute"]),
            "rate_per_channel_per_minute": _number(cfg, "rate_per_channel_per_minute", 1, 600, DEFAULTS["rate_per_channel_per_minute"]),
            "rate_per_minute": _number(cfg, "rate_per_minute", 1, 6000, DEFAULTS["rate_per_minute"])}


def env_names(config):
    """The names of the variables that hold the proofs (for envguard.hold at start: no program the monitor starts inherits them)."""
    cfg = settings(config)
    return [cfg["slack"]["env"], cfg["discord"]["env"]]


def proof(config, provider):
    """The secret (Slack, as text) or the public key (Discord, as 32 bytes) of the platform from the environment, or None when it is missing or does not look right. Never printed."""
    cfg = settings(config)[provider]
    value = envguard.get(cfg["env"]).strip()
    if provider == "slack":
        return value if len(value) >= MIN_SLACK_SECRET else None
    value = value.lower()
    return bytes.fromhex(value) if len(value) == 64 and HEX_RE.match(value) else None


def state(config, provider):
    """"defined" | "undefined": the only thing the page may know about a proof (never its value, nor its length)."""
    return "defined" if proof(config, provider) is not None else "undefined"


def lists_set(cfg):
    return bool(cfg["allowed_teams"] or cfg["allowed_channels"] or cfg["allowed_users"])


def active(config, provider):
    """True only when the master switch, the switch of the platform and the proof are all there (fail closed)."""
    cfg = settings(config)
    return cfg["enabled"] and cfg[provider]["enabled"] and proof(config, provider) is not None


def status_text(config):
    """One line for the console and the Live view: which platforms are on, never a value."""
    cfg = settings(config)
    if not cfg["enabled"]:
        return i18n.t("chatops.off")
    on = [p for p in PROVIDERS if active(config, p)]
    if not on:
        return i18n.t("chatops.no_proof")
    return i18n.t("chatops.on", providers=", ".join(on)) + ("" if lists_set(cfg) else " " + i18n.t("chatops.no_lists"))


# --- the proofs --------------------------------------------------------------------------------------------------------------------------------------------------------------
def slack_sign(secret, timestamp, body):
    return "v0=" + hmac.new(secret.encode("utf-8"), b"v0:" + str(timestamp).encode("ascii") + b":" + body, hashlib.sha256).hexdigest()


def fresh(timestamp, window, now):
    """The timestamp as a whole number of seconds when it is within `window` of now (the past or the future), else None."""
    if not isinstance(timestamp, str) or not re.match(r"^[0-9]{9,12}\Z", timestamp):
        return None
    value = int(timestamp)
    return value if abs(now - value) <= window else None


def verify_slack(secret, headers, body, window, now):
    """(ok, signature). The signature is returned (for the replay memory) only when it is valid."""
    timestamp = fresh(headers.get("X-Slack-Request-Timestamp"), window, now)
    given = headers.get("X-Slack-Signature")
    if timestamp is None or not isinstance(given, str) or not given.startswith("v0="):
        return False, ""
    try:
        good = hmac.compare_digest(slack_sign(secret, timestamp, body).encode("ascii"), given.strip().encode("ascii"))      # bytes: another character is a plain "no"
    except UnicodeError:
        return False, ""
    return good, given.strip()


def verify_discord(public, headers, body, window, now):
    """(ok, signature) for the Ed25519 signature of `timestamp + body` (RFC 8032); never raises."""
    stamp = headers.get("X-Signature-Timestamp")
    timestamp = fresh(stamp, window, now)
    given = headers.get("X-Signature-Ed25519")
    if timestamp is None or not isinstance(given, str) or len(given) != 128 or not HEX_RE.match(given.lower()):
        return False, ""
    try:
        good = sigverify.ed25519_verify(public, stamp.encode("ascii") + body, bytes.fromhex(given))
    except (ValueError, TypeError, UnicodeError):
        return False, ""
    return good, given.lower()


def replayed(signature, window, now):
    """True when this signature was already accepted within `window` seconds; otherwise remembers it (bounded memory) and returns False."""
    with _lock:
        while _seen and (len(_seen) > MAX_REMEMBERED or next(iter(_seen.values())) < now - window):
            _seen.popitem(last=False)
        if signature in _seen:
            return True
        _seen[signature] = now
        return False


# --- what a request asks ------------------------------------------------------------------------------------------------------------------------------------------------------
def parse_slack(body):
    """("challenge", text) | ("command", {...}) | ("ignored", None) | ("bad", None): the closed list of what Slack may send here."""
    if body[:1] == b"{":
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            return "bad", None
        if isinstance(payload, dict) and payload.get("type") == "url_verification":
            return ("challenge", payload["challenge"]) if isinstance(payload.get("challenge"), str) and CHALLENGE_RE.match(payload["challenge"]) else ("bad", None)
        return ("ignored", None) if isinstance(payload, dict) else ("bad", None)
    try:
        form = {k: v[0] for k, v in parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=False, max_num_fields=40).items() if v}
    except (ValueError, UnicodeError):
        return "bad", None
    ok = all(isinstance(form.get(k), str) and ID_RE.match(form[k]) for k in ("team_id", "channel_id", "user_id")) and COMMAND_NAME_RE.match(form.get("command", "") or "")
    if not ok:
        return "bad", None
    return "command", {"team": form["team_id"], "channel": form["channel_id"], "user": form["user_id"], "text": render.clean(form.get("text", ""), 200)}


def parse_discord(body):
    """Same for Discord: the PING (type 1) and the application command (type 2) of the closed list."""
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        return "bad", None
    if not isinstance(payload, dict):
        return "bad", None
    if payload.get("type") == 1:
        return "challenge", None
    if payload.get("type") != 2:
        return "ignored", None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    member = payload.get("member") if isinstance(payload.get("member"), dict) else {}
    user = (member.get("user") if isinstance(member.get("user"), dict) else None) or (payload.get("user") if isinstance(payload.get("user"), dict) else {})
    guild = payload.get("guild_id")
    ids = (payload.get("channel_id"), user.get("id"))
    if not all(isinstance(v, str) and SNOWFLAKE_RE.match(v) for v in ids) or not (guild is None or (isinstance(guild, str) and SNOWFLAKE_RE.match(guild))) \
            or not isinstance(data.get("name"), str) or not COMMAND_NAME_RE.match(data["name"]):
        return "bad", None
    text = ""
    for option in data.get("options") or []:
        if isinstance(option, dict) and isinstance(option.get("value"), str):
            text = render.clean(option["value"], 200)
            break
        if isinstance(option, dict) and isinstance(option.get("name"), str):
            text = render.clean(option["name"], 200)      # a sub command used as the word
            break
    return "command", {"team": guild or "", "channel": payload["channel_id"], "user": user["id"], "text": text}


def permitted(cfg, who):
    """True when the person is allowed. Each list that has something in it must contain the matching id; with no list at all nobody is allowed (the lists are required)."""
    if not lists_set(cfg):
        return False
    for key, value in (("allowed_teams", who["team"]), ("allowed_channels", who["channel"]), ("allowed_users", who["user"])):
        if cfg[key] and value not in cfg[key]:
            return False
    return True


def limited(cfg, provider, who):
    """True when this person, this channel or the whole chat already made too many commands in the last minute (counts this one otherwise)."""
    return (localguard.over_rate("chatops.user", f"{provider}:{who['user']}", cfg["rate_per_user_per_minute"])
            or localguard.over_rate("chatops.channel", f"{provider}:{who['channel']}", cfg["rate_per_channel_per_minute"])
            or localguard.over_rate("chatops.all", provider, cfg["rate_per_minute"]))


def answer_text(name, snapshot, cfg, provider, timeout=ANSWER_SECONDS):
    """The text of the answer to `name`: computed in a thread that has `timeout` seconds (the platform gives up at three), and a short 'busy' text when it takes longer or too many are running."""
    if not _busy.acquire(blocking=False):
        return i18n.t("chatops.busy")
    box = {}
    escape = render.ESCAPE[provider]
    language = i18n.language()

    def work():
        try:
            with i18n.use_language(language):
                snap = snapshot()
                box["lines"] = commands.run(name, snap, cfg["max_rows"], escape, cfg["allowed_words"])
        except Exception:      # noqa: BLE001 - whatever failed, the chat gets a plain sentence and nothing of the error
            box["error"] = True
        finally:
            _busy.release()
    thread = threading.Thread(target=work, name="chatops-answer", daemon=True)
    thread.start()
    thread.join(timeout)
    if "lines" in box:
        return render.fit(box["lines"])
    return i18n.t("chatops.busy")


def handle(provider, config, body, headers, snapshot, now=None):
    """(http code, answer, record). `headers` is any mapping with .get; `snapshot()` returns what the commands read. Never raises. `record` is None, or {"command", "user", "channel", "result"} for the log of
    actions (ids of the chat only: no text of the request and no secret)."""
    now = time.time() if now is None else now
    if provider not in PROVIDERS or not active(config, provider):
        return 404, {"ok": False}, None
    cfg = settings(config)
    if len(body) > MAX_BODY:
        count(provider, "too_big")
        return 413, {"ok": False}, None
    secret = proof(config, provider)
    good, signature = (verify_slack if provider == "slack" else verify_discord)(secret, headers, body, cfg["max_age_seconds"], now)
    if not good:
        count(provider, "bad_signature")
        return 401, {"ok": False}, None
    if replayed(signature, cfg["max_age_seconds"] * 2, now):      # a valid request captured and sent again: answered, never acted on (Slack's own retries land here too)
        count(provider, "replay")
        return 202, {"ok": True, "ignored": True, "duplicate": True}, None
    kind, found = (parse_slack if provider == "slack" else parse_discord)(body)
    if kind == "bad":
        count(provider, "bad_request")
        return 400, {"ok": False}, None
    if kind == "ignored":
        count(provider, "ignored")
        return 202, {"ok": True, "ignored": True}, None
    if kind == "challenge":
        count(provider, "challenge")
        return 200, ({"challenge": found} if provider == "slack" else {"type": 1}), None
    reply = render.REPLY[provider]
    who = found
    record = {"user": who["user"], "channel": who["channel"], "command": "", "result": "denied"}
    if not permitted(cfg, who):
        count(provider, "denied")
        return 200, reply(i18n.t("chatops.denied")), record
    if limited(cfg, provider, who):
        count(provider, "limited")
        record["result"] = "error"
        return 200, reply(i18n.t("chatops.limit")), record
    name = commands.parse(who["text"], cfg["allowed_words"])
    if name is None:
        count(provider, "unknown")
        record["result"] = "error"
        return 200, reply(i18n.t("chatops.unknown")), record
    record["command"] = name
    record["result"] = "ok"
    count(provider, "command")
    return 200, reply(answer_text(name, snapshot, cfg, provider)), record
