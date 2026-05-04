import streamlit as st
import pandas as pd
import altair as alt

def _kpi_card(label, value, accent_color="#FF0000", subtext=None):
    sub_html = f"<div style='font-size:0.75rem; color:#888898; margin-top:8px; font-weight:400;'>{subtext}</div>" if subtext else ""
    return (
        f"<div class='onyx-card onyx-animate' style='padding: 24px; margin-bottom: 0; border-top: 4px solid {accent_color}; height: 100%;'>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:0.75rem; "
        f"  font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#888898;'>"
        f"  {label}</div>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:2.4rem; "
        f"  font-weight:700; color:#FFFFFF; margin-top:8px; line-height:1;'>"
        f"  {value}</div>"
        f"  {sub_html}"
        f"</div>"
    )

def render_analytics_view(df_all):
    st.markdown("### 📊 Inteligencia de Mercado y Métricas Pro")

    if df_all.empty:
        st.info("No hay datos suficientes para generar analíticas. Inicia una misión de prospección.")
        return

    # Limpieza de datos rápida para métricas precisas
    df = df_all.copy()
    def _p_rat(x):
        try: return float(str(x).split('/')[0].strip()) if x else 0
        except: return 0
    df['rating_num'] = df['rating'].apply(_p_rat)
    df['reseñas_num'] = pd.to_numeric(df['reseñas'], errors='coerce').fillna(0)

    # --- MÉTRICAS ESTRATÉGICAS ---
    m1, m2, m3, m4 = st.columns(4)
    total_leads = len(df)
    oro_leads = len(df[df['calificacion'] == 'oro'])
    # Nueva métrica: Oportunidad SEO/Web (Rating >= 4.0 y Sin Web)
    seo_opps = len(df[(df['tiene_web'] == False) & (df['rating_num'] >= 4.0)])
    # Métrica de Calidad: % con teléfono
    has_tel_pct = (df['telefono'].replace('N/A', None).notna().sum() / total_leads * 100) if total_leads else 0

    with m1:
        st.markdown(_kpi_card("Total Leads", f"{total_leads:,}", "#FF0000", "En base de datos"), unsafe_allow_html=True)
    with m2:
        st.markdown(_kpi_card("Leads Oro", f"{oro_leads:,}", "#F5C518", f"{round(oro_leads/total_leads*100) if total_leads else 0}% del total"), unsafe_allow_html=True)
    with m3:
        st.markdown(_kpi_card("Oportunidad SEO", f"{seo_opps:,}", "#4ADE80", "Rating > 4.0 sin web"), unsafe_allow_html=True)
    with m4:
        st.markdown(_kpi_card("Salud de Datos", f"{round(has_tel_pct)}%", "#FFFFFF", "Con contacto válido"), unsafe_allow_html=True)

    st.divider()

    # --- FILA 1: ESTADO Y ADOPCIÓN ---
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("#### 📈 Embudo de Prospección")
        if not df['estado'].dropna().empty:
            status_counts = df['estado'].value_counts().reset_index()
            status_counts.columns = ['Estado', 'Cantidad']
            chart_funnel = alt.Chart(status_counts).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field="Cantidad", type="quantitative"),
                color=alt.Color(field="Estado", type="nominal", scale=alt.Scale(range=['#FF0000', '#6EB4C9', '#A06EC9', '#4ADE80', '#555568'])),
                tooltip=['Estado', 'Cantidad']
            ).properties(height=300)
            st.altair_chart(chart_funnel, use_container_width=True)
        else:
            st.caption("Sin datos de estado disponibles.")

    with g2:
        st.markdown("#### 💻 Madurez Digital")
        tech_stats = {
            'Con Web': len(df[df['tiene_web'] == True]),
            'Sin Web': len(df[df['tiene_web'] == False]),
            'Píxel FB': len(df[df['pixel_fb'] == True]),
            'Píxel Google': len(df[df['pixel_google'] == True]),
        }
        tech_df = pd.DataFrame(list(tech_stats.items()), columns=['Métrica', 'Cantidad'])
        if not tech_df.empty and tech_df['Cantidad'].sum() > 0:
            chart_tech = alt.Chart(tech_df).mark_bar(color='#FF0000', cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X('Métrica:N', sort=None, title=None),
                y=alt.Y('Cantidad:Q', title=None),
                tooltip=['Métrica', 'Cantidad']
            ).properties(height=300)
            st.altair_chart(chart_tech, use_container_width=True)
        else:
            st.caption("Esperando datos tecnológicos...")

    # --- FILA 2: SECTORES Y CIUDADES ---
    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🏗️ Top 10 Sectores Dominantes")
        if not df['nicho'].dropna().empty:
            nicho_counts = df['nicho'].value_counts().head(10).reset_index()
            nicho_counts.columns = ['Nicho', 'Cantidad']
            chart_nicho = alt.Chart(nicho_counts).mark_bar(color='#6EB4C9', cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                x=alt.X('Cantidad:Q', title=None),
                y=alt.Y('Nicho:N', sort='-x', title=None),
                tooltip=['Nicho', 'Cantidad']
            ).properties(height=350)
            st.altair_chart(chart_nicho, use_container_width=True)
        else:
            st.caption("No hay datos de sectores.")

    with c2:
        st.markdown("#### 📍 Concentración Geográfica")
        if not df['ciudad'].dropna().empty:
            city_counts = df['ciudad'].value_counts().head(10).reset_index()
            city_counts.columns = ['Ciudad', 'Cantidad']
            chart_city = alt.Chart(city_counts).mark_bar(color='#A06EC9', cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X('Ciudad:N', sort='-y', title=None),
                y=alt.Y('Cantidad:Q', title=None),
                tooltip=['Ciudad', 'Cantidad']
            ).properties(height=350)
            st.altair_chart(chart_city, use_container_width=True)
        else:
            st.caption("No hay datos geográficos.")

    # --- FILA 3: MATRIZ DE REPUTACIÓN ---
    st.divider()
    st.markdown("#### 💎 Matriz de Oportunidad (Reputación vs Tamaño)")
    st.caption("Los puntos arriba a la derecha representan negocios consolidados. Los puntos grandes sin web son tus mejores prospectos.")
    
    # Filtramos ceros para una mejor visualización logarítmica/dispersa
    df_gem = df[df['reseñas_num'] > 0].copy()
    
    if not df_gem.empty:
        chart_gems = alt.Chart(df_gem).mark_circle(size=100, opacity=0.6).encode(
            x=alt.X('reseñas_num:Q', title="Número de Reseñas", scale=alt.Scale(type='symlog')),
            y=alt.Y('rating_num:Q', title="Rating (Estrellas)", scale=alt.Scale(domain=[1, 5])),
            color=alt.Color('tiene_web:N', title="¿Tiene Web?", scale=alt.Scale(range=['#FF0000', '#4ADE80'])),
            size=alt.Size('rating_num:Q', legend=None),
            tooltip=['nombre', 'nicho', 'rating', 'reseñas', 'ciudad']
        ).properties(height=400).interactive()
        
        st.altair_chart(chart_gems, use_container_width=True)
    else:
        st.info("No hay suficientes datos de reputación (reseñas) para generar esta matriz.")
