<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](NOTIFICATIONS.md) | **🇪🇸 Español** | [🇫🇷 Français](NOTIFICATIONS_fra.md) | [🇮🇹 Italiano](NOTIFICATIONS_ita.md) | [🇩🇪 Deutsch](NOTIFICATIONS_deu.md) | [🇨🇳 简体中文](NOTIFICATIONS_zho.md) | [🇯🇵 日本語](NOTIFICATIONS_jpn.md) | [🇵🇹 Português](NOTIFICATIONS_por.md)

# Notificaciones

Opcionales y **apagadas por defecto**. Los eventos del feed (un rojo nuevo, un build colgado, un build esperando su firma, una conexión perdida, un run fallido avisado por el webhook) pueden enviarse a un chat o a un dispositivo. Una notificación es solo un mensaje con un enlace: nunca relanza, cancela ni escribe nada en GitHub.

## Canales

- `telegram` (un bot), `discord` y `slack` (webhook de canal), `matrix` (una sala), `mqtt` (un broker en este equipo, para luces y balizas) y `http_local` (un POST a una dirección de este equipo).
- Cada canal tiene su interruptor en la pestaña Configuración (subpestaña Notificaciones) y un botón para enviar una prueba.


## Seguridad

- Los tokens y las URL de webhook nunca se guardan en la configuración: se pone el NOMBRE de una variable de entorno y el valor solo se lee al enviar, sin mostrarse ni registrarse.
- `discord` solo acepta `discord.com` y `slack` solo `hooks.slack.com`; `mqtt` y `http_local` solo aceptan `127.0.0.1`, `localhost` o `[::1]`.
- Se rechaza un destino que sea, o resuelva a, una dirección de bucle local, privada (10.x, 172.16-31.x, 192.168.x, fc00::/7), de enlace local (169.254.x con la dirección de metadatos de la nube, fe80::/10), compartida (100.64.0.0/10) o reservada, salvo que `notify.allow_private_targets` esté encendido (apagado por defecto). El nombre se resuelve una vez, la conexión va a la dirección comprobada y cada redirección pasa por la misma regla. Así un servidor Matrix mal puesto no alcanza tu router ni el servicio de metadatos de una máquina en la nube.
- Como máximo salen `notify.max_per_hour` mensajes del equipo; un envío que falla se cuenta y se ignora, nunca detiene el monitor.


## El contrato de los adaptadores

