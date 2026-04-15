"""
Reformador Compuestos: Convierte Excel multi-hoja de vuelta a archivo JSON
Lee el Excel con todas las hojas (Usuarios, Consultas, Procedimientos, etc.) y genera JSON
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
    'numFactura','archivoOrigen','fuente_documento'
}
EXCLUDE_PREFIXES = ('_tmp','_aux','_original')

def ordenar_campos_servicio(servicio_dict, orden_campos):
    """
    Reordena los campos de un servicio según el orden especificado.
    Los campos que no están en el orden se agregan al final.
    
    Args:
        servicio_dict: Diccionario con los datos del servicio
        orden_campos: Lista con el orden correcto de los campos
    
    Returns:
        dict: Diccionario ordenado
    """
    resultado = {}
    # Primero agregar campos en el orden especificado
    for campo in orden_campos:
        if campo in servicio_dict:
            resultado[campo] = servicio_dict[campo]
    
    # Luego agregar campos adicionales que no están en el orden (por si hay campos extra)
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
    1. Rellena tipoMedicamento vacíos con "01"
    2. [SUSPENDIDO TEMPORALMENTE] Reemplaza diagnósticos Z300, Z010, Z258, Z001, Z002, Z003, Z000, Z348, Z359 por Z718
       EXCEPCIÓN: Si codDiagnostico comienza con Z y codConsulta = 890701, NO sustituir
    """
    servicios = usuario.get('servicios', {})
    
    """
    # Diagnósticos a reemplazar
    DIAGNOSTICOS_REEMPLAZAR = ['Z300', 'Z010', 'Z258', 'Z001', 'Z002', 'Z003', 'Z000', 'Z348', 'Z359']
    DIAGNOSTICO_REEMPLAZO = 'Z718'
    """

    # Validar y corregir cada tipo de servicio
    for servicio_tipo in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos']:
        lista_servicios = servicios.get(servicio_tipo, [])
        
        if not lista_servicios:
            continue
        
        for servicio in lista_servicios:
            
            # =========================================================================
            # REEMPLAZO DE DIAGNÓSTICOS POR Z718 - SUSPENDIDO TEMPORALMENTE
            # =========================================================================
            # Reemplazar diagnósticos específicos en consultas y medicamentos
            """
            if servicio_tipo in ['consultas', 'medicamentos']:
                if 'codDiagnosticoPrincipal' in servicio:
                    diag_principal = servicio.get('codDiagnosticoPrincipal', '')
                    
                    # Excepción para consultas: Si codDiagnosticoPrincipal comienza con Z y codConsulta = 890701, NO sustituir
                    if servicio_tipo == 'consultas':
                        cod_consulta = servicio.get('codConsulta', '')
                        if diag_principal.startswith('Z') and cod_consulta == '890701':
                            continue  # Saltar este servicio sin hacer cambios
                    
                    # Verificar si el diagnóstico está en la lista de reemplazo
                    if diag_principal in DIAGNOSTICOS_REEMPLAZAR:
                        # Sustituir por Z718
                        servicio['codDiagnosticoPrincipal'] = DIAGNOSTICO_REEMPLAZO
            """
            
            # Completar tipoMedicamento en medicamentos
            if servicio_tipo == 'medicamentos':
                if 'tipoMedicamento' in servicio:
                    tipo_med = servicio.get('tipoMedicamento')
                    if tipo_med is None or tipo_med == '' or (isinstance(tipo_med, str) and tipo_med.strip() == ''):
                        servicio['tipoMedicamento'] = '01'

def format_json_compact_arrays(obj, indent=4):
    """Formatea JSON con indentación y abre arrays de objetos como [{ y compacta separadores entre objetos como },{"""
    s = json.dumps(obj, ensure_ascii=False, indent=indent)
    # Compactar apertura de arrays de objetos: ": [\n    {" -> ": [{"
    s = re.sub(r'(":\s*\[\s*)\n(\s*)\{', r'\1{', s)
    # Compactar separadores entre objetos en arrays: "},\n    {" -> "}, {"
    s = re.sub(r'\},\s*\n\s*\{', r'}, {', s)
    return s

