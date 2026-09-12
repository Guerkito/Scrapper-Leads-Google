"""Panel web de ONYX LeadGen — FastAPI + HTMX.

Reutiliza todos los services del motor (scraper, DB, agentes, analítica).
Se ejecuta con:  uvicorn web.app:app --port 8502
"""

from __future__ import annotations

import datetime
import io
import json
import os
import re
import sqlite3
import tempfile
import threading
import urllib.parse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from config import EVO_API_KEY, EVO_INSTANCE, EVO_URL, PANEL_MAX_UPLOAD_MB
from db import (
    DB_PATH,
    _coerce_float,
    _coerce_reviews,
    init_db,
    open_conn,
    save_lead,
)
from engine.icp_builder import build_icp
from engine import decision_maker
from geo_data import GEO_DATA
from services import campaign_analytics
from services.campaigns import campaign_worker
from services.constants import STATUS_COLORS
from services.email_service import email_campaign_worker
from services.export_utils import safe_spreadsheet_frame
from services.leads import get_wa_link, invalidate_leads_cache, load_all_leads
from services.meetings import sync_meetings
from services.phone_utils import normalize_phone
from services.product_campaigns import (
    FREE_CAMPAIGN,
    build_search_terms,
    campaign_label,
    campaign_options,
    register_custom_campaign,
    segment_label,
    segment_options,
    valid_segments,
)
from services.whatsapp_service import check_whatsapp_connection
from sources.base_source import Lead
from sources.computrabajo import ComputrabajoSource
from sources.doctoralia import DoctoraliaSource
from sources.facebook import FacebookSource
from sources.glassdoor import GlassdoorSource
from sources.google_maps import GoogleMapsSource
from sources.instagram import InstagramSource
from sources.linkedin import LinkedInSource
from sources.paginas_amarillas import PaginasAmarillasSource
from sources.tripadvisor import TripAdvisorSource
from sources.yelp import YelpSource
from web import jobs
from web import auth


BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent

init_db()

app = FastAPI(title="ONYX LeadGen")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

PUBLIC_PATHS = {"/login", "/logout"}


def _safe_next(value: str | None) -> str:
    candidate = (value or "/").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    return candidate


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if not origin:
        return True
    host = request.headers.get("host", "")
    return origin.split("//", 1)[-1].split("/", 1)[0] == host


@app.middleware("http")
async def guard(request: Request, call_next):
    path = request.url.path
    if auth.is_enabled() and path not in PUBLIC_PATHS and not path.startswith("/static/"):
        if not auth.verify_token(request.cookies.get(auth.COOKIE_NAME)):
            if request.method in ("GET", "HEAD"):
                target = "/login"
                if path not in ("", "/"):
                    target += "?next=" + urllib.parse.quote(path)
                return RedirectResponse(target, status_code=303)
            return Response("No autorizado", status_code=401)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not _same_origin(request):
            return Response("Origen no permitido", status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response

SOURCES = {
    "Maps": GoogleMapsSource,
    "Páginas Amarillas": PaginasAmarillasSource,
    "LinkedIn": LinkedInSource,
    "Doctoralia (Salud)": DoctoraliaSource,
    "Instagram": InstagramSource,
    "TripAdvisor": TripAdvisorSource,
    "Computrabajo (B2B)": ComputrabajoSource,
    "Facebook": FacebookSource,
    "Yelp": YelpSource,
    "Glassdoor (Corporativo)": GlassdoorSource,
}

NAV = [
    ("Exploración", [("Inicio", "/"), ("Buscar clientes", "/search"), ("Decisores", "/decisions")]),
    ("Gestión", [
        ("Búsquedas", "/library"), ("CRM", "/crm"), ("Mapa", "/map"), ("Analítica", "/analytics"),
    ]),
    ("Comunicación", [("WhatsApp", "/whatsapp"), ("Email", "/email")]),
    ("Sistema", [("Admin", "/admin"), ("Cómo funciona", "/help"), ("Configuración", "/settings")]),
]

PAGE_META = {
    "/": ("Centro de mando", "ONYX LeadGen", "Encuentra, prioriza y contacta clientes potenciales."),
    "/search": ("Exploración", "Buscar clientes", "Define qué vendes, a quién buscas y en dónde."),
    "/decisions": ("Exploración", "Decisores", "Convierte cada negocio en una persona con nombre y cargo."),
    "/library": ("Gestión", "Búsquedas", "Tus misiones ejecutadas y las búsquedas guardadas."),
    "/crm": ("Gestión", "Leads y oportunidades", "Filtra, abre y actualiza cada prospecto."),
    "/map": ("Gestión", "Mapa", "Zonas calientes, cobertura y prospectos sobre el territorio."),
    "/analytics": ("Gestión", "Rendimiento", "Coste por lead, respuestas y optimización de campañas."),
    "/whatsapp": ("Comunicación", "Campañas WhatsApp", "Envía con control anti-ban y automatiza respuestas."),
    "/email": ("Comunicación", "Campañas de correo", "Personaliza por lead y dispara con pausas de seguridad."),
    "/admin": ("Sistema", "Admin", "Calidad de datos, respaldos, importación e historial."),
    "/help": ("Sistema", "Cómo funciona", "El flujo completo del sistema, explicado."),
    "/settings": ("Sistema", "Configuración", "Todo lo que antes vivía en el .env, editable aquí."),
}


# ── Helpers ──────────────────────────────────────────────────────────────────
def _redirect(path: str, message: str = "", ok: bool = False):
    if message:
        separator = "&" if "?" in path else "?"
        path = f"{path}{separator}msg={urllib.parse.quote(message)}&ok={1 if ok else 0}"
    return RedirectResponse(path, status_code=303)


def _page(request: Request, name: str, **extra):
    meta = PAGE_META.get(request.url.path)
    if not meta:
        meta = next(
            (value for prefix, value in PAGE_META.items() if prefix != "/" and request.url.path.startswith(prefix)),
            ("", "ONYX", ""),
        )
    context = {
        "request": request,
        "nav": NAV,
        "path": request.url.path,
        "kicker": meta[0],
        "title": meta[1],
        "subtitle": meta[2],
        "msg": request.query_params.get("msg", ""),
        "ok": request.query_params.get("ok") == "1",
        "auth_enabled": auth.is_enabled(),
    }
    context.update(extra)
    return templates.TemplateResponse(request, name, context)


def _parse_cities(raw: str, pais: str) -> list[dict]:
    lookup: dict[str, str] = {}
    for departamento, municipios in GEO_DATA.get(pais, {}).items():
        for ciudad in municipios:
            lookup.setdefault(ciudad.casefold(), departamento)
    cities = []
    for chunk in re.split(r"[,\n;]+", raw or ""):
        name = chunk.strip()
        if "—" in name:
            name = name.split("—")[0].strip()
        if not name:
            continue
        if name.startswith("coord:"):
            cities.append({"ciudad": name, "pais": pais})
            continue
        cities.append({
            "ciudad": name,
            "departamento": lookup.get(name.casefold(), ""),
            "pais": pais,
        })
    return cities


def _fetch_leads(where: str = "", params: tuple = (), limit: int = 200) -> list[dict]:
    query = "SELECT * FROM leads"
    if where:
        query += f" WHERE {where}"
    query += " ORDER BY id DESC LIMIT ?"
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, (*params, limit)).fetchall()]


