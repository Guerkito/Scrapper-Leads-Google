import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import urllib.parse
from db import DB_PATH, update_lead_field
from services.leads import get_wa_link
from services.constants import STATUS_COLORS

def _parse_rating_value(val):
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).split('/')[0].strip().replace(',', '.'))
    except Exception:
        return 0.0

def _parse_int_value(val):
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    return int("".join(filter(str.isdigit, str(val))) or 0)

def _has_contact_value(val):
    if pd.isna(val):
        return False
    clean = str(val).strip()
    return bool(clean and clean.lower() not in {"n/a", "na", "none", "nan", "sin telefono", "sin teléfono"})

def _is_truthy_value(val):
    if pd.isna(val):
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val == 1
    return str(val).strip().lower() in {"1", "true", "si", "sí", "yes", "y"}

def _safe_column(df, column, default=""):
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)

def _recommended_action(row):
    if not row["Tiene telefono"]:
        return "Buscar telefono antes de contactar"
    if not row["Tiene web"] and row["Rating"] >= 4.0:
        return "Ofrecer web, SEO local o presencia digital"
    if row["Tiene web"] and not row["Pixel Meta"] and not row["Pixel Google"]:
        return "Ofrecer pauta digital y medicion"
    if row["Prioridad"] == "Alta":
        return "Contactar por WhatsApp hoy"
    return "Nutrir y validar necesidad"

def _prepare_excel_export(df_source):
    df = df_source.copy()
    df_export = pd.DataFrame(index=df.index)
    df_export["Empresa"] = _safe_column(df, "nombre")
    df_export["Ciudad"] = _safe_column(df, "ciudad")
    df_export["Departamento"] = _safe_column(df, "departamento")
    df_export["Nicho"] = _safe_column(df, "nicho")
    df_export["Sector"] = _safe_column(df, "sector")
    df_export["Tipo"] = _safe_column(df, "tipo")
    df_export["Telefono"] = _safe_column(df, "telefono")
    df_export["Email"] = _safe_column(df, "email")
    df_export["Sitio web"] = _safe_column(df, "sitio_web")
    df_export["Maps"] = _safe_column(df, "maps_url")
    df_export["Rating"] = _safe_column(df, "rating", 0).apply(_parse_rating_value)
    df_export["Resenas"] = _safe_column(df, "reseñas", 0).apply(_parse_int_value)
    df_export["Tiene web"] = _safe_column(df, "tiene_web", False).apply(_is_truthy_value)
    df_export["Tiene telefono"] = df_export["Telefono"].apply(_has_contact_value)
    df_export["Instagram"] = _safe_column(df, "instagram")
    df_export["Facebook"] = _safe_column(df, "facebook")
    df_export["LinkedIn"] = _safe_column(df, "linkedin_empresa")
    df_export["Pixel Meta"] = _safe_column(df, "pixel_fb", False).apply(_is_truthy_value)
    df_export["Pixel Google"] = _safe_column(df, "pixel_google", False).apply(_is_truthy_value)
    df_export["NIT"] = _safe_column(df, "nit")
    df_export["Representante legal"] = _safe_column(df, "representante_legal")
    df_export["Calificacion"] = _safe_column(df, "calificacion")
    df_export["Estado"] = _safe_column(df, "estado")
    df_export["Fuente"] = _safe_column(df, "fuente")
    df_export["Fuentes encontradas"] = _safe_column(df, "fuentes_encontrado")
    df_export["Fecha captura"] = _safe_column(df, "fecha_captura")
    df_export["Notas"] = _safe_column(df, "notas")

    score = (
        (df_export["Rating"] * 12).clip(upper=60)
        + (df_export["Resenas"] / 10).clip(upper=20)
        + df_export["Tiene telefono"].astype(int) * 10
        + (~df_export["Tiene web"]).astype(int) * 8
        + df_export["Calificacion"].str.lower().map({"oro": 10, "bueno": 5, "frio": 0}).fillna(0)
    ).round(0).clip(upper=100)
    df_export.insert(0, "Puntaje oportunidad", score.astype(int))
    df_export.insert(1, "Prioridad", pd.cut(
        score,
        bins=[-1, 59, 79, 100],
        labels=["Baja", "Media", "Alta"]
    ).astype(str))
    df_export.insert(2, "Accion sugerida", df_export.apply(_recommended_action, axis=1))

    return df_export.sort_values(
        by=["Puntaje oportunidad", "Rating", "Resenas"],
        ascending=[False, False, False]
    )

