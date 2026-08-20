# Documentacion Tecnica - Lead Gen Pro / Onyx

## Changelog — Refactor mayo-julio 2026

Refactor mayor enfocado en seguridad, integridad de datos, mantenibilidad y eliminación de código obsoleto. Cambios resumidos a continuación; detalles técnicos en las secciones correspondientes del documento.

### Crítico (seguridad / integridad)

- **Webhook auth (`webhook.py`)**: el webhook ahora valida un token compartido (`WEBHOOK_AUTH_TOKEN`) antes de procesar cualquier request. Acepta el token vía `Authorization: Bearer <token>`, `X-Webhook-Token: <token>` o `apikey: <token>`. Comparación timing-safe con `hmac.compare_digest`. Si la variable está vacía arranca en modo dev con WARNING en logs.
- **Defensa básica del webhook**: límite de body (`WEBHOOK_MAX_BODY`, 64KB por defecto), validación de `Content-Length`, rechazo de body vacío y JSON inválido con códigos HTTP correctos (400/401/413/500). Logs estructurados con loguru e IP de los intentos fallidos.
- **`scraper.py` y `main.py` eliminados**: ambos eran scrapers monolíticos obsoletos. `scraper.py` acoplaba `st.session_state` a la lógica de scraping y duplicaba el motor de `engine/orchestrator.py`. Las constantes y helpers reutilizables se movieron a `engine/maps_helpers.py`.
- **`leads.db` raíz**: la BD vieja desactualizada en raíz (sin schema versionado) se movió a `data/leads_backup_pre-v5_<fecha>.db`. La BD activa es `data/leads.db`.

### Base de datos — esquema versionado e identidad por `place_id`

- **`schema_version`**: nueva tabla con la versión del esquema. `init_db()` solo aplica migraciones cuando la versión guardada es menor que `SCHEMA_VERSION`. Los `ALTER TABLE` ya no se ejecutan en cada arranque.
- **Migraciones aplicadas (v1 → v6)**:
  - **v1**: columnas históricas que faltaban en el `CREATE TABLE` original.
  - **v2**: nueva columna `place_id` indexada (`idx_place_id`) con backfill desde `maps_url`.
  - **v3**: consolidación de duplicados por `place_id` (rows distintos con el mismo CID se fusionan en el row de `id` menor; campos vacíos se rellenan, `fuentes_encontrado` se une por unión). Creación de `idx_unique_place_id` (índice único parcial donde `place_id IS NOT NULL`).
  - **v4**: recreación de la tabla `leads` para eliminar el `UNIQUE(nombre, ciudad)` del `CREATE` original (SQLite no permite quitar UNIQUE con `ALTER`). Se sustituye por un índice único parcial `idx_unique_nombre_ciudad_no_pid` que aplica solo cuando `place_id IS NULL`. Resultado: dos negocios reales con el mismo nombre+ciudad pero distinto `place_id` ahora coexisten.
  - **v5**: corrección de la regex de extracción de `place_id` (la versión anterior capturaba sólo medio CID porque no incluía el segundo `0x`). Re-extracción de `place_id` para todos los rows con `maps_url`.
  - **v6**: añade `telefono_e164` y `perfil_url`, recupera país/departamento sólo para ciudades inequívocas, normaliza teléfonos y cambia la identidad fallback a `(nombre, ciudad, país)` normalizada.
- **Identidad de un lead**: `place_id` (CID estable de Google Maps) es la clave primaria de identidad cuando existe. Si un lead no tiene `place_id`, se identifica por `(nombre, ciudad, país)` normalizado.
- **`save_lead` unificado** en una sola función. Lógica de upsert:
  1. Si el lead trae `place_id`, busca un row con ese mismo `place_id` o un único row sin `place_id` con la misma identidad (caso de promoción cuando otra fuente lo capturó antes). Nunca mezcla dos `place_id` distintos, aunque compartan nombre o NIT.
  2. Si el lead no trae `place_id`, busca por `(nombre, ciudad, país)` normalizado.
  3. Si encuentra, hace merge no destructivo (`COALESCE`/`MAX`) preservando datos previos. Si no, hace `INSERT`.
- **Resultado de la consolidación**: 921 → 755 leads (166 duplicados fusionados sin pérdida de campos).

### Performance

- **`load_all_leads` cacheado** con `@st.cache_data(ttl=30)`. Helper `invalidate_leads_cache()` en `services/leads.py` para invalidar tras inserts.
- **`load_known_identifiers`** ahora usa la columna indexada `place_id` en lugar de iterar `SELECT maps_url FROM leads` con regex sobre cada URL. Pasó de O(n × regex) a O(log n) por índice.
- **`SENT_CACHE` con TTL real**: en `services/campaigns.py`, antes era un dict global sin limpieza. Ahora tiene TTL de 24 horas, límite máximo de 5000 entradas y limpieza periódica con `_prune_sent_cache`.

