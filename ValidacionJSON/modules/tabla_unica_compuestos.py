"""
Generador de Tabla Única en Excel para ValidacionCOMPUESTOS - Versión Flask
Combina reglas de PYP y BC con validaciones específicas para Compuestos
"""

import json
import os
import re
from datetime import datetime
import pandas as pd
import random
from io import BytesIO
from modules.format_standards import (
    normalize_dict_fields,
    normalizar_documento,
    format_two_digit_code,
    format_integer,
    format_string,
    format_null_field,
    validar_tipo_documento_por_edad,
    calcular_curso_vida,
    FIELD_FORMATS,
    format_four_char_code,
    format_six_digit_code,
    format_three_digit_code
)
from modules.documentos_rips import (
    complementar_documento_profesional,
    consolidar_usuarios_por_documento,
    crear_pool_contextual,
    crear_pools_usuario,
    normalizar_ppt_pt_en_dataframes,
    validar_tipos_documento_usuarios,
)
from modules.motor_logico import (
    COMPUESTOS_CODIGOS_PROC_Z258,
    COMPUESTOS_TABLA_CUPS_FINALIDAD,
)
from modules.truncamiento_rips import truncar_campos_dataframe, truncar_codigo

# Importar pd para usar en funciones auxiliares
pd.options.mode.chained_assignment = None  # Desactivar advertencias de pandas

def normalizar_valor_campo(campo, valor):
    """Normaliza un valor según su tipo de campo definido en FIELD_FORMATS.
    
    Args:
        campo: Nombre del campo
        valor: Valor a normalizar
    
    Returns:
        Valor normalizado según el tipo de campo, o cadena vacía si está vacío
    """
    # Si el valor es NaN, None o vacío, retornar cadena vacía (no null)
    if pd.isna(valor) or valor is None or valor == '':
        return ''
    
    # Si hay una función de normalización definida, usarla
    if campo in FIELD_FORMATS:
        normalize_func, _ = FIELD_FORMATS[campo]
        return normalize_func(valor)
    
    # Si no hay formato definido, devolver como string
    return str(valor).strip()

def format_json_compact_arrays(obj, indent=4):
    """Formatea JSON con arrays en formato compacto [{ ... }]"""
    json_str = json.dumps(obj, ensure_ascii=False, indent=indent)
    
    # Mantener el formato estándar con saltos de línea para }]
    json_str = re.sub(r'(\s*)"(\w+)":\s*\[\s*\n\s+\{', r'\1"\2": [{', json_str)
    json_str = re.sub(r'\},\s*\n\s+\{', '}, {', json_str)
    
    return json_str

def generar_excel_comparativo(data_original, data_reformado, filename):
    """
    Genera un Excel en formato cuadrícula comparando JSON original vs reformado
    
    Args:
        data_original: Diccionario con datos del JSON original
        data_reformado: Diccionario con datos del JSON reformado
        filename: Nombre base del archivo
    
    Returns:
        BytesIO: Excel con comparación en cuadrícula
    """
    rows = []
    
    # Encabezado
    rows.append(['CAMPO', 'JSON ORIGINAL', 'JSON REFORMADO', 'CAMBIOS'])
    rows.append(['', '', '', ''])
    
    # Información general
    rows.append(['=== INFORMACIÓN GENERAL ===', '', '', ''])
    rows.append(['Archivo', filename, filename, ''])
    rows.append(['numFactura', data_original.get('numFactura', ''), data_reformado.get('numFactura', ''), ''])
    rows.append(['numDocumentoIdObligado', data_original.get('numDocumentoIdObligado', ''), data_reformado.get('numDocumentoIdObligado', ''), ''])
    rows.append(['', '', '', ''])
    
    # Usuarios
    usuarios_orig = data_original.get('usuarios', [])
    usuarios_ref = data_reformado.get('usuarios', [])
    
    rows.append(['=== USUARIOS ===', '', '', ''])
    rows.append(['Total Usuarios', len(usuarios_orig), len(usuarios_ref), len(usuarios_ref) - len(usuarios_orig)])
    rows.append(['', '', '', ''])
    
    # Servicios por usuario
    for idx, (user_orig, user_ref) in enumerate(zip(usuarios_orig, usuarios_ref), 1):
        doc_orig = user_orig.get('numDocumentoIdentificacion', '')
        doc_ref = user_ref.get('numDocumentoIdentificacion', '')
        
        rows.append([f'--- Usuario {idx}: {doc_orig} ---', '', '', ''])
        rows.append(['Tipo Documento', user_orig.get('tipoDocumentoIdentificacion', ''), user_ref.get('tipoDocumentoIdentificacion', ''), '✓' if user_orig.get('tipoDocumentoIdentificacion') != user_ref.get('tipoDocumentoIdentificacion') else ''])
        
        servicios_orig = user_orig.get('servicios', {})
        servicios_ref = user_ref.get('servicios', {})
        
        # Consultas
        consultas_orig = servicios_orig.get('consultas', [])
        consultas_ref = servicios_ref.get('consultas', [])
        rows.append(['  Consultas', len(consultas_orig), len(consultas_ref), len(consultas_ref) - len(consultas_orig)])
        
        # Procedimientos
        proc_orig = servicios_orig.get('procedimientos', [])
        proc_ref = servicios_ref.get('procedimientos', [])
        rows.append(['  Procedimientos', len(proc_orig), len(proc_ref), len(proc_ref) - len(proc_orig)])
        
        rows.append(['', '', '', ''])
    
    # Registros sospechosos
    total_consultas_orig = sum(len(u.get('servicios', {}).get('consultas', [])) for u in usuarios_orig)
    total_consultas_ref = sum(len(u.get('servicios', {}).get('consultas', [])) for u in usuarios_ref)
    registros_apartados = total_consultas_orig - total_consultas_ref
    
    rows.append(['=== REGISTROS SOSPECHOSOS ===', '', '', ''])
    rows.append(['Consultas con diagnóstico vacío apartadas', '', registros_apartados, ''])
    rows.append(['Guardadas en archivo', '', f'{filename}_RegistrosSospechosos.json', ''])
    
    # Crear DataFrame
    df = pd.DataFrame(rows)
    
    # Exportar a Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Comparación', index=False, header=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets['Comparación']
        worksheet.column_dimensions['A'].width = 50
        worksheet.column_dimensions['B'].width = 30
        worksheet.column_dimensions['C'].width = 30
        worksheet.column_dimensions['D'].width = 15
    
    output.seek(0)
    return output

def separar_registros_sospechosos_y_generar_json(data_original, df_usuarios, df_consultas, df_procedimientos,
                                                   df_medicamentos, df_otros_serv, df_urgencias, 
                                                   df_hospitalizacion, df_recien_nacidos, filename):
    """
    Separa registros sospechosos (consultas con diagnóstico vacío) y genera:
    1. JSON Reformado (solo registros válidos)
    2. JSON Registros Sospechosos
    3. Excel Comparativo
    
    Returns:
        tuple: (BytesIO json_reformado, BytesIO json_sospechosos, BytesIO excel_comparativo)
    """
    import copy
    
    # Validar que df_consultas tenga las columnas necesarias
    if df_consultas.empty or 'codDiagnosticoPrincipal' not in df_consultas.columns:
        print("⚠️  Advertencia: df_consultas vacío o sin columna 'codDiagnosticoPrincipal'")
        # Retornar JSON reformado completo sin separar registros
        data_reformado = reconstruir_json_desde_dataframes(
            data_original, df_usuarios, df_consultas, df_procedimientos,
            df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos
        )
        
        json_reformado = BytesIO()
        json_reformado.write(json.dumps(data_reformado, indent=2, ensure_ascii=False).encode('utf-8'))
        json_reformado.seek(0)
        
        excel_comparativo = generar_excel_comparativo(data_original, data_reformado, filename)
        
        return json_reformado, None, excel_comparativo
    
    # Identificar consultas sospechosas
    consultas_sospechosas = df_consultas[
        (df_consultas['codDiagnosticoPrincipal'].isna()) | 
        (df_consultas['codDiagnosticoPrincipal'] == '') |
        (df_consultas['codDiagnosticoPrincipal'] == 'nan')
    ].copy()
    
    # Consultas válidas (para JSON reformado)
    consultas_validas = df_consultas[
        ~((df_consultas['codDiagnosticoPrincipal'].isna()) | 
          (df_consultas['codDiagnosticoPrincipal'] == '') |
          (df_consultas['codDiagnosticoPrincipal'] == 'nan'))
    ].copy()
    
    print(f"\n📊 Separación de registros:")
    print(f"   Consultas válidas: {len(consultas_validas)}")
    print(f"   Consultas sospechosas (diagnóstico vacío): {len(consultas_sospechosas)}")
    
    # Reconstruir JSON reformado (solo válidos)
    data_reformado = reconstruir_json_desde_dataframes(
        data_original, df_usuarios, consultas_validas, df_procedimientos,
        df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos
    )
    
    # Reconstruir JSON sospechosos (solo sospechosos)
    data_sospechosos = None
    if not consultas_sospechosas.empty:
        data_sospechosos = reconstruir_json_desde_dataframes(
            data_original, df_usuarios, consultas_sospechosas, pd.DataFrame(),
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )
    
    # Generar BytesIO para JSON
    json_reformado = BytesIO()
    json_reformado.write(json.dumps(data_reformado, indent=2, ensure_ascii=False).encode('utf-8'))
    json_reformado.seek(0)
    
    json_sospechosos = None
    if data_sospechosos:
        json_sospechosos = BytesIO()
        json_sospechosos.write(json.dumps(data_sospechosos, indent=2, ensure_ascii=False).encode('utf-8'))
        json_sospechosos.seek(0)
    
    # Generar Excel comparativo
    excel_comparativo = generar_excel_comparativo(data_original, data_reformado, filename)
    
    return json_reformado, json_sospechosos, excel_comparativo

