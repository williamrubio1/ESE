"""
Validador de registros RIPS individuales contra la tabla universal RPYMS.

Reglas implementadas:
  1. CUPS debe existir en tabla universal
  2. CUPS debe estar contratado en NEPS (o emitir advertencia)
  3. Edad del paciente dentro del rango normativo
  4. Sexo compatible con el indicador
  5. Finalidad válida (acepta antigua y nueva equivalente Res 2275/2023)
  6. CIE-10 compatible con el indicador
  7. Causa externa correcta (40 / 41 / 42 según ruta)
"""
from typing import Dict, Any, List
import pandas as pd

from modules.edad_utils import edad_en_rango
from modules.cie10_utils import match_lista_cie10, normalizar_cie10
from modules.cups_parser import normalizar_cups

# Finalidades válidas por equivalencia Res 2275/2023
MAPA_FINALIDADES_VALIDAS: Dict[str, List[str]] = {
    '4':  ['4', '11'],
    '5':  ['5', '11'],
    '7':  ['7', '11'],
    '8':  ['8', '12'],
    '11': ['4', '5', '7', '11'],
    '12': ['8', '12'],
}

CAUSA_EXTERNA_PYMS      = '40'
CAUSA_EXTERNA_COLECTIVA = '41'
CAUSA_EXTERNA_MAT_PERIN = '42'


def _finalidades_aceptadas(finalidad_input: str) -> List[str]:
    """
    Retorna todas las finalidades que se consideran válidas para la finalidad dada,
    considerando la equivalencia entre Res 3280/2018 y Res 2275/2023.
    """
    f = str(finalidad_input).strip()
    return MAPA_FINALIDADES_VALIDAS.get(f, [f])


