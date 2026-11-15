# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Action proposals: hash binding, time to live, re-check at execute, policy, idempotence, audit chain, and that the complete edition never executes anything."""
import copy
import tempfile
import threading
import unittest

import _testenv  # noqa: F401
from github_actions_monitor import phase4
from github_actions_monitor.phase4 import proposals as pr

T0 = 1_800_000_000 - (1_800_000_000 % 86400) + 10 * 3600          # 10:00 UTC of some day


class Clock:
    def __init__(self, now=T0):
        self.now = now

    def __call__(self):
        return self.now


def settings(**over):
    s = copy.deepcopy(phase4.DEFAULTS["proposals"])
    s.update(enabled=True, execute_enabled=True, allowed_actions=["rerun", "label", "comment", "close", "dispatch"], max_per_day=3)
    s.update(over)
    return s


class Runner:
    def __init__(self, result=None, error=None):
        self.calls, self.result, self.error = [], result, error

    def __call__(self, action, account, repo, params, key):
        self.calls.append((action, account, repo, params, key))
        if self.error:
            raise self.error
        return {"ok": True} if self.result is None else self.result


def make(clock=None, **over):
    clock = clock or Clock()
    return pr.ProposalStore(settings(**over), clock=clock), clock


def new(store, **over):
    args = dict(account_id="acc1", repo="o/r", action_type="rerun", params={"run_id": 5}, reason="red", actor="system:ci")
    args.update(over)
    return store.create(**args)


class Create(unittest.TestCase):
    def test_pending_with_a_canonical_hash(self):
        store, _ = make()
        p = new(store)
        self.assertEqual((p["state"], p["created_by"]), ("pending", "system:ci"))
        self.assertEqual(p["content_hash"], pr.content_hash("acc1", "o/r", "rerun", {"run_id": 5}))
        self.assertEqual(pr.content_hash("a", "o/r", "rerun", {"b": 1, "a": 2}), pr.content_hash("a", "o/r", "rerun", {"a": 2, "b": 1}))
        self.assertNotEqual(pr.content_hash("a", "o/r", "rerun", {"a": 1}), pr.content_hash("a", "o/r", "rerun", {"a": 2}))

    def test_the_same_content_is_not_piled_up(self):
        store, _ = make()
        self.assertEqual(new(store)["id"], new(store)["id"])
        self.assertEqual(len(store.list()), 1)
        self.assertNotEqual(new(store, params={"run_id": 6})["id"], new(store)["id"])

    def test_bad_input_is_refused(self):
        store, _ = make()
        for over in ({"repo": "no-slash"}, {"repo": "a/b/c"}, {"account_id": "Bad Id"}, {"action_type": "delete_repo"}, {"actor": "bad actor!"}):
            with self.assertRaises(pr.ProposalError, msg=over):
                new(store, **over)

    def test_secret_looking_keys_and_odd_values_are_refused(self):
        store, _ = make()
        for params in ({"token": "x"}, {"a": {"password": "x"}}, {"Authorization": "x"}, {"k": object()}, {"bad key": 1}, {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}):
            with self.assertRaises(pr.ProposalError, msg=params):
                new(store, params=params)
        with self.assertRaises(pr.ProposalError):
            new(store, params={"text": ["x" * 1000] * 20})

    def test_a_viewer_cannot_propose_but_the_system_can(self):
        store, _ = make()
        with self.assertRaises(pr.ProposalError) as ctx:
            new(store, actor="visitor", role="viewer")
        self.assertEqual(ctx.exception.code, "api.forbidden")
        self.assertEqual(new(store, actor="system:ai", role="viewer")["created_by"], "system:ai")

    def test_long_values_are_cut(self):
        store, _ = make()
        p = new(store, reason="x" * 1000, params={"text": "y" * 5000})
        self.assertEqual((len(p["reason"]), len(p["params"]["text"])), (300, 1000))


