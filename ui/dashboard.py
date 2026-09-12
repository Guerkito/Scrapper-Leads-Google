import html

import pandas as pd
import streamlit as st

from db import DB_PATH
from services.constants import get_offer_suggestion
from services.product_campaigns import campaign_label
from ui.helpers import kpi_card, chip, empty_state
from ui.icons import svg_icon, title_html


def _truthy(val):
    if pd.isna(val):
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val == 1
    return str(val).strip().lower() in {"1", "true", "si", "sí", "yes", "y"}


def _rating_num(val):
    try:
        return float(str(val).split("/")[0].strip().replace(",", ".")) if val else 0.0
    except Exception:
        return 0.0


def _has_contact_value(val):
    if pd.isna(val):
        return False
    clean = str(val).strip()
    return bool(clean and clean.lower() not in {"n/a", "na", "none", "nan"})


def _open_lead(lead_id):
    st.session_state.crm_selected_id = int(lead_id)
    st.session_state.view = "CRM"


def _pipeline_rows(df_all):
    """Por campaña comercial: cantidad de leads y afinidad promedio."""
    if df_all.empty:
        return []
    keys_col = df_all["product_keys"] if "product_keys" in df_all.columns else pd.Series("", index=df_all.index)
    labels_col = df_all["productos_objetivo"] if "productos_objetivo" in df_all.columns else pd.Series("", index=df_all.index)
    fit_col = df_all["fit_score"] if "fit_score" in df_all.columns else pd.Series(0, index=df_all.index)

    rows = []
    for key in sorted({k.strip() for v in keys_col.fillna("") for k in str(v).split(",") if k.strip()}):
        mask = keys_col.fillna("").apply(lambda v: key in [k.strip() for k in str(v).split(",") if k.strip()])
        count = int(mask.sum())
        try:
            label = campaign_label(key)
        except Exception:
            labels = labels_col[mask]
            label = str(labels.iloc[0]) if not labels.empty else key
        avg_fit = float(pd.to_numeric(fit_col[mask], errors="coerce").mean()) if count else 0.0
        rows.append({"key": key, "label": label, "count": count, "fit": round(avg_fit)})
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows[:6]


def _recent_missions(limit=6):
    try:
        import sqlite3
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(
                "SELECT fecha, ciudad, nicho, zona, leads_nuevos, leads_duplicados "
                "FROM search_history ORDER BY fecha DESC LIMIT ?",
                conn, params=(limit,),
            )
    except Exception:
        return pd.DataFrame()


