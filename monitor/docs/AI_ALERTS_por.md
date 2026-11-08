<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Avisos para IAs

Um workflow vermelho de nada serve se ninguém de quem trabalha no repositório souber dele. O monitor escreve um pequeno feed que qualquer ferramenta de IA (Codex, Gemini CLI, Copilot) ou script pode ler.

## O que escreve (local, só leitura, sem rede)
- `ai_alerts.jsonl`: uma linha por evento (aberto, reconhecido, resolvido) com id estável, gravidade, repositório, workflow, conclusão, desde quando, sequência, ligação, uma causa provável (**real** ou **transitória**), uma ação sugerida e o estado.
- `ALERTS_BRIEF.md`: reescrito a cada ciclo e curto (`ai_alerts.brief_max_bytes`, 2 KB por defeito). Os avisos reais vêm primeiro.
- As causas transitórias (502/503/504, tempos esgotados, limites de utilização, falhas de transferência, uma execução que nunca arrancou) distinguem-se das falhas reais com regras que pode editar em `ai_alerts.transient_patterns`. Um aviso resolve-se sozinho quando o workflow volta a verde, e pode reconhecê-lo (`ack`), o que só altera este estado local.
- Tudo passa primeiro por um limpador: tokens, chaves, endereços de e-mail, endereços IP e a sua pasta pessoal nunca chegam aos ficheiros, aos endpoints nem ao hook.
- A pasta é `ai_alerts.folder` (por defeito junto ao monitor); escolha uma que as suas sessões de IA leiam. O `ci_red.json` traz um `ai_hint` opcional (classe, causa, ação) em cada workflow vermelho.

## Como uma IA o lê
- Ponha isto nas instruções do seu projeto ou skill: *«No início, lê ALERTS_BRIEF.md (caminho) e diz que avisos reais estão abertos.»*
- Ou pergunte ao monitor em execução: `GET /api/ai/brief` (Markdown, ou `?fmt=json`) e `GET /api/ai/alerts?since=SEGUNDOS`. Seguem as mesmas regras do resto da página (este computador; com o modo rede, o token de acesso).
- Ou acrescente o servidor MCP (só leitura): `python mcp_server.py`, ferramentas `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`; `--allow-ack` acrescenta `ack_alert` (só estado local). Gemini CLI, Codex e VS Code (Copilot): adicione o mesmo comando como servidor stdio nas definições MCP.

## Avisos que lhe chegam
- Um NOVO aviso real vai para os canais de notificação que já configurou (Definições > Notificações).
- Opcional, desligado por defeito: `ai_alerts.hook` envia por POST o novo aviso real (lista fechada de campos limpos) para um endereço deste computador, no máximo `max_per_hour` vezes por hora, para que um script seu acorde uma sessão de IA.
- Nada disto envia dados a um fornecedor de IA, executa um comando ou escreve no GitHub.
