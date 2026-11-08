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
