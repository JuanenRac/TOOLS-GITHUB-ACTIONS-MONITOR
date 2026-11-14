# Contribuir a GitHub Actions Monitor

## Pila tecnológica
- **Lenguaje**: Python 3.11 o superior; el núcleo no necesita paquetes (la vista de terminal, `bin/tui.py`, usa Rich, que es opcional; las pruebas omiten lo que lo necesita si falta).
- **Interfaz**: una página web local (`monitor/assets/static/actions_monitor.html`) servida en `127.0.0.1`, más herramientas de línea de comandos.
- **Fuente de datos**: el cliente oficial de línea de comandos de GitHub, `gh` (llamadas de solo lectura por defecto).

## Pautas
1. **Primero las pruebas**: `python -m unittest discover -s monitor/tests` debe pasar antes de un pull request. Sin conexión: las pruebas nunca llaman a GitHub. Para probar los servicios reales a mano, usa `python tools/manual_check_live.py`.
2. **Ocho idiomas**: todo texto que lea un usuario vive en `monitor/assets/locales/<lang>.json` para en, es, de, fr, it, ja, zh y pt (portugués europeo). Una clave nueva va a los ocho ficheros; las pruebas comprueban que tengan las mismas claves.
3. **Sin secretos**: por defecto el monitor no guarda ningún token (se lo pide a `gh`); el único token opcional vive solo en el almacén seguro del sistema (`secretstore.py`). No añadas código que lea, imprima, registre o escriba credenciales en ningún otro sitio, y no subas nunca un `actions_monitor.json` real.
4. **Seguro por defecto**: todo lo que escribe en GitHub, ejecuta un programa, abre un puerto de red o envía datos fuera está apagado por defecto, tiene su propio interruptor en Ajustes > Avanzado, pide una confirmación propia y escucha en `127.0.0.1` salvo que el modo red esté activo. Una función así trae pruebas que demuestran que se niega sin el interruptor, sin la confirmación y sin el token, y que nada se filtra a un registro.
5. **Pasos pequeños**: un cambio por pull request, con la línea correspondiente en `CHANGELOG.md`.
6. **Imágenes**: edita `docs/architecture.json` o `docs/structure.json` y ejecuta `python tools/make_architecture.py` / `python tools/make_structure.py`; nunca edites el SVG a mano.
7. **Registro de cambios en ocho idiomas**: cada entrada nueva de `monitor/CHANGELOG.md` lleva su traducción en `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` (mismas versiones y secciones; una entrada aún sin traducir conserva el texto en inglés bajo un aviso traducido). `python tools/make_help_index.py --check` y la puerta de la versión fallan si falta una versión en una traducción.

## Actualizar un panel de estado tras cada versión

`.github/workflows/dashboard-dispatch.yml` se ejecuta cuando el workflow `CI` termina en verde en `main` (solo eventos push). Si el responsable define el secreto opcional del repositorio `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, pide a un repositorio de panel que actualice su tabla de versiones; sin el secreto termina en silencio, no tiene permisos y nunca cambia ni retrasa el CI. La versión de `electro-hobby-3d.project.json` debe ser igual a `tool_version.py` en cada versión; una prueba lo comprueba.

- Lista de comprobación de la ayuda: la ayuda de Ajustes (`cfg.h.<clave>`) de cada ajuste nuevo, la ayuda de la pestaña que cambió, las guías de `monitor/docs/`, los ocho idiomas, el índice de ayuda (`python tools/make_help_index.py`) y el registro de cambios.
