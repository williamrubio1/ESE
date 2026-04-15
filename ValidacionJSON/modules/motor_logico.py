"""
Motor Lógico Centralizado para validación de finalidad, causa y CIE10 en RIPS-JSON.

Reemplaza las tablas de sustitución fijas de PyP y BC.
Opera de forma secuencial y jerárquica sobre cada registro:
  1. Normalización del CIE10 (formato XXXX, sin punto, mayúsculas)
  2. Clasificación por letra inicial en cuatro grupos funcionales
  3. Filtro por contrato EPS (CUPS)
  4. Finalidad como eje de control → reglas de causa

Grupos CIE10:
  - enfermedad    : A–R
  - trauma        : S–T
  - causa_externa : V–Y
  - factor        : Z

Reglas de causa según finalidad:
  - 11–14 (PyP)    : eliminar causa siempre
  - 15 (diagnóstico):
        enfermedad/factor  → sin causa
        trauma             → causa válida 21–49 (corregir si falta o inválida)
        causa_externa      → sin causa (no duplicar)
  - 16–44 (evento) : sin corrección automática; inconsistencias → alerta
"""

# ---------------------------------------------------------------------------
# Causa por defecto cuando un trauma con finalidad 15 no tiene causa válida
# ---------------------------------------------------------------------------
CAUSA_TRAUMA_DEFAULT = '26'
CAUSA_TRAUMA_MIN = 21
CAUSA_TRAUMA_MAX = 49

# ---------------------------------------------------------------------------
# Campo maps estándar (iguales en PyP y BC)
# ---------------------------------------------------------------------------
CAMPO_MAP_CONSULTAS = {
    'finalidad': 'finalidadTecnologiaSalud',
    'causa':     'causaMotivoAtencion',
    'cie10':     'codDiagnosticoPrincipal',
    'cups':      'codConsulta',
}

CAMPO_MAP_PROCEDIMIENTOS = {
    'finalidad': 'finalidadTecnologiaSalud',
    'causa':     None,   # los procedimientos no tienen causaMotivoAtencion
    'cie10':     'codDiagnosticoPrincipal',
    'cups':      'codProcedimiento',
}


# ---------------------------------------------------------------------------
# Funciones de apoyo
# ---------------------------------------------------------------------------

def normalizar_cie10(codigo):
    """
    Normaliza un código CIE10 al formato XXXX:
      - Elimina puntos
      - Convierte a mayúsculas
      - Trunca a 4 caracteres

    Devuelve cadena vacía si el valor es None o vacío.
    """
    if not codigo:
        return ''
    cod = str(codigo).strip().upper().replace('.', '')
    return cod[:4]


def clasificar_cie10(codigo):
    """
    Clasifica un código CIE10 por su primera letra.

    Returns:
        'enfermedad'    – A a R
        'trauma'        – S o T
        'causa_externa' – V a Y
        'factor'        – Z
        'desconocido'   – vacío o letra no reconocida
    """
    if not codigo:
        return 'desconocido'
    primera = codigo[0].upper()
    if primera in 'ABCDEFGHIJKLMNOPQR':
        return 'enfermedad'
    if primera in 'ST':
        return 'trauma'
    if primera in 'VWXY':
        return 'causa_externa'
    if primera == 'Z':
        return 'factor'
    return 'desconocido'


def _causa_valida_trauma(causa):
    """Devuelve True si causa es un entero en el rango 21–49."""
    try:
        val = int(str(causa).strip())
        return CAUSA_TRAUMA_MIN <= val <= CAUSA_TRAUMA_MAX
    except (ValueError, TypeError):
        return False


def _causa_ausente(causa):
    """Devuelve True si el valor de causa se considera vacío/nulo."""
    return not causa or str(causa).strip() in ('', 'None', 'nan')


# ---------------------------------------------------------------------------
# Clasificación clínica PYP para códigos Z
# ---------------------------------------------------------------------------

def clasificar_pyp_por_cie10(codigo):
    """
    Determina finalidadTecnologiaSalud y causaMotivoAtencion para un código
    CIE10 tipo Z según su familia clínica PYP.

    La clasificación se hace por prefijo numérico, no por código exacto, para
    capturar todos los subtipos de cada familia sin mapeos individuales.

    Familias reconocidas:
      Z34–Z35  Controles prenatales          → finalidad 23 / causa 42
      Z30      Planificación familiar         → finalidad 19 / causa 40
      Z31      Fertilidad / reproducción      → finalidad 22 / causa 40
      Z39      Control posparto               → finalidad 25 / causa 42
      Z01      Detección temprana / tamizajes → finalidad 14 / causa 40
      Z00      Valoración integral             → finalidad 11 / causa 40
      Z71, Z76 Consejería / contacto          → finalidad 11 / causa 40
      Resto Z  No clasifica claramente        → finalidad 11 / causa 40

    Args:
        codigo: código CIE10 normalizado (mayúsculas, sin punto, hasta 4 chars).

    Returns:
        tuple (finalidad_str, causa_str) con valores como cadenas de texto.
    """
    if not codigo or not codigo.startswith('Z'):
        return ('11', '40')

    # Extraer los dos dígitos que siguen a la letra Z
    prefijo_raw = codigo[1:3]
    try:
        num = int(prefijo_raw)
    except ValueError:
        return ('11', '40')

    # Controles prenatales: Z34–Z35
    if 34 <= num <= 35:
        return ('23', '42')

    # Planificación familiar: Z30
    if num == 30:
        return ('19', '40')

    # Fertilidad / reproducción: Z31
    if num == 31:
        return ('22', '40')

    # Control posparto: Z39
    if num == 39:
        return ('25', '42')

    # Detección temprana / tamizajes: Z01
    if num == 1:
        return ('12', '40')

    # Valoración integral: Z00
    if num == 0:
        return ('11', '40')

    # Consejería / contacto con servicios: Z71, Z76
    if num in (71, 76):
        return ('11', '40')

    # Default: Z no clasificado claramente → finalidad preventiva genérica
    return ('11', '40')


# ---------------------------------------------------------------------------
# Categorización de CUPS no incluidos en Ficha Técnica RPYMS
# ---------------------------------------------------------------------------
from modules.cups_categorias import get_categoria_cups

# Categorías cuya finalidad y causa se aplican de forma autoritativa
# (sobrescriben la lógica CIE-10 cuando el CUPS está clasificado)
_CATEGORIAS_OVERRIDE = {
    'MORBILIDAD_ODONTOLOGICA',
    'APOYO_DIAGNOSTICO',
    'RUTA_MATERNO_PERINATAL',
    'VACUNA_ESPECIAL',
    'VACUNA_PAI',
    'SALUD_ORAL_PE',
    'LAB_CARDIOMETABOLICO',
    'EDUCACION_GRUPAL',
    'EDUCACION_INDIVIDUAL',
    'PLANIFICACION_FAMILIAR_PE',
    'DETECCION_TEMPRANA_GENERAL',
}

# En Baja Complejidad estas categorías se manejan como apoyo diagnóstico.
_CATEGORIAS_FINALIDAD_15_BC = {
    'LAB_CARDIOMETABOLICO',
    'DETECCION_TEMPRANA_GENERAL',
}


# ---------------------------------------------------------------------------
# Motor principal
# ---------------------------------------------------------------------------

