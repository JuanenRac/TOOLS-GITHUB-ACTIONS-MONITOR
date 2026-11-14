<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Atualizar a partir de uma versão anterior à 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · **Português**

A versão 1.5.0 deu nomes em inglês a ficheiros, pastas, scripts e a uma definição. Não se perde nada: o monitor continua a LER os nomes antigos, por isso pode atualizar primeiro e arrumar depois.

## Passos

1. Pare o monitor e descomprima a versão nova sobre a pasta antiga (mantenha o seu `actions_monitor.json`).
2. Veja o que mudaria: `python bin/migrate_state.py` (simulação, não altera nada).
3. Faça-o: `python bin/migrate_state.py --apply` copia os ficheiros antigos para os nomes novos e mantém os antigos; acrescente `--move` para os renomear. Nunca se substitui o que já existe, e a definição `parte_history_days` passa a `report_history_days` depois de guardar uma cópia de `actions_monitor.json`.
4. Arranque o monitor com `MONITOR_GITHUB_ACTIONS` (o mesmo lançador de sempre) e use `BATCH_GITHUB_ACTIONS` para as ferramentas por lotes.
5. Apague os lançadores antigos que ainda tenha: `LOTE_GITHUB_ACTIONS.bat`, `.sh` e `.command`.

## Nomes antigos e novos

| Antes da 1.5.0 | Desde a 1.5.0 |
|---|---|
| `leer_parte.py` | `bin/read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`, o seu esquema e os ficheiros de `--export-status` não mudaram. O idioma é o inglês até escolher outro nas definições.

# Da 1.5.x para a 1.6.x

Não há nada para converter: o monitor continua a ler o seu `actions_monitor.json` e acrescenta as chaves novas, com valores seguros, a primeira vez que guardar a partir das Definições.

