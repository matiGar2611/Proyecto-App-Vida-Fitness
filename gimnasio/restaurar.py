"""Restaura la base de datos desde una copia de seguridad.

Uso:
    python -m gimnasio.restaurar RUTA_DE_LA_COPIA.db

Conviene hacerlo sin que nadie esté usando la app. Antes de restaurar se guarda
una copia '-previo' de la base actual, por si hay que deshacer.
"""

import sys

from . import db
from .servicios import respaldos


def main(argumentos):
    if len(argumentos) != 1:
        print(__doc__)
        return 1
    db.inicializar()
    try:
        previo = respaldos.restaurar_respaldo(argumentos[0])
    except ValueError as error:
        print(f"No se pudo restaurar: {error}")
        return 1
    print(f"Listo. La base anterior quedó guardada en: {previo}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
