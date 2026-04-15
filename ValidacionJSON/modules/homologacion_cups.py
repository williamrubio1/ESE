"""
Verificación de CUPS contratados para RIPS por EPS.

Se ejecuta antes de la validación clínica, pero ya no modifica codConsulta ni
codProcedimiento. Su único propósito es identificar CUPS fuera de contrato para
incluirlos en el reporte de cambios.

Compatibilidad: PYP · BC · Compuestos
Estructura JSON esperada:
    usuarios[].servicios.consultas[].codConsulta
    usuarios[].servicios.procedimientos[].codProcedimiento
"""

from modules.config_eps import registro_en_contrato


def aplicar_homologacion_rips(
    datos_json: dict,
    eps_id: str = 'nueva_eps',
    generar_reporte: bool = False,
):
    """
    Revisa todos los CUPS del JSON RIPS y reporta cuáles no están contratados.

    No modifica campos del JSON.

    Args:
        datos_json      : dict con la estructura completa del RIPS-JSON.
        eps_id          : Identificador de EPS configurada en config_eps.
        generar_reporte : Si True, retorna también la lista de novedades.

    Returns:
        Si generar_reporte=False : dict JSON original.
        Si generar_reporte=True  : (dict JSON modificado, list cambios).
            Cada cambio: {
                'usuario', 'tipo_servicio', 'consecutivo',
                'cups_original', 'cups_homologado', 'tipo',
                'En_Contrato'
            }
    """
    cambios = [] if generar_reporte else None

    for usuario in datos_json.get('usuarios', []):
        num_doc = usuario.get('numDocumentoIdentificacion', '')
        servicios = usuario.get('servicios', {})

        # Consultas → codConsulta
        for idx, consulta in enumerate(servicios.get('consultas', []), 1):
            original = str(consulta.get('codConsulta', '') or '').strip()
            if not original:
                continue
            en_contrato = registro_en_contrato(original, eps_id)
            if generar_reporte and not en_contrato:
                cambios.append({
                    'usuario':         num_doc,
                    'tipo_servicio':   'consulta',
                    'consecutivo':     idx,
                    'cups_original':   original,
                    'cups_homologado': original,
                    'tipo':            'no_contratado',
                    'En_Contrato':     'No',
                })

        # Procedimientos → codProcedimiento
        for idx, proc in enumerate(servicios.get('procedimientos', []), 1):
            original = str(proc.get('codProcedimiento', '') or '').strip()
            if not original:
                continue
            en_contrato = registro_en_contrato(original, eps_id)
            if generar_reporte and not en_contrato:
                cambios.append({
                    'usuario':         num_doc,
                    'tipo_servicio':   'procedimiento',
                    'consecutivo':     idx,
                    'cups_original':   original,
                    'cups_homologado': original,
                    'tipo':            'no_contratado',
                    'En_Contrato':     'No',
                })

    if generar_reporte:
        return datos_json, cambios
    return datos_json


def tabla_como_lista(eps_id: str = 'nueva_eps') -> list[dict]:
    """Sin tabla de homologación activa. Se conserva por compatibilidad."""
    return []



