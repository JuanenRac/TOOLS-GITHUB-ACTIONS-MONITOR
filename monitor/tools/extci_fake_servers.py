# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Fake Buildbot, GitLab CI, Jenkins and Azure Pipelines on 127.0.0.1, with answers written by hand and invented names, for the tests and to try the page without a real service.

  py -3 tools/extci_fake_servers.py [--port 8790]

The failure cases are paths of their own under /fail/<case>: 404, 429, 500, broken (JSON that does not parse), redirect, html, huge."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

LOG = "\x1b[31mstep one\x1b[0m\nstep two\n\x1b]0;title\x07FAILED: the answer was 41\n"


def _builds():
    return [{"buildid": 902, "number": 8, "complete": True, "results": 2, "started_at": 1760000600, "complete_at": 1760000700, "properties": {"branch": ["main", "x"]}},
            {"buildid": 901, "number": 7, "complete": True, "results": 0, "started_at": 1760000000, "complete_at": 1760000100, "properties": {"branch": ["main", "x"]}}]


def answers():
    """{path without the query: (content type, body)}."""
    j = "application/json"
    return {
        "/api/v2/builders": (j, {"builders": [{"builderid": 1, "name": "linux"}, {"builderid": 2, "name": "docs"}]}),
        "/api/v2/builders/1/builds": (j, {"builds": _builds()}),
        "/api/v2/builders/2/builds": (j, {"builds": [{"buildid": 911, "number": 3, "complete": True, "results": 0, "started_at": 1760000000, "complete_at": 1760000050, "properties": {"branch": ["main", "x"]}}]}),
        "/api/v2/builds/902/steps": (j, {"steps": [{"stepid": 5, "results": 2}]}),
        "/api/v2/steps/5/logs": (j, {"logs": [{"logid": 6, "num_lines": 3, "slug": "stdio", "type": "s"}]}),
        "/api/v2/logs/6/contents": (j, {"logchunks": [{"content": "".join("o" + line for line in LOG.splitlines(True))}]}),
        "/api/v4/projects/group%2Fapp/pipelines": (j, [{"id": 31, "status": "failed", "ref": "main", "source": "push", "sha": "abc", "created_at": "2026-01-02T10:00:00Z", "updated_at": "2026-01-02T10:05:00Z"},
                                                       {"id": 30, "status": "failed", "ref": "topic", "source": "merge_request_event", "created_at": "2026-01-02T09:00:00Z"},
                                                       {"id": 29, "status": "success", "ref": "main", "source": "push", "created_at": "2026-01-01T10:00:00Z"},
                                                       {"id": 28, "status": "somethingnew", "ref": "main", "source": "push", "created_at": "2026-01-03T10:00:00Z"}]),
        "/api/v4/projects/group%2Fapp/pipelines/31/jobs": (j, [{"id": 76, "allow_failure": True}, {"id": 77, "allow_failure": False}]),
        "/api/v4/projects/group%2Fapp/jobs/77/trace": ("text/plain", LOG),
        "/job/folder/job/app/api/json": (j, {"builds": [{"number": 12, "result": "FAILURE", "building": False, "timestamp": 1760000000000, "duration": 60000}, {"number": 11, "result": "SUCCESS", "timestamp": 1759990000000}]}),
        "/job/folder/job/app/12/consoleText": ("text/plain", LOG),
        "/proj/_apis/build/builds": (j, {"value": [{"id": 55, "status": "completed", "result": "failed", "sourceBranch": "refs/heads/main", "reason": "individualCI", "definition": {"name": "ci"},
                                                    "startTime": "2026-01-02T10:00:00Z", "finishTime": "2026-01-02T10:03:00Z"}]}),
        "/proj/_apis/build/builds/55/logs": (j, {"value": [{"id": 1}, {"id": 2}]}),
        "/proj/_apis/build/builds/55/logs/2": ("text/plain", "Finishing the job\n"),
        "/proj/_apis/build/builds/55/timeline": (j, {"records": [{"type": "Job", "result": "failed", "log": {"id": 2}}, {"type": "Task", "result": "failed", "log": {"id": 1}}]}),
        "/proj/_apis/build/builds/55/logs/1": ("text/plain", LOG),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code, kind="application/json", body=b"{}", headers=None):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):      # noqa: N802 - the name http.server asks for
        path = self.path.partition("?")[0]
        self.server.seen.append((path, dict(self.headers)))
        if path.startswith("/fail/"):
            case = path.split("/")[2]
            if case in ("404", "429", "500"):
                self.send(int(case))
            elif case == "redirect":
                self.send(302, headers={"Location": "http://192.0.2.1/elsewhere"})
            elif case == "html":
                self.send(200, "text/html", b"<html></html>")
            elif case == "huge":
                self.send(200, body=b"[" + b"1," * 200000 + b"1]")
            else:
                self.send(200, body=b"{not json")
            return
        if path == "/signin":      # Azure DevOps answers a refused token with 203 and a sign-in page
            self.send(203, "text/html", b"<html></html>")
            return
        found = answers().get(path) or answers().get(unquote(path))
        if found is None:
            self.send(404)
            return
        kind, body = found
        if self.headers.get("If-None-Match") == '"v1"':
            self.send(304)
            return
        self.send(200, kind, (body if isinstance(body, str) else json.dumps(body)).encode("utf-8"), {"ETag": '"v1"'})


def start(port=0):
    """A server on 127.0.0.1 in a thread: (server, base address). `server.seen` lists (path, headers) of the requests."""
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.seen = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def sources(base):
    """One source line of each kind that points at the fake server."""
    return [f"buildbot;repo=mirror-bb;url={base}", f"gitlab;repo=mirror-gl;url={base};project=group/app", f"jenkins;repo=mirror-jk;url={base};job=folder/app;branch=main", f"azure;repo=mirror-az;url={base};project=proj"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args(argv)
    server, base = start(args.port)
    print("\n".join(sources(base)))
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
