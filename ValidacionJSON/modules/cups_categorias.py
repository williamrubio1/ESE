"""
Categorización de CUPS contratados que NO están en la Ficha Técnica RPYMS.

Cada CUPS contratado que no aparece en los indicadores RPYMS pertenece a una de
seis categorías que determinan cómo debe registrarse en el RIPS.

Referencia normativa: Res 3280/2018, Res 2275/2023, Ficha Técnica RPYMS 2026.
"""

# ============================================================================
# CATEGORÍA 1 — Morbilidad Odontológica
# Exodoncias, obturaciones, endodoncias, detartraje subgingival.
# Finalidad: 16 (Tratamiento)   Causa: 38 (Enfermedad General)
# ¿Cuenta en RPYMS? Solo RPYMS338X (denominador)
# ============================================================================
CUPS_MORBILIDAD_ODONTOLOGICA = {
    '230101', '230102',   # Exodoncias simples
    '230201', '230202',   # Exodoncias con alveoloplastia
    '232101', '232102',   # Obturaciones
    '237301', '237302', '237303',  # Endodoncias
    '240200',             # Detartraje SUBgingival — NO confundir con 997301 (SUPRAgingival)
}

# ============================================================================
# CATEGORÍA 2 — Apoyo Diagnóstico General
# Se ordenan desde una consulta principal. No cuentan en PyP.
# Finalidad: 15 (Diagnóstico)   Causa: 38 (Enfermedad General)
# CIE-10: diagnóstico de la consulta que lo originó.
# ============================================================================
CUPS_APOYO_DIAGNOSTICO = {
    '902045', '902207', '902208',
    '903801', '903856',
    '907002', '907004',
    '903864',  # Sodio en suero — laboratorio de morbilidad general
    '901304',  # Examen directo fresco — laboratorio de morbilidad
    '898001',  # Código sin esp. en Ficha Técnica — apoyo diagnóstico provisional
    # Según Sigires: finalidad 15, Z017 (diagnóstico, no cuentan en PyP)
    '906249',  # VIH 1 y 2 anticuerpos — fin 15 siempre (retirado de DOBLE_PROPOSITO)
    '904508',  # Prueba de embarazo BHCG — fin 15 siempre (retirado de DOBLE_PROPOSITO)
    '902213',  # Hemoglobina — fin 15 (Sigires: Z017)
}
# Radiografías: prefijos 870xxx–873xxx
PREFIJOS_RADIOGRAFIAS = ('870', '871', '872', '873')

# ============================================================================
# CATEGORÍA 3 — Ruta Materno Perinatal (RMP)
# Tienen ficha técnica propia. No cuentan en RPYMS PyP.
# Finalidad: 23 (Cuidado prenatal)   Causa: 42 (Materno Perinatal)
# CIE-10 sugerido si vacío: Z340 (supervisión embarazo normal)
# ============================================================================
CUPS_RUTA_MATERNO_PERINATAL = {
    '881431', '881432',
    '901107', '901235',
    '903844', '903883',
    '906915',             # Prueba no treponémica — también categoría 5 (doble propósito)
    '911015', '911016',
    '129B01', '130B01', '130B02',
    '933700',             # Entrenamiento pre/peri/post parto — componente Ruta Materno Perinatal
}

# ============================================================================
# CATEGORÍA 4 — Urgencias y Soporte Hospitalario
# Finalidad: 15 o 16 según el caso   Causa: según motivo real
# No cuentan en RPYMS directamente (pueden aparecer en denominadores de tasas).
# ============================================================================
CUPS_URGENCIAS_SOPORTE = {
    '890701',  # Consulta de urgencias
    '890703',  # Consulta odontológica de urgencias
    '5DSB01',  # Procedimiento de soporte
    '869500',  # Sala de observación
    '961601',  # Sondaje vesical
    '976501',  # Otro soporte hospitalario
}

