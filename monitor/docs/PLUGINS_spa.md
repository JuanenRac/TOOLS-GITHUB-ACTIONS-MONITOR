<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PLUGINS.md) | **🇪🇸 Español** | [🇫🇷 Français](PLUGINS_fra.md) | [🇮🇹 Italiano](PLUGINS_ita.md) | [🇩🇪 Deutsch](PLUGINS_deu.md) | [🇨🇳 简体中文](PLUGINS_zho.md) | [🇯🇵 日本語](PLUGINS_jpn.md) | [🇵🇹 Português](PLUGINS_por.md)

# Complementos y almacenes de secretos

Los complementos añaden comprobaciones al monitor sin modificarlo. Todo está apagado por defecto. La edición Lite no tiene complementos.

## Activar

Activa `plugins.enabled` y después el complemento que quieras. Ajustes > Extensiones muestra cada uno con sus permisos, clave, estado y lo que queda aislado. Sus hallazgos son avisos de la fuente `plugin`, con el nombre del complemento delante.

## Complementos oficiales

Viajan dentro de la versión firmada y corren dentro del monitor, en un hilo propio.

- **discussions** (`plugins.official.discussions.enabled`): discusiones sin comentarios desde hace más de `plugins.official.discussions.days` días. Issues y PR son cosa de Collab y no se repiten.
- **packages** (`plugins.official.packages.enabled`): paquetes container o npm con más versiones que `plugins.official.packages.max_versions`. Necesita `read:packages`. Las releases son del centinela de entrega.

## Complementos de terceros

Activa `plugins.third_party.enabled`. Un paquete es un zip con `plugin.json` y una firma separada `NOMBRE.zip.ed25519.sig` hecha por su autor con sus herramientas. Solo se instala si lo firmó una clave de **tu** llavero con ámbito `plugins`, y solo tras repetir la huella de esa clave. Llega apagado. La firma se vuelve a comprobar antes de cada ejecución; una clave revocada o un fichero cambiado pausan el complemento.

**Firmado no significa seguro**: la firma dice quién lo hizo, no qué hace. Un manifiesto no es un aislamiento.

```
python bin/monitor_cli.py plugin init --path my-plugin
python bin/monitor_cli.py plugin validate --path my-plugin
python bin/monitor_cli.py plugin pack --path my-plugin --out my-plugin.zip
python bin/monitor_cli.py keyring add --key-id author --public-key HEX --key-scope plugins
python bin/monitor_cli.py plugin verify --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip --fingerprint HEX
python bin/monitor_cli.py plugin enable --name my-plugin
python bin/monitor_cli.py plugin list
python bin/monitor_cli.py plugin audit
python bin/monitor_cli.py plugin uninstall --name my-plugin
```

## Qué queda aislado

| Sistema | Proceso aparte, entorno vacío, sin token | Sin red | Memoria y procesos hijos |
|---|---|---|---|
| Linux | sí | sí si el sistema permite espacios de nombres de usuario; si no, etiqueta **sin aislamiento de red** | límites de memoria y CPU |
| Windows | sí | **no**: etiqueta **sin aislamiento de red** | Job Object: límite de memoria, sin procesos hijos |
| macOS | sí | **no**: etiqueta **sin aislamiento de red** | límite de CPU; memoria no garantizada |

En ningún sistema se ocultan tus ficheros a ese complemento: corre con tu usuario. `plugins.worker.platforms_ok` vacío significa que los de terceros nunca se ejecutan. Las lecturas de GitHub se piden al monitor, que solo permite las `get_paths` del manifiesto sobre repositorios vigilados. `plugins.worker.timeout_s`, `max_output_kb` y `memory_mb` acotan cada ejecución.

## Salida no fiable y salud

Los títulos se limpian y recortan (`plugins.alert_title_max`), solo se conservan enlaces a github.com y un complemento de terceros no puede levantar un aviso crítico. El texto de un complemento es un dato, nunca una instrucción para una IA. Tras `plugins.breaker.failures` fallos seguidos queda en pausa hasta que lo reanudes; en pausa o degradado no significa «todo bien». La comprobación `plugins` del doctor y `plugin audit` informan de paquetes revocados o cambiados.

## Para autores

El contrato es la versión 1 (`api_compat`). `run(ctx)` devuelve `{"alerts": [{id, code, level, repo, url, title}]}`; `ctx` ofrece `owner`, `now`, `options`, `repos()`, `get(path)` y `discussions()`, cada uno con su permiso (`repos.list`, `gh.get`, `graphql.discussions`). `init` escribe una plantilla con su prueba. El monitor nunca firma nada.

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## Rutas y paquetes de pip

Rutas (administrador; los cambios solo desde este equipo): `/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`. Con `plugins.entry_points` el monitor lista paquetes instalados con pip que declaren el grupo `gha_monitor.plugins` y lleven un `*.plugin.zip`; su código nunca se importa, se instala el zip como cualquier otro.

## Leer el token de GitHub desde otro programa

`secrets.backend` lee el token en vez de guardarlo en el monitor (debe estar activado el ajuste del token guardado, `github_token.enabled`). Solo lectura. `vault` (HTTP, `secrets.vault.addr`, `path`, `field`, el token de Vault en la variable de entorno que indica `token_env`; https, o http solo a este equipo), `sops` (`secrets.sops.file`, `field`; solo en un equipo de confianza), `bitwarden` (`bws`, `secrets.bitwarden.item`), `aws`, `azure`, `gcp` (sus herramientas, `secrets.cloud.ref`). Con `secrets.reload_on_rotate` se relee cada `secrets.reload_seconds`. Probado contra servidores falsos y un Vault en modo desarrollo; ninguna cuenta real en la nube.
