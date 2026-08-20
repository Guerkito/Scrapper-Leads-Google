import streamlit as st
import html
import json
import sqlite3
import pandas as pd
from sources.google_maps import GoogleMapsSource
from sources.paginas_amarillas import PaginasAmarillasSource
from sources.linkedin import LinkedInSource
from sources.doctoralia import DoctoraliaSource
from sources.instagram import InstagramSource
from sources.tripadvisor import TripAdvisorSource
from sources.computrabajo import ComputrabajoSource
from sources.facebook import FacebookSource
from sources.yelp import YelpSource
from sources.glassdoor import GlassdoorSource
from geo_data import GEO_DATA
from db import DB_PATH
from services.constants import NICHOS_DICT, get_offer_suggestion
from services.product_campaigns import (
    FREE_CAMPAIGN,
    build_search_terms,
    campaign_label,
    campaign_options,
    default_segments,
    get_campaign,
    recommended_sources,
    segment_label,
    segment_options,
    valid_segments,
)
from services.search_mission import SearchMission
from ui.icons import svg_icon, title_html


@st.fragment(run_every=2)
def _render_mission_monitor(mission):
    """Actualiza solo el monitor; evita recargar toda la interfaz cada 2 segundos.

    El resumen de la misión (total_session, last_summary) lo consolida app.py en
    cada rerun, así no se pierde aunque el usuario esté en otra pestaña cuando
    termina la misión.
    """
    mission_state = mission.snapshot()
    if not mission_state["running"]:
        if st.session_state.pop("mission_was_running", False):
            st.rerun()
        return
    st.session_state.mission_was_running = True
    with st.container(border=True):
        mc1, mc2 = st.columns([2, 1])
        with mc1:
            st.markdown(title_html("MISIÓN EN CURSO", "bolt", 3), unsafe_allow_html=True)
            st.write("Capturando datos en segundo plano. Puedes cambiar de pestaña dentro de la app.")
            if mission_state.get("product_campaign") != FREE_CAMPAIGN:
                st.caption(
                    f"Campaña activa: {campaign_label(mission_state['product_campaign'])}"
                )
        with mc2:
            if st.button("ABORTAR MISIÓN", type="primary", width="stretch"):
                mission.stop()
                st.rerun()
        if mission_state["cold_call_mode"]:
            st.metric(
                "Teléfonos únicos listos",
                mission_state["callable_phones_found"],
            )
        else:
            st.metric("Leads nuevos en esta misión", mission_state["total_processed"])
        if mission_state["logs"]:
            logs = "\n".join(mission_state["logs"][-8:])
            st.code(logs, language=None)

