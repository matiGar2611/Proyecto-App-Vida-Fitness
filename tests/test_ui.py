"""Pruebas de las pantallas con un NiceGUI de mentira (ver stub_nicegui.py).

Comprueban permisos, redirecciones, formularios y que cada acción llegue a la
base de datos y al registro de actividad. No reemplazan mirar la app en un
navegador real: ver la lista de comprobaciones manuales en el README.
"""

import asyncio
import json
import os
import unittest
from types import SimpleNamespace

from tests import stub_nicegui as stub

stub.instalar()  # tiene que ir antes de importar las pantallas

import gimnasio.ui  # noqa: E402,F401  (registra las páginas en el stub)
from gimnasio import config, db, seguridad  # noqa: E402
from gimnasio.datos import ajustes, auditoria, clientes, contabilidad, usuarios  # noqa: E402
from gimnasio.servicios import respaldos  # noqa: E402
from gimnasio.ui import clientes as ui_clientes  # noqa: E402
from gimnasio.ui import mi_cuenta, navbar, pwa, usuarios as ui_usuarios  # noqa: E402
from tests.base import BaseConDatos  # noqa: E402

PAGINAS_DEL_DUENO = ['/usuarios', '/precios', '/informacion', '/anuncios', '/contabilidad',
                     '/respaldos', '/actividad']


def evento(**args):
    return SimpleNamespace(args=args)


class BaseUi(BaseConDatos):
    def setUp(self):
        super().setUp()
        self.fijar_hoy(2026, 10, 8)
        stub.reiniciar()
        usuarios.crear_usuario('dueno1', 'clave-dueno-1', 'Dueña Uno', 'dueño')
        usuarios.crear_usuario('profe1', 'clave-profe-1', 'Profe Uno', 'profe')
        self.dni = self.nuevo_cliente('12345678', 'Ana Pérez')

    # --- sesión y pantalla ---
    def entrar_como(self, username):
        u = usuarios.obtener_usuario(username)
        stub.app.storage.user.clear()
        stub.app.storage.user.update(id=u['id'], username=u['username'], nombre=u['nombre'], rol=u['rol'])

    def entrar_como_cliente(self, dni='12345678'):
        stub.app.storage.user.clear()
        c = clientes.buscar_cliente_por_dni(dni)
        stub.app.storage.user.update(rol='cliente', dni=dni, nombre=c['nombre'])

    def pantalla_nueva(self):
        """Como recargar la página: se borra lo dibujado pero se conserva la sesión."""
        for lista in (stub.REGISTRO, stub.NOTIFICACIONES, stub.NAVEGACIONES, stub.DESCARGAS, stub.HEAD_Y_BODY):
            lista.clear()

    def abrir(self, ruta):
        self.pantalla_nueva()
        stub.PAGINAS[ruta]()

    # --- búsquedas ---
    def uno(self, tipo, texto, posicion=0):
        encontrados = stub.buscar(tipo, texto)
        self.assertGreater(len(encontrados), posicion, f"No se encontró {tipo} '{texto}'")
        return encontrados[posicion]

    def tipo(self, tipo):
        return [e for e in stub.REGISTRO if e.tipo == tipo]

    def hay_texto(self, texto):
        return any(texto in t for t in stub.textos('label'))

    def notificaciones(self, tipo=None):
        return [t for t, k in stub.NOTIFICACIONES if tipo is None or k == tipo]

    def ultima_actividad(self):
        return auditoria.ultimas(1)[0]


# ============================================================ estructura y permisos

class TestEstructura(BaseUi):
    def test_se_registran_todas_las_paginas(self):
        esperadas = {'/', '/login', '/mi-cuenta', *PAGINAS_DEL_DUENO}
        self.assertEqual(set(stub.PAGINAS), esperadas)

    def test_rutas_de_la_app_instalable(self):
        self.assertTrue({'/manifest.webmanifest', '/sw.js', '/health'} <= set(stub.RUTAS))

    def test_sin_sesion_todo_lleva_al_login(self):
        for ruta in ['/', '/mi-cuenta', *PAGINAS_DEL_DUENO]:
            self.abrir(ruta)
            self.assertEqual(stub.NAVEGACIONES, ['/login'], ruta)

    def test_el_profe_no_entra_a_las_paginas_del_dueno(self):
        self.entrar_como('profe1')
        for ruta in PAGINAS_DEL_DUENO:
            self.abrir(ruta)
            self.assertEqual(stub.NAVEGACIONES, ['/'], ruta)
            self.assertIn('No tenés permisos para acceder a esta página.', self.notificaciones('negative'), ruta)

    def test_el_cliente_no_entra_a_las_paginas_del_personal(self):
        self.entrar_como_cliente()
        for ruta in ['/', *PAGINAS_DEL_DUENO]:
            self.abrir(ruta)
            self.assertIn(stub.NAVEGACIONES[0], ('/mi-cuenta', '/'), ruta)
        self.abrir('/')
        self.assertEqual(stub.NAVEGACIONES, ['/mi-cuenta'])

    def test_el_personal_no_entra_a_mi_cuenta(self):
        self.entrar_como('dueno1')
        self.abrir('/mi-cuenta')
        self.assertEqual(stub.NAVEGACIONES, ['/'])

    def test_el_dueno_puede_abrir_todas_las_paginas(self):
        self.entrar_como('dueno1')
        for ruta in ['/', *PAGINAS_DEL_DUENO]:
            self.abrir(ruta)
            self.assertEqual(stub.NAVEGACIONES, [], ruta)
            self.assertTrue(any('manifest' in c for t, c in stub.HEAD_Y_BODY), ruta)  # cabecera común

    def test_la_sesion_de_un_usuario_borrado_deja_de_servir(self):
        self.entrar_como('profe1')
        usuarios.eliminar_usuario(usuarios.obtener_usuario('profe1')['id'])
        self.abrir('/')
        self.assertEqual(stub.NAVEGACIONES, ['/login'])
        self.assertEqual(stub.app.storage.user, {})

    def test_la_sesion_de_un_cliente_borrado_deja_de_servir(self):
        self.entrar_como_cliente()
        clientes.eliminar_cliente(self.dni)
        self.abrir('/mi-cuenta')
        self.assertEqual(stub.NAVEGACIONES, ['/login'])

    def test_un_cambio_de_rol_se_nota_en_el_momento(self):
        self.entrar_como('dueno1')
        usuarios.crear_usuario('dueno2', 'clave-dueno-2', 'Otra', 'dueño')
        u = usuarios.obtener_usuario('dueno1')
        usuarios.actualizar_usuario(u['id'], 'dueno1', u['nombre'], 'profe')
        self.abrir('/usuarios')
        self.assertEqual(stub.NAVEGACIONES, ['/login'])

    def test_botones_de_la_barra_segun_el_rol(self):
        def botones():
            self.pantalla_nueva()
            navbar.construir_navbar()
            return set(stub.textos('button'))

        self.entrar_como('dueno1')
        self.assertTrue({'Clientes', 'Usuarios', 'Contabilidad', 'Precios', 'Información', 'Anuncios',
                         'Respaldos', 'Actividad'} <= botones())
        self.entrar_como('profe1')
        b = botones()
        self.assertIn('Clientes', b)
        for solo_dueno in ('Usuarios', 'Contabilidad', 'Precios', 'Respaldos', 'Actividad'):
            self.assertNotIn(solo_dueno, b)
        self.entrar_como_cliente()
        self.assertIn('Mi cuenta', botones())
        self.assertNotIn('Clientes', botones())


