@echo off
title Lead Gen Pro Elite - Lanzador Maestro
setlocal enabledelayedexpansion

:: Colores y Estética
color 0A
echo ==========================================================
echo          🚀 LEAD GEN PRO - ELITE COMMAND CENTER
echo ==========================================================
echo [ SISTEMA DE INTELIGENCIA COMERCIAL - INICIANDO... ]
echo.

:: 0. Verificar archivos necesarios
if not exist "app.py" (
    color 0C
    echo [ERROR] No se encuentra 'app.py'. 
    echo Asegurate de extraer TODOS los archivos del ZIP antes de abrir este archivo.
    pause
    exit
)

:: 1. Verificar Python
set PYTHON_CMD=none
python --version >nul 2>&1 && set PYTHON_CMD=python
if "%PYTHON_CMD%"=="none" py --version >nul 2>&1 && set PYTHON_CMD=py

if "%PYTHON_CMD%"=="none" (
    echo [!] Python no detectado. Iniciando instalacion automatica...
    echo [!] Esto tardara unos minutos. No cierres esta ventana.
    
    echo [*] Descargando motor Python...
    curl -o python_installer.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe --silent
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] No se pudo descargar Python. Revisa tu conexion a internet.
        pause
        exit
    )
    
    echo [*] Instalando Python (proceso silencioso)...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    
    :: Forzar deteccion tras instalacion
    set PYTHON_CMD=python
    echo [OK] Python instalado.
)

:: 2. Crear Entorno Virtual
if not exist "venv_windows" (
    echo [*] Creando entorno de trabajo (esto solo ocurre una vez)...
    "%PYTHON_CMD%" -m venv venv_windows
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit
    )
    set FIRST_RUN=1
)

:: 3. Activar e Instalar
echo [*] Preparando librerias...
call venv_windows\Scripts\activate
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] No se pudo activar el entorno virtual.
    pause
    exit
)

if defined FIRST_RUN (
    echo [*] Instalando dependencias necesarias...
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] Error al instalar las librerias. Revisa tu internet.
        pause
        exit
    )
    echo [*] Instalando motor de busqueda...
    playwright install chromium
)

:: 4. Lanzar Scraper
echo [🚀] ¡Todo listo! Abriendo panel...
echo ----------------------------------------------------------
streamlit run app.py --server.port=8501 --server.headless=true --browser.gatherUsageStats=false --theme.base=dark

if %errorlevel% neq 0 (
    echo.
    color 0C
    echo [!] El programa se detuvo inesperadamente. Revisa los mensajes de arriba.
    pause
)