# ── Dashboard ────────────────────────────────────────────────────────────────
@app.get("/")
def dashboard(request: Request):
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        funnel_rows = conn.execute(
            "SELECT COALESCE(estado, 'Nuevo') AS estado, COUNT(*) AS n "
            "FROM leads GROUP BY COALESCE(estado, 'Nuevo') ORDER BY n DESC"
        ).fetchall()
        recent = [
            dict(row) for row in conn.execute(
                "SELECT id, nombre, ciudad, nicho, estado, telefono, email "
                "FROM leads ORDER BY id DESC LIMIT 12"
            ).fetchall()
        ]
        with_answer = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE estado IN ('Interesado','Cerrado','Reunión') "
            "OR COALESCE(historial_mensajes,'') LIKE '%Usuario:%'"
        ).fetchone()[0]
    summary = campaign_analytics.send_summary()
    return _page(
        request, "dashboard.html",
        total=total, funnel=funnel_rows, recent=recent, with_answer=with_answer,
        summary=summary, mission=jobs.MISSION.snapshot(),
        chart_labels=[row["estado"] for row in funnel_rows],
        chart_values=[row["n"] for row in funnel_rows],
    )


# ── Búsqueda ─────────────────────────────────────────────────────────────────
@app.get("/search")
def search_page(request: Request):
    campaigns = [
        {
            "key": key,
            "label": campaign_label(key),
            "segments": [
                {"key": segment, "label": segment_label(key, segment)}
                for segment in segment_options(key)
            ],
        }
        for key in campaign_options()
    ]
    paused = campaign_analytics.paused_segment_keys()
    params = request.query_params
    prefill = {
        "campaign": params.get("campaign", FREE_CAMPAIGN),
        "queries": params.get("queries", ""),
        "country": params.get("country", "Colombia"),
        "cities": params.get("cities", ""),
        "sources": [s for s in params.get("sources", "Maps").split(",") if s in SOURCES],
        "limit": params.get("limit", "20"),
        "segments": [s for s in params.get("segments", "").split(",") if s],
        "deep": params.get("deep") == "1",
        "hunter": params.get("hunter") == "1",
        "cold_call": params.get("cold_call") == "1",
    }
    return _page(
        request, "search.html",
        campaigns=campaigns,
        paused=paused,
        sources=list(SOURCES),
        countries=sorted(GEO_DATA),
        mission=jobs.MISSION.snapshot(),
        prefill=prefill,
    )


@app.post("/icp")
def generate_icp(site_url: str = Form("")):
    if not site_url.strip():
        return _redirect("/search", "Escribe la URL de tu web.", ok=False)
    try:
        icp = build_icp(site_url)
        key = register_custom_campaign(icp)
    except Exception as exc:
        return _redirect("/search", str(exc), ok=False)
    return _redirect("/search", f"Oferta creada: {campaign_label(key)}. Elígela y busca.", ok=True)