### Configuración centralizada

- **Nuevo `config.py`**: todas las variables de entorno se leen una sola vez aquí. El resto del código importa nombres directamente. Cero `os.getenv` fuera de `config.py`.
- **Backend local aislado**: el webhook usa Ollama por `OLLAMA_CHAT_URL`/`OLLAMA_MODEL` y no expone shell ni herramientas al texto entrante.
- **`evo_headers()`** helper en `config.py` que construye los headers estándar para Evolution API (`apikey`, `Content-Type`, `ngrok-skip-browser-warning`). Reemplaza la duplicación en webhook/campaigns.
- **`WEBHOOK_PORT`** acepta `WEBHOOK_PORT` (preferido) o `PORT` (legacy) por compatibilidad con `.env` existentes.

### i18n y robustez

- **`click_cookie_consent()`** en `engine/maps_helpers.py`: helper que prueba textos del botón de consentimiento de cookies en ES/EN/PT/FR/DE. Aplicado en las 6 fuentes que usaban el patrón `try: page.click('button:has-text("Aceptar")') except: pass`. Más robusto si Chromium arranca con otro locale (CI, Docker).
- **`print()` → `logger`** en módulos clave (`db.py`, `services/leads.py`, `engine/*`, `sources/*`). Antes se perdían pistas en producción; ahora todo va a loguru con nivel apropiado (`error`/`warning`/`info`).

### Limpieza

- Borrados: `scraper.py` (468 líneas), `main.py` (127 líneas), `camp_block.txt`, `camp_stable.txt`, `mejoras.md` (snapshots/notas obsoletas), `debug_*.png/.txt`, `streamlit.log/.out`, `webhook.log` (artefactos de runtime).
- Renombrado: `deps.txt` → `requirements.txt` (convención estándar Python). Dockerfile, `.bat` y docs actualizados.
- La refactorización también añadió fuentes, campañas de email, normalización telefónica y exportaciones seguras.

### Tests

Suite completa después del cierre de julio de 2026: **16/16 verde**. Incluye persistencia, identidad geográfica, campañas, exportación segura, helpers de Maps, webhook, integración y cancelación de misiones.

### Pendiente (no atacado por riesgo / scope)

- Renombrar columna `reseñas` → `resenas` (rompe los `ON CONFLICT` y todas las queries existentes; bajo beneficio, alto riesgo).
- Normalizar `fuentes_encontrado` (TEXT JSON) a una tabla `lead_fuentes`. Útil si se quieren queries por fuente, pero no urgente.
- Consolidación v3 fusionó 166 rows que con la regex incorrecta parecían el mismo negocio. Algunos podrían haber sido lugares distintos. No reversible sin re-scrapear; hacia adelante la identificación es correcta.

---

## 1. Resumen del proyecto

Este proyecto es una aplicacion Python orientada a prospeccion comercial. Su objetivo principal es buscar negocios por nicho y ubicacion, extraer informacion de contacto, enriquecerla, guardarla en SQLite y usarla despues en un CRM, mapas, analiticas y campanas de WhatsApp.

La interfaz principal esta construida con Streamlit en `app.py`. El scraping usa Playwright para navegar fuentes externas como Google Maps, Paginas Amarillas, LinkedIn por Google Search y una integracion parcial con RUES. La persistencia se maneja en SQLite desde `db.py`. La automatizacion de WhatsApp usa Evolution API y un webhook HTTP en `webhook.py`, con respuestas generadas por Ollama.

## 2. Estructura general

```text
.
|-- app.py                    # Interfaz Streamlit principal y flujos de usuario
|-- config.py                 # Config centralizada (lee .env una sola vez)
|-- db.py                     # Inicializacion, conexion, guardado y migraciones SQLite
|-- webhook.py                # Webhook autenticado para respuestas IA por WhatsApp
|-- hermes_bridge.py          # Puente CLI para que Hermes consulte/actualice leads
|-- geocerca.py               # Utilidades de geocerca y grillas GPS
|-- city_coords.py            # Coordenadas base de ciudades para deep scan
|-- geo_data.py               # Paises, departamentos y municipios
|-- nichos_dict.py            # Diccionario de nichos y queries especializadas
|-- engine/
|   |-- orchestrator.py       # Orquestador multi-fuente
|   |-- maps_helpers.py       # Constantes/selectores Maps + click_cookie_consent i18n
|   |-- query_expander.py     # Expansion de terminos por diccionario/Ollama
|   |-- niche_catalog.py      # Resolucion local de nichos, sectores y tipos
|   `-- web_extractor.py      # Extraccion profunda en sitios web
|-- sources/
|   |-- base_source.py        # Dataclass Lead y contrato BaseSource
|   |-- google_maps.py        # Fuente modular de Google Maps
|   |-- paginas_amarillas.py  # Fuente modular de Paginas Amarillas
|   |-- linkedin.py           # Fuente modular LinkedIn via Google dorking
|   |-- facebook.py, instagram.py, yelp.py, tripadvisor.py,
|   |-- doctoralia.py, computrabajo.py, glassdoor.py
|   `-- rues.py               # Fuente RUES, esqueleto parcial
|-- services/
|   |-- campaigns.py          # Worker de campanas WhatsApp (hilo de fondo)
|   |-- email_service.py      # Envío y campañas SMTP
|   |-- phone_utils.py        # Normalización internacional E.164
|   |-- export_utils.py       # Protección de CSV/Excel contra fórmulas
|   |-- leads.py              # Carga cacheada de leads + scoring + WA links
|   |-- whatsapp_service.py   # Estado de conexion Evolution API
|   |-- search_mission.py     # Estado de mision de scraping en background
|   `-- constants.py          # Prefijos pais, colores estado, etc.
|-- ui/                       # Vistas Streamlit (search, crm, map, analytics, whatsapp, admin)
|-- tests_onyx/               # Pruebas de persistencia, regresión, concurrencia e integración
|-- Dockerfile                # Imagen para Streamlit
|-- docker-compose.yml        # Evolution API + Postgres + Redis
`-- requirements.txt          # Dependencias Python
```

