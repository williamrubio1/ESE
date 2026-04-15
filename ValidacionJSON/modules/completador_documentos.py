"""
Módulo centralizado para completar campos de identificación vacíos en RIPS-JSON.
Completa tipoDocumentoIdentificacion y numDocumentoIdentificacion en servicios.
Implementa estrategia de 4 niveles con caché de consistencia y archivo acumulativo de especialistas.
"""

import random
import copy
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

# Importar pandas solo si está disponible
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# ============================================================================
# GESTIÓN DEL ARCHIVO DE ESPECIALISTAS
# ============================================================================

def _obtener_ruta_especialistas() -> str:
    """Retorna la ruta del archivo especialistas.json"""
    # Obtener directorio del módulo actual
    modulo_dir = os.path.dirname(os.path.abspath(__file__))
    # Subir un nivel y entrar a data/
    data_dir = os.path.join(os.path.dirname(modulo_dir), 'data')
    # Asegurar que existe el directorio
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'especialistas.json')


def _cargar_especialistas() -> Dict[str, Any]:
    """
    Carga el archivo de especialistas acumulativo.
    Si no existe o está corrupto, retorna diccionario vacío.
    
    Estructura esperada:
    {
        "12345678": {
            "tipoDocumento": "CC",
            "contextos": [{
                "prestador": "501100063411",
                "servicios": ["consultas", "urgencias"],
                "veces_visto": 10,
                "ultima_vez": "2025-12-07"
            }]
        }
    }
    """
    filepath = _obtener_ruta_especialistas()
    
    if not os.path.exists(filepath):
        print(f"📋 Creando nuevo archivo de especialistas: {filepath}", flush=True)
        _guardar_especialistas({})
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validar estructura básica
        if not isinstance(data, dict):
            print(f"⚠️  Archivo de especialistas corrupto, reiniciando", flush=True)
            return {}
        
        print(f"📚 Especialistas cargados: {len(data)} profesionales en base de datos", flush=True)
        return data
        
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️  Error leyendo especialistas: {e}. Reiniciando archivo.", flush=True)
        return {}


def _guardar_especialistas(data: Dict[str, Any]) -> bool:
    """Guarda el diccionario de especialistas en el archivo JSON"""
    filepath = _obtener_ruta_especialistas()
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"❌ Error guardando especialistas: {e}", flush=True)
        return False


def _limpiar_especialistas_antiguos(especialistas: Dict[str, Any], meses_antiguedad: int = 6) -> Tuple[Dict[str, Any], int]:
    """
    Elimina especialistas que no han sido vistos en más de N meses.
    Retorna el diccionario limpio y contador de eliminados.
    """
    fecha_limite = datetime.now() - timedelta(days=meses_antiguedad * 30)
    especialistas_limpios = {}
    eliminados = 0
    
    for doc, info in especialistas.items():
        # Filtrar contextos antiguos
        contextos_validos = []
        for contexto in info.get('contextos', []):
            try:
                ultima_vez = datetime.fromisoformat(contexto.get('ultima_vez', '2000-01-01'))
                if ultima_vez >= fecha_limite:
                    contextos_validos.append(contexto)
            except (ValueError, TypeError):
                # Si fecha inválida, mantener el contexto
                contextos_validos.append(contexto)
        
        # Si quedan contextos válidos, mantener el especialista
        if contextos_validos:
            especialistas_limpios[doc] = {
                'tipoDocumento': info.get('tipoDocumento', 'CC'),
                'contextos': contextos_validos
            }
        else:
            eliminados += 1
    
    if eliminados > 0:
        print(f"🧹 Limpieza: {eliminados} especialistas sin actividad en {meses_antiguedad} meses eliminados", flush=True)
    
    return especialistas_limpios, eliminados