@app.post("/search/start")
async def search_start(request: Request):
    form = await request.form()
    campaign = str(form.get("campaign") or FREE_CAMPAIGN)
    segments = valid_segments(campaign, form.getlist("segments"))
    country = str(form.get("country") or "Colombia")
    cities_raw = str(form.get("cities") or "")
    source_names = [name for name in form.getlist("sources") if name in SOURCES]
    limit = max(5, min(500, int(form.get("limit") or 20)))
    deep = form.get("deep") == "on" and form.get("cold_call") != "on"
    hunter = form.get("hunter") == "on"
    cold_call = form.get("cold_call") == "on"
    sweep_all = form.get("sweep_all") == "on"

    if campaign != FREE_CAMPAIGN:
        queries = build_search_terms(campaign, segments)
        if not queries:
            return _redirect("/search", "Selecciona al menos un tipo de cliente.", ok=False)
        final_query = ", ".join(queries)
    else:
        segments = []
        final_query = str(form.get("queries") or "").strip()
        if not final_query:
            return _redirect("/search", "Escribe al menos un tipo de empresa.", ok=False)

    cities = _parse_cities(cities_raw, country)
    if not cities:
        return _redirect("/search", "Escribe al menos una ciudad.", ok=False)

    if cold_call:
        source_names = ["Maps"] + (["Páginas Amarillas"] if country == "Colombia" else [])
    elif hunter:
        source_names = ["Maps"]
    if not source_names and not cold_call:
        return _redirect("/search", "Selecciona al menos una fuente.", ok=False)

    started = jobs.MISSION.start(
        [SOURCES[name]() for name in source_names], None, final_query, cities,
        deep, limit, sweep_all, hunter_mode=hunter, pais=country,
        cold_call_mode=cold_call, product_campaign=campaign,
        target_segments=segments,
    )
    if not started:
        return _redirect("/search", "Ya hay una misión en curso.", ok=False)
    return _redirect("/search", "Misión lanzada.", ok=True)


@app.get("/search/progress")
def search_progress(request: Request):
    return templates.TemplateResponse(
        request, "_mission.html", {"request": request, "mission": jobs.MISSION.snapshot()}
    )


@app.post("/search/stop")
def search_stop():
    jobs.MISSION.stop()
    return _redirect("/search", "Deteniendo misión…", ok=True)


# ── Decisores (Fase 4) ───────────────────────────────────────────────────────
@app.get("/decisions")
def decisions_page(request: Request, q: str = ""):
    pending = decision_maker.pending_count()
    where = "COALESCE(decisor_nombre, '') != ''"
    params: tuple = ()
    if q:
        where += " AND (nombre LIKE ? OR ciudad LIKE ?)"
        params = (f"%{q}%", f"%{q}%")
    rows = _fetch_leads(where, params, limit=100)
    with_linkedin = sum(1 for row in rows if row.get("decisor_linkedin"))
    return _page(
        request, "decisions.html",
        pending=pending, rows=rows, q=q, with_linkedin=with_linkedin,
        job=jobs.DECISION_JOB.snapshot(),
    )


@app.post("/decisions/start")
def decisions_start(limit: int = Form(20)):
    if not jobs.start_decision_enrichment(limit=max(1, min(200, limit))):
        return _redirect("/decisions", "Ya hay un lote en curso.", ok=False)
    return _redirect("/decisions", "Enriquecimiento lanzado.", ok=True)


@app.get("/decisions/progress")
def decisions_progress(request: Request):
    return templates.TemplateResponse(
        request, "_decisions_progress.html", {"request": request, "job": jobs.DECISION_JOB.snapshot()}
    )


