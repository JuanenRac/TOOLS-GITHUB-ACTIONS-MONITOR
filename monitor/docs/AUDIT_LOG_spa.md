<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | **🇪🇸 Español** | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# El registro de acciones

Solo Complete, encendido por defecto. Junto a la auditoría de los accesos (inicios de sesión, bloqueos, rechazos), el monitor lleva un registro de **acciones**: quién cambió qué, cuándo y en qué cuenta. Un cambio de ajustes, un silencio o su retirada, un cambio de usuarios, contraseñas, preferencias de notificación o credenciales. Es una línea JSON por acción en `logs/audit_actions.jsonl`, que nunca se reescribe.

## Qué dice una línea

`at`, `action` (una palabra simple como `settings_change` o `alert_mute`), `user`, `role`, `account`, `target` (un identificador corto: el nombre de un ajuste, un código de alerta), `result` (`ok`, `denied` o `error`) y, si ayuda, `details`. **Nunca entra un valor ni un secreto**: un cambio de ajustes escribe los nombres de los ajustes, no lo que valen; se descarta una clave cuyo nombre parece un secreto (token, password, key, cookie, authorization, session...); todo texto se limpia como las notas para IAs y se corta a 200 caracteres.

## La cadena

Cada línea lleva `prev` (el hash de la línea anterior) y `hash` (el hash de sí misma y de `prev`). Una línea cambiada, quitada o metida después rompe la cadena, y `GET /api/audit-log` dice dónde (`chain.broken_at`). Pasado `audit_log.max_mb`, la parte antigua se guarda como `audit_actions.jsonl.1` y la cadena sigue en el fichero nuevo. La cadena delata la manipulación; no puede impedir que quien tiene acceso al fichero lo borre entero, así que guarda una copia donde importe.

## Quién lo lee

Un administrador (y la persona en el equipo cuando no hay modo equipo). Un mantenedor solo cuando `audit_log.maintainers_can_read` está encendido; nadie más. `GET /api/audit-log` responde las últimas 200 líneas y el estado de la cadena. Lite no tiene nada de esto.

## Ajustes

Ajustes, pestaña Centinela, bloque **Registro de acciones**: `audit_log.enabled` (encendido), `audit_log.max_mb` (10) y `audit_log.maintainers_can_read` (apagado).
