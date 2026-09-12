import json
import re
import sqlite3

import pandas as pd
import streamlit as st

from db import DB_PATH, open_conn
from services.leads import load_all_leads, invalidate_leads_cache
from ui.analytics import render_analytics_view
from ui.crm import render_crm_view
from ui.email import render_email_view
from ui.helpers import kpi_card, empty_state
from ui.icons import title_html
from ui.map import render_map_view
from ui.whatsapp import render_whatsapp_view


def _norm(word):
    word = word.lower()
    for acc, plain in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ü', 'u'), ('ñ', 'n')]:
        word = word.replace(acc, plain)
    return word


def _roots(text):
    """Raíces (sin plural) de cada palabra: 'Clínicas Médicas' -> {'clinic', 'medic'}."""
    roots = set()
    for w in re.findall(r"[a-zñáéíóúü]+", _norm(text)):
        w = re.sub(r"(es|s)$", "", w)
        if len(w) > 2:
            roots.add(w)
    return roots


def _mask_search(df_all, row):
    """Leads que pertenecen a una búsqueda guardada: país + ciudades + nicho.

    El nicho del lead se guarda en singular/minúscula ('clínica médica') mientras
    la búsqueda usa el catálogo ('Clínicas Médicas'): se compara por raíz de
    palabras, exigiendo 2 raíces compartidas cuando el término tiene varias.
    """
    mask = df_all['pais'].fillna('').astype(str).str.strip() == str(row.get('pais') or '').strip()
    try:
        cities = json.loads(row.get('ciudades') or '[]')
        city_names = {
            str(c.get('ciudad', '')).strip()
            for c in cities if isinstance(c, dict) and c.get('ciudad')
        }
    except (TypeError, json.JSONDecodeError):
        city_names = set()
    if city_names:
        mask &= df_all['ciudad'].fillna('').astype(str).str.strip().isin(city_names)
    tags = [t.strip() for t in str(row.get('nicho') or '').split(',') if t.strip()]
    if tags:
        tag_roots = set().union(*[_roots(t) for t in tags]) if tags else set()
        min_shared = min(2, len(tag_roots))
        mask &= df_all['nicho'].fillna('').astype(str).apply(
            lambda n: len(_roots(n) & tag_roots) >= min_shared
        )
    return mask


def _leads_of_search(df_all, row):
    """Leads de una búsqueda: exactos por mision_id (misión ejecutada) o
    aproximados por país + ciudades + nicho (config guardada / misión antigua)."""
    mision_id = row.get('mision_id')
    if mision_id and 'mision_id' in df_all.columns:
        exact = df_all[df_all['mision_id'].fillna('') == str(mision_id)]
        if not exact.empty:
            return exact
    return df_all[_mask_search(df_all, row)]