def _actualizar_especialistas_desde_json(datos_json: Dict[str, Any], especialistas: Dict[str, Any]) -> Tuple[Dict[str, Any], int, int]:
    """
    Actualiza el diccionario de especialistas con los datos del JSON actual.
    Retorna el diccionario actualizado y contador de cambios.
    """
    nuevos = 0
    actualizados = 0
    fecha_hoy = datetime.now().isoformat()[:10]  # YYYY-MM-DD
    
    usuarios = datos_json.get('usuarios', [])
    
    for usuario in usuarios:
        servicios = usuario.get('servicios', {})
        
        for tipo_servicio in ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios',
                              'urgencias', 'hospitalizacion', 'recienNacidos']:
            lista_servicios = servicios.get(tipo_servicio, [])
            
            for servicio in lista_servicios:
                tipo_doc = str(servicio.get('tipoDocumentoIdentificacion', '')).strip()
                num_doc = str(servicio.get('numDocumentoIdentificacion', '')).strip()
                cod_prestador = str(servicio.get('codPrestador', '')).strip()
                
                # Solo procesar si documento y prestador NO están vacíos
                if not es_valor_vacio(num_doc) and not es_valor_vacio(cod_prestador):
                    # Crear entrada si no existe
                    if num_doc not in especialistas:
                        especialistas[num_doc] = {
                            'tipoDocumento': tipo_doc if tipo_doc else 'CC',
                            'contextos': []
                        }
                        nuevos += 1
                    
                    # Buscar contexto existente
                    contexto_existente = None
                    for ctx in especialistas[num_doc]['contextos']:
                        if ctx['prestador'] == cod_prestador:
                            contexto_existente = ctx
                            break
                    
                    if contexto_existente:
                        # Actualizar contexto existente
                        if tipo_servicio not in contexto_existente['servicios']:
                            contexto_existente['servicios'].append(tipo_servicio)
                        contexto_existente['veces_visto'] += 1
                        contexto_existente['ultima_vez'] = fecha_hoy
                        actualizados += 1
                    else:
                        # Crear nuevo contexto
                        especialistas[num_doc]['contextos'].append({
                            'prestador': cod_prestador,
                            'servicios': [tipo_servicio],
                            'veces_visto': 1,
                            'ultima_vez': fecha_hoy
                        })
                        actualizados += 1
    
    if nuevos > 0 or actualizados > 0:
        print(f"📊 Especialistas actualizados: {nuevos} nuevos, {actualizados} actualizaciones", flush=True)
    
    return especialistas, nuevos, actualizados


def es_valor_vacio(valor: Any) -> bool:
    """
    Verifica si un valor está vacío o es nulo (incluyendo casos especiales).
    
    Args:
        valor: Valor a verificar
    
    Returns:
        True si el valor está vacío, False en caso contrario
    """
    if valor is None:
        return True
    
    if PANDAS_AVAILABLE and pd.isna(valor):
        return True
    
    # Convertir a string y limpiar
    valor_str = str(valor).strip()
    
    # Casos considerados vacíos
    if valor_str == '' or valor_str == '0' or valor_str.lower() in ['nan', 'none', 'null']:
        return True
    
    return False


def _validar_estructura_json(datos: Dict[str, Any]) -> bool:
    """
    Valida que el JSON tenga la estructura esperada antes de procesar.
    
    Returns:
        True si la estructura es válida, False en caso contrario
    """
    if not isinstance(datos, dict):
        return False
    
    if 'usuarios' not in datos:
        return False
    
    if not isinstance(datos['usuarios'], list):
        return False
    
    return True


