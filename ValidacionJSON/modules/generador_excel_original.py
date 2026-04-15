"""
Módulo para generar Excel desde JSON sin aplicar correcciones ni validaciones.
Solo convierte los datos originales del JSON a formato de tabla Excel.
"""

import json
import pandas as pd
from datetime import datetime
from io import BytesIO
from modules.format_standards import normalizar_documento


def generar_excel_original_pyp(json_file, filename):
    """
    Genera Excel desde JSON PYP SIN aplicar correcciones.
    Mantiene los datos originales tal como vienen en el JSON.
    
    Args:
        json_file: Archivo JSON cargado
        filename: Nombre del archivo
        
    Returns:
        BytesIO: Archivo Excel con datos originales
    """
    cutoff_date = datetime.now()
    
    data = json.load(json_file)
    json_file.seek(0)  # Reset para uso posterior
    
    numFactura = data.get('numFactura', '')
    numDocumentoIdObligado = data.get('numDocumentoIdObligado', '')
    archivoOrigen = filename + '.json'
    
    usuarios_data = []
    consultas_data = []
    procedimientos_data = []
    
    usuarios_list = data.get('usuarios', [])
    
    for user in usuarios_list:
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
        
        # Process consultas
        for idx, consulta in enumerate(consultas, 1):
            fecha = consulta.get('fechaInicioAtencion', '')
            fechas_atencion.append(fecha)
            
            codPrestador = normalizar_documento(consulta.get('codPrestador', ''))
            diagPrincipal = consulta.get('codDiagnosticoPrincipal', '')
            
            prestadores_unicos.add(codPrestador)
            if diagPrincipal:
                diagnosticos_unicos.add(diagPrincipal)
            
            consultas_data.append({
                'numDocumento_usuario': numDocUsuario,
                'tipoDocumento_usuario': tipoDocUsuario,
                'numFactura': numFactura,
                'consecutivo_consulta': idx,
                'codPrestador': codPrestador,
                'fechaInicioAtencion': fecha,
                'numAutorizacion': consulta.get('numAutorizacion', ''),
                'codConsulta': consulta.get('codConsulta', ''),
                'modalidadGrupoServicioTecSal': consulta.get('modalidadGrupoServicioTecSal', ''),
                'grupoServicios': consulta.get('grupoServicios', ''),
                'codServicio': consulta.get('codServicio', ''),
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
            diagPrincipal = proc.get('codDiagnosticoPrincipal', '')
            
            prestadores_unicos.add(codPrestador)
            if diagPrincipal:
                diagnosticos_unicos.add(diagPrincipal)
            
            procedimientos_data.append({
                'numDocumento_usuario': numDocUsuario,
                'tipoDocumento_usuario': tipoDocUsuario,
                'numFactura': numFactura,
                'consecutivo_procedimiento': idx,
                'codPrestador': codPrestador,
                'fechaInicioAtencion': fecha,
                'idMIPRES': proc.get('idMIPRES', ''),
                'numAutorizacion': proc.get('numAutorizacion', ''),
                'codProcedimiento': proc.get('codProcedimiento', ''),
                'viaIngresoServicioSalud': proc.get('viaIngresoServicioSalud', ''),
                'modalidadGrupoServicioTecSal': proc.get('modalidadGrupoServicioTecSal', ''),
                'grupoServicios': proc.get('grupoServicios', ''),
                'codServicio': proc.get('codServicio', ''),
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
    
    # Create DataFrames
    df_usuarios = pd.DataFrame(usuarios_data)
    df_consultas = pd.DataFrame(consultas_data)
    df_procedimientos = pd.DataFrame(procedimientos_data)
    
    # Export to Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_usuarios.to_excel(writer, sheet_name='Usuarios', index=False)
        df_consultas.to_excel(writer, sheet_name='Consultas', index=False)
        df_procedimientos.to_excel(writer, sheet_name='Procedimientos', index=False)
    
    output.seek(0)
    print(f"\n📄 Excel ORIGINAL generado (sin correcciones): {len(df_usuarios)} usuarios, {len(df_consultas)} consultas, {len(df_procedimientos)} procedimientos")
    
    return output


def generar_excel_original_bc(json_file, filename):
    """
    Genera Excel desde JSON BC SIN aplicar correcciones.
    Preserva TODAS las hojas adicionales (medicamentos, urgencias, hospitalizacion, etc.)
    """
    cutoff_date = datetime.now()
    
    data = json.load(json_file)
    json_file.seek(0)
    
    numFactura = data.get('numFactura', '')
    numDocumentoIdObligado = data.get('numDocumentoIdObligado', '')
    archivoOrigen = filename + '.json'
    transaccion_top = data.get('transaccion') if isinstance(data, dict) else None
    
    usuarios_data = []
    consultas_rows = []
    procedimientos_rows = []
    medicamentos_rows = []
    otros_serv_rows = []
    urgencias_rows = []
    hospitalizacion_rows = []
    rn_rows = []
    
    usuarios_list = data.get('usuarios', [])
    
    for user in usuarios_list:
        numDocUsuario = normalizar_documento(user.get('numDocumentoIdentificacion', ''))
        tipoDocUsuario = user.get('tipoDocumentoIdentificacion', '')
        fechaNac = user.get('fechaNacimiento', '')
        
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
        
        fechas_atencion = []
        prestadores_unicos = set()
        diagnosticos_unicos = set()
        
        # Process consultas - preservar todas las columnas
        for idx, consulta in enumerate(consultas, 1):
            fecha = consulta.get('fechaInicioAtencion', '')
            fechas_atencion.append(fecha)
            codPrestador = consulta.get('codPrestador', '')
            diagPrincipal = consulta.get('codDiagnosticoPrincipal', '')
            prestadores_unicos.add(codPrestador)
            if diagPrincipal:
                diagnosticos_unicos.add(diagPrincipal)
            
            row = dict(consulta)
            if 'codPrestador' in row:
                row['codPrestador'] = normalizar_documento(row['codPrestador'])
            row['numDocumento_usuario'] = numDocUsuario
            row['tipoDocumento_usuario'] = tipoDocUsuario
            row['numFactura'] = numFactura
            row['consecutivo_consulta'] = idx
            row.setdefault('tipoDocumentoIdentificacion_profesional', consulta.get('tipoDocumentoIdentificacion', ''))
            doc_prof = consulta.get('numDocumentoIdentificacion', '')
            row.setdefault('numDocumentoIdentificacion_profesional', normalizar_documento(doc_prof) if doc_prof else '')
            consultas_rows.append(row)
        
        # Process procedimientos - preservar todas las columnas
        for idx, proc in enumerate(procedimientos, 1):
            fecha = proc.get('fechaInicioAtencion', '')
            fechas_atencion.append(fecha)
            codPrestador = proc.get('codPrestador', '')
            diagPrincipal = proc.get('codDiagnosticoPrincipal', '')
            prestadores_unicos.add(codPrestador)
            if diagPrincipal:
                diagnosticos_unicos.add(diagPrincipal)
            
            rowp = dict(proc)
            if 'codPrestador' in rowp:
                rowp['codPrestador'] = normalizar_documento(rowp['codPrestador'])
            if 'numDocumentoIdentificacion' in rowp:
                rowp['numDocumentoIdentificacion'] = normalizar_documento(rowp['numDocumentoIdentificacion'])
            rowp['numDocumento_usuario'] = numDocUsuario
            rowp['tipoDocumento_usuario'] = tipoDocUsuario
            rowp['numFactura'] = numFactura
            rowp['consecutivo_procedimiento'] = idx
            rowp.setdefault('tipoDocumentoIdentificacion_profesional', proc.get('tipoDocumentoIdentificacion', ''))
            doc_prof_proc = proc.get('numDocumentoIdentificacion', '')
            rowp.setdefault('numDocumentoIdentificacion_profesional', normalizar_documento(doc_prof_proc) if doc_prof_proc else '')
            procedimientos_rows.append(rowp)
        
        # Process medicamentos
        for idx, med in enumerate(medicamentos, 1):
            rowm = dict(med)
            if 'codPrestador' in rowm:
                rowm['codPrestador'] = normalizar_documento(rowm['codPrestador'])
            rowm['numDocumento_usuario'] = numDocUsuario
            rowm['tipoDocumento_usuario'] = tipoDocUsuario
            rowm['numFactura'] = numFactura
            rowm['consecutivo_medicamento'] = idx
            medicamentos_rows.append(rowm)
        
        # Process otrosServicios
        for idx, otro in enumerate(otros_servicios, 1):
            rowo = dict(otro)
            if 'codPrestador' in rowo:
                rowo['codPrestador'] = normalizar_documento(rowo['codPrestador'])
            rowo['numDocumento_usuario'] = numDocUsuario
            rowo['tipoDocumento_usuario'] = tipoDocUsuario
            rowo['numFactura'] = numFactura
            rowo['consecutivo_otro'] = idx
            otros_serv_rows.append(rowo)
        
        # Process urgencias
        for idx, urg in enumerate(urgencias, 1):
            rowu = dict(urg)
            if 'codPrestador' in rowu:
                rowu['codPrestador'] = normalizar_documento(rowu['codPrestador'])
            rowu['numDocumento_usuario'] = numDocUsuario
            rowu['tipoDocumento_usuario'] = tipoDocUsuario
            rowu['numFactura'] = numFactura
            rowu['consecutivo_urgencia'] = idx
            urgencias_rows.append(rowu)
        
        # Process hospitalizacion
        for idx, hosp in enumerate(hospitalizacion, 1):
            # Hospitalización NO lleva campos profesionales - filtrar explícitamente
            rowh = {k: v for k, v in hosp.items() 
                   if k not in ['tipoDocumentoIdentificacion', 'numDocumentoIdentificacion']}
            if 'codPrestador' in rowh:
                rowh['codPrestador'] = normalizar_documento(rowh['codPrestador'])
            rowh['numDocumento_usuario'] = numDocUsuario
            rowh['tipoDocumento_usuario'] = tipoDocUsuario
            rowh['numFactura'] = numFactura
            rowh['consecutivo_hospitalizacion'] = idx
            hospitalizacion_rows.append(rowh)
        
        # Process recienNacidos
        for idx, rn in enumerate(recien_nacidos, 1):
            rowrn = dict(rn)
            if 'codPrestador' in rowrn:
                rowrn['codPrestador'] = normalizar_documento(rowrn['codPrestador'])
            rowrn['numDocumento_usuario'] = numDocUsuario
            rowrn['tipoDocumento_usuario'] = tipoDocUsuario
            rowrn['numFactura'] = numFactura
            rowrn['consecutivo_recien_nacido'] = idx
            rn_rows.append(rowrn)
        
        # Summary
        fechas_atencion_validas = [f for f in fechas_atencion if f]
        fecha_primera = min(fechas_atencion_validas) if fechas_atencion_validas else ''
        fecha_ultima = max(fechas_atencion_validas) if fechas_atencion_validas else ''
        
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
    
    # Create DataFrames
    df_usuarios = pd.DataFrame(usuarios_data)
    df_consultas = pd.DataFrame(consultas_rows)
    df_procedimientos = pd.DataFrame(procedimientos_rows)
    df_medicamentos = pd.DataFrame(medicamentos_rows) if medicamentos_rows else pd.DataFrame()
    df_otros_serv = pd.DataFrame(otros_serv_rows) if otros_serv_rows else pd.DataFrame()
    df_urgencias = pd.DataFrame(urgencias_rows) if urgencias_rows else pd.DataFrame()
    df_hospitalizacion = pd.DataFrame(hospitalizacion_rows) if hospitalizacion_rows else pd.DataFrame()
    df_recien_nacidos = pd.DataFrame(rn_rows) if rn_rows else pd.DataFrame()
    
    # Export to Excel
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
        if transaccion_top:
            try:
                pd.DataFrame([transaccion_top]).to_excel(writer, sheet_name='Transaccion', index=False)
            except:
                pass
    
    output.seek(0)
    print(f"\n📄 Excel ORIGINAL BC generado (sin correcciones): {len(df_usuarios)} usuarios")
    
    return output


def generar_excel_original_compuestos(json_file, filename):
    """
    Genera Excel desde JSON COMPUESTOS SIN aplicar correcciones.
    Preserva todas las columnas adicionales que puedan existir.
    """
    # Compuestos usa la misma estructura que BC
    return generar_excel_original_bc(json_file, filename)
