<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | **🇪🇸 Español** | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# Vistas de colaboración y acciones opcionales

Vistas de lo que está esperando a alguien y unas pocas acciones en GitHub que siguen apagadas hasta que las permitas. Ediciones Complete y Full.

## Activarlo

Activa `teamwork.enabled` (Ajustes > Colaboración). Las vistas de ejecuciones salen de lo que el monitor ya lee; las pull requests, alertas y workflows se leen unos pocos repositorios por ciclo (`teamwork.repos_per_cycle`, `teamwork.refresh_hours`). La caja Colaboración está al final de la pestaña Colaboración del área Centinela.

## Las vistas

Esperando a una persona (aprobación de entorno, workflow de un fork, acción requerida) aparte de esperando un ejecutor. La ejecución más nueva de cada carril (workflow y rama); un rojo se puede apartar `teamwork.dismiss_days` días, solo esa ejecución, y restaurar. Pull requests abiertas agrupadas en listas para fusionar, detrás de la base, necesitan acción o no se sabe, con las actualizaciones de bots reconocidas por autor, rama o etiqueta; `teamwork.hide_workflows` oculta workflows por nombre. Repositorios con alertas de dependencias críticas o altas con la antigüedad de la más vieja, y los repositorios NO leídos, nombrados. Con `teamwork.dismissed_alerts`, quién descartó alertas de seguridad; un descarte de alguien que no está en `teamwork.dismiss_allowed` genera una alerta.

## Escribir en GitHub

No se escribe nada salvo que `github_actions.enabled` esté activado, la acción esté en `github_actions.allowed` y confirmes el plan, que muestra exactamente lo que se envía. Acciones nuevas: `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. Las vistas solo PROPONEN: actualizaciones de bots con checks en rojo, ramas atrasadas, ejecuciones demasiado tiempo en cola o corriendo (`teamwork.queued_hours`, `teamwork.stuck_hours`), las que coinciden con `teamwork.cancel_policy` y workflows desactivados por inactividad (`teamwork.inactive_workflows`). El formulario de un workflow manual lee sus entradas y las comprueba. Con `teamwork.forks_help`, datos del autor de una ejecución de fork (antigüedad de la cuenta, cambios fusionados aquí, ficheros de workflow tocados); no se da veredicto. Un despliegue se aprueba de un entorno cada vez, nombrado en la confirmación; si una ejecución espera varios, la página pregunta cuál.

## La única acción automática

`teamwork.auto_rerun` (apagado) relanza una vez los trabajos fallidos de una ejecución que no arrancó o agotó el tiempo, con las mismas comprobaciones (no hace nada con las acciones apagadas o sin `rerun_failed` permitido). Nunca lo intenta dos veces; si vuelve a fallar se genera una alerta.

## Mantener viva una programación

GitHub apaga los workflows programados de un repositorio público tras 60 días sin actividad. Con `teamwork.keep_alive_days` (0 = apagado; por ejemplo 45), un repositorio público sin ningún push durante ese tiempo y con workflows que se han ejecutado por programación aparece entre las propuestas como `enable_workflow`, con los días que quedan. Es una propuesta como las demás: no se envía nada hasta que la confirmas. GitHub no documenta que activar un workflow ya activo reinicie su cuenta, y esto no se ha probado en un repositorio real: lo seguro es un commit nuevo.

## Hooks de ejecutores propios

Con `teamwork.runner_hooks`, un hook de un ejecutor de este equipo anota el inicio y el fin de cada trabajo:

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

Para el final usa la variable ACTIONS_RUNNER_HOOK_JOB_COMPLETED con `completed`. Un ejecutor de otro equipo no está cubierto.

## API y línea de órdenes

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`.

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## Sin verificar

Las lecturas y escrituras solo se han probado con respuestas inventadas; ninguna de las acciones nuevas se ha ejecutado en un repositorio real.

## Todos los ajustes

`teamwork.enabled` `teamwork.repos_per_cycle` `teamwork.refresh_hours` `teamwork.dismiss_days` `teamwork.hide_workflows` `teamwork.bot_authors` `teamwork.bot_branches` `teamwork.bot_labels` `teamwork.dismissed_alerts` `teamwork.dismiss_allowed` `teamwork.auto_rerun` `teamwork.cancel_policy` `teamwork.queued_hours` `teamwork.stuck_hours` `teamwork.forks_help` `teamwork.inactive_workflows` `teamwork.keep_alive_days` `teamwork.runner_hooks`