1. Pare o monitor e descomprima a versão nova por cima da pasta antiga (mantenha o seu `actions_monitor.json` e os ficheiros de catálogo).
2. Arranque-o como antes. Aparecem ficheiros novos ao lado (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`); podem ser apagados a qualquer momento.
3. Opcional: `python bin/actions_monitor.py --doctor` verifica a instalação.

O que muda: existe a **edição lite** (`MONITOR_LITE_GITHUB_ACTIONS`, porta 8766, o seu próprio `actions_monitor_lite.json`, sem sentinela); o **vermelho no main** é uma só regra (o último run concluído de cada workflow no ramo por defeito; os runs cancelados, ignorados, neutros e caducados não dizem nada), por isso um número pode diferir da 1.5.x; a página de Definições começa por um separador **Básico**; as notificações, a análise, o linter, os eventos do webhook e o assistente de IA existem e estão **desligados** até os ativar; escrever no GitHub continua a exigir a sua confirmação explícita. O Rich e o Textual continuam opcionais; Python 3.11 ou superior.

# Da 1.6.4 para 1.6.5

Não é preciso converter nada. O que passa a comportar-se de outra forma, de propósito, porque o que não está provado deixa de ser dado como seguro:

- **Lotes**: o `finalize` só oferece para assinar uma execução cujo lote REGISTA que foi construída sobre o commit verificado. Um lote escrito por uma versão anterior diz `needs_review`. Para o usar na mesma: `finalize --accept-legacy` relê a execução no GitHub, só a aceita se o seu commit for o registado e pede a palavra LEGACY antes de cada assinatura. Ou dispare a compilação de novo.
- **CI verde** significa que os ficheiros de workflow obrigatórios passaram nesse commit (por omissão `ci.yml`; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), que nada falhou nem espera aprovação e que a lista de execuções está completa. Um repositório cujo ficheiro de CI tenha outro nome precisa desse nome em `dispatch.required_ci`.
- **Um `git fetch` falhado** (sem rede, sem credenciais) pára o despacho desse repositório.
- **targets.json**: `tool` tem de ser um nome de ficheiro simples (sem pasta nem `..`) que esteja na pasta das ferramentas; `extra` só admite pares `-f chave=valor` (não `dry_run` nem `ref`); `finalize_flags` só opções longas como `--bench`. Um catálogo que não cumpra é recusado com o motivo.
- **Notificações**: `max_per_hour` conta mensagens (uma por canal), não eventos.
- **Webhook**: cada pedido precisa de `X-GitHub-Delivery` (o GitHub envia-o sempre); um id repetido é ignorado; o proprietário de `full_name` tem de ser a conta vigiada.
- **act**: um clone que seja ligação para outra pasta é recusado (`act.allow_symlinks` permite-o).
- **Modo de rede**: apenas endereços IPv4; o endereço mostrado é aquele em que o servidor escuta; `GET /api/sentinel/parte.txt?save=1` já não escreve (a cópia é um POST com o token de uma só utilização).
- O token do GitHub guardado já não é posto no ambiente do processo: só o `gh` o recebe.
- O teste que descompacta o zip numa pasta limpa deixou de fazer parte da bateria normal; o `make_release.py` executa-o como etapa própria.

# Da 1.6.5 para 1.6.6

Não é preciso converter nada. O que se comporta de forma diferente, de propósito:

- **Modo rede com HTTPS**: as alterações feitas a partir da página já funcionam; o `Origin` tem de levar o esquema da sessão e a porta do monitor. Atrás de um proxy mantenha a porta do monitor no endereço, ou a verificação recusa-o.
- **Modo rede**: toda a definição que o esquema marca como `secure` só se altera a partir do próprio computador (antes: só `listen.`, `github_token.`, `act.`, `github_actions.`). Um script noutro computador que alterava `webhook.*`, `notify.*` e semelhantes recebe agora 403 `local_only`.
- **act**: depois do Stop a execução fica livre de imediato; um arranque logo a seguir já não responde `busy`.
- Ficheiros novos em `data/`: `degraded.json` e `degraded_lite.json` (os contadores de falhas engolidas); podem ser apagados a qualquer momento.
- O histórico de alterações (Ajuda > Registo de alterações) está traduzido: um ficheiro `docs/CHANGELOG_<idioma>.md` por idioma.

# Da 1.6.6 para 1.6.7

Não é preciso converter nada. O que se comporta de forma diferente, de propósito:

- **Modo rede atrás de um proxy HTTPS na porta 443**: nova definição `listen.proxy_public_host` (vazia por predefinição; se a deixar assim, nada muda). Ponha aí o nome de anfitrião público do proxy quando ele reencaminha `Host` e `Origin` sem porta; esse único nome é então aceite tal como está, só enquanto o modo rede está ligado e a sessão é HTTPS. Só se altera a partir do próprio computador. Atrás de um proxy que mantém a porta nada muda.
- O histórico de alterações (Ajuda > Registo de alterações) está agora traduzido para a 1.6.7 e a 1.6.5 nos outros sete idiomas; as entradas mais antigas continuam a mostrar o texto em inglês sob um aviso traduzido.

# Da 1.6.7 para 1.6.8

Não é preciso converter nada e nenhuma definição muda.

- Novidade no repositório (não no pacote): `python tools/manual_check_live.py proxy ANFITRIÃO [PORTA] [LIGAR]` verifica o seu proxy HTTPS real na porta 443 face a `listen.proxy_public_host`; defina antes `MONITOR_ACCESS_TOKEN`, é lido e nunca impresso.
- O histórico de alterações (Ajuda > Registo de alterações) está agora traduzido nos outros sete idiomas da 1.6.8 à 1.6.3.

# Da 1.6.8 para 1.7.0

Não é preciso converter nada: sem uma pasta `accounts/` o monitor funciona exatamente como antes.

- As **várias contas** são opcionais. Para as usar execute `python bin/actions_monitor.py --migrate-accounts` (um ensaio) e depois acrescente `--apply` para copiar os seus ficheiros para `accounts/default/`; os originais ficam até os apagar. Acrescente mais contas como `accounts/<id>/actions_monitor.json`. Veja `ACCOUNTS.md`.
- Com uma pasta `accounts/`, `python bin/actions_monitor.py` arranca um supervisor que executa um monitor por conta; `--account <id>` executa só uma. A edição lite não tem nada disto.
- Novidades: `?view=` e `?chrome=0` no endereço da página, `GET /api/accounts`, `GET /api/live-status` e um só `POST /api/webhook` para todas as contas.

# Da 1.7.x para a nova estrutura de pastas

O código vive agora em `src/github_actions_monitor/`, a página, os ficheiros de exemplo e os idiomas em `assets/`, e os scripts de versão e de migração em `tools/`. Nada do que utiliza muda: os lançadores (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) ficam onde estavam e abrem o mesmo endereço e a mesma porta, e os comandos deste guia (`python bin/read_report.py`, `python bin/actions_monitor.py --doctor`, `python bin/monitor_cli.py status` ...) continuam a funcionar, porque na pasta do produto fica um pequeno ficheiro de entrada com o mesmo nome. Os lançadores executam `python -m github_actions_monitor` (completo) e `python -m github_actions_monitor.lite` (lite) com `src/` no caminho.

Os seus dados não se movem: `actions_monitor.json`, as caches, os registos, `config_backups/`, `accounts/` e os seus próprios ficheiros de catálogo ficam na pasta do produto junto dos lançadores, nunca dentro de `src/`. Os exemplos neutros e o `quotas.json` que acompanham o programa estão agora em `assets/examples/`; um `quotas.json` seu junto dos lançadores continua a ter prioridade.

## Passos

1. Pare o monitor e descomprima a nova versão por cima da pasta antiga (mantenha o seu `actions_monitor.json`).
2. Arranque-o como sempre. Funciona mesmo que não faça mais nada.
3. Para retirar os restos da antiga estrutura plana: `python tools/migrate_layout.py` (simulação) e depois `python tools/migrate_layout.py --apply`. Copia os seus ficheiros de configuração para `layout_backup_<marca>/config/` e move os módulos antigos, a página antiga, os exemplos antigos e a pasta `locales/` antiga para `layout_backup_<marca>/old_code/`. Nada é apagado, nada do que existe é substituído e os seus dados não são tocados. `python bin/actions_monitor.py --doctor` avisa enquanto sobrarem ficheiros antigos.
4. Um script seu que importava um módulo pelo nome plano antigo (`import read_report`) passa a importar `github_actions_monitor.<pacote>.<módulo>` com `src/` no caminho.

| Pacote | O que contém |
|---|---|
| `app` | o servidor, as definições, os modos de trabalho, a configuração partilhada |
| `accounts` | várias contas: registo, supervisor, processo filho |
| `sentinels` | as sentinelas, o centro de alertas, os painéis |
| `security` | guarda local, segredos, webhook, confirmação, guarda de rede, assinaturas, ficheiros privados |
| `data_pipeline` | eventos, análise, leituras condicionais, descoberta, quotas, a regra do vermelho em main |
| `integrations` | GitHub, notificações, OpenTelemetry, espelho, runners, MCP, o feed e o hook da IA |
| `cli` | as ferramentas de linha de comandos |
| `ui` | Acerca de, documentos de ajuda, vistas de terminal |
| `i18n`, `util` | os oito idiomas; pequenos utilitários partilhados |

## Mover o estado entre ficheiros e SQLite (1.8.0)

Não é preciso migrar nada para atualizar: os ficheiros continuam a ser o predefinido. Se quiser o estado em SQLite, `python tools/migrate_storage.py --from file --to sqlite` mostra o que copiaria (simulação); acrescente `--apply` para copiar e verificar. Os seus ficheiros nunca são alterados nem apagados. Veja [STORAGE_por.md](STORAGE_por.md).

# De 1.7.9 para 1.8.0

Não é preciso converter nada. Uma definição pode precisar de uma alteração:

- extra_reader.file aponta para fora da pasta de contas, pelo que a segunda conta NÃO é usada. Mova o ficheiro do token para a pasta de contas (accounts/, ou a pasta indicada por MONITOR_ACCOUNTS_DIR) e mantenha o seu caminho em extra_reader.file, ou ative extra_reader.any_folder em Definições > Quota.
