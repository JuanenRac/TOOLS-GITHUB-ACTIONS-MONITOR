# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Notifications for each user of the team mode: the preferences, who is told what, the channels (ntfy, Teams, e-mail by a relay of this computer), the digests of unseen alerts and the
secrets of the channels.

1. The secrets of the channels never come back in an answer, a configuration or a log; they leave with the user.
2. The channels are off by default and judge their destination (a server that is not https, an address of Microsoft only, a header that cannot be split).
3. The dispatcher tells a user only what their role, their accounts, their sentinels and their lowest level allow; it caps the hour and does not undo itself under threads.
4. A digest gathers what the user has not seen; seeing it drops it; it is not sent twice.
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_auth as ta  # noqa: E402
from github_actions_monitor.integrations import channels, dispatcher  # noqa: E402
from github_actions_monitor.security import auth, channel_secrets  # noqa: E402

PASSWORD = "correct horse battery"
TEAMS_URL = "https://contoso.webhook.office.com/webhookb2/abc/IncomingWebhook/def/ghi"
SECRET_PROBE = "REDACTION-PROBE-" + "9f3c"


class Answer:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Opener:
    """The opener of a test: remembers the requests it was given."""

    def __init__(self, fail=None):
        self.requests, self.fail = [], fail

    def __call__(self, request, timeout=8):
        self.requests.append(request)
        if self.fail:
            raise self.fail
        return Answer()


class Smtp:
    sent = []

    def __init__(self, host, port, timeout=8):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send_message(self, mail):
        Smtp.sent.append(mail)


class Quiet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.environ.pop, "MONITOR_SECRET_BACKEND", None)
        self.addCleanup(os.environ.pop, "MONITOR_SECRET_DIR", None)
        os.environ["MONITOR_SECRET_BACKEND"] = "file"
        os.environ["MONITOR_SECRET_DIR"] = str(Path(self.tmp.name) / "secrets")
        dispatcher._sent.clear()
        Smtp.sent = []


class Secrets(Quiet):
    def test_a_secret_goes_in_comes_out_and_goes_away(self):
        self.assertEqual(channel_secrets.put("user.ana.teams", TEAMS_URL), (True, "file"))
        self.assertEqual(channel_secrets.get("user.ana.teams"), TEAMS_URL)
        self.assertTrue(channel_secrets.has("user.ana.teams"))
        self.assertTrue(channel_secrets.delete("user.ana.teams"))
        self.assertEqual(channel_secrets.get("user.ana.teams"), "")

    def test_a_bad_name_or_value_is_refused_and_nothing_is_written(self):
        for name in ("../x", "A", "", "a b", "x" * 90):
            self.assertEqual(channel_secrets.put(name, "value")[0], False, name)
        for value in ("", "   ", "a\nb", "x" * 2001, "bell\x07"):
            self.assertEqual(channel_secrets.put("user.ana.teams", value), (False, "format"))
        self.assertFalse(list((Path(self.tmp.name) / "secrets").glob("*")) if (Path(self.tmp.name) / "secrets").exists() else [])

    @unittest.skipIf(os.name == "nt", "modes of a file are a POSIX idea")
    def test_the_file_is_private(self):
        channel_secrets.put("user.ana.ntfy", "tk_" + SECRET_PROBE)
        path = Path(self.tmp.name) / "secrets" / "notify-user.ana.ntfy.600"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)