# ============================================================ login

class TestLogin(BaseUi):
    def intentar_personal(self, usuario, clave):
        self.abrir('/login')
        self.uno('input', 'Usuario').value = usuario
        self.uno('input', 'Contraseña', 0).value = clave
        self.uno('button', 'Ingresar', 0).on_click()

    def intentar_cliente(self, dni, clave):
        self.abrir('/login')
        self.uno('input', 'Tu DNI (usuario)').value = dni
        self.uno('input', 'Contraseña', 1).value = clave
        self.uno('button', 'Ingresar', 1).on_click()

    def test_ya_logueado_va_directo_a_su_pantalla(self):
        self.entrar_como('dueno1')
        self.abrir('/login')
        self.assertEqual(stub.NAVEGACIONES, ['/'])
        self.entrar_como_cliente()
        self.abrir('/login')
        self.assertEqual(stub.NAVEGACIONES, ['/mi-cuenta'])

    def test_no_muestra_la_cuenta_de_fabrica(self):
        self.abrir('/login')
        todo = ' '.join(stub.textos('label'))
        self.assertNotIn('admin123', todo)
        self.assertNotIn('Cuenta por defecto', todo)

    def test_personal_correcto(self):
        self.intentar_personal('dueno1', 'clave-dueno-1')
        self.assertEqual(stub.NAVEGACIONES, ['/'])
        self.assertEqual(stub.app.storage.user['rol'], 'dueño')
        self.assertEqual(stub.app.storage.user['username'], 'dueno1')
        self.assertEqual(self.ultima_actividad()['accion'], 'Inicio de sesión')
        self.assertEqual(self.ultima_actividad()['actor'], 'Dueña Uno')

    def test_personal_incorrecto_no_revela_si_el_usuario_existe(self):
        self.intentar_personal('dueno1', 'mala')
        self.assertEqual(stub.app.storage.user, {})
        mensaje_1 = [t for t in stub.textos('label') if 'incorrectos' in t]
        self.intentar_personal('no-existe', 'mala')
        mensaje_2 = [t for t in stub.textos('label') if 'incorrectos' in t]
        self.assertEqual(mensaje_1, ['Usuario o contraseña incorrectos'])
        self.assertEqual(mensaje_1, mensaje_2)

    def test_campos_vacios(self):
        self.intentar_personal('', '')
        self.assertTrue(self.hay_texto('Completá usuario y contraseña'))
        self.assertEqual(stub.app.storage.user, {})

    def test_bloqueo_tras_cinco_intentos_aun_con_la_clave_correcta(self):
        for _ in range(config.MAX_INTENTOS_LOGIN):
            self.intentar_personal('dueno1', 'mala')
        self.intentar_personal('dueno1', 'clave-dueno-1')
        self.assertTrue(self.hay_texto('Demasiados intentos'))
        self.assertEqual(stub.app.storage.user, {})

    def test_el_bloqueo_es_por_cuenta(self):
        for _ in range(config.MAX_INTENTOS_LOGIN):
            self.intentar_personal('dueno1', 'mala')
        self.intentar_personal('profe1', 'clave-profe-1')
        self.assertEqual(stub.app.storage.user['rol'], 'profe')

    def test_un_login_correcto_borra_los_fallos(self):
        for _ in range(config.MAX_INTENTOS_LOGIN - 1):
            self.intentar_personal('dueno1', 'mala')
        self.intentar_personal('dueno1', 'clave-dueno-1')
        stub.app.storage.user.clear()
        for _ in range(config.MAX_INTENTOS_LOGIN - 1):
            self.intentar_personal('dueno1', 'mala')
        self.intentar_personal('dueno1', 'clave-dueno-1')
        self.assertEqual(stub.app.storage.user['rol'], 'dueño')

    def test_cuenta_con_hash_viejo_entra_y_se_actualiza(self):
        import hashlib
        with db.escritura() as conn:
            conn.execute("UPDATE usuarios SET password_hash = ?, salt = 'sal' WHERE username = 'profe1'",
                         (hashlib.sha256(b'salclave-vieja').hexdigest(),))
        self.intentar_personal('profe1', 'clave-vieja')
        self.assertEqual(stub.app.storage.user['rol'], 'profe')
        self.assertTrue(usuarios.obtener_usuario('profe1')['password_hash'].startswith('pbkdf2_sha256$'))

    def test_cliente_correcto(self):
        self.intentar_cliente('12345678', '12345678')
        self.assertEqual(stub.NAVEGACIONES, ['/mi-cuenta'])
        self.assertEqual(stub.app.storage.user['rol'], 'cliente')
        self.assertEqual(stub.app.storage.user['dni'], '12345678')
        self.assertEqual(stub.app.storage.user['nombre'], 'Ana Pérez')

    def test_cliente_incorrecto_y_dni_inexistente_dan_el_mismo_mensaje(self):
        self.intentar_cliente('12345678', 'mala')
        mensaje_1 = [t for t in stub.textos('label') if 'incorrectos' in t]
        self.intentar_cliente('99999999', 'mala')
        mensaje_2 = [t for t in stub.textos('label') if 'incorrectos' in t]
        self.assertEqual(len(mensaje_1), 1)
        self.assertEqual(mensaje_1, mensaje_2)
        self.assertEqual(stub.app.storage.user, {})

    def test_cliente_bloqueado_tras_cinco_intentos(self):
        for _ in range(config.MAX_INTENTOS_LOGIN):
            self.intentar_cliente('12345678', 'mala')
        self.intentar_cliente('12345678', '12345678')
        self.assertTrue(self.hay_texto('Demasiados intentos'))
        self.assertEqual(stub.app.storage.user, {})

    def test_un_dni_inexistente_tambien_se_bloquea(self):
        for _ in range(config.MAX_INTENTOS_LOGIN):
            self.intentar_cliente('99999999', 'x')
        self.intentar_cliente('99999999', 'x')
        self.assertTrue(self.hay_texto('Demasiados intentos'))

    def test_cliente_con_hash_viejo_se_actualiza_sin_perder_el_estado(self):
        import hashlib
        clientes.cambiar_password_cliente(self.dni, 'mi-clave-propia')
        with db.escritura() as conn:
            conn.execute("UPDATE clientes SET password_hash = ?, password_salt = 'sal' WHERE dni = ?",
                         (hashlib.sha256(b'salmi-clave-propia').hexdigest(), self.dni))
        self.intentar_cliente(self.dni, 'mi-clave-propia')
        c = clientes.buscar_cliente_por_dni(self.dni)
        self.assertEqual(stub.app.storage.user['rol'], 'cliente')
        self.assertTrue(c['password_hash'].startswith('pbkdf2_sha256$'))
        self.assertFalse(c['debe_cambiar_password'])  # no se le vuelve a exigir cambiarla


