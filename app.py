#!/usr/bin/env python3
"""
BRAND Investment Data Processor (JAC / KAVAK)
---------------------------------------------
Procesa archivos de Inversión Offline y Online, los consolida 
y los agrega al archivo maestro automotriz.xlsx.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import shutil
import warnings
import calendar
from datetime import datetime

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE RUTAS
# ─────────────────────────────────────────────
# El script detecta la marca por el nombre de la carpeta donde está guardado
FOLDER_PATH       = Path(__file__).parent
BRAND_NAME        = FOLDER_PATH.name.upper() # Ej: "JAC" o "KAVAK"
AUTOMOTRIZ_PATH   = FOLDER_PATH.parent.parent / "Data" / "automotriz.xlsx"
MODIFICADO_FOLDER = FOLDER_PATH / "Modificado"

# Mapeo de nombres para el Excel maestro
BRAND_GROUPS = {
    "JAC": "JAC INDUSTRIA",
    "KAVAK": "KAVAK"
}
CURRENT_GROUP = BRAND_GROUPS.get(BRAND_NAME, BRAND_NAME)

# ─────────────────────────────────────────────
# DICCIONARIOS DE CATEGORIZACIÓN
# ─────────────────────────────────────────────
CAT_MAP = {
    'E 10X': 'SEDAN', 'E J7': 'SEDAN', 'J7': 'SEDAN',
    'E SEI4 PRO': 'SUV', 'SEI 2': 'SUV', 'SEI 3 PRO': 'SUV', 'SEI 4 PRO': 'SUV', 'SEI 6 PRO': 'SUV', 'SEI 7 PRO': 'SUV',
    'FRISON T6': 'PICK UP', 'FRISON T8': 'PICK UP', 'FRISON T9': 'PICK UP', 'E SUNRAY': 'COMERCIAL',
    'AWARENESS': 'INSTITUCIONAL', 'CONSIDERACION': 'INSTITUCIONAL'
}

# ─────────────────────────────────────────────
# FUNCIONES DE PROCESAMIENTO
# ─────────────────────────────────────────────

def get_month_from_name(filename):
    """Extrae mes y año del nombre del archivo (ej: 02.FEBRERO.2026)"""
    meses = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE']
    name_up = filename.upper()
    for i, mes in enumerate(meses):
        if mes in name_up:
            # Busca un año de 4 dígitos
            import re
            year_match = re.search(r'20\d{2}', name_up)
            year = int(year_match.group(0)) if year_match else datetime.now().year
            return f"{calendar.month_name[i+1][:3].lower()}{year}"
    return None

def process_offline(file_path, months_to_proc):
    if not file_path: return pd.DataFrame()
    
    df = pd.read_excel(file_path)
    # Limpieza básica de columnas
    df.columns = [c.strip() for c in df.columns]
    
    # Identificar columna de fecha/mes
    # En Offline suele ser 'yrmth', en otros 'Mes'
    date_col = 'yrmth' if 'yrmth' in df.columns else 'Mes'
    if date_col not in df.columns:
        return pd.DataFrame()

    df = df[df[date_col].isin(months_to_proc)].copy()
    
    # Cálculo de Inversión
    monto_col = 'monto' if 'monto' in df.columns else 'Inversión'
    bonif_col = 'Bonificación Cliente'
    if bonif_col not in df.columns: df[bonif_col] = 0
    
    df['Inversión (MXN)'] = df[monto_col] + df[bonif_col]
    
    # Mapeo al layout maestro
    new_df = pd.DataFrame()
    new_df['Fuente'] = df['medio'].apply(lambda x: 'OOH' if 'EXTERIOR' in str(x).upper() else 'Offline')
    new_df['Año-mes'] = df[date_col]
    new_df['Inversión (MXN)'] = df['Inversión (MXN)']
    new_df['#Grupo'] = CURRENT_GROUP
    new_df['modelo'] = df['Modelos'].str.upper() if 'Modelos' in df.columns else 'INSTITUCIONAL'
    new_df['Categoría'] = new_df['modelo'].map(CAT_MAP).fillna('SUV')
    
    # Columnas espejo por requerimiento de Power BI
    new_df['Inversión F30'] = new_df['Inversión (MXN)']
    new_df['Inversión F30 s/bonif'] = new_df['Inversión (MXN)']
    
    return new_df

def process_online(file_path, month_str):
    if not file_path: return pd.DataFrame()
    
    try:
        df = pd.read_excel(file_path, sheet_name='TOTAL FINAL')
    except:
        df = pd.read_excel(file_path, sheet_name=0) # Fallback a la primera hoja

    # Filtrar basura y vacíos
    df = df.dropna(subset=['Gasto'])
    
    new_df = pd.DataFrame()
    new_df['Fuente'] = 'Online'
    new_df['Año-mes'] = month_str
    new_df['Inversión (MXN)'] = df['Gasto']
    new_df['#Grupo'] = CURRENT_GROUP
    new_df['modelo'] = df['Modelo'].str.upper()
    new_df['Categoría'] = new_df['modelo'].map(CAT_MAP).fillna('SUV')
    new_df['medio'] = df['Plataforma']
    
    new_df['Inversión F30'] = new_df['Inversión (MXN)']
    new_df['Inversión F30 s/bonif'] = new_df['Inversión (MXN)']
    
    return new_df

# ─────────────────────────────────────────────
# LÓGICA PRINCIPAL
# ─────────────────────────────────────────────
def main():
    print(f"🚀 Iniciando proceso para: {CURRENT_GROUP}")
    
    # 1. Identificar archivos en la carpeta
    all_files = list(FOLDER_PATH.glob("*.xlsx"))
    offline_file = next((f for f in all_files if "NAMING" in f.name.upper() or "NC" in f.name.upper()), None)
    online_file = next((f for f in all_files if "ONLINE" in f.name.upper() or any(m in f.name.upper() for m in ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO"])), None)

    # 2. Leer archivo maestro para evitar duplicados
    df_main = pd.read_excel(AUTOMOTRIZ_PATH, sheet_name='Investment Raw data')
    existing_months = df_main[df_main['#Grupo'] == CURRENT_GROUP]['Año-mes'].unique()

    # 3. Determinar meses a procesar
    # Para Offline: leemos el archivo y vemos qué meses NO están en el maestro
    offline_to_proc = []
    if offline_file:
        temp_off = pd.read_excel(offline_file)
        date_col = 'yrmth' if 'yrmth' in temp_off.columns else 'Mes'
        offline_to_proc = [m for m in temp_off[date_col].unique() if m not in existing_months]

    # Para Online: sacamos el mes del nombre del archivo
    online_month = get_month_from_name(online_file.name) if online_file else None
    online_to_proc = [online_month] if online_month and online_month not in existing_months else []

    # 4. Ejecutar procesos
    df_off_new = process_offline(offline_file, offline_to_proc)
    df_on_new = process_online(online_file, online_month if online_to_proc else None)

    df_final = pd.concat([df_off_new, df_on_new], ignore_index=True)

    if not df_final.empty:
        # Guardar resultados
        with pd.ExcelWriter(AUTOMOTRIZ_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            combined = pd.concat([df_main, df_final], ignore_index=True)
            combined.to_excel(writer, sheet_name='Investment Raw data', index=False)
        
        print(f"✅ Se agregaron {len(df_final)} filas nuevas a automotriz.xlsx")
        
        # Mover a Modificado
        MODIFICADO_FOLDER.mkdir(exist_ok=True)
        if offline_file: shutil.move(str(offline_file), MODIFICADO_FOLDER / offline_file.name)
        if online_file: shutil.move(str(online_file), MODIFICADO_FOLDER / online_file.name)
    else:
        print("¡Nada nuevo que procesar! Los meses ya existen en el archivo maestro.")

if __name__ == "__main__":
    main()
