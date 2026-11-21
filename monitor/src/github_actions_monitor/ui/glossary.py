# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The glossary of the monitor: what each figure means exactly, the attacks the rules of the linter exist for, the limits of the analysis and a few places to learn more.

The definitions of the figures are written with the REAL parameters of the calculation, read from the code and from the settings of the person (the events that decide a red, the days after which a
workflow is called abandoned, the size of the sample), so the page never says one thing and the code does another. Everything is text of the eight languages (`gl.*`); the links are the only data here and
all of them are public documentation or projects that only READ workflows (nothing offensive is linked or integrated).

  metrics(config)       [{"id", "name", "definition"}] with the numbers filled in
  attacks()             [{"id", "name", "definition"}]
  limits()              the honest list of what the analysis does not do
  resources()           [{"name", "url"}]
  payload(config)       everything GET /api/glossary answers
"""
from github_actions_monitor import i18n
from github_actions_monitor.data_pipeline import redrule

METRICS = ("red_main", "ok24", "streak", "duration", "queue_wait", "fail_rate")
ATTACKS = ("pwn_request", "expression_injection", "cache_poisoning", "repo_jacking", "impostor_commit")
LIMITS = 5
RESOURCES = (
    ("Security hardening for GitHub Actions (GitHub Docs)", "https://docs.github.com/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions"),
    ("OpenSSF Scorecard", "https://scorecard.dev/"),
    ("OWASP Top 10 CI/CD Security Risks", "https://owasp.org/www-project-top-10-ci-cd-security-risks/"),
    ("zizmor, a static analyzer for GitHub Actions", "https://github.com/zizmorcore/zizmor"),
    ("GitHub Actions documentation", "https://docs.github.com/actions"),
    ("Awesome Actions", "https://github.com/sdras/awesome-actions"),
)


def _ci(config):
    block = (config or {}).get("ci") if isinstance((config or {}).get("ci"), dict) else {}
    events = block.get("red_events")
    return {"events": ", ".join(e for e in events if isinstance(e, str)) if isinstance(events, list) and events else ", ".join(redrule.RED_EVENTS),
            "inactive": block.get("inactive_days") if isinstance(block.get("inactive_days"), int) else redrule.DEFAULT_INACTIVE_DAYS,
            "aging": block.get("red_age_days") if isinstance(block.get("red_age_days"), int) else redrule.DEFAULT_RED_AGE_DAYS}


def metrics(config=None):
    ci = _ci(config)
    params = {"events": ci["events"], "inactive": ci["inactive"], "aging": ci["aging"], "recent": 10, "window": 24, "sample": 600}
    return [{"id": m, "name": i18n.t(f"gl.m.{m}.name"), "definition": i18n.t(f"gl.m.{m}.def", **params)} for m in METRICS]


def attacks():
    return [{"id": a, "name": i18n.t(f"gl.a.{a}.name"), "definition": i18n.t(f"gl.a.{a}.def")} for a in ATTACKS]


def limits():
    return [i18n.t(f"ui.rx_limits_{n}") for n in range(1, LIMITS + 1)]


def resources():
    return [{"name": name, "url": url} for name, url in RESOURCES]


def payload(config=None):
    return {"metrics": metrics(config), "attacks": attacks(), "limits_title": i18n.t("ui.rx_limits_title"), "limits": limits(), "resources": resources()}
