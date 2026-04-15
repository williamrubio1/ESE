"""Utilidades compartidas para identidad y documentos en flujos RIPS."""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime

import pandas as pd

from modules.format_standards import calcular_edad_en_dias, normalizar_documento, validar_tipo_documento_por_edad


TIPOS_ESPECIALES_SIN_CAMBIO = {'PT', 'PPT', 'PE', 'CE', 'CD', 'SC', 'AS', 'MS', 'CN'}


def _emit(message, logger=None, level='info'):
    if logger is not None:
        log_method = getattr(logger, level, None)
        if callable(log_method):
            log_method(message)
            return
    print(message)


def validar_tipos_documento_usuarios(usuarios_list, logger=None, include_cn_priority=False):
    """Corrige tipos de documento de usuarios con base en edad y homologa duplicados."""
    _emit("\nValidando tipos de documento por edad...", logger)

    correcciones = 0
    for usuario in usuarios_list:
        fecha_nacimiento = usuario.get('fechaNacimiento', '')
        tipo_actual = usuario.get('tipoDocumentoIdentificacion', '')

        if not fecha_nacimiento or tipo_actual in TIPOS_ESPECIALES_SIN_CAMBIO:
            continue

        fechas_atencion = []
        servicios = usuario.get('servicios', {})
        for tipo_servicio in ['consultas', 'procedimientos']:
            for servicio in servicios.get(tipo_servicio, []) or []:
                fecha = servicio.get('fechaInicioAtencion', '')
                if fecha:
                    fechas_atencion.append(fecha)

        fecha_max_atencion = max(fechas_atencion) if fechas_atencion else datetime.now().strftime('%Y-%m-%d')
        tipo_correcto = validar_tipo_documento_por_edad(fecha_nacimiento, tipo_actual, fecha_max_atencion)

        if tipo_correcto != tipo_actual:
            num_doc = usuario.get('numDocumentoIdentificacion', '?')
            edad_dias = calcular_edad_en_dias(fecha_nacimiento, fecha_max_atencion)
            _emit(
                f"      Corrigiendo doc {num_doc}: {tipo_actual} -> {tipo_correcto} "
                f"(edad: {edad_dias} días, nac: {fecha_nacimiento})",
                logger,
                'warning',
            )
            usuario['tipoDocumentoIdentificacion'] = tipo_correcto
            correcciones += 1

    if correcciones > 0:
        _emit(f"   {correcciones} tipos de documento corregidos segun edad", logger)
        _emit("   Rangos en dias: RC (0-2556), TI (2557-6574), CC (6575+)", logger)
    else:
        _emit("   Todos los tipos de documento son correctos", logger)

    usuarios_por_doc = defaultdict(list)
    for idx, usuario in enumerate(usuarios_list):
        num_doc = normalizar_documento(usuario.get('numDocumentoIdentificacion', ''))
        if num_doc:
            usuarios_por_doc[num_doc].append(idx)

    normalizaciones = 0
    for num_doc, indices in usuarios_por_doc.items():
        if len(indices) <= 1:
            continue

        tipos = [usuarios_list[i].get('tipoDocumentoIdentificacion', '') for i in indices]
        tipos_unicos = set(tipos)
        if len(tipos_unicos) <= 1:
            continue

        tipo_final = 'RC'
        if 'PT' in tipos_unicos or 'PPT' in tipos_unicos:
            tipo_final = 'PT'
        elif any(tipo in tipos_unicos for tipo in ['PE', 'CE', 'CD', 'SC']):
            tipo_final = next(tipo for tipo in ['PE', 'CE', 'CD', 'SC'] if tipo in tipos_unicos)
        elif 'CC' in tipos_unicos:
            tipo_final = 'CC'
        elif 'TI' in tipos_unicos:
            tipo_final = 'TI'
        elif include_cn_priority and 'CN' in tipos_unicos:
            tipo_final = 'CN'

        _emit(f"      Normalizando tipos para doc {num_doc}: {tipos_unicos} -> {tipo_final}", logger, 'warning')
        for idx in indices:
            tipo_actual = usuarios_list[idx].get('tipoDocumentoIdentificacion', '')
            if tipo_actual != tipo_final:
                _emit(f"         Cambiando usuario idx={idx}: {tipo_actual} -> {tipo_final}", logger, 'warning')
                usuarios_list[idx]['tipoDocumentoIdentificacion'] = tipo_final
                normalizaciones += 1

    if normalizaciones > 0:
        _emit(f"   {normalizaciones} normalizaciones adicionales de tipos duplicados", logger)

    return usuarios_list