def reconstruir_json_desde_dataframes(data_original, df_usuarios, df_consultas, df_procedimientos,
                                       df_medicamentos, df_otros_serv, df_urgencias,
                                       df_hospitalizacion, df_recien_nacidos):
    """
    Reconstruye la estructura JSON desde los DataFrames procesados
    """
    import copy

    pool_contextual = crear_pool_contextual([
        (df_consultas, 'codConsulta'),
        (df_procedimientos, 'codProcedimiento'),
        (df_medicamentos, 'CUMMedicamento'),
        (df_otros_serv, 'codTecnologiaSalud'),
    ])
    
    # Crear estructura base manteniendo el orden original
    resultado = {
        'numDocumentoIdObligado': data_original.get('numDocumentoIdObligado', ''),
        'numFactura': data_original.get('numFactura', ''),
        'tipoNota': data_original.get('tipoNota'),
        'numNota': data_original.get('numNota'),
        'usuarios': []
    }
    
    if 'transaccion' in data_original:
        resultado['transaccion'] = data_original['transaccion']
    
    
    # Validar que df_consultas y df_procedimientos tengan las columnas necesarias
    if not df_consultas.empty and 'numDocumento_usuario' not in df_consultas.columns:
        print("⚠️  Advertencia: df_consultas no tiene columna 'numDocumento_usuario'")
        df_consultas = pd.DataFrame()
    
    if not df_procedimientos.empty and 'numDocumento_usuario' not in df_procedimientos.columns:
        print("⚠️  Advertencia: df_procedimientos no tiene columna 'numDocumento_usuario'")
        df_procedimientos = pd.DataFrame()
    
    # Reconstruir cada usuario
    for _, user_row in df_usuarios.iterrows():
        num_doc = user_row['numDocumentoIdentificacion']
        tipo_doc = user_row['tipoDocumentoIdentificacion']
        
        # Obtener servicios de este usuario
        user_consultas = df_consultas[
            (df_consultas['numDocumento_usuario'] == num_doc) &
            (df_consultas['tipoDocumento_usuario'] == tipo_doc)
        ] if not df_consultas.empty else pd.DataFrame()
        
        user_procedimientos = df_procedimientos[
            (df_procedimientos['numDocumento_usuario'] == num_doc) &
            (df_procedimientos['tipoDocumento_usuario'] == tipo_doc)
        ] if not df_procedimientos.empty else pd.DataFrame()
        
        user_medicamentos = df_medicamentos[
            (df_medicamentos['numDocumento_usuario'] == num_doc) &
            (df_medicamentos['tipoDocumento_usuario'] == tipo_doc)
        ] if not df_medicamentos.empty else pd.DataFrame()
        
        user_otros_serv = df_otros_serv[
            (df_otros_serv['numDocumento_usuario'] == num_doc) &
            (df_otros_serv['tipoDocumento_usuario'] == tipo_doc)
        ] if not df_otros_serv.empty else pd.DataFrame()
        
        # PASO 1: Crear pools del usuario (REGLA 10)
        tipos_validos_usuario, nums_validos_usuario = crear_pools_usuario(
            user_consultas, user_procedimientos, user_medicamentos, user_otros_serv
        )
        
        # Mantener el orden exacto de los campos como en el JSON original
        usuario = {
            'tipoDocumentoIdentificacion': tipo_doc,
            'numDocumentoIdentificacion': num_doc,
            'tipoUsuario': user_row.get('tipoUsuario', ''),
            'fechaNacimiento': user_row.get('fechaNacimiento', ''),
            'codSexo': user_row.get('codSexo', ''),
            'codPaisResidencia': user_row.get('codPaisResidencia', ''),
            'codMunicipioResidencia': user_row.get('codMunicipioResidencia', ''),
            'codZonaTerritorialResidencia': user_row.get('codZonaTerritorialResidencia', ''),
            'incapacidad': user_row.get('incapacidad', ''),
            'consecutivo': int(user_row.get('consecutivo', 0)) if pd.notna(user_row.get('consecutivo')) else 0,
            'codPaisOrigen': user_row.get('codPaisOrigen', ''),
            'servicios': {}
        }
        
        # Consultas de este usuario
        if not user_consultas.empty:
            consultas_list = []
            for idx, cons in user_consultas.iterrows():
                # Construir consulta en orden correcto
                consulta = {}
                # Orden estándar de campos de consulta
                campos_orden = [
                    'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'codConsulta',
                    'modalidadGrupoServicioTecSal', 'grupoServicios', 'codServicio',
                    'finalidadTecnologiaSalud', 'causaMotivoAtencion', 'codDiagnosticoPrincipal',
                    'codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3',
                    'tipoDiagnosticoPrincipal',
                    'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional',
                    'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador'
                ]
                
                # Agregar campos en orden
                for campo in campos_orden:
                    # cons es una Series, usar campo como key directamente
                    try:
                        valor = cons[campo]
                        tiene_campo = True
                    except (KeyError, AttributeError):
                        tiene_campo = False
                        valor = ''
                    
                    if tiene_campo:
                        # Renombrar campos profesional (quitar sufijo _profesional)
                        if campo == 'tipoDocumentoIdentificacion_profesional':
                            valor_norm = normalizar_valor_campo('tipoDocumentoIdentificacion', valor)
                            consulta['tipoDocumentoIdentificacion'] = valor_norm
                        elif campo == 'numDocumentoIdentificacion_profesional':
                            valor_norm = normalizar_valor_campo('numDocumentoIdentificacion', valor)
                            consulta['numDocumentoIdentificacion'] = valor_norm
                        else:
                            consulta[campo] = normalizar_valor_campo(campo, valor)
                    else:
                        # Si el campo no existe, agregarlo como cadena vacía para campos del profesional
                        if campo == 'tipoDocumentoIdentificacion_profesional':
                            consulta['tipoDocumentoIdentificacion'] = ''
                        elif campo == 'numDocumentoIdentificacion_profesional':
                            consulta['numDocumentoIdentificacion'] = ''
                
                # PASO 2: Aplicar complemento de documentos profesionales (REGLA 10)
                tipo_prof = consulta.get('tipoDocumentoIdentificacion', '')
                num_prof = consulta.get('numDocumentoIdentificacion', '')
                cod_prestador = consulta.get('codPrestador', '')
                cod_consulta = consulta.get('codConsulta', '')
                
                tipo_prof_complementado, num_prof_complementado = complementar_documento_profesional(
                    tipo_prof, num_prof, cod_prestador, cod_consulta,
                    pool_contextual, tipos_validos_usuario, nums_validos_usuario
                )
                
                consulta['tipoDocumentoIdentificacion'] = tipo_prof_complementado
                consulta['numDocumentoIdentificacion'] = num_prof_complementado
                
                # Agregar campos adicionales que no estén en el orden estándar
                for k, v in cons.items():
                    if k not in ['numDocumento_usuario', 'tipoDocumento_usuario', 'numFactura', 'consecutivo_consulta'] and k not in campos_orden:
                        consulta[k] = normalizar_valor_campo(k, v)
                
                consultas_list.append(consulta)
            
            # Renumerar consecutivos (igual que separador)
            for idx_servicio, consulta in enumerate(consultas_list, 1):
                consulta['consecutivo'] = idx_servicio
            
            usuario['servicios']['consultas'] = consultas_list
        
        # Procedimientos de este usuario (solo si df_procedimientos no está vacío y tiene las columnas)
        if not df_procedimientos.empty:
            user_proc = df_procedimientos[
                (df_procedimientos['numDocumento_usuario'] == num_doc) &
                (df_procedimientos['tipoDocumento_usuario'] == tipo_doc)
            ]
            
            # Filtrar procedimientos con códigos OS520, OS521, OS522, OS523, OS527
            codigos_excluir = ['OS520', 'OS521', 'OS522', 'OS523', 'OS527']
            if not user_proc.empty and 'codProcedimiento' in user_proc.columns:
                user_proc = user_proc[
                    ~user_proc['codProcedimiento'].astype(str).str.upper().isin(codigos_excluir)
                ]
            
            if not user_proc.empty:
                proc_list = []
                for idx, proc in user_proc.iterrows():
                    # Construir procedimiento en orden correcto
                    procedimiento = {}
                    # Orden estándar de campos de procedimiento
                    campos_orden = [
                        'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'idMIPRES', 'codProcedimiento',
                        'viaIngresoServicioSalud', 'modalidadGrupoServicioTecSal', 'grupoServicios', 'codServicio',
                        'finalidadTecnologiaSalud', 'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional', 
                        'codDiagnosticoPrincipal', 'codDiagnosticoRelacionado', 'codComplicacion',
                        'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador'
                    ]
                    
                    # Agregar campos en orden
                    for campo in campos_orden:
                        # proc es una Series, usar campo como key directamente
                        try:
                            valor = proc[campo]
                            tiene_campo = True
                        except (KeyError, AttributeError):
                            tiene_campo = False
                            valor = ''
                        
                        if tiene_campo:
                            # Renombrar campos profesional (quitar sufijo _profesional)
                            if campo == 'tipoDocumentoIdentificacion_profesional':
                                valor_norm = normalizar_valor_campo('tipoDocumentoIdentificacion', valor)
                                procedimiento['tipoDocumentoIdentificacion'] = valor_norm
                            elif campo == 'numDocumentoIdentificacion_profesional':
                                valor_norm = normalizar_valor_campo('numDocumentoIdentificacion', valor)
                                procedimiento['numDocumentoIdentificacion'] = valor_norm
                            else:
                                procedimiento[campo] = normalizar_valor_campo(campo, valor)
                        else:
                            # Si el campo no existe, agregarlo como cadena vacía para campos del profesional
                            if campo == 'tipoDocumentoIdentificacion_profesional':
                                procedimiento['tipoDocumentoIdentificacion'] = ''
                            elif campo == 'numDocumentoIdentificacion_profesional':
                                procedimiento['numDocumentoIdentificacion'] = ''
                    
                    # PASO 2: Aplicar complemento de documentos profesionales (REGLA 10)
                    tipo_prof = procedimiento.get('tipoDocumentoIdentificacion', '')
                    num_prof = procedimiento.get('numDocumentoIdentificacion', '')
                    cod_prestador = procedimiento.get('codPrestador', '')
                    cod_procedimiento = procedimiento.get('codProcedimiento', '')
                    
                    tipo_prof_complementado, num_prof_complementado = complementar_documento_profesional(
                        tipo_prof, num_prof, cod_prestador, cod_procedimiento,
                        pool_contextual, tipos_validos_usuario, nums_validos_usuario
                    )
                    
                    procedimiento['tipoDocumentoIdentificacion'] = tipo_prof_complementado
                    procedimiento['numDocumentoIdentificacion'] = num_prof_complementado
                    
                    # Agregar campos adicionales que no estén en el orden estándar
                    for k, v in proc.items():
                        if k not in ['numDocumento_usuario', 'tipoDocumento_usuario', 'numFactura', 'consecutivo_procedimiento'] and k not in campos_orden:
                            procedimiento[k] = normalizar_valor_campo(k, v)
                    
                    proc_list.append(procedimiento)
                
                # Renumerar consecutivos (igual que separador)
                for idx_servicio, proc in enumerate(proc_list, 1):
                    proc['consecutivo'] = idx_servicio
                
                usuario['servicios']['procedimientos'] = proc_list
        
        # Medicamentos de este usuario
        if not df_medicamentos.empty:
            user_med = df_medicamentos[
                (df_medicamentos['numDocumento_usuario'] == num_doc) &
                (df_medicamentos['tipoDocumento_usuario'] == tipo_doc)
            ]
            
            if not user_med.empty:
                med_list = []
                for idx, med in user_med.iterrows():
                    medicamento = {}
                    
                    # Copiar todos los campos excepto los excluidos
                    for k, v in med.items():
                        if k not in ['numDocumento_usuario', 'tipoDocumento_usuario', 'numFactura', 'consecutivo_medicamento',
                                     'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional']:
                            medicamento[k] = normalizar_valor_campo(k, v)
                    
                    # Renombrar campos profesionales (quitar sufijo _profesional)
                    try:
                        tipo_prof = med['tipoDocumentoIdentificacion_profesional']
                        medicamento['tipoDocumentoIdentificacion'] = normalizar_valor_campo('tipoDocumentoIdentificacion', tipo_prof)
                    except (KeyError, AttributeError):
                        medicamento['tipoDocumentoIdentificacion'] = ''
                    
                    try:
                        num_prof = med['numDocumentoIdentificacion_profesional']
                        medicamento['numDocumentoIdentificacion'] = normalizar_valor_campo('numDocumentoIdentificacion', num_prof)
                    except (KeyError, AttributeError):
                        medicamento['numDocumentoIdentificacion'] = ''
                    
                    # PASO 2: Aplicar complemento de documentos profesionales (REGLA 10)
                    tipo_prof = medicamento.get('tipoDocumentoIdentificacion', '')
                    num_prof = medicamento.get('numDocumentoIdentificacion', '')
                    cod_prestador = medicamento.get('codPrestador', '')
                    cum_medicamento = medicamento.get('CUMMedicamento', '')
                    
                    tipo_prof_complementado, num_prof_complementado = complementar_documento_profesional(
                        tipo_prof, num_prof, cod_prestador, cum_medicamento,
                        pool_contextual, tipos_validos_usuario, nums_validos_usuario
                    )
                    
                    medicamento['tipoDocumentoIdentificacion'] = tipo_prof_complementado
                    medicamento['numDocumentoIdentificacion'] = num_prof_complementado
                    
                    med_list.append(medicamento)
                
                # Renumerar consecutivos (igual que separador)
                for idx_servicio, med in enumerate(med_list, 1):
                    med['consecutivo'] = idx_servicio
                
                usuario['servicios']['medicamentos'] = med_list
        
        # Otros Servicios de este usuario
        if not df_otros_serv.empty:
            user_otros = df_otros_serv[
                (df_otros_serv['numDocumento_usuario'] == num_doc) &
                (df_otros_serv['tipoDocumento_usuario'] == tipo_doc)
            ]
            
            if not user_otros.empty:
                otros_list = []
                for idx, otro in user_otros.iterrows():
                    otro_servicio = {}
                    
                    # Copiar todos los campos excepto los excluidos
                    for k, v in otro.items():
                        if k not in ['numDocumento_usuario', 'tipoDocumento_usuario', 'numFactura', 'consecutivo_otro',
                                     'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional']:
                            otro_servicio[k] = normalizar_valor_campo(k, v)
                    
                    # Renombrar campos profesionales (quitar sufijo _profesional)
                    try:
                        tipo_prof = otro['tipoDocumentoIdentificacion_profesional']
                        otro_servicio['tipoDocumentoIdentificacion'] = normalizar_valor_campo('tipoDocumentoIdentificacion', tipo_prof)
                    except (KeyError, AttributeError):
                        otro_servicio['tipoDocumentoIdentificacion'] = ''
                    
                    try:
                        num_prof = otro['numDocumentoIdentificacion_profesional']
                        otro_servicio['numDocumentoIdentificacion'] = normalizar_valor_campo('numDocumentoIdentificacion', num_prof)
                    except (KeyError, AttributeError):
                        otro_servicio['numDocumentoIdentificacion'] = ''
                    
                    # PASO 2: Aplicar complemento de documentos profesionales (REGLA 10)
                    tipo_prof = otro_servicio.get('tipoDocumentoIdentificacion', '')
                    num_prof = otro_servicio.get('numDocumentoIdentificacion', '')
                    cod_prestador = otro_servicio.get('codPrestador', '')
                    cod_tecnologia = otro_servicio.get('codTecnologiaSalud', '')
                    
                    tipo_prof_complementado, num_prof_complementado = complementar_documento_profesional(
                        tipo_prof, num_prof, cod_prestador, cod_tecnologia,
                        pool_contextual, tipos_validos_usuario, nums_validos_usuario
                    )
                    
                    otro_servicio['tipoDocumentoIdentificacion'] = tipo_prof_complementado
                    otro_servicio['numDocumentoIdentificacion'] = num_prof_complementado
                    
                    otros_list.append(otro_servicio)
                
                # Renumerar consecutivos (igual que separador)
                for idx_servicio, otro in enumerate(otros_list, 1):
                    otro['consecutivo'] = idx_servicio
                
                usuario['servicios']['otrosServicios'] = otros_list
        
        # Urgencias de este usuario
        if not df_urgencias.empty:
            user_urg = df_urgencias[
                (df_urgencias['numDocumento_usuario'] == num_doc) &
                (df_urgencias['tipoDocumento_usuario'] == tipo_doc)
            ]
            
            if not user_urg.empty:
                urg_list = []
                for idx, urg in user_urg.iterrows():
                    urgencia = {}
                    
                    # IMPORTANTE: Urgencias NO llevan campos de profesionales según normativa
                    # Copiar todos los campos excepto los excluidos (incluyendo campos profesionales)
                    for k, v in urg.items():
                        if k not in ['numDocumento_usuario', 'tipoDocumento_usuario', 'numFactura', 'consecutivo_urgencia',
                                     'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional',
                                     'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion']:
                            urgencia[k] = normalizar_valor_campo(k, v)
                    
                    # NO agregar campos profesionales para urgencias
                    
                    urg_list.append(urgencia)
                
                # Renumerar consecutivos (igual que separador)
                for idx_servicio, urg in enumerate(urg_list, 1):
                    urg['consecutivo'] = idx_servicio
                
                usuario['servicios']['urgencias'] = urg_list
        
        # Hospitalización de este usuario
        if not df_hospitalizacion.empty:
            user_hosp = df_hospitalizacion[
                (df_hospitalizacion['numDocumento_usuario'] == num_doc) &
                (df_hospitalizacion['tipoDocumento_usuario'] == tipo_doc)
            ]
            
            if not user_hosp.empty:
                hosp_list = []
                for idx, hosp in user_hosp.iterrows():
                    # Hospitalización NO lleva campos profesionales - filtrar explícitamente
                    hospitalizacion = {k: v for k, v in hosp.items()
                                      if k not in ['numDocumento_usuario', 'tipoDocumento_usuario', 'numFactura', 'consecutivo_hospitalizacion',
                                                   'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
                                                   'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional']}
                    
                    # Convertir NaN a None (null en JSON)
                    for key in list(hospitalizacion.keys()):
                        if pd.isna(hospitalizacion[key]):
                            hospitalizacion[key] = None
                    
                    hosp_list.append(hospitalizacion)
                
                # Renumerar consecutivos (igual que separador)
                for idx_servicio, hosp in enumerate(hosp_list, 1):
                    hosp['consecutivo'] = idx_servicio
                
                usuario['servicios']['hospitalizacion'] = hosp_list
        
        # Recién Nacidos de este usuario
        if not df_recien_nacidos.empty:
            user_rn = df_recien_nacidos[
                (df_recien_nacidos['numDocumento_usuario'] == num_doc) &
                (df_recien_nacidos['tipoDocumento_usuario'] == tipo_doc)
            ]
            
            if not user_rn.empty:
                rn_list = []
                for idx, rn in user_rn.iterrows():
                    recien_nacido = {}
                    
                    # Copiar todos los campos excepto los excluidos
                    for k, v in rn.items():
                        if k not in ['numDocumento_usuario', 'tipoDocumento_usuario', 'numFactura', 'consecutivo_rn',
                                     'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional']:
                            recien_nacido[k] = normalizar_valor_campo(k, v)
                    
                    # Renombrar campos profesionales (quitar sufijo _profesional)
                    try:
                        tipo_prof = rn['tipoDocumentoIdentificacion_profesional']
                        recien_nacido['tipoDocumentoIdentificacion'] = normalizar_valor_campo('tipoDocumentoIdentificacion', tipo_prof)
                    except (KeyError, AttributeError):
                        recien_nacido['tipoDocumentoIdentificacion'] = ''
                    
                    try:
                        num_prof = rn['numDocumentoIdentificacion_profesional']
                        recien_nacido['numDocumentoIdentificacion'] = normalizar_valor_campo('numDocumentoIdentificacion', num_prof)
                    except (KeyError, AttributeError):
                        recien_nacido['numDocumentoIdentificacion'] = ''
                    
                    rn_list.append(recien_nacido)
                
                # Renumerar consecutivos (igual que separador)
                for idx_servicio, rn in enumerate(rn_list, 1):
                    rn['consecutivo'] = idx_servicio
                
                usuario['servicios']['recienNacidos'] = rn_list
        
        # Solo agregar usuario si tiene al menos un servicio
        if usuario['servicios']:
            resultado['usuarios'].append(usuario)
    
    return resultado