# ── CRM ──────────────────────────────────────────────────────────────────────
@app.get("/crm")
def crm_page(request: Request, q: str = "", estado: str = "", page: int = 1):
    conditions, params = [], []
    if q:
        conditions.append("(nombre LIKE ? OR ciudad LIKE ? OR nicho LIKE ? OR email LIKE ?)")
        params.extend([f"%{q}%"] * 4)
    if estado:
        conditions.append("estado = ?")
        params.append(estado)
    where = " AND ".join(conditions)
    page = max(1, page)
    offset = (page - 1) * 50
    with open_conn() as conn:
        count = conn.execute(
            f"SELECT COUNT(*) FROM leads{' WHERE ' + where if where else ''}", params
        ).fetchone()[0]
        query = "SELECT * FROM leads"
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY id DESC LIMIT 50 OFFSET ?"
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(query, (*params, offset)).fetchall()]
    return _page(
        request, "crm.html", rows=rows, q=q, estado=estado, page=page,
        pages=max(1, (count + 49) // 50), total=count,
    )


@app.get("/leads/{lead_id}")
def lead_detail(request: Request, lead_id: int):
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if not row:
            return _redirect("/crm", "Lead no encontrado.", ok=False)
        opportunities = [
            dict(item) for item in conn.execute(
                "SELECT product_label, segment_label, fit_score, fit_reason, pitch "
                "FROM lead_opportunities WHERE lead_id = ? ORDER BY fit_score DESC",
                (lead_id,),
            ).fetchall()
        ]
    return _page(request, "lead_detail.html", lead=dict(row), opportunities=opportunities)


@app.post("/leads/{lead_id}")
async def lead_update(request: Request, lead_id: int):
    form = await request.form()
    with open_conn() as conn:
        conn.execute(
            """
            UPDATE leads SET estado = ?, estado_contacto = ?, notas = ?,
                decisor_nombre = ?, decisor_cargo = ?, decisor_linkedin = ?
            WHERE id = ?
            """,
            (
                str(form.get("estado") or "Nuevo"),
                str(form.get("estado_contacto") or "sin_contactar"),
                str(form.get("notas") or ""),
                str(form.get("decisor_nombre") or "").strip() or None,
                str(form.get("decisor_cargo") or "").strip() or None,
                str(form.get("decisor_linkedin") or "").strip() or None,
                lead_id,
            ),
        )
    return _redirect(f"/leads/{lead_id}", "Lead actualizado.", ok=True)


@app.post("/leads/{lead_id}/decisor")
def lead_enrich_decisor(lead_id: int):
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if not row or not row["sitio_web"]:
        return _redirect(f"/leads/{lead_id}", "El lead no tiene web para analizar.", ok=False)
    try:
        decision = decision_maker.enrich_lead(dict(row))
    except Exception as exc:
        return _redirect(f"/leads/{lead_id}", f"Error analizando la web: {exc}", ok=False)
    if not decision:
        return _redirect(f"/leads/{lead_id}", "No se encontró un decisor en la web.", ok=False)
    decision_maker.save_decision(lead_id, decision)
    return _redirect(f"/leads/{lead_id}", f"Decisor: {decision['nombre']}", ok=True)


# ── Analítica ────────────────────────────────────────────────────────────────
@app.get("/analytics")
def analytics_page(request: Request):
    summary = campaign_analytics.send_summary()
    rows = campaign_analytics.campaign_performance()
    paused = [row for row in rows if row["estado"] == "pausado"]
    top = sorted(rows, key=lambda row: row["leads"], reverse=True)[:8]
    return _page(
        request, "analytics.html", summary=summary, rows=rows, paused=paused,
        cost_per_email=os.getenv("COST_PER_EMAIL", "0"),
        provider=os.getenv("SENDER_PROVIDER", "smtp"),
        daily_limit=os.getenv("SENDER_DAILY_LIMIT", "0"),
        chart_labels=[row["segment_label"][:24] for row in top],
        chart_leads=[row["leads"] for row in top],
        chart_replies=[row["respondieron"] for row in top],
    )


@app.post("/analytics/optimize")
def analytics_optimize():
    actions = campaign_analytics.auto_optimize()
    paused = [a for a in actions if a["action"] == "pausar"]
    scaling = [a for a in actions if a["action"] == "escalar"]
    message = (
        f"Pausados: {len(paused)}. Para escalar: {len(scaling)}."
        if actions else "Sin cambios: ningún segmento cumple las reglas todavía."
    )
    return _redirect("/analytics", message, ok=bool(paused or scaling))


@app.post("/analytics/resume")
async def analytics_resume(request: Request):
    form = await request.form()
    pairs = form.getlist("segment")
    for pair in pairs:
        product_key, _, segment_key = str(pair).partition("|")
        if product_key and segment_key:
            campaign_analytics.set_segment_status(
                product_key, segment_key, "active", "Reanudado manualmente"
            )
    return _redirect("/analytics", f"Reanudados {len(pairs)} segmento(s).", ok=True)


# ── Email ────────────────────────────────────────────────────────────────────
def _email_candidates(states: list[str]) -> list[dict]:
    df = load_all_leads()
    if df.empty:
        return []
    mask = df["email"].notna() & df["email"].astype(str).str.contains("@", na=False)
    mask &= ~df["email"].astype(str).str.lower().isin(["none", "n/a", "null"])
    mask &= df["estado"].isin(states)
    if "estado_contacto" in df.columns:
        mask &= df["estado_contacto"].fillna("").str.casefold() != "no_contactar"
    return df[mask].to_dict("records")


@app.get("/email")
def email_page(request: Request):
    return _page(
        request, "email.html",
        campaign=jobs.EMAIL_CAMP,
        provider=os.getenv("SENDER_PROVIDER", "smtp"),
        daily_limit=os.getenv("SENDER_DAILY_LIMIT", "0"),
        has_credentials=bool(os.getenv("EMAIL_USER")),
    )


@app.post("/email/start")
async def email_start(request: Request):
    form = await request.form()
    states = list(form.getlist("states")) or ["Nuevo"]
    leads = _email_candidates(states)
    if not leads:
        return _redirect("/email", "No hay leads con email en esos estados.", ok=False)
    if jobs.EMAIL_CAMP.running:
        return _redirect("/email", "Ya hay una campaña de email en curso.", ok=False)
    jobs.EMAIL_CAMP.reset()
    threading.Thread(
        target=email_campaign_worker,
        args=(
            jobs.EMAIL_CAMP, leads,
            str(form.get("subject") or "Propuesta para {nombre}"),
            str(form.get("template") or "Hola {nombre}, ¿hablamos?"),
            form.get("test_mode") == "on",
            form.get("use_llm") == "on",
        ),
        daemon=True,
    ).start()
    return _redirect("/email", f"Campaña lanzada con {len(leads)} lead(s).", ok=True)


@app.get("/email/progress")
def email_progress(request: Request):
    return templates.TemplateResponse(
        request, "_email_progress.html", {"request": request, "campaign": jobs.EMAIL_CAMP}
    )


@app.post("/email/stop")
def email_stop():
    jobs.EMAIL_CAMP.stop = True
    return _redirect("/email", "Deteniendo campaña…", ok=True)


# ── WhatsApp ─────────────────────────────────────────────────────────────────
def _whatsapp_candidates(states: list[str], only_without_web: bool, pais: str) -> list[dict]:
    df = load_all_leads()
    if df.empty:
        return []
    mask = df["estado"].isin(states)
    if "estado_contacto" in df.columns:
        mask &= df["estado_contacto"].fillna("").str.casefold() != "no_contactar"
    if only_without_web:
        mask &= ~df["tiene_web"].fillna(False).astype(bool)
    candidates = df[mask].to_dict("records")
    valid = []
    for lead in candidates:
        phone = normalize_phone(
            lead.get("telefono_e164") or lead.get("telefono"),
            lead.get("pais") or pais,
        )
        if phone:
            lead["telefono_e164"] = phone
            valid.append(lead)
    return valid


@app.get("/whatsapp")
def whatsapp_page(request: Request):
    status = check_whatsapp_connection(EVO_URL, EVO_API_KEY, EVO_INSTANCE)
    return _page(request, "whatsapp.html", status=status, campaign=jobs.WA_CAMP)


@app.post("/whatsapp/start")
async def whatsapp_start(request: Request):
    form = await request.form()
    states = list(form.getlist("states")) or ["Interesado"]
    pais = str(form.get("country") or "Colombia")
    leads = _whatsapp_candidates(
        states, form.get("only_without_web") == "on", pais
    )
    if not leads:
        return _redirect("/whatsapp", "No hay leads con teléfono válido en esos estados.", ok=False)
    if jobs.WA_CAMP.running:
        return _redirect("/whatsapp", "Ya hay una campaña de WhatsApp en curso.", ok=False)
    jobs.WA_CAMP.reset()
    threading.Thread(
        target=campaign_worker,
        args=(
            jobs.WA_CAMP, leads,
            str(form.get("template") or "Hola {nombre}, ¿te comparto una propuesta breve?"),
            EVO_URL, str(form.get("instance") or EVO_INSTANCE), EVO_API_KEY, pais,
            form.get("test_mode") == "on",
            (
                int(form.get("delay_min") or 120),
                int(form.get("delay_max") or 300),
            ),
        ),
        daemon=True,
    ).start()
    return _redirect("/whatsapp", f"Campaña lanzada con {len(leads)} lead(s).", ok=True)


@app.get("/whatsapp/progress")
def whatsapp_progress(request: Request):
    return templates.TemplateResponse(
        request, "_whatsapp_progress.html", {"request": request, "campaign": jobs.WA_CAMP}
    )


@app.post("/whatsapp/stop")
def whatsapp_stop():
    jobs.WA_CAMP.stop = True
    return _redirect("/whatsapp", "Deteniendo campaña…", ok=True)


# ── Configuración ────────────────────────────────────────────────────────────
ENV_GROUPS = {
    "IA local (Ollama)": ["OLLAMA_CHAT_URL", "OLLAMA_MODEL"],
    "Scraping": ["DB_PATH", "MAX_CONCURRENT"],
    "Envío de email": [
        "SENDER_PROVIDER", "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USER", "EMAIL_PASS",
        "EMAIL_FROM_NAME", "SENDER_FROM_EMAIL", "RESEND_API_KEY",
        "SENDER_DAILY_LIMIT", "COST_PER_EMAIL", "CALCOM_LINK",
    ],
    "Respuestas (IMAP)": [
        "IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASS", "IMAP_FOLDER",
        "INBOX_POLL_SECONDS",
    ],
    "Follow-ups": ["FOLLOW_UP_MAX", "FOLLOW_UP_DAYS", "FOLLOW_UP_POLL_MINUTES"],
    "Optimización": ["AUTO_OPTIMIZE", "OPTIMIZE_MIN_LEADS", "OPTIMIZE_SCALE_RATE"],
    "WhatsApp (Evolution)": ["EVO_URL", "EVO_API_KEY", "EVO_INSTANCE"],
    "Webhook": ["WEBHOOK_PORT", "WEBHOOK_AUTH_TOKEN", "WEBHOOK_WORKERS"],
}


def _update_env_file(values: dict[str, str]) -> None:
    env_path = APP_DIR / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    remaining = dict(values)
    output = []
    for line in lines:
        match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if match and match.group(1) in remaining:
            key = match.group(1)
            output.append(f"{key}={remaining.pop(key)}")
        else:
            output.append(line)
    for key, value in remaining.items():
        output.append(f"{key}={value}")
    env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


@app.get("/settings")
def settings_page(request: Request):
    groups = {
        group: [
            {
                "key": key,
                "value": os.getenv(key, ""),
                "secret": any(hint in key for hint in ("PASS", "KEY", "TOKEN")),
            }
            for key in keys
        ]
        for group, keys in ENV_GROUPS.items()
    }
    return _page(request, "settings.html", groups=groups)


@app.post("/settings")
async def settings_save(request: Request):
    form = await request.form()
    values = {}
    for keys in ENV_GROUPS.values():
        for key in keys:
            if key in form:
                value = str(form.get(key) or "").strip()
                if value:
                    values[key] = value
    _update_env_file(values)
    load_dotenv(APP_DIR / ".env", override=True)
    return _redirect(
        "/settings",
        "Guardado. Los ajustes de envío se aplican ya; URL/API del sistema requieren reiniciar.",
        ok=True,
    )


# ── Búsquedas guardadas y ejecutadas ─────────────────────────────────────────
def _history_entries() -> list[dict]:
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(
            "SELECT * FROM search_history ORDER BY id DESC LIMIT 200"
        ).fetchall()]
        counts = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT mision_id, COUNT(*) FROM leads "
                "WHERE mision_id IS NOT NULL AND mision_id != '' GROUP BY mision_id"
            ).fetchall()
        }
    for row in rows:
        row["leads_count"] = counts.get(row.get("mision_id"), 0)
    return rows


