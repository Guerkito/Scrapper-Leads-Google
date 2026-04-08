FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Configurar usuario para Hugging Face (UID 1000)
# Hugging Face requiere que el usuario sea el 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Instalar dependencias de Python
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalar navegadores de Playwright (solo Chromium para ahorrar espacio)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el resto del código
COPY --chown=user . $HOME/app

# Crear carpeta de datos y asegurar permisos para la DB
RUN mkdir -p $HOME/app/data && chown -R user:user $HOME/app/data

USER user

# Puerto obligatorio para Hugging Face Spaces
EXPOSE 7860

# Configuración de Streamlit para evitar problemas de CORS y usar el puerto 7860
CMD ["streamlit", "run", "app.py", "--server.port", "7860", "--server.address", "0.0.0.0"]
