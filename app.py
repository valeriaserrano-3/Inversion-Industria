"""
Inversión Automotriz – App Unificada
Streamlit app para procesar archivos de inversión (GWM, JAC, KAVAK, Industria)
y generar el layout unificado para automotriz.xlsx.
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import calendar
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inversión Automotriz",
    page_icon="🚗",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# CONTRASEÑA
# ─────────────────────────────────────────────────────────────────────────────
def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
        <style>
        .login-box { max-width: 380px; margin: 80px auto; padding: 40px; background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,.1); text-align: center; }
        </style>
        <div class="login-box">
          <h2>Inversión Automotriz</h2>
          <p>Ingresa la contraseña para continuar</p>
        </div>
        """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        pwd = st.text_input("Contraseña", type="password", label_visibility="collapsed")
        if st.button("Entrar", use_container_width=True):
            if pwd == "automotriz2026":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    return False

if not check_password():
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS Y MULTIPLICADORES
# ─────────────────────────────────────────────────────────────────────────────
MULTIPLICADORES = {
    "radio": 1.30,
    "tele_abierta": 1.30,
    "tele_paga": 1.30,
    "online": 1.30,
    "ooh_factor": 1.30
}

MESES_DICC = {
    'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6,
    'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
}

def parse_yrmth(val):
    """Convierte 'jan2025' o fechas a Timestamp."""
    try:
        if isinstance(val, datetime): return val
        s = str(val).strip().lower()
        # Caso jan2025
        for i, m in enumerate(calendar.month_abbr):
            if m and s.startswith(m.lower()):
                return pd.Timestamp(year=int(s[3:]), month=i, day=1)
        return pd.to_datetime(val)
    except:
        return pd.NaT

# ─────────────────────────────────────────────────────────────────────────────
# LÓGICA DE PROCESAMIENTO POR LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

def process_naming_convention(df, grupo_nombre):
    """Procesador para GWM, JAC, KAVAK (Layout Naming Convention)"""
    # Limpieza básica
    df['monto'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0)
    df['Bonificación Cliente'] = pd.to_numeric(df['Bonificación Cliente'], errors='coerce').fillna(0)
    df['Inversión (MXN)'] = df['monto'] + df['Bonificación Cliente']
    
    # Mapeo de columnas al layout final
    res = pd.DataFrame()
    res['Fuente'] = df['FUENTE'].apply(lambda x: 'OOH' if 'EXTERIOR' in str(x).upper() else 'Offline')
    res['Año-mes'] = df['yrmth'].apply(parse_yrmth)
    res['Año'] = res['Año-mes'].dt.year
    res['Inversión (MXN)'] = df['Inversión (MXN)']
    res['Inversión F30'] = df['Inversión (MXN)'] # Ajustar si lleva multiplicador
    res['#Grupo'] = grupo_nombre
    res['Categoría'] = df.get('OBJETIVO', 'Institucional')
    res['Producto'] = df.get('Modelos', 'Varios')
    res['medio'] = df['FUENTE']
    res['modelo'] = df.get('Modelos', 'Varios')
    return res

def process_hr_ratings(df, medio_nombre):
    """Procesador para HR Ratings (Industria)"""
    # HR suele tener 42 columnas, aquí filtramos solo lo necesario
    res = pd.DataFrame()
    res['Fuente'] = 'Offline'
    # HR suele tener columnas como 'MES' y 'ANIO' o 'FECHA'
    date_col = next((c for c in df.columns if 'FECHA' in c.upper()), df.columns[0])
    res['Año-mes'] = pd.to_datetime(df[date_col]).dt.to_period('M').dt.to_timestamp()
    res['Año'] = res['Año-mes'].dt.year
    
    inv_col = next((c for c in df.columns if 'INVER' in c.upper() or 'TARIFA' in c.upper()), None)
    res['Inversión (MXN)'] = pd.to_numeric(df[inv_col], errors='coerce').fillna(0)
    res['Inversión F30'] = res['Inversión (MXN)'] * MULTIPLICADORES.get(medio_nombre.lower(), 1.0)
    
    res['#Grupo'] = df.get('MARCA', 'INDUSTRIA')
    res['Categoría'] = 'Automotriz'
    res['Producto'] = df.get('MODELO', 'Varios')
    res['medio'] = medio_nombre
    res['modelo'] = df.get('MODELO', 'Varios')
    return res

