<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SKILLS.md) | **🇪🇸 Español** | [🇫🇷 Français](SKILLS_fra.md) | [🇮🇹 Italiano](SKILLS_ita.md) | [🇩🇪 Deutsch](SKILLS_deu.md) | [🇨🇳 简体中文](SKILLS_zho.md) | [🇯🇵 日本語](SKILLS_jpn.md) | [🇵🇹 Português](SKILLS_por.md)

# Skills para IAs

El monitor incluye dos skills: guías cortas, en inglés, que dicen a una IA cómo trabajar con él. Están en la carpeta `skills/` del paquete, en la página (Ajustes, pestaña IA) y un comando las instala.

## Las dos skills

- `skills/internal`: para la IA integrada en el monitor, local (Ollama, un servidor llama.cpp, LM Studio) o externa (la API de un proveedor). Dice qué es el monitor y qué ve, qué puede leer, qué no debe hacer nunca, cómo diagnosticar un rojo, cuándo callar y cómo usar y proponer lecciones. Su núcleo (`SKILL.md`) se añade a cada prompt de esa IA, cortado a `ai.skill_max_chars`, cuando `ai.skill` está activado.
- `skills/external`: para las IA que hablan con el monitor desde fuera, en todos los sentidos: leer (`/api/ai/*`, los archivos de `ai/`), recibir avisos (el stream o el resumen cada pocos minutos), escribir (acusar recibo, lecciones, fallos, preferencias de notificación) con los permisos que correspondan, el enlace entre el monitor y una sesión, el resumen previo al push y todo el ciclo de autoaprendizaje. Cubre una IA con línea de comandos, una IA con solo HTTP o archivos, una IA con MCP y una IA con el stream.

## Qué contiene

Cada skill es un `SKILL.md` corto (el núcleo) y una carpeta `references/` que se lee solo cuando hace falta, de modo que un modelo con poco contexto pueda tomar solo el núcleo: escenarios paso a paso (un rojo real, un rojo pasajero, cuota baja, un monitor degradado, un fallo repetido, una lección nueva, sin red, varias pantallas), el ciclo de autoaprendizaje, los proveedores y sus límites, la seguridad (inyección de instrucciones desde los registros, secretos, permisos mínimos, auditoría de lo que escribe una IA) y las referencias generadas desde el código.

## No se queda nada fuera

Las referencias (`api.md`, `cli.md`, `settings.md`, `files.md`, `roles.md`, `tabs.md`) y `skills/COVERAGE.md` se GENERAN desde el código con `python tools/make_skill_refs.py`: cada endpoint con el rol mínimo que puede llamarlo, cada comando y opción, cada ajuste con su valor por defecto, cada archivo que escribe el monitor, cada rol y cada pestaña. Una prueba lee las mismas listas del código y falla si algo no se nombra en las skills, así que un endpoint, comando, ajuste o archivo nuevo no puede aparecer sin describirse a las IA (y el generador se detiene hasta que se escriba su nota).

## Instalar

Copie la skill a la carpeta de la que su herramienta de IA lee sus skills:

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## Seguridad del instalador

Escribe `github-actions-monitor-internal` o `github-actions-monitor-external` dentro de la carpeta que indique y nada más. Nunca sobrescribe un archivo que difiera del del paquete (conserva el suyo y dice cuál) y rechaza la unidad D: y las rutas de red. Una segunda ejecución no cambia nada.

## En la página y por HTTP

En Ajustes, pestaña IA, el bloque **Skills para IAs** tiene Copiar (el núcleo de la skill) y Descargar (la skill completa con sus referencias en un archivo) para cada una. `GET /api/skills` las lista y `GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` devuelve el texto; es solo lectura.

## Ajustes

`ai.skill` (activado) y `ai.skill_max_chars` (3000; 1500 para un modelo local pequeño). Registrar fallos desde fuera es `POST /api/ai/failures` y exige `lessons.allow_write` y un administrador, como escribir una lección.
