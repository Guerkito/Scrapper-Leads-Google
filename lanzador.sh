#!/bin/bash

# ==========================================================
# 🚀 LEAD GEN PRO - ELITE COMMAND CENTER
# Lanzador Unificado (Linux/macOS)
# ==========================================================

# 1. Configuración de Directorio
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Colores para la terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================================${NC}"
echo -e "${GREEN}         🚀 LEAD GEN PRO - ELITE COMMAND CENTER${NC}"
echo -e "${BLUE}==========================================================${NC}"
echo -e "[ SISTEMA DE INTELIGENCIA COMERCIAL - INICIANDO... ]"
echo ""

# 2. Verificar Archivo .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[!] Archivo .env no encontrado. Creando desde .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}[!] IMPORTANTE: Por favor, edita el archivo .env y configura tus credenciales.${NC}"
fi

# 3. Iniciar servicios Docker (Base de Datos, Redis, Evolution API)
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo -e "${BLUE}[*] Verificando servicios Docker (Postgres, Redis, Evolution API)...${NC}"
    # Verificar si las variables necesarias están en el .env antes de subir docker
    if grep -q "POSTGRES_PASSWORD=" .env && [ "$(grep "POSTGRES_PASSWORD=" .env | cut -d'=' -f2)" != "" ]; then
        docker compose up -d
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[OK] Servicios Docker activos.${NC}"
        else
            echo -e "${RED}[!] Error al iniciar Docker Compose. Continuando sin servicios externos...${NC}"
        fi
    else
        echo -e "${YELLOW}[!] ADVERTENCIA: POSTGRES_PASSWORD no configurado en .env. Saltando Docker Compose.${NC}"
    fi
else
    echo -e "${YELLOW}[!] ADVERTENCIA: Docker Compose no detectado. Los servicios externos podrían no funcionar.${NC}"
fi

# 4. Verificar Entorno Virtual
if [ ! -d "venv" ]; then
    echo -e "${BLUE}[*] Creando entorno virtual Python...${NC}"
    python3 -m venv venv
fi

# Activar el entorno virtual
source venv/bin/activate

# 5. Verificar/Instalar dependencias
if [ ! -f "venv/installed.txt" ]; then
    echo -e "${BLUE}[*] Instalando librerías y componentes (esto solo ocurre la primera vez)...${NC}"
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    playwright install chromium
    touch venv/installed.txt
    echo -e "${GREEN}[OK] Dependencias instaladas.${NC}"
fi

# 6. Iniciar el Webhook Inteligente en segundo plano
echo -e "${BLUE}[🤖] Iniciando Webhook Onyx...${NC}"
# Intentar matar instancias previas del webhook para evitar conflictos de puerto
pkill -f webhook.py 2>/dev/null
python3 webhook.py &
WEBHOOK_PID=$!

# Función para limpiar procesos al salir
cleanup() {
    echo -e "\n${YELLOW}[*] Deteniendo servicios y saliendo...${NC}"
    kill $WEBHOOK_PID 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM

# 7. Lanzar Aplicación Streamlit
echo -e "${GREEN}[🚀] ¡Todo listo! El panel se abrirá en tu navegador...${NC}"
echo -e "${BLUE}----------------------------------------------------------${NC}"
# Usamos exec para que streamlit tome el control del proceso y maneje las señales correctamente
streamlit run app.py --server.port=8501 --server.headless=true --browser.gatherUsageStats=false --theme.base=dark
