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
- `kind` es uno de `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`. Los campos solo se añaden. Responde cualquier 2xx; lo demás cuenta como fallo.
- `mqtt` publica el mismo JSON como carga de un mensaje QoS 0 en `notify.channels.mqtt.topic`.

## El límite por hora cuenta mensajes

`notify.max_per_hour` limita los MENSAJES que salen del ordenador, no los eventos: un evento que va a tres canales gasta tres unidades, una por canal. Si el cupo no alcanza para todos los canales, los primeros de la lista reciben el mensaje y el resto se descarta (la página lo cuenta como «limitado»). Un canal que no puede enviar (sin secreto, dirección incorrecta) no consume nada. El recuento se hace con un solo bloqueo, así que varios hilos nunca superan el límite.

## Avisos para cada usuario (modo equipo)

Desactivado por defecto (`notify.users.enabled`). Con el modo equipo activo, cada usuario elige en `GET/POST /api/auth/me/notify` los canales (`ntfy`, `teams`, `email`), los centinelas (`ci`, `collab`), el nivel mínimo (`info`, `warn`, `bad`), si quiere los eventos del sistema y si los mensajes llegan al momento o reunidos en un resumen (`hourly`, `daily`). El rol decide de qué puede enterarse un usuario: un lector, de los eventos de CI de las cuentas que puede ver; un mantenedor, además de lo que espera a una persona (una compilación pendiente de firma, una versión que toca publicar); un administrador, además de los eventos del sistema. Un evento de una cuenta nunca llega a quien no puede ver esa cuenta. `notify.users.max_per_hour` limita los mensajes que recibe un usuario.

- `ntfy`: el tema de cada usuario en el servidor `notify.channels.ntfy.server` (https, o uno de este equipo); un token de acceso es opcional.
- `teams`: la dirección del webhook entrante de un canal de Teams (solo servidores de Microsoft).
- `email`: la dirección del usuario, enviada por un relevo de este equipo que no pide inicio de sesión (`notify.channels.email`).

La dirección del webhook de Teams y el token de ntfy los guarda cifrados el sistema (DPAPI, Llavero, Secret Service o un archivo privado) y nunca vuelven en una respuesta, un registro ni la configuración; al borrar un usuario se borran. `MONITOR_SECRET_BACKEND=file` fuerza el archivo privado. Cada canal está apagado hasta que el administrador lo activa. El resumen reúne los avisos que el usuario no ha visto (hasta `notify.digest.max_items`); `POST /api/auth/me/notify/seen` los marca como vistos y no se envían; `POST /api/auth/me/notify/test` envía un mensaje de prueba a los canales del usuario. Un administrador lee las preferencias de todos (nunca un secreto) en `GET /api/auth/notify`.
