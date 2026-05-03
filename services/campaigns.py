import time
import random
import datetime
import sqlite3
import requests
import streamlit as st
from db import DB_PATH
from services.constants import COUNTRY_CODES

SENT_CACHE = {}

class CampState:
    def __init__(self):
        self.running   = False
        self.logs      = []   # lista de (nivel, mensaje)
        self.progress  = 0.0
        self.countdown = 0
        self.stop      = False

    def reset(self):
        self.running   = True
        self.logs      = []
        self.progress  = 0.0
        self.countdown = 0
        self.stop      = False

    def log(self, level, msg):
        self.logs.append((level, msg))

def campaign_worker(camp_state, leads_data, msg_template, evo_url, evo_instance, evo_key,
                     pais_sel, test_mode):
    """Corre la campaña en un hilo de fondo."""
    try:
        total = len(leads_data)
        for idx, lead in enumerate(leads_data):
            if camp_state.stop:
                camp_state.log("warning", "🛑 Campaña detenida manualmente.")
                break

            num = "".join(filter(str.isdigit, str(lead['telefono'])))
            
            # SEGURO ANTI-DUPLICADOS
            now = time.time()
            if num in SENT_CACHE and (now - SENT_CACHE[num]) < 10:
                camp_state.log("warning", f"🚫 Evitando duplicado para {num}")
                continue
            SENT_CACHE[num] = now

            mensaje = msg_template.replace("{nombre}", str(lead['nombre']))
            num = "".join(filter(str.isdigit, str(lead['telefono'])))
            camp_state.log("info", f"🔍 Procesando: {lead['nombre']} ({num})")
            
            pref = COUNTRY_CODES.get(pais_sel, "")
            if pref and len(num) <= 10:
                if not num.startswith(pref):
                    num = pref + num
                    camp_state.log("info", f"📍 Prefijo {pref} aplicado -> {num}")
            
            if len(num) < 7:
                camp_state.log("warning", f"⚠️ Número inválido, saltando...")
                continue

            sent_ok = False
            no_wa = False

            if test_mode:
                camp_state.log("info", f"🧪 [SIMULACIÓN] → Enviando a {num}")
                time.sleep(1.5)
                sent_ok = True
            else:
                camp_state.log("info", f"📡 Conectando a Evolution API...")
                try:
                    payload = {
                        "number": num,
                        "text": mensaje,
                        "delay": 0,
                        "linkPreview": False
                    }
                    headers = {
                        "apikey": evo_key,
                        "Authorization": f"Bearer {evo_key}",
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true",
                    }
                    
                    r = requests.post(f"{evo_url}/message/sendText/{evo_instance}", json=payload, headers=headers, timeout=30)
                    sent_ok = r.status_code in (200, 201)
                    
                    if not sent_ok:
                        try:
                            resp_data = r.json()
                            exists = None
                            res_obj = resp_data.get("response", {})
                            if isinstance(res_obj, dict):
                                msg_list = res_obj.get("message", [])
                                if isinstance(msg_list, list) and len(msg_list) > 0:
                                    exists = msg_list[0].get("exists")
                                else:
                                    exists = res_obj.get("exists")
                            
                            if exists is None:
                                exists = resp_data.get("exists")
                            
                            if exists == False:
                                no_wa = True
                                camp_state.log("warning", f"📵 El número {num} no tiene WhatsApp. Saltando...")
                            else:
                                camp_state.log("error", f"❌ Error API: {r.text[:200]}")
                        except Exception:
                            camp_state.log("error", f"❌ Error API (no legible): {r.text[:200]}")
                except Exception as e:
                    camp_state.log("error", f"❌ Excepción de red: {e}")

            new_status = None
            if sent_ok:
                new_status = "Contactado"
                label = "Simulado" if test_mode else "Enviado"
                camp_state.log("success", f"✅ {label} correctamente a {lead['nombre']}")
            elif no_wa:
                new_status = "Sin WhatsApp"

            if new_status:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "UPDATE leads SET estado=?, ultima_interaccion=? WHERE id=?",
                        (new_status, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), lead['id']),
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    camp_state.log("warning", f"⚠️ DB error: {e}")

            camp_state.progress = (idx + 1) / total

            if idx < total - 1 and not camp_state.stop:
                espera = random.randint(5, 10) if test_mode else random.randint(120, 300)
                camp_state.log("info", f"⏳ Pausa anti-ban: {espera}s...")
                for s in range(espera, 0, -1):
                    if camp_state.stop: break
                    camp_state.countdown = s
                    time.sleep(1)
                camp_state.countdown = 0

        if not camp_state.stop:
            camp_state.log("success", "🏁 ¡Campaña finalizada con éxito!")
        camp_state.running = False
    except Exception as e:
        camp_state.log("error", f"❌ Error fatal en campaña: {e}")
        camp_state.running = False
