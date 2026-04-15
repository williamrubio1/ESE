"""
OCR-HCL (OCR Historia Clínica)
Módulo para extraer texto de historias clínicas en formato PDF.
Usa Tesseract OCR para detección de layout horizontal.
Genera archivos .txt con el contenido de cada HC, nombrados según el número de historia clínica.
"""

import os
import re
from io import BytesIO
from typing import List, Tuple, Dict
import fitz  # PyMuPDF - fallback

# Configurar rutas de Tesseract y Poppler para Windows
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"

# Agregar Poppler al PATH si existe
if os.path.exists(POPPLER_PATH):
    os.environ['PATH'] += f';{POPPLER_PATH}'

# Importar Tesseract OCR (opcional)
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image
    
    # Configurar ruta de Tesseract
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        TESSERACT_AVAILABLE = True
        print("✅ Tesseract OCR disponible - Usando detección de layout horizontal")
    else:
        TESSERACT_AVAILABLE = False
        print("⚠️  Tesseract ejecutable no encontrado. Usando PyMuPDF como fallback.")
except ImportError as e:
    TESSERACT_AVAILABLE = False
    print(f"⚠️  Error al importar Tesseract: {e}. Usando PyMuPDF como fallback.")


# Configuración del encabezado a eliminar
HEADER_PATTERNS = [
    r"E\.S\.E\.\s+DEPARTAMENTAL\s+DEL\s+META\s+['\"]SOLUCIÓN\s+SALUD['\"]",
    r"822006595\s*-\s*1",
    r"E\.S\.E\.\s+DEPARTAMENTAL",
    r"SOLUCIÓN\s+SALUD",
    r"RHsClxFo",
    r"Pag:\s*\d+\s+de\s+\d+",
    r"Fecha:\s*\d{2}/\d{2}/\d{2,4}",
    r"G\.etareo:\s*\d+",
    r"\*\d{10,}",  # Números con asterisco (ej: *1016747642)
    r"^\*\s*\d+$",  # Solo asterisco y números
    r"^de\s+\d+$",  # "de 9" (parte del número de página)
    r"Empresa\s+[Ss]oci[ao][Ll]?\s+[adeo]+\s+[Ee]ste[dg][eo]\s+Getareo:\s*_?\s*\d+",  # Ruido de encabezado (flexibilidad en OCR)
]

# Patrones para el pie de página (footer)
FOOTER_PATTERNS = [
    r"7J\.0\s*\*HOSVITAL\*",
    r"Usuario:\s*\d+",
    r"^\d{8,}$",  # Números largos solos (ID de usuario)
]

# Patrones de ruido de firmas (OCR mal interpretado)
FIRMA_RUIDO_PATTERNS = [
    r'["\'][\(\?]?[WwNnEe0-9\s]*[Ff]?[ero]*[Yy]?[Aa]?[,;]?["\']',  # Comillas con caracteres raros
    r'[/¿]+\s*[—\-]+\s*\d*',  # Símbolos con guiones: "/¿/ — 7"
    r'^\s*["\'\(\)][^a-zA-Z]{0,20}[,;]?["\'\)]?\s*$',  # Líneas con comillas y símbolos sin letras reales
    r'^\s*["\']\([^\)]{0,15}\s*[Ff][a-z]*[,;]?["\']?\s*$',  # Patrones específicos como "(?W FrerYa,"
    r'^\s*[/¿\(\)\{\}\[\]—\-]{2,}\s*\d*\s*$',  # Solo símbolos raros
]

# Patrón para extraer el número de historia clínica con nombre completo
# El identificador puede estar en cualquier parte del texto, no necesariamente después de "HISTORIA CLÍNICA No."
# Ejemplo: "RC 1016747642 -- JOHAN SANTIAGO GONZALEZ REYES" (puede tener múltiples espacios)
# Tipos de documento: RC, CC, TI, CN, PT, CE, etc.
HC_IDENTIFIER_PATTERN = r"\b([A-Z]{2})\s+(\d{6,15})\s+--\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?)(?=\n|$|\s{3,})"

# Campos a eliminar del inicio del documento
CAMPOS_ENCABEZADO = [
    "Empresa:",
    "Afiliado:",
    "Fecha Nacimiento:",
    "Edad actual",
    "Sexo:",
    "Grupo Sanguíneo:",
    "Estado Civil",
    "Teléfono:",
    "Dirección:",
    "Barrio:",
    "Municipio:",
    "Departamento:",
    "Etnia:",
    "Grupo Étnico:",
    "Nivel Educativo:",
    "Discapacidad:",
    "Grupo Poblacional:",
    "Atención Especial:",
    "Ocupacion:",
    "Responsable:",
    "Parentesco:",
    "G.etareo:",
    "Usuario:",
    "7J.0 *HOSVITAL*"
]


