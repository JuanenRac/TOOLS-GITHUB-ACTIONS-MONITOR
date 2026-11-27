<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FLEET_APIS.md) | **🇪🇸 Español** | [🇫🇷 Français](FLEET_APIS_fra.md) | [🇮🇹 Italiano](FLEET_APIS_ita.md) | [🇩🇪 Deutsch](FLEET_APIS_deu.md) | [🇨🇳 简体中文](FLEET_APIS_zho.md) | [🇯🇵 日本語](FLEET_APIS_jpn.md) | [🇵🇹 Português](FLEET_APIS_por.md)

# Flota por rol y grupo, APIs de lectura y sitio de demostración

## Roles y grupos

Al final de la pestaña Flota: el peor estado de cada grupo (ecosistema) con enlace a su propia pantalla `/g/<clave>`, y una columna por rol de workflow (`fleet.roles`). Lo no leído es `sin saber`, nunca bien.

## Desactivar

`fleet.disabled` admite nombres, patrones o `group:<clave>`; el monitor deja de leerlos en el ciclo siguiente, sin reiniciar. Ediciones Complete y Full.

## APIs de lectura

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`. Todas de solo lectura, con los mismos controles de acceso que lo demás; también bajo `/api/v1/` si la API versionada está activa. `fleet.cctray` sirve la fuente CCTray para CCMenu y similares; `fleet.security_api` sirve recuentos de alertas de secretos y de código por repositorio (nunca un secreto), nombrando lo que no se pudo leer. Ambas apagadas de fábrica.

## Huella de informes

Los informes y los briefs de la IA llevan `report_digest`: SHA-256 de los hechos, la versión del monitor, la de las reglas y el veredicto. Dos lectores con la misma huella vieron lo mismo. No es una firma.

## Sitio de demostración

Una copia estática de la demostración (datos inventados, sin acceso, sin acciones, sin peticiones a otros sitios) y una comprobación de workflows que corre en el navegador con Pyodide (no se sube nada):

```
python tools/make_public_demo.py demo-site
```

El workflow *Demo site* la guarda como artefacto. Publicarla en una dirección web es una decisión aparte del dueño del repositorio; nada la publica solo. La comprobación en el navegador no se ha probado en un sitio publicado.

## Todos los ajustes

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
