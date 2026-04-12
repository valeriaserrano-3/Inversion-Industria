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
        ["GWM", "JAC", "KAVAK", "INDUSTRIA (HR)", "ADMETRICKS", "OOH", "Dashboard Global"]
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
            df_on = pd.read_excel(f_on)
            # Aquí puedes añadir la lógica de procesamiento para Online de GWM
            st.info("Procesando archivo Online...")
        
        if dataframes:
            final_df = pd.concat(dataframes, ignore_index=True)
            st.success("✅ GWM Procesado. Revisa el resumen abajo.")

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
        if f_jac_off:
            df_off = pd.read_excel(f_jac_off)
            dataframes.append(process_naming_convention(df_off, "JAC INDUSTRIA"))

        if f_jac_on:
            try:
                df_on_raw = pd.read_excel(f_jac_on, sheet_name='TOTAL FINAL')
                mes_detectado = get_month_from_name(f_jac_on.name)
                res_on = pd.DataFrame()
                res_on['Fuente'] = 'Online'; res_on['#Grupo'] = "JAC INDUSTRIA"
                res_on['Año-mes'] = mes_detectado if mes_detectado else pd.Timestamp.now().replace(day=1)
                res_on['Año'] = res_on['Año-mes'].dt.year
                inv_raw = pd.to_numeric(df_on_raw['Gasto'], errors='coerce').fillna(0)
                res_on['Inversión (MXN)'] = inv_raw
                res_on['Inversión F30'] = inv_raw * 1.3
                res_on['modelo'] = df_on_raw['Modelo'].str.upper()
                res_on['Categoría'] = res_on['modelo'].map(CAT_MAP).fillna('SUV')
                res_on['medio'] = df_on_raw['Plataforma']
                res_on['Producto'] = res_on['modelo']
                dataframes.append(res_on)
            except Exception as e:
                st.error(f"Error en JAC Online: {e}")

        if dataframes:
            final_df = pd.concat(dataframes, ignore_index=True)
            st.success("✅ JAC Procesado correctamente.")

# --- BLOQUE KAVAK ---
elif marca_seleccionada == "KAVAK":
    st.subheader("📍 Panel KAVAK")
    f_kavak = st.file_uploader("Subir Naming Convention KAVAK", type=['xlsx'], key="kavak_file")
    
    if f_kavak and st.button("Procesar KAVAK"):
        df_kav = pd.read_excel(f_kavak)
        df_kav.columns = [str(c).strip() for c in df_kav.columns]
        res_kav = pd.DataFrame()
        monto = pd.to_numeric(df_kav.get('monto', 0), errors='coerce').fillna(0)
        bonif = pd.to_numeric(df_kav.get('Bonificación Cliente', 0), errors='coerce').fillna(0)
        res_kav['Inversión (MXN)'] = monto + bonif
        res_kav['Inversión F30'] = res_kav['Inversión (MXN)'] * 1.0
        res_kav['Fuente'] = 'Offline'; res_kav['#Grupo'] = "KAVAK"
        res_kav['Año-mes'] = df_kav['yrmth'].apply(parse_yrmth)
        res_kav['Año'] = res_kav['Año-mes'].dt.year
        res_kav['modelo'] = df_kav.get('Modelos', 'INSTITUCIONAL').str.upper()
        res_kav['medio'] = df_kav['medio']
        res_kav['Producto'] = res_kav['modelo']
        res_kav['Categoría'] = df_kav.get('OBJETIVO', 'INSTITUCIONAL').str.upper()
        final_df = res_kav[res_kav['Inversión (MXN)'] > 0].copy()
        st.success("✅ KAVAK Procesado.")

