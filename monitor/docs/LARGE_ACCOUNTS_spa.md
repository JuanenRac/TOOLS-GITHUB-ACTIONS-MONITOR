<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | **🇪🇸 Español** | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Cuentas grandes: cientos de repositorios

Una cuenta con cientos de repositorios, muchos forks o varias organizaciones gasta deprisa la cuota de la API. Esto es una receta, en el orden que más ahorra; cada ajuste está en la pestaña Ajustes.

1. **Empieza por un perfil.** Ajustes > Básico > Perfil: *Organización de código abierto* fija casi todo lo siguiente en un clic (después puedes cambiar cada ajuste).
2. **Vigila lo que se mantiene.** `discovery.fork_policy` = `auto` conserva solo los forks con CI propio (el tipo de cuenta decide la ventana, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` reparte las preguntas en varios listados. `discovery.skip_archived` viene activado. `exclude` y `ecosystems` acotan la lista por nombre.
3. **Pregunta menos.** `cold_runs_per_repo` y `cold_refresh_seconds` fijan lo que cuestan los repositorios tranquilos; `runs_per_repo` y `refresh_seconds` hacen lo mismo con los calientes. `network.etag` hace gratis las lecturas repetidas cuando nada cambió, y el modo Bajo (`modes.auto_low`) lo frena todo solo cuando la cuota escasea.
4. **Dale un presupuesto al Centinela.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` y `sentinel.hygiene_seconds` (la higiene es una petición por repositorio cada seis horas por defecto; alárgala) acotan lo que gastan las comprobaciones de A3-A6.
5. **Añade una segunda cuota.** `github_app.share_reads` deja que una GitHub App conteste parte de las lecturas con su propia cuota.
6. **No te ahogues en ruido.** La comprobación de higiene (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), las de archivos de las releases (`sentinel.surface.checks.release_assets.allow_empty`) y `sentinel.bots_apart` evitan que se acumulen las comprobaciones que no se aplican a tus repositorios.

La pestaña Cuota muestra lo que le queda a cada fuente y cuánto gasta el propio monitor.

El seguimiento de los originales de los forks (`upstream.enabled`) dice en su panel cuánto dura una vuelta a todos los forks al ritmo de `upstream.requests_per_hour` y `upstream.forks_per_request`; cuando es más que `upstream.refresh_hours` el seguimiento no descansa nunca (727 forks a 8 por petición y 6 peticiones por hora duran 15,2 horas). Las peticiones de la última hora se conservan al reiniciar, así que un reinicio no devuelve el cupo.
