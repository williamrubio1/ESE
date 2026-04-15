"""
Reformador PYP: Convierte Excel Usuarios.xlsx de vuelta a archivo JSON
Lee el Excel y genera JSON con la estructura original
"""

import pandas as pd
import json
from collections import defaultdict
import re
from io import BytesIO
import random
from modules.documentos_rips import completar_documentos_profesionales_usuario
from modules.format_standards import (
    normalize_dataframe_columns,
    normalize_dict_fields,
    normalizar_documento,
    format_two_digit_code,
    format_three_digit_code,
    format_six_digit_code,
    format_integer,
    format_string,
    format_null_field,
    validar_tipo_documento_por_edad,
    FIELD_FORMATS
)

# ORDEN CORRECTO DE CAMPOS PARA JSON REFORMADO
# Este orden NO debe cambiarse jamás - preserva el orden original del estándar RIPS
ORDEN_CAMPOS_CONSULTAS = [
    'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'codConsulta',
    'modalidadGrupoServicioTecSal', 'grupoServicios', 'codServicio',
    'finalidadTecnologiaSalud', 'causaMotivoAtencion', 'codDiagnosticoPrincipal',
    'codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3',
    'tipoDiagnosticoPrincipal',
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',  # Profesional
    'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador',
    'consecutivo'
]

ORDEN_CAMPOS_PROCEDIMIENTOS = [
    'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'idMIPRES',
    'codProcedimiento', 'viaIngresoServicioSalud', 'modalidadGrupoServicioTecSal',
    'grupoServicios', 'codServicio', 'finalidadTecnologiaSalud',
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',  # Profesional
    'codDiagnosticoPrincipal', 'codDiagnosticoRelacionado', 'codComplicacion',
    'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador',
    'consecutivo'
]

def ordenar_campos_servicio(servicio_dict, orden_campos):
    """
    Reordena los campos de un servicio según el orden especificado.
    
    Args:
        servicio_dict: Diccionario con los campos del servicio
        orden_campos: Lista con el orden deseado de campos
        
    Returns:
        Diccionario con campos en el orden especificado
    """
    resultado = {}
    # Primero agregar campos en el orden especificado
    for campo in orden_campos:
        if campo in servicio_dict:
            resultado[campo] = servicio_dict[campo]
    # Luego agregar cualquier campo extra que no esté en la lista de orden
    for campo, valor in servicio_dict.items():
        if campo not in resultado:
            resultado[campo] = valor
    return resultado

def format_json_compact_arrays(obj, indent=2):
    """Formatea JSON con arrays en formato compacto [{ ... }]"""
    json_str = json.dumps(obj, ensure_ascii=False, indent=indent)
    
    # Mantener el formato estándar con saltos de línea para }]
    json_str = re.sub(r'(\s*)"(\w+)":\s*\[\s*\n\s+\{', r'\1"\2": [{', json_str)
    json_str = re.sub(r'\},\s*\n\s+\{', '}, {', json_str)
    
    return json_str

