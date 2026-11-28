# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Plugins: the manifest, signed packages (with the key of the RFC 8032 vectors made here), the separate process, untrusted output, lifecycle, official plugins, authoring tools and the secret backends."""
import base64
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
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
from github_actions_monitor.plugins import plugin_host as host  # noqa: E402
from github_actions_monitor.plugins import plugin_manifest as manifests  # noqa: E402
from github_actions_monitor.plugins import plugin_package as packages  # noqa: E402
from github_actions_monitor.plugins import plugin_worker  # noqa: E402
from github_actions_monitor.security import keyring, secret_backends, secretstore, sigverify  # noqa: E402
from github_actions_monitor.sentinels import alert_center  # noqa: E402

SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")      # the first test vector of RFC 8032: a key made for tests, known to everybody


def _sign_with_test_seed(data):
    """An Ed25519 signature made here only for the tests, with the arithmetic of the verifier (the product never signs)."""
    h = hashlib.sha512(SEED).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    q = 2 ** 252 + 27742317777372353535851937790883648493
    p = 2 ** 255 - 19
    d = -121665 * pow(121666, p - 2, p) % p

    def add(P, Q):
        x1, y1 = P
        x2, y2 = Q
        t = d * x1 * x2 * y1 * y2
        return ((x1 * y2 + x2 * y1) * pow(1 + t, p - 2, p) % p, (y1 * y2 + x1 * x2) * pow(1 - t, p - 2, p) % p)

    def mul(n, P):
        out = (0, 1)
        while n:
            if n & 1:
                out = add(out, P)
            P = add(P, P)
            n >>= 1
        return out

    def encode(P):
        return (P[1] | ((P[0] & 1) << 255)).to_bytes(32, "little")

    gy = 4 * pow(5, p - 2, p) % p
    xx = (gy * gy - 1) * pow(d * gy * gy + 1, p - 2, p)
    gx = pow(xx, (p + 3) // 8, p)
    if (gx * gx - xx) % p:
        gx = gx * pow(2, (p - 1) // 4, p) % p
    if gx & 1:
        gx = p - gx
    base = (gx, gy)
    public = encode(mul(a, base))
    r = int.from_bytes(hashlib.sha512(h[32:] + data).digest(), "little") % q
    big_r = encode(mul(r, base))
    k = int.from_bytes(hashlib.sha512(big_r + public + data).digest(), "little") % q
    return public.hex(), big_r + ((r + k * a) % q).to_bytes(32, "little")


PUBLIC = _sign_with_test_seed(b"")[0]


def keys(**extra):
    return [dict(keyring.clean_entry({"id": "author", "public": PUBLIC, "scopes": ["plugins"]}), **extra)]


def sign(package):
    signature = _sign_with_test_seed(Path(package).read_bytes())[1]
    Path(str(package) + keyring.SIGNATURE_SUFFIX).write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="ascii")


MANIFEST = {"name": "demo", "version": "1.0.0", "api_compat": "1", "author": "a", "description": "d", "trust": "third_party", "entry": "plugin.py", "permissions": ["repos.list", "gh.get"],
            "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 600}
CODE = """def run(ctx):
    print("noise that must not break the protocol")
    return {"alerts": [{"id": r, "code": "x", "repo": r, "title": str(ctx.get(f"repos/{ctx.owner}/{r}/labels"))} for r in ctx.repos()]}
"""


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        patch = mock.patch.dict(os.environ, {"MONITOR_DATA_DIR": str(self.base / "data"), "MONITOR_CONFIG_DIR": str(self.base / "config")})
        patch.start()
        self.addCleanup(patch.stop)
        host.PLUGINS.clear()
        host.STARTED["checked"] = False
        self.addCleanup(host.PLUGINS.clear)

    def folder(self, code=CODE, **manifest):
        folder = self.base / "src_plugin"
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir()
        (folder / "plugin.json").write_text(json.dumps(dict(MANIFEST, **manifest)), encoding="utf-8")
        (folder / "plugin.py").write_text(code, encoding="utf-8")
        return folder

    def package(self, code=CODE, **manifest):
        out = self.base / "demo.zip"
        packages.pack(self.folder(code, **manifest), out)
        sign(out)
        return out


class Manifest(unittest.TestCase):
    def refused(self, **change):
        with self.assertRaises(manifests.ManifestError) as caught:
            manifests.parse(json.dumps(dict(MANIFEST, **change)))
        return caught.exception.code

    def test_a_good_one_and_every_refusal_says_why(self):
        self.assertEqual(manifests.parse(json.dumps(MANIFEST))["name"], "demo")
        self.assertEqual(self.refused(api_compat="2"), "api_compat")
        self.assertEqual(self.refused(name="../x"), "name")
        self.assertEqual(self.refused(entry="../x.py"), "entry")
        self.assertEqual(self.refused(permissions=["gh.write"]), "permissions")
        self.assertEqual(self.refused(get_paths=["https://elsewhere"]), "get_paths")
        self.assertEqual(self.refused(refresh_seconds=1), "refresh")
        self.assertEqual(self.refused(surprise=1), "keys")

    def test_only_the_declared_paths_of_watched_repositories(self):
        manifest = manifests.parse(json.dumps(MANIFEST))
        self.assertTrue(manifests.path_allowed(manifest, "repos/me/app/labels", "me", ["app"]))
        for path in ("repos/me/other/labels", "repos/you/app/labels", "repos/me/app/hooks", "repos/me/app/labels?x=1", "repos/me/app/labels/../hooks"):
            self.assertFalse(manifests.path_allowed(manifest, path, "me", ["app"]), path)
        named = manifests.parse(json.dumps(dict(MANIFEST, get_paths=["users/{owner}/packages/container/{name}/versions"])))
        self.assertFalse(manifests.path_allowed(named, "users/me/packages/container/../versions", "me", []))
        self.assertTrue(manifests.path_allowed(named, "users/me/packages/container/a%2Fb/versions", "me", []))


class Packages(Temp):
    def test_signed_by_a_key_of_the_keyring_and_confirmed_by_its_fingerprint(self):
        package = self.package()
        found = packages.inspect(package, keys())
        self.assertEqual(found["fingerprint"], keyring.fingerprint(PUBLIC))
        with self.assertRaises(packages.PackageError) as caught:
            packages.install(package, keys(), "00")
        self.assertEqual(caught.exception.code, "fingerprint")
        done = packages.install(package, keys(), found["fingerprint"])
        self.assertFalse(done["enabled"], "it arrives switched off")
        self.assertEqual([r["state"] for r in packages.audit(keys())], ["ok"])
        self.assertEqual([r["state"] for r in packages.audit(keys(revoked=True))], ["revoked"])
        self.assertEqual([r["state"] for r in packages.audit([])], ["unknown_key"])
        self.assertTrue(packages.uninstall("demo")["removed"])
        self.assertEqual(packages.registry(), {})

    def test_unsigned_altered_wrong_scope_and_official_claims_are_refused(self):
        package = self.package()
        for change, code, ring in ((lambda: package.write_bytes(package.read_bytes() + b"x"), "signature", keys()),
                                   (lambda: Path(str(package) + keyring.SIGNATURE_SUFFIX).unlink(), "unsigned", keys()),
                                   (lambda: None, "unknown_key", keys(scopes=["packs"]))):
            package = self.package()
            change()
            with self.assertRaises(packages.PackageError) as caught:
                packages.inspect(package, ring)
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(packages.PackageError) as caught:
            packages.inspect(self.package(trust="official"), keys())
        self.assertEqual(caught.exception.code, "official")

    def test_a_changed_installed_package_does_not_run(self):
        package = self.package()
        packages.install(package, keys(), keyring.fingerprint(PUBLIC))
        stored = packages.install_folder() / "demo" / packages.PACKAGE_NAME
        stored.write_bytes(stored.read_bytes() + b"x")
        self.assertEqual(packages.audit(keys())[0]["state"], "files")

    def test_names_that_leave_the_folder_links_and_huge_files_are_refused(self):
        self.assertFalse(packages.safe_name("a\\b.py"))      # zipfile itself turns a backslash into a slash on Windows
        for name, code in (("../evil.py", "path"), ("/abs.py", "path"), ("c:x.py", "path")):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr(zipfile.ZipInfo(name), "x")
            with self.assertRaises(packages.PackageError) as caught:
                packages.members(buffer.getvalue())
            self.assertIn(caught.exception.code, (code, "zip"), name)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("link.py")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "target")
        with self.assertRaises(packages.PackageError) as caught:
            packages.members(buffer.getvalue())
        self.assertEqual(caught.exception.code, "link")
        with self.assertRaises(packages.PackageError):
            packages.members(b"0" * (packages.MAX_ZIP + 1))

    def test_the_same_folder_gives_the_same_package(self):
        folder = self.folder()
        self.assertEqual(packages.pack(folder, self.base / "a.zip"), packages.pack(folder, self.base / "b.zip"))


class Authoring(Temp):
    def test_the_template_is_valid_and_passes_its_own_test(self):
        from github_actions_monitor.plugins import plugin_cli
        work = self.base / "template"
        self.assertEqual(plugin_cli.init(work)[2], plugin_cli.OK)
        report = packages.validate(work)
        self.assertTrue(report["ok"], report)
        done = subprocess.run([sys.executable, "-m", "unittest", "test_plugin"], cwd=work, capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_validate_finds_a_permission_that_was_not_declared(self):
        report = packages.validate(self.folder("def run(ctx):\n    return ctx.discussions()\n"))
        self.assertFalse(report["ok"])
        self.assertIn("graphql.discussions", report["errors"][0])
        self.assertTrue(packages.validate(self.folder("import socket\ndef run(ctx):\n    return {}\n"))["warnings"])

    def test_entry_points_are_listed_and_never_imported(self):
        point = mock.Mock()
        point.name, point.dist.name, point.dist.files = "x", "pkg", []
        point.load.side_effect = AssertionError("never imported")
        self.assertEqual(packages.entry_point_candidates([point]), [{"distribution": "pkg", "name": "x", "package": ""}])


class Worker(Temp):
    def run_worker(self, code, broker=None, **options):
        folder = self.folder(code)
        manifest = manifests.parse((folder / "plugin.json").read_text(encoding="utf-8"))
        return plugin_worker.run(folder, manifest, broker or host.Reads(manifest, lambda *a: ["bug"], "me", ["app"]).broker, owner="me", **dict({"timeout_s": 60}, **options))

    def test_a_round_in_a_separate_process_says_what_was_isolated(self):
        answer, isolation = self.run_worker(CODE)
        self.assertEqual(answer["alerts"][0]["repo"], "app")
        self.assertIn("bug", answer["alerts"][0]["title"])
        if sys.platform in ("win32", "darwin"):
            self.assertFalse(isolation["network_isolated"])
        if sys.platform == "win32":
            self.assertTrue(isolation["job_object"])

    def test_it_does_not_receive_the_environment_of_the_monitor(self):
        with mock.patch.dict(os.environ, {"MONITOR_SENTINEL_VALUE": "visible", "GH_TOKEN": "not-a-real-value"}):
            answer, _ = self.run_worker("import os\ndef run(ctx):\n    return {'keys': sorted(os.environ)}\n")
        self.assertNotIn("MONITOR_SENTINEL_VALUE", answer["keys"])
        self.assertNotIn("GH_TOKEN", answer["keys"])

    def test_a_plugin_that_hangs_is_killed_and_a_huge_answer_is_cut(self):
        with self.assertRaises(plugin_worker.WorkerError) as caught:
            self.run_worker("import time\ndef run(ctx):\n    time.sleep(60)\n", timeout_s=3)
        self.assertEqual(caught.exception.code, "timeout")
        with self.assertRaises(plugin_worker.WorkerError) as caught:
            self.run_worker("def run(ctx):\n    return {'x': 'a' * 100000}\n", max_output_kb=16)
        self.assertEqual(caught.exception.code, "output")

    def test_a_path_that_was_not_declared_is_an_error_for_the_plugin(self):
        with self.assertRaises(plugin_worker.WorkerError) as caught:
            self.run_worker("def run(ctx):\n    return ctx.get('repos/me/app/hooks')\n")
        self.assertIn("get_paths", str(caught.exception))

    def test_a_system_that_is_not_allowed_loads_nothing(self):
        with self.assertRaises(plugin_worker.WorkerError) as caught:
            self.run_worker(CODE, platforms_ok=())
        self.assertEqual(caught.exception.code, "platform")


class Untrusted(unittest.TestCase):
    def test_what_a_plugin_says_is_cleaned_and_cut(self):
        answer = {"alerts": [{"id": "1", "code": "A B<script>", "level": "critical", "repo": "other", "url": "javascript:alert(1)", "title": "\x1b[31m<script>x</script>\x00" + "y" * 1000}]}
        row = host.clean_alerts("demo", "third_party", answer, ["app"], title_max=50)[0]
        self.assertEqual((row["level"], row["repo"], row["details"]["url"], row["sentinel"]), ("error", None, "", "plugin"))
        self.assertNotIn("\x1b", row["title"])
        self.assertNotIn("\x00", row["title"])
        self.assertLessEqual(len(row["title"]), len("[demo] ") + 50)
        self.assertEqual(row["code"], "plugin.demo.abscript")
        with self.assertRaises(ValueError):
            host.clean_alerts("demo", "third_party", "text", [])


class Lifecycle(Temp):
    CONFIG = {"plugins": {"enabled": True, "third_party": {"enabled": True}, "breaker": {"failures": 3}}}

    def install(self, code):
        packages.install(self.package(code), keys(), keyring.fingerprint(PUBLIC))
        packages.set_enabled("demo", True)
        patch = mock.patch.object(host, "user_keys", return_value=keys())
        patch.start()
        self.addCleanup(patch.stop)

    def test_three_failures_pause_it_the_state_survives_and_resume_starts_again(self):
        self.install("def run(ctx):\n    raise RuntimeError('broken')\n")
        for _ in range(3):
            host.refresh(self.CONFIG, lambda *a: [], "me", ["app"], force=True)
        self.assertEqual(host.PLUGINS["demo"].state(), "paused")
        self.assertEqual([a["code"] for a in host.alerts()], ["plugin.paused"])
        self.assertIn("plugin.paused", [a["code"] for a in alert_center.collect(None)])
        host.PLUGINS.clear()
        self.assertEqual(host.refresh(self.CONFIG, lambda *a: [], "me", ["app"]), [], "still paused after a restart")
        host.resume("demo")
        self.assertEqual(host.refresh(self.CONFIG, lambda *a: [], "me", ["app"], force=True), ["demo"])

    def test_a_revoked_key_pauses_at_the_next_start(self):
        self.install(CODE)
        with mock.patch.object(host, "user_keys", return_value=keys(revoked=True)):
            host.refresh(self.CONFIG, lambda *a: [], "me", ["app"])
        self.assertTrue(host.load_state()["demo"]["paused"])

    def test_off_means_nothing_runs(self):
        self.install(CODE)
        self.assertEqual(host.enabled_names({}), [])
        self.assertEqual(host.enabled_names({"plugins": {"enabled": True}}), [])
        self.assertEqual(host.enabled_names(self.CONFIG), [("demo", "third_party")])


class Official(Temp):
    CONFIG = {"plugins": {"enabled": True, "official": {"discussions": {"enabled": True, "days": 7}, "packages": {"enabled": True, "max_versions": 3}}}}

    def gh(self, *args):
        self.calls.append(args)
        if args[1] == "graphql":
            node = {"number": 4, "title": "help", "url": "https://github.com/me/app/discussions/4", "createdAt": "2000-01-01T00:00:00Z", "repository": {"name": "app"}, "comments": {"totalCount": 0}}
            return {"data": {"search": {"nodes": [node, dict(node, number=5, repository={"name": "not-watched"})]}}}
        return [{"name": "img", "version_count": 9, "html_url": "https://github.com/users/me/packages/container/package/img"}]

    def test_each_reports_with_its_own_codes_and_only_reads(self):
        self.calls = []
        host.refresh(self.CONFIG, self.gh, "me", ["app"], force=True)
        codes = sorted(a["code"] for a in host.alerts())
        self.assertEqual(codes, ["plugin.discussions.unanswered", "plugin.packages.retention"], [p.reason for p in host.PLUGINS.values()])
        for args in self.calls:
            self.assertFalse(any(x in ("-X", "--method") for x in args), args)
            self.assertNotIn("mutation", " ".join(args))
        rows = {r["name"]: r for r in host.catalogue(self.CONFIG)["plugins"]}
        self.assertEqual((rows["packages"]["state"], rows["packages"]["isolation"]), ("healthy", "in_process"))


class SecretBackends(unittest.TestCase):
    TOKEN = "gh" + "p_" + "a" * 36

    def tearDown(self):
        secretstore.clear_environment()

    def opener(self, body, seen):
        def open_(request, timeout):
            seen.append((request.full_url, request.get_header("X-vault-token")))
            return io.BytesIO(json.dumps(body).encode())
        return mock.Mock(open=open_)

    def test_vault_kv2_and_kv1_over_https_or_loopback_only(self):
        config = {"secrets": {"backend": "vault", "vault": {"addr": "http://127.0.0.1:8200", "path": "secret/data/monitor", "field": "token", "token_env": "T"}}}
        seen = []
        for body in ({"data": {"data": {"token": "abc"}}}, {"data": {"token": "abc"}}):
            self.assertEqual(secret_backends.read(config, environ={"T": "root"}, opener=self.opener(body, seen)), "abc")
        self.assertEqual(seen[0], ("http://127.0.0.1:8200/v1/secret/data/monitor", "root"))
        for change, code in ((dict(addr="http://vault.example.org"), "address"), (dict(path="../x"), "settings"), (dict(token_env="NOT_SET_ANYWHERE"), "no_token")):
            bad = {"secrets": {"backend": "vault", "vault": dict(config["secrets"]["vault"], **change)}}
            with self.assertRaises(secret_backends.BackendError) as caught:
                secret_backends.read(bad, environ={"T": "root"})
            self.assertEqual(caught.exception.code, code)

    def test_the_tools_get_a_fixed_command_and_their_output_is_never_repeated(self):
        seen = []

        def runner(command):
            seen.append(command)
            return mock.Mock(returncode=0, stdout=json.dumps({"value": "v"}) if command[0] == "bws" else "v\n")
        for backend, section in (("sops", {"sops": {"file": "s.enc.yaml", "field": "token"}}), ("bitwarden", {"bitwarden": {"item": "abc-1"}}), ("aws", {"cloud": {"ref": "my/secret"}}),
                                 ("azure", {"cloud": {"ref": "https://v.vault.azure.net/secrets/x"}}), ("gcp", {"cloud": {"ref": "x"}})):
            self.assertEqual(secret_backends.read({"secrets": dict(section, backend=backend)}, runner=runner), "v", backend)
        self.assertEqual([c[0] for c in seen], ["sops", "bws", "aws", "az", "gcloud"])
        with self.assertRaises(secret_backends.BackendError) as caught:
            secret_backends.read({"secrets": {"backend": "aws", "cloud": {"ref": "x"}}}, runner=lambda c: mock.Mock(returncode=1, stdout="secret text"))
        self.assertEqual(str(caught.exception), "tool_failed")
        with self.assertRaises(secret_backends.BackendError):
            secret_backends.read({"secrets": {"backend": "gcp", "cloud": {"ref": "--project=x"}}}, runner=runner)

    def test_the_token_goes_to_gh_only_and_a_rotation_is_picked_up(self):
        config = {"github_token": {"enabled": True}, "secrets": {"backend": "aws", "cloud": {"ref": "x"}, "reload_seconds": 60}}
        values = [self.TOKEN, self.TOKEN[:-1] + "b"]
        with mock.patch.object(secret_backends, "read", side_effect=lambda c: values[0]):
            self.assertTrue(secretstore.apply_to_environment(config))
        self.assertNotEqual(os.environ.get("GH_TOKEN"), self.TOKEN)
        self.assertEqual(secretstore.gh_kwargs()["env"]["GH_TOKEN"], values[0])
        secretstore.BACKEND["at"] -= 100
        with mock.patch.object(secret_backends, "read", side_effect=lambda c: values[1]):
            self.assertEqual(secretstore.gh_kwargs()["env"]["GH_TOKEN"], values[1])
        secretstore.BACKEND["at"] -= 100
        with mock.patch.object(secret_backends, "read", side_effect=secret_backends.BackendError("unreachable")):
            self.assertEqual(secretstore.gh_kwargs()["env"]["GH_TOKEN"], values[1], "a backend that does not answer keeps the token read before")


@unittest.skipUnless(os.environ.get("MONITOR_VAULT_LAB_ADDR"), "runs only in the workflows: it needs a Vault in development mode")
class VaultLab(unittest.TestCase):
    def test_a_real_vault_in_development_mode_and_a_rotation(self):
        import urllib.request
        address, root = os.environ["MONITOR_VAULT_LAB_ADDR"], os.environ["MONITOR_VAULT_LAB_ROOT"]
        config = {"secrets": {"backend": "vault", "vault": {"addr": address, "path": "secret/data/monitor", "field": "token", "token_env": "MONITOR_VAULT_LAB_ROOT"}}}
        for value in ("first-value", "second-value"):
            request = urllib.request.Request(address + "/v1/secret/data/monitor", data=json.dumps({"data": {"token": value}}).encode(), headers={"X-Vault-Token": root}, method="POST")
            urllib.request.urlopen(request, timeout=20).close()
            self.assertEqual(secret_backends.read(config), value)


class SkillBundle(unittest.TestCase):
    def test_the_bundle_is_reproducible_and_carries_the_version(self):
        tool = HERE.parent / "tools" / "prepare_skill_bundle.py"
        if not tool.is_file():
            self.skipTest("the tool lives in the repository")
        sys.path.insert(0, str(tool.parent))
        import prepare_skill_bundle
        from github_actions_monitor.tool_version import TOOL_VERSION
        with tempfile.TemporaryDirectory() as tmp:
            first = prepare_skill_bundle.bundle(Path(tmp) / "a")
            self.assertEqual(first, prepare_skill_bundle.bundle(Path(tmp) / "b"))
            info = json.loads((Path(tmp) / "a" / "bundle.json").read_text(encoding="utf-8"))
        self.assertEqual((info["version"], info["name"]), (TOOL_VERSION, "github-actions-monitor-external"))
        self.assertIn("SKILL.md", first)


if __name__ == "__main__":
    unittest.main()
