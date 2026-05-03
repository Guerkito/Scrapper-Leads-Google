import streamlit as st

def kpi_card(label, value, accent_color="#FF0000", subtext=None):
    sub_html = f"<div style='font-size:0.75rem; color:#888898; margin-top:8px; font-weight:400;'>{subtext}</div>" if subtext else ""
    return (
        f"<div class='onyx-card onyx-animate' style='padding: 24px; margin-bottom: 0; border-top: 4px solid {accent_color}; height: 100%;'>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:0.75rem; "
        f"  font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#888898;'>"
        f"  {label}</div>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:2.4rem; "
        f"  font-weight:700; color:#FFFFFF; margin-top:8px; line-height:1;'>"
        f"  {value}</div>"
        f"  {sub_html}"
        f"</div>"
    )
