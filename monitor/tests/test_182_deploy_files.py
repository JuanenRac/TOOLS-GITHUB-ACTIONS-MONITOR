# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The files of deploy/ and the workflow that publishes the image say what the guide says: no root, two volumes, a deep health check, the variables documented, the actions pinned by commit, a time
limit on every job, the minimum permissions, both platforms and no push unless a release asks for it."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

ROOT = HERE.parent
DEPLOY = ROOT / "deploy"
WORKFLOWS = ROOT / ".github" / "workflows"
SUFFIXES = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por")


def need(path):
    if not path.is_file():
        raise unittest.SkipTest("the files of deploy/ and the workflows live in the repository, not in the zip of the monitor")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


class Dockerfile(unittest.TestCase):
    def setUp(self):
        self.text = need(DEPLOY / "Dockerfile")

    def test_three_stages_a_user_that_is_not_root_and_two_volumes(self):
        self.assertGreaterEqual(len(re.findall(r"^FROM ", self.text, re.M)), 3)
        users = re.findall(r"^USER (.+)$", self.text, re.M)
        self.assertTrue(users and not users[-1].strip().startswith(("root", "0")), users)
        self.assertRegex(self.text, r'VOLUME \["/config", "/data"\]')
        self.assertIn("tini", self.text)

    def test_the_health_check_is_the_deep_one_and_the_entry_is_the_service(self):
        self.assertRegex(self.text, r"HEALTHCHECK .*\\\n\s+CMD \[\"python\", \"-m\", \"github_actions_monitor.cli.healthcheck\"\]")
        self.assertIn('"github_actions_monitor.service"]', self.text)

    def test_the_code_is_not_owned_by_the_user_that_runs_it(self):
        self.assertNotRegex(self.text, r"chown[^\n]*/app")
        self.assertNotIn("--chown", self.text.split("COPY --from=app")[1].split("\n")[0])

    def test_it_installs_nothing_it_does_not_need(self):
        for name in ("curl", "gnupg"):
            final = self.text.split("FROM python:${PYTHON_VERSION}-slim\n")[1]
            self.assertNotIn(name, final, name + " belongs to the stage that fetches gh, not to the final image")

    def test_every_variable_of_the_image_is_documented_in_the_eight_languages(self):
        names = set(re.findall(r"^\s*(?:ENV\s+)?([A-Z][A-Z0-9_]+)=", self.text.split("ENV ")[1].split("WORKDIR")[0], re.M))
        self.assertIn("MONITOR_CONFIG", names)
        for suffix in SUFFIXES:
            guide = (HERE / "docs" / f"DEPLOYMENT{suffix}.md").read_text(encoding="utf-8")
            for name in names - {"PYTHONPATH", "PYTHONUNBUFFERED", "PYTHONDONTWRITEBYTECODE", "MONITOR_PORT"}:
                self.assertIn(f"`{name}`", guide, f"{name} in DEPLOYMENT{suffix}.md")


class Compose(unittest.TestCase):
    def setUp(self):
        self.text = need(DEPLOY / "compose.yaml")

    def test_read_only_without_capabilities_and_the_login_is_a_secret(self):
        for needle in ("read_only: true", "cap_drop:", "no-new-privileges:true", "gh_token", "GH_TOKEN_FILE: /run/secrets/gh_token", "service_healthy"):
            self.assertIn(needle, self.text)
        self.assertNotRegex(self.text, r"GH_TOKEN:\s*\S")

    def test_the_port_is_published_on_this_machine_only(self):
        self.assertRegex(self.text, r'"127\.0\.0\.1:\$\{MONITOR_PORT:-8765\}:8765"')

    def test_the_proxy_is_an_option(self):
        self.assertIn('profiles: ["proxy"]', self.text)
        caddy = need(DEPLOY / "Caddyfile")
        self.assertIn("reverse_proxy monitor:8765", caddy)
        self.assertNotRegex(caddy, r"trusted_proxies", "Caddy must not believe the X-Forwarded-For it receives")

    def test_the_example_environment_names_only_variables_the_compose_file_reads(self):
        example = need(DEPLOY / ".env.example")
        asked = set(re.findall(r"^([A-Z_]+)=", example, re.M))
        used = set(re.findall(r"\$\{([A-Z_]+)", self.text))
        self.assertEqual(asked - used, set(), "every variable of .env.example is read by compose.yaml")


