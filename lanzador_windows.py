import streamlit.web.cli as stcli
import os
import sys
import subprocess
import traceback
import time
from multiprocessing import freeze_support

def resolve_path(path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, path)

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = """
    ==========================================================
             🚀 LEAD GEN PRO - ELITE COMMAND CENTER
    ==========================================================
    [ SISTEMA DE INTELIGENCIA COMERCIAL - CARGANDO... ]
    
    * Optimizando entorno de trabajo...
    * Iniciando motores de scraping...
    * Preparando panel de control...
    
    ----------------------------------------------------------
    """
    print(banner)

def install_playwright():
    # Ya no instalamos nada, usamos el Chrome del sistema
    pass

if __name__ == "__main__":
    freeze_support()
    
    try:
        if not "_STREAMLIT_RUN_COMMAND_" in os.environ:
            print_banner()
            print("[!] Iniciando con el navegador del sistema...")
            time.sleep(0.5)

        app_path = resolve_path("app.py")
        
        sys.argv = [
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            "--theme.base=dark",
            "--theme.primaryColor=#00FF41" # Color verde Matrix/Elite
        ]
        
        sys.exit(stcli.main())

    except Exception as e:
        print("\n\n**********************************************************")
        print("           ERROR CRITICO AL INICIAR")
        print("**********************************************************")
        traceback.print_exc()
        print("\nPresiona Enter para cerrar y contactar soporte...")
        input()
