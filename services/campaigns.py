import time
import random
import datetime
import threading
import requests
import uuid
from loguru import logger
from config import evo_headers
from db import (
    claim_campaign_destination,
    finish_campaign_destination,
    open_conn,
)
from services.phone_utils import phone_digits
from services.leads import invalidate_leads_cache

SENT_CACHE = {}
SENT_CACHE_TTL = 86400  # segunda defensa durante 24 horas
SENT_CACHE_MAX = 5000
_SENT_LOCK = threading.Lock()


def _prune_sent_cache(now):
    """Limpia entradas expiradas y limita tamaño máximo."""
    expired = [k for k, t in SENT_CACHE.items() if now - t > SENT_CACHE_TTL]
    for k in expired:
        SENT_CACHE.pop(k, None)
    if len(SENT_CACHE) > SENT_CACHE_MAX:
        # Mantener solo los más recientes
        oldest = sorted(SENT_CACHE.items(), key=lambda kv: kv[1])[: len(SENT_CACHE) - SENT_CACHE_MAX]
        for k, _ in oldest:
            SENT_CACHE.pop(k, None)

class CampState:
    def __init__(self):
        self.running   = False
        self.logs      = []   # lista de (nivel, mensaje)
        self.progress  = 0.0
        self.countdown = 0
        self.stop      = False
        self.campaign_id = None

    def reset(self, campaign_id=None):
        self.running   = True
        self.logs      = []
        self.progress  = 0.0
        self.countdown = 0
        self.stop      = False
        self.campaign_id = campaign_id or uuid.uuid4().hex

    def log(self, level, msg):
        self.logs.append((level, msg))

def _check_whatsapp_exists(evo_url, evo_instance, evo_key, num):
    """Consulta el endpoint isOnWhatsApp de Evolution para clasificar fallos de envío."""
    try:
        headers = evo_headers({"apikey": evo_key})
        resp = requests.get(
            f"{evo_url}/chat/isOnWhatsApp/{evo_instance}",
            params={"number": num},
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            body = resp.json()
            if isinstance(body, dict) and "exists" in body:
                return bool(body.get("exists"))
    except Exception:
        pass
    return None


def campaign_worker(camp_state, leads_data, msg_template, evo_url, evo_instance, evo_key,
                     pais_sel, test_mode, delay_range=(120, 300)):
    """Corre la campaña en un hilo de fondo."""
    try:
        if not camp_state.campaign_id:
            camp_state.campaign_id = uuid.uuid4().hex
        total = len(leads_data)
        for idx, lead in enumerate(leads_data):
            try:
                if camp_state.stop:
                    camp_state.log("warning", "Campaña detenida manualmente.")
                    break
                if str(lead.get("estado_contacto", "")).casefold() == "no_contactar":
                    camp_state.log("warning", f"Suprimido por no contactar: {lead.get('nombre', '')}")
                    continue

                country = lead.get("pais")
                if str(country).strip().casefold() in {"", "nan", "none", "null"}:
                    country = pais_sel
                phone_value = lead.get("telefono_e164")
                if str(phone_value).strip().casefold() in {"", "nan", "none", "null", "n/a"}:
                    phone_value = lead.get("telefono")
                num = phone_digits(phone_value, country)
                if not num:
                    camp_state.log("warning", f"Número inválido para {lead.get('nombre', '')}; omitido.")
                    continue

                now = time.time()
                _prune_sent_cache(now)
                if not test_mode and num in SENT_CACHE and (now - SENT_CACHE[num]) < SENT_CACHE_TTL:
                    camp_state.log("warning", f"Evitando duplicado reciente para {num}")
                    continue
                if not claim_campaign_destination(
                    camp_state.campaign_id, "whatsapp", lead.get("id"), num
                ):
                    camp_state.log("warning", f"{num} ya fue procesado en esta campaña.")
                    continue

                mensaje = msg_template
                for key in ("nombre", "nicho", "ciudad", "rating"):
                    mensaje = mensaje.replace(f"{{{key}}}", str(lead.get(key) or ""))
                camp_state.log("info", f"Procesando: {lead.get('nombre', '')} ({num})")

                if test_mode:
                    finish_campaign_destination(
                        camp_state.campaign_id, "whatsapp", num, "simulated"
                    )
                    camp_state.log("success", f"Simulado correctamente para {lead.get('nombre', '')}")
                    continue

                payload = {"number": num, "text": mensaje, "delay": 0, "linkPreview": False}
                headers = evo_headers({"Authorization": f"Bearer {evo_key}"})
                headers["apikey"] = evo_key
                response_data = {}
                try:
                    response = requests.post(
                        f"{evo_url}/message/sendText/{evo_instance}",
                        json=payload, headers=headers, timeout=30,
                    )
                    response_data = response.json() if response.content else {}
                    # Evolution puede devolver HTTP 200/201 con error lógico en el body.
                    if isinstance(response_data, dict) and response_data.get("error"):
                        raise RuntimeError(str(response_data["error"])[:500])
                    response.raise_for_status()
                    provider_id = (
                        response_data.get("key", {}).get("id")
                        if isinstance(response_data, dict) else None
                    )
                    # El envío YA ocurrió: si falla el registro interno NO debe
                    # marcar el evento como error, o al reanudar se reenviaría
                    # un WhatsApp duplicado al mismo cliente.
                    try:
                        finish_campaign_destination(
                            camp_state.campaign_id, "whatsapp", num, "sent",
                            provider_message_id=provider_id,
                        )
                        with _SENT_LOCK:
                            SENT_CACHE[num] = time.time()
                        with open_conn() as conn:
                            conn.execute(
                                "UPDATE leads SET estado='Contactado', ultima_interaccion=? WHERE id=?",
                                (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), lead.get("id")),
                            )
                        camp_state.log("success", f"Enviado correctamente a {lead.get('nombre', '')}")
                    except Exception as bookkeeping_error:
                        logger.warning(
                            f"Enviado a {num} pero falló el registro interno: {bookkeeping_error}"
                        )
                        camp_state.log(
                            "success",
                            f"Enviado a {lead.get('nombre', '')} (no se pudo registrar el envío)",
                        )
                except Exception as exc:
                    error = str(exc)[:500]
                    exists = _check_whatsapp_exists(evo_url, evo_instance, evo_key, num)
                    no_wa = exists is False
                    status = "no_whatsapp" if no_wa else "error"
                    finish_campaign_destination(
                        camp_state.campaign_id, "whatsapp", num, status, error=error
                    )
                    if no_wa:
                        with open_conn() as conn:
                            conn.execute("UPDATE leads SET estado='Sin WhatsApp' WHERE id=?", (lead.get("id"),))
                    camp_state.log("error", f"No se pudo enviar a {num}: {error}")

                if idx < total - 1 and not camp_state.stop:
                    low, high = sorted((max(0, int(delay_range[0])), max(0, int(delay_range[1]))))
                    # En simulación no hay envíos reales: sin pausa (igual que email).
                    espera = 0 if test_mode else (random.randint(low, high) if high else 0)
                    if espera:
                        camp_state.log("info", f"Pausa configurada: {espera}s...")
                    for seconds in range(espera, 0, -1):
                        if camp_state.stop:
                            break
                        camp_state.countdown = seconds
                        time.sleep(1)
                    camp_state.countdown = 0
            finally:
                camp_state.progress = (idx + 1) / max(total, 1)

        if not camp_state.stop:
            camp_state.log("success", "Campaña finalizada con éxito.")
    except Exception as e:
        camp_state.log("error", f"Error fatal en campaña: {e}")
    finally:
        invalidate_leads_cache()
        camp_state.running = False
