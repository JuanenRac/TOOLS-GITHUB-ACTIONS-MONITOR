# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The workflow files of a repository WITHOUT a clone: for accounts so large that cloning every repository that has Actions is not an option (several GB per account).

Two ways, both read only and both set by `lint.source`:

  auto    the folder `.github/workflows` of each repository without a local clone is read through the contents API of GitHub: one call for the list and one for each file that is new or changed.
          The list carries the SHA of every file, so a file whose SHA did not change is never read again (the text is kept compressed in memory). A budget of calls per tick and a time
          between two readings of the same repository keep the cost small; what could not be read says WHY (no access, SSO not authorised, allowance spent, too big, over the file limit).
  sparse  a clone of depth 1 that fetches no file contents except `.github` (`git sparse-checkout`), a few repositories per tick, kept in the data folder of the monitor.

The same text feeds the linter (A13) and the workflow scan of the surface checks (A10); what only a full clone can answer (stacks, dependabot.yml, manifest, CHANGELOG) is listed as "not
evaluable" instead of being guessed. Standard library only. Nothing is ever written to GitHub."""
import base64
import re
import subprocess
import threading
import time
import zlib

NAME_RE = re.compile(r"^(?!\.+\Z)[A-Za-z0-9._-]{1,100}\Z")      # "." and ".." name no repository
FILE_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\.ya?ml\Z")
MAX_BYTES = 262144      # a workflow file bigger than this is skipped (the clone scan reads the same limit)
NOT_EVALUABLE_BY_API = ("stacks", "dependabot_yml", "manifest", "changelog")      # what a list of workflow files cannot say
REASONS = ("sso", "rate_limited", "auth", "forbidden", "error", "budget", "too_big", "over_limit")


def reason_of(message):
    """Why a read failed, from the text of the error of `gh`: sso (the token is not authorised for the organization), rate_limited, auth (bad credentials), not_found, forbidden (missing scope or
    permission) or error."""
    low = str(message or "").lower()
    if "saml" in low or "sso" in low:
        return "sso"
    if "rate limit" in low:
        return "rate_limited"
    if "401" in low or "bad credentials" in low:
        return "auth"
    if "404" in low or "not found" in low:
        return "not_found"
    if "403" in low or "not accessible" in low or "forbidden" in low:
        return "forbidden"
    return "error"


def _pack(text):
    return zlib.compress(text.encode("utf-8", "replace"), 6)


def _unpack(blob):
    return zlib.decompress(blob).decode("utf-8", "replace")