# ============================================================ portal del cliente

class TestMiCuenta(BaseUi):
    def test_portal_completo(self):
        ajustes.agregar_anuncio('Cerramos el lunes')
        clientes.cambiar_password_cliente(self.dni, 'mi-clave-propia')
        clientes.actualizar_rutina(self.dni, '<b>Piernas</b><script>alert(1)</script>')
        self.entrar_como_cliente()
        self.abrir('/mi-cuenta')

        textos = stub.textos('label')
        self.assertIn('¡Hola, Ana Pérez!', textos)
        self.assertIn('Cerramos el lunes', textos)
        self.assertIn('Próximo vencimiento: 07/11/2026', textos)
        self.assertIn('Te quedan 30 día(s) de cuota vigente.', textos)
        self.assertIn('Cronómetro y rondas', textos)
        self.assertIn('00:00.0', textos)
        self.assertEqual(stub.NAVEGACIONES, [])
        self.assertEqual(self.tipo('dialog'), [])  # no tiene que cambiar la clave

        rutina = [e for e in self.tipo('html')][-1]
        self.assertIn('<b>Piernas</b>', rutina.args[0])
        self.assertNotIn('script', rutina.args[0])

    def test_el_cronometro_carga_su_script_con_la_clave_del_cliente(self):
        clientes.cambiar_password_cliente(self.dni, 'mi-clave-propia')
        self.entrar_como_cliente()
        self.abrir('/mi-cuenta')
        scripts = [c for t, c in stub.HEAD_Y_BODY if t == 'body']
        self.assertEqual(len(scripts), 1)
        self.assertIn("vf_entrenamiento_12345678", scripts[0])
        self.assertNotIn('__CLAVE__', scripts[0])
        for boton in ('iniciar', 'pausar', 'reiniciar-tiempo', 'rondas-mas', 'rondas-menos', 'rondas-reset'):
            self.assertTrue(any(f'data-vf={boton}' in p for e in self.tipo('button') for p in e.propiedades), boton)

    def test_saldo_pendiente_y_cuota_vencida(self):
        clientes.cambiar_password_cliente(self.dni, 'mi-clave-propia')
        with db.escritura() as conn:
            conn.execute("UPDATE clientes SET saldo_pendiente = 7000, fecha_vencimiento = '2026-10-03' WHERE dni = ?",
                         (self.dni,))
        self.entrar_como_cliente()
        self.abrir('/mi-cuenta')
        self.assertTrue(self.hay_texto('saldo pendiente de $7.000'))
        self.assertIn('Tu cuota está vencida hace 5 día(s).', stub.textos('label'))

    def test_sin_rutina(self):
        clientes.cambiar_password_cliente(self.dni, 'mi-clave-propia')
        self.entrar_como_cliente()
        self.abrir('/mi-cuenta')
        self.assertTrue(self.hay_texto('Todavía no tenés una rutina cargada'))

    def test_enlaces_de_whatsapp_y_encuesta(self):
        clientes.cambiar_password_cliente(self.dni, 'mi-clave-propia')
        self.entrar_como_cliente()
        self.abrir('/mi-cuenta')
        self.uno('button', 'Consultar por WhatsApp').on_click()
        self.assertTrue(stub.NAVEGACIONES[-1].startswith(f'https://wa.me/{config.NUMERO_WHATSAPP_GIMNASIO}?text='))
        self.assertIn('Ana', stub.NAVEGACIONES[-1])
        self.uno('button', 'Encuesta / Sugerencias').on_click()
        self.assertEqual(stub.NAVEGACIONES[-1], config.LINK_ENCUESTA)

    def test_cambio_de_clave_obligatorio_en_el_primer_ingreso(self):
        self.entrar_como_cliente()  # todavía tiene su DNI como clave
        self.abrir('/mi-cuenta')
        dialogos = self.tipo('dialog')
        self.assertEqual(len(dialogos), 1)
        self.assertIn('persistent', dialogos[0].propiedades)
        self.assertTrue(dialogos[0].abierto)
        self.assertNotIn('Cancelar', stub.textos('button'))  # no se puede salir sin cambiarla

    def completar_cambio(self, actual, nueva, confirmar):
        self.uno('input', 'Contraseña actual').value = actual
        self.uno('input', 'Nueva contraseña').value = nueva
        self.uno('input', 'Confirmar nueva contraseña').value = confirmar
        self.uno('button', 'Guardar').on_click()

    def test_cambio_de_clave_correcto(self):
        self.entrar_como_cliente()
        self.abrir('/mi-cuenta')
        self.completar_cambio('12345678', 'una-clave-nueva', 'una-clave-nueva')
        c = clientes.buscar_cliente_por_dni(self.dni)
        self.assertFalse(c['debe_cambiar_password'])
        self.assertTrue(clientes.verificar_password_cliente(c, 'una-clave-nueva'))
        self.assertEqual(stub.NAVEGACIONES, ['/mi-cuenta'])
        self.assertEqual(self.ultima_actividad()['accion'], 'Cambió su contraseña')

    def test_cambio_de_clave_rechaza_los_casos_invalidos(self):
        self.entrar_como_cliente()
        for actual, nueva, confirmar, mensaje in [
            ('mala', 'una-clave-nueva', 'una-clave-nueva', 'La contraseña actual no es correcta.'),
            ('12345678', 'corta', 'corta', 'al menos 6 caracteres'),
            ('12345678', '12345678', '12345678', 'no puede ser tu DNI'),
            ('12345678', 'una-clave-nueva', 'otra-distinta', 'no coinciden'),
        ]:
            self.abrir('/mi-cuenta')
            self.completar_cambio(actual, nueva, confirmar)
            self.assertTrue(any(mensaje in n for n in self.notificaciones('negative')), mensaje)
        self.assertTrue(clientes.buscar_cliente_por_dni(self.dni)['debe_cambiar_password'])

    def test_cambio_voluntario_se_puede_cancelar(self):
        clientes.cambiar_password_cliente(self.dni, 'mi-clave-propia')
        self.entrar_como_cliente()
        self.abrir('/mi-cuenta')
        self.uno('button', 'Cambiar mi contraseña').on_click()
        self.assertIn('Cancelar', stub.textos('button'))