def _write_dataframe_table(writer, df, sheet_name, startrow=0, startcol=0, table_style="Table Style Medium 2"):
    df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=startrow, startcol=startcol)
    worksheet = writer.sheets[sheet_name]
    workbook = writer.book
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'middle',
        'fg_color': '#111827',
        'font_color': '#FFFFFF',
        'border': 1
    })
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(startrow, startcol + col_num, value, header_format)
    if not df.empty:
        worksheet.add_table(
            startrow,
            startcol,
            startrow + len(df),
            startcol + len(df.columns) - 1,
            {
                'columns': [{'header': col} for col in df.columns],
                'style': table_style,
                'autofilter': True
            }
        )
    worksheet.freeze_panes(startrow + 1, startcol)
    return worksheet

def _set_smart_widths(workbook, worksheet, df, max_width=42):
    wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
    for idx, col in enumerate(df.columns):
        series_len = df[col].astype(str).map(len).max() if not df.empty else 0
        width = min(max(series_len, len(col)) + 2, max_width)
        fmt = wrap_format if col in {"Accion sugerida", "Notas", "Fuentes encontradas"} else None
        worksheet.set_column(idx, idx, width, fmt)

def _build_professional_excel(df_filtered):
    output = io.BytesIO()
    df_export = _prepare_excel_export(df_filtered)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        title_format = workbook.add_format({'bold': True, 'font_size': 18, 'font_color': '#111827'})
        section_format = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': '#FFFFFF', 'fg_color': '#DC2626'})
        label_format = workbook.add_format({'bold': True, 'font_color': '#374151'})
        kpi_format = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#DC2626', 'num_format': '#,##0'})
        pct_format = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#DC2626', 'num_format': '0%'})
        note_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_color': '#4B5563'})

        total = len(df_export)
        high_priority = int((df_export["Prioridad"] == "Alta").sum()) if total else 0
        with_phone = int(df_export["Tiene telefono"].sum()) if total else 0
        no_web = int((~df_export["Tiene web"]).sum()) if total else 0
        avg_rating = float(df_export["Rating"].mean()) if total else 0

        summary = workbook.add_worksheet("Resumen")
        writer.sheets["Resumen"] = summary
        summary.hide_gridlines(2)
        summary.write("A1", "Resumen ejecutivo de leads", title_format)
        summary.write("A3", "Total empresas", label_format)
        summary.write("B3", total, kpi_format)
        summary.write("D3", "Prioridad alta", label_format)
        summary.write("E3", high_priority, kpi_format)
        summary.write("A5", "Con telefono", label_format)
        summary.write("B5", with_phone / total if total else 0, pct_format)
        summary.write("D5", "Sin sitio web", label_format)
        summary.write("E5", no_web / total if total else 0, pct_format)
        summary.write("A7", "Rating promedio", label_format)
        summary.write("B7", avg_rating, workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#DC2626', 'num_format': '0.00'}))
        summary.write("A9", "Lectura rapida", section_format)
        summary.write(
            "A10",
            "La hoja Leads prioriza empresas por reputacion, resenas, datos de contacto, ausencia de web y calificacion CRM. "
            "Usa los filtros para segmentar por ciudad, nicho, estado, prioridad o accion sugerida.",
            note_format
        )
        summary.set_column("A:A", 24)
        summary.set_column("B:B", 16)
        summary.set_column("D:D", 22)
        summary.set_column("E:E", 16)
        summary.set_row(9, 54)

        leads_ws = _write_dataframe_table(writer, df_export, "Leads")
        _set_smart_widths(workbook, leads_ws, df_export)
        leads_ws.set_column(0, 0, 13)
        leads_ws.set_column(1, 1, 11)
        leads_ws.set_column(2, 2, 34)
        leads_ws.conditional_format(1, 0, max(len(df_export), 1), 0, {
            'type': '3_color_scale',
            'min_color': '#FCA5A5',
            'mid_color': '#FDE68A',
            'max_color': '#86EFAC'
        })
        priority_col = df_export.columns.get_loc("Prioridad")
        for label, color in {"Alta": "#DCFCE7", "Media": "#FEF3C7", "Baja": "#FEE2E2"}.items():
            leads_ws.conditional_format(1, priority_col, max(len(df_export), 1), priority_col, {
                'type': 'text',
                'criteria': 'containing',
                'value': label,
                'format': workbook.add_format({'bg_color': color, 'font_color': '#111827'})
            })

        top_cols = [
            "Puntaje oportunidad", "Prioridad", "Accion sugerida", "Empresa", "Ciudad",
            "Nicho", "Telefono", "Rating", "Resenas", "Tiene web", "Estado", "Notas"
        ]
        top_df = df_export[top_cols].head(50)
        top_ws = _write_dataframe_table(writer, top_df, "Top oportunidades", table_style="Table Style Medium 4")
        _set_smart_widths(workbook, top_ws, top_df)
        top_ws.conditional_format(1, 0, max(len(top_df), 1), 0, {
            'type': 'data_bar',
            'bar_color': '#DC2626'
        })

        segment_rows = []
        for label, column in [("Ciudad", "Ciudad"), ("Nicho", "Nicho"), ("Estado", "Estado"), ("Calificacion", "Calificacion")]:
            if column not in df_export.columns:
                continue
            grouped = df_export.groupby(column, dropna=False).agg(
                Empresas=("Empresa", "count"),
                Puntaje_promedio=("Puntaje oportunidad", "mean"),
                Rating_promedio=("Rating", "mean"),
                Con_telefono=("Tiene telefono", "sum"),
                Sin_web=("Tiene web", lambda s: int((~s).sum())),
                Prioridad_alta=("Prioridad", lambda s: int((s == "Alta").sum()))
            ).reset_index().rename(columns={column: "Segmento"})
            grouped.insert(0, "Vista", label)
            segment_rows.append(grouped.sort_values("Empresas", ascending=False).head(20))

        segments_df = pd.concat(segment_rows, ignore_index=True) if segment_rows else pd.DataFrame()
        if not segments_df.empty:
            segments_df["Puntaje_promedio"] = segments_df["Puntaje_promedio"].round(1)
            segments_df["Rating_promedio"] = segments_df["Rating_promedio"].round(2)
        seg_ws = _write_dataframe_table(writer, segments_df, "Segmentos", table_style="Table Style Medium 9")
        _set_smart_widths(workbook, seg_ws, segments_df)

        if not df_export.empty:
            chart_data = df_export["Nicho"].replace("", "Sin nicho").value_counts().head(10).reset_index()
            chart_data.columns = ["Nicho", "Empresas"]
            chart_data.to_excel(writer, index=False, sheet_name="Datos graficos")
            data_ws = writer.sheets["Datos graficos"]
            data_ws.hide()
            chart = workbook.add_chart({'type': 'bar'})
            chart.add_series({
                'name': 'Empresas por nicho',
                'categories': ['Datos graficos', 1, 0, len(chart_data), 0],
                'values': ['Datos graficos', 1, 1, len(chart_data), 1],
                'fill': {'color': '#DC2626'}
            })
            chart.set_title({'name': 'Top nichos'})
            chart.set_x_axis({'name': 'Empresas'})
            chart.set_legend({'none': True})
            summary.insert_chart("A13", chart, {'x_scale': 1.25, 'y_scale': 1.1})

    return output.getvalue()

def render_crm_view(df_all):
    st.markdown("### 🏢 Centro de Gestión de Leads (Onyx CRM)")
    pais_sel = st.session_state.get('pais_sel', 'Colombia')

    # --- FILTROS GLOBALES ---
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([1.5, 1, 1, 1.2])
        search_q = f1.text_input("🔍 Buscar por nombre o nicho...", autocomplete="off")
        sel_estado = f2.multiselect("Estado", list(STATUS_COLORS.keys()))
        sel_calif = f3.multiselect("Calificación", ["oro", "bueno", "frio"])
        rating_min = f4.slider("⭐ Rating mín", 0.0, 5.0, 0.0, 0.1)

    df_f = df_all.copy()

    # Aplicar Filtros
    if search_q:
        mask = (df_f['nombre'].str.contains(search_q, case=False, na=False)) | \
               (df_f['nicho'].str.contains(search_q, case=False, na=False))
        df_f = df_f[mask]
    if sel_estado: df_f = df_f[df_f['estado'].isin(sel_estado)]
    if sel_calif:  df_f = df_f[df_f['calificacion'].isin(sel_calif)]

    def parse_rating_f(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        if isinstance(val, str):
            try: return float(val.split('/')[0].strip().replace(',', '.'))
            except: return 0.0
        return 0.0

    df_f['rating_num'] = df_f['rating'].apply(parse_rating_f)
    if rating_min > 0:
        df_f = df_f[df_f['rating_num'] >= rating_min]

    # --- LAYOUT MASTER-DETAIL ---
    c_list, c_detail = st.columns([0.6, 0.4])

    with c_list:
        st.markdown(f"**Prospectos encontrados:** {len(df_f)}")

        if not df_f.empty:
            # Mostramos TODOS los leads en la tabla
            df_display = df_f[['id', 'nombre', 'ciudad', 'estado', 'calificacion', 'telefono']].sort_values(by='id', ascending=False)

            # Selector para el detalle
            lead_options = {f"{r['nombre']} ({r['ciudad']})": r['id'] for _, r in df_display.iterrows()}
            selected_label = st.selectbox("Selecciona un prospecto para gestionar:", list(lead_options.keys()), label_visibility="collapsed")
            selected_id = lead_options[selected_label]

            st.dataframe(
                df_display.drop(columns=['id']),
                width='stretch',
                height=550,
                hide_index=True
            )
        else:
            st.info("No hay leads que coincidan con los filtros.")
            selected_id = None

    with c_detail:
        if selected_id:
            lead = df_all[df_all['id'] == selected_id].iloc[0]

            with st.container(border=True):
                st.markdown(f"### 💎 {lead['nombre']}")
                st.markdown(f"<p style='color:#6A6A7A;'>{lead['ciudad']} · {lead['nicho']}</p>", unsafe_allow_html=True)

                # Gestión de Estado y Calificación
                g1, g2 = st.columns(2)
                with g1:
                    new_st = st.selectbox("Estado Actual", list(STATUS_COLORS.keys()),
                                         index=list(STATUS_COLORS.keys()).index(lead['estado']) if lead['estado'] in STATUS_COLORS else 0,
                                         key=f"st_{lead['id']}")
                    if new_st != lead['estado']:
                        if update_lead_field(lead['id'], 'estado', new_st):
                            st.toast(f"Estado: {new_st}")
                            st.rerun()

                with g2:
                    califs = ["oro", "bueno", "frio"]
                    new_ca = st.selectbox("Calificación", califs,
                                         index=califs.index(lead['calificacion']) if lead['calificacion'] in califs else 2,
                                         key=f"ca_{lead['id']}")
                    if new_ca != lead['calificacion']:
                        if update_lead_field(lead['id'], 'calificacion', new_ca):
                            st.toast(f"Calif: {new_ca}")
                            st.rerun()

                st.divider()

                # Datos de Contacto
                d1, d2 = st.columns(2)
                d1.markdown(f"**📞 Teléfono:**\n{lead['telefono']}")
                d2.markdown(f"**⭐ Rating:**\n{lead['rating']} ({lead['reseñas']} res)")

                if lead.get('sitio_web'):
                    st.link_button("🌐 Visitar Sitio Web", lead['sitio_web'], use_container_width=True)

                # Redes Sociales
                sc_cols = st.columns(3)
                if lead.get('instagram'): sc_cols[0].link_button("📸 IG", lead['instagram'], use_container_width=True)
                if lead.get('facebook'): sc_cols[1].link_button("📘 FB", lead['facebook'], use_container_width=True)
                if lead.get('linkedin_empresa'): sc_cols[2].link_button("💼 LI", lead['linkedin_empresa'], use_container_width=True)

                st.divider()

                # Notas Editables
                current_notes = lead.get('notes', lead.get('notas', ''))
                new_notes = st.text_area("📝 Notas de Seguimiento", value=current_notes if current_notes else "",
                                        height=120, key=f"notes_{lead['id']}")
                if st.button("Guardar Notas", use_container_width=True, key=f"btn_notes_{lead['id']}"):
                    if update_lead_field(lead['id'], 'notas', new_notes):
                        st.success("Notas actualizadas.")
                        st.rerun()

                # Acción Principal
                wa_link = get_wa_link(lead, pais_sel)
                if wa_link:
                    st.link_button("📲 CONTACTAR POR WHATSAPP", wa_link, type="primary", use_container_width=True)
                else:
                    st.button("📲 SIN TELÉFONO VÁLIDO", disabled=True, use_container_width=True)

    # Panel de Exportación Pro
    with st.expander("📤 HERRAMIENTAS DE EXPORTACIÓN Y FILTROS AVANZADOS"):
        st.markdown("**Previsualización de los datos filtrados:**")
        st.dataframe(df_f, width='stretch', height=300)

        c_ex1, c_ex2 = st.columns(2)
        if c_ex1.button("📊 Generar Reporte Excel (.xlsx)", use_container_width=True):
            report_bytes = _build_professional_excel(df_f.drop(columns=['rating_num'], errors='ignore'))

            st.download_button(
                "📥 Descargar Reporte Profesional",
                report_bytes,
                f"ONYX_Leads_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        if c_ex2.button("📄 Generar CSV de Contactos", use_container_width=True):
            st.download_button("📥 Descargar CSV", df_f.to_csv(index=False), "leads_contactos.csv", "text/csv", use_container_width=True)
