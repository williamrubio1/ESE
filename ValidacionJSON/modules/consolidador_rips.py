"""
Consolidador de Facturas RIPS - Resolución 3280 de 2018
Módulo Flask para consolidar múltiples facturas JSON en un único documento,
respetando la estructura global de los RIPS (sangría, dumps, etc.).
"""

import json
import re
from io import BytesIO
from typing import Dict, List, Tuple, Any
from collections import defaultdict


def cargar_json_desde_bytes(contenido: bytes) -> Dict:
    """Carga un JSON desde bytes (maneja BOM y distintas codificaciones)."""
    try:
        return json.loads(contenido.decode('utf-8-sig'))
    except Exception:
        return json.loads(contenido.decode('utf-8'))


def guardar_json_a_bytes(datos: Dict) -> bytes:
    """
    Serializa los datos JSON con formato compacto personalizado que respeta
    la estructura RIPS: arrays de servicios en línea ([ {}, {} ]) pero con
    indentación de 4 espacios en el resto del documento.
    """
    json_str = json.dumps(datos, ensure_ascii=False, indent=4)
    # Arrays de servicios: [{ en lugar de [\n    {
    json_str = re.sub(r'\[\s+\{', '[{', json_str)
    # }, { en lugar de },\n    {
    json_str = re.sub(r'\},\s+\{', '}, {', json_str)
    return json_str.encode('utf-8')


# ── Helpers internos ──────────────────────────────────────────────────────────

def _recopilar_todos_usuarios(archivos_contenido: List[Tuple[str, bytes]]):
    """
    Lee todos los archivos y devuelve la lista de usuarios raw,
    el encabezado de la primera factura y las estadísticas de procesamiento.
    """
    todos_usuarios: List[Dict] = []
    primera_factura: Dict = {}
    estadisticas = {
        'archivos_procesados': 0,
        'archivos_error': [],
        'total_usuarios': 0,
        'total_servicios': 0,
        'detalle': [],
    }

    for nombre_archivo, contenido in archivos_contenido:
        try:
            datos = cargar_json_desde_bytes(contenido)
            if not primera_factura:
                primera_factura = datos
            servicios_archivo = sum(
                len(s) for u in datos.get('usuarios', [])
                for s in u.get('servicios', {}).values()
                if isinstance(s, list)
            )
            todos_usuarios.extend(datos.get('usuarios', []))
            estadisticas['archivos_procesados'] += 1
            estadisticas['total_servicios'] += servicios_archivo
            estadisticas['detalle'].append({
                'archivo': nombre_archivo,
                'usuarios': len(datos.get('usuarios', [])),
                'servicios': servicios_archivo,
                'estado': 'OK',
            })
        except Exception as e:
            estadisticas['archivos_error'].append({'archivo': nombre_archivo, 'error': str(e)})
            estadisticas['detalle'].append({
                'archivo': nombre_archivo,
                'usuarios': 0,
                'servicios': 0,
                'estado': f'ERROR: {str(e)}',
            })

    return todos_usuarios, primera_factura, estadisticas


def _campos_base_usuario(usuario: Dict) -> Dict:
    """Devuelve los campos de encabezado de un usuario (sin servicios ni consecutivo)."""
    return {
        'tipoDocumentoIdentificacion': usuario.get('tipoDocumentoIdentificacion'),
        'numDocumentoIdentificacion': usuario.get('numDocumentoIdentificacion'),
        'tipoUsuario': usuario.get('tipoUsuario'),
        'fechaNacimiento': usuario.get('fechaNacimiento'),
        'codSexo': usuario.get('codSexo'),
        'codPaisResidencia': usuario.get('codPaisResidencia'),
        'codMunicipioResidencia': usuario.get('codMunicipioResidencia'),
        'codZonaTerritorialResidencia': usuario.get('codZonaTerritorialResidencia'),
        'incapacidad': usuario.get('incapacidad'),
        'codPaisOrigen': usuario.get('codPaisOrigen'),
    }