def render_dashboard_view(df_all):
    # ── KPIs ──
    total = len(df_all)
    callable_count = 0
    oro_count = 0
    no_web_opps = 0
    if not df_all.empty and "telefono_e164" in df_all.columns:
        callable_count = int(
            df_all["telefono_e164"].fillna("").astype(str).str.startswith("+").sum()
        )
        oro_count = int((df_all["calificacion"] == "oro").sum())
    if not df_all.empty and "tiene_web" in df_all.columns:
        has_web = df_all["tiene_web"].apply(_truthy)
        ratings = df_all["rating"].apply(_rating_num)
        no_web_opps = int((~has_web & (ratings >= 4.0)).sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi_card("Leads capturados", f"{total:,}", "#E5484D", "En tu base de datos"), unsafe_allow_html=True)
    k2.markdown(kpi_card("Listos para llamar", f"{callable_count:,}", "#5D9DF0", "Teléfono E.164 válido"), unsafe_allow_html=True)
    k3.markdown(kpi_card("Alta prioridad", f"{oro_count:,}", "#F5A524", "Calificación oro"), unsafe_allow_html=True)
    k4.markdown(kpi_card("Sin web (oportunidad)", f"{no_web_opps:,}", "#46A758", "Rating ≥ 4.0 sin sitio web"), unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Flujo en 4 pasos (narrativa del producto) ──
    st.markdown(
        "<div class='workflow-steps'>"
        "<div class='workflow-step'><b>1</b> Aprende tu oferta</div>"
        "<div class='workflow-step'><b>2</b> Define tu cliente ideal</div>"
        "<div class='workflow-step'><b>3</b> Encuentra los negocios</div>"
        "<div class='workflow-step'><b>4</b> Prepara el contacto</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([0.58, 0.42])

    with col_left:
        st.markdown(title_html("Campañas comerciales", "activity", 3), unsafe_allow_html=True)
        rows = _pipeline_rows(df_all)
        if rows:
            max_count = max(r["count"] for r in rows) or 1
            rows_html = []
            for r in rows:
                tone = "green" if r["fit"] >= 70 else ("amber" if r["fit"] >= 40 else "neutral")
                pct = r["count"] / max_count * 100
                rows_html.append(
                    "<div class='pipeline-row'>"
                    f"<div><div class='pv'>{html.escape(r['label'])}</div>"
                    f"<div class='head'>{r['count']} leads</div></div>"
                    f"<div><div class='pipeline-bar'><div style='width:{pct:.0f}%'></div></div></div>"
                    f"<div style='text-align:right'><span class='head'>Afinidad</span>"
                    f"<div class='pv'>{r['fit']}/100</div></div>"
                    f"<div>{chip('Activa' if r['count'] else 'En pausa', tone)}</div>"
                    "</div>"
                )
            st.markdown(
                "<div style='border:1px solid #232836;border-radius:12px;background:#12151C;overflow:hidden'>"
                + "".join(rows_html) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(empty_state(
                "Aún no hay campañas activas",
                "Crea una búsqueda con una oferta comercial desde «Buscar clientes» y verás aquí su estado y afinidad mínima.",
            ), unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(title_html("Actividad reciente", "refresh", 3), unsafe_allow_html=True)
        history = _recent_missions()
        if not history.empty:
            items = []
            for _, row in history.iterrows():
                fecha = str(row.get("fecha", ""))[:16]
                items.append(
                    f"<div class='feed-item'>"
                    f"<div class='feed-avatar'>{svg_icon('search', 15)}</div>"
                    f"<div style='flex:1;min-width:0'>"
                    f"<div style='font-size:0.83rem;font-weight:600;color:#E6E9EF'>{html.escape(str(row.get('nicho', '')))}</div>"
                    f"<div style='font-size:0.74rem;color:#6B7485'>{html.escape(str(row.get('ciudad', '')))} · {html.escape(str(row.get('zona', '')))} · {fecha}</div>"
                    f"</div>"
                    f"<div style='text-align:right'>"
                    f"<div style='font-size:0.82rem;color:#98A2B3'><b style='color:#E6E9EF'>{int(row.get('leads_nuevos', 0) or 0)}</b> nuevos</div>"
                    f"<div style='font-size:0.7rem;color:#6B7485'>{int(row.get('leads_duplicados', 0) or 0)} duplicados</div>"
                    f"</div></div>"
                )
            st.markdown(
                "<div style='border:1px solid #232836;border-radius:12px;background:#12151C;overflow:hidden'>"
                + "".join(items) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(empty_state(
                "Sin actividad por ahora",
                "El historial de misiones aparecerá aquí nada más completes la primera búsqueda.",
            ), unsafe_allow_html=True)

    with col_right:
        st.markdown(title_html("Siguientes acciones", "bolt", 3), unsafe_allow_html=True)
        if df_all.empty:
            st.markdown(empty_state(
                "Tu base está vacía",
                "Inicia una búsqueda para capturar tus primeros prospectos con datos de contacto.",
            ), unsafe_allow_html=True)
        else:
            df_act = df_all.copy()
            fit_num = pd.to_numeric(df_act.get("fit_score", 0), errors="coerce").fillna(0)
            rating_num = df_act["rating"].apply(_rating_num)
            score = fit_num * 0.6 + rating_num * 12 + pd.to_numeric(
                df_act.get("reseñas", 0), errors="coerce"
            ).fillna(0).clip(upper=100) / 10
            df_act = df_act.assign(_score=score).sort_values("_score", ascending=False).head(6)

            for _, lead in df_act.iterrows():
                name = str(lead.get("nombre") or "Sin nombre")
                initials = "".join(part[0].upper() for part in name.split()[:2])
                niche = str(lead.get("nicho") or "General")
                city = str(lead.get("ciudad") or "")
                pitch = lead.get("pitch_sugerido")
                offer = (
                    str(pitch) if _has_contact_value(pitch)
                    else get_offer_suggestion(niche)
                )
                lead_id = int(lead.get("id") or 0)
                row_cols = st.columns([0.82, 0.18], gap="small")
                with row_cols[0]:
                    st.markdown(
                        f"<div class='feed-item' style='border:1px solid #232836;border-radius:10px;background:#12151C;margin-bottom:8px'>"
                        f"<div class='feed-avatar'>{html.escape(initials)}</div>"
                        f"<div style='flex:1;min-width:0'>"
                        f"<div style='font-size:0.83rem;font-weight:600;color:#E6E9EF;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{html.escape(name)}</div>"
                        f"<div style='font-size:0.73rem;color:#6B7485;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{html.escape(niche)} · {html.escape(city)}</div>"
                        f"<div style='font-size:0.73rem;color:#98A2B3;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{html.escape(offer)}</div>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                with row_cols[1]:
                    if lead_id:
                        st.button(
                            "Abrir", key=f"feed_open_{lead_id}", width="stretch",
                            type="secondary", on_click=_open_lead, args=(lead_id,),
                        )

    # ── Accesos rápidos ──
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("＋  Nueva búsqueda", key="cta_search_dashboard", width="stretch", type="secondary"):
            st.session_state.view = "Búsqueda"
            st.rerun()
    with q2:
        if st.button("＋  Abrir CRM", key="cta_crm_dashboard", width="stretch", type="secondary"):
            st.session_state.view = "CRM"
            st.rerun()
    with q3:
        if st.button("📊  Ver analítica", key="cta_analytics_dashboard", width="stretch", type="secondary"):
            st.session_state.view = "Analítica"
            st.rerun()
