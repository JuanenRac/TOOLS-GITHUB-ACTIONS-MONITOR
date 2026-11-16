<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](HEALTH.md) | **🇪🇸 Español** | [🇫🇷 Français](HEALTH_fra.md) | [🇮🇹 Italiano](HEALTH_ita.md) | [🇩🇪 Deutsch](HEALTH_deu.md) | [🇨🇳 简体中文](HEALTH_zho.md) | [🇯🇵 日本語](HEALTH_jpn.md) | [🇵🇹 Português](HEALTH_por.md)

# La salud de un repositorio y del equipo

Solo Complete. Dos vistas de solo lectura, hechas con lo que el monitor ya tiene (ejecuciones, flujos rojos y atascados, las alertas abiertas de cada centinela y la preparación de las versiones). Nunca llaman a GitHub.

## De qué se compone la salud de un repositorio

| Parte | Qué dice |
|---|---|
| CI | éxitos y fallos de las últimas 24 horas, los flujos que están en rojo ahora, las ejecuciones atascadas |
| Alertas | todas las alertas abiertas de los centinelas de CI, Colaboración y Seguridad, por centinela y por nivel |
| Versión | la fila de la preparación de versiones, si el repositorio la tiene |
| Actividad | cuándo empezó la última ejecución y cuántas hubo en 7 días |
| Quién lo miró | el ciclo de vida de cada centinela: sano, degradado, en pausa, con error o apagado |

El estado es **malo** (un flujo en rojo, o una alerta de nivel crítico o error), **aviso** (una alerta de aviso o una ejecución atascada), **bien** o **sin ver** (no hay nada con qué juzgar). Un repositorio que ningún centinela miró, o que un centinela no pudo leer, nunca se muestra como bien: dice «no visto del todo por» y enumera quién. El riesgo es el número por el que se ordena la clasificación: cada flujo rojo (30), ejecución atascada (10), alerta crítica (25), de error (10), de aviso (3) e informativa (1) suma puntos, igual para todos los repositorios. Cuando todos los centinelas están en error, en pausa o degradados (o todos apagados y no ha corrido nada en una semana), un repositorio tranquilo se muestra como sin ver, nunca como OK, y su fila en el ranking lleva un asterisco y nombra los centinelas que no pudieron leerlo (`not_fully_seen`; los totales también los cuentan).

## Dónde verla

- La pestaña **Equipo**: la clasificación (primero los repositorios que necesitan a una persona), los totales, las cifras por ecosistema y por centinela, y tres filtros: ecosistema, gravedad mínima y un trozo del nombre. Pulsa un repositorio para ver su detalle.
- Enlaces directos para pantallas de pared: `?view=team&chrome=0`, `?view=repos&chrome=0` y `?view=repo&repo=owner/name&chrome=0`.
- La API: `GET /api/team/health?ecosystem=&severity=&q=&label=` y `GET /api/repos/<owner>/<repo>/health`. Las dos piden permiso para ver la cuenta; las respuestas llevan `schema: 1`. Un repositorio desconocido responde 404 con `code: repo_unknown`.
- La edición Lite conserva su vista sencilla de ejecuciones y no tiene ni la pestaña ni las rutas.
