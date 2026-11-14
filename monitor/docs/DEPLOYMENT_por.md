<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | **🇵🇹 Português**

# Executá-lo como serviço

O monitor é um programa que, por defeito, escuta apenas em `127.0.0.1` e não tem início de sessão. Estas notas servem para o executar como serviço: a imagem oficial, o Docker Compose com um proxy inverso, uma instalação clássica com systemd e o que acontece quando o GitHub revoga o acesso.

## Onde escuta

O monitor escuta de uma de três maneiras, e a página, `GET /api/accounts`, `monitor_cli.py status` e `monitor_cli.py accounts` dizem qual: **este computador** (apenas `127.0.0.1`: o predefinido, sem início de sessão), **a rede** (o modo de rede, `listen.network`: escuta também em `listen.host` e todos os pedidos levam o token de acesso) ou **atrás de um proxy** (o modo de rede com um proxy inverso declarado à frente: `listen.proxy_public_host`, `listen.secure_cookie` ou `listen.trusted_proxy`). A imagem e a unidade do serviço foram feitas para a segunda e a terceira; um monitor iniciado à mão fica na primeira.

No modo de rede, o supervisor de várias contas segue as mesmas regras do monitor de uma conta: o token de acesso em cada pedido (cookie, cabeçalho ou `POST /api/access`), bloqueio após tokens errados, a verificação de `Host`, TLS opcional com o seu certificado, a segunda porta de quem está no computador (`listen.local_port`), e as chaves que decidem a exposição, o acesso ao GitHub e as ações no GitHub apenas a partir do computador do monitor (um pedido vindo da rede chega à conta marcado como remoto).

## Sem navegador e a verificação de saúde

`python -m github_actions_monitor.service` é a entrada de um serviço: prepara as pastas e a primeira conta a partir do ambiente (ver a tabela abaixo) e arranca o monitor sem navegador. `python actions_monitor.py --no-browser --port 8765` continua a servir para um monitor que gere por si.

`GET /api/health` responde `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` mais o estado do ciclo de atualização e do acesso ao GitHub da conta; não chama o GitHub. `GET /api/health?deep=1` é a verificação profunda: responde 503 quando o ciclo de atualização de uma conta dura mais de `watchdog_minutes` (30 minutos se for 0) ou o seu fio desapareceu; no supervisor de várias contas também quando o próprio ciclo de supervisão parou, quando o ciclo de QUALQUER conta está preso ou quando nenhuma conta responde depois do arranque. Uma conta cujo acesso ao GitHub não serve (cega) é nomeada na resposta, mas não é uma falha: reiniciar não repara um acesso perdido, um novo repara.

`python -m github_actions_monitor.cli.healthcheck` faz essa chamada para um contentor ou um gestor de serviços (código de saída 0 saudável, 1 não saudável, 2 sem resposta, 3 recusado). Lê o token de acesso de `MONITOR_ACCESS_TOKEN`, do ficheiro indicado por `MONITOR_ACCESS_TOKEN_FILE` ou do que o serviço guarda em `MONITOR_STATE_DIR`. `monitor_cli.py health --deep` faz o mesmo a partir de qualquer computador.

## A imagem oficial

`ghcr.io/juanenrac/tools-github-actions-monitor` para `linux/amd64` e `linux/arm64`, com as etiquetas `1.8.2`, `1.8` e `latest`, construída pelo fluxo de publicação com uma atestação da sua proveniência. É feita em três etapas (`deploy/Dockerfile`) e contém apenas o Python, a CLI do GitHub, os certificados das CA e o código, só de leitura e pertencente ao root. Corre como o utilizador 10001 (nunca como root) e só escreve em dois volumes: `/config` (`actions_monitor.json`, criado no primeiro arranque e nunca substituído) e `/data` (`accounts/`, `state/` com o token de acesso, `secrets/`, o acesso do `gh`). Escuta no modo de rede na porta 8765 do contentor, pelo que todos os pedidos precisam do token de acesso, e não publica nenhuma porta por si.

