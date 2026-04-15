"""
Módulo centralizado para verificación y corrección de fechas en RIPS-JSON.
Asegura que todas las fechas de los servicios estén dentro del mes evaluado.
"""

from datetime import datetime, timedelta
from typing import Tuple, Dict, Any


def verificar_fecha(fecha_str: str, mes_evaluado: int, anio_evaluado: int) -> str:
    """
    Verifica si una fecha está dentro del mes evaluado.
    Si no pertenece, la ajusta al primer día del mes evaluado a las 00:00.
    
    Args:
        fecha_str: Fecha en formato "YYYY-MM-DD HH:MM"
        mes_evaluado: Número del mes (1-12)
        anio_evaluado: Año (ej: 2025)
    
    Returns:
        Fecha corregida en formato "YYYY-MM-DD HH:MM"
    
    Example:
        >>> verificar_fecha("2025-09-07 15:20", 10, 2025)
        "2025-10-01 00:00"
    """
    try:
        # Limpiar espacios extra en la fecha
        fecha_str = ' '.join(fecha_str.split())
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
        
        # Verificar si la fecha está dentro del mes evaluado
        if fecha.month != mes_evaluado or fecha.year != anio_evaluado:
            # Ajustar al primer día del mes evaluado a las 00:00
            fecha_corregida = datetime(anio_evaluado, mes_evaluado, 1, 0, 0)
            return fecha_corregida.strftime("%Y-%m-%d %H:%M")
        
        return fecha_str
    
    except (ValueError, TypeError):
        # Si la fecha no es válida, retornar primer día del mes
        return datetime(anio_evaluado, mes_evaluado, 1, 0, 0).strftime("%Y-%m-%d %H:%M")


def verificar_rango(fecha_inicio_str: str, fecha_egreso_str: str, 
                   mes_evaluado: int, anio_evaluado: int) -> Tuple[str, str]:
    """
    Verifica y corrige un rango de fechas (hospitalización, urgencias).
    
    Reglas:
    - Ajusta fechaInicioAtencion al primer día del mes si está fuera.
    - Recalcula fechaEgreso manteniendo la duración original.
    - Si la duración excede el mes evaluado, fechaEgreso se asigna al último día del mes a las 23:59.
    
    Args:
        fecha_inicio_str: Fecha de inicio en formato "YYYY-MM-DD HH:MM"
        fecha_egreso_str: Fecha de egreso en formato "YYYY-MM-DD HH:MM"
        mes_evaluado: Número del mes (1-12)
        anio_evaluado: Año (ej: 2025)
    
    Returns:
        Tupla (fecha_inicio_corregida, fecha_egreso_corregida)
    
    Example:
        >>> verificar_rango("2025-09-20 10:00", "2025-11-02 10:00", 10, 2025)
        ("2025-10-01 00:00", "2025-10-31 23:59")
    """
    try:
        # Limpiar espacios extra en las fechas
        fecha_inicio_str = ' '.join(fecha_inicio_str.split())
        fecha_egreso_str = ' '.join(fecha_egreso_str.split())
        
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d %H:%M")
        fecha_egreso = datetime.strptime(fecha_egreso_str, "%Y-%m-%d %H:%M")
        
        # Calcular duración original
        duracion = fecha_egreso - fecha_inicio
        
        # Ajustar inicio si está fuera del mes
        if fecha_inicio.month != mes_evaluado or fecha_inicio.year != anio_evaluado:
            fecha_inicio = datetime(anio_evaluado, mes_evaluado, 1, 0, 0)
        
        # Calcular egreso corregido manteniendo la duración
        fecha_egreso_corregida = fecha_inicio + duracion
        
        # Calcular el último día del mes evaluado a las 23:59
        if mes_evaluado == 12:
            primer_dia_mes_siguiente = datetime(anio_evaluado + 1, 1, 1)
        else:
            primer_dia_mes_siguiente = datetime(anio_evaluado, mes_evaluado + 1, 1)
        
        ultimo_dia_mes = primer_dia_mes_siguiente - timedelta(minutes=1)
        
        # Si la fecha de egreso excede el mes evaluado, ajustar al último día
        if fecha_egreso_corregida.month != mes_evaluado or fecha_egreso_corregida.year != anio_evaluado:
            fecha_egreso_corregida = ultimo_dia_mes
        
        return (
            fecha_inicio.strftime("%Y-%m-%d %H:%M"),
            fecha_egreso_corregida.strftime("%Y-%m-%d %H:%M")
        )
    
    except (ValueError, TypeError):
        # Si hay error, retornar primer día del mes para ambas fechas
        primer_dia = datetime(anio_evaluado, mes_evaluado, 1, 0, 0).strftime("%Y-%m-%d %H:%M")
        return (primer_dia, primer_dia)


