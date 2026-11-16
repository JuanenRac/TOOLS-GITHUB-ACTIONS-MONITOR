<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTRAS.md) | **🇪🇸 Español** | [🇫🇷 Français](EXTRAS_fra.md) | [🇮🇹 Italiano](EXTRAS_ita.md) | [🇩🇪 Deutsch](EXTRAS_deu.md) | [🇨🇳 简体中文](EXTRAS_zho.md) | [🇯🇵 日本語](EXTRAS_jpn.md) | [🇵🇹 Português](EXTRAS_por.md)

# Extras opcionales

Ambos están **desactivados por defecto** y se activan en Ajustes.

## El registro del paso fallido

`logs.failed_step.enabled`: una alerta de una ejecución fallida recibe un botón **Paso fallido**. Una pulsación lee de GitHub los trabajos y el registro fallido de esa ejecución (dos llamadas de su cuota), muestra el paso que falló y sus últimas líneas relevantes (`logs.failed_step.lines`, `logs.failed_step.max_bytes`) y guarda la respuesta en memoria, así que pulsar de nuevo no cuesta nada. El texto se limpia de tokens, claves, direcciones y carpeta personal. Solo se pueden consultar repositorios que el monitor vigila, con `GET /api/run-log?repo=&run=`; en el modo equipo, solo un administrador.

## Un token de solo lectura de la App de GitHub para sus herramientas

`github_app.share_reads`: el comando siguiente imprime, en este equipo, un token de instalación de su App de GitHub que dura una hora, para que el `gh` de sus herramientas y agentes lea con la cuota de la App y no con la suya (`GH_TOKEN`). El token va solo a la salida estándar, nunca a un archivo ni a un registro, y el comando necesita `--read-only`; dé a la App permisos de solo lectura al crearla. Sin `github_app.share_reads` se niega. El token se pide aparte del que guarda el monitor, solo con permisos de lectura; si la respuesta trae algún permiso de escritura, el comando se niega a imprimirlo.

```
python bin/monitor_cli.py gh-token --read-only
```

## Cuatro informes opcionales

Los cuatro están desactivados por defecto. Aparecen en la pestaña **Informes** (entrada del menú de la izquierda, dirección `#reports`) y en `GET /api/reports`. Los que leen GitHub gastan como mucho `reports.max_calls_per_cycle` llamadas en un ciclo, leen pocos repositorios cada vez y guardan lo leído en memoria durante un día.

- `reports.workflow_hygiene.enabled`: lee los archivos de workflow de los repositorios y enumera lo mal escrito - acciones no fijadas a un commit, permisos sin limitar, un trabajo sin `timeout-minutes`, sin grupo `concurrency`, riesgos de `pull_request_target` e inyección, secretos en claro (las reglas del linter del panel A13, que lee clones locales, más las dos nuevas).
- `reports.queue.enabled`: lee los trabajos de unas pocas ejecuciones terminadas que esperaron y dice cuánto esperó un trabajo antes de empezar para cada tipo de runner (Linux, Windows, macOS, grandes, autoalojados).
- `reports.release_view.enabled`: sin ninguna llamada; con lo que el centinela sabe dice qué repositorios están LISTOS para una versión (entradas en el changelog o una compilación verde que nadie publicó, nada en rojo, ninguna firma esperando) y cuáles BLOQUEADOS, y por qué.
- `reports.supply_chain.enabled`: lee la última versión de los repositorios y dice, por los nombres de sus archivos, si lleva una lista de materiales de software (SBOM), sumas de control y una firma o atestación. Los archivos nunca se descargan.
