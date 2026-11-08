# Política de seguridad

## Notificar una vulnerabilidad

Informa de los problemas de seguridad en privado a `electrohobby3d@gmail.com` (o con un aviso de seguridad privado de este repositorio) y no abras un issue público.
Los informes útiles son: una forma de llegar a la página web local desde otra máquina, una forma de hacer que el monitor escriba fuera de su propia carpeta, una forma de leer un token
o un fichero privado a través de la página o del endpoint de métricas, o una inyección a través del nombre de un repositorio, de un workflow o de una línea de registro.

## Puntos de diseño en los que puedes confiar
- La página web y el endpoint opcional de métricas escuchan solo en `127.0.0.1` y rechazan las peticiones cuyo `Host` u `Origin` no sea local. El modo red opcional (apagado por defecto) añade un token de acceso en cada petición, una lista de nombres de host aceptados y un aviso persistente.
- Por defecto el monitor no guarda ni muestra tokens; llama a tu propio cliente `gh` autenticado. El token opcional que guarda el monitor vive en el almacén seguro del sistema y nunca se escribe en un ajuste, un registro ni una respuesta.
- Todo lo que escribe en GitHub o ejecuta un programa está apagado por defecto, cada acción se confirma por separado con un token de un solo uso, y el asistente de IA no puede iniciar ninguna.
- La página de configuración solo escribe una lista fija de claves, validadas, tras guardar una copia de seguridad.