def _favorite_entries() -> list[dict]:
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(
            "SELECT * FROM search_favorites ORDER BY carpeta, nombre"
        ).fetchall()]
    for row in rows:
        try:
            cities = json.loads(row.get("ciudades") or "[]")
        except (TypeError, json.JSONDecodeError):
            cities = []
        try:
            sources = json.loads(row.get("fuentes") or "[]")
        except (TypeError, json.JSONDecodeError):
            sources = []
        try:
            segments = json.loads(row.get("target_segments") or "[]")
        except (TypeError, json.JSONDecodeError):
            segments = []
        params = {
            "campaign": row.get("product_campaign") or FREE_CAMPAIGN,
            "queries": row.get("nicho") or "",
            "country": row.get("pais") or "Colombia",
            "cities": ", ".join(
                str(city.get("ciudad", ""))
                for city in cities if isinstance(city, dict)
            ),
            "sources": ",".join(sources) if sources else "Maps",
            "limit": row.get("limit_sel") or 20,
            "segments": ",".join(segments),
        }
        for flag, key in (("deep", "deep_scan"), ("hunter", "hunter_mode"), ("cold_call", "cold_call_mode")):
            if row.get(key):
                params[flag] = "1"
        row["apply_url"] = "/search?" + urllib.parse.urlencode(params)
    return rows


