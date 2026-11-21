# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Read only commands from Slack and Discord: the proofs (signature, age, replay), the lists of allowed ones, the limits, the closed list of commands, the escaping of every outside text and the route."""
import json
import re
import sys
import tempfile
import itertools
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import _timing  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.chatops import commands, inbound, render  # noqa: E402
from github_actions_monitor.security import audit_log, envguard, localguard, sigverify  # noqa: E402
from test_164 import LiveServer  # noqa: E402
from test_next_level import keypair  # noqa: E402

SECRET = "0123456789abcdef0123456789abcdef"
PUBLIC, SIGN = keypair(b"\x07" * 32)
OTHER_PUBLIC, OTHER_SIGN = keypair(b"\x08" * 32)
ENV = {"MONITOR_SLACK_SIGNING_SECRET": SECRET, "MONITOR_DISCORD_PUBLIC_KEY": PUBLIC.hex()}
NOW = 1_800_000_000
COUNTER = itertools.count(1)      # every body is different, so a signature is never accidentally the same as an earlier one
ALLOW = {"allowed_users": ["U1", "100"]}
SNAP = {"loaded": True, "version": "9.9.9", "fleet": {"total": 5, "red": 2, "stuck": 1, "waiting": 0, "green": 1, "idle": 1}, "queue": {"running": 1, "queued": 2, "approval": 0, "minutes24": 33},
        "score": {"state": "ok", "value": 88.4, "letter": "B", "trend": -2.0}, "red": [{"repo": "app", "workflow": "ci", "seconds": 7200, "streak": 3}, {"repo": "private-1", "workflow": "", "seconds": 90, "streak": 1}],
        "alerts": {"total": 3, "rows": [{"level": "error", "code": "ci.red", "repo": "app"}, {"level": "info", "code": "x", "repo": None}]}}


def config(**more):
    return {"chatops": {"enabled": True, "slack": {"enabled": True}, "discord": {"enabled": True}, **ALLOW, **more}}


def slack_headers(body, secret=SECRET, ts=NOW):
    return {"X-Slack-Request-Timestamp": str(ts), "X-Slack-Signature": inbound.slack_sign(secret, ts, body)}


def slack_body(text="status", user="U1", channel="C1", team="T1", command="/monitor"):
    return f"token=x&team_id={team}&channel_id={channel}&user_id={user}&command=%2F{command[1:]}&text={text}&n={next(COUNTER)}".encode()


def discord_headers(body, sign=SIGN, ts=NOW):
    return {"X-Signature-Timestamp": str(ts), "X-Signature-Ed25519": sign(str(ts).encode() + body).hex()}


def discord_body(value="status", user="100", channel="200", guild="300", kind=2):
    return json.dumps({"type": kind, "channel_id": channel, "guild_id": guild, "member": {"user": {"id": user}}, "id": str(next(COUNTER)), "data": {"name": "monitor", "options": [{"name": "command", "type": 3, "value": value}]}}).encode()


class Base(unittest.TestCase):
    def setUp(self):
        inbound.reset()
        localguard.reset_limits()
        patch = mock.patch.dict(envguard.HELD, ENV)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(inbound.reset)

    def slack(self, body, headers=None, cfg=None, now=NOW, snap=None):
        return inbound.handle("slack", cfg if cfg is not None else config(), body, headers if headers is not None else slack_headers(body), lambda: snap or SNAP, now)

    def discord(self, body, headers=None, cfg=None, now=NOW, snap=None):
        return inbound.handle("discord", cfg if cfg is not None else config(), body, headers if headers is not None else discord_headers(body), lambda: snap or SNAP, now)