## 3. Puntos de entrada

### `app.py`

Es el punto de entrada principal. Se ejecuta con:

```bash
streamlit run app.py
```

Responsabilidades:

- Importa `config` (que carga `.env` una sola vez en todo el proyecto).
- Inicializa la base de datos llamando `init_db()` (aplica migraciones si la versión guardada es menor que `SCHEMA_VERSION`).
- Renderiza la UI de Streamlit.
- Maneja el estado de la sesion y de busquedas/campanas en segundo plano.
- Lanza scraping modular mediante `engine.orchestrator.Orchestrator`.
- Permite gestionar leads, exportar datos, visualizar mapa, ver analiticas y enviar campanas WhatsApp.

### `webhook.py`

Servidor HTTP autenticado para recibir eventos de Evolution API.

```bash
python webhook.py
```

Responsabilidades:

- **Auth**: valida `WEBHOOK_AUTH_TOKEN` contra el header entrante (`Authorization: Bearer`, `X-Webhook-Token` o `apikey`). Si la variable está vacía, arranca en modo dev con WARNING.
- **Defensa básica**: rechaza body vacío, JSON inválido o body mayor a `WEBHOOK_MAX_BODY` (64 KB por defecto).
- Recibe eventos `messages.upsert`.
- Busca el lead asociado por teléfono o `whatsapp_id`. Si no existe, crea un lead `whatsapp_inbound` automáticamente.
- Responde `202` de inmediato y procesa el mensaje en un pool de workers.
- Deduplica eventos por ID y reintenta como máximo tres veces los que fallaron.
- Construye un contexto público mínimo y llama a Ollama sin shell, herramientas ni acceso al CRM.
- Envía la respuesta por Evolution API.
- Guarda historial y logs del bot en SQLite.

## 4. Variables de entorno

Todas las variables se leen una sola vez en `config.py` y el resto del código las importa desde ahí. **No quedan llamadas `os.getenv` fuera de `config.py`**. Documentadas en `.env.example`. No se deben poner claves reales en repositorio.

| Variable | Uso | Default |
| --- | --- | --- |
| `EVO_URL` | URL base de Evolution API | `http://127.0.0.1:8080` |
| `EVO_API_KEY` | API key de Evolution API | vacío |
| `EVO_INSTANCE` | Nombre de la instancia WhatsApp | `onyxbot` |
| `WEBHOOK_PORT` | Puerto del webhook de WhatsApp (acepta `PORT` legacy) | `5001` |
| `WEBHOOK_AUTH_TOKEN` | Token compartido para autenticar el webhook. Si está vacío, arranca en modo dev (warning). | vacío |
| `WEBHOOK_MAX_BODY` | Tamaño máximo del body POST en bytes | `65536` |
| `WEBHOOK_WORKERS` | Workers concurrentes del webhook | `4` |
| `WEBHOOK_LLM_BACKEND` | Backend seguro de respuesta (actualmente `ollama`) | `ollama` |
| `OLLAMA_URL` | Endpoint Ollama generate | `http://localhost:11434/api/generate` |
| `OLLAMA_CHAT_URL` | Endpoint Ollama chat usado por `query_expander.py` | `http://127.0.0.1:11434/api/chat` |
| `OLLAMA_MODEL` | Modelo local de Ollama | `qwen2.5:7b` |
| `DB_PATH` | Ruta de la base SQLite | `data/leads.db` |
| `MAX_CONCURRENT` | Concurrencia máxima del orquestador (limitada entre 1 y 8) | `6` |
| `POSTGRES_PASSWORD` | Solo si usas `docker-compose` con Evolution API | vacío |

Helper público en `config.py`:

