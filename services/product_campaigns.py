"""Portafolio comercial de ONYX para orientar la prospección por oferta."""

from __future__ import annotations

import re
import unicodedata


FREE_CAMPAIGN = "busqueda_libre"


PRODUCT_CAMPAIGNS = {
    FREE_CAMPAIGN: {
        "label": "Búsqueda libre",
        "description": "Busca cualquier tipo de empresa con términos personalizados.",
        "pitch": "Soluciones de software e inteligencia artificial adaptadas a la operación.",
        "decision_roles": ["Gerencia", "Administración", "Tecnología"],
        "recommended_sources": ["Maps"],
        "segments": {},
    },
    "onyx_web": {
        "label": "ONYX · Páginas web",
        "description": (
            "Sitios web rápidos y orientados a convertir visitas en llamadas, reservas "
            "o solicitudes comerciales."
        ),
        "pitch": (
            "Convertir su presencia digital en un canal comercial medible, con una web "
            "rápida, clara y preparada para captar clientes."
        ),
        "decision_roles": ["Propietario", "Gerencia", "Mercadeo", "Administración"],
        "recommended_sources": ["Maps", "Instagram", "Facebook"],
        "match_tokens": [
            "odontologo", "abogado", "contador", "inmobiliaria", "estetica",
            "veterinaria", "taller", "hotel", "colegio", "academia", "fundacion",
        ],
        "service_family": "web",
        "qualification_note": (
            "Validar si tiene web propia, si recibe solicitudes desde ella y cuándo fue "
            "su última actualización."
        ),
        "default_segments": ["servicios_profesionales"],
        "segments": {
            "servicios_profesionales": {
                "label": "Servicios profesionales",
                "queries": ["odontólogo", "abogado", "contador", "inmobiliaria"],
            },
            "negocios_locales": {
                "label": "Negocios locales",
                "queries": ["centro de estética", "veterinaria", "taller mecánico", "hotel"],
            },
            "instituciones": {
                "label": "Educación, academias y fundaciones",
                "queries": ["colegio privado", "academia", "fundación"],
            },
        },
    },
    "onyx_ecommerce": {
        "label": "ONYX · Tiendas y ventas en línea",
        "description": (
            "Catálogos, tiendas en línea, pagos e integración del pedido con la operación."
        ),
        "pitch": (
            "Abrir o mejorar un canal de ventas propio para recibir pedidos y pagos sin "
            "depender por completo de mensajes o plataformas de terceros."
        ),
        "decision_roles": ["Propietario", "Gerencia comercial", "Mercadeo", "Operaciones"],
        "recommended_sources": ["Maps", "Instagram", "Facebook"],
        "match_tokens": [
            "tienda", "ropa", "zapateria", "joyeria", "muebleria", "panaderia",
            "reposteria", "productos naturales", "distribuidor", "mayorista", "importadora",
        ],
        "service_family": "ecommerce",
        "qualification_note": (
            "Validar cómo toma pedidos hoy, si cobra en línea y cuánto trabajo manual "
            "requiere confirmar inventario, pago y despacho."
        ),
        "default_segments": ["comercio_minorista"],
        "segments": {
            "comercio_minorista": {
                "label": "Comercio minorista",
                "queries": ["tienda de ropa", "zapatería", "joyería", "mueblería"],
            },
            "alimentos_catalogo": {
                "label": "Alimentos con catálogo",
                "queries": ["panadería", "repostería", "café especial", "productos naturales"],
            },
            "mayoristas": {
                "label": "Distribuidores, mayoristas e importadores",
                "queries": ["distribuidora", "mayorista", "importadora"],
            },
        },
    },
    "onyx_automation": {
        "label": "ONYX · Automatizaciones",
        "description": (
            "Automatización de tareas repetitivas, documentos, seguimiento comercial "
            "y flujos entre herramientas."
        ),
        "pitch": (
            "Reducir tareas manuales y errores conectando el proceso actual para que el "
            "equipo dedique más tiempo a vender y operar."
        ),
        "decision_roles": [
            "Gerencia", "Operaciones", "Administración", "Tecnología", "Gerencia comercial"
        ],
        "recommended_sources": ["Maps", "LinkedIn", "Computrabajo (B2B)"],
        "match_tokens": [
            "logistica", "transporte", "fabrica", "distribuidora", "contador",
            "abogado", "inmobiliaria", "seguros", "contact center", "mantenimiento",
        ],
        "service_family": "automation",
        "qualification_note": (
            "Preguntar qué tarea repite el equipo cada día, dónde copia información a "
            "mano y qué demora más una venta o entrega."
        ),
        "default_segments": ["operaciones"],
        "segments": {
            "operaciones": {
                "label": "Logística, transporte y producción",
                "queries": ["empresa de logística", "empresa de transporte", "fábrica", "distribuidora"],
            },
            "administracion": {
                "label": "Procesos administrativos y comerciales",
                "queries": ["firma de contadores", "firma de abogados", "inmobiliaria", "empresa de seguros"],
            },
            "servicio_cliente": {
                "label": "Atención y servicios recurrentes",
                "queries": ["contact center", "empresa de mantenimiento", "empresa de servicios empresariales"],
            },
        },
    },
    "onyx_ai_integrations": {
        "label": "ONYX · IA e integraciones",
        "description": (
            "Asistentes de IA, análisis documental e integraciones con los sistemas que "
            "la empresa ya utiliza."
        ),
        "pitch": (
            "Aplicar IA a un proceso concreto y conectarla con sus herramientas actuales "
            "para responder, clasificar o analizar información con supervisión humana."
        ),
        "decision_roles": ["Gerencia", "Tecnología", "Innovación", "Operaciones", "Servicio al cliente"],
        "recommended_sources": ["LinkedIn", "Computrabajo (B2B)", "Maps"],
        "match_tokens": [
            "contador", "abogado", "aseguradora", "cobranzas", "contact center",
            "bpo", "viajes", "inmobiliaria", "universidad", "consultoria",
        ],
        "service_family": "ai",
        "qualification_note": (
            "Validar qué información revisa o responde el equipo en volumen, qué sistemas "
            "usa y qué decisión siempre debe conservar una persona."
        ),
        "default_segments": ["documentos"],
        "segments": {
            "documentos": {
                "label": "Documentos, auditoría y clasificación",
                "queries": ["firma de contadores", "firma de abogados", "aseguradora", "empresa de cobranzas"],
            },
            "atencion": {
                "label": "Atención y respuesta al cliente",
                "queries": ["contact center", "BPO", "agencia de viajes", "inmobiliaria"],
            },
            "conocimiento": {
                "label": "Educación y servicios de conocimiento",
                "queries": ["universidad", "instituto de educación", "empresa de consultoría"],
            },
        },
    },
    "onyx_custom_software": {
        "label": "ONYX · Software a medida",
        "description": (
            "Sistemas web y móviles construidos alrededor de procesos que un software "
            "genérico no resuelve bien."
        ),
        "pitch": (
            "Centralizar su operación en un sistema hecho para el proceso real de la "
            "empresa, con trazabilidad, permisos e indicadores."
        ),
        "decision_roles": ["Gerencia general", "Operaciones", "Tecnología", "Dirección financiera"],
        "recommended_sources": ["LinkedIn", "Computrabajo (B2B)", "Maps"],
        "match_tokens": [
            "logistica", "transporte", "fabrica", "constructora", "cadena", "grupo",
            "propiedad horizontal", "asociacion", "distribuidora", "inmobiliaria",
        ],
        "service_family": "custom_software",
        "qualification_note": (
            "Validar si opera con hojas de cálculo o sistemas desconectados, cuántas "
            "personas intervienen y dónde pierde trazabilidad."
        ),
        "default_segments": ["operacion_compleja"],
        "segments": {
            "operacion_compleja": {
                "label": "Operación compleja",
                "queries": ["empresa de logística", "empresa de transporte", "fábrica", "constructora"],
            },
            "multisede": {
                "label": "Empresas con varias sedes",
                "queries": ["cadena de tiendas", "cadena de gimnasios", "colegio privado", "grupo empresarial"],
            },
            "portales": {
                "label": "Portales para clientes, aliados o asociados",
                "queries": ["inmobiliaria", "administración de propiedad horizontal", "asociación empresarial", "distribuidora"],
            },
        },
    },
    "watson_clinic": {
        "label": "Watson Clinic",
        "description": (
            "Asistente de documentación clínica con IA para grabar, transcribir y "
            "estructurar la consulta bajo revisión del profesional."
        ),
        "pitch": (
            "Reducir el tiempo administrativo de los profesionales y dejar la "
            "documentación clínica lista para revisión."
        ),
        "decision_roles": [
            "Gerencia", "Dirección médica", "Jefatura de sistemas", "Calidad clínica"
        ],
        "qualification_note": (
            "Validar cuántos profesionales documentan consultas, cuánto tardan y cómo "
            "revisan la historia antes de firmarla."
        ),
        "recommended_sources": ["Maps", "Doctoralia (Salud)"],
        "match_tokens": ["ips", "clinica", "hospital", "centro medico", "especialistas"],
        "segments": {
            "ips_privadas": {
                "label": "IPS y clínicas privadas",
                "queries": ["IPS", "clínica médica", "centro médico", "centro de especialistas"],
            },
            "ese_publicas": {
                "label": "ESE y hospitales públicos",
                "queries": ["ESE hospital", "hospital municipal", "centro de salud municipal"],
            },
        },
    },
    "watson_auditor_ips": {
        "label": "Watson Auditor · IPS",
        "description": (
            "Preauditoría con IA de cuentas médicas antes de presentarlas a las EPS."
        ),
        "pitch": (
            "Detectar inconsistencias antes del envío para reducir devoluciones, "
            "reprocesos y glosas."
        ),
        "decision_roles": [
            "Gerencia", "Auditoría médica", "Facturación", "Dirección financiera", "Sistemas"
        ],
        "qualification_note": (
            "Validar volumen mensual de cuentas, causas frecuentes de devolución o glosa "
            "y tiempo invertido en la preauditoría."
        ),
        "recommended_sources": ["Maps", "LinkedIn", "Doctoralia (Salud)"],
        "match_tokens": ["ips", "clinica", "hospital", "centro medico"],
        "segments": {
            "ips_privadas": {
                "label": "IPS y clínicas privadas",
                "queries": ["IPS de salud", "clínica médica", "hospital privado", "centro médico"],
            },
            "ese_publicas": {
                "label": "ESE y hospitales públicos",
                "queries": ["ESE hospital", "hospital municipal", "hospital público"],
            },
        },
    },
    "watson_auditor_eps": {
        "label": "Watson Auditor · EPS",
        "description": (
            "Auditoría asistida por IA para revisar y priorizar cuentas médicas recibidas."
        ),
        "pitch": (
            "Acelerar la revisión de cuentas recibidas y enfocar al equipo auditor en "
            "los casos de mayor riesgo."
        ),
        "decision_roles": [
            "Auditoría médica", "Cuentas médicas", "Operaciones", "Tecnología", "Vicepresidencia de salud"
        ],
        "qualification_note": (
            "Validar volumen de cuentas recibidas, reglas de priorización y dónde se "
            "concentra hoy el trabajo manual del equipo auditor."
        ),
        "recommended_sources": ["Maps", "LinkedIn"],
        "match_tokens": ["eps", "promotora de salud", "aseguradora de salud"],
        "segments": {
            "eps": {
                "label": "EPS y aseguradores en salud",
                "queries": ["EPS", "entidad promotora de salud", "aseguradora de salud"],
            },
        },
    },
    "divi_restaurantes": {
        "label": "DIVI · Restaurantes",
        "description": (
            "División de cuenta y pago desde la mesa para agilizar el cierre del servicio."
        ),
        "pitch": (
            "Reducir el tiempo para dividir y cobrar cuentas, evitando filas y errores al pagar."
        ),
        "decision_roles": ["Propietario", "Gerencia", "Administración", "Operaciones"],
        "qualification_note": (
            "Validar cuántas mesas maneja, cuánto tarda en dividir y cobrar una cuenta y "
            "si ya integra pagos con su sistema de ventas."
        ),
        "recommended_sources": ["Maps", "TripAdvisor", "Instagram"],
        "match_tokens": ["restaurante", "gastrobar", "bar restaurante"],
        "segments": {
            "servicio_mesa": {
                "label": "Restaurantes con servicio a la mesa",
                "queries": ["restaurante con servicio a la mesa", "restaurante familiar", "restaurante"],
            },
            "gastrobares": {
                "label": "Gastrobares y bares con mesa",
                "queries": ["gastrobar", "bar restaurante"],
            },
            "cadenas": {
                "label": "Cadenas y restaurantes con varias sedes",
                "queries": ["cadena de restaurantes", "restaurante varias sedes"],
            },
        },
    },
}


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def get_campaign(campaign_key: str | None) -> dict:
    return PRODUCT_CAMPAIGNS.get(campaign_key or FREE_CAMPAIGN, PRODUCT_CAMPAIGNS[FREE_CAMPAIGN])