def validar_rips(
    rips_row: Dict[str, Any],
    tabla_universal: pd.DataFrame,
    edad_paciente_meses: int,
    sexo: str,
) -> Dict[str, Any]:
    """
    Valida una fila de RIPS contra la tabla universal RPYMS.

    Args:
        rips_row: dict con claves:
                  'cups'          → código CUPS del servicio prestado
                  'finalidad'     → código de finalidad registrado
                  'cie10'         → diagnóstico principal CIE-10
                  'causa_externa' → código de causa externa (opcional)
        tabla_universal       : DataFrame de build_tabla_universal()
        edad_paciente_meses   : edad del paciente en meses completos
        sexo                  : 'M', 'F' (la tabla usa 'A' para ambos)

    Returns:
        dict con:
            'es_valido'              : bool
            'indicadores_que_cuenta' : list[str]  — indicadores RPYMS que acumula
            'finalidad_correcta'     : str | None — finalidad recomendada
            'finalidad_alternativa'  : str | None — equivalente Res 2275/2023
            'cie10_sugerido'         : str | None — primer CIE-10 normativo sugerido
            'causa_externa_correcta' : str | None
            'ruta_neps'              : str | None
            'observaciones'          : list[str]  — mensajes explicativos
    """
    resultado: Dict[str, Any] = {
        'es_valido':              False,
        'indicadores_que_cuenta': [],
        'finalidad_correcta':     None,
        'finalidad_alternativa':  None,
        'cie10_sugerido':         None,
        'causa_externa_correcta': None,
        'ruta_neps':              None,
        'observaciones':          [],
    }

    cups_input      = normalizar_cups(str(rips_row.get('cups', '')))
    finalidad_input = str(rips_row.get('finalidad', '')).strip()
    cie10_input     = normalizar_cie10(str(rips_row.get('cie10', '')))
    causa_input     = str(rips_row.get('causa_externa', '')).strip()

    # ── 1. CUPS vacío ──────────────────────────────────────────────────────────
    if not cups_input:
        resultado['observaciones'].append('CUPS vacío o inválido.')
        return resultado

    # ── 2. CUPS en tabla universal ─────────────────────────────────────────────
    df_cups = tabla_universal[tabla_universal['cups_codigo'] == cups_input]
    if df_cups.empty:
        resultado['observaciones'].append(
            f'CUPS {cups_input} no encontrado en tabla universal RPYMS.'
        )
        return resultado

    resultado['ruta_neps'] = df_cups['ruta_neps'].iloc[0]

    # ── 3. CUPS contratado NEPS ────────────────────────────────────────────────
    if not df_cups['es_cups_contratado_neps'].any():
        resultado['observaciones'].append(
            f'CUPS {cups_input} NO está contratado en NEPS. Verificar equivalente.'
        )

    # ── 4. Filtro por edad ─────────────────────────────────────────────────────
    df_edad = df_cups[
        (df_cups['edad_min_meses'].astype(int) <= edad_paciente_meses) &
        (df_cups['edad_max_meses'].astype(int) >= edad_paciente_meses)
    ]
    if df_edad.empty:
        rangos = df_cups[['edad_min_meses', 'edad_max_meses']].drop_duplicates().values.tolist()
        resultado['observaciones'].append(
            f'Edad {edad_paciente_meses} meses fuera de rango para CUPS {cups_input}. '
            f'Rangos válidos: {rangos}'
        )
        return resultado

    # ── 5. Filtro por sexo ─────────────────────────────────────────────────────
    df_sexo = df_edad[df_edad['sexo'].isin([sexo, 'A'])]
    if df_sexo.empty:
        resultado['observaciones'].append(
            f'Sexo {sexo!r} no aplica para CUPS {cups_input} en la edad indicada.'
        )
        return resultado

    # ── 6. Filtro por finalidad ────────────────────────────────────────────────
    finalidades_aceptadas = _finalidades_aceptadas(finalidad_input)
    df_finalidad = df_sexo[df_sexo['cod_finalidad'].isin(finalidades_aceptadas)]

    if df_finalidad.empty:
        finalidades_sugeridas = df_sexo['cod_finalidad'].unique().tolist()
        resultado['finalidad_correcta']    = finalidades_sugeridas[0] if finalidades_sugeridas else None
        resultado['finalidad_alternativa'] = df_sexo['finalidad_equivalente_2275'].iloc[0] \
                                             if 'finalidad_equivalente_2275' in df_sexo.columns else None
        resultado['observaciones'].append(
            f'Finalidad {finalidad_input!r} incorrecta. '
            f'Sugeridas: {finalidades_sugeridas}'
        )
        df_trabajo = df_sexo  # continúa con lo que hay para sugerir CIE-10
    else:
        resultado['finalidad_correcta'] = finalidad_input
        df_trabajo = df_finalidad

    # ── 7. Validación de CIE-10 ────────────────────────────────────────────────
    cie10_normativos = df_trabajo['cie10_codigo'].dropna().unique().tolist()
    cie10_ok = match_lista_cie10(cie10_input, cie10_normativos)

    if not cie10_ok:
        resultado['cie10_sugerido'] = cie10_normativos[0] if cie10_normativos else None
        resultado['observaciones'].append(
            f'CIE-10 {cie10_input!r} no corresponde al indicador. '
            f'Sugeridos: {cie10_normativos[:5]}'
        )

    # ── 8. Causa externa ───────────────────────────────────────────────────────
    causa_esperada = df_trabajo['causa_externa_correcta'].iloc[0] \
                     if 'causa_externa_correcta' in df_trabajo.columns else CAUSA_EXTERNA_PYMS
    resultado['causa_externa_correcta'] = causa_esperada

    if causa_input and causa_input != causa_esperada:
        resultado['observaciones'].append(
            f'Causa externa {causa_input!r} incorrecta. Esperada: {causa_esperada!r}.'
        )

    # ── 9. Indicadores que cuenta ─────────────────────────────────────────────
    indicadores = df_trabajo['indicador_rpyms'].dropna().unique().tolist()
    resultado['indicadores_que_cuenta'] = indicadores

    # ── 10. Veredicto final ────────────────────────────────────────────────────
    errores_criticos = [
        obs for obs in resultado['observaciones']
        if any(kw in obs for kw in [
            'fuera de rango', 'no encontrado', 'no aplica', 'incorrecta'
        ])
    ]
    resultado['es_valido'] = bool(indicadores) and len(errores_criticos) == 0

    return resultado


def validar_lote(
    rips_df: pd.DataFrame,
    tabla_universal: pd.DataFrame,
    pacientes_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Valida un lote de registros RIPS.

    Args:
        rips_df        : DataFrame con columnas cups, finalidad, cie10, causa_externa,
                          y un campo de unión al paciente (ej: num_documento)
        tabla_universal: resultado de build_tabla_universal()
        pacientes_df   : DataFrame con columnas num_documento, edad_meses, sexo

    Returns:
        DataFrame con columnas de validación añadidas a cada fila de rips_df.
    """
    pac_idx = pacientes_df.set_index('num_documento').to_dict('index')

    resultados = []
    for _, row in rips_df.iterrows():
        num_doc    = str(row.get('num_documento', ''))
        pac        = pac_idx.get(num_doc, {})
        edad_meses = int(pac.get('edad_meses', 0))
        sexo       = str(pac.get('sexo', 'A')).upper()

        val = validar_rips(row.to_dict(), tabla_universal, edad_meses, sexo)
        resultados.append({
            'num_documento':          num_doc,
            'es_valido':              val['es_valido'],
            'indicadores_que_cuenta': '|'.join(val['indicadores_que_cuenta']),
            'finalidad_correcta':     val['finalidad_correcta'],
            'cie10_sugerido':         val['cie10_sugerido'],
            'causa_externa_correcta': val['causa_externa_correcta'],
            'ruta_neps':              val['ruta_neps'],
            'observaciones':          ' | '.join(val['observaciones']),
        })

    result_df = pd.DataFrame(resultados)
    return pd.concat([rips_df.reset_index(drop=True), result_df.reset_index(drop=True)], axis=1)
