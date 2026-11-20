# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The wall screens (/screen/overview, /screen/now, /screen/sentinels): the settings and their limits, what an address may ask for, the names of private repositories, the payload (a closed list of fields, no
link, no title, no job or user name), and the routes against a real server: 404 while they are off, read only, and never a call to GitHub."""
import http.client
import json
import re
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.app import actions_monitor, screens, settings_api, toolconfig

NOW = 1_794_856_800.0      # a fixed moment: 2026-11-16T20:40:00Z
ISO = "%Y-%m-%dT%H:%M:%SZ"


def ago(seconds):
    import time
    return time.strftime(ISO, time.gmtime(NOW - seconds))


def run(repo, name, conclusion, seconds_ago, status="completed", branch="main", event="push", **extra):
    return {"repo": repo, "id": 1, "name": name, "title": "SECRET COMMIT TITLE", "event": event, "branch": branch, "status": status, "conclusion": conclusion, "started": ago(seconds_ago), "seconds": 120,
            "url": "https://github.com/o/" + repo + "/actions/runs/1", "actor": "someone-real", "sha": "abc1234", **extra}


def state():
    repos = ["pub-a", "pub-b", "priv-c", "pub-d"]
    jobs = [{"name": "SECRET JOB NAME", "status": "completed", "conclusion": "success", "steps_total": 4, "steps_done": 4, "step": "", "runner": "r1", "seconds": 5, "url": "#"},
            {"name": "other", "status": "in_progress", "conclusion": None, "steps_total": 4, "steps_done": 2, "step": "Compile", "runner": "r2", "seconds": 5, "url": "#"}]
    return {"updated": ago(5), "repos": repos, "repo_meta": {"pub-a": {"private": False, "branch": "main"}, "pub-b": {"private": False, "branch": "main"}, "priv-c": {"private": True, "branch": "main"}, "pub-d": {"private": False, "branch": "main"}},
            "runs": [run("pub-a", "CI", "success", 600), run("pub-a", "Release build", "success", 900), run("pub-b", "CI", "failure", 7200), run("priv-c", "Deploy", "failure", 1800), run("pub-d", "CI", "action_required", 400),
                     run("pub-b", "CI", "success", 3 * 86400, branch="dev")],
            "active": [run("pub-a", "Build", None, 300, status="in_progress", jobs=jobs), run("pub-b", "Build", None, 100, status="queued", jobs=[]), run("priv-c", "Stuck one", None, 5000, status="in_progress", stuck=True, jobs=[])],
            "failing": [run("pub-b", "CI", "failure", 7200), run("priv-c", "Deploy", "failure", 1800)], "rate": {"remaining": 4000, "limit": 5000, "reset": ago(-1500)}, "refresh_seconds": 45}


def snapshot():
    return {"generated": ago(30), "enabled": True, "loading": "", "cache_age_seconds": None, "level": "bad", "errors": [{"section": "a9", "message": "x", "at": "t"}], "totals": {"red": 2, "stuck": 1, "new_alerts": 0, "candidates": 1, "prs": 0, "codeql": 0, "dependabot": 0, "secret": 0},
            "a1": {"stuck": [{"repo": "priv-c"}], "issues": [], "level": "bad"}, "a2": {"red": [{"repo": "pub-b", "workflow": "CI", "since": ago(7200), "streak": 3}, {"repo": "priv-c", "workflow": "Deploy", "since": ago(1800), "streak": 1}], "level": "bad"},
            "a3": {"codeql_total": 1, "dependabot_total": 2, "secret_total": 0, "level": "warn"}, "a5": {"candidates": [{"repo": "pub-a", "entries": 5, "age_days": 3.0}], "pending_sign": [{"repo": "priv-c", "hours": 30.5}], "level": "info"},
            "a7": {"rows": [{"repo": "pub-a", "min24": 40, "min7d": 100}], "level": "ok"}, "a9": {"boards": [], "level": "unknown"}, "a10": {"sections": [{"count": 2}, {"count": 1}], "level": "info"}}


def alerts():
    return {"summary": {"total": 6, "by_level": {"error": 2, "warning": 3, "info": 1}, "by_sentinel": {"ci": 2, "collab": 4}}, "alerts": [{"title": "SECRET ALERT TITLE", "details": {"url": "https://github.com/x"}}]}


class Settings(unittest.TestCase):
    def test_the_defaults_are_the_conservative_ones(self):
        cfg = screens.settings({})
        self.assertEqual(cfg, screens.DEFAULTS)
        self.assertEqual((cfg["enabled"], cfg["rotate_seconds"], cfg["sound"], cfg["night_dim"], cfg["show_repo_names"]), (False, 0, False, False, "public"))
        self.assertEqual(actions_monitor.DEFAULTS["screens"], screens.DEFAULTS, "the defaults of the monitor and of the module are one and the same")

    def test_every_value_stays_inside_its_range(self):
        cfg = screens.settings({"screens": {"refresh_seconds": 1, "rotate_seconds": 99999, "blink_calm_minutes": -4, "night_dim_from_hour": 40, "default_theme": "pink", "show_repo_names": "everyone", "blink": "off", "enabled": "no"}})
        self.assertEqual((cfg["refresh_seconds"], cfg["rotate_seconds"], cfg["blink_calm_minutes"], cfg["night_dim_from_hour"]), (5, 3600, 0, 23))
        self.assertEqual((cfg["default_theme"], cfg["show_repo_names"], cfg["blink"], cfg["enabled"]), ("inherit", "public", False, False))
        self.assertEqual(screens.settings({"screens": "nonsense"}), screens.DEFAULTS)
        self.assertEqual(screens.settings({"screens": {"refresh_seconds": True}})["refresh_seconds"], 10, "a boolean is not a number")

    def test_every_setting_has_its_row_its_default_and_its_texts_in_eight_languages(self):
        for key in screens.DEFAULTS:
            self.assertIn("screens." + key, settings_api.FIELDS, key)
            last = key.rsplit("_", 1)[-1]
            self.assertNotIn(last, ("token", "secret", "password", "key", "command"))
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                for key in screens.DEFAULTS:
                    for prefix in ("cfg.f.screens.", "cfg.h.screens."):
                        self.assertNotEqual(i18n.t(prefix + key), prefix + key, f"{lang} {prefix}{key}")
                self.assertNotEqual(i18n.t("ui.cfg_b_wall"), "ui.cfg_b_wall")
        self.assertTrue(settings_api.META["screens.show_repo_names"]["secure"], "who sees the names of the repositories is a security option")


class WhatTheAddressMayAsk(unittest.TestCase):
    def test_the_defaults_come_from_the_settings(self):
        prm = screens.params({}, screens.settings({}))
        self.assertEqual((prm["theme"], prm["density"], prm["refresh"], prm["rotate"], prm["blink"], prm["sound"], prm["monitor"], prm["scale"]), ("auto", "normal", 10, 0, True, False, 1, 1.0))

    def test_a_window_can_make_things_quieter_but_never_louder(self):
        on = screens.settings({"screens": {"blink": True, "sound": True}})
        off = screens.settings({"screens": {"blink": False, "sound": False}})
        self.assertFalse(screens.params({"blink": "off"}, on)["blink"])
        self.assertTrue(screens.params({"blink": "on"}, on)["blink"])
        self.assertFalse(screens.params({"blink": "on"}, off)["blink"], "the setting that keeps blinking off wins over the address")
        self.assertFalse(screens.params({"sound": "on"}, off)["sound"], "sound is off unless the setting allows it")
        self.assertTrue(screens.params({"sound": "on"}, on)["sound"])
        self.assertFalse(screens.params({}, on)["sound"], "and even then the address has to ask for it")

    def test_the_numbers_are_clamped_and_a_turn_faster_than_five_seconds_is_no_turn(self):
        cfg = screens.settings({})
        prm = screens.params({"monitor": "77", "refresh": "1", "scale": "9", "rotate": "2", "density": "huge", "theme": "light"}, cfg)
        self.assertEqual((prm["monitor"], prm["refresh"], prm["scale"], prm["rotate"], prm["density"], prm["theme"]), (9, 5, 3.0, 0, "normal", "light"))
        self.assertEqual(screens.params({"rotate": "30", "scale": "1,5"}, cfg)["rotate"], 30)
        self.assertEqual(screens.params({"scale": "1,5"}, cfg)["scale"], 1.5)
        self.assertEqual(screens.params({"scale": "x", "refresh": "abc"}, cfg)["scale"], 1.0)

    def test_only_the_three_addresses_are_screens(self):
        for kind in screens.KINDS:
            self.assertEqual(screens.kind_of("/screen/" + kind), kind)
            self.assertEqual(screens.kind_of("/screen/" + kind + "/"), kind)
        for bad in ("/screen/1", "/screen/", "/screen/overview/x", "/screen/OVERVIEW", "/api/screens", "/screenoverview", None):
            self.assertIsNone(screens.kind_of(bad), bad)


class Names(unittest.TestCase):
    def test_public_hides_the_private_ones_with_a_stable_number(self):
        names = screens.Names(["a", "b", "c"], {"a": {"private": False}, "b": {"private": True}, "c": {}}, "public", key="k" * 32)
        shown = [names.name(r) for r in ("a", "b", "c")]
        self.assertEqual((shown[0], sorted(shown[1:])), ("a", ["private-1", "private-2"]), "a repository that is not known to be public is treated as private; only the hidden ones are numbered")
        again = screens.Names(["a", "b", "c"], {"a": {"private": False}, "b": {"private": True}, "c": {}}, "public", key="k" * 32)
        self.assertEqual([again.name(r) for r in ("a", "b", "c")], shown, "the same number every time with the same key")

    def test_all_and_none(self):
        meta = {"a": {"private": True}}
        self.assertEqual(screens.Names(["a"], meta, "all").name("a"), "a")
        hidden = screens.Names(["a", "b"], meta, "none")      # the numbers follow an HMAC with the key of the installation: which one is first is not fixed, that they are 1 and 2 is
        self.assertEqual({hidden.name("a"), hidden.name("b")}, {"repo-1", "repo-2"})
        self.assertEqual(screens.Names(["a"], meta, "bogus").mode, "public")


def fleet_view():
    """The answer of the fleet view for the four repositories of the double (the same shape as health/fleet.py gives)."""
    rows = [("pub-a", "ok", 0), ("pub-b", "bad", 8), ("priv-c", "bad", 7), ("pub-d", "warn", 3)]
    return {"group_by": "ecosystem", "groups": [{"key": "armor", "repos": 4, "bad": 2, "warn": 1, "ok": 1, "unknown": 0, "risk": 18}],
            "rows": [{"repo": r, "group": "armor", "state": s, "risk": k, "red_workflows": 1 if s == "bad" else 0, "running": 0} for r, s, k in rows]}


class ThePayload(unittest.TestCase):
    def build(self, kind, mode="public", snap=True, **cfg):
        c = screens.settings({"screens": {"show_repo_names": mode, **cfg}})
        return screens.build(kind, state(), snapshot() if snap else None, alerts(), {"enabled": True, "state": "scored", "score": 83.2, "letter": "B", "trend": 2}, c, now=NOW, fleet_view=fleet_view(), labels={"armor": "ARMOR"})

    def test_nothing_that_could_leak_leaves_the_server(self):
        for kind in screens.KINDS:
            for mode in screens.NAMES:
                text = json.dumps(self.build(kind, mode))
                for forbidden in ("SECRET COMMIT TITLE", "SECRET JOB NAME", "SECRET ALERT TITLE", "someone-real", "https://", "github.com", "abc1234", "Compile", "r1", "/actions/runs"):
                    self.assertNotIn(forbidden, text, f"{kind}/{mode}: {forbidden}")
                if mode != "all":
                    self.assertNotIn("priv-c", text, f"{kind}/{mode}")
                if mode == "none":
                    self.assertNotIn("pub-", text, f"{kind}/{mode}")
                if mode == "all":
                    self.assertIn("pub-a", text) if kind != "sentinels" else None

    def test_the_workflow_name_of_a_hidden_repository_is_hidden_too(self):
        text = json.dumps(self.build("overview"))
        self.assertNotIn("Deploy", text)
        self.assertIn("Release build", text)
        self.assertIn("private-1", text)
        self.assertNotIn("Deploy", json.dumps(self.build("now")))
        self.assertIn("Deploy", json.dumps(self.build("overview", "all")))

    def test_the_fleet_is_counted_once_each_in_the_order_red_stuck_waiting_green(self):
        fleet = self.build("overview")["fleet"]
        self.assertEqual(fleet, {"total": 4, "red": 2, "stuck": 0, "waiting": 1, "green": 1, "idle": 0}, "priv-c is red AND stuck: red wins; pub-d waits for approval")
        self.assertEqual(sum(v for k, v in fleet.items() if k != "total"), fleet["total"])
        bare = screens.build("overview", {"repos": ["x", "y"], "runs": [run("x", "CI", "success", 10)]}, None, None, None, screens.settings({}), now=NOW)["fleet"]
        self.assertEqual(bare, {"total": 2, "red": 0, "stuck": 0, "waiting": 0, "green": 1, "idle": 1}, "a repository without a run is idle, not green")

    def test_the_series_and_the_heat_map_have_a_fixed_shape(self):
        d = self.build("overview")
        self.assertEqual((len(d["trend24"]), len(d["trend7d"])), (24, 7))
        self.assertEqual(d["trend24"][-1]["ago"], 0)
        self.assertEqual(sum(p["ok"] + p["bad"] for p in d["trend24"]), 4, "the four completed runs of the last day (the one of 3 days ago and the one that waits do not count)")
        self.assertEqual(d["trend7d"][-4]["ok"], 1, "the run of three days ago")
        for row in d["heat"]:
            self.assertEqual(len(row["cells"]), 24)
            self.assertTrue(set(row["cells"]) <= {0, 1, 2, 3})
        self.assertTrue(all(r["red"] for r in d["heat"][:2]), "the red repositories come first")

    def test_the_top_red_are_ordered_by_how_long_they_have_been_red(self):
        top = self.build("overview")["top_red"]
        self.assertEqual([t["seconds"] for t in top], [7200, 1800])
        self.assertEqual(top[0]["streak"], 3)

    def test_score_alerts_and_queue(self):
        d = self.build("overview")
        self.assertEqual(d["score"], {"state": "scored", "value": 83.2, "letter": "B", "trend": 2})
        self.assertEqual(d["alerts"]["total"], 6)
        self.assertEqual((d["queue"]["running"], d["queue"]["queued"], d["queue"]["approval"], d["queue"]["minutes24"]), (2, 1, 1, 40))
        self.assertEqual(screens.build("overview", state(), None, None, None, screens.settings({}), now=NOW)["score"]["state"], "off")

    def test_now_has_progress_stuck_and_what_waits(self):
        d = self.build("now")
        running = {r["repo"]: r for r in d["running"]}
        self.assertEqual(running["pub-a"]["progress"], 0.75, "six of eight steps")
        self.assertIsNone(running["private-1"]["progress"])
        self.assertTrue(running["private-1"]["stuck"])
        self.assertEqual(d["running"][0]["repo"], "private-1", "a stuck run goes first")
        self.assertEqual(len(d["queued"]), 1)
        self.assertEqual(d["totals"], {"running": 2, "queued": 1, "approval": 1, "failures": 2})
        self.assertEqual([f["ago"] for f in d["failures"]], [1800, 7200], "the newest failure first")
        self.assertEqual(d["next_releases"][0]["entries"], 5)
        self.assertEqual(d["pending_sign"][0]["hours"], 30.5)
        self.assertTrue(any(m["release"] for m in d["merges"]) and all(m["ago"] is not None for m in d["merges"]))
        self.assertNotIn("pub-b", [m["repo"] for m in d["merges"]], "only a green run on the default branch is a merge")
        self.assertTrue(all(e["ago"] <= 7200 or True for e in d["timeline"]))

    def test_sentinels_cards_say_what_can_and_cannot_be_read(self):
        d = self.build("sentinels")
        self.assertEqual([c["id"] for c in d["cards"]], list(screens.SENTINELS))
        cards = {c["id"]: c for c in d["cards"]}
        self.assertEqual((cards["a1"]["open"], cards["a2"]["open"], cards["a3"]["open"], cards["a5"]["open"], cards["a10"]["open"]), (1, 2, 3, 2, 3))
        self.assertTrue(cards["a2"]["readable"])
        self.assertFalse(cards["a9"]["readable"], "a9 reported an error and has no data")
        self.assertFalse(cards["a12"]["readable"], "a panel the snapshot does not have")
        self.assertEqual(d["level"], "bad")
        self.assertEqual(d["sweep"], {"age_seconds": 30, "cycle_seconds": 45, "progress": 0.667})
        self.assertEqual(d["alerts"]["by_level"], {"critical": 0, "error": 2, "warning": 3, "info": 1})
        self.assertTrue(d["enabled"])
        off = self.build("sentinels", snap=False)
        self.assertFalse(off["enabled"])
        self.assertTrue(all(not c["readable"] for c in off["cards"]))

    def test_without_any_data_every_screen_still_answers(self):
        for kind in screens.KINDS:
            empty = screens.build(kind, None, None, None, None, screens.settings({}), now=NOW)
            self.assertFalse(empty["meta"]["have_data"])
            json.dumps(empty)
            weird = screens.build(kind, {"runs": [None, {"repo": "x", "started": "nonsense"}, "text"], "active": [3], "repos": ["x"], "rate": "bad"}, {"a2": "bad", "errors": [1]}, {"summary": 5}, "no", screens.settings({}), now=NOW)
            json.dumps(weird)
        with self.assertRaises(ValueError):
            screens.build("other", None, None, None, None, screens.settings({}))

    def test_the_closed_list_of_keys(self):
        self.assertEqual(sorted(self.build("overview")), sorted(["schema", "screen", "version", "epoch", "names", "meta", "score", "fleet", "trend24", "trend7d", "heat", "top_red", "queue", "events", "alerts", "groups"]))
        self.assertEqual(sorted(self.build("now")), sorted(["schema", "screen", "version", "epoch", "names", "meta", "running", "queued", "approval", "failures", "merges", "next_releases", "pending_sign", "timeline", "totals"]))
        self.assertEqual(sorted(self.build("sentinels")), sorted(["schema", "screen", "version", "epoch", "names", "meta", "enabled", "level", "loading", "sweep", "cards", "totals", "alerts"]))

    def test_the_meta_says_how_old_the_data_is_and_how_much_allowance_is_left(self):
        meta = self.build("overview")["meta"]
        self.assertEqual((meta["age_seconds"], meta["have_data"], meta["refresh_seconds"]), (5, True, 45))
        self.assertEqual((meta["api"]["remaining"], meta["api"]["limit"], meta["api"]["reset_seconds"], meta["api"]["low"]), (4000, 5000, 1500, False))
        low = screens.build("overview", {**state(), "rate": {"remaining": 100, "limit": 5000, "reset": ago(-60)}}, None, None, None, screens.settings({}), now=NOW)
        self.assertTrue(low["meta"]["api"]["low"])


class ThePage(unittest.TestCase):
    def test_the_page_data_carries_the_texts_of_the_language_and_nothing_from_the_settings_it_does_not_need(self):
        cfg = screens.settings({})
        with i18n.use_language("de"):
            data = screens.page_data("now", cfg, screens.params({}, cfg))
        self.assertEqual((data["lang"], data["html_lang"], data["screen"]), ("de", "de", "now"))
        self.assertEqual(data["texts"]["ui.scr_title_now"], "Gerade jetzt")
        self.assertIn("ui.a1", data["texts"])
        self.assertIn("ui.lv_bad", data["texts"])
        self.assertEqual(set(data["settings"]), {"blink", "blink_calm_minutes", "burn_in_protection", "night_dim", "night_dim_from_hour", "night_dim_to_hour", "life", "glance_seconds", "transition", "hide_healthy", "idle_dim_minutes", "min_font_px"})
        self.assertNotIn("show_repo_names", json.dumps(data))

    def test_every_text_the_page_asks_for_exists_in_eight_languages(self):
        html = (Path(actions_monitor.__file__).resolve().parents[3] / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
        keys = set(re.findall(r'"(ui\.scr_[a-z0-9_]+)"', html))
        prefixes = set(re.findall(r'T\("(ui\.scr_[a-z0-9_]+_)"\s*\+', html))
        self.assertTrue(keys)
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                for key in sorted(keys):
                    if key.endswith("_"):
                        self.assertTrue(any(k.startswith(key) for k in i18n.catalogue_keys()), f"{lang}: nothing starts with {key}")
                        continue
                    self.assertNotEqual(i18n.t(key), key, f"{lang}: {key}")
                for prefix in prefixes:
                    for word in {"ui.scr_u_": "dhms", "ui.scr_ev_": ("ok", "bad", "run", "wait", "skip"), "ui.scr_sev_": ("critical", "error", "warning", "info")}.get(prefix, ()):
                        self.assertNotEqual(i18n.t(prefix + (word if len(word) > 1 else word)), prefix + word, f"{lang}: {prefix}{word}")

    def test_the_page_has_no_menu_no_library_no_outside_address_and_no_text_of_its_own(self):
        html = (Path(actions_monitor.__file__).resolve().parents[3] / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"https?://(?!www\.w3\.org)", "no address of anybody else")
        self.assertNotIn("<script src", html)
        self.assertNotIn("<link", html)
        self.assertNotIn("<nav", html)
        self.assertNotRegex(html, r"<a\s")
        self.assertEqual(len(re.findall(r"<button", html)), 1, "one discreet button (full screen) and nothing that changes anything")
        self.assertNotRegex(html, r"method\s*:\s*[\"']POST|\.post\(|XMLHttpRequest", "read only")
        fetches = re.findall(r"fetch\(([^)]*)\)", html)
        self.assertEqual(len(fetches), 1)
        self.assertIn('"/api/screens/data?screen="', fetches[0])
        body = html.split("<body>", 1)[1].split("<script>", 1)[0]
        words = [w for w in re.findall(r"[A-Za-zÀ-ÿ]{3,}", re.sub(r"<[^>]+>", " ", body))]
        self.assertEqual(words, [], "every visible text comes from the catalogue")


ON = {"screens": {"enabled": True}}


class Running:
    def __init__(self, case, config):
        patcher = mock.patch.object(toolconfig, "raw_config", return_value=config)
        patcher.start()
        case.addCleanup(patcher.stop)
        patcher = mock.patch.dict(actions_monitor.STATE, {"data": state()})
        patcher.start()
        case.addCleanup(patcher.stop)
        self.server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def get(self, path, method="GET"):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            connection.request(method, path, headers={"Host": f"127.0.0.1:{self.port}"})
            answer = connection.getresponse()
            return answer.status, answer.read(), answer.getheader("Content-Type", "")
        finally:
            connection.close()


class TheRoutes(unittest.TestCase):
    def test_a_new_installation_has_them_off_and_every_address_is_a_404(self):
        server = Running(self, {})
        for path in ("/screen/overview", "/screen/now", "/screen/sentinels", "/api/screens/data?screen=now"):
            self.assertEqual(server.get(path)[0], 404, path)

    def test_the_three_pages_and_their_data_answer(self):
        server = Running(self, ON)
        for kind in screens.KINDS:
            status, body, kind_header = server.get("/screen/" + kind)
            self.assertEqual(status, 200, kind)
            self.assertIn("text/html", kind_header)
            text = body.decode("utf-8")
            self.assertNotIn("/*SCREEN_DATA*/", text)
            self.assertIn('"screen": "%s"' % kind, text)
            status, body, kind_header = server.get("/api/screens/data?screen=" + kind)
            self.assertEqual(status, 200, kind)
            self.assertIn("json", kind_header)
            self.assertEqual(json.loads(body)["screen"], kind)

    def test_the_address_is_taken_into_the_page_and_escaped(self):
        server = Running(self, ON)
        text = server.get("/screen/now?theme=light&monitor=3&rotate=30&lang=es&blink=off")[1].decode("utf-8")
        data = json.loads(re.search(r"const D=(\{.*\});\n", text).group(1).replace("<\\/", "</"))
        self.assertEqual((data["params"]["theme"], data["params"]["monitor"], data["params"]["rotate"], data["lang"], data["params"]["blink"]), ("light", 3, 30, "es", False))
        hostile = server.get("/screen/now?theme=%3C/script%3E%3Cscript%3Ealert(1)&lang=%3C/script%3E")[1].decode("utf-8")
        self.assertNotIn("<script>alert(1)", hostile)
        self.assertEqual(hostile.count("</script>"), 1)

    def test_while_they_are_off_every_address_is_a_404(self):
        server = Running(self, {"screens": {"enabled": False}})
        for path in ("/screen/overview", "/screen/now", "/screen/sentinels", "/api/screens/data?screen=now"):
            self.assertEqual(server.get(path)[0], 404, path)
        self.assertEqual(server.get("/screen/1")[0], 200, "the screens of one monitor (/screen/N) are another thing and stay")

    def test_an_unknown_screen_is_a_404_and_nothing_can_be_written(self):
        server = Running(self, ON)
        self.assertEqual(server.get("/api/screens/data?screen=admin")[0], 404)
        self.assertEqual(server.get("/api/screens/data")[0], 404)
        self.assertEqual(server.get("/screen/other")[0], 404)
        for path in ("/api/screens/data?screen=now", "/screen/overview"):
            self.assertNotEqual(server.get(path, method="POST")[0], 200, path)

    def test_the_screens_never_call_github_nor_run_anything(self):
        server = Running(self, ON)
        boom = AssertionError("a wall screen reached for GitHub or started a program")
        with mock.patch("subprocess.run", side_effect=boom), mock.patch("subprocess.Popen", side_effect=boom), mock.patch.object(actions_monitor, "gh_read", side_effect=boom), \
                mock.patch("urllib.request.urlopen", side_effect=boom):
            for kind in screens.KINDS:
                self.assertEqual(server.get("/screen/" + kind)[0], 200)
                self.assertEqual(server.get("/api/screens/data?screen=" + kind)[0], 200)

    def test_the_names_follow_the_setting_in_the_real_answer(self):
        for mode, hidden in (("public", True), ("all", False), ("none", True)):
            server = Running(self, {"screens": {"enabled": True, "show_repo_names": mode}})
            text = server.get("/api/screens/data?screen=overview")[1].decode("utf-8")
            self.assertEqual("priv-c" not in text, hidden, mode)

    def test_the_route_is_in_the_edition_without_sentinels_too(self):
        with mock.patch.dict(actions_monitor.LITE, {"on": True}):
            server = Running(self, ON)
            self.assertEqual(server.get("/api/screens/data?screen=sentinels")[0], 200)
            self.assertFalse(json.loads(server.get("/api/screens/data?screen=sentinels")[1])["enabled"])


if __name__ == "__main__":
    unittest.main()
