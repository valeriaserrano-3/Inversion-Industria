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
    st.subheader("📍 Panel JAC (Online + Offline)")
    
    col1, col2 = st.columns(2)
    with col1:
        f_jac_off = st.file_uploader("Subir Naming JAC (Offline)", type=['xlsx'], key="jac_off")
    with col2:
        f_jac_on = st.file_uploader("Subir Seguimiento Digital (Online)", type=['xlsx'], key="jac_on")

    if st.button("Procesar JAC"):
        dataframes = []
        
        # 1. Procesar Offline si existe
        if f_jac_off:
            df_off = pd.read_excel(f_jac_off)
            dataframes.append(process_naming_convention(df_off, "JAC INDUSTRIA"))
            st.info("Archivo Offline de JAC cargado.")

        # 2. Procesar Online si existe
        if f_jac_on:
            try:
                # Intentar leer la hoja 'TOTAL FINAL'
                df_on_raw = pd.read_excel(f_jac_on, sheet_name='TOTAL FINAL')
                
                # Extraer mes del nombre del archivo para la columna Año-mes
                mes_detectado = get_month_from_name(f_jac_on.name)
                
                # Limpieza y Transformación Online
                res_on = pd.DataFrame()
                res_on['Fuente'] = 'Online'
                res_on['Año-mes'] = mes_detectado if mes_detectado else "Revisar Fecha"
                res_on['Año'] = datetime.now().year # O extraer del nombre
                
                # Inversión con multiplicador F30 (1.30)
                inv_raw = pd.to_numeric(df_on_raw['Gasto'], errors='coerce').fillna(0)
                res_on['Inversión (MXN)'] = inv_raw
                res_on['Inversión F30'] = inv_raw * MULTIPLICADORES['online']
                
                res_on['#Grupo'] = "JAC INDUSTRIA"
                res_on['modelo'] = df_on_raw['Modelo'].str.upper()
                
                # Usar el CAT_MAP para poner SUV, SEDAN, etc.
                res_on['Categoría'] = res_on['modelo'].map(CAT_MAP).fillna('SUV')
                res_on['medio'] = df_on_raw['Plataforma']
                res_on['Producto'] = res_on['modelo']
                
                dataframes.append(res_on)
                st.success("Archivo Online de JAC procesado con éxito.")
            except Exception as e:
                st.error(f"Error al procesar el archivo Online: {e}. Asegúrate de que tenga la pestaña 'TOTAL FINAL'.")

        if dataframes:
            final_df = pd.concat(dataframes, ignore_index=True)
            st.write("Vista previa de los datos unificados:")
            st.dataframe(final_df.head())
            
# --- BLOQUE KAVAK ---
elif marca_seleccionada == "KAVAK":
    st.subheader("📍 Panel KAVAK")
    
    
    f_kavak = st.file_uploader("Subir Naming Convention KAVAK", type=['xlsx'], key="kavak_file")
    
    if f_kavak and st.button("Procesar KAVAK"):
        try:
            df_kav = pd.read_excel(f_kavak)
            
            # 1. Limpieza de columnas (quitar espacios)
            df_kav.columns = [str(c).strip() for c in df_kav.columns]
            
            # 2. Definir lógica de Fuente (Basado en tu script original)
            def get_fuente_kavak(medio):
                medio_up = str(medio).upper()
                offline_keywords = ['TV', 'RADIO', 'PRENSA', 'PERIÓDICO', 'CINE', 'ABIERTA', 'PAGA']
                if any(kw in medio_up for kw in offline_keywords):
                    return 'Offline'
                return 'OOH'

            # 3. Transformación al layout maestro
            res_kav = pd.DataFrame()
            
            # Inversión = monto + Bonificación
            monto = pd.to_numeric(df_kav.get('monto', 0), errors='coerce').fillna(0)
            bonif = pd.to_numeric(df_kav.get('Bonificación Cliente', 0), errors='coerce').fillna(0)
            inv_total = monto + bonif
            
            res_kav['Fuente'] = df_kav['medio'].apply(get_fuente_kavak)
            res_kav['Año-mes'] = df_kav['yrmth'].apply(parse_yrmth)
            res_kav['Año'] = res_kav['Año-mes'].dt.year
            res_kav['Inversión (MXN)'] = inv_total
            
            # Aplicar multiplicador si es necesario (ej. 1.0 para Kavak o 1.3 si es F30)
            res_kav['Inversión F30'] = inv_total * 1.0 
            
            res_kav['#Grupo'] = "KAVAK"
            res_kav['modelo'] = df_kav.get('Modelos', 'INSTITUCIONAL').str.upper()
            
            # Categoría basada en columna OBJETIVO
            res_kav['Categoría'] = df_kav.get('OBJETIVO', 'INSTITUCIONAL').str.upper()
            res_kav['medio'] = df_kav['medio']
            res_kav['Producto'] = res_kav['modelo']
            
            # Filtrar filas sin inversión
            final_kav = res_kav[res_kav['Inversión (MXN)'] > 0].copy()
            
            if not final_kav.empty:
                final_df = final_kav # Para que el botón de descarga lo detecte
                st.success(f"✅ Kavak procesado: {len(final_kav)} registros encontrados.")
                st.dataframe(final_kav.head())
            else:
                st.warning("No se encontraron registros con inversión mayor a $0.")
                
        except Exception as e:
            st.error(f"Error al procesar Kavak: {e}")

