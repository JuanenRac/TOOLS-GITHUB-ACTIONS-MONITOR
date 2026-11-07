<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | **🇪🇸 Español** | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# La pestaña Ajustes

La pestaña Ajustes (el icono del engranaje en la cabecera o en la barra de pestañas) cambia desde la página los valores de `actions_monitor.json`, de modo que nadie tenga que editar el fichero a mano.
Está escrita en los ocho idiomas de la página y sigue el aspecto del resto.

## Qué se puede cambiar

Solo las claves de la lista de `settings_api.py` (el esquema). Cada una tiene un tipo y un rango, y la página indica si un cambio necesita **reiniciar** el monitor (el bucle lee
su configuración una sola vez) o se **aplica ahora**.

| Grupo | Claves |
|---|---|
| Este navegador | idioma de la página, tema (auto / claro / oscuro), vista densa de la pestaña Ahora. Se guardan en el navegador, no en el fichero. |
| General | `language` (idioma por defecto de las herramientas), `github_owner`, `mode` (`full` / `lite`), `ecosystems`, `exclude`, `report_history_days` |
| Actualización y límites | `refresh_seconds`, `cold_refresh_seconds`, `issues_refresh_seconds`, `discover_refresh_seconds`, `stuck_minutes`, `runs_per_repo`, `cold_runs_per_repo`, `hot_hours`, `max_workers`, `min_rate_remaining` |
| Centinela | `sentinel.enabled`, los ciclos, el presupuesto de la API, los umbrales de candidatos, de pull requests obsoletas y de firmas pendientes, `sentinel.require_verified_signature`, las consultas de A2 |
| Comprobaciones de superficie (A10) | `sentinel.surface.enabled`, sus ciclos, los repositorios por ciclo, el factor de margen y la parte del presupuesto |
| Preparación (A11) | `sentinel.readiness.enabled`, `min_coverage`, `warn_below` |
| Carpetas y ficheros | `workspace_root`, `signed_dir`, `audit_dir`, `ecosystems_file`, `targets_file`, `profiles_file`, `tools_dir`, `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Salidas para otras herramientas | `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`, `outputs.json.enabled`, `outputs.dashboard.enabled` (véase OUTPUTS_spa.md) |

## Lo que nunca se puede cambiar ni ver desde la página

Tokens, secretos, claves de firma, el secreto del webhook, el comando que el centinela puede ejecutar (`sentinel.notify_command`), los ajustes de IA y cualquier clave de otra herramienta: **no están en el
esquema**, así que la página ni los muestra ni los escribe, y una petición que nombre alguno se rechaza. Todas las demás claves del fichero se conservan exactamente como estaban.

## Cómo funciona un guardado

1. Solo se envían los valores que han cambiado, como `POST /api/settings` con `Content-Type: application/json` y un cuerpo de 16 KB como máximo.
2. Cada valor se comprueba según su tipo y su rango; un solo valor no válido rechaza toda la petición y no se escribe nada. Las rutas deben ser texto sin caracteres de control, nunca una
   ruta de red (UNC) y nunca en la unidad `D:`.
3. El fichero anterior se copia a `config_backups/actions_monitor-<time>.json` (se conservan las diez últimas copias).
4. El fichero nuevo se escribe en uno temporal y se mueve sobre el antiguo (de forma atómica), así que un fallo nunca deja un fichero a medias. Un fichero que no sea JSON válido nunca se sobrescribe desde la página.
5. La página indica qué valores guardados necesitan reinicio y mantiene un aviso hasta que reinicies.

## Quién puede pedirlo

Solo la página de la misma máquina: el servidor escucha en `127.0.0.1` y rechaza toda petición cuyo `Host` u `Origin` no sea su propia dirección (las mismas comprobaciones que en todos los demás endpoints).
Un formulario de otro sitio no puede alcanzarlo, porque la petición debe ser JSON.

## Antes de la 1.5.0

El idioma de las herramientas lo decidía el idioma del sistema; ahora arrancan en inglés y el idioma es un ajuste (aquí, `language`, `MONITOR_LANG` o `--lang`).
`parte_history_days` ahora es `report_history_days` (el nombre antiguo se sigue leyendo).