class Approve(unittest.TestCase):
    def test_needs_the_hash_the_person_saw(self):
        store, _ = make()
        p = new(store)
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "boss", "admin", "0" * 64)
        self.assertEqual(ctx.exception.code, "act.hash_mismatch")
        self.assertEqual(store.approve(p["id"], "boss", "admin", p["content_hash"])["state"], "approved")

    def test_a_record_changed_behind_the_back_cannot_be_approved(self):
        store, _ = make()
        p = new(store)
        store.proposals[p["id"]]["params"]["run_id"] = 999            # tampered storage
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "boss", "admin", p["content_hash"])
        self.assertEqual(ctx.exception.code, "act.hash_mismatch")

    def test_four_eyes_by_default_and_can_be_relaxed(self):
        store, _ = make()
        p = new(store, actor="alice")
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "alice", "admin", p["content_hash"])
        self.assertEqual(ctx.exception.reason, "four_eyes")
        relaxed, _ = make(four_eyes=False)
        q = new(relaxed, actor="alice")
        self.assertEqual(relaxed.approve(q["id"], "alice", "admin", q["content_hash"])["state"], "approved")

    def test_roles_actions_and_merge(self):
        store, _ = make()
        p = new(store)
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "bob", "maintainer", p["content_hash"])
        self.assertEqual(ctx.exception.reason, "role")
        m = new(store, action_type="merge", params={"number": 3})
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(m["id"], "boss", "admin", m["content_hash"])
        self.assertEqual(ctx.exception.reason, "merge_off")
        on, _ = make(merge_allowed=True)
        m2 = new(on, action_type="merge", params={"number": 3})
        self.assertEqual(on.approve(m2["id"], "boss", "admin", m2["content_hash"])["state"], "approved")
        off, _ = make(allowed_actions=["label"])
        r = new(off)
        with self.assertRaises(pr.ProposalError) as ctx:
            off.approve(r["id"], "boss", "admin", r["content_hash"])
        self.assertEqual(ctx.exception.reason, "action_type")

    def test_a_denial_is_in_the_audit(self):
        store, _ = make()
        p = new(store)
        with self.assertRaises(pr.ProposalError):
            store.approve(p["id"], "bob", "viewer", p["content_hash"])
        self.assertEqual(store.audit()[-1]["event"], "approve_denied")

    def test_state_machine(self):
        store, _ = make()
        p = new(store)
        store.reject(p["id"], "boss", "admin", "no")
        for call in (lambda: store.approve(p["id"], "boss", "admin", p["content_hash"]), lambda: store.reject(p["id"], "boss", "admin")):
            with self.assertRaises(pr.ProposalError) as ctx:
                call()
            self.assertEqual(ctx.exception.code, "act.bad_state")
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve("nope", "boss", "admin", "x")
        self.assertEqual(ctx.exception.code, "api.not_found")

    def test_only_allowed_roles_reject(self):
        store, _ = make()
        p = new(store)
        with self.assertRaises(pr.ProposalError):
            store.reject(p["id"], "bob", "viewer")


class Expiry(unittest.TestCase):
    def test_ttl_applies_to_pending_and_to_approved(self):
        store, clock = make(ttl_seconds=100)
        p, q = new(store), new(store, params={"run_id": 8})
        store.approve(q["id"], "boss", "admin", q["content_hash"])
        clock.now += 100
        self.assertEqual(sorted(store.expire_due()), sorted([p["id"], q["id"]]))
        self.assertEqual(store.get(p["id"])["state"], "expired")
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "boss", "admin", p["content_hash"])
        self.assertEqual(ctx.exception.code, "act.expired")
        self.assertEqual(store.expire_due(), [])

    def test_approving_after_the_time_says_expired(self):
        store, clock = make(ttl_seconds=100)
        p = new(store)
        clock.now += 500
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "boss", "admin", p["content_hash"])
        self.assertEqual(ctx.exception.code, "act.expired")

    def test_an_expired_proposal_can_be_proposed_again(self):
        store, clock = make(ttl_seconds=100)
        a = new(store)
        clock.now += 200
        self.assertNotEqual(new(store)["id"], a["id"])


