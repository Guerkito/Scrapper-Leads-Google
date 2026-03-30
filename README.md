# ⚡ Lead Gen Pro - Google Maps Scraper & CRM v10

¡Bienvenido al **Lead Gen Pro**! Una herramienta potente y automatizada diseñada para encontrar negocios locales en Google Maps que **no tienen sitio web**, ayudándote a identificar prospectos ideales para servicios de diseño web, marketing digital y SEO.

## 🚀 Características Principales

- **🔍 Búsqueda Inteligente:** Filtra automáticamente negocios sin sitio web oficial.
- **📍 Cobertura Global:** Soporte para múltiples países (Colombia, España, México, USA, Argentina, Chile, Perú y más).
- **🎯 Nichos Curados:** Selector con más de 50 nichos y subnichos organizados por categorías con emojis (Salud, Gastronomía, Construcción, etc.).
- **🗺️ Geocerca por Zonas:** Opción para buscar por toda la ciudad o por cuadrantes (Norte, Sur, Este, Oeste) para una prospección profunda.
- **📊 Dashboard CRM:** Visualiza tus leads en tiempo real con filtros por nicho, ciudad y fecha.
- **📥 Exportación:** Descarga tus bases de datos filtradas en formato CSV compatible con Excel.
- **🤖 Automatización con Playwright:** Navegación robusta que simula comportamiento humano para evitar bloqueos.

## 🛠️ Instalación

Asegúrate de tener Python 3.10+ instalado. Luego, sigue estos pasos:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Guerkito/Scrapper-Leads-Google.git
   cd Scrapper-Leads-Google
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # En Linux/Mac
   # venv\Scripts\activate   # En Windows
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Instalar navegadores de Playwright:**
   ```bash
   playwright install chromium
   # Si estás en Linux, puede que necesites:
   # sudo playwright install-deps
   ```

## 🖥️ Uso del Dashboard

Para lanzar la interfaz visual y empezar a captar leads, ejecuta:

```bash
streamlit run app.py
```

1. Selecciona el **País**, **Departamento** y **Ciudad**.
2. Elige el **Nicho** o escribe uno personalizado.
3. Define la **Zona de búsqueda** (Norte, Sur, Toda la ciudad, etc.).
4. Ajusta el número de resultados y dale a **🚀 INICIAR**.

## 📁 Estructura del Proyecto

- `app.py`: Interfaz principal en Streamlit y lógica del dashboard.
- `main.py`: Motor de scraping independiente (CLI).
- `geo_data.py`: Base de datos de países, departamentos y ciudades.
- `leads.db`: Base de datos SQLite donde se guardan tus prospectos (se crea automáticamente).
- `requirements.txt`: Librerías necesarias.

## ⚠️ Descargo de Responsabilidad

Esta herramienta está destinada únicamente a fines educativos y de prospección ética. El scraping de datos públicos debe realizarse respetando los términos de servicio de las plataformas y las leyes de privacidad locales (GDPR, etc.).

---
Desarrollado con ❤️ para agencias y freelancers que buscan escalar sus ventas.
