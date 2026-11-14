#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The test of the container: builds the image, starts it the way a service runs (read-only code, no root, no capabilities), and checks the whole life of an account whose login GitHub revokes:
#   1. it starts, becomes healthy and listens as a service (the deep health check, the access token, the account is ok);
#   2. the login is revoked: ONLY that account turns blind (a second account stays ok), a critical system alert opens, the health check stays green (a restart does not fix a lost login);
#   3. a new login is put in place WITHOUT a restart with the command line (the new token is checked first, a bad one changes nothing) and the account is ok again, the alert closed;
#   4. the login is revoked again and the file of the secret is replaced: SIGHUP (docker kill -s HUP) makes the account read it and it is ok again.
# GitHub is never called: a fake `gh` (deploy/test/fake_gh.py) answers like GitHub from a list of good tokens that this script edits.
# Usage: deploy/test/container_test.sh [image]   (without an image it builds one from deploy/Dockerfile). Needs docker. Exit code 0 = every check passed.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
IMAGE="${1:-}"
NAME="monitor-container-test-$$"
WORK="$(mktemp -d)"
FAILED=0
GOOD1="ghp_$(printf 'A%.0s' $(seq 1 36))"
GOOD2="ghp_$(printf 'B%.0s' $(seq 1 36))"
GOOD3="ghp_$(printf 'C%.0s' $(seq 1 36))"
BAD="ghp_$(printf 'Z%.0s' $(seq 1 36))"
ACCESS="container-test-access-token-0123456789"

