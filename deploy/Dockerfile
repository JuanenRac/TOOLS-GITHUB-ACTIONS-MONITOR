# GitHub Actions monitor, the official image. Build from the root of the repository:
#
#   docker build -f deploy/Dockerfile -t github-actions-monitor .
#
# Three stages: `gh` fetches the GitHub CLI from its signed apt repository, `app` prepares the code (compiled, without the tests), and the final image holds only Python, `gh`, the CA
# certificates and the code, read-only and owned by root. It runs as the user 10001, never as root, and keeps everything it writes in two volumes:
#
#   /config   actions_monitor.json (written on the first start, kept after)
#   /data     the accounts (one folder each), the access token of the service, the state, the login of `gh`
#
# The environment variables are listed in monitor/docs/DEPLOYMENT.md. The image listens on every interface of the container in the NETWORK MODE (every request needs the access token) and
# publishes no port by itself: publish 8765 on 127.0.0.1 or put the reverse proxy of deploy/compose.yaml in front of it.
ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim AS gh
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/*

FROM python:${PYTHON_VERSION}-slim AS app
COPY monitor /build
RUN python -m compileall -q -j 0 /build/src \
 && rm -rf /build/tests

FROM python:${PYTHON_VERSION}-slim
ARG VERSION=dev
LABEL org.opencontainers.image.title="GitHub Actions monitor" \
      org.opencontainers.image.description="Watches the GitHub Actions of an account or an organisation: the page, the sentinel, the alerts and the command line." \
      org.opencontainers.image.source="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.version="${VERSION}"
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --gid 10001 monitor \
 && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /data --shell /usr/sbin/nologin monitor \
 && mkdir -p /config /data/accounts /data/state /data/secrets /data/gh \
 && chown -R 10001:10001 /config /data \
 && chmod 700 /data/secrets /data/state
COPY --from=gh /usr/bin/gh /usr/local/bin/gh
COPY --from=app /build /app
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MONITOR_SERVICE=1 \
    MONITOR_CONFIG=/config/actions_monitor.json \
    MONITOR_ACCOUNTS_DIR=/data/accounts \
    MONITOR_STATE_DIR=/data/state \
    MONITOR_SECRET_DIR=/data/secrets \
    GH_CONFIG_DIR=/data/gh \
    MONITOR_LISTEN_NETWORK=1 \
    MONITOR_LISTEN_HOST=0.0.0.0 \
    MONITOR_LOCAL_PORT=8766 \
    MONITOR_URL=http://127.0.0.1:8766 \
    MONITOR_PORT=8765
WORKDIR /app
USER 10001:10001
VOLUME ["/config", "/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python", "-m", "github_actions_monitor.cli.healthcheck"]
ENTRYPOINT ["/usr/bin/tini", "--", "python", "-m", "github_actions_monitor.service"]
