import streamlit as st
import pandas as pd
import datetime
import hashlib
import html
import io
import urllib.parse
import zipfile
from db import clean_phone_number, delete_portfolio_batch, update_lead_field
from services.leads import get_wa_link
from services.constants import STATUS_COLORS, get_offer_suggestion
from services.export_utils import safe_spreadsheet_frame
from services.product_campaigns import get_campaign
from ui.icons import title_html

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


def _campaign_values(value) -> set[str]:
    if pd.isna(value):
        return set()
    return {item.strip() for item in str(value).split(",") if item.strip()}


PORTFOLIO_EXPORTS = {
    "divi": {
        "label": "DIVI",
        "prefixes": ("divi_",),
        "filename": "DIVI",
    },
    "watson": {
        "label": "Watson",
        "prefixes": ("watson_",),
        "filename": "WATSON",
    },
    "onyx": {
        "label": "ONYX servicios",
        "prefixes": ("onyx_",),
        "filename": "ONYX_SERVICIOS",
    },
    "unassigned": {
        "label": "Sin clasificar",
        "prefixes": (),
        "filename": "SIN_CLASIFICAR",
    },
}


def _row_campaign_keys(row) -> set[str]:
    """Obtiene campañas modernas y reconoce etiquetas de bases anteriores."""
    keys = _campaign_values(row.get("product_keys"))
    labels = _campaign_values(row.get("productos_objetivo"))
    legacy_keys = set()
    for label in labels:
        normalized = label.casefold()
        if normalized.startswith("divi"):
            legacy_keys.add("divi_legacy")
        elif normalized.startswith("watson"):
            legacy_keys.add("watson_legacy")
        elif normalized.startswith("onyx"):
            legacy_keys.add("onyx_legacy")
    return keys | legacy_keys


def _split_portfolio_batches(df_source):
    """Separa sin eliminar: un lead multioferta puede aparecer en varios lotes."""
    if df_source.empty:
        return {key: df_source.copy() for key in PORTFOLIO_EXPORTS}

    campaign_keys = df_source.apply(_row_campaign_keys, axis=1)
    known_prefixes = tuple(
        prefix
        for key, config in PORTFOLIO_EXPORTS.items()
        if key != "unassigned"
        for prefix in config["prefixes"]
    )
    batches = {}
    for key, config in PORTFOLIO_EXPORTS.items():
        prefixes = config["prefixes"]
        if key == "unassigned":
            mask = campaign_keys.apply(
                lambda values: not any(
                    campaign.startswith(prefix)
                    for campaign in values
                    for prefix in known_prefixes
                )
            )
        else:
            mask = campaign_keys.apply(
                lambda values: any(
                    campaign.startswith(prefix)
                    for campaign in values
                    for prefix in prefixes
                )
            )
        batch = df_source.loc[mask].copy()
        batch["lote_exportado"] = config["label"]
        batches[key] = batch
    return batches


def _identity_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _valid_http_url(value) -> str:
    raw_url = _identity_text(value).removeprefix("'")
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return raw_url
    return ""


def _validate_export_identity(df_source, df_export):
    """Bloquea el archivo si ordenar/transformar separa identidad y contacto."""
    if "id" not in df_source.columns or "Lead ID" not in df_export.columns:
        raise ValueError("La exportación requiere Lead ID para verificar cada fila.")
    if df_source["id"].isna().any() or df_source["id"].duplicated().any():
        raise ValueError("Los Lead ID de origen no son únicos.")
    if df_export["Lead ID"].isna().any() or df_export["Lead ID"].duplicated().any():
        raise ValueError("Los Lead ID exportados no son únicos.")

    expected = df_source.set_index("id", drop=False)
    actual = df_export.set_index("Lead ID", drop=False)
    if set(expected.index) != set(actual.index):
        raise ValueError("El conjunto de Lead ID cambió durante la exportación.")

    field_map = {
        "Empresa": "nombre",
        "Telefono E164": "telefono_e164",
        "Maps": "maps_url",
        "Place ID": "place_id",
    }
    for lead_id in expected.index:
        for exported_field, source_field in field_map.items():
            if _identity_text(actual.at[lead_id, exported_field]) != _identity_text(
                expected.at[lead_id, source_field]
            ):
                raise ValueError(
                    f"La identidad del lead {lead_id} cambió en {exported_field}."
                )


def _crm_table_key(ordered_lead_ids) -> str:
    """La selección de Streamlit se reinicia si cambia el orden de las filas."""
    payload = ",".join(str(int(lead_id)) for lead_id in ordered_lead_ids)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"crm_leads_table_{digest}"

def _flush_pending_notes(lead_id, current_db_notes):
    """Persiste un borrador de notas antes de un st.rerun() para no perderlo."""
    pending = st.session_state.get(f"notes_{lead_id}")
    if pending is None:
        return
    if str(pending) != str(current_db_notes or ""):
        try:
            update_lead_field(lead_id, "notas", pending)
        except Exception:
            pass