def aplicar_motor_logico(registro, campo_map, config_eps=None):
    """
    Aplica el motor lógico centralizado a un registro (modifica in-place).

    Args:
        registro   : dict con los campos del servicio.
        campo_map  : dict con claves 'finalidad', 'causa', 'cie10', 'cups'.
                     'causa' puede ser None (procedimientos sin causaMotivoAtencion).
        config_eps : dict con clave 'cups_contrato' (set de CUPS del contrato activo).
                     Si None o conjunto vacío, no se aplica filtro.

    Returns:
        dict con:
            'modificado'   : bool – True si se cambió algún campo
            'en_contrato'  : bool – False si el CUPS no está en el contrato
            'alertas'      : list[str] – observaciones clínicas (sin corrección automática)
            'cambios'      : dict {campo: (valor_anterior, valor_nuevo)}
    """
    alertas = []
    cambios = {}

    campo_finalidad = campo_map.get('finalidad', 'finalidadTecnologiaSalud')
    campo_causa     = campo_map.get('causa')       # puede ser None
    campo_cie10     = campo_map.get('cie10', 'codDiagnosticoPrincipal')
    campo_cups      = campo_map.get('cups', '')

    # ------------------------------------------------------------------
    # Paso 0: Filtro por contrato EPS
    # ------------------------------------------------------------------
    if config_eps is not None:
        cups_contrato = config_eps.get('cups_contrato', set())
        if cups_contrato and campo_cups:
            cups_val = str(registro.get(campo_cups, '') or '').strip()
            if cups_val and cups_val not in cups_contrato:
                return {
                    'modificado':  False,
                    'en_contrato': False,
                    'alertas':     [f'CUPS {cups_val} no pertenece al contrato activo'],
                    'cambios':     {},
                }

    # ------------------------------------------------------------------
    # Paso 0.5: Override por categoría de CUPS (no incluidos en RPYMS)
    # Aplica finalidad, causa y CIE-10 predeterminados según la categoría.
    # Para todas las categorías en _CATEGORIAS_OVERRIDE el valor de la
    # categoría es autoritativo y omite la clasificación CIE-10 de los
    # pasos siguientes.
    #
    # Categorías protegidas (en _CATEGORIAS_OVERRIDE):
    #   MORBILIDAD_ODONTOLOGICA   — fin 16, causa 38
    #   APOYO_DIAGNOSTICO         — fin 15, causa 38
    #   RUTA_MATERNO_PERINATAL    — fin 23, causa 42, Z340
    #   VACUNA_ESPECIAL           — fin 14, causa 40, Z279 (lineamiento PAI especial)
    #   VACUNA_PAI                — fin 14, causa 40, Z279 (esquema PAI regular)
    #   SALUD_ORAL_PE             — fin 14, causa 40, CIE10 por CUPS
    #   LAB_CARDIOMETABOLICO      — fin 12, causa 40, Z108
    #   EDUCACION_GRUPAL          — fin 42, causa 41, Z718
    #   EDUCACION_INDIVIDUAL      — fin 40, causa 40, Z718
    #   PLANIFICACION_FAMILIAR_PE — fin 14, causa 40, CIE10 por CUPS
    #   DETECCION_TEMPRANA_GENERAL— fin 12, causa 40, CIE10 por CUPS
    #
    # DOBLE_PROPOSITO y URGENCIAS_SOPORTE NO están en _CATEGORIAS_OVERRIDE:
    # su finalidad depende del contexto clínico.
    # ------------------------------------------------------------------
    cups_val_paso05 = str(registro.get(campo_cups, '') or '').strip() if campo_cups else ''
    categoria_info = get_categoria_cups(cups_val_paso05) if cups_val_paso05 else None
    categoria_override = (
        categoria_info is not None
        and categoria_info['categoria'] in _CATEGORIAS_OVERRIDE
    )

    if categoria_info is not None:
        # Añadir alerta crítica si existe (siempre, independiente del override)
        if categoria_info.get('alerta'):
            alertas.append(categoria_info['alerta'])

    if categoria_override:
        # Aplicar finalidad de categoría
        cat_finalidad = categoria_info.get('finalidad')
        if cat_finalidad:
            fin_actual = str(registro.get(campo_finalidad, '') or '').strip()
            if fin_actual != cat_finalidad:
                registro[campo_finalidad] = cat_finalidad
                cambios[campo_finalidad]  = (fin_actual, cat_finalidad)

        # Aplicar causa de categoría
        cat_causa = categoria_info.get('causa')
        if campo_causa and cat_causa:
            causa_actual = str(registro.get(campo_causa, '') or '').strip()
            if causa_actual != cat_causa:
                registro[campo_causa] = cat_causa
                cambios[campo_causa]  = (causa_actual, cat_causa)

        # Aplicar CIE-10 sugerido solo si el campo está vacío
        cat_cie10 = categoria_info.get('cie10_default')
        if cat_cie10:
            cie10_actual = str(registro.get(campo_cie10, '') or '').strip()
            if not cie10_actual:
                registro[campo_cie10] = cat_cie10
                cambios[campo_cie10]  = ('', cat_cie10)

        # Añadir nota de categoría como alerta informativa
        if categoria_info.get('nota'):
            alertas.append(f'[Cat. {categoria_info["categoria"]}] {categoria_info["nota"]}')

        return {
            'modificado':  bool(cambios),
            'en_contrato': True,
            'alertas':     alertas,
            'cambios':     cambios,
        }

    # ------------------------------------------------------------------
    # Paso 1: Normalizar CIE10
    # ------------------------------------------------------------------
    cie10_original   = str(registro.get(campo_cie10, '') or '').strip()
    cie10_normalizado = normalizar_cie10(cie10_original)

    if cie10_normalizado != cie10_original:
        registro[campo_cie10] = cie10_normalizado
        cambios[campo_cie10]  = (cie10_original, cie10_normalizado)

    # ------------------------------------------------------------------
    # Paso 2: Clasificar CIE10
    # ------------------------------------------------------------------
    clasificacion = clasificar_cie10(cie10_normalizado)

    if clasificacion == 'desconocido':
        alertas.append(
            f'CIE10 "{cie10_normalizado}" no clasificable'
            if cie10_normalizado else 'CIE10 ausente'
        )

    # ------------------------------------------------------------------
    # Paso 3: Leer finalidad
    # ------------------------------------------------------------------
    finalidad_str = str(registro.get(campo_finalidad, '') or '').strip()
    try:
        finalidad = int(finalidad_str)
    except (ValueError, TypeError):
        finalidad = None
        alertas.append(f'Finalidad no reconocida: "{finalidad_str}"')

    # ------------------------------------------------------------------
    # Paso 4: Leer causa actual (si el campo aplica)
    # ------------------------------------------------------------------
    causa_original = str(registro.get(campo_causa, '') or '').strip() if campo_causa else None

    # ------------------------------------------------------------------
    # Paso 4.5: Clasificación clínica PYP — códigos Z reciben finalidad y
    # causa según su familia clínica; omite las reglas genéricas del paso 5.
    # ------------------------------------------------------------------
    nueva_causa = causa_original  # por defecto no cambia
    pyp_asignado = False

    if clasificacion == 'factor':
        finalidad_pyp, causa_pyp = clasificar_pyp_por_cie10(cie10_normalizado)
        finalidad_pyp_int = int(finalidad_pyp)

        # Corregir finalidad si difiere de la asignada por clasificación clínica
        if finalidad != finalidad_pyp_int:
            registro[campo_finalidad] = finalidad_pyp
            cambios[campo_finalidad]  = (finalidad_str, finalidad_pyp)
            finalidad = finalidad_pyp_int

        # Asignar causa PYP (autoritativa; sobrescribe cualquier valor previo)
        if campo_causa:
            nueva_causa = causa_pyp

        pyp_asignado = True

    # ------------------------------------------------------------------
    # Paso 5: Aplicar reglas de causa según finalidad (solo registros no-Z)
    # ------------------------------------------------------------------

    if not pyp_asignado and finalidad is not None:

        if 11 <= finalidad <= 14:
            # PyP no-Z: la causa debe estar ausente
            if campo_causa and not _causa_ausente(causa_original):
                nueva_causa = ''
                alertas.append(
                    f'Causa eliminada: finalidad PyP ({finalidad}) no admite causa'
                )

        elif finalidad == 15:
            # Diagnóstico: comportamiento según clasificación del CIE10
            if clasificacion in ('enfermedad', 'factor'):
                if campo_causa and not _causa_ausente(causa_original):
                    nueva_causa = ''
                    alertas.append(
                        f'Causa eliminada: clasificación "{clasificacion}" con finalidad 15 '
                        'no requiere causa'
                    )

            elif clasificacion == 'trauma':
                if campo_causa and not _causa_valida_trauma(causa_original):
                    nueva_causa = CAUSA_TRAUMA_DEFAULT
                    desc = f'"{causa_original}"' if not _causa_ausente(causa_original) else 'ausente'
                    alertas.append(
                        f'Causa {desc} corregida a {CAUSA_TRAUMA_DEFAULT} '
                        f'(trauma con finalidad 15 requiere causa 21–49)'
                    )

            elif clasificacion == 'causa_externa':
                if campo_causa and not _causa_ausente(causa_original):
                    nueva_causa = ''
                    alertas.append(
                        'Causa eliminada: causa_externa no debe tener causa adicional '
                        '(finalidad 15)'
                    )

        elif 16 <= finalidad <= 44:
            # Eventos / tratamientos: solo alertas, sin corrección automática
            if campo_causa and not _causa_ausente(causa_original):
                alertas.append(
                    f'Alerta: causa "{causa_original}" presente en finalidad {finalidad} '
                    '(evento); se conserva sin corrección automática'
                )

    # ------------------------------------------------------------------
    # Paso 6: Registrar cambio de causa si aplica
    # ------------------------------------------------------------------
    if campo_causa and nueva_causa != causa_original:
        registro[campo_causa] = nueva_causa
        cambios[campo_causa]  = (causa_original, nueva_causa)

    # Alerta adicional de contexto: trauma atendido en consulta externa (CUPS 890xxx)
    if clasificacion == 'trauma' and campo_cups:
        cups_val = str(registro.get(campo_cups, '') or '').strip()
        if cups_val.startswith('890'):
            alertas.append(
                f'Alerta contextual: trauma (CIE10 "{cie10_normalizado}") '
                f'atendido en consulta externa (CUPS {cups_val})'
            )

    return {
        'modificado':  bool(cambios),
        'en_contrato': True,
        'alertas':     alertas,
        'cambios':     cambios,
    }