# --- BLOQUE INDUSTRIA (HR) ---
elif marca_seleccionada == "INDUSTRIA (HR)":
    st.subheader("📊 Panel Industria (HR Ratings)")
    with st.expander("⚙️ Configuración de Factores", expanded=False):
        m_general = st.number_input("Factor General", value=1.3)
        m_tv_abierta = st.number_input("TV Abierta", value=0.40)
        m_tv_paga = st.number_input("TV Paga", value=0.60)
        m_radio = st.number_input("Radio", value=0.70)
    
    factores = {"TELEVISION ABIERTA": m_tv_abierta, "TELEVISION PAGA": m_tv_paga, "RADIO": m_radio, "PRENSA": 1.0, "REVISTAS": 1.0}
    t1, t2, t3 = st.tabs(["📺 TV", "📻 Radio", "📰 Impresos"])
    with t1: f_tv = st.file_uploader("Excel TV", type=['xlsx'])
    with t2: f_rd = st.file_uploader("Excel Radio", type=['xlsx'])
    with t3: f_pr = st.file_uploader("Excel Impresos", type=['xlsx'])

    if st.button("Procesar Industria"):
        list_ind = []
        files = [(f_tv, "TELEVISION ABIERTA"), (f_rd, "RADIO"), (f_pr, "PRENSA")]
        for f, m in files:
            if f:
                df_t = pd.read_excel(f)
                res = process_hr_ratings(df_t, m)
                res['Inversión F30'] = (res['Inversión (MXN)'] * m_general) * factores.get(m, 1.0)
                list_ind.append(res)
        if list_ind:
            final_df = pd.concat(list_ind, ignore_index=True)
            st.success("✅ Industria Procesada.")

# --- BLOQUE ADMETRICKS ---
elif marca_seleccionada == "ADMETRICKS":
    st.subheader("📊 Panel Admetricks")
    BRAND_MAP = {"GWM MOTORS": "GWM Motors", "JAC MOTORS": "JAC INDUSTRIA", "KAVAK": "KAVAK"}
    f_adme = st.file_uploader("Subir Admetricks", type=['xlsx'])
    if f_adme and st.button("Procesar Admetricks"):
        df_ad = pd.read_excel(f_adme)
        res_ad = pd.DataFrame()
        res_ad['#Grupo'] = df_ad['Marca'].str.upper().map(BRAND_MAP).fillna(df_ad['Marca'])
        res_ad['Inversión (MXN)'] = pd.to_numeric(df_ad['Valorización Est.'], errors='coerce').fillna(0)
        res_ad['Inversión F30'] = res_ad['Inversión (MXN)'] * 1.3
        res_ad['Fuente'] = 'Online'; res_ad['Categoría'] = 'ADMETRICKS'
        res_ad['Año-mes'] = pd.Timestamp.now().replace(day=1)
        final_df = res_ad[res_ad['Inversión (MXN)'] > 0].copy()
        st.success("✅ Admetricks Procesado.")

# --- BLOQUE OOH ---
elif marca_seleccionada == "OOH":
    st.subheader("🏢 Panel OOH")
    f_ooh = st.file_uploader("Subir OOH", type=['xlsx', 'csv'])
    if f_ooh and st.button("Procesar OOH"):
        df_ooh = pd.read_excel(f_ooh, skiprows=1) if not f_ooh.name.endswith('.csv') else pd.read_csv(f_ooh)
        res_ooh = pd.DataFrame()
        res_ooh['#Grupo'] = df_ooh['Marca'].str.upper()
        inv_raw = pd.to_numeric(df_ooh.filter(like='Costo').iloc[:,0], errors='coerce').fillna(0)
        res_ooh['Inversión (MXN)'] = inv_raw
        res_ooh['Inversión F30'] = inv_raw * 1.3
        res_ooh['Fuente'] = 'OOH'; res_ooh['Año-mes'] = pd.Timestamp.now().replace(day=1)
        final_df = res_ooh[res_ooh['Inversión (MXN)'] > 0].copy()
        st.success("✅ OOH Procesado.")

