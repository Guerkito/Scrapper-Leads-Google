# Documentacion Tecnica - Lead Gen Pro / Onyx

## 1. Resumen del proyecto

Este proyecto es una aplicacion Python orientada a prospeccion comercial. Su objetivo principal es buscar negocios por nicho y ubicacion, extraer informacion de contacto, enriquecerla, guardarla en SQLite y usarla despues en un CRM, mapas, analiticas y campanas de WhatsApp.

La interfaz principal esta construida con Streamlit en `app.py`. El scraping usa Playwright para navegar fuentes externas como Google Maps, Paginas Amarillas, LinkedIn por Google Search y una integracion parcial con RUES. La persistencia se maneja en SQLite desde `db.py`. La automatizacion de WhatsApp usa Evolution API y un webhook HTTP en `webhook.py`, con respuestas generadas por Ollama.

## 2. Estructura general

```text
.
|-- app.py                    # Interfaz Streamlit principal y flujos de usuario
|-- db.py                     # Inicializacion, conexion y guardado de SQLite
|-- scraper.py                # Scraper Google Maps legado/directo
|-- webhook.py                # Webhook para respuestas IA por WhatsApp
|-- main.py                   # Script CLI antiguo para Google Maps sin sitio web
|-- geocerca.py               # Utilidades de geocerca y grillas GPS
|-- city_coords.py            # Coordenadas base de ciudades para deep scan
|-- geo_data.py               # Paises, departamentos y municipios
|-- nichos_dict.py            # Diccionario de nichos y queries especializadas
|-- engine/
|   |-- orchestrator.py       # Orquestador multi-fuente
|   |-- query_expander.py     # Expansion de terminos por diccionario/Ollama
|   |-- deduplicator.py       # Deduplicacion y merge de leads
|   `-- web_extractor.py      # Extraccion profunda en sitios web
|-- sources/
|   |-- base_source.py        # Dataclass Lead y contrato BaseSource
|   |-- google_maps.py        # Fuente modular de Google Maps
|   |-- paginas_amarillas.py  # Fuente modular de Paginas Amarillas
|   |-- linkedin.py           # Fuente modular LinkedIn via Google dorking
|   `-- rues.py               # Fuente RUES, esqueleto parcial
|-- tests_onyx/               # Pruebas de persistencia, deduplicacion, concurrencia e integracion
|-- Dockerfile                # Imagen para Streamlit
|-- docker-compose.yml        # Evolution API + Postgres + Redis
`-- deps.txt                  # Dependencias Python
```

## 3. Puntos de entrada

### `app.py`

Es el punto de entrada principal. Se ejecuta con:

```bash
streamlit run app.py
```

Responsabilidades:

- Carga variables de entorno con `load_dotenv()`.
- Inicializa la base de datos llamando `init_db()`.
- Renderiza la UI de Streamlit.
- Maneja el estado de la sesion y de busquedas/campanas en segundo plano.
- Lanza scraping modular mediante `engine.orchestrator.Orchestrator`.
- Permite gestionar leads, exportar datos, visualizar mapa, ver analiticas y enviar campanas WhatsApp.

### `webhook.py`

Servidor HTTP para recibir eventos de Evolution API.

```bash
python webhook.py
```

Responsabilidades:

- Recibe eventos `messages.upsert`.
- Busca el lead asociado por telefono o `whatsapp_id`.
- Construye contexto conversacional.
- Llama a Ollama para generar respuesta.
- Envia la respuesta por Evolution API.
- Guarda historial y logs del bot en SQLite.

### `main.py`

Script CLI antiguo para buscar negocios sin sitio web en Google Maps y exportar CSV. No parece ser el flujo principal actual, pero sirve como herramienta independiente.

```bash
python main.py "odontologos en Bogota"
```

## 4. Variables de entorno

Las variables se documentan desde `.env.example`. No se deben poner claves reales en repositorio.

| Variable | Uso | Valor por defecto observado |
| --- | --- | --- |
| `EVO_URL` | URL base de Evolution API para enviar mensajes, verificar numeros y manejar instancia | `http://localhost:8090` en ejemplo, `app.py` usa fallback `http://127.0.0.1:8080` |
| `EVO_API_KEY` | API key de Evolution API | vacio en ejemplo |
| `EVO_INSTANCE` | Nombre de la instancia WhatsApp | `onyxbot` |
| `OLLAMA_URL` | Endpoint legacy de Ollama generate | `http://localhost:11434/api/generate` |
| `OLLAMA_CHAT_URL` | Endpoint usado por `query_expander.py`, `app.py` y `webhook.py` para chat | fallback `http://127.0.0.1:11434/api/chat` |
| `OLLAMA_MODEL` | Modelo local de Ollama para expansion, pitches y bot | fallback `qwen2.5:7b` |
| `DB_PATH` | Ruta deseada para la DB segun ejemplo | `data/leads.db` |
| `MAX_CONCURRENT` | Concurrencia maxima del orquestador modular | `5` |
| `WEBHOOK_PORT` | Puerto del webhook de WhatsApp | `5001` |

