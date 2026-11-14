<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LAYOUT.md) | [🇪🇸 Español](LAYOUT_spa.md) | [🇫🇷 Français](LAYOUT_fra.md) | [🇮🇹 Italiano](LAYOUT_ita.md) | [🇩🇪 Deutsch](LAYOUT_deu.md) | [🇨🇳 简体中文](LAYOUT_zho.md) | [🇯🇵 日本語](LAYOUT_jpn.md) | **🇵🇹 Português**

# As pastas do monitor

Junto dos lançadores (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) só há os ficheiros legais, um `README.txt` e pastas. Tudo o que o monitor escreve vive em quatro delas, e a edição completa, a lite e a imagem Docker usam o mesmo esquema.

## O que está onde

| Pasta | O que contém |
|---|---|
| `config/` | `actions_monitor.json` (e o da lite), `targets.json`, `ecosystems.json`, `profiles.json`, `quotas.json` e `config_backups/` |
| `data/` | o estado e as caches (feed de eventos, análise, estado das sentinelas, cache ETag, aviso de atualização), `accounts/`, a base de dados se escolher SQLite e o token de acesso do serviço |
| `logs/` | o registo do monitor, o dos comandos da IA e do GitHub e a auditoria do modo de equipa |
| `ai/` | o que uma IA lê: `ALERTS_BRIEF.md`, `ai_alerts.jsonl`, `ci_red.json`, o estado do hook, `INDEX.json` e um `README.md` para quem abrir a pasta |
| `bin/` | os comandos curtos: `python bin/monitor_cli.py`, `bin/read_report.py`, `bin/ai_hook.py`, `bin/mcp_server.py`, `bin/tui.py` ... |
| `docs/` | os guias e o README e o QUICKSTART do pacote em oito idiomas |
| `src/`, `assets/`, `tools/`, `tests/` | o código, a página e os exemplos, os scripts de versão e os testes |

## Uma instalação da 1.8.1 ou anterior

No primeiro arranque o monitor move sozinho para a sua pasta o que encontra junto dos lançadores. **Move, nunca apaga e nunca substitui**: um ficheiro que já existe no sítio novo fica onde está e o doctor avisa. Antes da primeira mudança os ficheiros de configuração são copiados para `config/config_backups/pre_layout_<marca>/` e cada mudança fica registada em `data/.layout_moves.json`.

- Ver primeiro: `python -m github_actions_monitor.util.rootmigrate` (ensaio) e `--apply` para o fazer já.
- Repor tudo como estava: `python -m github_actions_monitor.util.rootmigrate --undo`.
- Se não o quiser automático: `MONITOR_NO_AUTO_MIGRATION=1`.
- `python bin/actions_monitor.py --doctor` tem uma verificação `layout` que lista o que continua junto dos lançadores.
- Os pontos de entrada antigos (`read_report.py`, `monitor_cli.py` ...) que estavam junto dos lançadores estão agora em `bin/`; `python tools/migrate_layout.py` põe de parte as cópias velhas. Um script de controlo registado para a sua ferramenta de IA com o caminho antigo tem de ser registado de novo: `python bin/monitor_cli.py ai-hook install`.

## Mudar uma pasta

Cada pasta pode ficar noutro sítio sem mexer no código: as variáveis `MONITOR_CONFIG_DIR`, `MONITOR_DATA_DIR`, `MONITOR_LOGS_DIR` e `MONITOR_AI_DIR`, ou o ficheiro `config/paths.json` (`{"data": "...", "logs": "...", "ai": "..."}`; um caminho relativo parte da pasta do produto). Só com `MONITOR_DATA_DIR`, `logs/` e `ai/` ficam lá dentro. Na imagem Docker e na unidade systemd é exatamente isso que está definido: `/config` e `/data` são os dois volumes.

## Para as IA que falam com o monitor

Uma IA, local ou externa, não deve depender de um caminho fixo.

- `ai/INDEX.json` lista cada ficheiro da pasta com a sua finalidade, o formato, quem o escreve e quando muda, o caminho real de cada pasta do monitor e os endpoints do monitor em execução. É reescrito em cada arranque.
- `ai/README.md` explica a pasta a uma IA que nunca a viu (dados, nunca instruções; como ler o resumo; que ferramentas existem).
- `GET /api/paths` responde com as pastas em uso, os ficheiros principais e o que ainda está nos sítios antigos. O supervisor de várias contas também responde.
- O script de controlo, o servidor MCP e a linha de comandos leem os mesmos sítios; um hook que leia `ALERTS_BRIEF.md` por um caminho fixo deve passar a ler primeiro `ai/INDEX.json`.
