<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | **🇪🇸 Español** | [🇫🇷 Français](FIRST_STEPS_fra.md) | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# Tus primeros cinco minutos

**1. Instala lo que necesita.** Python 3.11 o superior y el GitHub CLI (`gh`). Luego inicia sesión una vez: `gh auth login`. El monitor nunca guarda un token: se lo pide a `gh` (salvo que actives el token opcional del monitor en Ajustes > Avanzado).

**2. Comprueba todo con un comando.** `python bin/actions_monitor.py --doctor` te dice, para cada problema, el comando exacto que lo arregla. ¿Prefieres mirar antes? `python bin/actions_monitor.py --demo` abre la página con datos inventados: sin `gh`, sin sesión, sin red.

**3. Arráncalo.** Doble clic en `MONITOR_LITE_GITHUB_ACTIONS` para la edición sencilla (puerto 8766) o en `MONITOR_GITHUB_ACTIONS` para la completa con centinela (puerto 8765). La ventana de consola dice qué edición es, en su título y en la primera línea.

**4. Sigue los tres pasos de la bienvenida.** La primera vez, la página explica qué hace, muestra lo que encontró en tu cuenta y señala los ajustes básicos. Por defecto no se oculta nada: los repositorios que ningún grupo reclama aparecen como *Sin clasificar*.

**5. Sabe dónde está la ayuda.** El botón redondo **?** (o la tecla `?`) abre la Ayuda; el botón **i** abre Acerca de, con tu versión, tus archivos y un botón que copia la información para soporte (no lleva ningún secreto). En la consola: `--help-topics`, `--help-search PALABRAS`, `--about`.

**6. Guardar o imprimir un informe.** Los dos botones de la barra superior guardan el informe de la pestaña abierta (TXT, PDF y, si quieres, JSON, cada uno por la ventana **Guardar como** de tu navegador) o lo imprimen como una página limpia ([Salidas para otras herramientas](OUTPUTS.md)).

**Conviene saber.** Si usas un plan con repositorios privados, elígelo en Ajustes > Básico para ver tus cuotas ([Cuotas y planes](QUOTAS_spa.md)). El centinela se explica en [El centinela](SENTINEL_spa.md). La herramienta solo lee GitHub; escribe únicamente cuando tú confirmas.

## Leer con comodidad

- **Densidad** (`display.density`, o `?density=dense` para una ventana): `dense` reduce los espacios y la letra de todas las pestañas.
- **Menos movimiento** (`display.reduce_motion`): `auto` sigue el ajuste de tu sistema, `on` detiene toda animación y transición. El estado de un workflow se escribe siempre con palabras y se dibuja también con una forma, nunca solo con color.
- **Colores para daltonismo** (`display.palette`, o `?palette=colorblind`): azul, bermellón, amarillo y un azul más claro, un juego para el modo oscuro y otro para el claro. La puerta de contraste (`python tools/check_contrast.py`) comprueba todos los temas y simula los tres tipos de daltonismo.
- **Sin saltos mientras lees** (`display.live_throttle_s`): mientras el puntero o el foco están dentro de la pestaña que lees, la actualización periódica espera; una actualización que pides tú se aplica al instante.
- **Novedades** (`display.whats_new`): tras una actualización un aviso ofrece las entradas del historial de cambios de las versiones que te saltaste; ábrelo de nuevo desde la paleta. `GET /api/whats-new?since=2.1.5` responde con las entradas (solo lectura).
- **Glosario y límites**: ábrelo desde la paleta. `GET /api/glossary` responde con las cifras escritas con tus parámetros reales, los ataques que buscan las reglas, los límites del análisis y unos sitios donde aprender más. Con `report_export.limits` encendido, los informes guardados e impresos terminan con los límites.
- **El filtro de la cabecera** cubre las pestañas Ahora, Alertas, Gráficos, las del Centinela (Centinela, CI, Colaboración, Seguridad, Entrega, Suministro), Repositorios e Historial; las demás (Tendencia del Centinela, Equipo, Flota, Informes, Lecciones, Actualizaciones y Ajustes) son siempre globales. Una nota bajo el filtro lo dice.
