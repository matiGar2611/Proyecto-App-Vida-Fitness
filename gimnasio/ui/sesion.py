"""Sesión del navegador: quién está logueado y qué puede hacer."""

from nicegui import app, ui

from ..datos import auditoria
from ..datos.clientes import buscar_cliente_por_dni
from ..datos.usuarios import obtener_usuario_por_id


# El rol 'cliente' NO vive en la tabla de usuarios: se arma en el momento del
# login por DNI (ver pagina_login) y se guarda solo en app.storage.user.

def sesion_valida():
    """Comprueba que la sesión guardada en el navegador siga correspondiendo
    a una cuenta que existe (y con el mismo rol). Así, si se borra un
    profe, se le cambia el rol o se elimina un cliente, su sesión abierta
    deja de funcionar en el momento."""
    rol = app.storage.user.get('rol')
    if rol is None:
        return False
    if rol == 'cliente':
        dni = app.storage.user.get('dni')
        return bool(dni) and buscar_cliente_por_dni(dni) is not None
    registro = obtener_usuario_por_id(app.storage.user.get('id'))
    return registro is not None and registro[5] == rol


def verificar_autenticacion():
    """Indica si hay una sesión activa y válida (dueño, profe o cliente) en este navegador."""
    if 'rol' not in app.storage.user:
        return False
    if not sesion_valida():
        app.storage.user.clear()
        return False
    return True


def rol_actual():
    """Devuelve el rol de la sesión activa ('dueño', 'profe' o 'cliente'), o None si no hay sesión."""
    return app.storage.user.get('rol')


def dni_actual():
    """Devuelve el DNI guardado en la sesión cuando el rol activo es 'cliente'."""
    return app.storage.user.get('dni')


def es_dueño():
    """Indica si la sesión activa corresponde al rol 'dueño' (y sigue siendo válida)."""
    return rol_actual() == 'dueño' and sesion_valida()


def es_cliente_rol():
    """Indica si la sesión activa corresponde al rol 'cliente'."""
    return rol_actual() == 'cliente'


def requerir_autenticacion():
    """Redirige a /login si no hay sesión activa. Se llama al principio de cada página que exige estar logueado."""
    if not verificar_autenticacion():
        ui.navigate.to('/login')
        return False
    return True


def cerrar_sesion():
    """Borra los datos de la sesión activa y vuelve a la pantalla de login."""
    app.storage.user.clear()
    ui.notify('Sesión cerrada', type='info')
    ui.navigate.to('/login')




def actor_actual():
    """Nombre de quien está usando la app, para el registro de actividad."""
    if es_cliente_rol():
        return f"Cliente {dni_actual()}"
    return app.storage.user.get('nombre') or app.storage.user.get('username') or '(desconocido)'


def registrar_actividad(accion, detalle=''):
    """Anota en el registro de actividad una acción hecha por la persona logueada."""
    auditoria.registrar(actor_actual(), accion, detalle)
