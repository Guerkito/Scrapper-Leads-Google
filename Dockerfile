FROM python:3.10-slim

# Force full rebuild - v1.0.4
RUN apt-get update && apt-get install -y \
    wget gnupg libgbm-dev libnss3 libasound2 libxshmfence1 libatk-bridge2.0-0 libgtk-3-0 \
    libx11-xcb1 libxcb-dri3-0 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 \
    libxi6 libxrandr2 libxrender1 libxtst6 libpangocairo-1.0-0 libpango-1.0-0 \
    libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario y entorno antes de copiar nada
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/home/user/app/pw-browsers \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

WORKDIR /home/user/app

# Instalar dependencias desde el nuevo archivo deps.txt
COPY --chown=user:user deps.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r deps.txt

# Instalar navegadores en la ruta local del usuario
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH && \
    chown -R user:user /home/user/app && \
    playwright install chromium && \
    playwright install-deps chromium

# Copiar el código fuente
COPY --chown=user:user . .

# Limpiar chowns finales
RUN chown -R user:user /home/user/app

USER user

EXPOSE 7860

# Comando para arrancar Streamlit
ENTRYPOINT ["streamlit", "run", "app.py"]