# ---------------------------------------------------------------------------
# Constantes para clasificación sobre DataFrames
# ---------------------------------------------------------------------------

# Procedimientos PYP que usan Z258 cuando el diagnóstico está vacío
# NOTA: los códigos cubiertos por _CATEGORIAS_OVERRIDE (VACUNA_PAI, VACUNA_ESPECIAL, etc.)
# son filtrados por los guards antes de llegar a esta constante. Solo quedan códigos
# sin categoría que necesitan un CIE-10 de respaldo en contexto PyP.
CODIGOS_PROC_Z258_PYP = {
    '993101',                       # Cólera — vacuna especial no en esquema PAI regular
    # '993106' migrado a CUPS_VACUNAS_ESPECIALES — fin 14 según Sigires
    '993121', '993123', '993125',   # Variantes DPT no catalogadas en NEPS
    '993131',                       # Pentavalente variante
    # '993503' migrado a CUPS_VACUNA_PAI — fin 14, Z279
    '993521', '993523',             # Variantes doble/triple viral
    '995101', '995202',             # Otras vacunaciones PAI
}

# Códigos de procedimiento de compuestos que deben llenarse con Z258.
COMPUESTOS_CODIGOS_PROC_Z258 = {
    '993101', '993102', '993103', '993104',
    '993120', '993121', '993122',
    '993123', '993124', '993125', '993130', '993131', '993501', '993502', '993503',
    '993504', '993505', '993506', '993507', '993508', '993509', '993510', '993512',
    '993513', '993520', '993521', '993522', '993523', '995101', '995201', '995202',
}

# Catálogo de fallback diagnóstico/finalidad para procedimientos de compuestos.
COMPUESTOS_TABLA_CUPS_FINALIDAD = {
    '997002': {'DX': 'Z012', 'FINALIDAD': '14'},
    '997107': {'DX': 'Z012', 'FINALIDAD': '14'},
    '990203': {'DX': 'Z012', 'FINALIDAD': '14'},
    '903841': {'DX': 'Z017', 'FINALIDAD': '15'},
    '997301': {'DX': 'Z012', 'FINALIDAD': '14'},
    '997106': {'DX': 'Z012', 'FINALIDAD': '14'},
    '907106': {'DX': 'Z017', 'FINALIDAD': '15'},
    '990201': {'DX': 'Z017', 'FINALIDAD': '14'},
    '990204': {'DX': 'Z017', 'FINALIDAD': '14'},
    '903818': {'DX': 'Z017', 'FINALIDAD': '15'},
    '903868': {'DX': 'Z017', 'FINALIDAD': '15'},
    '903815': {'DX': 'Z017', 'FINALIDAD': '15'},
    '903816': {'DX': 'Z017', 'FINALIDAD': '15'},
    '903895': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902208': {'DX': 'Z017', 'FINALIDAD': '15'},
    '990212': {'DX': 'Z012', 'FINALIDAD': '14'},
    '993510': {'DX': 'Z258', 'FINALIDAD': '14'},
    '993504': {'DX': 'Z243', 'FINALIDAD': '14'},
    '902207': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993501': {'DX': 'Z258', 'FINALIDAD': '14'},
    '903856': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993130': {'DX': 'Z258', 'FINALIDAD': '14'},
    '892901': {'DX': 'Z124', 'FINALIDAD': '12'},
    '901304': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993106': {'DX': 'Z258', 'FINALIDAD': '14'},
    '993513': {'DX': 'Z258', 'FINALIDAD': '14'},
    '993522': {'DX': 'Z258', 'FINALIDAD': '14'},
    '895100': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993509': {'DX': 'Z258', 'FINALIDAD': '14'},
    '906039': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902214': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993122': {'DX': 'Z258', 'FINALIDAD': '14'},
    '232102': {'DX': 'K021', 'FINALIDAD': '16'},
    '906249': {'DX': 'Z017', 'FINALIDAD': '15'},
    '904508': {'DX': 'Z017', 'FINALIDAD': '15'},
    '898001': {'DX': 'Z124', 'FINALIDAD': '12'},
    '903801': {'DX': 'Z017', 'FINALIDAD': '15'},
    '990211': {'DX': 'Z017', 'FINALIDAD': '14'},
    '993120': {'DX': 'Z258', 'FINALIDAD': '14'},
    '907008': {'DX': 'Z017', 'FINALIDAD': '15'},
    '871121': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993512': {'DX': 'Z258', 'FINALIDAD': '14'},
    '902210': {'DX': 'Z017', 'FINALIDAD': '15'},
    '933700': {'DX': 'Z018', 'FINALIDAD': '12'},
    '961601': {'DX': 'N398', 'FINALIDAD': '16'},
    '901326': {'DX': 'B559', 'FINALIDAD': '15'},
    '873312': {'DX': 'Z017', 'FINALIDAD': '15'},
    '870108': {'DX': 'Z017', 'FINALIDAD': '15'},
    '901305': {'DX': 'Z017', 'FINALIDAD': '15'},
    '995202': {'DX': 'Z258', 'FINALIDAD': '14'},
    '230201': {'DX': 'K083', 'FINALIDAD': '16'},
    '873112': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993505': {'DX': 'Z258', 'FINALIDAD': '14'},
    '873206': {'DX': 'Z017', 'FINALIDAD': '15'},
    '950601': {'DX': 'Z010', 'FINALIDAD': '12'},
    '237101': {'DX': 'K040', 'FINALIDAD': '16'},
    '977100': {'DX': 'Z305', 'FINALIDAD': '14'},
    '870101': {'DX': 'Z017', 'FINALIDAD': '15'},
    '873335': {'DX': 'Z017', 'FINALIDAD': '15'},
    '871050': {'DX': 'Z017', 'FINALIDAD': '15'},
    '697101': {'DX': 'Z305', 'FINALIDAD': '14'},
    '873121': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993107': {'DX': 'Z258', 'FINALIDAD': '14'},
    '902221': {'DX': 'Z017', 'FINALIDAD': '15'},
    '870001': {'DX': 'Z017', 'FINALIDAD': '15'},
    '872002': {'DX': 'Z017', 'FINALIDAD': '15'},
    '870107': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902215': {'DX': 'Z017', 'FINALIDAD': '15'},
    '990112': {'DX': 'Z012', 'FINALIDAD': '15'},
    '871111': {'DX': 'Z017', 'FINALIDAD': '15'},
    '993503': {'DX': 'Z258', 'FINALIDAD': '14'},
    '870104': {'DX': 'Z017', 'FINALIDAD': '15'},
    '873122': {'DX': 'Z017', 'FINALIDAD': '15'},
    '871091': {'DX': 'Z017', 'FINALIDAD': '15'},
    '870113': {'DX': 'Z017', 'FINALIDAD': '15'},
    '870112': {'DX': 'Z017', 'FINALIDAD': '15'},
    '232200': {'DX': 'K021', 'FINALIDAD': '16'},
    '873340': {'DX': 'K017', 'FINALIDAD': '15'},
    '906209': {'DX': 'A979', 'FINALIDAD': '15'},
    '993502': {'DX': 'Z258', 'FINALIDAD': '14'},
    '911015': {'DX': 'Z017', 'FINALIDAD': '15'},
    '907002': {'DX': 'Z017', 'FINALIDAD': '15'},
    '906317': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902209': {'DX': 'Z017', 'FINALIDAD': '15'},
    '861801': {'DX': 'Z304', 'FINALIDAD': '14'},
    '906915': {'DX': 'Z017', 'FINALIDAD': '15'},
    '871040': {'DX': 'Z017', 'FINALIDAD': '15'},
    '907009': {'DX': 'Z017', 'FINALIDAD': '15'},
    '903844': {'DX': 'Z017', 'FINALIDAD': '15'},
    '903843': {'DX': 'Z017', 'FINALIDAD': '15'},
    '861203': {'DX': 'Z304', 'FINALIDAD': '14'},
    '873420': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902213': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902211': {'DX': 'Z017', 'FINALIDAD': '15'},
    '901101': {'DX': 'Z017', 'FINALIDAD': '15'},
    '873204': {'DX': 'Z017', 'FINALIDAD': '15'},
    '873411': {'DX': 'Z017', 'FINALIDAD': '15'},
    '873333': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902204': {'DX': 'Z017', 'FINALIDAD': '15'},
    '230102': {'DX': 'K083', 'FINALIDAD': '16'},
    '871010': {'DX': 'Z017', 'FINALIDAD': '15'},
    '995201': {'DX': 'Z258', 'FINALIDAD': '14'},
    '871030': {'DX': 'Z017', 'FINALIDAD': '15'},
    '873210': {'DX': 'Z017', 'FINALIDAD': '15'},
    '906223': {'DX': 'Z017', 'FINALIDAD': '15'},
    '901107': {'DX': 'Z017', 'FINALIDAD': '15'},
    '990103': {'DX': 'Z012', 'FINALIDAD': '14'},
    '871020': {'DX': 'Z017', 'FINALIDAD': '15'},
    '903809': {'DX': 'R17X', 'FINALIDAD': '40'},
    '873313': {'DX': 'Z017', 'FINALIDAD': '15'},
    '902206': {'DX': 'Z017', 'FINALIDAD': '15'},
    '990104': {'DX': 'Z017', 'FINALIDAD': '14'},
    '901111': {'DX': 'A150', 'FINALIDAD': '12'},
    '990206': {'DX': 'Z017', 'FINALIDAD': '14'},
    '990101': {'DX': 'Z017', 'FINALIDAD': '14'},
    '993520': {'DX': 'Z258', 'FINALIDAD': '14'},
    '903842': {'DX': 'Z017', 'FINALIDAD': '15'},
    '230202': {'DX': 'K083', 'FINALIDAD': '16'},
    '873205': {'DX': 'Z017', 'FINALIDAD': '15'},
    '230101': {'DX': 'K083', 'FINALIDAD': '16'},
    '237301': {'DX': 'K040', 'FINALIDAD': '16'},
    '873431': {'DX': 'Z017', 'FINALIDAD': '15'},
    '890703': {'DX': 'K021', 'FINALIDAD': '38'},
}

