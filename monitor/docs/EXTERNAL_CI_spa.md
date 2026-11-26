<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTERNAL_CI.md) | **🇪🇸 Español** | [🇫🇷 Français](EXTERNAL_CI_fra.md) | [🇮🇹 Italiano](EXTERNAL_CI_ita.md) | [🇩🇪 Deutsch](EXTERNAL_CI_deu.md) | [🇨🇳 简体中文](EXTERNAL_CI_zho.md) | [🇯🇵 日本語](EXTERNAL_CI_jpn.md) | [🇵🇹 Português](EXTERNAL_CI_por.md)

# Fuentes de CI externas (solo lectura)

Un repositorio espejado en GitHub puede compilarse en otro sitio. El monitor lee Buildbot, GitLab CI, Jenkins y Azure Pipelines y muestra sus fallos como los de Actions. Solo lee (GET); nunca lanza, cancela ni escribe nada allí. Ediciones Complete y Full; apagado de fábrica.

## Configuración

Active `external_ci.enabled` y escriba una línea por fuente en `external_ci.sources` (Ajustes > CI externo). `repo` es el nombre con el que se muestra el resultado.

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## Rojo, correcto o degradado

Decide la última build terminada de cada builder, pipeline o job en su rama, como en Actions: las peticiones de cambios, los estados cancelados, omitidos y desconocidos nunca deciden. Un servicio que no responde, responde otra cosa o no tiene un builder queda **degradado**, nunca en rojo; los fallos vistos antes se mantienen, marcados como antiguos. Los fallos generan ci.external.red (nivel `external_ci.alert.level`) y se cuentan, notifican y silencian como un rojo de Actions; ci.external.degraded es informativo. Silenciarlos nunca silencia un aviso de seguridad. Cada fuente se lee como mucho cada `external_ci.refresh_seconds` (300 o más) y con menos frecuencia tras `external_ci.breaker.failures` fallos.

## Seguridad

La dirección se comprueba al conectar: este equipo, redes privadas y metadatos de la nube se rechazan salvo con `external_ci.allow_private_targets`. No se siguen redirecciones ni enlaces de las respuestas. Las respuestas se limitan con `external_ci.max_bytes` y `external_ci.timeout_s`. Ninguna credencial se escribe en la configuración: `token_env` solo lleva el NOMBRE de una variable de entorno (GitLab: token de lectura; Jenkins: `usuario:token`; Azure: token personal con lectura de Build) y no se envía sin TLS a una dirección pública. No consume cuota de GitHub. En modo sin conexión (`airgapped`) no se lee nada; `doctor --egress` lista los hosts.

## Logs de una build fallida

Apagado de fábrica (`external_ci.logs.enabled`). Solo se pide el final, limitado por `external_ci.logs.max_kb` y `external_ci.logs.tail_lines`, sin secuencias de terminal ni caracteres de control, depurado, en memoria durante `external_ci.logs.keep_hours`. Es texto no fiable y nunca se entrega a una IA como instrucción. La depuración no puede reconocer todos los secretos.

## Prueba, estado y consola

En Ajustes > CI externo está **Probar conexión**: una lectura sin guardar nada (`POST /api/external-ci/probe`). La pestaña de CI de los centinelas muestra cada fuente; `GET /api/external-ci/status` da lo mismo y `GET /api/external-ci/log` un log. Consola: `external-ci list`, `external-ci status` (código 1 si hay rojo o degradado) y `external-ci probe --source "LÍNEA"`.

## Aún sin verificar

Los cuatro adaptadores solo se han probado contra servidores falsos (`tools/extci_fake_servers.py`). Jenkins y Azure Pipelines llevan la etiqueta **experimental** (`external_ci.experimental`) y necesitan `external_ci.jenkins.enabled` / `external_ci.azure.enabled`. Para escribir otro adaptador: una función `(reader, source, cfg) -> (runs, missing)` en `integrations/external_ci/extci_adapters.py` que lea solo con `reader`.
