<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](STORAGE.md) | **🇪🇸 Español** | [🇫🇷 Français](STORAGE_fra.md) | [🇮🇹 Italiano](STORAGE_ita.md) | [🇩🇪 Deutsch](STORAGE_deu.md) | [🇨🇳 简体中文](STORAGE_zho.md) | [🇯🇵 日本語](STORAGE_jpn.md) | [🇵🇹 Português](STORAGE_por.md)

# Almacenamiento y retención

Dónde guarda la edición completa lo que aprende, cómo cambiarlo y qué elimina por sí sola. La edición lite guarda siempre archivos normales, no tiene base de datos ni tarea de retención y no muestra nada de esto.

## Qué se guarda

Por cada cuenta: la configuración (`actions_monitor.json`), el estado de los centinelas, el feed de eventos, lo que el feed ya anunció, las muestras de analíticas, los silencios y el aviso de actualización. Para toda la instalación: usuarios, las cuentas que pueden ver y sus sesiones (los usa el modo equipo). Las cachés de lecturas condicionales y los registros son siempre archivos normales.

## Los dos almacenamientos

|  | `file` (predeterminado) | `sqlite` |
|---|---|---|
| Dónde | `accounts/<id>/` (junto a los lanzadores si no hay `accounts/`) | `accounts/<id>/storage.sqlite3`, una base de datos por cuenta |
| Escrituras | un archivo temporal, volcado al disco y renombrado | una transacción corta, diario WAL |
| Elígelo para | una persona; archivos que puedes leer y editar | un servicio que funciona durante meses; muchos eventos |

Se elige en la configuración de la cuenta (o del monitor): `"storage": {"backend": "sqlite"}`. La configuración en sí es siempre un archivo JSON, porque es la que indica el almacenamiento. Con SQLite el feed de eventos está en la base de datos, no en `events_monitor.jsonl`. Una base de datos que no se puede abrir impide el arranque: el monitor nunca escribe su estado en otro sitio a tus espaldas.

## Decisión: un almacenamiento por cuenta (modelo A)

*Contexto.* La edición completa ejecuta un proceso por cuenta. *Decisión.* Cada proceso tiene su propio almacenamiento: sus archivos, o su base de datos `storage.sqlite3` dentro de `accounts/<id>/`. Dos procesos nunca escriben el mismo archivo, así que no hay nada que bloquear entre ellos y un problema en una cuenta no puede dañar otra. *Coste.* Una consulta entre cuentas obliga a leer varias bases de datos.

*Preparado: modelo B, una base de datos compartida.* Pon la misma ruta en el bloque `storage` de todas las cuentas (`"path": "/data/monitor.sqlite3"`). Funciona porque cada tabla lleva la cuenta, WAL deja leer a la página mientras escriben los centinelas, las transacciones son cortas y se espera hasta 5 segundos si la base está ocupada. Está probado (dos procesos haciendo su ciclo a la vez; una página que responde por HTTP mientras escriben) pero no es el valor predeterminado: es más frágil que A y solo compensa si necesitas SQL entre cuentas.

## Qué está garantizado

- Una escritura es atómica: quien lee ve el valor anterior o el nuevo. Un proceso cortado a medias (`kill -9`) deja el valor anterior; con SQLite el siguiente arranque se recupera solo.
- El esquema tiene versión (`schema_version`). Cada migración se ejecuta en una sola transacción junto con el cambio de versión, de modo que una interrumpida deja la base como estaba y se repite en el siguiente arranque. Una base escrita por una versión más nueva se rechaza, nunca se degrada.
- Un elemento dañado o ausente se lee como vacío: el monitor arranca con lo que haya en el disco.

## Mover datos y copias de seguridad

```
python tools/migrate_storage.py --from file --to sqlite              # simulación: muestra lo que copiaría
python tools/migrate_storage.py --from file --to sqlite --apply      # copia y luego compara cada elemento y cada evento
python tools/backup_storage.py backup backup.zip --backend sqlite    # un .zip con manifiesto y SHA-256
python tools/backup_storage.py verify backup.zip
python tools/backup_storage.py restore backup.zip --backend file     # en un almacenamiento vacío (--force sobre cuentas existentes)
```

La migración nunca modifica ni borra tus archivos, continúa tras una interrupción (una cuenta se copia entera o no se copia) y termina con error si los dos lados difieren; solo entonces cambia el almacenamiento y reinicia. Una copia hecha desde archivos se restaura en SQLite y al revés. `--db FILE` elige la base compartida del modelo B; `--flat` es la instalación sin `accounts/`. `--doctor` comprueba la base de datos (existe, integridad, esquema) sin modificarla.

## Retención

Un monitor que funciona durante meses crecería sin techo, así que una pasada corta al final de una actualización (cada `retention.interval_hours`, 24 por defecto) elimina lo antiguo:

| Ajuste | Predeterminado | Significado |
|---|---|---|
| `retention.enabled` | activado | el interruptor |
| `retention.events_days` | 90 | se eliminan los eventos más antiguos que esto |
| `retention.analytics_days` | 180 | se eliminan los días del histórico de analíticas más antiguos que esto |
| `retention.mode` | `delete` | `archive` escribe antes los eventos antiguos en un `.gz` en `events/archive/` |
| `retention.events_max_kb` | 512 | tope de tamaño del archivo del feed con el almacenamiento en archivos (como siempre) |
| `retention.warn_events_mb` | 20 | `--doctor` avisa por encima de este tamaño |

La purga solo toca eventos y días de analíticas más antiguos que su límite; nunca toca la configuración, el estado de los centinelas, los silencios ni un evento sin hora. Cada pasada deja una línea en el documento de auditoría (cuándo, cuántos eventos eliminados y conservados, el archivo, cuántos días de analíticas, el error si lo hubo). `--doctor` avisa del tamaño de los eventos y, en un monitor que funciona como servicio (modo red, sin navegador, un contenedor o `MONITOR_SERVICE=1`), cuando su configuración no tiene bloque `retention`. Haz una copia antes de acortar los límites.