class Off(Base):
    def test_it_is_off_by_default_and_closed_without_the_proof(self):
        self.assertEqual(self.slack(slack_body(), cfg={})[0], 404)
        self.assertEqual(self.discord(discord_body(), cfg={})[0], 404)
        self.assertFalse(inbound.settings({})["enabled"])
        self.assertIs(am.DEFAULTS["chatops"]["enabled"], False)
        envguard.HELD.pop("MONITOR_SLACK_SIGNING_SECRET")
        self.assertEqual(self.slack(slack_body())[0], 404)
        self.assertEqual(inbound.state(config(), "slack"), "undefined")
        for cfg in ({"chatops": {"enabled": True, "slack": {"enabled": False}}}, {"chatops": {"enabled": False, "slack": {"enabled": True}}}):
            self.assertEqual(self.slack(slack_body(), cfg=cfg)[0], 404)

    def test_a_short_secret_and_a_bad_public_key_keep_the_platform_closed(self):
        with mock.patch.dict(envguard.HELD, {"MONITOR_SLACK_SIGNING_SECRET": "short", "MONITOR_DISCORD_PUBLIC_KEY": "zz" * 32}):
            self.assertEqual(self.slack(slack_body())[0], 404)
            self.assertEqual(self.discord(discord_body())[0], 404)
            self.assertIn(i18n.t("chatops.no_proof"), inbound.status_text(config()))


class SlackProof(Base):
    def test_a_good_signature_gets_an_answer_only_the_asker_sees(self):
        code, answer, record = self.slack(slack_body("status"))
        self.assertEqual(code, 200)
        self.assertEqual(answer["response_type"], "ephemeral")
        self.assertIn("2 red", answer["text"])
        self.assertEqual((record["command"], record["result"], record["user"]), ("status", "ok", "U1"))

    def test_a_bad_stale_future_or_garbled_signature_is_refused_before_anything_is_read(self):
        body = slack_body()
        good = slack_headers(body)
        self.assertEqual(self.slack(body, {**good, "X-Slack-Signature": "v0=" + "0" * 64})[0], 401)
        self.assertEqual(self.slack(body, slack_headers(body, secret="x" * 32))[0], 401)
        self.assertEqual(self.slack(body, slack_headers(body, ts=NOW - 301))[0], 401)
        self.assertEqual(self.slack(body, slack_headers(body, ts=NOW + 301))[0], 401)
        self.assertEqual(self.slack(body, {**good, "X-Slack-Signature": "v0=é"})[0], 401)
        self.assertEqual(self.slack(body, {})[0], 401)
        self.assertEqual(self.slack(body + b"&x=1", good)[0], 401)        # the body was changed
        self.assertEqual(self.slack(body, {**good, "X-Slack-Request-Timestamp": "abc"})[0], 401)

    def test_the_age_window_can_be_shorter_but_never_longer_than_five_minutes(self):
        body = slack_body()
        self.assertEqual(self.slack(body, slack_headers(body, ts=NOW - 100), cfg=config(max_age_seconds=60))[0], 401)
        self.assertEqual(self.slack(body, slack_headers(body, ts=NOW - 400), cfg=config(max_age_seconds=9999))[0], 401)

    def test_a_signature_cannot_be_used_twice(self):
        body = slack_body()
        headers = slack_headers(body)
        self.assertEqual(self.slack(body, headers)[0], 200)
        code, answer, record = self.slack(body, headers)
        self.assertEqual((code, answer.get("duplicate"), record), (202, True, None))

    def test_a_huge_body_is_refused_without_a_check(self):
        body = b"a" * (inbound.MAX_BODY + 1)
        self.assertEqual(self.slack(body)[0], 413)

    def test_the_challenge_is_answered_after_the_signature_and_only_with_a_plain_text(self):
        body = json.dumps({"type": "url_verification", "challenge": "abc123"}).encode()
        self.assertEqual(self.slack(body)[:2], (200, {"challenge": "abc123"}))
        bad = json.dumps({"type": "url_verification", "challenge": "<script>"}).encode()
        self.assertEqual(self.slack(bad)[0], 400)
        self.assertEqual(self.slack(body, slack_headers(body, secret="y" * 32))[0], 401)
        events = json.dumps({"type": "event_callback"}).encode()
        self.assertEqual(self.slack(events)[0], 202)

    def test_a_request_that_is_not_a_slash_command_is_a_bad_request(self):
        for body in (b"team_id=T1", b"team_id=T1&channel_id=C1&user_id=<x>&command=%2Fm", b"\xff\xfe", b"[1]"):
            self.assertEqual(self.slack(body)[0], 400, body)


