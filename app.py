"""
Inversión Automotriz – App industria
Streamlit app para procesar archivos de inversión y generar análisis.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import calendar
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inversión Automotriz",
    page_icon=None,
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# CONTRASEÑA – GATE
# ─────────────────────────────────────────────────────────────────────────────
def check_password() -> bool:
    """Muestra el gate de contraseña. Devuelve True si ya está autenticado."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        """
        <style>
        .login-box {
            max-width: 380px;
            margin: 80px auto 0 auto;
            padding: 40px 36px 32px;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,.10);
            text-align: center;
        }
        .login-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 6px; }
        .login-sub   { font-size: .9rem; color: #666; margin-bottom: 28px; }
        </style>
        <div class="login-box">
          <div class="login-title">Inversión Automotriz</div>
          <div class="login-sub">Ingresa la contraseña para continuar</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col = st.columns([1, 2, 1])[1]
    with col:
        pwd = st.text_input("Contraseña", type="password", key="_pwd_input", label_visibility="collapsed")
        entered = st.button("Entrar", use_container_width=True)

    if entered or (pwd and pwd != ""):
        # CAMBIO AQUÍ: Ya no usa st.secrets para evitar el error de config
        correct = "automotriz2026" 
        if pwd == correct:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")

    return False

# ─────────────────────────────────────────────────────────────────────────────
# ACTIVAR / DESACTIVAR CONTRASEÑA
# ─────────────────────────────────────────────────────────────────────────────
# He puesto el # para que la app ignore la contraseña y funcione directo:
# if not check_password():
#     st.stop()

# Si algún día quieres volver a pedir contraseña, solo quita los # de arriba.
# ─────────────────────────────────────────────────────────────────────────────

# ... (El resto de tu código de estilos CSS, animaciones y procesamiento de datos sigue aquí abajo igual)
st.success("¡App cargada correctamente!") # Esto te confirmará que ya pasó la barrera
