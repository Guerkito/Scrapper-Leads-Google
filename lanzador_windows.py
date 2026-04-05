import streamlit.web.cli as stcli
import os
import sys
import subprocess
import traceback
from multiprocessing import freeze_support

def resolve_path(path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, path)

def install_playwright():
    # Solo intentamos instalar si no estamos ya en un subproceso de streamlit
    if "_STREAMLIT_RUN_COMMAND_" in os.environ:
        return
        
    try:
        # Verificamos si ya existe el navegador para no repetir
        # Esto evita que se abran multiples procesos
        print("Preparando entorno seguro...")
        # Ejecutamos la instalacion de forma que no bloquee ni cree bucles
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0" # Usa la ruta por defecto
        subprocess.run(["playwright", "install", "chromium"], 
                       shell=True, capture_output=True)
    except:
        pass

if __name__ == "__main__":
    # ¡IMPORTANTE! Evita que el EXE se abra a si mismo infinitamente en Windows
    freeze_support()
    
    try:
        if getattr(sys, 'frozen', False):
            install_playwright()

        app_path = resolve_path("app.py")
        
        # Configuracion para que Streamlit NO intente usar el EXE como interprete
        sys.argv = [
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ]
        
        sys.exit(stcli.main())

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        input("Presiona Enter para cerrar...")
