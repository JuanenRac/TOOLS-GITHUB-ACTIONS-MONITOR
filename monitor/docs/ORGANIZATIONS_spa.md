<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ORGANIZATIONS.md) | **🇪🇸 Español** | [🇫🇷 Français](ORGANIZATIONS_fra.md) | [🇮🇹 Italiano](ORGANIZATIONS_ita.md) | [🇩🇪 Deutsch](ORGANIZATIONS_deu.md) | [🇨🇳 简体中文](ORGANIZATIONS_zho.md) | [🇯🇵 日本語](ORGANIZATIONS_jpn.md) | [🇵🇹 Português](ORGANIZATIONS_por.md)

# Organizaciones y cuentas grandes

Cómo apuntar el monitor a una organización, o a una cuenta personal con cientos de repositorios, y qué hacer cuando una lectura vuelve vacía.

## 1. El token más pequeño que funciona

El monitor solo lee. Usa el acceso de `gh` (`gh auth login`) o un token en `GH_TOKEN`, y dale lo mínimo que necesita.

| Tipo de token | Qué darle |
|---|---|
| **Clásico** (token de acceso personal) | `repo` para repositorios privados (`public_repo` basta si todo es público) y `read:org` para listar los repositorios y equipos de una organización. Opcionales: `security_events` (alertas de code scanning, panel A3), `read:project` (los tableros de Projects, panel A9). No necesita `workflow` ni ningún alcance de escritura. |
| **De grano fino** | Un solo *propietario del recurso*: crea un token por organización (o por cuenta personal). Acceso a repositorios: todos, o los seleccionados. Permisos de solo lectura: Metadata, Actions, Contents, Pull requests, Issues, Administration (rulesets y reglas de rama), Code scanning alerts, Dependabot alerts, Secret scanning alerts. Una organización puede exigir que un propietario apruebe antes el token. |
| **GitHub App** | Lee con la cuota de la App en vez de la tuya (ver `QUOTA.md`). |

Una **cuenta personal** (`github_owner` es un usuario) no necesita más que lo anterior para sus propios repositorios. Los repositorios de una organización a la que perteneces se leen con un token cuyo propietario del recurso (grano fino) o alcances (clásico) incluyan esa organización.

## 2. Inicio de sesión único (SSO) y repositorios privados

Si la organización exige SAML, un token clásico debe estar autorizado para ella: en GitHub abre *Settings > Developer settings > Personal access tokens*, elige el token y pulsa *Configure SSO > Authorize*. Un acceso hecho con `gh auth login` se autoriza en el navegador al aceptar la organización. Hasta entonces GitHub responde `403` (*Resource protected by organization SAML enforcement*) o, peor, responde `200` dejando fuera los repositorios privados (la cabecera `X-GitHub-SSO: partial-results`), lo que parece una organización con pocos repositorios.

Un token que no ve un repositorio privado recibe `404`, igual que si no existiera. Así que una respuesta vacía puede significar: SSO sin autorizar, falta un alcance o permiso, un repositorio privado que el acceso no ve, o que no hay Actions. La sección siguiente los distingue.

## 3. `--doctor` lo explica

`py -3 bin/actions_monitor.py --doctor` (también `bin/monitor_cli.py doctor`) hace tres lecturas pequeñas e informa dos líneas:

- **El acceso puede leer la cuenta u organización** (`access`): `ok` con el usuario y sus alcances; o `warn` con la causa en el detalle: `sso` (sin autorizar, o repositorios privados ocultos), `rate_limited`, `scope` (falta un permiso), `not_found` (la cuenta no existe o no se ve), `forbidden`; `fail` cuando GitHub rechaza las credenciales. Un token de grano fino no tiene alcances que listar y la línea lo dice.
- **Las lecturas por hora caben en la cuota** (`estimate`): los repositorios de la cuenta y las lecturas por hora que necesitarían los ajustes actuales, frente a las 5.000 por hora de un token personal. Es una estimación sin llamadas: el sondeo de los runs (una décima parte de los repositorios calientes, cada `refresh_seconds`; el resto cada `cold_refresh_seconds`), la Centinela (como mucho `sentinel.budget_per_hour`) y, cuando los ficheros de workflow se leen sin clones, su parte. `warn` por encima del 60 %. Para bajarla: sube `cold_refresh_seconds`, activa el modo Bajo, vigila menos repositorios (`repos`) o lee con una GitHub App.

Las mismas causas se escriben, con el repositorio, allí donde el monitor no pudo leer ficheros de workflow: el panel A13 de la Centinela los lista como *no evaluables* con el motivo, nunca como un "sin datos" mudo.

## 4. Vigilar una cuenta que no es tuya (observador sin permisos)

Cualquier token puede leer los repositorios públicos de cualquier cuenta, así que puedes vigilar una organización de código abierto con un token sin ningún alcance. Lo que un observador no obtiene, y el monitor trata como *desconocido* y nunca como *bien*: rulesets y protección de ramas, alertas de Dependabot, code scanning y secret scanning, ajustes, y las listas de runs de repositorios con Actions desactivadas. Los paneles que dependen de ello (A3, partes de A6) salen vacíos o marcados como no evaluables para esos repositorios. Nunca se escribe nada, así que no hace falta ningún permiso de escritura.

## 5. Límites conocidos

- La cuota es de 5.000 lecturas por hora para un token personal; una GitHub App instalada en una organización grande tiene más (ver `QUOTA.md`). La estimación de arriba es la forma más rápida de saber si cabes.
- El monitor lee una muestra de los últimos runs de cada repositorio. Un repositorio que lanza cientos de runs por hora se ve a través de esa muestra, no run por run.
- GitHub conserva los logs y artefactos de un run 90 días por defecto; el monitor no puede leer lo que GitHub ha borrado.
- Un token de grano fino pertenece a un solo propietario: vigilar dos organizaciones necesita dos tokens (dos cuentas del monitor, ver `ACCOUNTS.md`).
- Las organizaciones que exigen aprobar los tokens, o bloquean los clásicos, necesitan que un propietario actúe antes; ningún ajuste del monitor puede saltarse eso.
