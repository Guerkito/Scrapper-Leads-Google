import smtplib
import re
import ssl
import uuid
import time
import random
import datetime
import json
import requests
from loguru import logger
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import (
    CALCOM_LINK,
    OLLAMA_CHAT_URL,
    OLLAMA_MODEL,
    RESEND_API_KEY,
    SENDER_DAILY_LIMIT,
    SENDER_FROM_EMAIL,
    SENDER_PROVIDER,
    email_settings,
)
from db import claim_campaign_destination, finish_campaign_destination, open_conn
from services.campaigns import CampState
from services.leads import invalidate_leads_cache


PERSONALIZE_PROMPT = """Eres un vendedor B2B experto. Personaliza este correo para el \
negocio destino usando solo los datos dados.

Reglas:
- Máximo 120 palabras, en español, tono humano y directo.
- Un solo llamado a la acción: una llamada de 10 minutos.
- Si hay nombre de decisor, salúdalo por su nombre; si no, usa el negocio.
- No inventes datos ni prometas resultados.
{link_rule}
- Devuelve SOLO JSON: {{"subject": "...", "body": "..."}}. Cuerpo en texto plano.

Datos del negocio destino:
{lead}

Asunto base: {subject}
Plantilla base: {template}
"""


def personalize_email(lead: dict, subject: str, body_template: str) -> tuple[str, str]:
    """Reescribe asunto y cuerpo para un lead concreto con el LLM local.

    Si Ollama falla, devuelve la plantilla original sin interrumpir la campaña.
    """
    context = {
        "negocio": str(lead.get("nombre") or "")[:120],
        "nicho": str(lead.get("nicho") or "")[:120],
        "ciudad": str(lead.get("ciudad") or "")[:80],
        "rating": lead.get("rating"),
        "sector": str(lead.get("sector") or "")[:80],
        "propuesta": str(lead.get("pitch_sugerido") or lead.get("producto_principal") or "")[:300],
        "motivo_afinidad": str(lead.get("motivo_afinidad") or "")[:300],
        "decisor": str(lead.get("decisor_nombre") or "")[:80],
        "cargo_decisor": str(lead.get("decisor_cargo") or "")[:80],
    }
    prompt = PERSONALIZE_PROMPT.format(
        link_rule=(
            f"Al final incluye este enlace de agenda: {CALCOM_LINK}" if CALCOM_LINK else ""
        ),
        lead=json.dumps(context, ensure_ascii=False),
        subject=subject,
        template=body_template,
    )
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=180)
        response.raise_for_status()
        data = json.loads(response.json().get("message", {}).get("content", "{}"))
        new_body = str(data.get("body") or "").strip()
        if not new_body:
            raise ValueError("cuerpo vacío")
        new_subject = str(data.get("subject") or subject).strip()[:200]
        return new_subject, new_body
    except Exception as exc:
        logger.warning(f"Email IA: sin personalización para {context['negocio']} ({exc})")
        return subject, body_template

def _daily_limit_reached() -> bool:
    if SENDER_DAILY_LIMIT <= 0:
        return False
    try:
        with open_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM email_sends WHERE date(created_at) = date('now')"
            ).fetchone()
        return (row[0] if row else 0) >= SENDER_DAILY_LIMIT
    except Exception as exc:
        logger.warning(f"No se pudo verificar el límite diario de envíos: {exc}")
        return False


def _record_send(destination: str, provider: str) -> None:
    try:
        with open_conn() as conn:
            conn.execute(
                "INSERT INTO email_sends (destino, provider) VALUES (?, ?)",
                (destination, provider),
            )
    except Exception as exc:
        logger.warning(f"No se pudo registrar el envío a {destination}: {exc}")