class Execute(unittest.TestCase):
    def ready(self, **over):
        store, clock = make(**over)
        runner = Runner()
        ex = pr.Executor(store, runner, "full", store.settings)
        p = new(store)
        store.approve(p["id"], "boss", "admin", p["content_hash"])
        return store, clock, runner, ex, p

    def test_runs_once_and_records_who(self):
        store, _, runner, ex, p = self.ready()
        out = ex.execute(p["id"], "boss2", "admin")
        self.assertEqual((out["state"], out["idempotent"], runner.calls[0][4]), ("executed", False, p["id"]))
        done = store.get(p["id"])
        self.assertEqual((done["approved_by"], done["executed_by"]), ("boss", "boss2"))

    def test_idempotent_by_proposal_id(self):
        _, _, runner, ex, p = self.ready()
        first = ex.execute(p["id"], "boss", "admin")
        second = ex.execute(p["id"], "boss", "admin")
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["result"], first["result"])
        self.assertEqual(len(runner.calls), 1)

    def test_concurrent_executions_run_once(self):
        _, _, runner, ex, p = self.ready()
        threads = [threading.Thread(target=ex.execute, args=(p["id"], "boss", "admin")) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(runner.calls), 1)

    def test_not_approved_cannot_run(self):
        store, _ = make()
        ex = pr.Executor(store, Runner(), "full", store.settings)
        p = new(store)
        with self.assertRaises(pr.ProposalError) as ctx:
            ex.execute(p["id"], "boss", "admin")
        self.assertEqual(ctx.exception.code, "act.bad_state")

    def test_hash_is_rechecked_at_execute(self):
        store, _, runner, ex, p = self.ready()
        store.proposals[p["id"]]["params"]["run_id"] = 7777
        with self.assertRaises(pr.ProposalError) as ctx:
            ex.execute(p["id"], "boss", "admin")
        self.assertEqual(ctx.exception.code, "act.hash_mismatch")
        self.assertEqual(runner.calls, [])
        self.assertEqual(store.audit()[-1]["event"], "execute_denied")

    def test_ttl_is_rechecked_at_execute(self):
        store, clock, runner, ex, p = self.ready(ttl_seconds=100)
        clock.now += 100
        with self.assertRaises(pr.ProposalError) as ctx:
            ex.execute(p["id"], "boss", "admin")
        self.assertEqual(ctx.exception.code, "act.expired")
        self.assertEqual(runner.calls, [])

    def test_policy_is_rechecked_at_execute(self):
        store, _, runner, ex, p = self.ready()
        store.settings["allowed_actions"] = []          # the policy changed after the approval
        with self.assertRaises(pr.ProposalError) as ctx:
            ex.execute(p["id"], "boss", "admin")
        self.assertEqual(ctx.exception.reason, "action_type")
        with self.assertRaises(pr.ProposalError):
            store.settings["allowed_actions"] = ["rerun"]
            ex.execute(p["id"], "bob", "maintainer")
        self.assertEqual(runner.calls, [])

    def test_a_failing_runner_is_a_failed_proposal_and_not_run_again(self):
        store, _ = make()
        runner = Runner(error=OSError("403 Forbidden"))
        ex = pr.Executor(store, runner, "full", store.settings)
        p = new(store)
        store.approve(p["id"], "boss", "admin", p["content_hash"])
        out = ex.execute(p["id"], "boss", "admin")
        self.assertEqual(out["state"], "failed")
        self.assertEqual(out["result"]["error"], "OSError")
        self.assertTrue(ex.execute(p["id"], "boss", "admin")["idempotent"])
        self.assertEqual(len(runner.calls), 1)

    def test_a_result_never_keeps_secret_looking_keys(self):
        store, _ = make()
        ex = pr.Executor(store, Runner(result={"ok": True, "token": "ghp_x", "nested": {"password": "p", "n": 1}}), "full", store.settings)
        p = new(store)
        store.approve(p["id"], "boss", "admin", p["content_hash"])
        result = ex.execute(p["id"], "boss", "admin")["result"]
        self.assertEqual(result, {"ok": True, "nested": {"n": 1}})
        for non_dict, want in ((True, {"ok": True, "detail": "True"}), (None, {"ok": False, "detail": "None"})):
            self.assertEqual(pr._result_of(non_dict), want)

    def test_rate_per_day(self):
        store, clock = make(max_per_day=2)
        ex = pr.Executor(store, Runner(), "full", store.settings)
        done = []
        for number in range(3):
            p = new(store, params={"run_id": number})
            try:
                store.approve(p["id"], "boss", "admin", p["content_hash"])
                ex.execute(p["id"], "boss", "admin")
                done.append(number)
            except pr.ProposalError as err:
                self.assertEqual(err.reason, "rate")
        self.assertEqual(done, [0, 1])
        clock.now += 86400 + 1
        p = new(store, params={"run_id": 9})
        store.approve(p["id"], "boss", "admin", p["content_hash"])
        self.assertEqual(ex.execute(p["id"], "boss", "admin")["state"], "executed")


