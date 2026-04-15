"""
Aplicación Flask para Validación de JSON
Consolida ValidacionPYP y ValidacionBC en una sola interfaz web
"""

import sys
import os

# Forzar unbuffered output desde el inicio
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session, send_from_directory, make_response
from werkzeug.utils import secure_filename
from modules.tabla_unica_pyp import procesar_json_pyp
from modules.reformador_pyp import reformar_excel_pyp
from modules.tabla_unica_bc import procesar_json_bc
from modules.reformador_bc import reformar_excel_bc
import json
import re

# Importar módulo de optimizaciones
from modules.optimizaciones import (
    MemoryManager,
    FileCache,
    OutputCleaner,
    validate_file_size,
    validate_json_structure,
    RateLimiter,
    cleanup_session_files,
    should_compress_response,
    ResourceMonitor
)


def save_compact_json(data, filepath):
    """Guarda JSON con formato compacto: [{ en lugar de [\\n{"""
    # Primero generar JSON con formato estándar
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    # Aplicar transformaciones para formato compacto en arrays
    json_str = re.sub(r'\[\s+\{', '[{', json_str)  # [{ en lugar de [\n  {
    json_str = re.sub(r'\},\s+\{', '}, {', json_str)  # }, { en lugar de },\n  {
    # Mantener }\n] (salto de línea antes del corchete final)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(json_str)
from modules.tabla_unica_compuestos import procesar_json_compuestos
from modules.separador_json import separar_por_prestador
from modules.excel_to_json import convert_excel_to_json
from modules.json_to_excel import convertir_json_a_excel
from modules.ocr_hcl import procesar_multiples_pdfs, generar_archivos_txt
import logging
import zipfile

app = Flask(__name__, static_folder='static')
app.secret_key = 'validacion_json_secret_key_2026'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 650 * 1024 * 1024  # 650MB max (para módulo JSON → Excel con archivos grandes)
app.config['MAX_FORM_PARTS'] = 10000  # Permitir hasta 10.000 archivos simultáneos (consolidador con muchos JSON)

# Versionado automático de archivos estáticos para evitar caché
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    """Agrega timestamp a archivos estáticos para forzar recarga"""
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path, 'static', filename)
            if os.path.isfile(file_path):
                values['v'] = int(os.path.getmtime(file_path))
    return url_for(endpoint, **values)

# Configurar logging para que se muestre en consola
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout,
    force=True
)

# Inicializar instancias de optimización
file_cache = FileCache()
output_cleaner = OutputCleaner(app.config['OUTPUT_FOLDER'])
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)
resource_monitor = ResourceMonitor()
memory_manager = MemoryManager()

# Asegurar que existan las carpetas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'json', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Middleware: before_request - Rate limiting y limpieza
@app.before_request
def before_request():
    """Middleware ejecutado antes de cada request"""
    # Limpiar sesión al cambiar de módulo
    current_module = None
    if request.endpoint:
        # Identificar módulo basado en el endpoint (incluye todas las rutas del módulo)
        if request.endpoint == 'pyp' or request.endpoint.startswith('pyp_'):
            current_module = 'pyp'
        elif request.endpoint == 'bc' or request.endpoint.startswith('bc_'):
            current_module = 'bc'
        elif 'compuestos' in request.endpoint:
            current_module = 'compuestos'
        elif 'consolidador' in request.endpoint:
            current_module = 'consolidador'
    
    # Si cambiamos de módulo, limpiar sesión del módulo anterior
    if current_module:
        last_module = session.get('current_module')
        if last_module and last_module != current_module:
            # Limpiar variables del módulo anterior
            keys_to_remove = [k for k in session.keys() if 
                            k.startswith(last_module + '_') or 
                            (k in ['last_processed_file', 'excel_available', 'excel_reformado_available', 
                                   'json_available', 'reporte_available', 'tipo'] and last_module != current_module)]
            for key in keys_to_remove:
                session.pop(key, None)
        session['current_module'] = current_module
    
    # Aplicar rate limiting solo en rutas de procesamiento
    if request.endpoint and any(x in request.endpoint for x in ['procesar', 'reformar', 'separar', 'convert']):
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(client_ip):
            flash('Demasiadas solicitudes. Por favor espere un momento antes de intentar nuevamente.', 'error')
            return redirect(url_for('index'))
    
    # Limpieza periódica de archivos antiguos
    if output_cleaner.should_cleanup():
        deleted_count = output_cleaner.cleanup_old_files()
        if deleted_count > 0:
            logging.info(f"Limpieza automática: {deleted_count} archivos eliminados")
    
    # Limpieza de caché expirado
    file_cache.cleanup_expired()

# Middleware: after_request - Headers de caché
@app.after_request
def after_request(response):
    """Middleware ejecutado después de cada request"""
    # Agregar headers de caché para archivos estáticos
    if request.path.startswith('/static/'):
        # En desarrollo: caché corto para ver cambios rápidamente
        # En producción: cambiar a 'public, max-age=31536000' (1 año)
        response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutos
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif request.endpoint in ['index', 'pyp', 'bc', 'compuestos', 'consolidador']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pyp', methods=['GET', 'POST'])
def pyp():
    """Ruta para procesar archivos PYP (Procedimientos y Programas)"""
    return render_template('pyp.html')

@app.route('/bc', methods=['GET', 'POST'])
def bc():
    """Ruta para procesar archivos BC (Baja Complejidad)"""
    return render_template('bc.html')

