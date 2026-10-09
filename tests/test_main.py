"""Prueba del arranque completo: ejecuta main.py con el NiceGUI de mentira."""

import os
import runpy
import unittest
from unittest import mock

from tests import stub_nicegui as stub

stub.instalar()

from gimnasio.datos import usuarios  # noqa: E402
from gimnasio.servicios import respaldos  # noqa: E402
from tests.base import BaseConDatos  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMain(BaseConDatos):
    def arrancar(self, **entorno):
        stub.reiniciar()
        stub.app.al_iniciar.clear()
        with mock.patch.dict(os.environ, entorno):
            runpy.run_path(os.path.join(RAIZ, 'main.py'), run_name='__main__')

    def test_arranque_completo(self):
        self.arrancar(ADMIN_PASSWORD='ClaveSegura99', PORT='9000')
        self.assertIsNotNone(usuarios.obtener_usuario('admin'))               # cuenta del dueño creada
        self.assertTrue(os.path.exists(os.path.join(self.carpeta, 'gimnasio.db')))  # base en DATA_DIR
        self.assertEqual(len(stub.app.al_iniciar), 1)                         # respaldos automáticos agendados
        self.assertIn('/', stub.PAGINAS)                                      # páginas registradas

        primera, segunda = stub.LLAMADAS_A_RUN
        self.assertEqual(primera['title'], 'Gimnasio Vida Fitness')
        self.assertFalse(primera['reload'])
        self.assertGreaterEqual(len(primera['storage_secret']), 32)
        self.assertEqual((segunda['host'], segunda['port']), ('0.0.0.0', 9000))

    def test_puerto_invalido_usa_8080(self):
        self.arrancar(ADMIN_PASSWORD='ClaveSegura99', PORT='no-es-un-numero')
        self.assertEqual(stub.LLAMADAS_A_RUN[1]['port'], 8080)

    def test_sin_puerto_usa_8080(self):
        with mock.patch.dict(os.environ):
            os.environ.pop('PORT', None)
            self.arrancar(ADMIN_PASSWORD='ClaveSegura99')
        self.assertEqual(stub.LLAMADAS_A_RUN[1]['port'], 8080)

    def test_la_tarea_de_respaldos_funciona_al_iniciar(self):
        import asyncio
        self.arrancar(ADMIN_PASSWORD='ClaveSegura99')

        async def iniciar():
            await stub.app.al_iniciar[0]()
            for _ in range(50):
                await asyncio.sleep(0.02)
                if respaldos.listar_respaldos():
                    break

        asyncio.run(iniciar())
        self.assertEqual(len(respaldos.listar_respaldos()), 1)


if __name__ == '__main__':
    unittest.main()
