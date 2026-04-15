"""
Parser de FichaTecnicasPYMS2026.csv

Fuente primaria de verdad para indicadores RPYMS.
El CSV usa ';' como separador y encoding latin-1.
Las celdas multilínea están entrecomilladas con doble comilla.

Estructura relevante (columnas, 0-indexadas):
  0  → Código Indicador (ej: RPYMS41X)
  1  → Nombre indicador
  2  → Definición operacional
  4  → Curso Vida (Primera Infancia / Infancia / Adolescencia / ...)
  5  → Tipo de actividad evaluada
  6  → Tipo de actividad evaluada (especifica)
  7  → Nivel de medición
  8  → Genero (Ambos / Femenino / Masculino)
  9  → núm  ← RIPS requeridos: CUPS, finalidades, CIE-10
  10 → den  ← Denominador: contiene descripción de la población
"""
import re
import csv
import pandas as pd

from modules.edad_utils import parse_rango_edad_texto, EDAD_MAX_TOPE
from modules.cie10_utils import extraer_cie10_de_texto
from modules.cups_parser import extraer_cups_de_texto

# Índices de columnas (0-based)
COL_INDICADOR   = 0
COL_NOMBRE      = 1
COL_DEFINICION  = 2
COL_CURSO_VIDA  = 4
COL_TIPO_ACT    = 5
COL_TIPO_ESP    = 6
COL_GENERO      = 8
COL_NUM         = 9
COL_DEN         = 10

SEXO_MAP = {
    'ambos':      'A',
    'femenino':   'F',
    'femenina':   'F',
    'masculino':  'M',
    'masculina':  'M',
}

# Mapeo antiguo → nuevo finalidades (Res 2275/2023)
MAPA_FINALIDADES_ANTIGUAS = {
    '4': '11',
    '5': '11',
    '7': '11',
    '8': '12',
}


def _normalizar_sexo(texto: str) -> str:
    return SEXO_MAP.get(str(texto).strip().lower(), 'A')


def _extraer_finalidades_de_texto(texto: str) -> list:
    """
    Extrae códigos de finalidad del texto del numerador.

    Reconoce patrones como:
      "Finalidad 4"
      "Finalidad 11 o finalidad 12"
      "finalidades: 4, 11"
    """
    if not texto:
        return []
    # Buscar números de 1-2 dígitos precedidos de "Finalidad"
    patrones = re.findall(r'[Ff]inalidad\s*[:\s]?\s*(\d{1,2})', texto)
    # También buscar listas separadas por coma o "o": "4 o 11"
    lista_pats = re.findall(
        r'[Ff]inalidad(?:es)?[:\s]+([0-9][0-9,\s/oóu]+)', texto
    )
    for lp in lista_pats:
        nums = re.findall(r'\d{1,2}', lp)
        patrones.extend(nums)

    # Añadir equivalentes Res 2275/2023
    resueltas = list(dict.fromkeys(patrones))
    for f in list(resueltas):
        nueva = MAPA_FINALIDADES_ANTIGUAS.get(str(f))
        if nueva and nueva not in resueltas:
            resueltas.append(nueva)
    return resueltas


def parse_ficha_tecnica(filepath: str, encoding: str = 'latin-1') -> pd.DataFrame:
    """
    Lee FichaTecnicasPYMS2026.csv y retorna un DataFrame normalizado.

    Returns:
        DataFrame con columnas:
            indicador, nombre, curso_vida, tipo_actividad, tipo_especifico,
            sexo, cups_lista, finalidades_lista, cie10_lista,
            edad_min_meses, edad_max_meses, texto_num, texto_den
    """
    filas = []

    with open(filepath, encoding=encoding, newline='') as f:
        reader = csv.reader(f, delimiter=';', quotechar='"')
        rows = list(reader)

    # Las primeras 2 filas son encabezados (meta-encabezado + encabezado real)
    data_rows = rows[2:]

    for row in data_rows:
        # Rellenar columnas faltantes
        while len(row) < 14:
            row.append('')

        indicador = row[COL_INDICADOR].strip()
        # Solo procesar indicadores RPYMS con código específico (ej: RPYMS41X)
        if not indicador or not re.match(r'^RPYMS\w+X$', indicador):
            continue

        nombre      = row[COL_NOMBRE].strip()
        curso_vida  = row[COL_CURSO_VIDA].strip()
        tipo_act    = row[COL_TIPO_ACT].strip()
        tipo_esp    = row[COL_TIPO_ESP].strip()
        sexo_raw    = row[COL_GENERO].strip()
        texto_num   = row[COL_NUM].strip() if len(row) > COL_NUM else ''
        texto_den   = row[COL_DEN].strip() if len(row) > COL_DEN else ''

        cups_lista        = extraer_cups_de_texto(texto_num)
        finalidades_lista = _extraer_finalidades_de_texto(texto_num)
        cie10_lista       = extraer_cie10_de_texto(texto_num)

        # Rango de edad: primero del denominador, luego del nombre
        edad_min, edad_max = parse_rango_edad_texto(texto_den)
        if edad_min == 0 and edad_max == EDAD_MAX_TOPE:
            edad_min, edad_max = parse_rango_edad_texto(nombre)

        filas.append({
            'indicador':          indicador,
            'nombre':             nombre,
            'curso_vida':         curso_vida,
            'tipo_actividad':     tipo_act,
            'tipo_especifico':    tipo_esp,
            'sexo':               _normalizar_sexo(sexo_raw),
            'cups_lista':         cups_lista,
            'finalidades_lista':  finalidades_lista,
            'cie10_lista':        cie10_lista,
            'edad_min_meses':     edad_min,
            'edad_max_meses':     edad_max,
            'texto_num':          texto_num,
            'texto_den':          texto_den,
        })

    return pd.DataFrame(filas)
