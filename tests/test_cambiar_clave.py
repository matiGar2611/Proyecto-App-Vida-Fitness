import os
import unittest

from gimnasio import cambiar_clave, seguridad
from gimnasio.datos import auditoria, usuarios
from tests.base import BaseConDatos


def claves(*respuestas):
    """Simula lo que se tipea cuando la consola pide la contraseña."""
    pendientes = iter(respuestas)
    return lambda _pregunta: next(pendientes)


class TestCambiarClave(BaseConDatos):
    def setUp(self):
        super().setUp()
        usuarios.crear_usuario('admin', 'clave-que-olvide', 'Dueño', 'dueño')

    def clave_valida(self, usuario, clave):
        u = usuarios.obtener_usuario(usuario)
        return seguridad.verificar_password(clave, u['salt'], u['password_hash'])

    def test_cambia_la_clave(self):
        self.assertEqual(cambiar_clave.main(['admin'], claves('NuevaClave123', 'NuevaClave123')), 0)
        self.assertTrue(self.clave_valida('admin', 'NuevaClave123'))
        self.assertFalse(self.clave_valida('admin', 'clave-que-olvide'))
        self.assertEqual(auditoria.ultimas(1)[0]['accion'], 'Contraseña cambiada desde la consola')

    def test_no_toca_los_demas_datos_de_la_cuenta(self):
        cambiar_clave.main(['admin'], claves('NuevaClave123', 'NuevaClave123'))
        u = usuarios.obtener_usuario('admin')
        self.assertEqual((u['nombre'], u['rol']), ('Dueño', 'dueño'))

    def test_clave_corta(self):
        self.assertEqual(cambiar_clave.main(['admin'], claves('corta', 'corta')), 1)
        self.assertTrue(self.clave_valida('admin', 'clave-que-olvide'))

    def test_no_coinciden(self):
        self.assertEqual(cambiar_clave.main(['admin'], claves('NuevaClave123', 'OtraDistinta1')), 1)
        self.assertTrue(self.clave_valida('admin', 'clave-que-olvide'))

    def test_cuenta_inexistente_muestra_las_que_hay(self):
        self.assertEqual(cambiar_clave.main(['nadie'], claves('x', 'x')), 1)

    def test_sin_argumentos(self):
        self.assertEqual(cambiar_clave.main([], claves()), 1)

    def test_base_inexistente_no_crea_una_vacia(self):
        os.remove(os.path.join(self.carpeta, 'gimnasio.db'))
        self.assertEqual(cambiar_clave.main(['admin'], claves('NuevaClave123', 'NuevaClave123')), 1)
        self.assertFalse(os.path.exists(os.path.join(self.carpeta, 'gimnasio.db')))


if __name__ == '__main__':
    unittest.main()