@app.route('/pyp/procesar_json', methods=['POST'])
@MemoryManager.cleanup_after_request
def pyp_procesar_json():
    """Procesa uno o más JSON de PYP y genera Excel y JSON reformado con verificación de fechas"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('pyp'))
    
    files = request.files.getlist('file')
    mes_evaluado = request.form.get('mes_evaluado')
    eps_id = request.form.get('eps_id', '').strip()

    if not files or all(f.filename == '' for f in files):
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('pyp'))
    
    if not mes_evaluado:
        flash('Debe seleccionar un mes para evaluar', 'error')
        return redirect(url_for('pyp'))

    if not eps_id:
        flash('Debe seleccionar una EPS', 'error')
        return redirect(url_for('pyp'))
    
    # Filtrar archivos válidos
    valid_files = [f for f in files if f and f.filename != '' and allowed_file(f.filename)]
    
    if not valid_files:
        flash('Tipo de archivo no permitido. Solo se aceptan archivos JSON.', 'error')
        return redirect(url_for('pyp'))
    
    archivos_procesados = []
    archivos_error = []
    
    for file in valid_files:
        try:
            # Validar tamaño del archivo
            validate_file_size(file, max_size_mb=50)
            
            # Obtener nombre sin extensión
            filename = secure_filename(file.filename)
            nombre_base = os.path.splitext(filename)[0]
            
            # Generar clave de caché
            cache_key = f"pyp_{nombre_base}_{mes_evaluado}"
            
            # Verificar si existe en caché
            cached_result = file_cache.get(cache_key)
            if cached_result:
                logging.info(f"Resultado en caché para {nombre_base}")
                flash(cached_result['message'], 'success')
                session['pyp_excel_path'] = cached_result['excel_path']
                session['pyp_json_path'] = cached_result['json_path']
                return redirect(url_for('pyp'))
            
            # Convertir mes a entero
            mes_evaluado = int(mes_evaluado)
            anio_evaluado = 2026
            
            # Leer el contenido del archivo
            file_content = file.read()
            file.seek(0)  # Reset para usarlo de nuevo
            
            # Procesar el archivo JSON y generar 2 versiones de Excel
            from io import BytesIO
            from modules.verificador_fechas import aplicar_verificacion_json, obtener_nombre_mes
            from modules.completador_documentos import aplicar_completado_json
            import json
            
            # Leer JSON y aplicar correcciones en orden:
            # 1. Completar documentos de identificación vacíos
            # 2. Verificar y corregir fechas
            datos_json = json.loads(file_content)
            
            # Validar estructura y cantidad de usuarios
            validate_json_structure(datos_json, max_usuarios=12000)
            
            datos_json_con_docs, cambios_documentos = aplicar_completado_json(datos_json, generar_reporte=True)
            datos_json_corregidos, cambios_fechas = aplicar_verificacion_json(datos_json_con_docs, mes_evaluado, anio_evaluado, generar_reporte=True)

            # PASO 0: Reportar CUPS fuera de contrato antes de cualquier validación clínica
            from modules.homologacion_cups import aplicar_homologacion_rips
            datos_json_corregidos, cambios_cups = aplicar_homologacion_rips(datos_json_corregidos, eps_id=eps_id, generar_reporte=True)

            # Aplicar sustituciones PYP en el JSON antes de guardarlo
            from modules.tabla_unica_pyp import aplicar_sustituciones_pyp_json
            from modules.config_eps import EPS_CONFIG
            datos_json_corregidos, cambios_sustituciones = aplicar_sustituciones_pyp_json(
                datos_json_corregidos,
                config_eps=EPS_CONFIG.get(eps_id),
                generar_reporte=True,
            )
            
            # Convertir a bytes para pasar a procesar_json_pyp
            file_content_corregido = json.dumps(datos_json_corregidos, ensure_ascii=False, indent=2).encode('utf-8')
            
            excel_original, excel_corregido, cambios_df = procesar_json_pyp(BytesIO(file_content_corregido), nombre_base)
            
            # Generar reporte de cambios (incluye asignaciones de diagnóstico del nivel DataFrame)
            from modules.generador_reportes import generar_reporte_cambios
            todos_cambios = (cambios_sustituciones or []) + (cambios_df or [])
            reporte_cambios = generar_reporte_cambios(
                cambios_fechas,
                cambios_documentos,
                todos_cambios,
                cambios_contrato=cambios_cups,
            )
            
            # Guardar reporte3
            reporte_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{nombre_base}_reporte_cambios.xlsx')
            with open(reporte_path, 'wb') as f:
                f.write(reporte_cambios.getvalue())
            
            # Convertir de vuelta a bytes -- ya generado arriba
            # excel_original y excel_corregido ya fueron generados por procesar_json_pyp
            
            # Guardar Excel ORIGINAL (sin correcciones) para descarga
            excel_original.seek(0)
            excel_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{nombre_base}.xlsx')
            with open(excel_path, 'wb') as f:
                f.write(excel_original.read())
            
            # Guardar Excel REFORMADO (con validaciones) para descarga
            excel_corregido.seek(0)
            excel_reformado_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{nombre_base}_Reformado.xlsx')
            with open(excel_reformado_path, 'wb') as f:
                f.write(excel_corregido.read())
            
            # Generar JSON reformado pasando el Excel reformado por el reformador
            # Esto asegura que tenga consecutivos correctos, null en lugar de "None", etc.
            excel_corregido.seek(0)
            json_reformado = reformar_excel_pyp(excel_corregido, nombre_base)
            json_reformado.seek(0)
            json_path = os.path.join(app.config['OUTPUT_FOLDER'], f'_{nombre_base}.json')
            with open(json_path, 'wb') as f:
                f.write(json_reformado.read())
            
            # Guardar información en sesión para las descargas (solo del último archivo)
            # Almacenar rutas en sesión
            session['pyp_excel_path'] = excel_path
            session['pyp_json_path'] = json_path
            
            # Guardar en caché
            nombre_mes_cache = obtener_nombre_mes(mes_evaluado)
            success_message = f'Archivos procesados exitosamente para {nombre_mes_cache} {anio_evaluado}: {nombre_base}.xlsx y _{nombre_base}.json'
            file_cache.set(cache_key, {
                'message': success_message,
                'excel_path': excel_path,
                'json_path': json_path
            })
            
            # Registrar uso de recursos
            resource_monitor.log_resource_usage(f"PYP procesado: {nombre_base}")
            
            archivos_procesados.append(nombre_base)
            
        except Exception as e:
            archivos_error.append(f'{nombre_base}: {str(e)}')
    
    # Mostrar resumen del procesamiento
    if archivos_procesados:
        if len(archivos_procesados) == 1:
            from modules.verificador_fechas import obtener_nombre_mes
            nombre_mes = obtener_nombre_mes(int(mes_evaluado))
            flash(f'Archivo procesado exitosamente para {nombre_mes} 2026: {archivos_procesados[0]}.xlsx y _{archivos_procesados[0]}.json', 'success')
        else:
            flash(f'✓ {len(archivos_procesados)} archivos procesados exitosamente: {", ".join(archivos_procesados)}', 'success')
        
        # Guardar el último archivo procesado en sesión
        session['last_processed_file'] = archivos_procesados[-1]
        session['excel_available'] = True
        session['excel_reformado_available'] = True
        session['json_available'] = True
        session['reporte_available'] = True
        session['tipo'] = 'pyp'
    
    if archivos_error:
        for error in archivos_error:
            flash(f'✗ Error: {error}', 'error')
    
    return redirect(url_for('pyp'))

@app.route('/pyp/reformar_excel', methods=['POST'])
@MemoryManager.cleanup_after_request
def pyp_reformar_excel():
    """Convierte Excel de PYP de vuelta a JSON"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('pyp'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('pyp'))
    
    if file and allowed_file(file.filename):
        try:
            # Validar tamaño del archivo
            validate_file_size(file, max_size_mb=50)
            
            filename = secure_filename(file.filename)
            nombre_base = os.path.splitext(filename)[0]
            json_output = reformar_excel_pyp(file, nombre_base)
            json_output.seek(0)
            json_path = os.path.join(app.config['OUTPUT_FOLDER'], f'_{nombre_base}.json')
            with open(json_path, 'wb') as f:
                f.write(json_output.read())
            session['last_processed_file'] = nombre_base
            session['excel_available'] = session.get('excel_available', False)
            session['json_available'] = True
            session['tipo'] = 'pyp'
            
            resource_monitor.log_resource_usage(f"PYP reformado: {nombre_base}")
            
            flash(f'JSON generado desde Excel: _{nombre_base}.json', 'success')
            return redirect(url_for('pyp'))
        except Exception as e:
            flash(f'Error reformando el archivo: {str(e)}', 'error')
            return redirect(url_for('pyp'))
    else:
        flash('Tipo de archivo no permitido. Solo se aceptan archivos XLSX.', 'error')
        return redirect(url_for('pyp'))

@app.route('/pyp/descargar_excel/<filename>')
def pyp_descargar_excel(filename):
    """Descarga el archivo Excel generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}.xlsx'
            )
        else:
            flash('El archivo Excel no está disponible', 'error')
            return redirect(url_for('pyp'))
    except Exception as e:
        flash(f'Error descargando Excel: {str(e)}', 'error')
        return redirect(url_for('pyp'))

@app.route('/pyp/descargar_excel_reformado/<filename>')
def pyp_descargar_excel_reformado(filename):
    """Descarga el archivo Excel REFORMADO (con validaciones) generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_Reformado.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}_Reformado.xlsx'
            )
        else:
            flash('El archivo Excel Reformado no está disponible', 'error')
            return redirect(url_for('pyp'))
    except Exception as e:
        flash(f'Error descargando Excel Reformado: {str(e)}', 'error')
        return redirect(url_for('pyp'))

@app.route('/pyp/descargar_json/<filename>')
def pyp_descargar_json(filename):
    """Descarga el archivo JSON reformado generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'_{filename}.json')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'_{filename}.json'
            )
        else:
            flash('El archivo JSON no está disponible', 'error')
            return redirect(url_for('pyp'))
    except Exception as e:
        flash(f'Error descargando JSON: {str(e)}', 'error')
        return redirect(url_for('pyp'))

@app.route('/pyp/descargar_reporte/<filename>')
def pyp_descargar_reporte(filename):
    """Descarga el reporte de cambios"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_reporte_cambios.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}_reporte_cambios.xlsx'
            )
        else:
            flash('El reporte de cambios no está disponible', 'error')
            return redirect(url_for('pyp'))
    except Exception as e:
        flash(f'Error descargando reporte: {str(e)}', 'error')
        return redirect(url_for('pyp'))

