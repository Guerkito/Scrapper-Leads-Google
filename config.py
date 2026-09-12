"""Configuración centralizada del proyecto.

Todas las variables de entorno se leen aquí una sola vez. El resto del código
debe importar desde este módulo en lugar de llamar a `os.getenv` directamente.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _strip_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


# ── Base de datos ─────────────────────────────────────────────────────────────
_container_data = "/data"
_default_db = (
    os.path.join(_container_data, "leads.db")
    if os.path.isdir(_container_data) and os.access(_container_data, os.W_OK)
    else os.path.join(os.getcwd(), "data", "leads.db")
)
DB_PATH = os.path.abspath(os.path.expanduser(os.getenv("DB_PATH", _default_db)))

# ── Evolution API (WhatsApp) ──────────────────────────────────────────────────
EVO_URL = _strip_url(os.getenv("EVO_URL", "http://127.0.0.1:8080"))
EVO_API_KEY = os.getenv("EVO_API_KEY", "")
EVO_INSTANCE = os.getenv("EVO_INSTANCE", "onyxbot")

# ── Webhook ───────────────────────────────────────────────────────────────────
# Acepta WEBHOOK_PORT (preferido) o PORT (legacy) por compatibilidad con .env existentes.
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT") or os.getenv("PORT") or 5001)
# Token compartido para autenticar requests entrantes al webhook.
# Configura el mismo valor en Evolution API como header (e.g. `Authorization: Bearer <token>`
# o `X-Webhook-Token: <token>`). Si está vacío, el webhook arranca en modo dev sin auth
# (NO recomendado en producción).
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN", "")
# Tamaño máximo del body en bytes (defensa básica contra abuso).
WEBHOOK_MAX_BODY = int(os.getenv("WEBHOOK_MAX_BODY", 65536))
WEBHOOK_WORKERS = max(1, min(16, int(os.getenv("WEBHOOK_WORKERS", 4))))
WEBHOOK_LLM_BACKEND = os.getenv("WEBHOOK_LLM_BACKEND", "ollama").strip().lower()

# ── Hermes (LLM agent) ────────────────────────────────────────────────────────
HERMES_PATH = os.getenv("HERMES_PATH", "hermes")  # asume que está en PATH

# ── Ollama (fallback local) ───────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# ── Scraping ──────────────────────────────────────────────────────────────────
MAX_CONCURRENT = max(1, min(8, int(os.getenv("MAX_CONCURRENT", 6))))

# ── Email Marketing ───────────────────────────────────────────────────────────
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")  # Password o App Password
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Onyx Lead Gen")

# Link de agenda (Cal.com, Calendly, etc.) que el bot y los correos comparten.
CALCOM_LINK = os.getenv("CALCOM_LINK", "").strip()

# API de Cal.com para confirmar reuniones automáticamente (requiere API key).
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY", "").strip()
CALCOM_API_VERSION = os.getenv("CALCOM_API_VERSION", "2026-05-01").strip()
try:
    MEETINGS_POLL_MINUTES = max(5, int(os.getenv("MEETINGS_POLL_MINUTES", 30)))
except ValueError:
    MEETINGS_POLL_MINUTES = 30
try:
    MEETINGS_BATCH = max(1, int(os.getenv("MEETINGS_BATCH", 25)))
except ValueError:
    MEETINGS_BATCH = 25

# ── Bandeja de entrada (IMAP) ─────────────────────────────────────────────────
# El agente de email responde a las respuestas de los prospectos desde esta cuenta.
# Si no se definen IMAP_*, se reutilizan EMAIL_USER / EMAIL_PASS.
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
IMAP_USER = os.getenv("IMAP_USER", "") or EMAIL_USER
IMAP_PASS = os.getenv("IMAP_PASS", "") or EMAIL_PASS
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")
INBOX_POLL_SECONDS = max(15, int(os.getenv("INBOX_POLL_SECONDS", 60)))

# ── Follow-ups automáticos ────────────────────────────────────────────────────
# FOLLOW_UP_MAX = 0 desactiva los seguimientos. FOLLOW_UP_DAYS es la espera
# entre toques (se cuenta desde la última interacción del lead).
FOLLOW_UP_MAX = max(0, int(os.getenv("FOLLOW_UP_MAX", 2)))
FOLLOW_UP_DAYS = max(1, int(os.getenv("FOLLOW_UP_DAYS", 3)))
FOLLOW_UP_POLL_MINUTES = max(5, int(os.getenv("FOLLOW_UP_POLL_MINUTES", 60)))

# ── Envío gestionado ──────────────────────────────────────────────────────────
# SENDER_PROVIDER: "smtp" (por defecto) o "resend" (API gestionada, requiere
# RESEND_API_KEY y un dominio verificado en Resend).
SENDER_PROVIDER = os.getenv("SENDER_PROVIDER", "smtp").strip().lower()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
SENDER_FROM_EMAIL = os.getenv("SENDER_FROM_EMAIL", "").strip() or EMAIL_USER
# Pausa los envíos al superar este número por día (0 = sin límite).
try:
    SENDER_DAILY_LIMIT = max(0, int(os.getenv("SENDER_DAILY_LIMIT", 0)))
except ValueError:
    SENDER_DAILY_LIMIT = 0
# Coste estimado por email para el panel de rendimiento (ej. 0.001 para Resend).
try:
    COST_PER_EMAIL = max(0.0, float(os.getenv("COST_PER_EMAIL", 0)))
except ValueError:
    COST_PER_EMAIL = 0.0

# ── Acceso al panel web ───────────────────────────────────────────────────────
# Si PANEL_PASSWORD queda vacío, el panel abre sin login (solo recomendado en
# localhost). SESSION_SECRET firma la cookie de sesión; si no se define se
# deriva de la contraseña (cambiarla cierra todas las sesiones).
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "").strip()
SESSION_SECRET = os.getenv("SESSION_SECRET", "").strip() or PANEL_PASSWORD
try:
    SESSION_DAYS = max(1, int(os.getenv("SESSION_DAYS", 30)))
except ValueError:
    SESSION_DAYS = 30
try:
    PANEL_MAX_UPLOAD_MB = max(1, int(os.getenv("PANEL_MAX_UPLOAD_MB", 20)))
except ValueError:
    PANEL_MAX_UPLOAD_MB = 20

# ── Optimización automática de campañas ───────────────────────────────────────
# AUTO_OPTIMIZE pausa segmentos sin ninguna respuesta tras OPTIMIZE_MIN_LEADS
# leads contactados. OPTIMIZE_SCALE_RATE es la tasa de respuesta desde la que
# el panel recomienda escalar un segmento.
AUTO_OPTIMIZE = os.getenv("AUTO_OPTIMIZE", "true").strip().lower() in {
    "1", "true", "si", "sí", "yes",
}
try:
    OPTIMIZE_MIN_LEADS = max(1, int(os.getenv("OPTIMIZE_MIN_LEADS", 25)))
except ValueError:
    OPTIMIZE_MIN_LEADS = 25
try:
    OPTIMIZE_SCALE_RATE = max(0.0, float(os.getenv("OPTIMIZE_SCALE_RATE", 0.08)))
except ValueError:
    OPTIMIZE_SCALE_RATE = 0.08


def evo_headers(extra: dict | None = None) -> dict:
    """Headers HTTP estándar para llamar a Evolution API."""
    headers = {
        "apikey": EVO_API_KEY,
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
    }
    if extra:
        headers.update(extra)
    return headers


def email_settings() -> dict:
    """Lee la config de email desde el entorno en cada llamada.

    Las constantes EMAIL_* se congelan al importar; esta función permite que
    una sesión en ejecución use credenciales recién guardadas sin reiniciar.
    """
    return {
        "host": os.getenv("EMAIL_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("EMAIL_PORT", 587)),
        "user": os.getenv("EMAIL_USER", ""),
        "pass": os.getenv("EMAIL_PASS", ""),
        "from_name": os.getenv("EMAIL_FROM_NAME", "Onyx Lead Gen"),
    }