```python
from config import evo_headers
requests.post(url, json=payload, headers=evo_headers())
```

`evo_headers()` retorna `{"apikey": EVO_API_KEY, "Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}` — reemplaza la duplicación previa en webhook y campañas.

## 5. Variables y constantes importantes por modulo

### `app.py`

| Nombre | Tipo | Funcion |
| --- | --- | --- |
| `NICHOS_DICT` | `dict[str, list[str]]` | Catalogo de sectores y subnichos para busqueda guiada y barrido total |
| `NICHO_SYNONYMS` | `dict[str, list[str]]` | Sinonimos por nicho para ampliar cobertura |
| `_NIVEL_CONFIG` | `dict` | Densidad de grilla para geocerca: 1, 9, 25 o 49 puntos |
| `COUNTRY_CODES` | `dict` | Prefijos telefonicos para WhatsApp |
| `MISSION` | `_SearchMission` en `st.session_state` | Estado persistente de una mision de scraping en segundo plano |
| `CAMP` | `_CampState` en `st.session_state` | Estado persistente de campanas WhatsApp |
| `AUTO_ZONAS` | `list[str]` | Zonas genericas usadas por flujos de busqueda legacy |
| `SENT_CACHE` | `dict` si esta definido en runtime | Cache anti-duplicado para envios recientes |

### `engine/maps_helpers.py`

Constantes y helpers reutilizables de scraping para Google Maps. Antes vivían en el `scraper.py` monolítico (eliminado).

| Nombre | Función |
| --- | --- |
| `BROWSER_ARGS` | Flags Chromium para Playwright en entorno headless/container |
| `_RATING_SELECTORS` | Selectores multi-idioma para rating de Google Maps |
| `_REVIEW_SELECTORS` | Selectores para cantidad de reseñas |
| `_WEB_SELECTORS` | Selectores para detectar sitio web |
| `_TYPE_SELECTORS` | Selectores para categoría/tipo de negocio |
| `_PANEL_LOADED_SELECTORS` | Selectores que indican que el panel lateral de Maps cargó |
| `_NO_MORE_SELECTORS` | Selectores/textos para detectar fin de resultados |
| `_extract_place_id(url)` | Extrae el CID de Google Maps (`0xHEX:0xHEX`) de una URL |
| `_wait_for_panel(page, name)` | Espera reactiva a que el panel lateral cargue |
| `_is_captcha(page)` | Detecta CAPTCHA o redirección a `consent.google` |
| `_scroll_and_wait(page, count)` | Scroll reactivo en el feed esperando nuevos items |
| `_is_end_of_results(page)` | Detecta texto de fin de resultados |
| `COOKIE_ACCEPT_TEXTS` | Textos del botón "Aceptar" en ES/EN/PT/FR/DE |
| `click_cookie_consent(page, timeout)` | Helper i18n: prueba todos los textos hasta cerrar el banner |

### `engine/orchestrator.py`

| Nombre | Funcion |
| --- | --- |
| `Orchestrator.fuentes` | Lista de fuentes que implementan `BaseSource` |
| `Orchestrator.semaphore` | Control de concurrencia segun `MAX_CONCURRENT` |
| `Orchestrator.stop_requested` | Bandera para cancelar una mision |

### `sources/base_source.py`

Define el modelo canonico `Lead`:

| Campo | Significado |
| --- | --- |
| `nombre` | Nombre del negocio |
| `ciudad` | Ciudad o punto GPS procesado |
| `nicho` | Nicho/query de busqueda |
| `fuente` | Fuente primaria: `google_maps`, `paginas_amarillas`, `linkedin`, `rues`, etc. |
| `fuentes_encontrado` | Lista de fuentes donde se encontro el mismo lead |
| `direccion`, `telefono`, `email`, `sitio_web` | Datos de contacto |
| `rating` | Calificacion numerica cuando existe |
| `nit` | Identificador legal, usado para deduplicacion |
| `lat`, `lng` | Coordenadas |
| `tiene_web` | Booleano para segmentar oportunidades sin web |
| `tipo` | `B2B` o `B2C` |
| `sector` | Sector comercial |
| `calificacion` | `oro`, `bueno` o `frio` |
| `estado` | Estado CRM inicial `Nuevo` |
| `instagram`, `facebook`, `linkedin_empresa` | Redes detectadas |
| `pixel_fb`, `pixel_google` | Indicadores de tecnologias de tracking |
| `decisor`, `verificado` | Datos comerciales y verificacion WhatsApp |
| `raw_data` | Datos crudos por fuente |

## 6. Base de datos

La base SQLite se inicializa desde `db.py`. Esquema **versionado** mediante la tabla `schema_version`.

### Ubicación

- En Hugging Face o contenedor con volumen `/data`: `/data/leads.db`.
- En local: `data/leads.db`.
- Backup automático de la BD pre-v5: `data/leads_backup_pre-v5_<fecha>.db`.