class TheChannels(Quiet):
    MESSAGE = {"title": "repo-a", "text": "CI is red", "url": "https://github.com/o/repo-a/actions/runs/1", "level": "bad", "repo": "repo-a"}

    def test_every_channel_is_off_by_default(self):
        for name, plugin in channels.PLUGINS.items():
            self.assertIs(plugin.defaults["enabled"], False, name)
            self.assertEqual(channels.deliver(name, channels.server_defaults()[name], {"topic": "t", "address": "a@b.cc"}, TEAMS_URL, self.MESSAGE, Opener(), smtp=Smtp), {"channel": name, "ok": False, "reason": "off"})

    def test_ntfy_sends_a_title_a_priority_a_link_and_the_token(self):
        opener = Opener()
        server = {"enabled": True, "server": "https://ntfy.example.org"}
        answer = channels.deliver("ntfy", server, {"topic": "my-topic"}, "tk_" + SECRET_PROBE, self.MESSAGE, opener)
        self.assertTrue(answer["ok"], answer)
        request = opener.requests[0]
        self.assertEqual(request.full_url, "https://ntfy.example.org/my-topic")
        self.assertEqual((request.get_header("Title"), request.get_header("Priority"), request.get_header("Authorization")), ("repo-a", "5", "Bearer tk_" + SECRET_PROBE))
        self.assertIn(b"CI is red", request.data)
        self.assertNotIn(SECRET_PROBE, json.dumps(answer))

    def test_ntfy_refuses_a_server_that_is_not_https_and_a_topic_with_a_path(self):
        for bad in ("http://ntfy.example.org", "ftp://x.org", "https://user:pw@ntfy.example.org", "ntfy.sh"):
            self.assertEqual(channels.deliver("ntfy", {"enabled": True, "server": bad}, {"topic": "t"}, "", self.MESSAGE, Opener())["reason"], "bad_host", bad)
        for topic in ("a/b", "../x", "", "a b", "x" * 65):
            self.assertEqual(channels.deliver("ntfy", {"enabled": True, "server": "https://ntfy.sh"}, {"topic": topic}, "", self.MESSAGE, Opener())["reason"], "bad_value", topic)

    def test_ntfy_on_this_computer_is_allowed_over_http(self):
        self.assertIsNone(channels.PLUGINS["ntfy"].check_server({"enabled": True, "server": "http://127.0.0.1:8080"}))

    def test_a_header_cannot_be_split_by_the_text(self):
        opener = Opener()
        channels.deliver("ntfy", {"enabled": True, "server": "https://ntfy.sh"}, {"topic": "t"}, "", {**self.MESSAGE, "title": "a\r\nX-Evil: 1", "url": "https://x.org/\r\nX-Evil: 2"}, opener)
        request = opener.requests[0]
        self.assertNotIn("X-evil", {k.lower().capitalize() for k in request.headers})
        self.assertNotIn("\n", request.get_header("Title"))
        self.assertNotIn("\n", request.get_header("Click"))

    def test_teams_takes_only_a_webhook_of_microsoft(self):
        opener = Opener()
        self.assertTrue(channels.deliver("teams", {"enabled": True}, {}, TEAMS_URL, self.MESSAGE, opener)["ok"])
        self.assertEqual(json.loads(opener.requests[0].data)["text"], "CI is red\nhttps://github.com/o/repo-a/actions/runs/1")
        for url in ("https://evil.example.org/hook", "http://x.webhook.office.com/a", "https://webhook.office.com.evil.org/a", "https://u:p@x.webhook.office.com/a"):
            self.assertEqual(channels.deliver("teams", {"enabled": True}, {}, url, self.MESSAGE, Opener())["reason"], "bad_host", url)
        self.assertEqual(channels.deliver("teams", {"enabled": True}, {}, "", self.MESSAGE, Opener())["reason"], "no_secret")

    def test_the_mail_goes_to_a_relay_of_this_computer_with_clean_headers(self):
        server = {"enabled": True, "host": "127.0.0.1", "port": 25, "sender": "monitor@localhost.test"}
        answer = channels.deliver("email", server, {"address": "ana@example.org"}, "", {**self.MESSAGE, "title": "repo\r\nBcc: x@y.zz"}, smtp=Smtp)
        self.assertTrue(answer["ok"], answer)
        mail = Smtp.sent[0]
        self.assertEqual((mail["To"], mail["From"]), ("ana@example.org", "monitor@localhost.test"))
        self.assertIsNone(mail["Bcc"])
        self.assertNotIn("\n", mail["Subject"])

    def test_the_relay_is_this_computer_unless_private_targets_are_allowed(self):
        for host in ("smtp.example.org", "192.168.1.5", "10.0.0.2"):
            self.assertEqual(channels.PLUGINS["email"].check_server({"enabled": True, "host": host, "port": 25, "sender": "m@x.test"}), "bad_host", host)
        self.assertIsNone(channels.PLUGINS["email"].check_server({"enabled": True, "host": "192.168.1.5", "port": 25, "sender": "m@x.test"}, allow_private=True))
        self.assertEqual(channels.PLUGINS["email"].check_server({"enabled": True, "host": "smtp.example.org", "port": 25, "sender": "m@x.test"}, allow_private=True), "bad_host")

    def test_a_bad_address_is_refused(self):
        server = {"enabled": True, "host": "127.0.0.1", "port": 25, "sender": "monitor@localhost.test"}
        for address in ("a@b", "a b@c.dd", "a@b.cc\nBcc: x@y.zz", "", "x" * 300 + "@a.bb"):
            self.assertEqual(channels.deliver("email", server, {"address": address}, "", self.MESSAGE, smtp=Smtp)["reason"], "bad_value", address)
        self.assertEqual(Smtp.sent, [])

    def test_a_failed_send_is_reported_without_the_secret(self):
        answer = channels.deliver("ntfy", {"enabled": True, "server": "https://ntfy.sh"}, {"topic": "t"}, "tk_" + SECRET_PROBE, self.MESSAGE, Opener(fail=OSError("boom " + SECRET_PROBE)))
        self.assertEqual((answer["ok"], answer["reason"]), (False, "failed"))
        self.assertNotIn(SECRET_PROBE, json.dumps(answer))


