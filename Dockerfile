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
    && rm -rf /var/lib/apt/lists/*

# Configurar el usuario para Hugging Face (UID 1000)
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Instalar dependencias de Python como root
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalar Playwright y sus navegadores como root
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el código y dar permisos al usuario
COPY . .
RUN chown -R user:user /home/user/app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

EXPOSE 7860

# Comando para arrancar Streamlit
CMD ["streamlit", "run", "app.py", "--server.port", "7860", "--server.address", "0.0.0.0"]
