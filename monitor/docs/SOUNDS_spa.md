<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SOUNDS.md) | **🇪🇸 Español** | [🇫🇷 Français](SOUNDS_fra.md) | [🇮🇹 Italiano](SOUNDS_ita.md) | [🇩🇪 Deutsch](SOUNDS_deu.md) | [🇨🇳 简体中文](SOUNDS_zho.md) | [🇯🇵 日本語](SOUNDS_jpn.md) | [🇵🇹 Português](SOUNDS_por.md)

# Sonidos

La página hace sus propios sonidos con la API Web Audio, uno por cada tipo de evento, para distinguir de oído qué ha pasado sin mirar. No hay ficheros de audio: los tonos se generan en el navegador, sin conexión, y no se envía nada a ninguna parte. Cada sonido tiene además su aviso visual (los recuadros, las pestañas, las etiquetas); el sonido nunca lo sustituye.

| Tipo | Cuándo suena | El sonido |
|---|---|---|
| Rojo | Un workflow que no estaba en rojo pasa a rojo (un fallo nuevo). | Dos tonos ascendentes, el clásico "bing bing". |
| Seguridad o grave | Una alerta nueva del centinela de seguridad, una alerta grave (error o crítica) del centinela de colaboración o una cuenta que se ha quedado ciega. | Tres pulsos graves. |
| Atascado | Una compilación atascada, una cola fantasma o un problema con los runners. | Un deslizamiento largo descendente. |
| Puntuación | Baja la puntuación de la flota (`score.dropped`). | Tres notas descendentes. |
| Conexión | Se pierde la conexión con GitHub o la de esta página con el monitor. | Dos notas graves y largas. |
| Aviso | Una alerta nueva de nivel aviso (una firma pendiente, una incidencia antigua, una pull request que espera). | Dos tonos medios iguales. |
| Resuelto | Un workflow en rojo vuelve a verde o desaparece una alerta grave. | Tres notas ascendentes. |
| Informe | Uno de los informes opcionales muestra un hallazgo que no estaba antes. | Dos campanadas suaves, aguda y luego más grave. |
| Lección | Las lecciones de los fallos muestran una categoría nueva, o una que empieza a repetirse o a aplicarse. | Tres notas agudas rápidas. |
| Noticia | Una alerta nueva de nivel informativo (la release del original de un fork, por ejemplo). | Un pitido suave. |
| De nuevo en línea | Vuelve la conexión con GitHub, o de esta página con el monitor, tras una caída. | Cuatro notas ascendentes. |

## Por qué un navegador puede quedarse en silencio y qué hace la página

- Un navegador deja sonar a una página solo después de que hayas hecho clic, tocado o pulsado una tecla en ella. Hasta entonces la barra muestra el aviso "Sonido bloqueado por el navegador: haz clic aquí para activarlo". El primer clic en cualquier sitio lo desbloquea.
- Lo que ocurrió mientras el sonido estaba bloqueado se guarda (como máximo diez minutos) y suena en la primera ocasión: el clic, la página que vuelve al primer plano o la siguiente comprobación, cada dos segundos. No se pierde nada entre dos lecturas; lo que tiene más de diez minutos es una noticia vieja y no se anuncia.
- La primera lectura de la página solo recuerda lo que ya hay; una recarga en pocas horas también lo recuerda, así que un fallo que llegó con la página cerrada es nuevo.
- Una pestaña en segundo plano conserva su sonido mientras el navegador mantenga despierta la página; algunos navegadores pausan las pestañas ocultas tras un rato. Lo mejor es dejar las pantallas de pared y la página en una ventana visible.

## Sin saturar

- Un tipo que acaba de sonar espera `sound.cooldown_seconds` (30 s por defecto) antes de volver a sonar.
- Varios tipos en una misma lectura hacen una sola ráfaga: como máximo tres patrones, el más grave primero; el resto espera a la ráfaga siguiente. Dos ráfagas nunca se pisan.
- Una alerta silenciada (pestaña Alertas) nunca suena.

## La biblioteca de sonidos