def limpiar_none_strings(obj):
    """
    Reemplaza recursivamente cadenas "None" o "nan" por None (null en JSON)
    en objetos dict, list, y valores simples.
    """
    if isinstance(obj, dict):
        return {k: limpiar_none_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [limpiar_none_strings(item) for item in obj]
    elif isinstance(obj, str) and obj in ("None", "nan"):
        return None
    else:
        return obj

def validar_y_corregir_servicios(usuario):
    """
    Valida y corrige los servicios de un usuario:
    1. Asegura que los consecutivos sean secuenciales
    2. Completa documentos de profesionales faltantes con valores existentes al azar
    """
    completar_documentos_profesionales_usuario(usuario, ['consultas', 'procedimientos'])

def reformar_excel_pyp(excel_file, filename):
    """
    Convierte Excel a JSON para ValidacionPYP
    
    Args:
        excel_file: Archivo Excel cargado
        filename: Nombre del archivo original (sin extensión)
    
    Returns:
        BytesIO: Archivo JSON en memoria
    """
    
    print("=" * 60)
    print("Reformador PYP: Excel → JSON")
    print("=" * 60)

    try:
        df_usuarios = pd.read_excel(excel_file, sheet_name='Usuarios')
        df_consultas = pd.read_excel(excel_file, sheet_name='Consultas')
        df_procedimientos = pd.read_excel(excel_file, sheet_name='Procedimientos')
        
        print(f"✓ Hoja 'Usuarios': {len(df_usuarios):,} filas cargadas")
        print(f"✓ Hoja 'Consultas': {len(df_consultas):,} filas cargadas")
        print(f"✓ Hoja 'Procedimientos': {len(df_procedimientos):,} filas cargadas")
        
    except Exception as e:
        print(f"❌ Error leyendo el archivo Excel: {e}")
        raise

    # Reemplazar NaN solo en campos que no pueden ser null
    # Para usuarios, podemos rellenar strings vacíos de forma segura
    df_usuarios = df_usuarios.fillna('')
    # Para consultas/procedimientos, NO hacemos fillna para preservar null en campos opcionales
    # El código debe manejar NaN correctamente con pd.isna() o pd.notna()

    print("\n🔄 Normalizando formatos...")
    # Normalizar todos los DataFrames usando el sistema centralizado
    df_usuarios = normalize_dataframe_columns(df_usuarios)
    df_consultas = normalize_dataframe_columns(df_consultas)
    df_procedimientos = normalize_dataframe_columns(df_procedimientos)
    print("✓ Normalización completada")

    print(f"\n🔄 Construyendo estructura JSON...")
    print(f"   Procesando {len(df_usuarios):,} usuarios...")
    
    # Agrupar usuarios por factura
    usuarios_por_factura = defaultdict(list)
    total_usuarios = len(df_usuarios)

    for idx, user_row in df_usuarios.iterrows():
        # Mostrar progreso cada 50 usuarios
        if (idx + 1) % 50 == 0 or (idx + 1) == total_usuarios:
            print(f"   → Usuario {idx + 1}/{total_usuarios}", end='\r')
        numFactura = str(user_row['numFactura'])
        numDocUsuario = str(user_row['numDocumentoIdentificacion'])
        
        # Construir objeto usuario
        fechaNacimiento = str(user_row['fechaNacimiento'])
        tipoDocOriginal = str(user_row['tipoDocumentoIdentificacion'])
        
        # Validar y corregir tipo de documento según edad
        tipoDocCorregido = validar_tipo_documento_por_edad(fechaNacimiento, tipoDocOriginal)
        
        usuario = {
            'tipoDocumentoIdentificacion': tipoDocCorregido,
            'numDocumentoIdentificacion': numDocUsuario,
            'tipoUsuario': format_two_digit_code(user_row['tipoUsuario']),
            'fechaNacimiento': fechaNacimiento,
            'codSexo': str(user_row['codSexo']),
            'codPaisResidencia': format_three_digit_code(user_row['codPaisResidencia']),
            'codMunicipioResidencia': str(user_row['codMunicipioResidencia']),
            'codZonaTerritorialResidencia': format_two_digit_code(user_row['codZonaTerritorialResidencia']),
            'incapacidad': str(user_row['incapacidad']),
            'consecutivo': int(user_row['consecutivo']) if user_row['consecutivo'] != '' else 0,
            'codPaisOrigen': format_three_digit_code(user_row['codPaisOrigen']),
            'servicios': {}
        }
        
        # Obtener consultas de este usuario
        if not df_consultas.empty:
            consultas_usuario = df_consultas[df_consultas['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            consultas_usuario = pd.DataFrame()
        if len(consultas_usuario) > 0:
            usuario['servicios']['consultas'] = []
        
        for idx_consulta, (_, consulta_row) in enumerate(consultas_usuario.iterrows(), 1):
            consulta = {
                'codPrestador': str(consulta_row['codPrestador']) if pd.notna(consulta_row.get('codPrestador')) else '',
                'fechaInicioAtencion': str(consulta_row['fechaInicioAtencion']) if pd.notna(consulta_row.get('fechaInicioAtencion')) else '',
                'numAutorizacion': str(consulta_row['numAutorizacion']) if pd.notna(consulta_row.get('numAutorizacion')) and str(consulta_row['numAutorizacion']).strip() != '' else None,
                'codConsulta': str(consulta_row['codConsulta']) if pd.notna(consulta_row.get('codConsulta')) else '',
                'modalidadGrupoServicioTecSal': format_two_digit_code(consulta_row['modalidadGrupoServicioTecSal']) if pd.notna(consulta_row.get('modalidadGrupoServicioTecSal')) else '',
                'grupoServicios': format_two_digit_code(consulta_row['grupoServicios']) if pd.notna(consulta_row.get('grupoServicios')) else '',
                'codServicio': int(consulta_row['codServicio']) if pd.notna(consulta_row.get('codServicio')) else None,
                'finalidadTecnologiaSalud': format_two_digit_code(consulta_row['finalidadTecnologiaSalud']) if pd.notna(consulta_row.get('finalidadTecnologiaSalud')) else '',
                'causaMotivoAtencion': str(consulta_row['causaMotivoAtencion']) if pd.notna(consulta_row.get('causaMotivoAtencion')) else '',
                'codDiagnosticoPrincipal': str(consulta_row['codDiagnosticoPrincipal']) if pd.notna(consulta_row.get('codDiagnosticoPrincipal')) else '',
                'codDiagnosticoRelacionado1': str(consulta_row['codDiagnosticoRelacionado1']) if pd.notna(consulta_row.get('codDiagnosticoRelacionado1')) and str(consulta_row['codDiagnosticoRelacionado1']).strip() != '' else None,
                'codDiagnosticoRelacionado2': str(consulta_row['codDiagnosticoRelacionado2']) if pd.notna(consulta_row.get('codDiagnosticoRelacionado2')) and str(consulta_row['codDiagnosticoRelacionado2']).strip() != '' else None,
                'codDiagnosticoRelacionado3': str(consulta_row['codDiagnosticoRelacionado3']) if pd.notna(consulta_row.get('codDiagnosticoRelacionado3')) and str(consulta_row['codDiagnosticoRelacionado3']).strip() != '' else None,
                'tipoDiagnosticoPrincipal': format_two_digit_code(consulta_row['tipoDiagnosticoPrincipal']) if pd.notna(consulta_row.get('tipoDiagnosticoPrincipal')) else '',
                'tipoDocumentoIdentificacion': str(consulta_row['tipoDocumentoIdentificacion_profesional']) if pd.notna(consulta_row.get('tipoDocumentoIdentificacion_profesional')) else '',
                'numDocumentoIdentificacion': str(consulta_row['numDocumentoIdentificacion_profesional']) if pd.notna(consulta_row.get('numDocumentoIdentificacion_profesional')) else '',
                'vrServicio': int(consulta_row['vrServicio']) if pd.notna(consulta_row.get('vrServicio')) else 0,
                'conceptoRecaudo': format_two_digit_code(consulta_row['conceptoRecaudo']) if pd.notna(consulta_row.get('conceptoRecaudo')) else '',
                'valorPagoModerador': int(consulta_row['valorPagoModerador']) if pd.notna(consulta_row.get('valorPagoModerador')) else 0,
                'numFEVPagoModerador': str(consulta_row['numFEVPagoModerador']) if pd.notna(consulta_row.get('numFEVPagoModerador')) and str(consulta_row['numFEVPagoModerador']).strip() != '' else None,
                'consecutivo': idx_consulta
            }
            # Aplicar normalización del diccionario centralizado
            consulta = normalize_dict_fields(consulta)
            # Reordenar campos según el orden estándar RIPS
            consulta = ordenar_campos_servicio(consulta, ORDEN_CAMPOS_CONSULTAS)
            usuario['servicios']['consultas'].append(consulta)
        
        # Obtener procedimientos de este usuario
        if not df_procedimientos.empty:
            procedimientos_usuario = df_procedimientos[df_procedimientos['numDocumento_usuario'].astype(str) == numDocUsuario]
            # Filtrar procedimientos con códigos OS520, OS521, OS522, OS523, OS527
            codigos_excluir = ['OS520', 'OS521', 'OS522', 'OS523', 'OS527']
            if 'codProcedimiento' in procedimientos_usuario.columns:
                procedimientos_usuario = procedimientos_usuario[
                    ~procedimientos_usuario['codProcedimiento'].astype(str).str.upper().isin(codigos_excluir)
                ]
        else:
            procedimientos_usuario = pd.DataFrame()
        if len(procedimientos_usuario) > 0:
            usuario['servicios']['procedimientos'] = []
        
        for idx_proc, (_, proc_row) in enumerate(procedimientos_usuario.iterrows(), 1):
            procedimiento = {
                'codPrestador': str(proc_row['codPrestador']) if pd.notna(proc_row.get('codPrestador')) else '',
                'fechaInicioAtencion': str(proc_row['fechaInicioAtencion']) if pd.notna(proc_row.get('fechaInicioAtencion')) else '',
                'numAutorizacion': str(proc_row['numAutorizacion']) if pd.notna(proc_row.get('numAutorizacion')) and str(proc_row['numAutorizacion']).strip() != '' else None,
                'idMIPRES': str(proc_row['idMIPRES']) if pd.notna(proc_row.get('idMIPRES')) and str(proc_row['idMIPRES']).strip() != '' else None,
                'codProcedimiento': format_six_digit_code(proc_row['codProcedimiento']) if pd.notna(proc_row.get('codProcedimiento')) else '',
                'viaIngresoServicioSalud': format_two_digit_code(proc_row['viaIngresoServicioSalud']) if pd.notna(proc_row.get('viaIngresoServicioSalud')) else '',
                'modalidadGrupoServicioTecSal': format_two_digit_code(proc_row['modalidadGrupoServicioTecSal']) if pd.notna(proc_row.get('modalidadGrupoServicioTecSal')) else '',
                'grupoServicios': format_two_digit_code(proc_row['grupoServicios']) if pd.notna(proc_row.get('grupoServicios')) else '',
                'codServicio': int(proc_row['codServicio']) if pd.notna(proc_row.get('codServicio')) else None,
                'finalidadTecnologiaSalud': format_two_digit_code(proc_row['finalidadTecnologiaSalud']) if pd.notna(proc_row.get('finalidadTecnologiaSalud')) else '',
                'tipoDocumentoIdentificacion': str(proc_row['tipoDocumentoIdentificacion_profesional']) if pd.notna(proc_row.get('tipoDocumentoIdentificacion_profesional')) else '',
                'numDocumentoIdentificacion': str(proc_row['numDocumentoIdentificacion_profesional']) if pd.notna(proc_row.get('numDocumentoIdentificacion_profesional')) else '',
                'codDiagnosticoPrincipal': str(proc_row['codDiagnosticoPrincipal']) if pd.notna(proc_row.get('codDiagnosticoPrincipal')) else '',
                'codDiagnosticoRelacionado': str(proc_row['codDiagnosticoRelacionado']) if pd.notna(proc_row.get('codDiagnosticoRelacionado')) and str(proc_row['codDiagnosticoRelacionado']).strip() != '' else None,
                'codComplicacion': str(proc_row['codComplicacion']) if pd.notna(proc_row.get('codComplicacion')) and str(proc_row['codComplicacion']).strip() != '' else None,
                'vrServicio': int(proc_row['vrServicio']) if pd.notna(proc_row.get('vrServicio')) else 0,
                'conceptoRecaudo': format_two_digit_code(proc_row['conceptoRecaudo']) if pd.notna(proc_row.get('conceptoRecaudo')) else '',
                'valorPagoModerador': int(proc_row['valorPagoModerador']) if pd.notna(proc_row.get('valorPagoModerador')) else 0,
                'numFEVPagoModerador': str(proc_row['numFEVPagoModerador']) if pd.notna(proc_row.get('numFEVPagoModerador')) and str(proc_row['numFEVPagoModerador']).strip() != '' else None,
                'consecutivo': idx_proc
            }
            # Aplicar normalización del diccionario centralizado
            procedimiento = normalize_dict_fields(procedimiento)
            # Reordenar campos según el orden estándar RIPS
            procedimiento = ordenar_campos_servicio(procedimiento, ORDEN_CAMPOS_PROCEDIMIENTOS)
            usuario['servicios']['procedimientos'].append(procedimiento)
        
        # Validar y corregir servicios antes de agregar
        validar_y_corregir_servicios(usuario)
        
        # Agregar usuario a la factura correspondiente
        usuarios_por_factura[numFactura].append({
            'usuario': usuario,
            'numDocumentoIdObligado': str(user_row['numDocumentoIdObligado'])
        })

    print(f"\n✓ {total_usuarios:,} usuarios procesados correctamente")
    print(f"\n🔄 Generando archivo JSON final...")
    print(f"✓ Usuarios agrupados en {len(usuarios_por_factura)} facturas")

    # Generar JSON (solo una factura esperada)
    if len(usuarios_por_factura) > 0:
        numFactura = list(usuarios_por_factura.keys())[0]
        usuarios_data = usuarios_por_factura[numFactura]
        numDocumentoIdObligado = usuarios_data[0]['numDocumentoIdObligado']
        
        # Construir estructura JSON
        json_data = {
            'numDocumentoIdObligado': numDocumentoIdObligado,
            'numFactura': numFactura,
            'tipoNota': None,
            'numNota': None,
            'usuarios': [item['usuario'] for item in usuarios_data]
        }
        
        # Limpiar cadenas "None" y convertirlas a null
        json_data = limpiar_none_strings(json_data)
        
        # Convertir a JSON con formato compacto
        json_formatted = format_json_compact_arrays(json_data, indent=4)
        
        # Guardar en BytesIO
        output = BytesIO()
        output.write(json_formatted.encode('utf-8'))
        output.seek(0)
        
        print(f"\n✅ JSON generado exitosamente")
        print(f"  • Usuarios exportados: {len(usuarios_data):,}")
        
        return output
    else:
        raise ValueError("No se encontraron facturas para procesar")