def aplicar_verificacion_servicio(servicio: Dict[str, Any], tipo_servicio: str, 
                                  mes_evaluado: int, anio_evaluado: int) -> Dict[str, Any]:
    """
    Aplica la verificación de fechas a un servicio según su tipo.
    
    Args:
        servicio: Diccionario con los datos del servicio
        tipo_servicio: Tipo de servicio (consultas, medicamentos, procedimientos, etc.)
        mes_evaluado: Número del mes (1-12)
        anio_evaluado: Año
    
    Returns:
        Servicio con fechas corregidas
    """
    servicio_corregido = servicio.copy()
    
    # Mapeo de campos de fecha según tipo de servicio
    if tipo_servicio in ['consultas', 'procedimientos']:
        if 'fechaInicioAtencion' in servicio_corregido:
            servicio_corregido['fechaInicioAtencion'] = verificar_fecha(
                servicio_corregido['fechaInicioAtencion'], 
                mes_evaluado, 
                anio_evaluado
            )
    
    elif tipo_servicio == 'medicamentos':
        if 'fechaDispensAdmon' in servicio_corregido:
            servicio_corregido['fechaDispensAdmon'] = verificar_fecha(
                servicio_corregido['fechaDispensAdmon'], 
                mes_evaluado, 
                anio_evaluado
            )
    
    elif tipo_servicio == 'otrosServicios':
        if 'fechaSuministroTecnologia' in servicio_corregido:
            servicio_corregido['fechaSuministroTecnologia'] = verificar_fecha(
                servicio_corregido['fechaSuministroTecnologia'], 
                mes_evaluado, 
                anio_evaluado
            )
    
    elif tipo_servicio in ['urgencias', 'hospitalizacion']:
        if 'fechaInicioAtencion' in servicio_corregido and 'fechaEgreso' in servicio_corregido:
            fecha_inicio_corr, fecha_egreso_corr = verificar_rango(
                servicio_corregido['fechaInicioAtencion'],
                servicio_corregido['fechaEgreso'],
                mes_evaluado,
                anio_evaluado
            )
            servicio_corregido['fechaInicioAtencion'] = fecha_inicio_corr
            servicio_corregido['fechaEgreso'] = fecha_egreso_corr
    
    return servicio_corregido


def aplicar_verificacion_json(datos: Dict[str, Any], mes_evaluado: int, 
                              anio_evaluado: int, generar_reporte: bool = False) -> tuple:
    """
    Aplica la verificación de fechas a todos los servicios de un JSON RIPS.
    
    Args:
        datos: Diccionario con la estructura completa del RIPS-JSON
        mes_evaluado: Número del mes (1-12)
        anio_evaluado: Año
        generar_reporte: Si True, retorna también la lista de cambios
    
    Returns:
        Si generar_reporte=False: JSON con todas las fechas corregidas
        Si generar_reporte=True: (JSON corregido, lista de cambios)
    """
    import copy
    datos_corregidos = copy.deepcopy(datos)
    cambios = [] if generar_reporte else None
    
    # Tipos de servicios que pueden estar en el JSON
    tipos_servicios = [
        'consultas', 
        'medicamentos', 
        'procedimientos', 
        'otrosServicios', 
        'urgencias', 
        'hospitalizacion'
    ]
    
    # Verificar si hay usuarios en el JSON
    if 'usuarios' in datos_corregidos and isinstance(datos_corregidos['usuarios'], list):
        for idx_usuario, usuario in enumerate(datos_corregidos['usuarios'], 1):
            num_doc_usuario = usuario.get('numDocumentoIdentificacion', 'Sin ID')
            
            if 'servicios' in usuario and isinstance(usuario['servicios'], dict):
                # Recorrer cada tipo de servicio dentro de usuario.servicios
                for tipo in tipos_servicios:
                    if tipo in usuario['servicios'] and isinstance(usuario['servicios'][tipo], list):
                        servicios_corregidos = []
                        for idx_servicio, servicio in enumerate(usuario['servicios'][tipo], 1):
                            servicio_original = copy.deepcopy(servicio) if generar_reporte else None
                            servicio_corregido = aplicar_verificacion_servicio(
                                servicio, 
                                tipo, 
                                mes_evaluado, 
                                anio_evaluado
                            )
                            servicios_corregidos.append(servicio_corregido)
                            
                            # Detectar cambios
                            if generar_reporte:
                                cambios_servicio = _detectar_cambios_fechas(
                                    servicio_original, servicio_corregido, tipo,
                                    num_doc_usuario, idx_usuario, idx_servicio
                                )
                                cambios.extend(cambios_servicio)
                        
                        usuario['servicios'][tipo] = servicios_corregidos
    
    # También procesar servicios en nivel raíz (por si hay estructura plana)
    for tipo in tipos_servicios:
        if tipo in datos_corregidos and isinstance(datos_corregidos[tipo], list):
            servicios_corregidos = []
            for idx_servicio, servicio in enumerate(datos_corregidos[tipo], 1):
                servicio_original = copy.deepcopy(servicio) if generar_reporte else None
                servicio_corregido = aplicar_verificacion_servicio(
                    servicio, 
                    tipo, 
                    mes_evaluado, 
                    anio_evaluado
                )
                servicios_corregidos.append(servicio_corregido)
                
                if generar_reporte:
                    cambios_servicio = _detectar_cambios_fechas(
                        servicio_original, servicio_corregido, tipo,
                        servicio.get('numDocumentoIdentificacion', 'Sin ID'), 
                        None, idx_servicio
                    )
                    cambios.extend(cambios_servicio)
            
            datos_corregidos[tipo] = servicios_corregidos
    
    if generar_reporte:
        return datos_corregidos, cambios
    return datos_corregidos