def consolidar_usuarios_por_documento(usuarios_list, service_types, logger=None):
    """Consolida usuarios duplicados por documento y preserva la estructura de servicios."""
    usuarios_dict = {}
    _emit("\nVerificando duplicados por documento...", logger)

    for user in usuarios_list:
        num_doc = normalizar_documento(user.get('numDocumentoIdentificacion', ''))
        tipo_doc = user.get('tipoDocumentoIdentificacion', '')

        if num_doc not in usuarios_dict:
            usuarios_dict[num_doc] = user.copy()
            usuarios_dict[num_doc].setdefault('servicios', {})
            continue

        tipo_existente = usuarios_dict[num_doc].get('tipoDocumentoIdentificacion', '')
        _emit(f"      Consolidando doc {num_doc}: tipo existente={tipo_existente}, tipo duplicado={tipo_doc}", logger)

        if (tipo_existente == 'PPT' and tipo_doc == 'PT') or (tipo_existente == 'PT' and tipo_doc == 'PPT'):
            _emit("         ⚠️ Detectado PPT+PT → Consolidando en PT", logger, 'warning')
            usuarios_dict[num_doc]['tipoDocumentoIdentificacion'] = 'PT'

        servicios_existentes = usuarios_dict[num_doc].setdefault('servicios', {})
        for tipo_servicio in service_types:
            servicios_nuevos = user.get('servicios', {}).get(tipo_servicio, [])
            if not servicios_nuevos:
                continue
            servicios_existentes.setdefault(tipo_servicio, [])
            servicios_existentes[tipo_servicio].extend(servicios_nuevos)
            _emit(f"         + {len(servicios_nuevos)} {tipo_servicio} agregados", logger)

    usuarios_consolidados = list(usuarios_dict.values())

    conversiones = 0
    for usuario in usuarios_consolidados:
        if usuario.get('tipoDocumentoIdentificacion') == 'PPT':
            num_doc = usuario.get('numDocumentoIdentificacion', '')
            _emit(f"      Convirtiendo PPT → PT para doc {num_doc} (sin duplicados)", logger)
            usuario['tipoDocumentoIdentificacion'] = 'PT'
            conversiones += 1

    for idx, usuario in enumerate(usuarios_consolidados, 1):
        usuario['consecutivo'] = idx
        for tipo_servicio in service_types:
            for idx_servicio, servicio in enumerate(usuario.get('servicios', {}).get(tipo_servicio, []) or [], 1):
                servicio['consecutivo'] = idx_servicio

    duplicados = len(usuarios_list) - len(usuarios_consolidados)
    if duplicados > 0:
        _emit(f"   {duplicados} duplicados consolidados", logger)
        _emit(f"   {len(usuarios_list)} usuarios -> {len(usuarios_consolidados)} usuarios unicos", logger)
        if conversiones > 0:
            _emit(f"   {conversiones} conversiones PPT -> PT", logger)
        _emit("   Consecutivos renumerados", logger)
        _emit("   Tipo de documento corregido por edad (en dias)", logger)
        _emit("   Rangos: RC (0-2556), TI (2557-6574), CC (6575+)", logger)
    else:
        _emit("   No se encontraron duplicados", logger)
        if conversiones > 0:
            _emit(f"   {conversiones} conversiones PPT -> PT", logger)

    return usuarios_consolidados


def normalizar_ppt_pt_en_dataframes(df_usuarios, service_dataframes):
    """Homologa PPT/PT en DataFrames de usuarios y servicios asociados."""
    if df_usuarios.empty:
        return df_usuarios, service_dataframes

    df_usuarios['tipoDocumentoIdentificacion'] = df_usuarios['tipoDocumentoIdentificacion'].fillna('')
    counts = df_usuarios['numDocumentoIdentificacion'].value_counts()
    usuarios_a_eliminar = []

    for num_doc in counts[counts > 1].index:
        mask = df_usuarios['numDocumentoIdentificacion'] == num_doc
        registros = df_usuarios[mask]
        tipos = registros['tipoDocumentoIdentificacion'].unique()
        if 'PPT' not in tipos or 'PT' not in tipos:
            continue

        idx_ppt = registros[registros['tipoDocumentoIdentificacion'] == 'PPT'].index.tolist()
        for df in service_dataframes:
            if df is None or df.empty:
                continue
            mask_tipo = (df['numDocumento_usuario'] == num_doc) & (df['tipoDocumento_usuario'] == 'PPT')
            df.loc[mask_tipo, 'tipoDocumento_usuario'] = 'PT'
        usuarios_a_eliminar.extend(idx_ppt)

    if usuarios_a_eliminar:
        df_usuarios.drop(usuarios_a_eliminar, inplace=True)
        df_usuarios.reset_index(drop=True, inplace=True)
        df_usuarios['consecutivo'] = range(1, len(df_usuarios) + 1)

    counts = df_usuarios['numDocumentoIdentificacion'].value_counts()
    for idx, row in df_usuarios.iterrows():
        if row['tipoDocumentoIdentificacion'] != 'PPT':
            continue
        num_doc = row['numDocumentoIdentificacion']
        if counts[num_doc] != 1:
            continue
        df_usuarios.at[idx, 'tipoDocumentoIdentificacion'] = 'PT'
        for df in service_dataframes:
            if df is None or df.empty:
                continue
            mask_tipo = (df['numDocumento_usuario'] == num_doc) & (df['tipoDocumento_usuario'] == 'PPT')
            df.loc[mask_tipo, 'tipoDocumento_usuario'] = 'PT'

    return df_usuarios, service_dataframes