Nota tecnica: `db.py` calcula `DB_PATH` internamente. Si existe `/data`, usa `/data/leads.db`; si no, usa `./data/leads.db`. La variable `DB_PATH` del `.env.example` no se usa directamente en `db.py` en la version revisada.

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

### `scraper.py`

| Nombre | Funcion |
| --- | --- |
| `MAX_CONCURRENT` | Limite de concurrencia del scraper directo |
| `BROWSER_ARGS` | Flags Chromium para Playwright en entorno headless/container |
| `_RATING_SELECTORS` | Selectores multi-idioma para rating de Google Maps |
| `_REVIEW_SELECTORS` | Selectores para cantidad de resenas |
| `_WEB_SELECTORS` | Selectores para detectar sitio web |
| `_TYPE_SELECTORS` | Selectores para categoria/tipo de negocio |
| `_PANEL_LOADED_SELECTORS` | Selectores que indican que el panel lateral de Maps cargo |
| `_NO_MORE_SELECTORS` | Selectores/textos para detectar fin de resultados |

### `engine/orchestrator.py`

| Nombre | Funcion |
| --- | --- |
| `Orchestrator.fuentes` | Lista de fuentes que implementan `BaseSource` |
| `Orchestrator.deduplicator` | Instancia de `Deduplicator` para unificar resultados |
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

La base SQLite se inicializa desde `db.py`.

### Ubicacion

- En Hugging Face o contenedor con volumen `/data`: `/data/leads.db`.
- En local: `data/leads.db`.

### Conexion

`open_conn()` abre SQLite con:

- `check_same_thread=False`
- `PRAGMA journal_mode = WAL`
- `PRAGMA synchronous = NORMAL`

Esto permite mejor comportamiento con hilos y escrituras concurrentes moderadas.

### Tabla `leads`

Tabla principal. Tiene `UNIQUE(nombre, ciudad)`, por lo que dos leads con mismo nombre y ciudad se fusionan o se ignoran segun el camino de guardado.

Columnas principales:

- Identidad: `id`, `nombre`, `nit`, `representante_legal`, `ciiu`.
- Ubicacion: `ciudad`, `departamento`, `direccion`, `pais`, `zona`, `lat`, `lng`.
- Contacto: `telefono`, `email`, `sitio_web`, `whatsapp_id`.
- Clasificacion: `nicho`, `sector`, `tipo`, `calificacion`, `estado`, `estado_contacto`.
- Fuente: `fuente`, `fuentes_encontrado`, `raw_data`.
- Digital: `instagram`, `facebook`, `linkedin_empresa`, `pixel_fb`, `pixel_google`, `tiene_web`.
- CRM/bot: `notas`, `ultima_interaccion`, `bot_pausado`, `historial_mensajes`, `fecha_ultimo_contacto`, `decisor`, `verificado`.
- Fechas: `fecha_captura`.

### Otras tablas

