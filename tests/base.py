"""Base común de los tests: cada test trabaja con una carpeta de datos temporal."""

import contextlib
import io
import logging
import os
import shutil
import tempfile
import unittest
from datetime import date
from unittest import mock

from gimnasio import config, db, seguridad, tiempo


class BaseConDatos(unittest.TestCase):
    """Crea una base vacía y aislada para cada test."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp(prefix='vida-fitness-test-')
        self.addCleanup(shutil.rmtree, self.carpeta, ignore_errors=True)

        patcher = mock.patch.object(config, 'DATA_DIR', self.carpeta)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Iteraciones bajas: los tests no tienen que esperar el hash lento real.
        patcher = mock.patch.object(seguridad, 'PBKDF2_ITERACIONES', 1000)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Sin ruido en la consola durante los tests (avisos, banners, logs).
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        salida = contextlib.redirect_stdout(io.StringIO())
        salida.__enter__()
        self.addCleanup(salida.__exit__, None, None, None)

        seguridad._intentos_fallidos.clear()
        seguridad._hash_de_relleno.cache_clear()
        self.addCleanup(seguridad._hash_de_relleno.cache_clear)

        # Que las variables de entorno de quien corre los tests no interfieran.
        entorno = mock.patch.dict(os.environ, {}, clear=False)
        entorno.start()
        self.addCleanup(entorno.stop)
        for variable in ('ADMIN_PASSWORD', 'STORAGE_SECRET'):
            os.environ.pop(variable, None)

        db.inicializar()

    def fijar_hoy(self, anio, mes, dia):
        """Hace que toda la app crea que hoy es esa fecha."""
        patcher = mock.patch.object(tiempo, 'hoy', return_value=date(anio, mes, dia))
        patcher.start()
        self.addCleanup(patcher.stop)

    def nuevo_cliente(self, dni='12345678', nombre='Ana Pérez', plan='Todos los días',
                      nacimiento='1990-05-10'):
        """Atajo para dar de alta un cliente de prueba."""
        from gimnasio.datos import clientes
        self.assertTrue(clientes.agregar_cliente(dni, nombre, '2615551234', plan, nacimiento))
        return dni


def escribir_archivo(ruta, contenido):
    """Escribe texto (str) o bytes en un archivo y lo cierra."""
    modo = 'wb' if isinstance(contenido, bytes) else 'w'
    with open(ruta, modo) as archivo:
        archivo.write(contenido)


def leer_bytes(ruta):
    with open(ruta, 'rb') as archivo:
        return archivo.read()