@app.get("/library")
def library_page(request: Request):
    return _page(
        request, "library.html",
        history=_history_entries(), favorites=_favorite_entries(),
    )


@app.get("/library/history/{history_id}")
def library_history(request: Request, history_id: int):
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        record = conn.execute(
            "SELECT * FROM search_history WHERE id = ?", (history_id,)
        ).fetchone()
        if not record:
            return _redirect("/library", "Búsqueda no encontrada.", ok=False)
        record = dict(record)
        mision_id = record.get("mision_id")
        rows = []
        if mision_id:
            rows = [dict(row) for row in conn.execute(
                "SELECT * FROM leads WHERE mision_id = ? ORDER BY id DESC LIMIT 1000",
                (mision_id,),
            ).fetchall()]
    metrics = {
        "total": len(rows),
        "callable": sum(1 for row in rows if str(row.get("telefono_e164") or "").startswith("+")),
        "oro": sum(1 for row in rows if row.get("calificacion") == "oro"),
        "sin_web": sum(1 for row in rows if not row.get("tiene_web")),
    }
    return _page(request, "library_detail.html", record=record, rows=rows, metrics=metrics)


@app.post("/library/history/{history_id}/rename")
def library_rename(history_id: int, nombre: str = Form("")):
    with open_conn() as conn:
        conn.execute(
            "UPDATE search_history SET nombre = ? WHERE id = ?",
            (nombre.strip() or None, history_id),
        )
    return _redirect(f"/library/history/{history_id}", "Nombre guardado.", ok=True)


@app.post("/library/history/{history_id}/delete")
def library_delete(history_id: int, confirm: str = Form("")):
    if confirm.strip().upper() != "ELIMINAR":
        return _redirect(
            f"/library/history/{history_id}", "Escribe ELIMINAR para confirmar.", ok=False
        )
    with open_conn() as conn:
        row = conn.execute(
            "SELECT mision_id FROM search_history WHERE id = ?", (history_id,)
        ).fetchone()
        mision_id = row[0] if row else None
        if not mision_id:
            return _redirect(
                f"/library/history/{history_id}",
                "Búsqueda antigua sin misión asociada; no se puede borrar con precisión.",
                ok=False,
            )
        conn.execute(
            "DELETE FROM campaign_events WHERE lead_id IN "
            "(SELECT id FROM leads WHERE mision_id = ?)", (mision_id,),
        )
        conn.execute(
            "DELETE FROM lead_opportunities WHERE lead_id IN "
            "(SELECT id FROM leads WHERE mision_id = ?)", (mision_id,),
        )
        deleted = conn.execute(
            "DELETE FROM leads WHERE mision_id = ?", (mision_id,)
        ).rowcount
    invalidate_leads_cache()
    return _redirect("/library", f"{deleted} lead(s) eliminados.", ok=True)


@app.post("/library/favorite/{favorite_id}/delete")
def library_favorite_delete(favorite_id: int):
    with open_conn() as conn:
        conn.execute("DELETE FROM search_favorites WHERE id = ?", (favorite_id,))
    return _redirect("/library", "Búsqueda guardada eliminada.", ok=True)


@app.post("/search/save")
async def search_save(request: Request):
    form = await request.form()
    name = str(form.get("favorite_name") or "").strip()
    if not name:
        return _redirect("/search", "Escribe un nombre para guardar la búsqueda.", ok=False)
    campaign = str(form.get("campaign") or FREE_CAMPAIGN)
    segments = valid_segments(campaign, form.getlist("segments"))
    country = str(form.get("country") or "Colombia")
    cities = _parse_cities(str(form.get("cities") or ""), country)
    sources = [source for source in form.getlist("sources") if source in SOURCES]
    queries = (
        ", ".join(build_search_terms(campaign, segments))
        if campaign != FREE_CAMPAIGN
        else str(form.get("queries") or "").strip()
    )
    with open_conn() as conn:
        conn.execute(
            """
            INSERT INTO search_favorites
                (nombre, nicho, pais, ciudades, fuentes, limit_sel, deep_scan,
                 product_campaign, target_segments, cold_call_mode, hunter_mode, carpeta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nombre) DO UPDATE SET
                nicho=excluded.nicho, pais=excluded.pais, ciudades=excluded.ciudades,
                fuentes=excluded.fuentes, limit_sel=excluded.limit_sel,
                deep_scan=excluded.deep_scan, product_campaign=excluded.product_campaign,
                target_segments=excluded.target_segments, cold_call_mode=excluded.cold_call_mode,
                hunter_mode=excluded.hunter_mode, carpeta=excluded.carpeta
            """,
            (
                name, queries, country,
                json.dumps(cities, ensure_ascii=False),
                json.dumps(sources, ensure_ascii=False),
                max(5, min(500, int(form.get("limit") or 20))),
                form.get("deep") == "on", campaign,
                json.dumps(segments, ensure_ascii=False),
                form.get("cold_call") == "on", form.get("hunter") == "on",
                str(form.get("favorite_folder") or "").strip() or "General",
            ),
        )
    return _redirect("/library", f"Búsqueda guardada: {name}", ok=True)


