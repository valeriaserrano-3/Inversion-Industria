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
    st.subheader("🏢 Panel OOH (Publicidad Exterior)")
    
    # --- NUEVA SECCIÓN DE CONFIGURACIÓN DE FACTORES ---
    with st.expander("⚙️ Configurar Multiplicadores OOH", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            factor_primario = st.number_input("Multiplicador Inicial (Ej. x2)", value=2.0, step=0.1)
        with col_f2:
            factor_f30 = st.number_input("Factor F30 (Ej. x1.3)", value=1.3, step=0.1)
    
    st.info("Sube los reportes de OOH. El sistema aplicará: (Costo * Factor Inicial) * Factor F30")

    f_ooh = st.file_uploader("Subir archivo OOH", type=['xlsx', 'csv'], key="ooh_uploader")

    if f_ooh and st.button("Procesar OOH"):
        try:
            # 1. Leer archivo
            if f_ooh.name.endswith('.csv'):
                df_ooh = pd.read_csv(f_ooh)
            else:
                df_raw = pd.read_excel(f_ooh, header=None)
                primer_celda = str(df_raw.iloc[0, 0])
                if "Filtros aplicados" in primer_celda:
                    df_ooh = pd.read_excel(f_ooh, skiprows=2)
                else:
                    df_ooh = pd.read_excel(f_ooh, skiprows=1)

            df_ooh.columns = [str(c).strip() for c in df_ooh.columns]

            # 2. Transformación
            res_ooh = pd.DataFrame()
            res_ooh['#Grupo'] = df_ooh['Marca'].str.upper()
            res_ooh['Fuente'] = 'OOH'
            
            # Fechas
            if 'Año-Mes' in df_ooh.columns:
                res_ooh['Año-mes'] = pd.to_datetime(df_ooh['Año-Mes'], errors='coerce')
            elif 'Mes' in df_ooh.columns:
                res_ooh['Año-mes'] = df_ooh['Mes'].apply(lambda x: pd.to_datetime(f"2026-{x}-01", errors='coerce'))
            else:
                res_ooh['Año-mes'] = pd.Timestamp.now().replace(day=1)
            res_ooh['Año'] = res_ooh['Año-mes'].dt.year

            # --- LÓGICA DE INVERSIÓN SOLICITADA ---
            costo_col = next((c for c in df_ooh.columns if 'COSTO' in c.upper() or 'SUMA' in c.upper()), None)
            if costo_col:
                inv_raw = pd.to_numeric(df_ooh[costo_col], errors='coerce').fillna(0)
                
                # Primero multiplicamos por el factor primario (x2)
                inversion_base = inv_raw * factor_primario
                res_ooh['Inversión (MXN)'] = inversion_base
                
                # Luego aplicamos el factor F30 (x1.3) sobre el resultado anterior
                res_ooh['Inversión F30'] = inversion_base * factor_f30
            
            # Otros campos
            res_ooh['modelo'] = df_ooh.get('ProductoTag', 'INSTITUCIONAL').str.upper()
            res_ooh['Producto'] = res_ooh['modelo']
            res_ooh['medio'] = df_ooh.get('TipoPublicidad', 'OOH GENÉRICO')
            res_ooh['Categoría'] = 'OOH'

            final_df = res_ooh[res_ooh['Inversión (MXN)'] > 0].copy()
            final_df = final_df[~final_df['#Grupo'].str.contains("TOTAL", na=False)]

            if not final_df.empty:
                st.success(f"✅ OOH procesado con éxito aplicando factores x{factor_primario} y x{factor_f30}")
            else:
                st.warning("No se encontraron datos válidos.")

        except Exception as e:
            st.error(f"Error al procesar OOH: {e}")
            
        
# --- BLOQUE DASHBOARD GLOBAL ---
elif marca_seleccionada == "Dashboard Global":
    st.title("📊 Dashboard Estratégico 2026")

    # 1. MEMORIA PARA NO DUPLICAR Y GUARDAR MESES ANTERIORES
    if 'historico_master' not in st.session_state:
        st.session_state.historico_master = pd.DataFrame()

    # --- DICCIONARIO DE MARCAS (Según tus fotos) ---
    GRUPOS_FOCO = {
        "GWM": ["GWM", "GWM MOTORS", "GREAT WALL", "HAVAL", "ORA", "POER", "TANK", "WEY"],
        "JAC": ["JAC", "JAC MOTORS", "JAC INDUSTRIA"],
        "KAVAK": ["KAVAK"],
        "BAIC": ["BAIC", "JMC", "MOTORNATION"]
    }
    todas_foco = [item for sublist in GRUPOS_FOCO.values() for item in sublist]

    f_master = st.file_uploader("Subir Reporte Mensual (Ene-26, Feb-26...)", type=['xlsx', 'csv'])

    if f_master:
        # Leer archivo saltando encabezados de reporte
        df_raw = pd.read_excel(f_master, skiprows=3) if f_master.name.endswith('.xlsx') else pd.read_csv(f_master, skiprows=3)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]

        # Identificar columnas de meses 2026
        cols_2026 = [c for c in df_raw.columns if '26' in c]
        col_marca = 'Brand' if 'Brand' in df_raw.columns else 'Marca'

        if cols_2026:
            # Transformar a formato largo
            df_melt = df_raw.melt(id_vars=[col_marca], value_vars=cols_2026, var_name='Mes', value_name='Inversión')
            
            # --- NORMALIZACIÓN DE MEDIOS ---
            def limpiar_medios(row):
                # Si la fila tiene un valor de inversión pero no tiene nombre de medio 
                # (en el TableBuilder el medio suele venir abajo de la marca o en columna aparte)
                # Aquí ajustamos según la estructura de tus archivos:
                m = str(row[col_marca]).upper()
                if any(x in m for x in ['BILLBOARD', 'BUS', 'OOH', 'VALLA', 'MUPI']): return 'OOH'
                if any(x in m for x in ['DIGITAL', 'SOCIAL', 'FACEBOOK', 'GOOGLE', 'ONLINE']): return 'DIGITAL'
                return 'OTROS'

            df_melt['Categoria_Medio'] = df_melt[col_marca].apply(limpiar_medios)
            
            # Unir a la memoria y eliminar duplicados exactos
            st.session_state.historico_master = pd.concat([st.session_state.historico_master, df_melt]).drop_duplicates()
            st.success("✅ Datos actualizados. Se conservan meses previos en memoria.")

    # --- VISUALIZACIÓN ---
    if not st.session_state.historico_master.empty:
        df_view = st.session_state.historico_master.copy()
        
        # Crear los Tabs que pediste
        tab1, tab2 = st.tabs(["🎯 Marcas Foco (GWM/JAC/KAVAK/BAIC)", "🌐 Mercado Total"])

        with tab1:
            # Filtrar solo tus marcas
            df_foco = df_view[df_view[col_marca].str.upper().isin(todas_foco)].copy()
            
            # Gráfica Apilada
            import altair as alt
            st.write("### Evolución Mensual Marcas Foco")
            chart = alt.Chart(df_foco).mark_bar().encode(
                x=alt.X('Mes:O', sort=['Amount Jan-26', 'Amount Feb-26', 'Amount Mar-26']),
                y=alt.Y('sum(Inversión):Q', title="Inversión ($)"),
                color=alt.Color('Categoria_Medio:N', title="Medio"),
                tooltip=['Mes', 'Categoria_Medio', alt.Tooltip('sum(Inversión)', format="$,.2f")]
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)

            # Matriz Marcas vs Meses (2026)
            st.write("### Matriz Detallada")
            pivot_foco = df_foco.pivot_table(index=col_marca, columns='Mes', values='Inversión', aggfunc='sum', fill_value=0)
            st.dataframe(pivot_foco.style.format("${:,.2f}"), use_container_width=True)

        with tab2:
            st.write("### Top 25 Marcas de la Industria")
            # Tabla general para toda la industria
            pivot_gen = df_view.pivot_table(index=col_marca, columns='Mes', values='Inversión', aggfunc='sum', fill_value=0)
            pivot_gen['Total'] = pivot_gen.sum(axis=1)
            st.dataframe(pivot_gen.sort_values('Total', ascending=False).head(25).style.format("${:,.2f}"), use_container_width=True)
            
    else:
        st.warning("Aún no hay datos. Por favor sube un archivo de TableBuilder o Descarga.")

    # Botón para resetear memoria si es necesario
    if st.sidebar.button("🗑️ Limpiar Histórico (Reset)"):
        st.session_state.historico_master = pd.DataFrame()
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
