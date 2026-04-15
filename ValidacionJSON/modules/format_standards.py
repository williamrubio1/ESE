"""
Sistema centralizado de normalización de formatos para campos JSON.
Define los formatos estándar y proporciona funciones de normalización.
"""
import pandas as pd
from datetime import datetime

# ============================================================================
# FUNCIONES DE NORMALIZACIÓN BASE
# ============================================================================

def calcular_edad_en_dias(fecha_nacimiento, fecha_referencia=None):
    """
    Calcula la edad en días a partir de la fecha de nacimiento.
    
    IMPORTANTE: Solo calcula si hay fecha_referencia válida (fechaInicioAtencion).
    NO usa la fecha actual del sistema como fallback.
    
    Args:
        fecha_nacimiento: String en formato 'YYYY-MM-DD'
        fecha_referencia: Fecha de referencia para el cálculo (fechaInicioAtencion máxima)
    
    Returns:
        int: Edad en días, o None si la fecha es inválida o no hay fecha_referencia
    """
    if not fecha_nacimiento or pd.isna(fecha_nacimiento):
        return None
    
    # Si no hay fecha de referencia, retornar None (NO usar fecha actual)
    if not fecha_referencia:
        return None
    
    try:
        fecha_nac = datetime.strptime(str(fecha_nacimiento).strip()[:10], '%Y-%m-%d')
        
        # Parsear fecha de referencia
        if isinstance(fecha_referencia, str):
            fecha_ref = datetime.strptime(str(fecha_referencia).strip()[:10], '%Y-%m-%d')
        else:
            fecha_ref = fecha_referencia
        
        diferencia = fecha_ref - fecha_nac
        return max(0, diferencia.days)
    except (ValueError, AttributeError):
        return None


def calcular_edad(fecha_nacimiento, fecha_referencia=None):
    """
    Calcula la edad en años a partir de la fecha de nacimiento.
    
    IMPORTANTE: Solo calcula si hay fecha_referencia válida (fechaInicioAtencion).
    NO usa la fecha actual del sistema como fallback.
    
    Args:
        fecha_nacimiento: String en formato 'YYYY-MM-DD'
        fecha_referencia: Fecha de referencia para el cálculo (fechaInicioAtencion máxima)
    
    Returns:
        int: Edad en años, o None si la fecha es inválida o no hay fecha_referencia
    """
    if not fecha_nacimiento or pd.isna(fecha_nacimiento):
        return None
    
    # Si no hay fecha de referencia, retornar None (NO usar fecha actual)
    if not fecha_referencia:
        return None
    
    try:
        fecha_nac = datetime.strptime(str(fecha_nacimiento).strip()[:10], '%Y-%m-%d')
        
        # Parsear fecha de referencia
        if isinstance(fecha_referencia, str):
            fecha_ref = datetime.strptime(str(fecha_referencia).strip()[:10], '%Y-%m-%d')
        else:
            fecha_ref = fecha_referencia
        
        edad = fecha_ref.year - fecha_nac.year - ((fecha_ref.month, fecha_ref.day) < (fecha_nac.month, fecha_nac.day))
        return edad
    except (ValueError, AttributeError):
        return None


def calcular_curso_vida(fecha_nacimiento, fecha_referencia=None):
    """
    Determina el curso de vida al que pertenece el usuario según Resolución 3280 de 2018.

    Args:
        fecha_nacimiento: String 'YYYY-MM-DD'
        fecha_referencia: Fecha de corte para el cálculo (fechaInicioAtencion)

    Returns:
        str: Nombre del curso de vida o 'Desconocido' si no se puede calcular.
    """
    edad = calcular_edad(fecha_nacimiento, fecha_referencia)
    if edad is None:
        return 'Desconocido'
    if edad <= 5:
        return 'Primera Infancia'
    if edad <= 11:
        return 'Infancia'
    if edad <= 17:
        return 'Adolescencia'
    if edad <= 26:
        return 'Juventud'
    if edad <= 59:
        return 'Adultez'
    return 'Vejez'


