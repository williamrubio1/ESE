"""
Parser de catálogos de referencia RIPS:
  - cupsContratadosNEPS.txt  (CUPS contratados Nueva EPS)
  - Finalidad.csv
  - CausaExterna.csv
  - CodigosPyp.csv
  - TablasCriterios/ (TablaUniversal_*.csv)
"""
import re
import os
import glob
import pandas as pd


def normalizar_cups(codigo) -> str:
    """
    Normaliza un código CUPS a formato estándar.

    - Numéricos: 6 dígitos sin puntos (ej: '890201', '89.0.2.01' → '890201')
    - Alfanuméricos: uppercase sin puntos (ej: '129B01', '5DSB01')
    - Elimina sufijos .0 de lectura como float
    """
    if pd.isna(codigo) or str(codigo).strip() in ('', 'nan', 'NaN'):
        return ''
    s = str(codigo).strip().upper()
    # Quitar sufijo float: '890201.0' → '890201'
    if re.match(r'^\d+\.0$', s):
        s = s[:-2]
    # Quitar puntos y espacios internos
    s = s.replace('.', '').replace(' ', '').replace('-', '')
    return s


def extraer_cups_de_texto(texto: str) -> list:
    """
    Extrae códigos CUPS de texto libre.

    Reconoce:
      - 6 dígitos consecutivos: '890201'
      - Formato con puntos: '89.0.2.01'
      - Alfanuméricos 6 chars: '129B01', '5DSB01'
    """
    if not texto:
        return []
    t = str(texto).upper()
    # CUPS numéricos de 6 dígitos
    cups6 = re.findall(r'\b(\d{6})\b', t)
    # CUPS alfanuméricos (letra(s) + dígitos, 5-7 chars total)
    cups_alfa = re.findall(r'\b([A-Z0-9]{2}[A-Z][A-Z0-9]{2,4})\b', t)
    # CUPS con puntos: normalizar
    cups_puntos = re.findall(r'\b(\d{2}\.\d{1}\.\d{2}\.\d{2})\b', t)
    cups_norm = [c.replace('.', '') for c in cups_puntos]

    todos = cups6 + cups_norm + cups_alfa
    # Filtrar falsos positivos comunes
    EXCLUIR = {'RPYMS', 'RIPS', 'CUPS', 'PYMS'}
    resultado = [c for c in todos if c not in EXCLUIR and len(c) >= 6]
    return list(dict.fromkeys(resultado))


def load_cups_neps(filepath: str, encoding: str = 'latin-1') -> pd.DataFrame:
    """
    Carga cupsContratadosNEPS.txt.

    Retorna DataFrame con columnas: CodigoCUPS, DescripcionCUPS, Grupo, Ruta
    """
    df = pd.read_csv(filepath, encoding=encoding, dtype=str, sep=',')
    df.columns = df.columns.str.strip()
    df['CodigoCUPS'] = df['CodigoCUPS'].apply(normalizar_cups)
    df['Ruta'] = df['Ruta'].str.strip().str.upper()
    # Eliminar filas con código vacío
    df = df[df['CodigoCUPS'] != ''].reset_index(drop=True)
    return df


def load_finalidades(filepath: str) -> dict:
    """Carga Finalidad.csv → dict {codigo_str: nombre}."""
    df = pd.read_csv(filepath, dtype=str)
    df.columns = df.columns.str.strip()
    return dict(zip(df['Codigo'].str.strip(), df['Nombre'].str.strip()))


def load_causa_externa(filepath: str) -> dict:
    """Carga CausaExterna.csv → dict {codigo_str: nombre}."""
    df = pd.read_csv(filepath, dtype=str)
    df.columns = df.columns.str.strip()
    return dict(zip(df['Codigo'].str.strip(), df['Nombre'].str.strip()))


def load_codigos_pyp(filepath: str, encoding: str = 'latin-1') -> pd.DataFrame:
    """
    Carga CodigosPyp.csv.

    Normaliza nombres de columnas y códigos CUPS.
    Retorna DataFrame limpio.
    """
    df = pd.read_csv(
        filepath, encoding=encoding, sep=',', dtype=str,
        engine='python', on_bad_lines='skip'
    )
    # Normalizar nombres: quitar saltos de línea, espacios, mayúsculas
    df.columns = [
        c.strip().replace('\n', '_').replace(' ', '_').upper()
        for c in df.columns
    ]
    # Normalizar columnas de CUPS
    for col in df.columns:
        if 'CUPS' in col or col.startswith('CODIGO'):
            df[col] = df[col].apply(normalizar_cups)
    return df


def load_tabla_criterios(dirpath: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """
    Carga y concatena todas las TablaUniversal_*.csv del directorio TablasCriterios.

    Retorna un DataFrame unificado con las columnas canónicas del modelo.
    """
    archivos = glob.glob(os.path.join(dirpath, 'TablaUniversal_*.csv'))
    if not archivos:
        raise FileNotFoundError(f'No se encontraron TablaUniversal_*.csv en {dirpath}')

    partes = []
    for archivo in sorted(archivos):
        nombre_tabla = os.path.splitext(os.path.basename(archivo))[0]
        try:
            df_part = pd.read_csv(archivo, encoding=encoding, dtype=str)
            df_part['tabla_origen'] = nombre_tabla
            partes.append(df_part)
        except Exception as e:
            print(f'  [ADVERTENCIA] No se pudo cargar {archivo}: {e}')

    if not partes:
        raise ValueError('Ninguna tabla de criterios pudo cargarse.')

    df = pd.concat(partes, ignore_index=True)

    # Normalizar tipos de columnas numéricas de edad
    for col in ['EdadMin_Meses', 'EdadMax_Meses']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Normalizar CUPS
    if 'CodigoCUPS' in df.columns:
        df['CodigoCUPS'] = df['CodigoCUPS'].apply(normalizar_cups)

    # Normalizar finalidad
    if 'CodFinalidad' in df.columns:
        df['CodFinalidad'] = df['CodFinalidad'].astype(str).str.strip()

    return df
