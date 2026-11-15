# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The read API v1: envelope, paging, compact payloads, versioning, compression, bearer scope and the contract. Deterministic: the clock and the secret are given."""
import gzip
import json
import unittest

import _testenv  # noqa: F401  (first: language, hermetic gh)
from github_actions_monitor.phase4 import apiv1, msgs

SECRET = b"k" * 32


def alerts(n):
    return [{"id": "a%03d" % i, "code": "ci.red", "level": "error", "sentinel": "ci", "account_id": "acc1" if i % 2 else "acc2", "repo": "r", "title": "t", "created_at": "2026-01-01T00:00:00Z"} for i in range(n)]


class Envelope(unittest.TestCase):
    def test_shape_and_language(self):
        status, body = apiv1.error(400, "api.bad_cursor", "es")
        self.assertEqual((status, set(body)), (400, {"error", "code", "message"}))
        self.assertEqual(body["error"], "bad_request")
        self.assertEqual(body["code"], "api.bad_cursor")
        self.assertIn("cursor", body["message"])
        self.assertNotEqual(body["message"], apiv1.error(400, "api.bad_cursor", "en")[1]["message"])

    def test_unknown_status_is_a_500(self):
        self.assertEqual(apiv1.error(418, "api.server_error")[0], 500)

    def test_every_message_has_the_eight_languages(self):
        for key, entry in msgs.CATALOGUE.items():
            self.assertEqual(set(entry), set(msgs.LANGS), key)
            placeholders = {lang: sorted(__import__("re").findall(r"\{(\w+)\}", text)) for lang, text in entry.items()}
            self.assertEqual(len({tuple(v) for v in placeholders.values()}), 1, key)

    def test_missing_placeholder_never_raises(self):
        self.assertTrue(msgs.t("en", "api.bad_limit"))
        self.assertEqual(msgs.t("en", "no.such"), "no.such")
        self.assertEqual(msgs.t("xx", "api.not_found"), msgs.t("en", "api.not_found"))

    def test_formal_register_in_german_french_and_portuguese(self):
        for key, entry in msgs.CATALOGUE.items():
            self.assertNotRegex(entry["de"], r"\b(du|dir|dein\w*)\b", key)
            self.assertNotRegex(entry["fr"], r"\b(tu|toi|ton|ta)\b", key)
            self.assertNotRegex(entry["pt"], r"\b(tu|teu|tua)\b", key)


class Versioning(unittest.TestCase):
    def test_default_prefix_and_header(self):
        self.assertEqual(apiv1.requested_version({}, "/api/alerts"), "1")
        self.assertEqual(apiv1.requested_version({}, "/api/v1/alerts"), "1")
        self.assertEqual(apiv1.requested_version({"x-api-version": "1"}, "/api/alerts"), "1")

    def test_unsupported_is_refused(self):
        for headers, path in (({"X-API-Version": "9"}, "/api/x"), ({}, "/api/v2/x")):
            with self.assertRaises(apiv1.ApiError) as ctx:
                apiv1.requested_version(headers, path)
            self.assertEqual((ctx.exception.status, ctx.exception.code), (400, "api.version_unsupported"))

    def test_both_spellings_reach_the_same_handler(self):
        self.assertEqual(apiv1.strip_prefix("/api/v1/alerts"), "/api/alerts")
        self.assertEqual(apiv1.strip_prefix("/api/alerts"), "/api/alerts")
        self.assertEqual(apiv1.strip_prefix("/api/v10/alerts"), "/api/v10/alerts")

    def test_headers(self):
        h = apiv1.response_headers({"Vary": "x"})
        self.assertEqual((h["X-API-Version"], h["Cache-Control"], h["Vary"]), ("1", "no-store", "x"))


