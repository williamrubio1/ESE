@echo off
echo ====================================
echo Sistema de Validacion de JSON
echo ====================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo Creando entorno virtual...
    python -m venv venv
    echo.
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar/actualizar dependencias
echo.
echo Instalando dependencias...
pip install -q -r requirements.txt

REM Ejecutar la aplicacion
echo.
echo ====================================
echo Iniciando servidor Flask...
echo La aplicacion estara disponible en:
echo http://localhost:5000
echo.
echo Presiona Ctrl+C para detener el servidor
echo ====================================
echo.

python app.py

pause
