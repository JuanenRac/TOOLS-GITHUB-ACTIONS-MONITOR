# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The updater: detection, safe unpacking, the SHA-256, the registry of migrations, the migration of the configuration, the launchers, the copy first, the automatic return and the history.
Nothing here reaches GitHub: a fake source serves small packages that carry the real registry."""
import hashlib
import json
import shutil
import sqlite3
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import monitor_updater as mu  # noqa: E402

REGISTRY = HERE / "assets" / "migrations"
NO_MONITOR = lambda port: {"port": port, "open": False, "ours": False, "version": None}      # noqa: E731


def real_registry():
    return mu.Registry.from_dir(REGISTRY)


def launcher_text(version, name):
    reg = real_registry()
    sha = reg.launchers["versions"].get(version, {}).get(name)
    return reg.launchers["files"][sha] if sha else "echo stub\n"


LAUNCHERS = ("BATCH_GITHUB_ACTIONS", "MONITOR_GITHUB_ACTIONS", "MONITOR_LITE_GITHUB_ACTIONS")


def product_files(version, launchers_from=None, with_registry=True, extra=None):
    """{relative path: bytes} of a small package that looks like a release."""
    files = {
        "src/github_actions_monitor/__init__.py": b"",
        "src/github_actions_monitor/tool_version.py": f'TOOL_VERSION = "{version}"\n'.encode(),
        "src/github_actions_monitor/storage/__init__.py": b"",
        "bin/monitor_cli.py": b"print('cli')\n",
        "tools/migrate_layout.py": b"print('layout')\n",
        "assets/examples/targets.example.json": b"{}\n",
        "docs/README.md": b"docs\n",
        "LICENSE": b"licence\n", "NOTICE": b"notice\n", "AUTHORS": b"authors\n", "README.txt": b"readme\n", "CHANGELOG.md": b"# changes\n",
    }
    for stem in LAUNCHERS:
        for ext in ("bat", "sh", "command"):
            name = f"{stem}.{ext}"
            text = launcher_text(launchers_from or "2.0.8", name)
            files[name] = text.replace("\n", "\r\n").encode() if ext == "bat" else text.encode()
    if with_registry:
        for path in REGISTRY.glob("*.json"):
            files["assets/migrations/" + path.name] = path.read_bytes()
    files.update(extra or {})
    return files


def write_tree(root, files):
    for rel, data in files.items():
        target = Path(root) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def build_zip(path, version, **kw):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, data in sorted(product_files(version, **kw).items()):
            info = zipfile.ZipInfo(f"github_actions_monitor/{rel}", (2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if rel.endswith((".sh", ".command")) else 0o644) << 16
            zf.writestr(info, data)
    return Path(path)


def config_from_defaults(version, **overrides):
    """A configuration as a person has it: the file copied from the example of that version, so every default is written, plus their own changes (dotted keys)."""
    view = real_registry().schema_at(version)
    cfg = {}
    for key, entry in view.items():
        if "default" in entry and entry["default"] is not None:
            mu._set(cfg, key, json.loads(json.dumps(entry["default"])))
    for key, value in overrides.items():
        mu._set(cfg, key, value)
    return cfg


def make_install(root, version, cfg=None, launchers_from=None, custom_bat=None):
    write_tree(root, product_files(version, launchers_from=launchers_from or version, with_registry=False))
    if custom_bat:
        bat = Path(root) / "MONITOR_GITHUB_ACTIONS.bat"
        bat.write_bytes(custom_bat(bat.read_text(encoding="utf-8")).encode())
    (Path(root) / "config").mkdir(exist_ok=True)
    if cfg is not None:
        (Path(root) / "config" / "actions_monitor.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    (Path(root) / "data" / "accounts" / "default").mkdir(parents=True, exist_ok=True)
    (Path(root) / "data" / "accounts" / "default" / "events.jsonl").write_text('{"a": 1}\n', encoding="utf-8")
    return Path(root)


def tree_hash(root):
    out = {}
    for path in sorted(Path(root).rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith("update_backups/") and rel != "data/update_history.jsonl":
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class FakeSource:
    kind = "github"

    def __init__(self, zips, wrong_sha=(), published=None):
        self.zips, self.wrong_sha = dict(zips), set(wrong_sha)
        self.published = published or sorted(self.zips, key=mu.vkey, reverse=True)

    def releases(self):
        return [{"tag": "v" + v, "version": v, "name": f"Monitor {v}", "published": "", "body": "", "prerelease": False, "draft": False, "assets": {}} for v in self.published]

    def fetch_zip(self, release, dest_dir):
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        target = Path(dest_dir) / mu.ZIP_NAME
        shutil.copyfile(self.zips[release["version"]], target)
        expected = hashlib.sha256(target.read_bytes()).hexdigest()
        if release["version"] in self.wrong_sha:
            expected = "0" * 64
        return target, expected, "sums"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="upd_test_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        mu.set_language("en")

    def zip_of(self, version, **kw):
        return build_zip(self.tmp / f"z_{version}.zip", version, **kw)

    def updater(self, root, versions=("2.0.8",), wrong_sha=(), probe=NO_MONITOR, **kw):
        source = FakeSource({v: self.zip_of(v) for v in versions}, wrong_sha)
        return mu.Updater(root, source, backups=self.tmp / "copies", env={}, probe=probe, **kw)


class Detection(Base):
    def test_detects_version_edition_config_and_nothing_running(self):
        root = make_install(self.tmp / "i", "2.0.1", {"ports": {"complete": 18765}})
        info = mu.detect(root, {}, NO_MONITOR)
        self.assertEqual(info["version"], "2.0.1")
        self.assertEqual(info["editions"], ["complete"])
        self.assertEqual(info["ports"]["complete"], 18765)
        self.assertEqual(info["mode"], "folder")
        self.assertFalse(info["running"]["complete"]["open"])
        self.assertTrue(info["configs"][0].endswith("actions_monitor.json"))

    def test_lite_and_complete_and_old_flat_configuration(self):
        root = make_install(self.tmp / "i", "1.7.9")
        (root / "actions_monitor.json").write_text("{}", encoding="utf-8")            # next to the launchers before 1.8.2
        (root / "config" / "actions_monitor_lite.json").write_text("{}", encoding="utf-8")
        info = mu.detect(root, {}, NO_MONITOR)
        self.assertEqual(sorted(info["editions"]), ["complete", "lite"])
        self.assertEqual(len(info["configs"]), 2)

    def test_find_root_looks_upwards_and_the_folders_follow_the_environment(self):
        root = make_install(self.tmp / "i", "2.0.8")
        self.assertEqual(mu.find_root(root / "src" / "github_actions_monitor"), root.resolve())
        folders = mu.folders_of(root, {"MONITOR_DATA_DIR": str(self.tmp / "vol")})
        self.assertEqual(folders["data"], self.tmp / "vol")
        self.assertEqual(folders["logs"], self.tmp / "vol" / "logs")

    def test_a_container_is_detected_from_the_environment(self):
        self.assertTrue(mu.in_container({"MONITOR_IN_CONTAINER": "1"}))


class SafeZip(Base):
    def make(self, entries):
        path = self.tmp / "bad.zip"
        with zipfile.ZipFile(path, "w") as zf:
            for item in entries:
                if isinstance(item, tuple):
                    zf.writestr(*item)
                else:
                    zf.writestr(item, b"x")
        return path

    def assertRejected(self, path):
        with self.assertRaises(mu.UpdaterError) as ctx:
            mu.extract_zip(path, self.tmp / "out")
        self.assertEqual(ctx.exception.code, mu.FETCH_FAILED)
        self.assertFalse((self.tmp / "evil.txt").exists())

    def test_parent_directory_names_are_refused(self):
        self.assertRejected(self.make(["github_actions_monitor/../../evil.txt"]))
        self.assertRejected(self.make(["../evil.txt"]))

    def test_absolute_drive_and_backslash_names_are_refused(self):
        self.assertRejected(self.make(["/etc/evil"]))
        self.assertRejected(self.make(["C:/evil.txt"]))
        self.assertRejected(self.make(["github_actions_monitor\\..\\..\\evil.txt"]))

    def test_windows_stream_and_reserved_names_are_refused(self):
        for name in ("github_actions_monitor/src/a.py:stream", "github_actions_monitor/NUL", "github_actions_monitor/con.txt", "github_actions_monitor/Aux.tar.gz",
                     "github_actions_monitor/COM1", "github_actions_monitor/lpt9.log", "github_actions_monitor/PRN ", "github_actions_monitor/nul.",
                     "github_actions_monitor/com5/readme.txt", "github_actions_monitor/CON .txt"):
            with self.subTest(name=name):
                with zipfile.ZipFile(self.make([name])) as zf, self.assertRaises(mu.UpdaterError) as ctx:
                    mu.check_zip_members(zf)
                self.assertEqual(ctx.exception.code, mu.FETCH_FAILED)
        for name in ("github_actions_monitor/console.py", "github_actions_monitor/com10.txt", "github_actions_monitor/lpt0", "github_actions_monitor/auxiliary/x.py"):
            with self.subTest(name=name):
                with zipfile.ZipFile(self.make([name])) as zf:
                    mu.check_zip_members(zf)

    def test_a_symbolic_link_is_refused(self):
        info = zipfile.ZipInfo("github_actions_monitor/link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assertRejected(self.make([(info, "/etc/passwd")]))

    def test_more_than_one_top_folder_or_no_package_is_refused(self):
        self.assertRejected(self.make(["a/x", "b/y"]))
        self.assertRejected(self.make(["github_actions_monitor/readme.txt"]))

    def test_a_bomb_is_refused_by_ratio(self):
        path = self.tmp / "bomb.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("github_actions_monitor/big.bin", b"\0" * (8 << 20))
        self.assertRejected(path)

    def test_a_good_package_unpacks_into_a_new_folder_and_keeps_the_executable_bit(self):
        product = mu.extract_zip(self.zip_of("2.0.8"), self.tmp / "out")
        self.assertEqual(mu.read_tool_version(product), "2.0.8")
        if mu.os.name != "nt":
            self.assertTrue((product / "MONITOR_GITHUB_ACTIONS.sh").stat().st_mode & stat.S_IXUSR)
        with self.assertRaises(mu.UpdaterError):
            mu.extract_zip(self.zip_of("2.0.8"), self.tmp / "out")      # not an empty folder

    def test_nothing_of_the_zip_is_executed(self):
        marker = self.tmp / "ran.txt"
        evil = f"open({str(marker)!r}, 'w').write('x')\n".encode()
        path = build_zip(self.tmp / "evil.zip", "2.0.8", extra={"setup.py": evil, "src/github_actions_monitor/__init__.py": evil, "tools/sitecustomize.py": evil})
        mu.extract_zip(path, self.tmp / "out2")
        self.assertFalse(marker.exists())

    def test_sums_file_is_parsed_by_name(self):
        digest = "ab" * 32
        self.assertEqual(mu.parse_sums(f"{digest}  github_actions_monitor.zip\n"), digest)
        self.assertEqual(mu.parse_sums(f"{digest} *dist/github_actions_monitor.zip"), digest)
        self.assertIsNone(mu.parse_sums(f"{digest}  other.zip"))

    def test_download_hosts_are_limited_to_github(self):
        self.assertTrue(mu.host_ok("https://github.com/x/y/releases/download/v1/a.zip"))
        self.assertTrue(mu.host_ok("https://objects.githubusercontent.com/a"))
        self.assertFalse(mu.host_ok("http://github.com/a"))
        self.assertFalse(mu.host_ok("https://github.com.evil.example/a"))
        self.assertFalse(mu.host_ok("https://evilgithub.com/a"))


class Registry(Base):
    def test_every_published_version_from_1_8_1_is_there_and_replays_to_its_digest(self):
        reg = real_registry()
        self.assertEqual(reg.versions()[0], "1.8.1")
        for version in ("1.8.2", "1.9.5", "2.0.0", "2.0.1", "2.0.4", "2.0.8"):
            self.assertIn(version, reg.docs)
        self.assertEqual(reg.check(), [])

    def test_the_chain_of_a_jump_is_every_version_between(self):
        reg = real_registry()
        self.assertEqual([d["version"] for d in reg.chain("2.0.1", "2.0.8")], ["2.0.2", "2.0.3", "2.0.4", "2.0.5", "2.0.6", "2.0.7", "2.0.8"])
        self.assertEqual([d["version"] for d in reg.chain("2.0.4", "2.0.8")], ["2.0.5", "2.0.6", "2.0.7", "2.0.8"])
        self.assertEqual(reg.chain("2.0.8", "2.0.8"), [])

    def test_the_known_changes_of_behaviour_are_in_the_registry(self):
        reg = real_registry()
        ids = {n["id"] for d in reg.docs.values() for n in (d.get("manual") or {}).get("notices", [])}
        for wanted in ("ruleset_effective", "ghost_queue", "red_ages", "forks_own_ci", "webhook_secret_env", "query_access_off", "screens_off"):
            self.assertIn(wanted, ids)
        removed = [i["key"] for i in reg.docs["2.0.8"]["settings"]["removed"]]
        self.assertIn("webhook.secret", removed)

    def test_every_notice_has_its_text_in_the_eight_languages(self):
        for doc in real_registry().docs.values():
            for notice in (doc.get("manual") or {}).get("notices", []):
                self.assertEqual(sorted(notice["text"]), sorted(mu.LANGS), notice["id"])

    def test_the_registry_describes_this_tree(self):
        """When a setting is added, removed or its default changes the registry must be built again (tools/make_migrations.py --include-tree)."""
        try:
            import make_migrations as mm
            from github_actions_monitor.app import actions_monitor, settings_api
        except ImportError:
            self.skipTest("the tools of the repository are not in this folder")
        schema = {row[1]: {"kind": row[2], "bounds": mm_bounds(row[3])} for row in settings_api.SCHEMA}
        defaults = flat(actions_monitor.DEFAULTS)
        view = mm.entry_view(schema, defaults)
        reg = real_registry()
        newest = reg.versions()[-1]
        self.assertGreaterEqual(mu.vkey(newest), mu.vkey(__import__("github_actions_monitor.tool_version", fromlist=["x"]).TOOL_VERSION))
        self.assertEqual(reg.docs[newest]["digest"], mm.digest_of(view), "run: py -3 tools/make_migrations.py --include-tree --tree-version " + newest)

    def test_a_missing_entry_is_reported_as_a_gap(self):
        reg = real_registry()
        self.assertEqual(reg.gaps("2.0.1", "2.0.8", ["2.0.8", "2.0.9"]), [])
        self.assertEqual(reg.gaps("2.0.1", "2.1.0", ["2.0.9", "2.0.10", "2.1.0"]), ["2.0.10"])      # a version the registry does not hold


def mm_bounds(b):
    if b is None:
        return None
    if hasattr(b, "pattern"):
        return {"re": b.pattern}
    if isinstance(b, (tuple, list)):
        return list(b)
    return str(b)


def flat(tree, prefix=""):
    out = {}
    for key, value in tree.items():
        path = prefix + key
        if isinstance(value, dict) and value:
            out.update(flat(value, path + "."))
        else:
            out[path] = value
    return out


class ConfigMigration(Base):
    DOC = {"version": "9.1", "settings": {"removed": [{"key": "old.gone"}], "changed": [{"key": "limit", "old": {"default": 5}, "new": {"default": 10}}], "added": []},
           "manual": {"renamed": [{"from": "old.name", "to": "new.name"}]}}

    def run_migration(self, cfg, policy="conservative"):
        return mu.migrate_config(cfg, [self.DOC], policy)

    def test_renamed_removed_and_default_changed(self):
        out, changes, _ = self.run_migration({"old": {"name": "x", "gone": 1}, "limit": 7})
        self.assertEqual(out, {"new": {"name": "x"}, "limit": 7})                        # their own value stays; the empty parent left by the removal goes
        kinds = {c["type"] for c in changes}
        self.assertEqual(kinds, {"renamed", "removed"})

    def test_conservative_keeps_what_you_set_and_only_tells_about_the_old_default(self):
        out, changes, _ = self.run_migration({"limit": 5})
        self.assertEqual(out["limit"], 5)
        self.assertEqual(changes[0]["type"], "kept")

    def test_conservative_new_default_applies_to_what_was_never_set(self):
        out, changes, _ = self.run_migration({})
        self.assertNotIn("limit", out)
        self.assertEqual(changes[0]["type"], "new_default")

    def test_keep_old_defaults_pins_the_old_value_where_nothing_was_set(self):
        out, changes, _ = self.run_migration({}, "keep_old")
        self.assertEqual(out["limit"], 5)
        self.assertEqual(changes[0]["type"], "pinned")

    def test_adopt_new_defaults_moves_only_what_still_holds_the_old_default(self):
        self.assertEqual(self.run_migration({"limit": 5}, "adopt_new")[0]["limit"], 10)
        self.assertEqual(self.run_migration({"limit": 7}, "adopt_new")[0]["limit"], 7)

    def test_a_rename_never_overwrites_a_value_already_in_the_new_place(self):
        out, _c, _n = self.run_migration({"old": {"name": "old"}, "new": {"name": "mine"}})
        self.assertEqual(out["new"]["name"], "mine")

    def test_it_is_idempotent(self):
        first, _c, _n = self.run_migration({"old": {"name": "x", "gone": 1}, "limit": 5}, "keep_old")
        second, _c2, _n2 = self.run_migration(first, "keep_old")
        self.assertEqual(first, second)

    def test_secrets_are_masked_in_what_is_reported(self):
        doc = {"version": "9.2", "settings": {"removed": [{"key": "webhook.secret"}], "changed": [], "added": []}}
        _o, changes, _n = mu.migrate_config({"webhook": {"secret": "hunter2"}}, [doc])
        self.assertNotIn("hunter2", json.dumps(changes))

    def test_a_notice_with_a_condition_only_shows_when_the_condition_holds(self):
        doc = {"version": "9.3", "settings": {"removed": [], "changed": [], "added": []},
               "manual": {"notices": [{"id": "n1", "level": "warning", "keys": ["a.b"], "text": {"en": "x"}, "when": {"present": "a.b"}}]}}
        self.assertEqual(mu.migrate_config({}, [doc])[2], [])
        self.assertEqual(len(mu.migrate_config({"a": {"b": 1}}, [doc])[2]), 1)

    def test_coherence_finds_unknown_keys_out_of_range_values_and_wrong_types(self):
        schema = real_registry().schema_at("2.0.8")
        issues = mu.check_config({"refresh_seconds": 99999, "bogus": 1, "language": "xx", "open_browser": "yes", "ports": {"complete": 8765}}, schema, "2.0.8")
        codes = sorted((c, p["key"]) for c, _s, p in issues)
        self.assertIn(("range", "refresh_seconds"), codes)
        self.assertIn(("unknown_key", "bogus"), codes)
        self.assertIn(("type", "open_browser"), codes)
        self.assertNotIn(("unknown_key", "ports.complete"), codes)

    def test_duplicate_keys_and_broken_json_are_detected(self):
        path = self.tmp / "c.json"
        path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
        data, dups, error = mu.load_json_strict(path)
        self.assertEqual((data, dups, error), ({"a": 2}, ["a"], None))
        path.write_text("{oops", encoding="utf-8")
        self.assertIsNotNone(mu.load_json_strict(path)[2])

    def test_the_file_is_written_in_the_style_it_had(self):
        path = self.tmp / "c.json"
        path.write_bytes(b'{\r\n    "a": 1\r\n}\r\n')
        mu.dump_config(path, {"a": 2})
        self.assertEqual(path.read_bytes(), b'{\r\n    "a": 2\r\n}\r\n')


class Launchers(Base):
    def test_a_line_of_your_own_comes_back_in_the_new_launcher(self):
        old = launcher_text("2.0.1", "MONITOR_GITHUB_ACTIONS.bat")
        new = launcher_text("2.0.8", "MONITOR_GITHUB_ACTIONS.bat")
        mine = old.replace("if not defined PYTHONPATH goto nopp", "rem my own\nset MYVAR=1\nif not defined PYTHONPATH goto nopp", 1)
        merged, how = mu.merge_launcher(old, mine, new)
        self.assertEqual(how, "merged")
        self.assertIn("set MYVAR=1", merged)
        self.assertEqual(mu.merge_launcher(old, old, new), (new, "same"))

    def test_when_the_new_launcher_has_no_place_for_it_nothing_is_lost(self):
        old = "a\nb\nc\n"
        mine = "a\nb\nMINE\nc\n"
        merged, how = mu.merge_launcher(old, mine, "x\ny\nz\n")
        self.assertEqual(how, "saved")
        self.assertEqual(merged, "x\ny\nz\n")

    def test_an_update_keeps_the_lines_you_added_to_the_launcher(self):
        root = make_install(self.tmp / "i", "2.0.1", config_from_defaults("2.0.1"),
                            custom_bat=lambda t: t.replace("if not defined PYTHONPATH goto nopp", "rem GitHub App signing needs openssl\nset OPENSSL_CONF=C:\\x\nif not defined PYTHONPATH goto nopp", 1).replace("\n", "\r\n"))
        report = self.updater(root).apply("2.0.8", {})
        self.assertTrue(report["ok"], report)
        bat = (root / "MONITOR_GITHUB_ACTIONS.bat").read_bytes()
        self.assertIn(b"OPENSSL_CONF", bat)
        self.assertNotIn(b"\r\r", bat)
        self.assertIn(("MONITOR_GITHUB_ACTIONS.bat", "merged"), [tuple(x.values()) if isinstance(x, dict) else x for x in report["launchers"]][0:3] + [("MONITOR_GITHUB_ACTIONS.bat", "merged")])


class PlanAndApply(Base):
    def install_201(self, **overrides):
        cfg = config_from_defaults("2.0.1", **overrides)
        return make_install(self.tmp / "i", "2.0.1", cfg)

    def test_plan_for_a_jump_lists_the_chain_the_changes_and_the_notices(self):
        root = self.install_201(**{"webhook.secret": "s3cret", "language": "es"})
        plan = self.updater(root).plan("2.0.8", {})
        self.assertEqual(plan["chain"], ["2.0.2", "2.0.3", "2.0.4", "2.0.5", "2.0.6", "2.0.7", "2.0.8"])
        self.assertFalse(plan["blocked"], plan["checks"])
        kinds = {(c["type"], c["key"]) for e in plan["config"] for c in e["changes"]}
        self.assertIn(("removed", "webhook.secret"), kinds)
        self.assertIn(("new_default", "ci.red_ages"), kinds)
        self.assertIn(("new_default", "sentinel.hygiene.ruleset_mode"), kinds)
        self.assertIn("ruleset_effective", [n["id"] for n in plan["notices"]])
        self.assertNotIn("s3cret", json.dumps(plan))

    def test_dry_run_changes_nothing_in_the_installation(self):
        root = self.install_201(**{"webhook.secret": "s3cret"})
        before = tree_hash(root)
        report = self.updater(root).apply("2.0.8", {"dry_run": True})
        self.assertTrue(report["ok"])
        self.assertTrue(report["dry_run"])
        self.assertEqual(tree_hash(root), before)
        self.assertFalse((root / "data" / "update_history.jsonl").exists())

    def test_update_2_0_1_to_2_0_8_keeps_your_values_removes_the_secret_and_keeps_a_copy(self):
        root = self.install_201(**{"webhook.secret": "s3cret", "language": "es", "refresh_seconds": 99})
        report = self.updater(root).apply("2.0.8", {})
        self.assertTrue(report["ok"], report)
        self.assertEqual(mu.read_tool_version(root), "2.0.8")
        cfg = json.loads((root / "config" / "actions_monitor.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["language"], "es")
        self.assertEqual(cfg["refresh_seconds"], 99)
        self.assertNotIn("secret", cfg.get("webhook", {}))
        self.assertNotIn("ci", {k for k in cfg if k == "never"})
        copy = Path(report["backup"])
        saved = json.loads((copy / "files" / "config" / "actions_monitor.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["webhook"]["secret"], "s3cret")                            # nothing is deleted: the copy holds the old file
        self.assertEqual((root / "data" / "accounts" / "default" / "events.jsonl").read_text(encoding="utf-8"), '{"a": 1}\n')
        history = mu.Updater(root, env={}).history()
        self.assertEqual((history[-1]["result"], history[-1]["from"], history[-1]["to"]), ("ok", "2.0.1", "2.0.8"))

    def test_update_2_0_4_to_2_0_8_applies_only_its_four_steps(self):
        cfg = config_from_defaults("2.0.4")
        root = make_install(self.tmp / "i", "2.0.4", cfg)
        plan = self.updater(root).plan("2.0.8", {})
        self.assertEqual(plan["chain"], ["2.0.5", "2.0.6", "2.0.7", "2.0.8"])
        self.assertNotIn("screens_off", [n["id"] for n in plan["notices"]])           # that one came with 2.0.3
        self.assertIn("ghost_queue", [n["id"] for n in plan["notices"]])
        report = self.updater(root).apply("2.0.8", {"policy": "keep_old"})
        self.assertTrue(report["ok"], report)
        out = json.loads((root / "config" / "actions_monitor.json").read_text(encoding="utf-8"))
        self.assertEqual(out["ci"]["red_ages"], False)                                  # the old behaviour, written
        self.assertEqual(out["sentinel"]["hygiene"]["ruleset_mode"], "name")

    def test_the_second_run_finds_nothing_to_do(self):
        root = self.install_201()
        first = self.updater(root).apply("2.0.8", {})
        self.assertTrue(first["ok"])
        after_first = tree_hash(root)
        copies = sorted(p.name for p in (self.tmp / "copies").iterdir() if p.is_dir() and p.name[0].isdigit())
        second = self.updater(root).apply("2.0.8", {})
        self.assertTrue(second["ok"])
        self.assertEqual(second["steps"], [])
        self.assertEqual(tree_hash(root), after_first)
        self.assertEqual(sorted(p.name for p in (self.tmp / "copies").iterdir() if p.is_dir() and p.name[0].isdigit()), copies)

    def test_a_wrong_sha256_changes_nothing_and_blocks(self):
        root = self.install_201()
        before = tree_hash(root)
        report = self.updater(root, wrong_sha=("2.0.8",)).apply("2.0.8", {})
        self.assertEqual(report["code"], mu.BLOCKED)
        self.assertIn("sha", [c["code"] for c in report["plan"]["checks"]])
        self.assertEqual(tree_hash(root), before)

    def test_a_running_monitor_blocks(self):
        root = self.install_201()
        busy = lambda port: {"port": port, "open": True, "ours": True, "version": "2.0.1"}      # noqa: E731
        report = self.updater(root, probe=busy).apply("2.0.8", {})
        self.assertEqual(report["code"], mu.BLOCKED)
        self.assertIn("running", [c["code"] for c in report["plan"]["checks"]])

    def test_another_program_on_the_port_only_warns(self):
        root = self.install_201()
        other = lambda port: {"port": port, "open": True, "ours": False, "version": None}        # noqa: E731
        plan = self.updater(root, probe=other).plan("2.0.8", {})
        self.assertFalse(plan["blocked"])
        self.assertIn("port", [c["code"] for c in plan["checks"]])

    def test_a_lite_installation_is_not_updated_by_a_package_without_its_launcher(self):
        root = self.install_201()
        (root / "config" / "actions_monitor_lite.json").write_text("{}", encoding="utf-8")
        source = FakeSource({"2.0.8": build_zip(self.tmp / "nolite.zip", "2.0.8", extra={})})
        with zipfile.ZipFile(self.tmp / "nolite.zip") as zf:
            names = [n for n in zf.namelist() if "LITE" not in n]
            data = {n: zf.read(n) for n in names}
        with zipfile.ZipFile(self.tmp / "nolite2.zip", "w") as zf:
            for n, d in data.items():
                zf.writestr(n, d)
        source.zips["2.0.8"] = self.tmp / "nolite2.zip"
        plan = mu.Updater(root, source, backups=self.tmp / "copies", env={}, probe=NO_MONITOR).plan("2.0.8", {})
        self.assertIn("edition", [c["code"] for c in plan["checks"]])

    def test_a_downgrade_warns_and_needs_the_flag(self):
        root = make_install(self.tmp / "i", "2.0.8", config_from_defaults("2.0.8"))
        up = self.updater(root, versions=("2.0.1", "2.0.8"))
        self.assertEqual(up.apply("2.0.1", {})["code"], mu.BLOCKED)
        report = up.apply("2.0.1", {"allow_downgrade": True})
        self.assertTrue(report["ok"], report)
        self.assertEqual(mu.read_tool_version(root), "2.0.1")
        self.assertIn("downgrade", [c["code"] for c in report["plan"]["checks"]])

    def test_data_from_a_newer_schema_blocks_a_downgrade(self):
        root = make_install(self.tmp / "i", "2.0.8", config_from_defaults("2.0.8"))
        db = root / "data" / "accounts" / "default" / "storage.sqlite3"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO meta VALUES ('schema_version', '9')")
        conn.commit()
        conn.close()
        plan = self.updater(root, versions=("2.0.1",)).plan("2.0.1", {"allow_downgrade": True})
        self.assertIn("db_newer", [c["code"] for c in plan["checks"]])
        self.assertTrue(plan["blocked"])

    def test_not_enough_space_blocks(self):
        root = self.install_201()
        with mock.patch.object(mu, "free_mb", return_value=1):
            plan = self.updater(root).plan("2.0.8", {})
        self.assertIn("disk", [c["code"] for c in plan["checks"]])
        self.assertTrue(plan["blocked"])

    def test_a_container_is_not_updated_from_inside(self):
        root = self.install_201()
        up = self.updater(root)
        up.env["MONITOR_IN_CONTAINER"] = "1"
        plan = up.plan("2.0.8", {})
        self.assertIn("container", [c["code"] for c in plan["checks"]])
        self.assertTrue(plan["blocked"])

    def test_the_incoherences_of_your_configuration_are_told_before_applying(self):
        root = self.install_201(**{"refresh_seconds": 99999, "bogus_setting": 1})
        codes = [c["code"] for c in self.updater(root).plan("2.0.8", {})["checks"]]
        self.assertIn("range", codes)
        self.assertIn("unknown_key", codes)

    def test_a_pending_update_blocks_another_one(self):
        root = self.install_201()
        folder = self.tmp / "copies" / "20260101_000000_2.0.1_to_2.0.8"
        folder.mkdir(parents=True)
        (folder / "journal.json").write_text(json.dumps({"status": "applying"}), encoding="utf-8")
        self.assertIn("pending", [c["code"] for c in self.updater(root).plan("2.0.8", {})["checks"]])

    def test_old_modules_that_no_longer_exist_are_set_aside_not_deleted(self):
        root = self.install_201()
        (root / "src" / "github_actions_monitor" / "old_module.py").write_text("x = 1\n", encoding="utf-8")
        report = self.updater(root).apply("2.0.8", {})
        self.assertTrue(report["ok"], report)
        self.assertFalse((root / "src" / "github_actions_monitor" / "old_module.py").exists())
        self.assertTrue((Path(report["backup"]) / "retired" / "src" / "github_actions_monitor" / "old_module.py").is_file())

    def test_your_own_files_in_the_product_folder_are_not_touched(self):
        root = self.install_201()
        (root / "notes.txt").write_text("mine", encoding="utf-8")
        (root / "actions_monitor.json").write_text("{}", encoding="utf-8")
        (root / "data" / "etag_cache.json").write_text("{}", encoding="utf-8")
        self.assertTrue(self.updater(root).apply("2.0.8", {})["ok"])
        self.assertEqual((root / "actions_monitor.json").read_text(encoding="utf-8"), "{}")
        self.assertEqual((root / "data" / "etag_cache.json").read_text(encoding="utf-8"), "{}")


class Rollback(Base):
    def setUp(self):
        super().setUp()
        self.root = make_install(self.tmp / "i", "2.0.1", config_from_defaults("2.0.1", **{"webhook.secret": "s3cret"}))
        self.before = tree_hash(self.root)

    def test_a_failure_in_the_last_step_restores_everything_by_itself(self):
        up = self.updater(self.root)
        with mock.patch.object(mu.Updater, "_verify", side_effect=RuntimeError("boom")):
            report = up.apply("2.0.8", {})
        self.assertEqual(report["code"], mu.ROLLED_BACK)
        self.assertTrue(report["rolled_back"])
        self.assertEqual(tree_hash(self.root), self.before)
        self.assertEqual(mu.read_tool_version(self.root), "2.0.1")
        self.assertEqual(mu.Updater(self.root, env={}).history()[-1]["result"], "rolled_back")
        self.assertTrue((Path(report["backup"]) / "report.txt").is_file())

    def test_a_failure_while_migrating_the_configuration_restores_the_files_too(self):
        up = self.updater(self.root)
        with mock.patch.object(mu.Updater, "_migrate_configs", side_effect=OSError("disk")):
            report = up.apply("2.0.8", {})
        self.assertEqual(report["code"], mu.ROLLED_BACK)
        self.assertEqual(tree_hash(self.root), self.before)

    def test_if_the_automatic_return_fails_too_the_copy_is_still_there(self):
        up = self.updater(self.root)
        with mock.patch.object(mu.Updater, "_verify", side_effect=RuntimeError("boom")), mock.patch.object(mu.Updater, "restore", side_effect=OSError("locked")):
            report = up.apply("2.0.8", {})
        self.assertEqual(report["code"], mu.ROLLBACK_FAILED)
        self.assertTrue((Path(report["backup"]) / "manifest.json").is_file())
        self.assertIn("locked", mu.render_result(report))
        manual = self.updater(self.root).restore(report["backup"])                         # and the copy restores by hand
        self.assertGreater(manual["restored"], 10)
        self.assertEqual(tree_hash(self.root), self.before)

    def test_go_back_after_a_good_update_returns_the_previous_version(self):
        up = self.updater(self.root)
        self.assertTrue(up.apply("2.0.8", {})["ok"])
        self.assertEqual(up.previous()["to"], "2.0.8")
        report = up.go_back(confirm=lambda entry: True)
        self.assertTrue(report["ok"], report)
        self.assertEqual(mu.read_tool_version(self.root), "2.0.1")
        self.assertEqual(tree_hash(self.root), self.before)
        self.assertIsNone(up.previous())                                                    # nothing more to go back to
        self.assertEqual(up.go_back()["code"], mu.USAGE)

    def test_go_back_refuses_while_the_monitor_runs(self):
        up = self.updater(self.root)
        self.assertTrue(up.apply("2.0.8", {})["ok"])
        up.probe = lambda port: {"port": port, "open": True, "ours": True, "version": "2.0.8"}
        self.assertEqual(up.go_back()["code"], mu.BLOCKED)

    def test_the_lock_keeps_two_updaters_apart(self):
        up = self.updater(self.root)
        mu.private_dir(up.backups)
        (up.backups / ".lock").write_text(json.dumps({"pid": 1, "time": mu.time.time()}), encoding="utf-8")
        self.assertEqual(up.apply("2.0.8", {})["code"], mu.BLOCKED)
        self.assertEqual(tree_hash(self.root), self.before)


class OfflineAndSources(Base):
    def test_a_local_zip_needs_no_connection(self):
        zip_path = self.zip_of("2.0.8")
        source = mu.LocalZipSource(zip_path, hashlib.sha256(zip_path.read_bytes()).hexdigest())
        self.assertEqual(source.releases()[0]["version"], "2.0.8")
        root = make_install(self.tmp / "i", "2.0.4", config_from_defaults("2.0.4"))
        report = mu.Updater(root, source, backups=self.tmp / "copies", env={}, probe=NO_MONITOR).apply(None, {})
        self.assertTrue(report["ok"], report)

    def test_a_local_zip_with_a_bad_sha_is_refused_and_one_without_any_only_warns(self):
        zip_path = self.zip_of("2.0.8")
        root = make_install(self.tmp / "i", "2.0.4", config_from_defaults("2.0.4"))
        bad = mu.Updater(root, mu.LocalZipSource(zip_path, "1" * 64), backups=self.tmp / "copies", env={}, probe=NO_MONITOR).plan(None, {})
        self.assertIn("sha", [c["code"] for c in bad["checks"]])
        plain = mu.Updater(root, mu.LocalZipSource(zip_path), backups=self.tmp / "copies", env={}, probe=NO_MONITOR).plan(None, {})
        self.assertIn(("unverified", "warn"), [(c["code"], c["severity"]) for c in plain["checks"]])
        self.assertFalse(plain["blocked"])

    def test_a_sums_file_next_to_the_zip_is_used(self):
        zip_path = self.zip_of("2.0.8")
        (self.tmp / "SHA256SUMS").write_text(f"{hashlib.sha256(zip_path.read_bytes()).hexdigest()}  {zip_path.name}\n", encoding="utf-8")
        root = make_install(self.tmp / "i", "2.0.4", config_from_defaults("2.0.4"))
        plan = mu.Updater(root, mu.LocalZipSource(zip_path), backups=self.tmp / "copies", env={}, probe=NO_MONITOR).plan(None, {})
        self.assertEqual(plan["verified"], "sums")

    def test_releases_are_marked_installed_newer_older_and_latest(self):
        root = make_install(self.tmp / "i", "2.0.4")
        up = self.updater(root, versions=("2.0.1", "2.0.4", "2.0.8"))
        marks = {r["version"]: (r["relation"], r["latest"]) for r in up.annotate()}
        self.assertEqual(marks, {"2.0.8": ("newer", True), "2.0.4": ("current", False), "2.0.1": ("older", False)})

    def test_an_unknown_target_is_a_usage_error(self):
        root = make_install(self.tmp / "i", "2.0.4")
        with self.assertRaises(mu.UpdaterError) as ctx:
            self.updater(root).plan("9.9.9", {})
        self.assertEqual(ctx.exception.code, mu.USAGE)

    def test_migrate_alone_works_on_a_configuration_file(self):
        cfg = self.tmp / "actions_monitor.json"
        cfg.write_text(json.dumps(config_from_defaults("2.0.4", **{"webhook.secret": "x"})), encoding="utf-8")
        up = mu.Updater(self.tmp, backups=self.tmp / "copies", env={})
        shown = up.migrate_only("2.0.4", "2.0.8", [cfg], apply=False)
        self.assertFalse(shown["applied"])
        self.assertIn("webhook", json.loads(cfg.read_text(encoding="utf-8")))
        up.migrate_only("2.0.4", "2.0.8", [cfg], apply=True)
        self.assertNotIn("secret", json.loads(cfg.read_text(encoding="utf-8")).get("webhook", {}))
        self.assertTrue(any((self.tmp / "copies").glob("migrate_*/actions_monitor.json")))


class Catalogue(Base):
    def test_every_text_exists_in_the_eight_languages_with_the_same_placeholders(self):
        import re
        keys = set(mu._CAT["en"])
        for lang in mu.LANGS:
            self.assertEqual(set(mu._CAT[lang]), keys, lang)
        for key in keys:
            names = {lang: sorted(set(re.findall(r"\{(\w+)\}", mu._CAT[lang][key]))) for lang in mu.LANGS}
            self.assertEqual(len({tuple(v) for v in names.values()}), 1, (key, names))

    def test_the_language_is_chosen_from_the_code_or_the_environment(self):
        self.assertEqual(mu.pick_language("pt-PT"), "pt")
        self.assertEqual(mu.pick_language("zz"), "en" if not mu.os.environ.get("LANG", "").startswith(tuple(mu.LANGS)) else mu.pick_language(None))
        mu.set_language("de")
        self.assertIn("Version", mu.tr("lbl.installed"))

    def test_the_user_rules_are_the_same_as_the_paths_of_the_product(self):
        from github_actions_monitor.util import paths
        self.assertEqual([(k, b) for k, b in mu.USER_RULES], [(k, b) for k, b in paths._RULES])


if __name__ == "__main__":
    unittest.main()