def _recommended_action(row):
    if not row["Tiene telefono"]:
        return "Buscar telefono antes de contactar"
    if _has_contact_value(row.get("Producto principal")):
        decision_role = row.get("Decisor objetivo") or "el decisor indicado"
        return f"Contactar a {decision_role} por {row['Producto principal']}"
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
    df_export["Lead ID"] = _safe_column(df, "id")
    df_export["Place ID"] = _safe_column(df, "place_id")
    df_export["Empresa"] = _safe_column(df, "nombre")
    df_export["Ciudad"] = _safe_column(df, "ciudad")
    df_export["Departamento"] = _safe_column(df, "departamento")
    df_export["Pais"] = _safe_column(df, "pais")
    df_export["Nicho"] = _safe_column(df, "nicho")
    df_export["Sector"] = _safe_column(df, "sector")
    df_export["Tipo"] = _safe_column(df, "tipo")
    df_export["Lote exportado"] = _safe_column(df, "lote_exportado")
    df_export["Producto principal"] = _safe_column(df, "producto_principal")
    df_export["Productos objetivo"] = _safe_column(df, "productos_objetivo")
    df_export["Segmento principal"] = _safe_column(df, "segmento_principal")
    df_export["Segmentos objetivo"] = _safe_column(df, "segmentos_objetivo")
    df_export["Afinidad producto"] = _safe_column(df, "fit_score", 0).apply(_parse_int_value)
    df_export["Motivo afinidad"] = _safe_column(df, "motivo_afinidad")
    df_export["Decisor objetivo"] = _safe_column(df, "decisor_objetivo")
    df_export["Pitch sugerido"] = _safe_column(df, "pitch_sugerido")
    df_export["Qué validar en llamada"] = _safe_column(
        df, "campaign_key_principal"
    ).apply(lambda key: get_campaign(key).get("qualification_note", ""))
    df_export["Telefono"] = _safe_column(df, "telefono")
    df_export["Telefono E164"] = _safe_column(df, "telefono_e164")
    df_export["Email"] = _safe_column(df, "email")
    df_export["Sitio web"] = _safe_column(df, "sitio_web")
    df_export["Maps"] = _safe_column(df, "maps_url")
    df_export["Perfil/directorio"] = _safe_column(df, "perfil_url")
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
    df_export["Estado contacto"] = _safe_column(df, "estado_contacto")
    df_export["Fuente"] = _safe_column(df, "fuente")
    df_export["Fuentes encontradas"] = _safe_column(df, "fuentes_encontrado")
    df_export["Fecha captura"] = _safe_column(df, "fecha_captura")
    df_export["Notas"] = _safe_column(df, "notas")
    df_export["Qué venderle"] = df_export.apply(
        lambda row: (
            row["Pitch sugerido"]
            if _has_contact_value(row["Pitch sugerido"])
            else get_offer_suggestion(row["Nicho"], row["Tiene web"])
        ),
        axis=1,
    )

    score = (
        (df_export["Rating"] * 12).clip(upper=60)
        + (df_export["Resenas"] / 10).clip(upper=20)
        + df_export["Tiene telefono"].astype(int) * 10
        + (~df_export["Tiene web"]).astype(int) * 8
        + df_export["Calificacion"].str.lower().map({"oro": 10, "bueno": 5, "frio": 0}).fillna(0)
    ).round(0).clip(upper=100)
    score = score.where(df_export["Afinidad producto"].le(0), df_export["Afinidad producto"])
    df_export.insert(0, "Puntaje oportunidad", score.astype(int))
    df_export.insert(1, "Prioridad", pd.cut(
        score,
        bins=[-1, 59, 79, 100],
        labels=["Baja", "Media", "Alta"]
    ).astype(str))
    df_export.insert(2, "Accion sugerida", df_export.apply(_recommended_action, axis=1))

    df_export = df_export.sort_values(
        by=["Puntaje oportunidad", "Rating", "Resenas"],
        ascending=[False, False, False]
    )
    _validate_export_identity(df, df_export)

    # Limpieza para evitar desfasajes en filas y errores de interpretación numérica en Excel/CSV
    for col in df_export.columns:
        if df_export[col].dtype == 'object':
            df_export[col] = df_export[col].fillna("").astype(str).str.replace(r'[\r\n]+', ' ', regex=True)

    # Normalizar; al escribir XLSX se fuerza tipo texto sin alterar el número.
    if "Telefono" in df_export.columns:
        df_export["Telefono"] = df_export["Telefono"].apply(lambda x: clean_phone_number(x))

    df_export = safe_spreadsheet_frame(df_export)
    return df_export


