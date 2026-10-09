"""Registro de actividad: quién hizo qué y cuándo (pagos, altas, bajas, etc.).

Nunca debe romper la acción que se está registrando: si falla, solo queda en el log.
"""

import logging

from .. import db, tiempo

log = logging.getLogger(__name__)


def registrar(actor, accion, detalle=''):
    """Anota una acción. 'actor' es el nombre de quien la hizo."""
    try:
        with db.escritura() as conn:
            conn.execute(
                "INSERT INTO auditoria (fecha_hora, actor, accion, detalle) VALUES (?, ?, ?, ?)",
                (tiempo.ahora().isoformat(timespec='seconds'), actor or '(desconocido)', accion, detalle),
            )
    except Exception:
        log.exception("No se pudo registrar la actividad: %s", accion)


def ultimas(limite=200):
    """Las últimas acciones registradas, de la más nueva a la más vieja."""
    with db.lectura() as conn:
        filas = conn.execute(
            "SELECT id, fecha_hora, actor, accion, detalle FROM auditoria ORDER BY id DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [dict(f) for f in filas]
