"""
Conversor Excel → JSON
Módulo independiente para convertir archivos Excel a JSON según el tipo detectado.
Soporta PyP, BC y Compuestos.
"""

import pandas as pd
import re
import json
from io import BytesIO
from modules.format_standards import FIELD_FORMATS, normalizar_documento

# Campos a excluir de usuarios
CAMPOS_EXCLUIR_USUARIOS = [
    'edad_al_2025_09_30', 'archivoOrigen', 'total_consultas', 'total_procedimientos',
    'total_eventos', 'fecha_primera_atencion', 'fecha_ultima_atencion',
    'num_prestadores_distintos', 'num_diagnosticos_distintos', 'diagnosticos_principales'
]

# Orden específico de campos para usuarios
ORDEN_CAMPOS_USUARIOS = [
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion', 'tipoUsuario',
    'fechaNacimiento', 'codSexo', 'codPaisResidencia', 'codMunicipioResidencia',
    'codZonaTerritorialResidencia', 'incapacidad', 'consecutivo', 'codPaisOrigen',
    'servicios'
]

# Orden específico de campos para consultas
ORDEN_CAMPOS_CONSULTAS = [
    'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'codConsulta',
    'modalidadGrupoServicioTecSal', 'grupoServicios', 'codServicio',
    'finalidadTecnologiaSalud', 'causaMotivoAtencion', 'codDiagnosticoPrincipal',
    'codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3',
    'tipoDiagnosticoPrincipal', 'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
    'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador',
    'consecutivo'
]

# Orden específico de campos para procedimientos
ORDEN_CAMPOS_PROCEDIMIENTOS = [
    'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'idMIPRES',
    'codProcedimiento', 'viaIngresoServicioSalud', 'modalidadGrupoServicioTecSal',
    'grupoServicios', 'codServicio', 'finalidadTecnologiaSalud',
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
    'codDiagnosticoPrincipal', 'codDiagnosticoRelacionado', 'codComplicacion',
    'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador',
    'consecutivo'
]

# Orden específico de campos para medicamentos
ORDEN_CAMPOS_MEDICAMENTOS = [
    'codPrestador', 'numAutorizacion', 'idMIPRES', 'fechaDispensAdmon',
    'codDiagnosticoPrincipal', 'codDiagnosticoRelacionado',
    'tipoMedicamento', 'codTecnologiaSalud', 'nomTecnologiaSalud',
    'concentracionMedicamento', 'unidadMedida', 'formaFarmaceutica',
    'unidadMinDispensa', 'cantidadMedicamento', 'diasTratamiento',
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
    'vrUnitMedicamento', 'vrServicio', 'conceptoRecaudo',
    'valorPagoModerador', 'numFEVPagoModerador', 'consecutivo'
]

# Orden específico de campos para otros servicios
ORDEN_CAMPOS_OTROS_SERVICIOS = [
    'codPrestador', 'numAutorizacion', 'idMIPRES', 'fechaSuministroTecnologia',
    'tipoOS', 'codTecnologiaSalud', 'nomTecnologiaSalud', 'cantidadOS',
    'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
    'vrUnitOS', 'vrServicio', 'conceptoRecaudo',
    'valorPagoModerador', 'numFEVPagoModerador', 'consecutivo'
]

# Orden específico de campos para urgencias
ORDEN_CAMPOS_URGENCIAS = [
    'codPrestador', 'fechaInicioAtencion', 'causaMotivoAtencion',
    'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
    'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
    'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte', 'fechaEgreso',
    'consecutivo'
]

# Orden específico de campos para hospitalización
ORDEN_CAMPOS_HOSPITALIZACION = [
    'codPrestador', 'viaIngresoServicioSalud', 'fechaInicioAtencion', 'numAutorizacion',
    'causaMotivoAtencion', 'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
    'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
    'codComplicacion', 'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte', 'fechaEgreso',
    'consecutivo'
]

# Orden específico de campos para recién nacidos
ORDEN_CAMPOS_RECIEN_NACIDOS = [
    'codPrestador', 'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
    'fechaNacimiento', 'edadGestacional', 'codSexoBiologico', 'peso',
    'codDiagnosticoPrincipal', 'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte',
    'fechaEgreso', 'consecutivo'
]

