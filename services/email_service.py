import smtplib
import re
import ssl
import uuid
import time
import random
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import email_settings
from db import claim_campaign_destination, finish_campaign_destination, open_conn
from services.campaigns import CampState
from services.leads import invalidate_leads_cache

def send_email(to_email, subject, body, html=True):
    """Envía un correo electrónico simple vía SMTP."""
    settings = email_settings()
    if not settings["user"] or not settings["pass"]:
        return False, "Configuración de email incompleta en el archivo .env"
    
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{settings['from_name']} <{settings['user']}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
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

def email_campaign_worker(camp_state, leads_data, subject, body_template, test_mode):
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
            personalized_subject = subject
            for key in ("nombre", "nicho", "ciudad", "rating"):
                personalized_subject = personalized_subject.replace(
                    f"{{{key}}}", str(lead.get(key) or "")
                )

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
