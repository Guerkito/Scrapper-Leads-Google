import http.server
import json
import sqlite3
import os
import requests
import datetime
import time
import random
from dotenv import load_dotenv
from db import DB_PATH, init_db, open_conn
from loguru import logger

# Configurar Loguru
logger.add("data/logs/webhook.log", rotation="10 MB", level="INFO")

load_dotenv()
init_db() 

PORT = int(os.getenv("WEBHOOK_PORT", 5001))
EVO_URL = os.getenv("EVO_URL", "http://127.0.0.1:8080")
EVO_API_KEY = os.getenv("EVO_API_KEY", "")
EVO_INSTANCE = os.getenv("EVO_INSTANCE", "onyxbot")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

PROMPTS_POR_SECTOR = {
    "educacion": """Eres un asesor de marketing digital de Onyx. Estás hablando con un colegio.
Tu objetivo: entender si el colegio necesita mejorar su presencia digital para atraer más familias. 
Pregunta por: número de estudiantes, si tienen web actualizada, si hacen publicidad digital.
REGLAS: máximo 2 líneas por mensaje, tono profesional pero cercano, no uses signos de admiración. Tutea siempre.""",
    
    "alimentos": """Eres un asesor de marketing digital de Onyx. Estás hablando con una empresa de alimentos/procesadora. 
Tu objetivo: entender si necesitan presencia B2B online para llegar a distribuidores. 
Pregunta por: si venden a supermercados, si tienen catálogo digital, si buscan expandirse a otras ciudades.
REGLAS: máximo 2 líneas por mensaje, tono empresarial directo. Tutea siempre.""",
    
    "medio_ambiente": """Eres un asesor de Onyx. Estás hablando con una empresa de tratamiento de aguas.
Tu objetivo: entender si necesitan un sitio web para conseguir más contratos con industrias. 
Pregunta por: tipo de clientes que tienen, si consiguen clientes por referidos, si tienen presencia en LinkedIn.
REGLAS: máximo 2 líneas, tono técnico-profesional. Tutea siempre.""",
    
    "general": """Eres el asesor senior de Onyx, agencia de desarrollo de software en Colombia. 
Tu objetivo es calificar leads y agendar llamadas de 20 min.
REGLAS: máximo 2 líneas, tutea, tono colombiano profesional y directo. 
Nunca uses signos de admiración ni frases cliché como 'juntos podemos'."""
}

def get_system_prompt(lead_data: dict) -> str:
    sector = lead_data.get("sector", "general").lower() if lead_data else "general"
    return PROMPTS_POR_SECTOR.get(sector, PROMPTS_POR_SECTOR["general"])

def get_lead_context(remote_jid):
    """Recupera el contexto del lead desde la DB usando su WhatsApp ID."""
    num = "".join(filter(str.isdigit, remote_jid))
    try:
        conn = open_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM leads WHERE telefono LIKE ? OR whatsapp_id = ? LIMIT 1",
            (f"%{num[-10:]}%", remote_jid)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error recuperando contexto: {e}")
        return None

def parse_history(hist_str):
    messages = []
    if not hist_str: return messages
    lines = hist_str.strip().split('\n')
    for line in lines:
        if line.startswith('Usuario: '):
            messages.append({"role": "user", "content": line.replace('Usuario: ', '').strip()})
        elif line.startswith('Onyx: '):
            messages.append({"role": "assistant", "content": line.replace('Onyx: ', '').strip()})
    return messages[-14:]

def ask_ollama(lead_data, message_now):
    system_prompt = get_system_prompt(lead_data)
    history_str = lead_data.get("historial_mensajes", "") if lead_data else ""
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(parse_history(history_str))
    messages.append({"role": "user", "content": message_now})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.4, "num_ctx": 4096}
    }

    try:
        r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=90)
        return r.json().get("message", {}).get("content", "").strip().replace('"', '')
    except Exception as e:
        logger.error(f"Error Ollama: {e}")
        return "Hola, dame un momento y ya te atiendo personalmente."

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            # Manejar evento de mensaje de Evolution API
            if data.get("event") == "messages.upsert":
                msg_obj = data.get("data", {})
                remote_jid = msg_obj.get("key", {}).get("remoteJid")
                from_me = msg_obj.get("key", {}).get("fromMe")
                
                if not from_me and remote_jid:
                    text = msg_obj.get("message", {}).get("conversation") or \
                           msg_obj.get("message", {}).get("extendedTextMessage", {}).get("text")
                    
                    if text:
                        logger.info(f"📩 Mensaje de {remote_jid}: {text}")
                        
                        # 1. Obtener contexto
                        lead_ctx = get_lead_context(remote_jid)
                        if lead_ctx:
                            logger.info(f"🎯 Contexto detectado: Sector={lead_ctx.get('sector')}, Calif={lead_ctx.get('calificacion')}")
                        
                        # 2. Generar respuesta
                        response_text = ask_ollama(lead_ctx, text)
                        
                        # 3. Enviar vía Evolution API
                        send_payload = {
                            "number": remote_jid.split("@")[0],
                            "text": response_text
                        }
                        if not EVO_API_KEY:
                            logger.error("EVO_API_KEY no está configurada; no se enviará respuesta por Evolution API.")
                            self.send_response(500)
                            self.end_headers()
                            return
                        headers = {"apikey": EVO_API_KEY, "Content-Type": "application/json"}
                        requests.post(f"{EVO_URL}/message/sendText/{EVO_INSTANCE}", 
                                      json=send_payload, headers=headers)
                        
                        # 4. Actualizar historial en DB
                        new_history = (lead_ctx.get("historial_mensajes") or "") + \
                                      f"\nUsuario: {text}\nOnyx: {response_text}"
                        
                        try:
                            conn = open_conn()
                            conn.execute(
                                "UPDATE leads SET historial_mensajes = ?, ultima_interaccion = ? WHERE id = ?",
                                (new_history, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), lead_ctx['id'])
                            )
                            # También loguear en bot_logs
                            conn.execute("INSERT INTO bot_logs (mensaje) VALUES (?)", 
                                        (f"IA -> {lead_ctx['nombre']}: {response_text[:50]}...",))
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            logger.error(f"Error actualizando historial: {e}")

            self.send_response(200)
            self.end_headers()
        except Exception as e:
            logger.error(f"Error Webhook: {e}")
            self.send_response(500)
            self.end_headers()

if __name__ == "__main__":
    server = http.server.HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    logger.info(f"🚀 Onyx Webhook v12.0 corriendo en puerto {PORT}")
    server.serve_forever()
