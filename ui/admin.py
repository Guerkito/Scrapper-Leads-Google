import streamlit as st
import sqlite3
import pandas as pd
import os
import re
import tempfile
import datetime
from config import email_settings
from db import DB_PATH, init_db, open_conn
from db import _coerce_float as coerce_float, _coerce_reviews as coerce_reviews
from services.leads import load_all_leads, invalidate_leads_cache
from services.export_utils import safe_spreadsheet_frame
from sources.base_source import Lead
from db import save_lead
from ui.icons import title_html

def _escape_env_value(value):
    """Escapa un valor para el archivo .env (comillas, espacios y caracteres shell)."""
    value = str(value or "")
    if re.search(r'[\s#"\'`$\\]', value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
        return f'"{escaped}"'
    return value

def update_env_variable(key, value):
    """Actualiza una variable en el archivo .env de forma segura."""
    serialized = f"{key}={_escape_env_value(value)}"
    env_file = ".env"
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            f.write(f"{serialized}\n")
    else:
        with open(env_file, "r") as f:
            lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{serialized}\n")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"{serialized}\n")

        with open(env_file, "w") as f:
            f.writelines(new_lines)

    # Aplicar el cambio al proceso en ejecución para que campañas de email ya
    # lanzadas desde esta sesión usen las credenciales nuevas sin reiniciar.
    os.environ[key] = str(value)

def render_admin_view():
    df_all = load_all_leads()

    st.markdown(title_html("Calidad de Datos", "chart", 4), unsafe_allow_html=True)
    if df_all.empty:
        st.info("Aún no hay leads para auditar.")
    else:
        def _truthy_web(val):
            if pd.isna(val):
                return False
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return val == 1
            return str(val).strip().lower() in {"1", "true", "si", "sí", "yes", "y"}

        def complete(column):
            if column not in df_all:
                return 0
            values = df_all[column].fillna("").astype(str).str.strip().str.casefold()
            return int((~values.isin(["", "n/a", "nan", "none", "null"])).mean() * 100)

        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Con teléfono válido", f"{complete('telefono_e164')}%")
        q2.metric("Con email", f"{complete('email')}%")
        q3.metric("Con país", f"{complete('pais')}%")
        q4.metric("Con web propia", f"{int(df_all['tiene_web'].map(_truthy_web).mean() * 100)}%")
        duplicate_keys = df_all.assign(
            _identity=df_all['nombre'].fillna('').str.strip().str.casefold()
            + "|" + df_all['ciudad'].fillna('').str.strip().str.casefold()
            + "|" + df_all['pais'].fillna('').str.strip().str.casefold()
        ).duplicated('_identity', keep=False).sum()
        st.caption(f"Filas en grupos de identidad duplicada: {int(duplicate_keys)}")

    # --- FILA 1: EXPORTACIÓN Y BACKUP ---
    st.markdown(title_html("Exportación y Respaldos", "download", 4), unsafe_allow_html=True)
    ex1, ex2, ex3 = st.columns(3)

    with ex1:
        st.download_button(
            "Exportar Leads (CSV)",
            safe_spreadsheet_frame(df_all).to_csv(index=False),
            f"leads_onyx_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            width='stretch',
            mime="text/csv"
        )

    with ex2:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                st.download_button(
                    "Descargar Backup (.db)",
                    f.read(),
                    f"backup_onyx_{datetime.datetime.now().strftime('%Y%m%d')}.db",
                    mime="application/octet-stream",
                    width='stretch',
                )
        else:
            st.button("Backup no disponible", disabled=True, width='stretch')

    with ex3:
        if st.button("Compactar Base de Datos", width='stretch', help="Optimiza el espacio en disco de la DB"):
            try:
                conn = open_conn()
                conn.execute("VACUUM")
                conn.close()
                st.success("Base de datos optimizada.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

    # --- FILA 2: RESTAURACIÓN E IMPORTACIÓN ---
    st.markdown(title_html("Importar y Restaurar", "file", 4), unsafe_allow_html=True)
    rb1, rb2 = st.columns(2)

    with rb1:
        st.markdown("<p style='font-size:0.8rem; color:#8888A0;'>Subir archivo <b>.db</b> (Reemplaza todo)</p>", unsafe_allow_html=True)
        uploaded_db = st.file_uploader("Subir base de datos", type=["db"], key="upload_db", label_visibility="collapsed")
        if uploaded_db:
            if st.button("Restaurar Sistema desde .db", type="primary", width='stretch'):
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
                        tmp.write(uploaded_db.read())
                        tmp_path = tmp.name

                    source = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
                    try:
                        integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
                        tables = {row[0] for row in source.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )}
                        if integrity != "ok" or "leads" not in tables:
                            raise ValueError("El archivo está corrupto o no contiene la tabla leads.")

                        backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
                        os.makedirs(backup_dir, exist_ok=True)
                        backup_path = os.path.join(
                            backup_dir,
                            f"pre_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                        )
                        with open_conn() as live, sqlite3.connect(backup_path) as backup:
                            live.backup(backup)
                        with open_conn() as live:
                            source.backup(live)
                    finally:
                        source.close()

                    init_db()
                    invalidate_leads_cache()
                    st.success(f"Base restaurada. Respaldo anterior: {backup_path}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fallo crítico en restauración: {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    with rb2:
        st.markdown("<p style='font-size:0.8rem; color:#8888A0;'>Importar desde <b>CSV/Excel</b> (Fusiona datos)</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Subir Excel o CSV", type=["csv", "xlsx"], key="upload_data", label_visibility="collapsed")
        if uploaded_file:
            if st.button("Procesar e Importar Datos", type="primary", width='stretch'):
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_import = pd.read_csv(uploaded_file)
                    else:
                        df_import = pd.read_excel(uploaded_file)

                    # Normalizar columnas
                    df_import.columns = [c.lower().strip() for c in df_import.columns]
                    required = {"nombre", "ciudad"}
                    missing = required - set(df_import.columns)

                    if missing:
                        st.error(f"Faltan columnas obligatorias: {missing}")
                    else:
                        if len(df_import) > 100_000:
                            raise ValueError("El archivo supera el máximo de 100.000 filas por importación.")

                        def value(row, key, default=None):
                            item = row.get(key, default)
                            return default if pd.isna(item) else item

                        inserted = updated = failed = 0
                        with open_conn() as conn:
                            for _, row in df_import.iterrows():
                                try:
                                    site = str(value(row, 'sitio_web', '') or '').strip()
                                    lead = Lead(
                                        nombre=str(value(row, 'nombre', '') or '').strip(),
                                        ciudad=str(value(row, 'ciudad', '') or '').strip(),
                                        pais=str(value(row, 'pais', '') or '').strip() or None,
                                        departamento=str(value(row, 'departamento', '') or '').strip() or None,
                                        nicho=str(value(row, 'nicho', 'Importado') or 'Importado'),
                                        fuente="importacion",
                                        telefono=str(value(row, 'telefono', '') or ''),
                                        email=str(value(row, 'email', '') or '') or None,
                                        sitio_web=site or None,
                                        tiene_web=bool(site),
                                        rating=coerce_float(value(row, 'rating', 0)) or None,
                                        reseñas=coerce_reviews(value(row, 'reseñas', 0)),
                                        nit=str(value(row, 'nit', '') or '') or None,
                                        raw_data={"imported": True},
                                    )
                                    result = save_lead(lead, conn)
                                    inserted += result == 1
                                    updated += result == 0
                                    failed += result < 0
                                except Exception:
                                    failed += 1
                        invalidate_leads_cache()
                        st.success(f"Importación lista: {inserted} nuevos, {updated} fusionados, {failed} errores.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al importar archivo: {e}")

    st.divider()

    st.markdown(title_html("Historial de Campañas", "mail", 4), unsafe_allow_html=True)
    with open_conn() as conn:
        campaigns = pd.read_sql_query(
            """
            SELECT campaign_id, channel, status, COUNT(*) AS destinos,
                   MIN(created_at) AS inicio, MAX(updated_at) AS ultima_actualizacion
            FROM campaign_events
            GROUP BY campaign_id, channel, status
            ORDER BY ultima_actualizacion DESC LIMIT 200
            """,
            conn,
        )
    if campaigns.empty:
        st.caption("Todavía no hay campañas registradas.")
    else:
        st.dataframe(campaigns, width="stretch", hide_index=True)

    st.divider()

    # --- NUEVA FILA: CONFIGURACIÓN DE EMAIL ---
    st.markdown(title_html("Configuración de Email (SMTP)", "mail", 4), unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<p style='font-size:0.85rem; color:#A0A0B0;'>Configura el servidor de correo para tus campañas de Email Marketing.</p>", unsafe_allow_html=True)

        c_mail1, c_mail2 = st.columns(2)

        _mail_cfg = email_settings()

        with c_mail1:
            new_host = st.text_input("Servidor SMTP", value=_mail_cfg["host"], placeholder="e.g. smtp.gmail.com")
            new_port = st.number_input("Puerto", value=int(_mail_cfg["port"]), min_value=1, max_value=65535)
            new_from_name = st.text_input("Nombre del Remitente", value=_mail_cfg["from_name"], placeholder="e.g. Onyx Intelligence")

        with c_mail2:
            new_user = st.text_input("Usuario / Email", value=_mail_cfg["user"], placeholder="tu-email@gmail.com")
            new_pass = st.text_input("Contraseña de Aplicación", value=_mail_cfg["pass"], type="password", help="En Gmail, usa una 'Contraseña de Aplicación' de 16 dígitos.")

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Guardar Configuración de Email", type="primary", width="stretch"):
            try:
                update_env_variable("EMAIL_HOST", new_host)
                update_env_variable("EMAIL_PORT", str(new_port))
                update_env_variable("EMAIL_USER", new_user)
                update_env_variable("EMAIL_PASS", new_pass)
                update_env_variable("EMAIL_FROM_NAME", new_from_name)

                st.success("✅ Configuración de email guardada. Los cambios ya están activos para esta sesión.")
                # No hacemos rerun forzoso aquí para que el usuario pueda ver el éxito
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    st.divider()

    # --- FILA 3: PELIGRO ---
    st.markdown(title_html("Zona de Peligro", "settings", 4), unsafe_allow_html=True)
    with st.container(border=True):
        st.warning("Las siguientes acciones son irreversibles. Procede con precaución.")
        col_p1, col_p2 = st.columns([2, 1])

        with col_p1:
            st.markdown("**Borrar todos los leads**")
            st.caption("Esto limpiará la tabla de leads pero mantendrá tus configuraciones y bot logs.")

        with col_p2:
            if st.button("BORRAR TODO", type="primary", width='stretch'):
                if st.session_state.get('confirm_full_delete', False):
                    try:
                        conn = open_conn()
                        conn.execute("DELETE FROM leads")
                        conn.commit()
                        conn.close()

                        # IMPORTANTE: Invalidar la caché para que la UI se entere del borrado
                        invalidate_leads_cache()

                        st.session_state.confirm_full_delete = False
                        st.success("Base de datos limpiada correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al borrar: {e}")
                else:
                    st.warning("⚠️ ¿Estás totalmente seguro? Haz clic de nuevo para confirmar el borrado total.")
                    st.session_state.confirm_full_delete = True
