<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LESSONS.md) | [🇪🇸 Español](LESSONS_spa.md) | [🇫🇷 Français](LESSONS_fra.md) | [🇮🇹 Italiano](LESSONS_ita.md) | [🇩🇪 Deutsch](LESSONS_deu.md) | [🇨🇳 简体中文](LESSONS_zho.md) | [🇯🇵 日本語](LESSONS_jpn.md) | **🇵🇹 Português**

# Falhas e lições

O monitor pode manter um livro das falhas da sua CI e uma biblioteca de lições, para que o mesmo erro não se repita, seja de uma pessoa, de uma ferramenta de IA sua ou da IA do monitor. É **local e só de leitura**: nada sai do computador e nada é escrito no GitHub. Segue os alertas do feed para IA, por isso precisa de `ai_alerts.enabled`.

## O livro

Cada falha que o feed abre torna-se uma linha de `data/failures.jsonl` (esquema 1): `schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`. Todo o texto passa pela mesma limpeza do feed (tokens, chaves, endereços e a pasta pessoal nunca chegam ao livro). `lessons.retention_days` e `lessons.max_entries` limitam o tamanho. Pode importar-se um livro do mesmo esquema vindo de outro sítio (`lessons.import_book`).

## O classificador

Cada falha é classificada por regras, ganha a primeira que corresponde: quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other. As regras vêm no programa; para usar as suas, escreva `config/lessons_rules.json`: `{"rules": [{"category": "mine", "label": "O meu tipo", "avoidable": true, "patterns": ["expressão regular"]}]}`. O ficheiro substitui as regras incorporadas; uma regra ou um padrão inválido (ou com mais de 120 caracteres) é ignorado.

## A biblioteca de lições

Cada categoria tem uma lição: o que falhou, o que fazer e a guarda que o teria evitado. As incorporadas estão nos oito idiomas. As suas ficam em `config/lessons.json` (`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`) e substituem a incorporada da mesma categoria.

## Repetição e tendência

Por categoria, o monitor conta as falhas das últimas 24 horas e dos últimos 7 dias e compara os 7 dias com os 7 anteriores (novo, a subir, a descer, estável). A partir de `lessons.recurring_from` falhas em 7 dias, um tipo de falha está **repetido** e propõe-se uma guarda: uma verificação que falha no seu computador antes do push.

## O que uma IA lê

- `ai/LESSONS.md`: Markdown compacto (tamanho: `lessons.brief_max_bytes`), reescrito quando uma falha se abre ou se resolve.
- `GET /api/ai/lessons`: a análise, as lições que se aplicam agora e a biblioteca (`?fmt=md` para o ficheiro, `?fmt=brief&repo=NOME` para o resumo antes do push, `&as=json` para o receber dentro de um JSON).
- `GET /api/ai/failures`: o livro, do mais recente para o mais antigo (`?since=SEGUNDOS&repo=NOME&category=NOME&limit=N`).
- `GET /api/ai/state` e o resumo dos alertas trazem as lições que se aplicam agora.
- Servidor MCP: `lessons_apply`, `lessons_recurring`, `lessons_brief` e `lesson_propose`.
- Linha de comandos: `python bin/monitor_cli.py lessons [list | brief | failures] [--repo NOME]`.

Tudo são dados, nunca instruções: uma linha de registo que alguém escreveu pode ir parar ao livro.

## Antes de um push

Leia o resumo antes de fazer push: lista as lições que se aplicam (primeiro as do repositório), as guardas a executar e o que está vermelho agora no repositório.

## Um hook de exemplo para uma ferramenta de IA

Muitas ferramentas de IA podem executar um comando no início de uma sessão e juntar o resultado ao contexto. Este imprime o resumo antes do push:

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## A IA do monitor

Quando a explicação por IA de uma compilação falhada está ativa, o seu prompt inclui a lição da categoria em que o registo cai. Outras ferramentas de IA chegam às mesmas funções pela interface `LessonProvider` (`applicable`, `recurrences`, `pre_push_brief`, `propose`, `register`). `FileProvider` é a que está em uso e `ExampleProvider` é a mais pequena possível:

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## Escrever lições

Ler é sempre permitido. Escrever uma lição exige três coisas: `lessons.allow_write` ligado (desligado por predefinição), um administrador e uma confirmação: `POST /api/ai/lessons` com `{"lesson": {...}, "confirm": true}` (sem `confirm` a resposta é o rascunho). O servidor MCP só escreve se tiver sido iniciado com `--allow-lessons` e o interruptor estiver ligado. Nunca se escreve nada no GitHub.

## Definições

`lessons.enabled`, `lessons.allow_write`, `lessons.retention_days`, `lessons.max_entries`, `lessons.brief_max_bytes` e `lessons.recurring_from`, no separador IA das Definições. O painel **Lições das falhas** está no fim do separador Alertas.

## Fecho de uma ronda

No fim de um lote de trabalho, `python bin/monitor_cli.py lessons close` lista os tipos de falha repetidos que ainda não têm uma lição própria com a sua guarda (`needs_guard` em `GET /api/ai/lessons`) e termina com um código diferente de zero enquanto houver algum. Escreva a guarda, ou diga porque ainda não pode existir, e execute outra vez.