# ============================================================ clientes (personal)

class TestClientes(BaseUi):
    def setUp(self):
        super().setUp()
        self.entrar_como('dueno1')

    def pagina(self):
        self.abrir('/')
        return self.tipo('table')[0]

    def test_la_tabla_y_las_estadisticas(self):
        tabla = self.pagina()
        self.assertEqual([f['dni'] for f in tabla.rows], ['12345678'])
        fila = tabla.rows[0]
        self.assertEqual((fila['nombre'], fila['vencimiento'], fila['debe']), ('Ana Pérez', '07/11/2026', '-'))
        self.assertNotIn('password', fila)
        estadisticas = [e.texto for e in self.tipo('label') if 'stat-value' in e.clases]
        self.assertEqual(estadisticas, ['1', '0', '$22.000', '$22.000'])
        self.assertFalse(any('Contraseña' in str(c.get('label')) for c in tabla.kwargs['columns']))

    def test_la_tabla_no_muestra_contrasenas_en_ninguna_columna(self):
        tabla = self.pagina()
        self.assertEqual({c['name'] for c in tabla.kwargs['columns']},
                         {'dni', 'nombre', 'telefono', 'plan', 'nacimiento', 'vencimiento', 'activo', 'debe', 'acciones'})

    def test_filtros_de_la_tabla(self):
        self.nuevo_cliente('22222222', 'Luis Gómez', plan='2 veces por semana')
        tabla = self.pagina()
        self.uno('input', None).value = 'luis'
        tabla_buscador = [e for e in self.tipo('input')][0]
        tabla_buscador.value = 'luis'
        tabla_buscador.manejadores['value_change']()
        self.assertEqual([f['dni'] for f in tabla.rows], ['22222222'])
        tabla_buscador.value = ''
        self.uno('select', 'Filtrar por plan').value = 'Todos los días'
        self.uno('select', 'Filtrar por plan').manejadores['value_change']()
        self.assertEqual([f['dni'] for f in tabla.rows], ['12345678'])

    def test_paneles_de_cumpleanos_y_vencimientos(self):
        with db.escritura() as conn:
            conn.execute("UPDATE clientes SET fecha_nacimiento = '1990-10-08', fecha_vencimiento = '2026-10-10'")
        self.pagina()
        textos = stub.textos('label')
        self.assertIn('Ana Pérez (12345678)', textos)
        self.assertIn('🎉 ¡Hoy!', textos)
        self.assertTrue(any('10/10/2026 · en 2 días' in t for t in textos))

    def test_exportar_csv(self):
        self.pagina()
        self.uno('button', 'Exportar CSV').on_click()
        contenido, nombre = stub.DESCARGAS[0]
        self.assertEqual(nombre, 'clientes.csv')
        self.assertIn('Ana Pérez', contenido.decode('utf-8-sig'))

    def test_alta_de_cliente(self):
        recargas = []
        ui_clientes.abrir_formulario_cliente(lambda: recargas.append(1))
        self.uno('input', 'DNI (8 caracteres)').value = '87654321'
        self.uno('input', 'Nombre y Apellido').value = ' Marta Díaz '
        self.uno('input', 'Teléfono (10 caracteres)').value = '2615559999'
        monto = self.uno('number', 'Monto que abona ahora (primer pago)')
        self.assertEqual(monto.value, 15000)  # sugiere el precio del plan elegido por defecto
        plan = self.uno('select', 'Plan')
        plan.value = '3 veces por semana'
        plan.manejadores['value_change']()
        self.assertEqual(monto.value, 18000)  # al cambiar de plan, sugiere el precio del nuevo
        self.tipo('date')[0].value = '1992-02-02'
        self.uno('button', 'Guardar').on_click()

        c = clientes.buscar_cliente_por_dni('87654321')
        self.assertEqual((c['nombre'], c['plan'], c['fecha_nacimiento']), ('Marta Díaz', '3 veces por semana', '1992-02-02'))
        self.assertTrue(c['debe_cambiar_password'])
        self.assertEqual(c['historial'][0]['monto'], 18000)
        self.assertEqual(contabilidad.cargar_movimientos()[-1]['monto'], 18000)  # queda en la contabilidad
        self.assertEqual(recargas, [1])
        actividad = self.ultima_actividad()
        self.assertEqual(actividad['accion'], 'Cliente creado')
        self.assertIn('$18.000', actividad['detalle'])

    def test_alta_con_pago_parcial(self):
        ui_clientes.abrir_formulario_cliente(lambda: None)
        self.uno('input', 'DNI (8 caracteres)').value = '87654321'
        self.uno('input', 'Nombre y Apellido').value = 'Marta Díaz'
        self.uno('input', 'Teléfono (10 caracteres)').value = '2615559999'
        self.uno('number', 'Monto que abona ahora (primer pago)').value = 5000
        self.tipo('date')[0].value = '1992-02-02'
        self.uno('button', 'Guardar').on_click()
        c = clientes.buscar_cliente_por_dni('87654321')
        self.assertEqual(c['saldo_pendiente'], 10000)  # plan de 15.000, abonó 5.000

    def test_alta_rechaza_datos_invalidos(self):
        for dni, tel, nac, mensaje in [
            ('123', '2615559999', '1990-01-01', 'El DNI debe tener 8 dígitos'),
            ('1234567a', '2615559999', '1990-01-01', 'El DNI debe tener 8 dígitos'),
            ('87654321', '12345', '1990-01-01', 'El teléfono debe tener 10 dígitos'),
            ('87654321', '2615559999', None, 'Elegí la fecha de nacimiento'),
            ('12345678', '2615559999', '1990-01-01', 'Este DNI ya está registrado'),
            ('87654321', '2615559999', '1990-01-01', 'primer pago tiene que ser mayor a cero'),
        ]:
            self.pantalla_nueva()
            ui_clientes.abrir_formulario_cliente(lambda: None)
            self.uno('input', 'DNI (8 caracteres)').value = dni
            self.uno('input', 'Nombre y Apellido').value = 'X'
            self.uno('input', 'Teléfono (10 caracteres)').value = tel
            self.tipo('date')[0].value = nac
            if 'primer pago' in mensaje:
                self.uno('number', 'Monto que abona ahora (primer pago)').value = 0
            self.uno('button', 'Guardar').on_click()
            self.assertTrue(any(mensaje in n for n in self.notificaciones('negative')), mensaje)
        self.assertEqual(len(clientes.cargar_clientes()), 1)

    def test_edicion_de_cliente(self):
        ui_clientes.abrir_formulario_editar_cliente(self.dni, lambda: None)
        self.uno('input', 'Nombre y Apellido').value = 'Ana Gómez'
        self.uno('select', 'Plan').value = '2 veces por semana'
        self.uno('button', 'Guardar cambios').on_click()
        c = clientes.buscar_cliente_por_dni(self.dni)
        self.assertEqual((c['nombre'], c['plan']), ('Ana Gómez', '2 veces por semana'))
        self.assertEqual(self.ultima_actividad()['accion'], 'Cliente editado')

    def test_pago_completo_desde_la_tabla(self):
        tabla = self.pagina()
        tabla.manejadores['pagar'](evento(dni=self.dni, nombre='Ana Pérez'))
        self.assertEqual(self.uno('number', 'Monto que abona ahora').value, 22000)  # sugiere el precio del plan
        self.assertEqual(self.tipo('date')[0].value, '2026-11-07')                  # y 30 días desde hoy
        self.tipo('date')[0].value = '2026-12-01'
        self.uno('button', 'Confirmar pago').on_click()
        c = clientes.buscar_cliente_por_dni(self.dni)
        self.assertEqual(c['fecha_vencimiento'], '2026-12-01')
        self.assertEqual(len(c['historial']), 2)
        self.assertEqual(len(contabilidad.cargar_movimientos()), 2)  # el del alta y este pago
        actividad = self.ultima_actividad()
        self.assertEqual((actividad['accion'], actividad['actor']), ('Pago registrado', 'Dueña Uno'))
        self.assertIn('$22.000', actividad['detalle'])

    def test_pago_parcial_y_abono_de_saldo(self):
        from gimnasio.datos import pagos
        ui_clientes.abrir_dialogo_pago(self.dni, 'Ana Pérez', lambda: None)
        self.uno('number', 'Monto que abona ahora').value = 15000
        self.uno('button', 'Confirmar pago').on_click()
        self.assertEqual(clientes.buscar_cliente_por_dni(self.dni)['saldo_pendiente'], 7000)

        self.pantalla_nueva()
        ui_clientes.abrir_dialogo_pago(self.dni, 'Ana Pérez', lambda: None)
        self.assertTrue(self.hay_texto('Saldo pendiente actual: $7.000'))

        self.pantalla_nueva()
        ui_clientes.abrir_dialogo_abonar_deuda(self.dni, 'Ana Pérez', lambda: None)
        self.assertEqual(self.uno('number', 'Monto que abona').value, 7000)
        self.uno('number', 'Monto que abona').value = 3000
        self.uno('button', 'Registrar abono').on_click()
        self.assertEqual(clientes.buscar_cliente_por_dni(self.dni)['saldo_pendiente'], 4000)
        self.assertEqual(self.ultima_actividad()['accion'], 'Abono de saldo')

    def test_pago_con_monto_cero_o_sin_fecha_se_rechaza(self):
        ui_clientes.abrir_dialogo_pago(self.dni, 'Ana Pérez', lambda: None)
        self.uno('number', 'Monto que abona ahora').value = 0
        self.uno('button', 'Confirmar pago').on_click()
        self.assertIn('El monto abonado tiene que ser mayor a cero.', self.notificaciones('negative'))
        self.tipo('date')[0].value = None
        self.uno('button', 'Confirmar pago').on_click()
        self.assertIn('Elegí una fecha en el calendario.', self.notificaciones('negative'))
        self.assertEqual(len(clientes.buscar_cliente_por_dni(self.dni)['historial']), 1)

    def test_abono_sin_deuda(self):
        ui_clientes.abrir_dialogo_abonar_deuda(self.dni, 'Ana Pérez', lambda: None)
        self.assertTrue(self.hay_texto('no tiene saldo pendiente'))

    def test_historial(self):
        from gimnasio.datos import pagos
        pagos.registrar_pago(self.dni, '2026-12-01', 15000)
        ui_clientes.abrir_dialogo_historial(self.dni, 'Ana Pérez')
        filas = self.tipo('table')[0].rows
        self.assertEqual([f['monto'] for f in filas], ['$15.000', '$22.000'])  # del más nuevo al más viejo
        self.assertEqual(filas[0]['saldo'], '$7.000')

    def test_rutina(self):
        ui_clientes.abrir_dialogo_rutina(self.dni, 'Ana Pérez')
        self.tipo('editor')[0].value = '<b>Espalda</b><img src=x onerror=alert(1)>'
        self.uno('button', 'Guardar rutina').on_click()
        self.assertEqual(clientes.buscar_cliente_por_dni(self.dni)['rutina'], '<b>Espalda</b>')
        self.assertEqual(self.ultima_actividad()['accion'], 'Rutina actualizada')

    def test_el_dueno_elimina_un_cliente(self):
        tabla = self.pagina()
        tabla.manejadores['eliminar'](evento(dni=self.dni, nombre='Ana Pérez'))
        self.uno('button', 'Eliminar').on_click()
        self.assertIsNone(clientes.buscar_cliente_por_dni(self.dni))
        self.assertEqual(self.ultima_actividad()['accion'], 'Cliente eliminado')

    def test_el_profe_no_puede_eliminar_clientes(self):
        self.entrar_como('profe1')
        tabla = self.pagina()
        tabla.manejadores['eliminar'](evento(dni=self.dni, nombre='Ana Pérez'))
        self.assertIn('No tenés permisos para eliminar clientes.', self.notificaciones('negative'))
        self.assertIsNotNone(clientes.buscar_cliente_por_dni(self.dni))

    def test_el_profe_si_puede_cobrar_y_editar(self):
        self.entrar_como('profe1')
        tabla = self.pagina()
        tabla.manejadores['pagar'](evento(dni=self.dni, nombre='Ana Pérez'))
        self.uno('button', 'Confirmar pago').on_click()
        self.assertEqual(len(clientes.buscar_cliente_por_dni(self.dni)['historial']), 2)
        self.assertEqual(self.ultima_actividad()['actor'], 'Profe Uno')

    def test_el_boton_de_eliminar_solo_existe_para_el_dueno(self):
        def botones_de_la_fila():
            self.abrir('/')
            tabla = self.tipo('table')[0]
            return tabla

        self.pagina()  # no falla para el dueño
        self.entrar_como('profe1')
        self.pagina()  # ni para el profe

    def test_restablecer_la_clave_de_un_cliente(self):
        clientes.cambiar_password_cliente(self.dni, 'clave-propia-1')
        tabla = self.pagina()
        tabla.manejadores['resetear'](evento(dni=self.dni, nombre='Ana Pérez'))
        self.assertTrue(self.hay_texto('va a volver a ser su DNI'))
        self.uno('button', 'Restablecer').on_click()
        c = clientes.buscar_cliente_por_dni(self.dni)
        self.assertTrue(c['debe_cambiar_password'])
        self.assertTrue(clientes.verificar_password_cliente(c, self.dni))
        self.assertEqual(self.ultima_actividad()['accion'], 'Contraseña de cliente restablecida')

    def test_todos_los_eventos_de_la_tabla_estan_conectados(self):
        tabla = self.pagina()
        self.assertEqual(set(tabla.manejadores),
                         {'editar', 'pagar', 'abonar', 'historial', 'rutina', 'eliminar', 'resetear'})
        for nombre in ('editar', 'abonar', 'historial', 'rutina'):
            self.pantalla_nueva()
            tabla.manejadores[nombre](evento(dni=self.dni, nombre='Ana Pérez'))