def reformar_excel_compuestos(excel_file, filename):
    """
    Convierte Excel multi-hoja a JSON para ValidacionCompuestos
    
    Args:
        excel_file: Archivo Excel cargado
        filename: Nombre del archivo original (sin extensión)
    
    Returns:
        BytesIO: Archivo JSON en memoria
    """
    
    print("=" * 60)
    print("Reformador Compuestos: Excel → JSON")
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

    # Reemplazar NaN solo en usuarios
    df_usuarios = df_usuarios.fillna('')

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
        
        # === CONSULTAS ===
        if not df_consultas.empty:
            consultas_usuario = df_consultas[df_consultas['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            consultas_usuario = pd.DataFrame()
        
        if len(consultas_usuario) > 0:
            usuario['servicios']['consultas'] = []
            for idx_consulta, (_, consulta_row) in enumerate(consultas_usuario.iterrows(), 1):
                consulta = {}
                for col, val in consulta_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                        consulta[col] = None
                    else:
                        consulta[col] = val
                consulta['consecutivo'] = idx_consulta
                consulta = normalize_dict_fields(consulta)
                # Reordenar campos según el orden estándar RIPS
                consulta = ordenar_campos_servicio(consulta, ORDEN_CAMPOS_CONSULTAS)
                usuario['servicios']['consultas'].append(consulta)
        
        # === PROCEDIMIENTOS ===
        if not df_procedimientos.empty:
            procedimientos_usuario = df_procedimientos[df_procedimientos['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            procedimientos_usuario = pd.DataFrame()
        
        if len(procedimientos_usuario) > 0:
            usuario['servicios']['procedimientos'] = []
            for idx_proc, (_, proc_row) in enumerate(procedimientos_usuario.iterrows(), 1):
                procedimiento = {}
                for col, val in proc_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                        procedimiento[col] = None
                    else:
                        procedimiento[col] = val
                procedimiento['consecutivo'] = idx_proc
                procedimiento = normalize_dict_fields(procedimiento)
                # Reordenar campos según el orden estándar RIPS
                procedimiento = ordenar_campos_servicio(procedimiento, ORDEN_CAMPOS_PROCEDIMIENTOS)
                usuario['servicios']['procedimientos'].append(procedimiento)
        
        # === MEDICAMENTOS ===
        if not df_medicamentos.empty:
            meds_usuario = df_medicamentos[df_medicamentos['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            meds_usuario = pd.DataFrame()
        
        if len(meds_usuario) > 0:
            usuario['servicios']['medicamentos'] = []
            for _, med_row in meds_usuario.iterrows():
                med = {}
                for col, val in med_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                        med[col] = None
                    else:
                        med[col] = val
                med = normalize_dict_fields(med)
                usuario['servicios']['medicamentos'].append(med)
        
        # === OTROS SERVICIOS ===
        if not df_otros_serv.empty:
            otros_usuario = df_otros_serv[df_otros_serv['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            otros_usuario = pd.DataFrame()
        
        if len(otros_usuario) > 0:
            usuario['servicios']['otrosServicios'] = []
            for _, otro_row in otros_usuario.iterrows():
                otro = {}
                for col, val in otro_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                        otro[col] = None
                    else:
                        otro[col] = val
                otro = normalize_dict_fields(otro)
                usuario['servicios']['otrosServicios'].append(otro)
        
        # === URGENCIAS ===
        if not df_urgencias.empty:
            urg_usuario = df_urgencias[df_urgencias['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            urg_usuario = pd.DataFrame()
        
        if len(urg_usuario) > 0:
            usuario['servicios']['urgencias'] = []
            for _, urg_row in urg_usuario.iterrows():
                urg = {}
                for col, val in urg_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                        urg[col] = None
                    else:
                        urg[col] = val
                urg = normalize_dict_fields(urg)
                usuario['servicios']['urgencias'].append(urg)
        
        # === HOSPITALIZACION ===
        if not df_hospitalizacion.empty:
            hosp_usuario = df_hospitalizacion[df_hospitalizacion['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            hosp_usuario = pd.DataFrame()
        
        if len(hosp_usuario) > 0:
            usuario['servicios']['hospitalizacion'] = []
            for _, hosp_row in hosp_usuario.iterrows():
                hosp = {}
                for col, val in hosp_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                        hosp[col] = None
                    else:
                        hosp[col] = val
                hosp = normalize_dict_fields(hosp)
                usuario['servicios']['hospitalizacion'].append(hosp)
        
        # === RECIEN NACIDOS ===
        if not df_recien_nacidos.empty:
            rn_usuario = df_recien_nacidos[df_recien_nacidos['numDocumento_usuario'].astype(str) == numDocUsuario]
        else:
            rn_usuario = pd.DataFrame()
        
        if len(rn_usuario) > 0:
            usuario['servicios']['recienNacidos'] = []
            for _, rn_row in rn_usuario.iterrows():
                rn = {}
                for col, val in rn_row.items():
                    if col in EXCLUDE_INTERNAL or any(col.startswith(p) for p in EXCLUDE_PREFIXES):
                        continue
                    if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                        rn[col] = None
                    else:
                        rn[col] = val
                rn = normalize_dict_fields(rn)
                usuario['servicios']['recienNacidos'].append(rn)
        
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
                    tx_obj = {k: (None if v == '' else v) for k, v in df_tx.iloc[0].to_dict().items()}
                    json_data['transaccion'] = tx_obj
        except Exception:
            pass
        
        # Validar y corregir servicios de cada usuario
        for usuario in json_data['usuarios']:
            validar_y_corregir_servicios(usuario)
        
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
        print("=" * 60)
        
        return output
    else:
        raise ValueError("No se encontraron facturas para procesar")
