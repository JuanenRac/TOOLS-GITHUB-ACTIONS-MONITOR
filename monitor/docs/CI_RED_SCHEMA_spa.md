<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_SCHEMA.md) | **🇪🇸 Español** | [🇫🇷 Français](CI_RED_SCHEMA_fra.md) | [🇮🇹 Italiano](CI_RED_SCHEMA_ita.md) | [🇩🇪 Deutsch](CI_RED_SCHEMA_deu.md) | [🇨🇳 简体中文](CI_RED_SCHEMA_zho.md) | [🇯🇵 日本語](CI_RED_SCHEMA_jpn.md) | [🇵🇹 Português](CI_RED_SCHEMA_por.md)

# ci_red.json - esquema 2 (contrato estable)

`ci_red.json` es la instantánea que escribe el monitor (de forma atómica, junto a sí mismo por defecto) para que cualquier consumidor pueda leer el estado de la CI sin preguntar
al monitor ni a GitHub: un panel, un script, un gancho de notificación. El formato es **estable: los campos solo se añaden, nunca se renombran ni se eliminan**.
Léelo con `.get()`; ignora los campos que no conozcas.

Dónde se escribe se define en `actions_monitor.json`:

| clave (`sentinel.`) | significado |
|---|---|
| `ci_red_file` | `""` = `ai/ci_red.json` del monitor (por defecto); `"off"` = no se escribe; una ruta = allí (las rutas relativas lo son respecto a la carpeta del monitor; se rechaza una unidad D:, una ruta UNC o una unidad que el sistema en ejecución no pueda usar) |
| `ci_red_audit_copy` | `true` además lo copia en la carpeta de auditoría cuando esa carpeta existe |

## Forma

```json
{
  "schema": 2,
  "generated": "2026-01-01T12:00:00Z",
  "generated_local": "2026-01-01 13:00:00 CET (12:00:00 UTC)",
  "tool_version": "1.2.0",
  "complete": true,
  "red_repos": 1,
  "pending_sign_repos": 1,
  "pending_sign_hours_threshold": 24,
  "repos": {
    "REPO": {
      "ecosystem": "armor | urtc | hydra | eh3d | other",
      "red": [{"workflow": "CI", "conclusion": "failure", "since": "2026-01-01T10:00:00Z", "streak": 2, "url": "https://github.com/OWNER/REPO/actions/runs/1"}],
      "pending_sign_hours": 31.5,
      "pending_sign": [{"workflow": "firmware-build.yml", "hours": 31.5, "state": "built_on_gha | signed_local",
                         "signature_kind": "none | dev | release", "signature_verified": true,
                         "last_build_at": "2026-01-01T08:00:00Z", "url": "https://github.com/OWNER/REPO/actions/runs/2"}]
    }
  }
}
```

* `complete` es `false` mientras el centinela sigue cargando: en ese caso no consideres en verde un repositorio que falte.
* `signature_verified` es `true`, `false` o la cadena `"unknown"` (nunca una suposición: los formatos que esta herramienta no puede comprobar son `"unknown"`).
* Los campos `pending_sign*` describen el **lado de firma local** y son para tus propias herramientas locales. Un consumidor público debe ignorarlos.
* La hora también se escribe para las personas: `generated_local` trae el mismo instante como fecha, hora y zona locales más la hora UTC (por ejemplo `2026-01-01 13:00:00 CET (12:00:00 UTC)`), en la zona de `display.timezone` (`local` por defecto). `generated` es siempre UTC y es el campo para los programas.

## La regla de «rojo» (una sola definición, en todas partes)

Se mira la **última ejecución completada de cada workflow en la rama por defecto**. Es roja cuando su conclusión es `failure`, `timed_out`,
`startup_failure` o `action_required` (espera una aprobación). `cancelled`, `skipped`, `neutral` y `stale` no dicen nada y se ignoran.
El «verde» del estado de firma usa la misma lista de ejecuciones. Un consumidor que vuelva a calcular la regla a partir de las ejecuciones de los workflows debe usar exactamente esta
definición para coincidir con el monitor.

## Publicar es un paso aparte y explícito

**Decisión: este PC no publica `ci_red.json` ni publica `pending_sign` ni ninguna otra parte del lado de firma en un repositorio, un panel ni ningún
servicio.** El fichero se queda en la máquina (y, cuando `ci_red_audit_copy` está activo, en la carpeta de auditoría local). Un panel público debe recalcular la lista de rojos a partir de las
ejecuciones públicas de los workflows con la regla anterior, o usar la exportación que se describe a continuación, que nunca incluye el estado de firma.

Nada en el monitor publica este fichero en un repositorio. Si un panel público necesita la lista de rojos, o bien déjale recalcular la regla a partir de los
datos públicos de las ejecuciones, o bien exporta tú mismo la parte no sensible:

```
python3 bin/read_report.py --export-status DIR
```

Esto escribe `ci_status_public.json` y `ci_status_public.md` en la carpeta que indiques y **solo** la lista de workflows en rojo (repositorio,
ecosistema, workflow, conclusión, desde cuándo, racha, enlace a la ejecución). Sin estado de firma, sin nombres de claves, sin rutas locales, sin comandos. La herramienta nunca hace commit ni
push; lo que ocurra con la carpeta después depende de ti.

`python3 bin/read_report.py --export-sign-queue FILE` (`.json` o `.csv`) escribe la cola global de firma con los comandos locales exactos. Ese fichero es
para el PC que ejecuta el monitor y lo dice en su interior.

Campo opcional `ai_hint` (añadido en la 1.6.4) en cada workflow en rojo: `{"class": "real|transient", "cause", "action"}` para una IA o un script. Los consumidores que leen con `.get()` pueden ignorarlo.