class Paging(unittest.TestCase):
    def page(self, items, **kw):
        base = dict(key=lambda a: a["id"], endpoint="alerts", filters={}, secret=SECRET, now=1000, limit=10)
        base.update(kw)
        return apiv1.paginate(items, **base)

    def test_walks_every_item_once_in_order(self):
        items, seen, cursor = alerts(25), [], None
        for _ in range(10):
            page = self.page(items, cursor=cursor)
            seen += [a["id"] for a in page["items"]]
            cursor = page["next_cursor"]
            if not cursor:
                break
        self.assertEqual(seen, sorted((a["id"] for a in items), reverse=True))

    def test_an_item_added_between_requests_does_not_repeat_or_shift(self):
        items = alerts(15)
        first = self.page(items, limit=5)
        newer = items + [dict(items[0], id="a999")]
        second = self.page(newer, limit=5, cursor=first["next_cursor"])
        self.assertEqual([a["id"] for a in first["items"] + second["items"]], [a["id"] for a in sorted(items, key=lambda a: a["id"], reverse=True)][:10])

    def test_last_page_has_no_cursor(self):
        self.assertIsNone(self.page(alerts(3))["next_cursor"])

    def test_cursor_of_another_query_is_refused(self):
        cursor = self.page(alerts(25))["next_cursor"]
        with self.assertRaises(apiv1.ApiError) as ctx:
            self.page(alerts(25), filters={"level": "error"}, cursor=cursor)
        self.assertEqual(ctx.exception.code, "api.bad_cursor")

    def test_tampered_foreign_expired_and_garbage_cursors(self):
        cursor = self.page(alerts(25))["next_cursor"]
        body, mac = cursor.split(".")
        for bad in (body + "." + "A" * len(mac), "x" + cursor, "nodot", "a.b.c", "é" * 4 + "." + mac, cursor + "x"):
            with self.assertRaises(apiv1.ApiError, msg=bad):
                self.page(alerts(25), cursor=bad)
        with self.assertRaises(apiv1.ApiError):
            self.page(alerts(25), cursor=cursor, secret=b"z" * 32)
        with self.assertRaises(apiv1.ApiError):
            self.page(alerts(25), cursor=cursor, now=1000 + 901)
        with self.assertRaises(apiv1.ApiError):
            self.page(alerts(25), cursor=cursor, now=10)      # from the future

    def test_limit_rules(self):
        self.assertEqual(apiv1.parse_limit(None, 50, 200), 50)
        self.assertEqual(apiv1.parse_limit("200", 50, 200), 200)
        for bad in ("0", "201", "-1", "x", "1.5", " "):
            with self.assertRaises(apiv1.ApiError, msg=bad):
                apiv1.parse_limit(bad, 50, 200)

    def test_ascending_order(self):
        page = self.page(alerts(12), descending=False, limit=4)
        self.assertEqual([a["id"] for a in page["items"]], ["a000", "a001", "a002", "a003"])
        nxt = self.page(alerts(12), descending=False, limit=4, cursor=page["next_cursor"])
        self.assertEqual(nxt["items"][0]["id"], "a004")


class Compact(unittest.TestCase):
    def test_fields_parse(self):
        self.assertEqual(apiv1.parse_fields("id, code,id"), ["id", "code"])
        self.assertIsNone(apiv1.parse_fields(""))
        for bad in ("Id", "a;b", "1x", "a,,b", "x" * 41):
            with self.assertRaises(apiv1.ApiError, msg=bad):
                apiv1.parse_fields(bad)

    def test_projection(self):
        item = alerts(1)[0]
        self.assertEqual(set(apiv1.project(item, "alerts", ["id", "code"])), {"id", "code"})
        self.assertEqual(set(apiv1.project(item, "alerts", profile="mobile")), set(apiv1.CONTRACT["alerts"]["compact"]))
        self.assertEqual(apiv1.project(item, "alerts"), item)
        with self.assertRaises(apiv1.ApiError):
            apiv1.project(item, "alerts", ["password"])

    def test_profile_negotiation(self):
        self.assertEqual(apiv1.negotiate_profile({}, {}), "full")
        self.assertEqual(apiv1.negotiate_profile({"profile": "compact"}, {}), "compact")
        self.assertEqual(apiv1.negotiate_profile({}, {"X-Client-Profile": "mobile"}), "mobile")
        self.assertEqual(apiv1.negotiate_profile({}, {"x-client-profile": "mobile"}, mobile_default=False), "full")
        self.assertEqual(apiv1.negotiate_profile({"profile": "weird"}, {}), "full")

    def test_compact_is_smaller(self):
        item = alerts(1)[0]
        self.assertLess(len(json.dumps(apiv1.project(item, "alerts", profile="compact"))), len(json.dumps(item)))


class Compression(unittest.TestCase):
    BODY = json.dumps(alerts(50)).encode()

    def test_gzip_roundtrip_and_reproducible(self):
        out, headers = apiv1.maybe_compress(self.BODY, "br, gzip;q=0.8", 100)
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(gzip.decompress(out), self.BODY)
        self.assertEqual(out, apiv1.maybe_compress(self.BODY, "gzip", 100)[0])
        self.assertLess(len(out), len(self.BODY))

    def test_not_when_refused_small_or_absent(self):
        for accept in ("", None, "identity", "gzip;q=0", "br"):
            out, headers = apiv1.maybe_compress(self.BODY, accept, 100)
            self.assertEqual(out, self.BODY)
            self.assertNotIn("Content-Encoding", headers)
            self.assertEqual(headers["Vary"], "Accept-Encoding")
        self.assertEqual(apiv1.maybe_compress(b"{}", "gzip", 100)[0], b"{}")


