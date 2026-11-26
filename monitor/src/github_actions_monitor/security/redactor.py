# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The ONE cleaner of text that leaves the monitor towards an AI, a feed, an endpoint, a hook or a provider: tokens, keys, credentials in addresses, e-mail addresses, IP addresses,
the home folder of a person and long opaque strings. By pattern: it lowers the risk, it is not a guarantee. Every output that an AI can read goes through `redact()`, `redact_data()` or
`redact_json()`; nothing else in the product defines its own list of secret patterns."""
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote

def _ipv6(match):
    """`[ip]` for a candidate that is really an IPv6 address (an hour such as 10:00:00 is not), else the text as it was."""
    import ipaddress
    text = match.group(0)
    for end in (len(text), len(text.rstrip(":")) if not text.endswith("::") else len(text)):
        try:
            ipaddress.IPv6Address(text[:end])
        except ValueError:
            continue
        return "[ip]" + text[end:]
    return text


_STATE_WORDS = frozenset("blind back none null true false yes no on off ok set unset present absent missing empty enabled disabled expired valid invalid required optional configured unknown masked hidden redacted error failure success".split())
_NOT_A_SECRET_KEY = re.compile(r"(?i)^(?:(?:max|min|input|output|prompt|completion|total|num)[_.-]?tokens?|tokens(?:[_.-](?:in|out|used|left|count|limit))?|token[_.-](?:count|limit))$|^secrets?[_.-](?:scanning|count|alerts?)$|^(?:cache|sort|primary|foreign|partition|group|order|hot)[_.-]?key$")


def _pair(match):
    """The replacement of a `name=value` rule: the value goes to [secret] unless the NAME is one that counts things or states (max_tokens=500, secret_scanning: disabled, cache-key: linux) or the value is a word of a
    closed list of states ("present", "blind", "disabled") on a name that is not a password. Everything else is a secret."""
    key, sep = match.group(1), match.group(2)
    value = match.group(0)[len(key) + len(sep):].strip("\"'")
    name = key.split("/")[-1]
    if _NOT_A_SECRET_KEY.match(name):
        return match.group(0)
    if value.lower() in _STATE_WORDS and not re.search(r"(?i)pass|pwd", name):
        return match.group(0)
    return key + sep + "[secret]"


def _ipv4(match):
    """`[ip]` for four numbers up to 255, but not for a version of four components ("version 2.0.8.1", "v1.2.3.4")."""
    text = match.group(0)
    if any(int(part) > 255 for part in text.split(".")):
        return text
    before = match.string[max(0, match.start() - 8):match.start()].lower()
    if before.endswith("v") or before.endswith("version "):
        return text
    return "[ip]"


_SECRETS = [
    (re.compile(r"(?s)[-\u2010-\u2015\u2212]{2,80}BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?[-\u2010-\u2015\u2212]{2,80}.*?(?:[-\u2010-\u2015\u2212]{2,80}END [A-Z ]*PRIVATE KEY(?: BLOCK)?[-\u2010-\u2015\u2212]{2,80}|$)"), "[pem]"),
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]{0,30}://)[^/\s:@]{1,300}:(?!\d{1,5}/)[^\s?#]{1,300}@"), r"\1[credentials]@"),      # user:password@host in an address
    (re.compile(r"(?i)\bhooks\.slack\.com/services/[A-Za-z0-9/_-]+"), "hooks.slack.com/services/[webhook]"),
    (re.compile(r"(?i)\bdiscord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9._-]+"), "discord.com/api/webhooks/[webhook]"),
    (re.compile(r"\bbot\d{6,}:[A-Za-z0-9_-]{20,}"), "bot[token]"),
    (re.compile(r"(?<![\w:])\d{8,10}:[A-Za-z0-9_-]{33,40}(?![\w-])"), "[token]"),      # the token of a Telegram bot without the word "bot"
    (re.compile(r"(?i)\bntfy\.sh/[A-Za-z0-9._-]+"), "ntfy.sh/[secret]"),      # the topic of ntfy is the secret
    (re.compile(r"(?i)([?&;](?:sid|jsessionid|phpsessid|session[_-]?id|sessionid)=)[^&\s#]+"), r"\1[secret]"),
    (re.compile(r"(?i)(\bmachine\s+\S+\s+login\s+\S+\s+password)\s+(?!\[)\S+"), r"\1 [secret]"),      # .netrc
    (re.compile(r"(?m)^([\w.*-]+:(?:\d+|\*):[\w*-]+:[\w*-]+:)\S+$"), r"\1[secret]"),      # .pgpass
    (re.compile(r"(?i)(\b(?:docker|podman|buildah|skopeo|helm)\b[^\r\n]*?\blogin\b[^\r\n]*?\s-p[ =]?)(?!\[)\S+"), r"\1[secret]"),
    (re.compile(r"(?i)(\bsshpass\b[^\r\n]*?\s-p\s+)(?!\[)\S+"), r"\1[secret]"),
    (re.compile(r"(?i)(\bcurl\b[^\r\n]*?\s(?:-u|--user)[ =]?)(?!\[)\S+"), r"\1[secret]"),
    (re.compile(r"\b((?:store|key)Password)(\s+)(?![\[\"'])\S+"), r"\1\2[secret]"),
    (re.compile(r"""(?i)(\b[A-Za-z0-9_.]{0,100}password)(\s+)(['"])(?!\[)[^'"\r\n]+\3"""), r"\1\2\3[secret]\3"),      # storePassword 'x' (Gradle)
    (re.compile(r"""(?i)((?:^|[^A-Za-z0-9])(?:_auth|x-auth[a-z-]*|["']auth["'])["']?\s*[:=]\s*)(?:"[^"\r\n]{0,300}"|'[^'\r\n]{0,300}'|[^\s"',;]+)"""), r"\1[secret]"),      # .npmrc _auth=, X-Auth:, {"auth": "..."}
    (re.compile(r"(?i)\b((?:otp|totp|(?:2fa|mfa)[_-]?code)\s*[:=]\s*)\d{4,10}"), r"\1[secret]"),
    (re.compile(r"(?i)((?:secret|token|password|passwd|pwd|api[_-]?key)[ :=]+)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), r"\1[secret]"),      # the identifier of a client secret
    (re.compile(r"(?i)[A-Za-z0-9._%+-]{1,100}\s?[\[(]at[\])]\s?[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){0,10}\.[A-Za-z]{2,}"), "[email]"),      # victima [at] corp.com
    (re.compile(r"""(?i)(x-monitor-access|monitor_access)(["']?\s*[:=]\s*)(?:"(?:[^"\\\n]|\\.){0,300}"|'(?:[^'\\\n]|\\.){0,300}'|["']?[^\s"',;]+)"""), r"\1\2[secret]"),
    (re.compile(r"(?<![A-Za-z0-9])(?:glpat-[A-Za-z0-9_-]{10,}|npm_[A-Za-z0-9]{16,}|pypi-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{20,}|dckr_pat_[A-Za-z0-9_-]{16,}|whsec_[A-Za-z0-9]{16,}|GOCSPX-[A-Za-z0-9_-]{16,})"), "[token]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]*|github_pat_[A-Za-z0-9_]*)[ \t]*\r?\n[ \t]*[A-Za-z0-9_]{6,}"), "[token]"),      # a token cut by a line break: the second half goes with the first
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,})"), "[token]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|(?:AKIA|ASIA)[0-9A-Z]{12,}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,})"), "[key]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "[jwt]"),
    (re.compile(r"""(?i)\b((?:proxy-)?authorization)(["']?\s*[:=]\s*)(?:(?:bearer|basic|token|digest|negotiate)\s+)?[^\r\n"']+"""), r"\1\2[secret]"),      # the whole credential, "Basic" or "Bearer" word included
    (re.compile(r"(?i)\b(set-cookie|cookie)(\s*:\s*)[^\r\n]+"), r"\1\2[secret]"),
    (re.compile(r"(?i)(--?(?:password|passwd|pwd|passphrase|token|secret|api[_-]?key|access[_-]?key)[ =])\S+"), r"\1[secret]"),      # mysql --password hunter2, curl --token abc
    (re.compile(r"(?i)(\b(?:mysql|mysqldump|mysqladmin|psql|sshpass|redis-cli)\b[^\r\n]*?\s-p)(?!\[)[^\s-]\S*"), r"\1[secret]"),      # mysql -uroot -phunter2
    (re.compile(r"""(?i)\b([A-Za-z0-9_.-]{0,100}[_.-](?:key|dsn|creds|credentials|pass)|dsn|creds|credentials)(["']?\s*[:=]\s*)(?:"(?:[^"\\\n]|\\.){0,300}"|'(?:[^'\\\n]|\\.){0,300}'|["']?[^\s"',;]+)"""), _pair),      # ENCRYPTION_KEY=, SENTRY_DSN=, AWS_CREDS=
    (re.compile(r"(?i)\b(password|passwd|passphrase)(\s*:\s+)(?![\"'\[])[^\r\n]+"), r"\1\2[secret]"),      # a phrase after "password:" (the value may hold spaces)
    (re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{8,}"), "[key]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 [secret]"),
    (re.compile(r"""(?i)([A-Za-z0-9_.-]{0,100}(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|authorization|contrase[\u00f1n]a|secreto|clave)[A-Za-z0-9_.-]{0,100})(["']?\s*[:=]\s*)(?:"(?:[^"\\\n]|\\.){0,300}"|'(?:[^'\\\n]|\\.){0,300}'|["']?[^\s"',;]+)"""), _pair),      # DB_PASSWORD=, AWS_SECRET_ACCESS_KEY=, MYSQL_PWD=
    (re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,}"), "[email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b(?!\.\d)"), _ipv4),
    (re.compile(r"(?i)\b[a-z0-9-]{1,63}(?:\.[a-z0-9-]{1,63}){0,10}\.(?:lan|internal|corp|intranet|private)\b(?::\d{1,5})?|\b[a-z0-9-]{1,63}(?:\.[a-z0-9-]{1,63}){2,10}\.local\b(?::\d{1,5})?"), "[host]"),      # a name that only exists inside a network
    (re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}\b"), "[ip]"),
    (re.compile(r"(?<![\w:.])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w])"), _ipv6),
    (re.compile(r"""(?i)[A-Z]:(?:\\+|/)Users(?:\\+|/)[^\\/\s'"]+"""), "~"),      # also with doubled bars: it is how repr(), JSON and the text of an OSError write it
    (re.compile(r"(?i)\\\\[^\\\s]+\\(?:Users|home)\\[^\\\s]+"), "~"),      # \\server\Users\name
    (re.compile(r"(?<![A-Za-z0-9._-])/root(?=/|\s|$)"), "~"),
    (re.compile(r"(?:/var/lib/jenkins/secrets|/run/secrets|/etc/secrets)(?:/\S*)?"), "[path]"),
    (re.compile(r"/(?:home|Users)/[^/\s]+|(?<![\w./-])/users/[^/\s]+"), "~"),
    (re.compile(r"(?<![\w/~])~[A-Za-z_][\w.-]{1,31}(?=/)"), "~"),      # ~victima/project
    (re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{30,}(?![0-9A-Fa-f])"), "[hex]"),
    (re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{12,}={1,2}(?![A-Za-z0-9=])"), "[blob]"),      # base64 with its padding (user:password is 16 characters)
    (re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}"), "[blob]"),
]


# The address of a page of GitHub (a repository, a run, a commit, an issue, a file): public, it carries no secret and the AI needs it whole. Only a closed list of SHAPES passes untouched and the
# address is cut at the first character outside [A-Za-z0-9._/-]: what follows (a query, a fragment, an encoded character, a colon, a comma...) is cleaned like any other text.
_GITHUB_URL = re.compile(r"https://(?P<api>api\.)?github\.com(?![A-Za-z0-9@:-]|\.[A-Za-z0-9])(?P<path>(?:/[A-Za-z0-9._-]*)*)")
_SEG = r"[A-Za-z0-9._-]*[A-Za-z0-9_-]"
_GITHUB_SHAPE = re.compile(
    rf"(?:/repos)?/{_SEG}(?:/{_SEG}(?:/actions/runs/\d+(?:/job/\d+|/attempts/\d+)?|/commit/[0-9A-Fa-f]{{40}}|/(?:issues|pull)/\d+|/(?:blob|tree)(?=/)(?:/{_SEG})*)?)?(?![A-Za-z0-9_-])")
_OPAQUE_SEGMENT = re.compile(r"[0-9A-Fa-f]{32,}|[A-Za-z0-9_-]{40,}")      # what the rules of the text turn into [hex] and [blob]


def _github_safe(match):
    """The part of a github.com address that may pass untouched: the host and the longest prefix of the path that has one of the shapes of the list, with no segment that looks like a secret."""
    path = match.group("path") or ""
    shape = _GITHUB_SHAPE.match(path)
    if not shape or not path.startswith("/"):
        return "https://" + ("api." if match.group("api") else "") + "github.com"
    kept = shape.group(0)
    parts = kept.split("/")
    for index, part in enumerate(parts):
        if index and _OPAQUE_SEGMENT.search(part) and not (index >= 2 and parts[index - 1] == "commit"):      # the 40 hexadecimal digits of a commit are public; any other opaque segment is not
            kept = "/".join(parts[:index])
            break
    return "https://" + ("api." if match.group("api") else "") + "github.com" + kept


def _clean(text, limit=None):
    """The text without tokens, keys, e-mail addresses, IP addresses, the home folder of a person and long opaque strings. The addresses of github.com that have the shape of a repository, a run,
    a commit, an issue, a pull request or a file pass untouched (a run link is longer than the 40 characters of an opaque string and used to be cut to [blob]); nothing after the first character
    outside [A-Za-z0-9._/-] does."""
    out = str(text or "").replace("\ue000", "").replace("\ue001", "")      # the marks below belong to this function only
    home = str(Path.home())
    for variant in {home, home.replace("\\", "/"), home.replace("\\", "\\\\")}:
        if len(variant) > 3:
            out = out.replace(variant, "~")
    kept = []

    def keep(match):
        url = _github_safe(match)
        if match.string[match.end():match.end() + 1] == "@" or any(pattern.search(url) for pattern, replacement in _SECRETS if replacement not in ("[hex]", "[blob]")):      # an address that goes on as an e-mail, or that itself holds a token, a key, a home folder...: it is cleaned like any text
            return match.group(0)
        kept.append(url)
        return f"\ue000{len(kept) - 1}\ue001" + match.group(0)[len(url):]
    out = _GITHUB_URL.sub(keep, out)
    for pattern, replacement in _SECRETS:
        out = pattern.sub(replacement, out)
    for index, url in enumerate(kept):
        out = out.replace(f"\ue000{index}\ue001", url)
    return out[:limit] if limit else out


_MARK = re.compile(r"\[(?:secret|token|key|jwt|email|ip|credentials|pem|hex|blob|webhook|path|host)\]")
_INVISIBLE = re.compile("[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180e\u200b-\u200d\u2060-\u2064\u3164\ufeff]")


def redact(text, limit=None):
    """`_clean` of the text as it is and, when the text hides itself behind an encoding (full-width letters, zero-width characters, %XX), of its plain form too: the one that finds more wins."""
    out = _clean(str(text or ""))
    plain = _INVISIBLE.sub("", unicodedata.normalize("NFKC", out))
    plain = unquote(plain) if "%" in plain else plain
    if plain != out:      # a secret that is only seen once the text is plain: the plain form is cleaned too and is the one that is kept (the zero-width characters and the %XX are not information)
        out = _clean(plain)
    return out[:limit] if limit else out


_SECRET_KEY = re.compile(r"(?i)(?:^|[_.\s-])(?:password|passwd|pwd|passphrase|secret|token|cookie|credential|credentials|authorization)$|api[_-]?key$|apikey$")


def _secret_pair(key, value):
    """True for a pair whose KEY says the value is a secret ({'password': 'x'} has nothing the patterns of the text could see): the whole name, or its last word, is one of the list (`token_state`,
    `tokens_in` and a repository called `secret-santa` are not); the name of an environment variable (`*_env`) is not a secret, and neither is a word of a closed list of states ({'credential': 'blind'})."""
    return (isinstance(key, str) and isinstance(value, str) and len(value) > 3 and bool(_SECRET_KEY.search(key.strip())) and not key.lower().endswith(("_env", "_name", "_label"))
            and not _MARK.fullmatch(value) and not (value.strip().lower() in _STATE_WORDS and not re.search(r"(?i)pass|pwd", key)))


def redact_data(value, limit=None):
    """The same cleaning for a structure (dict, list, text): every text inside is cleaned ON ITS OWN, keys included, and the structure is serialised afterwards. Never clean a JSON that is already
    written: a value that ends at the quote of its string would take the quote with it and break the document."""
    if isinstance(value, str):
        return redact(value, limit)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            name = redact(k) if isinstance(k, str) else k
            if name in out:      # two keys that look the same once cleaned ([hex], [email]): numbered, none is lost
                number = 2
                while f"{name}#{number}" in out:
                    number += 1
                name = f"{name}#{number}"
            out[name] = "[secret]" if _secret_pair(k, v) else redact_data(v)
        return out
    if isinstance(value, (list, tuple)):
        return [redact_data(v) for v in value]
    return value


def _lists(node, found):
    """Every list with more than one element inside `node`, as (list, written size)."""
    if isinstance(node, dict):
        for item in node.values():
            _lists(item, found)
    elif isinstance(node, list):
        if len(node) > 1:
            found.append((node, len(json.dumps(node, ensure_ascii=False))))
        for item in node:
            _lists(item, found)
    return found


def fit_json(value, limit=None, first=None, **dumps):
    """JSON of `value` with every text cleaned (see redact_data) that is ALWAYS a valid document: when it is longer than `limit` the STRUCTURE is trimmed, never the written text. Rows are taken from the
    end of the longest list until it fits; the rows for which `first(row)` is true (the health of the monitor) are moved to the head of their list first, so they are the last to go. A trimmed answer says
    so: `truncated` is true and `omitted_rows` counts the rows left out (a document that is not an object is wrapped in {"truncated", "omitted_rows", "data"})."""
    options = {"ensure_ascii": False} | dumps
    data = redact_data(value)
    text = json.dumps(data, **options)
    if not limit or len(text) <= limit:
        return text
    if not isinstance(data, dict):
        data = {"data": data}
    data = {"truncated": True, "omitted_rows": 0, **data}
    omitted = 0
    while True:
        text = json.dumps(data, **options)
        if len(text) <= limit:
            return text
        found = _lists(data, [])
        if not found:
            return json.dumps({"truncated": True, "omitted_rows": omitted, "note": "the answer is larger than its limit"}, **options)
        rows, size = max(found, key=lambda pair: pair[1])
        if first is not None:
            rows.sort(key=lambda row: 0 if first(row) else 1)
        drop = max(1, min(len(rows) - 1, int(len(rows) * (1 - limit / len(text)) * 1.1) + 1))
        del rows[len(rows) - drop:]
        omitted += drop
        data["omitted_rows"] = omitted


def redact_json(value, limit=None, **dumps):
    """JSON of `value` with every text cleaned; with a `limit`, see fit_json."""
    return fit_json(value, limit, **dumps)
