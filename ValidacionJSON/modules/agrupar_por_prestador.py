import json
from collections import defaultdict
from pathlib import Path

def agrupar_usuarios_por_prestador(input_file, output_dir):
    """
    Agrupa usuarios y sus servicios por codPrestador.
    Cada codPrestador generará un archivo JSON separado.
    """
    
    # Leer el archivo JSON original
    print(f"Leyendo archivo: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
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
    for usuario in data.get('usuarios', []):
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
        for seccion in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion']:
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
            for seccion in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 'urgencias', 'hospitalizacion']:
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
    
    # Crear directorio de salida si no existe
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Guardar un archivo JSON por cada prestador
    print(f"\nGenerando archivos JSON por prestador...")
    for cod_prestador, datos in prestadores.items():
        output_file = output_path / f"{cod_prestador}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        num_usuarios = len(datos['usuarios'])
        print(f"  - {output_file.name}: {num_usuarios} usuario(s)")
    
    print(f"\n✓ Proceso completado. Se generaron {len(prestadores)} archivo(s) en: {output_dir}")
    return prestadores, conteo_prestadores


if __name__ == "__main__":
    # Configuración de rutas
    input_file = "input/72763_101_2275.json"
    output_dir = "output"
    
    try:
        prestadores, conteo_prestadores = agrupar_usuarios_por_prestador(input_file, output_dir)
        
        # Crear tabla con resumen de apariciones de codPrestador por archivo
        print(f"\n{'='*80}")
        print(f"{'RESUMEN DE APARICIONES DE codPrestador POR ARCHIVO':^80}")
        print(f"{'='*80}")
        print(f"{'Archivo':<40} | {'Apariciones':>12} | {'Usuarios':>10}")
        print(f"{'-'*40}-+-{'-'*12}-+-{'-'*10}")
        
        # Ordenar por cantidad de apariciones (descendente)
        prestadores_ordenados = sorted(
            conteo_prestadores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_apariciones = 0
        total_usuarios = 0
        for cod_prestador, num_apariciones in prestadores_ordenados:
            total_apariciones += num_apariciones
            num_usuarios = len(prestadores[cod_prestador]['usuarios'])
            total_usuarios += num_usuarios
            archivo = f"{cod_prestador}.json"
            print(f"{archivo:<40} | {num_apariciones:>12,} | {num_usuarios:>10,}")
        
        print(f"{'-'*40}-+-{'-'*12}-+-{'-'*10}")
        print(f"{'TOTAL':<40} | {total_apariciones:>12,} | {total_usuarios:>10,}")
        print(f"{'='*80}")
        print(f"\nTotal de prestadores únicos: {len(prestadores)}")
        
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{input_file}'")
        print("Asegúrate de que el archivo JSON esté en la carpeta 'input'")
    except json.JSONDecodeError as e:
        print(f"Error al leer el JSON: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")
