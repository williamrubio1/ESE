"""
Core module - Contiene la lógica de procesamiento de RIPS
"""
from .procesador import recorrer_datos, procesar_medicamento, procesar_procedimiento

__all__ = [
	'recorrer_datos',
	'procesar_medicamento',
	'procesar_procedimiento',
]
