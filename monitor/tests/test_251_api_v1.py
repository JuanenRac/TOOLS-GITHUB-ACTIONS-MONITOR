# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The read API under /api/v1/: off by default, read only, the old routes under the new prefix, and the three own routes (me, repos, openapi.json) with one error envelope, signed cursors and
compact answers. The rules are tested as functions and then against a real server of each edition."""
import gzip
import json
import time
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
import check_api_contract as contract_tool
from github_actions_monitor import i18n
from github_actions_monitor.app import actions_monitor, api_v1, settings_api
from test_200_contract import Served

HERE = Path(__file__).resolve().parent.parent
CONTRACT = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
SECRET = b"s" * 32
CFG = api_v1.settings({})
ON = {"api": {"v1_enabled": True}}

# the floor of the frozen shape of the two routes: a later version may add keys, never take one of these away
FLOOR = {"/api/v1/me": {"schema": "int", "api_version": "str", "version": "str", "edition": "str", "mode": "str", "authenticated": "bool", "user": "any", "role": "any", "accounts": "any", "limits": "object"},
         "/api/v1/repos": {"schema": "int", "api_version": "str", "total": "int", "limit": "int", "next_cursor": "any", "items": "list"}}


def view(name, state="ok", eco="HYDRA"):
    return {"repo": name, "ecosystem": eco, "state": state, "risk": 3, "ci": {"runs_24h": 4, "failures_24h": 1, "red_workflows": ["a"], "stuck_runs": 0}, "alerts": {"total": 2}, "activity": {"last_run_at": "2026-01-01T00:00:00Z"}}


VIEWS = [view("repo%03d" % n, "bad" if n % 10 == 0 else "ok", "HYDRA" if n % 2 else "ARMOR") for n in range(120)]


class TheRules(unittest.TestCase):
    def test_it_is_automatic_by_default_and_the_values_are_bounded(self):
        self.assertEqual(CFG["v1_enabled"], "auto")
        for old, new in ((True, "on"), (False, "off"), ("on", "on"), ("off", "off"), ("auto", "auto"), ("maybe", "auto"), (1, "auto"), (None, "auto")):      # the old true / false keep their meaning
            self.assertEqual(api_v1.settings({"api": {"v1_enabled": old}})["v1_enabled"], new, old)
        bad = api_v1.settings({"api": {"v1_enabled": "yes", "default_limit": 0, "max_limit": True, "cursor_ttl_seconds": 5, "gzip_min_bytes": -1}})
        self.assertEqual(bad, CFG)
        self.assertEqual(api_v1.settings({"api": {"default_limit": 500, "max_limit": 100}})["default_limit"], 100)      # the default never passes the ceiling

    def test_auto_is_on_in_the_service_mode_only(self):
        for mode, service, want in (("auto", True, True), ("auto", False, False), ("on", False, True), ("on", True, True), ("off", True, False), ("off", False, False)):
            self.assertEqual(api_v1.enabled({"v1_enabled": mode}, service), want, (mode, service))

    def test_the_capabilities_follow_the_role_and_v1_never_writes(self):
        self.assertEqual(api_v1.capabilities("individual", None), {"read": True, "write": True, "admin": True, "v1_write": False})
        self.assertEqual(api_v1.capabilities("team", "viewer"), {"read": True, "write": False, "admin": False, "v1_write": False})
        self.assertEqual(api_v1.capabilities("team", "maintainer"), {"read": True, "write": True, "admin": False, "v1_write": False})
        self.assertEqual(api_v1.capabilities("team", "admin"), {"read": True, "write": True, "admin": True, "v1_write": False})
        self.assertEqual(api_v1.capabilities("team", None), {"read": True, "write": False, "admin": False, "v1_write": False})      # a team session without a known role gets the least

    def test_the_program_defaults_and_the_example_file_are_the_same_as_the_module(self):
        self.assertEqual(actions_monitor.DEFAULTS["api"], api_v1.DEFAULTS)
        self.assertIs(api_v1.DEFAULTS["experimental_routes"], False)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["api"], api_v1.DEFAULTS)

    def test_the_old_route_is_found_under_the_prefix(self):
        self.assertEqual(api_v1.route_of("/api/v1/alerts"), ("1", "/api/alerts"))
        self.assertEqual(api_v1.route_of("/api/v1/team/health"), ("1", "/api/team/health"))
        self.assertEqual(api_v1.route_of("/api/v2/alerts"), ("2", "/api/alerts"))
        self.assertEqual(api_v1.route_of("/api/alerts"), (None, "/api/alerts"))
        self.assertEqual(api_v1.route_of("/api/version"), (None, "/api/version"))
        self.assertEqual(api_v1.route_of("/api/v1x/alerts"), (None, "/api/v1x/alerts"))

    def test_the_envelope_has_a_stable_code_and_a_message_in_the_language_in_use(self):
        status, body = api_v1.ApiError(400, "api.bad_limit", max=200).envelope()
        self.assertEqual((status, body["error"], body["code"]), (400, "bad_request", "api.bad_limit"))
        self.assertIn("200", body["message"])
        with i18n.use_language("es"):
            self.assertIn("entero", api_v1.ApiError(400, "api.bad_limit", max=200).envelope()[1]["message"])
        self.assertEqual(api_v1.ApiError(418, "api.x").envelope()[0], 500)


class ThePaging(unittest.TestCase):
    def pages(self, **ask):
        seen, cursor, count = [], None, 0
        while True:
            body = api_v1.repos_payload(VIEWS, dict(ask, **({"cursor": cursor} if cursor else {})), secret=SECRET, now=1000, cfg=CFG)
            seen += [i["repo"] for i in body["items"]]
            count += 1
            cursor = body["next_cursor"]
            if not cursor:
                return seen, count

    def test_every_repository_comes_once_and_in_order(self):
        seen, count = self.pages(limit="50")
        self.assertEqual(seen, sorted(v["repo"] for v in VIEWS))
        self.assertEqual(count, 3)

    def test_a_filter_keeps_its_own_pages_and_the_total_is_of_the_filter(self):
        body = api_v1.repos_payload(VIEWS, {"state": "bad", "limit": "5"}, secret=SECRET, now=1000, cfg=CFG)
        self.assertEqual((body["total"], len(body["items"])), (12, 5))
        self.assertTrue(all(i["state"] == "bad" for i in body["items"]))
        seen, _ = self.pages(state="bad", limit="5")
        self.assertEqual(len(seen), 12)
        self.assertEqual(api_v1.repos_payload(VIEWS, {"q": "REPO01"}, secret=SECRET, now=1000, cfg=CFG)["total"], 10)

    def test_a_cursor_of_another_query_a_forged_one_and_an_old_one_are_refused(self):
        first = api_v1.repos_payload(VIEWS, {"limit": "10"}, secret=SECRET, now=1000, cfg=CFG)["next_cursor"]
        for ask, now, secret in (({"limit": "10", "state": "bad", "cursor": first}, 1000, SECRET), ({"cursor": first + "x"}, 1000, SECRET), ({"cursor": first}, 1000 + 901, SECRET),
                                 ({"cursor": first}, 1000, b"t" * 32), ({"cursor": "nonsense"}, 1000, SECRET), ({"cursor": "a." * 400}, 1000, SECRET)):
            with self.assertRaises(api_v1.ApiError) as raised:
                api_v1.repos_payload(VIEWS, ask, secret=secret, now=now, cfg=CFG)
            self.assertEqual((raised.exception.status, raised.exception.code), (400, "api.bad_cursor"), ask)
        ok = api_v1.repos_payload(VIEWS, {"cursor": first, "limit": "10"}, secret=SECRET, now=1000 + 899, cfg=CFG)
        self.assertEqual(ok["items"][0]["repo"], "repo010")

    def test_a_new_repository_between_two_pages_never_repeats_or_shifts_one(self):
        first = api_v1.repos_payload(VIEWS, {"limit": "10"}, secret=SECRET, now=1000, cfg=CFG)
        grown = [view("repo000a")] + VIEWS      # sorts inside the first page, already read
        second = api_v1.repos_payload(grown, {"limit": "10", "cursor": first["next_cursor"]}, secret=SECRET, now=1000, cfg=CFG)
        self.assertEqual([i["repo"] for i in second["items"]], ["repo%03d" % n for n in range(10, 20)])

    def test_the_limit_has_a_default_and_a_ceiling(self):
        self.assertEqual(api_v1.repos_payload(VIEWS, {}, secret=SECRET, now=1, cfg=CFG)["limit"], 50)
        for bad in ("0", "201", "-1", "x", "1.5"):
            with self.assertRaises(api_v1.ApiError) as raised:
                api_v1.repos_payload(VIEWS, {"limit": bad}, secret=SECRET, now=1, cfg=CFG)
            self.assertEqual(raised.exception.code, "api.bad_limit", bad)

    def test_fields_and_the_compact_profile_cut_the_lines(self):
        line = api_v1.repos_payload(VIEWS, {"fields": "repo,state", "limit": "1"}, secret=SECRET, now=1, cfg=CFG)["items"][0]
        self.assertEqual(sorted(line), ["repo", "state"])
        self.assertEqual(sorted(api_v1.repos_payload(VIEWS, {"profile": "compact", "limit": "1"}, secret=SECRET, now=1, cfg=CFG)["items"][0]), sorted(api_v1.CONTRACT["repos"]["compact"]))
        for ask, code in (({"fields": "nope"}, "api.unknown_field"), ({"fields": "Repo"}, "api.unknown_field"), ({"fields": "repo;drop"}, "api.unknown_field"), ({"profile": "huge"}, "api.bad_profile")):
            with self.assertRaises(api_v1.ApiError) as raised:
                api_v1.repos_payload(VIEWS, ask, secret=SECRET, now=1, cfg=CFG)
            self.assertEqual(raised.exception.code, code, ask)

    def test_a_line_carries_what_the_contract_promises(self):
        line = api_v1.repo_item(view("x"))
        self.assertEqual(sorted(line), sorted(api_v1.CONTRACT["repos"]["item"]))
        self.assertEqual((line["red_workflows"], line["alerts"]), (1, 2))
        self.assertEqual(sorted(api_v1.repo_item({"repo": "bare"})), sorted(api_v1.CONTRACT["repos"]["item"]))      # a repository with nothing yet still has every key


class TheCompression(unittest.TestCase):
    def test_gzip_only_when_asked_and_large_enough(self):
        body = b"x" * 5000
        packed, headers = api_v1.maybe_compress(body, "gzip, deflate", 1024)
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(gzip.decompress(packed), body)
        for accept, minimum in ((None, 1024), ("identity", 1024), ("gzip;q=0", 1024), ("gzip", 0), ("gzip", 6000)):
            self.assertEqual(api_v1.maybe_compress(body, accept, minimum)[0], body, (accept, minimum))
        self.assertEqual(api_v1.maybe_compress(body, "gzip", 1024), api_v1.maybe_compress(body, "gzip", 1024))      # the same bytes every time


class TheMe(unittest.TestCase):
    def test_a_team_session_and_the_individual_mode(self):
        team = api_v1.me_payload(version="2", edition="complete", mode="team", authenticated=True, user="ana", role="viewer", accounts=["a1"], cfg=CFG)
        self.assertEqual((team["role"], team["accounts"], team["user"]), ("viewer", ["a1"], "ana"))
        alone = api_v1.me_payload(version="2", edition="complete", mode="individual", authenticated=False, user="", role=None, accounts=None, cfg=CFG)
        self.assertEqual((alone["role"], alone["accounts"], alone["user"]), (None, None, None))
        self.assertEqual(sorted(alone), sorted(api_v1.CONTRACT["me"]["required"]))

    def test_the_openapi_names_the_two_routes_and_the_envelope(self):
        spec = api_v1.openapi("1")
        self.assertEqual(sorted(spec["paths"]), ["/api/v1/me", "/api/v1/repos"])
        self.assertIn("Error", spec["components"]["schemas"])
        self.assertEqual(sorted(spec["components"]["securitySchemes"]), ["access", "cookie"])


class TheServer(unittest.TestCase):
    def serve(self, lite=False, enabled=True):
        served = Served(self, lite=lite)
        patcher = mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=ON if enabled else {})
        patcher.start()
        self.addCleanup(patcher.stop)
        views = mock.patch.object(actions_monitor, "health_views", return_value=VIEWS)
        views.start()
        self.addCleanup(views.stop)
        return served

    def get(self, served, path, headers=None):
        status, raw, answer = served.raw("GET", path, headers)
        try:
            return status, json.loads(gzip.decompress(raw) if answer.getheader("Content-Encoding") == "gzip" else raw), answer
        except ValueError:
            return status, None, answer

    def test_the_whole_prefix_answers_404_while_it_is_off_and_in_the_lite_edition(self):
        for lite, enabled in ((False, False), (True, True)):
            served = self.serve(lite=lite, enabled=enabled)
            for path in ("/api/v1/me", "/api/v1/repos", "/api/v1/openapi.json", "/api/v1/health", "/api/v1/alerts"):
                self.assertEqual(self.get(served, path)[0], 404, (lite, enabled, path))
        self.assertEqual(self.get(self.serve(enabled=False), "/api/health")[0], 200)      # the old routes do not change

    def test_an_old_route_answers_the_same_under_the_prefix_with_the_version_header(self):
        served = self.serve()
        old = self.get(served, "/api/health")
        new = self.get(served, "/api/v1/health")
        self.assertEqual(new[0], 200)
        self.assertEqual(sorted(new[1]), sorted(old[1]))
        self.assertEqual(new[2].getheader("X-API-Version"), "1")
        self.assertIsNone(old[2].getheader("X-API-Version"))
        self.assertEqual(self.get(served, "/api/v1/no-such-route")[0], 404)
        self.assertEqual(self.get(served, "/api/v2/me")[0], 404)

    def test_the_roles_of_an_old_route_apply_under_the_prefix_too(self):
        # the prefix is removed BEFORE the gate, so the role a route needs is the one of the old route (ADMIN_GET stays admin); the gate sees only the old path
        from github_actions_monitor.security import auth
        for path in auth.ADMIN_GET:
            self.assertEqual(auth.required_role("GET", api_v1.route_of("/api/v1/" + path[len("/api/"):])[1]), "admin", path)

    def test_the_frozen_shape_holds_on_a_real_server(self):
        served = self.serve()
        self.assertEqual(contract_tool.check_v1(contract_tool.make_caller(served.url)), [])
        for path, keys in FLOOR.items():
            row = next(r for r in CONTRACT["v1_endpoints"] if r["path"] == path)
            for key, kind in keys.items():
                self.assertEqual(row["keys"].get(key) if not isinstance(row["keys"].get(key), dict) else "object", kind, (path, key))

    def test_auto_follows_the_service_mode_over_http(self):
        served = self.serve(enabled=False)      # the configuration says nothing: "auto"
        self.assertEqual(self.get(served, "/api/v1/me")[0], 404)      # one person at one computer
        with mock.patch.object(actions_monitor, "service_mode", return_value=True):
            status, body, _ = self.get(served, "/api/v1/me")      # the image, the unit, the process of an account
            self.assertEqual((status, body["contract"]), (200, api_v1.CONTRACT_VERSION))
            self.assertEqual(self.get(served, "/api/v1/health")[0], 200)
            with mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={"api": {"v1_enabled": "off"}}):
                self.assertEqual(self.get(served, "/api/v1/me")[0], 404)      # off switches it off in the service mode too

    def test_me_in_the_individual_mode(self):
        status, body, _ = self.get(self.serve(), "/api/v1/me")
        self.assertEqual((status, body["mode"], body["authenticated"], body["role"], body["accounts"]), (200, "individual", False, None, None))

    def test_the_repositories_by_pages_over_http(self):
        served = self.serve()
        status, first, answer = self.get(served, "/api/v1/repos?limit=100&state=bad")
        self.assertEqual((status, first["total"], len(first["items"])), (200, 12, 12))
        status, page, _ = self.get(served, "/api/v1/repos?limit=50")
        names = [i["repo"] for i in page["items"]]
        status, page2, _ = self.get(served, "/api/v1/repos?limit=50&cursor=" + page["next_cursor"])
        names += [i["repo"] for i in page2["items"]]
        self.assertEqual(len(set(names)), 100)
        status, small, _ = self.get(served, "/api/v1/repos?limit=3&profile=compact")
        self.assertEqual(sorted(small["items"][0]), sorted(api_v1.CONTRACT["repos"]["compact"]))

    def test_gzip_is_used_when_the_client_accepts_it(self):
        served = self.serve()
        status, body, answer = self.get(served, "/api/v1/repos?limit=100", {"Accept-Encoding": "gzip"})
        self.assertEqual((status, answer.getheader("Content-Encoding"), len(body["items"])), (200, "gzip", 100))
        self.assertIsNone(self.get(served, "/api/v1/repos?limit=100")[2].getheader("Content-Encoding"))

    def test_the_errors_use_the_envelope_and_the_language_asked(self):
        served = self.serve()
        for path, code in (("/api/v1/repos?limit=0", "api.bad_limit"), ("/api/v1/repos?cursor=bad", "api.bad_cursor"), ("/api/v1/repos?fields=zzz", "api.unknown_field"), ("/api/v1/repos?profile=x", "api.bad_profile")):
            status, body, _ = self.get(served, path)
            self.assertEqual((status, body["error"], body["code"]), (400, "bad_request", code), path)
            self.assertTrue(body["message"])
        _, spanish, _ = self.get(served, "/api/v1/repos?limit=0&lang=es")
        self.assertIn("entero", spanish["message"])

    def test_nothing_can_be_written_under_the_prefix(self):
        served = self.serve()
        for path in ("/api/v1/me", "/api/v1/repos", "/api/v1/settings", "/api/v1/mode"):
            status, _, _ = served.raw("POST", path, {"Content-Type": "application/json"}, "{}")
            self.assertNotEqual(status, 200, path)

    def test_the_openapi_is_served(self):
        status, body, _ = self.get(self.serve(), "/api/v1/openapi.json")
        self.assertEqual(status, 200)
        self.assertTrue({"/api/v1/me", "/api/v1/repos", "/api/v1/openapi.json", "/api/v1/health", "/api/v1/alerts"} <= set(body["paths"]))


class TheSurface(unittest.TestCase):
    def test_the_settings_are_in_the_schema_with_texts_in_eight_languages(self):
        keys = ["api." + k for k in ("v1_enabled", "experimental_routes", "default_limit", "max_limit", "cursor_ttl_seconds", "gzip_min_bytes")]
        for key in keys:
            self.assertIn(key, settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(texts.get("cfg.f." + key) and texts.get("cfg.h." + key), (lang, key))
            for key in ("ui.cfg_b_api_v1", "api.bad_cursor", "api.bad_limit", "api.unknown_field", "api.bad_profile"):
                self.assertTrue(texts.get(key), (lang, key))
        self.assertIn("{max}", json.loads((HERE / "assets" / "locales" / "ja.json").read_text(encoding="utf-8"))["api.bad_limit"])

    def test_the_tool_checks_the_prefix_and_the_docs_describe_it(self):
        self.assertIn("--v1", (HERE / "tools" / "check_api_contract.py").read_text(encoding="utf-8"))
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho"):
            text = (HERE / "docs" / f"API{tail}.md").read_text(encoding="utf-8")
            for word in ("api.v1_enabled", "/api/v1/me", "/api/v1/repos", "v1_endpoints"):
                self.assertIn(word, text, (tail, word))


if __name__ == "__main__":
    unittest.main()