@app.route('/bc/procesar_json', methods=['POST'])
@MemoryManager.cleanup_after_request
def bc_procesar_json():
    """Procesa uno o más JSON de BC y genera Excel y JSON reformado con verificación de fechas"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('bc'))
    
    files = request.files.getlist('file')
    mes_evaluado = request.form.get('mes_evaluado')
    eps_id = request.form.get('eps_id', '').strip()

    if not files or all(f.filename == '' for f in files):
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('bc'))
    
    if not mes_evaluado:
        flash('Debe seleccionar un mes para evaluar', 'error')
        return redirect(url_for('bc'))

    if not eps_id:
        flash('Debe seleccionar una EPS', 'error')
        return redirect(url_for('bc'))
    
    # Filtrar archivos válidos
    valid_files = [f for f in files if f and f.filename != '' and allowed_file(f.filename)]
    
    if not valid_files:
        flash('Tipo de archivo no permitido. Solo se aceptan archivos JSON.', 'error')
        return redirect(url_for('bc'))
    
    archivos_procesados = []
    archivos_error = []
    
    for file in valid_files:
        try:
            # Validar tamaño del archivo
            validate_file_size(file, max_size_mb=50)
            
            # Obtener nombre sin extensión
            filename = secure_filename(file.filename)
            nombre_base = os.path.splitext(filename)[0]
            
            # Convertir mes a entero
            mes_evaluado = int(mes_evaluado)
            anio_evaluado = 2026
            
            # Generar clave de caché
            cache_key = f"bc_{nombre_base}_{mes_evaluado}"
            
            # Verificar si existe en caché
            cached_result = file_cache.get(cache_key)
            if cached_result:
                logging.info(f"Resultado en caché para {nombre_base}")
                flash(cached_result['message'], 'success')
                session['bc_excel_path'] = cached_result['excel_path']
                session['bc_json_path'] = cached_result['json_path']
                session['last_processed_file'] = nombre_base
                session['excel_available'] = True
                session['excel_reformado_available'] = True
                session['json_available'] = True
                session['reporte_available'] = True
                session['tipo'] = 'bc'
                return redirect(url_for('bc'))
            
            # Leer el contenido del archivo
            file_content = file.read()
            file.seek(0)
            
            # Aplicar correcciones al JSON
            from io import BytesIO
            from modules.verificador_fechas import aplicar_verificacion_json, obtener_nombre_mes
            from modules.completador_documentos import aplicar_completado_json
            import json
            
            # Aplicar correcciones en orden:
            # 1. Completar documentos de identificación vacíos
            # 2. Verificar y corregir fechas
            datos_json = json.loads(file_content)
            
            # Validar estructura y cantidad de usuarios
            validate_json_structure(datos_json, max_usuarios=10000)
            
            datos_json_con_docs, cambios_documentos = aplicar_completado_json(datos_json, generar_reporte=True)
            datos_json_corregidos, cambios_fechas = aplicar_verificacion_json(datos_json_con_docs, mes_evaluado, anio_evaluado, generar_reporte=True)

            # PASO 0: Reportar CUPS fuera de contrato antes de cualquier validación clínica
            from modules.homologacion_cups import aplicar_homologacion_rips
            datos_json_corregidos, cambios_cups = aplicar_homologacion_rips(datos_json_corregidos, eps_id=eps_id, generar_reporte=True)

            # Aplicar cambios BC en el JSON antes de guardarlo
            from modules.motor_logico import aplicar_cambios_bc_json
            from modules.config_eps import EPS_CONFIG
            datos_json_corregidos, cambios_bc = aplicar_cambios_bc_json(
                datos_json_corregidos,
                config_eps=EPS_CONFIG.get(eps_id),
                generar_reporte=True,
            )
            
            file_content_corregido = json.dumps(datos_json_corregidos, ensure_ascii=False, indent=2).encode('utf-8')
            
            # Procesar el archivo JSON y generar 2 versiones de Excel
            excel_original, excel_corregido, cambios_df = procesar_json_bc(BytesIO(file_content_corregido), nombre_base)
            
            # Generar reporte de cambios (incluye asignaciones de diagnóstico del nivel DataFrame)
            from modules.generador_reportes import generar_reporte_cambios
            todos_cambios_bc = (cambios_bc or []) + (cambios_df or [])
            reporte_cambios = generar_reporte_cambios(
                cambios_fechas,
                cambios_documentos,
                cambios_diagnosticos=todos_cambios_bc,
                cambios_contrato=cambios_cups,
            )
            
            # Guardar reporte
            reporte_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{nombre_base}_reporte_cambios.xlsx')
            with open(reporte_path, 'wb') as f:
                f.write(reporte_cambios.getvalue())
            
            # excel_original y excel_corregido ya fueron generados por procesar_json_bc
            
            # Guardar Excel ORIGINAL (sin correcciones) para descarga
            excel_original.seek(0)
            excel_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{nombre_base}.xlsx')
            with open(excel_path, 'wb') as f:
                f.write(excel_original.read())
            
            # Guardar Excel REFORMADO (con validaciones) para descarga
            excel_corregido.seek(0)
            excel_reformado_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{nombre_base}_Reformado.xlsx')
            with open(excel_reformado_path, 'wb') as f:
                f.write(excel_corregido.read())
            
            # Generar JSON reformado pasando el Excel reformado por el reformador
            # Esto asegura que tenga consecutivos correctos, null en lugar de "None", etc.
            excel_corregido.seek(0)
            json_reformado = reformar_excel_bc(excel_corregido, nombre_base)
            json_reformado.seek(0)
            json_path = os.path.join(app.config['OUTPUT_FOLDER'], f'_{nombre_base}.json')
            with open(json_path, 'wb') as f:
                f.write(json_reformado.read())
            
            # Guardar información en sesión para las descargas (solo del último archivo)
            # Almacenar rutas en sesión
            session['bc_excel_path'] = excel_path
            session['bc_json_path'] = json_path
            
            # Guardar en caché
            from modules.verificador_fechas import obtener_nombre_mes
            nombre_mes_cache = obtener_nombre_mes(mes_evaluado)
            success_message = f'Archivos procesados exitosamente para {nombre_mes_cache}: Excel original, Excel reformado, JSON reformado y reporte completo de cambios (todos los servicios: consultas, procedimientos, medicamentos, otros servicios, urgencias, hospitalización)'
            file_cache.set(cache_key, {
                'message': success_message,
                'excel_path': excel_path,
                'json_path': json_path
            })
            
            # Registrar uso de recursos
            resource_monitor.log_resource_usage(f"BC procesado: {nombre_base}")
            
            archivos_procesados.append(nombre_base)
            
        except Exception as e:
            archivos_error.append(f'{nombre_base}: {str(e)}')
    
    # Mostrar resumen del procesamiento
    if archivos_procesados:
        if len(archivos_procesados) == 1:
            from modules.verificador_fechas import obtener_nombre_mes
            nombre_mes = obtener_nombre_mes(int(mes_evaluado))
            flash(f'Archivo procesado exitosamente para {nombre_mes}: {archivos_procesados[0]} (Excel original, Excel reformado, JSON reformado y reporte completo)', 'success')
        else:
            flash(f'✓ {len(archivos_procesados)} archivos procesados exitosamente: {", ".join(archivos_procesados)}', 'success')
        
        # Guardar el último archivo procesado en sesión
        session['last_processed_file'] = archivos_procesados[-1]
        session['excel_available'] = True
        session['excel_reformado_available'] = True
        session['json_available'] = True
        session['reporte_available'] = True
        session['tipo'] = 'bc'
    
    if archivos_error:
        for error in archivos_error:
            flash(f'✗ Error: {error}', 'error')
    
    return redirect(url_for('bc'))

@app.route('/bc/reformar_excel', methods=['POST'])
@MemoryManager.cleanup_after_request
def bc_reformar_excel():
    """Convierte Excel de BC de vuelta a JSON"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('bc'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('bc'))
    
    if file and allowed_file(file.filename):
        try:
            # Validar tamaño del archivo
            validate_file_size(file, max_size_mb=50)
            
            filename = secure_filename(file.filename)
            nombre_base = os.path.splitext(filename)[0]
            json_output = reformar_excel_bc(file, nombre_base)
            json_output.seek(0)
            json_path = os.path.join(app.config['OUTPUT_FOLDER'], f'_{nombre_base}.json')
            with open(json_path, 'wb') as f:
                f.write(json_output.read())
            session['last_processed_file'] = nombre_base
            session['excel_available'] = session.get('excel_available', False)
            session['json_available'] = True
            session['tipo'] = 'bc'
            
            resource_monitor.log_resource_usage(f"BC reformado: {nombre_base}")
            
            flash(f'JSON BC generado desde Excel: _{nombre_base}.json', 'success')
            return redirect(url_for('bc'))
        except Exception as e:
            flash(f'Error reformando el archivo: {str(e)}', 'error')
            return redirect(url_for('bc'))
    else:
        flash('Tipo de archivo no permitido. Solo se aceptan archivos XLSX.', 'error')
        return redirect(url_for('bc'))

