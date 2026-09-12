"""Acceso al panel: token de sesión firmado y límite de intentos de login.

Pensado para un solo operador (el dueño del panel): una contraseña en el .env,
cookie HttpOnly firmada con HMAC y bloqueo temporal por intentos fallidos.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from config import PANEL_PASSWORD, SESSION_DAYS, SESSION_SECRET


COOKIE_NAME = "onyx_session"
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = 900  # 15 minutos

_attempts: dict[str, list[float]] = {}


def is_enabled() -> bool:
    return bool(PANEL_PASSWORD)


def verify_password(candidate: str) -> bool:
    if not PANEL_PASSWORD:
        return True
    return hmac.compare_digest(str(candidate or ""), PANEL_PASSWORD)


def make_token() -> str:
    issued = str(int(time.time()))
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"), issued.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{issued}.{signature}"


def verify_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    issued, signature = token.split(".", 1)
    try:
        timestamp = int(issued)
    except ValueError:
        return False
    expected = hmac.new(
        SESSION_SECRET.encode("utf-8"), issued.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    return time.time() - timestamp < SESSION_DAYS * 86400


def _prune(now: float, ip: str) -> None:
    _attempts[ip] = [
        stamp for stamp in _attempts.get(ip, []) if now - stamp < ATTEMPT_WINDOW
    ]


def too_many_attempts(ip: str) -> bool:
    now = time.time()
    _prune(now, ip)
    return len(_attempts.get(ip, [])) >= MAX_ATTEMPTS


def record_attempt(ip: str) -> None:
    _prune(time.time(), ip)
    _attempts.setdefault(ip, []).append(time.time())


def clear_attempts(ip: str) -> None:
    _attempts.pop(ip, None)