class Team(Quiet):
    def setUp(self):
        super().setUp()
        self.storage = ta.new_storage(Path(self.tmp.name) / "data")
        self.addCleanup(self.storage.close)
        auth.use_storage(self.storage)
        self.addCleanup(auth.use_storage, None)
        for name, role, accounts in (("root", "admin", None), ("mia", "maintainer", ["alpha"]), ("vic", "viewer", ["alpha"]), ("zoe", "viewer", ["beta"])):
            user, code = auth.create_user(self.storage, name, PASSWORD, role, accounts)
            self.assertEqual(code, "", name)
        self.config = {"notify": {"users": {"enabled": True}, "channels": {"ntfy": {"enabled": True, "server": "https://ntfy.example.org"}, "email": {"enabled": True, "host": "127.0.0.1", "port": 25, "sender": "monitor@localhost.test"}}}}

    def prefs(self, user, **more):
        body = {"enabled": True, "channels": ["ntfy"], "destinations": {"ntfy": {"topic": user + "-topic"}}, **more}
        prefs, code = dispatcher.set_prefs(self.storage, user, body)
        self.assertEqual(code, "", (user, body))
        return prefs

    @staticmethod
    def event(kind="red_new", level="bad", repo="repo-a"):
        return {"kind": kind, "code": kind, "level": level, "repo": repo, "owner": "main", "url": "https://github.com/o/" + repo, "text": f"{kind} {repo}"}

    def told(self, event, account="alpha", **kw):
        opener = Opener()
        answers = dispatcher.dispatch(self.config, event, self.storage, account, opener=opener, smtp=Smtp, **kw)
        return sorted(answers), opener