@app.route('/bc/descargar_excel/<filename>')
def bc_descargar_excel(filename):
    """Descarga el archivo Excel generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}.xlsx'
            )
        else:
            flash('El archivo Excel no está disponible', 'error')
            return redirect(url_for('bc'))
    except Exception as e:
        flash(f'Error descargando Excel: {str(e)}', 'error')
        return redirect(url_for('bc'))

@app.route('/bc/descargar_excel_reformado/<filename>')
def bc_descargar_excel_reformado(filename):
    """Descarga el archivo Excel REFORMADO (con validaciones) generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_Reformado.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}_Reformado.xlsx'
            )
        else:
            flash('El archivo Excel Reformado no está disponible', 'error')
            return redirect(url_for('bc'))
    except Exception as e:
        flash(f'Error descargando Excel Reformado: {str(e)}', 'error')
        return redirect(url_for('bc'))

@app.route('/bc/descargar_json/<filename>')
def bc_descargar_json(filename):
    """Descarga el archivo JSON reformado generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'_{filename}.json')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'_{filename}.json'
            )
        else:
            flash('El archivo JSON no está disponible', 'error')
            return redirect(url_for('bc'))
    except Exception as e:
        flash(f'Error descargando JSON: {str(e)}', 'error')
        return redirect(url_for('bc'))

@app.route('/bc/descargar_reporte/<filename>')
def bc_descargar_reporte(filename):
    """Descarga el reporte de cambios"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_reporte_cambios.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}_reporte_cambios.xlsx'
            )
        else:
            flash('El reporte de cambios no está disponible', 'error')
            return redirect(url_for('bc'))
    except Exception as e:
        flash(f'Error descargando reporte: {str(e)}', 'error')
        return redirect(url_for('bc'))

# ============================================================================
# RUTAS PARA COMPUESTOS
# ============================================================================

@app.route('/compuestos', methods=['GET', 'POST'])
def compuestos():
    """Página principal de Compuestos"""
    return render_template('compuestos.html')

