@echo off
title Constructor de LeadGenPro Elite
echo ===============================================
echo   Preparando entorno para crear EXE...
echo ===============================================

:: Instalar dependencias necesarias
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

:: Instalar navegador para el entorno de compilacion
python -m playwright install chromium

echo.
echo ===============================================
echo   Creando ejecutable (esto puede tardar)...
echo ===============================================

:: Comando de PyInstaller optimizado
pyinstaller --noconfirm --onefile --windowed ^
    --add-data "app.py;." ^
    --add-data "geo_data.py;." ^
    --collect-all streamlit ^
    --collect-all playwright ^
    --name "LeadGenPro_Elite" ^
    lanzador_windows.py

echo.
echo ===============================================
echo   ¡HECHO! El archivo esta en la carpeta 'dist'
echo ===============================================
pause
