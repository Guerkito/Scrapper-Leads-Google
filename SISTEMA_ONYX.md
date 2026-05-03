# 🤖 Sistema Onyx v10.0 - Manual de Operación

Este documento detalla la arquitectura profesional desplegada para el ecosistema de **Onyx Software & Web**.

## 🏗️ Arquitectura del Sistema

### 1. Motor de WhatsApp (Evolution API v2.3.7)
- **Versión:** v2.3.7 (Última estable, con parches oficiales para el problema de LIDs).
- **Base de Datos:** PostgreSQL 15 (ORM Prisma). Requerido para la estabilidad de la v2.
- **Cache/Eventos:** Redis 7. Gestiona la cola de mensajes para evitar pérdidas y duplicados.
- **Red:** `network_mode: host`. El tráfico es directo entre Docker y tu máquina, eliminando latencias de proxy.
- **Puerto:** `8080`.

### 2. Cerebro de IA (Ollama + Qwen 9B)
- **Modelo:** `qwen3.5:9b`. Un modelo de 9 billones de parámetros optimizado para español y razonamiento de negocios.
- **Endpoint:** `/api/chat`. Permite una separación real entre las instrucciones del sistema y el historial del usuario.
- **Memoria:** El sistema recupera y envía los últimos 15 mensajes de la base de datos en cada interacción para mantener el contexto.

### 3. Orquestador (Webhook.py)
- **Puerto:** `5001`.
- **Funciones:**
    - **Registro Automático:** Crea leads nuevos en `leads.db` al recibir mensajes de desconocidos.
    - **LID Fix:** Prioriza `remoteJidAlt` para que los usuarios con dispositivos vinculados nunca fallen.
    - **Control de Horario:** Responde automáticamente fuera de oficina (8 PM - 8 AM).
    - **Auditoría:** Envía logs en tiempo real a la base de datos para verlos en el Dashboard.

## 🚀 Cómo Iniciar Todo

Si el servidor se reinicia, sigue este orden:

1. **Infraestructura:**
   ```bash
   docker compose up -d
   ```
2. **Bot Onyx:**
   ```bash
   python3 webhook.py
   ```
3. **Panel Streamlit:**
   ```bash
   ./venv/bin/streamlit run app.py --server.port 8501
   ```

## 🕵️‍♂️ Monitor de Auditoría
Puedes ver lo que Onyx está pensando y haciendo directamente en la pestaña **"🚀 Campañas WA"** del panel de Streamlit, en la sección **"Auditoría de Onyx"**.

## 🛠️ Variables de Calificación
El sistema ahora captura automáticamente (si la charla lo permite) y guarda en la base de datos:
- `tipo_proyecto` (Web, App, Software)
- `urgencia` (Alta, Media, Baja)
- `decisor` (Si es el dueño)
- `presupuesto_aprox`

---
**Nota Técnica:** El modelo Qwen 9B puede tardar entre 10-30 segundos en responder si se usa solo CPU. El timeout está configurado en 120s para garantizar la entrega.