# Columnas internas que no deben incluirse en los servicios del JSON
EXCLUDE_INTERNAL = {
    'numDocumento_usuario', 'tipoDocumento_usuario',
    'consecutivo_consulta', 'consecutivo_procedimiento',
    'consecutivo_medicamento', 'consecutivo_otro', 'consecutivo_urgencia',
    'consecutivo_hospitalizacion', 'consecutivo_recien_nacido',
    'tipoDocumentoIdentificacion_profesional', 'numDocumentoIdentificacion_profesional',
    'numFactura', 'archivoOrigen'
}

def normalizar_valor_campo(campo, valor):
    """
    Normaliza un valor según su tipo de campo definido en FIELD_FORMATS.
    
    Args:
        campo: Nombre del campo
        valor: Valor a normalizar
    
    Returns:
        Valor normalizado según el tipo de campo
    """
    # Si el valor es NaN, None o vacío
    if pd.isna(valor) or valor is None or valor == '':
        # Campos que deben ser null cuando vacíos
        if campo in ['codDiagnosticoRelacionado', 'codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 
                     'codDiagnosticoRelacionado3', 'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2',
                     'codDiagnosticoRelacionadoE3', 'codComplicacion', 'codDiagnosticoCausaMuerte',
                     'numAutorizacion', 'idMIPRES', 'numFEVPagoModerador', 'formaFarmaceutica',
                     'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE']:
            return None
        return ''
    
    # Si hay una función de normalización definida, usarla
    if campo in FIELD_FORMATS:
        normalize_func, _ = FIELD_FORMATS[campo]
        return normalize_func(valor)
    
    # Si no hay formato definido, devolver como string
    return str(valor).strip()


def detectar_tipo_excel(sheet_names):
    """
    Detecta el tipo de Excel (PyP, BC o Compuestos) según las pestañas.
    
    Args:
        sheet_names: Lista de nombres de pestañas del Excel
    
    Returns:
        str: 'PYP', 'BC' o 'COMPUESTOS'
    """
    sheet_names_lower = [s.lower() for s in sheet_names]
    
    # Compuestos tiene pestañas específicas como Usuarios, Consultas, Procedimientos, etc.
    if 'usuarios' in sheet_names_lower:
        return 'COMPUESTOS'
    
    # PyP tiene hojas como Transacciones, Usuarios, Consultas
    if 'transacciones' in sheet_names_lower:
        return 'PYP'
    
    # BC tiene hojas como Usuarios, Consultas pero sin Transacciones
    if 'consultas' in sheet_names_lower or 'procedimientos' in sheet_names_lower:
        return 'BC'
    
    # Por defecto, asumir BC si no se puede determinar
    return 'BC'


