---
title: Lead Gen Pro Elite
emoji: 📍
colorFrom: green
colorTo: indigo
sdk: docker
app_port: 7860
---

# Lead Gen ONYX

Herramienta privada de prospección para capturar, depurar, calificar y preparar leads para cold calling, WhatsApp y email. No incluye login: está pensada para ejecutarse en una máquina o red controlada.

---

### ⚠️ IMPORTANTE: Persistencia en Hugging Face
Para evitar que tus leads capturados se borren al reiniciar el Space, **debes activar el Persistent Storage**:
1. Ve a la pestaña **"Settings"** de tu Space en Hugging Face.
2. Baja hasta **"Persistent Storage"**.
3. Haz clic en **"Choose storage tier"** y selecciona una opción (la de 20GB es suficiente).
4. La aplicación guardará automáticamente la base de datos en `/data`, que es el volumen montado, para que tus datos sobrevivan a reinicios.

---

## 💻 Instalación Rápida para Windows (Recomendado)

¡Ya no necesitas usar la consola ni ser un experto! Sigue estos 3 pasos:

1.  **📥 Descarga:** Haz clic en el botón verde **"<> Code"** (arriba a la derecha) y selecciona **"Download ZIP"**.
2.  **📂 Descomprime:** Extrae la carpeta en tu escritorio o donde prefieras.
3.  **⚡ Ejecuta:** Haz doble clic en el archivo **`INICIAR_LEADGEN.bat`**.

> **¿Qué pasará?** El programa configurará todo automáticamente (Python, librerías y motor de búsqueda) y abrirá el panel en tu navegador. ¡Ahorra tiempo y empieza a prospectar!

---

## Funciones principales

### 🌪️ Prospección Universal Multi-Nicho
- Búsqueda multi-fuente en Maps, directorios, redes y portales empresariales.
- Catálogo local de más de 80 objetivos y soporte para términos libres mediante Ollama.
- Filtro real de empresas sin sitio web; perfiles sociales/directorios no cuentan como web propia.
- Deep Scan por cuadrícula cuando la ciudad tiene coordenadas inequívocas.
- Deduplicación por Place ID o identidad `empresa + ciudad + país`.
- Teléfonos internacionales E.164, scoring Oro/Bueno/Frío y enriquecimiento de emails.

### 🎯 Estrategia de Ventas (Matchmaker)
- Campañas simuladas o reales con registro persistente, supresión “No contactar” y protección anti-duplicados.
- Exportación CSV/Excel protegida contra fórmulas inyectadas.
- Panel de calidad de datos, historial de campañas y búsquedas favoritas.
- Webhook concurrente e idempotente para Evolution API con respuestas de Ollama sin herramientas.

---

## 🛠️ Instalación para Desarrolladores (Linux / Avanzado)

Si prefieres la terminal o usas Linux, sigue estos pasos:

1. **Clonar y Preparar:**
   ```bash
   git clone https://github.com/Guerkito/Scrapper-Leads-Google.git
   cd Scrapper-Leads-Google
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Ejecución:**
   ```bash
   bash lanzador.sh
   # O directamente con streamlit
   streamlit run app.py
   ```

---

## 🎨 Personalización (Icono de Escritorio)
Para tener un acceso directo profesional en Windows:
1. Clic derecho en `INICIAR_LEADGEN.bat` > **"Enviar a"** > **"Escritorio (crear acceso directo)"**.
2. Clic derecho en el nuevo icono del escritorio > **Propiedades** > **Cambiar icono**.
3. ¡Listo! Ya tienes tu Command Center a un solo clic.

---
*Desarrollado para cerrar contratos, no solo para buscar datos. 🚀🟢💎*

## Verificación

```bash
pytest -q
streamlit run app.py
```

Para Docker, la base se guarda en `/data/leads.db`. Monta un volumen persistente en `/data`.