@app.route('/compuestos/procesar_json', methods=['POST'])
@MemoryManager.cleanup_after_request
def compuestos_procesar_json():
    """Procesa uno o más JSON de Compuestos y genera Excel + JSON reformado con verificación de fechas"""
    print("=" * 60, flush=True)
    print("📥 Nueva petición: Procesar JSON Compuestos", flush=True)
    
    if 'file' not in request.files:
        print("❌ No se seleccionó ningún archivo", flush=True)
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('compuestos'))
    
    files = request.files.getlist('file')
    mes_evaluado = request.form.get('mes_evaluado')
    eps_id = request.form.get('eps_id', 'capital_salud').strip()

    if not files or all(f.filename == '' for f in files):
        print("❌ Nombre de archivo vacío", flush=True)
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('compuestos'))
    
    if not mes_evaluado:
        print("❌ No se seleccionó mes para evaluar", flush=True)
        flash('Debe seleccionar un mes para evaluar', 'error')
        return redirect(url_for('compuestos'))
    
    # Filtrar archivos válidos
    valid_files = [f for f in files if f and f.filename != '' and allowed_file(f.filename) and f.filename.endswith('.json')]
    
    if not valid_files:
        print("❌ Tipo de archivo no válido", flush=True)
        print("=" * 60, flush=True)
        flash('Por favor sube un archivo JSON válido', 'error')
        return redirect(url_for('compuestos'))
    
    archivos_procesados = []
    archivos_error = []
    
    for file in valid_files:
        try:
            # Validar tamaño del archivo
            validate_file_size(file, max_size_mb=50)
            
            # Guardar archivo temporal
            filename = secure_filename(file.filename)
            filename_sin_ext = os.path.splitext(filename)[0]
            
            # Convertir mes a entero
            mes_evaluado = int(mes_evaluado)
            anio_evaluado = 2026
            
            # Generar clave de caché
            cache_key = f"compuestos_{filename_sin_ext}_{mes_evaluado}"
            
            # Verificar si existe en caché
            cached_result = file_cache.get(cache_key)
            if cached_result:
                logging.info(f"Resultado en caché para {filename_sin_ext}")
                flash(cached_result['message'], 'success')
                session['compuestos_excel_path'] = cached_result['excel_path']
                session['compuestos_json_path'] = cached_result['json_path']
                session['last_processed_file'] = filename_sin_ext
                session['excel_available'] = True
                session['excel_reformado_available'] = True
                session['json_available'] = True
                session['reporte_available'] = True
                session['tipo'] = 'compuestos'
                return redirect(url_for('compuestos'))
            
            print(f"📄 Archivo recibido: {filename}", flush=True)
            print(f"📅 Mes a evaluar: {mes_evaluado}", flush=True)
            
            # Aplicar correcciones al JSON
            from io import BytesIO
            from modules.verificador_fechas import aplicar_verificacion_json, obtener_nombre_mes
            from modules.completador_documentos import aplicar_completado_json
            import json
            
            file_content = file.read()
            datos_json = json.loads(file_content)
            
            # Validar estructura y cantidad de usuarios
            validate_json_structure(datos_json, max_usuarios=12000)
            
            print(f"  ✓ Completando documentos de identificación...", flush=True)
            datos_json_con_docs, cambios_documentos = aplicar_completado_json(datos_json, generar_reporte=True)

            print(f"  ✓ Verificando fechas para el mes {mes_evaluado}...", flush=True)
            datos_json_corregidos, cambios_fechas = aplicar_verificacion_json(datos_json_con_docs, mes_evaluado, anio_evaluado, generar_reporte=True)

            # PASO 0: Reportar CUPS fuera de contrato antes de cualquier validación clínica
            from modules.homologacion_cups import aplicar_homologacion_rips
            print(f"  ✓ Verificando CUPS contra contrato...", flush=True)
            datos_json_corregidos, cambios_cups = aplicar_homologacion_rips(datos_json_corregidos, eps_id=eps_id, generar_reporte=True)

            # Aplicar cambios COMPUESTOS en el JSON antes de guardarlo
            from modules.tabla_unica_compuestos import aplicar_cambios_compuestos_json
            from modules.config_eps import EPS_CONFIG
            print(f"  ✓ Aplicando reglas de Compuestos...", flush=True)
            datos_json_corregidos, cambios_compuestos = aplicar_cambios_compuestos_json(
                datos_json_corregidos,
                config_eps=EPS_CONFIG.get(eps_id),
                generar_reporte=True,
            )
            
            # Generar reporte de cambios (incluir diagnósticos si están disponibles en el procesamiento)
            from modules.generador_reportes import generar_reporte_cambios
            reporte_cambios = generar_reporte_cambios(
                cambios_fechas,
                cambios_documentos,
                cambios_diagnosticos=cambios_compuestos,
                cambios_contrato=cambios_cups,
            )
            
            # Guardar reporte
            reporte_cambios_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename_sin_ext}_reporte_cambios.xlsx')
            with open(reporte_cambios_path, 'wb') as f:
                f.write(reporte_cambios.getvalue())
            print(f"  ✓ Reporte de Cambios: {filename_sin_ext}_reporte_cambios.xlsx", flush=True)
            
            file_content_corregido = json.dumps(datos_json_corregidos, ensure_ascii=False, indent=2).encode('utf-8')
            
            print(f"⏳ Procesando JSON...", flush=True)
            
            # Procesar JSON → Excel (retorna tupla: excel original, excel corregido, reporte, json_reformado)
            excel_original, excel_corregido, reporte_output, json_reformado = procesar_json_compuestos(BytesIO(file_content_corregido), filename_sin_ext)
            
            print(f"💾 Guardando archivos generados...", flush=True)
            
            # Guardar Excel ORIGINAL (sin correcciones) para descarga
            excel_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename_sin_ext}.xlsx')
            with open(excel_path, 'wb') as f:
                f.write(excel_original.getvalue())
            print(f"  ✓ Excel Original: {filename_sin_ext}.xlsx", flush=True)
            
            # Guardar Excel CORREGIDO (con validaciones) para descarga
            excel_corregido_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename_sin_ext}_Reformado.xlsx')
            with open(excel_corregido_path, 'wb') as f:
                f.write(excel_corregido.getvalue())
            print(f"  ✓ Excel Reformado: {filename_sin_ext}_Reformado.xlsx", flush=True)
            
            # Guardar reporte de diagnósticos vacíos si existe
            if reporte_output:
                reporte_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename_sin_ext}_diagnosticos_vacios.xlsx')
                with open(reporte_path, 'wb') as f:
                    f.write(reporte_output.getvalue())
                session['compuestos_reporte_file'] = filename_sin_ext
                print(f"  ✓ Reporte Diagnósticos Vacíos: {filename_sin_ext}_diagnosticos_vacios.xlsx", flush=True)
            else:
                session['compuestos_reporte_file'] = None
            
            # Generar JSON reformado desde el Excel corregido (como PYP/BC)
            # Esto asegura que todos los módulos usen la misma lógica de reformado
            print(f"  ✓ Generando JSON reformado desde Excel corregido...", flush=True)
            from modules.reformador_compuestos import reformar_excel_compuestos
            excel_corregido.seek(0)  # Resetear el buffer
            json_reformado_output = reformar_excel_compuestos(BytesIO(excel_corregido.getvalue()), filename_sin_ext)
            json_reformado_output.seek(0)
            json_path = os.path.join(app.config['OUTPUT_FOLDER'], f'_{filename_sin_ext}.json')
            with open(json_path, 'wb') as f:
                f.write(json_reformado_output.read())
            print(f"  ✓ JSON Reformado: _{filename_sin_ext}.json", flush=True)
            
            # Guardar información en sesión (solo del último archivo)
            session['compuestos_excel_file'] = filename_sin_ext
            session.pop('compuestos_json_from_excel_file', None) # Limpiar el botón de Excel->JSON
            session['compuestos_excel_reformado_file'] = filename_sin_ext
            session['compuestos_json_file'] = filename_sin_ext
            session['compuestos_reporte_cambios_file'] = filename_sin_ext
            session['processed'] = True # Bandera para evitar limpieza en la redirección
            
            # Almacenar rutas en sesión
            session['compuestos_excel_path'] = excel_path
            session['compuestos_json_path'] = json_path
            
            # Guardar en caché
            from modules.verificador_fechas import obtener_nombre_mes
            nombre_mes_cache = obtener_nombre_mes(mes_evaluado)
            success_message = f'✅ Archivos generados exitosamente para {nombre_mes_cache}: Excel original, Excel reformado, JSON reformado, reporte de diagnósticos vacíos y reporte integral de cambios (todos los servicios: consultas, procedimientos, medicamentos, otros servicios, urgencias, hospitalización, recién nacidos)'
            file_cache.set(cache_key, {
                'message': success_message,
                'excel_path': excel_path,
                'json_path': json_path
            })
            
            # Registrar uso de recursos
            resource_monitor.log_resource_usage(f"Compuestos procesado: {filename_sin_ext}")
            
            archivos_procesados.append(filename_sin_ext)
            
        except Exception as e:
            print(f"❌ Error procesando archivo: {str(e)}", flush=True)
            archivos_error.append(f'{filename_sin_ext}: {str(e)}')
    
    # Mostrar resumen del procesamiento
    if archivos_procesados:
        if len(archivos_procesados) == 1:
            from modules.verificador_fechas import obtener_nombre_mes
            nombre_mes = obtener_nombre_mes(int(mes_evaluado))
            flash(f'✅ Archivo procesado exitosamente para {nombre_mes}: {archivos_procesados[0]} (Excel original, Excel reformado, JSON reformado, reporte de diagnósticos vacíos y reporte integral)', 'success')
        else:
            flash(f'✓ {len(archivos_procesados)} archivos procesados exitosamente: {", ".join(archivos_procesados)}', 'success')
    
    if archivos_error:
        for error in archivos_error:
            flash(f'✗ Error: {error}', 'error')
    
    print("✅ Procesamiento completado", flush=True)
    print("=" * 60, flush=True)
    
    return redirect(url_for('compuestos'))