def validar_tipos_documento_por_edad(usuarios_list):
    return validar_tipos_documento_usuarios(usuarios_list, include_cn_priority=True)


def consolidar_usuarios_duplicados(usuarios_list):
    return consolidar_usuarios_por_documento(
        usuarios_list,
        ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos'],
    )

def aplicar_cambios_compuestos_json(datos_json, config_eps=None, generar_reporte=False):
    """
    Aplica las reglas de COMPUESTOS y rastrea todos los cambios realizados en todos los servicios.

    Args:
        datos_json   : Diccionario con la estructura completa del RIPS-JSON
        config_eps   : dict con 'cups_contrato' (set de CUPS del contrato activo).
                       Si None o conjunto vacío, no se aplica filtro por contrato.
        generar_reporte: Si True, retorna también lista de cambios
    - CONSULTAS:
      * Si codDiagnosticoPrincipal vacío → vacío se mantiene (no se modifica)
      * Registrar cualquier cambio de finalidad/causa que se aplique
    
    - PROCEDIMIENTOS:
            * Si diagnóstico vacío:
                1. Si codProcedimiento en COMPUESTOS_CODIGOS_PROC_Z258 → Z258, finalidad=14
                2. Si no, buscar diagnóstico de consulta con misma fecha
                3. Si no, buscar en COMPUESTOS_TABLA_CUPS_FINALIDAD
      * Si codProcedimiento comienza con 5DS o 865 → finalidad=16
    
    Args:
        datos_json: Diccionario con la estructura completa del RIPS-JSON
        generar_reporte: Si True, retorna también lista de cambios
    
    Returns:
        Si generar_reporte=False: dict con JSON modificado
        Si generar_reporte=True: tuple (dict JSON modificado, list cambios_compuestos)
    """
    
    # Contadores para debug
    debug_stats = {
        'consultas_truncadas_principal': 0,
        'consultas_truncadas_relacionadas': 0,
        'procedimientos_truncados_principal': 0,
        'procedimientos_truncados_relacionado': 0,
        'urgencias_campos_eliminados': 0,
        'urgencias_truncadas': 0,
        'hospitalizacion_campos_eliminados': 0,
        'hospitalizacion_truncadas': 0,
        'sustituciones_diagnostico': 0
    }
    
    cambios_compuestos = [] if generar_reporte else None
    
    from modules.motor_logico import (
        COMPUESTOS_JSON_SUSTITUCIONES_Z,
        _resolver_consulta_compuestos_registro,
        _resolver_procedimiento_compuestos_registro,
    )
    
    usuarios = datos_json.get('usuarios', [])
    
    # Crear índice de diagnósticos de consultas por usuario/fecha para búsqueda rápida
    indice_consultas = {}
    if generar_reporte:
        for usuario in usuarios:
            num_doc = usuario.get('numDocumentoIdentificacion', '')
            tipo_doc = usuario.get('tipoDocumentoIdentificacion', '')
            servicios = usuario.get('servicios', {})
            
            for consulta in servicios.get('consultas', []):
                fecha_atencion = consulta.get('fechaInicioAtencion', '')
                if fecha_atencion:
                    # Extraer solo la parte de fecha (aaaa-mm-dd)
                    fecha_solo = fecha_atencion.split(' ')[0] if ' ' in str(fecha_atencion) else str(fecha_atencion)
                    clave = (num_doc, tipo_doc, fecha_solo)
                    
                    if clave not in indice_consultas:
                        indice_consultas[clave] = []
                    
                    cod_diag = str(consulta.get('codDiagnosticoPrincipal', '')).strip()
                    if cod_diag and cod_diag != '' and cod_diag != 'nan':
                        indice_consultas[clave].append(cod_diag)
    
    sustituciones = COMPUESTOS_JSON_SUSTITUCIONES_Z
    
    # Archivo de debug
    debug_log = []
    
    for usuario in usuarios:
        num_doc_usuario = usuario.get('numDocumentoIdentificacion', '')
        tipo_doc_usuario = usuario.get('tipoDocumentoIdentificacion', '')
        fecha_nacimiento = usuario.get('fechaNacimiento', '')
        servicios = usuario.get('servicios', {})
        
        # ======================================================================
        # PROCESAR CONSULTAS
        # ======================================================================
        cups_contrato = config_eps.get('cups_contrato', set()) if config_eps else set()

        for idx_consulta, consulta in enumerate(servicios.get('consultas', []), 1):
            cod_diag_original = str(consulta.get('codDiagnosticoPrincipal', '')).strip()
            cod_consulta = str(consulta.get('codConsulta', '')).strip()
            finalidad_original = consulta.get('finalidadTecnologiaSalud', '')
            causa_original = consulta.get('causaMotivoAtencion', '')
            if cod_diag_original and len(cod_diag_original) > 4:
                debug_stats['consultas_truncadas_principal'] += 1
                cod_diag_original = truncar_codigo(cod_diag_original)

            for campo in ['codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3']:
                diag_rel = str(consulta.get(campo, '')).strip()
                if diag_rel and len(diag_rel) > 4:
                    debug_stats['consultas_truncadas_relacionadas'] += 1

            if (not cod_diag_original or cod_diag_original in ['', 'nan', 'null', 'none']) and cod_consulta in ['890203', '890303', '890703']:
                debug_log.append({
                    'tipo': 'CONSULTA_PRE',
                    'usuario': f"{tipo_doc_usuario}-{num_doc_usuario}",
                    'consecutivo': idx_consulta,
                    'codConsulta': cod_consulta,
                    'codDiag_original': cod_diag_original,
                    'finalidad_original': finalidad_original,
                    'causa_original': causa_original,
                })

            resultado = _resolver_consulta_compuestos_registro(consulta, sustituciones, config_eps)
            cod_diag_final = str(consulta.get('codDiagnosticoPrincipal', '')).strip()
            cambio_diagnostico = cod_diag_original != cod_diag_final
            cambio_finalidad = finalidad_original != consulta.get('finalidadTecnologiaSalud', '')
            cambio_causa = causa_original != consulta.get('causaMotivoAtencion', '')
            if cambio_diagnostico:
                debug_stats['sustituciones_diagnostico'] += 1

            if cambio_diagnostico and cod_consulta in ['890203', '890303', '890703']:
                debug_log.append({
                    'tipo': 'CONSULTA_POST',
                    'usuario': f"{tipo_doc_usuario}-{num_doc_usuario}",
                    'consecutivo': idx_consulta,
                    'codConsulta': cod_consulta,
                    'codDiag_asignado': cod_diag_final,
                    'finalidad_asignada': consulta.get('finalidadTecnologiaSalud', ''),
                    'causa_asignada': consulta.get('causaMotivoAtencion', ''),
                    'cambio_aplicado': 'SI',
                })
            
            # Registrar cambios
            if generar_reporte and ((cambio_diagnostico or cambio_finalidad or cambio_causa) or not resultado['en_contrato']):
                cambio = {
                    'Tipo': 'CONSULTA',
                    'Usuario_Documento': num_doc_usuario,
                    'Usuario_TipoDoc': tipo_doc_usuario,
                    'Curso_Vida': calcular_curso_vida(fecha_nacimiento, consulta.get('fechaInicioAtencion', '')),
                    'Consecutivo_Servicio': idx_consulta,
                    'Codigo_Consulta': cod_consulta,
                    'Diagnostico_Original': cod_diag_original if cod_diag_original else '(vacío)',
                    'Diagnostico_Final': cod_diag_final if cod_diag_final else '(vacío)',
                    'Cambio_Diagnostico': 'Sí' if cambio_diagnostico else 'No',
                    'Finalidad_Original': finalidad_original,
                    'Finalidad_Nueva': consulta.get('finalidadTecnologiaSalud', ''),
                    'Cambio_Finalidad': 'Sí' if cambio_finalidad else 'No',
                    'Causa_Original': causa_original,
                    'Causa_Nueva': consulta.get('causaMotivoAtencion', ''),
                    'Cambio_Causa': 'Sí' if cambio_causa else 'No',
                    'En_Contrato': 'Sí' if resultado['en_contrato'] else 'No',
                }
                cambios_compuestos.append(cambio)
        
        # ======================================================================
        # PROCESAR PROCEDIMIENTOS
        # ======================================================================
        for idx_proc, procedimiento in enumerate(servicios.get('procedimientos', []), 1):
            cod_diag_original = str(procedimiento.get('codDiagnosticoPrincipal', '')).strip()
            cod_proc = str(procedimiento.get('codProcedimiento', '')).strip()
            finalidad_original = procedimiento.get('finalidadTecnologiaSalud', '')
            if cod_diag_original and len(cod_diag_original) > 4:
                debug_stats['procedimientos_truncados_principal'] += 1
                cod_diag_original = truncar_codigo(cod_diag_original)

            diag_rel = str(procedimiento.get('codDiagnosticoRelacionado', '')).strip()
            if diag_rel and len(diag_rel) > 4:
                debug_stats['procedimientos_truncados_relacionado'] += 1

            fecha_proc = procedimiento.get('fechaInicioAtencion', '')
            fecha_proc_solo = fecha_proc.split(' ')[0] if fecha_proc and ' ' in str(fecha_proc) else str(fecha_proc)
            clave = (num_doc_usuario, tipo_doc_usuario, fecha_proc_solo) if fecha_proc_solo else None
            diagnosticos_consulta = indice_consultas.get(clave, []) if clave else []

            resultado = _resolver_procedimiento_compuestos_registro(
                procedimiento,
                COMPUESTOS_CODIGOS_PROC_Z258,
                COMPUESTOS_TABLA_CUPS_FINALIDAD,
                diagnosticos_consulta_fecha=diagnosticos_consulta,
                config_eps=config_eps,
            )

            cod_diag_final = str(procedimiento.get('codDiagnosticoPrincipal', '')).strip()
            cambio_diagnostico = cod_diag_original != cod_diag_final
            cambio_finalidad = finalidad_original != procedimiento.get('finalidadTecnologiaSalud', '')
            razon_cambio = ''
            if not cod_diag_original and cod_diag_final == 'Z258':
                razon_cambio = 'Código en COMPUESTOS_CODIGOS_PROC_Z258'
            elif not cod_diag_original and diagnosticos_consulta and cod_diag_final == diagnosticos_consulta[0]:
                razon_cambio = 'Copiado de consulta con misma fecha'
            elif not cod_diag_original and cod_proc in COMPUESTOS_TABLA_CUPS_FINALIDAD and cod_diag_final:
                razon_cambio = 'Diagnóstico de COMPUESTOS_TABLA_CUPS_FINALIDAD'
            elif cambio_finalidad and (cod_proc.startswith('5DS') or cod_proc.startswith('865')):
                razon_cambio = 'Código procedimiento comienza con 5DS/865'

            if cambio_diagnostico:
                debug_stats['sustituciones_diagnostico'] += 1
            
            # Registrar cambios
            if generar_reporte and ((cambio_diagnostico or cambio_finalidad) or not resultado['en_contrato']):
                cambio = {
                    'Tipo': 'PROCEDIMIENTO',
                    'Usuario_Documento': num_doc_usuario,
                    'Usuario_TipoDoc': tipo_doc_usuario,
                    'Curso_Vida': calcular_curso_vida(fecha_nacimiento, procedimiento.get('fechaInicioAtencion', '')),
                    'Consecutivo_Servicio': idx_proc,
                    'Codigo_Procedimiento': cod_proc,
                    'Diagnostico_Original': cod_diag_original if cod_diag_original else '(vacío)',
                    'Diagnostico_Final': cod_diag_final if cod_diag_final else '(vacío)',
                    'Cambio_Diagnostico': 'Sí' if cambio_diagnostico else 'No',
                    'Razon_Cambio': razon_cambio,
                    'Finalidad_Original': finalidad_original,
                    'Finalidad_Nueva': procedimiento.get('finalidadTecnologiaSalud', ''),
                    'Cambio_Finalidad': 'Sí' if cambio_finalidad else 'No',
                    'En_Contrato': 'Sí' if resultado['en_contrato'] else 'No',
                }
                cambios_compuestos.append(cambio)
        
        # ======================================================================
        # MEDICAMENTOS, OTROS SERVICIOS, URGENCIAS, HOSPITALIZACIÓN, RECIÉN NACIDOS
        # No tienen reglas específicas de cambio, pero podríamos rastrear
        # cambios futuros aquí si es necesario
        # ======================================================================
    
    # ======================================================================
    # PROCESAR URGENCIAS Y HOSPITALIZACIÓN - Eliminar campos profesionales y truncar diagnósticos
    # ======================================================================
    for usuario in usuarios:
        servicios = usuario.get('servicios', {})
        
        # PROCESAR URGENCIAS
        for urgencia in servicios.get('urgencias', []):
            # Eliminar campos profesionales que no forman parte de urgencias en RIPS
            if urgencia.pop('tipoDocumentoIdentificacion', None) is not None:
                debug_stats['urgencias_campos_eliminados'] += 1
            if urgencia.pop('numDocumentoIdentificacion', None) is not None:
                debug_stats['urgencias_campos_eliminados'] += 1
            
            # Truncar diagnósticos a 4 caracteres
            for campo in ['codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
                         'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
                         'codDiagnosticoCausaMuerte']:
                diag = str(urgencia.get(campo, '')).strip()
                if diag and len(diag) > 4:
                    urgencia[campo] = truncar_codigo(diag)
                    debug_stats['urgencias_truncadas'] += 1
        
        # PROCESAR HOSPITALIZACIÓN
        for hospitalizacion in servicios.get('hospitalizacion', []):
            # Eliminar campos profesionales que no forman parte de hospitalización en RIPS
            if hospitalizacion.pop('tipoDocumentoIdentificacion', None) is not None:
                debug_stats['hospitalizacion_campos_eliminados'] += 1
            if hospitalizacion.pop('numDocumentoIdentificacion', None) is not None:
                debug_stats['hospitalizacion_campos_eliminados'] += 1
            
            # Truncar diagnósticos a 4 caracteres
            for campo in ['codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
                         'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
                         'codDiagnosticoCausaMuerte', 'codComplicacion']:
                diag = str(hospitalizacion.get(campo, '')).strip()
                if diag and len(diag) > 4:
                    hospitalizacion[campo] = truncar_codigo(diag)
                    debug_stats['hospitalizacion_truncadas'] += 1
    
    # Guardar debug log
    if debug_log:
        import json
        import os
        debug_path = os.path.join('outputs', 'debug_compuestos_consultas.json')
        try:
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(debug_log, f, ensure_ascii=False, indent=2)
            print(f"\n📝 DEBUG: {len(debug_log)} eventos registrados en {debug_path}")
        except Exception as e:
            print(f"\n⚠️  Error guardando debug log: {e}")
    
    # Imprimir estadísticas de debug
    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS DE PROCESAMIENTO COMPUESTOS")
    print("="*60)
    print(f"✂️  Truncación de diagnósticos:")
    print(f"   • Consultas (principal): {debug_stats['consultas_truncadas_principal']}")
    print(f"   • Consultas (relacionados 1/2/3): {debug_stats['consultas_truncadas_relacionadas']}")
    print(f"   • Procedimientos (principal): {debug_stats['procedimientos_truncados_principal']}")
    print(f"   • Procedimientos (relacionado): {debug_stats['procedimientos_truncados_relacionado']}")
    print(f"   • Urgencias: {debug_stats['urgencias_truncadas']}")
    print(f"   • Hospitalización: {debug_stats['hospitalizacion_truncadas']}")
    print(f"\n🗑️  Eliminación de campos profesionales:")
    print(f"   • Urgencias: {debug_stats['urgencias_campos_eliminados']} campos eliminados")
    print(f"   • Hospitalización: {debug_stats['hospitalizacion_campos_eliminados']} campos eliminados")
    print(f"\n🔄 Sustituciones de diagnósticos: {debug_stats['sustituciones_diagnostico']}")
    print("="*60 + "\n")
    
    if generar_reporte:
        return datos_json, cambios_compuestos
    else:
        return datos_json

