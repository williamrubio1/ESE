@echo off
echo ====================================
echo LIMPIANDO CACHE DE PYTHON
echo ====================================
echo.

cd /d "%~dp0"

echo Eliminando archivos __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo Eliminando archivos .pyc...
del /s /q *.pyc 2>nul

echo.
echo ====================================
echo CACHE LIMPIADO EXITOSAMENTE
echo ====================================
echo.
pause