| Tabla | Funcion |
| --- | --- |
| `bot_logs` | Auditoria reciente del bot IA |
| `search_history` | Historial de busquedas por ciudad, pais, nicho y zona |
| `search_favorites` | Configuraciones guardadas de busqueda |
| `orders` | Pedidos/ordenes comerciales, estructura preparada |

### Guardado de leads

`save_lead(lead, conn)` tiene dos modos:

1. Si recibe un objeto `Lead`, hace `INSERT ... ON CONFLICT(nombre, ciudad) DO UPDATE`. Enriquece campos faltantes con `COALESCE`, conserva el mejor `rating`, agrega redes/pixeles y concatena fuentes.
2. Si recibe un `dict` legacy, usa `INSERT OR IGNORE` con columnas basicas: `nombre`, `ciudad`, `telefono`, `rating`, `nicho`.

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
10. `Deduplicator.deduplicar(...)` fusiona duplicados.
11. `extract_deep_data(...)` visita sitios web detectados para extraer email, redes y pixeles.
12. `save_lead(...)` guarda o enriquece los registros.
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
- Usa el perfil LinkedIn como `sitio_web`.
- Marca `tipo="B2B"` y calificacion por defecto `bueno`.

### RUES

Archivo: `sources/rues.py`.

Estado actual:

- **INACTIVO**: Tiene estructura de fuente y metodos base, pero la logica real de busqueda esta pendiente. No esta habilitado en la interfaz de usuario.

## 9. Deduplicacion

Archivo: `engine/deduplicator.py`.

La deduplicacion ocurre antes del guardado masivo:

1. Normaliza nombres a minusculas.
2. Elimina sufijos legales comunes: SAS, LTDA, SA, EU, IPS.
3. Quita puntuacion y espacios extras.
4. Fusiona por:
   - NIT igual.
   - Telefono igual.
   - Nombre similar en la misma ciudad con ratio fuzzy mayor a `0.85`.
5. `merge_leads(...)` conserva la informacion mas completa y une fuentes.

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

## 14. Campanas WhatsApp

El envio masivo vive en `app.py`, principalmente en `_campaign_worker(...)`.

Flujo:

1. El usuario filtra leads con telefono valido.
2. Selecciona objetivo: nuevos, contactados o interesados.
3. Define plantilla con `{nombre}`.
4. Selecciona lote.
5. Puede usar modo simulacion o envio real.
6. En modo real, envia `POST {EVO_URL}/message/sendText/{EVO_INSTANCE}`.
7. Aplica prefijo de pais desde `COUNTRY_CODES`.
8. Actualiza `estado` a `Contactado` si fue enviado.
9. Si Evolution API indica que el numero no existe en WhatsApp, marca `Sin WhatsApp`.
10. Aplica pausa anti-ban:
    - Simulacion: 5 a 10 segundos.
    - Real: 120 a 300 segundos.

La UI tambien permite:

- Crear/conectar instancia Evolution API.
- Mostrar QR.
- Vincular por codigo.
- Borrar/resetear instancia.
- Ver logs de `bot_logs`.
- Pausar bot para un lead con `bot_pausado=1`.

## 15. Webhook IA de WhatsApp

`webhook.py` recibe mensajes entrantes y responde automaticamente:

1. Evolution API envia evento `messages.upsert`.
2. Se ignoran mensajes propios (`fromMe`).
3. Se extrae texto de `conversation` o `extendedTextMessage.text`.
4. `get_lead_context(remote_jid)` busca lead por telefono parcial o `whatsapp_id`.
5. `get_system_prompt(...)` elige prompt segun `sector`.
6. `ask_ollama(...)` envia historial y mensaje actual a Ollama.
7. Se responde via Evolution API.
8. Se guarda `historial_mensajes`, `ultima_interaccion` y `bot_logs`.

Prompts actuales por sector:

- `educacion`
- `alimentos`
- `medio_ambiente`
- `general`

## 16. Dependencias

Definidas en `deps.txt`:

- `streamlit`
- `playwright`
- `playwright-stealth`
- `pandas`
- `beautifulsoup4`
- `pydeck`
- `folium`
- `streamlit-folium`
- `altair`
- `watchdog`
- `pyarrow`
- `requests`
- `python-dotenv`

