"""
Generador de Tabla Única en Excel para ValidacionPYP - Versión Flask
Estructura:
- Hoja 1 "Usuarios": Datos demográficos + resúmenes por usuario
- Hoja 2 "Consultas": Una fila por consulta (normalizada)
- Hoja 3 "Procedimientos": Una fila por procedimiento (normalizada)
"""

import json
import os
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
    FIELD_FORMATS
)
from modules.documentos_rips import (
    consolidar_usuarios_por_documento,
    normalizar_ppt_pt_en_dataframes,
    validar_tipos_documento_usuarios,
)
from modules.truncamiento_rips import truncar_campos_dataframe, truncar_codigo

def aplicar_sustituciones_pyp_json(datos_json, config_eps=None, generar_reporte=False):
    """
    Aplica el motor lógico centralizado a los registros PyP del JSON.
    Esta función debe ejecutarse ANTES de guardar el JSON Reformado.

    ORDEN DE EJECUCIÓN (motor lógico):
    1. Filtro por contrato EPS (si config_eps está presente)
    2. Normalización del CIE10 (sin punto, mayúsculas, 4 caracteres)
    3. Clasificación por letra inicial (enfermedad/trauma/causa_externa/factor)
    4. Finalidad como eje de control → reglas de causa

    Args:
        datos_json    : Diccionario con la estructura completa del RIPS-JSON
        config_eps    : dict con 'cups_contrato' (set de CUPS del contrato activo).
                        Si None, no se aplica filtro por contrato.
        generar_reporte: Si True, retorna también lista de cambios

    Returns:
        Si generar_reporte=False: dict con JSON modificado
        Si generar_reporte=True: tuple (dict JSON modificado, list cambios_sustituciones)
    """
    from modules.motor_logico import (
        aplicar_motor_logico, normalizar_cie10,
        CAMPO_MAP_CONSULTAS, CAMPO_MAP_PROCEDIMIENTOS,
    )

    cambios_sustituciones = [] if generar_reporte else None

    usuarios = datos_json.get('usuarios', [])

    for usuario in usuarios:
        num_doc_usuario  = usuario.get('numDocumentoIdentificacion', '')
        tipo_doc_usuario = usuario.get('tipoDocumentoIdentificacion', '')
        fecha_nacimiento = usuario.get('fechaNacimiento', '')
        servicios        = usuario.get('servicios', {})

        # ------------------------------------------------------------------
        # CONSULTAS
        # ------------------------------------------------------------------
        for idx_consulta, consulta in enumerate(servicios.get('consultas', []), 1):
            cod_diag_original  = str(consulta.get('codDiagnosticoPrincipal', '') or '').strip()
            if cod_diag_original:
                cod_diag_original = truncar_codigo(cod_diag_original)
                consulta['codDiagnosticoPrincipal'] = cod_diag_original
            finalidad_original = consulta.get('finalidadTecnologiaSalud', '')
            causa_original     = consulta.get('causaMotivoAtencion', '')

            resultado = aplicar_motor_logico(consulta, CAMPO_MAP_CONSULTAS, config_eps)

            # Normalizar diagnósticos relacionados (solo formato)
            for campo in ['codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2',
                          'codDiagnosticoRelacionado3']:
                if campo in consulta:
                    val = str(consulta.get(campo, '') or '').strip()
                    normalizado = normalizar_cie10(val)
                    if normalizado != val:
                        consulta[campo] = normalizado

            if generar_reporte and (resultado['modificado'] or resultado['alertas']):
                # Si el diagnóstico era vacío y motor_logico no lo modificó,
                # la asignación del Z-código ocurre en el nivel DataFrame
                # (aplicar_clasificacion_df_pyp) y ya queda registrada en cambios_df.
                # Emitir la entrada aquí produciría Diagnostico_Final vacío.
                if not cod_diag_original and not resultado['modificado']:
                    pass
                else:
                    cambios_sustituciones.append({
                        'Tipo':                'CONSULTA',
                        'Usuario_Documento':   num_doc_usuario,
                        'Usuario_TipoDoc':     tipo_doc_usuario,
                        'Curso_Vida':          calcular_curso_vida(fecha_nacimiento, consulta.get('fechaInicioAtencion', '')),
                        'Consecutivo_Servicio': idx_consulta,
                        'Codigo_Consulta':     str(consulta.get('codConsulta', '') or '').strip(),
                        'Diagnostico_Original': cod_diag_original if cod_diag_original else '(vacío)',
                        'Diagnostico_Final':   consulta.get('codDiagnosticoPrincipal', ''),
                        'Finalidad_Original':  finalidad_original,
                        'Finalidad_Nueva':     consulta.get('finalidadTecnologiaSalud', ''),
                        'Causa_Original':      causa_original,
                        'Causa_Nueva':         consulta.get('causaMotivoAtencion', ''),
                        'En_Contrato':         'Sí' if resultado['en_contrato'] else 'No',
                        'Alertas':             '; '.join(resultado['alertas']),
                    })

        # ------------------------------------------------------------------
        # PROCEDIMIENTOS
        # ------------------------------------------------------------------
        for idx_proc, proc in enumerate(servicios.get('procedimientos', []), 1):
            cod_proc           = str(proc.get('codProcedimiento', '') or '').strip()
            cod_diag_original  = str(proc.get('codDiagnosticoPrincipal', '') or '').strip()
            if cod_diag_original:
                cod_diag_original = truncar_codigo(cod_diag_original)
                proc['codDiagnosticoPrincipal'] = cod_diag_original
            finalidad_original = proc.get('finalidadTecnologiaSalud', '')

            resultado = aplicar_motor_logico(proc, CAMPO_MAP_PROCEDIMIENTOS, config_eps)

            # Normalizar diagnóstico relacionado (solo formato)
            if 'codDiagnosticoRelacionado' in proc:
                val = str(proc.get('codDiagnosticoRelacionado', '') or '').strip()
                normalizado = normalizar_cie10(val)
                if normalizado != val:
                    proc['codDiagnosticoRelacionado'] = normalizado

            if generar_reporte and (resultado['modificado'] or resultado['alertas']):
                if not cod_diag_original and not resultado['modificado']:
                    pass
                else:
                    cambios_sustituciones.append({
                        'Tipo':                'PROCEDIMIENTO',
                        'Usuario_Documento':   num_doc_usuario,
                        'Usuario_TipoDoc':     tipo_doc_usuario,
                        'Curso_Vida':          calcular_curso_vida(fecha_nacimiento, proc.get('fechaInicioAtencion', '')),
                        'Consecutivo_Servicio': idx_proc,
                        'Codigo_Procedimiento': cod_proc,
                        'Diagnostico_Original': cod_diag_original if cod_diag_original else '(vacío)',
                        'Diagnostico_Final':   proc.get('codDiagnosticoPrincipal', ''),
                        'Finalidad_Original':  finalidad_original,
                        'Finalidad_Nueva':     proc.get('finalidadTecnologiaSalud', ''),
                        'Causa_Original':      '',
                        'Causa_Nueva':         '',
                        'En_Contrato':         'Sí' if resultado['en_contrato'] else 'No',
                        'Alertas':             '; '.join(resultado['alertas']),
                    })
    
    if generar_reporte:
        return datos_json, cambios_sustituciones
    else:
        return datos_json