def _detectar_cambios_fechas(servicio_original: dict, servicio_corregido: dict, 
                             tipo_servicio: str, num_doc: str, 
                             idx_usuario: int, idx_servicio: int) -> list:
    """
    Detecta cambios entre servicio original y corregido.
    
    Returns:
        Lista de diccionarios con información de cada cambio
    """
    cambios = []
    
    # Campos de fecha según tipo de servicio
    campos_fecha_simple = ['fechaInicioAtencion', 'fechaPrescripcion', 'fechaDispensacion']
    campos_fecha_rango = [('fechaInicioAtencion', 'fechaEgreso')]
    
    # Revisar campos de fecha simple
    for campo in campos_fecha_simple:
        if campo in servicio_original and campo in servicio_corregido:
            fecha_antes = servicio_original[campo]
            fecha_despues = servicio_corregido[campo]
            
            if fecha_antes != fecha_despues:
                cambios.append({
                    'Usuario': f"#{idx_usuario}" if idx_usuario else "N/A",
                    'Documento Usuario': num_doc,
                    'Tipo Servicio': tipo_servicio.capitalize(),
                    'Consecutivo': servicio_original.get('consecutivo', idx_servicio),
                    'Campo': campo,
                    'Fecha Antes': fecha_antes,
                    'Fecha Después': fecha_despues,
                    'Tipo Cambio': 'Corrección de fecha'
                })
    
    # Revisar rangos de fecha
    if tipo_servicio in ['urgencias', 'hospitalizacion']:
        if 'fechaInicioAtencion' in servicio_original and 'fechaEgreso' in servicio_original:
            inicio_antes = servicio_original['fechaInicioAtencion']
            egreso_antes = servicio_original['fechaEgreso']
            inicio_despues = servicio_corregido['fechaInicioAtencion']
            egreso_despues = servicio_corregido['fechaEgreso']
            
            if inicio_antes != inicio_despues or egreso_antes != egreso_despues:
                cambios.append({
                    'Usuario': f"#{idx_usuario}" if idx_usuario else "N/A",
                    'Documento Usuario': num_doc,
                    'Tipo Servicio': tipo_servicio.capitalize(),
                    'Consecutivo': servicio_original.get('consecutivo', idx_servicio),
                    'Campo': 'Rango (Inicio - Egreso)',
                    'Fecha Antes': f"{inicio_antes} → {egreso_antes}",
                    'Fecha Después': f"{inicio_despues} → {egreso_despues}",
                    'Tipo Cambio': 'Corrección de rango'
                })
    
    return cambios


# Constantes útiles
MESES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre'
}

def obtener_nombre_mes(numero_mes: int) -> str:
    """Retorna el nombre del mes en español."""
    return MESES.get(numero_mes, 'Desconocido')