# ── Mapa ─────────────────────────────────────────────────────────────────────
@app.get("/map")
def map_page(request: Request, min_rating: float = 0.0):
    requested = request.query_params.getlist("estados")
    selected = [
        estado for estado in (requested or list(STATUS_COLORS))
        if estado in STATUS_COLORS
    ]
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(
            "SELECT id, nombre, lat, lng, estado, rating, reseñas, ciudad, nicho, "
            "telefono, telefono_e164, maps_url, calificacion, zona, pais "
            "FROM leads WHERE lat IS NOT NULL AND lng IS NOT NULL"
        ).fetchall()]

    def _rating(value):
        try:
            return float(str(value).split("/")[0].strip().replace(",", "."))
        except (TypeError, ValueError):
            return 0.0

    visible = [
        row for row in rows
        if (row.get("estado") or "Nuevo") in selected and _rating(row.get("rating")) >= min_rating
    ]
    cap = 800
    points = []
    for row in visible[:cap]:
        row["wa"] = get_wa_link(row, row.get("pais") or "Colombia")
        points.append({
            "nombre": row.get("nombre") or "",
            "lat": row.get("lat"),
            "lng": row.get("lng"),
            "estado": row.get("estado") or "Nuevo",
            "rating": str(row.get("rating") or ""),
            "resenas": row.get("reseñas") or 0,
            "ciudad": row.get("ciudad") or "",
            "nicho": row.get("nicho") or "",
            "telefono": row.get("telefono_e164") or row.get("telefono") or "",
            "maps_url": row.get("maps_url") or "",
            "wa": row.get("wa") or "",
            "color": STATUS_COLORS.get(row.get("estado"), STATUS_COLORS["Nuevo"])["color"],
        })
    center = {
        "lat": sum(point["lat"] for point in points) / len(points) if points else 4.65,
        "lng": sum(point["lng"] for point in points) / len(points) if points else -74.09,
    }
    zones: dict[str, int] = {}
    for row in visible:
        zone = str(row.get("zona") or "").strip()
        if zone and "coord:" not in zone:
            zones[zone] = zones.get(zone, 0) + 1
    return _page(
        request, "map.html",
        points=points, center=center, legend=STATUS_COLORS,
        selected=selected, min_rating=min_rating,
        total_geo=len(rows), visible=len(visible), cap=cap,
        top_zone=(max(zones, key=zones.get)[:20] if zones else "—"),
        gold=sum(1 for row in visible if row.get("calificacion") == "oro"),
        coverage=round(len(visible) / len(rows) * 100) if rows else 0,
    )


