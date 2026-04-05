import streamlit.web.cli as stcli
import os
import sys
import subprocess

def resolve_path(path):
    # Obtener la ruta absoluta para el ejecutable (soporta PyInstaller)
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, path)

def install_playwright():
    try:
        # Intentar verificar si playwright esta instalado
        print("Verificando dependencias del navegador...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                       capture_output=True, check=True)
    except Exception as e:
        print(f"Error al instalar navegadores: {e}")

if __name__ == "__main__":
    # Instalacion automatica de navegadores si es necesario
    if getattr(sys, 'frozen', False):
        install_playwright()

    # Configurar los argumentos para arrancar Streamlit
    # Agregamos configuraciones para mejorar el rendimiento del EXE
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--global.developmentMode=false",
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    
    # Ejecutar el cli de streamlit
    sys.exit(stcli.main())