def _prepare_call_queue(df_export):
    """Crea una cola única de teléfonos válidos conservando el Lead ID ganador."""
    queue = df_export.copy()
    phone_identity = queue["Telefono E164"].map(
        lambda value: _identity_text(value).removeprefix("'")
    )
    contact_state = queue["Estado contacto"].map(_identity_text).str.casefold()
    queue = queue[
        phone_identity.str.startswith("+")
        & phone_identity.str[1:].str.isdigit()
        & contact_state.ne("no_contactar")
    ].assign(_phone_identity=phone_identity)
    queue = queue.drop_duplicates("_phone_identity", keep="first").drop(
        columns=["_phone_identity"]
    )
    columns = [
        "Lead ID", "Place ID", "Lote exportado", "Prioridad",
        "Producto principal", "Segmento principal", "Afinidad producto",
        "Decisor objetivo", "Empresa", "Ciudad", "Nicho", "Telefono",
        "Telefono E164", "Rating", "Resenas", "Qué venderle", "Estado",
        "Estado contacto", "Maps",
    ]
    return queue[columns]

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

    # Los teléfonos se escriben como texto real (sin apóstrofos visibles).
    text_format = workbook.add_format({'num_format': '@'})
    for column in ("Telefono", "Telefono E164"):
        if column not in df.columns:
            continue
        column_index = startcol + df.columns.get_loc(column)
        for row_offset, value in enumerate(df[column], start=1):
            clean = _identity_text(value).removeprefix("'")
            worksheet.write_string(startrow + row_offset, column_index, clean, text_format)

    # Los enlaces se escriben explícitamente en la misma fila del Lead ID.
    link_labels = {
        "Maps": "Abrir Maps",
        "Sitio web": "Abrir sitio",
        "Perfil/directorio": "Abrir perfil",
    }
    url_format = workbook.add_format({'font_color': '#0563C1', 'underline': 1})
    for column, label in link_labels.items():
        if column not in df.columns:
            continue
        column_index = startcol + df.columns.get_loc(column)
        for row_offset, value in enumerate(df[column], start=1):
            raw_url = _valid_http_url(value)
            if not raw_url:
                continue
            try:
                worksheet.write_url(
                    startrow + row_offset,
                    column_index,
                    raw_url,
                    url_format,
                    label,
                )
            except ValueError:
                # URL demasiado larga o inválida: se conserva como texto seguro.
                continue
    worksheet.freeze_panes(startrow + 1, startcol)
    return worksheet

def _set_smart_widths(workbook, worksheet, df, max_width=42):
    wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
    for idx, col in enumerate(df.columns):
        series_len = df[col].astype(str).map(len).max() if not df.empty else 0
        width = min(max(series_len, len(col)) + 2, max_width)
        fmt = wrap_format if col in {
            "Accion sugerida", "Qué venderle", "Notas", "Fuentes encontradas",
            "Motivo afinidad", "Pitch sugerido", "Decisor objetivo",
        } else None
        worksheet.set_column(idx, idx, width, fmt)

def _build_professional_excel(df_filtered):
    output = io.BytesIO()
    df_export = _prepare_excel_export(df_filtered)
    call_queue = _prepare_call_queue(df_export)

    with pd.ExcelWriter(
        output,
        engine='xlsxwriter',
        engine_kwargs={'options': {'strings_to_formulas': False, 'strings_to_urls': False}},
    ) as writer:
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
        summary.write("D7", "Listos para llamar", label_format)
        summary.write("E7", len(call_queue), kpi_format)
        summary.write("A9", "Lectura rapida", section_format)
        summary.write(
            "A10",
            "La hoja Leads prioriza empresas por afinidad con la oferta comercial y, cuando no existe una campaña, "
            "por reputación, reseñas y datos de contacto. Usa los filtros para segmentar por oferta, cliente, "
            "ciudad, nicho, estado o prioridad.",
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
            "Puntaje oportunidad", "Prioridad", "Accion sugerida", "Lead ID", "Place ID",
            "Lote exportado", "Producto principal", "Segmento principal",
            "Afinidad producto", "Decisor objetivo", "Qué venderle", "Empresa",
            "Ciudad", "Nicho", "Telefono", "Telefono E164", "Rating", "Resenas",
            "Tiene web", "Estado", "Maps", "Notas"
        ]
        top_df = df_export[top_cols].head(50)
        top_ws = _write_dataframe_table(writer, top_df, "Top oportunidades", table_style="Table Style Medium 4")
        _set_smart_widths(workbook, top_ws, top_df)
        top_ws.conditional_format(1, 0, max(len(top_df), 1), 0, {
            'type': 'data_bar',
            'bar_color': '#DC2626'
        })

        queue_ws = _write_dataframe_table(
            writer, call_queue, "Lista para llamar",
            table_style="Table Style Medium 4",
        )
        _set_smart_widths(workbook, queue_ws, call_queue)

        segment_rows = []
        for label, column in [
            ("Lote", "Lote exportado"), ("Oferta", "Producto principal"),
            ("Cliente objetivo", "Segmento principal"),
            ("Ciudad", "Ciudad"), ("Nicho", "Nicho"), ("Estado", "Estado"),
            ("Calificacion", "Calificacion"),
        ]:
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