### Conexión

`open_conn()` abre SQLite con:

- `check_same_thread=False`
- `PRAGMA journal_mode = WAL`
- `PRAGMA synchronous = NORMAL`

### Esquema versionado

```python
SCHEMA_VERSION = 6
```

`init_db()`:

1. Crea `leads`, `schema_version`, `bot_logs`, `search_history`, `search_favorites`, `orders` si no existen (idempotente).
2. Lee la versión actual de `schema_version`.
3. Si la versión actual < `SCHEMA_VERSION`, ejecuta `_migrate(conn, current)` y guarda la nueva versión.
4. Crea índices (idempotente, barato).

Migraciones aplicadas:

| Versión | Cambio |
| --- | --- |
| v1 | Añade columnas históricas que faltaban en el `CREATE` original (`departamento`, `direccion`, `email`, `sitio_web`, `tiene_web`, redes sociales, píxeles, etc.). |
| v2 | Añade columna `place_id TEXT` indexada con backfill desde `maps_url`. |
| v3 | Consolida duplicados por `place_id` (rows distintas con mismo CID se fusionan en el de `id` menor; campos vacíos se rellenan, `fuentes_encontrado` se une). Crea `idx_unique_place_id` (índice único parcial cuando `place_id IS NOT NULL`). |
| v4 | Recrea la tabla `leads` para eliminar `UNIQUE(nombre, ciudad)` del `CREATE` original. Lo sustituye por `idx_unique_nombre_ciudad_no_pid` (índice único parcial cuando `place_id IS NULL`). Permite que dos negocios reales con mismo nombre+ciudad pero distinto `place_id` coexistan. |
| v5 | Corrige la regex de extracción de `place_id` (la versión anterior capturaba sólo medio CID). Re-extrae `place_id` para todos los rows con `maps_url`. |
| v6 | Añade `telefono_e164` y `perfil_url`, recupera geografía inequívoca, normaliza teléfonos y crea la identidad fallback normalizada por nombre, ciudad y país. |

### Identidad de un lead

`place_id` (CID estable de Google Maps, formato `0xHEX:0xHEX`) es la clave primaria de identidad cuando existe. Si un lead no tiene `place_id`, se identifica por `(nombre, ciudad, país)` normalizado. Dos `place_id` distintos nunca se fusionan por coincidencia de nombre o NIT.

Dos índices únicos parciales garantizan integridad sin bloquear casos legítimos:

```sql
CREATE UNIQUE INDEX idx_unique_place_id
  ON leads(place_id) WHERE place_id IS NOT NULL;

CREATE UNIQUE INDEX idx_unique_identity_no_pid ON leads(
  lower(trim(nombre)),
  lower(trim(COALESCE(ciudad, ''))),
  lower(trim(COALESCE(pais, '')))
) WHERE place_id IS NULL;
```

### Tabla `leads`

Columnas principales:

- Identidad: `id`, `nombre`, `place_id`, `maps_url`, `nit`, `representante_legal`, `ciiu`.
- Ubicación: `ciudad`, `departamento`, `direccion`, `pais`, `zona`, `lat`, `lng`.
- Contacto: `telefono`, `telefono_e164`, `email`, `sitio_web`, `perfil_url`, `whatsapp_id`.
- Clasificación: `nicho`, `sector`, `tipo`, `calificacion`, `estado`, `estado_contacto`.
- Fuente: `fuente`, `fuentes_encontrado` (JSON list), `raw_data` (JSON).
- Digital: `instagram`, `facebook`, `linkedin_empresa`, `pixel_fb`, `pixel_google`, `tiene_web`.
- CRM/bot: `notas`, `ultima_interaccion`, `bot_pausado`, `historial_mensajes`, `fecha_ultimo_contacto`, `decisor`, `verificado`.
- Fechas: `fecha_captura`.

### Otras tablas

| Tabla | Función |
| --- | --- |
| `schema_version` | Controla la versión del esquema para migraciones idempotentes |
| `bot_logs` | Auditoría reciente del bot IA |
| `search_history` | Historial de búsquedas por ciudad, país, nicho y zona |
| `search_favorites` | Configuraciones guardadas de búsqueda |
| `orders` | Pedidos/órdenes comerciales, estructura preparada |

### Guardado de leads — `save_lead(lead, conn)`

Función **única** (la antigua rama `dict` legacy fue eliminada al borrar `scraper.py`). Acepta un objeto `Lead`. Lógica:

1. Extrae `place_id` de `lead.maps_url` con `_extract_place_id_from_url(...)`.
2. Busca un row existente:
   - Si el lead trae `place_id`: busca por `place_id` exacto. Si no encuentra, sólo puede promover un único row compatible que aún no tenga `place_id`.
   - Si el lead no trae `place_id`: busca por `(nombre, ciudad, país)` normalizado y sólo fusiona coincidencias inequívocas.