# Códigos Z propios de PYP/maternidad que no deben aparecer en consultas BC
DIAGNOSTICOS_REEMPLAZAR_BC = {
    'Z000', 'Z300', 'Z010', 'Z258', 'Z001', 'Z002', 'Z003',
    'Z348', 'Z359', 'Z357', 'Z304', 'Z358', 'Z349', 'Z354',
    'Z314', 'Z340', 'Z309',
}


def _bc_tiene_override(codigo_cups):
    """Devuelve la metadata de categoría si el CUPS BC usa override autoritativo."""
    codigo = str(codigo_cups or '').strip()
    if not codigo:
        return None

    categoria = get_categoria_cups(codigo)
    if categoria is None:
        return None

    if categoria['categoria'] not in _CATEGORIAS_OVERRIDE:
        return None

    return categoria


def _aplicar_override_categoria_bc(registro, campo_map, categoria_info, config_eps=None):
    """Aplica el override autoritativo de categoría con ajustes específicos de BC."""
    alertas = []
    cambios = {}

    campo_finalidad = campo_map.get('finalidad', 'finalidadTecnologiaSalud')
    campo_causa = campo_map.get('causa')
    campo_cie10 = campo_map.get('cie10', 'codDiagnosticoPrincipal')
    campo_cups = campo_map.get('cups', '')

    if config_eps is not None:
        cups_contrato = config_eps.get('cups_contrato', set())
        if cups_contrato and campo_cups:
            cups_val = str(registro.get(campo_cups, '') or '').strip()
            if cups_val and cups_val not in cups_contrato:
                return {
                    'modificado': False,
                    'en_contrato': False,
                    'alertas': [f'CUPS {cups_val} no pertenece al contrato activo'],
                    'cambios': {},
                }

    if categoria_info.get('alerta'):
        alertas.append(categoria_info['alerta'])

    categoria = categoria_info.get('categoria')
    cat_finalidad = categoria_info.get('finalidad')
    if categoria in _CATEGORIAS_FINALIDAD_15_BC:
        cat_finalidad = '15'

    if cat_finalidad:
        fin_actual = str(registro.get(campo_finalidad, '') or '').strip()
        if fin_actual != cat_finalidad:
            registro[campo_finalidad] = cat_finalidad
            cambios[campo_finalidad] = (fin_actual, cat_finalidad)

    cat_causa = categoria_info.get('causa')
    if campo_causa and cat_causa:
        causa_actual = str(registro.get(campo_causa, '') or '').strip()
        if causa_actual != cat_causa:
            registro[campo_causa] = cat_causa
            cambios[campo_causa] = (causa_actual, cat_causa)

    cat_cie10 = categoria_info.get('cie10_default')
    if cat_cie10:
        cie10_actual = str(registro.get(campo_cie10, '') or '').strip()
        if not cie10_actual:
            registro[campo_cie10] = cat_cie10
            cambios[campo_cie10] = ('', cat_cie10)

    nota_categoria = categoria_info.get('nota')
    if categoria in _CATEGORIAS_FINALIDAD_15_BC:
        ajuste = 'Ajuste BC: finalidad 15.'
        if nota_categoria:
            alertas.append(f'[Cat. {categoria}] {nota_categoria} {ajuste}')
        else:
            alertas.append(f'[Cat. {categoria}] {ajuste}')
    elif nota_categoria:
        alertas.append(f'[Cat. {categoria}] {nota_categoria}')

    return {
        'modificado': bool(cambios),
        'en_contrato': True,
        'alertas': alertas,
        'cambios': cambios,
    }


def _normalizar_campos_cie10(registro, campos):
    """Normaliza campos CIE10 in-place usando la misma regla central del motor."""
    for campo in campos:
        if campo not in registro:
            continue

        valor_actual = str(registro.get(campo, '') or '').strip()
        valor_normalizado = normalizar_cie10(valor_actual)
        if valor_normalizado != valor_actual:
            registro[campo] = valor_normalizado


