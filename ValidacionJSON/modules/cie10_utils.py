"""
Utilidades para manejo de códigos CIE-10 en validación RIPS.

Soporta:
  - Patrones con comodín X (ej: 'Z00X' coincide con Z001, Z002, Z009...)
  - Prefijos cortos (ej: 'Z0' coincide con Z000-Z099)
  - Coincidencia exacta
  - Extracción de códigos desde texto libre
"""
import re


def normalizar_cie10(codigo: str) -> str:
    """Normaliza un código CIE-10: mayúsculas, sin espacios."""
    if not codigo:
        return ''
    return str(codigo).strip().upper()


def match_cie10(codigo: str, patron: str) -> bool:
    """
    Verifica si un código CIE-10 cumple un patrón.

    Patrones soportados:
        'Z001'    → coincidencia exacta
        'Z00X'    → Z00 + cualquier dígito o letra (1 carácter opcional)
        'Z0'      → prefijo Z0 (cualquier código que empiece con Z0)
        'Z124'    → exacto
    """
    codigo = normalizar_cie10(codigo)
    patron = normalizar_cie10(patron)

    if not codigo or not patron:
        return False

    # X actúa como comodín de un carácter alfanumérico (opcional)
    pat_regex = re.escape(patron).replace('X', r'[A-Z0-9]?')
    return bool(re.fullmatch(f'{pat_regex}.*', codigo))


def match_lista_cie10(codigo: str, patrones) -> bool:
    """Retorna True si el código coincide con al menos uno de los patrones."""
    if not patrones:
        return True  # sin restricción CIE-10 → cualquier código es válido
    return any(match_cie10(codigo, p) for p in patrones if p)


def extraer_cie10_de_texto(texto: str) -> list:
    """
    Extrae todos los códigos CIE-10 de un texto libre.

    Reconoce patrones del tipo: letra + 2-4 alfanuméricos + X opcional.
    Excluye siglas comunes (IPS, RIPS, etc.).
    """
    if not texto:
        return []

    # Texto a mayúsculas para buscar
    t = str(texto).upper()

    # Patrón CIE-10: letra mayúscula + 2-4 dígitos, opcionalmente terminado en X
    candidatos = re.findall(r'\b([A-Z]\d{2,3}[X\d]?)\b', t)

    # Exclusiones: siglas que no son CIE-10
    EXCLUIR = {'IPS', 'RIPS', 'EPS', 'PYP', 'PAI', 'VPH', 'VIH', 'BCG',
               'DPT', 'VOP', 'IVP', 'HBB', 'HBS', 'SRP', 'DIU', 'RMP'}
    resultado = [c for c in candidatos if c not in EXCLUIR and len(c) >= 3]

    # Deduplicar conservando orden
    return list(dict.fromkeys(resultado))
