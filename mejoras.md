# Hoja de Ruta: Lead Gen Pro "Elite" 🚀

Este documento detalla las mejoras estratégicas y técnicas para convertir este scraper en la herramienta definitiva de prospección B2B.

---

## 1. El Filtro Dinámico de Calificación (SEO vs Diseño) 🎯
*   **Problema:** Actualmente se descartan empresas con web, lo que mata el flujo de trabajo para expertos en SEO y Google Ads.
*   **Mejora:** Implementar un selector de "Modo de Operación":
    *   **Modo "Caza-Sitios" (Diseño Web):** Filtrar negocios SIN sitio web.
    *   **Modo "SEO Audit" (Marketing):** Filtrar negocios CON sitio web y capturar la URL.
    *   **Modo "Google Ads":** Filtrar negocios con buen rating pero sin el distintivo "Gestionado por el propietario".

---

## 2. Optimización de Velocidad "Hyper-Speed" ⚡
*   **Procesamiento Multi-Contexto:** Utilizar `browser.new_context()` para abrir 5 o 10 ventanas virtuales en paralelo, reduciendo el tiempo de escaneo de una zona de 10 minutos a menos de 2.
*   **Navegación Selectiva:** No cargar imágenes ni CSS de Google Maps para ahorrar ancho de banda y CPU, acelerando la carga de datos.
*   **Detección Dinámica de Carga:** Eliminar los `asyncio.sleep()` fijos. Usar `wait_for_selector` con tiempos de respuesta adaptativos.
*   **Bypass de Captcha:** Integración de servicios de resolución de captchas o rotación de User-Agents proactiva.

---

## 3. Inteligencia Geográfica Táctica 📍
*   **Sectorización Completa:** Ya se ha incluido la **Zona Centro**. 
*   **Búsqueda por Radio Exacto:** Implementar un slider para buscar en un radio de 1km, 5km o 10km desde una dirección específica usando coordenadas.
*   **Multi-Ciudad:** Permitir poner una lista de 5 ciudades y que el scraper trabaje solo durante la noche saltando de una a otra.

---

## 4. Extracción Profunda (Deep Scraping) 🔍
*   **Buscador de Emails:** Si se encuentra una web, el scraper debe visitarla automáticamente para buscar correos electrónicos (ej. info@empresa.com) y redes sociales (Instagram, Facebook, LinkedIn).
*   **Detección de Tecnologías:** Identificar si la web usa WordPress, Shopify, o si tiene instalado el Píxel de Facebook. Si no tiene Píxel, es un lead caliente para Ads.
*   **Horarios de Apertura:** Capturar si el negocio está abierto actualmente para priorizar llamadas telefónicas.

---

## 5. IA y Automatización de Ventas (Gemini Integration) 🤖
*   **Redacción de Pitch con IA:** Un botón que genere automáticamente un mensaje de WhatsApp personalizado usando el nombre del dueño, el nicho y una crítica constructiva sobre su perfil de Maps.
*   **Reporte de Auditoría PDF:** Generar un PDF profesional de una página que diga: "He analizado tu negocio en Google Maps y tienes estos 3 fallos...", listo para enviar por email.

---

## 6. Infraestructura y CRM 🗄️
*   **Dashboard de Estadísticas:** Gráficas en Streamlit que muestren la evolución de captación por día y por nicho.
*   **Exportación Total:** Además de CSV, añadir Excel (con formatos limpios), JSON y sincronización directa con Google Sheets.
*   **Gestión de Estados:** Añadir columnas para marcar leads como "Frío", "Contactado", "Cita Programada" o "Cerrado".

---

## 7. App Mobile y Notificaciones 📱
*   **Alertas al Móvil:** Notificación vía Telegram o WhatsApp cada vez que se encuentre un "Lead de Oro" (Rating > 4.5, muchas reseñas, pero sin web).

---

## Próximos Pasos Técnicos Inmediatos
1.  **Arreglar el Filtro:** Modificar la lógica de `app.py` para que el experto en SEO pueda ver negocios con web.
2.  **Multiprocesamiento:** Refactorizar el loop principal para lanzar procesos en paralelo.
3.  **Actualización de DB:** Añadir columnas para URL, Email y Redes Sociales.