class Systemd(unittest.TestCase):
    def test_hardened_restarts_reloads_and_checks_the_deep_health(self):
        text = need(DEPLOY / "github-actions-monitor.service")
        for needle in ("NoNewPrivileges=true", "ProtectSystem=strict", "PrivateTmp=true", "Restart=on-failure", "ExecReload=/bin/kill -HUP $MAINPID", "cli.healthcheck", "User=monitor", "CapabilityBoundingSet="):
            self.assertIn(needle, text)
        self.assertNotIn("User=root", text)
        env = need(DEPLOY / "github-actions-monitor.env")
        for needle in ("MONITOR_SERVICE=1", "MONITOR_CONFIG=", "GH_TOKEN_FILE="):
            self.assertIn(needle, env)
        self.assertNotRegex(env, r"(?m)^GH_TOKEN=\S", "the login is a file, not a variable")


class Workflow(unittest.TestCase):
    def setUp(self):
        self.text = need(WORKFLOWS / "release-image.yml")

    def test_every_action_is_pinned_by_commit(self):
        uses = re.findall(r"uses:\s*(\S+)", self.text)
        self.assertTrue(uses)
        for item in uses:
            self.assertRegex(item, r"@[0-9a-f]{40}$", item)

    def test_every_job_has_a_time_limit_and_the_top_level_grants_nothing(self):
        self.assertRegex(self.text, r"(?m)^permissions: \{\}$")
        jobs = self.text.split("\njobs:\n")[1]
        self.assertEqual(len(re.findall(r"timeout-minutes:", self.text)), len(re.findall(r"(?m)^  [a-z0-9_-]+:$", jobs)))

    def test_the_permissions_of_the_job_are_the_minimum(self):
        block = self.text.split("    permissions:\n")[1].split("    env:")[0]
        granted = dict(re.findall(r"^\s+([a-z-]+): (read|write)", block, re.M))
        self.assertEqual(granted, {"contents": "read", "packages": "write", "id-token": "write", "attestations": "write"})

    def test_both_platforms_and_the_tags(self):
        self.assertIn("--platform linux/amd64,linux/arm64", self.text)
        for tag in ("${image}:${version}", "${image}:${version%.*}", "${image}:latest"):
            self.assertIn(tag, self.text)

    def test_only_actions_of_github_are_used_because_the_settings_of_the_repository_allow_no_others(self):
        for item in re.findall(r"uses:\s*(\S+)", self.text):
            self.assertTrue(item.startswith("actions/"), item)

    def test_nothing_is_pushed_unless_a_release_is_published_or_someone_asks_by_hand(self):
        self.assertIn("release:\n    types: [published]", self.text)
        self.assertRegex(self.text, r"(?s)push:\s+description:.*?default: false")
        self.assertIn("PUBLISH: ${{ github.event_name == 'release' || inputs.push }}", self.text)
        self.assertIn('if [ "$PUBLISH" = "true" ]; then output="--push"; else output="--output type=cacheonly"; fi', self.text)
        self.assertNotIn("pull_request", self.text, "a pull request never reaches the registry")
        self.assertNotIn("pull_request_target", self.text)

    def test_a_release_whose_tag_is_not_the_version_of_the_code_stops(self):
        self.assertIn('"v${version}"', self.text)

    def test_the_workflow_reads_the_version_from_the_file_that_has_it(self):
        from github_actions_monitor.tool_version import TOOL_VERSION
        found = re.search(r"TOOL_VERSION = \"([0-9.]+)\"", (HERE / "src" / "github_actions_monitor" / "tool_version.py").read_text(encoding="utf-8")).group(1)
        self.assertEqual(found, TOOL_VERSION)
        self.assertIn("monitor/src/github_actions_monitor/tool_version.py", self.text)

    def test_the_ci_builds_the_image_and_runs_the_container_test(self):
        ci = need(WORKFLOWS / "ci.yml")
        self.assertIn("deploy/test/container_test.sh", ci)
        self.assertRegex(ci, r"(?s)  container:.*?timeout-minutes:")


class ContainerTestScript(unittest.TestCase):
    def test_it_checks_each_behaviour_of_a_revoked_login(self):
        text = need(DEPLOY / "test" / "container_test.sh")
        for needle in ("--read-only", "--cap-drop ALL", "alpha turns blind", "beta is still ok", "system.credential_blind", "credential replace", "nothing was restarted", "kill -s HUP", "the token is nowhere in the log"):
            self.assertIn(needle, text)

    def test_the_fake_gh_refuses_what_github_refuses(self):
        text = need(DEPLOY / "test" / "fake_gh.py")
        self.assertIn("Bad credentials (HTTP 401)", text)
        self.assertIn("GH_TOKEN environment variable", text)


if __name__ == "__main__":
    unittest.main()