def procesar_json_compuestos(json_file, filename):
    """
    Procesa un archivo JSON de Validacion COMPUESTOS y genera archivos:
    1. Excel ORIGINAL (sin correcciones) para descarga
    2. Excel CORREGIDO (con validaciones) para generar JSON reformado
    3. Reporte de diagnósticos vacíos (si aplica) - para análisis
    4. JSON Reformado (con TODOS los registros, incluidos diagnósticos vacíos)
    
    Args:
        json_file: Archivo JSON cargado
        filename: Nombre del archivo original (sin extensión)
    
    Returns:
        tuple: (excel_original, excel_corregido, reporte, json_reformado)
    """
    
    # Usar fecha actual para cálculo de edad
    cutoff_date = datetime.now()
    
    print("=" * 60)
    print("Procesando archivo JSON COMPUESTOS...")
    print("=" * 60)
    
    # PASO 0: Generar Excel ORIGINAL sin correcciones
    from modules.generador_excel_original import generar_excel_original_compuestos
    json_file.seek(0)
    excel_original = generar_excel_original_compuestos(json_file, filename)
    json_file.seek(0)  # Reset para procesamiento con validaciones

    # Data structures
    usuarios_data = []
    # En Compuestos preservaremos todas las llaves originales
    consultas_rows = []
    procedimientos_rows = []
    medicamentos_rows = []
    otros_serv_rows = []
    urgencias_rows = []
    hospitalizacion_rows = []
    rn_rows = []

    try:
        data = json.load(json_file)
        
        numFactura = data.get('numFactura', '')
        numDocumentoIdObligado = data.get('numDocumentoIdObligado', '')
        archivoOrigen = filename + '.json'
        transaccion_top = data.get('transaccion') if isinstance(data, dict) else None
        
        # PASO 1: Validar tipos de documento por edad (TODOS los usuarios)
        usuarios_list = data.get('usuarios', [])
        usuarios_list = validar_tipos_documento_por_edad(usuarios_list)
        
        # PASO 2: Consolidar usuarios duplicados
        usuarios_list = consolidar_usuarios_duplicados(usuarios_list)
        
        for user in usuarios_list:
            # Extract user basic info - NORMALIZAR documentos desde el inicio
            numDocUsuario = normalizar_documento(user.get('numDocumentoIdentificacion', ''))
            tipoDocUsuario = user.get('tipoDocumentoIdentificacion', '')
            fechaNac = user.get('fechaNacimiento', '')
            
            # Nota: La validación de tipo de documento se hace ANTES en validar_tipos_documento_por_edad()
            
            # Calculate age
            edad = None
            try:
                if fechaNac:
                    birth = datetime.strptime(fechaNac, "%Y-%m-%d")
                    edad = cutoff_date.year - birth.year - ((cutoff_date.month, cutoff_date.day) < (birth.month, birth.day))
            except:
                pass
            
            servicios = user.get('servicios', {})
            consultas = servicios.get('consultas', [])
            procedimientos = servicios.get('procedimientos', [])
            medicamentos = servicios.get('medicamentos', [])
            otros_servicios = servicios.get('otrosServicios', [])
            urgencias = servicios.get('urgencias', [])
            hospitalizacion = servicios.get('hospitalizacion', [])
            recien_nacidos = servicios.get('recienNacidos', [])
            
            # Collect dates and unique values for summary
            fechas_atencion = []
            prestadores_unicos = set()
            diagnosticos_unicos = set()
            
            # Contadores de consecutivos por usuario (para fallback si no existe en JSON)
            consecutivo_consulta_counter = 1
            consecutivo_procedimiento_counter = 1
            
            # Process consultas preservando columnas extra
            for idx, consulta in enumerate(consultas, 1):
                fecha = consulta.get('fechaInicioAtencion', '')
                fechas_atencion.append(fecha)
                codPrestador = consulta.get('codPrestador', '')
                codServicio = consulta.get('codServicio', '')
                codConsulta = consulta.get('codConsulta', '')
                diagPrincipal = consulta.get('codDiagnosticoPrincipal', '')
                prestadores_unicos.add(codPrestador)
                if diagPrincipal:
                    diagnosticos_unicos.add(diagPrincipal)
                # Copiar diccionario preservando tipos originales
                row = dict(consulta)
                # Normalizar solo campos que pueden tener decimales no deseados
                if 'codPrestador' in row:
                    row['codPrestador'] = normalizar_documento(row['codPrestador'])
                if 'causaMotivoAtencion' in row:
                    row['causaMotivoAtencion'] = format_two_digit_code(row['causaMotivoAtencion'])
                if 'conceptoRecaudo' in row:
                    row['conceptoRecaudo'] = format_two_digit_code(row['conceptoRecaudo'])
                row['numDocumento_usuario'] = numDocUsuario
                row['tipoDocumento_usuario'] = tipoDocUsuario
                row['numFactura'] = numFactura
                # Usar consecutivo del JSON o generar uno secuencial
                consecutivo_actual = consulta.get('consecutivo')
                if consecutivo_actual is None or consecutivo_actual == '':
                    consecutivo_actual = consecutivo_consulta_counter
                    consecutivo_consulta_counter += 1
                row['consecutivo_consulta'] = consecutivo_actual
                row.setdefault('tipoDocumentoIdentificacion_profesional', consulta.get('tipoDocumentoIdentificacion', ''))
                doc_prof = consulta.get('numDocumentoIdentificacion', '')
                row.setdefault('numDocumentoIdentificacion_profesional', normalizar_documento(doc_prof) if doc_prof else '')
                consultas_rows.append(row)
            
            # Process procedimientos preservando columnas extra
            for idx, proc in enumerate(procedimientos, 1):
                fecha = proc.get('fechaInicioAtencion', '')
                fechas_atencion.append(fecha)
                codPrestador = proc.get('codPrestador', '')
                codServicio = proc.get('codServicio', '')
                codProcedimiento = proc.get('codProcedimiento', '')
                diagPrincipal = proc.get('codDiagnosticoPrincipal', '')
                prestadores_unicos.add(codPrestador)
                if diagPrincipal:
                    diagnosticos_unicos.add(diagPrincipal)
                # Copiar diccionario preservando tipos originales
                rowp = dict(proc)
                # Normalizar solo campos que pueden tener decimales no deseados
                if 'codPrestador' in rowp:
                    rowp['codPrestador'] = normalizar_documento(rowp['codPrestador'])
                if 'numDocumentoIdentificacion' in rowp:
                    rowp['numDocumentoIdentificacion'] = normalizar_documento(rowp['numDocumentoIdentificacion'])
                if 'conceptoRecaudo' in rowp:
                    rowp['conceptoRecaudo'] = format_two_digit_code(rowp['conceptoRecaudo'])
                rowp['numDocumento_usuario'] = numDocUsuario
                rowp['tipoDocumento_usuario'] = tipoDocUsuario
                rowp['numFactura'] = numFactura
                # Usar consecutivo del JSON o generar uno secuencial
                consecutivo_actual = proc.get('consecutivo')
                if consecutivo_actual is None or consecutivo_actual == '':
                    consecutivo_actual = consecutivo_procedimiento_counter
                    consecutivo_procedimiento_counter += 1
                rowp['consecutivo_procedimiento'] = consecutivo_actual
                rowp.setdefault('tipoDocumentoIdentificacion_profesional', proc.get('tipoDocumentoIdentificacion', ''))
                doc_prof_proc = proc.get('numDocumentoIdentificacion', '')
                rowp.setdefault('numDocumentoIdentificacion_profesional', normalizar_documento(doc_prof_proc) if doc_prof_proc else '')
                procedimientos_rows.append(rowp)

            # Process medicamentos
            for idx, med in enumerate(medicamentos, 1):
                # Copiar diccionario preservando tipos originales
                rowm = dict(med)
                # Normalizar solo campos que pueden tener decimales no deseados
                if 'codPrestador' in rowm:
                    rowm['codPrestador'] = normalizar_documento(rowm['codPrestador'])
                if 'numDocumentoIdentificacion' in rowm:
                    rowm['numDocumentoIdentificacion'] = normalizar_documento(rowm['numDocumentoIdentificacion'])
                if 'tipoMedicamento' in rowm:
                    rowm['tipoMedicamento'] = format_two_digit_code(rowm['tipoMedicamento'])
                if 'conceptoRecaudo' in rowm:
                    rowm['conceptoRecaudo'] = format_two_digit_code(rowm['conceptoRecaudo'])
                if rowm.get('unidadMinDispensa') == 0:
                    rowm['unidadMinDispensa'] = 1
                rowm['numDocumento_usuario'] = numDocUsuario
                rowm['tipoDocumento_usuario'] = tipoDocUsuario
                rowm['numFactura'] = numFactura
                rowm['consecutivo_medicamento'] = idx
                # Agregar campos profesionales con sufijo
                rowm.setdefault('tipoDocumentoIdentificacion_profesional', med.get('tipoDocumentoIdentificacion', ''))
                doc_prof_med = med.get('numDocumentoIdentificacion', '')
                rowm.setdefault('numDocumentoIdentificacion_profesional', normalizar_documento(doc_prof_med) if doc_prof_med else '')
                medicamentos_rows.append(rowm)

            # Process otrosServicios
            for idx, otro in enumerate(otros_servicios, 1):
                # Copiar diccionario preservando tipos originales
                rowo = dict(otro)
                # Normalizar solo campos que pueden tener decimales no deseados
                if 'codPrestador' in rowo:
                    rowo['codPrestador'] = normalizar_documento(rowo['codPrestador'])
                if 'numDocumentoIdentificacion' in rowo:
                    rowo['numDocumentoIdentificacion'] = normalizar_documento(rowo['numDocumentoIdentificacion'])
                if 'tipoOS' in rowo:
                    rowo['tipoOS'] = format_two_digit_code(rowo['tipoOS'])
                if 'conceptoRecaudo' in rowo:
                    rowo['conceptoRecaudo'] = format_two_digit_code(rowo['conceptoRecaudo'])
                rowo['numDocumento_usuario'] = numDocUsuario
                rowo['tipoDocumento_usuario'] = tipoDocUsuario
                rowo['numFactura'] = numFactura
                rowo['consecutivo_otro'] = idx
                # Agregar campos profesionales con sufijo
                rowo.setdefault('tipoDocumentoIdentificacion_profesional', otro.get('tipoDocumentoIdentificacion', ''))
                doc_prof_otro = otro.get('numDocumentoIdentificacion', '')
                rowo.setdefault('numDocumentoIdentificacion_profesional', normalizar_documento(doc_prof_otro) if doc_prof_otro else '')
                otros_serv_rows.append(rowo)

            # Process urgencias
            for idx, urg in enumerate(urgencias, 1):
                # Copiar diccionario preservando tipos originales
                rowu = dict(urg)
                # Normalizar solo campos que pueden tener decimales no deseados
                if 'codPrestador' in rowu:
                    rowu['codPrestador'] = normalizar_documento(rowu['codPrestador'])
                
                # ELIMINAR campos que no forman parte de urgencias en RIPS
                rowu.pop('tipoDocumentoIdentificacion', None)
                rowu.pop('numDocumentoIdentificacion', None)
                
                rowu['numDocumento_usuario'] = numDocUsuario
                rowu['tipoDocumento_usuario'] = tipoDocUsuario
                rowu['numFactura'] = numFactura
                rowu['consecutivo_urgencia'] = idx
                urgencias_rows.append(rowu)

            # Process hospitalizacion
            for idx, hosp in enumerate(hospitalizacion, 1):
                # Copiar diccionario preservando tipos originales
                rowh = dict(hosp)
                # Normalizar solo campos que pueden tener decimales no deseados
                if 'codPrestador' in rowh:
                    rowh['codPrestador'] = normalizar_documento(rowh['codPrestador'])
                
                # ELIMINAR campos que no forman parte de hospitalización en RIPS
                rowh.pop('tipoDocumentoIdentificacion', None)
                rowh.pop('numDocumentoIdentificacion', None)
                
                rowh['numDocumento_usuario'] = numDocUsuario
                rowh['tipoDocumento_usuario'] = tipoDocUsuario
                rowh['numFactura'] = numFactura
                rowh['consecutivo_hospitalizacion'] = idx
                hospitalizacion_rows.append(rowh)

            # Process recienNacidos
            for idx, rn in enumerate(recien_nacidos, 1):
                # Copiar diccionario preservando tipos originales
                rowrn = dict(rn)
                # Normalizar solo campos que pueden tener decimales no deseados
                if 'codPrestador' in rowrn:
                    rowrn['codPrestador'] = normalizar_documento(rowrn['codPrestador'])
                if 'numDocumentoIdentificacion' in rowrn:
                    rowrn['numDocumentoIdentificacion'] = normalizar_documento(rowrn['numDocumentoIdentificacion'])
                rowrn['numDocumento_usuario'] = numDocUsuario
                rowrn['tipoDocumento_usuario'] = tipoDocUsuario
                rowrn['numFactura'] = numFactura
                rowrn['consecutivo_recien_nacido'] = idx
                # Agregar campos profesionales con sufijo
                rowrn.setdefault('tipoDocumentoIdentificacion_profesional', rn.get('tipoDocumentoIdentificacion', ''))
                doc_prof_rn = rn.get('numDocumentoIdentificacion', '')
                rowrn.setdefault('numDocumentoIdentificacion_profesional', normalizar_documento(doc_prof_rn) if doc_prof_rn else '')
                rn_rows.append(rowrn)
            
            # Calculate summary data for user
            fechas_atencion_validas = [f for f in fechas_atencion if f]
            fecha_primera = min(fechas_atencion_validas) if fechas_atencion_validas else ''
            fecha_ultima = max(fechas_atencion_validas) if fechas_atencion_validas else ''
            
            # Add to usuarios list
            usuarios_data.append({
                'numDocumentoIdentificacion': numDocUsuario,
                'tipoDocumentoIdentificacion': tipoDocUsuario,
                'tipoUsuario': user.get('tipoUsuario', ''),
                'fechaNacimiento': fechaNac,
                'edad_al_2025_09_30': edad,
                'codSexo': user.get('codSexo', ''),
                'codPaisResidencia': user.get('codPaisResidencia', ''),
                'codMunicipioResidencia': user.get('codMunicipioResidencia', ''),
                'codZonaTerritorialResidencia': user.get('codZonaTerritorialResidencia', ''),
                'incapacidad': user.get('incapacidad', ''),
                'codPaisOrigen': user.get('codPaisOrigen', ''),
                'consecutivo': user.get('consecutivo', ''),
                'numFactura': numFactura,
                'numDocumentoIdObligado': numDocumentoIdObligado,
                'archivoOrigen': archivoOrigen,
                'total_consultas': len(consultas),
                'total_procedimientos': len(procedimientos),
                'total_eventos': len(consultas) + len(procedimientos),
                'fecha_primera_atencion': fecha_primera,
                'fecha_ultima_atencion': fecha_ultima,
                'num_prestadores_distintos': len(prestadores_unicos),
                'num_diagnosticos_distintos': len(diagnosticos_unicos),
                'diagnosticos_principales': ', '.join(sorted(diagnosticos_unicos)) if diagnosticos_unicos else ''
            })

    except Exception as e:
        print(f"Error procesando archivo: {e}")
        raise

    print(f"\nUsuarios procesados: {len(usuarios_data)}")
    print(f"Total consultas: {len(consultas_rows)}")
    print(f"Total procedimientos: {len(procedimientos_rows)}")

    if not usuarios_data:
        raise ValueError("No se encontraron usuarios para procesar.")

    # Create DataFrames
    df_usuarios = pd.DataFrame(usuarios_data)
    df_consultas = pd.DataFrame(consultas_rows)
    df_procedimientos = pd.DataFrame(procedimientos_rows)
    df_medicamentos = pd.DataFrame(medicamentos_rows) if medicamentos_rows else pd.DataFrame()
    df_otros_serv = pd.DataFrame(otros_serv_rows) if otros_serv_rows else pd.DataFrame()
    df_urgencias = pd.DataFrame(urgencias_rows) if urgencias_rows else pd.DataFrame()
    df_hospitalizacion = pd.DataFrame(hospitalizacion_rows) if hospitalizacion_rows else pd.DataFrame()
    df_recien_nacidos = pd.DataFrame(rn_rows) if rn_rows else pd.DataFrame()

    # Normalizar TODOS los documentos de identidad para quitar decimales
    if 'numDocumentoIdentificacion' in df_usuarios.columns:
        df_usuarios['numDocumentoIdentificacion'] = df_usuarios['numDocumentoIdentificacion'].apply(normalizar_documento)
    if 'numDocumento_usuario' in df_consultas.columns:
        df_consultas['numDocumento_usuario'] = df_consultas['numDocumento_usuario'].apply(normalizar_documento)
    if 'numDocumentoIdentificacion_profesional' in df_consultas.columns:
        df_consultas['numDocumentoIdentificacion_profesional'] = df_consultas['numDocumentoIdentificacion_profesional'].apply(normalizar_documento)
    if 'numDocumento_usuario' in df_procedimientos.columns:
        df_procedimientos['numDocumento_usuario'] = df_procedimientos['numDocumento_usuario'].apply(normalizar_documento)
    if 'numDocumentoIdentificacion' in df_procedimientos.columns:
        df_procedimientos['numDocumentoIdentificacion'] = df_procedimientos['numDocumentoIdentificacion'].apply(normalizar_documento)
    if 'numDocumentoIdentificacion_profesional' in df_procedimientos.columns:
        df_procedimientos['numDocumentoIdentificacion_profesional'] = df_procedimientos['numDocumentoIdentificacion_profesional'].apply(normalizar_documento)
    # Normalizar en secciones adicionales
    for df in [df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos]:
        if not df.empty:
            if 'numDocumento_usuario' in df.columns:
                df['numDocumento_usuario'] = df['numDocumento_usuario'].apply(normalizar_documento)
            if 'numDocumentoIdentificacion_profesional' in df.columns:
                df['numDocumentoIdentificacion_profesional'] = df['numDocumentoIdentificacion_profesional'].apply(normalizar_documento)

    # Asegurar columnas mínimas para validaciones
    min_cons = ['codDiagnosticoPrincipal','finalidadTecnologiaSalud','causaMotivoAtencion','codConsulta','codPrestador','fechaInicioAtencion','numAutorizacion']
    for c in min_cons:
        if c not in df_consultas.columns:
            df_consultas[c] = ''
    if 'codDiagnosticoRelacionado1' not in df_consultas.columns:
        df_consultas['codDiagnosticoRelacionado1'] = ''
    if 'codDiagnosticoRelacionado2' not in df_consultas.columns:
        df_consultas['codDiagnosticoRelacionado2'] = ''
    if 'tipoDocumentoIdentificacion_profesional' not in df_consultas.columns:
        df_consultas['tipoDocumentoIdentificacion_profesional'] = ''
    if 'numDocumentoIdentificacion_profesional' not in df_consultas.columns:
        df_consultas['numDocumentoIdentificacion_profesional'] = ''
    if 'consecutivo_consulta' not in df_consultas.columns:
        df_consultas['consecutivo_consulta'] = ''

    min_proc = ['codDiagnosticoPrincipal','finalidadTecnologiaSalud','codProcedimiento','codPrestador','fechaInicioAtencion','numAutorizacion']
    for c in min_proc:
        if c not in df_procedimientos.columns:
            df_procedimientos[c] = ''
    if 'codDiagnosticoRelacionado' not in df_procedimientos.columns:
        df_procedimientos['codDiagnosticoRelacionado'] = ''
    if 'tipoDocumentoIdentificacion_profesional' not in df_procedimientos.columns:
        df_procedimientos['tipoDocumentoIdentificacion_profesional'] = ''
    if 'numDocumentoIdentificacion_profesional' not in df_procedimientos.columns:
        df_procedimientos['numDocumentoIdentificacion_profesional'] = ''
    if 'consecutivo_procedimiento' not in df_procedimientos.columns:
        df_procedimientos['consecutivo_procedimiento'] = ''

    # Ordenar columnas colocando estándar primero
    std_cons = [
        'numDocumento_usuario','tipoDocumento_usuario','numFactura','consecutivo_consulta',
        'codPrestador','fechaInicioAtencion','numAutorizacion','codConsulta',
        'modalidadGrupoServicioTecSal','grupoServicios','codServicio',
        'finalidadTecnologiaSalud','causaMotivoAtencion','codDiagnosticoPrincipal',
        'codDiagnosticoRelacionado1','codDiagnosticoRelacionado2','codDiagnosticoRelacionado3','tipoDiagnosticoPrincipal',
        'tipoDocumentoIdentificacion_profesional','numDocumentoIdentificacion_profesional','vrServicio','conceptoRecaudo','valorPagoModerador','numFEVPagoModerador'
    ]
    df_consultas = df_consultas.reindex(columns=[c for c in std_cons if c in df_consultas.columns] + [c for c in df_consultas.columns if c not in std_cons])

    std_proc = [
        'numDocumento_usuario','tipoDocumento_usuario','numFactura','consecutivo_procedimiento',
        'codPrestador','fechaInicioAtencion','idMIPRES','numAutorizacion','codProcedimiento',
        'viaIngresoServicioSalud','modalidadGrupoServicioTecSal','grupoServicios','codServicio',
        'finalidadTecnologiaSalud','codDiagnosticoPrincipal','codDiagnosticoRelacionado','codComplicacion',
        'tipoDocumentoIdentificacion_profesional','numDocumentoIdentificacion_profesional',
        'vrServicio','conceptoRecaudo','valorPagoModerador','numFEVPagoModerador'
    ]
    df_procedimientos = df_procedimientos.reindex(columns=[c for c in std_proc if c in df_procedimientos.columns] + [c for c in df_procedimientos.columns if c not in std_proc])

    # Aplicar validaciones específicas de COMPUESTOS (incluye REGLA 10: complemento de profesionales para TODOS los servicios)
    df_usuarios, df_consultas, df_procedimientos, df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos, df_reporte_diagnosticos_vacios = aplicar_validaciones_compuestos(
        df_usuarios, df_consultas, df_procedimientos, df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos
    )

    # Export to Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_usuarios.to_excel(writer, sheet_name='Usuarios', index=False)
        df_consultas.to_excel(writer, sheet_name='Consultas', index=False)
        df_procedimientos.to_excel(writer, sheet_name='Procedimientos', index=False)
        if not df_medicamentos.empty:
            df_medicamentos.to_excel(writer, sheet_name='Medicamentos', index=False)
        if not df_otros_serv.empty:
            df_otros_serv.to_excel(writer, sheet_name='OtrosServicios', index=False)
        if not df_urgencias.empty:
            df_urgencias.to_excel(writer, sheet_name='Urgencias', index=False)
        if not df_hospitalizacion.empty:
            df_hospitalizacion.to_excel(writer, sheet_name='Hospitalizacion', index=False)
        if not df_recien_nacidos.empty:
            df_recien_nacidos.to_excel(writer, sheet_name='RecienNacidos', index=False)
        # Hoja Transaccion (opcional)
        if transaccion_top:
            try:
                pd.DataFrame([transaccion_top]).to_excel(writer, sheet_name='Transaccion', index=False)
            except Exception:
                pass
    
    output.seek(0)
    
    print(f"\n✅ Excel CORREGIDO generado (con validaciones)")
    print(f"  1. Usuarios: {len(df_usuarios):,} filas × {len(df_usuarios.columns)} columnas")
    print(f"  2. Consultas: {len(df_consultas):,} filas × {len(df_consultas.columns)} columnas")
    print(f"  3. Procedimientos: {len(df_procedimientos):,} filas × {len(df_procedimientos.columns)} columnas")
    if 'df_medicamentos' in locals() and not df_medicamentos.empty:
        print(f"  4. Medicamentos: {len(df_medicamentos):,} filas × {len(df_medicamentos.columns)} columnas")
    if 'df_otros_serv' in locals() and not df_otros_serv.empty:
        print(f"  5. OtrosServicios: {len(df_otros_serv):,} filas × {len(df_otros_serv.columns)} columnas")
    if 'df_urgencias' in locals() and not df_urgencias.empty:
        print(f"  6. Urgencias: {len(df_urgencias):,} filas × {len(df_urgencias.columns)} columnas")
    if 'df_hospitalizacion' in locals() and not df_hospitalizacion.empty:
        print(f"  7. Hospitalizacion: {len(df_hospitalizacion):,} filas × {len(df_hospitalizacion.columns)} columnas")
    if 'df_recien_nacidos' in locals() and not df_recien_nacidos.empty:
        print(f"  8. RecienNacidos: {len(df_recien_nacidos):,} filas × {len(df_recien_nacidos.columns)} columnas")
    if 'transaccion_top' in locals() and transaccion_top:
        print("  9. Transaccion: 1 fila × {} columnas".format(len(pd.DataFrame([transaccion_top]).columns)))
    
    # Generar reporte de diagnósticos vacíos si existen
    reporte_output = None
    if df_reporte_diagnosticos_vacios is not None and not df_reporte_diagnosticos_vacios.empty:
        reporte_output = BytesIO()
        with pd.ExcelWriter(reporte_output, engine='openpyxl') as writer:
            df_reporte_diagnosticos_vacios.to_excel(writer, sheet_name='Diagnosticos_Vacios', index=False)
        reporte_output.seek(0)
        print(f"\n⚠️  REPORTE: {len(df_reporte_diagnosticos_vacios)} usuarios con diagnósticos vacíos en consultas")
    
    # Generar JSON reformado con TODOS los registros (incluyendo diagnósticos vacíos)
    data_reformado = reconstruir_json_desde_dataframes(
        data, df_usuarios, df_consultas, df_procedimientos,
        df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos
    )
    
    json_reformado = BytesIO()
    json_reformado.write(format_json_compact_arrays(data_reformado, indent=4).encode('utf-8'))
    json_reformado.seek(0)
    
    print(f"\n✅ JSON Reformado generado con {len(data_reformado.get('usuarios', []))} usuarios (incluye registros con diagnósticos vacíos)")
    
    return excel_original, output, reporte_output, json_reformado

