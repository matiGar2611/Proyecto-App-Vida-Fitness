"""Cambia la contraseña de una cuenta del personal desde la consola.

Sirve cuando se olvidó la contraseña (o el dueño se quedó sin poder entrar).

Uso:
    python -m gimnasio.cambiar_clave USUARIO

Hay que correrlo con la misma variable DATA_DIR que usa la app, porque es la
que dice dónde está la base de datos. En Render: pestaña Shell del servicio
(disponible en los planes pagos).
"""

import getpass
import os
import sys

from . import config, db
from .datos import auditoria, usuarios


def main(argumentos, pedir_clave=getpass.getpass):
    if len(argumentos) != 1:
        print(__doc__)
        return 1

    if not os.path.exists(db.ruta_db()):
        print(f"No encontré la base de datos en: {db.ruta_db()}")
        print("Revisá que DATA_DIR sea la misma carpeta que usa la app.")
        return 1

    db.inicializar()
    registro = usuarios.obtener_usuario(argumentos[0])
    if registro is None:
        existentes = ', '.join(u['username'] for u in usuarios.obtener_todos_usuarios()) or '(ninguna)'
        print(f"No existe la cuenta '{argumentos[0]}'. Cuentas que hay: {existentes}")
        return 1

    nueva = pedir_clave("Nueva contraseña: ")
    if len(nueva) < config.MIN_PASSWORD_PERSONAL:
        print(f"La contraseña tiene que tener al menos {config.MIN_PASSWORD_PERSONAL} caracteres.")
        return 1
    if pedir_clave("Repetila: ") != nueva:
        print("Las contraseñas no coinciden.")
        return 1

    usuarios.actualizar_usuario(registro['id'], registro['username'], registro['nombre'], registro['rol'], nueva)
    auditoria.registrar('Consola', 'Contraseña cambiada desde la consola', registro['username'])
    print(f"Listo: cambiaste la contraseña de '{registro['username']}'.")
    print("Si la cuenta estaba bloqueada por intentos fallidos, esperá 5 minutos o reiniciá la app.")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