def _construir_tablas_profesionales(datos: Dict[str, Any]) -> Tuple[Dict, Dict, Dict, set]:
    """
    Construye tablas temporales para mapeo de profesionales en diferentes niveles.
    
    Returns:
        tuple: (tabla_nivel1, tabla_nivel2, tabla_nivel3, profesionales_globales)
        - tabla_nivel1: {usuario: {prestador: {tipo_servicio: [profesionales]}}}
        - tabla_nivel2: {usuario: {prestador: [profesionales]}} (sin filtrar por tipo)
        - tabla_nivel3: {usuario: [profesionales]} (sin filtrar por prestador)
        - profesionales_globales: set con TODOS los profesionales disponibles en el JSON
    """
    tabla_nivel1 = {}  # Estricto: usuario → prestador → tipo_servicio → profesionales
    tabla_nivel2 = {}  # Medio: usuario → prestador → profesionales
    tabla_nivel3 = {}  # Flexible: usuario → profesionales (todos)
    profesionales_globales = set()  # Set global de TODOS los profesionales
    
    tipos_servicios = ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 
                       'urgencias', 'hospitalizacion', 'recienNacidos']
    
    usuarios = datos.get('usuarios', [])
    
    for idx_usuario, usuario in enumerate(usuarios):
        # Usar índice como fallback si el documento está vacío
        usuario_doc = usuario.get('numDocumentoIdentificacion', '')
        if es_valor_vacio(usuario_doc):
            usuario_doc = f'USUARIO_{idx_usuario}'
        else:
            usuario_doc = str(usuario_doc).strip()
        
        # Inicializar tablas para este usuario
        if usuario_doc not in tabla_nivel1:
            tabla_nivel1[usuario_doc] = {}
            tabla_nivel2[usuario_doc] = {}
            tabla_nivel3[usuario_doc] = []
        
        # Validar que servicios exista y sea dict
        servicios = usuario.get('servicios')
        if not isinstance(servicios, dict):
            continue
        
        # Procesar cada tipo de servicio
        for tipo_servicio in tipos_servicios:
            lista_servicios = servicios.get(tipo_servicio)
            
            # Validar que sea lista
            if not isinstance(lista_servicios, list):
                continue
            
            for servicio in lista_servicios:
                if not isinstance(servicio, dict):
                    continue
                
                cod_prestador = servicio.get('codPrestador', '')
                if es_valor_vacio(cod_prestador):
                    continue  # Saltar servicios sin prestador válido
                
                cod_prestador = str(cod_prestador).strip()
                
                num_doc_profesional = servicio.get('numDocumentoIdentificacion', '')
                
                # Solo agregar profesionales con documento NO vacío
                if not es_valor_vacio(num_doc_profesional):
                    num_doc_profesional = str(num_doc_profesional).strip()
                    
                    # NIVEL 1: Tabla estricta (usuario → prestador → tipo_servicio)
                    if cod_prestador not in tabla_nivel1[usuario_doc]:
                        tabla_nivel1[usuario_doc][cod_prestador] = {}
                    
                    if tipo_servicio not in tabla_nivel1[usuario_doc][cod_prestador]:
                        tabla_nivel1[usuario_doc][cod_prestador][tipo_servicio] = []
                    
                    if num_doc_profesional not in tabla_nivel1[usuario_doc][cod_prestador][tipo_servicio]:
                        tabla_nivel1[usuario_doc][cod_prestador][tipo_servicio].append(num_doc_profesional)
                    
                    # NIVEL 2: Tabla media (usuario → prestador)
                    if cod_prestador not in tabla_nivel2[usuario_doc]:
                        tabla_nivel2[usuario_doc][cod_prestador] = []
                    
                    if num_doc_profesional not in tabla_nivel2[usuario_doc][cod_prestador]:
                        tabla_nivel2[usuario_doc][cod_prestador].append(num_doc_profesional)
                    
                    # NIVEL 3: Tabla flexible (usuario → todos)
                    if num_doc_profesional not in tabla_nivel3[usuario_doc]:
                        tabla_nivel3[usuario_doc].append(num_doc_profesional)
                    
                    # Agregar a set global de profesionales
                    profesionales_globales.add(num_doc_profesional)
    
    return tabla_nivel1, tabla_nivel2, tabla_nivel3, profesionales_globales


