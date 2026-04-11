FROM python:3.10-slim

# Instalar dependencias del sistema necesarias para Playwright
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

# Configurar el usuario para Hugging Face (UID 1000)
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Configurar variables de entorno para Playwright
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/home/user/app/ms-playwright

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Crear carpeta de navegadores y descargar Chromium
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH && \
    playwright install chromium && \
    playwright install-deps chromium

# Copiar el código
COPY . .

# Dar permisos totales al usuario sobre la carpeta de la app y los navegadores
RUN chown -R user:user /home/user/app && \
    chmod -R 777 /home/user/app/ms-playwright

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/home/user/app/ms-playwright \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 7860

# Comando para arrancar Streamlit
CMD ["streamlit", "run", "app.py"]
