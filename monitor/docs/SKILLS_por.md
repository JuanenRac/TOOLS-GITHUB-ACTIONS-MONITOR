<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SKILLS.md) | [🇪🇸 Español](SKILLS_spa.md) | [🇫🇷 Français](SKILLS_fra.md) | [🇮🇹 Italiano](SKILLS_ita.md) | [🇩🇪 Deutsch](SKILLS_deu.md) | [🇨🇳 简体中文](SKILLS_zho.md) | [🇯🇵 日本語](SKILLS_jpn.md) | **🇵🇹 Português**

# Skills para IAs

O monitor traz duas skills: guias curtos, em inglês, que dizem a uma IA como trabalhar com ele. Estão na pasta `skills/` do pacote, na página (Definições, separador IA) e um comando instala-as.

## As duas skills

- `skills/internal`: para a IA integrada no monitor, local (Ollama, um servidor llama.cpp, LM Studio) ou externa (a API de um fornecedor). Diz o que é o monitor e o que vê, o que pode ler, o que nunca deve fazer, como diagnosticar um vermelho, quando se calar e como usar e propor lições. O seu núcleo (`SKILL.md`) é acrescentado a cada prompt dessa IA, cortado a `ai.skill_max_chars`, quando `ai.skill` está ligado.
- `skills/external`: para as IA que falam com o monitor a partir de fora, em todos os sentidos: ler (`/api/ai/*`, os ficheiros de `ai/`), ser avisadas (o stream ou o resumo de poucos em poucos minutos), escrever (confirmar leitura, lições, falhas, preferências de notificação) com as permissões devidas, a ligação entre o monitor e uma sessão, o resumo antes do push e todo o ciclo de autoaprendizagem. Cobre uma IA com linha de comandos, uma IA só com HTTP ou ficheiros, uma IA com MCP e uma IA no stream.

## O que contém

Cada skill é um `SKILL.md` curto (o núcleo) e uma pasta `references/` lida apenas quando é preciso, para que um modelo com pouco contexto possa levar só o núcleo: cenários passo a passo (um vermelho real, um vermelho passageiro, quota baixa, um monitor degradado, uma falha repetida, uma lição nova, sem rede, vários ecrãs), o ciclo de autoaprendizagem, os fornecedores e os seus limites, a segurança (injeção de instruções a partir dos registos, segredos, permissões mínimas, auditoria do que uma IA escreve) e as referências geradas a partir do código.

## Nada fica de fora

As referências (`api.md`, `cli.md`, `settings.md`, `files.md`, `roles.md`, `tabs.md`) e `skills/COVERAGE.md` são GERADAS a partir do código por `python tools/make_skill_refs.py`: cada endpoint com o papel mínimo que o pode chamar, cada comando e opção, cada definição com o seu valor predefinido, cada ficheiro que o monitor escreve, cada papel e cada separador. Um teste lê as mesmas listas do código e falha se algo não for nomeado nas skills, por isso um endpoint, comando, definição ou ficheiro novo não pode aparecer sem ser descrito às IA (e o gerador pára até a sua nota ser escrita).

## Instalar

Copie a skill para a pasta de onde a sua ferramenta de IA lê as suas skills:

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## Segurança do instalador

Escreve `github-actions-monitor-internal` ou `github-actions-monitor-external` dentro da pasta indicada e mais nada. Nunca substitui um ficheiro que difira do do pacote (mantém o seu e diz qual) e recusa a unidade D: e caminhos de rede. Uma segunda execução não altera nada.

## Na página e por HTTP

Nas Definições, separador IA, o bloco **Skills para IAs** tem Copiar (o núcleo da skill) e Descarregar (a skill completa com as referências num ficheiro) para cada uma. `GET /api/skills` lista-as e `GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` devolve o texto; é só de leitura.

## Definições

`ai.skill` (ligado) e `ai.skill_max_chars` (3000; 1500 para um modelo local pequeno). Registar falhas a partir de fora é `POST /api/ai/failures` e exige `lessons.allow_write` e um administrador, como escrever uma lição.

## Publicação num registo de skills

`python tools/prepare_skill_bundle.py --out DIR` deixa a pasta da skill externa pronta a publicar (SKILL.md, referências, `bundle.json` com a versão do monitor e a licença, `SHA256SUMS`); as mesmas fontes dão os mesmos bytes. Não publica nada: o envio para o ClawHub faz-se à mão, com a conta do responsável, depois de ler as condições.

## Assistentes

Só se diz testado o que foi realmente experimentado.

| Assistente ou via | Linha de comandos | HTTP e ficheiros | MCP |
|---|---|---|---|
| Claude Code | testado | testado | compatível por protocolo, não testado |
| Outros assistentes | compatível por protocolo, não testado | compatível por protocolo, não testado | compatível por protocolo, não testado |