say() { printf '%s\n' "$*"; }
pass() { say "ok    $*"; }
fail() { say "FAIL  $*"; FAILED=1; }
check() { local what="$1"; shift; if "$@" >/dev/null 2>&1; then pass "$what"; else fail "$what"; fi; }
cleanup() {
  docker logs "$NAME" > "$WORK/container.log" 2>&1
  [ "$FAILED" != "0" ] && { say "--- container log ---"; tail -n 80 "$WORK/container.log"; }
  docker rm -f "$NAME" >/dev/null 2>&1
  chmod -R u+rwX "$WORK" 2>/dev/null; rm -rf "$WORK"
}
trap cleanup EXIT
cli() { docker exec -e MONITOR_ACCESS_TOKEN="$ACCESS" "$NAME" python /app/bin/monitor_cli.py "$@"; }
cli_in() { docker exec -i -e MONITOR_ACCESS_TOKEN="$ACCESS" "$NAME" python /app/bin/monitor_cli.py "$@"; }
account_state() { cli accounts --json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print({a["id"]: a["state"] for a in d["accounts"]}.get(sys.argv[1], "?"))' "$1"; }
wait_for() { # wait_for SECONDS "description" command...
  local limit="$1" what="$2"; shift 2
  local end=$((SECONDS + limit))
  while [ "$SECONDS" -lt "$end" ]; do if "$@" >/dev/null 2>&1; then pass "$what"; return 0; fi; sleep 3; done
  fail "$what (waited ${limit}s)"; return 1
}
state_is() { [ "$(account_state "$1")" = "$2" ]; }

if [ -z "$IMAGE" ]; then
  IMAGE="monitor-container-test:local"
  docker build -f "$REPO/deploy/Dockerfile" -t "$IMAGE" "$REPO" || { fail "the image builds"; exit 1; }
fi
pass "the image is $IMAGE"

# the world the container sees: two accounts (one whose token stays good), the list of tokens the fake gh accepts, the secret file
mkdir -p "$WORK/data/accounts/alpha" "$WORK/data/accounts/beta" "$WORK/config" "$WORK/secret"
printf '{"github_owner": "alpha-owner", "refresh_seconds": 30, "open_browser": false, "repos": "all"}\n' > "$WORK/data/accounts/alpha/actions_monitor.json"
printf '{"github_owner": "beta-owner", "refresh_seconds": 30, "open_browser": false, "repos": "all"}\n' > "$WORK/data/accounts/beta/actions_monitor.json"
printf '%s\n%s\n' "$GOOD1" "$GOOD3" > "$WORK/good"
printf '%s\n' "$GOOD1" > "$WORK/secret/gh_token"
sed 's/\r$//' "$HERE/fake_gh.py" > "$WORK/gh"; chmod 755 "$WORK/gh"      # LF even if the checkout has CRLF
chmod -R 777 "$WORK/data" "$WORK/config"; chmod 644 "$WORK/good" "$WORK/secret/gh_token"
# beta has a login of its own (a file in its folder) that is always good, so it proves that a revoked login of alpha does not touch it
printf '%s\n' "$GOOD3" > "$WORK/data/accounts/beta/credential"; chmod 666 "$WORK/data/accounts/beta/credential"

docker run -d --name "$NAME" --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  -v "$WORK/data:/data" -v "$WORK/config:/config" -v "$WORK/gh:/usr/local/bin/gh:ro" -v "$WORK/good:/fake/good:ro" -v "$WORK/secret/gh_token:/run/secrets/gh_token:ro" \
  -e FAKE_GH_GOOD=/fake/good -e GH_TOKEN_FILE=/run/secrets/gh_token -e MONITOR_ACCESS_TOKEN="$ACCESS" \
  "$IMAGE" >/dev/null || { fail "the container starts"; exit 1; }

wait_for 150 "the container is healthy (deep health check)" bash -c "[ \"\$(docker inspect -f '{{.State.Health.Status}}' $NAME)\" = healthy ]"
check "it does not run as root" bash -c "[ \"\$(docker exec $NAME id -u)\" != 0 ]"
check "the code is read-only" bash -c "! docker exec $NAME sh -c 'echo x > /app/src/github_actions_monitor/__init__.py'"
check "the deep health check from the command line says healthy" cli health --deep
check "it says it listens on the network" bash -c "docker exec -e MONITOR_ACCESS_TOKEN=$ACCESS $NAME python /app/bin/monitor_cli.py accounts --json | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)[\"data\"][\"listening\"] == \"network\" else 1)'"
check "without the access token every request is refused" bash -c "! docker exec -e MONITOR_ACCESS_TOKEN= $NAME python /app/bin/monitor_cli.py accounts"
wait_for 120 "alpha is ok" state_is alpha ok
wait_for 120 "beta is ok" state_is beta ok

say "--- the login of alpha is revoked ---"
printf '%s\n' "$GOOD3" > "$WORK/good"       # GOOD1 (the token of alpha) is no longer accepted; the token of beta stays good
wait_for 240 "alpha turns blind" state_is alpha blind
check "beta is still ok (only that account is blind)" state_is beta ok
check "the critical system alert is open" bash -c "cli() { docker exec -e MONITOR_ACCESS_TOKEN=$ACCESS $NAME python /app/bin/monitor_cli.py \"\$@\"; }; cli alerts --account alpha --sentinel system --json | python3 -c 'import json,sys; a=json.load(sys.stdin)[\"data\"][\"alerts\"]; sys.exit(0 if any(x[\"level\"]==\"critical\" and x[\"code\"]==\"system.credential_blind\" for x in a) else 1)'"
check "the deep health check stays green (a restart does not fix a lost login)" cli health --deep
check "the status command says the account cannot sign in" bash -c "cli() { docker exec -e MONITOR_ACCESS_TOKEN=$ACCESS $NAME python /app/bin/monitor_cli.py \"\$@\"; }; ! cli status --account alpha"

say "--- a new login without a restart ---"
STARTED="$(docker inspect -f '{{.State.StartedAt}}' "$NAME")"
printf '%s\n' "$BAD" | cli_in credential replace --account alpha --new-token-file - >/dev/null 2>&1
[ $? -ne 0 ] && pass "a token GitHub refuses is not kept (exit code is not 0)" || fail "a token GitHub refuses is not kept"
check "alpha is still blind after the refused token" state_is alpha blind
printf '%s\n%s\n' "$GOOD2" "$GOOD3" > "$WORK/good"
printf '%s\n' "$GOOD2" | cli_in credential replace --account alpha --new-token-file - >/dev/null 2>&1
[ $? -eq 0 ] && pass "the new token is accepted" || fail "the new token is accepted"
wait_for 90 "alpha is ok again" state_is alpha ok
check "the critical alert closed" bash -c "cli() { docker exec -e MONITOR_ACCESS_TOKEN=$ACCESS $NAME python /app/bin/monitor_cli.py \"\$@\"; }; cli alerts --account alpha --sentinel system --json | python3 -c 'import json,sys; sys.exit(0 if not json.load(sys.stdin)[\"data\"][\"alerts\"] else 1)'"
check "the new token is kept in the folder of that account only (mode 600)" bash -c "[ \"\$(docker exec $NAME stat -c %a /data/accounts/alpha/credential)\" = 600 ] && ! docker exec $NAME test -e /data/accounts/beta/credential_alpha"
[ "$(docker inspect -f '{{.State.StartedAt}}' "$NAME")" = "$STARTED" ] && pass "nothing was restarted" || fail "nothing was restarted"
check "the token is nowhere in the log" bash -c "! docker logs $NAME 2>&1 | grep -q '$GOOD2'"

say "--- the secret file is replaced and SIGHUP is sent ---"
docker exec "$NAME" rm -f /data/accounts/alpha/credential
printf '%s\n' "$GOOD3" > "$WORK/good"
wait_for 240 "alpha turns blind again (the token of the file is not accepted any more)" state_is alpha blind
printf '%s\n' "$GOOD3" > "$WORK/secret/gh_token"
docker kill -s HUP "$NAME" >/dev/null
wait_for 120 "alpha is ok again after SIGHUP" state_is alpha ok
[ "$(docker inspect -f '{{.State.StartedAt}}' "$NAME")" = "$STARTED" ] && pass "SIGHUP restarted nothing" || fail "SIGHUP restarted nothing"
check "the container is still healthy" bash -c "[ \"\$(docker inspect -f '{{.State.Health.Status}}' $NAME)\" = healthy ]"

if [ "$FAILED" = "0" ]; then say "CONTAINER_TEST=PASS"; else say "CONTAINER_TEST=FAIL"; fi
exit "$FAILED"
