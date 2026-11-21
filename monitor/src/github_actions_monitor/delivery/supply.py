# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The supply chain signals of the workflows of a repository: what a workflow file lets an outsider (or a moved tag) do with the token and the code of the repository.

Pure functions over the TEXT of the workflow files (the sentinel reads it from the API, `integrations/remote_workflows.Reader`); nothing here touches the network or the disk. There are NO rules of
its own: the findings come from `cli/lint_workflows.lint_text` (one source of truth for the local linter, the panels and this sentinel), only four of its rules are switched on and the others
(`secrets_in_clear` above all) stay off, so the value of a suspected secret is never even read here. A finding of the linter is mapped to one signal:

  actions.supply.unpinned            `uses:` of an action or reusable workflow that is not pinned to a full commit SHA (a tag can be moved by its owner)
  actions.supply.mutable_ref         the same, but on a branch that moves by itself (`@main`, `@master`...): worse than a tag
  actions.supply.permissions_wide    `permissions: write-all`
  actions.supply.permissions_missing a workflow with no `permissions:` block (the token gets the broader default)
  actions.supply.pr_target_checkout  `pull_request_target` together with a checkout of the pull request's code

Frontier with the Security sentinel: `security.workflow_write` is the default permission of the REPOSITORY (a setting of GitHub); the signals here are about the CONTENT of each workflow file, so the
same repository never raises the same finding from both. A `uses:` that points to a workflow of the same repository (`OWNER/REPO/.github/workflows/x.yml@ref`) is not a third party and is left out.
"""
import fnmatch
import re

from github_actions_monitor.cli import lint_workflows

SIGNALS = ("unpinned", "mutable_ref", "permissions_wide", "permissions_missing", "pr_target_checkout")
CODES = {name: "actions.supply." + name for name in SIGNALS}
SIGNAL_OF = {code: name for name, code in CODES.items()}
USED_RULES = ("unpinned_uses", "permissions", "pr_target")      # the only rules of the linter this module switches on
LEVELS = ("info", "warning", "error", "critical")
DEFAULT_LEVEL = {"unpinned": "warning", "mutable_ref": "warning", "permissions_wide": "warning", "permissions_missing": "warning", "pr_target_checkout": "error"}
USES_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}/[A-Za-z0-9._*?-]{1,100}\Z")      # `owner/repo` of an action or reusable workflow, with * and ? for any
MAX_FILES, MAX_EXAMPLES = 5, 3      # what an alert lists of where it was found (the numbers carry the rest)


def lint_rules(config=None):
    """The rules handed to `lint_text`: the user's `lint` settings (own owners, how an own action is treated) with ONLY the three rules of this module on, whatever `lint.rules` says (the sentinel has
    its own switches per signal). Every other rule is off, so nothing else of the file is read."""
    rules = lint_workflows.settings(config)["rules"]
    for name in lint_workflows.RULES:
        entry = dict(rules.get(name) or {})
        entry["enabled"] = name in USED_RULES
        rules[name] = entry
    return rules


def signal_of(finding, repo="", owner=""):
    """The signal of a finding of the linter, or "" when it is not one of ours (or points to the repository itself)."""
    rule, detail = finding.get("rule"), str(finding.get("detail") or "")
    if rule == "unpinned_uses":
        spec = detail.lower()
        if owner and repo and spec.startswith(f"{owner}/{repo}/".lower()):
            return ""
        ref = spec.split("@", 1)[1] if "@" in spec else ""
        return "mutable_ref" if ref in lint_workflows.MOVING_REFS else "unpinned"
    if rule == "permissions":
        return "permissions_wide" if detail == "write-all" else ("permissions_missing" if detail == "missing" else "")
    if rule == "pr_target":
        return "pr_target_checkout"
    return ""


def left_out(detail, patterns):
    """True when the `uses:` text (`owner/repo[/path]@ref`) belongs to an `owner/repo` of `patterns` (`sentinels.supply.ignore_uses`): an action or reusable workflow of another organisation that the token
    cannot see, whose ref the monitor cannot judge, so it is left out of the findings instead of being reported on a guess. The name is compared in lower case."""
    spec = str(detail or "").split("@", 1)[0].lower().split("/")
    name = "/".join(spec[:2])
    return len(spec) >= 2 and any(fnmatch.fnmatchcase(name, str(p).lower()) for p in patterns or ())


def findings(repo, texts, config=None, owner="", ignore=(), ignore_uses=(), skipped=None, unlintable=None):
    """[{"signal", "file", "line", "detail", "severity"}] of every workflow file of `repo` (`texts` = {file name: text}), already filtered by `ignore` (patterns `repo:file:rule`), by the comment
    `# monitor-lint: ignore RULE` of the file and by `ignore_uses` (`owner/repo` of the actions that cannot be judged: the ones left out are appended to the list `skipped`, when given, so they are counted and
    never silent). A file the linter cannot process is skipped on its own (its name goes to `unlintable`, when given) and the other files are still judged. Order: by file and line, so the answer is the same for the same texts."""
    rules, out = lint_rules(config), []
    for name in sorted(texts):
        label = ".github/workflows/" + name
        try:
            items = list(lint_workflows.lint_text(texts[name], label, rules))
        except Exception:   # noqa: BLE001 - one file that cannot be linted never takes the repository with it
            if unlintable is not None:
                unlintable.append(name)
            continue
        for item in items:
            if lint_workflows.ignored(repo, item, ignore):
                continue
            signal = signal_of(item, repo, owner)
            if signal in ("unpinned", "mutable_ref") and left_out(item["detail"], ignore_uses):
                if skipped is not None:
                    skipped.append({"file": name, "line": item["line"], "detail": item["detail"]})
                continue
            if signal:
                out.append({"signal": signal, "file": name, "line": item["line"], "detail": item["detail"] if signal in ("unpinned", "mutable_ref") else "", "severity": item["severity"]})
    return out


def evaluate(repo, found, signals, known=None, stamp=""):
    """{alert id: alert} of one repository from its findings (`found` = `findings(...)`); `signals` = {signal: {"enabled", "level"}}. One alert per repository and signal, with the number of findings and
    where they are (a few files and examples: the name of an action is public, the value of a secret is never read). Pure. `known` are the alerts already open (they keep their `created_at`)."""
    known, alerts = known or {}, {}
    for signal in SIGNALS:
        mine = [f for f in found if f["signal"] == signal]
        rule = signals.get(signal) or {}
        if not mine or not rule.get("enabled", True):
            continue
        key = f"{CODES[signal]}:{repo}"
        level = rule.get("level") or DEFAULT_LEVEL[signal]
        if signal in ("unpinned", "mutable_ref") and all(f["severity"] == "info" for f in mine):
            level = "info"      # an own action that the user lowered to information in `lint.unpinned_own`
        files = sorted({f["file"] for f in mine})
        examples = []
        for f in mine:
            if f["detail"] and f["detail"] not in examples:
                examples.append(f["detail"])
        alerts[key] = {"id": key, "code": CODES[signal], "level": level, "repo": repo, "created_at": (known.get(key) or {}).get("created_at") or stamp,
                       "detail": {"n": len(mine), "files": files[:MAX_FILES], "files_total": len(files), "examples": examples[:MAX_EXAMPLES]}}
    return alerts


def penalty(alerts, per_finding, cap):
    """Points for the open alerts, informative (the score does not use them unless the owner gives the part a weight): `per_finding` for each finding, at most `cap` per repository."""
    by_repo = {}
    for a in alerts:
        by_repo[a["repo"]] = by_repo.get(a["repo"], 0) + int((a.get("detail") or {}).get("n", 1)) * per_finding
    return sum(min(cap, points) for points in by_repo.values())