def _construir_reporte_bc(tipo, registro, original, idx_servicio, alertas='', en_contrato=''):
    """Construye una fila de reporte BC con esquema compatible con el reporte actual."""
    reporte = {
        'Tipo': tipo,
        'Usuario_Documento': original.get('usuario_documento', ''),
        'Usuario_TipoDoc': original.get('usuario_tipodoc', ''),
        'Consecutivo_Servicio': idx_servicio,
        'Diagnostico_Original': original.get('diagnostico') or '(vacío)',
        'Diagnostico_Final': str(registro.get('codDiagnosticoPrincipal', '') or '').strip(),
        'Cambio_Diagnostico': 'Sí' if original.get('diagnostico') != str(registro.get('codDiagnosticoPrincipal', '') or '').strip() else 'No',
        'Finalidad_Original': original.get('finalidad', ''),
        'Finalidad_Nueva': str(registro.get('finalidadTecnologiaSalud', '') or '').strip(),
        'Cambio_Finalidad': 'Sí' if original.get('finalidad', '') != str(registro.get('finalidadTecnologiaSalud', '') or '').strip() else 'No',
        'Causa_Original': original.get('causa', ''),
        'Causa_Nueva': str(registro.get('causaMotivoAtencion', '') or '').strip(),
        'Cambio_Causa': 'Sí' if original.get('causa', '') != str(registro.get('causaMotivoAtencion', '') or '').strip() else 'No',
        'En_Contrato': en_contrato,
        'Alertas': alertas,
    }

    codigo_consulta = str(registro.get('codConsulta', '') or '').strip()
    codigo_proc = str(registro.get('codProcedimiento', '') or '').strip()
    if codigo_consulta:
        reporte['Codigo_Consulta'] = codigo_consulta
    if codigo_proc:
        reporte['Codigo_Procedimiento'] = codigo_proc

    return reporte


def _snapshot_registro(registro, campos):
    """Captura los valores actuales de un subconjunto de campos."""
    return {campo: registro.get(campo) for campo in campos if campo in registro}


def _resultado_desde_snapshot(original, registro, campos, alertas=None, en_contrato=True):
    """Construye un resultado estándar comparando el registro final contra un snapshot."""
    cambios = {}
    for campo in campos:
        anterior = original.get(campo)
        nuevo = registro.get(campo)
        if anterior != nuevo:
            cambios[campo] = (anterior, nuevo)

    return {
        'modificado': bool(cambios),
        'en_contrato': en_contrato,
        'alertas': alertas or [],
        'cambios': cambios,
    }


def _resolver_consulta_bc_registro(registro, config_eps=None):
    """Aplica las reglas BC de consulta sobre un dict de servicio."""
    campos = [
        'codDiagnosticoPrincipal',
        'codDiagnosticoRelacionado1',
        'codDiagnosticoRelacionado2',
        'codDiagnosticoRelacionado3',
        'finalidadTecnologiaSalud',
        'causaMotivoAtencion',
    ]
    original = _snapshot_registro(registro, campos)

    _normalizar_campos_cie10(
        registro,
        ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3'],
    )

    cod_consulta = str(registro.get('codConsulta', '') or '').strip()
    categoria_override = _bc_tiene_override(cod_consulta)
    if categoria_override:
        resultado = _aplicar_override_categoria_bc(registro, CAMPO_MAP_CONSULTAS, categoria_override, config_eps)
        return _resultado_desde_snapshot(original, registro, campos, resultado['alertas'], resultado['en_contrato'])

    alertas = []
    cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()

    if cod_diag in DIAGNOSTICOS_REEMPLAZAR_BC and cod_consulta != '890701':
        registro['codDiagnosticoPrincipal'] = 'Z718'
        cod_diag = 'Z718'
        alertas.append('Diagnóstico Z-PYP inválido en BC sustituido por Z718')
    elif not cod_diag or cod_diag in ('nan', 'None'):
        registro['codDiagnosticoPrincipal'] = 'Z719'
        cod_diag = 'Z719'
        alertas.append('Diagnóstico vacío asignado por defecto')

    registro['finalidadTecnologiaSalud'] = '44'
    if cod_diag == 'Y050':
        registro['causaMotivoAtencion'] = '32'
    elif cod_diag and cod_diag[0].upper() in ('S', 'T', 'W'):
        registro['causaMotivoAtencion'] = '26'
    else:
        registro['causaMotivoAtencion'] = '38'

    return _resultado_desde_snapshot(original, registro, campos, alertas)


def _resolver_procedimiento_bc_registro(registro, config_eps=None):
    """Aplica las reglas BC de procedimiento sobre un dict de servicio."""
    campos = [
        'codDiagnosticoPrincipal',
        'codDiagnosticoRelacionado',
        'codComplicacion',
        'finalidadTecnologiaSalud',
    ]
    original = _snapshot_registro(registro, campos)

    _normalizar_campos_cie10(
        registro,
        ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado', 'codComplicacion'],
    )

    cod_proc = str(registro.get('codProcedimiento', '') or '').strip()
    categoria_override = _bc_tiene_override(cod_proc)
    if categoria_override:
        resultado = _aplicar_override_categoria_bc(registro, CAMPO_MAP_PROCEDIMIENTOS, categoria_override, config_eps)
        return _resultado_desde_snapshot(original, registro, campos, resultado['alertas'], resultado['en_contrato'])

    alertas = []
    cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()
    if not cod_diag or cod_diag in ('nan', 'None'):
        registro['codDiagnosticoPrincipal'] = 'Z018'
        registro['finalidadTecnologiaSalud'] = '15'
        alertas.append('Diagnóstico vacío asignado por defecto')

    if cod_proc.startswith('5DS') or cod_proc.startswith('865'):
        registro['finalidadTecnologiaSalud'] = '16'

    return _resultado_desde_snapshot(original, registro, campos, alertas)