def truncar_diagnostico(codigo):
    return truncar_codigo(codigo)

def aplicar_validaciones_compuestos(df_usuarios, df_consultas, df_procedimientos, df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos):
    """Aplica validaciones específicas para COMPUESTOS incluyendo complemento de profesionales en TODOS los servicios"""
    df_usuarios, [df_consultas, df_procedimientos, df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos] = normalizar_ppt_pt_en_dataframes(
        df_usuarios,
        [df_consultas, df_procedimientos, df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos],
    )
    
    # NOTA: Ya NO recalculamos consecutivos - se preservan del JSON original
    # Los consecutivos originales ya fueron leídos con consulta.get('consecutivo', idx)
    # Si el JSON no tiene consecutivo, se usa idx como fallback
    # 2. Recalcular consecutivos en consultas - DESACTIVADO
    # if not df_consultas.empty:
    #     df_consultas = df_consultas.sort_values(['numDocumento_usuario', 'tipoDocumento_usuario', 'fechaInicioAtencion'])
    #     df_consultas['consecutivo_consulta'] = df_consultas.groupby(['numDocumento_usuario', 'tipoDocumento_usuario']).cumcount() + 1
    
    # 3. Recalcular consecutivos en procedimientos - DESACTIVADO
    # if not df_procedimientos.empty:
    #     df_procedimientos = df_procedimientos.sort_values(['numDocumento_usuario', 'tipoDocumento_usuario', 'fechaInicioAtencion'])
    #     df_procedimientos['consecutivo_procedimiento'] = df_procedimientos.groupby(['numDocumento_usuario', 'tipoDocumento_usuario']).cumcount() + 1
    
    truncar_campos_dataframe(df_consultas, ['codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3', 'codDiagnosticoPrincipal'])
    truncar_campos_dataframe(df_procedimientos, ['codDiagnosticoRelacionado', 'codDiagnosticoPrincipal'])
    
    from modules.motor_logico import (
        COMPUESTOS_DF_SUSTITUCIONES_Z,
        _resolver_consulta_compuestos_registro,
        _resolver_procedimiento_compuestos_registro,
    )
    sustituciones = COMPUESTOS_DF_SUSTITUCIONES_Z
    
    # 5. CONSULTAS: Identificar diagnósticos vacíos y aplicar reglas
    usuarios_con_diagnosticos_vacios = set()
    
    for idx, row in df_consultas.iterrows():
        registro = row.to_dict()
        resultado = _resolver_consulta_compuestos_registro(registro, sustituciones)
        for campo, valor in registro.items():
            if campo in df_consultas.columns:
                df_consultas.at[idx, campo] = valor

        cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()

        # Identificar usuarios con diagnósticos vacíos en consultas
        if not cod_diag or cod_diag == '' or cod_diag == 'nan':
            num_doc = row.get('numDocumento_usuario', '')
            tipo_doc = row.get('tipoDocumento_usuario', '')
            if num_doc and tipo_doc:
                usuarios_con_diagnosticos_vacios.add((tipo_doc, num_doc))
    
    # Crear DataFrame de reporte con usuarios que tienen diagnósticos vacíos
    df_reporte_diagnosticos_vacios = None
    if usuarios_con_diagnosticos_vacios:
        usuarios_reporte = []
        for tipo_doc, num_doc in usuarios_con_diagnosticos_vacios:
            # Buscar el usuario en df_usuarios
            usuario = df_usuarios[
                (df_usuarios['tipoDocumentoIdentificacion'] == tipo_doc) & 
                (df_usuarios['numDocumentoIdentificacion'] == num_doc)
            ]
            if not usuario.empty:
                usuario_data = usuario.iloc[0]
                usuarios_reporte.append({
                    'tipoDocumentoIdentificacion': usuario_data.get('tipoDocumentoIdentificacion', ''),
                    'numDocumentoIdentificacion': usuario_data.get('numDocumentoIdentificacion', ''),
                    'tipoUsuario': usuario_data.get('tipoUsuario', ''),
                    'fechaNacimiento': usuario_data.get('fechaNacimiento', ''),
                    'codSexo': usuario_data.get('codSexo', ''),
                    'codPaisResidencia': usuario_data.get('codPaisResidencia', ''),
                    'codMunicipioResidencia': usuario_data.get('codMunicipioResidencia', ''),
                    'codZonaTerritorialResidencia': usuario_data.get('codZonaTerritorialResidencia', ''),
                    'incapacidad': usuario_data.get('incapacidad', ''),
                    'consecutivo': usuario_data.get('consecutivo', '')
                })
        
        if usuarios_reporte:
            df_reporte_diagnosticos_vacios = pd.DataFrame(usuarios_reporte)
    
    # 6. PROCEDIMIENTOS: Aplicar reglas específicas con nuevo orden de llenado
    for idx, row in df_procedimientos.iterrows():
        registro = row.to_dict()
        fecha_proc = row.get('fechaInicioAtencion', '')
        num_doc = row.get('numDocumento_usuario', '')
        tipo_doc = row.get('tipoDocumento_usuario', '')
        diagnosticos_consulta = []

        if fecha_proc and num_doc and tipo_doc:
            fecha_proc_solo = fecha_proc.split(' ')[0] if ' ' in str(fecha_proc) else str(fecha_proc)
            consultas_misma_fecha = df_consultas[
                (df_consultas['numDocumento_usuario'] == num_doc) &
                (df_consultas['tipoDocumento_usuario'] == tipo_doc) &
                (df_consultas['fechaInicioAtencion'].astype(str).str.split(' ').str[0] == fecha_proc_solo)
            ]
            if not consultas_misma_fecha.empty:
                for _, consulta in consultas_misma_fecha.iterrows():
                    diag_consulta = str(consulta['codDiagnosticoPrincipal']).strip() if pd.notna(consulta['codDiagnosticoPrincipal']) else ''
                    if diag_consulta and diag_consulta != '' and diag_consulta != 'nan':
                        diagnosticos_consulta.append(diag_consulta)
                        break

        _resolver_procedimiento_compuestos_registro(
            registro,
            COMPUESTOS_CODIGOS_PROC_Z258,
            COMPUESTOS_TABLA_CUPS_FINALIDAD,
            diagnosticos_consulta_fecha=diagnosticos_consulta,
        )
        for campo, valor in registro.items():
            if campo in df_procedimientos.columns:
                df_procedimientos.at[idx, campo] = valor
    
    # ============================================================================
    # REGLA 10: COMPLETAR SOLO TIPOS DE DOCUMENTO VACÍOS
    # Los números de documento ya vienen completados por completador_documentos.py
    # NOTA: Hospitalización NO lleva campos de profesionales según normativa
    # ============================================================================
    print("\nAplicando REGLA 10: Completar tipos de documento profesionales...")
    
    # Lista de DataFrames con campos profesionales (EXCLUYENDO Hospitalización)
    dataframes_con_profesionales = [
        ('Consultas', df_consultas),
        ('Procedimientos', df_procedimientos),
        ('Medicamentos', df_medicamentos),
        ('OtrosServicios', df_otros_serv),
        ('Urgencias', df_urgencias),
        ('RecienNacidos', df_recien_nacidos)
    ]
    
    total_tipos_rellenados = 0
    
    # Solo completar tipos de documento vacíos (usar 'CC' como default)
    for nombre_servicio, df in dataframes_con_profesionales:
        if df.empty or 'tipoDocumentoIdentificacion_profesional' not in df.columns:
            continue
        
        tipo_vacios = df['tipoDocumentoIdentificacion_profesional'].isna() | \
                     (df['tipoDocumentoIdentificacion_profesional'] == '')
        
        if tipo_vacios.sum() > 0:
            df.loc[tipo_vacios, 'tipoDocumentoIdentificacion_profesional'] = 'CC'
            total_tipos_rellenados += tipo_vacios.sum()
    
    print(f"\n   ✅ REGLA 10 completada:")
    print(f"      - Tipos de documento rellenados: {total_tipos_rellenados}")
    print(f"      - Números de documento: ya completados por completador_documentos.py")
    
    print("\n✅ Validaciones COMPUESTOS aplicadas")
    
    return df_usuarios, df_consultas, df_procedimientos, df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos, df_reporte_diagnosticos_vacios
