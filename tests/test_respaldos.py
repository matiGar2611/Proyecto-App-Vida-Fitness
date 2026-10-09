import io
import os
import sqlite3
import unittest
import zipfile

from gimnasio import config, db
from gimnasio.datos import clientes, usuarios
from gimnasio.servicios import respaldos
from tests.base import BaseConDatos, escribir_archivo


def contar_clientes(ruta):
    conn = sqlite3.connect(ruta)
    try:
        return conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    finally:
        conn.close()


class TestRespaldos(BaseConDatos):
    def setUp(self):
        super().setUp()
        self.fijar_hoy(2026, 10, 8)
        self.nuevo_cliente('11111111')

    def test_crear_respaldo_tiene_los_datos(self):
        ruta = respaldos.crear_respaldo()
        self.assertTrue(os.path.isfile(ruta))
        self.assertEqual(contar_clientes(ruta), 1)
        if os.name != 'nt':  # Windows no maneja permisos tipo Linux
            self.assertEqual(oct(os.stat(ruta).st_mode)[-3:], '600')

    def test_el_respaldo_es_una_foto_del_momento(self):
        ruta = respaldos.crear_respaldo()
        self.nuevo_cliente('22222222')
        self.assertEqual(contar_clientes(ruta), 1)
        self.assertEqual(len(clientes.cargar_clientes()), 2)

    def test_listar_del_mas_nuevo_al_mas_viejo(self):
        from unittest import mock
        from datetime import datetime, timezone
        for segundo in (1, 2, 3):
            with mock.patch('gimnasio.tiempo.ahora', return_value=datetime(2026, 10, 8, 10, 0, segundo, tzinfo=timezone.utc)):
                respaldos.crear_respaldo()
        nombres = [r['nombre'] for r in respaldos.listar_respaldos()]
        self.assertEqual(nombres, sorted(nombres, reverse=True))
        self.assertEqual(len(nombres), 3)

    def test_rotacion_conserva_solo_los_ultimos(self):
        from unittest import mock
        from datetime import datetime, timezone
        for segundo in range(1, 8):
            with mock.patch('gimnasio.tiempo.ahora', return_value=datetime(2026, 10, 8, 10, 0, segundo, tzinfo=timezone.utc)):
                respaldos.crear_respaldo()
        respaldos.rotar_respaldos(conservar=3)
        nombres = [r['nombre'] for r in respaldos.listar_respaldos()]
        self.assertEqual(len(nombres), 3)
        self.assertTrue(nombres[0].endswith('100007.db'))  # quedan los más nuevos

    def test_rotacion_automatica_segun_configuracion(self):
        from unittest import mock
        from datetime import datetime, timezone
        with mock.patch.object(config, 'RESPALDOS_A_CONSERVAR', 2):
            for segundo in range(1, 5):
                with mock.patch('gimnasio.tiempo.ahora', return_value=datetime(2026, 10, 8, 10, 0, segundo, tzinfo=timezone.utc)):
                    respaldos.crear_respaldo()
        self.assertEqual(len(respaldos.listar_respaldos()), 2)

    def test_no_toca_archivos_ajenos(self):
        ajeno = os.path.join(respaldos.carpeta_respaldos(), 'notas.txt')
        escribir_archivo(ajeno, 'hola')
        respaldos.crear_respaldo()
        respaldos.rotar_respaldos(conservar=0)
        self.assertTrue(os.path.exists(ajeno))
        self.assertEqual(respaldos.listar_respaldos(), [])

    def test_diario_solo_si_falta(self):
        from datetime import datetime, timezone
        from unittest import mock

        def a_las(dia, hora):
            return mock.patch('gimnasio.tiempo.ahora',
                              return_value=datetime(2026, 10, dia, hora, 0, 0, tzinfo=timezone.utc))

        with a_las(8, 9):
            self.assertIsNotNone(respaldos.respaldo_diario_si_falta())   # el primero del día se crea
        with a_las(8, 20):
            self.assertIsNone(respaldos.respaldo_diario_si_falta())      # el mismo día, no se repite
        self.assertEqual(len(respaldos.listar_respaldos()), 1)
        with a_las(9, 1):
            self.assertIsNotNone(respaldos.respaldo_diario_si_falta())   # al día siguiente, otra copia
        self.assertEqual(len(respaldos.listar_respaldos()), 2)

    def test_diario_sin_fijar_el_reloj_tampoco_depende_del_dia(self):
        self.assertIsNotNone(respaldos.respaldo_diario_si_falta())
        self.assertIsNone(respaldos.respaldo_diario_si_falta())

    def test_zip_con_la_base_y_el_leeme(self):
        datos = respaldos.zip_de_respaldo()
        with zipfile.ZipFile(io.BytesIO(datos)) as zf:
            self.assertEqual(sorted(zf.namelist()), ['LEEME.txt', 'gimnasio.db'])
            destino = os.path.join(self.carpeta, 'sacada.db')
            escribir_archivo(destino, zf.read('gimnasio.db'))
        self.assertEqual(contar_clientes(destino), 1)

    def test_restaurar(self):
        ruta = respaldos.crear_respaldo()
        self.nuevo_cliente('22222222')
        self.nuevo_cliente('33333333')
        self.assertEqual(len(clientes.cargar_clientes()), 3)
        previo = respaldos.restaurar_respaldo(ruta)
        self.assertEqual(len(clientes.cargar_clientes()), 1)
        self.assertEqual(contar_clientes(previo), 3)  # lo anterior queda a salvo
        self.assertTrue(os.path.basename(previo).endswith('-previo.db'))

    def test_restaurar_rechaza_archivos_invalidos(self):
        basura = os.path.join(self.carpeta, 'basura.db')
        escribir_archivo(basura, b'esto no es una base de datos')
        with self.assertRaises(ValueError):
            respaldos.restaurar_respaldo(basura)
        with self.assertRaises(ValueError):
            respaldos.restaurar_respaldo(os.path.join(self.carpeta, 'no-existe.db'))
        ajena = os.path.join(self.carpeta, 'ajena.db')
        conn = sqlite3.connect(ajena)
        conn.execute("CREATE TABLE otra_cosa (x INTEGER)")
        conn.commit()
        conn.close()
        with self.assertRaises(ValueError):
            respaldos.restaurar_respaldo(ajena)
        self.assertEqual(len(clientes.cargar_clientes()), 1)  # la base actual quedó intacta

    def test_cli_de_restauracion(self):
        from gimnasio import restaurar
        ruta = respaldos.crear_respaldo()
        self.nuevo_cliente('22222222')
        self.assertEqual(restaurar.main([ruta]), 0)
        self.assertEqual(len(clientes.cargar_clientes()), 1)
        self.assertEqual(restaurar.main([]), 1)
        self.assertEqual(restaurar.main([os.path.join(self.carpeta, 'nada.db')]), 1)