# ============================================================ cuentas del personal

class TestUsuarios(BaseUi):
    def setUp(self):
        super().setUp()
        self.entrar_como('dueno1')

    def id_de(self, username):
        return usuarios.obtener_usuario(username)['id']

    def test_listado_sin_contrasenas(self):
        self.abrir('/usuarios')
        tabla = self.tipo('table')[0]
        self.assertEqual({f['username'] for f in tabla.rows}, {'dueno1', 'profe1'})
        self.assertEqual(set(tabla.rows[0]), {'id', 'username', 'nombre', 'rol'})
        self.assertFalse(any('CONTRASEÑA' in str(c['label']).upper() for c in tabla.kwargs['columns']))

    def test_alta(self):
        ui_usuarios.abrir_formulario_usuario(lambda: None)
        self.uno('input', 'Usuario').value = 'profe2'
        self.uno('input', 'Nombre completo').value = 'Profe Dos'
        self.uno('input', 'Contraseña').value = 'clave-larga-2'
        self.uno('select', 'Rol').value = 'profe'
        self.uno('button', 'Crear usuario').on_click()
        u = usuarios.obtener_usuario('profe2')
        self.assertEqual((u['nombre'], u['rol']), ('Profe Dos', 'profe'))
        self.assertTrue(seguridad.verificar_password('clave-larga-2', u['salt'], u['password_hash']))
        self.assertEqual(self.ultima_actividad()['accion'], 'Usuario creado')

    def test_alta_rechaza_casos_invalidos(self):
        for usuario, nombre, clave, mensaje in [
            ('', 'X', 'clave-larga-2', 'Usuario y nombre son obligatorios'),
            ('nuevo', 'X', 'corta', 'al menos 8 caracteres'),
            ('profe1', 'X', 'clave-larga-2', 'ya existe'),
        ]:
            self.pantalla_nueva()
            ui_usuarios.abrir_formulario_usuario(lambda: None)
            self.uno('input', 'Usuario').value = usuario
            self.uno('input', 'Nombre completo').value = nombre
            self.uno('input', 'Contraseña').value = clave
            self.uno('button', 'Crear usuario').on_click()
            self.assertTrue(any(mensaje in n for n in self.notificaciones('negative')), mensaje)
        self.assertEqual(len(usuarios.obtener_todos_usuarios()), 2)

    def test_edicion_con_y_sin_cambio_de_clave(self):
        uid = self.id_de('profe1')
        ui_usuarios.abrir_formulario_editar_usuario(uid, lambda: None)
        self.uno('input', 'Nombre completo').value = 'Profe Renombrado'
        self.uno('button', 'Guardar cambios').on_click()
        u = usuarios.obtener_usuario('profe1')
        self.assertEqual(u['nombre'], 'Profe Renombrado')
        self.assertTrue(seguridad.verificar_password('clave-profe-1', u['salt'], u['password_hash']))

        self.pantalla_nueva()
        ui_usuarios.abrir_formulario_editar_usuario(uid, lambda: None)
        self.uno('input', 'Nueva contraseña (opcional)').value = 'otra-clave-larga'
        self.uno('button', 'Guardar cambios').on_click()
        u = usuarios.obtener_usuario('profe1')
        self.assertTrue(seguridad.verificar_password('otra-clave-larga', u['salt'], u['password_hash']))
        self.assertEqual(self.ultima_actividad()['accion'], 'Usuario editado')

    def test_clave_nueva_corta_en_la_edicion(self):
        ui_usuarios.abrir_formulario_editar_usuario(self.id_de('profe1'), lambda: None)
        self.uno('input', 'Nueva contraseña (opcional)').value = 'corta'
        self.uno('button', 'Guardar cambios').on_click()
        self.assertTrue(any('al menos 8' in n for n in self.notificaciones('negative')))

    def test_no_se_puede_quitar_el_rol_al_ultimo_dueno(self):
        ui_usuarios.abrir_formulario_editar_usuario(self.id_de('dueno1'), lambda: None)
        self.uno('select', 'Rol').value = 'profe'
        self.uno('button', 'Guardar cambios').on_click()
        self.assertIn('Tiene que quedar al menos una cuenta de dueño.', self.notificaciones('negative'))
        self.assertEqual(usuarios.obtener_usuario('dueno1')['rol'], 'dueño')

    def test_editarse_a_uno_mismo_actualiza_la_sesion(self):
        ui_usuarios.abrir_formulario_editar_usuario(self.id_de('dueno1'), lambda: None)
        self.uno('input', 'Nombre completo').value = 'Dueña Renombrada'
        self.uno('button', 'Guardar cambios').on_click()
        self.assertEqual(stub.app.storage.user['nombre'], 'Dueña Renombrada')

    def eliminar(self, username):
        self.abrir('/usuarios')
        tabla = self.tipo('table')[0]
        tabla.manejadores['eliminar'](evento(id=self.id_de(username)))

    def test_eliminar_un_profe(self):
        self.eliminar('profe1')
        self.assertIsNone(usuarios.obtener_usuario('profe1'))
        self.assertEqual(self.ultima_actividad()['accion'], 'Usuario eliminado')

    def test_no_se_puede_eliminar_la_propia_cuenta(self):
        self.eliminar('dueno1')
        self.assertIn('No podés eliminar tu propia cuenta.', self.notificaciones('negative'))
        self.assertIsNotNone(usuarios.obtener_usuario('dueno1'))

    def test_no_se_puede_eliminar_a_admin_ni_al_ultimo_dueno(self):
        usuarios.crear_usuario('admin', 'clave-admin-1', 'Admin', 'dueño')
        self.eliminar('admin')
        self.assertIn('Esta cuenta no se puede eliminar.', self.notificaciones('negative'))
        self.assertIsNotNone(usuarios.obtener_usuario('admin'))

        usuarios.eliminar_usuario(self.id_de('admin'))
        usuarios.crear_usuario('dueno2', 'clave-dueno-2', 'Otro', 'dueño')
        self.entrar_como('profe1')  # un profe no llega ni a ver la página
        self.abrir('/usuarios')
        self.assertEqual(stub.NAVEGACIONES, ['/'])

    def test_un_profe_no_puede_eliminar_usuarios_ni_con_el_evento_directo(self):
        from gimnasio.ui import sesion
        self.abrir('/usuarios')
        tabla = self.tipo('table')[0]
        self.entrar_como('profe1')  # la sesión cambió mientras la pantalla seguía abierta
        tabla.manejadores['eliminar'](evento(id=self.id_de('dueno1')))
        self.assertIn('No tenés permisos para eliminar usuarios.', self.notificaciones('negative'))
        self.assertIsNotNone(usuarios.obtener_usuario('dueno1'))


