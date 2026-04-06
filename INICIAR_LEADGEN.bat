@echo off
title Lead Gen Pro Elite - Instalador Inteligente
setlocal enabledelayedexpansion

:: Colores y Estética
color 0A
echo ==========================================================
echo          🚀 LEAD GEN PRO - ELITE COMMAND CENTER
echo ==========================================================
echo [ SISTEMA DE INTELIGENCIA COMERCIAL - INICIANDO... ]
echo.

:: 1. Verificar si existe Python
set PYTHON_CMD=none
python --version >nul 2>&1 && set PYTHON_CMD=python
if "%PYTHON_CMD%"=="none" py --version >nul 2>&1 && set PYTHON_CMD=py

if "%PYTHON_CMD%"=="none" (
    echo [!] Python no detectado. Iniciando instalacion automatica...
    echo [!] Por favor, espera mientras preparamos el entorno. No cierres esta ventana.
    
    :: Descargar instalador de Python oficial (version 3.10.11 estable)
    echo [*] Descargando motor Python...
    curl -o python_installer.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe --silent
    
    :: Instalacion Silenciosa con PATH activado
    echo [*] Instalando Python (este proceso es silencioso, tarda 1-2 minutos)...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    :: Limpieza
    del python_installer.exe
    echo [OK] Python instalado con exito.
    
    :: Recargar el entorno para que reconozca a Python recien instalado
    set PATH=%PATH%;C:\Program Files\Python310;C:\Program Files\Python310\Scripts
    set PYTHON_CMD=python
)

:: 2. Crear Entorno Virtual
if not exist "venv_windows" (
    echo [OK] Entorno Python Listo.
    echo [*] Configurando entorno de trabajo por primera vez...
    %PYTHON_CMD% -m venv venv_windows
    set FIRST_RUN=1
)

:: 3. Activar e Instalar Librerias
call venv_windows\Scripts\activate
if defined FIRST_RUN (
    echo [*] Instalando librerias necesarias (esto solo ocurre una vez)...
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    echo [*] Instalando motor de busqueda...
    playwright install chromium
)

:: 4. Lanzar Scraper
echo [🚀] ¡Todo listo! El panel se abrira en unos segundos...
echo [!] NO CIERRES ESTA VENTANA mientras uses el programa.
echo ----------------------------------------------------------
streamlit run app.py --server.port=8501 --server.headless=true --browser.gatherUsageStats=false --theme.base=dark

pause
