<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | **🇵🇹 Português**

# Executá-lo como serviço

O monitor é um programa local que escuta apenas em `127.0.0.1` e não tem login. Estas notas servem para o executar sem navegador, num servidor ou num contentor, para uma conta ou para uma organização.

## Sem navegador

`python actions_monitor.py --no-browser --port 8765`. `GET /api/health` responde `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` para um gestor de serviços ou uma verificação de contentor; não chama o GitHub.


## Configuração e ambiente

- Tudo vive em `actions_monitor.json`; o ambiente acrescenta `GH_HOST` (nome de anfitrião de um GitHub Enterprise Server: todas as chamadas e todas as ligações da página o usam), `GH_TOKEN` (lido pelo `gh`; o monitor nunca o guarda), `MONITOR_LANG`, `MONITOR_ECOSYSTEMS_FILE`, `MONITOR_TARGETS_FILE` e `MONITOR_PROFILES_FILE`.
- `github_owner` pode ser um utilizador ou uma organização. Para vigiar várias contas, execute um monitor por conta, cada um com a sua porta e a sua pasta.


## Exemplos para adaptar

systemd:

```ini
# /etc/systemd/system/github-actions-monitor.service
[Unit]
Description=GitHub Actions monitor
After=network-online.target

[Service]
User=monitor
WorkingDirectory=/opt/github_actions_monitor
EnvironmentFile=/etc/github-actions-monitor/env     # a file with a line GH_TOKEN=... (mode 600)
ExecStart=/usr/bin/python3 actions_monitor.py --no-browser --port 8765
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/github_actions_monitor

[Install]
WantedBy=multi-user.target
```

Contentor:

```dockerfile
# the same file is deploy/Dockerfile of the repository (the CI builds it)
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/githubcli.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*
COPY github_actions_monitor /app
WORKDIR /app
USER 1000
CMD ["python", "actions_monitor.py", "--no-browser", "--port", "8765"]
```
```yaml
# docker-compose.yml: the monitor only listens on 127.0.0.1, so on Linux share the host network namespace
services:
  monitor:
    build: .
    network_mode: host
    environment:
      GH_TOKEN: ${GH_TOKEN}          # a token with the minimum permissions listed below
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8765/api/health', timeout=4)"]
```

- launchd: `~/Library/LaunchAgents/org.example.ghamon.plist`: `ProgramArguments` = `/usr/bin/python3`, `actions_monitor.py`, `--no-browser`; `WorkingDirectory` = the folder; `KeepAlive` = true; `RunAtLoad` = true.
- Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/actions_monitor.py --no-browser"`


## Atrás de um proxy inverso

Por defeito, o monitor só escuta em `127.0.0.1`. Se precisar de lhe chegar a partir de outra máquina, ponha à frente um proxy inverso com TLS, ative o modo de rede (`listen.network`: então todos os pedidos têm de levar o token de acesso) e DECLARE o proxy (`listen.proxy_public_host` com o seu nome público, `listen.secure_cookie` ou `listen.trusted_proxy`). O monitor recusa qualquer pedido cujo `Host` não seja o seu próprio endereço nem esse nome público; por isso o proxy tem de o enviar e tem de acrescentar o endereço real do cliente:

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

Com um proxy declarado, nada do que chega pela porta principal conta como «este computador», diga o que disser nos cabeçalhos (um proxy que se esqueça de um cabeçalho faria parecer locais todos os clientes da internet). Por isso as chaves que decidem a exposição, as ações no GitHub e os testes dos canais não podem ser usados a partir daí. Para os usar, abra com `listen.local_port` (um número de 1024 a 65535) uma segunda porta que só escuta em `127.0.0.1` e use-a a partir do computador do monitor: pede o mesmo token de acesso.

`listen.trusted_proxy` pressupõe que o proxy corre no MESMO computador que o monitor (o monitor acredita em `X-Forwarded-For` em qualquer ligação que chegue por loopback): não o use com um proxy noutra máquina. Os tokens errados de todos os clientes do proxy são também contados em conjunto (o triplo do limite de um endereço), para que mudar o cabeçalho a cada tentativa não anule o bloqueio.

## Permissões mínimas do acesso (`gh` ou um token de granularidade fina)

- Listas de runs, jobs e issues: Actions (leitura), Issues (leitura), Metadata (leitura). Alertas: alertas de Code scanning, Dependabot e Secret scanning (leitura). Pull requests e versões: Pull requests (leitura), Contents (leitura). Pacotes: `read:packages`.
- Só as ações opcionais da IA escrevem: voltar a executar um workflow precisa de Actions (escrita) e fechar um issue precisa de Issues (escrita). Deixe-as desligadas e dê ao acesso apenas leitura.


## Muitos repositórios

As leituras condicionais (`cache.etag`) fazem com que um repositório sem alterações não custe quota; `mode: lite`, `ecosystems`, `exclude` e `max_workers` limitam o trabalho; o webhook de entrada elimina a consulta dos repositórios que enviam eventos. `discover_limit` é o máximo de repositórios listados de uma conta (1000 por predefinição).