def limpiar_encabezado(texto: str) -> str:
    """
    Elimina el encabezado repetitivo de E.S.E. DEPARTAMENTAL DEL META,
    la información estructurada inicial (datos del paciente),
    el ruido de la esquina superior derecha (RHsClxFo, Pag, Fecha, G.etareo, *números)
    y el pie de página (7J.0 *HOSVITAL*, Usuario).
    
    Args:
        texto: Texto extraído del PDF
    
    Returns:
        Texto sin el encabezado repetitivo, sin datos estructurados iniciales,
        sin ruido de esquina superior derecha y sin pie de página
    """
    lineas = texto.split('\n')
    lineas_limpias = []
    
    # Flag para saber cuándo empezar a incluir líneas
    encontro_fin_encabezado = False
    lineas_vacias_consecutivas = 0
    
    for linea in lineas:
        linea_limpia = linea.strip()
        
        # Omitir líneas vacías al inicio
        if not linea_limpia:
            lineas_vacias_consecutivas += 1
            # Después de encontrar el fin del encabezado, mantener líneas vacías
            if encontro_fin_encabezado:
                lineas_limpias.append('')
            continue
        else:
            lineas_vacias_consecutivas = 0
        
        # Verificar patrones de header (esquina superior derecha) - en toda la página
        es_header_ruido = False
        for patron in HEADER_PATTERNS:
            if re.search(patron, linea, re.IGNORECASE):
                es_header_ruido = True
                break
        
        if es_header_ruido:
            continue
        
        # Verificar patrones de footer (pie de página) - en toda la página
        es_footer_ruido = False
        for patron in FOOTER_PATTERNS:
            if re.search(patron, linea, re.IGNORECASE):
                es_footer_ruido = True
                break
        
        if es_footer_ruido:
            continue
        
        # Verificar patrones de ruido de firmas (OCR mal interpretado)
        es_firma_ruido = False
        for patron in FIRMA_RUIDO_PATTERNS:
            if re.search(patron, linea, re.IGNORECASE):
                es_firma_ruido = True
                break
        
        if es_firma_ruido:
            continue
        
        # Eliminar líneas que solo contienen ruido de número de página o códigos
        # Ejemplos: "e * 1016747642", "1", "2", "Pag: 1"
        if re.match(r'^[a-z]?\s*[★\*]\s*\d{8,}$', linea_limpia, re.IGNORECASE):
            continue
        
        # Si la línea contiene "HISTORIA CLÍNICA No.", omitirla
        if re.search(r"HISTORIA\s+CLÍNICA\s+No\.", linea, re.IGNORECASE):
            continue
        
        # Si la línea contiene alguno de los campos estructurados, omitirla
        es_campo_estructurado = False
        for campo in CAMPOS_ENCABEZADO:
            if campo in linea:
                es_campo_estructurado = True
                break
        
        if es_campo_estructurado:
            continue
        
        # Si la línea contiene solo números de página o códigos, omitirla
        if re.match(r'^(Pag:|de\s+\d+|Fecha:|RHsClxFo|\d{1,2}|[★\*]\d+)$', linea_limpia, re.IGNORECASE):
            continue
        
        # Si llegamos aquí y la línea tiene contenido sustancial, marcar fin de encabezado
        if len(linea_limpia) > 20 and not encontro_fin_encabezado:
            encontro_fin_encabezado = True
        
        # Solo agregar líneas después de encontrar el fin del encabezado
        if encontro_fin_encabezado:
            lineas_limpias.append(linea)
    
    return '\n'.join(lineas_limpias)


