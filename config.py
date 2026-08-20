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