class Capability(unittest.TestCase):
    def test_complete_edition_has_no_executor(self):
        store, _ = make()
        runner = Runner()
        for edition, enabled in (("complete", True), ("lite", True), ("full", False), ("", True)):
            with self.assertRaises(pr.ProposalError) as ctx:
                pr.Executor(store, runner, edition, settings(execute_enabled=enabled))
            self.assertEqual(ctx.exception.code, "act.exec_disabled")
        self.assertEqual(runner.calls, [])

    def test_the_default_settings_never_allow_it(self):
        s = phase4.settings({})["proposals"]
        with self.assertRaises(pr.ProposalError):
            pr.Executor(pr.ProposalStore(s), Runner(), "full", s)

    def test_a_whole_complete_session_never_calls_a_runner(self):
        store, _ = make()
        runner = Runner()
        p = new(store)
        store.approve(p["id"], "boss", "admin", p["content_hash"])
        store.simulate(p["id"])
        store.list()
        store.expire_due()
        self.assertEqual(runner.calls, [])
        self.assertFalse(hasattr(store, "execute"))

    def test_simulate_describes_the_call_and_the_policy(self):
        store, _ = make()
        p = new(store, params={"run_id": 5})
        sim = store.simulate(p["id"])
        self.assertEqual(sim["would_call"], "POST /repos/o/r/actions/runs/5/rerun")
        self.assertTrue(sim["policy_ok"])
        self.assertFalse(sim["executes"])
        merge, _ = make()
        m = new(merge, action_type="merge", params={"number": 4})
        self.assertFalse(merge.simulate(m["id"])["policy_ok"])
        self.assertEqual(merge.simulate(m["id"])["policy_reason"], "merge_off")
        for action in pr.ACTION_TYPES:
            self.assertIn(action, pr.SIMULATED_CALLS)


class Policy(unittest.TestCase):
    def test_window(self):
        self.assertTrue(pr.in_window("", T0))
        self.assertTrue(pr.in_window("08:00-18:00", T0))
        self.assertFalse(pr.in_window("11:00-18:00", T0))
        self.assertTrue(pr.in_window("22:00-12:00", T0))                  # wraps midnight
        self.assertFalse(pr.in_window("12:00-22:00", T0))
        self.assertFalse(pr.in_window("garbage", T0))                      # unreadable = closed
        self.assertFalse(pr.in_window("08:00-18:00\n", T0))

    def test_window_blocks_the_approval(self):
        store, _ = make(hours="11:00-12:00")
        p = new(store)
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "boss", "admin", p["content_hash"])
        self.assertEqual(ctx.exception.reason, "hours")

    def test_rules_by_account_and_repository(self):
        rules = [{"account": "acc1", "repo": "o/*", "actions": ["rerun"], "roles": ["admin"]}]
        store = pr.ProposalStore(settings(), clock=Clock(), policy=pr.PolicyEngine(settings(), rules))
        ok = new(store)
        self.assertEqual(store.approve(ok["id"], "boss", "admin", ok["content_hash"])["state"], "approved")
        other_repo = new(store, repo="x/y")
        other_action = new(store, action_type="label", params={"number": 1})
        other_account = new(store, account_id="acc2", params={"run_id": 77})
        for p in (other_repo, other_action, other_account):
            with self.assertRaises(pr.ProposalError) as ctx:
                store.approve(p["id"], "boss", "admin", p["content_hash"])
            self.assertEqual(ctx.exception.reason, "no_rule")

    def test_rule_roles_and_hours(self):
        rules = [{"repo": "*", "roles": ["admin"], "hours": "00:00-01:00"}]
        store = pr.ProposalStore(settings(allowed_roles=["admin", "maintainer"]), clock=Clock(), policy=pr.PolicyEngine(settings(allowed_roles=["admin", "maintainer"]), rules))
        p = new(store)
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "bob", "maintainer", p["content_hash"])
        self.assertEqual(ctx.exception.reason, "rule_role")
        with self.assertRaises(pr.ProposalError) as ctx:
            store.approve(p["id"], "boss", "admin", p["content_hash"])
        self.assertEqual(ctx.exception.reason, "hours")