# ============================================================================
# CATEGORÍA 5 — Doble Propósito
# La finalidad define si cuentan en indicadores PyP o no.
# Requieren capacitación a IPS sobre uso correcto de finalidad.
# ============================================================================
CUPS_DOBLE_PROPOSITO = {
    # NOTA: 904508 y 906249 fueron migrados a CUPS_APOYO_DIAGNOSTICO
    # (finalidad siempre 15 según Sigires). Ya no son doble propósito.
    # NOTA: 906039 migrado a CUPS_DETECCION_TEMPRANA_GENERAL (fin 12, Z114)
    # ya que en SIGIRES siempre aplica como tamizaje PYP, no como morbilidad.

    '906915': {
        'descripcion':          'Prueba no treponémica (sífilis)',
        'finalidad_pyp':        '12',
        'indicador_si_pyp':     'RPYMS348X',
        'finalidad_morbilidad': '15',
    },
    '903426': {
        'descripcion':          'Hemoglobina glicosilada',
        'finalidad_pyp':        '12',
        'indicador_si_pyp':     'Ruta Cardiometabólica',
        'finalidad_morbilidad': '15',
    },
    # NOTA: 907008 (sangre oculta) fue migrado a CUPS_DETECCION_TEMPRANA_GENERAL
    # para fijar Z120/fin12 de forma determinista. Si se necesita comportamiento
    # doble propósito explícito, restaurar la entrada y eliminar de DETECCION_TEMPRANA_GENERAL.
}

# ============================================================================
# CATEGORÍA 6 — Vacunas Especiales y Componentes
# Finalidad: 14 (Detección temprana/vacunación)   Causa: 40   CIE-10: Z279
# Requieren verificación de lineamiento PAI antes de registrar.
# ============================================================================
CUPS_VACUNAS_ESPECIALES = {
    '993506', '993507', '993508',  # SRP individuales (verificar duplicidad con 993522)
    '993103',   # Meningococo — solo bajo lineamiento específico
    '993104',   # Haemophilus influenza B — verificar inclusión en pentavalente 993130
    '993106',   # Vacuna Neumococo — fin 14 según Sigires (Z258); retirado de CODIGOS_PROC_Z258_PYP
    '993505',   # Rabia post-exposición
    '995201',   # Otra vacunación PAI (comodín — usar solo si no hay CUPS específico)
    '997103',   # Flúor en gel — DESACTUALIZADO; Res 2275/2023 establece 997106
}

# ============================================================================
# CATEGORÍA 7 — Vacunas PAI (Programa Ampliado de Inmunizaciones)
# Vacunas del esquema regular PAI. Finalidad: 14  Causa: 40  CIE-10: Z279
# Nota: 993120 (TD) en gestantes debe usar causa 42 — depende del contexto.
# ============================================================================
CUPS_VACUNA_PAI = {
    '993102': {
        'descripcion': 'Vacuna BCG (tuberculosis) — recién nacidos',
        'indicador':   'RPYMS272X / RPYMS589X',
    },
    '993120': {
        'descripcion': 'Vacuna TD (Tétanos-Difteria) — MEF y gestantes',
        'indicador':   'RPYMS91X',
    },
    '993122': {
        'descripcion': 'Vacuna DPT (Difteria-Tos ferina-Tétanos)',
        'indicador':   'RPYMS34X / RPYMS106X / RPYMS107X',
    },
    '993124': {
        'descripcion': 'Vacuna Tetravalente (DPT-HepB)',
        'indicador':   'RPYMS34X / RPYMS106X',
    },
    '993130': {
        'descripcion': 'Vacuna Pentavalente (DPT-HepB-Hib)',
        'indicador':   'RPYMS34X / RPYMS106X / RPYMS107X',
    },
    '993501': {
        'descripcion': 'Vacuna Poliomielitis (VOP o IVP)',
        'indicador':   'RPYMS34X / RPYMS289X',
    },
    '993502': {
        'descripcion': 'Vacuna Hepatitis A',
        'indicador':   'RPYMS285X',
    },
    '993504': {
        'descripcion': 'Vacuna Fiebre Amarilla',
        'indicador':   'RPYMS288X / RPYMS295X / RPYMS621X / RPYMS623X',
    },
    '993509': {
        'descripcion': 'Vacuna Varicela',
        'indicador':   'RPYMS292X',
    },
    '993510': {
        'descripcion': 'Vacuna Influenza — menores 2 años y mayores 60 años (en gestantes: causa 42)',
        'indicador':   'RPYMS93X / RPYMS309X / RPYMS310X',
    },
    '993512': {
        'descripcion': 'Vacuna Rotavirus',
        'indicador':   'RPYMS34X / RPYMS106X',
    },
    '993513': {
        'descripcion': 'Vacuna VPH (Virus Papiloma Humano) — niñas 9–17 años + niños 9 años',
        'indicador':   'RPYMS90X / RPYMS384X / RPYMS390X',
    },
    '993520': {
        'descripcion': 'Vacuna SR doble viral (Sarampión-Rubéola)',
        'indicador':   'RPYMS296X',
    },
    '993522': {
        'descripcion': 'Vacuna Triple Viral SRP (Sarampión-Paperas-Rubéola)',
        'indicador':   'RPYMS34X / RPYMS107X',
    },
    '993503': {
        'descripcion': 'Vacuna Hepatitis B monovalente (sola, no en pentavalente)',
        'indicador':   'RPYMS34X / RPYMS106X',
    },
}

