import requests
import streamlit as st
import html
from config import EVO_URL, EVO_API_KEY, EVO_INSTANCE


@st.cache_data(ttl=15, show_spinner=False)
def check_whatsapp_connection(evo_url, evo_key, evo_instance):
    """Verifica el estado de la conexión de WhatsApp con la API de Evolution."""
    if not evo_url or not evo_key:
        return {"status": "info", "message": "Configura la API en WhatsApp"}

    try:
        headers = {"apikey": evo_key, "ngrok-skip-browser-warning": "true"}
        url = f"{evo_url.rstrip('/')}/instance/connectionState/{evo_instance}"
        # Es solo un indicador visual: nunca debe bloquear la aplicación.
        r = requests.get(url, headers=headers, timeout=(0.5, 1.0))

        if r.status_code == 200:
            state = r.json().get("instance", {}).get("state", "disconnected")
            if state == "open":
                return {"status": "success", "message": "WhatsApp: CONECTADO"}
            return {"status": "error", "message": "WhatsApp: DESCONECTADO"}
        return {"status": "warning", "message": "Instancia no iniciada"}
    except Exception:
        return {"status": "error", "message": "API Offline"}


def render_whatsapp_status_sidebar():
    """Renderiza el estado de WhatsApp en el sidebar."""
    evo_instance = st.session_state.get("evo_instance_name", EVO_INSTANCE)
    status_info = check_whatsapp_connection(EVO_URL, EVO_API_KEY, evo_instance)

    status = status_info["status"]
    message = html.escape(status_info["message"].replace("WhatsApp: ", ""))
    st.markdown(
        f"<div class='connection-status' data-status='{status}'>"
        "<span class='connection-dot' aria-hidden='true'></span>"
        f"<div><small>WhatsApp</small><strong>{message}</strong></div>"
        "</div>",
        unsafe_allow_html=True,
    )