3. Si encuentra, llama a `_merge_into_existing(...)` que hace UPDATE no destructivo: `COALESCE` rellena solo campos vacíos, `MAX` para rating/reseñas, promueve `place_id` y `maps_url` si el destino los tenía vacíos, y reemplaza `fuentes_encontrado` con la unión.
4. Si no encuentra, hace `INSERT`.

`COALESCE`/`NULLIF` evitan sobrescribir un valor real con `'N/A'` o vacío. La fusión preserva el lead más completo.

## 7. Flujo de busqueda principal

El flujo moderno es:

1. Usuario entra a vista `Busqueda` en `app.py`.
2. Selecciona nichos, pais, ciudades, fuentes, limite, deep scan y filtro sin sitio web.
3. `MISSION.start(...)` crea un hilo de fondo.
4. El hilo crea un event loop de asyncio.
5. Se instancia `Orchestrator` con las fuentes seleccionadas.
6. `Orchestrator.buscar_todos(...)` expande la query con `expandir_query(...)`.
7. Para cada ciudad y fuente, ejecuta busquedas asincronas.
8. Si `deep_scan` esta activo y la ciudad existe en `CITY_COORDS`, genera puntos GPS.
9. Cada fuente devuelve objetos `Lead`.
10. El orquestador elimina duplicados exactos de la tanda por URL o identidad normalizada.
11. `extract_deep_data(...)` visita sitios web detectados para extraer email, redes y pixeles.
12. `save_lead(...)` aplica la identidad persistente y guarda o enriquece los registros.
13. La UI refresca y muestra logs/contador.

## 8. Fuentes de datos

### Google Maps

Archivo: `sources/google_maps.py`.

Funcionamiento:

- Construye URL de Google Maps por query y ciudad o coordenadas `coord:lat,lng,zoom`.
- Usa Playwright headless.
- Acepta cookies si aparece el boton.
- Detecta captcha y corta la fuente.
- Lee items `a.hfpxzc`.
- Hace click en cada resultado y espera panel.
- Extrae nombre, telefono, sitio web, rating, coordenadas y URL cruda.
- Devuelve objetos `Lead`.

### Paginas Amarillas

Archivo: `sources/paginas_amarillas.py`.

Funcionamiento:

- Construye URL `https://www.paginasamarillas.com.co/busqueda/{query}/{ciudad}`.
- Detecta bloqueo/captcha por contenido HTML.
- Extrae items `.advert-item`, nombre, telefono y web.
- Devuelve objetos `Lead`.

### LinkedIn

Archivo: `sources/linkedin.py`.

Funcionamiento:

- No entra directamente a LinkedIn.
- Busca en Google con `site:linkedin.com/company "{query}" "{ciudad}"`.
- Extrae resultados `div.g`, titulo, link y snippet.
- Guarda el perfil en `perfil_url`/`linkedin_empresa`; no lo considera sitio web corporativo.
- Marca `tipo="B2B"` y calificacion por defecto `bueno`.

### RUES

Archivo: `sources/rues.py`.

Estado actual:

- **INACTIVO**: Tiene estructura de fuente y metodos base, pero la logica real de busqueda esta pendiente. No esta habilitado en la interfaz de usuario.

## 9. Deduplicacion

La deduplicación está integrada en `engine/orchestrator.py` y `db.py`:

1. El orquestador elimina repeticiones exactas dentro de la tanda usando `maps_url`, `perfil_url` o `(nombre, ciudad, país)`.
2. `db.save_lead(...)` usa `place_id` como identidad principal.
3. Sin `place_id`, el índice único usa nombre, ciudad y país normalizados.
4. Un registro sin `place_id` puede promocionarse cuando llega su identidad de Maps.
5. Dos `place_id` distintos permanecen separados aunque coincidan nombre, ciudad o NIT.
6. El merge rellena campos vacíos, conserva el mejor rating/calificación y une fuentes y `raw_data`.

## 10. Expansion de queries

Archivo: `engine/query_expander.py`.

Flujo:

1. Divide el input por comas.
2. Busca cada termino en `nichos_dict.NICHOS`.
3. Si hay coincidencia exacta o parcial, usa `queries_maps`.
4. Si no existe en el diccionario, consulta Ollama con `OLLAMA_CHAT_URL` y `OLLAMA_MODEL`.
5. Si Ollama falla, usa el termino original.
6. Deduplica las variaciones.

Para mas de 15 terminos, evita expansion IA y usa los terminos directos para no ralentizar.

## 11. Extraccion profunda web

Archivo: `engine/web_extractor.py`.

Para cada lead con `sitio_web`:

- Abre la pagina con Playwright.
- Bloquea imagenes, fuentes, CSS y media para acelerar.
- Extrae emails con regex.
- Detecta enlaces de Facebook, Instagram y LinkedIn Company.
- Detecta Facebook Pixel por `connect.facebook.net` o `fbevents.js`.
- Detecta Google Tag Manager / Analytics por `googletagmanager.com` o `google-analytics.com`.

