"""Piezas de interfaz reutilizables."""

from nicegui import ui


def html_confiable(contenido):
    """Muestra HTML que ya es de confianza (el logo fijo, o la rutina ya pasada
    por sanitizar_html). NiceGUI 3.x exige indicar el parámetro 'sanitize'; las
    versiones anteriores no lo conocen, así que se prueba primero con él y, si
    no existe, sin él."""
    try:
        return ui.html(contenido, sanitize=False)
    except TypeError:
        return ui.html(contenido)



