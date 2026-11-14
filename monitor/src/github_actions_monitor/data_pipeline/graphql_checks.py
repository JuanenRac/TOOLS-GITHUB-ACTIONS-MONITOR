# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Reading the workflows of COLD repositories through GraphQL (OFF by default, `network.graphql_checks`).

GraphQL has an allowance of its own, apart from the REST one, and one query can ask for many repositories (an alias each). For a repository that nothing has touched for a while, one read of the
check suites of the last commit of its default branch tells which workflows are red or green, so a batch of up to `network.graphql_batch` repositories costs one GraphQL call instead of one REST call
each. What it cannot give is said in docs/QUOTA.md: only the last commit of the default branch (a workflow that did not run on that commit is not listed), no durations, no attempts, no other
branches. Hot repositories (a run in progress, a red workflow) keep being read through REST, and any repository the query does not answer is read through REST in the same cycle.

This module only builds the query and reads the answer; actions_monitor.py makes the call (`gh api graphql`, the login of the user)."""
import re

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{1,39}\Z")
DEFAULT_BATCH = 20
STATS = {"calls": 0, "repos": 0, "fallbacks": 0, "cost": 0, "errors": 0}


def settings(config):
    """{"enabled": bool, "batch": int}; anything that is not a clean value gives the defaults (off, 20)."""
    block = config.get("network") if isinstance(config, dict) else None
    block = block if isinstance(block, dict) else {}
    batch = block.get("graphql_batch")
    batch = batch if isinstance(batch, int) and not isinstance(batch, bool) and 1 <= batch <= 30 else DEFAULT_BATCH
    return {"enabled": block.get("graphql_checks") is True, "batch": batch}


def stats(config=None):
    """The counters of this process for the accounting of the allowance; None while the feature is off and has never been used."""
    if config is not None and not settings(config)["enabled"] and not STATS["calls"]:
        return None
    return dict(STATS)


def query(owner, repos):
    """The GraphQL text for a batch of repositories (one alias each). Names that are not plain repository names are left out (they could not be inlined safely)."""
    if not OWNER_RE.match(str(owner)):
        raise ValueError("owner")
    parts = []
    for index, repo in enumerate(repos):
        if not NAME_RE.match(str(repo)):
            continue
        parts.append(f'r{index}: repository(owner: "{owner}", name: "{repo}") {{ defaultBranchRef {{ name target {{ ... on Commit {{ oid checkSuites(first: 30) {{ nodes {{ conclusion status createdAt '
                     f'workflowRun {{ event runNumber databaseId url workflow {{ name resourcePath }} }} }} }} }} }} }} }}')
    return "query { " + " ".join(parts) + " rateLimit { cost remaining } }"


def _runs(repo, node):
    branch = (node.get("defaultBranchRef") or {})
    commit = branch.get("target") or {}
    suites = ((commit.get("checkSuites") or {}).get("nodes")) or []
    runs = []
    for suite in suites:
        flow = suite.get("workflowRun") if isinstance(suite, dict) else None
        if not isinstance(flow, dict) or flow.get("databaseId") is None:      # a check suite of an app that is not a workflow of Actions
            continue
        workflow = flow.get("workflow") or {}
        status = str(suite.get("status") or "").lower()
        conclusion = str(suite.get("conclusion") or "").lower() or None
        runs.append({
            "repo": repo, "id": flow["databaseId"], "name": workflow.get("name") or "", "title": "", "event": str(flow.get("event") or "").lower(), "branch": branch.get("name"),
            "path": str(workflow.get("resourcePath") or "").rsplit("/", 1)[-1], "sha": str(commit.get("oid") or "")[:7], "actor": "", "status": status,
            "number": flow.get("runNumber"), "queued": None, "conclusion": conclusion if status == "completed" else None, "started": suite.get("createdAt"),
            "seconds": None, "url": flow.get("url"), "attempt": None,
        })
    return runs


def parse(answer, repos):
    """{repo: [runs]} for the repositories the answer carries; a repository that came back null (no access, no Actions, no commit) is missing so that the caller reads it through REST."""
    data = (answer or {}).get("data") if isinstance(answer, dict) else None
    out = {}
    if not isinstance(data, dict):
        return out
    for index, repo in enumerate(repos):
        node = data.get(f"r{index}")
        if isinstance(node, dict) and node.get("defaultBranchRef"):
            out[repo] = _runs(repo, node)
    return out


def cost_of(answer):
    """The points that a batch cost, from its own rateLimit block (0 when it is not there)."""
    limit = ((answer or {}).get("data") or {}).get("rateLimit") if isinstance(answer, dict) else None
    cost = (limit or {}).get("cost") if isinstance(limit, dict) else None
    return cost if isinstance(cost, int) and not isinstance(cost, bool) else 0


def read_batches(owner, repos, batch, call):
    """Reads `repos` in batches through `call(query_text)` (it returns the decoded JSON answer or raises). Returns ({repo: runs}, [repos to read through REST]). A batch that fails is not
    retried here: its repositories are read through REST and the failure is counted."""
    found, rest = {}, []
    names = [r for r in repos if NAME_RE.match(str(r))]
    rest.extend(r for r in repos if r not in names)
    for start in range(0, len(names), batch):
        chunk = names[start:start + batch]
        try:
            answer = call(query(owner, chunk))
        except Exception:      # noqa: BLE001 - any failure (rate limit, access, network) sends the batch to REST
            STATS["errors"] += 1
            STATS["fallbacks"] += len(chunk)
            rest.extend(chunk)
            continue
        STATS["calls"] += 1
        STATS["cost"] += cost_of(answer)
        got = parse(answer, chunk)
        STATS["repos"] += len(got)
        found.update(got)
        missing = [r for r in chunk if r not in got]
        STATS["fallbacks"] += len(missing)
        rest.extend(missing)
    return found, rest
