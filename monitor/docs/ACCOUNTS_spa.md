<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ACCOUNTS.md) | **🇪🇸 Español** | [🇫🇷 Français](ACCOUNTS_fra.md) | [🇮🇹 Italiano](ACCOUNTS_ita.md) | [🇩🇪 Deutsch](ACCOUNTS_deu.md) | [🇨🇳 简体中文](ACCOUNTS_zho.md) | [🇯🇵 日本語](ACCOUNTS_jpn.md) | [🇵🇹 Português](ACCOUNTS_por.md)

# Varias cuentas

La edición completa puede vigilar varias cuentas de GitHub (una persona o una organización) a la vez. Cada cuenta es un monitor propio: un proceso aparte, con su carpeta, su puerto en `127.0.0.1`, su configuración y su propia lectura del margen de GitHub. Un fallo, una respuesta lenta o un límite de tasa de una cuenta nunca toca a las demás. La edición lite tiene una cuenta y nada de esto: ni siquiera muestra las opciones de abajo.

## Cuando no hay nada que hacer

Sin una carpeta `accounts/` el monitor funciona exactamente como antes: una cuenta, con sus ficheros junto al código. Solo sigues leyendo si quieres más de una.

## La carpeta de cuentas

```
accounts/
  global.json              opcional: {"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   la configuración de esta cuenta (su github_owner, repos, centinela...)
  org-acme/
    actions_monitor.json
```

El id de una cuenta son letras minúsculas, dígitos, `_` y `-` (hasta 40 caracteres), porque es el nombre de una carpeta; lo demás se rechaza. `enabled_accounts` es `"all"` o una lista; `default_account` es la que se abre cuando no se pide ninguna. `MONITOR_ACCOUNTS_DIR` mueve la carpeta. Cada cuenta guarda su caché, eventos, analítica, estado del centinela y registros dentro de su carpeta, así que dos cuentas nunca comparten un fichero.

## Pasar de una cuenta a varias

```
python actions_monitor.py --migrate-accounts          # muestra qué se copiaría, no escribe nada
python actions_monitor.py --migrate-accounts --apply  # lo copia en accounts/default/
python actions_monitor.py --accounts                  # lista las cuentas
```

Los originales nunca se mueven ni se borran: los borras tú cuando lo hayas comprobado. Una segunda ejecución se niega, así que dos estados nunca se mezclan. Para añadir una cuenta, crea `accounts/<id>/actions_monitor.json` con su `github_owner` (copia la plantilla `assets/examples/actions_monitor.example.json`).

## Ejecutar

`python actions_monitor.py` con una carpeta `accounts/` arranca el supervisor, un proceso pequeño en el puerto de siempre (8765) que arranca un monitor por cuenta y da a la página y a las herramientas una única dirección. No lee nada de GitHub y no escribe nada. Si una cuenta muere, la arranca de nuevo con una espera creciente (2, 5, 15, 30, 60 y luego 120 segundos) y el resumen dice que está caída mientras tanto. `python actions_monitor.py --account personal` ejecuta solo esa cuenta, como un monitor normal.

## La página

La página es la que conoces, con un selector de cuentas arriba en el panel lateral y una entrada **Todas las cuentas** que muestra una tarjeta por cuenta (estado, repositorios, en marcha, en rojo) y abre cualquiera de ellas. Cada ventana guarda su propia cuenta y vista: se leen de la dirección, nunca de un ajuste único que otra ventana pisaría.

| Dirección | Qué muestra |
|---|---|
| `/?account=org-acme` | la página de esa cuenta |
| `/?account=all` | las tarjetas de todas las cuentas |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | un panel |
| `/?chrome=0` | sin botones de cabecera, pestañas ni filtros: una pantalla para una pared o un segundo monitor |

Para varias pantallas abre una ventana por vista, por ejemplo `?view=now&chrome=0`, `?view=alerts&chrome=0` y `?view=live&chrome=0`. Un solo monitor las sirve todas, así que no gastas el margen dos veces. La vista **En vivo** muestra los últimos eventos que envió GitHub, el estado del receptor de webhook (activo o apagado, cuántas entregas se aceptaron, ignoraron, repitieron o rechazaron, nunca el secreto) y un selector del modo de trabajo.

## La API

`GET /api/accounts` es el resumen, `GET /api/accounts/<id>/status` una cuenta, y cualquier otra petición bajo `/api/` va a la cuenta indicada con `?account=<id>` o la cabecera `X-Account-Id` (la cuenta por defecto si no se da ninguna). Una cuenta desconocida es un 404. Las reglas de acceso son las de un monitor suelto: la misma comprobación de host y origen, y el mismo token de acceso en el modo red. El token de un solo uso de un cambio debe pedirse a la misma cuenta a la que se envía el cambio.

## Un webhook para todas

`POST /api/webhook` es una sola dirección para toda la instalación. El supervisor lee solo el propietario del repositorio en la carga (`repository.full_name`) y pasa el evento, intacto, a la cuenta cuyo `github_owner` es ese propietario; la cuenta verifica la firma con su propio secreto. Un propietario que nadie vigila se responde y se ignora. Para elegir tú la cuenta añade `?account=<id>`.

## Límites y honestidad

- Varias cuentas son varios procesos: cada uno lee GitHub por su cuenta, así que el margen lo comparte el login que uses. Míralo en las tarjetas y baja `refresh_seconds` o `max_workers` por cuenta si hace falta.
- Las comprobaciones que necesitan un navegador real, cuentas reales de GitHub y un túnel de webhook real las haces tú; las pruebas usan sustitutos del monitor de una cuenta y nunca llaman a GitHub.
- Una versión posterior traerá las cuentas a un solo proceso; la disposición de carpetas y la API de arriba se mantienen.