class AuditChain(unittest.TestCase):
    def run_session(self, store):
        p = new(store)
        store.approve(p["id"], "boss", "admin", p["content_hash"])
        pr.Executor(store, Runner(), "full", store.settings).execute(p["id"], "boss", "admin")

    def test_the_chain_verifies_and_records_everything(self):
        store, _ = make()
        self.run_session(store)
        self.assertEqual([x["event"] for x in store.audit()], ["created", "approved", "executed"])
        self.assertEqual(store.verify_audit(), (True, 0))

    def test_change_cut_and_insert_are_detected(self):
        for mutate in (lambda a: a[1].update(actor="mallory"), lambda a: a.pop(1), lambda a: a.insert(1, dict(a[0])), lambda a: a.reverse(), lambda a: a[2].update(hash="0" * 64)):
            store, _ = make()
            self.run_session(store)
            mutate(store._audit)
            self.assertFalse(store.verify_audit()[0])

    def test_it_never_holds_a_secret(self):
        store, _ = make()
        self.run_session(store)
        self.assertNotRegex(str(store.audit()), r"(?i)password|token|secret")

    def test_the_file_backend_survives_a_restart_and_keeps_the_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = Clock()
            first = pr.ProposalStore(settings(), pr.FileBackend(tmp), clock)
            self.run_session(first)
            second = pr.ProposalStore(settings(), pr.FileBackend(tmp), clock)
            self.assertEqual(len(second.list()), 1)
            self.assertEqual(second.list()[0]["state"], "executed")
            self.assertEqual(second.verify_audit(), (True, 0))
            q = new(second, params={"run_id": 2})
            self.assertEqual(second.verify_audit(), (True, 0))
            self.assertEqual(len(second.audit()), 4)
            self.assertNotEqual(q["id"], second.list()[0]["id"])

    def test_a_corrupt_line_on_disk_breaks_the_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = pr.ProposalStore(settings(), pr.FileBackend(tmp), Clock())
            self.run_session(first)
            path = pr.FileBackend(tmp)._p("proposals_audit.jsonl")
            lines = path.read_text(encoding="utf-8").splitlines()
            lines[1] = lines[1].replace("boss", "evil")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(pr.ProposalStore(settings(), pr.FileBackend(tmp), Clock()).verify_audit()[0])
            path.write_text("not json\n", encoding="utf-8")
            self.assertFalse(pr.ProposalStore(settings(), pr.FileBackend(tmp), Clock()).verify_audit()[0])


class Text(unittest.TestCase):
    def test_errors_speak_every_language(self):
        err = pr.ProposalError("act.not_allowed", "merge_off")
        texts = {lang: err.text(lang) for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt")}
        self.assertEqual(len(set(texts.values())), 8)
        self.assertTrue(all("merge_off" in t for t in texts.values()))


if __name__ == "__main__":
    unittest.main()
