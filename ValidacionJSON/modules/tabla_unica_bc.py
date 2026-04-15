"""
Generador de Tabla Única en Excel para ValidacionBC - Versión Flask
Estructura similar a PYP pero con reglas de validación específicas para Baja Complejidad
"""

import json
import os
from datetime import datetime
import pandas as pd
import random
from io import BytesIO
import logging

# Configurar logging para debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - BC - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_consolidacion_bc.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

# Importar pd para usar en funciones auxiliares
pd.options.mode.chained_assignment = None  # Desactivar advertencias de pandas

def validar_tipos_documento_por_edad(usuarios_list):
    logger.info("=" * 60)
    logger.info("INICIANDO VALIDACION DE TIPOS DE DOCUMENTO POR EDAD")
    logger.info(f"Total usuarios a validar: {len(usuarios_list)}")
    logger.info("=" * 60)
    return validar_tipos_documento_usuarios(usuarios_list, logger=logger)


def consolidar_usuarios_duplicados(usuarios_list):
    logger.info("=" * 60)
    logger.info("INICIANDO CONSOLIDACION DE USUARIOS DUPLICADOS")
    logger.info(f"Total usuarios a procesar: {len(usuarios_list)}")
    logger.info("=" * 60)
    return consolidar_usuarios_por_documento(
        usuarios_list,
        ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos'],
        logger=logger,
    )

def aplicar_cambios_bc_json(datos_json, config_eps=None, generar_reporte=False):
    """
    Delegado al motor lógico centralizado para mantener una sola fuente de verdad.
    """
    from modules.motor_logico import aplicar_cambios_bc_json as aplicar_cambios_bc_json_motor

    return aplicar_cambios_bc_json_motor(
        datos_json,
        config_eps=config_eps,
        generar_reporte=generar_reporte,
    )

