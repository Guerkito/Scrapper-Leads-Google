FROM python:3.10-slim

# v1.0.7 - Corrección total de permisos de carpeta app
RUN apt-get update && apt-get install -y \
    wget gnupg \
    && rm -rf /var/lib/apt/lists/*

# Instalar Playwright y dependencias de sistema como ROOT
RUN pip install --no-cache-dir playwright && \
    playwright install-deps chromium

# Crear usuario y configurar su carpeta de inicio
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# IMPORTANTE: Cambiar el dueño de la carpeta de la app al usuario 1000 antes de cambiar de usuario
RUN mkdir -p /data && chown user:user /home/user/app /data

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/user/app/ms-playwright

# Instalar dependencias de Python
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Ahora el usuario ya tiene permiso para crear carpetas aquí
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH && \
    playwright install chromium

# Copiar el código
COPY --chown=user:user . .

# Configuración de Streamlit
ENV STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=true \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    DB_PATH=/data/leads.db

VOLUME ["/data"]

EXPOSE 7860

CMD ["streamlit", "run", "app.py"]