# ─────────────────────────────────────────────────────────────────────────────
# INTERFAZ DE USUARIO (STREAMLIT)
# ─────────────────────────────────────────────────────────────────────────────
st.title("🚀 Procesador de Inversión Automotriz")
st.markdown("Carga tus archivos según la marca para generar el consolidado.")

# Menú lateral para elegir qué procesar
with st.sidebar:
    st.header("Configuración")
    marca_seleccionada = st.selectbox(
        "¿Qué marca vas a procesar hoy?",
        ["GWM", "JAC", "KAVAK", "INDUSTRIA (HR)", "ADMETRICKS"]
    )
    st.divider()
    st.info("El archivo resultante tendrá el formato de 'automotriz.xlsx'")

final_df = pd.DataFrame()

# --- BLOQUE GWM ---
if marca_seleccionada == "GWM":
    st.subheader("📍 Panel GWM")
    col1, col2 = st.columns(2)
    with col1:
        f_off = st.file_uploader("Subir Naming Convention (Offline/OOH)", type=['xlsx'], key="gwm_off")
    with col2:
        f_on = st.file_uploader("Subir Resumen Digital (Online)", type=['xlsx'], key="gwm_on")
    
    if st.button("Procesar GWM"):
        dataframes = []
        if f_off:
            df = pd.read_excel(f_off)
            dataframes.append(process_naming_convention(df, "GWM"))
        if f_on:
            # Lógica simple para el excel de online
            df_on = pd.read_excel(f_on)
            # (Aquí iría tu lógica de 'Investment' * 1.3)
            st.success("Archivo Online detectado")
        
        if dataframes:
            final_df = pd.concat(dataframes)
            st.dataframe(final_df.head())

# --- BLOQUE JAC ---
elif marca_seleccionada == "JAC":
    st.subheader("📍 Panel JAC")
    f_jac = st.file_uploader("Subir Naming JAC", type=['xlsx'])
    if f_jac and st.button("Procesar JAC"):
        final_df = process_naming_convention(pd.read_excel(f_jac), "JAC INDUSTRIA")
        st.success("JAC procesado correctamente")

# --- BLOQUE INDUSTRIA (HR) ---
elif marca_seleccionada == "INDUSTRIA (HR)":
    st.subheader("📊 Panel Industria (HR Ratings)")
    st.info("Sube cada medio en su espacio correspondiente para aplicar los multiplicadores correctos.")
    
    tab1, tab2, tab3 = st.tabs(["📺 Televisión", "📻 Radio", "📰 Prensa"])
    
    with tab1:
        f_tv = st.file_uploader("Reporte HR - TV (Nacional/Local)", type=['xlsx'])
    with tab2:
        f_rd = st.file_uploader("Reporte HR - Radio", type=['xlsx'])
    with tab3:
        f_pr = st.file_uploader("Reporte HR - Prensa/Revistas", type=['xlsx'])
        
    if st.button("Procesar Industria"):
        list_ind = []
        if f_tv: list_ind.append(process_hr_ratings(pd.read_excel(f_tv), "TELEVISION"))
        if f_rd: list_ind.append(process_hr_ratings(pd.read_excel(f_rd), "RADIO"))
        if f_pr: list_ind.append(process_hr_ratings(pd.read_excel(f_pr), "PRENSA"))
        
        if list_ind:
            final_df = pd.concat(list_ind)
            st.success(f"Procesadas {len(final_df)} filas de industria.")

# ─────────────────────────────────────────────────────────────────────────────
# DESCARGA DE RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────
if not final_df.empty:
    st.divider()
    st.subheader("✅ Resultado Listo")
    
    # Botón para descargar el CSV compatible con Power BI
    csv = final_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="⬇️ Descargar layout_automotriz.csv",
        data=csv,
        file_name=f"upload_to_automotriz_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
    
    # Resumen visual rápido
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Filas", len(final_df))
    c2.metric("Inversión Total", f"${final_df['Inversión (MXN)'].sum():,.0f}")
    c3.metric("Meses Detectados", final_df['Año-mes'].dt.month.nunique())
    