```sh
docker run -d --name github-actions-monitor --restart unless-stopped \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  -e MONITOR_GITHUB_OWNER=my-org -e GH_TOKEN_FILE=/run/secrets/gh_token \
  -v "$PWD/gh_token.txt:/run/secrets/gh_token:ro" \
  -v monitor-config:/config -v monitor-data:/data \
  -p 127.0.0.1:8765:8765 \
  ghcr.io/juanenrac/tools-github-actions-monitor:latest

docker exec github-actions-monitor cat /data/state/access_token      # the access token, made on the first start
```

No primeiro arranque cria a configuração, a primeira conta (a partir de `MONITOR_GITHUB_OWNER`; várias com `MONITOR_ACCOUNTS=pessoal:eu,trabalho:minha-org`) e, se `MONITOR_ACCESS_TOKEN` não for dado, um token de acesso que guarda em `/data/state/access_token` (modo 600) e nunca imprime. Abra `http://127.0.0.1:8765/?access=TOKEN` uma vez: o cookie fica definido e o endereço é limpo. Com um bind mount em vez de um volume com nome, entregue a pasta ao utilizador 10001 (`chown -R 10001:10001`). A edição lite não está na imagem.

## Docker Compose, com proxy e TLS opcionais

`deploy/compose.yaml` executa o monitor com o código só de leitura, sem capacidades, o acesso como segredo do Docker e os dois volumes. O perfil `proxy` põe o Caddy (`deploy/Caddyfile`) à frente: obtém e renova sozinho o certificado de um nome público (`tls internal` para um nome da sua própria rede, `http://nome` para nenhum). Copie `deploy/.env.example` para `deploy/.env`, preencha-o e arranque:

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

Atrás do proxy, o monitor tem de conhecer o seu nome público e saber que a sessão é HTTPS: `MONITOR_PROXY_PUBLIC_HOST` e `MONITOR_SECURE_COOKIE=1`. Nada do que chega à porta principal conta então como o computador do monitor: use a segunda porta (`MONITOR_LOCAL_PORT`, 8766 na imagem, só loopback) com `docker compose exec monitor python monitor_cli.py ...` (a imagem aponta `MONITOR_URL` para ela).

## Uma instalação clássica com systemd

`deploy/github-actions-monitor.service` e `deploy/github-actions-monitor.env` executam a versão descomprimida como o utilizador `monitor`, com o reforço do systemd (nada gravável exceto a sua pasta, sem novos privilégios), reiniciam-na em caso de falha, verificam a saúde profunda após o arranque e voltam a ler os ficheiros de credenciais com `systemctl reload`.

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

O ficheiro env guarda os dados em `/var/lib/github-actions-monitor` e o acesso em `/etc/github-actions-monitor/gh_token` (modo 600). Escuta em `127.0.0.1`, a menos que aí ative o modo de rede.

launchd (macOS): `ProgramArguments` = `/usr/bin/python3`, `-m`, `github_actions_monitor.service`, as variáveis em `EnvironmentVariables`, `KeepAlive` e `RunAtLoad` a true. Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/caminho/para/actions_monitor.py --no-browser"`.

## Variáveis de ambiente

