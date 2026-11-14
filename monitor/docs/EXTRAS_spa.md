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

`github_app.share_reads`: el comando siguiente imprime, en este equipo, un token de instalación de su App de GitHub que dura una hora, para que el `gh` de sus herramientas y agentes lea con la cuota de la App y no con la suya (`GH_TOKEN`). El token va solo a la salida estándar, nunca a un archivo ni a un registro, y el comando necesita `--read-only`; dé a la App permisos de solo lectura al crearla. Sin `github_app.share_reads` se niega.

```
python bin/monitor_cli.py gh-token --read-only
```

## Todavía no está

El panel de higiene de workflows, el informe de cola, la vista de versión lista o bloqueada y el panel de cadena de suministro no forman parte de esta versión.