def extraer_numero_hc(texto: str) -> str:
    """
    Extrae el identificador completo de historia clínica del texto.
    Formato esperado: "RC 10167_____ -- J____ S_______ G_______ R____"
    
    El identificador puede estar en cualquier parte del documento,
    típicamente aparece después de "HISTORIA CLÍNICA No." pero en líneas separadas.
    
    Args:
        texto: Texto extraído del PDF
    
    Returns:
        Identificador completo de HC o "HC_DESCONOCIDA" si no se encuentra
    """
    # Estrategia 1: Buscar el identificador completo (tipo + número + -- + nombre)
    # Este patrón captura: "RC 1016747642 -- JOHAN SANTIAGO GONZALEZ REYES"
    match = re.search(HC_IDENTIFIER_PATTERN, texto, re.MULTILINE)
    if match:
        tipo_doc = match.group(1).strip()  # RC, CC, TI, etc.
        num_doc = match.group(2).strip()   # 1016747642
        nombre = match.group(3).strip()     # JOHAN SANTIAGO GONZALEZ REYES
        
        # Limpiar el nombre (remover saltos de línea y espacios múltiples)
        nombre = re.sub(r'\s+', ' ', nombre)
        nombre = nombre.replace('\n', ' ').replace('\r', ' ').strip()
        
        identificador = f"{tipo_doc} {num_doc} -- {nombre}"
        print(f"   ✅ Identificador encontrado: {identificador}")
        return identificador
    
    # Estrategia 2: Buscar solo tipo y número (sin nombre)
    match_simple = re.search(r"\b([A-Z]{2})\s+(\d{6,15})\b", texto)
    if match_simple:
        tipo_doc = match_simple.group(1).strip()
        num_doc = match_simple.group(2).strip()
        identificador = f"{tipo_doc} {num_doc}"
        print(f"   ⚠️  Solo se encontró identificador parcial: {identificador}")
        return identificador
    
    print("   ❌ No se encontró identificador de HC en el texto")
    return "HC_DESCONOCIDA"


def extraer_texto_pdf_tesseract(pdf_stream: BytesIO, filename: str) -> str:
    """
    Extrae texto de un PDF usando Tesseract OCR con detección de layout.
    Convierte cada página a imagen y aplica OCR respetando la estructura horizontal.
    
    Args:
        pdf_stream: Stream del archivo PDF
        filename: Nombre del archivo (para logs)
    
    Returns:
        Texto extraído del PDF
    """
    try:
        print(f"   🔍 Usando Tesseract OCR (detección de layout horizontal)")
        
        pdf_stream.seek(0)
        
        # Convertir PDF a imágenes (300 DPI para buena calidad)
        imagenes = convert_from_bytes(pdf_stream.read(), dpi=300)
        
        print(f"   📊 Total de páginas: {len(imagenes)}")
        
        texto_completo = []
        
        for i, imagen in enumerate(imagenes, 1):
            print(f"   📄 Procesando página {i}/{len(imagenes)}...")
            
            # Configuración de Tesseract:
            # --psm 6: Bloque uniforme de texto (mejor para documentos estructurados)
            # --oem 3: Motor LSTM (mejor precisión)
            config_tesseract = '--psm 6 --oem 3'
            
            # Extraer texto con OCR en español
            texto_pagina = pytesseract.image_to_string(
                imagen,
                lang='spa',  # Español
                config=config_tesseract
            )
            
            if texto_pagina.strip():
                texto_completo.append(texto_pagina)
            else:
                print(f"      ⚠️  Página {i} sin texto extraíble")
        
        resultado = '\n\n'.join(texto_completo)
        print(f"   ✅ OCR completado: {len(resultado)} caracteres")
        
        return resultado
    
    except Exception as e:
        print(f"   ❌ Error con Tesseract OCR: {str(e)}")
        return ""


def extraer_texto_pdf_pymupdf(pdf_stream: BytesIO) -> str:
    """
    Extrae texto de un PDF usando PyMuPDF (fitz).
    Método fallback más rápido pero menos preciso para layouts horizontales.
    
    Args:
        pdf_stream: Stream del archivo PDF
    
    Returns:
        Texto extraído del PDF
    """
    try:
        print(f"   📖 Usando PyMuPDF (fallback)")
        pdf_stream.seek(0)
        doc = fitz.open(stream=pdf_stream.read(), filetype="pdf")
        texto_completo = []
        
        for pagina_num in range(len(doc)):
            pagina = doc[pagina_num]
            texto = pagina.get_text("text")
            texto_completo.append(texto)
        
        doc.close()
        return '\n'.join(texto_completo)
    
    except Exception as e:
        print(f"   ❌ Error con PyMuPDF: {str(e)}")
        return ""


