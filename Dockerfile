FROM python:3.10-slim

# Versión para romper caché: 1.0.2
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libgbm-dev \
    libnss3 \
    libasound2 \
    libxshmfence1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Configurar el usuario primero
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Definir rutas de Playwright ANTES de instalar nada
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/home/user/app/ms-playwright \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Instalar dependencias de Python
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalar navegadores en la carpeta de la app como el usuario 1000
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH && \
    chown -R user:user /home/user/app && \
    playwright install chromium && \
    playwright install-deps chromium

# Copiar el resto del código
COPY --chown=user:user . .

USER user

EXPOSE 7860

# Comando para arrancar Streamlit
CMD ["streamlit", "run", "app.py"]