@app.route('/compuestos/reformar_excel', methods=['POST'])
def compuestos_reformar_excel():
    """Convierte Excel de Compuestos de vuelta a JSON SIN aplicar validaciones"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('compuestos'))

    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('compuestos'))

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            nombre_base = os.path.splitext(filename)[0]
            
            filename = secure_filename(file.filename)
            nombre_base = os.path.splitext(filename)[0]
            
            print(f"📄 Excel recibido para conversión PURA: {filename}", flush=True)
            print(f"⏳ Leyendo Excel y reconstruyendo JSON (SIN VALIDACIONES)...", flush=True)
            file.seek(0)
            excel_data = pd.ExcelFile(file)
            
            # Leer todas las hojas dejando que pandas detecte los tipos automáticamente
            df_usuarios = pd.read_excel(excel_data, 'Usuarios') if 'Usuarios' in excel_data.sheet_names else pd.DataFrame()
            df_consultas = pd.read_excel(excel_data, 'Consultas') if 'Consultas' in excel_data.sheet_names else pd.DataFrame()
            df_procedimientos = pd.read_excel(excel_data, 'Procedimientos') if 'Procedimientos' in excel_data.sheet_names else pd.DataFrame()
            df_medicamentos = pd.read_excel(excel_data, 'Medicamentos') if 'Medicamentos' in excel_data.sheet_names else pd.DataFrame()
            df_otros_serv = pd.read_excel(excel_data, 'OtrosServicios') if 'OtrosServicios' in excel_data.sheet_names else pd.DataFrame()
            df_urgencias = pd.read_excel(excel_data, 'Urgencias') if 'Urgencias' in excel_data.sheet_names else pd.DataFrame()
            df_hospitalizacion = pd.read_excel(excel_data, 'Hospitalizacion') if 'Hospitalizacion' in excel_data.sheet_names else pd.DataFrame()
            df_recien_nacidos = pd.read_excel(excel_data, 'RecienNacidos') if 'RecienNacidos' in excel_data.sheet_names else pd.DataFrame()

            # Limpiar DataFrames de filas completamente vacías que Excel a veces agrega
            for df in [df_usuarios, df_consultas, df_procedimientos, df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos]:
                if not df.empty:
                    df.dropna(how='all', inplace=True)
            
            # Crear estructura JSON base
            if not df_usuarios.empty and 'numDocumentoIdObligado' in df_usuarios.columns:
                numDocumentoIdObligado = df_usuarios['numDocumentoIdObligado'].iloc[0]
            else:
                numDocumentoIdObligado = ''
            
            if not df_usuarios.empty and 'numFactura' in df_usuarios.columns:
                numFactura = df_usuarios['numFactura'].iloc[0]
            else:
                numFactura = ''
            
            data_original = {
                'numDocumentoIdObligado': str(numDocumentoIdObligado),
                'numFactura': str(numFactura),
                'tipoNota': None,
                'numNota': None
            }
            
            # Usar la función de reconstrucción de COMPUESTOS (que no valida)
            from modules.tabla_unica_compuestos import reconstruir_json_desde_dataframes, format_json_compact_arrays
            data_reformado = reconstruir_json_desde_dataframes(
                data_original, df_usuarios, df_consultas, df_procedimientos,
                df_medicamentos, df_otros_serv, df_urgencias, df_hospitalizacion, df_recien_nacidos
            )
            
            # Crear contenido JSON con formato compacto
            json_content = format_json_compact_arrays(data_reformado, indent=4)
            
            # Guardar JSON en el servidor para descarga posterior
            json_filename = f'desde_excel_{nombre_base}.json'
            json_path = os.path.join(app.config['OUTPUT_FOLDER'], json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            print(f"✅ JSON (puro) generado desde Excel: {json_filename}", flush=True)
            session.pop('compuestos_excel_reformado_file', None)
            session.pop('compuestos_json_file', None)
            session.pop('compuestos_reporte_file', None)

            # Guardar en sesión para mostrar el botón de descarga
            session['compuestos_json_from_excel_file'] = json_filename
            session['processed'] = True # Bandera para evitar limpieza en la redirección
            
            flash(f'JSON (sin validaciones) generado desde Excel: {json_filename}. Usa el nuevo botón para descargarlo.', 'success')
            return redirect(url_for('compuestos'))
            
        except Exception as e:
            return redirect(url_for('compuestos'))
            
        except Exception as e:
            print(f"❌ Error reformando Excel: {str(e)}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            flash(f'Error reformando el archivo: {str(e)}', 'error')
            return redirect(url_for('compuestos'))

@app.route('/compuestos/descargar_excel/<filename>')
def compuestos_descargar_excel(filename):
    """Descarga el archivo Excel ORIGINAL generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}.xlsx'
            )
        else:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('compuestos'))
    except Exception as e:
        flash(f'Error al descargar el archivo: {str(e)}', 'error')
        return redirect(url_for('compuestos'))

@app.route('/compuestos/descargar_excel_reformado/<filename>')
def compuestos_descargar_excel_reformado(filename):
    """Descarga el archivo Excel REFORMADO (con validaciones) generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_Reformado.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}_Reformado.xlsx'
            )
        else:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('compuestos'))
    except Exception as e:
        flash(f'Error al descargar el archivo: {str(e)}', 'error')
        return redirect(url_for('compuestos'))

@app.route('/compuestos/descargar_json/<filename>')
def compuestos_descargar_json(filename):
    """Descarga el archivo JSON reformado generado"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'_{filename}.json')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'_{filename}.json'
            )
        else:
            flash('El archivo JSON no está disponible', 'error')
            return redirect(url_for('compuestos'))
    except Exception as e:
        flash(f'Error descargando JSON: {str(e)}', 'error')
        return redirect(url_for('compuestos'))

@app.route('/compuestos/descargar_json_excel/<filename>')
def compuestos_descargar_json_excel(filename):
    """Descarga el archivo JSON generado desde Excel"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/json',
                as_attachment=True,
                download_name=filename
            )
        else:
            flash('El archivo JSON generado desde Excel no está disponible.', 'error')
            return redirect(url_for('compuestos'))
    except Exception as e:
        flash(f'Error descargando JSON desde Excel: {str(e)}', 'error')
        return redirect(url_for('compuestos'))

@app.route('/compuestos/descargar_reporte/<filename>')
def compuestos_descargar_reporte(filename):
    """Descarga el reporte Excel de diagnósticos vacíos"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_diagnosticos_vacios.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}_diagnosticos_vacios.xlsx'
            )
        else:
            flash('El reporte de diagnósticos vacíos no está disponible', 'error')
            return redirect(url_for('compuestos'))
    except Exception as e:
        flash(f'Error descargando reporte: {str(e)}', 'error')
        return redirect(url_for('compuestos'))

@app.route('/compuestos/descargar_reporte_cambios/<filename>')
def compuestos_descargar_reporte_cambios(filename):
    """Descarga el reporte de cambios (fechas y documentos)"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_reporte_cambios.xlsx')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{filename}_reporte_cambios.xlsx'
            )
        else:
            flash('El reporte de cambios no está disponible', 'error')
            return redirect(url_for('compuestos'))
    except Exception as e:
        flash(f'Error descargando reporte de cambios: {str(e)}', 'error')
        return redirect(url_for('compuestos'))


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

@app.route('/separador', methods=['GET', 'POST'])
@MemoryManager.cleanup_after_request
def separador():
    """Página del Separador JSON por codPrestador"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('separador'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('separador'))
        
        if file and file.filename.endswith('.json'):
            try:
                # Validar tamaño del archivo
                validate_file_size(file, max_size_mb=75)
                
                filename = secure_filename(file.filename)
                nombre_base = os.path.splitext(filename)[0]
                
                # Procesar el archivo y generar ZIP
                zip_buffer, resumen = separar_por_prestador(file)
                
                # Guardar el ZIP
                zip_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{nombre_base}_separado.zip')
                with open(zip_path, 'wb') as f:
                    f.write(zip_buffer.read())
                
                # Guardar información en sesión
                session['separador_file'] = nombre_base
                session['separador_resumen'] = resumen
                
                resource_monitor.log_resource_usage(f"Separador: {nombre_base}")
                
                flash(f'Archivo procesado exitosamente. Se generaron {resumen["total_prestadores"]} archivos JSON.', 'success')
                return redirect(url_for('separador'))
                
            except Exception as e:
                flash(f'Error procesando el archivo: {str(e)}', 'error')
                return redirect(url_for('separador'))
        else:
            flash('Tipo de archivo no permitido. Solo se aceptan archivos JSON.', 'error')
            return redirect(url_for('separador'))
    
    # GET request
    resumen = session.get('separador_resumen')
    return render_template('separador.html', resumen=resumen)