class TestBucleAutomatico(BaseConDatos):
    def test_arranque_registra_la_tarea(self):
        import asyncio
        from unittest import mock
        from gimnasio import arranque

        registrados = []

        class AppFalsa:
            def on_startup(self, funcion):
                registrados.append(funcion)

        arranque.iniciar_respaldos_automaticos(AppFalsa())
        self.assertEqual(len(registrados), 1)

        async def probar():
            with mock.patch.object(arranque, '_bucle_respaldos', mock.AsyncMock()) as bucle:
                await registrados[0]()
                await asyncio.sleep(0)
                bucle.assert_called_once()

        asyncio.run(probar())

    def test_el_bucle_hace_el_respaldo_y_sigue_aunque_falle(self):
        import asyncio
        from unittest import mock
        from gimnasio import arranque

        llamadas = []

        def falla_y_luego_anda():
            llamadas.append(1)
            if len(llamadas) == 1:
                raise RuntimeError('disco lleno')
            return '/ruta/respaldo.db'

        async def probar():
            with mock.patch.object(respaldos, 'respaldo_diario_si_falta', falla_y_luego_anda):
                tarea = asyncio.create_task(arranque._bucle_respaldos(cada_segundos=0.01))
                await asyncio.sleep(0.2)
                tarea.cancel()

        asyncio.run(probar())
        self.assertGreaterEqual(len(llamadas), 2)  # el error no mató el bucle


if __name__ == '__main__':
    unittest.main()