# ============================================================================
# CATEGORÍA 8 — Protección Específica Salud Oral
# Procedimientos preventivos orales del esquema RPYMS.
# Finalidad: 14 (Protección Específica)  Causa: 40  CIE-10: varía por CUPS.
# ============================================================================
CUPS_SALUD_ORAL_PE = {
    '997002': {
        'descripcion':   'Control de placa dental (profilaxis bacteriana)',
        'cie10_default': 'K021',
        'indicador':     'RPYMS19X / RPYMS20X / RPYMS21X / RPYMS35X',
    },
    '997106': {
        'descripcion':   'Topicación de flúor en barniz (vigente Res 2275/2023)',
        'cie10_default': 'K003',
        'indicador':     'RPYMS30X / RPYMS30aX',
    },
    '997107': {
        'descripcion':   'Aplicación de sellantes (3–15 años)',
        'cie10_default': 'Z012',
        'indicador':     'RPYMS31X / RPYMS37X',
    },
    '997301': {
        'descripcion':   'Detartraje supragingival (12 años y más)',
        'cie10_default': 'K051',
        'indicador':     'RPYMS32X / RPYMS38X',
    },
}

# ============================================================================
# CATEGORÍA 9 — Laboratorios de Tamizaje Cardiometabólico
# Finalidad: 12 (Detección Temprana)  Causa: 40  CIE-10: Z108
# Cuentan en RPYMS16X–18X según curso de vida.
# ============================================================================
CUPS_LAB_CARDIOMETABOLICO = {
    '903815',  # Colesterol HDL
    '903816',  # Colesterol LDL semiautomatizado
    '903818',  # Colesterol total
    '903841',  # Glucosa en suero
    '903895',  # Creatinina en suero
    '907106',  # Uroanálisis
}

# ============================================================================
# CATEGORÍA 10 — Educación en Salud Grupal (Intervención Colectiva)
# Finalidad: 42  Causa: 41  CIE-10: Z718. Cuentan en RPYMS389X.
# ============================================================================
CUPS_EDUCACION_GRUPAL = {
    '990101',  # Educación grupal por medicina general
    '990103',  # Educación grupal por odontología
    '990104',  # Educación grupal por enfermería
}

# ============================================================================
# CATEGORÍA 11 — Educación en Salud Individual
# Finalidad: 40  Causa: 40  CIE-10: Z718. Cuentan en RPYMS389X.
# ============================================================================
CUPS_EDUCACION_INDIVIDUAL = {
    '990201',  # Educación individual por medicina general
    '990203',  # Educación individual por odontología
    '990204',  # Educación individual por enfermería
}

# ============================================================================
# CATEGORÍA 12 — Planificación Familiar — Protección Específica
# Inserción y extracción de implante subdérmico.
# Finalidad: 14  Causa: 40  CIE-10: varía por CUPS. Solo mujeres 10–49 años.
# ============================================================================
CUPS_PLANIFICACION_FAMILIAR_PE = {
    '861801': {
        'descripcion':   'Inserción implante subdérmico anticonceptivo',
        'cie10_default': 'Z301',
        'indicador':     'RPYMS94X',
    },
    '861203': {
        'descripcion':   'Extracción implante subdérmico anticonceptivo',
        'cie10_default': 'Z305',
        'indicador':     'RPYMS94AX',
    },
}

