<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](MODES.md) | **🇪🇸 Español** | [🇫🇷 Français](MODES_fra.md) | [🇮🇹 Italiano](MODES_ita.md) | [🇩🇪 Deutsch](MODES_deu.md) | [🇨🇳 简体中文](MODES_zho.md) | [🇯🇵 日本語](MODES_jpn.md) | [🇵🇹 Português](MODES_por.md)

# Modos de trabajo: normal, rápido y turbo

Cuando quieres vigilar algo más de cerca durante un rato (una hora, por ejemplo) puedes pasar el monitor a un modo más rápido aunque gaste antes la cuota de la API. El selector con el icono del medidor está en la cabecera; en la consola usa `--mode fast` o `--mode turbo` con `--mode-minutes 60`.

| Modo | Qué cambia | Valores por defecto |
|---|---|---|
| **normal** | nada: tu propia configuración | los tuyos |
| **fast** (rápido) | refresco, refresco en frío, runs por repositorio, ventana caliente | 30 s, 300 s, 30 runs, 6 h |
| **turbo** | lo mismo, más | 15 s, 90 s, 50 runs, 12 h |

Los presets son el bloque `modes` de `actions_monitor.json` (`modes.fast`, `modes.turbo`, `modes.default_minutes`, `modes.start`); edítalos a tu gusto. Un preset nunca vuelve un valor más lento o más pequeño que el que tú pusiste, y nada baja de 10 segundos, para no acercarse a los límites secundarios de GitHub (tras uno, el monitor espera al menos un minuto y luego más).

**Antes de empezar**, la página muestra las llamadas por hora del modo en el peor caso, lo que suele ahorrar la caché (una lectura condicional que responde `304` no gasta la cuota primaria) y cuánto duraría la cuota que queda. **Vuelve a normal solo** al acabar el tiempo (la cabecera lo cuenta atrás) y cuando la cuota restante baja de `min_rate_remaining`; un aviso dice por qué y la consola lo imprime. **Sin sesión GitHub solo da 60 llamadas por hora**, así que rápido y turbo quedan desactivados con el motivo (ejecuta `gh auth login`).

Cambiar el modo es un ajuste local: necesita el token de un solo uso de la página como cualquier otro cambio, vive solo en memoria (un reinicio vuelve a normal salvo que tú escribas `modes.start`) y no envía nada a ninguna parte. Funciona en las dos ediciones; el centinela de la edición completa mantiene sus propios intervalos y su propio presupuesto de llamadas (`sentinel.budget_per_hour`), explicado en [el centinela](SENTINEL_spa.md). El banner de la consola y las líneas de estado indican el modo activo.
