FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar el navegador Chromium específicamente
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el código
COPY . .

# Crear carpeta para la base de datos persistente
RUN mkdir -p /app/data

# Exponer el puerto de Streamlit
EXPOSE 8501

# Comando para arrancar la app
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
