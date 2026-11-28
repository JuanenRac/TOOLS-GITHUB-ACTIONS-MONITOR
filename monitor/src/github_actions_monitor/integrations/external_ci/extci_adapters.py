# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One adapter per service. Each gives runs in the shape of a run of Actions (RunLike), with `source` = "external:<kind>"; every state of a service maps to a conclusion or to "unknown", which never decides.
Links are built here from the address of the configuration: a link that comes in an answer is never followed nor shown."""
import calendar
import time
import urllib.parse

from github_actions_monitor.integrations.external_ci.extci_fetch import Failed

EXPERIMENTAL = ("jenkins", "azure")      # no real server has been read yet: the label stays until one has
REQUIRED = {"buildbot": (), "gitlab": ("project",), "jenkins": ("job",), "azure": ("project",)}
PER_BUILD = 10


def iso(seconds):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds)) if isinstance(seconds, (int, float)) and seconds > 0 else ""


def epoch(text):
    try:
        return calendar.timegm(time.strptime(str(text)[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return 0


def _rows(value, key=None):
    if key is not None:
        value = value.get(key) if isinstance(value, dict) else None
    if not isinstance(value, list):
        raise Failed("not_json")
    return [row for row in value if isinstance(row, dict)]


def _text(value, limit=120):
    return "".join(c for c in str(value or "") if c.isprintable())[:limit]


def _id(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def run(source, workflow, number, status, conclusion, branch, started, ended=0, event="push", url="", sha="", ref=None):
    return {"repo": source["repo"], "name": _text(workflow), "path": _text(workflow), "branch": _text(branch) or None, "event": event, "status": status, "conclusion": conclusion, "id": number,
            "started": iso(started), "seconds": int(ended - started) if ended and started and ended >= started else None, "queued": 0, "url": url, "sha": _text(sha, 40), "source": "external:" + source["kind"], "ref": ref}


def buildbot(reader, source, cfg):
    results = {0: "success", 1: "success", 2: "failure", 3: "skipped", 4: "failure", 5: "neutral", 6: "cancelled"}
    wanted = [b for b in source.get("builders", "").split("+") if b]
    limit = cfg["buildbot"]["max_builders"]
    builders = _rows(reader.json(f"/api/v2/builders?limit={500 if wanted else limit}"), "builders")
    names = {_text(b.get("name")): _id(b.get("builderid")) for b in builders}
    missing = [w for w in wanted if w not in names]
    chosen = [w for w in wanted if w in names] if wanted else list(names)
    out = []
    for name in chosen[:limit]:
        builder = names[name]
        for build in _rows(reader.json(f"/api/v2/builders/{builder}/builds?order=-number&limit={PER_BUILD}&property=branch"), "builds"):
            props = build.get("properties")
            branch = (props.get("branch") or [""])[0] if isinstance(props, dict) else ""
            done = build.get("complete") is True
            out.append(run(source, name, _id(build.get("number")), "completed" if done else "in_progress", results.get(build.get("results"), "unknown") if done else None, branch, build.get("started_at") or 0,
                           build.get("complete_at") or 0, url=reader.url(f"/#/builders/{builder}/builds/{_id(build.get('number'))}"), ref=_id(build.get("buildid"))))
    return out, ["builder:" + m for m in missing]


def _project(source):
    return urllib.parse.quote(urllib.parse.unquote(source["project"]), safe="")


def gitlab(reader, source, cfg):
    table = {"success": ("completed", "success"), "failed": ("completed", "failure"), "canceled": ("completed", "cancelled"), "skipped": ("completed", "skipped"), "manual": ("waiting", None),
             "created": ("queued", None), "pending": ("queued", None), "waiting_for_resource": ("queued", None), "preparing": ("queued", None), "scheduled": ("queued", None), "running": ("in_progress", None),
             "canceling": ("in_progress", None), "waiting_for_callback": ("in_progress", None)}
    events = {"push": "push", "schedule": "schedule", "web": "workflow_dispatch", "api": "workflow_dispatch", "trigger": "workflow_dispatch", "pipeline": "workflow_run", "parent_pipeline": "workflow_run",
              "merge_request_event": "pull_request", "external_pull_request_event": "pull_request"}
    ref = "&ref=" + urllib.parse.quote(source["branch"], safe="") if source.get("branch") else ""
    project = _project(source)
    page = "/".join(urllib.parse.quote(p, safe="") for p in urllib.parse.unquote(source["project"]).split("/"))
    out = []
    for row in _rows(reader.json(f"/api/v4/projects/{project}/pipelines?per_page={min(100, cfg['gitlab']['max_pipelines'])}{ref}")):
        status, conclusion = table.get(row.get("status"), ("completed", "unknown"))
        number = _id(row.get("id"))
        out.append(run(source, "pipeline", number, status, conclusion, row.get("ref"), epoch(row.get("created_at")), epoch(row.get("updated_at")), events.get(row.get("source"), "other"),
                       reader.url(f"/{page}/-/pipelines/{number}"), row.get("sha"), number))
    return out, []


def _job_path(source):
    return "".join("/job/" + urllib.parse.quote(urllib.parse.unquote(p), safe="") for p in source["job"].split("/") if p)


def jenkins(reader, source, cfg):
    table = {"SUCCESS": "success", "UNSTABLE": "failure", "FAILURE": "failure", "ABORTED": "cancelled", "NOT_BUILT": "skipped"}
    path = _job_path(source)
    name = urllib.parse.unquote(source["job"])
    out = []
    for row in _rows(reader.json(path + "/api/json?tree=builds[number,result,building,timestamp,duration]%7B0,10%7D"), "builds"):
        number = _id(row.get("number"))
        start = row["timestamp"] / 1000 if isinstance(row.get("timestamp"), (int, float)) else 0
        length = row["duration"] / 1000 if isinstance(row.get("duration"), (int, float)) else 0
        building = row.get("building") is True
        out.append(run(source, name, number, "in_progress" if building else "completed", None if building else table.get(row.get("result"), "unknown"), source.get("branch"), start,
                       start + length if length else 0, url=reader.url(f"{path}/{number}/"), ref=number))
    return out, []


def azure(reader, source, cfg):
    results = {"succeeded": "success", "partiallySucceeded": "failure", "failed": "failure", "canceled": "cancelled"}
    events = {"individualCI": "push", "batchedCI": "push", "schedule": "schedule", "manual": "workflow_dispatch", "pullRequest": "pull_request", "buildCompletion": "workflow_run"}
    project = _project(source)
    out = []
    for row in _rows(reader.json(f"/{project}/_apis/build/builds?api-version=7.0&$top=50&queryOrder=queueTimeDescending"), "value"):
        number = _id(row.get("id"))
        status = {"completed": "completed", "inProgress": "in_progress", "cancelling": "in_progress"}.get(row.get("status"), "queued")
        branch = str(row.get("sourceBranch") or "")
        branch = branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else branch
        definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
        out.append(run(source, definition.get("name") or "build", number, status, results.get(row.get("result"), "unknown") if status == "completed" else None, branch,
                       epoch(row.get("startTime") or row.get("queueTime")), epoch(row.get("finishTime")), events.get(row.get("reason"), "other"),
                       reader.url(f"/{project}/_build/results?buildId={number}"), row.get("sourceVersion"), number))
    return out, []


ADAPTERS = {"buildbot": buildbot, "gitlab": gitlab, "jenkins": jenkins, "azure": azure}


def _azure_failed_log(reader, build):
    """The log of the first step that failed, from the timeline of the build; 0 when it does not say (the last log is the closing of the job, not the failure)."""
    try:
        records = _rows(reader.json(f"{build}/timeline?api-version=7.0"), "records")
    except Failed:
        return 0
    for row in records:
        log = row.get("log")
        if row.get("type") == "Task" and row.get("result") == "failed" and isinstance(log, dict) and _id(log.get("id")):
            return _id(log.get("id"))
    return 0


def log_tail(reader, source, run_row, keep):
    """(text, cut) of the end of the log of a failed build. Only asked for when external_ci.logs.enabled."""
    kind, ref = source["kind"], _id(run_row.get("ref"))
    if kind == "jenkins":
        return reader.tail(f"{_job_path(source)}/{ref}/consoleText", keep)
    if kind == "gitlab":
        jobs = _rows(reader.json(f"/api/v4/projects/{_project(source)}/pipelines/{ref}/jobs?scope%5B%5D=failed&per_page=5"))
        if not jobs:
            return "", False
        job = next((j for j in jobs if j.get("allow_failure") is not True), jobs[0])      # a job that may fail is not why the pipeline is red
        return reader.tail(f"/api/v4/projects/{_project(source)}/jobs/{_id(job.get('id'))}/trace", keep)
    if kind == "azure":
        build = f"/{_project(source)}/_apis/build/builds/{ref}"
        number = _azure_failed_log(reader, build)
        if not number:
            logs = _rows(reader.json(f"{build}/logs?api-version=7.0"), "value")
            if not logs:
                return "", False
            number = _id(logs[-1].get("id"))
        return reader.tail(f"{build}/logs/{number}?api-version=7.0", keep)
    failed = [s for s in _rows(reader.json(f"/api/v2/builds/{ref}/steps"), "steps") if s.get("results") in (2, 4)]
    if not failed:
        return "", False
    logs = _rows(reader.json(f"/api/v2/steps/{_id(failed[0].get('stepid'))}/logs"), "logs")
    if not logs:
        return "", False
    log = next((row for row in logs if row.get("slug") == "stdio"), logs[0])
    lines = _id(log.get("num_lines"))
    chunks = _rows(reader.json(f"/api/v2/logs/{_id(log.get('logid'))}/contents?offset={max(0, lines - 400)}&limit=400"), "logchunks")
    text = "".join(str(c.get("content") or "") for c in chunks)
    if log.get("type") == "s":      # in a stdio log every line starts with the letter of its channel (o, e, h)
        text = "".join(line[1:] for line in text.splitlines(True))
    return text[-keep:], lines > 400 or len(text) > keep
