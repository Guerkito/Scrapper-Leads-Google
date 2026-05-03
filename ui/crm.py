import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import urllib.parse
from db import DB_PATH
from services.leads import get_wa_link
from services.constants import STATUS_COLORS

def render_crm_view(df_all):
    st.markdown("### 🏢 Centro de Gestión de Leads (Master-Detail)")
    pais_sel = st.session_state.get('pais_sel', 'Colombia')
    
    # Panel de Exportación Pro
    with st.expander("📤 EXPORTACIÓN PRO (SaaS Level)", expanded=False):
        with st.container(border=True):
            e1, e2, e3 = st.columns([1.5, 1, 1])
            export_status = e1.multiselect("Filtrar por Estado para Exportar", list(STATUS_COLORS.keys()), default=["Interesado", "Cerrado"])
            export_min_rating = e2.slider("Rating mín para CSV", 0.0, 5.0, 3.5)

            df_export = df_all.copy()
            if export_status:
                df_export = df_export[df_export['estado'].isin(export_status)]
            
            def parse_rating(val):
                if pd.isna(val): return 0.0
                if isinstance(val, (int, float)): return float(val)
                if isinstance(val, str):
                    try:
                        return float(val.split('/')[0].strip().replace(',', '.'))
                    except (ValueError, IndexError):
                        return 0.0
                return 0.0

            df_export['rating_num'] = df_export['rating'].apply(parse_rating)
            df_export = df_export[df_export['rating_num'] >= export_min_rating]

            st.markdown(f"**Previsualización de Exportación:** {len(df_export)} leads seleccionados.")

            cols_pro = [
                'nombre', 'nit', 'telefono', 'ciudad', 'direccion', 'sitio_web', 
                'email', 'instagram', 'facebook', 'linkedin_empresa', 
                'decisor', 'rating', 'verificado', 'fecha_captura'
            ]
            for c in cols_pro:
                if c not in df_export.columns: df_export[c] = None

            df_final_export = df_export[cols_pro].copy()
            df_final_export.columns = [
                'Razón Social', 'NIT', 'Teléfono', 'Ciudad', 'Dirección', 'Sitio Web',
                'Email Corporativo', 'Instagram', 'Facebook', 'LinkedIn',
                'Decisor / Representante', 'Rating', 'WA Verificado', 'Fecha Captura'
            ]

            df_final_export['Exportado por'] = "Onyx Lead Gen Pro"
            df_final_export['Fecha Exportación'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            st.dataframe(df_final_export.head(10), width="stretch")

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final_export.to_excel(writer, index=False, sheet_name='Leads Onyx')
                workbook  = writer.book
                worksheet = writer.sheets['Leads Onyx']
                header_format = workbook.add_format({
                    'bold': True, 'text_wrap': True, 'valign': 'top',
                    'fg_color': '#D7E4BC', 'border': 1
                })
                for col_num, value in enumerate(df_final_export.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    worksheet.set_column(col_num, col_num, 20)

            excel_data = output.getvalue()
            st.download_button(
                label="📥 DESCARGAR PAQUETE DE LEADS (EXCEL .xlsx)",
                data=excel_data,
                file_name=f'onyx_leads_pro_{datetime.datetime.now().strftime("%Y%m%d")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary",
                width="stretch"
            )

    # Filtros de Visualización
    with st.expander("🔍 Filtros de Visualización"):
        f1, f2, f3 = st.columns(3)
        sel_fuente = f1.multiselect("Fuente", df_all['fuente'].unique()) if 'fuente' in df_all.columns else []
        sel_calif = f2.multiselect("Calificación", ["oro", "bueno", "frio"])
        search_q = f3.text_input("Buscar por nombre...", autocomplete="off")
        
        f4, f5 = st.columns(2)
        rating_min = f4.slider("⭐ Rating mínimo", 0.0, 5.0, 0.0, 0.1)
        no_website = f5.toggle("🚫 Sin sitio web (Leads Oro)", value=False)
    
    df_f = df_all.copy()
    if sel_fuente: df_f = df_f[df_f['fuente'].isin(sel_fuente)]
    if sel_calif:  df_f = df_f[df_f['calificacion'].isin(sel_calif)]
    if search_q:   df_f = df_f[df_f['nombre'].str.contains(search_q, case=False, na=False)]
    
    if rating_min > 0:
        def parse_rating_f(val):
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val)
            if isinstance(val, str):
                try:
                    return float(val.split('/')[0].strip().replace(',', '.'))
                except (ValueError, IndexError):
                    return 0.0
            return 0.0
        df_f['rating_num'] = df_f['rating'].apply(parse_rating_f)
        df_f = df_f[df_f['rating_num'] >= rating_min]
    
    if no_website:
        df_f = df_f[(df_f['sitio_web'].isna()) | (df_f['sitio_web'] == "") | (df_f['sitio_web'] == "N/A")]

    c_list, c_detail = st.columns([0.55, 0.45])
    
    with c_list:
        st.markdown("<p style='font-size:0.8rem; color:#6A6A7A;'>Selecciona un lead para ver detalles</p>", unsafe_allow_html=True)
        if not df_f.empty:
            lead_names = df_f.sort_values(by='id', ascending=False)['nombre'].tolist()
            selected_name = st.selectbox("Seleccionar Prospecto", lead_names, label_visibility="collapsed")
            selected_lead = df_f[df_f['nombre'] == selected_name].iloc[0]
            st.dataframe(df_f[['nombre', 'telefono', 'calificacion', 'fuente']].head(20), width="stretch")
        else:
            st.info("No hay leads que coincidan con los filtros.")
            selected_lead = None
        
    with c_detail:
        if selected_lead is not None:
            with st.container(border=True):
                st.markdown(f"### 💎 {selected_lead['nombre']}")
            
            calif_val = selected_lead['calificacion'] if selected_lead['calificacion'] else "frio"
            color = "#F5C518" if calif_val == "oro" else "#4ADE80" if calif_val == "bueno" else "#6A6A7A"
            st.markdown(f"<span style='background:{color}; color:black; padding:4px 12px; border-radius:20px; font-weight:bold; box-shadow:0 0 10px {color};'>{calif_val.upper()}</span>", unsafe_allow_html=True)
            
            st.divider()
            d1, d2 = st.columns(2)
            d1.markdown(f"**📞 Teléfono:**\n{selected_lead['telefono']}")
            d2.markdown(f"**🏢 Sector:**\n{selected_lead.get('sector', 'N/A')}")
            
            st.markdown(f"**📍 Ubicación:** {selected_lead['ciudad']}")
            if selected_lead.get('nit'):
                st.markdown(f"**🆔 NIT:** {selected_lead['nit']}")
            
            st.markdown("---")
            st.markdown("**🌐 Presencia Digital y Tech**")
            
            social_cols = st.columns(3)
            if selected_lead.get('instagram'):
                social_cols[0].link_button("📸 Instagram", selected_lead['instagram'], width="stretch")
            if selected_lead.get('facebook'):
                social_cols[1].link_button("📘 Facebook", selected_lead['facebook'], width="stretch")
            if selected_lead.get('linkedin_empresa'):
                social_cols[2].link_button("💼 LinkedIn", selected_lead['linkedin_empresa'], width="stretch")
            
            pix_fb = "✅ Píxel FB" if selected_lead.get('pixel_fb') else "❌ Sin Píxel FB"
            pix_gg = "✅ Píxel Google" if selected_lead.get('pixel_google') else "❌ Sin Píxel Google"
            p1, p2 = st.columns(2)
            p1.caption(pix_fb)
            p2.caption(pix_gg)

            if selected_lead['sitio_web']:
                st.link_button("🌐 Visitar Sitio Web", selected_lead['sitio_web'], width="stretch")
            
            st.divider()
            st.markdown("**📝 Notas y Seguimiento**")
            # En una aplicación real, esto requeriría guardar en DB
            st.text_area("Notas del lead", value=selected_lead.get('notas', ''), key=f"notes_{selected_lead['id']}", height=80)
            
            wa_link = get_wa_link(selected_lead, pais_sel)
            if wa_link:
                st.link_button("📲 Ir al Chat de WhatsApp", wa_link, type="primary", width="stretch")
            else:
                st.button("📲 Sin Teléfono Válido", disabled=True, width="stretch")