# --- BLOQUE INDUSTRIA (HR) ---
elif marca_seleccionada == "INDUSTRIA (HR)":
    st.subheader("📊 Panel Industria (HR Ratings)")
    
    with st.expander("⚙️ Configurar Multiplicadores de Inversión", expanded=True):
        # 1. Nuevo factor que afecta a TODO
        m_general = st.number_input("Factor General (Base)", min_value=1.0, value=1.0, step=0.1, help="Primero se multiplica por este valor")
        
        st.divider() # Línea divisoria
        
        # 2. Factores específicos por medio
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            m_tv = st.number_input("Factor TV", min_value=1.0, value=1.3, step=0.1)
        with col_m2:
            m_rd = st.number_input("Factor Radio", min_value=1.0, value=1.3, step=0.1)
        with col_m3:
            m_pr = st.number_input("Factor Prensa", min_value=1.0, value=1.0, step=0.1)
            
    multiplicadores_usuario = {
        "TELEVISION": m_tv,
        "RADIO": m_rd,
        "PRENSA": m_pr
    }

    st.info(f"Fórmula aplicada: (Inversión × {m_general}) × Factor de Medio")
    
    tab1, tab2, tab3 = st.tabs(["📺 Televisión", "📻 Radio", "📰 Prensa"])
    
    with tab1:
        f_tv = st.file_uploader("Reporte HR - TV", type=['xlsx'], key="hr_tv")
    with tab2:
        f_rd = st.file_uploader("Reporte HR - Radio", type=['xlsx'], key="hr_rd")
    with tab3:
        f_pr = st.file_uploader("Reporte HR - Prensa", type=['xlsx'], key="hr_pr")
        
    if st.button("Procesar Industria"):
        list_ind = []
        
        def process_hr_custom(file, medio_key):
            df_temp = pd.read_excel(file)
            res = process_hr_ratings(df_temp, medio_key)
            
            # --- AQUÍ SUCEDE LA DOBLE MULTIPLICACIÓN ---
            factor_medio = multiplicadores_usuario.get(medio_key, 1.0)
            
            # Paso 1: Multiplicar por Factor General
            # Paso 2: Multiplicar por Factor de Medio
            res['Inversión F30'] = (res['Inversión (MXN)'] * m_general) * factor_medio
            
            return res

        if f_tv: list_ind.append(process_hr_custom(f_tv, "TELEVISION"))
        if f_rd: list_ind.append(process_hr_custom(f_rd, "RADIO"))
        if f_pr: list_ind.append(process_hr_custom(f_pr, "PRENSA"))
        
        if list_ind:
            final_df = pd.concat(list_ind, ignore_index=True)
            st.success(f"✅ Procesadas {len(final_df)} filas con doble factor.")
            st.dataframe(final_df.head())
            
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