Dependencias importadas pero no listadas explicitamente en `deps.txt`:

- `httpx`, usado en `engine/query_expander.py`.
- `loguru`, usado en `webhook.py`.
- `xlsxwriter`, usado para exportacion Excel en `app.py`.
- `pytest`, usado por `tests_onyx/`.

Si el entorno no las trae transitivamente, se deben agregar a `deps.txt`.

## 17. Despliegue

### Local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r deps.txt
playwright install chromium
streamlit run app.py
```

### Docker Streamlit

`Dockerfile`:

- Usa `python:3.10-slim`.
- Instala dependencias de sistema de Playwright.
- Crea usuario `user`.
- Instala `deps.txt`.
- Instala Chromium.
- Expone puerto `7860`.
- Ejecuta `streamlit run app.py`.

### Evolution API

`docker-compose.yml` levanta:

- `api`: Evolution API `evoapicloud/evolution-api:v2.3.7`.
- `db`: Postgres 15.
- `redis`: Redis 7.

Usa `network_mode: host`, por lo que los servicios quedan disponibles en localhost del host.

## 18. Pruebas

Carpeta: `tests_onyx/`.

| Archivo | Que valida |
| --- | --- |
| `test_persistence.py` | UPSERT y enriquecimiento de leads |
| `test_deduplicator.py` | Merge por nombre fuzzy, telefono y NIT |
| `test_concurrency.py` | Inserciones concurrentes sobre SQLite WAL |
| `test_integration.py` | Flujo del orquestador con fuentes mock |
| `test_bot_context.py` | Recuperacion de contexto del bot por WhatsApp ID/telefono |

Ejecucion esperada:

```bash
pytest tests_onyx
```

## 19. Notas tecnicas y riesgos detectados

Estas notas salen de la revision del codigo actual:

1. `app.py` referencia columnas como `reseñas`, `fecha`, `web` y `maps_url` en algunos bloques legacy/importacion, pero `db.py` no las crea como columnas principales. La tabla actual usa `rating`, `sitio_web`, `fecha_captura` y guarda `maps_url` dentro de `raw_data` para leads modulares. Esto puede romper vistas o importaciones antiguas.
2. `db.py` define `DB_PATH` internamente y no lee `DB_PATH` desde variables de entorno, aunque `.env.example` la documenta.
3. `RUESSource` esta incompleta; no extrae datos reales todavia.
4. `engine/query_expander.py` depende de `httpx`, y `webhook.py` depende de `loguru`; no aparecen en `deps.txt`.
5. La exportacion Excel usa `xlsxwriter`; tampoco aparece en `deps.txt`.
6. `save_lead(...)` concatena `fuentes_encontrado` como string JSON sin separador en el UPSERT. Puede terminar generando contenido dificil de parsear si el lead se actualiza varias veces.
7. En `app.py` hay bloques de vistas no expuestas por el navbar principal. Conviene limpiar o conectar esas vistas para evitar deuda tecnica.
8. La verificacion WhatsApp y los envios dependen totalmente de Evolution API y del estado de la instancia. Si la API no esta disponible, la UI muestra errores pero no hay cola persistente de reintentos.
9. El scraping de Google Maps depende de selectores CSS de una pagina externa. Puede romperse si Google cambia clases o estructura.
10. El uso de Playwright y scraping externo puede activar CAPTCHA; el codigo detecta algunos casos y omite la zona/fuente.

## 20. Flujo completo resumido

```text
Usuario Streamlit
  -> app.py / vista Busqueda
  -> MISSION.start en hilo
  -> Orchestrator
  -> query_expander
  -> sources seleccionadas
  -> Lead[]
  -> Deduplicator
  -> web_extractor si hay sitio web
  -> db.save_lead
  -> SQLite leads
  -> CRM / Mapa / Analytics / WhatsApp
  -> Evolution API
  -> webhook.py para respuestas entrantes
  -> Ollama
  -> historial_mensajes + bot_logs
```
