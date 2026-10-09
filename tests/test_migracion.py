import hashlib
import json
import os
import sqlite3
import unittest

from gimnasio import arranque, db, seguridad
from gimnasio.datos import ajustes, clientes, contabilidad, usuarios
from gimnasio.servicios import migracion
from tests.base import BaseConDatos, escribir_archivo, leer_bytes


def viejo_hash(clave, sal):
    return hashlib.sha256((sal + clave).encode()).hexdigest()


class TestMigracion(BaseConDatos):
    """Importa datos con el formato de la versión anterior (JSON + usuarios.db)."""

    def escribir_json(self, nombre, datos):
        with open(os.path.join(self.carpeta, nombre), 'w', encoding='utf-8') as f:
            json.dump(datos, f)

    def preparar_datos_anteriores(self):
        conn = sqlite3.connect(os.path.join(self.carpeta, 'usuarios.db'))
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, "
                     "password_hash TEXT NOT NULL, salt TEXT NOT NULL, password_plain TEXT NOT NULL, "
                     "nombre TEXT NOT NULL, rol TEXT NOT NULL)")
        conn.execute("INSERT INTO usuarios VALUES (1, 'admin', ?, 's1', 'admin123', 'Dueño', 'dueño')",
                     (viejo_hash('admin123', 's1'),))
        conn.execute("INSERT INTO usuarios VALUES (2, 'profe1', ?, 's2', 'clave-profe', 'Profe Uno', 'profe')",
                     (viejo_hash('clave-profe', 's2'),))
        conn.commit()
        conn.close()

        base = {"Telefono": "2615551111", "Plan": "Todos los días", "Fecha de nacimiento": "1990-01-01",
                "Fecha de inicio": "2026-09-01", "Fecha de vencimiento": "2026-10-01",
                "Fecha ultimo pago": "2026-09-01", "Cliente Activo": True, "Rutina": "<b>Hola</b><script>x()</script>"}
        self.escribir_json('Clientes.json', [
            dict(base, DNI="11111111", **{"Nombre y  Apellido": "Con DNI de clave"},
                 **{"Password Hash": viejo_hash("11111111", "s3"), "Password Salt": "s3",
                    "Password Plain": "11111111"},
                 **{"Saldo pendiente": 7000, "Historial de pagos": [
                     {"fecha": "2026-09-01", "monto": 15000, "vencimiento": "2026-10-01"},
                     {"fecha": "2026-09-15", "monto": 5000, "vencimiento": "2026-10-15", "saldo_pendiente_tras_pago": 7000}]}),
            dict(base, DNI="22222222", **{"Nombre y  Apellido": "Con clave propia"},
                 **{"Password Hash": viejo_hash("mi-clave", "s4"), "Password Salt": "s4",
                    "Password Plain": "mi-clave"}, **{"Historial de pagos": []}),
            dict(base, DNI="33333333", **{"Nombre y  Apellido": "Ficha muy vieja"}),
            dict(base, DNI="11111111", **{"Nombre y  Apellido": "Repetido"}),
        ])
        self.escribir_json('precios.json', {"Todos los días": 25000})
        self.escribir_json('informacion.json', {"texto": "Horario especial"})
        self.escribir_json('anuncios.json', [{"id": 2, "fecha": "2026-09-20", "texto": "Nuevo"},
                                             {"id": 1, "fecha": "2026-09-10", "texto": "Viejo"}])
        self.escribir_json('contabilidad.json', [
            {"id": 1, "fecha": "2026-09-01", "tipo": "ingreso", "categoria": "Cuota",
             "descripcion": "Pago", "monto": 15000, "dni_cliente": "11111111"},
            {"id": 2, "fecha": "2026-09-02", "tipo": "egreso", "categoria": "Luz",
             "descripcion": "Luz", "monto": 3000, "dni_cliente": None}])

    def test_sin_datos_anteriores_no_hace_nada(self):
        self.assertIsNone(migracion.migrar_si_corresponde())

    def test_importa_todo(self):
        self.preparar_datos_anteriores()
        resumen = migracion.migrar_si_corresponde()
        self.assertEqual(resumen, {'usuarios': 2, 'clientes': 3, 'pagos': 2, 'anuncios': 2, 'movimientos': 2})

        self.assertEqual({u['username'] for u in usuarios.obtener_todos_usuarios()}, {'admin', 'profe1'})
        self.assertEqual([c['dni'] for c in clientes.cargar_clientes()], ['11111111', '22222222', '33333333'])
        self.assertEqual(ajustes.precio_de_plan('Todos los días'), 25000)
        self.assertEqual(ajustes.cargar_informacion(), 'Horario especial')
        self.assertEqual([a['texto'] for a in ajustes.cargar_anuncios()], ['Nuevo', 'Viejo'])
        self.assertEqual(len(contabilidad.cargar_movimientos()), 2)

        c = clientes.buscar_cliente_por_dni('11111111')
        self.assertEqual(c['saldo_pendiente'], 7000)
        self.assertEqual([p['monto'] for p in c['historial']], [15000, 5000])
        self.assertEqual(c['historial'][0]['saldo_pendiente_tras_pago'], 0)
        self.assertEqual(c['nombre'], 'Con DNI de clave')  # no pisa por el DNI repetido

    def test_las_contrasenas_siguen_funcionando_pero_no_se_copian_en_texto_plano(self):
        self.preparar_datos_anteriores()
        migracion.migrar_si_corresponde()
        profe = usuarios.obtener_usuario('profe1')
        self.assertTrue(seguridad.verificar_password('clave-profe', profe['salt'], profe['password_hash']))
        c = clientes.buscar_cliente_por_dni('22222222')
        self.assertTrue(clientes.verificar_password_cliente(c, 'mi-clave'))
        with db.lectura() as conn:
            volcado = ' '.join(str(tuple(f)) for t in ('usuarios', 'clientes')
                               for f in conn.execute(f"SELECT * FROM {t}"))
        for secreto in ('clave-profe', 'admin123', 'mi-clave'):
            self.assertNotIn(secreto, volcado)

    def test_debe_cambiar_password_segun_cada_caso(self):
        self.preparar_datos_anteriores()
        migracion.migrar_si_corresponde()
        self.assertTrue(clientes.buscar_cliente_por_dni('11111111')['debe_cambiar_password'])   # clave = DNI
        self.assertFalse(clientes.buscar_cliente_por_dni('22222222')['debe_cambiar_password'])  # clave propia
        sin_hash = clientes.buscar_cliente_por_dni('33333333')
        self.assertTrue(sin_hash['debe_cambiar_password'])                                      # ficha muy vieja
        self.assertTrue(clientes.verificar_password_cliente(sin_hash, '33333333'))

    def test_la_rutina_se_limpia(self):
        self.preparar_datos_anteriores()
        migracion.migrar_si_corresponde()
        self.assertEqual(clientes.buscar_cliente_por_dni('11111111')['rutina'], '<b>Hola</b>')

    def test_se_ejecuta_una_sola_vez(self):
        self.preparar_datos_anteriores()
        self.assertIsNotNone(migracion.migrar_si_corresponde())
        self.assertIsNone(migracion.migrar_si_corresponde())
        self.assertEqual(len(clientes.cargar_clientes()), 3)

    def test_no_pisa_una_base_que_ya_tiene_datos(self):
        self.preparar_datos_anteriores()
        usuarios.crear_usuario('nuevo', 'clavelarga1', 'Nuevo', 'dueño')
        self.assertIsNone(migracion.migrar_si_corresponde())
        self.assertEqual(clientes.cargar_clientes(), [])

    def test_no_modifica_los_archivos_anteriores(self):
        self.preparar_datos_anteriores()
        ruta = os.path.join(self.carpeta, 'Clientes.json')
        antes = leer_bytes(ruta)
        migracion.migrar_si_corresponde()
        self.assertEqual(leer_bytes(ruta), antes)

    def test_json_corrupto_se_omite(self):
        self.preparar_datos_anteriores()
        escribir_archivo(os.path.join(self.carpeta, 'Clientes.json'), '{esto no es json')
        resumen = migracion.migrar_si_corresponde()
        self.assertEqual(resumen['clientes'], 0)
        self.assertEqual(resumen['usuarios'], 2)

    def test_arranque_completo_con_datos_anteriores(self):
        self.preparar_datos_anteriores()
        os.environ['ADMIN_PASSWORD'] = 'NuevaClave123'
        arranque.preparar()
        admin = usuarios.obtener_usuario('admin')
        self.assertTrue(seguridad.verificar_password('NuevaClave123', admin['salt'], admin['password_hash']))
        self.assertEqual(len(clientes.cargar_clientes()), 3)


class TestArranque(BaseConDatos):
    def test_primer_arranque_crea_el_dueno(self):
        os.environ['ADMIN_PASSWORD'] = 'ClaveSegura99'
        arranque.preparar()
        u = usuarios.obtener_usuario('admin')
        self.assertTrue(seguridad.verificar_password('ClaveSegura99', u['salt'], u['password_hash']))

    def test_es_seguro_repetirlo(self):
        os.environ['ADMIN_PASSWORD'] = 'ClaveSegura99'
        arranque.preparar()
        arranque.preparar()
        self.assertEqual(usuarios.contar_usuarios(), 1)


if __name__ == '__main__':
    unittest.main()
