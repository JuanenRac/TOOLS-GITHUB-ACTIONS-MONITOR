# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Three official example plugins, written as sentinels behind the contract of `BaseSentinel`: Discussions, Release notes and Packages. They only read, they raise only findings (alerts) and they
take everything from the context they are given:

  ctx.plugin_repos()          the repositories to look at ("owner/name")
  ctx.plugin_fetch(kind, repo)  a list of plain dicts for kind "discussions", "releases" or "packages" (the product backs it with its conditional GET reader)
  ctx.account_id              the account (empty for the single account)

Time comes from the `clock` given to the constructor, so the rules are tested without waiting. They are also the checklist of "how to write an official sentinel": a class with a `name`, a stable
`code` per finding, a title through the language of the page, a `get_config_schema`, and nothing written to GitHub.

Findings
  discussions.unanswered   a discussion that asks a question and has had no answer for `unanswered_days`
  releases.draft_old       a draft release that has stayed a draft for `draft_days`
  releases.no_notes        a published release with an empty body
  packages.stale           a package with no new version for `stale_days`
  packages.many_versions   a package with more than `max_versions` versions"""
import time
from datetime import datetime, timezone

from github_actions_monitor.phase4 import msgs
from github_actions_monitor.sentinels import sentinel_base

TITLES = {
    "discussions.unanswered": {
        "en": "Discussion {item} has had no answer for {days} days", "es": "La discusión {item} lleva {days} días sin respuesta",
        "de": "Diskussion {item} ist seit {days} Tagen unbeantwortet", "fr": "La discussion {item} est sans réponse depuis {days} jours",
        "it": "La discussione {item} è senza risposta da {days} giorni", "ja": "ディスカッション {item} は {days} 日間回答がありません",
        "zh": "讨论 {item} 已 {days} 天无人回答", "pt": "A discussão {item} está há {days} dias sem resposta"},
    "releases.draft_old": {
        "en": "Draft release {item} has been a draft for {days} days", "es": "La release {item} lleva {days} días como borrador",
        "de": "Release-Entwurf {item} ist seit {days} Tagen ein Entwurf", "fr": "La release {item} est un brouillon depuis {days} jours",
        "it": "La release {item} è una bozza da {days} giorni", "ja": "リリース {item} は {days} 日間下書きのままです",
        "zh": "发布 {item} 已有 {days} 天处于草稿状态", "pt": "A release {item} está há {days} dias como rascunho"},
    "releases.no_notes": {
        "en": "Release {item} was published without notes", "es": "La release {item} se publicó sin notas",
        "de": "Release {item} wurde ohne Notizen veröffentlicht", "fr": "La release {item} a été publiée sans notes",
        "it": "La release {item} è stata pubblicata senza note", "ja": "リリース {item} はノートなしで公開されました",
        "zh": "发布 {item} 没有说明就已发布", "pt": "A release {item} foi publicada sem notas"},
    "packages.stale": {
        "en": "Package {item} has had no new version for {days} days", "es": "El paquete {item} lleva {days} días sin versión nueva",
        "de": "Paket {item} hat seit {days} Tagen keine neue Version", "fr": "Le paquet {item} n'a pas de nouvelle version depuis {days} jours",
        "it": "Il pacchetto {item} non ha una nuova versione da {days} giorni", "ja": "パッケージ {item} は {days} 日間新しいバージョンがありません",
        "zh": "软件包 {item} 已 {days} 天没有新版本", "pt": "O pacote {item} está há {days} dias sem versão nova"},
    "packages.many_versions": {
        "en": "Package {item} keeps {count} versions", "es": "El paquete {item} guarda {count} versiones", "de": "Paket {item} hält {count} Versionen vor",
        "fr": "Le paquet {item} conserve {count} versions", "it": "Il pacchetto {item} conserva {count} versioni", "ja": "パッケージ {item} は {count} 個のバージョンを保持しています",
        "zh": "软件包 {item} 保留了 {count} 个版本", "pt": "O pacote {item} guarda {count} versões"},
}
LEVELS = {"discussions.unanswered": "info", "releases.draft_old": "warning", "releases.no_notes": "info", "packages.stale": "info", "packages.many_versions": "info"}


def _parse(stamp):
    try:
        return datetime.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _Example(sentinel_base.BaseSentinel):
    kind = ""
    DEFAULTS: dict = {}
    BOUNDS: dict = {}

    def __init__(self, ctx, config, clock=None, lang="en"):
        super().__init__(ctx, config)
        self._clock = clock or time.time
        self._lang = lang
        self.cfg = dict(self.DEFAULTS)
        for key, value in (config or {}).items():
            default = self.DEFAULTS.get(key)
            low, high = self.BOUNDS.get(key, (None, None))
            if key in self.DEFAULTS and isinstance(value, type(default)) and not isinstance(value, bool) and (low is None or low <= value <= high):
                self.cfg[key] = value
        self._alerts = []
        self._errors = []
        self._checked = 0
        self._loaded = False

    @property
    def refresh_seconds(self):
        return self.cfg["refresh_seconds"]

    def findings(self, repo, rows, now):          # pragma: no cover - overridden
        raise NotImplementedError

    def tick(self):
        now = self._clock()
        alerts, errors, checked = [], [], 0
        for repo in self.ctx.plugin_repos():
            try:
                rows = self.ctx.plugin_fetch(self.kind, repo)
            except Exception as exc:   # noqa: BLE001 - one repository that cannot be read does not hide the others
                errors.append("{}: {}".format(repo, str(exc)[:80]))
                continue
            checked += 1
            for code, item, days, count in self.findings(repo, rows, now):
                text = TITLES[code].get(self._lang) or TITLES[code]["en"]
                alerts.append({"id": "{}:{}:{}".format(code, repo, item), "code": code, "level": LEVELS[code], "sentinel": self.name,
                               "account_id": getattr(self.ctx, "account_id", "") or "", "repo": repo,
                               "title": text.format(item=item, days=days, count=count), "details": {"item": item, "days": days, "count": count}, "created_at": _iso(now)})
        self._alerts, self._errors, self._checked, self._loaded = alerts, errors, checked, True

    def get_status(self):
        return {"enabled": self.enabled, "loading": not self._loaded, "errors": list(self._errors), "repos_checked": self._checked,
                "level": "unknown" if not self._loaded else ("warning" if self._alerts else "ok")}

    def get_alerts(self):
        return list(self._alerts)

    def get_metrics(self):
        return {self.name + "_alerts": len(self._alerts), self.name + "_repos_checked": self._checked, self.name + "_errors": len(self._errors)}

    def get_config_schema(self):
        return {key: {"type": type(value).__name__, "default": value, "min": self.BOUNDS.get(key, (None, None))[0], "max": self.BOUNDS.get(key, (None, None))[1]} for key, value in self.DEFAULTS.items()}


class DiscussionsSentinel(_Example):
    name = "discussions"
    kind = "discussions"
    DEFAULTS = {"refresh_seconds": 900, "unanswered_days": 7}
    BOUNDS = {"refresh_seconds": (60, 86400), "unanswered_days": (1, 365)}

    def findings(self, repo, rows, now):
        for row in rows or []:
            stamp = _parse(row.get("created_at"))
            if row.get("is_question") and not row.get("answered") and not row.get("closed") and stamp is not None:
                days = int((now - stamp) // 86400)
                if days >= self.cfg["unanswered_days"]:
                    yield "discussions.unanswered", "#{}".format(row.get("number")), days, 0


class ReleaseNotesSentinel(_Example):
    name = "releases"
    kind = "releases"
    DEFAULTS = {"refresh_seconds": 900, "draft_days": 14}
    BOUNDS = {"refresh_seconds": (60, 86400), "draft_days": (1, 365)}

    def findings(self, repo, rows, now):
        for row in rows or []:
            tag = str(row.get("tag") or row.get("name") or "?")[:60]
            stamp = _parse(row.get("created_at"))
            if row.get("draft"):
                if stamp is not None and (now - stamp) // 86400 >= self.cfg["draft_days"]:
                    yield "releases.draft_old", tag, int((now - stamp) // 86400), 0
            elif not str(row.get("body") or "").strip():
                yield "releases.no_notes", tag, 0, 0


class PackagesSentinel(_Example):
    name = "packages"
    kind = "packages"
    DEFAULTS = {"refresh_seconds": 3600, "stale_days": 180, "max_versions": 100}
    BOUNDS = {"refresh_seconds": (60, 86400), "stale_days": (7, 3650), "max_versions": (5, 10000)}

    def findings(self, repo, rows, now):
        for row in rows or []:
            name = str(row.get("name") or "?")[:80]
            stamp = _parse(row.get("last_published_at"))
            if stamp is not None and (now - stamp) // 86400 >= self.cfg["stale_days"]:
                yield "packages.stale", name, int((now - stamp) // 86400), 0
            count = row.get("versions")
            if isinstance(count, int) and not isinstance(count, bool) and count > self.cfg["max_versions"]:
                yield "packages.many_versions", name, 0, count


OFFICIAL = {"discussions": DiscussionsSentinel, "releases": ReleaseNotesSentinel, "packages": PackagesSentinel}
MANIFESTS = {name: {"name": name, "version": "1.0.0", "api_compat": "1", "author": "official", "permissions": ["read_github"], "trust": "official",
                    "entry": "github_actions_monitor.phase4.official_plugins:" + cls.__name__} for name, cls in OFFICIAL.items()}


def official_factory(manifest, ctx, config):
    """The factory for `PluginRegistry`: only entries that name one of the official classes above can be built; there is no import by name."""
    entry = manifest["entry"]
    for cls in OFFICIAL.values():
        if entry == "github_actions_monitor.phase4.official_plugins:" + cls.__name__:
            return cls(ctx, config)
    raise LookupError(msgs.t("en", "plugin.invalid_manifest", reason="entry"))
