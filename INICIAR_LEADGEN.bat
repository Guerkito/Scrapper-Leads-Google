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

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ERROR: Python no esta instalado.
    echo [!] Por favor, ve a https://www.python.org y descarga "Python 3.10" o superior.
    echo [!] Asegurate de marcar la casilla "Add Python to PATH" al instalar.
    pause
    exit
)

:: 2. Crear Entorno Virtual
if not exist "venv_windows" (
    echo [!] Configurando entorno de trabajo por primera vez...
    python -m venv venv_windows
    set FIRST_RUN=1
)

:: 3. Activar e Instalar
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
