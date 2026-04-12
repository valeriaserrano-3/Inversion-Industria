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

# --- BLOQUE DASHBOARD GLOBAL: UNIFICACIÓN TOTAL BASADA EN "SHORT NAME" ---
# --- BLOQUE DASHBOARD GLOBAL: FIX CHEVROLET Y SUMATORIAS EXACTAS ---
elif marca_seleccionada == "Dashboard Global":
    st.title("📊 Dashboard Estratégico 2026")
    
    if 'dg_memoria_historica' not in st.session_state:
        st.session_state.dg_memoria_historica = pd.DataFrame()

    # CATÁLOGO MAESTRO (Nombres finales exactos)
    GRUPOS_VISTAS = {
        "GWM": ["GWM MEXICO", "NISSAN", "CHEVROLET", "VOLKSWAGEN", "HYUNDAI", "BYD", "KIA", "GEELY", "CHIREY", "MG", "GAC", "TOYOTA", "CHANGAN MEXICO", "EXEED"],
        "JAC": ["JAC", "JAC INDUSTRIA", "BYD", "NISSAN", "RAM", "CHEVROLET", "VOLKSWAGEN", "KIA", "HYUNDAI", "GEELY", "CHIREY", "RENAULT", "HONDA", "FORD", "MITSUBISHI", "MG", "TOYOTA", "GWM MEXICO", "PEUGEOT", "GAC", "SUZUKI", "CHANGAN MEXICO", "SEAT", "MAZDA", "FOTON", "JETOUR"],
        "KAVAK": ["KAVAK", "NISSAN", "CHEVROLET", "HYUNDAI", "VOLKSWAGEN", "KIA", "MITSUBISHI", "FORD", "GEELY", "JEEP", "INFINITI", "PEUGEOT", "CHIREY", "RENAULT", "TOYOTA", "MG", "BBVA AUTOMARKET", "HONDA"],
        "BAIC": ["BAIC", "MOTORNATION", "MG", "CHIREY", "BYD", "GEELY", "GAC MOTOR", "JETOUR", "CHANGAN MEXICO", "JAC"]
    }
    
    dg_archivo = st.file_uploader("Subir Reporte Mensual", type=['xlsx', 'csv'], key="dg_fix_chevrolet_v5")

    if dg_archivo:
        try:
            df_raw = pd.read_csv(dg_archivo) if dg_archivo.name.endswith('.csv') else pd.read_excel(dg_archivo)
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
            
            # Usamos "short name" como columna maestra
            col_ref = "short name" if "short name" in df_raw.columns else "#Grupo"

            if col_ref in df_raw.columns:
                df_temp = df_raw.copy()
                
                # --- FUNCIÓN DE UNIFICACIÓN QUIRÚRGICA ---
                def unificar_marcas_dashboard(valor):
                    v = str(valor).upper().strip()
                    
                    # NISSAN: Solo si es Nissan o Nissan Mexico/Mexicana
                    if v in ["BYD", "BYD AUTO", "BUILD YOUR DR B MEX"]:
                        return "BYD"
                        
                    # NISSAN: Solo si es Nissan o Nissan Mexico/Mexicana
                    if v in ["NISSAN", "NISSAN MEXICO", "NISSAN MEXICANA"]:
                        return "NISSAN"
                    
                    # VOLKSWAGEN: Solo si es VW o variantes de país
                    if v in ["VOLKSWAGEN", "VOLKSWAGEN MEXICO", "VOLKSWAGEN DE MEXICO", "VW"]:
                        return "VOLKSWAGEN"
                    
                    # CHEVROLET / GM: Unificar para evitar el salto de 59 a 109
                    if v in ["CHEVROLET", "GENERAL MOTORS", "GM", "GENERAL MOTORS MEX", "GMC"]:
                        return "CHEVROLET"

                    # GWM: Unificar 
                    if v in ["GWM", "GREAT WALL MOTOR", "GREAT WALL MOTOR MEX", "GWM Great Wall Motors", "GWM MEXICO", "HAVAL"]:
                        return "GWM MEXICO"
                        
                    # Chirey: Unificar las marcas
                    if v in ["CHERY", "CHIREY", "Chirey Motor", "CHIREY MOTOR MEXICO", "JETOUR MEXICO", "JAECOO", "OMODA", "OMODA+JAECOO"]:
                        return "Chirey"
                        
                    # MG: Unificar las marcas
                    if v in ["MG", "MG MOTOR", "MG MOTORS", "MG ROVER MEXICO", "MORRIS GARAGES", "MORRIS MOTORS"]:
                        return "MG"

                    # GAC: Unificar las marcas
                    if v in ["GAC", "GAC MOTOR"]:
                        return "GAC"

                    # Changan: Unificar las marcas
                    if v in ["CHANGAN", "CHANGAN AUTO", "CHANGAN MEXICO"]:
                        return "Changan"

                    return v

                df_temp['Marca_Final'] = df_temp[col_ref].apply(unificar_marcas_dashboard)
                df_temp['Monto'] = pd.to_numeric(df_temp['Inversión (MXN)'], errors='coerce').fillna(0)
                
                # Limpieza de Meses
                df_temp['Mes_Raw'] = df_temp['Año-mes'].astype(str).str.replace("'", "").str.strip().str.lower()
                mapa_meses = {'jan': 'Enero', 'feb': 'Febrero', 'mar': 'Marzo', 'apr': 'Abril', 'may': 'Mayo', 'jun': 'Junio'}
                df_temp['Mes_Nombre'] = df_temp['Mes_Raw'].str[:3].map(mapa_meses).fillna("Otros")
                
                # Medios
                def cat_medio(x):
                    f = str(x).upper()
                    if any(k in f for k in ['OOH', 'EXTERIOR', 'VALLA', 'MUPI', 'RELOJ', 'KIOSCO', 'COLUMNA', 'SITIO']): return 'OOH'
                    if any(k in f for k in ['OFFLINE', 'TV', 'RADIO', 'PRENSA']): return 'OFFLINE'
                    return 'ONLINE'
                df_temp['Medio_Final'] = df_temp['Fuente'].apply(cat_medio)
                
                st.session_state.dg_memoria_historica = df_temp
                st.success("✅ Datos procesados. Chevrolet, Nissan y VW ajustados.")

        except Exception as e:
            st.error(f"Error: {e}")

    # --- RENDERIZADO ---
    if not st.session_state.dg_memoria_historica.empty:
        df_full = st.session_state.dg_memoria_historica
        mes_sel = st.selectbox("📅 Selecciona el mes:", [m for m in df_full['Mes_Nombre'].unique() if m != "Otros"])
        df_mes = df_full[df_full['Mes_Nombre'] == mes_sel]
        
        import altair as alt
        tabs = st.tabs(list(GRUPOS_VISTAS.keys()))

        for i, grupo in enumerate(GRUPOS_VISTAS.keys()):
            with tabs[i]:
                marcas_ok = GRUPOS_VISTAS[grupo]
                # Filtramos SOLO las marcas del catálogo
                df_g = df_mes[df_mes['Marca_Final'].isin(marcas_ok)]
                
                if not df_g.empty:
                    st.markdown(f"## {grupo} - {mes_sel}")
                    
                    # Métricas con sumatorias limpias
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("TOTAL GRUPO", f"${df_g['Monto'].sum():,.0f}")
                    c2.metric("ONLINE", f"${df_g[df_g['Medio_Final'] == 'ONLINE']['Monto'].sum():,.0f}")
                    c3.metric("OFFLINE", f"${df_g[df_g['Medio_Final'] == 'OFFLINE']['Monto'].sum():,.0f}")
                    c4.metric("OOH", f"${df_g[df_g['Medio_Final'] == 'OOH']['Monto'].sum():,.0f}")
                    
                    # Gráfica
                    chart = alt.Chart(df_g).mark_bar(size=120).encode(
                        x=alt.X('Mes_Nombre:N', title="Mes"),
                        y=alt.Y('sum(Monto):Q', title="Inversión ($)"),
                        color=alt.Color('Medio_Final:N', scale=alt.Scale(domain=['OOH', 'OFFLINE', 'ONLINE'], range=['#2471A3', '#D35400', '#28B463'])),
                        tooltip=['Medio_Final', alt.Tooltip('sum(Monto)', format="$,.0f")]
                    ).properties(height=450)
                    st.altair_chart(chart, use_container_width=True)

                    st.write("### Detalle Consolidado (Sin duplicados)")
                    # Agrupamos para que Chevrolet solo aparezca UNA vez con su suma real
                    df_t = df_g.groupby('Marca_Final')['Monto'].sum().reset_index().sort_values('Monto', ascending=False)
                    st.dataframe(df_t.style.format({"Monto": "${:,.2f}"}), use_container_width=True)
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
