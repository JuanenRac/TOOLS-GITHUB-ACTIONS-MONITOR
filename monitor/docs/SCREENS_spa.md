<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | **🇪🇸 Español** | [🇫🇷 Français](SCREENS_fra.md) | [🇮🇹 Italiano](SCREENS_ita.md) | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | [🇵🇹 Português](SCREENS_por.md)

# Pantallas, tamaños y orientación

La página se adapta al tamaño de su ventana, de un móvil a 4K, en vertical o en horizontal, y un mismo monitor puede servir varias pantallas, cada una con las pestañas que elijas. Nada se consulta dos veces: todas las pantallas leen el mismo estado.

## Direcciones

- `/` - la página entera.
- `/screen/1`, `/screen/2`, `/screen/3` - las pestañas fijadas para esa pantalla (`ui.screen1_tabs` ...). Abre cada una en una ventana de su propio monitor o tele.
- `?orient=portrait` o `?orient=landscape` fuerza la disposición de una ventana; `?tabs=now,charts` y `?rotate=30` fijan las pestañas y los segundos entre ellas en una ventana.

## Ajustes

| Ajuste | Qué hace |
|---|---|
| `ui.orientation` | auto sigue a la ventana; portrait apila los paneles en una columna; landscape mantiene la disposición lado a lado. |
| `ui.rotate_seconds` | 0 = apagado. Segundos entre las pestañas de una pantalla que tiene más de una. |
| `ui.screen1_tabs` | Pestañas de /screen/1, separadas por comas: now, al, rep, les, sent, charts, repos, hist, cfg. Vacío = todas. |
| `ui.screen1_orientation` | auto, portrait o landscape solo para /screen/1. |
| `ui.screen2_tabs` | Pestañas de /screen/2. |
| `ui.screen2_orientation` | Orientación de /screen/2. |
| `ui.screen3_tabs` | Pestañas de /screen/3. |
| `ui.screen3_orientation` | Orientación de /screen/3. |
| `ui.now_sort` | Orden de Ocurriendo ahora para quien no ha elegido: ecosystem, severity, age, newest, repo, event o state. |
| `ui.alerts_sort` | Orden de la pestaña Alertas para quien no ha elegido: server, severity, streak, class, age, newest, repo, origin o state. |

## Orden de las listas

La sección **Ocurriendo ahora** de la primera pestaña se ordena por ecosistema, con un encabezado por cada uno. La lista que hay sobre la sección lo cambia: ecosistema, gravedad (primero las atascadas, luego las que tienen un trabajo fallido, luego las en curso y al final las en cola), antigüedad (la que lleva más tiempo, primero), más reciente primero, repositorio, disparador (push, pull_request, schedule...) y estado (en curso antes que en cola). La elección se recuerda para cada persona: en el modo de equipo la guarda el servidor con el usuario (`GET` y `POST /api/auth/me/view`, así le acompaña a otro navegador); si no, la guarda este navegador. Mientras nadie elige, el orden es `ui.now_sort` del fichero de configuración (ecosistema si falta o es erróneo). Los botones **Desplegar todo** y **Plegar todo** junto a la lista despliegan o pliegan de golpe todos los repositorios de la sección, con cualquier orden; la elección se recuerda por persona en el mismo sitio y sobrevive a un refresco (un repositorio que abras o cierres a mano después conserva tu elección).

La lista de la pestaña **Alertas** conserva el orden que envía el monitor salvo que alguien elija otro con la lista que hay sobre ella: gravedad (crítica, error, aviso, info), la racha de fallos seguidos más larga primero, clase (una alerta de error o crítica es real y va antes de las que hay que vigilar), las más antiguas primero, las más recientes primero, repositorio, origen (el centinela que la levantó) y estado (abiertas antes que silenciadas). Se recuerda del mismo modo y, mientras nadie elige, vale `ui.alerts_sort` del fichero de configuración (`server` si falta o es erróneo).

## Tamaños probados

Una prueba de navegador abre la página en cada uno de estos tamaños, recorre todas las pestañas y falla si hay scroll lateral o un texto que sale de su caja. Las ventanas de 2400 px o más reciben una letra más grande (y las de 3200 px, aún mayor) en vez de una disposición estirada; una ventana más alta que ancha apila los paneles.

