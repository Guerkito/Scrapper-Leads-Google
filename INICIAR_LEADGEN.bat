@echo off
title Lead Gen Pro Elite - Lanzador
setlocal enabledelayedexpansion

:: Colores y Estética
color 0A
echo ==========================================================
echo          🚀 LEAD GEN PRO - ELITE COMMAND CENTER
echo ==========================================================
echo [ SISTEMA DE INTELIGENCIA COMERCIAL - INICIANDO... ]
echo.

:: 1. Verificar Python (Busqueda exhaustiva)
set PYTHON_CMD=none
for %%p in (python.exe py.exe python3.exe) do (
    where %%p >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON_CMD=%%p
        goto :python_found
    )
)

:python_not_found
echo [!] ERROR: No se detecto Python en tu sistema.
echo [!] Por favor, instala Python 3.10 o superior desde:
echo     https://www.python.org/downloads/
echo [!] RECUERDA: Marcar la casilla "Add Python to PATH".
echo.
pause
exit

:python_found
echo [OK] Motor Python detectado.

:: 2. Crear/Activar Entorno Virtual
if not exist "venv_windows" (
    echo [*] Configurando entorno por primera vez...
    %PYTHON_CMD% -m venv venv_windows
)

echo [*] Preparando motores de busqueda...
call venv_windows\Scripts\activate

:: 3. Instalar dependencias solo si faltan
if not exist "venv_windows\installed.txt" (
    echo [*] Instalando librerias (esto solo tarda un minuto)...
    python -m pip install --upgrade pip --quiet
    pip install -r deps.txt --quiet
    echo [*] Instalando navegador interno...
    playwright install chromium
    echo done > "venv_windows\installed.txt"
)

:: 4. Iniciar Webhook Inteligente (Bot de WhatsApp)
echo [🤖] Iniciando Webhook de IA en segundo plano...
start /B python webhook.py

:: 5. Lanzar Scraper
echo [🚀] ¡Todo listo! El panel se abrira en tu navegador...
echo ----------------------------------------------------------
streamlit run app.py --server.port=8501 --server.headless=true --browser.gatherUsageStats=false --theme.base=dark

if %errorlevel% neq 0 (
    echo.
    echo [!] Hubo un error al iniciar el programa.
    pause
)