class Preferences(Team):
    def test_by_default_nobody_is_told_anything(self):
        users, opener = self.told(self.event())
        self.assertEqual((users, opener.requests), ([], []))
        self.assertEqual(dispatcher.get_prefs(self.storage, "vic")["enabled"], False)

    def test_the_whole_thing_is_off_without_its_own_switch(self):
        self.prefs("vic")
        self.config["notify"]["users"]["enabled"] = False
        self.assertEqual(self.told(self.event())[0], [])
        self.assertEqual(dispatcher.settings({"notify": {"users": {"enabled": "yes"}}})["enabled"], False, "only a real true turns it on")

    def test_a_wrong_value_keeps_the_conservative_default(self):
        prefs = dispatcher.clean_prefs({"enabled": "true", "channels": "ntfy", "min_level": "all", "digest": "weekly", "sentinels": ["x"], "destinations": {"ntfy": {"topic": 3}}}, "viewer")
        self.assertEqual((prefs["enabled"], prefs["channels"], prefs["min_level"], prefs["digest"], prefs["sentinels"], prefs["destinations"]), (False, [], "warn", "off", [], {}))

    def test_the_preferences_are_validated_when_saved(self):
        for body, code in (({"channels": ["sms"]}, "channels_invalid"), ({"min_level": "none"}, "min_level_invalid"), ({"digest": "weekly"}, "digest_invalid"), ({"sentinels": ["x"]}, "sentinels_invalid"),
                           ({"channels": ["ntfy"], "destinations": {"ntfy": {"topic": "a/b"}}}, "destination_invalid"), ({"channels": ["teams"]}, "secret_missing"),
                           ({"secrets": {"teams": "https://evil.example.org"}}, "secret_invalid"), ({"secrets": {"email": "x"}}, "secret_invalid"), ({"secrets": {"ntfy": "a\nb"}}, "secret_invalid")):
            self.assertEqual(dispatcher.set_prefs(self.storage, "vic", body)[1], code, body)
        self.assertEqual(dispatcher.get_prefs(self.storage, "vic")["channels"], [], "a refused save changes nothing")
        self.assertEqual(dispatcher.set_prefs(self.storage, "nobody", {})[1], "user_unknown")

    def test_a_secret_is_stored_encrypted_and_never_returned(self):
        prefs, code = dispatcher.set_prefs(self.storage, "vic", {"enabled": True, "channels": ["teams"], "secrets": {"teams": TEAMS_URL}})
        self.assertEqual(code, "")
        self.assertEqual(prefs["secrets"], {"ntfy": False, "teams": True})
        self.assertNotIn("contoso", json.dumps(prefs))
        self.assertNotIn("contoso", json.dumps(self.storage.get_record("users", "vic")), "the record of the user does not carry it")
        self.assertEqual(channel_secrets.get("user.vic.teams"), TEAMS_URL)
        dispatcher.set_prefs(self.storage, "vic", {"secrets": {"teams": ""}})
        self.assertFalse(channel_secrets.has("user.vic.teams"), "an empty text removes it")

    def test_deleting_a_user_deletes_the_secrets(self):
        dispatcher.set_prefs(self.storage, "vic", {"enabled": True, "channels": ["teams"], "secrets": {"teams": TEAMS_URL}})
        self.assertEqual(auth.delete_user(self.storage, "vic"), "")
        self.assertFalse(channel_secrets.has("user.vic.teams"))

    def test_changing_the_password_or_the_role_keeps_the_preferences(self):
        self.prefs("vic", min_level="info")
        auth.update_user(self.storage, "vic", role="maintainer")
        self.assertEqual(dispatcher.get_prefs(self.storage, "vic")["min_level"], "info")