# --- BLOQUE DASHBOARD GLOBAL CORREGIDO (GRÁFICA SIN DUPLICADOS) ---
elif marca_seleccionada == "Dashboard Global":
    st.title("📊 Dashboard Estratégico 2026")
    
    if 'dg_memoria_historica' not in st.session_state:
        st.session_state.dg_memoria_historica = pd.DataFrame()

    # Listas de marcas por pestaña
    GRUPOS_VISTAS = {
        "GWM": ["NISSAN", "CHEVROLET", "VOLKSWAGEN", "HYUNDAI", "BYD", "KIA", "GWM", "GEELY", "CHIREY OMODA", "MG", "GAC", "TOYOTA", "CHANGAN", "EXEED"],
        "JAC": ["BYD", "NISSAN", "RAM", "CHEVROLET", "VOLKSWAGEN", "KIA", "HYUNDAI", "GEELY", "CHIREY", "RENAULT", "HONDA", "FORD", "MITSUBISHI", "MG", "TOYOTA", "GWM MOTORS", "PEUGEOT", "GAC", "SUZUKI", "CHANGAN", "JAC", "JAC INDUSTRIA", "SEAT", "MAZDA", "FOTON", "JETOUR"],
        "KAVAK": ["NISSAN", "GENERAL MOTORS", "HYUNDAI", "VOLKSWAGEN", "KAVAK", "KIA", "MITSUBISHI", "FORD MOTOR", "GEELY", "JEEP", "INFINITI", "PEUGEOT", "CHIREY", "RENAULT", "TOYOTA", "MG", "BBVA AUTOMARKET", "HONDA"],
        "BAIC": ["MG", "CHIREY", "BYD", "GEELY", "GAC MOTOR", "JETOUR", "CHANGAN", "JAC", "MOTORNATION", "BAIC"]
    }
    
    dg_archivo = st.file_uploader("Subir Reporte Mensual", type=['xlsx', 'csv'], key="dg_fix_final")

    if dg_archivo:
        # Procesamiento de archivo
        dg_df_raw = pd.read_csv(dg_archivo) if dg_archivo.name.endswith('.csv') else pd.read_excel(dg_archivo)
        dg_df_raw.columns = [str(c).strip() for c in dg_df_raw.columns]

        if '#Grupo' in dg_df_raw.columns:
            dg_temp = dg_df_raw.copy()
            dg_temp['Monto'] = pd.to_numeric(dg_temp['Inversión (MXN)'], errors='coerce').fillna(0)
            dg_temp['Periodo'] = pd.to_datetime(dg_temp['Año-mes'], errors='coerce')
            dg_temp['Marca_Final'] = dg_temp['#Grupo'].str.upper()
            dg_temp['Medio_Final'] = dg_temp['Fuente'].str.upper().fillna('ONLINE')
            
            st.session_state.dg_memoria_historica = dg_temp.dropna(subset=['Periodo'])
            st.success("✅ Datos sincronizados.")

    if not st.session_state.dg_memoria_historica.empty:
        df_display = st.session_state.dg_memoria_historica.copy()
        import altair as alt
        
        tabs = st.tabs(list(GRUPOS_VISTAS.keys()))

        for i, nombre_grupo in enumerate(GRUPOS_VISTAS.keys()):
            with tabs[i]:
                marcas_foco = GRUPOS_VISTAS[nombre_grupo]
                df_g = df_display[df_display['Marca_Final'].isin(marcas_foco)]
                
                if not df_g.empty:
                    # --- 1. TARJETAS DE MÉTRICAS REINTEGRADAS ---
                    t_total = df_g['Monto'].sum()
                    t_on = df_g[df_g['Medio_Final'].str.contains('ONLINE|DIGITAL', na=False)]['Monto'].sum()
                    t_off = df_g[df_g['Medio_Final'].str.contains('OFFLINE|TV|RADIO|PRENSA', na=False)]['Monto'].sum()
                    t_ooh = df_g[df_g['Medio_Final'].str.contains('OOH|EXTERIOR', na=False)]['Monto'].sum()

                    st.markdown(f"### Resumen {nombre_grupo}")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("TOTAL GRUPO", f"${t_total:,.0f}")
                    c2.metric("ONLINE", f"${t_on:,.0f}")
                    c3.metric("OFFLINE", f"${t_off:,.0f}")
                    c4.metric("OOH", f"${t_ooh:,.0f}")
                    st.divider()

                    # --- 2. GRÁFICO CON BARRA MÁS ANCHA ---
                    # Agrupamos por mes y medio para evitar barras traslapadas
                    df_plot = df_g.groupby([df_g['Periodo'].dt.strftime('%B %Y'), 'Medio_Final'])['Monto'].sum().reset_index()
                    df_plot.columns = ['Mes', 'Medio_Final', 'Monto']

                    chart = alt.Chart(df_plot).mark_bar(
                        size=60  # <-- Esto hace la barra más gruesa
                    ).encode(
                        x=alt.X('Mes:N', title="Mes", sort=None),
                        y=alt.Y('Monto:Q', title="Inversión ($)", axis=alt.Axis(format="$.2s")),
                        color=alt.Color('Medio_Final:N', 
                                       scale=alt.Scale(domain=['OOH', 'OFFLINE', 'ONLINE'], 
                                                       range=['#2471A3', '#D35400', '#28B463'])),
                        tooltip=['Mes', 'Medio_Final', alt.Tooltip('Monto', format="$,.0f")]
                    ).properties(height=500)

                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.warning(f"No hay datos para las marcas de {nombre_grupo} en este archivo.")

    if st.sidebar.button("🗑️ Limpiar Datos Actuales"):
        st.session_state.dg_memoria_historica = pd.DataFrame()
        st.rerun()
