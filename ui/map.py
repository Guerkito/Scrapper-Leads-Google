import streamlit as st
import folium
import html as html_lib
from urllib.parse import urlparse
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
import pandas as pd
from services.leads import get_wa_link
from services.constants import STATUS_COLORS
from ui.helpers import kpi_card
from ui.icons import title_html

def _status_color(estado):
    return STATUS_COLORS.get(estado, STATUS_COLORS["Nuevo"])

def _build_popup(row, pais_sel, compact=False):
    def safe(value):
        if pd.isna(value):
            return ""
        return html_lib.escape(str(value), quote=True)

    def safe_url(value):
        candidate = str(value or "").strip()
        try:
            return candidate if urlparse(candidate).scheme in {"http", "https"} else ""
        except ValueError:
            return ""

    wa   = get_wa_link(row, pais_sel)
    maps = safe_url(row.get('maps_url', ''))
    sc   = _status_color(row['estado'])
    pad  = "6px 10px" if compact else "10px 14px"
    badge = (f"<span style='background:{sc['color']};color:#0C0C0E;padding:2px 8px;"
             f"border-radius:4px;font-size:11px;font-weight:700;'>{safe(row['estado'])}</span>")
    html = (f"<div style='min-width:200px;font-family:\"Space Grotesk\",sans-serif; background:#16161E; color:white; padding:10px; border-radius:8px;'>"
            f"<b style='font-size:14px; color:#FFFFFF;'>{safe(row['nombre'])}</b><br>"
            f"<span style='color:#888898;font-size:11px;'>Rating {safe(row['rating'])} &nbsp;·&nbsp; {safe(row['reseñas'])} reseñas</span><br>"
            f"<div style='margin:8px 0'>{badge}</div>"
            f"<p style='color:#6A6A7A; font-size:11px; margin:4px 0;'>{safe(row.get('ciudad', ''))} · {safe(row.get('nicho', ''))}</p>"
            f"<hr style='border-color:#1E1E28;margin:8px 0;'>")
    if wa:
        html += (f"<a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:{pad};"
                 f"display:block;text-align:center;text-decoration:none;border-radius:6px;"
                 f"font-size:12px;font-weight:600;margin-bottom:8px;'>WhatsApp</a>")
    if maps:
        html += (f"<a href='{safe(maps)}' target='_blank' rel='noopener noreferrer' style='color:{sc['color']};text-align:center;"
                 f"display:block;font-size:12px;font-weight:600;text-decoration:none;'>Ver en Google Maps</a>")
    html += "</div>"
    return html

