<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](MODES.md) | [🇪🇸 Español](MODES_spa.md) | [🇫🇷 Français](MODES_fra.md) | [🇮🇹 Italiano](MODES_ita.md) | [🇩🇪 Deutsch](MODES_deu.md) | [🇨🇳 简体中文](MODES_zho.md) | [🇯🇵 日本語](MODES_jpn.md) | **🇵🇹 Português**

# Modos de trabalho: normal, rápido e turbo

Quando quer vigiar algo mais de perto durante um tempo (uma hora, por exemplo) pode passar o monitor para um modo mais rápido, mesmo que gaste mais depressa a quota da API. O seletor com o ícone do medidor está no cabeçalho; na consola use `--mode fast` ou `--mode turbo` com `--mode-minutes 60`.

| Modo | O que muda | Valores por defeito |
|---|---|---|
| **normal** | nada: a sua configuração | os seus |
| **fast** (rápido) | atualização, atualização a frio, runs por repositório, janela quente | 30 s, 300 s, 30 runs, 6 h |
| **turbo** | o mesmo, mais | 15 s, 90 s, 50 runs, 12 h |

As predefinições são o bloco `modes` de `actions_monitor.json` (`modes.fast`, `modes.turbo`, `modes.default_minutes`, `modes.start`); edite-as ao seu gosto. Uma predefinição nunca torna um valor mais lento ou mais pequeno do que o que definiu, e nada desce abaixo de 10 segundos, para se manter longe dos limites secundários do GitHub (depois de um, o monitor espera pelo menos um minuto e depois mais).

**Antes de começar**, a página mostra as chamadas por hora do modo no pior caso, o que a cache costuma poupar (uma leitura condicional que responde `304` não gasta quota primária) e quanto duraria a quota que resta. **Volta a normal sozinho** quando o tempo acaba (o cabeçalho faz a contagem decrescente) e quando a quota restante desce abaixo de `min_rate_remaining`; um aviso diz porquê e a consola imprime-o. **Sem sessão o GitHub só dá 60 chamadas por hora**, por isso rápido e turbo ficam desativados com o motivo (execute `gh auth login`).

Mudar de modo é uma definição local: precisa do token de uso único da página como qualquer outra alteração, vive só em memória (um reinício volta a normal, a menos que escreva `modes.start`) e não envia nada para lado nenhum. Funciona nas duas edições; a sentinela da edição completa mantém os seus intervalos e o seu orçamento de chamadas (`sentinel.budget_per_hour`), descritos em [A sentinela](SENTINEL_por.md). O banner da consola e as linhas de estado indicam o modo ativo.