def render_search_library_view():
    with sqlite3.connect(DB_PATH) as conn:
        favs = pd.read_sql_query(
            "SELECT * FROM search_favorites ORDER BY carpeta, nombre", conn
        )
        hist = pd.read_sql_query(
            "SELECT * FROM search_history ORDER BY fecha DESC", conn
        )

    entries = []
    for _, f in favs.iterrows():
        entry = f.to_dict()
        entry['tipo'] = 'guardada'
        entries.append(entry)
    for _, h in hist.iterrows():
        cities = [c.strip() for c in str(h.get('ciudad') or '').split(',') if c.strip()]
        if not cities:
            continue
        nombre_auto = f"{str(h.get('nicho') or '').strip()[:70]} · {str(h.get('fecha'))[:16]}"
        entries.append({
            'id': f"hist_{h['id']}",
            'nombre': str(h.get('nombre') or '').strip() or nombre_auto,
            'nombre_auto': nombre_auto,
            'carpeta': 'Ejecutadas',
            'pais': h.get('pais', ''),
            'ciudades': json.dumps([{'ciudad': c} for c in cities], ensure_ascii=False),
            'nicho': h.get('nicho', ''),
            'fecha_creacion': h.get('fecha', ''),
            'tipo': 'ejecutada',
            'mision_id': h.get('mision_id'),
        })

    if not entries:
        st.markdown(empty_state(
            "No hay búsquedas todavía",
            "Ejecuta una búsqueda desde «Buscar clientes» o guárdala como favorita "
            "y aparecerá aquí con su CRM, mapa, analítica y campañas.",
        ), unsafe_allow_html=True)
        return

    pool = pd.DataFrame(entries)
    folders = ["Todas"] + sorted(pool['carpeta'].dropna().replace('', 'General').unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
        sel_folder = st.selectbox("Carpeta", folders, key="lib_folder_filter")
    pool_f = pool if sel_folder == "Todas" else pool[pool['carpeta'].fillna('General') == sel_folder]
    with c2:
        ordered = pool_f.sort_values("fecha_creacion", ascending=False)
        selected_fav = st.selectbox(
            "Búsqueda", ["Seleccionar..."] + ordered['nombre'].tolist(),
            key="lib_favorite_filter",
        )
    if selected_fav == "Seleccionar...":
        st.info("Selecciona una búsqueda para abrir su espacio (CRM, mapa, analítica y campañas).")
        return

    row = pool[pool["nombre"] == selected_fav].iloc[0]
    df_all = load_all_leads()
    df_search = _leads_of_search(df_all, row).copy()

    if df_search.empty:
        st.warning(
            f"Esta búsqueda no tiene leads en la base de datos. "
            "Ejecútala desde «Buscar clientes»."
        )
        return

    total = len(df_search)
    callable_count = int(df_search["telefono_e164"].fillna("").astype(str).str.startswith("+").sum()) if "telefono_e164" in df_search else 0
    oro_count = int((df_search["calificacion"] == "oro").sum()) if "calificacion" in df_search else 0
    no_web = int(df_search["tiene_web"].fillna(False).astype(bool).eq(False).sum()) if "tiene_web" in df_search else 0

    st.markdown(title_html(f"Búsqueda: {row['nombre']}", "folder", 2), unsafe_allow_html=True)
    st.caption(
        f"{'📁 ' + str(row['carpeta']) if row.get('tipo') == 'guardada' else '⚡ Ejecutada'} · "
        f"{row['pais']} · {str(row.get('fecha_creacion', ''))[:16]}"
    )

    if row.get('tipo') == 'ejecutada':
        with st.container(border=True):
            c_ren, c_btn = st.columns([3, 1])
            with c_ren:
                new_name = st.text_input(
                    "Nombre de la búsqueda",
                    value=row['nombre'] if row.get('nombre') != row.get('nombre_auto') else "",
                    placeholder=row.get('nombre_auto', ''),
                    key="lib_rename_input",
                )
            with c_btn:
                st.write("")
                if st.button("Guardar nombre", key="lib_rename_save", width="stretch"):
                    hist_id = int(str(row['id']).replace("hist_", ""))
                    with sqlite3.connect(DB_PATH) as hist_conn:
                        hist_conn.execute(
                            "UPDATE search_history SET nombre = ? WHERE id = ?",
                            (new_name.strip() or None, hist_id),
                        )
                    st.success("Nombre guardado.")
                    st.rerun()

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi_card("Leads de esta búsqueda", f"{total:,}", "#E5484D", "En la base"), unsafe_allow_html=True)
    k2.markdown(kpi_card("Listos para llamar", f"{callable_count:,}", "#5D9DF0", "Teléfono E.164"), unsafe_allow_html=True)
    k3.markdown(kpi_card("Alta prioridad", f"{oro_count:,}", "#F5A524", "Calificación oro"), unsafe_allow_html=True)
    k4.markdown(kpi_card("Sin web", f"{no_web:,}", "#46A758", "Oportunidad"), unsafe_allow_html=True)

    section = st.radio(
        "Sección",
        ["CRM", "Mapa", "Analítica", "Email", "WhatsApp"],
        horizontal=True,
        key="lib_section",
    )

    if section == "CRM":
        render_crm_view(df_search)
    elif section == "Mapa":
        render_map_view(df_search)
    elif section == "Analítica":
        render_analytics_view(df_search)
    elif section == "Email":
        render_email_view(df_search)
    elif section == "WhatsApp":
        render_whatsapp_view(df_search)

    st.divider()
    with st.expander("Zona de peligro"):
        st.error(
            f"Borrará los {total} leads de «{row['nombre']}» (y sus oportunidades y eventos de campaña) "
            "de la base de datos. No se puede deshacer."
        )
        confirm = st.text_input(
            f"Escribe ELIMINAR para confirmar", key="lib_delete_confirm",
        )
        if st.button("🗑️ Borrar los leads de esta búsqueda", type="primary", key="lib_delete_leads"):
            if confirm.strip() != "ELIMINAR":
                st.warning("Escribe ELIMINAR para confirmar el borrado.")
            else:
                lead_ids = df_search["id"].astype(int).tolist()
                with open_conn() as conn:
                    conn.execute(
                        "DELETE FROM campaign_events WHERE lead_id IN (%s)" % ",".join("?" * len(lead_ids)),
                        lead_ids,
                    )
                    conn.execute(
                        "DELETE FROM lead_opportunities WHERE lead_id IN (%s)" % ",".join("?" * len(lead_ids)),
                        lead_ids,
                    )
                    conn.execute(
                        "DELETE FROM leads WHERE id IN (%s)" % ",".join("?" * len(lead_ids)),
                        lead_ids,
                    )
                invalidate_leads_cache()
                st.success(f"{len(lead_ids)} leads eliminados.")
                st.rerun()
        if row.get('tipo') == 'guardada' and st.button("Eliminar la búsqueda guardada (config)", key="lib_delete_favorite"):
            with sqlite3.connect(DB_PATH) as fav_conn:
                fav_conn.execute("DELETE FROM search_favorites WHERE id = ?", (int(row["id"]),))
            st.success("Búsqueda guardada eliminada.")
            st.rerun()