class TestCambiarMiClave(BaseUi):
    def test_cambio_de_la_propia_clave(self):
        self.entrar_como('profe1')
        navbar.abrir_dialogo_cambiar_mi_password()
        self.uno('input', 'Contraseña actual').value = 'clave-profe-1'
        self.uno('input', 'Nueva contraseña').value = 'clave-nueva-1'
        self.uno('input', 'Confirmar nueva contraseña').value = 'clave-nueva-1'
        self.uno('button', 'Guardar').on_click()
        u = usuarios.obtener_usuario('profe1')
        self.assertTrue(seguridad.verificar_password('clave-nueva-1', u['salt'], u['password_hash']))
        self.assertEqual(self.ultima_actividad()['accion'], 'Cambió su contraseña')

    def test_rechazos(self):
        self.entrar_como('profe1')
        for actual, nueva, conf, mensaje in [
            ('mala', 'clave-nueva-1', 'clave-nueva-1', 'actual no es correcta'),
            ('clave-profe-1', 'corta', 'corta', 'al menos 8'),
            ('clave-profe-1', 'clave-nueva-1', 'distinta-1234', 'no coinciden'),
        ]:
            self.pantalla_nueva()
            navbar.abrir_dialogo_cambiar_mi_password()
            self.uno('input', 'Contraseña actual').value = actual
            self.uno('input', 'Nueva contraseña').value = nueva
            self.uno('input', 'Confirmar nueva contraseña').value = conf
            self.uno('button', 'Guardar').on_click()
            self.assertTrue(any(mensaje in n for n in self.notificaciones('negative')), mensaje)
        u = usuarios.obtener_usuario('profe1')
        self.assertTrue(seguridad.verificar_password('clave-profe-1', u['salt'], u['password_hash']))


