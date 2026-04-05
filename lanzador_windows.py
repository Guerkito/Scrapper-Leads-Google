import os
import sys
import multiprocessing

# --- CONFIGURACIÓN DE EMERGENCIA ANTI-BUCLE ---
# Forzamos estas variables ANTES de importar nada pesado
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'

if __name__ == '__main__':
    # Evita que el EXE se abra a sí mismo infinitamente en Windows
    multiprocessing.freeze_support()

def resolve_path(path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.dirname(__file__), path)

def main():
    import streamlit.web.cli as stcli
    
    # Si somos un subproceso de streamlit, dejamos que stcli tome el control
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        stcli.main()
        return

    # Si somos el proceso principal, preparamos el arranque
    app_path = resolve_path("app.py")
    
    # Argumentos críticos para evitar reinicios y bucles
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.port=8501",
        "--server.headless=true",
        "--global.developmentMode=false",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false"
    ]
    
    print("--------------------------------------------------")
    print("   INICIANDO LEAD GEN PRO ELITE (MODO SEGURO)     ")
    print("--------------------------------------------------")
    print(f"Buscando panel en: {app_path}")
    print("Por favor, espera unos segundos...")
    
    try:
        stcli.main()
    except Exception as e:
        print(f"\nERROR AL INICIAR: {e}")
        input("\nPresiona Enter para cerrar...")

if __name__ == '__main__':
    main()
