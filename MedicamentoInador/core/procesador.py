"""
Módulo de procesamiento de RIPS
Contiene la lógica para procesar procedimientos y medicamentos
"""


def procesar_procedimiento(proc, stats):
    return proc


def procesar_medicamento(med, cum_dict, cum_modificado, stats):
    """
    Procesa medicamentos:
    - Busca en cum.json por nomTecnologiaSalud y sustituye codTecnologiaSalud y unidadMedida
    - Si no existe en cum.json y tiene datos válidos, guarda en cum.json para referencia futura
    """
    unidad = med.get("unidadMedida")
    nombre = med.get("nomTecnologiaSalud", "")
    codigo = med.get("codTecnologiaSalud", "")

    # Truncar nombre a 30 caracteres antes de comparaciones y sustituciones
    nombre = nombre[:30]
    med["nomTecnologiaSalud"] = nombre

    # Buscar por nomTecnologiaSalud en cum.json (normalizar para comparación)
    nombre_normalizado = nombre.strip().upper()
    encontrado = False
    
    for item in cum_dict:
        nombre_cum = item.get("nomTecnologiaSalud", "").strip().upper()
        if nombre_cum == nombre_normalizado:
            encontrado = True
            stats['medicamentos_encontrados'] += 1
            
            # Actualizar unidadMedida
            nueva_unidad = item.get("unidadMedida")
            if nueva_unidad and nueva_unidad != 0:
                if unidad != nueva_unidad:
                    med["unidadMedida"] = nueva_unidad
                    stats['unidades_sustituidas'] += 1
            
            # Actualizar codTecnologiaSalud solo si es válido (no "0" ni vacío)
            nuevo_codigo = item.get("codTecnologiaSalud", "")
            if nuevo_codigo and nuevo_codigo not in ["0", ""]:
                if codigo != nuevo_codigo:
                    med["codTecnologiaSalud"] = nuevo_codigo
                    stats['codigos_sustituidos'] += 1
            break
    
    # Si no se encontró en cum.json y tiene datos válidos, agregarlo
    if not encontrado and nombre and unidad and unidad != 0:
        cum_dict.append({
            "nomTecnologiaSalud": nombre,
            "codTecnologiaSalud": codigo,
            "unidadMedida": unidad
        })
        cum_modificado[0] = True
        stats['medicamentos_nuevos_en_cum'] += 1
        stats['medicamentos_nuevos_en_cum_detalle'].append({
            "nombre": nombre,
            "codigo": codigo,
            "unidad": unidad
        })
    elif not encontrado:
        stats['no_encontrados'] += 1
        stats['no_encontrados_detalle'].append({
            "nombre": nombre if nombre else "Sin nombre",
            "codigo": codigo,
            "unidad": unidad
        })


def recorrer_datos(data, cum_dict, cum_modificado, stats):
    """
    Recorre la estructura del JSON buscando la lista de procedimientos y medicamentos.
    Se adapta a si la raíz es una lista de usuarios o un objeto con usuarios.
    """
    if isinstance(data, list):
        for item in data:
            recorrer_datos(item, cum_dict, cum_modificado, stats)
    elif isinstance(data, dict):
        # Si encontramos la clave 'procedimientos', procesamos esa lista
        if "procedimientos" in data and isinstance(data["procedimientos"], list):
            for proc in data["procedimientos"]:
                procesar_procedimiento(proc, stats)
        
        # Si encontramos la clave 'medicamentos', procesamos esa lista
        if "medicamentos" in data and isinstance(data["medicamentos"], list):
            for med in data["medicamentos"]:
                procesar_medicamento(med, cum_dict, cum_modificado, stats)
        
        # Continuamos recorriendo recursivamente los valores del diccionario
        # para encontrar 'procedimientos' anidados (ej. dentro de 'servicios')
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                recorrer_datos(value, cum_dict, cum_modificado, stats)