def crear_pool_contextual(servicio_specs):
    """Construye un índice contextual de documentos profesionales por prestador y código."""
    pool = {}
    for df, codigo_col in servicio_specs:
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            tipo_prof = row.get('tipoDocumentoIdentificacion_profesional', '')
            num_prof = row.get('numDocumentoIdentificacion_profesional', '')
            if not (tipo_prof and str(tipo_prof).strip() and num_prof and str(num_prof).strip()):
                continue
            cod_prestador = row.get('codPrestador', '')
            cod_servicio = row.get(codigo_col, '')
            if cod_prestador and cod_servicio:
                pool[(str(cod_prestador), str(cod_servicio))] = (str(tipo_prof).strip(), str(num_prof).strip())
    return pool


def crear_pools_usuario(*service_frames):
    """Recolecta tipos y números válidos de documentos profesionales del mismo usuario."""
    tipos_validos = set()
    nums_validos = set()
    for df in service_frames:
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            tipo = row.get('tipoDocumentoIdentificacion_profesional', '')
            num = row.get('numDocumentoIdentificacion_profesional', '')
            if tipo and str(tipo).strip():
                tipos_validos.add(str(tipo).strip())
            if num and str(num).strip():
                nums_validos.add(str(num).strip())
    return tipos_validos, nums_validos


def complementar_documento_profesional(tipo_doc, num_doc, cod_prestador, cod_servicio, pool_contextual, tipos_validos_usuario, nums_validos_usuario):
    """Completa documentos profesionales vacíos conservando la regla actual de prioridad."""
    if not tipo_doc or not str(tipo_doc).strip():
        tipo_doc = list(tipos_validos_usuario)[0] if tipos_validos_usuario else 'CC'

    if not num_doc or not str(num_doc).strip():
        clave = (str(cod_prestador), str(cod_servicio))
        if clave in pool_contextual:
            _, num_doc = pool_contextual[clave]
        elif nums_validos_usuario:
            num_doc = random.choice(list(nums_validos_usuario))
        else:
            num_doc = ''

    return str(tipo_doc).strip() if tipo_doc else '', str(num_doc).strip() if num_doc else ''


def completar_documentos_profesionales_usuario(usuario, service_types):
    """Completa documentos profesionales faltantes en servicios ya reconstruidos."""
    servicios = usuario.get('servicios', {})
    todos_documentos_validos = []

    for servicio_tipo in service_types:
        for servicio in servicios.get(servicio_tipo, []) or []:
            num_doc = servicio.get('numDocumentoIdentificacion', '')
            if num_doc and str(num_doc).strip() and not pd.isna(num_doc):
                doc_str = str(num_doc).strip()
                if doc_str not in todos_documentos_validos:
                    todos_documentos_validos.append(doc_str)

    for servicio_tipo in service_types:
        for servicio in servicios.get(servicio_tipo, []) or []:
            if 'tipoDocumentoIdentificacion' in servicio:
                tipo_doc = servicio.get('tipoDocumentoIdentificacion', '')
                if not tipo_doc or tipo_doc == '' or pd.isna(tipo_doc):
                    servicio['tipoDocumentoIdentificacion'] = 'CC'

            if 'numDocumentoIdentificacion' in servicio:
                num_doc = servicio.get('numDocumentoIdentificacion', '')
                if not num_doc or num_doc == '' or pd.isna(num_doc):
                    servicio['numDocumentoIdentificacion'] = random.choice(todos_documentos_validos) if todos_documentos_validos else ''