def validar_tipos_documento_por_edad(usuarios_list):
    return validar_tipos_documento_usuarios(usuarios_list)


def consolidar_usuarios_duplicados(usuarios_list):
    return consolidar_usuarios_por_documento(usuarios_list, ['consultas', 'procedimientos'])

def procesar_json_pyp(json_file, filename):
    """
    Procesa un archivo JSON de ValidacionPYP y genera DOS archivos Excel:
    1. Excel ORIGINAL (sin correcciones) para descarga
    2. Excel CORREGIDO (con validaciones) para generar JSON reformado
    
    Args:
        json_file: Archivo JSON cargado
        filename: Nombre del archivo original (sin extensión)
    
    Returns:
        tuple: (BytesIO Excel original, BytesIO Excel corregido)
    """
    
    # Usar fecha actual para cálculo de edad
    cutoff_date = datetime.now()
    
    print("=" * 60)
    print("Procesando archivo JSON PYP...")
    print("=" * 60)
    
    # PASO 0: Generar Excel ORIGINAL sin correcciones
    from modules.generador_excel_original import generar_excel_original_pyp
    json_file.seek(0)
    excel_original = generar_excel_original_pyp(json_file, filename)
    json_file.seek(0)  # Reset para procesamiento con validaciones

    # Data structures
    usuarios_data = []
    consultas_data = []
    procedimientos_data = []

    try:
        data = json.load(json_file)
        
        numFactura = data.get('numFactura', '')
        numDocumentoIdObligado = data.get('numDocumentoIdObligado', '')
        archivoOrigen = filename + '.json'
        
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
            
            # Collect dates and unique values for summary
            fechas_atencion = []
            prestadores_unicos = set()
            diagnosticos_unicos = set()
            
            # Contadores de consecutivos por usuario (para fallback si no existe en JSON)
            consecutivo_consulta_counter = 1
            consecutivo_procedimiento_counter = 1
            
            # Process consultas
            for idx, consulta in enumerate(consultas, 1):
                fecha = consulta.get('fechaInicioAtencion', '')
                fechas_atencion.append(fecha)
                
                codPrestador = normalizar_documento(consulta.get('codPrestador', ''))
                codServicio = consulta.get('codServicio', '')
                codConsulta = consulta.get('codConsulta', '')
                diagPrincipal = consulta.get('codDiagnosticoPrincipal', '')
                
                prestadores_unicos.add(codPrestador)
                if diagPrincipal:
                    diagnosticos_unicos.add(diagPrincipal)
                
                # Usar consecutivo del JSON o generar uno secuencial
                consecutivo_actual = consulta.get('consecutivo')
                if consecutivo_actual is None or consecutivo_actual == '':
                    consecutivo_actual = consecutivo_consulta_counter
                    consecutivo_consulta_counter += 1
                
                # Add to consultas list
                consultas_data.append({
                    'numDocumento_usuario': numDocUsuario,
                    'tipoDocumento_usuario': tipoDocUsuario,
                    'numFactura': numFactura,
                    'consecutivo_consulta': consecutivo_actual,
                    'codPrestador': codPrestador,
                    'fechaInicioAtencion': fecha,
                    'numAutorizacion': consulta.get('numAutorizacion', ''),
                    'codConsulta': codConsulta,
                    'modalidadGrupoServicioTecSal': consulta.get('modalidadGrupoServicioTecSal', ''),
                    'grupoServicios': consulta.get('grupoServicios', ''),
                    'codServicio': codServicio,
                    'finalidadTecnologiaSalud': consulta.get('finalidadTecnologiaSalud', ''),
                    'causaMotivoAtencion': consulta.get('causaMotivoAtencion', ''),
                    'codDiagnosticoPrincipal': diagPrincipal,
                    'codDiagnosticoRelacionado1': consulta.get('codDiagnosticoRelacionado1', ''),
                    'codDiagnosticoRelacionado2': consulta.get('codDiagnosticoRelacionado2', ''),
                    'codDiagnosticoRelacionado3': consulta.get('codDiagnosticoRelacionado3', ''),
                    'tipoDiagnosticoPrincipal': consulta.get('tipoDiagnosticoPrincipal', ''),
                    'tipoDocumentoIdentificacion_profesional': consulta.get('tipoDocumentoIdentificacion', ''),
                    'numDocumentoIdentificacion_profesional': normalizar_documento(consulta.get('numDocumentoIdentificacion', '')),
                    'vrServicio': consulta.get('vrServicio', 0),
                    'conceptoRecaudo': consulta.get('conceptoRecaudo', ''),
                    'valorPagoModerador': consulta.get('valorPagoModerador', 0),
                    'numFEVPagoModerador': consulta.get('numFEVPagoModerador', '')
                })
            
            # Process procedimientos
            for idx, proc in enumerate(procedimientos, 1):
                fecha = proc.get('fechaInicioAtencion', '')
                fechas_atencion.append(fecha)
                
                codPrestador = normalizar_documento(proc.get('codPrestador', ''))
                codServicio = proc.get('codServicio', '')
                codProcedimiento = proc.get('codProcedimiento', '')
                diagPrincipal = proc.get('codDiagnosticoPrincipal', '')
                
                prestadores_unicos.add(codPrestador)
                if diagPrincipal:
                    diagnosticos_unicos.add(diagPrincipal)
                
                # Usar consecutivo del JSON o generar uno secuencial
                consecutivo_actual = proc.get('consecutivo')
                if consecutivo_actual is None or consecutivo_actual == '':
                    consecutivo_actual = consecutivo_procedimiento_counter
                    consecutivo_procedimiento_counter += 1
                
                # Add to procedimientos list
                procedimientos_data.append({
                    'numDocumento_usuario': numDocUsuario,
                    'tipoDocumento_usuario': tipoDocUsuario,
                    'numFactura': numFactura,
                    'consecutivo_procedimiento': consecutivo_actual,
                    'codPrestador': codPrestador,
                    'fechaInicioAtencion': fecha,
                    'idMIPRES': proc.get('idMIPRES', ''),
                    'numAutorizacion': proc.get('numAutorizacion', ''),
                    'codProcedimiento': codProcedimiento,
                    'viaIngresoServicioSalud': proc.get('viaIngresoServicioSalud', ''),
                    'modalidadGrupoServicioTecSal': proc.get('modalidadGrupoServicioTecSal', ''),
                    'grupoServicios': proc.get('grupoServicios', ''),
                    'codServicio': codServicio,
                    'finalidadTecnologiaSalud': proc.get('finalidadTecnologiaSalud', ''),
                    'tipoDocumentoIdentificacion_profesional': proc.get('tipoDocumentoIdentificacion', ''),
                    'numDocumentoIdentificacion_profesional': normalizar_documento(proc.get('numDocumentoIdentificacion', '')),
                    'codDiagnosticoPrincipal': diagPrincipal,
                    'codDiagnosticoRelacionado': proc.get('codDiagnosticoRelacionado', ''),
                    'codComplicacion': proc.get('codComplicacion', ''),
                    'vrServicio': proc.get('vrServicio', 0),
                    'conceptoRecaudo': proc.get('conceptoRecaudo', ''),
                    'valorPagoModerador': proc.get('valorPagoModerador', 0),
                    'numFEVPagoModerador': proc.get('numFEVPagoModerador', '')
                })
            
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
    print(f"Total consultas: {len(consultas_data)}")
    print(f"Total procedimientos: {len(procedimientos_data)}")

    if not usuarios_data:
        raise ValueError("No se encontraron usuarios para procesar.")

    # Create DataFrames
    df_usuarios = pd.DataFrame(usuarios_data)
    df_consultas = pd.DataFrame(consultas_data)
    df_procedimientos = pd.DataFrame(procedimientos_data)

    # Normalizar TODOS los documentos de identidad para quitar decimales
    if 'numDocumentoIdentificacion' in df_usuarios.columns:
        df_usuarios['numDocumentoIdentificacion'] = df_usuarios['numDocumentoIdentificacion'].apply(normalizar_documento)
    if 'numDocumento_usuario' in df_consultas.columns:
        df_consultas['numDocumento_usuario'] = df_consultas['numDocumento_usuario'].apply(normalizar_documento)
    if 'numDocumentoIdentificacion_profesional' in df_consultas.columns:
        df_consultas['numDocumentoIdentificacion_profesional'] = df_consultas['numDocumentoIdentificacion_profesional'].apply(normalizar_documento)
    if 'numDocumento_usuario' in df_procedimientos.columns:
        df_procedimientos['numDocumento_usuario'] = df_procedimientos['numDocumento_usuario'].apply(normalizar_documento)
    if 'numDocumentoIdentificacion_profesional' in df_procedimientos.columns:
        df_procedimientos['numDocumentoIdentificacion_profesional'] = df_procedimientos['numDocumentoIdentificacion_profesional'].apply(normalizar_documento)

    # Aplicar validaciones específicas de PYP
    df_usuarios, df_consultas, df_procedimientos, cambios_diag = aplicar_validaciones_pyp(df_usuarios, df_consultas, df_procedimientos)

    # Rellenar solo tipos de documento vacíos (los números ya vienen completados por completador_documentos.py)
    if not df_consultas.empty:
        consultas_tipo_vacios = df_consultas['tipoDocumentoIdentificacion_profesional'].isna() | (df_consultas['tipoDocumentoIdentificacion_profesional'] == '')
        df_consultas.loc[consultas_tipo_vacios, 'tipoDocumentoIdentificacion_profesional'] = 'CC'
    
    if not df_procedimientos.empty:
        proc_tipo_vacios = df_procedimientos['tipoDocumentoIdentificacion_profesional'].isna() | (df_procedimientos['tipoDocumentoIdentificacion_profesional'] == '')
        df_procedimientos.loc[proc_tipo_vacios, 'tipoDocumentoIdentificacion_profesional'] = 'CC'

    # Export to Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_usuarios.to_excel(writer, sheet_name='Usuarios', index=False)
        df_consultas.to_excel(writer, sheet_name='Consultas', index=False)
        df_procedimientos.to_excel(writer, sheet_name='Procedimientos', index=False)
    
    output.seek(0)
    
    print(f"\n✅ Excel CORREGIDO generado (con validaciones)")
    print(f"  1. Usuarios: {len(df_usuarios):,} filas × {len(df_usuarios.columns)} columnas")
    print(f"  2. Consultas: {len(df_consultas):,} filas × {len(df_consultas.columns)} columnas")
    print(f"  3. Procedimientos: {len(df_procedimientos):,} filas × {len(df_procedimientos.columns)} columnas")
    
    return excel_original, output, cambios_diag