def _buscar_en_especialistas_nivel4(cod_prestador: str, tipo_servicio: str, 
                                    especialistas: Dict[str, Any], 
                                    profesionales_ya_usados: Dict[str, set]) -> Tuple[Optional[str], Optional[str]]:
    """
    Nivel 4 (archivo histórico): Busca en el archivo de especialistas.
    
    Estrategia conservadora:
    1. Buscar profesionales que hayan atendido ese prestador + tipo_servicio
    2. Priorizar profesionales que NO estén ya asignados en otro prestador
    3. Si hay múltiples opciones, seleccionar uno al azar
    
    Returns:
        tuple: (num_doc_profesional, fuente) o (None, None)
    """
    candidatos = []
    
    # Primero: Buscar por prestador + tipo_servicio exacto
    for num_doc, info in especialistas.items():
        for contexto in info.get('contextos', []):
            if contexto['prestador'] == cod_prestador:
                if tipo_servicio in contexto.get('servicios', []):
                    # Verificar que no esté usado en otro prestador
                    if num_doc not in profesionales_ya_usados:
                        candidatos.append((num_doc, 'Archivo histórico (mismo prestador + servicio)'))
    
    if candidatos:
        seleccionado = random.choice(candidatos)
        return seleccionado
    
    # Fallback: Buscar solo por prestador (sin filtrar por tipo de servicio)
    candidatos_prestador = []
    for num_doc, info in especialistas.items():
        for contexto in info.get('contextos', []):
            if contexto['prestador'] == cod_prestador:
                if num_doc not in profesionales_ya_usados:
                    candidatos_prestador.append((num_doc, 'Archivo histórico (mismo prestador)'))
    
    if candidatos_prestador:
        seleccionado = random.choice(candidatos_prestador)
        return seleccionado
    
    # No se encontró ningún candidato válido
    return None, None