def _send_smtp(settings, to_email, subject, body, html, in_reply_to):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{settings['from_name']} <{settings['user']}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
            msg['References'] = in_reply_to

        # El cuerpo puede ser HTML o texto plano
        content_type = 'html' if html else 'plain'
        msg.attach(MIMEText(body, content_type))

        # Conexión SMTP
        with smtplib.SMTP(settings["host"], settings["port"], timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(settings["user"], settings["pass"])
            server.send_message(msg)

        return True, "Enviado"
    except Exception as e:
        return False, str(e)


def _send_resend(settings, to_email, subject, body, html, in_reply_to):
    payload = {
        "from": f"{settings['from_name']} <{SENDER_FROM_EMAIL or settings['user']}>",
        "to": [to_email],
        "subject": subject,
    }
    if html:
        payload["html"] = body
    else:
        payload["text"] = body
    if in_reply_to:
        payload["headers"] = {"In-Reply-To": in_reply_to, "References": in_reply_to}
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            return False, f"Resend {response.status_code}: {response.text[:300]}"
        return True, "Enviado"
    except Exception as e:
        return False, str(e)


def send_email(to_email, subject, body, html=True, in_reply_to=None):
    """Envía un correo por el proveedor configurado (SMTP o Resend)."""
    settings = email_settings()
    if _daily_limit_reached():
        return False, f"Límite diario de envíos alcanzado ({SENDER_DAILY_LIMIT})"
    if SENDER_PROVIDER == "resend":
        if not RESEND_API_KEY:
            return False, "SENDER_PROVIDER=resend requiere RESEND_API_KEY en el .env"
        ok, message = _send_resend(settings, to_email, subject, body, html, in_reply_to)
    else:
        if not settings["user"] or not settings["pass"]:
            return False, "Configuración de email incompleta en el archivo .env"
        ok, message = _send_smtp(settings, to_email, subject, body, html, in_reply_to)
    if ok:
        _record_send(to_email, SENDER_PROVIDER)
    return ok, message

def email_campaign_worker(camp_state, leads_data, subject, body_template, test_mode, use_llm=False):
    """Corre la campaña de email en un hilo de fondo (thread)."""
    try:
        if not camp_state.campaign_id:
            camp_state.campaign_id = uuid.uuid4().hex
        total = len(leads_data)
        for idx, lead in enumerate(leads_data):
            if camp_state.stop:
                camp_state.log("warning", "Campaña de email detenida manualmente.")
                break

            email_addr = str(lead.get('email', '')).strip()
            # Validación básica de email (la clase \s excluye saltos de línea)
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email_addr):
                camp_state.log("warning", f"Lead '{lead['nombre']}' no tiene email válido. Saltando...")
                camp_state.progress = (idx + 1) / max(total, 1)
                continue
            if str(lead.get("estado_contacto", "")).casefold() == "no_contactar":
                camp_state.log("warning", f"Suprimido por no contactar: {lead.get('nombre', '')}")
                camp_state.progress = (idx + 1) / max(total, 1)
                continue
            destination = email_addr.casefold()
            if not claim_campaign_destination(
                camp_state.campaign_id, "email", lead.get("id"), destination
            ):
                camp_state.log("warning", f"{destination} ya fue procesado en esta campaña.")
                camp_state.progress = (idx + 1) / max(total, 1)
                continue

            camp_state.log("info", f"Procesando: {lead['nombre']} ({email_addr})")
            
            # Personalizar el cuerpo del mensaje
            body = body_template.replace("{nombre}", str(lead.get('nombre', 'propietario')))
            body = body.replace("{nicho}", str(lead.get('nicho', 'negocio')))
            body = body.replace("{ciudad}", str(lead.get('ciudad', 'tu ciudad')))
            body = body.replace("{rating}", str(lead.get('rating', 'N/A')))
            body = body.replace("{decisor}", str(lead.get('decisor_nombre') or 'propietario'))
            body = body.replace("{link_agenda}", CALCOM_LINK)
            personalized_subject = subject.replace("{link_agenda}", CALCOM_LINK)
            personalized_subject = personalized_subject.replace(
                "{decisor}", str(lead.get("decisor_nombre") or "")
            )
            for key in ("nombre", "nicho", "ciudad", "rating"):
                personalized_subject = personalized_subject.replace(
                    f"{{{key}}}", str(lead.get(key) or "")
                )

            if use_llm:
                llm_subject, llm_body = personalize_email(dict(lead), personalized_subject, body)
                if llm_body != body:
                    camp_state.log("info", f"Correo personalizado con IA para {lead['nombre']}")
                    body = llm_body.replace("\n", "<br>")
                    personalized_subject = llm_subject

            sent_ok = False
            error_msg = ""

            if test_mode:
                camp_state.log("info", f"[SIMULACIÓN] Enviando email a {email_addr}")
                sent_ok = True
                finish_campaign_destination(
                    camp_state.campaign_id, "email", destination, "simulated"
                )
            else:
                sent_ok, error_msg = send_email(email_addr, personalized_subject, body)
                if not sent_ok:
                    finish_campaign_destination(
                        camp_state.campaign_id, "email", destination, "error", error=error_msg[:500]
                    )
                    camp_state.log("error", f"Error enviando a {email_addr}: {error_msg}")

            if sent_ok:
                label = "Simulado" if test_mode else "Enviado"
                camp_state.log("success", f"{label} correctamente a {lead['nombre']}")
                
                # Actualizar estado en DB si no es modo test
                if not test_mode:
                    try:
                        finish_campaign_destination(
                            camp_state.campaign_id, "email", destination, "sent"
                        )
                        with open_conn() as conn:
                            conn.execute(
                                "UPDATE leads SET estado=?, ultima_interaccion=? WHERE id=?",
                                ("Contactado", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), lead['id']),
                            )
                    except Exception as e:
                        camp_state.log("warning", f"Error al actualizar DB: {e}")

            # Actualizar progreso
            camp_state.progress = (idx + 1) / total

            # Pausa entre envíos para evitar ser marcado como spam
            if idx < total - 1 and not camp_state.stop:
                espera = 0 if test_mode else random.randint(45, 120)
                camp_state.log("info", f"Pausa de seguridad: {espera}s...")
                for s in range(espera, 0, -1):
                    if camp_state.stop: break
                    camp_state.countdown = s
                    time.sleep(1)
                camp_state.countdown = 0

        if not camp_state.stop:
            camp_state.log("success", "Campaña de email completada.")
    except Exception as e:
        camp_state.log("error", f"Error crítico en campaña: {e}")
    finally:
        invalidate_leads_cache()
        camp_state.running = False