def validar_tipo_documento_por_edad(fecha_nacimiento, tipo_actual, fecha_referencia=None):
    """
    Valida y corrige el tipoDocumentoIdentificacion según la edad en días.
    
    IMPORTANTE: Solo valida si hay fecha_referencia válida (fechaInicioAtencion máxima).
    NO usa la fecha actual del sistema. Si no hay fecha_referencia, mantiene tipo_actual.
    
    Rangos precisos basados en días:
    - RC: 0 días hasta 6 años, 11 meses, 29 días (0-2556 días)
    - TI: 7 años hasta 17 años, 11 meses, 29 días (2557-6574 días)
    - CC: 18 años en adelante (6575+ días)
    
    Cálculo de días límite:
    - 7 años = 7 * 365.25 ≈ 2557 días
    - 18 años = 18 * 365.25 ≈ 6575 días
    
    Args:
        fecha_nacimiento: String en formato 'YYYY-MM-DD'
        tipo_actual: Tipo de documento actual
        fecha_referencia: Fecha de referencia (fechaInicioAtencion máxima entre consultas/procedimientos)
    
    Returns:
        str: Tipo de documento correcto según la edad en días, o tipo_actual si no hay fecha_referencia
    """
    # Si no hay fecha de referencia, mantener el tipo actual (NO usar fecha actual del sistema)
    if not fecha_referencia:
        return tipo_actual
    
    edad_dias = calcular_edad_en_dias(fecha_nacimiento, fecha_referencia)
    
    if edad_dias is None:
        return tipo_actual  # Si no se puede calcular la edad, mantener el tipo actual
    
    # RC: hasta 6 años, 11 meses, 29 días
    if edad_dias < 2557:
        return 'RC'
    # TI: de 7 años hasta 17 años, 11 meses, 29 días
    elif edad_dias < 6575:
        return 'TI'
    # CC: 18 años en adelante
    else:
        return 'CC'


def normalizar_documento(valor):
    """Convierte valores numéricos a string sin decimales (para IDs y códigos)."""
    if valor == '' or valor is None or pd.isna(valor):
        return ''
    try:
        # Si es numérico, convertir a int primero para quitar decimales
        num_val = float(valor)
        return str(int(num_val))
    except (ValueError, TypeError):
        # Si no es numérico, devolver como string limpio
        return str(valor).strip()


def format_two_digit_code(value):
    """Formatea códigos de 2 dígitos agregando cero inicial si es necesario, quitando decimales primero."""
    if value == '' or value is None or pd.isna(value):
        return ''
    # Primero quitar decimales si es numérico
    try:
        num_val = float(value)
        value_str = str(int(num_val))
    except (ValueError, TypeError):
        value_str = str(value).strip()
    # Si tiene un solo dígito, agregar cero inicial
    if len(value_str) == 1 and value_str.isdigit():
        return f'0{value_str}'
    return value_str


def format_four_char_code(value):
    """Formatea códigos de diagnóstico truncándolos a 4 caracteres."""
    if value == '' or value is None or pd.isna(value):
        return ''
    # Truncar a 4 caracteres
    return str(value).strip()[:4]


def format_four_char_code_nullable(value):
    """Formatea códigos de diagnóstico truncándolos a 4 caracteres. Retorna None si está vacío."""
    if value is None or pd.isna(value):
        return None
    value_str = str(value).strip()
    if value_str == '' or value_str.upper() in ('NONE', 'NAN'):
        return None
    # Truncar a 4 caracteres
    return value_str[:4]


def format_three_digit_code(value):
    """Formatea códigos de 3 dígitos agregando ceros iniciales si es necesario."""
    if value == '' or value is None or pd.isna(value):
        return ''
    # Primero quitar decimales si es numérico
    try:
        num_val = float(value)
        value_str = str(int(num_val))
    except (ValueError, TypeError):
        value_str = str(value).strip()
    # Rellenar con ceros a la izquierda hasta 3 dígitos
    if value_str.isdigit():
        return value_str.zfill(3)
    return value_str


