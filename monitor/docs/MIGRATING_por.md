<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Atualizar a partir de uma versão anterior à 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · **Português**

A versão 1.5.0 deu nomes em inglês a ficheiros, pastas, scripts e a uma definição. Não se perde nada: o monitor continua a LER os nomes antigos, por isso pode atualizar primeiro e arrumar depois.

## Passos

1. Pare o monitor e descomprima a versão nova sobre a pasta antiga (mantenha o seu `actions_monitor.json`).
2. Veja o que mudaria: `python migrate_state.py` (simulação, não altera nada).
3. Faça-o: `python migrate_state.py --apply` copia os ficheiros antigos para os nomes novos e mantém os antigos; acrescente `--move` para os renomear. Nunca se substitui o que já existe, e a definição `parte_history_days` passa a `report_history_days` depois de guardar uma cópia de `actions_monitor.json`.
4. Arranque o monitor com `MONITOR_GITHUB_ACTIONS` (o mesmo lançador de sempre) e use `BATCH_GITHUB_ACTIONS` para as ferramentas por lotes.
5. Apague os lançadores antigos que ainda tenha: `LOTE_GITHUB_ACTIONS.bat`, `.sh` e `.command`.

## Nomes antigos e novos

| Antes da 1.5.0 | Desde a 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
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
3. Opcional: `python actions_monitor.py --doctor` verifica a instalação.

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
- Ficheiros novos junto do monitor: `degraded.json` e `degraded_lite.json` (os contadores de falhas engolidas); podem ser apagados a qualquer momento.
- O histórico de alterações (Ajuda > Registo de alterações) está traduzido: um ficheiro `docs/CHANGELOG_<idioma>.md` por idioma.

# Da 1.6.6 para 1.6.7

Não é preciso converter nada. O que se comporta de forma diferente, de propósito:

- **Modo rede atrás de um proxy HTTPS na porta 443**: nova definição `listen.proxy_public_host` (vazia por predefinição; se a deixar assim, nada muda). Ponha aí o nome de anfitrião público do proxy quando ele reencaminha `Host` e `Origin` sem porta; esse único nome é então aceite tal como está, só enquanto o modo rede está ligado e a sessão é HTTPS. Só se altera a partir do próprio computador. Atrás de um proxy que mantém a porta nada muda.
- O histórico de alterações (Ajuda > Registo de alterações) está agora traduzido para a 1.6.7 e a 1.6.5 nos outros sete idiomas; as entradas mais antigas continuam a mostrar o texto em inglês sob um aviso traduzido.

# Da 1.6.7 para 1.6.8

Não é preciso converter nada e nenhuma definição muda.

- Novidade no repositório (não no pacote): `python tools/manual_check_live.py proxy ANFITRIÃO [PORTA] [LIGAR]` verifica o seu proxy HTTPS real na porta 443 face a `listen.proxy_public_host`; defina antes `MONITOR_ACCESS_TOKEN`, é lido e nunca impresso.
- O histórico de alterações (Ajuda > Registo de alterações) está agora traduzido nos outros sete idiomas da 1.6.8 à 1.6.3.
