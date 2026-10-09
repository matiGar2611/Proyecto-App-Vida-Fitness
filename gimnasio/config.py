"""Configuración central de la aplicación.

Acá viven las constantes y los valores que se pueden ajustar por
variables de entorno. No importa NiceGUI, así que se puede usar (y
probar) sin levantar la interfaz.

Variables de entorno:
    DATA_DIR        carpeta donde se guardan todos los datos (en Render,
                    el punto de montaje del disco persistente, ej. /data).
    ADMIN_PASSWORD  contraseña inicial de la cuenta 'admin'.
    STORAGE_SECRET  clave que firma las sesiones del navegador.
    PORT            puerto del servidor.
"""

import os

# Carpeta de datos. Se lee al arrancar; los tests la reemplazan por una temporal.
DATA_DIR = os.environ.get('DATA_DIR', '.')
NOMBRE_DB = 'gimnasio.db'

ROLES = ['dueño', 'profe']  # el rol 'cliente' no vive en la base de usuarios: se entra solo con el DNI
PLANES = ['2 veces por semana', '3 veces por semana', 'Todos los días']

PRECIOS_POR_DEFECTO = {
    "2 veces por semana": 15000,
    "3 veces por semana": 18000,
    "Todos los días": 22000,
}

# Número de WhatsApp del gimnasio para el botón de consultas del cliente.
# Formato: código de país + número, SIN el "+", sin espacios ni guiones.
# Ejemplo Argentina, Mendoza, celular 261 555-1234 -> "5492615551234"
NUMERO_WHATSAPP_GIMNASIO = "5492634847749"

# Encuesta anónima de satisfacción / propuestas de mejora.
LINK_ENCUESTA = "https://qr-feedback-collector.web.app?location=1774472795678"

# Todas las fechas de la app se calculan en esta zona horaria (Render corre en UTC).
ZONA_HORARIA = 'America/Argentina/Buenos_Aires'

INFO_IMPORTANTE_POR_DEFECTO = """
- El gimnasio abre de lunes a sábado de 7:00 a 22:00 hs.
- Traé una toalla propia para usar las máquinas.
- Avisá con anticipación si vas a dejar de asistir, para no acumular
  atraso en el vencimiento.
- Cualquier consulta sobre tu cuota, hablá con recepción.
""".strip()

# Seguridad
MIN_PASSWORD_PERSONAL = 8   # dueño y profes
MIN_PASSWORD_CLIENTE = 6
MAX_INTENTOS_LOGIN = 5
SEGUNDOS_BLOQUEO_LOGIN = 300

# Respaldos automáticos: cuántos se conservan en DATA_DIR/respaldos
RESPALDOS_A_CONSERVAR = 14

MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def ruta_datos(nombre):
    """Ruta completa de un archivo dentro de la carpeta de datos (la crea si no existe)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, nombre)
