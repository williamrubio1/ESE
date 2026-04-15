from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from core import procesador
import logging
import socket
from urllib.request import urlopen

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medicamentos-flask-2026'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['LOG_FOLDER'] = 'logs'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Crear carpetas necesarias
for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['LOG_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Configurar logging
def setup_logging():
    log_file = os.path.join(app.config['LOG_FOLDER'], f'modificaciones_{datetime.now().strftime("%Y%m%d")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()

@app.errorhandler(413)
def archivo_demasiado_grande(e):
    return jsonify({'error': 'El archivo supera el tamaño máximo permitido (100 MB)'}), 413

def obtener_ip_publica():
    """Obtiene la IP pública desde un servicio externo con timeout corto."""
    servicios = [
        'https://api.ipify.org',
        'https://ifconfig.me/ip'
    ]

    for servicio in servicios:
        try:
            with urlopen(servicio, timeout=3) as respuesta:
                return respuesta.read().decode('utf-8').strip()
        except Exception:
            continue

    return None

def mostrar_urls_servidor(puerto):
    """Imprime en consola las rutas de acceso local, de red e IP pública."""
    try:
        hostname = socket.gethostname()
        ip_local = socket.gethostbyname(hostname)
    except Exception:
        ip_local = '127.0.0.1'

    ip_publica = obtener_ip_publica()

    print('\n=== Servidor Flask iniciado ===')
    print(f'Local:    http://127.0.0.1:{puerto}')
    print(f'Red:      http://{ip_local}:{puerto}')
    if ip_publica:
        print(f'Publica:  http://{ip_publica}:{puerto}')
    else:
        print('Publica:  No disponible (sin internet o servicio no accesible)')
    print('================================\n')

@app.route('/')
def index():
    """Renderiza la interfaz principal de selección de módulo"""
    return render_template('home.html')

@app.route('/modulo/carga')
def modulo_carga():
    """Renderiza el módulo de sustitución normal"""
    return render_template('index.html',
                           modo='carga',
                           titulo_modulo='Módulo de carga',
                           descripcion_modulo='Sustituye finalidades y procesa medicamentos')

@app.route('/modulo/inverso')
def modulo_inverso():
    """Renderiza el módulo de reversión de finalidades"""
    return render_template('index.html',
                           modo='inverso',
                           titulo_modulo='Módulo inverso',
                           descripcion_modulo='Revierte finalidades sustituidas de vuelta a 11')

@app.route('/procesar', methods=['POST'])
def procesar_archivo():
    """Compatibilidad con flujo anterior: procesa en modo carga"""
    return ejecutar_procesamiento('carga')

@app.route('/procesar/<modo>', methods=['POST'])
def procesar_archivo_por_modo(modo):
    """Procesa el archivo JSON según el módulo solicitado"""
    return ejecutar_procesamiento(modo)

def ejecutar_procesamiento(modo):
    """Procesa el archivo JSON cargado"""
    if modo not in ['carga', 'inverso']:
        return jsonify({'error': 'Modo de procesamiento no válido'}), 400

    if 'archivo' not in request.files:
        return jsonify({'error': 'No se proporcionó ningún archivo'}), 400
    
    archivo = request.files['archivo']
    
    if archivo.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    if not archivo.filename.endswith('.json'):
        return jsonify({'error': 'El archivo debe ser un JSON'}), 400
    
    try:
        # Guardar archivo temporal
        filename = secure_filename(archivo.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        archivo.save(upload_path)
        
        logging.info(f"Archivo cargado: {filename}")
        
        # Cargar cum.json (solo se requiere para el modo carga)
        cum_dict = []
        if modo == 'carga':
            if os.path.exists('cum.json'):
                with open('cum.json', 'r', encoding='utf-8') as f:
                    cum_dict = json.load(f)
            else:
                return jsonify({'error': 'No se encontró el archivo cum.json'}), 500
        
        # Cargar el archivo JSON del usuario
        with open(upload_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Procesar el archivo
        stats = {
            'medicamentos_encontrados': 0,
            'unidades_sustituidas': 0,
            'codigos_sustituidos': 0,
            'no_encontrados': 0,
            'medicamentos_nuevos_en_cum': 0,
            'procedimientos_modificados': 0,
            'medicamentos_nuevos_en_cum_detalle': [],
            'no_encontrados_detalle': [],
            'procedimientos_modificados_detalle': []
        }
        
        cum_modificado = [False]
        if modo == 'carga':
            procesador.recorrer_datos(data, cum_dict, cum_modificado, stats)
        
        # Guardar archivo procesado
        output_filename = f"_{filename}"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json_str = json.dumps(data, ensure_ascii=False, indent=4)
            # Aplicar transformaciones para formato compacto en arrays
            import re
            json_str = re.sub(r'\[\s+\{', '[{', json_str)
            json_str = re.sub(r'\},\s+\{', '}, {', json_str)
            f.write(json_str)
        
        # Guardar cum.json si fue modificado (solo modo carga)
        if modo == 'carga' and cum_modificado[0]:
            with open('cum.json', 'w', encoding='utf-8') as f:
                json.dump(cum_dict, f, ensure_ascii=False, indent=0)
            logging.info(f"cum.json actualizado con {len(cum_dict)} registros")
        
        # Registrar estadísticas en el log
        logging.info(f"Procesamiento ({modo}) completado - Archivo: {filename}")
        logging.info(f"  - Medicamentos encontrados: {stats['medicamentos_encontrados']}")
        logging.info(f"  - Unidades sustituidas: {stats['unidades_sustituidas']}")
        logging.info(f"  - Códigos sustituidos: {stats['codigos_sustituidos']}")
        logging.info(f"  - Medicamentos no encontrados: {stats['no_encontrados']}")
        logging.info(f"  - Medicamentos nuevos en cum.json: {stats['medicamentos_nuevos_en_cum']}")
        logging.info(f"  - Procedimientos modificados: {stats['procedimientos_modificados']}")
        
        # Limpiar archivo temporal
        os.remove(upload_path)
        
        return jsonify({
            'success': True,
            'filename': output_filename,
            'modo': modo,
            'stats': stats
        })
    
    except json.JSONDecodeError:
        logging.error(f"Error: El archivo no es un JSON válido - {archivo.filename}")
        return jsonify({'error': 'El archivo no es un JSON válido'}), 400
    except Exception as e:
        logging.error(f"Error procesando archivo: {str(e)}")
        return jsonify({'error': f'Error procesando el archivo: {str(e)}'}), 500

@app.route('/descargar/<filename>')
def descargar_archivo(filename):
    """Permite descargar el archivo procesado"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            logging.info(f"Descargando archivo: {filename}")
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'Archivo no encontrado'}), 404
    except Exception as e:
        logging.error(f"Error descargando archivo: {str(e)}")
        return jsonify({'error': f'Error descargando el archivo: {str(e)}'}), 500

@app.route('/logs')
def ver_logs():
    """Obtiene el contenido del log actual"""
    try:
        log_file = os.path.join(app.config['LOG_FOLDER'], f'modificaciones_{datetime.now().strftime("%Y%m%d")}.log')
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
                # Devolver las últimas 50 líneas
                return jsonify({'logs': logs[-50:]})
        else:
            return jsonify({'logs': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    mostrar_urls_servidor(5100)
    app.run(debug=True, port=5100, host='0.0.0.0')
