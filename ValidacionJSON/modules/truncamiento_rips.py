"""Utilidades compartidas para truncamiento de códigos RIPS."""

import pandas as pd


def truncar_codigo(codigo, longitud=4):
    """Trunca códigos de diagnóstico a la longitud requerida sin alterar vacíos."""
    if pd.isna(codigo) or codigo == '':
        return codigo
    codigo_str = str(codigo).strip()
    if len(codigo_str) > longitud:
        return codigo_str[:longitud]
    return codigo_str


def truncar_campos_dataframe(df, columnas, longitud=4):
    """Trunca en sitio un conjunto de columnas diagnósticas si existen en el DataFrame."""
    if df is None or df.empty:
        return df
    for idx, row in df.iterrows():
        for col in columnas:
            if col not in df.columns:
                continue
            codigo = str(row[col]).strip() if pd.notna(row[col]) and row[col] != '' else ''
            if codigo and len(codigo) > longitud:
                df.at[idx, col] = truncar_codigo(codigo, longitud=longitud)
    return df