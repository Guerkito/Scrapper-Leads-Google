import http.server
import json
import sqlite3
import os
import requests
from dotenv import load_dotenv

# Cargar configuración desde .env
load_dotenv()

PORT = int(os.getenv("PORT", 5001))
DB_PATH = os.getenv("DB_PATH", "data/leads.db")
EVO_URL = os.getenv("EVO_URL", "http://localhost:8080")
EVO_API_KEY = os.getenv("EVO_API_KEY", "")
EVO_INSTANCE = os.getenv("EVO_INSTANCE", "onyxbot")

# Configuración de Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

def get_lead_info(phone):
    """Busca info del lead en la DB por teléfono (limpio)."""
    if not os.path.exists(DB_PATH): return None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM leads WHERE telefono LIKE ? ORDER BY id DESC LIMIT 1",
            (f"%{phone}%",)
        )
        lead = cursor.fetchone()
        conn.close()
        return lead
    except: return None

def update_lead_status_and_history(lead_id, status, history, bot_pause=1):
    """Actualiza el estado y el historial del lead."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE leads SET estado=?, bot_pausado=?, historial_mensajes=? WHERE id=?",
            (status, bot_pause, history, lead_id)
        )
        conn.commit(); conn.close()
    except Exception as e:
        print(f"Error guardando historial: {e}")

def get_system_prompt():
    """Lee el prompt de instrucciones desde el archivo de texto."""
    try:
        with open("bot_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        # Fallback de emergencia por si el archivo no existe
        return "Responde como experto en marketing para {nombre} de {nicho}. Historial:\n{historial}\n\nMensaje: {mensaje}\nTu respuesta:"

def ask_ollama(prompt):
    """Consulta al modelo local de Ollama."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7, # Más creatividad para que suene natural
            "num_predict": 100  # Respuestas cortas por WhatsApp
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=40)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"⚠️ Error conectando con Ollama: {e}")
    return None

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            
            # Evitar responder a nuestros propios mensajes (fromMe)
            if 'data' in data and data['data'].get('key', {}).get('fromMe', False) == True:
                self.send_response(200)
                self.end_headers()
                return

            # Detectar el remitente y el mensaje
            sender = ""
            msg_text = ""
            
            if 'data' in data:
                sender = data['data'].get('key', {}).get('remoteJid', '') or data['data'].get('from', '')
                
                msg_obj = data['data'].get('message', {})
                msg_text = msg_obj.get('conversation', '')
                if not msg_text and msg_obj.get('extendedTextMessage'):
                    msg_text = msg_obj.get('extendedTextMessage', {}).get('text', '')
                if not msg_text:
                    msg_text = data['data'].get('pushName', '')
            
            clean_number = "".join(filter(str.isdigit, sender.split('@')[0]))
            
            if clean_number and msg_text:
                print(f"📩 Mensaje de {clean_number}: {msg_text[:50]}...")
                
                lead = get_lead_info(clean_number)
                
                if lead:
                    name = lead['nombre']
                    nicho = lead['nicho']
                    historial_previo = lead['historial_mensajes'] or ""
                    print(f"👤 Lead identificado: {name} ({nicho})")
                    
                    # 1. Agregar nuevo mensaje del cliente al historial
                    nuevo_historial = f"{historial_previo}\n[Cliente]: {msg_text}".strip()
                    
                    # (Opcional) Limitar historial a las últimas 10 líneas para no ahogar a Ollama local
                    lineas = nuevo_historial.split("\n")
                    if len(lineas) > 10:
                        nuevo_historial = "\n".join(lineas[-10:])
                    
                    # 2. Construir el prompt dinámico
                    plantilla_prompt = get_system_prompt()
                    prompt_final = plantilla_prompt.replace("{nombre}", name).replace("{nicho}", nicho).replace("{historial}", nuevo_historial).replace("{mensaje}", msg_text)
                    
                    print(f"🧠 Pensando respuesta con Ollama ({OLLAMA_MODEL})...")
                    reply = ask_ollama(prompt_final)
                    
                    if reply:
                        # Limpiar tics raros de la IA
                        reply = reply.replace("[Onyx]:", "").replace("Onyx:", "").replace('"', "").strip()
                        
                        if send_whatsapp_msg(clean_number, reply):
                            print(f"🤖 Bot respondió: {reply}")
                            # 3. Guardar la respuesta del bot en el historial
                            historial_final = f"{nuevo_historial}\n[Onyx]: {reply}"
                            update_lead_status_and_history(lead['id'], "En Conversación", historial_final, 0)
                        else:
                            print(f"❌ Falló el envío de respuesta a {name}")
                    else:
                        print("⚠️ Ollama no respondió o está apagado. Pausando bot para este lead.")
                        update_lead_status_and_history(lead['id'], "Respondido", nuevo_historial, 1)
                
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            
        except Exception as e:
            print(f"❌ Error webhook: {e}")
            self.send_response(500)
            self.end_headers()

def run(server_class=http.server.HTTPServer, handler_class=WebhookHandler):
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    print(f"🚀 Webhook Inteligente (Ollama) escuchando en el puerto {PORT}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