class Reader:
    """Reads and remembers the workflow files of repositories. `read(endpoint)` answers the JSON of a read of the API or raises; `owner()` answers the owner of the repositories."""

    def __init__(self, read, owner, clock=time.time):
        self.read, self.owner, self.clock = read, owner, clock
        self.entries = {}
        self.version = 0      # grows with every reading, so whoever caches a result of the linter knows it is old
        self.lock = threading.RLock()

    def forget(self, repos=None):
        with self.lock:
            for repo in list(self.entries) if repos is None else repos:
                self.entries.pop(repo, None)
            self.version += 1

    def due(self, repos, ttl):
        """The repositories to read now, the oldest (or never read) first: one never read, one that stayed partial, or one older than `ttl` seconds."""
        now = self.clock()
        with self.lock:
            late = [(self.entries.get(r, {}).get("at", 0.0), r) for r in repos if NAME_RE.match(str(r)) and (r not in self.entries or self.entries[r]["state"] == "partial" or now - self.entries[r]["at"] > ttl)]
        return [r for _, r in sorted(late)]

    def refresh(self, repo, max_calls, max_files=40):
        """Reads one repository inside `max_calls` calls. Returns the calls made. Never raises."""
        if max_calls < 1 or not NAME_RE.match(str(repo)):
            return 0
        with self.lock:
            old = self.entries.get(repo) or {}
        files, listing, skipped, calls, reason, state = dict(old.get("files") or {}), {}, [], 1, "", "ok"
        base = f"repos/{self.owner()}/{repo}/contents/.github/workflows"
        try:
            answer = self.read(base)
        except Exception as error:      # noqa: BLE001 - a repository that cannot be read says why, it never stops the others
            reason = reason_of(error)
            if reason == "not_found":      # there is no such folder: a repository without workflows
                files, reason = {}, ""
            else:
                state = "not_evaluable"
            self._store(repo, {"at": self.clock(), "state": state, "reason": reason, "files": files, "skipped": [], "truncated": False})
            return calls
        items = sorted((i for i in answer if isinstance(i, dict) and i.get("type") == "file" and FILE_RE.match(str(i.get("name") or ""))), key=lambda i: i["name"]) if isinstance(answer, list) else []
        truncated = len(items) > max_files
        fresh = {}
        for item in items[:max_files]:
            name, sha = item["name"], str(item.get("sha") or "")
            kept = files.get(name)
            if kept and sha and kept[0] == sha:      # the same file as the last time: not read again
                fresh[name] = kept
                continue
            if isinstance(item.get("size"), int) and item["size"] > MAX_BYTES:
                skipped.append((name, "too_big"))
                continue
            if calls >= max_calls:
                skipped.append((name, "budget"))
                continue
            calls += 1
            try:
                body = self.read(f"{base}/{name}")
                text = base64.b64decode(str(body.get("content") or "")).decode("utf-8", "replace") if isinstance(body, dict) and body.get("encoding") == "base64" else ""
            except Exception as error:      # noqa: BLE001
                skipped.append((name, reason_of(error)))
                if kept:
                    fresh[name] = kept      # an older reading of the file is better than none
                continue
            fresh[name] = (sha, _pack(text[:MAX_BYTES]))
        if skipped:
            state = "partial" if any(why == "budget" for _, why in skipped) else "ok"
            reason = skipped[0][1]
        if truncated and state == "ok":
            reason = "over_limit"
        self._store(repo, {"at": self.clock(), "state": state, "reason": reason, "files": fresh, "skipped": [n for n, _ in skipped], "truncated": truncated})
        return calls

    def _store(self, repo, entry):
        with self.lock:
            self.entries[repo] = entry
            self.version += 1

    def texts(self, repo):
        """{file name: text} of what is known about a repository (empty when nothing)."""
        with self.lock:
            entry = self.entries.get(repo) or {}
            return {name: _unpack(pair[1]) for name, pair in (entry.get("files") or {}).items()}

    def shas(self, repo):
        """[[file name, blob SHA], ...] sorted, of the files of a repository that were read completely (empty when the reading is partial or nothing is known): the content fingerprint of the folder."""
        with self.lock:
            entry = self.entries.get(repo) or {}
            if entry.get("state") != "ok" or entry.get("skipped"):
                return []
            return [[name, pair[0]] for name, pair in sorted((entry.get("files") or {}).items())]

    def state(self, repo):
        """None when the repository was never read, else {"state": ok | partial | not_evaluable, "reason", "files", "skipped", "truncated", "at"}."""
        with self.lock:
            entry = self.entries.get(repo)
            return None if entry is None else {"state": entry["state"], "reason": entry["reason"], "files": len(entry["files"]), "skipped": list(entry["skipped"]), "truncated": entry["truncated"], "at": entry["at"]}

    def known(self):
        with self.lock:
            return sorted(self.entries)