## 12. Geocerca y deep scan

### `city_coords.py`

Contiene `CITY_COORDS`, un diccionario con coordenadas base por ciudad. Se usa para generar grillas GPS en deep scan.

### `geocerca.py`

Permite convertir dibujos de mapa en puntos de busqueda:

- `haversine_m(...)`: distancia en metros.
- `point_in_polygon(...)`: verifica si un punto cae dentro de un poligono.
- `_radius_to_zoom(...)`: convierte radio estimado a zoom de Google Maps.
- `generate_grid_in_feature(...)`: genera strings `coord:lat,lng,zoom`.
- `feature_centroid(...)`: calcula centroide para centrar el mapa.

## 13. CRM, mapas y analiticas

La UI de `app.py` maneja cinco vistas principales visibles:

| Vista | Funcion |
| --- | --- |
| `Busqueda` | Configurar y lanzar misiones de extraccion |
| `CRM` | Filtrar, revisar, exportar y editar leads |
| `Mapa` | Visualizar leads con coordenadas usando Folium |
| `Analytics` | KPIs, embudo, adopcion tecnologica y top ciudades |
| `WhatsApp` | Campanas, QR Evolution API, logs del bot y conversaciones |

Tambien existen referencias en documentacion antigua a vistas adicionales (`Geocerca`, `Historial`, `CRM full`, `Mapa full`, `Dividida`), pero han sido eliminadas del codigo actual para simplificar el mantenimiento.

## 14. Campañas WhatsApp

El worker de envío masivo vive en `services/campaigns.py` (`campaign_worker`). La UI está en `ui/whatsapp.py`.

Flujo:

1. El usuario filtra leads con teléfono válido.
2. Selecciona objetivo: nuevos, contactados o interesados.
3. Define plantilla con `{nombre}`.
4. Selecciona lote.
5. Puede usar modo simulación o envío real.
6. En modo real, envía `POST {EVO_URL}/message/sendText/{EVO_INSTANCE}` con headers de `evo_headers()` (helper de `config.py`).
7. Aplica prefijo de país desde `COUNTRY_CODES`.
8. Actualiza `estado` a `Contactado` si fue enviado.
9. Si Evolution API indica que el número no existe en WhatsApp, marca `Sin WhatsApp`.
10. Aplica pausa anti-ban:
    - Simulación: 5 a 10 segundos.
    - Real: 120 a 300 segundos.

**Anti-duplicados**: `SENT_CACHE` (módulo-global en `services/campaigns.py`) almacena el timestamp del último envío por número. TTL configurable (60 s por defecto), límite máximo de 5000 entradas, limpieza automática con `_prune_sent_cache()`. Antes era un dict sin limpieza (memory leak en procesos largos).

La UI también permite:

- Crear/conectar instancia Evolution API.
- Mostrar QR.
- Vincular por código.
- Borrar/resetear instancia.
- Ver logs de `bot_logs`.
- Pausar bot para un lead con `bot_pausado=1`.

## 15. Webhook IA de WhatsApp

`webhook.py` recibe mensajes entrantes, consulta Ollama con un prompt aislado sin herramientas y responde automáticamente.

### Auth (obligatoria en producción)

Antes de procesar cualquier request, valida un token compartido:

```python
def _is_authorized(headers) -> bool:
    if not WEBHOOK_AUTH_TOKEN:
        return True  # modo dev (warning emitido en arranque)
    presented = _extract_token(headers)
    return bool(presented) and hmac.compare_digest(presented, WEBHOOK_AUTH_TOKEN)
```

`_extract_token` acepta el token en tres formatos comunes:

1. `Authorization: Bearer <token>`
2. `X-Webhook-Token: <token>`
3. `apikey: <token>` (Evolution API usa este)

Comparación con `hmac.compare_digest` (timing-safe).

### Defensa básica

| Caso | Respuesta |
| --- | --- |
| Sin token / token incorrecto (con `WEBHOOK_AUTH_TOKEN` configurado) | `401 unauthorized` |
| `Content-Length` ausente o inválido | `400 invalid Content-Length` |
| Body vacío | `400 empty body` |
| Body > `WEBHOOK_MAX_BODY` (64 KB default) | `413 payload too large` |
| JSON inválido | `400 invalid JSON` |
| Evento duplicado/ignorado | `200` |
| Evento válido aceptado por el pool | `202 {"ok":true,"queued":true}` |

### Flujo de respuesta

1. Evolution API envía evento `messages.upsert`.
2. Se ignoran mensajes propios (`fromMe`).
3. Se extrae texto de `conversation` o `extendedTextMessage.text`.
4. `get_lead_context(remote_jid)` busca lead por teléfono parcial o `whatsapp_id`.
5. Si no existe, crea automáticamente un lead `whatsapp_inbound`.
6. `ask_local_assistant(lead, mensaje)` consulta `OLLAMA_CHAT_URL` con contexto público mínimo y sin acceso a herramientas, shell o base de datos.
7. Se responde vía Evolution API.
8. Se guarda `historial_mensajes`, `ultima_interaccion` y `bot_logs`.

