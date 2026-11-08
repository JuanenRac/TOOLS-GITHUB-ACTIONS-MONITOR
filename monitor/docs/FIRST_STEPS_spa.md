<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | **🇪🇸 Español** | [🇫🇷 Français](FIRST_STEPS_fra.md) | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# Tus primeros cinco minutos

**1. Instala lo que necesita.** Python 3.11 o superior y el GitHub CLI (`gh`). Luego inicia sesión una vez: `gh auth login`. El monitor nunca guarda un token: se lo pide a `gh`.

**2. Comprueba todo con un comando.** `python actions_monitor.py --doctor` te dice, para cada problema, el comando exacto que lo arregla. ¿Prefieres mirar antes? `python actions_monitor.py --demo` abre la página con datos inventados: sin `gh`, sin sesión, sin red.

**3. Arráncalo.** Doble clic en `MONITOR_LITE_GITHUB_ACTIONS` para la edición sencilla (puerto 8766) o en `MONITOR_GITHUB_ACTIONS` para la completa con centinela (puerto 8765). La ventana de consola dice qué edición es, en su título y en la primera línea.

**4. Sigue los tres pasos de la bienvenida.** La primera vez, la página explica qué hace, muestra lo que encontró en tu cuenta y señala los ajustes básicos. Por defecto no se oculta nada: los repositorios que ningún grupo reclama aparecen como *Sin clasificar*.

**5. Sabe dónde está la ayuda.** El botón redondo **?** (o la tecla `?`) abre la Ayuda; el botón **i** abre Acerca de, con tu versión, tus archivos y un botón que copia la información para soporte (no lleva ningún secreto). En la consola: `--help-topics`, `--help-search PALABRAS`, `--about`.

**Conviene saber.** Si usas un plan con repositorios privados, elígelo en Ajustes > Básico para ver tus cuotas ([Cuotas y planes](QUOTAS_spa.md)). El centinela se explica en [El centinela](SENTINEL_spa.md). La herramienta solo lee GitHub; escribe únicamente cuando tú confirmas.