def _obtener_profesional_con_cache(usuario_doc: str, cod_prestador: str, tipo_servicio: str,
                                   tabla_nivel1: Dict, tabla_nivel2: Dict, tabla_nivel3: Dict,
                                   profesionales_globales: set,
                                   especialistas: Dict[str, Any],
                                   cache_asignaciones: Dict, profesionales_asignados: Dict,
                                   fuentes_asignacion: Dict) -> Optional[str]:
    """
    Obtiene un profesional apropiado usando estrategia de 5 niveles con caché.
    
    Args:
        usuario_doc: Documento del usuario
        cod_prestador: Código del prestador
        tipo_servicio: Tipo de servicio (consultas, medicamentos, etc.)
        tabla_nivel1: Tabla estricta
        tabla_nivel2: Tabla media
        tabla_nivel3: Tabla flexible
        profesionales_globales: Set global de todos los profesionales
        especialistas: Diccionario de especialistas del archivo histórico
        cache_asignaciones: Caché de decisiones previas
        profesionales_asignados: Tracking de profesional → prestadores asignados
        fuentes_asignacion: Dict para guardar la fuente de cada asignación
    
    Returns:
        Documento del profesional o None si no se encuentra
    """
    # Clave para caché y fuente
    clave = (usuario_doc, cod_prestador, tipo_servicio)
    
    if clave in cache_asignaciones:
        return cache_asignaciones[clave]
    
    profesionales_disponibles = []
    fuente = None
    
    # NIVEL 1: Intentar búsqueda estricta (usuario + prestador + tipo_servicio)
    if (usuario_doc in tabla_nivel1 and 
        cod_prestador in tabla_nivel1[usuario_doc] and
        tipo_servicio in tabla_nivel1[usuario_doc][cod_prestador]):
        profesionales_disponibles = tabla_nivel1[usuario_doc][cod_prestador][tipo_servicio]
        fuente = 'Nivel 1 (mismo usuario + prestador + servicio)'
    
    if profesionales_disponibles:
        profesional = random.choice(profesionales_disponibles)
        cache_asignaciones[clave] = profesional
        fuentes_asignacion[clave] = fuente
        
        # Registrar asignación
        if profesional not in profesionales_asignados:
            profesionales_asignados[profesional] = set()
        profesionales_asignados[profesional].add(cod_prestador)
        
        return profesional
    
    # NIVEL 2: Buscar en usuario + prestador (sin filtrar por tipo_servicio)
    if usuario_doc in tabla_nivel2 and cod_prestador in tabla_nivel2[usuario_doc]:
        profesionales_disponibles = tabla_nivel2[usuario_doc][cod_prestador]
        fuente = 'Nivel 2 (mismo usuario + prestador)'
    
    if profesionales_disponibles:
        profesional = random.choice(profesionales_disponibles)
        cache_asignaciones[clave] = profesional
        fuentes_asignacion[clave] = fuente
        
        if profesional not in profesionales_asignados:
            profesionales_asignados[profesional] = set()
        profesionales_asignados[profesional].add(cod_prestador)
        
        return profesional
    
    # NIVEL 3: Buscar en usuario (cualquier prestador)
    # Filtrar profesionales que NO estén ya asignados a otro prestador
    if usuario_doc in tabla_nivel3:
        # Priorizar profesionales que no están asignados a ningún prestador aún
        profesionales_sin_asignar = [
            p for p in tabla_nivel3[usuario_doc]
            if p not in profesionales_asignados or cod_prestador in profesionales_asignados[p]
        ]
        
        profesionales_disponibles = profesionales_sin_asignar if profesionales_sin_asignar else tabla_nivel3[usuario_doc]
        fuente = 'Nivel 3 (mismo usuario, cualquier prestador)'
    
    if profesionales_disponibles:
        profesional = random.choice(profesionales_disponibles)
        cache_asignaciones[clave] = profesional
        fuentes_asignacion[clave] = fuente
        
        if profesional not in profesionales_asignados:
            profesionales_asignados[profesional] = set()
        profesionales_asignados[profesional].add(cod_prestador)
        
        return profesional
    
    # NIVEL 4: Buscar en archivo histórico de especialistas
    profesional, fuente = _buscar_en_especialistas_nivel4(
        cod_prestador, tipo_servicio, especialistas, profesionales_asignados
    )
    
    if profesional:
        cache_asignaciones[clave] = profesional
        fuentes_asignacion[clave] = fuente
        
        if profesional not in profesionales_asignados:
            profesionales_asignados[profesional] = set()
        profesionales_asignados[profesional].add(cod_prestador)
        
        return profesional
    
    # NIVEL 5: Global Fallback - Usar cualquier profesional disponible
    # IMPORTANTE: Este nivel NO registra en especialistas.json para mantener integridad de datos
    if profesionales_globales:
        profesionales_disponibles = list(profesionales_globales)
        profesional = random.choice(profesionales_disponibles)
        fuente = 'Nivel 5 (Global Fallback - cualquier profesional)'
        
        cache_asignaciones[clave] = profesional
        fuentes_asignacion[clave] = fuente
        
        # Registrar en tracking pero NO actualizar especialistas.json
        if profesional not in profesionales_asignados:
            profesionales_asignados[profesional] = set()
        profesionales_asignados[profesional].add(cod_prestador)
        
        return profesional
    
    # No se encontró ningún profesional
    return None


