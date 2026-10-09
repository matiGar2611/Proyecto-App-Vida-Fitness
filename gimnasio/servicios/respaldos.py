"""Copias de seguridad de la base de datos.

- crear_respaldo(): copia consistente de gimnasio.db en DATA_DIR/respaldos.
- respaldo_diario_si_falta(): la usa el arranque para hacer una copia por día.
- zip_de_respaldo(): un .zip descargable con una copia al momento.
- restaurar_respaldo(): vuelve la base a una copia anterior.

Las copias usan la API de respaldo de SQLite, que es segura aunque la app
esté escribiendo en ese momento (copiar el archivo "a mano" no lo es).
"""

import io
import os
import re
import sqlite3
import tempfile
import zipfile

from .. import config, db, tiempo

PATRON = re.compile(r'^gimnasio-\d{8}-\d{6}(-previo)?\.db$')


def carpeta_respaldos():
    carpeta = config.ruta_datos('respaldos')
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _copiar_base(origen_ruta, destino_ruta):
    """Copia una base SQLite a otra de forma consistente."""
    origen = sqlite3.connect(origen_ruta, timeout=10)
    destino = sqlite3.connect(destino_ruta)
    try:
        origen.backup(destino)
    finally:
        destino.close()
        origen.close()


def crear_respaldo(sufijo=''):
    """Crea una copia ahora y devuelve su ruta. Después borra las más viejas."""
    nombre = f"gimnasio-{tiempo.ahora():%Y%m%d-%H%M%S}{sufijo}.db"
    destino = os.path.join(carpeta_respaldos(), nombre)
    _copiar_base(db.ruta_db(), destino)
    try:
        os.chmod(destino, 0o600)
    except OSError:
        pass
    rotar_respaldos()
    return destino


def listar_respaldos():
    """Copias existentes, de la más nueva a la más vieja: [{nombre, ruta, bytes}]."""
    carpeta = carpeta_respaldos()
    nombres = sorted((n for n in os.listdir(carpeta) if PATRON.match(n)), reverse=True)
    return [
        {'nombre': n, 'ruta': os.path.join(carpeta, n), 'bytes': os.path.getsize(os.path.join(carpeta, n))}
        for n in nombres
    ]


def rotar_respaldos(conservar=None):
    """Borra las copias más viejas y deja las 'conservar' más nuevas."""
    conservar = config.RESPALDOS_A_CONSERVAR if conservar is None else conservar
    for viejo in listar_respaldos()[conservar:]:
        try:
            os.remove(viejo['ruta'])
        except OSError:
            pass


def respaldo_diario_si_falta():
    """Crea una copia si todavía no hay ninguna de hoy. Devuelve la ruta o None."""
    prefijo = f"gimnasio-{tiempo.ahora():%Y%m%d}-"  # el mismo reloj con el que se nombran las copias
    if any(r['nombre'].startswith(prefijo) for r in listar_respaldos()):
        return None
    return crear_respaldo()


def zip_de_respaldo():
    """Bytes de un .zip con una copia de la base tomada en este momento."""
    with tempfile.TemporaryDirectory() as temporal:
        copia = os.path.join(temporal, 'gimnasio.db')
        _copiar_base(db.ruta_db(), copia)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(copia, 'gimnasio.db')
            zf.writestr(
                'LEEME.txt',
                f"Copia de seguridad de Vida Fitness tomada el {tiempo.ahora():%d/%m/%Y a las %H:%M}.\n"
                "Contiene datos personales de los socios: guardala en un lugar seguro.\n"
                "Para restaurarla: python -m gimnasio.restaurar gimnasio.db\n",
            )
        return buffer.getvalue()


def _es_base_valida(ruta):
    """True si el archivo es una base SQLite íntegra con todas las tablas de la app."""
    try:
        conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != 'ok':
                return False
            tablas = {f[0] for f in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return db.TABLAS_ESPERADAS.issubset(tablas)


def restaurar_respaldo(ruta):
    """Reemplaza la base actual por la de la copia indicada.

    Antes guarda una copia 'previo' de lo que había, por si hay que deshacer.
    Lanza ValueError si el archivo no es una copia válida."""
    if not os.path.isfile(ruta) or not _es_base_valida(ruta):
        raise ValueError("El archivo no es una copia de seguridad válida de la aplicación.")
    previo = crear_respaldo(sufijo='-previo')
    _copiar_base(ruta, db.ruta_db())
    return previo
