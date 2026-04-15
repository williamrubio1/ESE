"""
Utilidades para cálculo y conversión de edades en meses.

Resolución 3280/2018 y 2275/2023 trabajan con edad en meses,
especialmente para menores de 24 meses (indicadores RPYMS41X, RPYMS43X, etc.).
"""
import re
from datetime import date

EDAD_MAX_TOPE = 1440  # 120 años en meses (tope práctico)

# Rangos normativos de cursos de vida (Res 3280/2018, Art. 12) — en meses
CURSOS_VIDA_RANGOS = {
    'Primera Infancia': (0, 71),
    'Infancia':         (72, 143),
    'Adolescencia':     (144, 215),
    'Juventud':         (216, 335),
    'Adultez':          (336, 719),
    'Vejez':            (720, EDAD_MAX_TOPE),
}


def calcular_edad_meses(fecha_nacimiento: date, fecha_referencia: date) -> int:
    """Calcula la edad en meses completos entre dos fechas."""
    meses = (fecha_referencia.year - fecha_nacimiento.year) * 12
    meses += fecha_referencia.month - fecha_nacimiento.month
    if fecha_referencia.day < fecha_nacimiento.day:
        meses -= 1
    return max(0, meses)


def anios_a_meses(anios: float) -> int:
    return int(round(anios * 12))


def meses_a_anios(meses: int) -> float:
    return round(meses / 12, 1)


def parse_rango_edad_texto(texto: str) -> tuple:
    """
    Convierte texto de rango de edad a (edad_min_meses, edad_max_meses).

    Ejemplos:
        '2 a 11 meses'        → (2, 11)
        '12 a 23 meses'       → (12, 23)
        '18 a 28 años'        → (216, 335)
        '60 años y más'       → (720, 1440)
        'menores de 5 años'   → (0, 59)
        'mayor de 60 años'    → (721, 1440)
        '1 a 17 años'         → (12, 215)
        '25 a 29 años'        → (300, 347)
        '30 a 65 años'        → (360, 779)
    """
    if not texto or not isinstance(texto, str):
        return (0, EDAD_MAX_TOPE)

    t = texto.strip().lower()

    # "X a Y meses"
    m = re.search(r'(\d+)\s*(?:a|–|-|y)\s*(\d+)\s*meses?', t)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # "X a Y semanas" (recién nacidos)
    m = re.search(r'(\d+)\s*(?:a|–|-|y)\s*(\d+)\s*semanas?', t)
    if m:
        min_s, max_s = int(m.group(1)), int(m.group(2))
        return (max(0, int(min_s / 4.33)), min(int(max_s / 4.33) + 1, EDAD_MAX_TOPE))

    # "X a Y años" — límite superior: fin del año max (último mes antes del siguiente)
    m = re.search(r'(\d+)\s*(?:a|–|-|y)\s*(\d+)\s*a[ñn]os?', t)
    if m:
        min_a, max_a = int(m.group(1)), int(m.group(2))
        return (anios_a_meses(min_a), anios_a_meses(max_a + 1) - 1)

    # "X años y/o más" / "mayor(es) de X años" / "X años y más"
    m = re.search(r'(\d+)\s*a[ñn]os?\s+(?:y|o|ó)?\s*m[aá]s', t)
    if m:
        return (anios_a_meses(int(m.group(1))), EDAD_MAX_TOPE)

    m = re.search(r'ma?yor(?:es)?\s+(?:de|a)\s+(\d+)\s*a[ñn]os?', t)
    if m:
        return (anios_a_meses(int(m.group(1))) + 1, EDAD_MAX_TOPE)

    # "menor(es) de X años"
    m = re.search(r'menor(?:es)?\s+de\s+(\d+)\s*a[ñn]os?', t)
    if m:
        return (0, anios_a_meses(int(m.group(1))) - 1)

    # "menor(es) de X meses"
    m = re.search(r'menor(?:es)?\s+de\s+(\d+)\s*meses?', t)
    if m:
        return (0, int(m.group(1)) - 1)

    # Número suelto + "años" → rango de ese año
    m = re.search(r'^(\d+)\s*a[ñn]os?$', t)
    if m:
        a = int(m.group(1))
        return (anios_a_meses(a), anios_a_meses(a + 1) - 1)

    return (0, EDAD_MAX_TOPE)


def edad_en_rango(edad_meses: int, edad_min_meses: int, edad_max_meses: int) -> bool:
    """Verifica si una edad en meses está dentro del rango, inclusive en ambos extremos."""
    return edad_min_meses <= edad_meses <= edad_max_meses


def curso_vida_por_edad(edad_meses: int) -> str:
    """Retorna el curso de vida según edad en meses (art. 12 Res 3280/2018)."""
    for curso, (min_m, max_m) in CURSOS_VIDA_RANGOS.items():
        if min_m <= edad_meses <= max_m:
            return curso
    return 'Desconocido'
