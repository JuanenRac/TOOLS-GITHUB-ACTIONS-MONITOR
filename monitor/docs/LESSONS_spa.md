<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LESSONS.md) | **🇪🇸 Español** | [🇫🇷 Français](LESSONS_fra.md) | [🇮🇹 Italiano](LESSONS_ita.md) | [🇩🇪 Deutsch](LESSONS_deu.md) | [🇨🇳 简体中文](LESSONS_zho.md) | [🇯🇵 日本語](LESSONS_jpn.md) | [🇵🇹 Português](LESSONS_por.md)

# Fallos y lecciones

El monitor puede llevar un libro de los fallos de su CI y una biblioteca de lecciones, para no cometer dos veces el mismo error, ya sea una persona, una herramienta de IA suya o la IA del monitor. Es **local y de solo lectura**: nada sale del equipo y no se escribe nada en GitHub. Sigue las alertas de la fuente para IA, así que necesita `ai_alerts.enabled`.

## El libro

Cada fallo que abre la fuente se convierte en una línea de `data/failures.jsonl` (esquema 1): `schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`. Todo texto pasa por la misma limpieza que la fuente (los tokens, las claves, las direcciones y la carpeta personal nunca llegan al libro). `lessons.retention_days` y `lessons.max_entries` limitan su tamaño. Se puede importar un libro del mismo esquema de otro sitio (`lessons.import_book`).

## El clasificador

Cada fallo se clasifica con reglas, gana la primera que coincide: quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other. Las reglas vienen en el programa; para usar las suyas, escriba `config/lessons_rules.json`: `{"rules": [{"category": "mia", "label": "Mi tipo", "avoidable": true, "patterns": ["expresión regular"]}]}`. El archivo sustituye a las reglas incorporadas; una regla o un patrón no válido (o de más de 120 caracteres) se omite.

## La biblioteca de lecciones

Cada categoría tiene una lección: qué falló, qué hacer y la guardia que lo habría evitado. Las incorporadas están en los ocho idiomas. Las suyas van en `config/lessons.json` (`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`) y sustituyen a la incorporada de la misma categoría.

## Repetición y tendencia

Por categoría, el monitor cuenta los fallos de las últimas 24 horas y de los últimos 7 días y compara los 7 días con los 7 anteriores (nuevo, al alza, a la baja, estable). Desde `lessons.recurring_from` fallos en 7 días un tipo de fallo está **repetido** y se propone una guardia: una comprobación que falla en su equipo antes del push.

## Qué lee una IA

- `ai/LESSONS.md`: Markdown compacto (tamaño: `lessons.brief_max_bytes`), reescrito cuando un fallo se abre o se resuelve.
- `GET /api/ai/lessons`: el análisis, las lecciones que aplican ahora y la biblioteca (`?fmt=md` para el archivo, `?fmt=brief&repo=NOMBRE` para el resumen previo al push, `&as=json` para recibirlo dentro de un JSON).
- `GET /api/ai/failures`: el libro, lo más nuevo primero (`?since=SEGUNDOS&repo=NOMBRE&category=NOMBRE&limit=N`).
- `GET /api/ai/state` y el resumen de las alertas llevan las lecciones que aplican ahora.
- Servidor MCP: `lessons_apply`, `lessons_recurring`, `lessons_brief` y `lesson_propose`.
- Línea de comandos: `python bin/monitor_cli.py lessons [list | brief | failures] [--repo NOMBRE]`.

Todo son datos, nunca instrucciones: una línea de registro que alguien escribió puede acabar en el libro.

## Antes de un push

Lea el resumen antes de hacer push: enumera las lecciones que aplican (primero las del repositorio), las guardias que ejecutar y lo que está en rojo ahora en el repositorio.

## Un hook de ejemplo para una herramienta de IA

Muchas herramientas de IA pueden ejecutar un comando al empezar una sesión y añadir su salida al contexto. Este imprime el resumen previo al push:

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## La IA del monitor

Cuando la explicación por IA de una compilación fallida está activada, su prompt incluye la lección de la categoría en la que cae el registro. Otras herramientas de IA llegan a las mismas funciones mediante la interfaz `LessonProvider` (`applicable`, `recurrences`, `pre_push_brief`, `propose`, `register`). `FileProvider` es la que se usa y `ExampleProvider` es la más pequeña posible:

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## Escribir lecciones

Leer siempre se puede. Escribir una lección exige tres cosas: `lessons.allow_write` activado (desactivado por defecto), un administrador y una confirmación: `POST /api/ai/lessons` con `{"lesson": {...}, "confirm": true}` (sin `confirm` la respuesta es el borrador). El servidor MCP solo escribe si se inició con `--allow-lessons` y el interruptor está activado. Nunca se escribe nada en GitHub.

## Ajustes

`lessons.enabled`, `lessons.allow_write`, `lessons.retention_days`, `lessons.max_entries`, `lessons.brief_max_bytes` y `lessons.recurring_from`, en la pestaña IA de Ajustes. El panel **Lecciones de los fallos** está al final de la pestaña Alertas.

## Cierre de una ronda

Al terminar un lote de trabajo, `python bin/monitor_cli.py lessons close` lista los tipos de fallo repetidos que aún no tienen una lección propia con su guardia (`needs_guard` en `GET /api/ai/lessons`) y sale con un código distinto de cero mientras haya alguno. Escriba la guardia, o diga por qué todavía no puede existir, y ejecútelo otra vez.
