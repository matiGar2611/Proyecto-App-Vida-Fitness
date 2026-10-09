import os
import sqlite3
import unittest

from gimnasio import seguridad
from gimnasio.datos import usuarios
from tests.base import BaseConDatos


class TestUsuarios(BaseConDatos):
    def test_crear_y_buscar(self):
        usuarios.crear_usuario('profe1', 'clavelarga1', 'Profe Uno', 'profe')
        u = usuarios.obtener_usuario('profe1')
        self.assertEqual((u['username'], u['nombre'], u['rol']), ('profe1', 'Profe Uno', 'profe'))
        self.assertTrue(seguridad.verificar_password('clavelarga1', u['salt'], u['password_hash']))
        self.assertEqual(usuarios.obtener_usuario_por_id(u['id'])['username'], 'profe1')
        self.assertEqual(len(u), 6)  # también se accede por posición

    def test_inexistente(self):
        self.assertIsNone(usuarios.obtener_usuario('nadie'))
        self.assertIsNone(usuarios.obtener_usuario_por_id(999))
        self.assertIsNone(usuarios.obtener_usuario_por_id(None))

    def test_usuario_repetido_o_rol_invalido(self):
        usuarios.crear_usuario('a', 'clavelarga1', 'A', 'profe')
        with self.assertRaises(sqlite3.IntegrityError):
            usuarios.crear_usuario('a', 'clavelarga1', 'Otro', 'profe')
        with self.assertRaises(sqlite3.IntegrityError):
            usuarios.crear_usuario('b', 'clavelarga1', 'B', 'superadmin')

    def test_actualizar_sin_y_con_contrasena(self):
        usuarios.crear_usuario('a', 'clave-vieja1', 'A', 'profe')
        uid = usuarios.obtener_usuario('a')['id']
        usuarios.actualizar_usuario(uid, 'a2', 'Nuevo Nombre', 'profe')
        u = usuarios.obtener_usuario_por_id(uid)
        self.assertEqual((u['username'], u['nombre']), ('a2', 'Nuevo Nombre'))
        self.assertTrue(seguridad.verificar_password('clave-vieja1', u['salt'], u['password_hash']))
        usuarios.actualizar_usuario(uid, 'a2', 'Nuevo Nombre', 'profe', 'clave-nueva1')
        u = usuarios.obtener_usuario_por_id(uid)
        self.assertTrue(seguridad.verificar_password('clave-nueva1', u['salt'], u['password_hash']))
        self.assertFalse(seguridad.verificar_password('clave-vieja1', u['salt'], u['password_hash']))

    def test_listado_y_conteo_de_duenos(self):
        usuarios.crear_usuario('d', 'clavelarga1', 'D', 'dueño')
        usuarios.crear_usuario('p', 'clavelarga1', 'P', 'profe')
        self.assertEqual(usuarios.contar_dueños(), 1)
        self.assertEqual(len(usuarios.obtener_todos_usuarios()), 2)
        self.assertEqual(usuarios.obtener_todos_usuarios()[0].keys(), ['id', 'username', 'nombre', 'rol'])

    def test_eliminar(self):
        usuarios.crear_usuario('p', 'clavelarga1', 'P', 'profe')
        usuarios.eliminar_usuario(usuarios.obtener_usuario('p')['id'])
        self.assertIsNone(usuarios.obtener_usuario('p'))

    def test_cuenta_dueno_con_variable_de_entorno(self):
        os.environ['ADMIN_PASSWORD'] = 'MiClaveSegura9'
        self.assertIsNone(usuarios.asegurar_cuenta_dueño())
        u = usuarios.obtener_usuario('admin')
        self.assertEqual(u['rol'], 'dueño')
        self.assertTrue(seguridad.verificar_password('MiClaveSegura9', u['salt'], u['password_hash']))

    def test_cuenta_dueno_con_clave_generada(self):
        clave = usuarios.asegurar_cuenta_dueño()
        self.assertGreaterEqual(len(clave), 12)
        u = usuarios.obtener_usuario('admin')
        self.assertTrue(seguridad.verificar_password(clave, u['salt'], u['password_hash']))
        self.assertFalse(seguridad.verificar_password('admin123', u['salt'], u['password_hash']))

    def test_variable_corta_se_ignora(self):
        os.environ['ADMIN_PASSWORD'] = 'corta'
        self.assertIsNotNone(usuarios.asegurar_cuenta_dueño())

    def test_no_crea_admin_si_ya_hay_cuentas(self):
        usuarios.crear_usuario('p', 'clavelarga1', 'P', 'profe')
        self.assertIsNone(usuarios.asegurar_cuenta_dueño())
        self.assertIsNone(usuarios.obtener_usuario('admin'))

    def test_endurecer_admin_de_fabrica(self):
        # Cuenta heredada con la contraseña de fábrica.
        usuarios.crear_usuario('admin', 'admin123', 'Dueño', 'dueño')
        self.assertFalse(usuarios.endurecer_admin_de_fabrica())  # sin variable: solo avisa
        os.environ['ADMIN_PASSWORD'] = 'NuevaClave123'
        self.assertTrue(usuarios.endurecer_admin_de_fabrica())
        u = usuarios.obtener_usuario('admin')
        self.assertTrue(seguridad.verificar_password('NuevaClave123', u['salt'], u['password_hash']))
        self.assertFalse(usuarios.endurecer_admin_de_fabrica())  # ya no tiene la de fábrica

    def test_endurecer_no_toca_una_clave_propia(self):
        usuarios.crear_usuario('admin', 'una-clave-propia', 'Dueño', 'dueño')
        os.environ['ADMIN_PASSWORD'] = 'NuevaClave123'
        self.assertFalse(usuarios.endurecer_admin_de_fabrica())
        u = usuarios.obtener_usuario('admin')
        self.assertTrue(seguridad.verificar_password('una-clave-propia', u['salt'], u['password_hash']))


if __name__ == '__main__':
    unittest.main()