| Tamaño | Tipo |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Receta para un puesto con dos o tres pantallas

1. En el equipo que ejecuta el monitor, pon `ui.screen1_tabs` en `now,al`, `ui.screen2_tabs` en `charts,repos` y, para un monitor girado, `ui.screen2_orientation` en `portrait`.
2. Abre `http://este-equipo:8765/screen/1` en una ventana del primer monitor y `/screen/2` en el segundo; pulsa F11 para pantalla completa. Desde otro equipo, usa el modo red con su token de acceso.
3. Para una pantalla de pared que nadie toca, dale varias pestañas y pon `ui.rotate_seconds` en 20-30.

## Pantallas de pared: general, ahora y centinelas

Tres páginas para un monitor o una tele que nadie toca. No tienen menú lateral ni navegación, lo muestran todo en una sola vista con letra grande, animan lo que está vivo y hacen parpadear los fallos con suavidad. Solo leen: ningún botón cambia nada y nunca llaman a GitHub (muestran lo que el monitor ya tiene).

| Dirección | Qué muestra |
|---|---|
| `/screen/overview` | Anillo y letra de la puntuación; la flota (verdes, rojos, atascados, esperando); las últimas 24 horas y 7 días en gráficos de área; un mapa de calor de repositorios por hora; lo que lleva más tiempo en rojo; runners y minutos; los últimos eventos; la cuota de GitHub como medidor. |
| `/screen/now` | Lo que ocurre este minuto: ejecuciones en curso con progreso y duración, la cola, ejecuciones esperando aprobación, fallos recientes, fusiones y versiones publicadas, versiones pendientes y una línea en directo de las últimas dos horas. |
| `/screen/sentinels` | Una tarjeta por cada centinela (A1 a A12) con su nivel, los hallazgos abiertos, si sus fuentes se pueden leer, el último barrido y un anillo que sigue el barrido; un radar animado que marca lo que va mal y las alertas por gravedad. |

### Parámetros de la dirección

Una dirección para cada monitor. Un parámetro puede hacer una ventana más tranquila o más pequeña de lo que permiten los ajustes, nunca más ruidosa.

| Parámetro | Efecto |
|---|---|
| `?monitor=1` a `9` | El número que se muestra junto al título. |
| `?theme=dark`, `light` o `contrast` | Colores; contrast es blanco sobre negro, para una pantalla vista de lejos. |
| `?density=compact`, `normal` o `large` | Tamaño de la letra. `?scale=1.5` agranda todo (de 0,5 a 3). |
| `?refresh=10` | Segundos entre actualizaciones (de 5 a 120). |
| `?lang=de` | Idioma (en, es, de, fr, it, ja, zh, pt). |
| `?rotate=30` | La ventana pasa sola por general, ahora y centinelas cada 30 segundos (mínimo 5; 0 = sin rotación). |
| `?blink=off` | Los fallos conservan un halo fijo en lugar de parpadear. No puede activar lo que `screens.blink` mantiene apagado. |
| `?sound=on` | Un pitido corto con cada fallo nuevo, solo si `screens.sound` lo permite. Desactivado por defecto. |

### Ajustes de las pantallas de pared

