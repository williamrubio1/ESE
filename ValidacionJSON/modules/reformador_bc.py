"""
Reformador BC: Convierte Excel Usuarios.xlsx de vuelta a archivo JSON
Lee el Excel y genera JSON con la estructura original
"""

import pandas as pd
import json
from collections import defaultdict
import re
from io import BytesIO
import random
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

ORDEN_CAMPOS_MEDICAMENTOS = [
    'codPrestador', 'numAutorizacion', 'idMIPRES', 'fechaDispensAdmon',
    'codDiagnosticoPrincipal', 'codDiagnosticoRelacionado',
    'tipoMedicamento', 'codTecnologiaSalud', 'nomTecnologiaSalud',
    'concentracionMedicamento', 'unidadMedida', 'formaFarmaceutica',
    'unidadMinDispensa', 'cantidadMedicamento', 'diasTratamiento',
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',  # Profesional
    'vrUnitMedicamento', 'vrServicio', 'conceptoRecaudo',
    'valorPagoModerador', 'numFEVPagoModerador', 'consecutivo'
]

ORDEN_CAMPOS_OTROS_SERVICIOS = [
    'codPrestador', 'numAutorizacion', 'idMIPRES', 'fechaSuministroTecnologia',
    'tipoOS', 'codTecnologiaSalud', 'nomTecnologiaSalud', 'cantidadOS',
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',  # Profesional
    'vrUnitOS', 'vrServicio', 'conceptoRecaudo',
    'valorPagoModerador', 'numFEVPagoModerador', 'consecutivo'
]

ORDEN_CAMPOS_URGENCIAS = [
    'codPrestador', 'fechaInicioAtencion', 'causaMotivoAtencion',
    'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
    'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
    'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte', 'fechaEgreso',
    'consecutivo'
]

ORDEN_CAMPOS_HOSPITALIZACION = [
    'codPrestador', 'viaIngresoServicioSalud', 'fechaInicioAtencion', 'numAutorizacion',
    'causaMotivoAtencion', 'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
    'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
    'codComplicacion', 'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte', 'fechaEgreso',
    'consecutivo'
]

ORDEN_CAMPOS_RECIEN_NACIDOS = [
    'codPrestador', 'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
    'fechaNacimiento', 'edadGestacional', 'codSexoBiologico', 'peso',
    'codDiagnosticoPrincipal', 'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte',
    'fechaEgreso', 'consecutivo'
]

# Columnas internas que no deben volver al JSON original y prefijos a excluir
EXCLUDE_INTERNAL = {
    'numDocumento_usuario','tipoDocumento_usuario',
    'consecutivo_consulta','consecutivo_procedimiento',
    'consecutivo_medicamento','consecutivo_otro','consecutivo_urgencia','consecutivo_hospitalizacion','consecutivo_recien_nacido',
    'tipoDocumentoIdentificacion_profesional','numDocumentoIdentificacion_profesional',
    'numFactura','archivoOrigen'
}
EXCLUDE_PREFIXES = ('_tmp','_aux')

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

