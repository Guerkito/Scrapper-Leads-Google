#!/bin/bash
# Navegar al directorio del proyecto
cd "/home/guerk/Scrapper Clientes"

# Activar el entorno virtual
source venv/bin/activate

# Iniciar el Webhook Inteligente en segundo plano
echo "🚀 Iniciando Webhook Onyx..."
python3 webhook.py &

# Ejecutar la aplicación Streamlit
echo "🖥️ Iniciando Panel de Control..."
streamlit run app.py
