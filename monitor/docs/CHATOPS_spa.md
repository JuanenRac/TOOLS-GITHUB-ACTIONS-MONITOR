<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CHATOPS.md) | **🇪🇸 Español** | [🇫🇷 Français](CHATOPS_fra.md) | [🇮🇹 Italiano](CHATOPS_ita.md) | [🇩🇪 Deutsch](CHATOPS_deu.md) | [🇨🇳 简体中文](CHATOPS_zho.md) | [🇯🇵 日本語](CHATOPS_jpn.md) | [🇵🇹 Português](CHATOPS_por.md)

# Comandos de chat (Slack y Discord)

Opcional, **desactivado por defecto**. Permite preguntar al monitor, desde un canal de Slack o Discord, por un estado breve: cuántos repositorios están en rojo, las alertas abiertas, la cola y la puntuación. Es de **solo lectura**.

## Qué hace (y qué nunca hace)

- Los comandos son una lista cerrada: `help`, `status`, `alerts`, `red`, `queue` y `score`. Cualquier otra cosa recibe "No conozco ese comando". `chatops.allowed_words` solo puede reducir la lista.
- Un comando lee lo que el monitor ya tiene (el último ciclo, las alertas, la puntuación). Nunca escribe en GitHub, nunca ejecuta una acción, nunca cambia un ajuste y nunca lee un secreto; no existe un comando para eso y no se puede añadir desde el chat.
- La respuesta solo la ve quien preguntó, no menciona a nadie y no lleva enlaces salvo uno: con `chatops.links` activado (por defecto), la dirección de un repositorio (`https://<host>/<propietario>/<repositorio>`, comprobada) junto a un nombre que se muestra tal cual. Todo texto que viene de GitHub (el nombre de un repositorio o de un workflow) se limpia, se recorta y se escapa para la plataforma.
- Cada comando que llega al monitor deja una línea en el registro de acciones (`chatops_command`) con los ids del chat, nunca el texto de la petición.

## Seguridad

- Desactivado hasta que `chatops.enabled` y el interruptor de la plataforma (`chatops.slack.enabled`, `chatops.discord.enabled`) estén activados **y** la prueba esté en el entorno. Los ajustes guardan solo el NOMBRE de la variable (`chatops.slack.signing_secret_env`, `chatops.discord.public_key_env`), nunca su valor; el valor no se escribe, no se muestra y no se registra.
- Slack: cada petición debe llevar `X-Slack-Signature: v0=<hmac>`, el HMAC-SHA256 de `v0:<marca de tiempo>:<cuerpo>` hecho con el secreto de firma, y `X-Slack-Request-Timestamp` no más antigua que `chatops.max_age_seconds` (cinco minutos como máximo). La comparación tarda lo mismo sea cual sea la firma.
- Discord: cada petición debe llevar `X-Signature-Ed25519` y `X-Signature-Timestamp`: una firma Ed25519 de la marca de tiempo seguida del cuerpo, comprobada con la clave pública de tu app (RFC 8032, biblioteca estándar; no se acepta nada sin la comprobación).
- Una firma mala, antigua o del futuro recibe `401` y no se mira nada del cuerpo. Una firma ya aceptada no se acepta otra vez. Un cuerpo de más de 16 KB recibe `413`. Una dirección puede hacer 120 peticiones por minuto.
- **Las listas son obligatorias**: `chatops.allowed_teams`, `chatops.allowed_channels` y `chatops.allowed_users`. Sin ninguna rellena, no se ejecuta ningún comando (el desafío de la plataforma se sigue respondiendo para que puedas terminar la configuración). Una lista con entradas debe contener el equipo, el canal o el usuario de la petición.
- Límites por minuto: `chatops.rate_per_user_per_minute`, `chatops.rate_per_channel_per_minute` y `chatops.rate_per_minute`. La respuesta debe llegar en 3 segundos: el monitor responde desde la memoria y, si tardara más, avisa de que está ocupado.
- Las dos rutas (`/api/chatops/slack`, `/api/chatops/discord`) no piden el token de acceso del modo red, porque una plataforma no puede enviarlo: la firma es su prueba, igual que en el webhook de entrada. El monitor sigue escuchando en `127.0.0.1` salvo que abras el modo red; las plataformas solo lo alcanzan por una dirección HTTPS que montas tú a propósito (un túnel o un proxy inverso; la herramienta nunca abre ninguno). Publica por ahí solo `/api/chatops/`.

