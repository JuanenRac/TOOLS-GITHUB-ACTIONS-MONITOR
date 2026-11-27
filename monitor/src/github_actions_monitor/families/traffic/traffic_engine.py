# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Downloads of release files, visits and clones: which chosen repositories are read (each at most once a day, a few per cycle), what is kept (data/state/traffic.json) and what comes out (the report and
the CSV). Only GET requests to GitHub; nothing is ever sent anywhere else. GitHub keeps visits and clones for 14 days only, so a day that was never read is lost: a gap stays a gap, never a zero."""
import copy
import csv
import io
import json
import re
import threading
import time

from github_actions_monitor import families, i18n
from github_actions_monitor.storage import state_io
from github_actions_monitor.util import paths

LOCK = threading.RLock()
RUNNING = {"on": False}
MAX_REPOS = 50
RELEASE_PAGES = 3          # 100 releases a page
MAX_ASSETS = 500
SHOWN_DAYS = 90
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{1,39}\Z")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
DAY_FIELDS = ("downloads", "new", "views", "views_unique", "clones", "clones_unique")


class Refused(Exception):
    """A read GitHub did not give: `reason` is no_permission, missing, rate_limited or failed."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def settings(config):
    return families.block(config if isinstance(config, dict) else {}, "traffic")


def active(config):
    config = config if isinstance(config, dict) else {}
    return settings(config)["enabled"] is True and config.get("airgapped") is not True


def selected(config, owner):
    """[owner/name] of the repositories the user chose: a name alone belongs to the account that is watched."""
    out = []
    chosen = settings(config).get("repos")
    for entry in chosen if isinstance(chosen, list) else []:      # a hand-written text is not a list of names
        first, slash, rest = str(entry).partition("/")
        who, name = (first, rest) if slash else (str(owner or ""), first)
        if OWNER_RE.match(who) and NAME_RE.match(name) and name not in (".", "..") and f"{who}/{name}" not in out:
            out.append(f"{who}/{name}")
    return out[:MAX_REPOS]


def state_file(account=""):
    suffix = "_" + re.sub(r"[^A-Za-z0-9_-]", "", account) if account else ""
    return paths.place("state") / f"traffic{suffix}.json"