def truncar_diagnostico(codigo):
    return truncar_codigo(codigo)

def aplicar_validaciones_pyp(df_usuarios, df_consultas, df_procedimientos):
    """Aplica validaciones específicas para PYP (Promoción y Prevención)"""
    df_usuarios, [df_consultas, df_procedimientos] = normalizar_ppt_pt_en_dataframes(
        df_usuarios,
        [df_consultas, df_procedimientos],
    )
    
    # NOTA: Ya NO recalculamos consecutivos - se preservan del JSON original
    # Los consecutivos originales ya fueron leídos con consulta.get('consecutivo', idx)
    # Si el JSON no tiene consecutivo, se usa idx como fallback
    # if not df_consultas.empty:
    #     df_consultas = df_consultas.sort_values(['numDocumento_usuario', 'tipoDocumento_usuario', 'fechaInicioAtencion'])
    #     df_consultas['consecutivo_consulta'] = df_consultas.groupby(['numDocumento_usuario', 'tipoDocumento_usuario']).cumcount() + 1
    
    # if not df_procedimientos.empty:
    #     df_procedimientos = df_procedimientos.sort_values(['numDocumento_usuario', 'tipoDocumento_usuario', 'fechaInicioAtencion'])
    #     df_procedimientos['consecutivo_procedimiento'] = df_procedimientos.groupby(['numDocumento_usuario', 'tipoDocumento_usuario']).cumcount() + 1
    
    # Truncar diagnósticos a 4 caracteres (ANTES de normalizar y aplicar sustituciones)
    columnas_diagnostico_consultas = ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado1', 
                                      'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3']
    columnas_diagnostico_procedimientos = ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado']
    
    truncar_campos_dataframe(df_consultas, columnas_diagnostico_consultas)
    truncar_campos_dataframe(df_procedimientos, columnas_diagnostico_procedimientos)
    
    from modules.motor_logico import aplicar_clasificacion_df_pyp
    df_consultas, df_procedimientos, cambios_diag = aplicar_clasificacion_df_pyp(df_consultas, df_procedimientos)

    print(f"Validaciones PYP aplicadas")
    
    return df_usuarios, df_consultas, df_procedimientos, cambios_diag