def campaign_label(campaign_key: str | None) -> str:
    return get_campaign(campaign_key)["label"]


def campaign_options() -> list[str]:
    return list(PRODUCT_CAMPAIGNS)


def segment_options(campaign_key: str | None) -> list[str]:
    return list(get_campaign(campaign_key).get("segments", {}))


def default_segments(campaign_key: str | None) -> list[str]:
    campaign = get_campaign(campaign_key)
    configured = campaign.get("default_segments")
    return valid_segments(campaign_key, configured) if configured else segment_options(campaign_key)


def valid_segments(campaign_key: str | None, selected: list[str] | None) -> list[str]:
    available = segment_options(campaign_key)
    wanted = available if selected is None else selected
    return [key for key in wanted if key in available]


def segment_label(campaign_key: str | None, segment_key: str | None) -> str:
    segment = get_campaign(campaign_key).get("segments", {}).get(segment_key or "", {})
    return segment.get("label", "Sin segmento")


def build_search_terms(campaign_key: str | None, selected: list[str] | None) -> list[str]:
    campaign = get_campaign(campaign_key)
    terms = []
    for key in valid_segments(campaign_key, selected):
        terms.extend(campaign["segments"][key].get("queries", []))
    return list(dict.fromkeys(term for term in terms if str(term).strip()))