def _resolver_medicamento_bc_registro(registro):
    """Aplica las reglas BC de medicamentos sobre un dict de servicio."""
    campos = ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado']
    original = _snapshot_registro(registro, campos)

    _normalizar_campos_cie10(registro, ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado'])

    alertas = []
    cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()
    if cod_diag in DIAGNOSTICOS_REEMPLAZAR_BC:
        registro['codDiagnosticoPrincipal'] = 'Z718'
        alertas.append('Diagnóstico Z-PYP inválido en BC sustituido por Z718')

    return _resultado_desde_snapshot(original, registro, campos, alertas)


COMPUESTOS_JSON_SUSTITUCIONES_Z = {
    'Z321': ('23', '42'),
    'Z340': ('23', '42'),
    'Z348': ('23', '42'),
    'Z349': ('23', '42'),
    'Z350': ('23', '42'),
    'Z351': ('23', '42'),
    'Z352': ('23', '42'),
    'Z353': ('23', '42'),
    'Z354': ('23', '42'),
    'Z355': ('23', '42'),
    'Z356': ('23', '42'),
    'Z357': ('23', '42'),
    'Z358': ('23', '42'),
    'Z359': ('23', '42'),
    'Z300': ('19', '40'),
    'Z301': ('19', '40'),
    'Z304': ('19', '40'),
    'Z305': ('19', '40'),
    'Z308': ('19', '40'),
    'Z309': ('19', '40'),
    'Z000': ('11', '40'),
    'Z001': ('11', '40'),
    'Z002': ('11', '40'),
    'Z003': ('11', '40'),
    'Z010': ('11', '40'),
    'Z011': ('11', '40'),
    'Z012': ('11', '40'),
    'Z018': ('11', '40'),
    'Z019': ('11', '40'),
    'Z761': ('11', '40'),
    'Z108': ('11', '40'),
    'Z123': ('11', '40'),
    'Z124': ('11', '40'),
    'Z125': ('11', '40'),
    'Z392': ('25', '42'),
    'Z972': ('11', '40'),
    'Z762': ('11', '40'),
    'Z316': ('22', '40'),
    'Z318': ('22', '40'),
    'Z319': ('22', '40'),
    'Z313': ('22', '40'),
    'Z381': ('11', '40'),
    'Z718': ('21', '40'),
    'Z370': ('11', '40'),
}


COMPUESTOS_DF_SUSTITUCIONES_Z = {
    'Z002': ('11', '40'),
    'Z321': ('23', '42'),
    'Z340': ('23', '42'),
    'Z348': ('23', '42'),
    'Z349': ('23', '42'),
    'Z350': ('23', '42'),
    'Z351': ('23', '42'),
    'Z352': ('23', '42'),
    'Z353': ('23', '42'),
    'Z354': ('23', '42'),
    'Z355': ('23', '42'),
    'Z356': ('23', '42'),
    'Z357': ('23', '42'),
    'Z358': ('23', '42'),
    'Z359': ('22', '42'),
    'Z300': ('19', '40'),
    'Z301': ('19', '40'),
    'Z304': ('19', '40'),
    'Z305': ('19', '40'),
    'Z308': ('19', '40'),
    'Z309': ('19', '40'),
    'Z000': ('11', '40'),
    'Z001': ('11', '40'),
    'Z003': ('11', '40'),
    'Z010': ('44', '40'),
    'Z011': ('11', '40'),
    'Z012': ('11', '40'),
    'Z018': ('44', '40'),
    'Z019': ('11', '40'),
    'Z761': ('11', '40'),
    'Z108': ('11', '40'),
    'Z123': ('11', '40'),
    'Z124': ('11', '40'),
    'Z125': ('11', '40'),
    'Z392': ('25', '42'),
    'Z972': ('11', '40'),
    'Z762': ('11', '40'),
    'Z316': ('22', '40'),
    'Z318': ('22', '40'),
    'Z319': ('22', '40'),
    'Z313': ('22', '40'),
    'Z381': ('11', '40'),
    'Z370': ('11', '40'),
}


def _resolver_consulta_compuestos_registro(registro, sustituciones_z, config_eps=None):
    """Aplica la lógica de consultas de compuestos regida solo por sus tablas y reglas propias."""
    campos = [
        'codDiagnosticoPrincipal',
        'codDiagnosticoRelacionado1',
        'codDiagnosticoRelacionado2',
        'codDiagnosticoRelacionado3',
        'finalidadTecnologiaSalud',
        'causaMotivoAtencion',
    ]
    original = _snapshot_registro(registro, campos)

    _normalizar_campos_cie10(
        registro,
        ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado1', 'codDiagnosticoRelacionado2', 'codDiagnosticoRelacionado3'],
    )

    cod_consulta = str(registro.get('codConsulta', '') or '').strip()
    cups_contrato = config_eps.get('cups_contrato', set()) if config_eps else set()
    if cups_contrato and cod_consulta and cod_consulta not in cups_contrato:
        return _resultado_desde_snapshot(original, registro, campos, [], False)

    cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()
    if not cod_diag or cod_diag.lower() in ('nan', 'null', 'none'):
        if cod_consulta in ('890203', '890303'):
            registro['codDiagnosticoPrincipal'] = 'Z012'
            registro['finalidadTecnologiaSalud'] = '11'
            registro['causaMotivoAtencion'] = '40'
        elif cod_consulta == '890703':
            registro['codDiagnosticoPrincipal'] = 'K021'
            registro['finalidadTecnologiaSalud'] = '38'

        return _resultado_desde_snapshot(original, registro, campos, [])

    cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()
    if cod_diag.startswith('Z'):
        reemplazo = sustituciones_z.get(cod_diag)
        if reemplazo is not None:
            registro['finalidadTecnologiaSalud'] = reemplazo[0]
            registro['causaMotivoAtencion'] = reemplazo[1]
        else:
            registro['finalidadTecnologiaSalud'] = '44'
            registro['causaMotivoAtencion'] = '38'
    elif cod_diag[0].upper() in ('S', 'T', 'W'):
        registro['causaMotivoAtencion'] = '26'
        registro['finalidadTecnologiaSalud'] = '44'
    else:
        registro['finalidadTecnologiaSalud'] = '44'
        registro['causaMotivoAtencion'] = '38'

    return _resultado_desde_snapshot(original, registro, campos, [])


def _resolver_procedimiento_compuestos_registro(
    registro,
    codigos_proc_z258,
    tabla_cups_finalidad,
    diagnosticos_consulta_fecha=None,
    config_eps=None,
):
    """Aplica la lógica de procedimientos de compuestos regida solo por sus tablas y reglas propias."""
    campos = [
        'codDiagnosticoPrincipal',
        'codDiagnosticoRelacionado',
        'codComplicacion',
        'finalidadTecnologiaSalud',
    ]
    original = _snapshot_registro(registro, campos)

    _normalizar_campos_cie10(registro, ['codDiagnosticoPrincipal', 'codDiagnosticoRelacionado', 'codComplicacion'])

    cod_proc = str(registro.get('codProcedimiento', '') or '').strip()
    cups_contrato = config_eps.get('cups_contrato', set()) if config_eps else set()
    if cups_contrato and cod_proc and cod_proc not in cups_contrato:
        return _resultado_desde_snapshot(original, registro, campos, [], False)

    cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()
    if not cod_diag or cod_diag == 'nan':
        if cod_proc in codigos_proc_z258:
            registro['codDiagnosticoPrincipal'] = 'Z258'
            registro['finalidadTecnologiaSalud'] = '14'
        elif diagnosticos_consulta_fecha:
            registro['codDiagnosticoPrincipal'] = diagnosticos_consulta_fecha[0]
        elif cod_proc in tabla_cups_finalidad:
            cups_data = tabla_cups_finalidad[cod_proc]
            dx = cups_data.get('DX')
            finalidad = cups_data.get('FINALIDAD')
            if dx:
                registro['codDiagnosticoPrincipal'] = dx
            if finalidad:
                registro['finalidadTecnologiaSalud'] = finalidad

    if cod_proc.startswith('5DS') or cod_proc.startswith('865'):
        registro['finalidadTecnologiaSalud'] = '16'

    return _resultado_desde_snapshot(original, registro, campos, [])


def aplicar_cambios_bc_json(datos_json, config_eps=None, generar_reporte=False):
    """
    Aplica al JSON RIPS BC la misma lógica clínica centralizada del módulo BC.

    Reglas reflejadas en RIPS:
            - Overrides autoritativos por categoría CUPS (con finalidad 15 en BC para
                LAB_CARDIOMETABOLICO y DETECCION_TEMPRANA_GENERAL)
      - Consultas BC: Z-PYP inválidos → Z718, vacío → Z719, trauma/Y050 → causa específica
      - Procedimientos BC: vacío → Z018 y finalidad 15; 5DS*/865* → finalidad 16
      - Medicamentos BC: Z-PYP inválidos → Z718
      - Urgencias / hospitalización: truncamiento uniforme de diagnósticos

    Args:
        datos_json: Diccionario RIPS completo.
        config_eps: Configuración de EPS; se usa solo cuando aplica override por motor.
        generar_reporte: Si True, retorna también detalle de cambios.

    Returns:
        dict o tuple(dict, list[dict]) según generar_reporte.
    """
    cambios_bc = [] if generar_reporte else None

    usuarios = datos_json.get('usuarios', [])

    for usuario in usuarios:
        num_doc_usuario = usuario.get('numDocumentoIdentificacion', '')
        tipo_doc_usuario = usuario.get('tipoDocumentoIdentificacion', '')
        servicios = usuario.get('servicios', {})

        for idx_consulta, consulta in enumerate(servicios.get('consultas', []), 1):
            original = {
                'usuario_documento': num_doc_usuario,
                'usuario_tipodoc': tipo_doc_usuario,
                'diagnostico': str(consulta.get('codDiagnosticoPrincipal', '') or '').strip(),
                'finalidad': str(consulta.get('finalidadTecnologiaSalud', '') or '').strip(),
                'causa': str(consulta.get('causaMotivoAtencion', '') or '').strip(),
            }
            resultado = _resolver_consulta_bc_registro(consulta, config_eps)

            if generar_reporte:
                reporte = _construir_reporte_bc(
                    'CONSULTA',
                    consulta,
                    original,
                    idx_consulta,
                    alertas='; '.join(resultado['alertas']),
                    en_contrato='Sí' if resultado['en_contrato'] else 'No',
                )
                if (
                    reporte['Cambio_Diagnostico'] == 'Sí'
                    or reporte['Cambio_Finalidad'] == 'Sí'
                    or reporte['Cambio_Causa'] == 'Sí'
                    or reporte['Alertas']
                ):
                    cambios_bc.append(reporte)

        for idx_proc, procedimiento in enumerate(servicios.get('procedimientos', []), 1):
            original = {
                'usuario_documento': num_doc_usuario,
                'usuario_tipodoc': tipo_doc_usuario,
                'diagnostico': str(procedimiento.get('codDiagnosticoPrincipal', '') or '').strip(),
                'finalidad': str(procedimiento.get('finalidadTecnologiaSalud', '') or '').strip(),
                'causa': '',
            }
            resultado = _resolver_procedimiento_bc_registro(procedimiento, config_eps)

            if generar_reporte:
                reporte = _construir_reporte_bc(
                    'PROCEDIMIENTO',
                    procedimiento,
                    original,
                    idx_proc,
                    alertas='; '.join(resultado['alertas']),
                    en_contrato='Sí' if resultado['en_contrato'] else 'No',
                )
                if (
                    reporte['Cambio_Diagnostico'] == 'Sí'
                    or reporte['Cambio_Finalidad'] == 'Sí'
                    or reporte['Alertas']
                ):
                    cambios_bc.append(reporte)

        for idx_med, medicamento in enumerate(servicios.get('medicamentos', []), 1):
            original = {
                'usuario_documento': num_doc_usuario,
                'usuario_tipodoc': tipo_doc_usuario,
                'diagnostico': str(medicamento.get('codDiagnosticoPrincipal', '') or '').strip(),
                'finalidad': '',
                'causa': '',
            }
            resultado = _resolver_medicamento_bc_registro(medicamento)

            if generar_reporte:
                reporte = _construir_reporte_bc(
                    'MEDICAMENTO',
                    medicamento,
                    original,
                    idx_med,
                    alertas='; '.join(resultado['alertas']),
                )
                if reporte['Cambio_Diagnostico'] == 'Sí' or reporte['Alertas']:
                    cambios_bc.append(reporte)

        for urgencia in servicios.get('urgencias', []):
            _normalizar_campos_cie10(
                urgencia,
                [
                    'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
                    'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2',
                    'codDiagnosticoRelacionadoE3', 'codDiagnosticoCausaMuerte',
                ],
            )

        for hospitalizacion in servicios.get('hospitalizacion', []):
            _normalizar_campos_cie10(
                hospitalizacion,
                [
                    'codDiagnosticoPrincipal', 'codDiagnosticoPrincipalE',
                    'codDiagnosticoRelacionadoE1', 'codDiagnosticoRelacionadoE2',
                    'codDiagnosticoRelacionadoE3', 'codDiagnosticoCausaMuerte',
                    'codComplicacion',
                ],
            )

    if generar_reporte:
        return datos_json, cambios_bc
    return datos_json


# ---------------------------------------------------------------------------
# Clasificación clínica PYP sobre DataFrames
# ---------------------------------------------------------------------------

def aplicar_clasificacion_df_pyp(df_consultas, df_procedimientos):
    """
    Aplica la clasificación clínica PYP a DataFrames de consultas y procedimientos.

    Reglas aplicadas:
      - Diagnóstico vacío/no-Z en consultas   → Z001 / Z718 (fallback)
      - Diagnóstico vacío/no-Z en procs       → Z012 / Z258 / Z018 / Z718 según tipo de CUPS
      - Asignación de finalidad + causa       → clasificar_pyp_por_cie10
      - Procedimientos 997xxx                 → finalidad '14' (prevalece)

    Modifica los DataFrames in-place y los retorna.
    """
    import pandas as pd

    cambios_diag = []

    if not df_consultas.empty:
        for idx, row in df_consultas.iterrows():
            # Si el CUPS ya fue gestionado por motor_logico (Paso 0.5), respetar el resultado.
            _cups_c = str(row.get('codConsulta', '') or '').strip()
            _cat_c  = get_categoria_cups(_cups_c) if _cups_c else None
            if _cat_c is not None and _cat_c['categoria'] in _CATEGORIAS_OVERRIDE:
                continue

            orig = str(row['codDiagnosticoPrincipal']).strip() if pd.notna(row['codDiagnosticoPrincipal']) else ''
            orig_finalidad = str(row.get('finalidadTecnologiaSalud', '')).strip() if pd.notna(row.get('finalidadTecnologiaSalud', '')) else ''
            orig_causa = str(row.get('causaMotivoAtencion', '')).strip() if pd.notna(row.get('causaMotivoAtencion', '')) else ''

            if not orig:
                cod_diag = 'Z001'
                df_consultas.at[idx, 'codDiagnosticoPrincipal'] = cod_diag
            elif not orig.startswith('Z'):
                cod_diag = 'Z718'
                df_consultas.at[idx, 'codDiagnosticoPrincipal'] = cod_diag
            else:
                cod_diag = orig

            finalidad_pyp, causa_pyp = clasificar_pyp_por_cie10(cod_diag)
            df_consultas.at[idx, 'finalidadTecnologiaSalud'] = finalidad_pyp
            df_consultas.at[idx, 'causaMotivoAtencion'] = causa_pyp

            if cod_diag != orig:
                cambios_diag.append({
                    'Tipo':                'CONSULTA',
                    'Usuario_Documento':   str(row.get('numDocumento_usuario', '')),
                    'Usuario_TipoDoc':     str(row.get('tipoDocumento_usuario', '')),
                    'Consecutivo_Servicio': row.get('consecutivo_consulta', idx),
                    'Diagnostico_Original': orig or '(vacío)',
                    'Diagnostico_Final':   cod_diag,
                    'Finalidad_Original':  orig_finalidad,
                    'Finalidad_Nueva':     finalidad_pyp,
                    'Causa_Original':      orig_causa,
                    'Causa_Nueva':         causa_pyp,
                    'En_Contrato':         '',
                    'Alertas':             'Diagnóstico vacío asignado por defecto' if not orig else 'Diagnóstico no-Z sustituido',
                })

    if not df_procedimientos.empty:
        for idx, row in df_procedimientos.iterrows():
            cod_proc = str(row['codProcedimiento']).strip() if pd.notna(row['codProcedimiento']) else ''
            # Si el CUPS ya fue gestionado por motor_logico (Paso 0.5), respetar el resultado.
            _cat_p = get_categoria_cups(cod_proc) if cod_proc else None
            if _cat_p is not None and _cat_p['categoria'] in _CATEGORIAS_OVERRIDE:
                continue

            orig = str(row['codDiagnosticoPrincipal']).strip() if pd.notna(row['codDiagnosticoPrincipal']) else ''
            orig_finalidad = str(row.get('finalidadTecnologiaSalud', '')).strip() if pd.notna(row.get('finalidadTecnologiaSalud', '')) else ''

            if not orig:
                if cod_proc.startswith('997'):
                    cod_diag = 'Z012'
                elif cod_proc in CODIGOS_PROC_Z258_PYP:
                    cod_diag = 'Z258'
                else:
                    cod_diag = 'Z018'
                df_procedimientos.at[idx, 'codDiagnosticoPrincipal'] = cod_diag
            elif not orig.startswith('Z'):
                cod_diag = 'Z718'
                df_procedimientos.at[idx, 'codDiagnosticoPrincipal'] = cod_diag
            else:
                cod_diag = orig

            finalidad_pyp, _ = clasificar_pyp_por_cie10(cod_diag)
            df_procedimientos.at[idx, 'finalidadTecnologiaSalud'] = finalidad_pyp

            # 997xxx → detección temprana (prevalece sobre clasificación familiar)
            if cod_proc.startswith('997'):
                df_procedimientos.at[idx, 'finalidadTecnologiaSalud'] = '14'
                finalidad_pyp = '14'

            if cod_diag != orig:
                cambios_diag.append({
                    'Tipo':                'PROCEDIMIENTO',
                    'Usuario_Documento':   str(row.get('numDocumento_usuario', '')),
                    'Usuario_TipoDoc':     str(row.get('tipoDocumento_usuario', '')),
                    'Consecutivo_Servicio': row.get('consecutivo_procedimiento', idx),
                    'Codigo_Procedimiento': cod_proc,
                    'Diagnostico_Original': orig or '(vacío)',
                    'Diagnostico_Final':   cod_diag,
                    'Finalidad_Original':  orig_finalidad,
                    'Finalidad_Nueva':     finalidad_pyp,
                    'Causa_Original':      '',
                    'Causa_Nueva':         '',
                    'En_Contrato':         '',
                    'Alertas':             'Diagnóstico vacío asignado por defecto' if not orig else 'Diagnóstico no-Z sustituido',
                })

    return df_consultas, df_procedimientos, cambios_diag


# ---------------------------------------------------------------------------
# Clasificación clínica BC sobre DataFrames
# ---------------------------------------------------------------------------

def aplicar_clasificacion_df_bc(df_consultas, df_procedimientos, df_medicamentos):
    """
    Aplica las reglas clínicas BC a DataFrames de consultas, procedimientos
    y medicamentos.

    Reglas aplicadas:
      Consultas:
        - Códigos Z de PYP/maternidad (DIAGNOSTICOS_REEMPLAZAR_BC) → Z718
          (excepción: codConsulta 890701 no se toca)
                - Diagnóstico vacío → Z719, finalidad 44, causa 38
        - Y050              → finalidad 44, causa 32
        - S / T / W         → finalidad 44, causa 26
        - Resto             → finalidad 44, causa 38
      Medicamentos:
        - Misma sustitución DIAGNOSTICOS_REEMPLAZAR_BC → Z718
      Procedimientos:
        - Diagnóstico vacío → Z018, finalidad 15
        - 5DS / 865         → finalidad 16 (prevalece)

    Modifica los DataFrames in-place y los retorna.
    """
    import pandas as pd

    cambios_diag = []

    # ------------------------------------------------------------------
    # Consultas: reemplazar Z-PYP por Z718 y registrar cambio
    # ------------------------------------------------------------------
    if not df_consultas.empty:
        for idx, row in df_consultas.iterrows():
            orig = str(row['codDiagnosticoPrincipal']).strip() if pd.notna(row['codDiagnosticoPrincipal']) else ''
            cod_consulta = str(row.get('codConsulta', '')).strip()

            if orig.startswith('Z') and cod_consulta == '890701':
                continue

            _cat_bc = get_categoria_cups(cod_consulta) if cod_consulta else None
            if _cat_bc is not None and _cat_bc['categoria'] in _CATEGORIAS_OVERRIDE:
                continue

            if orig in DIAGNOSTICOS_REEMPLAZAR_BC:
                df_consultas.at[idx, 'codDiagnosticoPrincipal'] = 'Z718'
                cambios_diag.append({
                    'Tipo':                'CONSULTA',
                    'Usuario_Documento':   str(row.get('numDocumento_usuario', '')),
                    'Usuario_TipoDoc':     str(row.get('tipoDocumento_usuario', '')),
                    'Consecutivo_Servicio': row.get('consecutivo_consulta', idx),
                    'Diagnostico_Original': orig,
                    'Diagnostico_Final':   'Z718',
                    'Finalidad_Original':  '',
                    'Finalidad_Nueva':     '',
                    'Causa_Original':      '',
                    'Causa_Nueva':         '',
                    'En_Contrato':         '',
                    'Alertas':             'Diagnóstico Z-PYP inválido en BC sustituido por Z718',
                })

    # Medicamentos: mismo reemplazo
    if not df_medicamentos.empty and 'codDiagnosticoPrincipal' in df_medicamentos.columns:
        for idx, row in df_medicamentos.iterrows():
            orig = str(row['codDiagnosticoPrincipal']).strip() if pd.notna(row['codDiagnosticoPrincipal']) else ''
            if orig in DIAGNOSTICOS_REEMPLAZAR_BC:
                df_medicamentos.at[idx, 'codDiagnosticoPrincipal'] = 'Z718'
                cambios_diag.append({
                    'Tipo':                'MEDICAMENTO',
                    'Usuario_Documento':   str(row.get('numDocumento_usuario', '')),
                    'Usuario_TipoDoc':     str(row.get('tipoDocumento_usuario', '')),
                    'Consecutivo_Servicio': row.get('consecutivo_medicamento', idx),
                    'Diagnostico_Original': orig,
                    'Diagnostico_Final':   'Z718',
                    'Finalidad_Original':  '',
                    'Finalidad_Nueva':     '',
                    'Causa_Original':      '',
                    'Causa_Nueva':         '',
                    'En_Contrato':         '',
                    'Alertas':             'Diagnóstico Z-PYP inválido en BC sustituido por Z718',
                })

    # ------------------------------------------------------------------
    # Consultas: finalidad y causa BC (registrar asignación de Z719 si vacío)
    # ------------------------------------------------------------------
    if not df_consultas.empty:
        for idx, row in df_consultas.iterrows():
            registro = row.to_dict()
            resultado = _resolver_consulta_bc_registro(registro)
            for campo, valor in registro.items():
                if campo in df_consultas.columns:
                    df_consultas.at[idx, campo] = valor

            cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()

            if not cod_diag or cod_diag == 'Z719':
                cambios_diag.append({
                    'Tipo':                'CONSULTA',
                    'Usuario_Documento':   str(row.get('numDocumento_usuario', '')),
                    'Usuario_TipoDoc':     str(row.get('tipoDocumento_usuario', '')),
                    'Consecutivo_Servicio': row.get('consecutivo_consulta', idx),
                    'Diagnostico_Original': '(vacío)',
                    'Diagnostico_Final':   'Z719',
                    'Finalidad_Original':  str(row.get('finalidadTecnologiaSalud', '')),
                    'Finalidad_Nueva':     '44',
                    'Causa_Original':      str(row.get('causaMotivoAtencion', '')),
                    'Causa_Nueva':         '38',
                    'En_Contrato':         '',
                    'Alertas':             'Diagnóstico vacío asignado por defecto',
                })

    # ------------------------------------------------------------------
    # Procedimientos: fallback diagnóstico y reglas de finalidad
    # ------------------------------------------------------------------
    if not df_procedimientos.empty:
        for idx, row in df_procedimientos.iterrows():
            registro = row.to_dict()
            _resolver_procedimiento_bc_registro(registro)
            for campo, valor in registro.items():
                if campo in df_procedimientos.columns:
                    df_procedimientos.at[idx, campo] = valor

            cod_diag = str(registro.get('codDiagnosticoPrincipal', '') or '').strip()
            if cod_diag == 'Z018':
                cod_proc = str(registro.get('codProcedimiento', '') or '').strip()
                cambios_diag.append({
                    'Tipo':                'PROCEDIMIENTO',
                    'Usuario_Documento':   str(row.get('numDocumento_usuario', '')),
                    'Usuario_TipoDoc':     str(row.get('tipoDocumento_usuario', '')),
                    'Consecutivo_Servicio': row.get('consecutivo_procedimiento', idx),
                    'Codigo_Procedimiento': cod_proc,
                    'Diagnostico_Original': '(vacío)',
                    'Diagnostico_Final':   'Z018',
                    'Finalidad_Original':  str(row.get('finalidadTecnologiaSalud', '')),
                    'Finalidad_Nueva':     '15',
                    'Causa_Original':      '',
                    'Causa_Nueva':         '',
                    'En_Contrato':         '',
                    'Alertas':             'Diagnóstico vacío asignado por defecto',
                })

    return df_consultas, df_procedimientos, df_medicamentos, cambios_diag
