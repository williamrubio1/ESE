"""
Módulo Separador JSON: Agrupa usuarios y servicios por codPrestador
Genera múltiples archivos JSON (uno por prestador)
"""

import json
from collections import defaultdict
from io import BytesIO
import zipfile

def separar_por_prestador(json_file):
    """
    Agrupa usuarios y sus servicios por codPrestador.
    
    Args:
        json_file: Archivo JSON cargado
    
    Returns:
        tuple: (archivo ZIP en memoria, datos de la tabla de resumen)
    """
    
    print("=" * 80)
    print("Separador JSON: Agrupando por codPrestador")
    print("=" * 80)
    
    try:
        # Leer el archivo JSON
        if hasattr(json_file, 'read'):
            content = json_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
        else:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        print(f"JSON cargado correctamente")
        
        # Estructura para almacenar datos agrupados por codPrestador
        prestadores = defaultdict(lambda: {
            'numDocumentoIdObligado': data.get('numDocumentoIdObligado'),
            'numFactura': data.get('numFactura'),
            'tipoNota': data.get('tipoNota'),
            'numNota': data.get('numNota'),
            'usuarios': []
        })
        
        # Contador de apariciones por prestador
        conteo_prestadores = defaultdict(int)
        
        # Procesar cada usuario
        total_usuarios = len(data.get('usuarios', []))
        print(f"Procesando {total_usuarios:,} usuarios...")
        
        for idx, usuario in enumerate(data.get('usuarios', []), 1):
            if idx % 100 == 0:
                print(f"   Usuario {idx:,}/{total_usuarios:,}")
            
            # Extraer información del usuario
            usuario_info = {
                'tipoDocumentoIdentificacion': usuario.get('tipoDocumentoIdentificacion'),
                'numDocumentoIdentificacion': usuario.get('numDocumentoIdentificacion'),
                'tipoUsuario': usuario.get('tipoUsuario'),
                'fechaNacimiento': usuario.get('fechaNacimiento'),
                'codSexo': usuario.get('codSexo'),
                'codPaisResidencia': usuario.get('codPaisResidencia'),
                'codMunicipioResidencia': usuario.get('codMunicipioResidencia'),
                'codZonaTerritorialResidencia': usuario.get('codZonaTerritorialResidencia'),
                'incapacidad': usuario.get('incapacidad'),
                'consecutivo': usuario.get('consecutivo'),
                'codPaisOrigen': usuario.get('codPaisOrigen')
            }
            
            servicios = usuario.get('servicios', {})
            
            # Obtener todos los codPrestador del usuario
            prestadores_usuario = set()
            
            # Buscar en cada sección de servicios
            for seccion in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos']:
                if seccion in servicios and servicios[seccion]:
                    for servicio in servicios[seccion]:
                        if 'codPrestador' in servicio:
                            prestadores_usuario.add(servicio['codPrestador'])
                            # Contar cada aparición del codPrestador
                            conteo_prestadores[servicio['codPrestador']] += 1
            
            # Para cada prestador del usuario, crear una copia del usuario con solo los servicios de ese prestador
            for cod_prestador in prestadores_usuario:
                # Crear una copia del usuario con servicios filtrados
                usuario_filtrado = usuario_info.copy()
                servicios_filtrados = {}
                
                # Filtrar servicios por prestador
                for seccion in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos']:
                    if seccion in servicios and servicios[seccion]:
                        servicios_seccion = [
                            s for s in servicios[seccion]
                            if s.get('codPrestador') == cod_prestador
                        ]
                        if servicios_seccion:
                            servicios_filtrados[seccion] = servicios_seccion
                
                usuario_filtrado['servicios'] = servicios_filtrados
                
                # Agregar usuario al prestador correspondiente
                prestadores[cod_prestador]['usuarios'].append(usuario_filtrado)
        
        print(f"Procesamiento completado: {len(prestadores)} prestadores encontrados")
        
        # Renumerar consecutivos de usuarios y servicios en cada prestador
        print(f"Renumerando consecutivos...")
        for cod_prestador, datos in prestadores.items():
            # Renumerar consecutivo de usuarios
            for idx_usuario, usuario in enumerate(datos['usuarios'], 1):
                usuario['consecutivo'] = idx_usuario
                
                # Renumerar consecutivos de servicios
                servicios = usuario.get('servicios', {})
                for seccion in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion', 'recienNacidos']:
                    if seccion in servicios and servicios[seccion]:
                        for idx_servicio, servicio in enumerate(servicios[seccion], 1):
                            servicio['consecutivo'] = idx_servicio
        
        print(f"Consecutivos renumerados correctamente")
        
        # Crear archivo ZIP en memoria con todos los JSON
        print(f"Generando archivo ZIP...")
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for cod_prestador, datos in prestadores.items():
                # Generar JSON con formato compacto en los corchetes de apertura
                # Usar separators para mantener formato: "key": value
                json_content = json.dumps(datos, ensure_ascii=False, indent=4)
                
                # Ajustar formato para coincidir con el original:
                import re
                # 1. Cambiar "[\n    {" por "[{"
                json_content = re.sub(r'\[\n +(\{)', r'[\1', json_content)
                # 2. Cambiar "},\n    {" por "}, {"
                json_content = re.sub(r'\},\n +(\{)', r'}, \1', json_content)
                
                # Agregar al ZIP
                filename = f"{cod_prestador}.json"
                zip_file.writestr(filename, json_content)
                
                num_usuarios = len(datos['usuarios'])
                print(f"   {filename}: {num_usuarios:,} usuario(s)")
        
        zip_buffer.seek(0)
        print(f"Archivo ZIP generado exitosamente")
        
        # Preparar datos de la tabla
        tabla_datos = []
        prestadores_ordenados = sorted(
            conteo_prestadores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_apariciones = 0
        total_usuarios_tabla = 0
        
        for cod_prestador, num_apariciones in prestadores_ordenados:
            total_apariciones += num_apariciones
            num_usuarios = len(prestadores[cod_prestador]['usuarios'])
            total_usuarios_tabla += num_usuarios
            
            tabla_datos.append({
                'archivo': f"{cod_prestador}.json",
                'codPrestador': cod_prestador,
                'apariciones': num_apariciones,
                'usuarios': num_usuarios
            })
        
        resumen = {
            'total_prestadores': len(prestadores),
            'total_apariciones': total_apariciones,
            'total_usuarios': total_usuarios_tabla,
            'tabla': tabla_datos
        }
        
        print(f"{'='*80}")
        print(f"Proceso completado exitosamente")
        print(f"{'='*80}")
        
        return zip_buffer, resumen
        
    except json.JSONDecodeError as e:
        print(f"ERROR al leer el JSON: {e}")
        raise ValueError(f"Error al leer el JSON: {e}")
    except Exception as e:
        print(f"ERROR inesperado: {e}")
        raise
