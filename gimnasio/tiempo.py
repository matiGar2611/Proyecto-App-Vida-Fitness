"""Fechas, horas y formatos de la aplicación.

TODA la app obtiene "hoy" desde acá (hora de Argentina), nunca con
date.today() directo: Render corre en UTC y, pasadas las 21:00 de
Argentina, el servidor ya cree que es el día siguiente.
"""

from datetime import datetime, timedelta, timezone
from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _zona():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(config.ZONA_HORARIA)
    except Exception:
        # Sin base de zonas horarias (ej. Windows sin 'tzdata'): Argentina es UTC-3 todo el año.
        return timezone(timedelta(hours=-3))


def ahora():
    """Fecha y hora actuales en Argentina."""
    return datetime.now(_zona())


def hoy():
    """Fecha de hoy en Argentina."""
    return ahora().date()


def parsear_fecha(texto):
    """Convierte un texto 'AAAA-MM-DD' a date. Devuelve None si viene vacío o mal formado."""
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def formatear_fecha(fecha_texto):
    """'AAAA-MM-DD' -> 'DD/MM/AAAA' (formato argentino) para mostrar en pantalla."""
    fecha = parsear_fecha(fecha_texto)
    return fecha.strftime("%d/%m/%Y") if fecha else "(sin fecha)"


def formatear_moneda(monto):
    """Da formato de moneda: '$' adelante y punto como separador de miles."""
    return "$" + f"{monto:,.0f}".replace(",", ".")
