import streamlit as st
import sqlite3
import pandas as pd
import os
import shutil
import tempfile
import datetime
from db import DB_PATH, init_db, open_conn
from services.leads import load_all_leads

def render_admin_view():
    st.markdown("### ⚙️ Administración de Base de Datos")
    
    df_all = load_all_leads()
    
    # --- FILA 1: EXPORTACIÓN Y BACKUP ---
    st.markdown("#### 📤 Exportación y Respaldos")
    ex1, ex2, ex3 = st.columns(3)
    
    with ex1:
        st.download_button(
            "Exportar Leads (CSV)",
            df_all.to_csv(index=False),
            f"leads_onyx_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True,
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
                    use_container_width=True,
                )
        else:
            st.button("Backup no disponible", disabled=True, use_container_width=True)

    with ex3:
        if st.button("Compactar Base de Datos", use_container_width=True, help="Optimiza el espacio en disco de la DB"):
            try:
                conn = open_conn()
                conn.execute("VACUUM")
                conn.close()
                st.success("Base de datos optimizada.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

    # --- FILA 2: RESTAURACIÓN E IMPORTACIÓN ---
    st.markdown("#### 📥 Importar y Restaurar")
    rb1, rb2 = st.columns(2)

    with rb1:
        st.markdown("<p style='font-size:0.8rem; color:#8888A0;'>Subir archivo <b>.db</b> (Reemplaza todo)</p>", unsafe_allow_html=True)
        uploaded_db = st.file_uploader("Subir base de datos", type=["db"], key="upload_db", label_visibility="collapsed")
        if uploaded_db:
            if st.button("Restaurar Sistema desde .db", type="primary", use_container_width=True):
                try:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
                    tmp.write(uploaded_db.read())
                    tmp.flush()
                    
                    # Validar
                    test_conn = sqlite3.connect(tmp.name)
                    tables = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    test_conn.close()
                    
                    table_names = [t[0] for t in tables]
                    if "leads" not in table_names:
                        st.error("Error: El archivo no es una base de datos Onyx válida.")
                    else:
                        shutil.copy2(tmp.name, DB_PATH)
                        os.unlink(tmp.name)
                        init_db() # Migrar si es necesario
                        st.success("✅ Base de datos restaurada con éxito.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Fallo crítico en restauración: {e}")

    with rb2:
        st.markdown("<p style='font-size:0.8rem; color:#8888A0;'>Importar desde <b>CSV/Excel</b> (Fusiona datos)</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Subir Excel o CSV", type=["csv", "xlsx"], key="upload_data", label_visibility="collapsed")
        if uploaded_file:
            if st.button("Procesar e Importar Datos", type="primary", use_container_width=True):
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
                        conn = open_conn()
                        inserted = 0
                        for _, r in df_import.iterrows():
                            # Mapeo simple para INSERT OR IGNORE
                            cur = conn.execute(
                                '''INSERT OR IGNORE INTO leads
                                   (nombre, ciudad, telefono, rating, reseñas, nicho, sitio_web, tiene_web, estado)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                (
                                    str(r.get('nombre')), str(r.get('ciudad')), str(r.get('telefono', 'N/A')),
                                    r.get('rating', 0), r.get('reseñas', 0), r.get('nicho', 'Importado'),
                                    r.get('sitio_web', ''), bool(r.get('sitio_web')), 'Nuevo'
                                )
                            )
                            inserted += cur.rowcount
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {inserted} leads nuevos importados.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al importar archivo: {e}")

    st.divider()

    # --- FILA 3: PELIGRO ---
    st.markdown("#### ☢️ Zona de Peligro")
    with st.container(border=True):
        st.warning("Las siguientes acciones son irreversibles. Procede con precaución.")
        col_p1, col_p2 = st.columns([2, 1])
        
        with col_p1:
            st.markdown("**Borrar todos los leads**")
            st.caption("Esto limpiará la tabla de leads pero mantendrá tus configuraciones y bot logs.")
            
        with col_p2:
            if st.button("BORRAR TODO", type="primary", use_container_width=True):
                if st.session_state.get('confirm_full_delete', False):
                    conn = open_conn()
                    conn.execute("DELETE FROM leads")
                    conn.commit()
                    conn.close()
                    st.session_state.confirm_full_delete = False
                    st.success("Base de datos limpiada.")
                    st.rerun()
                else:
                    st.warning("¿Estás seguro? Haz clic de nuevo para confirmar.")
                    st.session_state.confirm_full_delete = True
