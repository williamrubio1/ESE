"""
Módulo de optimizaciones para servicios web Flask
Incluye: gestión de memoria, caché, límites de tráfico y limpieza automática
"""

import os
import time
import threading
from datetime import datetime, timedelta
from functools import wraps
import gc

# ============================================================================
# GESTIÓN DE MEMORIA
# ============================================================================

class MemoryManager:
    """Gestor de memoria para liberar recursos después de operaciones pesadas"""
    
    @staticmethod
    def cleanup_after_request(func):
        """Decorator para limpiar memoria después de cada request"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Forzar recolección de basura
                gc.collect()
        return wrapper
    
    @staticmethod
    def cleanup_dataframes(*dfs):
        """Libera memoria de DataFrames"""
        for df in dfs:
            if df is not None and hasattr(df, 'memory_usage'):
                del df
        gc.collect()
    
    @staticmethod
    def cleanup_buffers(*buffers):
        """Libera memoria de buffers BytesIO"""
        for buffer in buffers:
            if buffer is not None and hasattr(buffer, 'close'):
                try:
                    buffer.close()
                except:
                    pass
        gc.collect()


# ============================================================================
# GESTIÓN DE CACHÉ DE ARCHIVOS
# ============================================================================

class FileCache:
    """Caché simple con expiración por tiempo"""
    
    def __init__(self, ttl_seconds=300):  # 5 minutos por defecto
        self.cache = {}
        self.ttl = ttl_seconds
        self.lock = threading.Lock()
    
    def get(self, key):
        """Obtiene valor del caché si no ha expirado"""
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self.cache[key]
        return None
    
    def set(self, key, value):
        """Guarda valor en caché con timestamp"""
        with self.lock:
            self.cache[key] = (value, time.time())
    
    def clear(self):
        """Limpia todo el caché"""
        with self.lock:
            self.cache.clear()
            gc.collect()
    
    def cleanup_expired(self):
        """Elimina entradas expiradas"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if current_time - timestamp >= self.ttl
            ]
            for key in expired_keys:
                del self.cache[key]
            if expired_keys:
                gc.collect()


# Instancia global de caché
file_cache = FileCache(ttl_seconds=600)  # 10 minutos


# ============================================================================
# LIMPIEZA AUTOMÁTICA DE ARCHIVOS TEMPORALES
# ============================================================================

class OutputCleaner:
    """Limpia archivos antiguos en la carpeta outputs/"""
    
    def __init__(self, output_folder, max_age_hours=24):
        self.output_folder = output_folder
        self.max_age_seconds = max_age_hours * 3600
        self.last_cleanup = 0
        self.cleanup_interval = 3600  # Limpiar cada hora
    
    def should_cleanup(self):
        """Verifica si es hora de limpiar"""
        return time.time() - self.last_cleanup > self.cleanup_interval
    
    def cleanup_old_files(self):
        """Elimina archivos más antiguos que max_age_hours"""
        if not self.should_cleanup():
            return 0
        
        deleted_count = 0
        current_time = time.time()
        
        try:
            for filename in os.listdir(self.output_folder):
                filepath = os.path.join(self.output_folder, filename)
                
                # Solo archivos (no directorios)
                if not os.path.isfile(filepath):
                    continue
                
                # Verificar edad del archivo
                file_age = current_time - os.path.getmtime(filepath)
                
                if file_age > self.max_age_seconds:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception:
                        pass  # Ignorar errores al eliminar
            
            self.last_cleanup = current_time
            
            if deleted_count > 0:
                print(f"🧹 Limpieza automática: {deleted_count} archivos antiguos eliminados", flush=True)
                gc.collect()
            
            return deleted_count
            
        except Exception:
            return 0


# ============================================================================
# VALIDADORES DE TAMAÑO Y FORMATO
# ============================================================================

def validate_file_size(file, max_size_mb=50):
    """Valida que el archivo no exceda el tamaño máximo"""
    file.seek(0, 2)  # Ir al final
    size = file.tell()
    file.seek(0)  # Volver al inicio
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if size > max_size_bytes:
        raise ValueError(f'El archivo excede el tamaño máximo de {max_size_mb}MB')
    
    return size