def load(account=""):
    try:
        data = state_io.load_json(state_file(account))
        if isinstance(data, dict) and isinstance(data.get("repos"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"repos": {}}


def save(data, account=""):
    target = state_file(account)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        state_io.save_text(target, json.dumps(data, ensure_ascii=False))
        return True
    except OSError:
        return False


def reader():
    """The GET of the monitor (conditional reads, retries). Every refusal becomes Refused."""
    from github_actions_monitor.app import actions_monitor

    def get(endpoint):
        try:
            return actions_monitor.gh_read(endpoint, retries=1)
        except Exception as error:      # noqa: BLE001 - whatever gh says, it is "not read"
            raise Refused(reason_of(str(error))) from None
    return get


def reason_of(message):
    text = message.lower()
    if "rate limit" in text:
        return "rate_limited"
    if re.search(r"\b404\b", text):
        return "missing"
    if re.search(r"\b40[13]\b", text) or "push access" in text:
        return "no_permission"
    return "failed"


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def read_assets(get, full):
    """{"tag/file": downloads} of the files attached to the releases. The "Source code" archives of GitHub are not files of a release and have no count."""
    out = {}
    for page in range(1, RELEASE_PAGES + 1):
        rows = get(f"repos/{full}/releases?per_page=100&page={page}")
        if not isinstance(rows, list):
            raise Refused("failed")
        for release in rows:
            if not isinstance(release, dict) or release.get("draft"):
                continue
            tag = str(release.get("tag_name") or "")[:100].replace("/", "_")
            for asset in release.get("assets") or []:
                if isinstance(asset, dict) and asset.get("name") and len(out) < MAX_ASSETS:
                    out[f"{tag}/{str(asset['name'])[:200]}"] = _count(asset.get("download_count"))
        if len(rows) < 100:
            break
    return out


def read_traffic(get, full, kind):
    """{date: (count, uniques)} of the days GitHub still keeps; kind is views or clones."""
    answer = get(f"repos/{full}/traffic/{kind}")
    if not isinstance(answer, dict):
        raise Refused("failed")
    out = {}
    for row in answer.get(kind) or []:
        if isinstance(row, dict) and DATE_RE.match(str(row.get("timestamp") or "")):
            out[str(row["timestamp"])[:10]] = (_count(row.get("count")), _count(row.get("uniques")))
    return out


def read_one(get, full, entry, cfg, today):
    """Reads one repository into its entry. A rate limit goes up (nothing of the day is marked); any other refusal is written in the entry and is not an error."""
    days = entry.setdefault("days", {})
    try:
        assets = read_assets(get, full)
    except Refused as refused:
        if refused.reason == "rate_limited":
            raise
        entry["releases_status"] = refused.reason
    else:
        previous = entry.get("latest")
        row = days.setdefault(today, {})
        row["downloads"] = sum(assets.values())
        if isinstance(previous, dict):      # the new downloads of the files that are there now: a deleted release never makes a negative day
            row["new"] = sum(max(0, count - _count(previous.get(key))) for key, count in assets.items())
        changed = {key: count for key, count in assets.items() if not isinstance(previous, dict) or previous.get(key) != count}
        if changed:
            row.setdefault("assets", {}).update(changed)
        entry["latest"] = assets
        entry["releases_status"] = "ok"
    if cfg.get("views_clones") is not True:
        entry["traffic_status"] = "off"
    else:
        try:
            for kind in ("views", "clones"):
                for date, (count, uniques) in read_traffic(get, full, kind).items():
                    row = days.setdefault(date, {})
                    row[kind], row[kind + "_unique"] = count, uniques
        except Refused as refused:
            if refused.reason == "rate_limited":
                raise
            entry["traffic_status"] = refused.reason
        else:
            entry["traffic_status"] = "ok"
    entry["day"] = today


def prune(entry, keep_days, now):
    limit = time.strftime("%Y-%m-%d", time.gmtime(now - keep_days * 86400))
    entry["days"] = {date: row for date, row in (entry.get("days") or {}).items() if date >= limit}


def _number(value, default, low, high):
    """A number of the configuration file; anything else written there by hand is the default."""
    return min(high, max(low, value)) if isinstance(value, int) and not isinstance(value, bool) else default


def room(config, data):
    """True when this cycle can spend requests: not while the connection is lost or the first reading is under way, nor with no more than twice `min_rate_remaining` left (like the other optional reads)."""
    if not isinstance(data, dict):
        return True
    if data.get("loading") or (data.get("offline") or {}).get("offline"):
        return False
    remaining = (data.get("rate") or {}).get("remaining")
    return remaining is None or remaining > 2 * _number(config.get("min_rate_remaining"), 800, 0, 100000)


def refresh(config, owner, account="", get=None, now=None):
    """Reads the chosen repositories not yet read today (UTC), at most traffic.repos_per_cycle of them. Returns the names read."""
    if not active(config):
        return []
    cfg = settings(config)
    now = time.time() if now is None else now
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    get = get or reader()
    done = []
    with LOCK:
        data = load(account)
        due = [full for full in selected(config, owner) if (data["repos"].get(full) or {}).get("day") != today]
        for full in due[:_number(cfg.get("repos_per_cycle"), 2, 1, 10)]:
            entry = copy.deepcopy(data["repos"].get(full) or {})      # a read cut half way leaves what was kept as it was, so its new downloads are still counted next time
            try:
                read_one(get, full, entry, cfg, today)
            except Refused:      # the allowance is over: stop, and try again in a later cycle
                break
            prune(entry, _number(cfg.get("keep_days"), 400, 30, 3650), now)
            data["repos"][full] = entry
            done.append(full)
        if done:
            save(data, account)
    return done


def tick(config, account="", data=None):
    if not active(config) or RUNNING["on"] or not room(config, data):
        return None
    from github_actions_monitor.app import toolconfig
    owner = toolconfig.github_owner(config)
    RUNNING["on"] = True

    def work():
        try:
            refresh(config, owner, account)
        finally:
            RUNNING["on"] = False
    thread = threading.Thread(target=work, name="traffic", daemon=True)
    thread.start()
    return thread


def report(config, owner, account=""):
    """What is kept of the chosen repositories (the last 90 days) and how each read went. Nothing is read from GitHub here."""
    data = load(account)
    repos = []
    for full in selected(config, owner):
        entry = data["repos"].get(full) or {}
        days = [dict({"date": date}, **{field: row.get(field) for field in DAY_FIELDS}) for date, row in sorted((entry.get("days") or {}).items())][-SHOWN_DAYS:]
        latest = entry.get("latest")
        repos.append({"repo": full, "day": entry.get("day", ""), "releases_status": entry.get("releases_status", "pending"), "traffic_status": entry.get("traffic_status", "pending"),
                      "downloads": sum(latest.values()) if isinstance(latest, dict) else None, "days": days})
    return {"ok": True, "enabled": active(config), "repos": repos}


def cell(value):
    """A value of the CSV: a text that a spreadsheet would run as a formula gets a quote in front, and a line break never starts a row of its own."""
    if value is None:
        return ""
    text = str(value)
    risky = text[:1] in ("=", "+", "-", "@", "\t", "\r", "\n", "\uff1d", "\uff0b", "\uff0d", "\uff20")
    text = text.replace("\r", " ").replace("\n", " ")
    return "'" + text if risky else text


def csv_text(what="days", account=""):
    """Everything that is kept, also of repositories no longer chosen."""
    data = load(account)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    if what == "assets":
        writer.writerow(("date", "repository", "release", "file", "downloads"))
    else:
        writer.writerow(("date", "repository", "downloads_total", "downloads_new", "views", "views_unique", "clones", "clones_unique"))
    for full, entry in sorted(data["repos"].items()):
        for date, row in sorted((entry.get("days") or {}).items()):
            if what == "assets":
                for key, count in sorted((row.get("assets") or {}).items()):
                    tag, _slash, name = key.partition("/")
                    writer.writerow([cell(date), cell(full), cell(tag), cell(name), cell(count)])
            else:
                writer.writerow([cell(date), cell(full)] + [cell(row.get(field)) for field in DAY_FIELDS])
    return out.getvalue()


def text_lines(report_data):
    """One line per chosen repository for the command line."""
    lines = []
    for repo in report_data["repos"]:
        downloads = "-" if repo["downloads"] is None else repo["downloads"]
        lines.append(i18n.t("cli.traffic.line", repo=repo["repo"], downloads=downloads, day=repo["day"] or "-", releases=i18n.t("ui.traffic.status_" + repo["releases_status"]),
                            traffic=i18n.t("ui.traffic.status_" + repo["traffic_status"])))
    return lines