def _merge_por_usuario(todos_usuarios: List[Dict]) -> List[Dict]:
    """
    Combina usuarios con el mismo numDocumentoIdentificacion, uniendo todos
    sus servicios en un único registro por paciente y reasignando consecutivos.
    """
    merged: Dict[str, Dict] = {}
    for usuario in todos_usuarios:
        num_doc = usuario.get('numDocumentoIdentificacion') or '__sin_doc__'
        if num_doc not in merged:
            merged[num_doc] = _campos_base_usuario(usuario)
            merged[num_doc]['servicios'] = {}
        for tipo, lista in usuario.get('servicios', {}).items():
            if isinstance(lista, list):
                merged[num_doc]['servicios'].setdefault(tipo, []).extend(lista)

    resultado = list(merged.values())
    for i, u in enumerate(resultado, 1):
        u['consecutivo'] = i
    return resultado


def _split_por_prestador(usuarios: List[Dict], encabezado: Dict) -> Dict[str, bytes]:
    """
    Divide la lista de usuarios en documentos separados por codPrestador.
    Devuelve un dict {codPrestador: json_bytes} con un JSON por prestador.
    """
    prestadores: Dict[str, Dict[str, Dict]] = defaultdict(dict)

    for usuario in usuarios:
        num_doc = usuario.get('numDocumentoIdentificacion') or '__sin_doc__'
        for tipo_servicio, lista in usuario.get('servicios', {}).items():
            if not isinstance(lista, list):
                continue
            for servicio in lista:
                cod = str(servicio.get('codPrestador') or '__sin_prestador__')
                if num_doc not in prestadores[cod]:
                    prestadores[cod][num_doc] = _campos_base_usuario(usuario)
                    prestadores[cod][num_doc]['servicios'] = {}
                prestadores[cod][num_doc]['servicios'].setdefault(tipo_servicio, []).append(servicio)

    resultado = {}
    for cod_prestador, usuarios_dict in prestadores.items():
        usuarios_list = list(usuarios_dict.values())
        for i, u in enumerate(usuarios_list, 1):
            u['consecutivo'] = i
        documento = {
            **encabezado,
            'numFactura': f'CONSOLIDADO_{cod_prestador}',
            'usuarios': usuarios_list,
        }
        resultado[cod_prestador] = guardar_json_a_bytes(documento)

    return resultado


# ── API pública ───────────────────────────────────────────────────────────────

def consolidar_multiples_json(
    archivos_contenido: List[Tuple[str, bytes]],
    modo: str = 'usuario',
) -> Tuple[Any, Dict]:
    """
    Consolida múltiples JSON RIPS según el modo indicado.

    Args:
        archivos_contenido: Lista de tuplas (nombre_archivo, contenido_bytes)
        modo:
            'usuario'   → un único JSON con usuarios deduplicados por
                          numDocumentoIdentificacion y sus servicios combinados.
            'prestador' → dict {codPrestador: bytes}, un JSON por prestador
                          (los usuarios no se deduplicán entre sí).
            'ambos'     → dict {codPrestador: bytes}, usuarios primero
                          deduplicados y luego divididos por prestador.

    Returns:
        Tupla (resultado, estadisticas)
        - resultado: bytes en modo 'usuario'; dict[str, bytes] en los demás.
    """
    if not archivos_contenido:
        raise ValueError("No se proporcionaron archivos para consolidar.")

    todos_usuarios, primera_factura, estadisticas = _recopilar_todos_usuarios(archivos_contenido)

    encabezado = {
        'numDocumentoIdObligado': primera_factura.get('numDocumentoIdObligado', '') if primera_factura else '',
        'tipoNota': None,
        'numNota': None,
    }

    if modo == 'usuario':
        usuarios_merged = _merge_por_usuario(todos_usuarios)
        documento = {**encabezado, 'numFactura': 'CONSOLIDADO', 'usuarios': usuarios_merged}
        estadisticas['total_usuarios'] = len(usuarios_merged)
        return guardar_json_a_bytes(documento), estadisticas

    elif modo == 'prestador':
        resultado = _split_por_prestador(todos_usuarios, encabezado)
        estadisticas['total_usuarios'] = len(todos_usuarios)
        estadisticas['prestadores'] = sorted(resultado.keys())
        return resultado, estadisticas

    elif modo == 'ambos':
        usuarios_merged = _merge_por_usuario(todos_usuarios)
        resultado = _split_por_prestador(usuarios_merged, encabezado)
        estadisticas['total_usuarios'] = len(usuarios_merged)
        estadisticas['prestadores'] = sorted(resultado.keys())
        return resultado, estadisticas

    else:
        raise ValueError(f"Modo no válido: '{modo}'. Use 'usuario', 'prestador' o 'ambos'.")
