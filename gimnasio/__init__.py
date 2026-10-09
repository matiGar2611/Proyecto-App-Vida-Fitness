"""Gestor de gimnasio Vida Fitness.

Organización del paquete:
    config.py       constantes y variables de entorno
    tiempo.py       fechas y formatos (hora de Argentina)
    seguridad.py    contraseñas, límite de intentos, HTML y CSV seguros
    db.py           conexión y esquema de la base SQLite
    datos/          acceso a los datos (usuarios, clientes, pagos, ...)
    servicios/      lógica: estadísticas, respaldos, migración
    ui/             pantallas (NiceGUI)
    arranque.py     preparación al iniciar la app

Todo lo que no está en ui/ funciona sin NiceGUI, por eso se puede probar solo.
"""