# ============================================================================
# CATEGORÍA 13 — Detección Temprana General
# Tamizajes con indicadores RPYMS propios y CIE-10 específico por CUPS.
# Finalidad: 12 (Detección Temprana)  Causa: 40  CIE-10: varía por CUPS.
# ============================================================================
CUPS_DETECCION_TEMPRANA_GENERAL = {
    '892901': {
        'descripcion':   'Toma de citología cervicovaginal (cáncer cervical)',
        'cie10_default': 'Z124',
        'indicador':     'RPYMS63X / RPYMS61X',
    },
    '902211': {
        'descripcion':   'Hematocrito (anemia infancia-adolescencia)',
        'cie10_default': 'Z003',
        'indicador':     'RPYMS (Hematocrito)',
    },
    '907008': {
        'descripcion':   'Sangre oculta en materia fecal — tamizaje cáncer colorrectal',
        'cie10_default': 'Z120',
        'indicador':     'RPYMS88X',
    },
    '950601': {
        'descripcion':   'Medición de agudeza visual — tamizaje (fin 12, no fin 14)',
        'cie10_default': 'Z010',
        'indicador':     'RPYMS14X',
    },
    '906039': {
        'descripcion':   'Treponema pallidum anticuerpos (prueba treponémica) — tamizaje sífilis PYP',
        'cie10_default': 'Z114',
        'indicador':     'RPYMS347X / RPYMS348X',
    },
}

# ============================================================================
# ALERTAS CRÍTICAS — requieren decisión inmediata
# ============================================================================
ALERTAS_CUPS = {
    '240200': (
        'ALERTA CRÍTICA: Detartraje SUBgingival (finalidad 16, NO cuenta en RPYMS32X). '
        'No confundir con CUPS 997301 (detartraje SUPRAgingival, finalidad 14, SÍ cuenta).'
    ),
    '997103': (
        'ALERTA CRÍTICA: CUPS desactualizado. Res 2275/2023 establece 997106 (barniz de flúor). '
        'Los registros con 997103 NO cuentan en RPYMS30aX.'
    ),
    '997104': (
        'ALERTA: Verificar vigencia de 997104 (solución fluoruro). '
        'El CUPS vigente según Res 2275/2023 es 997106 (barniz).'
    ),
    '907008': (
        'AVISO: Si se dispone de 907009 en contrato, preferir 907009 para RPYMS88X. '
        '907008 registrado como Detección Temprana (fin 12, Z120). '
        'En contexto morbilidad, colocar el diagnóstico real manualmente.'
    ),
    '993506': (
        'ALERTA: Verificar duplicidad con 993522 (triple viral SRP). '
        'No registrar sarampión individual si se aplicó la triple viral.'
    ),
    '993507': (
        'ALERTA: Verificar duplicidad con 993522 (triple viral SRP). '
        'No registrar parotiditis individual si se aplicó la triple viral.'
    ),
    '993508': (
        'ALERTA: Verificar duplicidad con 993522 (triple viral SRP). '
        'No registrar rubéola individual si se aplicó la triple viral.'
    ),
    '993104': (
        'ALERTA: Verificar si Haemophilus influenza B ya está incluido en '
        'pentavalente 993130. Posible duplicidad.'
    ),
    '898001': (
        'ALERTA: CUPS 898001 no encontrado en Ficha Técnica RPYMS ni en catálogo NEPS. '
        'Verificar con el área de contratación. Clasificado provisionalmente como Apoyo Diagnóstico.'
    ),
}