### Configuración para producción

```bash
# Genera un token aleatorio
echo "WEBHOOK_AUTH_TOKEN=$(openssl rand -hex 32)" >> .env
```

Configura el mismo valor en Evolution API (header del webhook).

## 16. Tests

Suite en `tests_onyx/`:

| Test | Cubre |
| --- | --- |
| `test_persistence.py` | `save_lead` y merge de campos en upserts |
| `test_concurrency.py` | Colisiones repetidas de upsert sobre SQLite WAL |
| `test_bot_context.py` | Recuperación de contexto del lead desde el webhook |
| `test_integration.py` | Flujo del orquestador y filtro hunter |
| `test_maps_helpers.py` | Coincidencia del panel y coordenadas exactas de lugares |
| `test_regressions.py` | Identidad, campañas, exportación, teléfonos y cancelación segura |

Ejecutar con:

```bash
venv/bin/pytest -q
```

Tras el cierre de julio de 2026: **16/16 verde**.

## 17. Dependencias

Definidas en `requirements.txt` (renombrado desde `deps.txt`):

```
streamlit==1.55.0
playwright==1.58.0
playwright-stealth
pandas==2.3.3
beautifulsoup4==4.14.3
pydeck
folium==0.20.0
streamlit-folium==0.26.2
altair==6.0.0
watchdog==6.0.0
pyarrow==23.0.1
requests
python-dotenv
scrapling
curl_cffi
patchright
browserforge
apify-fingerprint-datapoints
httpx           # usado por engine/query_expander.py
loguru          # logging del webhook y módulos core
xlsxwriter      # exportación Excel
openpyxl        # importación Excel desde Administración
phonenumbers    # normalización E.164 por país
pytest          # tests_onyx/
```

## 18. Despliegue

### Local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
streamlit run app.py
```

### Docker Streamlit

`Dockerfile`:

- Usa `python:3.10-slim`.
- Instala dependencias de sistema de Playwright.
- Crea usuario `user`.
- Instala `requirements.txt`.
- Instala Chromium.
- Expone puerto `7860`.
- Ejecuta `streamlit run app.py`.

### Evolution API

`docker-compose.yml` levanta:

- `api`: Evolution API `evoapicloud/evolution-api:v2.3.7`.
- `db`: Postgres 15.
- `redis`: Redis 7.

Usa `network_mode: host`, por lo que los servicios quedan disponibles en localhost del host.

## 19. Notas técnicas y riesgos pendientes

1. `RUESSource` está incompleta; no extrae datos reales todavía.
2. `save_lead(...)` guarda `fuentes_encontrado` como JSON list (`json.dumps`). Si se quiere consultar por fuente con SQL, una tabla normalizada `lead_fuentes` sería más adecuada. No urgente.
3. Columna `reseñas` (con ñ): funciona en SQLite pero puede romper con algunas herramientas de migración. Renombrar a `resenas` es alto riesgo (rompe los `ON CONFLICT` y todas las queries existentes); pendiente.
4. La verificación WhatsApp y los envíos dependen totalmente de Evolution API y del estado de la instancia. Si la API no está disponible, la UI muestra errores pero no hay cola persistente de reintentos.
5. El scraping de Google Maps depende de selectores CSS de una página externa. Puede romperse si Google cambia clases o estructura.
6. El uso de Playwright y scraping externo puede activar CAPTCHA; el código detecta algunos casos y omite la zona/fuente.
7. **Consolidación v3**: fusionó 166 rows que con la regex de `place_id` incorrecta parecían el mismo negocio. Algunos podrían haber sido lugares distintos. No reversible sin re-scrapear; hacia adelante (v6) la identificación es correcta.

## 20. Flujo completo resumido

```text
Usuario Streamlit
  -> app.py / vista Búsqueda
  -> MISSION.start en hilo
  -> engine/orchestrator.Orchestrator
  -> engine/query_expander (diccionario o Ollama)
  -> sources/* seleccionadas (google_maps, paginas_amarillas, linkedin, ...)
  -> Lead[]
  -> deduplicación exacta de la tanda en engine/orchestrator
  -> engine/web_extractor (si hay sitio web)
  -> db.save_lead (upsert por place_id o nombre+ciudad+país)
  -> SQLite leads (data/leads.db, schema v6)
  -> CRM / Mapa / Analytics / WhatsApp (vistas Streamlit)
  -> services/campaigns + Evolution API
  -> webhook.py (auth) <- Evolution API webhook entrante
  -> Ollama local sin herramientas
  -> historial_mensajes + bot_logs
```
