FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Configurar usuario para Hugging Face (UID 1000)
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Instalar dependencias de Python como root primero
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores de Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el resto del código y dar permisos al usuario
COPY --chown=user . /home/user/app

# Crear carpeta de datos y asegurar permisos
RUN mkdir -p /home/user/app/data && chown -R user:user /home/user/app/data

# Cambiar al usuario no-root
USER user

# Puerto obligatorio para Hugging Face
EXPOSE 7860

# Comando para arrancar Streamlit en el puerto correcto
CMD ["streamlit", "run", "app.py", "--server.port", "7860", "--server.address", "0.0.0.0"]