def _build_portfolio_zip(batches, selected_keys, file_format="xlsx", stamp=None):
    """Construye un paquete con un archivo independiente por portafolio."""
    if file_format not in {"xlsx", "csv"}:
        raise ValueError("Formato de lote no soportado.")

    timestamp = stamp or datetime.datetime.now().strftime("%Y%m%d_%H%M")
    output = io.BytesIO()
    files_written = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key in selected_keys:
            if key not in PORTFOLIO_EXPORTS:
                continue
            batch = batches.get(key, pd.DataFrame())
            if batch.empty:
                continue

            source = batch.drop(
                columns=["rating_num", "sugerencia_venta"], errors="ignore"
            )
            file_stem = f"{PORTFOLIO_EXPORTS[key]['filename']}_Leads_{timestamp}"
            if file_format == "xlsx":
                content = _build_professional_excel(source)
                filename = f"{file_stem}.xlsx"
            else:
                exported = _prepare_excel_export(source)
                content = exported.to_csv(index=False, sep=";").encode("utf-8-sig")
                filename = f"{file_stem}.csv"
            archive.writestr(filename, content)
            files_written += 1

    if not files_written:
        raise ValueError("No hay leads en los lotes seleccionados.")
    return output.getvalue()


def _render_export_panel(df_all, df_filtered):
    """Exportación visible y segura: vista actual o archivos separados por portafolio."""
    if st.session_state.pop("_reset_crm_delete_confirmation", False):
        st.session_state.pop("crm_delete_confirmation", None)
    delete_notice = st.session_state.pop("_crm_batch_delete_notice", None)

    with st.expander("Exportar leads", expanded=False):
        if delete_notice:
            st.success(delete_notice)
        st.info(
            "Descargar no elimina ni modifica tus leads. Puedes exportar varias veces."
        )
        export_mode = st.radio(
            "¿Cómo quieres organizar la descarga?",
            ["filtered", "portfolio"],
            format_func=lambda value: {
                "filtered": "Vista filtrada",
                "portfolio": "Lotes por portafolio",
            }[value],
            captions=[
                "Un archivo con los filtros visibles del CRM.",
                "Un ZIP con archivos separados para DIVI, Watson, ONYX y sin clasificar.",
            ],
            horizontal=True,
            key="crm_export_mode",
        )

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        if export_mode == "filtered":
            export_source = df_filtered.drop(
                columns=["rating_num", "sugerencia_venta"], errors="ignore"
            )
            st.markdown(f"**Se exportarán {len(export_source):,} leads.**")
            preview_columns = [
                column for column in (
                    "nombre", "producto_principal", "segmento_principal",
                    "telefono_e164", "ciudad", "estado",
                ) if column in export_source.columns
            ]
            if preview_columns:
                st.dataframe(
                    export_source[preview_columns].head(20),
                    width="stretch", height=220, hide_index=True,
                )

            excel_col, csv_col = st.columns(2)
            if excel_col.button(
                "Preparar Excel", width="stretch", disabled=export_source.empty,
                key="prepare_filtered_excel",
            ):
                try:
                    with st.spinner("Preparando el Excel filtrado..."):
                        report_bytes = _build_professional_excel(export_source)
                except ValueError as export_error:
                    st.error(f"Exportación bloqueada por identidad: {export_error}")
                else:
                    st.download_button(
                        "Descargar Excel filtrado", report_bytes,
                        f"ONYX_Leads_Filtrados_{timestamp}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch", key="download_filtered_excel",
                    )

            if csv_col.button(
                "Preparar CSV", width="stretch", disabled=export_source.empty,
                key="prepare_filtered_csv",
            ):
                try:
                    exported = _prepare_excel_export(export_source)
                except ValueError as export_error:
                    st.error(f"Exportación bloqueada por identidad: {export_error}")
                else:
                    csv_data = exported.to_csv(index=False, sep=";").encode("utf-8-sig")
                    st.download_button(
                        "Descargar CSV filtrado", csv_data,
                        f"ONYX_Leads_Filtrados_{timestamp}.csv", "text/csv",
                        width="stretch", key="download_filtered_csv",
                    )
            return

        scope = st.radio(
            "¿De dónde tomar los lotes?",
            ["all", "filtered"],
            format_func=lambda value: (
                "Toda la base" if value == "all" else "Solo los filtros actuales"
            ),
            horizontal=True,
            key="crm_export_scope",
        )
        batch_source = df_all if scope == "all" else df_filtered
        batches = _split_portfolio_batches(batch_source)
        available = [key for key, frame in batches.items() if not frame.empty]
        selected_batches = st.multiselect(
            "¿Qué lotes quieres incluir?",
            list(PORTFOLIO_EXPORTS),
            default=available,
            format_func=lambda key: (
                f"{PORTFOLIO_EXPORTS[key]['label']} ({len(batches[key]):,})"
            ),
            placeholder="Selecciona uno o más lotes",
            key="crm_export_batches",
        )

        batch_summary = pd.DataFrame([
            {
                "Lote": PORTFOLIO_EXPORTS[key]["label"],
                "Leads": len(batches[key]),
            }
            for key in selected_batches
        ])
        if not batch_summary.empty:
            st.dataframe(batch_summary, width="stretch", hide_index=True)
        if len(batches["unassigned"]):
            st.caption(
                "Los leads sin campaña aparecen en ‘Sin clasificar’; se mantienen "
                "separados para no mezclarlos con DIVI, Watson u ONYX."
            )

        batch_format = st.radio(
            "Formato de los archivos",
            ["xlsx", "csv"],
            format_func=lambda value: "Excel" if value == "xlsx" else "CSV",
            horizontal=True,
            key="crm_export_batch_format",
        )
        if st.button(
            "Preparar paquete por lotes", type="primary", width="stretch",
            disabled=not selected_batches,
            key="prepare_portfolio_zip",
        ):
            try:
                with st.spinner("Creando archivos separados por portafolio..."):
                    package = _build_portfolio_zip(
                        batches, selected_batches, batch_format, timestamp
                    )
            except ValueError as export_error:
                st.error(f"No se pudo preparar el paquete: {export_error}")
            else:
                st.download_button(
                    "Descargar paquete ZIP", package,
                    f"ONYX_Lotes_{timestamp}.zip", "application/zip",
                    width="stretch", key="download_portfolio_zip",
                )

        if not available:
            st.info("No hay leads en este alcance para exportar o borrar por lotes.")
            return

        st.divider()
        with st.container(border=True):
            st.markdown("**Borrar un lote**")
            st.warning(
                "Esta acción es irreversible. Descarga una copia antes de continuar."
            )
            delete_target = st.selectbox(
                "Lote que quieres borrar",
                available,
                format_func=lambda key: (
                    f"{PORTFOLIO_EXPORTS[key]['label']} ({len(batches[key]):,} leads)"
                ),
                key="crm_delete_batch_target",
            )
            delete_label = PORTFOLIO_EXPORTS[delete_target]["label"]
            delete_count = len(batches[delete_target])
            scope_label = (
                "toda la base" if scope == "all" else "los filtros actuales"
            )
            st.markdown(
                f"Se quitarán **{delete_count:,} leads** del lote "
                f"**{delete_label}**, tomando {scope_label}."
            )
            if delete_target != "unassigned":
                st.caption(
                    "Si un lead también pertenece a otro portafolio, su ficha se "
                    "conserva y solo se elimina la asociación con este lote."
                )

            confirmation_phrase = f"BORRAR {delete_label.upper()}"
            confirmation = st.text_input(
                f"Escribe `{confirmation_phrase}` para confirmar",
                placeholder=confirmation_phrase,
                key="crm_delete_confirmation",
            )
            confirmed = confirmation.strip() == confirmation_phrase
            if st.button(
                f"Borrar lote {delete_label}",
                type="primary",
                width="stretch",
                disabled=not confirmed,
                key="delete_portfolio_batch",
            ):
                try:
                    with st.spinner(f"Borrando únicamente el lote {delete_label}..."):
                        deletion = delete_portfolio_batch(
                            batches[delete_target]["id"].tolist(), delete_target
                        )
                except Exception as delete_error:
                    st.error(
                        "No se pudo borrar el lote. La transacción se revirtió y "
                        f"no se aplicó un borrado parcial: {delete_error}"
                    )
                else:
                    if not deletion["matched"]:
                        st.warning(
                            "El lote cambió desde que se cargó la pantalla y no se "
                            "borró ningún lead. Actualiza el CRM e inténtalo de nuevo."
                        )
                    else:
                        notice = (
                            f"Lote {delete_label} borrado: "
                            f"{deletion['matched']:,} leads retirados del lote; "
                            f"{deletion['leads_deleted']:,} fichas eliminadas."
                        )
                        if deletion["leads_preserved"]:
                            notice += (
                                f" {deletion['leads_preserved']:,} fichas se conservaron "
                                "porque pertenecen a otro portafolio."
                            )
                        st.session_state["_crm_batch_delete_notice"] = notice
                        st.session_state["_reset_crm_delete_confirmation"] = True
                        st.rerun()

