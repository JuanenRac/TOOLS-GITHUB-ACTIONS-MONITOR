<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | **🇪🇸 Español** | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Cuentas grandes: cientos de repositorios

Una cuenta con cientos de repositorios, muchos forks o varias organizaciones gasta deprisa la cuota de la API. Esto es una receta, en el orden que más ahorra; cada ajuste está en la pestaña Ajustes.

1. **Empieza por un perfil.** Ajustes > Básico > Perfil: *Organización de código abierto* fija casi todo lo siguiente en un clic (después puedes cambiar cada ajuste).
2. **Vigila lo que se mantiene.** `discovery.fork_policy` = `auto` conserva solo los forks con CI propio (el tipo de cuenta decide la ventana, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` reparte las preguntas en varios listados. `discovery.skip_archived` viene activado. `exclude` y `ecosystems` acotan la lista por nombre. Un listado de la cuenta que llega vacío, o con menos del `discovery.min_keep_pct` por ciento del último bueno, no se cree: se conserva el último listado bueno, se vuelve a leer en cinco minutos y el informe para las herramientas de IA tiene la señal repos.listing. `discovery.hide` acepta también `public` (y `private`, `fork`, `empty`); la pestaña Básico cuenta lo que dejó fuera cada regla, así nada dejado fuera por un filtro se lee como limpio.
3. **Pregunta menos.** `cold_runs_per_repo` y `cold_refresh_seconds` fijan lo que cuestan los repositorios tranquilos; `runs_per_repo` y `refresh_seconds` hacen lo mismo con los calientes. `network.etag` hace gratis las lecturas repetidas cuando nada cambió, y el modo Bajo (`modes.auto_low`) lo frena todo solo cuando la cuota escasea.
4. **Dale un presupuesto al Centinela.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` y `sentinel.hygiene_seconds` (la higiene es una petición por repositorio cada seis horas por defecto; alárgala) acotan lo que gastan las comprobaciones de A3-A6.
5. **Añade una segunda cuota.** `github_app.share_reads` deja que una GitHub App conteste parte de las lecturas con su propia cuota.
6. **No te ahogues en ruido.** La comprobación de higiene (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), las de archivos de las releases (`sentinel.surface.checks.release_assets.allow_empty`) y `sentinel.bots_apart` evitan que se acumulen las comprobaciones que no se aplican a tus repositorios.

La pestaña Cuota muestra lo que le queda a cada fuente y cuánto gasta el propio monitor.

El seguimiento de los originales de los forks (`upstream.enabled`) dice en su panel cuánto dura una vuelta a todos los forks al ritmo de `upstream.requests_per_hour` y `upstream.forks_per_request`; cuando es más que `upstream.refresh_hours` el seguimiento no descansa nunca (727 forks a 8 por petición y 6 peticiones por hora duran 15,2 horas). Las peticiones de la última hora se conservan al reiniciar, así que un reinicio no devuelve el cupo.

Las llamadas de un tick del Centinela (`sentinel.max_calls_per_tick`) son una sola cuenta para todas sus etapas, y un repositorio cuyas lecturas fallan tres veces seguidas se deja en paz 30 segundos, duplicando hasta 10 minutos, mientras se leen los demás.

La pestaña Flota tiene además una caja opcional por [rol de workflow y grupo, con una pantalla para cada grupo](FLEET_APIS_spa.md).

## Cola de lecturas, límites y una lectura para todos

- **Contrapresión** (`backpressure.enabled`, apagada por defecto): las lecturas de un ciclo pasan por una cola acotada (primero los repositorios en rojo, luego los calientes, los nunca leídos y los leídos hace más tiempo). `backpressure.max_reads_per_cycle` fija un número (0 = ninguno); cuando un ciclo dura más del `backpressure.shed_percent` por ciento de la pausa entre ciclos las lecturas permitidas se reducen a la mitad (nunca bajo `backpressure.min_reads`) y vuelven a crecer una décima tras cada ciclo rápido. Lo que espera conserva su última imagen y va primero en el siguiente ciclo. `/metrics` muestra `ghamon_read_queue_*`.
- **Límites y el doctor**: `monitor_cli.py doctor` tiene una comprobación `capacity` que compara la configuración con sus techos (llamadas por hora frente a la cuota y a `sampling.api_budget_per_hour`, la memoria de las ejecuciones guardadas frente a `limits.memory_mb`, los repositorios frente a `discover_limit`) y avisa desde `limits.warn_percent`. `/metrics` muestra los que están vivos como `ghamon_limit_used_percent{limit=...}` (eventos guardados, flujos, cola de lecturas, series de los histogramas).
- **Una lectura para todos** (`refresh.share_by_workflow`, apagada por defecto): cuando el ciclo, una página, una pantalla de pared o un cliente de la API piden los jobs de la misma ejecución a la vez, el primero lee de GitHub y los demás toman su respuesta, válida `refresh.share_seconds` segundos. `/metrics` cuenta las lecturas ahorradas (`ghamon_shared_reads_spared_total`).