class Bearer(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(apiv1.parse_bearer("Bearer abcdefgh12345"), "abcdefgh12345")
        self.assertEqual(apiv1.parse_bearer("bearer abcdefgh12345"), "abcdefgh12345")
        for bad in (None, "", "Basic abcdefgh", "Bearer short", "Bearer a b c d e f g h", "Bearer " + "x" * 513, "Bearer abcdefgh\n"):
            self.assertIsNone(apiv1.parse_bearer(bad), bad)

    def test_roles(self):
        self.assertTrue(apiv1.role_allows("admin", "viewer"))
        self.assertFalse(apiv1.role_allows("viewer", "admin"))
        self.assertFalse(apiv1.role_allows("root", "viewer"))
        self.assertFalse(apiv1.role_allows("viewer", "root"))

    def test_authorize(self):
        with self.assertRaises(apiv1.ApiError) as ctx:
            apiv1.authorize(None, "alerts")
        self.assertEqual(ctx.exception.status, 401)
        with self.assertRaises(apiv1.ApiError) as ctx:
            apiv1.authorize({"role": "nobody", "accounts": None}, "alerts")
        self.assertEqual(ctx.exception.status, 403)
        apiv1.authorize({"role": "viewer", "accounts": None}, "alerts", "any")
        apiv1.authorize({"role": "viewer", "accounts": ["a"]}, "account_status", "a")

    def test_an_account_out_of_scope_looks_like_one_that_does_not_exist(self):
        with self.assertRaises(apiv1.ApiError) as ctx:
            apiv1.authorize({"role": "admin", "accounts": ["a"]}, "account_status", "b")
        self.assertEqual((ctx.exception.status, ctx.exception.code), (404, "api.not_found"))

    def test_accounts_are_isolated_for_cookie_and_bearer_alike(self):
        items = alerts(10)
        only1 = apiv1.scope_accounts(items, {"role": "viewer", "accounts": ["acc1"]})
        self.assertTrue(only1 and all(a["account_id"] == "acc1" for a in only1))
        self.assertEqual(apiv1.scope_accounts(items, {"role": "viewer", "accounts": []}), [])
        self.assertEqual(len(apiv1.scope_accounts(items, {"role": "admin", "accounts": None})), 10)


class Contract(unittest.TestCase):
    def test_compact_lists_are_inside_the_promise(self):
        for name, spec in apiv1.CONTRACT.items():
            self.assertTrue(set(spec["compact"]) <= set(spec["required"]), name)
            self.assertIn(spec["kind"], ("list", "object"))
            self.assertTrue(spec["path"].startswith("/api/"))

    def test_the_roadmap_endpoints_are_all_there(self):
        paths = {s["path"] for s in apiv1.CONTRACT.values()}
        for want in ("/api/health", "/api/accounts", "/api/accounts/{id}/status", "/api/status", "/api/alerts", "/api/events", "/api/live-events", "/api/live-status", "/api/score",
                     "/api/repos/{owner}/{repo}/health", "/api/team/health"):
            self.assertIn(want, paths)

    def test_check_payload_fails_when_a_promised_field_goes_missing(self):
        ok = alerts(2)
        self.assertEqual(apiv1.check_payload("alerts", ok), [])
        broken = [dict(ok[0]), {k: v for k, v in ok[1].items() if k != "level"}]
        self.assertEqual(apiv1.check_payload("alerts", broken), ["alerts[1]: missing level"])
        self.assertTrue(apiv1.check_payload("alerts", {"a": 1}))
        self.assertTrue(apiv1.check_payload("alerts", ["x"]))
        self.assertEqual(apiv1.check_payload("health", {"ok": True, "edition": "complete", "version": "1"}), [])
        self.assertEqual(apiv1.check_payload("health", {"ok": True}), ["health[0]: missing edition", "health[0]: missing version"])

    def test_openapi_covers_the_contract(self):
        doc = apiv1.openapi()
        self.assertEqual(doc["openapi"], "3.0.3")
        self.assertEqual(len(doc["paths"]), len(apiv1.CONTRACT))
        self.assertIn("/api/v1/alerts", doc["paths"])
        self.assertIn("/api/v1/accounts/{id}/status", doc["paths"])
        ops = {p["get"]["operationId"] for p in doc["paths"].values()}
        self.assertEqual(ops, set(apiv1.CONTRACT))
        params = {p["name"] for p in doc["paths"]["/api/v1/alerts"]["get"]["parameters"]}
        self.assertTrue({"fields", "profile", "limit", "cursor", "account", "sentinel", "level", "since"} <= params)
        json.dumps(doc)


if __name__ == "__main__":
    unittest.main()
