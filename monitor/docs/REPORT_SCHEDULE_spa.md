<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](REPORT_SCHEDULE.md) | **🇪🇸 Español** | [🇫🇷 Français](REPORT_SCHEDULE_fra.md) | [🇮🇹 Italiano](REPORT_SCHEDULE_ita.md) | [🇩🇪 Deutsch](REPORT_SCHEDULE_deu.md) | [🇨🇳 简体中文](REPORT_SCHEDULE_zho.md) | [🇯🇵 日本語](REPORT_SCHEDULE_jpn.md) | [🇵🇹 Português](REPORT_SCHEDULE_por.md)

# Informes programados

Solo Complete, apagado por defecto. El monitor puede escribir un informe de la cuenta según un horario o cuando lo pides: la puntuación, qué ha cambiado desde el último informe, los repositorios que necesitan a una persona y las alertas abiertas, como página HTML y como Markdown. Se hace con lo que el monitor ya tiene, no pide nada a GitHub y no envía nada a ningún sitio: los ficheros se quedan en la carpeta `data/reports/`.

## Cómo encenderlo

Ajustes, pestaña Centinela, bloque **Informes programados**:

| Ajuste | Por defecto | Qué hace |
|---|---|---|
| `report_schedule.enabled` | apagado | escribe un informe según el horario |
| `report_schedule.cron` | `0 8 * * 1` | cinco campos (minuto, hora, día del mes, mes, día de la semana) en la hora local de este equipo; números, listas, rangos y pasos, sin nombres; `0 8 * * 1` es cada lunes a las 8:00 |
| `report_schedule.formats` | ambos | `html`, `markdown` o `both` |
| `report_schedule.keep` | 12 | cuántas tandas se conservan; las más antiguas se quitan |
| `report_schedule.top` | 10 | cuántos repositorios y alertas muestra cada lista, los peores primero |

El primer informe espera al primer minuto programado después de encenderlo. Se escribe un informe por minuto programado, aunque el monitor haya estado apagado días (entonces escribe uno, no un montón). Un informe que falla queda anotado en la salud del monitor y el siguiente minuto programado lo intenta otra vez. Una programación que nombra un día del mes sigue debiéndose tras una parada de hasta un mes (si nombra un mes, hasta un año), y la hora que ocurre dos veces cuando el reloj retrocede en otoño no se informa dos veces. Un informe es todos sus formatos o nada: si el segundo formato no se puede escribir, el primer archivo se elimina.

## Qué lleva un informe

La puntuación de la cuenta (con su letra y tendencia; mientras calibra o tiene pocos datos lo dice y no muestra número), qué ha cambiado desde el último informe (la diferencia en puntos, las alertas nuevas y las que han desaparecido), los repositorios de la vista de salud que necesitan a una persona primero y las alertas abiertas, las peores primero. Una alerta silenciada no está abierta. Todo texto que viene de los datos se escapa: la página no tiene scripts ni direcciones externas.

## PDF

No hay un PDF propio: abre la página HTML e imprímela a PDF desde el navegador. La página tiene un estilo de impresión para A4.

## Dónde verlos y pedirlos

- La pestaña **Equipo** tiene una sección Informes: la lista, un enlace a cada fichero y el botón **Escribir un informe ahora** (un administrador, desde este equipo).
- `GET /api/report-files` los lista, `GET /api/report-files/file?name=...` abre uno (solo un fichero que el servicio escribió para esta cuenta) y `POST /api/report-files/run` escribe uno ahora.
- En el modo equipo, quien puede ver la cuenta puede leer sus informes; escribir uno ahora es para un administrador en este equipo. La edición Lite no tiene nada de esto.

## Comparación con el periodo anterior

Con `compare.include_in_report` activado (apagado por defecto, y solo mientras `compare.enabled` esté activo) el informe lleva además una sección breve que pone este periodo frente al anterior, una línea por cifra. Véase [COMPARE_spa.md](COMPARE_spa.md).