- Para llegar a un servicio que no está en la lista, ejecuta un pequeño receptor en este equipo y apunta `http_local` hacia él. Recibe un POST con `Content-Type: application/json` y este cuerpo: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` es uno de `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `ai_alert`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`, `github_incident`, `github_incident_over`, `score_dropped`, `security_new`, `security_fixed`, `delivery_new`, `delivery_fixed`, `alerts_digest`, `silence_review`. Los campos solo se añaden. Responde cualquier 2xx; lo demás cuenta como fallo.
- `mqtt` publica el mismo JSON como carga de un mensaje QoS 0 en `notify.channels.mqtt.topic`.

## Apprise (opcional, apagado por defecto)

El canal `apprise` entrega el mensaje a la orden `apprise` (instálala tú, por ejemplo `pip install apprise`) para llegar a cualquiera de los servicios que conoce. Las direcciones contienen los secretos de esos servicios, así que están en una variable de entorno cuyo NOMBRE es `notify.channels.apprise.urls_env` (separadas por espacios o comas, como mucho diez); se escriben en un fichero temporal privado durante el instante de la llamada, nunca en los argumentos de la orden, y la orden recibe un entorno sin las claves del monitor. **Apprise abre sus propias conexiones: la protección del monitor contra direcciones privadas no se le aplica**, así que lo que alcance depende de las direcciones que le des; por eso el canal tiene su propio interruptor, apagado por defecto, y está marcado como ajuste de seguridad. Si falta la orden, el canal dice `not_installed`; un fallo se cuenta como cualquier otro y nunca detiene el monitor.

## El estado de GitHub (desactivado por defecto)

Con `github_status.enabled` activado, el monitor lee el resumen público de githubstatus.com cada `github_status.interval_seconds` (300 por defecto): un JSON pequeño, sin cuenta y sin enviar nada sobre ti. La barra inferior de la página muestra el estado de GitHub. Cuando GitHub Actions tiene un incidente el monitor lo avisa una vez (los tipos `github_incident` y `github_incident_over`, que solo se notifican si los añades a `notify.events`), y con `github_status.mark_reds` (activado) un rojo que aparece durante el incidente dice «causa posible: un incidente de GitHub» en su texto y en el campo `possible_cause`. El rojo nunca se oculta.

## El límite por hora cuenta mensajes

`notify.max_per_hour` limita los MENSAJES que salen del ordenador, no los eventos: un evento que va a tres canales gasta tres unidades, una por canal. Si el cupo no alcanza para todos los canales, los primeros de la lista reciben el mensaje y el resto se descarta (la página lo cuenta como «limitado»). Un canal que no puede enviar (sin secreto, dirección incorrecta) no consume nada. El recuento se hace con un solo bloqueo, así que varios hilos nunca superan el límite.

## Avisos para cada usuario (modo equipo)

Desactivado por defecto (`notify.users.enabled`). Con el modo equipo activo, cada usuario elige en `GET/POST /api/auth/me/notify` los canales (`ntfy`, `teams`, `email`), los centinelas (`ci`, `collab`), el nivel mínimo (`info`, `warn`, `bad`), si quiere los eventos del sistema y si los mensajes llegan al momento o reunidos en un resumen (`hourly`, `daily`). El rol decide de qué puede enterarse un usuario: un lector, de los eventos de CI de las cuentas que puede ver; un mantenedor, además de lo que espera a una persona (una compilación pendiente de firma, una versión que toca publicar); un administrador, además de los eventos del sistema. Un evento de una cuenta nunca llega a quien no puede ver esa cuenta. `notify.users.max_per_hour` limita los mensajes que recibe un usuario.

- `ntfy`: el tema de cada usuario en el servidor `notify.channels.ntfy.server` (https, o uno de este equipo); un token de acceso es opcional.
- `teams`: la dirección del webhook entrante de un canal de Teams (solo servidores de Microsoft). El mensaje siempre lleva su `Content-Length` (nunca en trozos, que Teams rechaza) y, para una dirección de Workflows (`logic.azure.com`, `powerplatform.com`), va como tarjeta adaptable.
- `email`: la dirección del usuario, enviada por un relevo de este equipo que no pide inicio de sesión (`notify.channels.email`).

La dirección del webhook de Teams y el token de ntfy los guarda cifrados el sistema (DPAPI, Llavero, Secret Service o un archivo privado) y nunca vuelven en una respuesta, un registro ni la configuración; al borrar un usuario se borran. `MONITOR_SECRET_BACKEND=file` fuerza el archivo privado. Cada canal está apagado hasta que el administrador lo activa. El resumen reúne los avisos que el usuario no ha visto (hasta `notify.digest.max_items`); `POST /api/auth/me/notify/seen` los marca como vistos y no se envían; `POST /api/auth/me/notify/test` envía un mensaje de prueba a los canales del usuario. Un administrador lee las preferencias de todos (nunca un secreto) en `GET /api/auth/notify`.

### El panel de cada usuario

En el modo equipo, el menú del usuario con sesión (el nombre arriba) tiene la entrada **Notificaciones**. El panel muestra y guarda las mismas preferencias que `GET/POST /api/auth/me/notify`: si quieres notificaciones, los canales (ntfy con su tema y un token opcional, Teams con la dirección web del canal, correo con una dirección), los centinelas (CI, colaboración), el nivel mínimo, los eventos del sistema (solo para un administrador) y si cada alerta llega al momento o en un resumen por hora o por día. Un secreto ya guardado se muestra como guardado y nunca vuelve a la página; solo se envía si escribes uno nuevo, y una casilla vacía lo conserva. **Enviar una prueba** manda un mensaje a tus canales y **He visto mis alertas** marca las pendientes como vistas. Si el administrador no ha activado `notify.users.enabled`, el panel lo dice: puedes guardar tus preferencias, aún no se envía nada.

## Muchos avisos, o los mismos una y otra vez

Cuatro ajustes opcionales del bloque `alerts` (todos apagados o vacíos por defecto) deciden qué llega a los canales de arriba. Las listas, la pestaña Alertas y el registro de eventos siguen mostrándolo todo.

- **Silencios permanentes** (`alerts.silences`): una entrada por línea, `repositorio:workflow:rama;motivo;fecha de revisión`. Todo salvo el repositorio es opcional y `*` vale para cualquier texto. Los avisos que coinciden se muestran como silenciados, nadie recibe notificación y en la fecha de revisión se anuncia un recordatorio; el silencio sigue hasta que lo quites.
- **Servicios y crons cortos** (`alerts.service`): un workflow que solo se ejecuta programado o a mano y falla de vez en cuando se anuncia solo tras `failures` fallos seguidos, o cuando falló `rate_percent` de sus últimos runs; se anuncia una vez y se despeja una vez en lugar de avisar en bucle. `workflows` añade más workflows a esta clase.
- **Agrupar por commit** (`alerts.group`): cuando `min` o más workflows de un repositorio se ponen en rojo en el mismo commit, una notificación los lista.
- **Resumen cuando hay muchos** (`alerts.digest`): pasadas `threshold` notificaciones en la última hora, el resto se retiene y se cuenta en un resumen cada `minutes` minutos. Los eventos retenidos quedan en el registro de eventos.

## No repetir una notificación

Con `notify.dedupe_ledger` encendido (apagado por defecto) el monitor guarda un registro de lo que ya notificó en un fichero pequeño de la carpeta de datos: un hash del tipo de evento, el repositorio, el workflow y el enlace de la ejecución, nunca el texto. La misma notificación no se vuelve a enviar al recargar una página, tras un reinicio, ni cuando un pipeline sale un rato de la ventana y vuelve; una ejecución nueva del mismo workflow es una notificación nueva. Una etiqueta se recuerda `notify.dedupe_hours` horas (24 por defecto). `notify.max_event_age_hours` (0 = apagado) descarta además un evento cuya propia fecha es más antigua que eso: la noticia de algo ocurrido hace días no es noticia.

El canal de Microsoft Teams acepta la dirección de un flujo de **Workflows** de Power Automate (hosts `logic.azure.com` y `api.powerplatform.com`) además de los antiguos conectores de Office 365 (`webhook.office.com`, `outlook.office.com`): crea el flujo con el desencadenador "Cuando se recibe una solicitud de webhook de Teams", copia su dirección en la variable que nombra el canal y el monitor le publica un mensaje de texto simple.
