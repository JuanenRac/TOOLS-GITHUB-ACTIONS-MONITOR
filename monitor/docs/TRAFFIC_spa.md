<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](TRAFFIC.md) | **🇪🇸 Español** | [🇫🇷 Français](TRAFFIC_fra.md) | [🇮🇹 Italiano](TRAFFIC_ita.md) | [🇩🇪 Deutsch](TRAFFIC_deu.md) | [🇨🇳 简体中文](TRAFFIC_zho.md) | [🇯🇵 日本語](TRAFFIC_jpn.md) | [🇵🇹 Português](TRAFFIC_por.md)

# Descargas y tráfico

Un historial, guardado en este equipo, de cuántas veces se descargan los ficheros de tus releases y de las visitas y clonados de los repositorios que elijas. GitHub solo conserva 14 días de visitas y clonados y no da historial de descargas, así que lo que no se guarda se pierde. Edición Complete; apagado de fábrica.

## Activación

Enciende `traffic.enabled` (Ajustes > Descargas y tráfico) y escribe los repositorios en `traffic.repos`, uno por línea: un nombre (de la cuenta que vigilas) o dueño/nombre, como máximo 50. Con la lista vacía no se lee nada. El panel aparece en la pestaña Repositorios.

## Qué se lee y cuánto cuesta

Solo peticiones GET, después de un ciclo: cada repositorio elegido como máximo una vez al día (UTC), `traffic.repos_per_cycle` por ciclo. Un repositorio cuesta de una a cinco peticiones de tu cuota de GitHub (releases, hasta 300; visitas; clonados). Si la cuota se acaba, para y lo intenta más tarde. `traffic.views_clones` apaga las visitas y clonados. Las instalaciones sin red no leen nada.

## Permisos

Las visitas y los clonados solo se dan a un token con permiso de escritura (push) en el repositorio. Sin él, el panel lo dice para ese repositorio; no es un error y las descargas se siguen guardando.

## Qué significan las cifras

Las descargas son anónimas, incluyen robots y espejos, y no cuentan los archivos "Source code" que GitHub añade a una release. Las descargas nuevas comparan una lectura con la anterior, solo para los ficheros que siguen ahí. Un día no leído es un hueco, nunca un cero.

## Exportación y privacidad

El panel exporta dos ficheros CSV: una línea por repositorio y día, y una por fichero de release y día en que cambió su cuenta. `monitor_cli.py traffic export` imprime el primero. Los días más antiguos que `traffic.keep_days` se borran. El historial queda en la carpeta de datos de este equipo; no se envía a ningún sitio.