def format_six_digit_code(value):
    """Formatea códigos de procedimiento truncándolos a 6 dígitos."""
    if value == '' or value is None or pd.isna(value):
        return ''
    # Primero quitar decimales si es numérico
    try:
        num_val = float(value)
        value_str = str(int(num_val))
    except (ValueError, TypeError):
        value_str = str(value).strip()
    # Truncar a 6 dígitos
    return value_str[:6]


def format_integer(value):
    """Convierte a entero, maneja valores vacíos. Devuelve int, no string."""
    if value is None or value == '' or (isinstance(value, float) and pd.isna(value)):
        return 0
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    value_str = str(value).strip()
    if value_str == '' or value_str.lower() == 'nan':
        return 0
    
    try:
        return int(float(value_str))
    except (ValueError, TypeError):
        return 0


def format_string(value):
    """Convierte a string, maneja valores vacíos."""
    if value == '' or value is None or pd.isna(value):
        return ''
    return str(value).strip()


def format_null_field(value):
    """Retorna None para campos que deben ser null cuando están vacíos."""
    if value is None or pd.isna(value):
        return None
    value_str = str(value).strip()
    if value_str == '' or value_str.upper() in ('NONE', 'NAN'):
        return None
    return value_str


# ============================================================================
# DEFINICIÓN DE FORMATOS ESTÁNDAR POR CAMPO
# ============================================================================