# ── Admin ────────────────────────────────────────────────────────────────────
@app.get("/admin")
def admin_page(request: Request):
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

        def pct(sql: str) -> int:
            if not total:
                return 0
            return round(conn.execute(sql).fetchone()[0] / total * 100)

        stats = {
            "total": total,
            "phone": pct("SELECT COUNT(*) FROM leads WHERE COALESCE(telefono_e164, '') LIKE '+%'"),
            "email": pct("SELECT COUNT(*) FROM leads WHERE email LIKE '%@%'"),
            "pais": pct("SELECT COUNT(*) FROM leads WHERE COALESCE(trim(pais), '') != ''"),
            "web": pct("SELECT COUNT(*) FROM leads WHERE tiene_web = 1"),
        }
        duplicate_rows = conn.execute(
            """
            SELECT COALESCE(SUM(c - 1), 0) FROM (
                SELECT COUNT(*) AS c FROM leads
                GROUP BY lower(trim(nombre)), lower(trim(COALESCE(ciudad, ''))),
                         lower(trim(COALESCE(pais, '')))
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        campaigns = [dict(row) for row in conn.execute(
            """
            SELECT campaign_id, channel, status, COUNT(*) AS destinos,
                   MIN(created_at) AS inicio, MAX(updated_at) AS ultima
            FROM campaign_events
            GROUP BY campaign_id, channel, status
            ORDER BY ultima DESC LIMIT 200
            """
        ).fetchall()]
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    return _page(
        request, "admin.html",
        stats=stats, duplicate_rows=duplicate_rows, campaigns=campaigns,
        db_mb=round(db_size / 1024 / 1024, 2),
    )


@app.post("/admin/vacuum")
def admin_vacuum():
    with open_conn() as conn:
        conn.execute("VACUUM")
    return _redirect("/admin", "Base de datos compactada.", ok=True)


@app.get("/admin/export.csv")
def admin_export():
    df = load_all_leads()
    body = safe_spreadsheet_frame(df).to_csv(index=False) if not df.empty else "sin_datos\n"
    filename = f"leads_onyx_{datetime.date.today():%Y%m%d}.csv"
    return Response(
        body, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/admin/backup.db")
def admin_backup():
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    handle.close()
    try:
        with open_conn() as live, sqlite3.connect(handle.name) as destination:
            live.backup(destination)
    except Exception as exc:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        return _redirect("/admin", f"No se pudo crear el respaldo: {exc}", ok=False)
    filename = f"backup_onyx_{datetime.date.today():%Y%m%d}.db"
    return FileResponse(
        handle.name, filename=filename, media_type="application/octet-stream",
        background=BackgroundTask(lambda path: os.path.exists(path) and os.unlink(path), handle.name),
    )


@app.post("/admin/restore")
async def admin_restore(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        return _redirect("/admin", "Archivo vacío.", ok=False)
    if len(data) > PANEL_MAX_UPLOAD_MB * 1024 * 1024:
        return _redirect("/admin", f"El archivo supera el máximo de {PANEL_MAX_UPLOAD_MB} MB.", ok=False)
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    handle.write(data)
    handle.close()
    try:
        source = sqlite3.connect(f"file:{handle.name}?mode=ro", uri=True)
        try:
            integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {
                row[0] for row in source.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if integrity != "ok" or "leads" not in tables:
                raise ValueError("El archivo está corrupto o no contiene la tabla leads.")
            backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(
                backup_dir,
                f"pre_restore_{datetime.datetime.now():%Y%m%d_%H%M%S}.db",
            )
            with open_conn() as live, sqlite3.connect(backup_path) as backup:
                live.backup(backup)
            with open_conn() as live:
                source.backup(live)
        finally:
            source.close()
        init_db()
        invalidate_leads_cache()
        return _redirect("/admin", "Base restaurada. Respaldo previo guardado en data/backups.", ok=True)
    except Exception as exc:
        return _redirect("/admin", f"Fallo en restauración: {exc}", ok=False)
    finally:
        if os.path.exists(handle.name):
            os.unlink(handle.name)


@app.post("/admin/import")
async def admin_import(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > PANEL_MAX_UPLOAD_MB * 1024 * 1024:
        return _redirect("/admin", f"El archivo supera el máximo de {PANEL_MAX_UPLOAD_MB} MB.", ok=False)
    name = (file.filename or "").lower()
    try:
        frame = (
            pd.read_csv(io.BytesIO(data))
            if name.endswith(".csv")
            else pd.read_excel(io.BytesIO(data))
        )
    except Exception as exc:
        return _redirect("/admin", f"No se pudo leer el archivo: {exc}", ok=False)
    frame.columns = [str(column).lower().strip() for column in frame.columns]
    missing = {"nombre", "ciudad"} - set(frame.columns)
    if missing:
        return _redirect("/admin", f"Faltan columnas obligatorias: {missing}", ok=False)
    if len(frame) > 100_000:
        return _redirect("/admin", "El archivo supera el máximo de 100.000 filas.", ok=False)

    def value(row, key, default=None):
        item = row.get(key, default)
        return default if pd.isna(item) else item

    inserted = updated = failed = 0
    with open_conn() as conn:
        for _, row in frame.iterrows():
            try:
                site = str(value(row, "sitio_web", "") or "").strip()
                lead = Lead(
                    nombre=str(value(row, "nombre", "") or "").strip(),
                    ciudad=str(value(row, "ciudad", "") or "").strip(),
                    pais=str(value(row, "pais", "") or "").strip() or None,
                    departamento=str(value(row, "departamento", "") or "").strip() or None,
                    nicho=str(value(row, "nicho", "Importado") or "Importado"),
                    fuente="importacion",
                    telefono=str(value(row, "telefono", "") or ""),
                    email=str(value(row, "email", "") or "") or None,
                    sitio_web=site or None,
                    tiene_web=bool(site),
                    rating=_coerce_float(value(row, "rating", 0)) or None,
                    reseñas=_coerce_reviews(value(row, "reseñas", 0)),
                    nit=str(value(row, "nit", "") or "") or None,
                    raw_data={"imported": True},
                )
                result = save_lead(lead, conn)
                inserted += result == 1
                updated += result == 0
                failed += result < 0
            except Exception:
                failed += 1
    invalidate_leads_cache()
    return _redirect(
        "/admin",
        f"Importación lista: {inserted} nuevos, {updated} fusionados, {failed} errores.",
        ok=True,
    )


@app.post("/admin/wipe")
def admin_wipe(confirm: str = Form("")):
    if confirm.strip().upper() != "ELIMINAR":
        return _redirect("/admin", "Escribe ELIMINAR para confirmar el borrado total.", ok=False)
    with open_conn() as conn:
        conn.execute("DELETE FROM leads")
    invalidate_leads_cache()
    return _redirect("/admin", "Base de datos limpiada.", ok=True)


@app.post("/admin/check-meetings")
def admin_check_meetings():
    result = sync_meetings()
    if result.get("skipped"):
        return _redirect("/admin", "Configura CALCOM_API_KEY para confirmar reuniones.", ok=False)
    return _redirect(
        "/admin",
        f"Reuniones: {result['confirmed']} confirmadas, {result['reverted']} revertidas "
        f"({result['checked']} leads revisados, {result['errors']} errores).",
        ok=bool(result["confirmed"] or result["reverted"]),
    )


@app.get("/help")
def help_page():
    path = APP_DIR / "docs" / "flujo.html"
    if not path.exists():
        return _redirect("/", "El documento de flujo no está disponible.", ok=False)
    return FileResponse(path)


# ── Acceso ───────────────────────────────────────────────────────────────────
@app.get("/login")
def login_page(request: Request, next: str = "/"):
    if not auth.is_enabled():
        return _redirect("/")
    return templates.TemplateResponse(
        request, "login.html",
        {"request": request, "error": "", "next": _safe_next(next)},
    )


@app.post("/login")
async def login_submit(request: Request, password: str = Form(""), next: str = Form("/")):
    if not auth.is_enabled():
        return _redirect("/")
    ip = request.client.host if request.client else "desconocido"
    if auth.too_many_attempts(ip):
        return templates.TemplateResponse(
            request, "login.html",
            {"request": request, "error": "Demasiados intentos. Espera 15 minutos.", "next": _safe_next(next)},
            status_code=429,
        )
    if not auth.verify_password(password):
        auth.record_attempt(ip)
        return templates.TemplateResponse(
            request, "login.html",
            {"request": request, "error": "Contraseña incorrecta.", "next": _safe_next(next)},
            status_code=401,
        )
    auth.clear_attempts(ip)
    response = RedirectResponse(_safe_next(next), status_code=303)
    response.set_cookie(
        auth.COOKIE_NAME, auth.make_token(),
        max_age=auth.SESSION_DAYS * 86400, httponly=True, samesite="lax",
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.COOKIE_NAME)
    return response