@app.route('/separador/descargar_zip/<filename>')
def separador_descargar_zip(filename):
    """Descarga el archivo ZIP con todos los JSON separados"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{filename}_separado.zip')
        if os.path.exists(filepath):
            return send_file(
                filepath,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'{filename}_separado.zip'
            )
        else:
            flash('El archivo ZIP no está disponible', 'error')
            return redirect(url_for('separador'))
    except Exception as e:
        flash(f'Error descargando ZIP: {str(e)}', 'error')
        return redirect(url_for('separador'))


# ============================================================================
# CONSOLIDADOR RIPS
# ============================================================================

@app.route('/consolidador')
def consolidador():
    """Página del Consolidador RIPS"""
    estadisticas = session.get('consolidador_estadisticas')
    archivo_resultado = session.get('consolidador_archivo')
    return render_template('consolidador.html', estadisticas=estadisticas, archivo_resultado=archivo_resultado)


@app.route('/consolidador/consolidar', methods=['POST'])
@MemoryManager.cleanup_after_request
def consolidador_consolidar():
    """Consolida múltiples archivos JSON RIPS en uno solo"""
    import zipfile
    from io import BytesIO as _BytesIO
    from modules.consolidador_rips import consolidar_multiples_json

    if 'files' not in request.files:
        flash('No se seleccionaron archivos', 'error')
        return redirect(url_for('consolidador'))

    files = request.files.getlist('files')
    valid_files = [f for f in files if f and f.filename != '' and f.filename.lower().endswith('.json')]

    if not valid_files:
        flash('No se seleccionaron archivos JSON válidos.', 'error')
        return redirect(url_for('consolidador'))

    if len(valid_files) < 2:
        flash('Se necesitan al menos 2 archivos JSON para consolidar.', 'error')
        return redirect(url_for('consolidador'))

    modo = request.form.get('modo', 'usuario')
    if modo not in ('usuario', 'prestador', 'ambos'):
        modo = 'usuario'

    try:
        archivos_contenido = []
        for file in valid_files:
            validate_file_size(file, max_size_mb=100)
            contenido = file.read()
            archivos_contenido.append((secure_filename(file.filename), contenido))

        resultado, estadisticas = consolidar_multiples_json(archivos_contenido, modo=modo)

        if isinstance(resultado, bytes):
            # Modo 'usuario': un único JSON
            output_filename = 'facturas_consolidadas.json'
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            with open(output_path, 'wb') as f:
                f.write(resultado)
        else:
            # Modos 'prestador' / 'ambos': ZIP con un JSON por prestador
            buf = _BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for cod_prestador, contenido_json in resultado.items():
                    zf.writestr(f'consolidado_{cod_prestador}.json', contenido_json)
            output_filename = 'facturas_consolidadas.zip'
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            with open(output_path, 'wb') as f:
                f.write(buf.getvalue())

        # Solo guardar resumen en sesión (la cookie tiene límite ~4KB).
        # 'detalle' puede tener miles de entradas y desborda la cookie silenciosamente.
        session['consolidador_archivo'] = output_filename
        session['consolidador_estadisticas'] = {
            'archivos_procesados': estadisticas['archivos_procesados'],
            'archivos_error': estadisticas['archivos_error'][:30],
            'total_usuarios': estadisticas['total_usuarios'],
            'total_servicios': estadisticas['total_servicios'],
            'detalle': estadisticas['detalle'][:100] if len(estadisticas['detalle']) <= 100 else [],
            'detalle_truncado': len(estadisticas['detalle']) > 100,
            'prestadores': estadisticas.get('prestadores', [])[:50],
            'modo': modo,
        }

        resource_monitor.log_resource_usage(f"Consolidador: {len(valid_files)} archivos, modo={modo}")

        errores = len(estadisticas.get('archivos_error', []))
        num_prestadores = len(estadisticas.get('prestadores', []))
        if errores > 0:
            flash(
                f'Consolidación completada con {estadisticas["archivos_procesados"]} archivos OK y {errores} con error. '
                f'Total: {estadisticas["total_usuarios"]} usuarios, {estadisticas["total_servicios"]} servicios.',
                'warning'
            )
        elif modo in ('prestador', 'ambos'):
            flash(
                f'Consolidación exitosa: {estadisticas["archivos_procesados"]} archivos → {num_prestadores} prestadores. '
                f'Total: {estadisticas["total_usuarios"]} usuarios, {estadisticas["total_servicios"]} servicios.',
                'success'
            )
        else:
            flash(
                f'Consolidación exitosa: {estadisticas["archivos_procesados"]} archivos procesados. '
                f'Total: {estadisticas["total_usuarios"]} usuarios únicos, {estadisticas["total_servicios"]} servicios.',
                'success'
            )

    except Exception as e:
        flash(f'Error en la consolidación: {str(e)}', 'error')

    return redirect(url_for('consolidador'))


@app.route('/consolidador/descargar')
def consolidador_descargar():
    """Descarga el archivo consolidado (JSON o ZIP según el modo usado)"""
    try:
        filename = session.get('consolidador_archivo', 'facturas_consolidadas.json')
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(filepath):
            mimetype = 'application/zip' if filename.endswith('.zip') else 'application/json'
            return send_file(
                filepath,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        else:
            flash('El archivo consolidado no está disponible.', 'error')
            return redirect(url_for('consolidador'))
    except Exception as e:
        flash(f'Error descargando el archivo: {str(e)}', 'error')
        return redirect(url_for('consolidador'))


# ============================================================================
# FAVICON
# ============================================================================

@app.route('/favicon.ico')
def favicon():
    """Sirve el favicon"""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


# ============================================================================
# CONVERSOR EXCEL → JSON (Módulo Independiente)
# ============================================================================

@app.route('/excel-to-json')
def excel_to_json():
    """Página del conversor Excel → JSON"""
    return render_template('excel_to_json.html')


@app.route('/excel-to-json/convert', methods=['POST'])
@MemoryManager.cleanup_after_request
def excel_to_json_convert():
    """Convierte Excel a JSON detectando automáticamente el tipo (PyP, BC o Compuestos)"""
    print("\n" + "=" * 60, flush=True)
    print("📊 CONVERSOR EXCEL → JSON", flush=True)
    print("=" * 60, flush=True)
    
    if 'file' not in request.files:
        print("❌ Error: No se recibió archivo", flush=True)
        return {'error': 'No se recibió ningún archivo'}, 400
    
    file = request.files['file']
    
    if file.filename == '':
        print("❌ Error: Nombre de archivo vacío", flush=True)
        return {'error': 'Nombre de archivo vacío'}, 400
    
    # Validar extensión
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        print(f"❌ Error: Extensión no válida - {file.filename}", flush=True)
        return {'error': 'Solo se permiten archivos .xlsx o .xls'}, 400
    
    try:
        # Validar tamaño del archivo
        validate_file_size(file, max_size_mb=50)
        
        filename = secure_filename(file.filename)
        filename_base = os.path.splitext(filename)[0]
        
        print(f"📄 Archivo recibido: {filename}", flush=True)
        
        # Convertir Excel a JSON
        from io import BytesIO
        excel_buffer = BytesIO(file.read())
        excel_buffer.seek(0)
        
        json_string, tipo_detectado = convert_excel_to_json(excel_buffer)
        
        print(f"✅ Conversión exitosa", flush=True)
        print(f"📊 Tipo detectado: {tipo_detectado}", flush=True)
        print(f"📦 Tamaño JSON: {len(json_string)} bytes", flush=True)
        
        # Crear BytesIO con el JSON
        json_buffer = BytesIO(json_string.encode('utf-8'))
        json_buffer.seek(0)
        
        # Nombre del archivo de salida
        download_filename = f"{filename_base}_{tipo_detectado}.json"
        
        print(f"⬇️  Descargando: {download_filename}", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()
        
        resource_monitor.log_resource_usage(f"Excel → JSON: {filename_base}")
        
        return send_file(
            json_buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        print(f"❌ Error al convertir: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return {'error': f'Error al convertir el archivo: {str(e)}'}, 500


# ============================================================================
# CONVERSOR JSON → EXCEL (Módulo Independiente - Visualización Pura)
# ============================================================================

@app.route('/json-to-excel')
def json_to_excel():
    """Página del conversor JSON → Excel"""
    response = make_response(render_template('json_to_excel.html'))
    # Deshabilitar caché para que siempre cargue la última versión
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/json-to-excel/convert', methods=['POST'])
@MemoryManager.cleanup_after_request
def json_to_excel_convert():
    """Convierte uno o varios JSON a Excel para visualización sin transformaciones"""
    print("\n" + "=" * 60, flush=True)
    print("📊 CONVERSOR JSON → EXCEL - VISUALIZACIÓN PURA", flush=True)
    print("=" * 60, flush=True)
    
    try:
        if 'files' not in request.files:
            print("❌ Error: No se recibieron archivos", flush=True)
            from flask import jsonify
            return jsonify({'error': 'No se recibieron archivos'}), 400
        
        files = request.files.getlist('files')
        
        if not files or all(f.filename == '' for f in files):
            print("❌ Error: Nombres de archivo vacíos", flush=True)
            from flask import jsonify
            return jsonify({'error': 'No se seleccionaron archivos válidos'}), 400
        
        # Validar extensión
        archivos_invalidos = [f.filename for f in files if not f.filename.lower().endswith('.json')]
        if archivos_invalidos:
            print(f"❌ Error: Archivos no JSON detectados: {archivos_invalidos}", flush=True)
            from flask import jsonify
            return jsonify({'error': f'Solo se permiten archivos .json. Archivos inválidos: {", ".join(archivos_invalidos)}'}), 400
        
        # Validar tamaño de cada archivo (hasta 600MB por archivo para este módulo)
        for file in files:
            validate_file_size(file, max_size_mb=600)
            file.seek(0)  # Resetear después de validar
        
        print(f"📄 Archivos recibidos: {len(files)}", flush=True)
        for f in files:
            print(f"   • {f.filename}", flush=True)
        
        # Preparar archivos para procesamiento
        from io import BytesIO
        archivos_json = []
        nombres_archivos = []
        
        for file in files:
            try:
                # Leer contenido del archivo
                contenido = file.read()
                
                # Validar que no esté vacío
                if not contenido or len(contenido) == 0:
                    print(f"   ⚠️  Advertencia: {file.filename} está vacío, se omitirá", flush=True)
                    continue
                
                # Asegurar que contenido sea bytes y obtener string para validación
                if isinstance(contenido, bytes):
                    contenido_bytes = contenido
                    try:
                        contenido_str = contenido.decode('utf-8')
                    except UnicodeDecodeError:
                        print(f"   ⚠️  Advertencia: {file.filename} no se pudo decodificar como UTF-8", flush=True)
                        continue
                else:
                    # Si es string, convertir a bytes
                    contenido_str = contenido
                    contenido_bytes = contenido.encode('utf-8')
                
                # Validar que sea JSON válido
                try:
                    json.loads(contenido_str)
                except json.JSONDecodeError as je:
                    print(f"   ⚠️  Advertencia: {file.filename} no es un JSON válido: {str(je)}", flush=True)
                    continue
                
                # Si es válido, crear BytesIO para procesamiento (con los bytes)
                json_stream = BytesIO(contenido_bytes)
                archivos_json.append(json_stream)
                nombres_archivos.append(secure_filename(file.filename))
                
            except Exception as e:
                print(f"   ⚠️  Advertencia: Error al leer {file.filename}: {str(e)}", flush=True)
                continue
        
        # Verificar que haya al menos un archivo válido
        if not archivos_json:
            print("❌ Error: No se encontraron archivos JSON válidos para procesar", flush=True)
            from flask import jsonify
            return jsonify({'error': 'No se encontraron archivos JSON válidos. Verifica que los archivos no estén vacíos y sean JSON válidos.'}), 400
        
        # Convertir JSON a Excel
        excel_output, tipo_detectado, estadisticas = convertir_json_a_excel(archivos_json, nombres_archivos)
        
        if not excel_output:
            # Determinar el mensaje de error según las estadísticas
            if estadisticas['archivos_procesados'] == 0:
                error_msg = 'No se pudo procesar ningún archivo. Verifica que los JSON sean válidos y tengan la estructura correcta.'
            else:
                error_msg = 'No se encontraron datos válidos en los archivos. Verifica que contengan información de usuarios y servicios.'
            
            print(f"❌ Error: {error_msg}", flush=True)
            from flask import jsonify
            return jsonify({'error': error_msg}), 500
        
        # Nombre del archivo de salida
        if len(files) == 1:
            filename_base = os.path.splitext(nombres_archivos[0])[0]
            download_filename = f"{filename_base}_vista.xlsx"
        else:
            download_filename = f"multiple_json_{tipo_detectado}_vista.xlsx"
        
        print(f"⬇️  Descargando: {download_filename}", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()
        
        resource_monitor.log_resource_usage(f"JSON → Excel: {len(files)} archivos")
        
        return send_file(
            excel_output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        print(f"❌ Error al convertir: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        # Asegurar que siempre devolvemos JSON válido
        from flask import jsonify
        return jsonify({'error': f'Error al convertir los archivos: {str(e)}'}), 500


# ============================================================================
# RUTAS - OCR HISTORIA CLÍNICA
# ============================================================================

@app.route('/ocr-hcl')
def ocr_hcl():
    """Muestra la página del módulo OCR Historia Clínica"""
    return render_template('ocr_hcl.html')


@app.route('/ocr-hcl/process', methods=['POST'])
@MemoryManager.cleanup_after_request
def ocr_hcl_process():
    """Procesa múltiples PDFs de historias clínicas y genera archivos TXT"""
    print("\n" + "=" * 60, flush=True)
    print("🔍 OCR HISTORIA CLÍNICA - PROCESAMIENTO", flush=True)
    print("=" * 60, flush=True)
    
    if 'pdf_files' not in request.files:
        print("❌ Error: No se recibieron archivos", flush=True)
        return {'error': 'No se recibieron archivos'}, 400
    
    files = request.files.getlist('pdf_files')
    
    if not files or all(f.filename == '' for f in files):
        print("❌ Error: Nombres de archivo vacíos", flush=True)
        return {'error': 'No se seleccionaron archivos válidos'}, 400
    
    # Validar que todos sean PDFs
    archivos_invalidos = [f.filename for f in files if not f.filename.lower().endswith('.pdf')]
    if archivos_invalidos:
        print(f"❌ Error: Archivos no PDF detectados: {archivos_invalidos}", flush=True)
        return {'error': f'Solo se permiten archivos PDF. Archivos inválidos: {", ".join(archivos_invalidos)}'}, 400
    
    try:
        # Validar tamaño de cada archivo
        for file in files:
            validate_file_size(file, max_size_mb=50)
            file.seek(0)  # Resetear después de validar
        
        print(f"📄 Archivos recibidos: {len(files)}", flush=True)
        for f in files:
            print(f"   • {f.filename}", flush=True)
        
        # Preparar archivos para procesamiento
        from io import BytesIO
        archivos_pdf = []
        for file in files:
            pdf_stream = BytesIO(file.read())
            archivos_pdf.append((pdf_stream, secure_filename(file.filename)))
        
        # Procesar PDFs
        resultados = procesar_multiples_pdfs(archivos_pdf)
        
        # Generar archivos TXT
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'ocr_hcl')
        archivos_generados = generar_archivos_txt(resultados, output_dir)
        
        if not archivos_generados:
            print("❌ Error: No se generaron archivos", flush=True)
            return {'error': 'No se pudieron generar archivos de texto. Verifica que los PDFs contengan texto extraíble.'}, 500
        
        # Crear ZIP con todos los archivos
        zip_filename = 'historias_clinicas.zip'
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for archivo in archivos_generados:
                arcname = os.path.basename(archivo)
                zipf.write(archivo, arcname)
                print(f"📦 Agregado al ZIP: {arcname}", flush=True)
        
        print(f"✅ ZIP generado: {zip_filename}", flush=True)
        print(f"📊 Total archivos en ZIP: {len(archivos_generados)}", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()
        
        resource_monitor.log_resource_usage(f"OCR procesado: {len(files)} archivos")
        
        # Enviar archivo ZIP
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    
    except Exception as e:
        print(f"❌ Error al procesar: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return {'error': f'Error al procesar los archivos: {str(e)}'}, 500


if __name__ == '__main__':
    # Configurar werkzeug para mostrar logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.INFO)
    
    # Agregar carpeta modules/ al vigilante de cambios
    extra_dirs = ['modules']
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                filename = os.path.join(dirname, filename)
                if os.path.isfile(filename):
                    extra_files.append(filename)
    
    print(f"📂 Vigilando {len(extra_files)} archivos en modules/")
    print("=" * 60)
    sys.stdout.flush()
    
    # Ejecutar Flask con extra_files para vigilar cambios en modules/
    app.run(host='0.0.0.0', port=5500, debug=True, use_reloader=True, extra_files=extra_files)