def validate_json_structure(data, max_usuarios=10000):
    """Valida estructura JSON y límites razonables"""
    if not isinstance(data, dict):
        raise ValueError('JSON debe ser un diccionario')
    
    usuarios = data.get('usuarios', [])
    if not isinstance(usuarios, list):
        raise ValueError('usuarios debe ser una lista')
    
    if len(usuarios) > max_usuarios:
        raise ValueError(f'El archivo tiene demasiados usuarios (máximo {max_usuarios}). Procese en lotes.')
    
    return True


# ============================================================================
# RATE LIMITING SIMPLE
# ============================================================================

class RateLimiter:
    """Rate limiter simple basado en IP"""
    
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [timestamps]}
        self.lock = threading.Lock()
    
    def is_allowed(self, ip):
        """Verifica si la IP puede hacer otra request"""
        with self.lock:
            current_time = time.time()
            
            # Limpiar timestamps antiguos
            if ip in self.requests:
                self.requests[ip] = [
                    ts for ts in self.requests[ip]
                    if current_time - ts < self.window_seconds
                ]
            else:
                self.requests[ip] = []
            
            # Verificar límite
            if len(self.requests[ip]) >= self.max_requests:
                return False
            
            # Agregar nueva request
            self.requests[ip].append(current_time)
            return True
    
    def cleanup_old_entries(self):
        """Limpia entradas antiguas para liberar memoria"""
        with self.lock:
            current_time = time.time()
            to_delete = []
            
            for ip, timestamps in self.requests.items():
                # Si todos los timestamps son antiguos, eliminar entrada
                if all(current_time - ts >= self.window_seconds for ts in timestamps):
                    to_delete.append(ip)
            
            for ip in to_delete:
                del self.requests[ip]
            
            if to_delete:
                gc.collect()


# Instancia global de rate limiter
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)


# ============================================================================
# MONITOREO DE RECURSOS
# ============================================================================

class ResourceMonitor:
    """Monitor simple de uso de recursos"""
    
    @staticmethod
    def get_memory_usage():
        """Retorna uso de memoria en MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return None
    
    @staticmethod
    def log_resource_usage(operation_name):
        """Loguea uso de recursos después de una operación"""
        memory_mb = ResourceMonitor.get_memory_usage()
        if memory_mb:
            print(f"💾 Memoria después de '{operation_name}': {memory_mb:.2f} MB", flush=True)


# ============================================================================
# UTILIDADES DE SESIÓN
# ============================================================================

def cleanup_session_files(session, output_folder):
    """
    Limpia archivos asociados a una sesión
    
    Args:
        session: Objeto de sesión de Flask
        output_folder: Carpeta donde están los archivos
    """
    import os
    
    # Obtener nombre de archivo de la sesión
    filename = session.get('last_processed_file')
    if not filename:
        return
    
    # Lista de patrones de archivos a eliminar
    patterns = [
        f"{filename}.xlsx",
        f"{filename}_Reformado.xlsx",
        f"_{filename}.json",
        f"{filename}_reporte_cambios.xlsx",
        f"{filename}_diagnosticos_vacios.xlsx",
        f"{filename}_separado.zip"
    ]
    
    deleted_count = 0
    for pattern in patterns:
        filepath = os.path.join(output_folder, pattern)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                deleted_count += 1
            except Exception as e:
                print(f"⚠️  Error eliminando {filepath}: {e}")
    
    if deleted_count > 0:
        print(f"🗑️  Archivos de sesión eliminados: {deleted_count}")


# ============================================================================
# HELPERS DE COMPRESIÓN
# ============================================================================

def should_compress_response(response, min_size=1024):
    """
    Determina si una respuesta debe ser comprimida
    
    Args:
        response: Objeto de respuesta de Flask
        min_size: Tamaño mínimo en bytes para comprimir (default: 1KB)
    
    Returns:
        bool: True si debe comprimir, False si no
    """
    # Solo comprimir si la respuesta es suficientemente grande
    content_length = getattr(response, 'content_length', None)
    if content_length is None:
        return False
    
    return content_length >= min_size