def convert_excel_to_json_pyp(excel_file):
    """
    Convierte Excel de PyP a JSON.
    
    Estructura PyP:
    - Transacciones
    - Usuarios
    - Consultas
    - Procedimientos
    """
    excel_data = pd.ExcelFile(excel_file)
    
    # Leer hojas (sin forzar dtype=str, dejar que pandas detecte tipos)
    df_transacciones = pd.read_excel(excel_data, 'Transacciones') if 'Transacciones' in excel_data.sheet_names else pd.DataFrame()
    df_usuarios = pd.read_excel(excel_data, 'Usuarios') if 'Usuarios' in excel_data.sheet_names else pd.DataFrame()
    df_consultas = pd.read_excel(excel_data, 'Consultas') if 'Consultas' in excel_data.sheet_names else pd.DataFrame()
    df_procedimientos = pd.read_excel(excel_data, 'Procedimientos') if 'Procedimientos' in excel_data.sheet_names else pd.DataFrame()
    
    print(f"📊 PyP - Registros leídos:")
    print(f"   • Transacciones: {len(df_transacciones)}")
    print(f"   • Usuarios: {len(df_usuarios)}")
    print(f"   • Consultas: {len(df_consultas)}")
    print(f"   • Procedimientos: {len(df_procedimientos)}")
    
    # Extraer numDocumentoIdObligado y numFactura desde Transacciones o Usuarios
    num_documento_id_obligado = ''
    num_factura = ''
    if not df_transacciones.empty:
        first_row = df_transacciones.iloc[0]
        if 'numDocumentoIdObligado' in df_transacciones.columns:
            num_documento_id_obligado = str(first_row['numDocumentoIdObligado']) if pd.notna(first_row['numDocumentoIdObligado']) else ''
        if 'numFactura' in df_transacciones.columns:
            num_factura = str(first_row['numFactura']) if pd.notna(first_row['numFactura']) else ''
    if not num_documento_id_obligado and not df_usuarios.empty:
        if 'numDocumentoIdObligado' in df_usuarios.columns:
            num_documento_id_obligado = str(df_usuarios.iloc[0]['numDocumentoIdObligado']) if pd.notna(df_usuarios.iloc[0]['numDocumentoIdObligado']) else ''
    if not num_factura and not df_usuarios.empty:
        if 'numFactura' in df_usuarios.columns:
            num_factura = str(df_usuarios.iloc[0]['numFactura']) if pd.notna(df_usuarios.iloc[0]['numFactura']) else ''

    # Estructura base PyP — igual a BC y Compuestos
    resultado = {
        'numDocumentoIdObligado': num_documento_id_obligado,
        'numFactura': num_factura,
        'tipoNota': None,
        'numNota': None,
        'usuarios': []
    }
    
    # Procesar usuarios con servicios
    if not df_usuarios.empty:
        for _, user_row in df_usuarios.iterrows():
            usuario = {}
            # Agregar campos en orden específico (excluyendo 'servicios')
            for campo in ORDEN_CAMPOS_USUARIOS:
                if campo != 'servicios' and campo in user_row.index:
                    usuario[campo] = normalizar_valor_campo(campo, user_row[campo])
            
            # Agregar servicios del usuario
            num_doc = normalizar_documento(usuario.get('numDocumentoIdentificacion', ''))
            tipo_doc = usuario.get('tipoDocumentoIdentificacion', '')
            
            usuario['servicios'] = {}
            
            # Consultas del usuario
            if not df_consultas.empty:
                # Normalizar los documentos de las consultas para comparación
                df_consultas_norm = df_consultas.copy()
                df_consultas_norm['numDocumentoIdentificacion'] = df_consultas_norm['numDocumentoIdentificacion'].apply(normalizar_documento)
                
                user_consultas = df_consultas_norm[
                    (df_consultas_norm['numDocumentoIdentificacion'] == num_doc) &
                    (df_consultas_norm['tipoDocumentoIdentificacion'] == tipo_doc)
                ]
                if not user_consultas.empty:
                    consultas_list = []
                    for _, cons in user_consultas.iterrows():
                        consulta = {}
                        # Agregar campos en orden específico
                        for campo in ORDEN_CAMPOS_CONSULTAS:
                            if campo in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons['numDocumentoIdentificacion_profesional'])
                        consultas_list.append(consulta)
                    usuario['servicios']['consultas'] = consultas_list
                    print(f"   ✓ Usuario {num_doc}: {len(consultas_list)} consultas")
            
            # Procedimientos del usuario
            if not df_procedimientos.empty:
                # Normalizar los documentos de los procedimientos para comparación
                df_procedimientos_norm = df_procedimientos.copy()
                df_procedimientos_norm['numDocumentoIdentificacion'] = df_procedimientos_norm['numDocumentoIdentificacion'].apply(normalizar_documento)
                
                user_proc = df_procedimientos_norm[
                    (df_procedimientos_norm['numDocumentoIdentificacion'] == num_doc) &
                    (df_procedimientos_norm['tipoDocumentoIdentificacion'] == tipo_doc)
                ]
                if not user_proc.empty:
                    proc_list = []
                    for _, proc in user_proc.iterrows():
                        procedimiento = {}
                        # Agregar campos en orden específico
                        for campo in ORDEN_CAMPOS_PROCEDIMIENTOS:
                            if campo in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc['numDocumentoIdentificacion_profesional'])
                        proc_list.append(procedimiento)
                    usuario['servicios']['procedimientos'] = proc_list
                    print(f"   ✓ Usuario {num_doc}: {len(proc_list)} procedimientos")
            
            resultado['usuarios'].append(usuario)
    
    return resultado


