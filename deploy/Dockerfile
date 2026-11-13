# GitHub Actions monitor in a container. Build from the root of the repository:  docker build -f deploy/Dockerfile -t github-actions-monitor .
# The monitor only listens on 127.0.0.1: run it with `--network host` on Linux (see monitor/docs/DEPLOYMENT.md). Give it a login with the minimum permissions through GH_TOKEN.
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/githubcli.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y --no-install-recommends gh && rm -rf /var/lib/apt/lists/*
COPY monitor /app
WORKDIR /app
ENV PYTHONPATH=/app/src
RUN useradd --create-home --uid 1000 monitor && chown -R monitor /app
USER monitor
CMD ["python", "-m", "github_actions_monitor", "--no-browser", "--port", "8765"]
