<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](HEALTH.md) | [🇪🇸 Español](HEALTH_spa.md) | [🇫🇷 Français](HEALTH_fra.md) | [🇮🇹 Italiano](HEALTH_ita.md) | [🇩🇪 Deutsch](HEALTH_deu.md) | [🇨🇳 简体中文](HEALTH_zho.md) | [🇯🇵 日本語](HEALTH_jpn.md) | **🇵🇹 Português**

# A saúde de um repositório e da equipa

Só Complete. Duas vistas só de leitura, feitas com o que o monitor já tem (execuções, fluxos vermelhos e encravados, os alertas abertos de cada sentinela e a preparação das versões). Nunca chamam o GitHub.

## De que é feita a saúde de um repositório

| Parte | O que diz |
|---|---|
| CI | sucessos e falhas das últimas 24 horas, os fluxos que estão vermelhos agora, as execuções encravadas |
| Alertas | todos os alertas abertos das sentinelas de CI, Colaboração e Segurança, por sentinela e por nível |
| Versão | a linha da preparação das versões, se o repositório a tiver |
| Atividade | quando começou a última execução e quantas houve em 7 dias |
| Quem o viu | o ciclo de vida de cada sentinela: saudável, degradada, em pausa, com erro ou desligada |

O estado é **mau** (um fluxo vermelho, ou um alerta de nível crítico ou erro), **aviso** (um alerta de aviso ou uma execução encravada), **bom** ou **não visto** (nada com que julgar). Um repositório que nenhuma sentinela viu, ou que uma sentinela não conseguiu ler, nunca aparece como bom: diz «não visto por completo por» e enumera quem. O risco é o número pelo qual a classificação se ordena: cada fluxo vermelho (30), execução encravada (10), alerta crítico (25), de erro (10), de aviso (3) e informativo (1) soma pontos, iguais para todos os repositórios.

## Onde vê-la

- O separador **Equipa**: a classificação (primeiro os repositórios que precisam de uma pessoa), os totais, os números por ecossistema e por sentinela, e três filtros: ecossistema, gravidade mínima e um bocado do nome. Clique num repositório para ver o detalhe.
- Ligações diretas para ecrãs de parede: `?view=team&chrome=0`, `?view=repos&chrome=0` e `?view=repo&repo=owner/name&chrome=0`.
- A API: `GET /api/team/health?ecosystem=&severity=&q=&label=` e `GET /api/repos/<owner>/<repo>/health`. Ambas exigem permissão para ver a conta; as respostas levam `schema: 1`. Um repositório desconhecido responde 404 com `code: repo_unknown`.
- A edição Lite mantém a sua vista simples das execuções e não tem nem o separador nem as rotas.