def render_map_view(df_all):
    pais_sel = st.session_state.get('pais_sel', 'Colombia')

    # Filtrado inicial de coordenadas
    df_map = df_all.dropna(subset=['lat', 'lng']).copy()
    
    if df_map.empty:
        st.info("No hay datos geográficos para mostrar. Asegúrate de capturar leads con el modo Maps.")
        return

    # Sidebar lateral de filtros rápidos para el mapa
    with st.container(border=True):
        f1, f2, f3 = st.columns([2, 1, 1])
        estados_map = f1.multiselect("Estados a visualizar", list(STATUS_COLORS.keys()), default=list(STATUS_COLORS.keys()))
        min_rating = f2.slider("Rating mín", 0.0, 5.0, 0.0)
        zoom_init = f3.selectbox("Zoom inicial", [10, 12, 14, 16], index=1)
    
    # Aplicar filtros
    df_f = df_map[df_map['estado'].isin(estados_map)].copy()
    def _p(x):
        try: return float(str(x).split('/')[0].strip()) if x else 0
        except: return 0
    df_f['rating_num'] = df_f['rating'].apply(_p)
    df_f = df_f[df_f['rating_num'] >= min_rating]

    if df_f.empty:
        st.warning("No hay leads que coincidan con los filtros seleccionados.")
        return

    # Crear el Mapa
    center_lat = df_f['lat'].mean()
    center_lon = df_f['lng'].mean()
    
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=zoom_init, 
        tiles="CartoDB dark_matter",
        attr="Onyx Intelligence Map"
    )

    # Inyectar CSS personalizado para Popups Oscuros
    dark_popup_css = """
    <style>
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {
            background: #16161E !important;
            color: white !important;
            border: 1px solid #1E1E28 !important;
            box-shadow: 0 0 20px rgba(0,0,0,0.5) !important;
        }
        .leaflet-popup-content {
            margin: 0 !important;
            width: auto !important;
        }
        .leaflet-container a.leaflet-popup-close-button {
            color: #888898 !important;
            padding: 8px 8px 0 0 !important;
        }
    </style>
    """
    m.get_root().header.add_child(folium.Element(dark_popup_css))
    
    # Añadir marcadores (agrupados en clústeres para mapas densos)
    cluster = MarkerCluster(name="Leads", show=True).add_to(m)
    for _, row in df_f.iterrows():
        sc = _status_color(row['estado'])
        folium.CircleMarker(
            location=[row['lat'], row['lng']],
            radius=9,
            popup=folium.Popup(_build_popup(row, pais_sel), max_width=300),
            color=sc['color'],
            fill=True,
            fill_color=sc['fill'],
            fill_opacity=0.7,
            weight=2
        ).add_to(cluster)

    # Mapa de calor: zonas calientes ponderadas por rating
    heat_data = [
        [row['lat'], row['lng'], row['rating_num']]
        for _, row in df_f.iterrows()
        if not (pd.isna(row['lat']) or pd.isna(row['lng']))
    ]
    if heat_data:
        HeatMap(
            heat_data, name="Calor", blur=18, radius=14,
            min_opacity=0.35, gradient={0.2: "#3b2f8f", 0.5: "#8f2f8f", 0.8: "#e5484d", 1.0: "#ffd166"},
        ).add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
    
    # Renderizar mapa
    st_folium(m, use_container_width=True, height=550, returned_objects=[])

    # --- INFORMACIÓN DEBAJO DEL MAPA ---
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    
    # Leyenda de Estados
    st.markdown(title_html("Leyenda de Prospección", "pin", 4), unsafe_allow_html=True)
    l_cols = st.columns(len(STATUS_COLORS))
    for i, (name, style) in enumerate(STATUS_COLORS.items()):
        l_cols[i].markdown(
            f"<div style='display:flex; align-items:center; gap:8px;'>"
            f"<div style='width:12px; height:12px; border-radius:50%; background:{style['color']}; border:2px solid #FFFFFF33;'></div>"
            f"<span style='font-size:0.75rem; color:#888898; font-weight:600;'>{name.upper()}</span>"
            f"</div>", 
            unsafe_allow_html=True
        )

    st.divider()
    
    # Métricas Geográficas
    i1, i2, i3, i4 = st.columns(4)
    with i1:
        st.markdown(kpi_card("Leads en Mapa", f"{len(df_f)}", "#E5484D", "Total visibles"), unsafe_allow_html=True)
    with i2:
        z_counts = df_f['zona'].value_counts()
        top_barrio = z_counts.idxmax() if not z_counts.empty else "N/A"
        if "coord:" in str(top_barrio): top_barrio = "Sector GPS"
        st.markdown(kpi_card("Zona Caliente", f"{str(top_barrio)[:12]}", "#A384F0", "Mayor densidad"), unsafe_allow_html=True)
    with i3:
        oro_geos = len(df_f[df_f['calificacion'] == 'oro'])
        st.markdown(kpi_card("Objetivos Oro", f"{oro_geos}", "#F5A524", "Alta prioridad"), unsafe_allow_html=True)
    with i4:
        pct_visible = round((len(df_f) / len(df_map) * 100)) if not df_map.empty else 0
        st.markdown(kpi_card("Cobertura", f"{pct_visible}%", "#5D9DF0", "Del total con coordenadas"), unsafe_allow_html=True)