# ============================================================================
# Defaults por categoría
# ============================================================================
_DEFAULTS_CATEGORIA = {
    'MORBILIDAD_ODONTOLOGICA': {
        'finalidad':     '16',
        'causa':         '38',
        'cie10_default': None,
        'cuenta_rpyms':  False,
        'nota':          'Morbilidad odontológica — registrar con finalidad 16 (Tratamiento)',
    },
    'APOYO_DIAGNOSTICO': {
        'finalidad':     '15',
        'causa':         '38',
        'cie10_default': None,
        'cuenta_rpyms':  False,
        'nota':          'Apoyo diagnóstico — no cuenta en PyP',
    },
    'RUTA_MATERNO_PERINATAL': {
        'finalidad':     '23',
        'causa':         '42',
        'cie10_default': 'Z340',
        'cuenta_rpyms':  False,
        'nota':          'Ruta Materno Perinatal — tiene ficha técnica propia',
    },
    'URGENCIAS_SOPORTE': {
        'finalidad':     None,   # Depende del contexto — no se sobrescribe
        'causa':         None,
        'cie10_default': None,
        'cuenta_rpyms':  False,
        'nota':          'Urgencias/soporte — finalidad según contexto clínico',
    },
    'DOBLE_PROPOSITO': {
        'finalidad':     None,   # La IPS debe elegir según servicio prestado
        'causa':         None,
        'cie10_default': None,
        'cuenta_rpyms':  None,   # Depende de la finalidad elegida
        'nota':          'Doble propósito — la finalidad determina si cuenta en PyP',
    },
    'VACUNA_ESPECIAL': {
        'finalidad':     '14',
        'causa':         '40',
        'cie10_default': 'Z279',
        'cuenta_rpyms':  True,
        'nota':          'Vacuna especial — verificar lineamiento PAI',
    },
    'VACUNA_PAI': {
        'finalidad':     '14',
        'causa':         '40',
        'cie10_default': 'Z279',
        'cuenta_rpyms':  True,
        'nota':          'Vacuna PAI — Protección Específica, Z279, finalidad 14',
    },
    'SALUD_ORAL_PE': {
        'finalidad':     '14',
        'causa':         '40',
        'cie10_default': None,   # Se sobreescribe por CUPS en get_categoria_cups
        'cuenta_rpyms':  True,
        'nota':          'PE Salud Oral — finalidad 14, CIE-10 específico por procedimiento',
    },
    'LAB_CARDIOMETABOLICO': {
        'finalidad':     '12',
        'causa':         '40',
        'cie10_default': 'Z108',
        'cuenta_rpyms':  True,
        'nota':          'Laboratorio tamizaje cardiometabólico — finalidad 12, Z108',
    },
    'EDUCACION_GRUPAL': {
        'finalidad':     '42',
        'causa':         '41',
        'cie10_default': 'Z718',
        'cuenta_rpyms':  True,
        'nota':          'Educación grupal en salud — Intervención Colectiva (finalidad 42)',
    },
    'EDUCACION_INDIVIDUAL': {
        'finalidad':     '40',
        'causa':         '40',
        'cie10_default': 'Z718',
        'cuenta_rpyms':  True,
        'nota':          'Educación individual en salud — Promoción agencia (finalidad 40)',
    },
    'PLANIFICACION_FAMILIAR_PE': {
        'finalidad':     '14',
        'causa':         '40',
        'cie10_default': None,   # Se sobreescribe por CUPS en get_categoria_cups
        'cuenta_rpyms':  True,
        'nota':          'Planificación Familiar PE — finalidad 14, CIE-10 específico por CUPS',
    },
    'DETECCION_TEMPRANA_GENERAL': {
        'finalidad':     '12',
        'causa':         '40',
        'cie10_default': None,   # Se sobreescribe por CUPS en get_categoria_cups
        'cuenta_rpyms':  True,
        'nota':          'Detección temprana general — finalidad 12, CIE-10 específico por CUPS',
    },
}


# ============================================================================
# Función principal de lookup
# ============================================================================

