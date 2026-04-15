"""
Módulo para generar reportes de cambios en JSON RIPS.
Documenta fechas corregidas, documentos completados y diagnósticos modificados.
"""

import pandas as pd
from io import BytesIO
from datetime import datetime


def generar_reporte_cambios(cambios_fechas: list, cambios_documentos: list, cambios_sustituciones: list = None, cambios_diagnosticos: list = None, cambios_contrato: list = None) -> BytesIO:
    """
    Genera un archivo Excel con el reporte de todos los cambios realizados.
    
    Args:
        cambios_fechas: Lista de diccionarios con cambios de fechas
        cambios_documentos: Lista de diccionarios con cambios de documentos
        cambios_sustituciones: Lista de diccionarios con cambios de diagnósticos, finalidades y causas (PyP)
        cambios_diagnosticos: Lista de diccionarios con cambios de diagnósticos y finalidades (BC/Compuestos)
        cambios_contrato: Lista de CUPS fuera de contrato detectados en consultas/procedimientos
    
    Returns:
        BytesIO con el archivo Excel generado
    """
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hoja 1: Cambios de Fechas
        if cambios_fechas:
            df_fechas = pd.DataFrame(cambios_fechas)
            df_fechas.to_excel(writer, sheet_name='Fechas Corregidas', index=False)
        else:
            # Hoja vacía con mensaje
            df_vacio = pd.DataFrame([{'Mensaje': 'No se realizaron correcciones de fechas'}])
            df_vacio.to_excel(writer, sheet_name='Fechas Corregidas', index=False)
        
        # Hoja 2: Cambios de Documentos
        if cambios_documentos:
            df_docs = pd.DataFrame(cambios_documentos)
            df_docs.to_excel(writer, sheet_name='Documentos Completados', index=False)
        else:
            df_vacio = pd.DataFrame([{'Mensaje': 'No se completaron documentos'}])
            df_vacio.to_excel(writer, sheet_name='Documentos Completados', index=False)
        
        # Hoja 3: Cambios de Sustituciones (Diagnósticos, Finalidades y Causas)
        if cambios_sustituciones is not None:
            if cambios_sustituciones:
                df_sust = pd.DataFrame(cambios_sustituciones)
                df_sust.to_excel(writer, sheet_name='Sustituciones PYP', index=False)
            else:
                df_vacio = pd.DataFrame([{'Mensaje': 'No se aplicaron sustituciones'}])
                df_vacio.to_excel(writer, sheet_name='Sustituciones PYP', index=False)
        
        # Hoja 4: Cambios de Diagnósticos y Finalidades (BC/Compuestos)
        if cambios_diagnosticos is not None:
            if cambios_diagnosticos:
                df_diag = pd.DataFrame(cambios_diagnosticos)
                df_diag.to_excel(writer, sheet_name='Cambios Servicios', index=False)
            else:
                df_vacio = pd.DataFrame([{'Mensaje': 'No se realizaron cambios en servicios'}])
                df_vacio.to_excel(writer, sheet_name='Cambios Servicios', index=False)

        # Hoja 5: CUPS fuera de contrato
        if cambios_contrato is not None:
            if cambios_contrato:
                df_contrato = pd.DataFrame(cambios_contrato)
                df_contrato.to_excel(writer, sheet_name='CUPS No Contratados', index=False)
            else:
                df_vacio = pd.DataFrame([{'Mensaje': 'No se detectaron CUPS fuera de contrato'}])
                df_vacio.to_excel(writer, sheet_name='CUPS No Contratados', index=False)
        
        # Hoja 6: Resumen estructurado
        filas = []

        def seccion(titulo):
            filas.append({'Sección': f'── {titulo} ──', 'Detalle': '', 'Cantidad': ''})

        def fila(detalle, cantidad):
            filas.append({'Sección': '', 'Detalle': detalle, 'Cantidad': cantidad})

        def separador():
            filas.append({'Sección': '', 'Detalle': '', 'Cantidad': ''})

        # ── CORRECCIÓN DE FECHAS ──
        n_fechas = len(cambios_fechas) if cambios_fechas else 0
        seccion('CORRECCIÓN DE FECHAS')
        fila('Total fechas corregidas', n_fechas)
        if cambios_fechas:
            from collections import Counter
            by_tipo = Counter(c.get('Tipo Servicio', 'Otro') for c in cambios_fechas)
            for tipo, cnt in sorted(by_tipo.items()):
                fila(f'  · {tipo}', cnt)
        separador()

        # ── COMPLEMENTO DE PROFESIONALES ──
        n_docs = len(cambios_documentos) if cambios_documentos else 0
        seccion('COMPLEMENTO DE PROFESIONALES')
        fila('Total documentos completados', n_docs)
        if cambios_documentos:
            from collections import Counter
            by_fuente = Counter(c.get('Fuente', 'Desconocida') for c in cambios_documentos)
            for fuente, cnt in sorted(by_fuente.items()):
                fila(f'  · Fuente: {fuente}', cnt)
            by_tipo_srv = Counter(c.get('Tipo Servicio', 'Otro') for c in cambios_documentos)
            for tipo, cnt in sorted(by_tipo_srv.items()):
                fila(f'  · Servicio: {tipo}', cnt)
        separador()

        # ── SUSTITUCIONES PyP ──
        if cambios_sustituciones is not None:
            n_sust = len(cambios_sustituciones)
            seccion('SUSTITUCIONES PyP (Motor Lógico)')
            fila('Total registros modificados', n_sust)
            cons_sust = sum(1 for c in cambios_sustituciones if c.get('Tipo') == 'CONSULTA')
            proc_sust = sum(1 for c in cambios_sustituciones if c.get('Tipo') == 'PROCEDIMIENTO')
            fila('  · Consultas', cons_sust)
            fila('  · Procedimientos', proc_sust)
            diag_camb = sum(1 for c in cambios_sustituciones
                            if c.get('Diagnostico_Original', '') != c.get('Diagnostico_Final', ''))
            fin_camb = sum(1 for c in cambios_sustituciones
                           if c.get('Finalidad_Original', '') != c.get('Finalidad_Nueva', ''))
            causa_camb = sum(1 for c in cambios_sustituciones
                             if c.get('Causa_Original', '') != c.get('Causa_Nueva', ''))
            fila('  · Diagnóstico modificado', diag_camb)
            fila('  · Finalidad modificada', fin_camb)
            if causa_camb:
                fila('  · Causa modificada', causa_camb)
            fuera_contrato = sum(1 for c in cambios_sustituciones if c.get('En_Contrato') == 'No')
            if fuera_contrato:
                fila('  · Fuera de contrato (excluidos)', fuera_contrato)
            separador()

        # ── CAMBIOS EN SERVICIOS BC / COMPUESTOS ──
        if cambios_diagnosticos is not None:
            n_diag = len(cambios_diagnosticos)
            seccion('CAMBIOS EN SERVICIOS BC / COMPUESTOS')
            fila('Total registros en reporte', n_diag)
            cons_bc = sum(1 for c in cambios_diagnosticos if c.get('Tipo') == 'CONSULTA')
            proc_bc = sum(1 for c in cambios_diagnosticos if c.get('Tipo') == 'PROCEDIMIENTO')
            fila('  · Consultas', cons_bc)
            fila('  · Procedimientos', proc_bc)
            cambios_dx  = sum(1 for c in cambios_diagnosticos if c.get('Cambio_Diagnostico') == 'Sí')
            cambios_fin = sum(1 for c in cambios_diagnosticos if c.get('Cambio_Finalidad') == 'Sí')
            cambios_cau = sum(1 for c in cambios_diagnosticos if c.get('Cambio_Causa') == 'Sí')
            fila('  · Diagnóstico modificado', cambios_dx)
            fila('  · Finalidad modificada', cambios_fin)
            if cambios_cau:
                fila('  · Causa modificada', cambios_cau)
            fuera_bc = sum(1 for c in cambios_diagnosticos if c.get('En_Contrato') == 'No')
            si_bc    = sum(1 for c in cambios_diagnosticos if c.get('En_Contrato') == 'Sí')
            if fuera_bc:
                fila('  · Fuera de contrato (excluidos)', fuera_bc)
            if si_bc:
                fila('  · En contrato (procesados)', si_bc)
            separador()

        # ── CUPS FUERA DE CONTRATO ──
        if cambios_contrato is not None:
            n_contrato = len(cambios_contrato)
            seccion('CUPS FUERA DE CONTRATO')
            fila('Total registros fuera de contrato', n_contrato)
            if cambios_contrato:
                cons_no_contrato = sum(1 for c in cambios_contrato if c.get('tipo_servicio') == 'consulta')
                proc_no_contrato = sum(1 for c in cambios_contrato if c.get('tipo_servicio') == 'procedimiento')
                fila('  · Consultas', cons_no_contrato)
                fila('  · Procedimientos', proc_no_contrato)
            separador()

        # ── TOTALES ──
        total = n_fechas + n_docs + \
                (len(cambios_sustituciones) if cambios_sustituciones else 0) + \
                (len(cambios_diagnosticos) if cambios_diagnosticos else 0) + \
                (len(cambios_contrato) if cambios_contrato else 0)
        seccion('TOTALES')
        fila('Total general de cambios registrados', total)
        fila('Fecha de generación', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        df_resumen = pd.DataFrame(filas)
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
    
    output.seek(0)
    return output