def procesar_json_bc(json_file, filename):
    """
    Procesa un archivo JSON de ValidacionBC y genera DOS archivos Excel:
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
    print("Procesando archivo JSON BC...")
    print("=" * 60)
    
    # PASO 0: Generar Excel ORIGINAL sin correcciones
    from modules.generador_excel_original import generar_excel_original_bc
    json_file.seek(0)
    excel_original = generar_excel_original_bc(json_file, filename)
    json_file.seek(0)  # Reset para procesamiento con validaciones

    # Data structures
    usuarios_data = []
    # En BC preservaremos todas las llaves originales de cada evento
    consultas_rows = []
    procedimientos_rows = []
    medicamentos_rows = []
    otros_serv_rows = []
    urgencias_rows = []
    hospitalizacion_rows = []
    rn_rows = []  # recienNacidos

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
        
        total_usuarios = len(usuarios_list)
        print(f"\nProcesando {total_usuarios:,} usuarios unicos...")
        
        for user_idx, user in enumerate(usuarios_list, 1):
            # Mostrar progreso cada 50 usuarios
            if user_idx % 50 == 0 or user_idx == total_usuarios:
                print(f"   Usuario {user_idx}/{total_usuarios}", end='\r')
            
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
                # Campos estándar/derivados
                row['numDocumento_usuario'] = numDocUsuario
                row['tipoDocumento_usuario'] = tipoDocUsuario
                row['numFactura'] = numFactura
                # Usar consecutivo del JSON o generar uno secuencial
                consecutivo_actual = consulta.get('consecutivo')
                if consecutivo_actual is None or consecutivo_actual == '':
                    consecutivo_actual = consecutivo_consulta_counter
                    consecutivo_consulta_counter += 1
                row['consecutivo_consulta'] = consecutivo_actual
                # Normalizar profesional si no existe con sufijo - NORMALIZAR documentos
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
                procedimientos_rows.append(rowp)

            # Process medicamentos preservando columnas extra
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
                medicamentos_rows.append(rowm)

            # Process otrosServicios preservando columnas extra
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
                if 'viaIngresoServicioSalud' in rowh:
                    rowh['viaIngresoServicioSalud'] = format_two_digit_code(rowh['viaIngresoServicioSalud'])
                if 'condicionDestinoUsuarioEgreso' in rowh:
                    rowh['condicionDestinoUsuarioEgreso'] = format_two_digit_code(rowh['condicionDestinoUsuarioEgreso'])
                
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
    print(f"Total medicamentos: {len(medicamentos_rows)}")
    print(f"Total otrosServicios: {len(otros_serv_rows)}")
    print(f"Total urgencias: {len(urgencias_rows)}")
    print(f"Total hospitalizacion: {len(hospitalizacion_rows)}")
    print(f"Total recienNacidos: {len(rn_rows)}")
    if transaccion_top:
        print("Transaccion presente a nivel de factura")

    if not usuarios_data:
        raise ValueError("No se encontraron usuarios para procesar.")

    print(f"\n{total_usuarios:,} usuarios procesados correctamente")
    print(f"\nGenerando archivo Excel...")
    
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
    # Normalizar en secciones adicionales
    for df in [df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos]:
        if not df.empty and 'numDocumento_usuario' in df.columns:
            df['numDocumento_usuario'] = df['numDocumento_usuario'].apply(normalizar_documento)

    # Asegurar columnas mínimas para validaciones (crear si faltan)
    min_cols_cons = ['codDiagnosticoPrincipal','finalidadTecnologiaSalud','causaMotivoAtencion','codConsulta','codPrestador','fechaInicioAtencion','numAutorizacion']
    for c in min_cols_cons:
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

    min_cols_proc = ['codDiagnosticoPrincipal','finalidadTecnologiaSalud','codProcedimiento','codPrestador','fechaInicioAtencion','numAutorizacion']
    for c in min_cols_proc:
        if c not in df_procedimientos.columns:
            df_procedimientos[c] = ''
    if 'codDiagnosticoRelacionado' not in df_procedimientos.columns:
        df_procedimientos['codDiagnosticoRelacionado'] = ''
    if 'consecutivo_procedimiento' not in df_procedimientos.columns:
        df_procedimientos['consecutivo_procedimiento'] = ''

    # Ordenar: estándar primero y luego extras
    std_cons_order = [
        'numDocumento_usuario','tipoDocumento_usuario','numFactura','consecutivo_consulta',
        'codPrestador','fechaInicioAtencion','numAutorizacion','codConsulta',
        'modalidadGrupoServicioTecSal','grupoServicios','codServicio',
        'finalidadTecnologiaSalud','causaMotivoAtencion','codDiagnosticoPrincipal',
        'codDiagnosticoRelacionado1','codDiagnosticoRelacionado2','codDiagnosticoRelacionado3','tipoDiagnosticoPrincipal',
        'tipoDocumentoIdentificacion_profesional','numDocumentoIdentificacion_profesional','vrServicio','conceptoRecaudo','valorPagoModerador','numFEVPagoModerador'
    ]
    df_consultas = df_consultas.reindex(columns=[c for c in std_cons_order if c in df_consultas.columns] + [c for c in df_consultas.columns if c not in std_cons_order])

    std_proc_order = [
        'numDocumento_usuario','tipoDocumento_usuario','numFactura','consecutivo_procedimiento',
        'codPrestador','fechaInicioAtencion','idMIPRES','numAutorizacion','codProcedimiento',
        'viaIngresoServicioSalud','modalidadGrupoServicioTecSal','grupoServicios','codServicio',
        'finalidadTecnologiaSalud',
        'codDiagnosticoPrincipal','codDiagnosticoRelacionado','codComplicacion','vrServicio','conceptoRecaudo','valorPagoModerador','numFEVPagoModerador'
    ]
    df_procedimientos = df_procedimientos.reindex(columns=[c for c in std_proc_order if c in df_procedimientos.columns] + [c for c in df_procedimientos.columns if c not in std_proc_order])

    # Aplicar validaciones específicas de BC
    df_usuarios, df_consultas, df_procedimientos, df_medicamentos, cambios_diag = aplicar_validaciones_bc(df_usuarios, df_consultas, df_procedimientos, df_medicamentos)

    # Export to Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_usuarios.to_excel(writer, sheet_name='Usuarios', index=False)
        df_consultas.to_excel(writer, sheet_name='Consultas', index=False)
        df_procedimientos.to_excel(writer, sheet_name='Procedimientos', index=False)
        # Hojas adicionales si existen
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
                df_tx = pd.DataFrame([transaccion_top])
                df_tx.to_excel(writer, sheet_name='Transaccion', index=False)
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
    
    return excel_original, output, cambios_diag

def truncar_diagnostico(codigo):
    return truncar_codigo(codigo)

def aplicar_validaciones_bc(df_usuarios, df_consultas, df_procedimientos, df_medicamentos):
    """Aplica validaciones específicas para Baja Complejidad"""
    df_usuarios, [df_consultas, df_procedimientos, df_medicamentos] = normalizar_ppt_pt_en_dataframes(
        df_usuarios,
        [df_consultas, df_procedimientos, df_medicamentos],
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
    
    # Rellenar solo tipos de documento vacíos (los números ya vienen completados por completador_documentos.py)
    
    if not df_consultas.empty:
        consultas_tipo_vacios = df_consultas['tipoDocumentoIdentificacion_profesional'].isna() | (df_consultas['tipoDocumentoIdentificacion_profesional'] == '')
        df_consultas.loc[consultas_tipo_vacios, 'tipoDocumentoIdentificacion_profesional'] = 'CC'
    
    truncar_campos_dataframe(df_consultas, ['codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoPrincipal'])
    truncar_campos_dataframe(df_procedimientos, ['codDiagnosticoRelacionado', 'codDiagnosticoPrincipal'])
    
    from modules.motor_logico import aplicar_clasificacion_df_bc
    df_consultas, df_procedimientos, df_medicamentos, cambios_diag = aplicar_clasificacion_df_bc(
        df_consultas, df_procedimientos, df_medicamentos
    )

    print("Validaciones BC aplicadas")
    
    return df_usuarios, df_consultas, df_procedimientos, df_medicamentos, cambios_diag
