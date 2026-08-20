import streamlit as st
import html
import re

def kpi_card(label, value, accent_color="#FF0000", subtext=None):
    color = accent_color if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(accent_color)) else "#FF0000"
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    safe_subtext = html.escape(str(subtext)) if subtext else ""
    sub_html = f"<div style='font-size:0.75rem; color:#888898; margin-top:8px; font-weight:400;'>{safe_subtext}</div>" if safe_subtext else ""
    return (
        f"<div class='onyx-card onyx-animate' style='padding: 24px; margin-bottom: 0; border-top: 4px solid {color}; height: 100%;'>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:0.75rem; "
        f"  font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#888898;'>"
        f"  {safe_label}</div>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:2.4rem; "
        f"  font-weight:700; color:#FFFFFF; margin-top:8px; line-height:1;'>"
        f"  {safe_value}</div>"
        f"  {sub_html}"
        f"</div>"
    )


def overview_strip(items):
    """Resumen compacto para no empujar la tarea principal fuera de pantalla."""
    cells = []
    for label, value, hint in items:
        cells.append(
            "<div class='overview-item'>"
            f"<span>{html.escape(str(label))}</span>"
            f"<strong>{html.escape(str(value))}</strong>"
            f"<small>{html.escape(str(hint))}</small>"
            "</div>"
        )
    return "<div class='overview-strip'>" + "".join(cells) + "</div>"