def render_search_view():
    if 'MISSION' not in st.session_state:
        st.session_state.MISSION = SearchMission()
    MISSION = st.session_state.MISSION

    pending_favorite = st.session_state.pop("pending_search_favorite", None)
    if pending_favorite:
        try:
            saved_cities = json.loads(pending_favorite.get("ciudades") or "[]")
            saved_sources = json.loads(pending_favorite.get("fuentes") or "[]")
        except (TypeError, json.JSONDecodeError):
            saved_cities, saved_sources = [], []
        # Validar el país contra el catálogo: un valor fuera de GEO_DATA rompería
        # el selectbox y toda la vista con un KeyError.
        saved_country = str(pending_favorite.get("pais") or "Colombia")
        if saved_country not in GEO_DATA:
            saved_country = "Colombia"
        st.session_state.pais_sel = saved_country
        st.session_state.pais_sel_widget = saved_country
        st.session_state.city_locations = [
            f"{item.get('ciudad')} — {item.get('departamento')}"
            for item in saved_cities if isinstance(item, dict)
        ]
        st.session_state.search_sources = saved_sources
        st.session_state.search_limit = int(pending_favorite.get("limit_sel") or 20)
        st.session_state.search_deep = bool(pending_favorite.get("deep_scan"))
        st.session_state.search_cold_call = bool(pending_favorite.get("cold_call_mode"))
        st.session_state.search_no_website = bool(pending_favorite.get("hunter_mode"))
        saved_campaign = pending_favorite.get("product_campaign") or FREE_CAMPAIGN
        if saved_campaign not in campaign_options():
            saved_campaign = FREE_CAMPAIGN
        try:
            saved_segments = json.loads(pending_favorite.get("target_segments") or "[]")
        except (TypeError, json.JSONDecodeError):
            saved_segments = []
        st.session_state.search_product_campaign = saved_campaign
        st.session_state.search_target_segments = valid_segments(
            saved_campaign, saved_segments
        )
        tags = [tag.strip() for tag in str(pending_favorite.get("nicho") or "").split(",") if tag.strip()]
        if saved_campaign != FREE_CAMPAIGN:
            tags = build_search_terms(saved_campaign, st.session_state.search_target_segments)
        st.session_state.query_tags = tags
        st.session_state.multiselect_tags = tags

    st.markdown(title_html("Buscar nuevos clientes", "search", 2), unsafe_allow_html=True)
    st.caption(
        "Configura qué quieres vender, a quién buscas y en qué zona. "
        "ONYX preparará la lista y el argumento comercial."
    )

    with st.container(border=True):
        st.markdown(
            "<div class='workflow-steps'>"
            "<div class='workflow-step'><b>1</b> Oferta</div>"
            "<div class='workflow-step'><b>2</b> Cliente ideal</div>"
            "<div class='workflow-step'><b>3</b> Zona y fuentes</div>"
            "<div class='workflow-step'><b>4</b> Crear lista</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        barrido_total = bool(st.session_state.get("search_sweep_all", False))
        if barrido_total:
            st.warning(
                "Búsqueda general activa: se ignorarán la oferta y los tipos de empresa "
                "para recorrer todos los sectores disponibles."
            )

        product_keys = campaign_options()
        if st.session_state.get("search_product_campaign") not in product_keys:
            st.session_state.search_product_campaign = FREE_CAMPAIGN

        def _sync_product_campaign():
            selected_campaign = st.session_state.search_product_campaign
            selected_segments = default_segments(selected_campaign)
            campaign_terms = build_search_terms(selected_campaign, selected_segments)
            st.session_state.search_target_segments = selected_segments
            st.session_state.query_tags = campaign_terms
            st.session_state.multiselect_tags = campaign_terms
            st.session_state.search_sources = recommended_sources(selected_campaign)

        campaign_key = st.selectbox(
            "1. ¿Qué quieres vender?",
            product_keys,
            format_func=campaign_label,
            key="search_product_campaign",
            on_change=_sync_product_campaign,
            disabled=barrido_total,
            help="Esto adapta los clientes sugeridos, las fuentes, el decisor y el argumento de venta.",
        )
        campaign_active = campaign_key != FREE_CAMPAIGN and not barrido_total
        target_segments = []
        if campaign_active:
            allowed_segments = segment_options(campaign_key)
            current_segments = valid_segments(
                campaign_key, st.session_state.get("search_target_segments")
            )
            if not current_segments:
                current_segments = default_segments(campaign_key)
            st.session_state.search_target_segments = current_segments

            def _sync_target_segments():
                selected = valid_segments(
                    st.session_state.search_product_campaign,
                    st.session_state.search_target_segments,
                )
                campaign_terms = build_search_terms(
                    st.session_state.search_product_campaign, selected
                )
                st.session_state.query_tags = campaign_terms
                st.session_state.multiselect_tags = campaign_terms

            target_segments = st.multiselect(
                "2. ¿Qué tipo de cliente buscas?",
                allowed_segments,
                format_func=lambda key: segment_label(campaign_key, key),
                key="search_target_segments",
                on_change=_sync_target_segments,
                placeholder="Selecciona uno o más tipos de cliente",
            )
            campaign_data = get_campaign(campaign_key)
            roles = html.escape(" · ".join(campaign_data["decision_roles"]))
            note = html.escape(campaign_data.get("qualification_note", ""))
            st.markdown(
                "<div class='campaign-summary'>"
                f"<p><strong>{html.escape(campaign_data['label'])}</strong> — "
                f"{html.escape(campaign_data['description'])}</p>"
                f"<p><strong>Propuesta:</strong> {html.escape(campaign_data['pitch'])}</p>"
                f"<p><strong>A quién contactar:</strong> {roles}</p>"
                + (f"<p><strong>Qué validar:</strong> {note}</p>" if note else "")
                + "</div>",
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            if campaign_active:
                modo_input = True
            else:
                st.markdown(title_html("2. Clientes objetivo", "target", 4), unsafe_allow_html=True)
                modo_input = st.toggle(
                    "Escribir mis propios tipos de empresa", value=True,
                    help="Desactívalo para elegir un sector del catálogo de ONYX.",
                    disabled=barrido_total,
                )

            if not modo_input:
                cat_pre = st.selectbox("Sector", list(NICHOS_DICT.keys()), disabled=barrido_total)
                nicho_pre = st.selectbox("Tipo de empresa", NICHOS_DICT[cat_pre], disabled=barrido_total)
                query_input = nicho_pre
                if "TODOS LOS" not in nicho_pre:
                    st.info(f"**Qué podrías venderle:** {get_offer_suggestion(nicho_pre)}")
            else:
                if 'query_tags' not in st.session_state:
                    st.session_state.query_tags = []

                def _add_quick_niche(niche):
                    if 'query_tags' not in st.session_state: st.session_state.query_tags = []
                    if 'multiselect_tags' not in st.session_state: st.session_state.multiselect_tags = []

                    if niche not in st.session_state.query_tags:
                        st.session_state.query_tags.append(niche)

                    new_multiselect = list(st.session_state.multiselect_tags)
                    if niche not in new_multiselect:
                        new_multiselect.append(niche)
                    st.session_state.multiselect_tags = new_multiselect

                def _update_tags():
                    st.session_state.query_tags = st.session_state.multiselect_tags

                def _add_custom_tag():
                    val = st.session_state.new_tag_input.strip()
                    if val:
                        if 'query_tags' not in st.session_state: st.session_state.query_tags = []
                        if 'multiselect_tags' not in st.session_state: st.session_state.multiselect_tags = []

                        if val not in st.session_state.query_tags:
                            st.session_state.query_tags.append(val)

                        new_multiselect = list(st.session_state.multiselect_tags)
                        if val not in new_multiselect:
                            new_multiselect.append(val)
                        st.session_state.multiselect_tags = new_multiselect

                    st.session_state.new_tag_input = ""

                if campaign_active:
                    st.markdown(title_html("Términos preparados", "target", 4), unsafe_allow_html=True)
                    st.caption("Se generan automáticamente a partir del tipo de cliente elegido.")
                else:
                    st.caption("Sugerencias rápidas")
                    quick_niches = ["Colegios", "Odontólogos", "Restaurantes", "Fábricas", "Inmobiliarias"]
                    for idx, qn in enumerate(quick_niches):
                        if idx % 3 == 0:
                            q_cols = st.columns(3)
                        q_cols[idx % 3].button(
                            qn, key=f"quick_{qn}", width="stretch",
                            disabled=barrido_total, on_click=_add_quick_niche, args=(qn,),
                        )

                all_suggestions = sorted(list(set([n for sublist in NICHOS_DICT.values() for n in sublist])))

                selected_tags = st.multiselect(
                    "Términos automáticos" if campaign_active else "Tipos de empresa que buscarás",
                    options=sorted(list(set(all_suggestions + st.session_state.query_tags))),
                    default=st.session_state.query_tags,
                    disabled=barrido_total or campaign_active,
                    key="multiselect_tags",
                    on_change=_update_tags,
                    placeholder="Selecciona tipos de empresa",
                )

                if not campaign_active:
                    st.text_input(
                        "Agregar otro tipo de empresa",
                        key="new_tag_input",
                        disabled=barrido_total,
                        autocomplete="off",
                        on_change=_add_custom_tag
                    )

                # Mostrar etiquetas agregadas de forma Premium y limpia inline
                if st.session_state.query_tags and not campaign_active:
                    tags_html = "".join(
                        f"<span class='premium-badge'>{html.escape(t.strip())}</span>"
                        for t in st.session_state.query_tags
                    )
                    st.markdown(
                        f"<div class='badges-wrapper'>"
                        f"  {tags_html}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    # Botón discreto para limpiar todos los términos
                    c_clean, _ = st.columns([1, 2])
                    with c_clean:
                        if st.button("Limpiar selección", key="btn_clear_tags", type="secondary", disabled=campaign_active):
                            st.session_state.query_tags = []
                            st.session_state.multiselect_tags = []
                            st.rerun()

                query_input = ", ".join(st.session_state.query_tags)
                if st.session_state.query_tags:
                    with st.expander("Qué podrías venderles"):
                        for selected_niche in st.session_state.query_tags:
                            st.markdown(f"**{selected_niche}:** {get_offer_suggestion(selected_niche)}")

        with col2:
            st.markdown(title_html("3. Zona y fuentes", "pin", 4), unsafe_allow_html=True)
            paises = sorted(GEO_DATA.keys())
            def_idx = paises.index(st.session_state.pais_sel) if st.session_state.pais_sel in paises else 0
            pais_sel = st.selectbox("País", paises, index=def_idx, key="pais_sel_widget")
            st.session_state.pais_sel = pais_sel

            location_by_label = {}
            for departamento, municipios in GEO_DATA[pais_sel].items():
                for ciudad in municipios:
                    label = f"{ciudad} — {departamento}"
                    location_by_label[label] = {
                        "ciudad": ciudad,
                        "departamento": departamento,
                        "pais": pais_sel,
                    }
            default_locations = [
                label for label, value in location_by_label.items()
                if value["ciudad"] == "Bogotá"
            ][:1]
            ciudades_labels = st.multiselect(
                "Ciudades o municipios",
                options=sorted(location_by_label),
                default=default_locations,
                key="city_locations",
                placeholder="Selecciona ciudades o municipios",
            )
            ciudades_sel = [location_by_label[label] for label in ciudades_labels]

            fuentes_opciones = {
                "Maps": GoogleMapsSource(),
                "Páginas Amarillas": PaginasAmarillasSource(),
                "LinkedIn": LinkedInSource(),
                "Doctoralia (Salud)": DoctoraliaSource(),
                "Instagram": InstagramSource(),
                "TripAdvisor": TripAdvisorSource(),
                "Computrabajo (B2B)": ComputrabajoSource(),
                "Facebook": FacebookSource(),
                "Yelp": YelpSource(),
                "Glassdoor (Corporativo)": GlassdoorSource()
            }
            # RUES retirado: el portal rues.org.co no expone una búsqueda scrapeable
            # y su implementación anterior era un stub que nunca devolvía leads.

            fuentes_sel = st.multiselect(
                "Dónde buscar", list(fuentes_opciones.keys()), default=["Maps"],
                key="search_sources",
                help="Maps suele ser la opción más rápida para conseguir teléfonos públicos.",
                placeholder="Selecciona fuentes",
            )

        st.divider()
        st.markdown(title_html("4. Tipo de lista", "phone", 4), unsafe_allow_html=True)
        cold_call_mode = st.toggle(
            "Priorizar teléfonos y velocidad",
            value=True,
            help=(
                "Crea una lista de números válidos y únicos. Omite el análisis profundo "
                "de cada página para terminar más rápido."
            ),
            key="search_cold_call",
            disabled=barrido_total,
        )
        if barrido_total:
            cold_call_mode = False
        if cold_call_mode:
            st.caption("Usará Maps y, en Colombia, Páginas Amarillas. La meta se aplica por ciudad.")

        limit_sel = st.number_input(
            "Cantidad objetivo por ciudad" if cold_call_mode else "Cantidad máxima por zona",
            5, 500, 20, key="search_limit",
        )

        with st.expander("Opciones avanzadas y búsquedas guardadas"):
            advanced_1, advanced_2, advanced_3 = st.columns(3)
            with advanced_1:
                st.checkbox(
                    "Buscar todos los sectores",
                    key="search_sweep_all",
                    help="Ignora la oferta seleccionada y recorre el catálogo completo.",
                )
            with advanced_2:
                deep_scan = st.toggle(
                    "Explorar por cuadrículas",
                    help="Busca más zonas geográficas, pero tarda considerablemente más.",
                    key="search_deep", disabled=cold_call_mode,
                )
                if cold_call_mode:
                    deep_scan = False
            with advanced_3:
                hunter_mode = st.toggle(
                    "Solo negocios sin sitio web",
                    key="search_no_website",
                    help="Usa únicamente Maps y conserva negocios donde no se capturó una web.",
                )

            st.divider()
            st.markdown("**Búsquedas guardadas**")
            conn_fav = sqlite3.connect(DB_PATH)
            try:
                favs = pd.read_sql_query("SELECT * FROM search_favorites", conn_fav)
            except:
                favs = pd.DataFrame()
            conn_fav.close()
            if not favs.empty:
                selected_fav = st.selectbox("Cargar una búsqueda", ["Seleccionar..."] + favs['nombre'].tolist())
                if selected_fav != "Seleccionar...":
                    selected_row = favs[favs["nombre"] == selected_fav].iloc[0]
                    st.caption(
                        f"{selected_row.get('nicho', '')} · "
                        f"{selected_row.get('pais', '')} · "
                        f"{selected_row.get('ciudades', '')}"
                    )
                    if st.button("Aplicar favorito", key="apply_search_favorite"):
                        st.session_state.pending_search_favorite = selected_row.to_dict()
                        st.rerun()

            favorite_name = st.text_input(
                "Guardar esta configuración como", placeholder="Ej. Restaurantes Bogotá",
                key="favorite_name",
            )
            if st.button("Guardar búsqueda", key="save_search_favorite"):
                if not favorite_name.strip():
                    st.warning("Escribe un nombre para el favorito.")
                else:
                    with sqlite3.connect(DB_PATH) as favorite_conn:
                        favorite_conn.execute(
                            """
                            INSERT INTO search_favorites
                                (nombre, nicho, pais, ciudades, fuentes, limit_sel, deep_scan,
                                 product_campaign, target_segments, cold_call_mode, hunter_mode)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(nombre) DO UPDATE SET
                                nicho=excluded.nicho, pais=excluded.pais,
                                ciudades=excluded.ciudades, fuentes=excluded.fuentes,
                                limit_sel=excluded.limit_sel, deep_scan=excluded.deep_scan,
                                product_campaign=excluded.product_campaign,
                                target_segments=excluded.target_segments,
                                cold_call_mode=excluded.cold_call_mode,
                                hunter_mode=excluded.hunter_mode
                            """,
                            (
                                favorite_name.strip(),
                                ", ".join(st.session_state.get("query_tags", [])),
                                pais_sel, json.dumps(ciudades_sel, ensure_ascii=False),
                                json.dumps(fuentes_sel, ensure_ascii=False), int(limit_sel), bool(deep_scan),
                                campaign_key,
                                json.dumps(target_segments, ensure_ascii=False),
                                bool(cold_call_mode), bool(hunter_mode),
                            ),
                        )
                    st.success("Configuración guardada.")

        if MISSION.running:
            _render_mission_monitor(MISSION)

        if not MISSION.running:
            # Calcular dinámicamente qué términos se van a buscar
            if barrido_total:
                display_query = "TODAS LAS EMPRESAS (BARRIDO TOTAL)"
                final_query = "TODAS LAS EMPRESAS"
            else:
                if modo_input:
                    # Capturamos también lo que el usuario haya escrito en el campo de texto pero no haya presionado Enter
                    current_typed = st.session_state.get("new_tag_input", "").strip()
                    query_list = list(st.session_state.query_tags)
                    if current_typed and current_typed not in query_list:
                        query_list.append(current_typed)
                    final_query = ", ".join(query_list)
                    display_query = final_query
                else:
                    final_query = query_input
                    display_query = query_input

            # Mostrar mensaje informativo de términos a buscar de forma Premium y Estética
            if display_query:
                # Generamos los tags en HTML Premium
                tags_html = "".join(
                    f"<span class='premium-badge'>{html.escape(t.strip())}</span>"
                    for t in display_query.split(",") if t.strip()
                )
                st.markdown(
                    f"<div class='premium-terms-box'>"
                    f"  <div style='color:#CBD5E1; font-size:0.8rem; font-weight:700; margin-bottom:8px;'>Búsqueda lista</div>"
                    f"  <div class='badges-wrapper'>{tags_html}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='premium-terms-box' style='border-left-color: #FFCC00 !important;'>"
                    f"  <div style='color:#FBBF24; font-size:0.8rem; font-weight:700; margin-bottom:8px;'>Falta el tipo de empresa</div>"
                    f"  <div style='color:#CBD5E1; font-size:0.85rem;'>Selecciona una sugerencia o escribe el tipo de cliente que quieres encontrar.</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            cold_bulk_mode = cold_call_mode and "TODOS LOS SUBNICHOS" in final_query.upper()
            if cold_bulk_mode:
                st.warning("Elige un nicho concreto para crear una lista de llamadas rápida.")
            missing_campaign_segment = campaign_active and not target_segments
            if missing_campaign_segment:
                st.warning("Selecciona al menos un tipo de cliente para esta campaña.")
            missing_query = not barrido_total and not final_query.strip()
            missing_location = not ciudades_sel
            missing_sources = not fuentes_sel and not cold_call_mode
            if missing_location:
                st.warning("Selecciona al menos una ciudad o municipio.")
            if missing_sources:
                st.warning("Selecciona al menos una fuente de búsqueda.")

            if st.button(
                "Crear lista para llamar" if cold_call_mode else "Iniciar búsqueda completa",
                type="primary", width="stretch",
                disabled=(
                    cold_bulk_mode or missing_campaign_segment or missing_query
                    or missing_location or missing_sources
                ),
            ):
                # Si el usuario tenía algo escrito pero no presionó Enter, limpiarlo para la próxima vez
                if modo_input and st.session_state.get("new_tag_input"):
                    st.session_state.new_tag_input = ""

                if (final_query or barrido_total) and ciudades_sel and (fuentes_sel or cold_call_mode):
                    fuentes_instancias = [fuentes_opciones[f] for f in fuentes_sel]
                    if cold_call_mode:
                        fuentes_instancias = [fuentes_opciones["Maps"]]
                        if pais_sel == "Colombia":
                            fuentes_instancias.append(fuentes_opciones["Páginas Amarillas"])
                    if hunter_mode:
                        fuentes_instancias = [fuentes_opciones["Maps"]]

                    MISSION.start(
                        fuentes_instancias,
                        None,
                        final_query,
                        ciudades_sel,
                        deep_scan,
                        limit_sel,
                        barrido_total,
                        hunter_mode=hunter_mode,
                        pais=pais_sel,
                        cold_call_mode=cold_call_mode,
                        product_campaign=(campaign_key if campaign_active else FREE_CAMPAIGN),
                        target_segments=target_segments,
                    )
                    st.rerun()
                else:
                    st.warning("Completa los campos necesarios para iniciar.")
