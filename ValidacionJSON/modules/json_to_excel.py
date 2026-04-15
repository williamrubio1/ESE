"""
Módulo JSON → Excel - Visualización pura sin transformaciones
Convierte archivos JSON (PYP, BC, Compuestos) a Excel para revisión
NO aplica correcciones, validaciones ni sustituciones
"""

import json
import pandas as pd
from datetime import datetime
from io import BytesIO
from modules.format_standards import normalizar_documento


def detectar_tipo_json(data):
    """
    Detecta el tipo de JSON basándose en la estructura de servicios.
    Revisa todos los usuarios para no depender del orden.
    
    Returns:
        str: 'pyp', 'bc' o 'compuestos'
    """
    if not data.get('usuarios'):
        return 'pyp'  # Default
    
    for usuario in data['usuarios']:
        servicios = usuario.get('servicios', {})
        # Si algún usuario tiene recién nacidos, es Compuestos
        if 'recienNacidos' in servicios:
            return 'compuestos'
        # Si algún usuario tiene medicamentos, urgencias u hospitalización, es BC
        if any(key in servicios for key in ['medicamentos', 'hospitalizacion', 'otrosServicios']):
            return 'bc'
    
    # Solo consultas y procedimientos = PYP
    return 'pyp'


def convertir_json_a_excel(json_files, nombres_archivos):
    """
    Convierte uno o múltiples archivos JSON a un único Excel con hojas separadas.
    NO aplica validaciones ni transformaciones.
    
    Args:
        json_files: Lista de archivos JSON (BytesIO)
        nombres_archivos: Lista de nombres de archivos originales
        
    Returns:
        BytesIO: Archivo Excel con todas las hojas
        str: Tipo detectado ('pyp', 'bc', 'compuestos')
        dict: Estadísticas del procesamiento
    """
    
    print(f"\n{'='*60}")
    print(f"📊 JSON → EXCEL - VISUALIZACIÓN PURA")
    print(f"{'='*60}")
    print(f"📁 Archivos a procesar: {len(json_files)}")
    
    # Estructuras acumuladoras para todos los archivos
    usuarios_data = []
    consultas_data = []
    procedimientos_data = []
    medicamentos_data = []
    otros_servicios_data = []
    urgencias_data = []
    hospitalizacion_data = []
    recien_nacidos_data = []
    
    tipo_detectado = None
    estadisticas = {
        'archivos_procesados': 0,
        'total_usuarios': 0,
        'total_consultas': 0,
        'total_procedimientos': 0,
        'total_medicamentos': 0,
        'total_otros_servicios': 0,
        'total_urgencias': 0,
        'total_hospitalizacion': 0,
        'total_recien_nacidos': 0
    }
    
    cutoff_date = datetime.now()
    
    # Procesar cada archivo JSON
    for idx, (json_file, nombre_archivo) in enumerate(zip(json_files, nombres_archivos), 1):
        try:
            print(f"  📄 Archivo {idx}/{len(json_files)}: {nombre_archivo}")
            
            json_file.seek(0)
            content = json_file.read()
            
            # Validar que el archivo no esté vacío
            if not content or len(content) == 0:
                print(f"     ❌ Error: Archivo vacío")
                continue
            
            # Decodificar bytes si es necesario
            if isinstance(content, bytes):
                try:
                    content = content.decode('utf-8')
                except UnicodeDecodeError:
                    print(f"     ❌ Error: No se pudo decodificar el archivo como UTF-8")
                    continue
            
            # Intentar parsear el JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as je:
                print(f"     ❌ Error JSON inválido: {str(je)}")
                continue
            
            # Validar estructura básica
            if not isinstance(data, dict):
                print(f"     ❌ Error: El JSON debe ser un objeto, no {type(data).__name__}")
                continue
            
            if 'usuarios' not in data:
                print(f"     ❌ Error: El JSON no contiene la clave 'usuarios'")
                continue
            
            if not isinstance(data.get('usuarios'), list):
                print(f"     ❌ Error: 'usuarios' debe ser una lista")
                continue
            
            # Detectar tipo en el primer archivo
            if tipo_detectado is None:
                tipo_detectado = detectar_tipo_json(data)
                print(f"     ℹ️ Tipo detectado: {tipo_detectado.upper()}")
            
            numFactura = data.get('numFactura', '')
            numDocumentoIdObligado = data.get('numDocumentoIdObligado', '')
            archivoOrigen = nombre_archivo
            
            usuarios_list = data.get('usuarios', [])
            estadisticas['total_usuarios'] += len(usuarios_list)
            
            # Procesar cada usuario
            for user in usuarios_list:
                numDocUsuario = normalizar_documento(user.get('numDocumentoIdentificacion', ''))
                tipoDocUsuario = user.get('tipoDocumentoIdentificacion', '')
                fechaNac = user.get('fechaNacimiento', '')
                
                # Calcular edad
                edad = None
                try:
                    if fechaNac:
                        birth = datetime.strptime(fechaNac, "%Y-%m-%d")
                        edad = cutoff_date.year - birth.year - ((cutoff_date.month, cutoff_date.day) < (birth.month, birth.day))
                except:
                    pass
                
                servicios = user.get('servicios', {})
                
                # Procesar CONSULTAS
                consultas = servicios.get('consultas', [])
                estadisticas['total_consultas'] += len(consultas)
                for consulta in consultas:
                    consultas_data.append({
                        'archivoOrigen': archivoOrigen,
                        'numFactura': numFactura,
                        'numDocumento_usuario': numDocUsuario,
                        'tipoDocumento_usuario': tipoDocUsuario,
                        'consecutivo': consulta.get('consecutivo', ''),
                        'codPrestador': normalizar_documento(consulta.get('codPrestador', '')),
                        'fechaInicioAtencion': consulta.get('fechaInicioAtencion', ''),
                        'numAutorizacion': consulta.get('numAutorizacion', ''),
                        'codConsulta': consulta.get('codConsulta', ''),
                        'modalidadGrupoServicioTecSal': consulta.get('modalidadGrupoServicioTecSal', ''),
                        'grupoServicios': consulta.get('grupoServicios', ''),
                        'codServicio': consulta.get('codServicio', ''),
                        'finalidadTecnologiaSalud': consulta.get('finalidadTecnologiaSalud', ''),
                        'causaMotivoAtencion': consulta.get('causaMotivoAtencion', ''),
                        'codDiagnosticoPrincipal': consulta.get('codDiagnosticoPrincipal', ''),
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
                
                # Procesar PROCEDIMIENTOS
                procedimientos = servicios.get('procedimientos', [])
                estadisticas['total_procedimientos'] += len(procedimientos)
                for proc in procedimientos:
                    procedimientos_data.append({
                        'archivoOrigen': archivoOrigen,
                        'numFactura': numFactura,
                        'numDocumento_usuario': numDocUsuario,
                        'tipoDocumento_usuario': tipoDocUsuario,
                        'consecutivo': proc.get('consecutivo', ''),
                        'codPrestador': normalizar_documento(proc.get('codPrestador', '')),
                        'fechaInicioAtencion': proc.get('fechaInicioAtencion', ''),
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
                        'codDiagnosticoPrincipal': proc.get('codDiagnosticoPrincipal', ''),
                        'codDiagnosticoRelacionado': proc.get('codDiagnosticoRelacionado', ''),
                        'codComplicacion': proc.get('codComplicacion', ''),
                        'vrServicio': proc.get('vrServicio', 0),
                        'conceptoRecaudo': proc.get('conceptoRecaudo', ''),
                        'valorPagoModerador': proc.get('valorPagoModerador', 0),
                        'numFEVPagoModerador': proc.get('numFEVPagoModerador', '')
                    })
                
                # Procesar MEDICAMENTOS
                medicamentos = servicios.get('medicamentos', [])
                estadisticas['total_medicamentos'] += len(medicamentos)
                for med in medicamentos:
                        medicamentos_data.append({
                            'archivoOrigen': archivoOrigen,
                            'numFactura': numFactura,
                            'numDocumento_usuario': numDocUsuario,
                            'tipoDocumento_usuario': tipoDocUsuario,
                            'consecutivo': med.get('consecutivo', ''),
                            'codPrestador': normalizar_documento(med.get('codPrestador', '')),
                            'fechaDispensAdmon': med.get('fechaDispensAdmon', ''),
                            'idMIPRES': med.get('idMIPRES', ''),
                            'numAutorizacion': med.get('numAutorizacion', ''),
                            'codTecnologiaSalud': med.get('codTecnologiaSalud', ''),
                            'nomTecnologiaSalud': med.get('nomTecnologiaSalud', ''),
                            'tipoMedicamento': med.get('tipoMedicamento', ''),
                            'concentracionMedicamento': med.get('concentracionMedicamento', ''),
                            'unidadMedida': med.get('unidadMedida', ''),
                            'formaFarmaceutica': med.get('formaFarmaceutica', ''),
                            'unidadMinDispensa': med.get('unidadMinDispensa', ''),
                            'cantidadMedicamento': med.get('cantidadMedicamento', 0),
                            'diasTratamiento': med.get('diasTratamiento', 0),
                            'tipoDocumentoIdentificacion_profesional': med.get('tipoDocumentoIdentificacion', ''),
                            'numDocumentoIdentificacion_profesional': normalizar_documento(med.get('numDocumentoIdentificacion', '')),
                            'codDiagnosticoPrincipal': med.get('codDiagnosticoPrincipal', ''),
                            'codDiagnosticoRelacionado': med.get('codDiagnosticoRelacionado', ''),
                            'vrUnitMedicamento': med.get('vrUnitMedicamento', 0),
                            'vrServicio': med.get('vrServicio', 0),
                            'conceptoRecaudo': med.get('conceptoRecaudo', ''),
                            'valorPagoModerador': med.get('valorPagoModerador', 0),
                            'numFEVPagoModerador': med.get('numFEVPagoModerador', '')
                        })
                
                # Procesar OTROS SERVICIOS
                otros_servicios = servicios.get('otrosServicios', [])
                estadisticas['total_otros_servicios'] += len(otros_servicios)
                for otro in otros_servicios:
                        otros_servicios_data.append({
                            'archivoOrigen': archivoOrigen,
                            'numFactura': numFactura,
                            'numDocumento_usuario': numDocUsuario,
                            'tipoDocumento_usuario': tipoDocUsuario,
                            'consecutivo': otro.get('consecutivo', ''),
                            'codPrestador': normalizar_documento(otro.get('codPrestador', '')),
                            'fechaSuministroTecnologia': otro.get('fechaSuministroTecnologia', ''),
                            'idMIPRES': otro.get('idMIPRES', ''),
                            'numAutorizacion': otro.get('numAutorizacion', ''),
                            'codTecnologiaSalud': otro.get('codTecnologiaSalud', ''),
                            'nomTecnologiaSalud': otro.get('nomTecnologiaSalud', ''),
                            'tipoOS': otro.get('tipoOS', ''),
                            'cantidadOS': otro.get('cantidadOS', 0),
                            'tipoDocumentoIdentificacion_profesional': otro.get('tipoDocumentoIdentificacion', ''),
                            'numDocumentoIdentificacion_profesional': normalizar_documento(otro.get('numDocumentoIdentificacion', '')),
                            'codDiagnosticoPrincipal': otro.get('codDiagnosticoPrincipal', ''),
                            'codDiagnosticoRelacionado': otro.get('codDiagnosticoRelacionado', ''),
                            'vrUnitOS': otro.get('vrUnitOS', 0),
                            'vrServicio': otro.get('vrServicio', 0),
                            'conceptoRecaudo': otro.get('conceptoRecaudo', ''),
                            'valorPagoModerador': otro.get('valorPagoModerador', 0),
                            'numFEVPagoModerador': otro.get('numFEVPagoModerador', '')
                        })
                
                # Procesar URGENCIAS
                urgencias = servicios.get('urgencias', [])
                estadisticas['total_urgencias'] += len(urgencias)
                for urg in urgencias:
                        urgencias_data.append({
                            'archivoOrigen': archivoOrigen,
                            'numFactura': numFactura,
                            'numDocumento_usuario': numDocUsuario,
                            'tipoDocumento_usuario': tipoDocUsuario,
                            'consecutivo': urg.get('consecutivo', ''),
                            'codPrestador': normalizar_documento(urg.get('codPrestador', '')),
                            'fechaInicioAtencion': urg.get('fechaInicioAtencion', ''),
                            'causaMotivoAtencion': urg.get('causaMotivoAtencion', ''),
                            'codDiagnosticoPrincipal': urg.get('codDiagnosticoPrincipal', ''),
                            'codDiagnosticoPrincipalE': urg.get('codDiagnosticoPrincipalE', ''),
                            'codDiagnosticoRelacionado1': urg.get('codDiagnosticoRelacionado1', ''),
                            'codDiagnosticoRelacionado2': urg.get('codDiagnosticoRelacionado2', ''),
                            'codDiagnosticoRelacionado3': urg.get('codDiagnosticoRelacionado3', ''),
                            'condicionDestinoUsuarioEgreso': urg.get('condicionDestinoUsuarioEgreso', ''),
                            'codDiagnosticoCausaMuerte': urg.get('codDiagnosticoCausaMuerte', ''),
                            'fechaEgreso': urg.get('fechaEgreso', ''),
                            'vrServicio': urg.get('vrServicio', 0),
                            'conceptoRecaudo': urg.get('conceptoRecaudo', ''),
                            'valorPagoModerador': urg.get('valorPagoModerador', 0),
                            'numFEVPagoModerador': urg.get('numFEVPagoModerador', '')
                        })
                
                # Procesar HOSPITALIZACIÓN
                hospitalizacion = servicios.get('hospitalizacion', [])
                estadisticas['total_hospitalizacion'] += len(hospitalizacion)
                for hosp in hospitalizacion:
                        hospitalizacion_data.append({
                            'archivoOrigen': archivoOrigen,
                            'numFactura': numFactura,
                            'numDocumento_usuario': numDocUsuario,
                            'tipoDocumento_usuario': tipoDocUsuario,
                            'consecutivo': hosp.get('consecutivo', ''),
                            'codPrestador': normalizar_documento(hosp.get('codPrestador', '')),
                            'viaIngresoServicioSalud': hosp.get('viaIngresoServicioSalud', ''),
                            'fechaInicioAtencion': hosp.get('fechaInicioAtencion', ''),
                            'numAutorizacion': hosp.get('numAutorizacion', ''),
                            'causaMotivoAtencion': hosp.get('causaMotivoAtencion', ''),
                            'codDiagnosticoPrincipal': hosp.get('codDiagnosticoPrincipal', ''),
                            'codDiagnosticoPrincipalE': hosp.get('codDiagnosticoPrincipalE', ''),
                            'codDiagnosticoRelacionado1': hosp.get('codDiagnosticoRelacionado1', ''),
                            'codDiagnosticoRelacionado2': hosp.get('codDiagnosticoRelacionado2', ''),
                            'codDiagnosticoRelacionado3': hosp.get('codDiagnosticoRelacionado3', ''),
                            'codComplicacion': hosp.get('codComplicacion', ''),
                            'condicionDestinoUsuarioEgreso': hosp.get('condicionDestinoUsuarioEgreso', ''),
                            'codDiagnosticoCausaMuerte': hosp.get('codDiagnosticoCausaMuerte', ''),
                            'fechaEgreso': hosp.get('fechaEgreso', ''),
                            'vrServicio': hosp.get('vrServicio', 0),
                            'conceptoRecaudo': hosp.get('conceptoRecaudo', ''),
                            'valorPagoModerador': hosp.get('valorPagoModerador', 0),
                            'numFEVPagoModerador': hosp.get('numFEVPagoModerador', '')
                        })
                
                # Procesar RECIÉN NACIDOS
                if tipo_detectado == 'compuestos':
                    recien_nacidos = servicios.get('recienNacidos', [])
                    estadisticas['total_recien_nacidos'] += len(recien_nacidos)
                    for rn in recien_nacidos:
                        recien_nacidos_data.append({
                            'archivoOrigen': archivoOrigen,
                            'numFactura': numFactura,
                            'numDocumento_usuario': numDocUsuario,
                            'tipoDocumento_usuario': tipoDocUsuario,
                            'consecutivo': rn.get('consecutivo', ''),
                            'codPrestador': normalizar_documento(rn.get('codPrestador', '')),
                            'fechaNacimiento': rn.get('fechaNacimiento', ''),
                            'edadGestacional': rn.get('edadGestacional', ''),
                            'numConsultasCPrenatal': rn.get('numConsultasCPrenatal', ''),
                            'codSexoBiologico': rn.get('codSexoBiologico', ''),
                            'peso': rn.get('peso', 0),
                            'codDiagnosticoPrincipal': rn.get('codDiagnosticoPrincipal', ''),
                            'condicionDestinoUsuarioEgreso': rn.get('condicionDestinoUsuarioEgreso', ''),
                            'codDiagnosticoCausaMuerte': rn.get('codDiagnosticoCausaMuerte', ''),
                            'fechaEgreso': rn.get('fechaEgreso', ''),
                            'vrServicio': rn.get('vrServicio', 0),
                            'conceptoRecaudo': rn.get('conceptoRecaudo', ''),
                            'valorPagoModerador': rn.get('valorPagoModerador', 0),
                            'numFEVPagoModerador': rn.get('numFEVPagoModerador', '')
                        })
                
                # Agregar datos del usuario (al final para incluir resúmenes)
                usuarios_data.append({
                    'archivoOrigen': archivoOrigen,
                    'numFactura': numFactura,
                    'numDocumentoIdObligado': numDocumentoIdObligado,
                    'numDocumentoIdentificacion': numDocUsuario,
                    'tipoDocumentoIdentificacion': tipoDocUsuario,
                    'tipoUsuario': user.get('tipoUsuario', ''),
                    'fechaNacimiento': fechaNac,
                    'edad_calculada': edad,
                    'codSexo': user.get('codSexo', ''),
                    'codPaisResidencia': user.get('codPaisResidencia', ''),
                    'codMunicipioResidencia': user.get('codMunicipioResidencia', ''),
                    'codZonaTerritorialResidencia': user.get('codZonaTerritorialResidencia', ''),
                    'incapacidad': user.get('incapacidad', ''),
                    'codPaisOrigen': user.get('codPaisOrigen', ''),
                    'consecutivo': user.get('consecutivo', '')
                })
            
            estadisticas['archivos_procesados'] += 1
            print(f"     ✓ {len(usuarios_list)} usuarios procesados")
            
        except json.JSONDecodeError as je:
            print(f"     ❌ Error al parsear JSON: {str(je)}")
            continue
        except KeyError as ke:
            print(f"     ❌ Error: Falta clave requerida: {str(ke)}")
            continue
        except Exception as e:
            print(f"     ❌ Error inesperado: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # Validar que se haya procesado al menos un archivo exitosamente
    if estadisticas['archivos_procesados'] == 0:
        print(f"\n  ❌ ERROR: No se pudo procesar ningún archivo")
        return None, None, estadisticas
    
    # Crear DataFrames
    print(f"\n  📊 Generando Excel...")
    df_usuarios = pd.DataFrame(usuarios_data)
    df_consultas = pd.DataFrame(consultas_data)
    df_procedimientos = pd.DataFrame(procedimientos_data)
    df_medicamentos = pd.DataFrame(medicamentos_data)
    df_otros_servicios = pd.DataFrame(otros_servicios_data)
    df_urgencias = pd.DataFrame(urgencias_data)
    df_hospitalizacion = pd.DataFrame(hospitalizacion_data)
    df_recien_nacidos = pd.DataFrame(recien_nacidos_data)
    
    # Validar que haya al menos una hoja con datos
    tiene_datos = (not df_usuarios.empty or not df_consultas.empty or 
                   not df_procedimientos.empty or not df_medicamentos.empty or
                   not df_otros_servicios.empty or not df_urgencias.empty or
                   not df_hospitalizacion.empty or not df_recien_nacidos.empty)
    
    if not tiene_datos:
        print(f"\n  ❌ ERROR: No se encontraron datos válidos en los archivos JSON")
        return None, None, estadisticas
    
    # Exportar a Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hojas comunes a todos los tipos
        if not df_usuarios.empty:
            df_usuarios.to_excel(writer, sheet_name='Usuarios', index=False)
        if not df_consultas.empty:
            df_consultas.to_excel(writer, sheet_name='Consultas', index=False)
        if not df_procedimientos.empty:
            df_procedimientos.to_excel(writer, sheet_name='Procedimientos', index=False)
        
        # Hojas adicionales para BC y Compuestos
        if not df_medicamentos.empty:
            df_medicamentos.to_excel(writer, sheet_name='Medicamentos', index=False)
        if not df_otros_servicios.empty:
            df_otros_servicios.to_excel(writer, sheet_name='OtrosServicios', index=False)
        if not df_urgencias.empty:
            df_urgencias.to_excel(writer, sheet_name='Urgencias', index=False)
        if not df_hospitalizacion.empty:
            df_hospitalizacion.to_excel(writer, sheet_name='Hospitalizacion', index=False)
        
        # Hoja adicional solo para Compuestos
        if tipo_detectado == 'compuestos':
            if not df_recien_nacidos.empty:
                df_recien_nacidos.to_excel(writer, sheet_name='RecienNacidos', index=False)
    
    output.seek(0)
    
    # Mostrar estadísticas
    print(f"\n  ✅ Excel generado exitosamente")
    print(f"     📈 Estadísticas:")
    print(f"        • Archivos: {estadisticas['archivos_procesados']}")
    print(f"        • Usuarios: {estadisticas['total_usuarios']}")
    print(f"        • Consultas: {estadisticas['total_consultas']}")
    print(f"        • Procedimientos: {estadisticas['total_procedimientos']}")
    print(f"        • Medicamentos: {estadisticas['total_medicamentos']}")
    print(f"        • Otros Servicios: {estadisticas['total_otros_servicios']}")
    print(f"        • Urgencias: {estadisticas['total_urgencias']}")
    print(f"        • Hospitalización: {estadisticas['total_hospitalizacion']}")
    if tipo_detectado == 'compuestos':
        print(f"        • Recién Nacidos: {estadisticas['total_recien_nacidos']}")
    print(f"{'='*60}\n")
    
    return output, tipo_detectado, estadisticas