Só são lidos os nomes desta tabela. No serviço, um valor ilegível é ignorado com um aviso e não altera nada. As que nomeiam uma parte da configuração (`MONITOR_LISTEN_*`, `MONITOR_ALLOWED_HOSTS`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_SECURE_COOKIE`, `MONITOR_TRUSTED_PROXY`, `MONITOR_LOCAL_PORT`, `MONITOR_TLS_*`, `MONITOR_QUERY_ACCESS`, `MONITOR_TEAM_MODE`) são escritas em `listen` e `auth` em cada arranque do serviço, pelo que o ambiente continua a mandar nelas; tudo o resto do ficheiro é seu.

| Variável | O que faz |
|---|---|
| `MONITOR_GITHUB_OWNER` | O utilizador ou organização a vigiar; a primeira conta é criada a partir dele no primeiro arranque. |
| `MONITOR_ACCOUNT` | O id da primeira conta (por defeito `default`). |
| `MONITOR_ACCOUNTS` | Várias contas de uma vez: `pessoal:eu,trabalho:minha-org` (id:proprietário). Só quando ainda não há nenhuma conta. |
| `MONITOR_LANG` | O idioma dos textos (`en es de fr it ja zh pt`). |
| `MONITOR_PORT` | A porta dentro do contentor ou do serviço (por defeito 8765). |
| `MONITOR_CONFIG` | O ficheiro de configuração (a imagem: `/config/actions_monitor.json`); criado no primeiro arranque e nunca substituído. |
| `MONITOR_ACCOUNTS_DIR` | A pasta das contas, uma pasta por conta (a imagem: `/data/accounts`). |
| `MONITOR_STATE_DIR` | Ficheiros que de outro modo ficariam junto ao código: o token de acesso do serviço, a auditoria dos inícios de sessão (a imagem: `/data/state`). |
| `MONITOR_SECRET_DIR` | Onde vive o token guardado pelo próprio monitor, se o ativar (a imagem: `/data/secrets`). |
| `GH_CONFIG_DIR` | A pasta de configuração do `gh` (a imagem: `/data/gh`). |
| `GH_TOKEN_FILE` | Um ficheiro com o token do GitHub na primeira linha (um segredo do Docker, uma credencial do systemd). Lido no arranque e de novo com SIGHUP. |
| `GH_TOKEN` | Um token do GitHub no ambiente; o `gh` lê-o. Um ficheiro é melhor: o ambiente é visível para qualquer processo do contentor. |
| `GH_HOST` | O nome de um anfitrião do GitHub Enterprise Server: todas as chamadas e todas as ligações da página usam-no. |
| `MONITOR_ACCESS_TOKEN` | O token de acesso do modo de rede (pelo menos 16 caracteres). Sem ele, o serviço cria um e guarda-o em `MONITOR_STATE_DIR`. |
| `MONITOR_ACCESS_TOKEN_FILE` | Um ficheiro com o token de acesso na primeira linha, em vez da variável. |
| `MONITOR_LISTEN_NETWORK` | `1` = o modo de rede (`listen.network`): escuta em `MONITOR_LISTEN_HOST` e todos os pedidos precisam do token de acesso. A imagem ativa-o. |
| `MONITOR_LISTEN_HOST` | O endereço em que escuta no modo de rede (`0.0.0.0` na imagem; noutros sítios é melhor um endereço privado da máquina). |
| `MONITOR_ALLOWED_HOSTS` | Nomes de anfitrião que o monitor aceita além do seu endereço, separados por vírgulas (`listen.allowed_hosts`). |
| `MONITOR_PROXY_PUBLIC_HOST` | O nome público do proxy inverso (`listen.proxy_public_host`); declara o proxy. |
| `MONITOR_SECURE_COOKIE` | `1` = a sessão é HTTPS (um proxy termina-a): o cookie leva Secure (`listen.secure_cookie`). |
| `MONITOR_TRUSTED_PROXY` | `1` = o proxy corre na MESMA máquina e o seu `X-Forwarded-For` é acreditado (`listen.trusted_proxy`). |
| `MONITOR_LOCAL_PORT` | Uma segunda porta, só loopback, para quem está no computador quando há um proxy declarado (`listen.local_port`; 8766 na imagem). |
| `MONITOR_TLS_CERT_FILE` | Um certificado (PEM) para servir HTTPS diretamente (`listen.tls_cert_file`); com a chave. Se não puder ser usado, o monitor não arranca em HTTP simples. |
| `MONITOR_TLS_KEY_FILE` | A chave privada desse certificado (`listen.tls_key_file`). |
| `MONITOR_QUERY_ACCESS` | `0` = o endereço com `?access=` já não abre sessão (`listen.query_access`); use `POST /api/access`. |
| `MONITOR_TEAM_MODE` | `1` = o modo de equipa (`auth.enabled`): utilizadores, papéis e sessões. |
| `MONITOR_SERVICE` | `1` = corre como serviço: não desiste perante um acesso que não serve e o doctor verifica a retenção. A imagem e o serviço ativam-no. |
| `MONITOR_URL` | Para o `monitor_cli.py` e a verificação de saúde: o endereço do monitor (a imagem: a segunda porta). |
| `MONITOR_CA_FILE` | Para o `monitor_cli.py`: um ficheiro PEM com a autoridade que assinou o certificado HTTPS do monitor. |
| `MONITOR_USER` | Para o `monitor_cli.py` no modo de equipa: o utilizador com que iniciar sessão. |
| `MONITOR_PASSWORD_FILE` | Para o `monitor_cli.py`: um ficheiro com a palavra-passe de `MONITOR_USER` na primeira linha. |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`: segundos que a suite normal pode demorar antes de a porta falhar (por defeito 3600; de 60 a 86400). |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`: segundos que a suite do zip extraído pode demorar (por defeito 3600; de 60 a 86400). |

## Quando o GitHub revoga ou deixa caducar o acesso

Cada conta é um processo próprio, pelo que um acesso que deixa de funcionar só afeta essa conta. Após duas recusas seguidas que dizem que o próprio acesso não serve (um 401, `Bad credentials`, um token caducado ou revogado, uma conta suspensa, nenhum acesso), a conta fica **cega**: a página, a verificação de saúde profunda, `GET /api/accounts` (`state: blind`) e o `monitor_cli.py` dizem-no, abre-se um **alerta crítico de sistema** (`system.credential_blind`, sentinela `system`) no separador de alertas, e os tipos de notificação `credential_blind` (ativo por defeito) e `credential_back` avisam os canais uma vez. A recusa de uma só permissão (um 403 para um repositório) não torna uma conta cega. As outras contas continuam e a verificação de saúde profunda mantém-se verde. A conta continua a tentar e o primeiro ciclo bom fecha o alerta.

Um serviço que arranca com um acesso que já não serve fica ativo e cego em vez de desistir, para haver algo a substituir. O token de uma conta vem de, ganha o primeiro que existir: o ficheiro `credential` da sua pasta (escrito por uma substituição), o ficheiro indicado por `GH_TOKEN_FILE`, depois o que o `gh` usa (`GH_TOKEN` ou o seu próprio início de sessão). Uma substituição não precisa de reiniciar o supervisor nem a conta, de três maneiras:

```sh
# 1. the command line (a token is read from a file or the standard input, never from a flag)
docker compose exec -T monitor python monitor_cli.py credential replace --account default --new-token-file - < new_token.txt
python monitor_cli.py credential replace --url https://monitor.example.org --user ann --password-file pw.txt --account default --new-token-file new_token.txt

# 2. the administrator endpoint (an administrator session in the team mode, or the computer of the monitor)
#    POST /api/accounts/<id>/credential   {"action": "replace", "token": "..."}   or   {"action": "reload"}
#    (a monitor without a supervisor: POST /api/credential, from its own computer)

# 3. replace the file and send SIGHUP: every account reads its credential files again
docker kill --signal HUP github-actions-monitor
systemctl reload github-actions-monitor
```

O novo token é verificado no GitHub (a chamada `rate_limit`, gratuita) ANTES de ser guardado: um token que o GitHub recusa não altera nada e responde 422 (`rejected`). Um bom é escrito apenas na pasta dessa conta (modo 600), usado de imediato, e a conta volta a ler sem esperar. No modo de equipa, o endpoint é para uma sessão `admin` (com o token CSRF de uma sessão por cookie) e a auditoria regista quem o fez, nunca o token; sem o modo de equipa, com o modo de rede ativo, só o computador do monitor pode. O token nunca aparece numa resposta, num registo, num alerta nem na página.

## Primeiro arranque, cópia de segurança e atualização

Primeiro arranque como serviço: defina o proprietário e o acesso (`GH_TOKEN_FILE`), arranque, leia uma vez o token de acesso (`/data/state/access_token`), abra a página e execute `monitor_cli.py health --deep`. `python actions_monitor.py --doctor` com `MONITOR_SERVICE=1` avisa ainda de um bloco de retenção em falta e de contas que partilham o mesmo token.

Cópia de segurança: tudo o que há a guardar está nos dois volumes. Faça uma cópia consistente do armazenamento antes de atualizar e uma cópia dos volumes:

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

Atualização: os dados sobrevivem porque vivem nos volumes. Fixe uma versão (`:1.8.2`) em produção, descarregue, recrie e verifique a atestação da imagem. Um monitor mais antigo nunca abre um armazenamento mais recente (ver `STORAGE.md`); guarde a cópia até a nova versão ter funcionado.

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:1.8.2 --owner JuanenRac
```

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

## A linha de comandos contra outro computador

O `monitor_cli.py` funciona contra um monitor de outra máquina: `--url https://monitor.example.org` (ou `MONITOR_URL`), o token de acesso de `MONITOR_ACCESS_TOKEN` ou `--token-file`, `--ca-file` (ou `MONITOR_CA_FILE`) para confiar na autoridade que assinou um certificado HTTPS próprio e, no modo de equipa, `--user NOME` com `--password-file FICHEIRO` (ou `MONITOR_USER`, `MONITOR_PASSWORD_FILE`), que inicia sessão com uma sessão Bearer (`auth.allow_bearer`). `status`, `accounts`, `alerts`, `health` (`--deep`) e `credential` funcionam da mesma forma e os códigos de saída são os mesmos (3 = recusado, também para uma conta cega em `status` e `accounts`). HTTP simples para outro computador imprime um aviso.

## Permissões mínimas do acesso (`gh` ou um token de granularidade fina)

- Listas de runs, jobs e issues: Actions (leitura), Issues (leitura), Metadata (leitura). Alertas: alertas de Code scanning, Dependabot e Secret scanning (leitura). Pull requests e versões: Pull requests (leitura), Contents (leitura). Pacotes: `read:packages`.
- Só as ações opcionais da IA escrevem: voltar a executar um workflow precisa de Actions (escrita) e fechar um issue precisa de Issues (escrita). Deixe-as desligadas e dê ao acesso apenas leitura.

## Muitos repositórios

As leituras condicionais (`cache.etag`) fazem com que um repositório sem alterações não custe quota; `mode: lite`, `ecosystems`, `exclude` e `max_workers` limitam o trabalho; o webhook de entrada elimina a consulta dos repositórios que enviam eventos. `discover_limit` é o máximo de repositórios listados de uma conta (1000 por predefinição).

## A correr durante meses: armazenamento e retenção

Mantenha `accounts/` (ou a base de dados) num volume que sobreviva ao contentor e faça uma cópia com `python tools/backup_storage.py backup FICHEIRO.zip --backend file` (ou `sqlite`) antes de atualizar. De origem, uma passagem curta remove os eventos com mais de 90 dias e as análises com mais de 180; defina `retention` na configuração para mudar isso, e `MONITOR_SERVICE=1` faz o `--doctor` tratar o monitor como um serviço (e então avisa se não houver bloco `retention` ou se os eventos crescerem muito). Com SQLite, uma base de dados por conta é o predefinido; um ficheiro partilhado é possível e está descrito em [STORAGE_por.md](STORAGE_por.md).