Además de los once sonidos que cada tipo de evento siempre ha tenido, el monitor lleva una biblioteca de 54 sonidos (65 en total) que puedes asignar a cualquier tipo de evento. Se fabrican en el navegador (y, para el pitido de este equipo, con las mismas notas), así que no hay ficheros de audio que descargar. Los sonidos de los tipos son los once primeros; el resto se pueden asignar libremente: `bell`, `chime`, `ding_dong`, `doorbell`, `ding`, `ping_high`, `ping_low`, `tick_soft`, `tock_soft`, `double_tick`, `tick_tock`, `knock`, `knock_three`, `blip`, `bloop`, `bubble`, `drop`, `droplet`, `arpeggio_up`, `arpeggio_down`, `minor_up`, `minor_down`, `fanfare`, `level_up`, `coin`, `harp_up`, `harp_down`, `marimba`, `xylophone`, `pluck`, `cascade`, `sparkle`, `ascend`, `descend`, `notify_a`, `notify_b`, `notify_c`, `sweep_up`, `sweep_down`, `whistle_up`, `whistle_down`, `zap`, `laser`, `radar`, `sonar`, `beacon`, `heartbeat`, `alarm_fast`, `siren`, `klaxon`, `buzzer`, `gong`, `phone`, `cuckoo`.

Para dar a un tipo otro sonido escribe pares `tipo=sonido` separados por comas en `sound.voices`, por ejemplo `new_red=coin,warning=drop`. Los tipos son `new_red`, `sentinel`, `stuck`, `score_drop`, `connection_lost`, `warning`, `resolved`, `report`, `lesson`, `info`, `live_recovered`. Un nombre que no esté en la biblioteca se ignora y el tipo conserva su propio sonido. Las pantallas de pared pueden añadir su propia lista en `screens.sound_voices` y su propio volumen en `screens.sound_volume`. Ningún sonido dura más de un segundo y todos son distintos entre sí.

Dos fondos opcionales, ambos apagados por defecto: `sound.ambient` (dos notas graves muy suaves, tranquilas mientras nada está en rojo y más ásperas mientras algo lo está) y `sound.tick` (un chasquido seco muy corto cada `sound.tick_seconds`, para que se oiga una pantalla congelada). Los dos obedecen al chip de silencio, al interruptor principal y al horario silencioso.

## Ajustes (Ajustes, Sonido)

Todos están en el fichero de configuración y en la pestaña Ajustes; el volumen, el tema y los interruptores se aplican al instante.

| Ajuste | Qué hace |
|---|---|
| `sound.enabled` | Interruptor general de todos los sonidos de la página. |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info`, `sound.on_live_recovered` | Un interruptor por tipo (todos activados por defecto). |
| `sound.theme` | `classic` (tonos claros) o `soft` (tonos más graves, redondos y lentos). Cada tipo conserva su ritmo en ambos. |
| `sound.volume` | De 1 a 100, moderado por defecto. |
| `sound.cooldown_seconds` | Pausa entre dos sonidos del mismo tipo. |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | Horario silencioso (desactivado por defecto): entre las dos horas de este ordenador no suena nada; puede cruzar la medianoche. |
| `sound.server_beep` | Apagado por defecto. El propio monitor suena en este equipo cuando no hay ninguna página abierta o el navegador bloquea el sonido: un patrón para cada tipo de evento de la tabla anterior (tonos de Windows, sonidos del sistema de macOS, eventos de canberra en Linux), con los mismos interruptores y horario silencioso que la página, en una ráfaga de como máximo tres tipos a la vez; solo local. |
| `sound.voices` | Da a un tipo de evento otro sonido de la biblioteca (pares `tipo=sonido` separados por comas). Vacío por defecto. |
| `sound.ambient`, `sound.ambient_volume` | Sonido de ambiente (apagado por defecto) y su volumen, de 1 a 50. |
| `sound.tick`, `sound.tick_seconds` | Tic de reloj (apagado por defecto) y los segundos entre tics, de 1 a 60. |
| `screens.sound_voices`, `screens.sound_volume` | Lo mismo que `sound.voices`, solo para las pantallas de pared, y su propio volumen (0 = el de `sound.volume`). |

## Probar cada sonido

En Ajustes, Interfaz, el botón "Probar sonido" reproduce el bing bing clásico y un botón por tipo reproduce ese tipo con el volumen y el tema de los ajustes. La etiqueta "Sonido" de la barra inferior silencia todo en este navegador.

## Pantallas de pared

Las pantallas de pared (`/screen/...`) usan los mismos sonidos, con el mismo tema, volumen, interruptores y horario silencioso. Están desactivadas por defecto: `screens.sound` debe estar activado y la ventana necesita `?sound=on`. Una pantalla que nadie toca no puede recibir el clic que pide el navegador: arranca el navegador de la pantalla con su opción de "permitir audio sin gesto" (en Chromium, `--autoplay-policy=no-user-gesture-required`) o haz clic una vez en la ventana.

## Dónde se guarda

La etiqueta de silencio la recuerda cada navegador; lo que la página sabe de su última lectura también se guarda en el navegador. No se envía nada de los sonidos a ningún servidor.
