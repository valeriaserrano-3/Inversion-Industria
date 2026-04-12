# Inversión Automotriz – App industria

App local en Streamlit para procesar archivos de inversión publicitaria automotriz (GWM, JAC, KAVAK, BAIC) y generar análisis con tablas y gráficas.

---

## Estructura

```
App industria/
├── app.py                        # App principal
├── requirements.txt              # Dependencias Python
├── .gitignore                    # Excluye archivos sensibles de Git
├── .streamlit/
│   ├── secrets.toml              # ⚠️ NO subir a GitHub (está en .gitignore)
│   └── secrets.toml.example     # Plantilla sin datos reales
└── README.md
```

---

## Instalación local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar contraseña (ver sección Contraseña)

# 3. Correr la app
streamlit run app.py
```

---

## Contraseña de acceso

La app pide contraseña al entrar para proteger los datos.

**Primera vez:**

```bash
# Crea el archivo de contraseña (no se sube a GitHub)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Luego edita `.streamlit/secrets.toml` y pon la contraseña que quieras:

```toml
APP_PASSWORD = "tu_contraseña"
```

**⚠️ Importante:** El archivo `secrets.toml` está en `.gitignore`. Nunca lo subas a GitHub — contiene la contraseña real.

---

## Subir a GitHub (repo público)

Como el repo es público, asegúrate de que:

1. `.gitignore` esté activo (ya incluido — excluye `secrets.toml`, `*.xlsx`, `*.csv`)
2. Solo subas `app.py`, `requirements.txt`, `README.md`, `.gitignore`, y `secrets.toml.example`
3. Nunca hagas `git add .streamlit/secrets.toml` directamente

```bash
git init
git add app.py requirements.txt README.md .gitignore .streamlit/secrets.toml.example
git commit -m "Initial commit"
git remote add origin https://github.com/tu-usuario/tu-repo.git
git push -u origin main
```

---

## Usuarios y rutas

La app detecta automáticamente el usuario por la carpeta home. Si no lo detecta, muestra botones para elegir.

Para agregar o editar usuarios, busca el diccionario `USERS` en `app.py`:

```python
USERS = {
    "Vale": {
        "home": "/Users/vserrano",
        "drive": "GoogleDrive-valeria.serrano@3zero.mx",
    },
    "Ale": {
        "home": "/Users/ale",            # ← cambiar
        "drive": "GoogleDrive-ale@3zero.mx",  # ← cambiar
    },
    ...
}
```

---

## Datos históricos 2025

Los datos de 2025 están hardcodeados en `HIST_2025` (en `app.py`). Úsalos solo como respaldo cuando automotriz.xlsx no tenga ese mes. Para editarlos busca:

```python
HIST_2025 = {
     1: (138_000_000, 245_000_000,  91_000_000),  # jan-25: Online, Offline, OOH
     ...
}
```

---

## Multiplicadores

Los multiplicadores se pueden ajustar en la barra lateral de la app (sección "Multiplicadores") o directamente en el código (`DEFAULT_MULT`):

| Fuente          | M1   | M2   |
|-----------------|------|------|
| Radio           | 0.70 | 1.30 |
| TV Abierta      | 0.40 | 1.30 |
| TV Paga / Local | 0.60 | 1.30 |
| Online          | 1.00 | 1.30 |
| OOH MXN         | × 2  |      |
| OOH F30         | × 1.30 |    |

---

## Flujo de uso

1. Abre la app con `streamlit run app.py`
2. Ingresa la contraseña
3. Selecciona usuario (o se detecta automático)
4. Elige mes y año
5. Sube los archivos en las pestañas GWM / JAC / KAVAK·BAIC·Industria
6. Haz clic en **▶ Procesar archivos**
7. Revisa el resumen, métricas y gráficas
8. Descarga XLSX o CSV para Power BI

---

## Dependencias

- Python 3.10+
- streamlit, pandas, numpy, openpyxl, plotly, xlrd
