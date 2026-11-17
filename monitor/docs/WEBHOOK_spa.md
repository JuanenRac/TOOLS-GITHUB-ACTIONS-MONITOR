<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | **🇪🇸 Español** | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Webhook de entrada

Opcional y **apagado por defecto**. Permite que GitHub avise al monitor de que algo cambió, para que el repositorio se refresque en el siguiente ciclo en vez de esperar a la próxima consulta.

## Qué hace (solo refrescar)

Un evento aceptado solo marca el repositorio que nombra para refrescarlo en el siguiente ciclo. No se escribe nada en GitHub ni en disco, no se guarda ni se muestra ningún texto del evento y solo se aceptan repositorios que el monitor ya vigila. Eventos que entiende: `workflow_run`, `workflow_job`, `push`, `release`, `check_run`, `check_suite` y `ping`; cualquier otro se responde `202` y se ignora.

## Seguridad

- El monitor sigue escuchando solo en `127.0.0.1`. GitHub solo puede llegar a él por un túnel que montes a propósito; la herramienta nunca abre ninguno.
- Apagado hasta que `webhook.enabled` esté activo **y** el secreto compartido (32 caracteres o más) esté en la variable de entorno que indica `webhook.secret_env` (`MONITOR_WEBHOOK_SECRET` por defecto; `MONITOR_WEBHOOK_SECRET_FILE` puede nombrar un fichero cuya primera línea es el secreto, como hacen los secretos de un contenedor). El secreto nunca se escribe en `actions_monitor.json`, ni se muestra, ni se registra, ni lo heredan los programas que lanza el monitor; la pestaña Ajustes solo dice si está definido. La forma antigua (un `secret` en el fichero) solo se lee si `webhook.allow_config_secret` es verdadero, y la vista En vivo avisa mientras se usa.
- Toda petición debe llevar `X-Hub-Signature-256: sha256=<hmac>`, hecho con ese secreto y comparado en tiempo constante; cualquier otra recibe `401`, y no se mira nada del contenido antes de comprobar la firma.
- Un cuerpo de más de 256 KB recibe `413`, antes de calcular nada.
- Las listas son cerradas: solo se actúa sobre `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` y `ping`, de un evento solo se guardan campos cortos y validados (nunca un mensaje de commit ni texto libre), y todo lo demás se responde `202` y se descarta.

## Cómo activarlo

1. Crea un secreto de 32 o más caracteres aleatorios, por ejemplo `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Pásaselo al monitor por su entorno, nunca por el fichero: `$env:MONITOR_WEBHOOK_SECRET = "<el secreto>"` en PowerShell antes de arrancar el monitor, `export MONITOR_WEBHOOK_SECRET=...` en una shell, `Environment=` o `EnvironmentFile=` (un fichero que solo tú puedas leer) en un servicio, `-e` o un fichero de secreto nombrado por `MONITOR_WEBHOOK_SECRET_FILE` en un contenedor.
3. Activa el receptor (Ajustes > Webhook de entrada > Receptor activado, o `"webhook": {"enabled": true}` en `actions_monitor.json`) y reinicia el monitor.
4. Haz alcanzable la dirección: GitHub no llega a `127.0.0.1`. Usa un túnel que montes a propósito (una dirección HTTPS acabada en `/api/webhook`) o, en este equipo, `gh webhook forward` apuntando a `http://127.0.0.1:PUERTO/api/webhook` (mira la documentación de la CLI de GitHub para darle el mismo secreto sin escribirlo en la línea de comandos).
5. En GitHub abre el repositorio (o la organización) > Settings > Webhooks > Add webhook. **Payload URL**: la dirección de tu túnel acabada en `/api/webhook`. **Content type**: `application/json`. **Secret**: el mismo secreto. **SSL verification**: activada. **Events**: «Let me select individual events», luego Workflow runs y Workflow jobs, y opcionalmente Check runs, Pushes y Releases. **Active**: activado. Un webhook de una organización cubre todos sus repositorios; el monitor ignora los que no vigila.
6. Compruébalo: en GitHub, Recent deliveries debe mostrar `200` en el primer `ping`; en el monitor la vista En vivo muestra el receptor activo, los contadores y la cobertura.

## Eventos en tiempo real

