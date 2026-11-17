#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E1 - the basic start: the image starts as a service, becomes healthy by its own health check, and the API inside the container keeps its contract on the published port."""
import sys

import audit_lib as lib


def body(s):
    image = s.image()
    s.base_digests("python:3.13-slim")
    mounts, env, _token = s.login_files()
    config, data = s.volume("config"), s.volume("data")
    volumes = ["%s:/config" % config, "%s:/data" % data] + mounts
    name, code, out = s.service("monitor", image, volumes, env, ports=["127.0.0.1:8765:8765"])
    if not s.check("the container starts", code == 0, out):
        return
    s.check("it becomes healthy through its own health check", s.wait_healthy(name, 180), s.logs(name)[-1500:])
    token = s.read_token(name)
    s.check("the access token was made on the first start and is in /data/state/access_token", len(token) >= 16, "length %d" % len(token))

    # the health check of the image is the deep one, as the Dockerfile says
    _c, inspect = s.docker("inspect", "-f", "{{json .Config.Healthcheck.Test}}|{{.Config.User}}|{{json .Config.Volumes}}|{{json .Config.ExposedPorts}}", name)
    s.check("the image declares the deep health check, the user 10001 and the two volumes", "cli.healthcheck" in inspect and "10001" in inspect and "/config" in inspect and "/data" in inspect, inspect)

    refused = lib.http_request(8765, "GET", "/api/health", {"Host": "127.0.0.1:8765"})
    s.check("without the access token a request is refused (401 or 403)", refused["status"] in (401, 403), "%s %s" % (refused["status"], refused["body"][:200]))
    auth = {"Host": "127.0.0.1:8765", "X-Monitor-Access": token}
    ok = lib.http_request(8765, "GET", "/api/health", auth)
    answer = lib.jbody(ok) or {}
    s.check("with the token /api/health answers ok", ok["status"] == 200 and answer.get("ok") is True, "%s %s" % (ok["status"], ok["body"][:300]))
    deep = lib.http_request(8765, "GET", "/api/health?deep=1", auth)
    s.check("the deep health check answers 200", deep["status"] == 200, "%s %s" % (deep["status"], deep["body"][:300]))
    alien = lib.http_request(8765, "GET", "/api/health", {"Host": "other.example", "X-Monitor-Access": token})
    s.check("a request with a Host that is not the monitor's own is refused (403)", alien["status"] == 403, "%s %s" % (alien["status"], alien["body"][:200]))
    s.note("GET /api/health in the container answers: %s" % ok["body"][:300])
    about = lib.http_request(8765, "GET", "/api/about", auth)
    s.note("version the container reports in /api/about: %s" % (lib.jbody(about) or {}).get("version"))

    # the frozen contract of the read endpoints, from this machine against the published port, with the script of the version under check
    script = s.target / "monitor" / "tools" / "check_api_contract.py"
    tokenfile = s.file("contract_token", token, 0o600)
    if script.is_file():
        code, out = s.run([sys.executable, "-I", str(script), "--url", "http://127.0.0.1:8765", "--token-file", str(tokenfile)], timeout=300, label="check_api_contract.py against the published port")
        s.check("the contract of the API holds on the published port (CONTRACT=PASS)", code == 0 and "CONTRACT=PASS" in out, out[-1500:])
    else:
        s.note("this version has no tools/check_api_contract.py: the contract is not checked")
    # and from inside, on the second port that only listens on loopback (what `docker exec` uses)
    code, out = s.docker("exec", "-e", "MONITOR_ACCESS_TOKEN=" + token, name, "python", "/app/tools/check_api_contract.py", "--url", "http://127.0.0.1:8766", "--token-file", "/data/state/access_token",
                         label="check_api_contract.py inside the container (second port)")
    s.check("the same contract holds inside the container (CONTRACT=PASS)", code == 0 and "CONTRACT=PASS" in out, out[-1500:])

    logs = s.logs(name)
    s.check("the log has no traceback", "Traceback" not in logs, logs[-1500:])
    s.check("the token is not in the log", token not in logs, "")
    s.check("the container is still healthy at the end", s.health(name) == "healthy", s.health(name))


if __name__ == "__main__":
    sys.exit(lib.main_of("E1", "Basic start, health check and API contract inside the container", body))
