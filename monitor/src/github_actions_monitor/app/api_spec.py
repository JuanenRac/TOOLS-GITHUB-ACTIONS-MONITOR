# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The OpenAPI description of the whole read API, built from the frozen contract (docs/schemas/api_contract.json) and never written by hand.

  load()                   the contract of the folder of the product (None when the file is not there: a copy without docs/)
  document(version, ...)   the OpenAPI 3.0.3 document: every frozen route under `/api/v1/`, with the keys and the types the contract promises; the routes that are not frozen appear only when
                           `experimental` is true, each one marked `x-experimental`
  contract_suite()         the module of tools/api_contract_suite.py (None in a copy without tools/): the one suite that the command line, the MCP server and tools/check_api_contract.py all run
  experimental(path, c)    whether a route (without the prefix) is one of those that are not frozen: under `/api/v1/` they answer 404 unless `api.experimental_routes` is on

The three routes of the prefix (me, repos, openapi.json) keep the detailed description of api_v1.openapi(); the contract only adds what they do not say. Nothing here talks to the network or the clock."""
import json
import re

from github_actions_monitor.app import api_v1
from github_actions_monitor.util.paths import ROOT

CONTRACT_FILE = ROOT / "docs" / "schemas" / "api_contract.json"
SCALARS = {"bool": {"type": "boolean"}, "int": {"type": "integer"}, "number": {"type": "number"}, "str": {"type": "string"}, "list": {"type": "array", "items": {}},
           "object": {"type": "object"}, "any": {"nullable": True}}
FED_ITEM = re.compile(r"^/api/repos/\{owner\}/[^/{}]+/health\Z")
_CACHE = {}


def load():
    """The contract as data, read once; None when the file is missing or broken."""
    if "contract" not in _CACHE:
        try:
            _CACHE["contract"] = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE["contract"] = None
    return _CACHE["contract"]


def contract_suite():
    """The contract suite for clients as a module, loaded once from the folder of the product; None when the file is not there. It has no state of its own: `module.run(module.Client(url, token))`."""
    if "suite" not in _CACHE:
        import importlib.util
        path = ROOT / "tools" / "api_contract_suite.py"
        module = None
        if path.is_file():
            spec = importlib.util.spec_from_file_location("api_contract_suite", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        _CACHE["suite"] = module
    return _CACHE["suite"]


def suite_summary(report):
    """The same JSON for the command line and the MCP tool: {ok, checks, failed, rows}."""
    failed = report.failed
    return {"ok": not failed, "checks": len(report.rows), "failed": len(failed), "rows": report.rows}


def schema_of(keys):
    """The JSON schema of a described shape: {key: type} with a nested object for a nested dict and a one-element list for the elements of a list."""
    if isinstance(keys, dict):
        props = {name: schema_of(kind) for name, kind in keys.items()}
        return {"type": "object", "required": sorted(keys), "properties": props}
    if isinstance(keys, list):
        return {"type": "array", "items": schema_of(keys[0]) if keys else {}}
    return dict(SCALARS.get(keys, {}))


def _split(path):
    """('/api/help/topic', {'id': 'readme'}) for '/api/help/topic?id=readme'."""
    base, _, query = path.partition("?")
    return base, dict(part.partition("=")[::2] for part in query.split("&") if part)


def prefixed(path):
    """The route under the prefix: /api/health -> /api/v1/health."""
    return api_v1.PREFIX + path[len("/api"):]


def _operation_id(path):
    return "get_" + re.sub(r"[^a-z0-9]+", "_", path[len(api_v1.PREFIX):].lower()).strip("_") if path != api_v1.PREFIX else "get_root"


def _operation(path, params, keys, extra, summary):
    operation = {"operationId": _operation_id(path), "summary": summary, "security": [{"cookie": []}, {"access": []}],
                 "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": schema_of(keys)}}} if isinstance(keys, (dict, list)) else {"description": "ok"},
                               "default": {"$ref": "#/components/responses/Error"}}}
    names = [m for m in re.findall(r"\{(\w+)\}", path)]
    parameters = [{"name": n, "in": "path", "required": True, "schema": {"type": "string"}} for n in names]
    parameters += [{"name": k, "in": "query", "schema": {"type": "string"}, "example": v} for k, v in params.items()]
    if parameters:
        operation["parameters"] = parameters
    operation.update(extra)
    return operation


def experimental(path, contract=None):
    """True when `path` (the route without the prefix, no query) is one of the routes the contract lists as not frozen and is not frozen by another row (`/api/repos/` is not frozen as a prefix, but
    `/api/repos/{owner}/{repo}/health` is)."""
    contract = contract or load()
    if not contract:
        return False
    path = path.split("?")[0]
    if re.fullmatch(r"/api/repos/[^/]+/[^/]+/health", path):
        return False
    for row in contract.get("unfrozen", []):
        mark = row["path"]
        if path == mark or (mark.endswith("/") and path.startswith(mark)):
            return True
    return False


def frozen_paths(contract=None):
    """{route under the prefix: (the contract row, 'endpoints' | 'fed')} of every frozen route that answers 200 with a shape (the routes that need data are the `fed` ones)."""
    contract = contract or load()
    found = {}
    for row in (contract or {}).get("endpoints", []):
        base, _ = _split(row["path"])
        found.setdefault(prefixed(base), (row, "endpoints"))
    for row in (contract or {}).get("fed_endpoints", []):
        base, _ = _split(row["path"])
        if FED_ITEM.match(base):
            base = "/api/repos/{owner}/{repo}/health"
        found.setdefault(prefixed(base), (row, "fed"))
    return found


def document(version, contract=None, experimental_routes=False):
    """The OpenAPI document. `version` = the version of the monitor; the version of the contract is `info.x-contract-version`."""
    contract = contract or load() or {"endpoints": [], "fed_endpoints": [], "unfrozen": [], "errors": []}
    base = api_v1.openapi(version)
    paths = {}
    for path, (row, kind) in sorted(frozen_paths(contract).items()):
        if path in base["paths"]:
            continue
        query = _split(row["path"])[1]
        keys = row["complete"] if kind == "endpoints" else row["keys"]
        extra = {}
        if kind == "endpoints" and isinstance(row.get("lite"), int):
            extra["x-lite"] = row["lite"]
        elif kind == "endpoints":
            extra["x-lite"] = "same"
        if row.get("local_only"):
            extra["x-local-only"] = True
        if kind == "fed":
            extra["x-needs-data"] = True
        status = keys if isinstance(keys, int) else None
        operation = _operation(path, query, None if status else keys, extra, "Read " + path[len(api_v1.PREFIX):])
        if status:      # a route that answers with a fixed status in the complete edition (for example 404 where it does not exist)
            operation["responses"] = {str(status): {"description": "fixed answer"}, "default": {"$ref": "#/components/responses/Error"}}
        paths[path] = {"get": operation}
    paths.update(base["paths"])
    paths["/api/v1/openapi.json"] = {"get": {"operationId": "get_openapi", "summary": "This document", "security": [{"cookie": []}, {"access": []}],
                                             "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": {"type": "object", "required": ["openapi", "info", "paths", "components"]}}}},
                                                           "default": {"$ref": "#/components/responses/Error"}}}}
    if experimental_routes:
        for row in contract.get("unfrozen", []):
            mark = row["path"]
            if mark.endswith("/") or prefixed(mark) in paths:
                continue
            operation = _operation(prefixed(mark), {}, None, {"x-experimental": True, "x-reason": row["reason"]}, "Read " + prefixed(mark)[len(api_v1.PREFIX):])
            paths[prefixed(mark)] = {"get": operation}
    components = base["components"]
    components["responses"] = {"Error": {"description": "error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}}
    info = {**base["info"], "version": version, "x-contract-version": api_v1.CONTRACT_VERSION,
            "description": "Read only. Every route here is frozen: a key may be added, never removed or renamed. Routes marked x-experimental are not frozen."}
    return {"openapi": base["openapi"], "info": info, "paths": dict(sorted(paths.items())), "components": components}
