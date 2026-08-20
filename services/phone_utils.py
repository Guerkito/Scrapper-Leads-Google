"""Normalizacion consistente de telefonos para deduplicacion y campanas."""

from __future__ import annotations

import re

import phonenumbers
from phonenumbers import PhoneNumberFormat


COUNTRY_REGIONS = {
    "alemania": "DE",
    "argentina": "AR",
    "australia": "AU",
    "bolivia": "BO",
    "brasil": "BR",
    "canada": "CA",
    "canadá": "CA",
    "chile": "CL",
    "colombia": "CO",
    "costa rica": "CR",
    "ecuador": "EC",
    "el salvador": "SV",
    "espana": "ES",
    "españa": "ES",
    "estados unidos": "US",
    "francia": "FR",
    "guatemala": "GT",
    "honduras": "HN",
    "italia": "IT",
    "mexico": "MX",
    "méxico": "MX",
    "panama": "PA",
    "panamá": "PA",
    "paraguay": "PY",
    "peru": "PE",
    "perú": "PE",
    "portugal": "PT",
    "reino unido": "GB",
    "republica dominicana": "DO",
    "república dominicana": "DO",
    "uruguay": "UY",
    "usa": "US",
    "venezuela": "VE",
}


def country_region(country: str | None) -> str | None:
    """Convierte el nombre visible de un pais a su region ISO-3166."""
    key = str(country or "").strip().casefold()
    if len(key) == 2 and key.isalpha():
        return key.upper()
    return COUNTRY_REGIONS.get(key)


def normalize_phone(phone: object, country: str | None = None) -> str:
    """Retorna E.164 si el numero es valido; de lo contrario retorna cadena vacia."""
    raw = str(phone or "").strip()
    if raw.casefold() in {"", "nan", "n/a", "none", "null"}:
        return ""
    if raw.endswith(".0"):
        raw = raw[:-2]
    if "e+" in raw.casefold() or "e-" in raw.casefold():
        try:
            raw = str(int(float(raw)))
        except (TypeError, ValueError, OverflowError):
            return ""
    raw = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\ue0b0\u00ad\xa0\s]", "", raw)
    try:
        parsed = phonenumbers.parse(raw, country_region(country))
    except phonenumbers.NumberParseException:
        return ""
    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        return ""
    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


def phone_digits(phone: object, country: str | None = None) -> str:
    """Identidad numerica estable para APIs que no aceptan el signo +."""
    normalized = normalize_phone(phone, country)
    return normalized.lstrip("+") if normalized else ""
