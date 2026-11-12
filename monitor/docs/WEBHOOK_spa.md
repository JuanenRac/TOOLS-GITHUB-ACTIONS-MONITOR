<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | **🇪🇸 Español** | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Webhook de entrada

Opcional y **apagado por defecto**. Permite que GitHub avise al monitor de que algo cambió, para que el repositorio se refresque en el siguiente ciclo en vez de esperar a la próxima consulta.

## Qué hace (solo refrescar)

Un evento aceptado solo marca el repositorio que nombra para refrescarlo en el siguiente ciclo. No se escribe nada en GitHub ni en disco, no se guarda ni se muestra ningún texto del evento y solo se aceptan repositorios que el monitor ya vigila. Eventos que entiende: `workflow_run`, `workflow_job`, `push`, `release`, `check_suite` y `ping`; cualquier otro se responde `202` y se ignora.

## Seguridad

- El monitor sigue escuchando solo en `127.0.0.1`. GitHub solo puede llegar a él por un túnel que tú montes a propósito; la herramienta nunca abre uno.
- Apagado hasta que `webhook.enabled` esté activo **y** el secreto compartido de `actions_monitor.json` tenga al menos 32 caracteres (si no, el endpoint sigue cerrado).
- Toda petición debe llevar `X-Hub-Signature-256: sha256=<hmac>`, hecho con ese secreto; lo demás recibe `401`. El secreto nunca se muestra: la pestaña Configuración solo dice si está definido.
- Un cuerpo de más de 256 KB recibe `413`.

## Cómo activarlo

En `actions_monitor.json`: `"webhook": {"enabled": true, "secret": "<32 o más caracteres aleatorios>"}`; el interruptor también está en la pestaña Configuración (subpestaña Webhook de entrada), el secreto solo en el archivo. Reinicia el monitor. En los ajustes del webhook de GitHub usa el tipo `application/json`, el mismo secreto y la URL de tu túnel acabada en `/api/webhook`.

## Eventos en tiempo real

- Con `webhook.record_events` activado (por defecto), un evento `workflow_run` firmado actualiza al instante la lista de runs de ese repositorio, sin leer GitHub: el repositorio no gasta cuota hasta su siguiente lectura programada. Un evento `workflow_job` aporta además el tiempo en cola y el de cada paso para la analítica.
- Solo se guardan campos cortos validados (workflow, run, estado, conclusión, rama, commit corto, enlace al run, duraciones); nunca el mensaje del commit ni texto libre. Los `webhook.live_events_keep` eventos más recientes se leen en `GET /api/live-events` (solo este equipo).
- Un run que termina en rojo envía además la notificación `workflow_failed` si las notificaciones están activas. Con `webhook.record_events` apagado el webhook vuelve al modo de solo refrescar descrito arriba.
- GitHub no puede llegar a `127.0.0.1`: usa `gh webhook forward` (ver la documentación de la CLI de GitHub) o un túnel que montes a propósito, apuntando a `http://127.0.0.1:PUERTO/api/webhook`.

## Reenvíos e inundaciones

Una petición firmada válida que alguien capturó y vuelve a enviar se responde pero no se ejecuta: cada entrega necesita su id `X-GitHub-Delivery`, los ids ya aceptados se recuerdan `webhook.replay_seconds` (una hora por defecto, memoria acotada) y una repetición recibe `202 {"duplicate": true}`. (Una re-entrega manual desde la página de GitHub reutiliza el id, así que se ignora dentro de esa ventana.) Un repositorio puede causar como mucho `webhook.max_per_minute` eventos aceptados por minuto; el resto se responden y se ignoran. Si la carga indica `full_name`, su propietario debe ser la cuenta vigilada (o uno de `webhook.allowed_owners`). En modo red, una dirección puede enviar 120 peticiones por minuto. Tras un evento aceptado se descartan las lecturas condicionales guardadas de ese repositorio y se vuelve a leer en el ciclo siguiente, así un evento en vivo siempre se concilia con GitHub.

## Lista de comprobación de la vista En vivo

1. Define `webhook.secret` con al menos 32 caracteres y activa el webhook.
2. Redirige el puerto (`gh webhook forward`) o abre un túnel y usa su dirección acabada en `/api/webhook` en GitHub.
3. Envía el evento de prueba de GitHub (Recent deliveries > Redeliver) y búscalo en `?view=live`.
4. Vigila la cuota en la cabecera: con webhooks basta un ciclo más lento.
