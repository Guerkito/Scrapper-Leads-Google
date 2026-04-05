import streamlit.web.cli as stcli
import os
import sys
import subprocess
import traceback
from multiprocessing import freeze_support

# Obtener la ruta del Escritorio para logs de error
def get_desktop_path():
    return os.path.join(os.path.expanduser("~"), "Desktop", "LEADGEN_ERROR_LOG.txt")

def resolve_path(path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, path)

if __name__ == "__main__":
    # ¡CRUCIAL para Windows!
    freeze_support()
    
    # Si Streamlit intenta reiniciarse, interceptamos el comando
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        # Estamos en un subproceso de Streamlit, dejamos que siga
        stcli.main()
        sys.exit(0)

    try:
        app_path = resolve_path("app.py")
        
        # Preparamos los argumentos de Streamlit
        # Forzamos todo a false para evitar subprocesos innecesarios
        sys.argv = [
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            "--server.fileWatcherType=none",
            "--client.toolbarMode=hidden"
        ]
        
        print("Iniciando LeadGen Pro Elite...")
        print("Cargando servidor interno...")
        
        # Arrancamos Streamlit
        stcli.main()

    except Exception as e:
        # Si algo falla antes de abrir, guardamos el error en el escritorio
        error_file = get_desktop_path()
        with open(error_file, "w") as f:
            f.write("--- ERROR DE ARRANQUE LEADGEN PRO ---\n")
            traceback.print_exc(file=f)
        
        print(f"\nFATAL ERROR: El programa no pudo iniciar.")
        print(f"Se ha guardado un reporte detallado en tu Escritorio: {error_file}")
        traceback.print_exc()
        input("\nPresiona Enter para cerrar...")