def sanitize_strings(obj):
    """Normaliza strings: reemplaza NBSP (\u00A0) por espacio normal, deja el resto igual."""
    if isinstance(obj, dict):
        return {k: sanitize_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_strings(v) for v in obj]
    if isinstance(obj, str):
        return obj.replace('\u00A0', ' ')
    return obj

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
    2. Rellena tipoMedicamento vacíos con "01"
    3. Completa documentos de profesionales faltantes con valores existentes al azar
    4. Reemplaza diagnósticos Z300, Z010, Z258, Z001 por Z718 en consultas y medicamentos
    """
    servicios = usuario.get('servicios', {})
    
    # Diagnósticos a reemplazar
    DIAGNOSTICOS_REEMPLAZAR = ['Z300', 'Z010', 'Z258', 'Z001', 'Z002', 'Z003', 'Z000', 'Z348', 'Z359']
    DIAGNOSTICO_REEMPLAZO = 'Z718'
    
    # Primero, recopilar TODOS los números de documento válidos de TODOS los servicios del usuario
    todos_documentos_validos = []
    for servicio_tipo in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos']:
        lista_servicios = servicios.get(servicio_tipo, [])
        for servicio in lista_servicios:
            num_doc = servicio.get('numDocumentoIdentificacion', '')
            if num_doc and str(num_doc).strip() != '' and not pd.isna(num_doc):
                doc_str = str(num_doc).strip()
                if doc_str not in todos_documentos_validos:
                    todos_documentos_validos.append(doc_str)
    
    # Validar y corregir cada tipo de servicio
    for servicio_tipo in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos']:
        lista_servicios = servicios.get(servicio_tipo, [])
        
        if not lista_servicios:
            continue
        
        # Completar datos faltantes de profesionales (NO renumerar consecutivos)
        for servicio in lista_servicios:
            
            # Reemplazar diagnósticos específicos en consultas y medicamentos
            if servicio_tipo in ['consultas', 'medicamentos']:
                if 'codDiagnosticoPrincipal' in servicio:
                    diag_principal = servicio.get('codDiagnosticoPrincipal', '')
                    if diag_principal in DIAGNOSTICOS_REEMPLAZAR:
                        servicio['codDiagnosticoPrincipal'] = DIAGNOSTICO_REEMPLAZO
            
            # Completar tipoMedicamento en medicamentos
            if servicio_tipo == 'medicamentos':
                if 'tipoMedicamento' in servicio:
                    if not servicio['tipoMedicamento'] or servicio['tipoMedicamento'] == '' or pd.isna(servicio['tipoMedicamento']):
                        servicio['tipoMedicamento'] = '01'
            
            # Completar documentos de profesionales SOLO SI EL CAMPO EXISTE
            # Completar tipo de documento faltante con "CC" solo si la clave existe
            if 'tipoDocumentoIdentificacion' in servicio:
                tipo_doc = servicio.get('tipoDocumentoIdentificacion', '')
                if not tipo_doc or tipo_doc == '' or pd.isna(tipo_doc):
                    servicio['tipoDocumentoIdentificacion'] = 'CC'
            
            # Completar número de documento faltante solo si la clave existe
            if 'numDocumentoIdentificacion' in servicio:
                num_doc = servicio.get('numDocumentoIdentificacion', '')
                if not num_doc or num_doc == '' or pd.isna(num_doc):
                    if todos_documentos_validos:
                        servicio['numDocumentoIdentificacion'] = random.choice(todos_documentos_validos)
                    else:
                        servicio['numDocumentoIdentificacion'] = ''

def format_json_compact_arrays(obj, indent=4):
    """Formatea JSON con indentación y abre arrays de objetos como [{ y compacta separadores entre objetos como },{"""
    s = json.dumps(obj, ensure_ascii=False, indent=indent)
    # Compactar apertura de arrays de objetos: ": [\n    {" -> ": [{"
    s = re.sub(r'(":\s*\[\s*)\n(\s*)\{', r'\1{', s)
    # Compactar separadores entre objetos en arrays: "},\n    {" -> "}, {"
    s = re.sub(r'\},\s*\n\s*\{', r'}, {', s)
    return s

def reformar_excel_bc(excel_file, filename):
    """
    Convierte Excel a JSON para ValidacionBC
    
    Args:
        excel_file: Archivo Excel cargado
        filename: Nombre del archivo original (sin extensión)
    
    Returns:
        BytesIO: Archivo JSON en memoria
    """
    
    print("=" * 60)
    print("Reformador BC: Excel → JSON")
    print("=" * 60)

    try:
        xls = pd.ExcelFile(excel_file)
        df_usuarios = pd.read_excel(xls, sheet_name='Usuarios')
        df_consultas = pd.read_excel(xls, sheet_name='Consultas') if 'Consultas' in xls.sheet_names else pd.DataFrame()
        df_procedimientos = pd.read_excel(xls, sheet_name='Procedimientos') if 'Procedimientos' in xls.sheet_names else pd.DataFrame()
        df_medicamentos = pd.read_excel(xls, sheet_name='Medicamentos') if 'Medicamentos' in xls.sheet_names else pd.DataFrame()
        df_otros_serv = pd.read_excel(xls, sheet_name='OtrosServicios') if 'OtrosServicios' in xls.sheet_names else pd.DataFrame()
        df_urgencias = pd.read_excel(xls, sheet_name='Urgencias') if 'Urgencias' in xls.sheet_names else pd.DataFrame()
        df_hospitalizacion = pd.read_excel(xls, sheet_name='Hospitalizacion') if 'Hospitalizacion' in xls.sheet_names else pd.DataFrame()
        df_recien_nacidos = pd.read_excel(xls, sheet_name='RecienNacidos') if 'RecienNacidos' in xls.sheet_names else pd.DataFrame()
        
        print(f"✓ Hoja 'Usuarios': {len(df_usuarios):,} filas cargadas")
        if not df_consultas.empty: print(f"✓ Hoja 'Consultas': {len(df_consultas):,} filas cargadas")
        if not df_procedimientos.empty: print(f"✓ Hoja 'Procedimientos': {len(df_procedimientos):,} filas cargadas")
        if not df_medicamentos.empty: print(f"✓ Hoja 'Medicamentos': {len(df_medicamentos):,} filas cargadas")
        if not df_otros_serv.empty: print(f"✓ Hoja 'OtrosServicios': {len(df_otros_serv):,} filas cargadas")
        if not df_urgencias.empty: print(f"✓ Hoja 'Urgencias': {len(df_urgencias):,} filas cargadas")
        if not df_hospitalizacion.empty: print(f"✓ Hoja 'Hospitalizacion': {len(df_hospitalizacion):,} filas cargadas")
        if not df_recien_nacidos.empty: print(f"✓ Hoja 'RecienNacidos': {len(df_recien_nacidos):,} filas cargadas")

    except Exception as e:
        print(f"❌ Error leyendo el archivo Excel: {e}")
        raise

    # Reemplazar NaN solo en campos que no pueden ser null
    # Para usuarios, podemos rellenar strings vacíos de forma segura
    df_usuarios = df_usuarios.fillna('')
    # Para consultas/procedimientos y demás, NO hacemos fillna para preservar null en campos opcionales
    # El código debe manejar NaN correctamente con pd.isna() o pd.notna()

    print("\n🔄 Normalizando formatos...")
    # Normalizar todos los DataFrames usando el sistema centralizado
    df_usuarios = normalize_dataframe_columns(df_usuarios)
    df_consultas = normalize_dataframe_columns(df_consultas)
    df_procedimientos = normalize_dataframe_columns(df_procedimientos)
    df_medicamentos = normalize_dataframe_columns(df_medicamentos)
    df_otros_serv = normalize_dataframe_columns(df_otros_serv)
    df_urgencias = normalize_dataframe_columns(df_urgencias)
    df_hospitalizacion = normalize_dataframe_columns(df_hospitalizacion)
    df_recien_nacidos = normalize_dataframe_columns(df_recien_nacidos)

    print(f"✓ Normalización completada")
    print(f"\n🔄 Construyendo estructura JSON...")
    print(f"   Procesando {len(df_usuarios):,} usuarios...")
    
    # Agrupar usuarios por factura
    usuarios_por_factura = defaultdict(list)
    total_usuarios = len(df_usuarios)
    
    for idx, user_row in df_usuarios.iterrows():
        # Mostrar progreso cada 50 usuarios
        if (idx + 1) % 50 == 0 or (idx + 1) == total_usuarios:
            print(f"   → Procesando usuario {idx + 1}/{total_usuarios}...", end='\r')
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
            # Construir objeto base estándar
            consulta = {
                'codPrestador': str(consulta_row.get('codPrestador','')) if pd.notna(consulta_row.get('codPrestador')) else '',
                'fechaInicioAtencion': str(consulta_row.get('fechaInicioAtencion','')) if pd.notna(consulta_row.get('fechaInicioAtencion')) else '',
                'numAutorizacion': str(consulta_row['numAutorizacion']) if pd.notna(consulta_row.get('numAutorizacion')) and str(consulta_row['numAutorizacion']).strip() != '' else '',
                'codConsulta': str(consulta_row.get('codConsulta','')) if pd.notna(consulta_row.get('codConsulta')) else '',
                'modalidadGrupoServicioTecSal': format_two_digit_code(consulta_row.get('modalidadGrupoServicioTecSal','')) if pd.notna(consulta_row.get('modalidadGrupoServicioTecSal')) else '',
                'grupoServicios': format_two_digit_code(consulta_row.get('grupoServicios','')) if pd.notna(consulta_row.get('grupoServicios')) else '',
                'codServicio': int(consulta_row['codServicio']) if pd.notna(consulta_row.get('codServicio')) else '',
                'finalidadTecnologiaSalud': format_two_digit_code(consulta_row.get('finalidadTecnologiaSalud','')) if pd.notna(consulta_row.get('finalidadTecnologiaSalud')) else '',
                'causaMotivoAtencion': str(consulta_row.get('causaMotivoAtencion','')) if pd.notna(consulta_row.get('causaMotivoAtencion')) else '',
                'codDiagnosticoPrincipal': str(consulta_row['codDiagnosticoPrincipal']) if pd.notna(consulta_row.get('codDiagnosticoPrincipal')) else '',
                'codDiagnosticoRelacionado1': str(consulta_row['codDiagnosticoRelacionado1']) if pd.notna(consulta_row.get('codDiagnosticoRelacionado1')) and str(consulta_row['codDiagnosticoRelacionado1']).strip() != '' else None,
                'codDiagnosticoRelacionado2': str(consulta_row['codDiagnosticoRelacionado2']) if pd.notna(consulta_row.get('codDiagnosticoRelacionado2')) and str(consulta_row['codDiagnosticoRelacionado2']).strip() != '' else None,
                'codDiagnosticoRelacionado3': str(consulta_row['codDiagnosticoRelacionado3']) if pd.notna(consulta_row.get('codDiagnosticoRelacionado3')) and str(consulta_row['codDiagnosticoRelacionado3']).strip() != '' else None,
                'tipoDiagnosticoPrincipal': format_two_digit_code(consulta_row.get('tipoDiagnosticoPrincipal','')) if pd.notna(consulta_row.get('tipoDiagnosticoPrincipal')) else '',
                'tipoDocumentoIdentificacion': str(consulta_row.get('tipoDocumentoIdentificacion_profesional','')) if pd.notna(consulta_row.get('tipoDocumentoIdentificacion_profesional')) else '',
                'numDocumentoIdentificacion': str(consulta_row.get('numDocumentoIdentificacion_profesional','')) if pd.notna(consulta_row.get('numDocumentoIdentificacion_profesional')) else '',
                'vrServicio': int(consulta_row['vrServicio']) if pd.notna(consulta_row.get('vrServicio')) else 0,
                'conceptoRecaudo': format_two_digit_code(consulta_row.get('conceptoRecaudo','')) if pd.notna(consulta_row.get('conceptoRecaudo')) else '',
                'valorPagoModerador': int(consulta_row['valorPagoModerador']) if pd.notna(consulta_row.get('valorPagoModerador')) else 0,
                'numFEVPagoModerador': str(consulta_row['numFEVPagoModerador']) if pd.notna(consulta_row.get('numFEVPagoModerador')) and str(consulta_row['numFEVPagoModerador']).strip() != '' else None,
                'consecutivo': idx_consulta
            }
            # Reinyectar columnas extra no estándar (omitir internas y vacías)
            for col in consultas_usuario.columns:
                if col in consulta or col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                    continue
                val = consulta_row[col]
                if pd.isna(val) or val == '':
                    continue
                consulta[col] = val
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
                'codPrestador': str(proc_row.get('codPrestador','')) if pd.notna(proc_row.get('codPrestador')) else '',
                'fechaInicioAtencion': str(proc_row.get('fechaInicioAtencion','')) if pd.notna(proc_row.get('fechaInicioAtencion')) else '',
                'numAutorizacion': str(proc_row['numAutorizacion']) if pd.notna(proc_row.get('numAutorizacion')) and str(proc_row['numAutorizacion']).strip() != '' else None,
                'idMIPRES': str(proc_row['idMIPRES']) if pd.notna(proc_row.get('idMIPRES')) and str(proc_row['idMIPRES']).strip() != '' else None,
                'codProcedimiento': format_six_digit_code(proc_row.get('codProcedimiento','')) if pd.notna(proc_row.get('codProcedimiento')) else '',
                'viaIngresoServicioSalud': format_two_digit_code(proc_row.get('viaIngresoServicioSalud','')) if pd.notna(proc_row.get('viaIngresoServicioSalud')) else '',
                'modalidadGrupoServicioTecSal': format_two_digit_code(proc_row.get('modalidadGrupoServicioTecSal','')) if pd.notna(proc_row.get('modalidadGrupoServicioTecSal')) else '',
                'grupoServicios': format_two_digit_code(proc_row.get('grupoServicios','')) if pd.notna(proc_row.get('grupoServicios')) else '',
                'codServicio': int(proc_row['codServicio']) if pd.notna(proc_row.get('codServicio')) else None,
                'finalidadTecnologiaSalud': format_two_digit_code(proc_row.get('finalidadTecnologiaSalud','')) if pd.notna(proc_row.get('finalidadTecnologiaSalud')) else '',
                'tipoDocumentoIdentificacion': str(proc_row.get('tipoDocumentoIdentificacion_profesional', proc_row.get('tipoDocumentoIdentificacion',''))) if pd.notna(proc_row.get('tipoDocumentoIdentificacion_profesional', proc_row.get('tipoDocumentoIdentificacion'))) else '',
                'numDocumentoIdentificacion': str(proc_row.get('numDocumentoIdentificacion_profesional', proc_row.get('numDocumentoIdentificacion',''))) if pd.notna(proc_row.get('numDocumentoIdentificacion_profesional', proc_row.get('numDocumentoIdentificacion'))) else '',
                'codDiagnosticoPrincipal': str(proc_row.get('codDiagnosticoPrincipal','')) if pd.notna(proc_row.get('codDiagnosticoPrincipal')) else '',
                'codDiagnosticoRelacionado': str(proc_row['codDiagnosticoRelacionado']) if pd.notna(proc_row.get('codDiagnosticoRelacionado')) and str(proc_row['codDiagnosticoRelacionado']).strip() != '' else None,
                'codComplicacion': str(proc_row['codComplicacion']) if pd.notna(proc_row.get('codComplicacion')) and str(proc_row['codComplicacion']).strip() != '' else None,
                'vrServicio': int(proc_row['vrServicio']) if pd.notna(proc_row.get('vrServicio')) else 0,
                'conceptoRecaudo': format_two_digit_code(proc_row.get('conceptoRecaudo','')) if pd.notna(proc_row.get('conceptoRecaudo')) else '',
                'valorPagoModerador': int(proc_row['valorPagoModerador']) if pd.notna(proc_row.get('valorPagoModerador')) else 0,
                'numFEVPagoModerador': str(proc_row['numFEVPagoModerador']) if pd.notna(proc_row.get('numFEVPagoModerador')) and str(proc_row['numFEVPagoModerador']).strip() != '' else None,
                'consecutivo': idx_proc
            }
            for col in procedimientos_usuario.columns:
                if col in procedimiento or col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                    continue
                val = proc_row[col]
                if pd.isna(val) or val == '':
                    continue
                procedimiento[col] = val
            # Aplicar normalización del diccionario centralizado
            procedimiento = normalize_dict_fields(procedimiento)
            # Reordenar campos según el orden estándar RIPS
            procedimiento = ordenar_campos_servicio(procedimiento, ORDEN_CAMPOS_PROCEDIMIENTOS)
            usuario['servicios']['procedimientos'].append(procedimiento)
        
        # Otros subconjuntos relacionados al usuario
        meds_usuario = df_medicamentos[df_medicamentos.get('numDocumento_usuario','').astype(str) == numDocUsuario] if not df_medicamentos.empty else pd.DataFrame()
        if not meds_usuario.empty:
            usuario['servicios']['medicamentos'] = []
            for _, med_row in meds_usuario.iterrows():
                med = {}
                for col, val in med_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    # Conservar null (None) en JSON si el valor es NaN
                    if pd.isna(val):
                        med[col] = None
                    else:
                        med[col] = val
                # Aplicar normalización y ordenamiento
                med = normalize_dict_fields(med)
                med = ordenar_campos_servicio(med, ORDEN_CAMPOS_MEDICAMENTOS)
                # Los valores ya vienen normalizados del DataFrame
                usuario['servicios']['medicamentos'].append(med)

        otros_usuario = df_otros_serv[df_otros_serv.get('numDocumento_usuario','').astype(str) == numDocUsuario] if not df_otros_serv.empty else pd.DataFrame()
        if not otros_usuario.empty:
            usuario['servicios']['otrosServicios'] = []
            for _, otro_row in otros_usuario.iterrows():
                otro = {}
                for col, val in otro_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val):
                        otro[col] = None
                    else:
                        otro[col] = val
                # Aplicar normalización y ordenamiento
                otro = normalize_dict_fields(otro)
                otro = ordenar_campos_servicio(otro, ORDEN_CAMPOS_OTROS_SERVICIOS)
                # Los valores ya vienen normalizados del DataFrame
                usuario['servicios']['otrosServicios'].append(otro)

        urg_usuario = df_urgencias[df_urgencias.get('numDocumento_usuario','').astype(str) == numDocUsuario] if not df_urgencias.empty else pd.DataFrame()
        if not urg_usuario.empty:
            usuario['servicios']['urgencias'] = []
            for _, urg_row in urg_usuario.iterrows():
                urg = {}
                for col, val in urg_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val):
                        urg[col] = None
                    else:
                        urg[col] = val
                # Aplicar normalización y ordenamiento
                urg = normalize_dict_fields(urg)
                urg = ordenar_campos_servicio(urg, ORDEN_CAMPOS_URGENCIAS)
                # Los valores ya vienen normalizados del DataFrame
                usuario['servicios']['urgencias'].append(urg)

        hosp_usuario = df_hospitalizacion[df_hospitalizacion.get('numDocumento_usuario','').astype(str) == numDocUsuario] if not df_hospitalizacion.empty else pd.DataFrame()
        if not hosp_usuario.empty:
            usuario['servicios']['hospitalizacion'] = []
            for _, hosp_row in hosp_usuario.iterrows():
                hosp = {}
                for col, val in hosp_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val):
                        hosp[col] = None
                    else:
                        hosp[col] = val
                # Aplicar normalización y ordenamiento
                hosp = normalize_dict_fields(hosp)
                hosp = ordenar_campos_servicio(hosp, ORDEN_CAMPOS_HOSPITALIZACION)
                # Los valores ya vienen normalizados del DataFrame
                usuario['servicios']['hospitalizacion'].append(hosp)

        rn_usuario = df_recien_nacidos[df_recien_nacidos.get('numDocumento_usuario','').astype(str) == numDocUsuario] if not df_recien_nacidos.empty else pd.DataFrame()
        if not rn_usuario.empty:
            usuario['servicios']['recienNacidos'] = []
            for _, rn_row in rn_usuario.iterrows():
                rn = {}
                for col, val in rn_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val):
                        rn[col] = None
                    else:
                        rn[col] = val
                # Aplicar normalización y ordenamiento
                rn = normalize_dict_fields(rn)
                rn = ordenar_campos_servicio(rn, ORDEN_CAMPOS_RECIEN_NACIDOS)
                # Los valores ya vienen normalizados del DataFrame
                usuario['servicios']['recienNacidos'].append(rn)

        # Validar y corregir servicios antes de agregar
        validar_y_corregir_servicios(usuario)
        
        # Agregar usuario a la factura correspondiente
        usuarios_por_factura[numFactura].append({
            'usuario': usuario,
            'numDocumentoIdObligado': str(user_row['numDocumentoIdObligado'])
        })

    print(f"\n✓ {total_usuarios:,} usuarios procesados correctamente")
    print(f"\n🔄 Generando archivo JSON final...")
    print(f"\n✓ Usuarios agrupados en {len(usuarios_por_factura)} facturas")

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
        # Sección Transaccion: si existe hoja 'Transaccion', anexar su primera fila como objeto
        try:
            if 'Transaccion' in xls.sheet_names:
                df_tx = pd.read_excel(xls, sheet_name='Transaccion').fillna('')
                if not df_tx.empty:
                    # Usar la primera fila como objeto
                    tx_obj = {k: (None if v == '' else v) for k, v in df_tx.iloc[0].to_dict().items()}
                    json_data['transaccion'] = tx_obj
        except Exception:
            pass
        
        # Limpiar cadenas "None" y convertirlas a null
        json_data = limpiar_none_strings(json_data)
        
        # Sanitizar strings (espacios NBSP) y formatear JSON con apertura inline de arrays
        json_sanitized = sanitize_strings(json_data)
        json_formatted = format_json_compact_arrays(json_sanitized, indent=4)
        
        # Guardar en BytesIO
        output = BytesIO()
        output.write(json_formatted.encode('utf-8'))
        output.seek(0)
        
        print(f"\n✅ JSON generado exitosamente")
        print(f"  • Usuarios exportados: {len(usuarios_data):,}")
        
        return output
    else:
        raise ValueError("No se encontraron facturas para procesar")