| Ajuste | Qué hace |
|---|---|
| `screens.enabled` | Activa las tres páginas. Desactivado: `/screen/overview`, `/screen/now`, `/screen/sentinels` y `/api/screens/data` responden 404 (`/screen/1` a `/screen/3` son la propia página y no dependen de esto). La edición lite también sirve las pantallas de pared, con la pantalla de centinelas vacía. Desactivado por defecto. |
| `screens.default_theme` | dark (por defecto), light o contrast. |
| `screens.default_density` | compact, normal (por defecto) o large. |
| `screens.refresh_seconds` | Segundos entre actualizaciones de una ventana (10 por defecto). Las páginas leen del monitor, nunca de GitHub, así que un tiempo corto no gasta cuota. |
| `screens.rotate_seconds` | 0 (por defecto) = sin rotación; a partir de 5, una ventana pasa por las tres páginas. |
| `screens.blink` | Los fallos parpadean con suavidad (activado por defecto). |
| `screens.blink_calm_minutes` | Minutos tras los cuales un fallo que nadie atiende conserva un halo fijo en lugar de parpadear (30 por defecto; 0 = parpadea hasta que se resuelve). |
| `screens.sound` | Un pitido con cada fallo nuevo (desactivado por defecto). |
| `screens.burn_in_protection` | Desplaza todo unos píxeles cada minuto (activado por defecto). |
| `screens.night_dim` | Atenúa las pantallas entre `screens.night_dim_from_hour` (22) y `screens.night_dim_to_hour` (7); desactivado por defecto. |
| `screens.show_repo_names` | all, public (por defecto: los repositorios privados aparecen como private-1, private-2...) o none (se ocultan todos los nombres). Usa public o none en una pantalla que otras personas puedan ver. Con una lista de repositorios escrita a mano en `repos`, la visibilidad se lee con un listado de la cuenta cada `discover_refresh_seconds`; un repositorio cuya visibilidad no se pudo leer cuenta como privado. Los números (private-1...) se dan solo a los repositorios ocultos, en el orden de un HMAC del nombre con una clave de la instalación guardada en un fichero privado de la carpeta de datos, así que no dicen nada de dónde cae un repositorio entre los demás. |

### Qué muestran y qué ocultan

Los datos salen de `/api/screens/data?screen=overview` (o `now`, `sentinels`): una lista cerrada de campos construida con el último ciclo, la instantánea de los centinelas, las alertas y la puntuación. Nunca contiene un enlace, un título de commit, el nombre de un job, el nombre de una persona ni una ruta de este equipo, y los nombres de workflow de los repositorios ocultos también se ocultan. En el modo red las páginas necesitan el mismo token de acceso que el resto del monitor y la respuesta es de solo lectura.

### Cómo se comportan

- Los fallos parpadean menos de dos veces por segundo (nunca de forma estroboscópica); un fallo nuevo hace un solo destello; un fallo que nadie atiende durante `screens.blink_calm_minutes` conserva un halo fijo. Con el ajuste del sistema para reducir el movimiento, o con `?blink=off`, nada parpadea ni se mueve. Un fallo nunca se muestra solo con color: lleva un símbolo y una palabra.
- Si el monitor no responde, la página lo dice, se atenúa y reintenta a los 5, 10, 20... segundos (hasta 60).
- Una pantalla siempre encendida se protege contra el quemado: todo se desplaza unos píxeles cada minuto y la página puede atenuarse de noche.

### Montar varios monitores

1. Elige una dirección para cada monitor, por ejemplo `/screen/overview?monitor=1`, `/screen/now?monitor=2` y `/screen/sentinels?monitor=3`; o abre una sola ventana con `?rotate=20`.
2. Abre cada una en Chrome o Edge en modo quiosco: `msedge --kiosk "http://este-equipo:8765/screen/now?monitor=2" --edge-kiosk-type=fullscreen` o `chrome --kiosk "http://este-equipo:8765/screen/now?monitor=2"`; con `--app=DIRECCIÓN` en lugar de `--kiosk` la ventana no tiene barras. Sin modo quiosco, el botón discreto del pie de la página pide la pantalla completa.
3. Desde otro equipo usa el modo red: basta el token de acceso de un visor, porque estas páginas nunca escriben.

## Imágenes

La pestaña Ahora en cuatro tamaños, con datos inventados (4K, un monitor 21:9, un monitor girado, un móvil):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![girado 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![móvil 390x844](../../docs/screenshots/web_size_phone_light.png)

Las tres pantallas de pared en 4K y en un monitor girado, con datos inventados:

![General 4K 3840x2160](../../docs/screenshots/web_screen_overview_4k.png)

![General 1080x1920](../../docs/screenshots/web_screen_overview_portrait.png)

![Ahora 4K 3840x2160](../../docs/screenshots/web_screen_now_4k.png)

![Ahora 1080x1920](../../docs/screenshots/web_screen_now_portrait.png)

![Centinelas 4K 3840x2160](../../docs/screenshots/web_screen_sentinels_4k.png)

![Centinelas 1080x1920](../../docs/screenshots/web_screen_sentinels_portrait.png)