def convert_excel_to_json_bc(excel_file):
    """
    Convierte Excel de BC a JSON.
    
    Estructura BC:
    - Usuarios
    - Consultas
    - Procedimientos
    """
    excel_data = pd.ExcelFile(excel_file)
    
    # Leer hojas
    df_usuarios = pd.read_excel(excel_data, 'Usuarios') if 'Usuarios' in excel_data.sheet_names else pd.DataFrame()
    df_consultas = pd.read_excel(excel_data, 'Consultas') if 'Consultas' in excel_data.sheet_names else pd.DataFrame()
    df_procedimientos = pd.read_excel(excel_data, 'Procedimientos') if 'Procedimientos' in excel_data.sheet_names else pd.DataFrame()
    
    print(f"📊 BC - Registros leídos:")
    print(f"   • Usuarios: {len(df_usuarios)}")
    print(f"   • Consultas: {len(df_consultas)}")
    print(f"   • Procedimientos: {len(df_procedimientos)}")
    
    # Extraer numDocumentoIdObligado y numFactura desde Usuarios
    num_documento_id_obligado = ''
    num_factura = ''
    if not df_usuarios.empty:
        if 'numDocumentoIdObligado' in df_usuarios.columns:
            num_documento_id_obligado = str(df_usuarios.iloc[0]['numDocumentoIdObligado']) if pd.notna(df_usuarios.iloc[0]['numDocumentoIdObligado']) else ''
        if 'numFactura' in df_usuarios.columns:
            num_factura = str(df_usuarios.iloc[0]['numFactura']) if pd.notna(df_usuarios.iloc[0]['numFactura']) else ''

    # Estructura base BC — igual a PyP y Compuestos
    resultado = {
        'numDocumentoIdObligado': num_documento_id_obligado,
        'numFactura': num_factura,
        'tipoNota': None,
        'numNota': None,
        'usuarios': []
    }
    
    # Procesar usuarios con servicios
    if not df_usuarios.empty:
        for _, user_row in df_usuarios.iterrows():
            usuario = {}
            # Agregar campos en orden específico (excluyendo 'servicios')
            for campo in ORDEN_CAMPOS_USUARIOS:
                if campo != 'servicios' and campo in user_row.index:
                    usuario[campo] = normalizar_valor_campo(campo, user_row[campo])
            
            # Agregar servicios del usuario
            num_doc = normalizar_documento(usuario.get('numDocumentoIdentificacion', ''))
            tipo_doc = usuario.get('tipoDocumentoIdentificacion', '')
            
            usuario['servicios'] = {}
            
            # Consultas del usuario
            if not df_consultas.empty:
                # Normalizar los documentos de las consultas para comparación
                df_consultas_norm = df_consultas.copy()
                df_consultas_norm['numDocumentoIdentificacion'] = df_consultas_norm['numDocumentoIdentificacion'].apply(normalizar_documento)
                
                user_consultas = df_consultas_norm[
                    (df_consultas_norm['numDocumentoIdentificacion'] == num_doc) &
                    (df_consultas_norm['tipoDocumentoIdentificacion'] == tipo_doc)
                ]
                if not user_consultas.empty:
                    consultas_list = []
                    for _, cons in user_consultas.iterrows():
                        consulta = {}
                        # Agregar campos en orden específico
                        for campo in ORDEN_CAMPOS_CONSULTAS:
                            if campo in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons['numDocumentoIdentificacion_profesional'])
                        consultas_list.append(consulta)
                    usuario['servicios']['consultas'] = consultas_list
                    print(f"   ✓ Usuario {num_doc}: {len(consultas_list)} consultas")
            
            # Procedimientos del usuario
            if not df_procedimientos.empty:
                # Normalizar los documentos de los procedimientos para comparación
                df_procedimientos_norm = df_procedimientos.copy()
                df_procedimientos_norm['numDocumentoIdentificacion'] = df_procedimientos_norm['numDocumentoIdentificacion'].apply(normalizar_documento)
                
                user_proc = df_procedimientos_norm[
                    (df_procedimientos_norm['numDocumentoIdentificacion'] == num_doc) &
                    (df_procedimientos_norm['tipoDocumentoIdentificacion'] == tipo_doc)
                ]
                if not user_proc.empty:
                    proc_list = []
                    for _, proc in user_proc.iterrows():
                        procedimiento = {}
                        # Agregar campos en orden específico
                        for campo in ORDEN_CAMPOS_PROCEDIMIENTOS:
                            if campo in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc['numDocumentoIdentificacion_profesional'])
                        proc_list.append(procedimiento)
                    usuario['servicios']['procedimientos'] = proc_list
                    print(f"   ✓ Usuario {num_doc}: {len(proc_list)} procedimientos")
            
            resultado['usuarios'].append(usuario)
    
    return resultado