def get_categoria_cups(cups_code: str) -> dict:
    """
    Devuelve la categoría y valores recomendados para un CUPS que no está en
    la Ficha Técnica RPYMS.

    Args:
        cups_code: Código CUPS normalizado (string).

    Returns:
        dict con claves:
            categoria    (str)        — nombre de la categoría
            finalidad    (str|None)   — finalidad recomendada, None si depende del contexto
            causa        (str|None)   — causa externa recomendada
            cie10_default(str|None)   — CIE-10 sugerido cuando el campo está vacío
            cuenta_rpyms (bool|None)  — True si puede contar en RPYMS (con la finalidad correcta)
            nota         (str)        — descripción de la regla
            alerta       (str|None)   — texto de alerta crítica, None si no aplica
    """
    cups = str(cups_code).strip().upper()
    alerta = ALERTAS_CUPS.get(cups)

    if cups in CUPS_MORBILIDAD_ODONTOLOGICA:
        return {**_DEFAULTS_CATEGORIA['MORBILIDAD_ODONTOLOGICA'],
                'categoria': 'MORBILIDAD_ODONTOLOGICA', 'alerta': alerta}

    if cups in CUPS_APOYO_DIAGNOSTICO or (
        cups.isdigit() and len(cups) == 6 and cups[:3] in PREFIJOS_RADIOGRAFIAS
    ):
        return {**_DEFAULTS_CATEGORIA['APOYO_DIAGNOSTICO'],
                'categoria': 'APOYO_DIAGNOSTICO', 'alerta': alerta}

    if cups in CUPS_RUTA_MATERNO_PERINATAL:
        return {**_DEFAULTS_CATEGORIA['RUTA_MATERNO_PERINATAL'],
                'categoria': 'RUTA_MATERNO_PERINATAL', 'alerta': alerta}

    if cups in CUPS_URGENCIAS_SOPORTE:
        return {**_DEFAULTS_CATEGORIA['URGENCIAS_SOPORTE'],
                'categoria': 'URGENCIAS_SOPORTE', 'alerta': alerta}

    if cups in CUPS_DOBLE_PROPOSITO:
        info = CUPS_DOBLE_PROPOSITO[cups]
        return {
            'categoria':     'DOBLE_PROPOSITO',
            'finalidad':     info['finalidad_pyp'],   # valor predeterminado PyP
            'causa':         '40',
            'cie10_default': None,
            'cuenta_rpyms':  True,
            'nota': (
                f"Doble propósito: con finalidad {info['finalidad_pyp']} cuenta en "
                f"{info['indicador_si_pyp']}; con finalidad {info['finalidad_morbilidad']} "
                f"NO cuenta en PyP."
            ),
            'alerta': alerta,
        }

    if cups in CUPS_VACUNAS_ESPECIALES:
        return {**_DEFAULTS_CATEGORIA['VACUNA_ESPECIAL'],
                'categoria': 'VACUNA_ESPECIAL', 'alerta': alerta}

    if cups in CUPS_VACUNA_PAI:
        info = CUPS_VACUNA_PAI[cups]
        return {
            **_DEFAULTS_CATEGORIA['VACUNA_PAI'],
            'categoria': 'VACUNA_PAI',
            'nota':      f'Vacuna PAI — {info["descripcion"]} — Indicador: {info["indicador"]}',
            'alerta':    alerta,
        }

    if cups in CUPS_SALUD_ORAL_PE:
        info = CUPS_SALUD_ORAL_PE[cups]
        defaults = dict(_DEFAULTS_CATEGORIA['SALUD_ORAL_PE'])
        defaults['cie10_default'] = info['cie10_default']
        return {
            **defaults,
            'categoria': 'SALUD_ORAL_PE',
            'nota':      f'PE Salud Oral — {info["descripcion"]} — Indicador: {info["indicador"]}',
            'alerta':    alerta,
        }

    if cups in CUPS_LAB_CARDIOMETABOLICO:
        return {**_DEFAULTS_CATEGORIA['LAB_CARDIOMETABOLICO'],
                'categoria': 'LAB_CARDIOMETABOLICO', 'alerta': alerta}

    if cups in CUPS_EDUCACION_GRUPAL:
        return {**_DEFAULTS_CATEGORIA['EDUCACION_GRUPAL'],
                'categoria': 'EDUCACION_GRUPAL', 'alerta': alerta}

    if cups in CUPS_EDUCACION_INDIVIDUAL:
        return {**_DEFAULTS_CATEGORIA['EDUCACION_INDIVIDUAL'],
                'categoria': 'EDUCACION_INDIVIDUAL', 'alerta': alerta}

    if cups in CUPS_PLANIFICACION_FAMILIAR_PE:
        info = CUPS_PLANIFICACION_FAMILIAR_PE[cups]
        defaults = dict(_DEFAULTS_CATEGORIA['PLANIFICACION_FAMILIAR_PE'])
        defaults['cie10_default'] = info['cie10_default']
        return {
            **defaults,
            'categoria': 'PLANIFICACION_FAMILIAR_PE',
            'nota':      f'PF PE — {info["descripcion"]} — Indicador: {info["indicador"]}',
            'alerta':    alerta,
        }

    if cups in CUPS_DETECCION_TEMPRANA_GENERAL:
        info = CUPS_DETECCION_TEMPRANA_GENERAL[cups]
        defaults = dict(_DEFAULTS_CATEGORIA['DETECCION_TEMPRANA_GENERAL'])
        defaults['cie10_default'] = info['cie10_default']
        return {
            **defaults,
            'categoria': 'DETECCION_TEMPRANA_GENERAL',
            'nota':      f'Detección temprana — {info["descripcion"]} — Indicador: {info["indicador"]}',
            'alerta':    alerta,
        }

    return {
        'categoria':     'SIN_CATEGORIA',
        'finalidad':     None,
        'causa':         None,
        'cie10_default': None,
        'cuenta_rpyms':  False,
        'nota':          'CUPS no clasificado — revisar manualmente',
        'alerta':        alerta,
    }
