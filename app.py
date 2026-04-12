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

elif marca_seleccionada == "Dashboard Global":
        st.title("📊 Dashboard Estratégico 2026")
        
        if 'dg_memoria_historica' not in st.session_state:
            st.session_state.dg_memoria_historica = pd.DataFrame()

        # --- LISTAS MAESTRAS ---
        GRUPOS_VISTAS = {
            "GWM": ["NISSAN", "CHEVROLET", "VOLKSWAGEN", "HYUNDAI", "BYD", "KIA", "GWM", "GEELY", "CHIREY OMODA", "MG", "GAC", "TOYOTA", "CHANGAN", "EXEED"],
            "JAC": ["BYD", "NISSAN", "RAM", "CHEVROLET", "VOLKSWAGEN", "KIA", "HYUNDAI", "GEELY", "CHIREY", "RENAULT", "HONDA", "FORD", "MITSUBISHI", "MG", "TOYOTA", "GWM MOTORS", "PEUGEOT", "GAC", "SUZUKI", "CHANGAN", "JAC", "JAC INDUSTRIA", "SEAT", "MAZDA", "FOTON", "JETOUR"],
            "KAVAK": ["NISSAN", "GENERAL MOTORS", "HYUNDAI", "VOLKSWAGEN", "KAVAK", "KIA", "MITSUBISHI", "FORD MOTOR", "GEELY", "JEEP", "INFINITI", "PEUGEOT", "CHIREY", "RENAULT", "TOYOTA", "MG", "BBVA AUTOMARKET", "HONDA"],
            "BAIC": ["MG", "CHIREY", "BYD", "GEELY", "GAC MOTOR", "JETOUR", "CHANGAN", "JAC", "MOTORNATION", "BAIC"]
        }
        
        dg_todas_foco = list(set([m for sub in GRUPOS_VISTAS.values() for m in sub]))
        dg_archivo = st.file_uploader("Subir Reporte Mensual", type=['xlsx', 'csv'], key="dg_v23_final")

        if dg_archivo:
            if dg_archivo.name.endswith('.csv'):
                dg_df_raw = pd.read_csv(dg_archivo)
            else:
                df_check = pd.read_excel(dg_archivo, nrows=5)
                skip = 3 if any(df_check.iloc[:,0].astype(str).str.contains("Fuente", na=False)) else 0
                dg_df_raw = pd.read_excel(dg_archivo, skiprows=skip)
            
            dg_df_raw.columns = [str(c).strip() for c in dg_df_raw.columns]

            if '#Grupo' in dg_df_raw.columns:
                dg_temp = dg_df_raw.copy()
                dg_temp['Marca_Original'] = dg_temp['#Grupo']
                dg_temp['Periodo'] = dg_temp['Año-mes']
                dg_temp['Monto'] = pd.to_numeric(dg_temp['Inversión (MXN)'], errors='coerce').fillna(0)
                dg_temp['Fuente_Raw'] = dg_temp['Fuente'].fillna('OTROS')
            else:
                dg_col_marca = next((c for c in dg_df_raw.columns if c.lower() in ['brand', 'marca']), None)
                dg_cols_2026 = [c for c in dg_df_raw.columns if '26' in c]
                if dg_col_marca and dg_cols_2026:
                    dg_temp = dg_df_raw.melt(id_vars=[dg_col_marca], value_vars=dg_cols_2026, var_name='Periodo', value_name='Monto')
                    dg_temp['Marca_Original'] = dg_temp[dg_col_marca]
                    dg_temp['Monto'] = pd.to_numeric(dg_temp['Monto'], errors='coerce').fillna(0)
                    dg_temp['Fuente_Raw'] = dg_temp['Marca_Original']
                else: dg_temp = pd.DataFrame()

            if not dg_temp.empty:
                def dg_cat(x):
                    v = str(x).upper()
                    if any(k in v for k in ['BILLBOARD', 'BUS', 'OOH', 'VALLA', 'EXTERIOR']): return 'OOH'
                    if any(k in v for k in ['DIGITAL', 'SOCIAL', 'ONLINE', 'WEB']): return 'ONLINE'
                    if any(k in v for k in ['TV', 'RADIO', 'PRENSA', 'OFFLINE']): return 'OFFLINE'
                    return 'ONLINE'
                
                dg_temp['Medio_Final'] = dg_temp['Fuente_Raw'].apply(dg_cat)
                def asignar_marca_limpia(txt):
                    t = str(txt).upper()
                    for m in dg_todas_foco:
                        if m in t: return m
                    return t
                dg_temp['Marca_Final'] = dg_temp['Marca_Original'].apply(asignar_marca_limpia)
                
                # --- LIMPIEZA DE DUPLICADOS REAL ---
                dg_final_to_save = dg_temp[['Marca_Final', 'Periodo', 'Monto', 'Medio_Final']].copy()
                periodos_nuevos = dg_final_to_save['Periodo'].unique()
                df_historial = st.session_state.dg_memoria_historica
                
                if not df_historial.empty:
                    df_historial = df_historial[~df_historial['Periodo'].isin(periodos_nuevos)]
                
                st.session_state.dg_memoria_historica = pd.concat([df_historial, dg_final_to_save])
                st.success("✅ Datos actualizados.")

        if not st.session_state.dg_memoria_historica.empty:
            df_display = st.session_state.dg_memoria_historica.copy()
            import altair as alt
            tabs = st.tabs(list(GRUPOS_VISTAS.keys()) + ["MERCADO TOTAL"])

            for i, nombre_grupo in enumerate(GRUPOS_VISTAS.keys()):
                with tabs[i]:
                    lista_marcas = GRUPOS_VISTAS[nombre_grupo]
                    df_grupo = df_display[df_display['Marca_Final'].isin(lista_marcas)]
                    
                    if not df_grupo.empty:
                        # KPIs superiores
                        t_gral = df_grupo['Monto'].sum()
                        t_on = df_grupo[df_grupo['Medio_Final']=='ONLINE']['Monto'].sum()
                        t_off = df_grupo[df_grupo['Medio_Final']=='OFFLINE']['Monto'].sum()
                        t_ooh = df_grupo[df_grupo['Medio_Final']=='OOH']['Monto'].sum()

                        st.write(f"### Resumen Inversión - {nombre_grupo}")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("TOTAL GRUPO", f"${t_gral:,.0f}")
                        c2.metric("ONLINE", f"${t_on:,.0f}")
                        c3.metric("OFFLINE", f"${t_off:,.0f}")
                        c4.metric("OOH", f"${t_ooh:,.0f}")
                        st.markdown("---")

                        # --- GRÁFICA CORREGIDA PARA COINCIDIR CON LOS TOTALES ---
                        # Agrupamos todo por Mes y Medio para que la barra sume EXACTAMENTE lo mismo que las tarjetas
                        df_plot = df_grupo.groupby(['Periodo', 'Medio_Final'])['Monto'].sum().reset_index()
                        df_total_mes = df_plot.groupby('Periodo')['Monto'].sum().reset_index()

                        # Base de la gráfica
                        base = alt.Chart(df_plot).encode(x=alt.X('Periodo:O', title="Mes"))

                        # 1. Las barras apiladas
                        bars = base.mark_bar().encode(
                            y=alt.Y('Monto:Q', title="Inversión Total", stack="zero"),
                            color=alt.Color('Medio_Final:N', 
                                           scale=alt.Scale(domain=['OOH', 'OFFLINE', 'ONLINE'], 
                                                         range=['#2471A3', '#D35400', '#28B463']),
                                           title="Categoría"),
                            tooltip=[alt.Tooltip('Periodo'), alt.Tooltip('Medio_Final'), alt.Tooltip('Monto', format='$,.0f')]
                        )

                        # 2. Etiquetas BLANCAS dentro de cada sección (Monto real)
                        labels = base.mark_text(color='white', fontWeight='bold', dy=10, size=12).encode(
                            y=alt.Y('Monto:Q', stack='zero'),
                            text=alt.Text('Monto:Q', format='$.3s') # Ejemplo: $287M
                        )

                        # 3. TOTAL NEGRO arriba de toda la barra
                        totals = alt.Chart(df_total_mes).mark_text(dy=-15, fontWeight='bold', size=15, color='black').encode(
                            x=alt.X('Periodo:O'),
                            y=alt.Y('Monto:Q'),
                            text=alt.Text('Monto:Q', format='$.3s')
                        )

                        st.altair_chart((bars + labels + totals).properties(height=500), use_container_width=True)

                        # Tabla detalle
                        st.write("#### Detalle por Marca")
                        piv_g = df_grupo.pivot_table(index='Marca_Final', columns='Periodo', values='Monto', aggfunc='sum', fill_value=0)
                        piv_g = piv_g.reindex(lista_marcas).dropna(how='all')
                        st.dataframe(piv_g.style.format("${:,.2f}"), use_container_width=True)

        if st.sidebar.button("🗑️ Resetear Memoria Dashboard", key="dg_final_reset"):
            st.session_state.dg_memoria_historica = pd.DataFrame()
            st.rerun()