## Los comandos

| Comando | Respuesta |
| --- | --- |
| `help` | la lista de comandos |
| `status` | repositorios en rojo, atascados, esperando, en verde e inactivos, y las alertas abiertas |
| `alerts` | las alertas abiertas (nivel, código y repositorio), hasta `chatops.max_rows` |
| `red` | los workflows en rojo con el tiempo que llevan así, hasta `chatops.max_rows` |
| `queue` | en ejecución, en cola, esperando aprobación y minutos usados en 24 horas |
| `score` | la puntuación, su letra y su cambio |

`chatops.show_repo_names` decide los nombres: `all` (todos los nombres, también los repositorios privados), `public` (por defecto: un repositorio privado es `private-N` y sus workflows no se nombran) o `none`. **Riesgo de `all`:** los nombres de repositorios y workflows privados llegan a todos los canales y usuarios que permitan tus listas. Por eso las listas son obligatorias y toda lista con entradas debe coincidir (equipo, canal y usuario a la vez). Mantén `public` o elige `none` si el canal es más amplio que las personas que pueden conocer esos nombres.

## Slack, paso a paso

1. Abre api.slack.com/apps > Create New App > From scratch. Ponle nombre y elige tu workspace.
2. Slash Commands > Create New Command: comando `/monitor`, **Request URL** `https://<tu dirección pública>/api/chatops/slack`, una descripción breve. No hace falta ningún permiso de bot.
3. Basic Information > App Credentials > **Signing Secret**: cópialo y dáselo al monitor por el entorno, nunca por el fichero: `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"` en PowerShell antes de arrancar el monitor, `export MONITOR_SLACK_SIGNING_SECRET=...` en una shell, una entrada de entorno o un fichero de secreto en un servicio o un contenedor.
4. Instala la app en el workspace (Install App).
5. Rellena las listas: el id de tu equipo (empieza por `T`), el id del canal (abre el canal, sus detalles, el id al final: `C...`) y tu id de miembro (tu perfil > Copy member ID: `U...`). Ponlos en Ajustes > Comandos de chat, o `"chatops": {"allowed_channels": ["C0123456789"]}` en `actions_monitor.json`.
6. Activa Comandos de chat y Slack, y reinicia el monitor.

## Discord, paso a paso

1. Abre discord.com/developers/applications > New Application. En General Information copia la **Public Key** (64 caracteres hexadecimales) y dásela al monitor por el entorno: `$env:MONITOR_DISCORD_PUBLIC_KEY = "<clave pública>"` en PowerShell, `export MONITOR_DISCORD_PUBLIC_KEY=...` en una shell.
2. Rellena las listas y activa Comandos de chat y Discord (Ajustes > Comandos de chat), y reinicia el monitor. Hazlo **antes** del paso siguiente: Discord envía una prueba firmada al guardar la dirección y la rechaza si el monitor no responde.
3. General Information > **Interactions Endpoint URL**: `https://<tu dirección pública>/api/chatops/discord`, y Save.
4. Registra el comando una vez con tu propia herramienta (la API de Discord, `POST /applications/<id de la aplicación>/commands`) con este cuerpo:

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. Invita la app solo con el alcance `applications.commands` (OAuth2 > URL Generator); no hace falta ningún permiso de bot. Ids: en Discord activa el Modo desarrollador (Avanzado) y usa Copiar ID en el servidor, el canal y tu usuario.

## Prueba

En un canal permitido escribe `/monitor help` (Slack) o `/monitor command:status` (Discord). Otras respuestas:

| Lo que ves | Significado |
| --- | --- |
| nada, o "no respondió" | la dirección no es alcanzable, el monitor está apagado, o respondió `401` (secreto o clave equivocados, o un reloj desfasado más de cinco minutos) |
| "Este comando no está disponible aquí." | el equipo, el canal o el usuario no está en las listas |
| "Demasiados comandos." | uno de los tres límites por minuto |
| "El monitor aún no ha leído GitHub." | el primer ciclo no ha terminado |