# Formato: 'campo': (función_normalización, descripción)
FIELD_FORMATS = {
    # Campos comunes - Identificadores
    'codPrestador': (normalizar_documento, 'String de 12 caracteres'),
    'numDocumentoIdentificacion': (normalizar_documento, 'String sin decimales'),
    'numDocumentoIdentificacion_profesional': (normalizar_documento, 'String sin decimales'),
    'tipoDocumentoIdentificacion': (format_string, 'String'),
    'tipoDocumentoIdentificacion_profesional': (format_string, 'String'),
    
    # Campos comunes - Códigos de 2 dígitos
    'viaIngresoServicioSalud': (format_two_digit_code, 'String de 2 caracteres'),
    'modalidadGrupoServicioTecSal': (format_two_digit_code, 'String de 2 caracteres'),
    'grupoServicios': (format_two_digit_code, 'String de 2 caracteres'),
    'finalidadTecnologiaSalud': (format_two_digit_code, 'String de 2 caracteres'),
    'causaMotivoAtencion': (format_two_digit_code, 'String de 2 caracteres'),
    'tipoDiagnosticoPrincipal': (format_two_digit_code, 'String de 2 caracteres'),
    'conceptoRecaudo': (format_two_digit_code, 'String de 2 caracteres'),
    'tipoMedicamento': (format_two_digit_code, 'String de 2 caracteres'),
    'tipoOS': (format_two_digit_code, 'String de 2 caracteres'),
    'condicionDestinoUsuarioEgreso': (format_two_digit_code, 'String de 2 caracteres'),
    'tipoUsuario': (format_two_digit_code, 'String de 2 caracteres'),
    'codZonaTerritorialResidencia': (format_two_digit_code, 'String de 2 caracteres'),
    
    # Campos comunes - Códigos de 3 dígitos (países)
    'codPaisOrigen': (format_three_digit_code, 'String de 3 caracteres'),
    'codPaisResidencia': (format_three_digit_code, 'String de 3 caracteres'),
    
    # Campos comunes - Códigos de 4 caracteres
    'codDiagnosticoPrincipal': (format_four_char_code, 'String de 4 caracteres'),
    'codDiagnosticoPrincipalE': (format_four_char_code, 'String de 4 caracteres'),
    'codDiagnosticoRelacionado': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codDiagnosticoRelacionado1': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codDiagnosticoRelacionado2': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codDiagnosticoRelacionado3': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codDiagnosticoRelacionadoE1': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codDiagnosticoRelacionadoE2': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codDiagnosticoRelacionadoE3': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codComplicacion': (format_four_char_code_nullable, 'String de 4 caracteres o null'),
    'codDiagnosticoCausaMuerte': (format_null_field, 'null o String de 4 caracteres'),
    
    # Campos comunes - Enteros
    'codServicio': (format_integer, 'Integer'),
    'vrServicio': (format_integer, 'Integer'),
    'valorPagoModerador': (format_integer, 'Integer'),
    'consecutivo': (format_integer, 'Integer'),
    'consecutivo_consulta': (format_integer, 'Integer'),
    'consecutivo_procedimiento': (format_integer, 'Integer'),
    'consecutivo_medicamento': (format_integer, 'Integer'),
    'consecutivo_otro': (format_integer, 'Integer'),
    'consecutivo_urgencia': (format_integer, 'Integer'),
    'consecutivo_hospitalizacion': (format_integer, 'Integer'),
    'consecutivo_recien_nacido': (format_integer, 'Integer'),
    
    # Medicamentos - Enteros
    'concentracionMedicamento': (format_integer, 'Integer'),
    'unidadMedida': (format_integer, 'Integer'),
    'unidadMinDispensa': (format_integer, 'Integer'),
    'cantidadMedicamento': (format_integer, 'Integer'),
    'diasTratamiento': (format_integer, 'Integer'),
    'vrUnitMedicamento': (format_integer, 'Integer'),
    
    # Otros Servicios - Enteros
    'cantidadOS': (format_integer, 'Integer'),
    'vrUnitOS': (format_integer, 'Integer'),
    
    # Procedimientos - String
    'codProcedimiento': (format_six_digit_code, 'String de 6 dígitos'),
    
    # Campos comunes - Strings
    'codConsulta': (format_string, 'String'),
    'codTecnologiaSalud': (format_string, 'String'),
    'nomTecnologiaSalud': (format_string, 'String'),
    
    # Campos que deben ser null cuando vacíos
    'numAutorizacion': (format_null_field, 'null o String'),
    'idMIPRES': (format_null_field, 'null o String'),
    'numFEVPagoModerador': (format_null_field, 'null'),
    'formaFarmaceutica': (format_null_field, 'null o String'),
    
    # Campos de fecha (se manejan como string, el formato ya viene correcto)
    'fechaInicioAtencion': (format_string, 'Fecha yyyy-mm-dd hh:mm'),
    'fechaDispensAdmon': (format_string, 'Fecha yyyy-mm-dd hh:mm'),
    'fechaSuministroTecnologia': (format_string, 'Fecha yyyy-mm-dd hh:mm'),
    'fechaEgreso': (format_string, 'Fecha yyyy-mm-dd hh:mm'),
    'fechaNacimiento': (format_string, 'Fecha yyyy-mm-dd'),
    
    # Usuarios
    'codSexo': (format_string, 'String'),
    'codPaisResidencia': (format_string, 'String'),
    'codMunicipioResidencia': (format_string, 'String'),
    'incapacidad': (format_string, 'String'),
    'codPaisOrigen': (format_string, 'String'),
}


# ============================================================================
# FUNCIONES DE APLICACIÓN MASIVA
# ============================================================================

def normalize_dataframe_columns(df, column_list=None):
    """
    Normaliza las columnas de un DataFrame según los formatos estándar definidos.
    
    Args:
        df: DataFrame de pandas
        column_list: Lista de columnas a normalizar. Si es None, normaliza todas las columnas conocidas.
    
    Returns:
        DataFrame normalizado
    """
    if df.empty:
        return df
    
    columns_to_process = column_list if column_list else df.columns
    
    for col in columns_to_process:
        if col in df.columns and col in FIELD_FORMATS:
            normalize_func, _ = FIELD_FORMATS[col]
            df[col] = df[col].apply(normalize_func)
    
    return df