# --- BLOQUE DASHBOARD GLOBAL CORREGIDO ---
elif marca_seleccionada == "Dashboard Global":
    st.title("📊 Dashboard Estratégico 2026")
    
    # Inicialización de memoria si no existe
    if 'dg_memoria_historica' not in st.session_state:
        st.session_state.dg_memoria_historica = pd.DataFrame()

    with st.sidebar:
        if st.button("🗑️ Limpiar Memoria"):
            st.session_state.dg_memoria_historica = pd.DataFrame()
            st.rerun()

    dg_archivo = st.file_uploader("Subir Reporte Mensual (Layout Automotriz)", type=['xlsx', 'csv'], key="dg_uploader")

    if dg_archivo:
        # 1. Lectura de datos
        dg_df_raw = pd.read_excel(dg_archivo) if dg_archivo.name.endswith('.xlsx') else pd.read_csv(dg_archivo)
        dg_df_raw.columns = [str(c).strip() for c in dg_df_raw.columns]

        # 2. Procesamiento Limpio (Evita que los montos se dupliquen)
        dg_temp = pd.DataFrame()
        
        # Identificar columna de inversión (Usamos MXN para coincidir con tus capturas)
        inv_col = 'Inversión (MXN)' if 'Inversión (MXN)' in dg_df_raw.columns else 'monto'
        
        dg_temp['Monto'] = pd.to_numeric(dg_df_raw[inv_col], errors='coerce').fillna(0)
        dg_temp['Periodo'] = dg_df_raw['yrmth'].apply(parse_yrmth)
        dg_temp['Marca_Final'] = dg_df_raw.get('#Grupo', 'SIN MARCA')
        
        # Mapeo de medios para que coincidan con los nombres de tu gráfica
        def asignar_medio(x):
            v = str(x).upper()
            if any(k in v for k in ['EXTERIOR', 'OOH', 'BILLBOARD']): return 'OOH'
            if any(k in v for k in ['DIGITAL', 'ONLINE', 'SOCIAL']): return 'ONLINE'
            return 'OFFLINE'
        
        dg_temp['Medio_Final'] = dg_df_raw['FUENTE'].apply(asignar_medio)
        
        # GUARDAR EN SESIÓN (REEMPLAZAR para evitar duplicidad)
        st.session_state.dg_memoria_historica = dg_temp
        st.success(f"✅ Datos cargados: {len(dg_temp)} filas procesadas.")

    # 3. Visualización (Si hay datos)
    if not st.session_state.dg_memoria_historica.empty:
        df_plot = st.session_state.dg_memoria_historica.copy()
        df_plot['Mes_Nombre'] = df_plot['Periodo'].dt.month_name()

        # Métricas principales (Como en tu segunda captura)
        t_on = df_plot[df_plot['Medio_Final'] == 'ONLINE']['Monto'].sum()
        t_off = df_plot[df_plot['Medio_Final'] == 'OFFLINE']['Monto'].sum()
        t_ooh = df_plot[df_plot['Medio_Final'] == 'OOH']['Monto'].sum()
        t_total = t_on + t_off + t_ooh

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TOTAL GRUPO", f"${t_total:,.0f}")
        c2.metric("ONLINE", f"${t_on:,.0f}")
        c3.metric("OFFLINE", f"${t_off:,.0f}")
        c4.metric("OOH", f"${t_ooh:,.0f}")

        # Gráfica de Barras Apiladas (Como en tu primera captura)
        # Ordenamos los meses para que January vaya antes que February
        bars = alt.Chart(df_plot).mark_bar().encode(
            x=alt.X('Mes_Nombre:N', sort=['January', 'February', 'March'], title="Periodo 2026"),
            y=alt.Y('sum(Monto):Q', title="Inversión Total"),
            color=alt.Color('Medio_Final:N', 
                           scale=alt.Scale(domain=['OFFLINE', 'ONLINE', 'OOH'], 
                                           range=['#4494F6', '#1A237E', '#D87A4D']), # Colores de tu foto
                           title="Medio"),
            tooltip=[alt.Tooltip('Mes_Nombre'), alt.Tooltip('Medio_Final'), alt.Tooltip('sum(Monto)', format='$,.0f')]
        ).properties(height=500)

        # Etiquetas con los montos (ej: $319M)
        text = bars.mark_text(dy=15, color='white', fontWeight='bold').encode(
            text=alt.Text('sum(Monto):Q', format='$.3s')
        )

        # Etiqueta de total sobre la barra (ej: $550M)
        totals = alt.Chart(df_plot).mark_text(dy=-15, fontWeight='bold', size=14).encode(
            x=alt.X('Mes_Nombre:N', sort=['January', 'February']),
            y=alt.Y('sum(Monto):Q'),
            text=alt.Text('sum(Monto):Q', format='$.3s')
        )

        st.altair_chart(bars + text + totals, use_container_width=True)
        
        # Tabla detallada opcional
        with st.expander("Ver tabla de datos"):
            st.dataframe(df_plot.style.format({"Monto": "${:,.0f}"}))

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
