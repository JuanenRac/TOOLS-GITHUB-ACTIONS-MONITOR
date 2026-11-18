# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The CI sentinel (1.7.1): the sentinel of always (stuck builds, red CI, alerts, releases, hygiene, consumption...) behind the contract of `sentinel_base.BaseSentinel`.

Nothing of how it decides changes: `sentinel_local.Sentinel` keeps its rules, its criterion of "red" (the last completed run of each workflow on the default branch), its files and its own
loop; this class holds one of them and answers the contract with what it already knows. Whatever the monitor asked of the old object it still can: the attributes that are not part of the
contract (`snapshot`, `feed`, `refresh_repos`, `ai_explain`...) are those of the held sentinel.

The alerts it gives have stable codes, independent of the language: `ci.red`, `ci.stuck`, `ci.ghost_queue`, `ci.upstream_red`, `ci.upstream_release`, `ci.pending_sign`, `ci.dependabot_failed` (medium: the dependency updates of GitHub failed) and `ci.copilot_activity` (information: a workflow of Copilot failed; off by default).
"""
from github_actions_monitor.sentinels import sentinel_base
from github_actions_monitor.sentinels import sentinel_local
from github_actions_monitor import i18n
from github_actions_monitor.data_pipeline import redrule


def _type_name(value):
    for kind, label in ((bool, "bool"), (int, "int"), (float, "float"), (str, "str"), (list, "list"), (dict, "dict")):
        if isinstance(value, kind):
            return label
    return "any"


class SentinelCI(sentinel_base.BaseSentinel):
    name = "ci"

    def __init__(self, ctx, config):
        super().__init__(ctx, config)
        self.core = sentinel_local.Sentinel(ctx, config)

    def __getattr__(self, attribute):
        if attribute == "core":                  # not built yet (or being copied): never loop looking for it
            raise AttributeError(attribute)
        return getattr(self.core, attribute)

    @property
    def enabled(self):
        return bool(self.core.cfg["enabled"])

    @property
    def refresh_seconds(self):
        return int(self.core.cfg["refresh_seconds"])

    @property
    def account_id(self):
        return str((self.ctx or {}).get("account_id") or "")

    # -- the cycle: the old object has its own loop, and it is the one that runs
    def start(self):
        self.core.start()

    def stop(self):
        super().stop()

    def tick(self):
        return self.core.tick()

    def _picture(self):
        return self.core.last_snap or self.core.snapshot()

    # -- the contract
    def get_status(self):
        snap = self._picture()
        return {"enabled": self.enabled, "loading": snap.get("loading", "") if snap.get("enabled", True) else "", "level": snap.get("level", "unknown") if snap.get("enabled", True) else "off",
                "errors": [{"section": e["section"], "at": e["at"]} for e in snap.get("errors", [])], "refresh_seconds": self.refresh_seconds}

    def get_alerts(self):
        snap = self._picture()
        if not snap.get("enabled", True):
            return []
        generated = snap.get("generated") or ""
        out = []

        def alert(code, level, repo, title, details, created, key):
            out.append({"id": f"{code}:{key}", "code": code, "level": level, "sentinel": self.name, "account_id": self.account_id, "repo": repo or None, "title": title, "details": details,
                        "created_at": created or generated})

        for red in (snap.get("a2") or {}).get("red", []):
            alert("ci.red", "error", red.get("repo"), i18n.t("evt.red_new", repo=red.get("repo"), workflow=red.get("workflow")),
                  {"workflow": red.get("workflow"), "streak": red.get("streak"), "url": red.get("url"), "branch": red.get("branch"), "file": red.get("file")}, red.get("since"), f"{red.get('repo')}:{red.get('workflow')}")
        for stuck in (snap.get("a1") or {}).get("stuck", []):
            alert("ci.stuck", "error", stuck.get("repo"), i18n.t("evt.stuck_new", repo=stuck.get("repo"), name=stuck.get("name")),
                  {"name": stuck.get("name"), "seconds": stuck.get("seconds"), "url": stuck.get("url")}, None, f"{stuck.get('repo')}:{stuck.get('name')}")
        ghosts = {}
        for ghost in (snap.get("a1") or {}).get("ghosts", []):
            ghosts.setdefault(ghost.get("repo"), []).append(ghost)
        for repo, items in sorted(ghosts.items(), key=lambda kv: str(kv[0])):      # one notice per repository, never an error: GitHub never starts these runs, nobody can fix them with a push
            days = (snap.get("a1") or {}).get("ghost_days")
            alert("ci.ghost_queue", "info", repo, i18n.t("evt.ghost_queue", repo=repo, n=len(items), days=days),
                  {"count": len(items), "days": days, "oldest": min((g.get("since") or "" for g in items), default=""), "urls": [g.get("url") for g in items[:5]]}, None, f"{repo}")
        follow = snap.get("upstream") or {}
        if follow.get("enabled") and follow.get("notify"):      # only what the person asked to be told: the original is red, or published a release lately; information, never an error
            for row in follow.get("rows", []):
                if row.get("red"):
                    alert("ci.upstream_red", "info", row.get("repo"), i18n.t("evt.upstream_red", repo=row.get("repo"), parent=row.get("parent")),
                          {"parent": row.get("parent"), "branch": row.get("branch"), "url": row.get("url"), "since": row.get("state_since")}, None, f"{row.get('repo')}")
                if row.get("news") and row.get("release"):
                    alert("ci.upstream_release", "info", row.get("repo"), i18n.t("evt.upstream_release", repo=row.get("repo"), parent=row.get("parent"), tag=row["release"].get("tag")),
                          {"parent": row.get("parent"), "tag": row["release"].get("tag"), "url": row["release"].get("url")}, None, f"{row.get('repo')}:{row['release'].get('tag')}")
        for wait in (snap.get("a5") or {}).get("pending_sign", []):
            alert("ci.pending_sign", "warning", wait.get("repo"), i18n.t("evt.pending_sign", repo=wait.get("repo"), hours=wait.get("hours")),
                  {"workflow": wait.get("workflow"), "hours": wait.get("hours"), "url": wait.get("url")}, wait.get("since"), f"{wait.get('repo')}:{wait.get('workflow')}")
        for row in (snap.get("a2") or {}).get("services", []):      # the workflows GitHub makes for itself are never a red: a failing update of Dependabot is a medium alert, the activity of Copilot a notice
            if row.get("service") == "dependabot" and redrule.POLICY["dependabot_alerts"]:
                alert("ci.dependabot_failed", "warning", row.get("repo"), i18n.t("evt.dependabot_failed", repo=row.get("repo")),
                      {"workflow": row.get("workflow"), "conclusion": row.get("conclusion"), "url": row.get("url")}, row.get("since"), f"{row.get('repo')}")
            elif row.get("service") == "copilot" and redrule.POLICY["copilot_alerts"]:
                alert("ci.copilot_activity", "info", row.get("repo"), i18n.t("evt.copilot_activity", repo=row.get("repo"), workflow=row.get("workflow")),
                      {"workflow": row.get("workflow"), "conclusion": row.get("conclusion"), "url": row.get("url")}, row.get("since"), f"{row.get('repo')}:{row.get('workflow')}")
        return out

    def get_metrics(self):
        snap = self._picture()
        if not snap.get("enabled", True):
            return {}
        metrics = {f"ci_{key}": value for key, value in (snap.get("totals") or {}).items() if isinstance(value, (int, float))}
        remaining = (snap.get("rate") or {}).get("remaining")
        if isinstance(remaining, (int, float)):
            metrics["ci_api_remaining"] = remaining
        metrics["ci_api_calls_last_hour"] = len([t for t in self.core.calls if t > __import__("time").time() - 3600])
        return metrics

    def get_config_schema(self):
        """The options of `sentinel` (and of `sentinels.ci`, which overrides them) with their type and default."""
        return {"name": self.name, "keys": {key: {"type": _type_name(value), "default": value} for key, value in sorted(sentinel_local.DEFAULTS.items()) if key not in ("surface", "readiness")},
                "groups": ["surface", "readiness"]}
