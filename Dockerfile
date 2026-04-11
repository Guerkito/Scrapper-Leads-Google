FROM python:3.10-slim

# v1.0.6 - Corrección de permisos de instalación
RUN apt-get update && apt-get install -y \
    wget gnupg \
    && rm -rf /var/lib/apt/lists/*

# Instalar Playwright temporalmente como root para configurar el sistema
RUN pip install --no-cache-dir playwright

# Instalar dependencias del sistema para Chromium como ROOT
# Esto evita que pida contraseña después
RUN playwright install-deps chromium

# Crear usuario y preparar entorno
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Cambiar al usuario para las tareas de la aplicación
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/user/app/ms-playwright

# Instalar dependencias de Python
COPY --chown=user:user deps.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r deps.txt

# Instalar el navegador Chromium en la carpeta de la app
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH && \
    playwright install chromium

# Copiar el código
COPY --chown=user:user . .

# Configuración de Streamlit
ENV STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 7860

CMD ["streamlit", "run", "app.py"]
