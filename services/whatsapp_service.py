import os
import requests
import streamlit as st

def check_whatsapp_connection(evo_url, evo_key, evo_instance):
    """Verifica el estado de la conexión de WhatsApp con la API de Evolution."""
    if not evo_url or not evo_key:
        return {"status": "info", "message": "💡 Configura la API en WhatsApp"}
    
    try:
        headers = {"apikey": evo_key, "ngrok-skip-browser-warning": "true"}
        url = f"{evo_url.strip().rstrip('/')}/instance/connectionState/{evo_instance}"
        r = requests.get(url, headers=headers, timeout=2)
        
        if r.status_code == 200:
            state = r.json().get("instance", {}).get("state", "disconnected")
            if state == "open":
                return {"status": "success", "message": "📱 WhatsApp: CONECTADO"}
            else:
                return {"status": "error", "message": "📱 WhatsApp: DESCONECTADO"}
        else:
            return {"status": "warning", "message": "⚠️ Instancia no iniciada"}
    except Exception:
        return {"status": "error", "message": "🔌 API Offline"}

def render_whatsapp_status_sidebar():
    """Renderiza el estado de WhatsApp en el sidebar."""
    evo_url = os.getenv("EVO_URL", "http://127.0.0.1:8080")
    evo_key = os.getenv("EVO_API_KEY", "")
    evo_instance = st.session_state.get("evo_instance_name", "onyxbot")
    
    status_info = check_whatsapp_connection(evo_url, evo_key, evo_instance)
    
    if status_info["status"] == "success":
        st.success(status_info["message"])
    elif status_info["status"] == "error":
        st.error(status_info["message"])
    elif status_info["status"] == "warning":
        st.warning(status_info["message"])
    else:
        st.info(status_info["message"])