def convert_excel_to_json_compuestos(excel_file):
    """
    Convierte Excel de Compuestos a JSON.
    
    Estructura Compuestos:
    - numDocumentoIdObligado
    - numFactura
    - usuarios (con múltiples servicios)
    """
    excel_data = pd.ExcelFile(excel_file)
    
    # Leer hojas
    df_usuarios = pd.read_excel(excel_data, 'Usuarios') if 'Usuarios' in excel_data.sheet_names else pd.DataFrame()
    df_consultas = pd.read_excel(excel_data, 'Consultas') if 'Consultas' in excel_data.sheet_names else pd.DataFrame()
    df_procedimientos = pd.read_excel(excel_data, 'Procedimientos') if 'Procedimientos' in excel_data.sheet_names else pd.DataFrame()
    df_medicamentos = pd.read_excel(excel_data, 'Medicamentos') if 'Medicamentos' in excel_data.sheet_names else pd.DataFrame()
    df_otros_serv = pd.read_excel(excel_data, 'OtrosServicios') if 'OtrosServicios' in excel_data.sheet_names else pd.DataFrame()
    df_urgencias = pd.read_excel(excel_data, 'Urgencias') if 'Urgencias' in excel_data.sheet_names else pd.DataFrame()
    df_hospitalizacion = pd.read_excel(excel_data, 'Hospitalizacion') if 'Hospitalizacion' in excel_data.sheet_names else pd.DataFrame()
    df_recien_nacidos = pd.read_excel(excel_data, 'RecienNacidos') if 'RecienNacidos' in excel_data.sheet_names else pd.DataFrame()
    
    print(f"📊 Compuestos - Registros leídos:")
    print(f"   • Usuarios: {len(df_usuarios)}")
    print(f"   • Consultas: {len(df_consultas)}")
    print(f"   • Procedimientos: {len(df_procedimientos)}")
    print(f"   • Medicamentos: {len(df_medicamentos)}")
    print(f"   • Otros Servicios: {len(df_otros_serv)}")
    print(f"   • Urgencias: {len(df_urgencias)}")
    print(f"   • Hospitalización: {len(df_hospitalizacion)}")
    print(f"   • Recién Nacidos: {len(df_recien_nacidos)}")
    
    # Estructura base Compuestos
    resultado = {
        'numDocumentoIdObligado': '',
        'numFactura': '',
        'tipoNota': None,
        'numNota': None,
        'usuarios': []
    }
    
    # Obtener información de factura desde primera fila de cualquier sheet
    if not df_usuarios.empty and 'numFactura' in df_usuarios.columns:
        resultado['numFactura'] = str(df_usuarios.iloc[0]['numFactura']) if pd.notna(df_usuarios.iloc[0]['numFactura']) else ''
    if not df_usuarios.empty and 'numDocumentoIdObligado' in df_usuarios.columns:
        resultado['numDocumentoIdObligado'] = str(df_usuarios.iloc[0]['numDocumentoIdObligado']) if pd.notna(df_usuarios.iloc[0]['numDocumentoIdObligado']) else ''
    
    # Procesar usuarios con servicios
    if not df_usuarios.empty:
        for _, user_row in df_usuarios.iterrows():
            usuario = {}
            # Agregar campos en orden específico (excluyendo 'servicios', 'numFactura', 'numDocumentoIdObligado')
            for campo in ORDEN_CAMPOS_USUARIOS:
                if campo != 'servicios' and campo in user_row.index and campo not in ['numFactura', 'numDocumentoIdObligado']:
                    usuario[campo] = normalizar_valor_campo(campo, user_row[campo])
            
            # Agregar servicios del usuario
            num_doc = normalizar_documento(usuario.get('numDocumentoIdentificacion', ''))
            tipo_doc = usuario.get('tipoDocumentoIdentificacion', '')
            
            usuario['servicios'] = {}
            
            # Consultas del usuario
            if not df_consultas.empty and 'numDocumento_usuario' in df_consultas.columns:
                # Normalizar los documentos para comparación
                df_consultas_norm = df_consultas.copy()
                df_consultas_norm['numDocumento_usuario'] = df_consultas_norm['numDocumento_usuario'].apply(normalizar_documento)
                
                user_consultas = df_consultas_norm[
                    (df_consultas_norm['numDocumento_usuario'] == num_doc) &
                    (df_consultas_norm['tipoDocumento_usuario'] == tipo_doc)
                ]
                if not user_consultas.empty:
                    consultas_list = []
                    for _, cons in user_consultas.iterrows():
                        consulta = {}
                        # Agregar campos en orden específico
                        for campo in ORDEN_CAMPOS_CONSULTAS:
                            if campo in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in cons.index:
                                consulta[campo] = normalizar_valor_campo(campo, cons['numDocumentoIdentificacion_profesional'])
                        consultas_list.append(consulta)
                    usuario['servicios']['consultas'] = consultas_list
                    print(f"   ✓ Usuario {num_doc}: {len(consultas_list)} consultas")
            
            # Procedimientos del usuario
            if not df_procedimientos.empty and 'numDocumento_usuario' in df_procedimientos.columns:
                # Normalizar los documentos para comparación
                df_procedimientos_norm = df_procedimientos.copy()
                df_procedimientos_norm['numDocumento_usuario'] = df_procedimientos_norm['numDocumento_usuario'].apply(normalizar_documento)
                
                user_proc = df_procedimientos_norm[
                    (df_procedimientos_norm['numDocumento_usuario'] == num_doc) &
                    (df_procedimientos_norm['tipoDocumento_usuario'] == tipo_doc)
                ]
                if not user_proc.empty:
                    proc_list = []
                    for _, proc in user_proc.iterrows():
                        procedimiento = {}
                        # Agregar campos en orden específico
                        for campo in ORDEN_CAMPOS_PROCEDIMIENTOS:
                            if campo in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in proc.index:
                                procedimiento[campo] = normalizar_valor_campo(campo, proc['numDocumentoIdentificacion_profesional'])
                        proc_list.append(procedimiento)
                    usuario['servicios']['procedimientos'] = proc_list
                    print(f"   ✓ Usuario {num_doc}: {len(proc_list)} procedimientos")
            
            # Medicamentos del usuario
            if not df_medicamentos.empty and 'numDocumento_usuario' in df_medicamentos.columns:
                # Normalizar los documentos para comparación
                df_medicamentos_norm = df_medicamentos.copy()
                df_medicamentos_norm['numDocumento_usuario'] = df_medicamentos_norm['numDocumento_usuario'].apply(normalizar_documento)
                
                user_med = df_medicamentos_norm[
                    (df_medicamentos_norm['numDocumento_usuario'] == num_doc) &
                    (df_medicamentos_norm['tipoDocumento_usuario'] == tipo_doc)
                ]
                if not user_med.empty:
                    med_list = []
                    for _, med in user_med.iterrows():
                        medicamento = {}
                        for campo in ORDEN_CAMPOS_MEDICAMENTOS:
                            if campo in med.index and campo not in EXCLUDE_INTERNAL:
                                medicamento[campo] = normalizar_valor_campo(campo, med[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in med.index:
                                medicamento[campo] = normalizar_valor_campo(campo, med['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in med.index:
                                medicamento[campo] = normalizar_valor_campo(campo, med['numDocumentoIdentificacion_profesional'])
                        med_list.append(medicamento)
                    usuario['servicios']['medicamentos'] = med_list
                    print(f"   ✓ Usuario {num_doc}: {len(med_list)} medicamentos")
            
            # Otros Servicios del usuario
            if not df_otros_serv.empty and 'numDocumento_usuario' in df_otros_serv.columns:
                # Normalizar los documentos para comparación
                df_otros_serv_norm = df_otros_serv.copy()
                df_otros_serv_norm['numDocumento_usuario'] = df_otros_serv_norm['numDocumento_usuario'].apply(normalizar_documento)
                
                user_otros = df_otros_serv_norm[
                    (df_otros_serv_norm['numDocumento_usuario'] == num_doc) &
                    (df_otros_serv_norm['tipoDocumento_usuario'] == tipo_doc)
                ]
                if not user_otros.empty:
                    otros_list = []
                    for _, otro in user_otros.iterrows():
                        otro_servicio = {}
                        for campo in ORDEN_CAMPOS_OTROS_SERVICIOS:
                            if campo in otro.index and campo not in EXCLUDE_INTERNAL:
                                otro_servicio[campo] = normalizar_valor_campo(campo, otro[campo])
                            # Si el campo no existe pero hay versión _profesional, usar esa
                            elif campo == 'tipoDocumentoIdentificacion' and 'tipoDocumentoIdentificacion_profesional' in otro.index:
                                otro_servicio[campo] = normalizar_valor_campo(campo, otro['tipoDocumentoIdentificacion_profesional'])
                            elif campo == 'numDocumentoIdentificacion' and 'numDocumentoIdentificacion_profesional' in otro.index:
                                otro_servicio[campo] = normalizar_valor_campo(campo, otro['numDocumentoIdentificacion_profesional'])
                        otros_list.append(otro_servicio)
                    usuario['servicios']['otrosServicios'] = otros_list
                    print(f"   ✓ Usuario {num_doc}: {len(otros_list)} otros servicios")
            
            # Urgencias del usuario
            if not df_urgencias.empty and 'numDocumento_usuario' in df_urgencias.columns:
                # Normalizar los documentos para comparación
                df_urgencias_norm = df_urgencias.copy()
                df_urgencias_norm['numDocumento_usuario'] = df_urgencias_norm['numDocumento_usuario'].apply(normalizar_documento)
                
                user_urg = df_urgencias_norm[
                    (df_urgencias_norm['numDocumento_usuario'] == num_doc) &
                    (df_urgencias_norm['tipoDocumento_usuario'] == tipo_doc)
                ]
                if not user_urg.empty:
                    urg_list = []
                    for _, urg in user_urg.iterrows():
                        urgencia = {}
                        for campo in ORDEN_CAMPOS_URGENCIAS:
                            if campo in urg.index and campo not in EXCLUDE_INTERNAL:
                                urgencia[campo] = normalizar_valor_campo(campo, urg[campo])
                        urg_list.append(urgencia)
                    usuario['servicios']['urgencias'] = urg_list
                    print(f"   ✓ Usuario {num_doc}: {len(urg_list)} urgencias")
            
            # Hospitalización del usuario
            if not df_hospitalizacion.empty and 'numDocumento_usuario' in df_hospitalizacion.columns:
                # Normalizar los documentos para comparación
                df_hospitalizacion_norm = df_hospitalizacion.copy()
                df_hospitalizacion_norm['numDocumento_usuario'] = df_hospitalizacion_norm['numDocumento_usuario'].apply(normalizar_documento)
                
                user_hosp = df_hospitalizacion_norm[
                    (df_hospitalizacion_norm['numDocumento_usuario'] == num_doc) &
                    (df_hospitalizacion_norm['tipoDocumento_usuario'] == tipo_doc)
                ]
                if not user_hosp.empty:
                    hosp_list = []
                    for _, hosp in user_hosp.iterrows():
                        hospitalizacion = {}
                        for campo in ORDEN_CAMPOS_HOSPITALIZACION:
                            if campo in hosp.index and campo not in EXCLUDE_INTERNAL:
                                hospitalizacion[campo] = normalizar_valor_campo(campo, hosp[campo])
                        hosp_list.append(hospitalizacion)
                    usuario['servicios']['hospitalizacion'] = hosp_list
                    print(f"   ✓ Usuario {num_doc}: {len(hosp_list)} hospitalizaciones")
            
            # Recién Nacidos del usuario
            if not df_recien_nacidos.empty and 'numDocumento_usuario' in df_recien_nacidos.columns:
                # Normalizar los documentos para comparación
                df_recien_nacidos_norm = df_recien_nacidos.copy()
                df_recien_nacidos_norm['numDocumento_usuario'] = df_recien_nacidos_norm['numDocumento_usuario'].apply(normalizar_documento)
                
                user_rn = df_recien_nacidos_norm[
                    (df_recien_nacidos_norm['numDocumento_usuario'] == num_doc) &
                    (df_recien_nacidos_norm['tipoDocumento_usuario'] == tipo_doc)
                ]
                if not user_rn.empty:
                    rn_list = []
                    for _, rn in user_rn.iterrows():
                        recien_nacido = {}
                        for campo in ORDEN_CAMPOS_RECIEN_NACIDOS:
                            if campo in rn.index and campo not in EXCLUDE_INTERNAL:
                                recien_nacido[campo] = normalizar_valor_campo(campo, rn[campo])
                        rn_list.append(recien_nacido)
                    usuario['servicios']['recienNacidos'] = rn_list
                    print(f"   ✓ Usuario {num_doc}: {len(rn_list)} recién nacidos")
            
            resultado['usuarios'].append(usuario)
    
    return resultado


def convert_excel_to_json(file_stream):
    """
    Función principal: Convierte Excel a JSON detectando automáticamente el tipo.
    
    Args:
        file_stream: BytesIO o archivo Excel
    
    Returns:
        tuple: (json_string, tipo_detectado)
    """
    # Detectar tipo de Excel
    excel_file = pd.ExcelFile(file_stream)
    tipo_excel = detectar_tipo_excel(excel_file.sheet_names)
    
    print(f"📊 Tipo de Excel detectado: {tipo_excel}")
    
    # Convertir según el tipo
    file_stream.seek(0)  # Reset stream
    
    if tipo_excel == 'PYP':
        resultado = convert_excel_to_json_pyp(file_stream)
    elif tipo_excel == 'BC':
        resultado = convert_excel_to_json_bc(file_stream)
    else:  # COMPUESTOS
        resultado = convert_excel_to_json_compuestos(file_stream)
    
    # Convertir a JSON string con indentación compacta
    # Usar separators para formato compacto: [{ en vez de [\n  {
    json_string = json.dumps(resultado, indent=4, ensure_ascii=False, separators=(',', ': '))

    # Mantener el formato estándar con saltos de línea para }]
    json_string = re.sub(r'(\s*)"(\w+)":\s*\[\s*\n\s+\{', r'\1"\2": [{', json_string)
    json_string = re.sub(r'\},\s*\n\s+\{', '}, {', json_string)
    
    # Resumen de servicios generados
    total_usuarios = len(resultado.get('usuarios', []))
    total_servicios = 0
    tipos_servicios = {}
    
    for usuario in resultado.get('usuarios', []):
        servicios = usuario.get('servicios', {})
        for tipo_servicio, lista_servicios in servicios.items():
            if isinstance(lista_servicios, list):
                count = len(lista_servicios)
                total_servicios += count
                tipos_servicios[tipo_servicio] = tipos_servicios.get(tipo_servicio, 0) + count
    
    print(f"\n📦 Resumen de conversión:")
    print(f"   • Total usuarios: {total_usuarios}")
    print(f"   • Total servicios: {total_servicios}")
    for tipo, cantidad in tipos_servicios.items():
        print(f"   • {tipo}: {cantidad}")
    print()
    
    return json_string, tipo_excel