class DiscordProof(Base):
    def test_rfc8032_vectors(self):
        pub = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        sig = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        self.assertTrue(sigverify.ed25519_verify(pub, b"", sig))
        self.assertFalse(sigverify.ed25519_verify(pub, b"x", sig))
        pub2 = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
        sig2 = bytes.fromhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
        self.assertTrue(sigverify.ed25519_verify(pub2, b"\x72", sig2))
        self.assertFalse(sigverify.ed25519_verify(pub2, b"\x73", sig2))

    def test_a_good_signature_gets_an_ephemeral_answer_that_mentions_nobody(self):
        code, answer, record = self.discord(discord_body("red"))
        self.assertEqual(code, 200)
        self.assertEqual((answer["type"], answer["data"]["flags"], answer["data"]["allowed_mentions"]), (4, 64, {"parse": []}))
        self.assertIn("app", answer["data"]["content"])
        self.assertEqual(record["command"], "red")

    def test_the_ping_is_answered_with_a_pong_after_the_signature(self):
        body = json.dumps({"type": 1}).encode()
        self.assertEqual(self.discord(body)[:2], (200, {"type": 1}))
        self.assertEqual(self.discord(body, discord_headers(body, sign=OTHER_SIGN))[0], 401)

    def test_a_bad_wrong_key_stale_or_changed_signature_is_refused(self):
        body = discord_body()
        good = discord_headers(body)
        self.assertEqual(self.discord(body, discord_headers(body, sign=OTHER_SIGN))[0], 401)
        self.assertEqual(self.discord(body, discord_headers(body, ts=NOW - 301))[0], 401)
        self.assertEqual(self.discord(body + b" ", good)[0], 401)
        self.assertEqual(self.discord(body, {**good, "X-Signature-Ed25519": "00" * 64})[0], 401)
        self.assertEqual(self.discord(body, {**good, "X-Signature-Ed25519": "zz" * 64})[0], 401)
        self.assertEqual(self.discord(body, {**good, "X-Signature-Ed25519": "ab"})[0], 401)
        self.assertEqual(self.discord(body, {})[0], 401)

    def test_a_signature_cannot_be_used_twice(self):
        body = discord_body()
        headers = discord_headers(body)
        self.assertEqual(self.discord(body, headers)[0], 200)
        self.assertEqual(self.discord(body, headers)[0], 202)

    def test_other_kinds_of_interaction_and_odd_ids_are_not_commands(self):
        self.assertEqual(self.discord(discord_body(kind=3))[0], 202)
        self.assertEqual(self.discord(discord_body(user="1x"))[0], 400)
        self.assertEqual(self.discord(b"{bad", discord_headers(b"{bad"))[0], 400)


class Lists(Base):
    def test_with_no_list_at_all_no_command_runs_but_the_challenge_still_works(self):
        cfg = {"chatops": {"enabled": True, "slack": {"enabled": True}}}
        code, answer, record = self.slack(slack_body(), cfg=cfg)
        self.assertEqual((code, answer["text"], record["result"]), (200, i18n.t("chatops.denied"), "denied"))
        challenge = json.dumps({"type": "url_verification", "challenge": "ok1"}).encode()
        self.assertEqual(self.slack(challenge, cfg=cfg)[0], 200)

    def test_every_list_with_entries_must_match(self):
        cfg = config(allowed_channels=["C9"])
        self.assertEqual(self.slack(slack_body(), cfg=cfg)[2]["result"], "denied")
        self.assertEqual(self.slack(slack_body(channel="C9"), cfg=cfg)[2]["result"], "ok")
        self.assertEqual(self.slack(slack_body(user="U7", channel="C9"), cfg=cfg)[2]["result"], "denied")
        cfg = config(allowed_teams=["T9"])
        self.assertEqual(self.slack(slack_body(team="T1"), cfg=cfg)[2]["result"], "denied")
        self.assertEqual(self.discord(discord_body(guild="300"), cfg=config(allowed_teams=["300"]))[2]["result"], "ok")
        self.assertEqual(self.discord(discord_body(guild="301"), cfg=config(allowed_teams=["300"]))[2]["result"], "denied")

    def test_a_denied_person_learns_nothing(self):
        text = self.slack(slack_body(user="U7"))[1]["text"]
        self.assertEqual(text, i18n.t("chatops.denied"))