class WhoIsTold(Team):
    def test_the_role_decides_the_families(self):
        for name in ("root", "mia", "vic"):
            self.prefs(name, min_level="info", system=True)
        self.assertEqual(self.told(self.event("red_new"))[0], ["mia", "root", "vic"])
        self.assertEqual(self.told(self.event("pending_sign", "warn"))[0], ["mia", "root"], "a viewer is not told what waits for a person to act")
        self.assertEqual(self.told(self.event("offline", "bad", ""))[0], ["root"], "the system is for the administrator")

    def test_the_accounts_decide_what_a_user_may_hear(self):
        self.prefs("vic")
        self.prefs("zoe")
        self.assertEqual(self.told(self.event(), "alpha")[0], ["vic"])
        self.assertEqual(self.told(self.event(), "beta")[0], ["zoe"])
        self.assertEqual(self.told(self.event(), "gamma")[0], [])

    def test_the_lowest_level_and_the_sentinels_are_respected(self):
        self.prefs("vic", min_level="bad")
        self.prefs("mia", sentinels=["collab"], min_level="info")
        self.assertEqual(self.told(self.event(level="warn"))[0], ["mia"][:0] + [], "a warn is below the level of vic and mia wants only the collaborators")
        self.assertEqual(self.told(self.event(level="bad"))[0], ["vic"])
        self.assertEqual(self.told(self.event("collab_new", "info"))[0], ["mia"])

    def test_an_inactive_user_hears_nothing(self):
        self.prefs("vic")
        auth.update_user(self.storage, "vic", active=False)
        self.assertEqual(self.told(self.event())[0], [])

    def test_an_event_of_an_external_ecosystem_or_an_unknown_kind_is_not_sent(self):
        self.prefs("vic")
        self.assertEqual(self.told({**self.event(), "owner": "other"})[0], [])
        self.assertEqual(self.told(self.event("loaded", "info"))[0], [])

    def test_every_channel_of_the_user_gets_the_message(self):
        self.prefs("vic", channels=["ntfy", "email"], destinations={"ntfy": {"topic": "vic-topic"}, "email": {"address": "vic@example.org"}})
        users, opener = self.told(self.event())
        self.assertEqual((users, len(opener.requests), len(Smtp.sent)), (["vic"], 1, 1))

    def test_a_channel_the_administrator_left_off_sends_nothing(self):
        self.prefs("vic")
        self.config["notify"]["channels"]["ntfy"]["enabled"] = False
        users, opener = self.told(self.event())
        self.assertEqual(opener.requests, [])

    def test_the_cap_of_an_hour_holds_under_threads(self):
        self.prefs("vic")
        self.config["notify"]["users"]["max_per_hour"] = 3
        opener, barrier, results = Opener(), threading.Barrier(12), []

        def go():
            barrier.wait()
            results.append(dispatcher.dispatch(self.config, self.event(), self.storage, "alpha", opener=opener, smtp=Smtp, now=1_800_000_000))
        threads = [threading.Thread(target=go) for _ in range(12)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(self.told(self.event(), now=1_800_000_000 + 3601)[0], ["vic"], "an hour later it is open again")

    def test_a_failing_channel_never_raises(self):
        self.prefs("vic")
        opener = Opener(fail=OSError("down"))
        answers = dispatcher.dispatch(self.config, self.event(), self.storage, "alpha", opener=opener)
        self.assertFalse(answers["vic"][0]["ok"])


class Digests(Team):
    def setUp(self):
        super().setUp()
        self.prefs("vic", digest="hourly", min_level="info")

    def run_digest(self, now):
        opener = Opener()
        answers = dispatcher.run_digests(self.config, self.storage, "alpha", opener=opener, smtp=Smtp, now=now)
        return answers, opener

    def test_an_event_goes_to_the_queue_and_not_to_the_channel(self):
        users, opener = self.told(self.event(), now=1_800_000_000)
        self.assertEqual((users, opener.requests), ([], []))
        self.assertEqual(len(dispatcher.pending(self.storage, "alpha", "vic")), 1)

    def test_the_digest_comes_once_when_its_time_has_come_and_gathers_everything(self):
        for repo in ("r1", "r2", "r3"):
            self.told(self.event(repo=repo), now=1_800_000_000)
        answers, opener = self.run_digest(1_800_000_000 + 10)
        self.assertEqual(sorted(answers), ["vic"], "the first one is due at once")
        text = opener.requests[0].data.decode()
        self.assertTrue(all(r in text for r in ("r1", "r2", "r3")))
        self.assertIn("3", opener.requests[0].get_header("Title"))
        self.assertEqual(self.run_digest(1_800_000_000 + 20)[0], {}, "nothing is sent twice")
        self.told(self.event(repo="r4"), now=1_800_000_100)
        self.assertEqual(self.run_digest(1_800_000_000 + 600)[0], {}, "not before an hour has passed")
        self.assertEqual(sorted(self.run_digest(1_800_000_000 + 3700)[0]), ["vic"])

    def test_what_the_user_has_seen_is_not_sent(self):
        self.told(self.event(), now=1_800_000_000)
        self.assertEqual(dispatcher.mark_seen(self.storage, "vic", ["alpha"]), 1)
        self.assertEqual(self.run_digest(1_800_000_000 + 10)[0], {})

    def test_the_queue_keeps_the_newest_and_a_cap_holds_with_threads(self):
        self.config["notify"]["digest"] = {"max_items": 5}
        threads = [threading.Thread(target=self.told, args=(self.event(repo=f"r{i}"),), kwargs={"now": 1_800_000_000 + i}) for i in range(20)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(dispatcher.pending(self.storage, "alpha", "vic")), 5)

    def test_a_user_who_turned_it_off_gets_no_digest(self):
        self.told(self.event(), now=1_800_000_000)
        dispatcher.set_prefs(self.storage, "vic", {"digest": "off"})
        self.assertEqual(self.run_digest(1_800_000_000 + 10)[0], {})

    def test_the_digest_title_is_in_the_eight_languages(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            data = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertIn("{n}", data["notify.digest_title"], lang)


class OverHttp(unittest.TestCase):
    start = ta.LiveTeam.start
    call = ta.LiveTeam.call
    make_admin = ta.LiveTeam.make_admin
    sign_in = ta.LiveTeam.sign_in
    add_user = ta.LiveTeam.add_user

    def setUp(self):
        self.addCleanup(os.environ.pop, "MONITOR_SECRET_BACKEND", None)
        self.addCleanup(os.environ.pop, "MONITOR_SECRET_DIR", None)
        self.secrets = tempfile.TemporaryDirectory()
        self.addCleanup(self.secrets.cleanup)
        os.environ["MONITOR_SECRET_BACKEND"] = "file"
        os.environ["MONITOR_SECRET_DIR"] = self.secrets.name

    def team(self):
        self.start({"auth": {"enabled": True}, "session_guard": False, "notify": {"users": {"enabled": True}}})
        self.make_admin()
        admin = self.sign_in("root")
        self.add_user(admin, "vic", "viewer", ["alpha"])
        return admin, self.sign_in("vic")

    def test_a_user_reads_and_writes_their_own_preferences_and_the_secret_stays_in(self):
        admin, vic = self.team()
        status, body, _ = self.call("/api/auth/me/notify", headers=vic)
        self.assertEqual((status, body["enabled"], body["prefs"]["enabled"], body["unseen"]), (200, True, False, 0))
        status, body, _ = self.call("/api/auth/me/notify", {"enabled": True, "channels": ["teams"], "secrets": {"teams": TEAMS_URL}}, vic)
        self.assertEqual((status, body["prefs"]["secrets"]["teams"]), (200, True), body)
        raw = json.dumps(self.call("/api/auth/me/notify", headers=vic)[1]) + json.dumps(self.call("/api/auth/notify", headers=admin)[1])
        self.assertNotIn("contoso", raw)
        self.assertNotIn("contoso", Path(self.tmp.name).joinpath("audit.jsonl").read_text(encoding="utf-8"), "the audit has no secret either")

    def test_a_viewer_cannot_read_everybody_and_nobody_signed_in_reads_nothing(self):
        admin, vic = self.team()
        self.assertEqual(self.call("/api/auth/notify", headers=vic)[0], 403)
        self.assertEqual(self.call("/api/auth/me/notify")[0], 401)
        self.assertEqual(self.call("/api/auth/notify", headers=admin)[0], 200)

    def test_a_refused_save_says_why(self):
        _admin, vic = self.team()
        status, body, _ = self.call("/api/auth/me/notify", {"channels": ["sms"]}, vic)
        self.assertEqual((status, body["code"]), (400, "channels_invalid"))

    def test_seeing_the_alerts_and_the_test_message(self):
        _admin, vic = self.team()
        self.assertEqual(self.call("/api/auth/me/notify/seen", {}, vic)[1]["dropped"], 0)
        self.assertEqual(self.call("/api/auth/me/notify/test", {}, vic)[1]["code"], "no_channel")
        self.assertEqual(self.call("/api/auth/me/notify/other", {}, vic)[0], 404)

    def test_without_the_cookie_of_the_session_a_write_is_refused(self):
        _admin, vic = self.team()
        self.assertEqual(self.call("/api/auth/me/notify", {"enabled": True}, {"Cookie": vic["Cookie"]})[1]["code"], "csrf")


if __name__ == "__main__":
    unittest.main()