def _detectar_cambios_documentos(datos_original: dict, datos_completados: dict, 
                                fuentes_asignacion: Dict) -> List[Dict]:
    """
    Detecta los cambios realizados en documentos de identificación.
    Incluye la fuente de cada asignación en el reporte.
    
    Returns:
        list: Lista de cambios realizados
    """
    cambios = []
    
    tipos_servicios = ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 
                       'urgencias', 'hospitalizacion', 'recienNacidos']
    
    usuarios_original = datos_original.get('usuarios', [])
    usuarios_completados = datos_completados.get('usuarios', [])
    
    for idx_usuario, usuario_original in enumerate(usuarios_original):
        if idx_usuario >= len(usuarios_completados):
            continue
        
        usuario_completado = usuarios_completados[idx_usuario]
        usuario_doc = usuario_completado.get('numDocumentoIdentificacion', '')
        if es_valor_vacio(usuario_doc):
            usuario_doc = f'USUARIO_{idx_usuario}'
        else:
            usuario_doc = str(usuario_doc).strip()
        
        servicios_original = usuario_original.get('servicios', {})
        servicios_completados = usuario_completado.get('servicios', {})
        
        for tipo_servicio in tipos_servicios:
            lista_original = servicios_original.get(tipo_servicio, [])
            lista_completada = servicios_completados.get(tipo_servicio, [])
            
            for idx_servicio, servicio_original in enumerate(lista_original):
                if idx_servicio >= len(lista_completada):
                    continue
                
                servicio_completado = lista_completada[idx_servicio]
                
                tipo_doc_antes = str(servicio_original.get('tipoDocumentoIdentificacion', '')).strip()
                tipo_doc_despues = str(servicio_completado.get('tipoDocumentoIdentificacion', '')).strip()
                
                num_doc_antes = str(servicio_original.get('numDocumentoIdentificacion', '')).strip()
                num_doc_despues = str(servicio_completado.get('numDocumentoIdentificacion', '')).strip()
                
                cod_prestador = str(servicio_completado.get('codPrestador', '')).strip()
                consecutivo = servicio_completado.get('consecutivo', idx_servicio + 1)
                
                # Detectar si hubo cambio
                cambio_tipo = tipo_doc_antes != tipo_doc_despues
                cambio_num = num_doc_antes != num_doc_despues
                
                if cambio_tipo or cambio_num:
                    # Buscar fuente de asignación
                    clave_fuente = (usuario_doc, cod_prestador, tipo_servicio)
                    fuente = fuentes_asignacion.get(clave_fuente, 'Desconocida')
                    
                    cambios.append({
                        'Usuario': usuario_doc,
                        'Tipo Servicio': tipo_servicio,
                        'Consecutivo': consecutivo,
                        'Prestador': cod_prestador,
                        'Tipo Doc Antes': tipo_doc_antes if tipo_doc_antes else '(vacío)',
                        'Tipo Doc Después': tipo_doc_despues,
                        'Num Doc Antes': num_doc_antes if num_doc_antes else '(vacío)',
                        'Num Doc Después': num_doc_despues,
                        'Fuente': fuente
                    })
    
    return cambios