# ============================================================ páginas del dueño

class TestPaginasDelDueno(BaseUi):
    def setUp(self):
        super().setUp()
        self.entrar_como('dueno1')

    def test_precios(self):
        self.abrir('/precios')
        self.assertEqual(self.uno('number', 'Todos los días').value, 22000)
        self.uno('number', 'Todos los días').value = 30000
        self.uno('button', 'Guardar precios').on_click()
        self.assertEqual(ajustes.precio_de_plan('Todos los días'), 30000)
        self.assertEqual(self.ultima_actividad()['accion'], 'Precios actualizados')

    def test_informacion(self):
        self.abrir('/informacion')
        self.tipo('textarea')[0].value = '  Abrimos a las 8  '
        self.uno('button', 'Guardar cambios').on_click()
        self.assertEqual(ajustes.cargar_informacion(), 'Abrimos a las 8')
        self.assertEqual(self.ultima_actividad()['accion'], 'Información para clientes actualizada')

    def test_anuncios(self):
        self.abrir('/anuncios')
        self.uno('button', 'Publicar').on_click()
        self.assertIn('Escribí un texto antes de publicar.', self.notificaciones('negative'))
        self.tipo('textarea')[0].value = 'Feriado: cerrado'
        self.uno('button', 'Publicar').on_click()
        self.assertEqual([a['texto'] for a in ajustes.cargar_anuncios()], ['Feriado: cerrado'])
        borrar = [e for e in self.tipo('button') if e.kwargs.get('icon') == 'delete'][-1]
        borrar.on_click()
        self.assertEqual(ajustes.cargar_anuncios(), [])
        self.assertEqual(self.ultima_actividad()['accion'], 'Anuncio eliminado')

    def test_los_anuncios_se_ven_en_el_portal_y_en_clientes(self):
        ajustes.agregar_anuncio('Aviso para todos')
        self.abrir('/')
        self.assertIn('Aviso para todos', stub.textos('label'))

    def test_contabilidad(self):
        self.abrir('/contabilidad')
        self.uno('number', 'Monto').value = 1500
        self.uno('input', 'Categoría (ej: Bebidas, Luz, Limpieza)').value = 'Bebidas'
        self.uno('button', 'Registrar').on_click()
        mov = contabilidad.cargar_movimientos()
        self.assertEqual((mov[-1]['tipo'], mov[-1]['categoria'], mov[-1]['monto']), ('ingreso', 'Bebidas', 1500))
        self.assertEqual(self.ultima_actividad()['accion'], 'Movimiento contable registrado')
        self.assertEqual(self.tipo('table')[0].rows[0]['ingresos'], '$23.500')  # cuota del alta + bebidas
        self.assertEqual(self.tipo('table')[1].rows[0]['categoria'], 'Bebidas')

    def test_contabilidad_rechaza_monto_cero_o_sin_categoria(self):
        self.abrir('/contabilidad')
        self.uno('button', 'Registrar').on_click()
        self.assertIn('El monto tiene que ser mayor a cero.', self.notificaciones('negative'))
        self.uno('number', 'Monto').value = 100
        self.uno('button', 'Registrar').on_click()
        self.assertTrue(any('categoría' in n for n in self.notificaciones('negative')))
        self.assertEqual(len(contabilidad.cargar_movimientos()), 1)  # solo el del alta

    def test_contabilidad_eliminar_movimiento(self):
        contabilidad.registrar_movimiento('egreso', 'Luz', 'Factura', 4000)
        self.abrir('/contabilidad')
        tabla_mov = self.tipo('table')[1]
        tabla_mov.manejadores['eliminar'](evento(id=tabla_mov.rows[0]['id']))
        self.assertEqual([m['categoria'] for m in contabilidad.cargar_movimientos()], ['Cuota'])

    def test_respaldos(self):
        self.abrir('/respaldos')
        self.assertEqual(self.tipo('table')[0].rows, [])
        self.uno('button', 'Crear una copia ahora').on_click()
        self.assertEqual(len(respaldos.listar_respaldos()), 1)
        self.assertEqual(len(self.tipo('table')[0].rows), 1)
        self.assertEqual(self.ultima_actividad()['accion'], 'Copia de seguridad creada')

        self.uno('button', 'Descargar copia (.zip)').on_click()
        contenido, nombre = stub.DESCARGAS[0]
        self.assertTrue(contenido.startswith(b'PK'))
        self.assertTrue(nombre.startswith('vida-fitness-') and nombre.endswith('.zip'))
        self.assertEqual(self.ultima_actividad()['accion'], 'Copia de seguridad descargada')

    def test_actividad(self):
        auditoria.registrar('Dueña Uno', 'Pago registrado', 'Ana (DNI 1): $22.000')
        self.abrir('/actividad')
        filas = self.tipo('table')[0].rows
        self.assertEqual(filas[0]['accion'], 'Pago registrado')
        self.assertRegex(filas[0]['fecha'], r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$')


# ============================================================ app instalable y salud

class TestPwa(BaseUi):
    def test_manifest(self):
        m = pwa.datos_manifest()
        self.assertEqual((m['start_url'], m['display']), ('/', 'standalone'))
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for icono in m['icons']:
            self.assertTrue(os.path.isfile(os.path.join(raiz, 'static', os.path.basename(icono['src']))), icono['src'])

    def test_carpeta_de_iconos_publicada(self):
        self.assertTrue(any(url == '/static-vf' for url, _ in stub.app.estaticos))

    def test_salud(self):
        self.assertTrue(pwa.estado_salud())
        respuesta = stub.RUTAS['/health']()
        self.assertEqual(respuesta.status_code, 200)

    def test_salud_con_la_base_caida(self):
        from unittest import mock
        with mock.patch.object(db, 'lectura', side_effect=RuntimeError('caída')):
            self.assertFalse(pwa.estado_salud())
            self.assertEqual(stub.RUTAS['/health']().status_code, 503)

    def test_service_worker_y_manifest_por_http(self):
        self.assertIn('fetch', stub.RUTAS['/sw.js']().body.decode('utf-8'))
        self.assertEqual(json.loads(stub.RUTAS['/manifest.webmanifest']().body)['short_name'], 'Vida Fitness')

    def test_cabeceras_de_seguridad(self):
        self.assertIn(pwa._CabecerasSeguridad, stub.app.middlewares)

        async def probar():
            respuesta = SimpleNamespace(headers={})

            async def siguiente(_):
                return respuesta

            return await pwa._CabecerasSeguridad(None).dispatch(None, siguiente)

        headers = asyncio.run(probar()).headers
        self.assertEqual(headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')


if __name__ == '__main__':
    unittest.main()