def segment_for_query(
    campaign_key: str | None, query: str, selected: list[str] | None
) -> str:
    normalized_query = _normalize(query)
    campaign = get_campaign(campaign_key)
    valid = valid_segments(campaign_key, selected)
    for key in valid:
        queries = campaign["segments"][key].get("queries", [])
        if normalized_query in {_normalize(item) for item in queries}:
            return key
    return valid[0] if valid else ""


def recommended_sources(campaign_key: str | None) -> list[str]:
    return list(get_campaign(campaign_key).get("recommended_sources", ["Maps"]))


def _has_value(value: object) -> bool:
    return str(value or "").strip().casefold() not in {
        "", "n/a", "nan", "none", "null", "sin sitio web"
    }


def score_campaign_lead(lead, campaign_key: str | None) -> tuple[int, str]:
    """Puntúa afinidad con evidencia disponible, sin fingir necesidades no verificadas."""
    campaign = get_campaign(campaign_key)
    score = 35
    reasons = ["Coincide con el tipo de cliente buscado"]

    searchable = _normalize(
        " ".join([
            getattr(lead, "nombre", "") or "",
            getattr(lead, "nicho", "") or "",
            getattr(lead, "sector", "") or "",
        ])
    )
    if any(_normalize(token) in searchable for token in campaign.get("match_tokens", [])):
        score += 15
        reasons.append("el nombre o nicho coincide con la oferta seleccionada")

    if _has_value(getattr(lead, "telefono_e164", None) or getattr(lead, "telefono", None)):
        score += 15
        reasons.append("tiene teléfono público")
    if _has_value(getattr(lead, "email", None)):
        score += 10
        reasons.append("tiene correo de contacto")
    has_website = _has_value(getattr(lead, "sitio_web", None))
    family = campaign.get("service_family", "product")
    if family == "web":
        if has_website:
            score += 3
            reasons.append("tiene un sitio que se puede auditar por vigencia y conversión")
        else:
            score += 20
            reasons.append("no se capturó sitio web y conviene verificar esa oportunidad")
    elif family == "ecommerce":
        if has_website:
            score += 5
            reasons.append("tiene presencia web para validar si ya vende y cobra en línea")
        else:
            score += 15
            reasons.append("no se capturó sitio web y conviene validar su canal de pedidos")
    elif has_website:
        score += 8 if family in {"automation", "ai", "custom_software"} else 5
        reasons.append("tiene presencia digital para investigar su operación")

    source = _normalize(getattr(lead, "fuente", ""))
    if family in {"automation", "ai", "custom_software"} and any(
        token in source for token in ("linkedin", "computrabajo", "glassdoor")
    ):
        score += 8
        reasons.append("la fuente aporta una señal de estructura empresarial")

    try:
        reviews = int(getattr(lead, "reseñas", 0) or 0)
    except (TypeError, ValueError):
        reviews = 0
    if reviews >= 100:
        score += 15
        reasons.append("el volumen de reseñas sugiere alta operación")
    elif reviews >= 30:
        score += 10
        reasons.append("las reseñas sugieren operación activa")
    elif reviews >= 10:
        score += 5

    try:
        rating = float(getattr(lead, "rating", 0) or 0)
    except (TypeError, ValueError):
        rating = 0
    if rating >= 4.3:
        score += 5

    return min(score, 100), "; ".join(reasons)


def apply_campaign_context(
    lead,
    campaign_key: str | None,
    selected_segments: list[str] | None,
    source_query: str = "",
):
    """Adjunta una oportunidad comercial al lead para persistirla por separado."""
    key = campaign_key or FREE_CAMPAIGN
    if key == FREE_CAMPAIGN:
        return lead

    campaign = get_campaign(key)
    target_key = segment_for_query(key, source_query, selected_segments)
    score, reason = score_campaign_lead(lead, key)
    lead.campaign_key = key
    lead.campaign_label = campaign["label"]
    lead.target_segment_key = target_key
    lead.target_segment = segment_label(key, target_key)
    lead.fit_score = score
    lead.fit_reason = reason
    lead.pitch_sugerido = campaign["pitch"]
    lead.decision_roles = " · ".join(campaign["decision_roles"])
    lead.source_query = source_query
    return lead