def normalize_dict_fields(data_dict):
    """
    Normaliza los campos de un diccionario según los formatos estándar definidos.
    
    Args:
        data_dict: Diccionario con los datos
    
    Returns:
        Diccionario con campos normalizados
    """
    normalized = {}
    
    for key, value in data_dict.items():
        if key in FIELD_FORMATS:
            normalize_func, _ = FIELD_FORMATS[key]
            normalized[key] = normalize_func(value)
        else:
            # Campos no definidos se pasan tal cual
            if pd.isna(value):
                normalized[key] = None
            else:
                normalized[key] = value
    
    return normalized


def get_field_format_info(field_name):
    """
    Obtiene información sobre el formato de un campo.
    
    Args:
        field_name: Nombre del campo
    
    Returns:
        Tupla (función_normalización, descripción) o None si no está definido
    """
    return FIELD_FORMATS.get(field_name)


# ============================================================================
# SECCIONES ESPECÍFICAS
# ============================================================================

# Definir qué campos pertenecen a cada sección para validación
SECTION_FIELDS = {
    'consultas': [
        'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'codConsulta',
        'modalidadGrupoServicioTecSal', 'grupoServicios', 'codServicio',
        'finalidadTecnologiaSalud', 'causaMotivoAtencion', 'codDiagnosticoPrincipal',
        'codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3',
        'tipoDiagnosticoPrincipal', 'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
        'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador', 'consecutivo'
    ],
    'procedimientos': [
        'codPrestador', 'fechaInicioAtencion', 'numAutorizacion', 'idMIPRES', 'codProcedimiento',
        'viaIngresoServicioSalud', 'modalidadGrupoServicioTecSal', 'grupoServicios', 'codServicio',
        'finalidadTecnologiaSalud', 'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
        'codDiagnosticoPrincipal', 'codDiagnosticoRelacionado', 'codComplicacion',
        'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador', 'consecutivo'
    ],
    'medicamentos': [
        'codPrestador', 'numAutorizacion', 'idMIPRES', 'fechaDispensAdmon',
        'codDiagnosticoPrincipal', 'codDiagnosticoRelacionado', 'tipoMedicamento',
        'codTecnologiaSalud', 'nomTecnologiaSalud', 'concentracionMedicamento',
        'unidadMedida', 'formaFarmaceutica', 'unidadMinDispensa', 'cantidadMedicamento',
        'diasTratamiento', 'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion',
        'vrUnitMedicamento', 'vrServicio', 'conceptoRecaudo', 'valorPagoModerador',
        'numFEVPagoModerador', 'consecutivo'
    ],
    'otrosServicios': [
        'codPrestador', 'numAutorizacion', 'idMIPRES', 'fechaSuministroTecnologia',
        'tipoOS', 'codTecnologiaSalud', 'nomTecnologiaSalud', 'cantidadOS',
        'tipoDocumentoIdentificacion', 'numDocumentoIdentificacion', 'vrUnitOS',
        'vrServicio', 'conceptoRecaudo', 'valorPagoModerador', 'numFEVPagoModerador', 'consecutivo'
    ],
    'urgencias': [
        'codPrestador', 'fechaInicioAtencion', 'causaMotivoAtencion',
        'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
        'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
        'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte', 'fechaEgreso', 'consecutivo'
    ],
    'hospitalizacion': [
        'codPrestador', 'viaIngresoServicioSalud', 'fechaInicioAtencion', 'numAutorizacion',
        'causaMotivoAtencion', 'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
        'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2', 'codDiagnosticoRelacionadoE3',
        'codComplicacion', 'condicionDestinoUsuarioEgreso', 'codDiagnosticoCausaMuerte',
        'fechaEgreso', 'consecutivo'
    ],
    'recienNacidos': [
        'codPrestador', 'fechaInicioAtencion', 'edadGestacional', 'controlPrenatal',
        'sexoBiologico', 'peso', 'codDiagnosticoPrincipal', 'condicionDestinoUsuarioEgreso',
        'codDiagnosticoCausaMuerte', 'fechaEgreso', 'consecutivo'
    ]
}