def render_crm_view(df_all):
    pais_sel = st.session_state.get('pais_sel', 'Colombia')

    # --- FILTROS GLOBALES ---
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([1.5, 1, 1, 1.2])
        search_q = f1.text_input("Buscar por nombre o nicho...", autocomplete="off")
        sel_estado = f2.multiselect(
            "Estado", list(STATUS_COLORS.keys()), placeholder="Todos los estados"
        )
        sel_calif = f3.multiselect(
            "Calificación", ["oro", "bueno", "frio"], placeholder="Todas"
        )
        rating_min = f4.slider("Rating mínimo", 0.0, 5.0, 0.0, 0.1)
        queue_col, dedupe_col = st.columns(2)
        call_queue_only = queue_col.toggle(
            "Solo listos para llamar",
            help="Muestra contactos con teléfono E.164 válido y excluye los marcados como no contactar.",
        )
        hide_dup_phones = dedupe_col.checkbox(
            "Un negocio por número", value=True,
            help="Conserva la sede con mejor reputación cuando varias comparten teléfono.",
        )
        product_col, segment_col = st.columns(2)
        product_options = sorted({
            item
            for value in _safe_column(df_all, "productos_objetivo")
            for item in _campaign_values(value)
        })
        segment_options = sorted({
            item
            for value in _safe_column(df_all, "segmentos_objetivo")
            for item in _campaign_values(value)
        })
        selected_products = product_col.multiselect(
            "Servicio o producto", product_options,
            help="Muestra únicamente prospectos encontrados para estas ofertas.",
            placeholder="Todas las ofertas",
        )
        selected_segments = segment_col.multiselect(
            "Tipo de cliente", segment_options,
            help="Filtra por el destinatario definido al crear la búsqueda.",
            placeholder="Todos los tipos",
        )

    df_f = df_all.copy()

    if selected_products:
        selected_set = set(selected_products)
        df_f = df_f[
            _safe_column(df_f, "productos_objetivo").apply(
                lambda value: bool(_campaign_values(value) & selected_set)
            )
        ]
    if selected_segments:
        selected_set = set(selected_segments)
        df_f = df_f[
            _safe_column(df_f, "segmentos_objetivo").apply(
                lambda value: bool(_campaign_values(value) & selected_set)
            )
        ]

    if call_queue_only:
        phone_identity = _safe_column(df_f, 'telefono_e164').map(
            lambda value: _identity_text(value).removeprefix("'")
        )
        contact_state = _safe_column(df_f, 'estado_contacto').astype(str).str.casefold()
        df_f = df_f[
            phone_identity.str.startswith("+")
            & phone_identity.str[1:].str.isdigit()
            & contact_state.ne('no_contactar')
        ]

    # Deduplicar por teléfono si está activo
    if hide_dup_phones and "telefono" in df_f.columns:
        # Ordenar para quedarnos siempre con la sede principal (la de más reseñas/rating)
        df_f = df_f.sort_values(by=['reseñas', 'rating'], ascending=[False, False])
        phone_identity = (
            df_f['telefono_e164']
            if 'telefono_e164' in df_f.columns
            else df_f['telefono']
        )
        mask_valid = ~phone_identity.isin(["N/A", "", None, "NaN", "nan"]) & phone_identity.notna()

        valid_phones = df_f[mask_valid].assign(_phone_identity=phone_identity[mask_valid]).drop_duplicates(
            subset=['_phone_identity'], keep='first'
        ).drop(columns=['_phone_identity'])
        no_phones = df_f[~mask_valid]

        df_f = pd.concat([valid_phones, no_phones]).sort_index()

    # Aplicar Filtros
    if search_q:
        mask = (df_f['nombre'].str.contains(search_q, case=False, na=False)) | \
               (df_f['nicho'].str.contains(search_q, case=False, na=False)) | \
               (_safe_column(df_f, 'productos_objetivo').str.contains(search_q, case=False, na=False))
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
    if 'tiene_web' in df_f.columns:
        has_web = df_f['tiene_web'].apply(_is_truthy_value)
    elif 'sitio_web' in df_f.columns:
        has_web = df_f['sitio_web'].apply(_has_contact_value)
    else:
        has_web = pd.Series(False, index=df_f.index)
    campaign_pitch = _safe_column(df_f, 'pitch_sugerido')
    df_f['sugerencia_venta'] = [
        pitch if _has_contact_value(pitch) else get_offer_suggestion(niche, website)
        for niche, website, pitch in zip(df_f['nicho'], has_web, campaign_pitch)
    ]
    if rating_min > 0:
        df_f = df_f[df_f['rating_num'] >= rating_min]

    _render_export_panel(df_all, df_f)

    # --- LAYOUT MASTER-DETAIL ---
    c_list, c_detail = st.columns([0.6, 0.4])

    with c_list:
        st.markdown(f"**Prospectos encontrados:** {len(df_f)}")

        if not df_f.empty:
            # Mostramos TODOS los leads en la tabla
            display_columns = [
                'id', 'nombre', 'producto_principal', 'segmento_principal', 'fit_score',
                'nicho', 'ciudad', 'estado', 'calificacion', 'telefono',
                'rating_num', 'sugerencia_venta'
            ]
            df_display = df_f[[
                column for column in display_columns if column in df_f.columns
            ]]
            if call_queue_only:
                df_display = df_display.sort_values(
                    by=['rating_num', 'id'], ascending=[False, False]
                )
            else:
                df_display = df_display.sort_values(by='id', ascending=False)
            df_display = df_display.rename(columns={'rating_num': 'Rating'})
            df_display = df_display.rename(columns={'sugerencia_venta': 'Qué venderle'})
            df_display = df_display.rename(columns={
                'producto_principal': 'Oferta',
                'segmento_principal': 'Cliente objetivo',
                'fit_score': 'Afinidad',
            })
            table_key = _crm_table_key(df_display['id'].tolist())
            previous_table_key = st.session_state.get('_crm_table_widget_key')
            if previous_table_key and previous_table_key != table_key:
                st.session_state.pop(previous_table_key, None)
            st.session_state._crm_table_widget_key = table_key
            table_view = df_display.rename(columns={'id': 'Lead ID'})

            table_event = st.dataframe(
                table_view,
                width='stretch',
                height=560,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=table_key,
                column_config={
                    "Afinidad": st.column_config.ProgressColumn(
                        "Afinidad", min_value=0, max_value=100,
                        format="%d%%",
                    ),
                    "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
                },
            )
            selected_rows = getattr(getattr(table_event, "selection", None), "rows", [])
            if selected_rows:
                selected_id = int(table_view.iloc[selected_rows[0]]['Lead ID'])
                st.session_state.crm_selected_id = selected_id
            elif st.session_state.get("crm_selected_id") in set(df_display['id'].tolist()):
                selected_id = st.session_state.crm_selected_id
            else:
                selected_id = int(df_display.iloc[0]['id'])
                st.session_state.crm_selected_id = selected_id
        else:
            st.info("No hay leads que coincidan con los filtros.")
            selected_id = None

    with c_detail:
        if selected_id:
            lead = df_all[df_all['id'] == selected_id].iloc[0]

            with st.container(border=True):
                estado_lead = str(lead.get('estado', 'Nuevo'))
                estado_tone = {
                    "Nuevo": "blue", "Contactado": "amber", "Interesado": "violet",
                    "Cerrado": "green", "Descartado": "neutral", "Sin WhatsApp": "neutral",
                }.get(estado_lead, "neutral")
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap'>"
                    f"<h3 style='margin:0!important;font-size:1.25rem!important;'>{html.escape(str(lead['nombre']))}</h3>"
                    f"<span class='onyx-chip {estado_tone}'>{html.escape(estado_lead)}</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Lead ID {int(lead['id'])} · {lead['ciudad']} · {lead['nicho']}"
                )
                current_notes_value = lead.get('notes', lead.get('notas', ''))

                # Gestión de Estado y Calificación
                g1, g2 = st.columns(2)
                with g1:
                    new_st = st.selectbox("Estado Actual", list(STATUS_COLORS.keys()),
                                         index=list(STATUS_COLORS.keys()).index(lead['estado']) if lead['estado'] in STATUS_COLORS else 0,
                                         key=f"st_{lead['id']}")
                    if new_st != lead['estado']:
                        _flush_pending_notes(lead['id'], current_notes_value)
                        if update_lead_field(lead['id'], 'estado', new_st):
                            st.toast(f"Estado: {new_st}")
                            st.rerun()

                with g2:
                    califs = ["oro", "bueno", "frio"]
                    new_ca = st.selectbox("Calificación", califs,
                                         index=califs.index(lead['calificacion']) if lead['calificacion'] in califs else 2,
                                         key=f"ca_{lead['id']}")
                    if new_ca != lead['calificacion']:
                        _flush_pending_notes(lead['id'], current_notes_value)
                        if update_lead_field(lead['id'], 'calificacion', new_ca):
                            st.toast(f"Calif: {new_ca}")
                            st.rerun()

                st.divider()

                # Datos de Contacto
                d1, d2 = st.columns(2)
                phone_value = lead.get('telefono')
                phone_display = phone_value if _has_contact_value(phone_value) else "Sin teléfono"
                rating_value = _parse_rating_value(lead.get('rating'))
                rating_display = f"{rating_value:.1f}" if rating_value > 0 else "Sin rating"
                reviews_value = _parse_int_value(lead.get('reseñas'))
                d1.markdown(f"**Teléfono:**\n{phone_display}")
                d2.markdown(f"**Rating:**\n{rating_display} ({reviews_value} reseñas)")

                lead_has_web = (
                    _is_truthy_value(lead.get('tiene_web'))
                    if 'tiene_web' in lead.index
                    else _has_contact_value(lead.get('sitio_web'))
                )
                product_pitch = lead.get('pitch_sugerido')
                if _has_contact_value(lead.get('producto_principal')):
                    fit_val = int(lead.get('fit_score') or 0)
                    fit_tone = "green" if fit_val >= 70 else ("amber" if fit_val >= 40 else "neutral")
                    pitch_html = (
                        f"<div class='campaign-summary' style='margin:12px 0 0'>"
                        f"<p><strong>Oferta:</strong> {html.escape(str(lead.get('producto_principal')))} "
                        f"<span class='onyx-chip {fit_tone}' style='margin-left:6px'>{fit_val}/100 afinidad</span></p>"
                        f"<p><strong>Cliente objetivo:</strong> {html.escape(str(lead.get('segmento_principal') or 'Por validar'))}</p>"
                        f"<p><strong>Argumento de venta:</strong> {html.escape(str(product_pitch))}</p>"
                        + (
                            f"<p><strong>Buscar:</strong> {html.escape(str(lead.get('decisor_objetivo')))} </p>"
                            if _has_contact_value(lead.get('decisor_objetivo')) else ""
                        )
                        + (
                            f"<p><strong>Evidencia:</strong> {html.escape(str(lead.get('motivo_afinidad')))}</p>"
                            if _has_contact_value(lead.get('motivo_afinidad')) else ""
                        )
                        + "</div>"
                    )
                    st.markdown(pitch_html, unsafe_allow_html=True)
                    qualification_note = get_campaign(
                        lead.get('campaign_key_principal')
                    ).get('qualification_note')
                    if qualification_note:
                        st.warning(f"**Qué validar en la llamada:** {qualification_note}")
                else:
                    st.info(
                        f"**Qué venderle:** "
                        f"{get_offer_suggestion(lead['nicho'], lead_has_web)}"
                    )

                suppressed = str(lead.get('estado_contacto', '')).casefold() == 'no_contactar'
                new_suppressed = st.toggle(
                    "No contactar (excluir de todas las campañas)",
                    value=suppressed,
                    key=f"suppress_{lead['id']}",
                )
                if new_suppressed != suppressed:
                    _flush_pending_notes(lead['id'], current_notes_value)
                    if update_lead_field(
                        lead['id'], 'estado_contacto',
                        'no_contactar' if new_suppressed else 'sin_contactar',
                    ):
                        st.rerun()

                maps_url = _valid_http_url(lead.get('maps_url'))
                website_url = _valid_http_url(lead.get('sitio_web'))
                resource_cols = st.columns(2)
                if maps_url:
                    resource_cols[0].link_button(
                        "ABRIR MAPS", maps_url, width="stretch"
                    )
                if website_url:
                    resource_cols[1].link_button(
                        "VISITAR SITIO", website_url, width="stretch"
                    )

                # Redes Sociales
                sc_cols = st.columns(3)
                if lead.get('instagram'): sc_cols[0].link_button("IG", lead['instagram'], width="stretch")
                if lead.get('facebook'): sc_cols[1].link_button("FB", lead['facebook'], width="stretch")
                if lead.get('linkedin_empresa'): sc_cols[2].link_button("LI", lead['linkedin_empresa'], width="stretch")
                if _has_contact_value(lead.get('perfil_url')):
                    st.link_button("Ver perfil/directorio de origen", lead['perfil_url'], width="stretch")

                st.divider()

                # Notas Editables
                new_notes = st.text_area("Notas de Seguimiento", value=current_notes_value if current_notes_value else "",
                                        height=120, key=f"notes_{lead['id']}")
                if st.button("Guardar Notas", width="stretch", key=f"btn_notes_{lead['id']}"):
                    if update_lead_field(lead['id'], 'notas', new_notes):
                        st.success("Notas actualizadas.")
                        st.rerun()

                # Acciones principales para llamada y WhatsApp
                wa_link = get_wa_link(lead, pais_sel)
                dial_source = lead.get('telefono_e164')
                if not _has_contact_value(dial_source):
                    dial_source = lead.get('telefono')
                dial_phone = ''.join(
                    char for char in str(dial_source or '')
                    if char.isdigit() or char == '+'
                )
                action_cols = st.columns(2)
                if suppressed:
                    action_cols[0].button("CONTACTO SUPRIMIDO", disabled=True, width="stretch")
                    action_cols[1].button("WHATSAPP BLOQUEADO", disabled=True, width="stretch")
                else:
                    if dial_phone:
                        action_cols[0].link_button(
                            "LLAMAR AHORA", f"tel:{dial_phone}",
                            type="primary", width="stretch",
                        )
                    else:
                        action_cols[0].button("SIN TELÉFONO VÁLIDO", disabled=True, width="stretch")
                    if wa_link:
                        action_cols[1].link_button(
                            "WHATSAPP", wa_link, width="stretch", type="primary"
                        )
                    else:
                        action_cols[1].button("SIN WHATSAPP", disabled=True, width="stretch")