class Commands(Base):
    def run_text(self, text, cfg=None, snap=None):
        cfg = cfg or config(rate_per_user_per_minute=600, rate_per_channel_per_minute=600, rate_per_minute=6000)
        return self.slack(slack_body(text), cfg=cfg, snap=snap, headers=None)[1]["text"]

    def test_the_closed_list_answers_and_nothing_else_does(self):
        self.assertEqual(sorted(commands.COMMANDS), ["alerts", "help", "queue", "red", "score", "status"])
        self.assertIn("help", self.run_text("help"))
        self.assertIn("3", self.run_text("alerts"))
        self.assertIn("ci.red in app", self.run_text("alerts"))
        self.assertIn("app: ci", self.run_text("red"))
        self.assertIn("private-1: red for", self.run_text("red"))
        self.assertIn("Queued: 2", self.run_text("queue"))
        self.assertIn("88", self.run_text("score"))
        for word in ("rerun", "cancel", "set", "settings", "dispatch", "merge", "token", "exec", "delete", "run", "config"):
            self.assertEqual(self.run_text(word + " repo"), i18n.t("chatops.unknown"), word)

    def test_a_word_after_the_command_is_ignored_and_the_default_is_help(self):
        self.assertEqual(self.run_text("red rerun everything"), self.run_text("red"))
        self.assertIn("help", self.run_text(""))

    def test_the_list_can_be_narrowed_never_widened(self):
        cfg = config(allowed_words=["status"], rate_per_user_per_minute=600)
        self.assertEqual(self.run_text("alerts", cfg=cfg), i18n.t("chatops.unknown"))
        self.assertIn("2 red", self.run_text("status", cfg=cfg))
        self.assertEqual(inbound.settings(config(allowed_words=["status", "rerun"]))["allowed_words"], ["status"])
        self.assertEqual(settings_api.check_value("chatops.allowed_words", ["status", "rerun"]), (False, "names"))
        self.assertEqual(settings_api.check_value("chatops.allowed_words", ["status"]), (True, ["status"]))

    def test_rows_are_limited_and_the_rest_is_counted(self):
        snap = dict(SNAP, red=[{"repo": "r%d" % i, "workflow": "w", "seconds": 60, "streak": 1} for i in range(9)], fleet=dict(SNAP["fleet"], red=9))
        text = self.run_text("red", cfg=config(max_rows=3), snap=snap)
        self.assertEqual(len([line for line in text.splitlines() if line.startswith("- ")]), 3)
        self.assertIn("6 more", text)

    def test_nothing_loaded_yet(self):
        self.assertEqual(self.run_text("status", snap={"loaded": False}), i18n.t("chatops.nodata"))

    def test_the_commands_cannot_reach_github_or_the_configuration(self):
        source = (HERE / "src" / "github_actions_monitor" / "chatops" / "commands.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "urllib", "socket", "open(", "toolconfig", "ghactions", "os.environ", "envguard"):
            self.assertNotIn(forbidden, source, forbidden)


class Escaping(unittest.TestCase):
    EVIL = "<!channel> <@U1> *bold* `code` [x](http://evil.example) @everyone _i_ ~s~ |p| \x00‮" + "z" * 300

    def test_slack_cannot_get_a_mention_a_link_or_a_format(self):
        text = render.slack_escape(self.EVIL, 120)
        for bad in ("<", ">", "*", "`", "_", "~", "|", "\x00", "‮"):
            self.assertNotIn(bad, text)
        self.assertLessEqual(len(text), 130)

    def test_discord_cannot_get_a_mention_a_link_or_a_format(self):
        text = render.discord_escape(self.EVIL, 120)
        self.assertNotIn("@everyone", text)
        self.assertNotIn("](", text.replace("\\]\\(", ""))
        for bad in ("<", "`", "[", "\x00", "‮"):
            self.assertNotIn(bad.replace("[", "\\["), text.replace("\\" + bad, "")) if bad != "\x00" else self.assertNotIn(bad, text)

    def test_a_hostile_name_goes_through_a_command_escaped(self):
        snap = dict(SNAP, red=[{"repo": "<!channel>", "workflow": "[x](http://evil.example)", "seconds": 1, "streak": 1}])
        text = "\n".join(commands.run("red", snap, 5, render.slack_escape))
        self.assertNotIn("<!channel>", text)
        text = "\n".join(commands.run("red", snap, 5, render.discord_escape))
        self.assertNotIn("](", text.replace("\\]\\(", ""))
        self.assertNotIn("http://evil.example)", text)

    def test_a_row_without_a_link_has_none_and_the_only_link_is_a_repository_address(self):
        for name in commands.COMMANDS:
            self.assertNotIn("http", "\n".join(commands.run(name, SNAP, 8, render.slack_escape)))
        self.assertEqual(render.link("https://github.com/me/app"), "<https://github.com/me/app>")
        self.assertEqual(render.link("https://ghe.example.org/me/app.v2"), "<https://ghe.example.org/me/app.v2>")
        for bad in ("http://github.com/me/app", "https://github.com/me", "https://github.com/me/app/issues", "https://github.com/me/app?x=1", "https://github.com/me/..", "javascript:alert(1)",
                    "https://github.com/me/app> <@U1", "https://github.com/me/a pp", "https://github.com/me/app\n", None, 7):
            self.assertEqual(render.link(bad), "", bad)
        snap = dict(SNAP, red=[dict(SNAP["red"][0], link="https://github.com/me/app"), dict(SNAP["red"][1], link="https://evil.example/x/y/z")],
                    alerts={"total": 1, "rows": [{"level": "error", "code": "ci.red", "repo": "app", "link": "https://github.com/me/app"}]})
        red = "\n".join(commands.run("red", snap, 8, render.discord_escape))
        self.assertIn("<https://github.com/me/app>", red)
        self.assertNotIn("evil", red)
        self.assertIn("<https://github.com/me/app>", "\n".join(commands.run("alerts", snap, 8, render.slack_escape)))


class Snapshot(unittest.TestCase):
    """The adapter of the monitor: names and links follow chatops.show_repo_names and chatops.links."""

    def snapshot(self, **chat):
        state = {"repos": ["pub", "priv"], "repo_meta": {"pub": {"private": False}, "priv": {"private": True}}}
        alerts = {"alerts": [{"level": "error", "code": "ci.red", "repo": "pub"}, {"level": "weird", "code": "Bad Code!", "repo": "priv"}, {"level": "info", "code": "x", "repo": None}], "summary": {"total": 3}}

        def screens(kind, cfg):
            names = am.screens.Names(state["repos"], state["repo_meta"], cfg["show_repo_names"])
            return {"fleet": {"red": 2}, "queue": {}, "score": {}, "top_red": [{"repo": names.name("pub"), "workflow": "ci", "seconds": 5, "streak": 1}, {"repo": names.name("priv"), "workflow": "", "seconds": 5, "streak": 1}]}
        with mock.patch.dict(am.STATE, {"data": state}), mock.patch.object(am, "alerts_payload", lambda ask: alerts), mock.patch.object(am, "screens_payload", screens), \
                mock.patch.object(am.toolconfig, "github_owner", lambda config=None: "me"), mock.patch.dict(am.os.environ, {"GH_HOST": ""}):
            return am.chatops_snapshot({"chatops": chat})

    def test_the_default_hides_the_name_of_a_private_repository(self):
        snap = self.snapshot()
        self.assertEqual([r["repo"] for r in snap["red"]], ["pub", "private-1"])

    def test_all_names_and_links_including_private_repositories_when_asked(self):
        snap = self.snapshot(show_repo_names="all")
        self.assertEqual([r["repo"] for r in snap["red"]], ["pub", "priv"])
        self.assertEqual([r["link"] for r in snap["red"]], ["https://github.com/me/pub", "https://github.com/me/priv"])
        self.assertEqual([r["link"] for r in snap["alerts"]["rows"]], ["https://github.com/me/pub", "https://github.com/me/priv", None])
        self.assertEqual([r["code"] for r in snap["alerts"]["rows"]], ["ci.red", "other", "x"])
        self.assertEqual(snap["alerts"]["rows"][1]["level"], "info")

    def test_public_hides_the_private_name_and_its_link(self):
        snap = self.snapshot(show_repo_names="public")
        self.assertEqual([(r["repo"], r["link"]) for r in snap["red"]], [("pub", "https://github.com/me/pub"), ("private-1", None)])
        self.assertEqual([r["repo"] for r in snap["alerts"]["rows"]], ["pub", "private-1", None])

    def test_none_and_the_switch_remove_every_link(self):
        self.assertTrue(all(r["link"] is None for r in self.snapshot(show_repo_names="none")["red"]))
        snap = self.snapshot(links=False)
        self.assertTrue(all(r["link"] is None for r in snap["red"] + snap["alerts"]["rows"]))


class Limits(Base):
    def test_a_flood_from_one_person_gets_a_short_refusal(self):
        cfg = config(rate_per_user_per_minute=3)
        results = []
        for i in range(5):
            body = slack_body("status", user="U1")
            results.append(self.slack(body, cfg=cfg)[1]["text"])
        self.assertEqual(results[:3].count(i18n.t("chatops.limit")), 0)
        self.assertEqual(results[3:], [i18n.t("chatops.limit")] * 2)

    def test_a_channel_and_the_whole_chat_have_a_ceiling_too(self):
        cfg = config(rate_per_channel_per_minute=2, allowed_users=[])
        cfg["chatops"]["allowed_channels"] = ["C1"]
        out = [self.slack(slack_body("status", user="U%d" % i), cfg=cfg)[1]["text"] for i in range(4)]
        self.assertEqual(out[2:], [i18n.t("chatops.limit")] * 2)
        localguard.reset_limits()
        cfg = config(rate_per_minute=1)
        out = [self.slack(slack_body("status", user="U1"), cfg=cfg)[1]["text"] for i in range(2)]
        self.assertEqual(out[1], i18n.t("chatops.limit"))

    def test_a_slow_answer_is_cut_at_the_time_of_the_platform(self):
        def slow():
            time.sleep(0.6)
            return SNAP
        start = time.perf_counter()
        text = inbound.answer_text("status", slow, inbound.settings(config()), "slack", timeout=0.05)
        self.assertEqual(text, i18n.t("chatops.busy"))
        self.assertLess(time.perf_counter() - start, _timing.limit(0.5))

    def test_a_failing_snapshot_gives_a_plain_sentence_and_nothing_of_the_error(self):
        def boom():
            raise RuntimeError("secret detail")
        text = inbound.answer_text("status", boom, inbound.settings(config()), "slack", timeout=2)
        self.assertEqual(text, i18n.t("chatops.busy"))

    def test_the_stats_and_the_status_never_hold_a_secret(self):
        self.slack(slack_body())
        self.slack(slack_body(), slack_headers(slack_body(), secret="y" * 32))
        shown = json.dumps(inbound.stats()) + inbound.status_text(config()) + inbound.state(config(), "slack") + inbound.state(config(), "discord")
        self.assertNotIn(SECRET, shown)
        self.assertNotIn(PUBLIC.hex(), shown)
        self.assertEqual(inbound.stats()["slack.bad_signature"], 1)


class Schema(unittest.TestCase):
    def test_the_settings_are_in_the_schema_the_example_and_the_eight_languages(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))["chatops"]
        self.assertEqual(example["enabled"], False)
        self.assertEqual(inbound.settings({"chatops": example}), inbound.settings({}))
        keys = [k for k in settings_api.META if k.startswith("chatops.")]
        self.assertGreaterEqual(len(keys), 15)
        for key in keys:
            self.assertTrue(settings_api.META[key]["secure"] or key.endswith(".state") or key.startswith("chatops.max_") or key.startswith("chatops.rate_"), key)
            for lang in ("en", "es", "de", "fr", "it", "ja", "pt", "zh"):
                for text_key in ("cfg.f." + key, "cfg.h." + key):
                    self.assertNotEqual(i18n.tl(lang, text_key), text_key, (lang, text_key))
        for lang in ("en", "es", "de", "fr", "it", "ja", "pt", "zh"):
            for text_key in ("ui.cfg_b_chatops", "mon.chatops", "chatops.help", "chatops.status", "chatops.red_line"):
                self.assertNotEqual(i18n.tl(lang, text_key), text_key, (lang, text_key))

    def test_the_routes_are_recorded_and_the_proof_is_the_signature(self):
        from github_actions_monitor.security import audited_posts, auth
        for route in ("/api/chatops/slack", "/api/chatops/discord"):
            self.assertIn(route, audited_posts.EXEMPT)
            self.assertIn(route, auth.PUBLIC)

    def test_a_value_that_is_not_valid_falls_back_to_the_conservative_default(self):
        cfg = inbound.settings({"chatops": {"enabled": "yes", "max_rows": 999, "show_repo_names": "x", "allowed_users": "U1", "slack": {"enabled": 1, "signing_secret_env": "lower case"}}})
        self.assertEqual((cfg["enabled"], cfg["max_rows"], cfg["show_repo_names"], cfg["allowed_users"], cfg["slack"]["enabled"], cfg["slack"]["env"]),
                         (False, 8, "public", [], False, "MONITOR_SLACK_SIGNING_SECRET"))
        self.assertIs(inbound.settings({})["links"], True)
        self.assertIs(inbound.settings({"chatops": {"links": False}})["links"], False)
        self.assertIs(am.DEFAULTS["chatops"]["links"], True)
        self.assertEqual(am.DEFAULTS["chatops"]["show_repo_names"], "public")


class Route(unittest.TestCase):
    def setUp(self):
        inbound.reset()
        localguard.reset_limits()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "audit_actions.jsonl"
        audit_log.FILE = self.log
        audit_log._last.update(path=None, hash="")
        self.addCleanup(lambda: (setattr(audit_log, "FILE", None), audit_log._last.update(path=None, hash="")))
        patch = mock.patch.dict(envguard.HELD, ENV)
        patch.start()
        self.addCleanup(patch.stop)

    def post(self, server, path, body, headers):
        request = urllib.request.Request(server.base + path, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:
                return answer.status, json.loads(answer.read() or b"{}")
        except urllib.error.HTTPError as error:
            with error:
                return error.code, {}

    def test_the_route_is_closed_when_off_and_signed_requests_work_when_on(self):
        saved = am.STATE["data"]
        am.STATE["data"] = None        # another test may have left a state behind: this one is about a monitor that has read nothing yet
        self.addCleanup(am.STATE.__setitem__, "data", saved)
        now = int(time.time())
        body = slack_body("status")
        with LiveServer({}) as server:
            self.assertEqual(self.post(server, "/api/chatops/slack", body, slack_headers(body, ts=now))[0], 404)
        with LiveServer(config()) as server:
            self.assertEqual(self.post(server, "/api/chatops/slack", body, {})[0], 401)
            code, answer = self.post(server, "/api/chatops/slack", body, slack_headers(body, ts=now))
            self.assertEqual((code, answer["text"]), (200, i18n.t("chatops.nodata")))
            ping = json.dumps({"type": 1}).encode()
            self.assertEqual(self.post(server, "/api/chatops/discord", ping, discord_headers(ping, ts=now)), (200, {"type": 1}))
            self.assertEqual(self.post(server, "/api/chatops/discord", ping, discord_headers(ping, sign=OTHER_SIGN, ts=now))[0], 401)
            self.assertEqual(self.post(server, "/api/chatops/other", ping, {})[0], 404)
        lines = [json.loads(x) for x in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(x["action"], x["target"], x["result"]) for x in lines], [("chatops_command", "slack:status", "ok")])
        self.assertNotIn(SECRET, self.log.read_text(encoding="utf-8"))
        self.assertNotIn("status&", self.log.read_text(encoding="utf-8"))

    def test_the_network_mode_does_not_ask_the_platform_for_the_access_token(self):
        now = int(time.time())
        body = slack_body("help")
        with LiveServer(config(), network="T" * 24) as server:
            self.assertEqual(self.post(server, "/api/chatops/slack", body, slack_headers(body, ts=now))[0], 200)


if __name__ == "__main__":
    unittest.main()
