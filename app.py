import streamlit as st
import pandas as pd
import numpy as np
import io
import calendar
import warnings
import re
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inversión Automotriz", page_icon="🚗", layout="wide")

# --- FUNCIONES DE APOYO ---
def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    col = st.columns([1, 2, 1])[1]
    with col:
        st.title("Inversión Automotriz")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if pwd == "automotriz2026":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    return False

def get_month_from_name(filename):
    """Extrae fecha del nombre del archivo (ej: 'Reporte_Enero.xlsx')"""
    meses = {'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,
             'JULIO':7,'AGOSTO':8,'SEPTIEMBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12}
    name = filename.upper()
    for m, n in meses.items():
        if m in name:
            return pd.Timestamp(year=2026, month=n, day=1)
    return pd.Timestamp.now().replace(day=1)

def parse_yrmth(val):
    try:
        if isinstance(val, datetime): return val
        s = str(val).strip().lower()
        for i, m in enumerate(calendar.month_abbr):
            if m and s.startswith(m.lower()):
                return pd.Timestamp(year=int(s[3:]), month=i, day=1)
        return pd.to_datetime(val)
    except:
        return pd.NaT

# --- PROCESADORES ---
def process_naming_convention(df, grupo_nombre):
    df['monto'] = pd.to_numeric(df.get('monto', 0), errors='coerce').fillna(0)
    df['Bonificación Cliente'] = pd.to_numeric(df.get('Bonificación Cliente', 0), errors='coerce').fillna(0)
    df['Inversión (MXN)'] = df['monto'] + df['Bonificación Cliente']
    
    res = pd.DataFrame()
    res['Fuente'] = df['FUENTE'].apply(lambda x: 'OOH' if 'EXTERIOR' in str(x).upper() else 'Offline')
    res['Año-mes'] = df['yrmth'].apply(parse_yrmth)
    res['Año'] = res['Año-mes'].dt.year
    res['Inversión (MXN)'] = df['Inversión (MXN)']
    res['Inversión F30'] = df['Inversión (MXN)'] * 1.3
    res['#Grupo'] = grupo_nombre
    res['Categoría'] = df.get('OBJETIVO', 'Institucional')
    res['Producto'] = df.get('Modelos', 'Varios')
    res['medio'] = df['FUENTE']
    res['modelo'] = df.get('Modelos', 'Varios')
    return res

# --- INICIO DE APP ---
if not check_password():
    st.stop()

with st.sidebar:
    st.header("Configuración")
    marca_seleccionada = st.selectbox(
        "¿Qué marca vas a procesar hoy?",
        ["GWM", "JAC", "KAVAK", "INDUSTRIA (HR)", "Dashboard Global"]
    )

final_df = pd.DataFrame()

# --- LÓGICA DE MARCAS ---
if marca_seleccionada == "GWM":
    st.subheader("📍 Panel GWM")
    f_off = st.file_uploader("Subir Naming Convention", type=['xlsx'], key="gwm_off")
    if f_off and st.button("Procesar GWM"):
        df = pd.read_excel(f_off)
        final_df = process_naming_convention(df, "GWM")
        st.success("✅ GWM Procesado")

elif marca_seleccionada == "JAC":
    st.subheader("📍 Panel JAC")
    f_jac_on = st.file_uploader("Subir Seguimiento Digital", type=['xlsx'], key="jac_on")
    if f_jac_on and st.button("Procesar JAC"):
        try:
            df_on_raw = pd.read_excel(f_jac_on, sheet_name=0) # Lee la primera hoja si no existe 'TOTAL FINAL'
            res_on = pd.DataFrame()
            res_on['Inversión (MXN)'] = pd.to_numeric(df_on_raw.get('Gasto', 0), errors='coerce').fillna(0)
            res_on['#Grupo'] = "JAC"
            res_on['Año-mes'] = get_month_from_name(f_jac_on.name)
            final_df = res_on
            st.success("✅ JAC Procesado")
        except Exception as e:
            st.error(f"Error: {e}")

elif marca_seleccionada == "KAVAK":
    st.subheader("📍 Panel KAVAK")
    f_kavak = st.file_uploader("Subir Naming KAVAK", type=['xlsx'])
    if f_kavak and st.button("Procesar KAVAK"):
        df_kav = pd.read_excel(f_kavak)
        final_df = process_naming_convention(df_kav, "KAVAK")
        st.success("✅ KAVAK Procesado")

elif marca_seleccionada == "Dashboard Global":
    st.title("📊 Dashboard Estratégico 2026")
    if 'dg_memoria_historica' not in st.session_state:
        st.session_state.dg_memoria_historica = pd.DataFrame()

    GRUPOS_VISTAS = {
        "GWM": ["NISSAN", "CHEVROLET", "VOLKSWAGEN", "HYUNDAI", "BYD", "KIA", "GWM", "GEELY", "CHIREY OMODA", "MG", "GAC", "TOYOTA", "CHANGAN", "EXEED"],
        "JAC": ["BYD", "NISSAN", "RAM", "CHEVROLET", "VOLKSWAGEN", "KIA", "HYUNDAI", "GEELY", "CHIREY", "RENAULT", "HONDA", "FORD", "MITSUBISHI", "MG", "TOYOTA", "GWM MOTORS", "PEUGEOT", "GAC", "SUZUKI", "CHANGAN", "JAC", "JAC INDUSTRIA", "SEAT", "MAZDA", "FOTON", "JETOUR"],
        "KAVAK": ["NISSAN", "GENERAL MOTORS", "HYUNDAI", "VOLKSWAGEN", "KAVAK", "KIA", "MITSUBISHI", "FORD MOTOR", "GEELY", "JEEP", "INFINITI", "PEUGEOT", "CHIREY", "RENAULT", "TOYOTA", "MG", "BBVA AUTOMARKET", "HONDA"],
        "BAIC": ["MG", "CHIREY", "BYD", "GEELY", "GAC MOTOR", "JETOUR", "CHANGAN", "JAC", "MOTORNATION", "BAIC"]
    }
    
    dg_archivo = st.file_uploader("Subir Reporte Mensual", type=['xlsx', 'csv'], key="dg_main_up")
    if dg_archivo:
        # Lógica de carga...
        st.info("Archivo cargado para el dashboard.")

# --- SECCIÓN DE DESCARGA ---
if not final_df.empty:
    st.divider()
    st.subheader("✅ Resultado Listo")
    total_inv = final_df['Inversión (MXN)'].sum()
    st.metric("Inversión Total", f"${total_inv:,.2f}")
    
    csv = final_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("⬇️ Descargar Layout CSV", data=csv, file_name="resultado.csv", mime="text/csv")
    st.dataframe(final_df.head())