# ─────────────────────────────────────────────────────────────────────────────
# DESCARGA DE RESULTADOS (FINAL DEL SCRIPT)
# ─────────────────────────────────────────────────────────────────────────────
if not final_df.empty:
    st.divider()
    st.subheader("✅ Resultado Listo")
    
    # 1. MÉTRICAS (Números grandes en el formato que pediste)
    c1, c2, c3 = st.columns(3)
    total_inv = final_df['Inversión (MXN)'].sum()
    
    c1.metric("Total Filas", f"{len(final_df):,}")
    
    # Formato de Millones para la métrica
    if total_inv >= 1_000_000:
        inv_format = f"${total_inv / 1_000_000:.1f}M"
    else:
        inv_format = f"${total_inv:,.0f}"
        
    c2.metric("Inversión Total", inv_format)
    c3.metric("Meses Detectados", final_df['Año-mes'].dt.month.nunique())

    # 2. GRÁFICA DE BARRAS (Con formato de moneda)
    st.write("### Inversión por Marca/Grupo")
    import altair as alt
    
    # Agrupamos datos para la gráfica
    chart_data = final_df.groupby('#Grupo')['Inversión (MXN)'].sum().reset_index()
    
    # Creamos la gráfica con formato de moneda en el tooltip (el cuadrito que sale al pasar el mouse)
    chart = alt.Chart(chart_data).mark_bar(color='#0077b6').encode(
        x=alt.X('#Grupo:N', title="Marca", sort='-y'),
        y=alt.Y('Inversión (MXN):Q', title="Inversión Acumulada ($)"),
        tooltip=[
            alt.Tooltip('#Grupo:N', title="Marca"),
            alt.Tooltip('Inversión (MXN):Q', title="Total", format="$,.2f") # <--- Comas y $ aquí
        ]
    ).properties(height=400)
    
    st.altair_chart(chart, use_container_width=True)

    # 3. BOTÓN DE DESCARGA
    csv = final_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="⬇️ Descargar layout_automotriz.csv",
        data=csv,
        file_name=f"upload_to_automotriz_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # 4. TABLA DETALLADA (Con formato de moneda en las celdas)
    st.write("### Vista previa de los datos")
    st.dataframe(
        final_df.style.format({
            "Inversión (MXN)": "${:,.2f}",
            "Inversión F30": "${:,.2f}"
        }),
        use_container_width=True
    )
