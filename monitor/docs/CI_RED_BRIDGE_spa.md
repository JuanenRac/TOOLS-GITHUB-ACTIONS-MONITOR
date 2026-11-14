<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_BRIDGE.md) | **🇪🇸 Español** | [🇫🇷 Français](CI_RED_BRIDGE_fra.md) | [🇮🇹 Italiano](CI_RED_BRIDGE_ita.md) | [🇩🇪 Deutsch](CI_RED_BRIDGE_deu.md) | [🇨🇳 简体中文](CI_RED_BRIDGE_zho.md) | [🇯🇵 日本語](CI_RED_BRIDGE_jpn.md) | [🇵🇹 Português](CI_RED_BRIDGE_por.md)

# Del monitor al panel: `ci_red.json`

Qué escribe el monitor, cómo exportarlo y qué necesita quien lee el fichero. El monitor solo lee GitHub y escribe ficheros locales: nunca hace push, nunca hace commit y nunca cierra nada por su cuenta.

## Qué escribe el monitor

`ci_red.json` junto a `bin/actions_monitor.py`, actualizado tras cada pasada del centinela (esquema 2):

| Campo | Significado |
|---|---|
| `schema` | `2`. Los campos solo se añaden, nunca se renombran. |
| `generated` | Hora UTC de la pasada. |
| `tool_version` | Versión de la herramienta que escribió el fichero. |
| `complete` | `true` cuando se leyó cada repositorio vigilado en esa pasada. `false` mientras carga, cuando la cuota de la API se quedó corta o cuando faltan clones: no actúes sobre la lista de repositorios en rojo ni sobre la cola de firma hasta que sea `true`. |
| `red_repos` / `pending_sign_repos` | Recuentos. |
| `repos.<NAME>.ecosystem` | `armor`, `urtc`, `hydra`, `eh3d` u `other`. |
| `repos.<NAME>.red[]` | Una entrada por workflow cuya última ejecución completada en la rama por defecto falló: `workflow`, `conclusion`, `since`, `streak`, `url`. |
| `repos.<NAME>.pending_sign[]` y `pending_sign_hours` | Versiones compiladas y aún sin firmar, y la antigüedad de la más antigua. |

## Cómo exportarlo

```
py -3 bin/read_report.py --export-status DIR          # ci_status_public.json + .md, solo lo que se puede publicar
py -3 bin/read_report.py --export-sign-queue FILE     # la cola de firma
```

Ambos leen el monitor en ejecución en `127.0.0.1` (sin cuota de GitHub). Se niegan a escribir mientras la instantánea está cargando y explican por qué; en ese caso el código de salida no es cero.

## Qué necesita quien lee (el generador del panel)

1. Leer `schema`; aceptar cualquier valor `>= 2` e ignorar los campos desconocidos.
2. Leer `complete`; cuando sea `false`, conservar la última exportación completa en lugar de sustituirla.
3. Mostrar `generated` junto a las cifras para que un fichero obsoleto se note.
4. Usar `repos.<NAME>.red[].url` como enlace; nunca reconstruirlo.

## Qué no hace el monitor

No publica el fichero, no hace push al repositorio del perfil y no toca ningún workflow. Llevar la exportación al panel es un paso del propietario (o de un workflow del repositorio del perfil que lea el fichero exportado).

## El panel del perfil (contrato del consumidor)

El panel de estado de un repositorio de perfil puede leer el mismo documento de dos maneras: del monitor en marcha (`GET /api/outputs/dashboard.json`, apagado hasta activar `outputs.dashboard.enabled`, solo este equipo) o del archivo que escribe `py -3 bin/read_report.py --export-status DIR` (solo los workflows en rojo, nunca la parte de firma). Lo que el panel puede dar por seguro, comprobado por una prueba de este repositorio:

1. `schema` es `2` y los campos solo se añaden.
2. El documento servido es exactamente el de `ci_red.json`.
3. `complete: false` significa: conserva tu última imagen completa.
4. La exportación pública tiene las claves `schema`, `generated`, `tool_version`, `complete`, `red_repos` y `red`, y nada del estado de firma.

El monitor nunca sube el archivo al repositorio del perfil; llevarlo allí es un paso de su dueño.
