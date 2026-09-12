import streamlit as st
import html
import re

def kpi_card(label, value, accent_color="#E5484D", subtext=None, icon=None):
    color = accent_color if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(accent_color)) else "#E5484D"
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    safe_subtext = html.escape(str(subtext)) if subtext else ""
    bar = f"<div style='width:34px;height:3px;border-radius:99px;background:{color};margin-bottom:10px;'></div>"
    sub_html = f"<div style='font-size:0.74rem; color:#6B7485; margin-top:6px; font-weight:500;'>{safe_subtext}</div>" if safe_subtext else ""
    return (
        f"<div class='onyx-card' style='padding: 18px 20px; margin-bottom: 0; height: 100%;'>"
        f"{bar}"
        f"<div class='kpi-label'>{safe_label}</div>"
        f"<div class='kpi-value'>{safe_value}</div>"
        f"{sub_html}"
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


def chip(text, tone="neutral"):
    """Píldora de estado con color semántico."""
    safe = html.escape(str(text))
    return f"<span class='onyx-chip {tone}'>{safe}</span>"


def chips_list(items, tone="neutral"):
    return "<div class='badges-wrapper'>" + "".join(chip(i, tone) for i in items) + "</div>"


def section_header(text, icon="target", level=3):
    from ui.icons import title_html
    return title_html(text, icon, level)


def empty_state(title, hint):
    safe_title = html.escape(str(title))
    safe_hint = html.escape(str(hint))
    return (
        "<div class='empty-state'>"
        f"<div style='font-weight:700; margin-bottom:6px; color:#98A2B3;'>{safe_title}</div>"
        f"<div>{safe_hint}</div>"
        "</div>"
    )
