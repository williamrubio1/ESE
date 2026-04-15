"""
Constructor de la tabla universal RIPS.

Flujo:
  1. Carga las TablasCriterios (ya procesadas) como base estructurada.
  2. Cruza con cupsContratadosNEPS para añadir:
       - es_cups_contratado_neps  (bool)
       - ruta_neps                (str: PYMS / MULTIRUTA / MATERNO PERINATAL / ...)
  3. Marca la EPS de referencia.
  4. Opcionalmente enriquece CodigosPyp.

Separación entre EPS:
    Nueva EPS     → cups_neps_df de cupsContratadosNEPS.txt
    Capital Salud → cups del conjunto config_eps.py['capital_salud']
"""
import pandas as pd

from modules.cups_parser import normalizar_cups

# Mapeo de finalidades (Res 3280/2018 → Res 2275/2023)
MAPA_FINALIDADES_ANTIGUAS = {
    '4': '11',
    '5': '11',
    '7': '11',
    '8': '12',
}

# Causa externa normativa por tipo de intervención
CAUSA_EXTERNA_PYMS      = '40'
CAUSA_EXTERNA_COLECTIVA = '41'
CAUSA_EXTERNA_MAT_PERIN = '42'


def _causa_externa_por_ruta(ruta: str) -> str:
    ruta_up = str(ruta).upper()
    if 'MATERNO' in ruta_up or 'PERINATAL' in ruta_up:
        return CAUSA_EXTERNA_MAT_PERIN
    if 'COLECTIV' in ruta_up:
        return CAUSA_EXTERNA_COLECTIVA
    return CAUSA_EXTERNA_PYMS


def build_tabla_universal(
    criterios_df: pd.DataFrame,
    cups_neps_df: pd.DataFrame,
    finalidad_dict: dict,
    eps_nombre: str = 'nueva_eps',
) -> pd.DataFrame:
    """
    Construye la tabla universal cruzando TablasCriterios con cupsContratadosNEPS.

    Args:
        criterios_df  : DataFrame de load_tabla_criterios() — columnas canónicas
        cups_neps_df  : DataFrame de load_cups_neps()
        finalidad_dict: dict {codigo: nombre} de load_finalidades()
        eps_nombre    : etiqueta de la EPS ('nueva_eps' o 'capital_salud')

    Columnas del resultado:
        indicador_rpyms, nombre_programa, cups_codigo, descripcion_cups,
        grupo_cups, ruta_norma, cod_finalidad, nombre_finalidad,
        cod_causa, nombre_causa, cie10_codigo, edad_min_meses, edad_max_meses,
        sexo, es_cups_contratado_neps, ruta_neps, causa_externa_correcta,
        finalidad_equivalente_2275, fuente_norma, eps, tabla_origen
    """
    # Índice NEPS: CodigoCUPS → Ruta
    cups_neps_set = set(cups_neps_df['CodigoCUPS'].astype(str))
    cups_ruta_map = dict(zip(
        cups_neps_df['CodigoCUPS'].astype(str),
        cups_neps_df['Ruta'].astype(str),
    ))

    df = criterios_df.copy()

    # Normalizar CUPS por si acaso
    df['CodigoCUPS'] = df['CodigoCUPS'].apply(normalizar_cups)

    # Marcar contratado en NEPS
    df['es_cups_contratado_neps'] = df['CodigoCUPS'].isin(cups_neps_set)
    df['ruta_neps'] = df['CodigoCUPS'].map(cups_ruta_map).fillna('NO CONTRATADO')

    # Causa externa correcta según ruta normativa
    df['causa_externa_correcta'] = df['Ruta'].apply(_causa_externa_por_ruta)

    # Finalidad equivalente (Res 2275/2023)
    df['finalidad_equivalente_2275'] = df['CodFinalidad'].apply(
        lambda f: MAPA_FINALIDADES_ANTIGUAS.get(str(f).strip(), str(f).strip())
    )

    # Enriquecer nombre de finalidad si falta
    if 'NombreFinalidad' not in df.columns or df['NombreFinalidad'].isna().all():
        df['NombreFinalidad'] = df['CodFinalidad'].map(
            lambda c: finalidad_dict.get(str(c).strip(), '')
        )

    # Añadir EPS
    df['eps'] = eps_nombre

    # Renombrar a nombres canónicos de salida
    rename_map = {
        'IndicadorRPYMS':   'indicador_rpyms',
        'Programa':         'nombre_programa',
        'CodigoCUPS':       'cups_codigo',
        'DescripcionCUPS':  'descripcion_cups',
        'Grupo':            'grupo_cups',
        'Ruta':             'ruta_norma',
        'CodFinalidad':     'cod_finalidad',
        'NombreFinalidad':  'nombre_finalidad',
        'CodCausa':         'cod_causa',
        'NombreCausa':      'nombre_causa',
        'CIE10':            'cie10_codigo',
        'EdadMin_Meses':    'edad_min_meses',
        'EdadMax_Meses':    'edad_max_meses',
        'Sexo':             'sexo',
        'FuenteNormativa':  'fuente_norma',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Columnas de salida en orden canónico
    cols_salida = [
        'indicador_rpyms', 'nombre_programa', 'cups_codigo', 'descripcion_cups',
        'grupo_cups', 'ruta_norma', 'cod_finalidad', 'nombre_finalidad',
        'cod_causa', 'nombre_causa', 'cie10_codigo',
        'edad_min_meses', 'edad_max_meses', 'sexo',
        'es_cups_contratado_neps', 'ruta_neps', 'causa_externa_correcta',
        'finalidad_equivalente_2275', 'fuente_norma', 'eps', 'tabla_origen',
    ]
    cols_presentes = [c for c in cols_salida if c in df.columns]
    return df[cols_presentes].reset_index(drop=True)


def completar_codigos_pyp(
    codigos_pyp_df: pd.DataFrame,
    tabla_universal_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Enriquece CodigosPyp con metadatos de la tabla universal:
      - es_contratado_neps
      - ruta_neps
      - indicadores_rpyms (todos los que aplican)
      - causa_externa_correcta

    Busca por la columna de CUPS actuales (CODIGO_CUPS_ACTUALES_)
    y también por CUPS nuevos (CODIGO_CUPS_NUEVOS_).
    """
    # Resumen por CUPS desde tabla universal
    cups_meta = (
        tabla_universal_df
        .groupby('cups_codigo')
        .agg(
            es_contratado_neps=('es_cups_contratado_neps', 'first'),
            ruta_neps=('ruta_neps', 'first'),
            causa_externa_correcta=('causa_externa_correcta', 'first'),
            indicadores_rpyms=('indicador_rpyms', lambda x: '|'.join(sorted(set(x.dropna())))),
        )
        .reset_index()
    )

    result = codigos_pyp_df.copy()

    # Detectar columnas de CUPS en CodigosPyp
    cups_cols = [c for c in result.columns if 'CUPS' in c.upper() or c.upper().startswith('CODIGO')]

    for col in cups_cols:
        suffix = col.lower().replace(' ', '_')
        result = result.merge(
            cups_meta.rename(columns={
                'cups_codigo':            col,
                'es_contratado_neps':     f'es_contratado_{suffix}',
                'ruta_neps':              f'ruta_{suffix}',
                'causa_externa_correcta': f'causa_ext_{suffix}',
                'indicadores_rpyms':      f'indicadores_{suffix}',
            }),
            on=col,
            how='left',
        )

    return result
