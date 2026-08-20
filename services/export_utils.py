"""Protecciones comunes para exportaciones abiertas luego en hojas de calculo."""

from __future__ import annotations

import re

import pandas as pd


_FORMULA_PREFIX = re.compile(r"^[\t\r\n ]*['\"=+\-@]")


def safe_spreadsheet_value(value):
    if pd.isna(value):
        return ""
    if not isinstance(value, str):
        return value
    clean = re.sub(r"[\r\n]+", " ", value)
    # Prefijos de fórmula según OWASP: = + - @ y comillas simples/dobles/acento.
    return "'" + clean if _FORMULA_PREFIX.match(clean) else clean


def safe_spreadsheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if result[column].dtype == "object":
            result[column] = result[column].map(safe_spreadsheet_value)
    return result
