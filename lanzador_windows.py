import streamlit.web.cli as stcli
import os
import sys
import subprocess
import traceback

def resolve_path(path):
    # Obtener la ruta absoluta para el ejecutable (soporta PyInstaller)
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, path)

def install_playwright():
    try:
        print("Verificando dependencias del navegador...")
        # Usamos el ejecutable de python interno del bundle
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                       capture_output=True, check=True)
    except Exception as e:
        print(f"Aviso: Error instalando navegadores (puede que ya existan): {e}")

if __name__ == "__main__":
    try:
        # Instalacion automatica de navegadores si es necesario
        if getattr(sys, 'frozen', False):
            install_playwright()

        # Configurar los argumentos para arrancar Streamlit
        # IMPORTANTE: Nos aseguramos de que app.py exista antes de arrancar
        app_path = resolve_path("app.py")
        if not os.path.exists(app_path):
            print(f"ERROR CRITICO: No se encuentra el archivo app.py en {app_path}")
            sys.exit(1)

        sys.argv = [
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ]
        
        print("Arrancando servidor de LeadGenPro Elite...")
        sys.exit(stcli.main())

    except Exception as e:
        print("\n--- ERROR AL ARRANCAR LA APLICACIÓN ---")
        traceback.print_exc()
        print("\nPresiona Enter para cerrar...")
        input()
