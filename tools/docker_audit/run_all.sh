#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Runs the container checks (E1 ... E8) on a Linux machine with Docker and the Docker Compose plugin, one after the other, the way the workflow docker-audit.yml runs them one per job.
#
#   tools/docker_audit/run_all.sh [--target DIR] [--previous DIR] [--out DIR] [--only E1,E3]
#
#   --target    a checkout of the version to check (default: this repository)
#   --previous  a checkout of the version before it, for the migration check E5 (without it E5 skips the migration)
#   --out       where the result files go (default: docker-audit-out in the current folder)
#   --only      a list of checks (default: all eight)
# The exit code is 0 only when no check failed. Needs Python 3.8 or newer and nothing else: no package, no account, no registry login.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
TARGET="$REPO"
PREVIOUS=""
OUT="docker-audit-out"
ONLY="E1,E2,E3,E4,E5,E6,E7,E8"
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --previous) PREVIOUS="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
command -v docker >/dev/null 2>&1 || { echo "docker is not installed or not in PATH" >&2; exit 2; }
docker info >/dev/null 2>&1 || { echo "the Docker daemon does not answer (is your user allowed to use it?)" >&2; exit 2; }
declare -A SCRIPT=([E1]=e1_basic_start.py [E2]=e2_team_mode.py [E3]=e3_proxy.py [E4]=e4_hardening.py [E5]=e5_volumes.py [E6]=e6_secrets.py [E7]=e7_shutdown.py [E8]=e8_webhook.py)
FAILED=0
IFS=',' read -r -a CODES <<< "$ONLY"
for code in "${CODES[@]}"; do
  script="${SCRIPT[$code]:-}"
  [ -n "$script" ] || { echo "unknown check: $code" >&2; exit 2; }
  echo "=== $code ==="
  args=(--target "$TARGET" --out "$OUT")
  [ -n "$PREVIOUS" ] && args+=(--previous "$PREVIOUS")
  python3 "$HERE/$script" "${args[@]}" || FAILED=1
done
python3 "$HERE/collect.py" --dir "$OUT" --expected "$ONLY" --ref "$(basename "$TARGET")" || FAILED=1
exit "$FAILED"