def coverage(reader, repos, clone_repos, sparse_repos, source, limit=50):
    """What was read and how, for the page and the brief: {"source", "repos", "clone", "sparse", "api", "partial", "waiting", "not_evaluable": [{"repo", "reason"}], "not_evaluable_total",
    "by_reason": {reason: n}, "api_cannot": [...checks a list of files cannot answer]}. A repository without a clone, while `source` is `clone`, is not evaluable with the reason `no_clone`."""
    clone_set, sparse_set = set(clone_repos), set(sparse_repos)
    api, partial, waiting, missing = 0, 0, 0, []
    for repo in repos:
        if repo in clone_set or repo in sparse_set:
            continue
        state = reader.state(repo) if source != "clone" else None
        if state is None:
            if source == "clone":
                missing.append({"repo": repo, "reason": "no_clone"})
            else:
                waiting += 1
        elif state["state"] == "not_evaluable":
            missing.append({"repo": repo, "reason": state["reason"] or "error"})
        else:
            api += 1
            partial += 1 if state["state"] == "partial" or state["skipped"] or state["truncated"] else 0
    by_reason = {}
    for row in missing:
        by_reason[row["reason"]] = by_reason.get(row["reason"], 0) + 1
    return {"source": source, "repos": len(repos), "clone": len(clone_set & set(repos)), "sparse": len(sparse_set & set(repos)), "api": api, "partial": partial, "waiting": waiting,
            "not_evaluable": missing[:limit], "not_evaluable_total": len(missing), "by_reason": by_reason, "api_cannot": list(NOT_EVALUABLE_BY_API) if api else []}


def coverage_text(cov, t):
    """The sentence of the coverage for the panel and the brief (`t` translates): empty when everything was read from clones and nothing is missing."""
    if not isinstance(cov, dict) or not (cov.get("api") or cov.get("sparse") or cov.get("not_evaluable_total") or cov.get("waiting")):
        return ""
    parts = [t("ui.a13_cov", clone=cov.get("clone", 0), sparse=cov.get("sparse", 0), api=cov.get("api", 0))]
    if cov.get("not_evaluable_total"):
        reasons = ", ".join(f"{t('lint.reason.' + reason)} x{n}" for reason, n in sorted((cov.get("by_reason") or {}).items(), key=lambda kv: (-kv[1], kv[0])))
        parts.append(t("ui.a13_cov_ne", n=cov["not_evaluable_total"], reasons=reasons))
    if cov.get("waiting"):
        parts.append(t("ui.a13_cov_wait", n=cov["waiting"]))
    if cov.get("partial"):
        parts.append(t("ui.a13_cov_partial", n=cov["partial"]))
    if cov.get("api_cannot"):
        parts.append(t("ui.a13_cov_cannot"))
    return " ".join(parts)


# -- sparse clone -------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def default_runner(args, timeout=180):
    """(code, stdout, stderr) of one command with a fixed argument list (no shell)."""
    try:
        extra = {}
        if args and args[0] == "gh":
            from github_actions_monitor.security import secretstore
            extra = secretstore.gh_kwargs()
        done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, **extra)
        return done.returncode, done.stdout, done.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, "", str(error)


def gh_read(endpoint, runner=default_runner):
    """The JSON of one GET of the API through `gh`, or a RuntimeError with the text of the error (for the command line; the monitor uses its own reader)."""
    import json
    code, out, err = runner(["gh", "api", endpoint], 40)
    if code != 0:
        raise RuntimeError((err or out or "gh failed").strip()[:300])
    return json.loads(out) if out.strip() else None


def sparse_commands(owner, repo, dest, exists):
    """The commands that bring `.github` of a repository to `dest` and nothing else: a clone of depth 1 without file contents (`--filter=blob:none`) restricted to `.github`, or, when the clone is
    already there, a fetch of depth 1 and a reset. Pure: the caller runs them."""
    if exists:
        return [["git", "-C", dest, "fetch", "--depth", "1", "origin"], ["git", "-C", dest, "reset", "--hard", "FETCH_HEAD"]]
    return [["gh", "repo", "clone", f"{owner}/{repo}", dest, "--", "--depth", "1", "--filter=blob:none", "--sparse"], ["git", "-C", dest, "sparse-checkout", "set", ".github"]]


def sparse_refresh(owner, repo, root, runner=default_runner):
    """Fetches `.github` of one repository into `root/repo` with a sparse clone. Returns (ok, reason). The reason is the one `reason_of` gives for the first command that failed."""
    from pathlib import Path
    if not NAME_RE.match(str(repo)):
        return False, "error"
    dest = Path(root) / repo
    for command in sparse_commands(owner, repo, str(dest), (dest / ".git").exists()):
        code, _out, err = runner(command)
        if code != 0:
            return False, reason_of(err)
    return True, ""