def procesar_pdf_hc(pdf_stream: BytesIO, nombre_archivo: str) -> Tuple[str, str, str]:
    """
    Procesa un PDF de historia clínica y extrae su contenido.
    
    Args:
        pdf_stream: Stream del archivo PDF
        nombre_archivo: Nombre del archivo original
    
    Returns:
        Tupla (numero_hc, texto_limpio, nombre_archivo_original)
    """
    print(f"\n📄 Procesando: {nombre_archivo}")
    
    # Intentar con Tesseract OCR primero (mejor para layouts horizontales)
    texto = ""
    if TESSERACT_AVAILABLE:
        texto = extraer_texto_pdf_tesseract(pdf_stream, nombre_archivo)
    
    # Si Tesseract no está disponible o falla, usar PyMuPDF
    if not texto:
        if not TESSERACT_AVAILABLE:
            print("   ⚠️  Tesseract no disponible, usando PyMuPDF...")
        else:
            print("   ⚠️  Tesseract falló, intentando con PyMuPDF...")
        texto = extraer_texto_pdf_pymupdf(pdf_stream)
    
    if not texto:
        print("   ❌ No se pudo extraer texto del PDF")
        return "ERROR", "", nombre_archivo
    
    print(f"   ✓ Texto extraído: {len(texto)} caracteres")
    
    # Extraer número de HC
    numero_hc = extraer_numero_hc(texto)
    print(f"   ✓ Identificador HC: {numero_hc}")
    
    # Limpiar encabezados
    texto_limpio = limpiar_encabezado(texto)
    print(f"   ✓ Texto limpio: {len(texto_limpio)} caracteres")
    
    return numero_hc, texto_limpio, nombre_archivo


def procesar_multiples_pdfs(archivos_pdf: List[Tuple[BytesIO, str]]) -> List[Dict]:
    """
    Procesa múltiples PDFs de historias clínicas.
    
    Args:
        archivos_pdf: Lista de tuplas (pdf_stream, nombre_archivo)
    
    Returns:
        Lista de diccionarios con los resultados:
        {
            'numero_hc': str,
            'texto': str,
            'nombre_archivo_original': str,
            'nombre_archivo_salida': str,
            'exitoso': bool,
            'error': str (opcional)
        }
    """
    print("\n" + "=" * 60)
    print("📊 PROCESAMIENTO DE HISTORIAS CLÍNICAS (OCR-HCL)")
    print("=" * 60)
    print(f"📁 Total de archivos: {len(archivos_pdf)}")
    
    resultados = []
    
    for pdf_stream, nombre_archivo in archivos_pdf:
        try:
            numero_hc, texto_limpio, nombre_original = procesar_pdf_hc(pdf_stream, nombre_archivo)
            
            if numero_hc == "ERROR":
                resultados.append({
                    'numero_hc': numero_hc,
                    'texto': '',
                    'nombre_archivo_original': nombre_original,
                    'nombre_archivo_salida': '',
                    'exitoso': False,
                    'error': 'No se pudo extraer texto del PDF'
                })
            else:
                nombre_salida = f"{numero_hc}.txt"
                resultados.append({
                    'numero_hc': numero_hc,
                    'texto': texto_limpio,
                    'nombre_archivo_original': nombre_original,
                    'nombre_archivo_salida': nombre_salida,
                    'exitoso': True
                })
        
        except Exception as e:
            print(f"\n❌ Error procesando {nombre_archivo}: {str(e)}")
            resultados.append({
                'numero_hc': 'ERROR',
                'texto': '',
                'nombre_archivo_original': nombre_archivo,
                'nombre_archivo_salida': '',
                'exitoso': False,
                'error': str(e)
            })
    
    # Resumen
    exitosos = sum(1 for r in resultados if r['exitoso'])
    fallidos = len(resultados) - exitosos
    
    print("\n" + "=" * 60)
    print("📦 RESUMEN DE PROCESAMIENTO")
    print("=" * 60)
    print(f"✅ Exitosos: {exitosos}")
    print(f"❌ Fallidos: {fallidos}")
    print("=" * 60 + "\n")
    
    return resultados


def generar_archivos_txt(resultados: List[Dict], directorio_salida: str) -> List[str]:
    """
    Genera archivos .txt a partir de los resultados del procesamiento.
    
    Args:
        resultados: Lista de diccionarios con los resultados del procesamiento
        directorio_salida: Directorio donde guardar los archivos .txt
    
    Returns:
        Lista de rutas de archivos generados
    """
    os.makedirs(directorio_salida, exist_ok=True)
    archivos_generados = []
    
    for resultado in resultados:
        if resultado['exitoso']:
            ruta_archivo = os.path.join(directorio_salida, resultado['nombre_archivo_salida'])
            
            try:
                with open(ruta_archivo, 'w', encoding='utf-8') as f:
                    f.write(resultado['texto'])
                
                archivos_generados.append(ruta_archivo)
                print(f"✓ Generado: {resultado['nombre_archivo_salida']}")
            
            except Exception as e:
                print(f"❌ Error generando {resultado['nombre_archivo_salida']}: {str(e)}")
    
    return archivos_generados