def aplicar_completado_json(datos: Dict[str, Any], generar_reporte: bool = False) -> tuple:
    """
    Aplica el completado de documentos a todos los usuarios de un JSON RIPS.
    Implementa estrategia de 4 niveles con caché de consistencia y archivo acumulativo.
    
    Args:
        datos: Diccionario con la estructura completa del RIPS-JSON
        generar_reporte: Si True, retorna también la lista de cambios
    
    Returns:
        Si generar_reporte=False: JSON con todos los documentos completados
        Si generar_reporte=True: (JSON completado, lista de cambios)
    """
    print("=" * 60, flush=True)
    print("🔧 COMPLETADO DE DOCUMENTOS DE IDENTIFICACIÓN", flush=True)
    print("=" * 60, flush=True)
    
    # Validar estructura JSON
    if not _validar_estructura_json(datos):
        print("⚠️ Estructura JSON inválida, retornando sin cambios", flush=True)
        if generar_reporte:
            return datos, []
        return datos
    
    # Cargar archivo de especialistas
    especialistas = _cargar_especialistas()
    
    # Limpiar especialistas antiguos (> 6 meses sin actividad)
    especialistas, eliminados = _limpiar_especialistas_antiguos(especialistas, meses_antiguedad=6)
    
    # Actualizar especialistas con datos del JSON actual
    especialistas, nuevos, actualizados = _actualizar_especialistas_desde_json(datos, especialistas)
    
    # Guardar especialistas actualizados
    _guardar_especialistas(especialistas)
    
    # Crear copia profunda
    datos_completados = copy.deepcopy(datos)
    
    # Construir tablas de profesionales
    print("📊 Construyendo tablas de profesionales (3 niveles + global)...", flush=True)
    tabla_nivel1, tabla_nivel2, tabla_nivel3, profesionales_globales = _construir_tablas_profesionales(datos)
    
    total_profesionales = sum(len(profs) for profs in tabla_nivel3.values())
    print(f"   ✓ Tablas construidas: {len(tabla_nivel3)} usuarios, {total_profesionales} profesionales únicos", flush=True)
    print(f"   ✓ Pool global: {len(profesionales_globales)} profesionales disponibles", flush=True)
    
    # Inicializar cachés
    cache_asignaciones = {}  # (usuario, prestador, tipo) → profesional
    profesionales_asignados = {}  # profesional → {prestadores}
    fuentes_asignacion = {}  # (usuario, prestador, tipo) → fuente
    
    # Contadores
    cambios_tipo = 0
    cambios_num = 0
    no_completados_count = 0
    
    tipos_servicios = ['consultas', 'procedimientos', 'medicamentos', 'otrosServicios', 
                       'urgencias', 'hospitalizacion', 'recienNacidos']
    
    # Procesar servicios
    usuarios = datos_completados.get('usuarios', [])
    
    for idx_usuario, usuario in enumerate(usuarios):
        usuario_doc = usuario.get('numDocumentoIdentificacion', '')
        if es_valor_vacio(usuario_doc):
            usuario_doc = f'USUARIO_{idx_usuario}'
        else:
            usuario_doc = str(usuario_doc).strip()
        
        servicios = usuario.get('servicios')
        if not isinstance(servicios, dict):
            continue
        
        for tipo_servicio in tipos_servicios:
            lista_servicios = servicios.get(tipo_servicio)
            if not isinstance(lista_servicios, list):
                continue
            
            for servicio in lista_servicios:
                if not isinstance(servicio, dict):
                    continue
                
                # Completar tipo de documento si está vacío
                tipo_doc = servicio.get('tipoDocumentoIdentificacion', '')
                if es_valor_vacio(tipo_doc):
                    servicio['tipoDocumentoIdentificacion'] = 'CC'
                    cambios_tipo += 1
                
                # Completar número de documento si está vacío
                num_doc = servicio.get('numDocumentoIdentificacion', '')
                if es_valor_vacio(num_doc):
                    cod_prestador = servicio.get('codPrestador', '')
                    
                    if not es_valor_vacio(cod_prestador):
                        cod_prestador = str(cod_prestador).strip()
                        
                        profesional_asignado = _obtener_profesional_con_cache(
                            usuario_doc, cod_prestador, tipo_servicio,
                            tabla_nivel1, tabla_nivel2, tabla_nivel3, profesionales_globales,
                            especialistas,
                            cache_asignaciones, profesionales_asignados,
                            fuentes_asignacion
                        )
                        
                        if profesional_asignado:
                            servicio['numDocumentoIdentificacion'] = profesional_asignado
                            cambios_num += 1
                        else:
                            no_completados_count += 1
                    else:
                        no_completados_count += 1
    
    print(f"✅ Completado finalizado:", flush=True)
    print(f"   • Tipos de documento completados: {cambios_tipo}", flush=True)
    print(f"   • Números de documento completados: {cambios_num}", flush=True)
    print(f"   • Total de campos completados: {cambios_tipo + cambios_num}", flush=True)
    if no_completados_count > 0:
        print(f"   ⚠️  No completados (sin profesional disponible): {no_completados_count}", flush=True)
    print("=" * 60, flush=True)
    
    if generar_reporte:
        cambios = _detectar_cambios_documentos(datos, datos_completados, fuentes_asignacion)
        return datos_completados, cambios
    
    return datos_completados