- Con `webhook.record_events` activado (por defecto), un evento `workflow_run` firmado actualiza al instante la lista de runs de ese repositorio, sin leer GitHub: el repositorio se vuelve a leer igualmente en el ciclo siguiente (el evento es la noticia, la lectura es la prueba), así que una entrega muestra el cambio al instante pero no ahorra una lectura. Un evento `workflow_job` aporta además el tiempo en cola y el de cada paso para la analítica.
- Solo se guardan campos cortos validados (workflow, run, estado, conclusión, rama, commit corto, enlace al run, duraciones); nunca el mensaje del commit. Los nombres del workflow, la rama y el trabajo son texto de terceros de hasta 100 caracteres: se guardan y se muestran como texto plano, y los nombres de los pasos van a las estadísticas. Los `webhook.live_events_keep` eventos más recientes se leen en `GET /api/live-events` (quien pueda abrir la página: el token de acceso en modo red, una sesión en modo equipo).
- Opcional, apagado por defecto: con `live.sse.enabled` encendido, `GET /api/live-events/stream` envía esos mismos eventos según se aceptan, como eventos del servidor (`hello`, luego un marco `live` por evento, con un `id` correlativo para reanudar con `Last-Event-ID` o `?since=`, un comentario de latido y un `bye` final). Solo lectura; en modo red pide el token de acceso como cualquier otra petición; como máximo `live.sse.max_clients` oyentes, cada uno durante `live.sse.max_seconds`. La edición Lite no lo tiene.
- Un run que termina en rojo envía además la notificación `workflow_failed` si las notificaciones están activas. Con `webhook.record_events` apagado el webhook vuelve al modo de solo refrescar descrito arriba.
- GitHub no puede llegar a `127.0.0.1`: usa `gh webhook forward` (ver la documentación de la CLI de GitHub) o un túnel que montes a propósito, apuntando a `http://127.0.0.1:PUERTO/api/webhook`.

## Cobertura en el tiempo

La vista En vivo dice cuánto del tiempo cubren los eventos el estado: **cubierto por eventos** (el último evento es más reciente que `savings.webhook_window_minutes`, 60 minutos por defecto), **sin eventos desde hace ...** (más antiguo: un repositorio tranquilo o un túnel caído) o **esperando el primer evento**. El sondeo es siempre el respaldo: un envío que nunca llegó (el monitor estaba apagado, el túnel se cayó) lo recoge la siguiente lectura del repositorio, así que los eventos reducen las lecturas pero nunca las sustituyen. Las mismas cifras están en `GET /api/live-status`, en `coverage` y `secret_source` (`env`, `config` o `none`; nunca el secreto).

## Si no funciona

| Respuesta | Significado |
|---|---|
| `404` | El receptor está apagado, o falta el secreto o tiene menos de 32 caracteres en la variable de entorno. |
| `401` | La firma no coincide: usa el mismo secreto en ambos lados y el tipo de contenido `application/json`. |
| `413` | El cuerpo supera 256 KB. |
| `400` | No hay un id `X-GitHub-Delivery` válido, o el contenido no se entiende. |
| `202` | Aceptado e ignorado: un repositorio que no se vigila, un evento fuera de la lista, un envío repetido o un repositorio por encima de su límite por minuto. |
| `429` | Una dirección envió más de 120 peticiones con firma correcta en un minuto, o más de `webhook.max_bad_per_minute` (120 por defecto) cuya firma no se verifica. |

## Reenvíos e inundaciones

Una petición firmada válida que alguien capturó y vuelve a enviar se responde pero no se ejecuta: cada entrega necesita su id `X-GitHub-Delivery`, los ids ya aceptados, y el propio cuerpo firmado, se recuerdan `webhook.replay_seconds` (una hora por defecto, memoria acotada), así que una petición capturada y reenviada con otro id es la misma entrega, y una repetición recibe `202 {"duplicate": true}`. (Una re-entrega manual desde la página de GitHub repite el mismo cuerpo, así que se ignora dentro de esa ventana.) Un repositorio puede causar como mucho `webhook.max_per_minute` eventos aceptados por minuto; el resto se responden y se ignoran. Si la carga indica `full_name`, su propietario debe ser la cuenta vigilada (o uno de `webhook.allowed_owners`). Una dirección puede enviar 120 peticiones con firma correcta por minuto y `webhook.max_bad_per_minute` con firma que no se verifica; se cuentan por separado, en todos los modos, de modo que la basura nunca gasta el cupo de las entregas reales (con `listen.trusted_proxy` la dirección es la que vio el proxy). Tras un evento aceptado se descartan las lecturas condicionales guardadas de ese repositorio y se vuelve a leer en el ciclo siguiente, así un evento en vivo siempre se concilia con GitHub.

## Lista de comprobación de la vista En vivo

1. Pon un secreto de al menos 32 caracteres en la variable de entorno que indica `webhook.secret_env` y activa el webhook.
2. Redirige el puerto (`gh webhook forward`) o abre un túnel y usa su dirección acabada en `/api/webhook` en GitHub.
3. Envía el evento de prueba de GitHub (Recent deliveries > Redeliver) y búscalo en `?view=live`.
4. Vigila la cuota en la cabecera: con webhooks basta un ciclo más lento.
