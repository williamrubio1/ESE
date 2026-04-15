# Procesador de RIPS - Flask

Sistema web para el procesamiento de archivos JSON de RIPS (Registro Individual de Prestación de Servicios de Salud).

## Características

- **Carga de archivos**: Permite cargar archivos JSON arrastrándolos o seleccionándolos desde el explorador
- **Procesamiento automático**: Procesa medicamentos y procedimientos según reglas predefinidas
- **Estadísticas en tiempo real**: Muestra estadísticas detalladas del procesamiento
- **Descarga de resultados**: Permite descargar los archivos procesados
- **Registro de log**: Mantiene un registro detallado de todas las modificaciones realizadas
- **Interfaz sobria y sencilla**: Diseño moderno y fácil de usar

## Requisitos

- Python 3.8 o superior
- Flask 3.0.0
- Archivo `cum.json` en la raíz del proyecto

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

2. Asegurarse de que el archivo `cum.json` existe en la raíz del proyecto

## Ejecución

Para iniciar el servidor en modo debug en el puerto 5100:

```bash
python app.py
```

Luego abrir el navegador en: `http://localhost:5100`

## Estructura del proyecto

```
MedicamentosFlask/
├── app.py                  # Aplicación Flask principal (ejecutar este archivo)
├── cum.json               # Base de datos de medicamentos
├── requirements.txt       # Dependencias de Python
├── core/                  # Módulos de procesamiento
│   ├── __init__.py
│   └── procesador.py      # Lógica de procesamiento
├── templates/
│   └── index.html         # Interfaz web
├── static/
│   ├── css/
│   │   └── style.css      # Estilos
│   └── js/
│       └── main.js        # JavaScript
├── logs/                  # Registros de modificaciones
├── uploads/               # Archivos temporales
├── output/                # Archivos procesados
└── input/                 # Archivos de entrada (opcional)
```

## Uso

1. Abrir la aplicación en el navegador
2. Arrastrar un archivo JSON de RIPS o hacer clic en "Buscar archivo en el PC"
3. Hacer clic en "Procesar archivo"
4. Revisar las estadísticas de procesamiento
5. Descargar el archivo procesado

## Registro de modificaciones

El sistema mantiene un log diario de todas las operaciones realizadas en la carpeta `logs/`.
Se puede acceder al registro desde la interfaz web haciendo clic en "Ver registro de modificaciones".

## Puerto y configuración

- **Puerto**: 5100
- **Modo debug**: Activado
- **Host**: 0.0.0.0 (accesible desde cualquier interfaz de red)

---

© 2026 Procesador de RIPS - Sistema de gestión de medicamentos
