"""Consultas y cálculos sobre los clientes: vencimientos, cumpleaños,
ingresos, filtros de la tabla y exportación a CSV."""

import io
from datetime import date

from .. import db, seguridad, tiempo
from ..datos import ajustes, clientes as repo_clientes


# ---- Estado de la cuota ----

def esta_vencido(cliente):
    """True si la fecha de vencimiento del cliente ya pasó."""
    fecha = tiempo.parsear_fecha(cliente.get('fecha_vencimiento'))
    return fecha is not None and fecha < tiempo.hoy()


def dias_para_vencimiento(cliente):
    """Positivo: días que faltan para vencer. Negativo: días desde que venció."""
    fecha = tiempo.parsear_fecha(cliente.get('fecha_vencimiento'))
    if fecha is None:
        return 0
    return (fecha - tiempo.hoy()).days


def contadores():
    """(clientes activos, cuotas vencidas)."""
    todos = repo_clientes.cargar_clientes()
    return sum(1 for c in todos if c['activo']), sum(1 for c in todos if esta_vencido(c))


def proximos_vencimientos(dias_rango=7):
    """Clientes cuya cuota vence dentro de los próximos 'dias_rango' días
    (los que ya vencieron no entran: figuran en 'Cuotas vencidas')."""
    resultados = []
    for cliente in repo_clientes.cargar_clientes():
        dias = dias_para_vencimiento(cliente)
        if 0 <= dias <= dias_rango:
            resultados.append({
                "nombre": cliente['nombre'],
                "dni": cliente['dni'],
                "fecha": tiempo.formatear_fecha(cliente['fecha_vencimiento']),
                "dias": dias,
                "vence_hoy": dias == 0,
            })
    resultados.sort(key=lambda r: r["dias"])
    return resultados


def proximos_cumpleanos(dias_rango=30):
    """Cumpleaños dentro de 'dias_rango' días, del más próximo al más lejano.
    Compara solo mes y día (sin importar el año de nacimiento)."""
    hoy = tiempo.hoy()
    resultados = []
    for cliente in repo_clientes.cargar_clientes():
        nacimiento = tiempo.parsear_fecha(cliente.get('fecha_nacimiento'))
        if nacimiento is None:
            continue

        proximo = _con_anio(nacimiento, hoy.year)
        if proximo < hoy:
            proximo = _con_anio(nacimiento, hoy.year + 1)

        faltan = (proximo - hoy).days
        if faltan <= dias_rango:
            resultados.append({
                "nombre": cliente['nombre'],
                "dni": cliente['dni'],
                "fecha": proximo.strftime("%d/%m"),
                "dias_faltantes": faltan,
                "es_hoy": faltan == 0,
            })
    resultados.sort(key=lambda r: r["dias_faltantes"])
    return resultados


def _con_anio(fecha, anio):
    """La misma fecha en otro año (el 29/02 pasa al 28/02 si ese año no es bisiesto)."""
    try:
        return fecha.replace(year=anio)
    except ValueError:
        return fecha.replace(year=anio, day=28)


# ---- Ingresos ----

def ingresos_esperados_mensuales():
    """Lo que el gimnasio factura por mes si todos los clientes activos pagaran en fecha."""
    precios = ajustes.cargar_precios()
    return sum(precios.get(c['plan'], 0) for c in repo_clientes.cargar_clientes() if c['activo'])


def ingresos_cobrados_mes_actual():
    """Suma de los pagos del historial hechos en el mes y año actuales."""
    hoy = tiempo.hoy()
    primero = date(hoy.year, hoy.month, 1)
    siguiente = date(hoy.year + (hoy.month == 12), hoy.month % 12 + 1, 1)
    with db.lectura() as conn:
        return conn.execute(
            "SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE fecha >= ? AND fecha < ?",
            (str(primero), str(siguiente)),
        ).fetchone()[0]


# ---- Tabla de clientes ----

def _coincide_busqueda(cliente, busqueda):
    if not busqueda:
        return True
    busqueda = busqueda.strip().lower()
    return busqueda in cliente['dni'].lower() or busqueda in cliente['nombre'].lower()


def filtrar_clientes(solo_vencidos=False, plan_filtro="Todos", busqueda=""):
    """Clientes que cumplen los filtros. La usan la tabla y la exportación a CSV,
    así el criterio queda en un solo lugar."""
    resultado = []
    for cliente in repo_clientes.cargar_clientes():
        if solo_vencidos and not esta_vencido(cliente):
            continue
        if plan_filtro != "Todos" and cliente['plan'] != plan_filtro:
            continue
        if not _coincide_busqueda(cliente, busqueda):
            continue
        resultado.append(cliente)
    return resultado


def obtener_filas(solo_vencidos=False, plan_filtro="Todos", busqueda=""):
    """Filas ya formateadas para la tabla de clientes (sin ningún dato de contraseña)."""
    filas = []
    for cliente in filtrar_clientes(solo_vencidos, plan_filtro, busqueda):
        saldo = cliente['saldo_pendiente']
        filas.append({
            "dni": cliente['dni'],
            "nombre": cliente['nombre'],
            "telefono": cliente['telefono'],
            "plan": cliente['plan'],
            "nacimiento": tiempo.formatear_fecha(cliente['fecha_nacimiento'])
                          if cliente.get('fecha_nacimiento') else "-",
            "vencimiento": tiempo.formatear_fecha(cliente['fecha_vencimiento']),
            "activo": "Sí" if cliente['activo'] else "No",
            "debe": tiempo.formatear_moneda(saldo) if saldo > 0 else "-",
        })
    return filas


def exportar_clientes_csv(solo_vencidos=False, plan_filtro="Todos", busqueda=""):
    """Contenido de un CSV (texto) con los clientes que cumplen los filtros.
    Usa ';' como separador porque Excel en configuración regional argentina lo
    interpreta mejor que ','."""
    buffer = io.StringIO()
    escritor = seguridad.EscritorCSVSeguro(buffer, delimiter=';')
    escritor.writerow([
        'DNI', 'Nombre y Apellido', 'Teléfono', 'Plan', 'Fecha de nacimiento',
        'Fecha de inicio', 'Fecha de vencimiento', 'Fecha ultimo pago', 'Activo',
    ])
    for cliente in filtrar_clientes(solo_vencidos, plan_filtro, busqueda):
        escritor.writerow([
            cliente['dni'], cliente['nombre'], cliente['telefono'], cliente['plan'],
            cliente.get('fecha_nacimiento') or '', cliente['fecha_inicio'],
            cliente['fecha_vencimiento'], cliente['fecha_ultimo_pago'],
            'Sí' if cliente['activo'] else 'No',
        ])
    return buffer.getvalue()
