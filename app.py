import streamlit as st
import pandas as pd
import requests
import re
import os
import zipfile
import io
import unicodedata
from pathlib import Path
from datetime import datetime

# ─── CONSTANTES ───────────────────────────────────────────────────────────────

BRANDS_LIST = sorted([
    "BYD", "CHANGAN", "CHEVROLET", "CHIREY", "FORD", "FOTON",
    "GAC", "GEELY", "GWM", "HONDA", "HYUNDAI", "JAC", "JAC INDUSTRIA",
    "JETOUR", "KIA", "MAZDA", "MG", "MITSUBISHI", "NISSAN",
    "OMODA", "PEUGEOT", "RAM", "RENAULT", "SEAT", "SUZUKI",
    "TOYOTA", "VOLKSWAGEN", "VOLVO",
])

MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

BRAND_ALIASES = {
    "VW": "VOLKSWAGEN",
    "VOLKSWAGEN": "VOLKSWAGEN",
    "GWM MOTORS": "GWM",
    "GWM MEXICO": "GWM",
    "GWM": "GWM",
    "MG MOTOR": "MG",
    "JAC INDUSTRIA": "JAC INDUSTRIA",
    "JAC": "JAC",
}

OFFER_PATTERNS = [
    r"tasa", r"inter[eé]s", r"\bcat\b", r"anualidad",
    r"desde\s*\$", r"\$\s*[\d,]+", r"[\d,]+\s*%",
    r"\d+\s*meses?", r"mensualidad", r"mensuale?s?",
    r"enganche", r"financiam\w*", r"descuento",
    r"oferta", r"promoci[oó]n", r"\bmsi\b",
    r"sin intereses", r"pago\s+mensual", r"bonificaci\w*",
    r"plan de pago", r"cuota", r"cashback",
    r"ahorra", r"regalo", r"bono",
]

MEDIO_MAP = {
    # Auditsa
    "revista":              "revista",
    "periódico":            "periodico",
    "periodico":            "periodico",
    "radio":                "radio",
    "televisión":           "tv",
    "television":           "tv",
    "tv":                   "tv",
    # Admetricks
    "online":               "online",
    "display":              "online",
    "text":                 "online",
    "video":                "online",
    "facebook":             "online",
    "instagram":            "online",
    "youtube":              "online",
    "search":               "online",
    "banner":               "online",
    # OOH (todos los TipoPublicidad → ooh)
    "muro":                 "ooh",
    "tunel":                "ooh",
    "cartelera":            "ooh",
    "cartelera doble":      "ooh",
    "cartelera digital":    "ooh",
    "mega valla":           "ooh",
    "valla":                "ooh",
    "valla digital":        "ooh",
    "puente":               "ooh",
    "cabina inteligente":   "ooh",
    "kiosco":               "ooh",
    "kiosco digital":       "ooh",
    "reloj":                "ooh",
    "columna":              "ooh",
    "mupi":                 "ooh",
    "parabuses":            "ooh",
    "parabus digital":      "ooh",
}

MAX_PER_MEDIO = 3

# ─── CSS BLOQUES ──────────────────────────────────────────────────────────────

_CSS_BASE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Poppins:wght@400;500;600;700&display=swap');

/* ── Fuentes — NO tocar span/div para no romper Material Icons ── */
h1, h2, h3, h4, h5 { font-family: 'Poppins', sans-serif !important; }
p, label, li, td, th, input, select, textarea,
.stMarkdown p, .stText, .stCaption {
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Proteger iconos Material (fixes keyboard_double y uploadupload) ── */
[data-testid="collapsedControl"] span,
[data-testid="stFileUploaderDropzone"] button span:first-child,
[class*="material"], .material-icons, .material-symbols-rounded {
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
}

/* ── Sidebar collapse arrow — siempre visible ── */
[data-testid="collapsedControl"] {
    display: flex !important; visibility: visible !important; opacity: 1 !important;
}

/* ── Pills nativos de Streamlit (st.pills) — estilos compactos ── */
[data-testid="stPills"] {
    gap: 4px !important;
}
[data-testid="stPills"] button {
    font-size: 10px !important;
    padding: 2px 8px !important;
    min-height: 0 !important;
    line-height: 1.4 !important;
    border-radius: 3px !important;
}

/* ── Animaciones coche ── */
@keyframes drive_car { from { left: -70px; } to { left: 100%; } }
@keyframes road_move { from { background-position: 0 0; } to { background-position: 56px 0; } }
@keyframes blink_txt { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

.car-road {
    position: relative; width: 100%; height: 60px;
    border-radius: 5px; border: 1px solid; overflow: hidden; margin: 10px 0 4px 0;
}
.car-road-surface { position: absolute; bottom: 0; left: 0; right: 0; height: 20px; border-top: 1px solid; }
.car-road-dashes-anim {
    position: absolute; bottom: 9px; left: 0; right: 0; height: 2px;
    animation: road_move 0.5s linear infinite;
}
.car-road-dashes-static { position: absolute; bottom: 9px; left: 0; right: 0; height: 2px; }
.car-driving {
    position: absolute; bottom: 14px; left: -70px;
    font-size: 30px; line-height: 1; animation: drive_car 2.8s linear infinite;
}
.car-parked { position: absolute; bottom: 14px; right: 24px; font-size: 30px; line-height: 1; }
.car-status {
    font-family: 'IBM Plex Sans', sans-serif; font-size: 0.72em;
    font-weight: 500; letter-spacing: 0.12em; margin-bottom: 6px;
}
.car-status-blink { animation: blink_txt 1.4s ease-in-out infinite; }
</style>
"""

_CSS_LIGHT = """
<style>
.stApp { background: #ffffff !important; }
section[data-testid="stSidebar"] { background: #f7f7f7 !important; border-right: 1px solid #e2e2e2 !important; }

h1 { color: #111111 !important; font-size: 1.4em !important; font-weight: 700; border-bottom: 2px solid #111; padding-bottom: 8px; }
h2 { color: #666666 !important; font-size: 0.78em !important; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; }
h3 { color: #222222 !important; font-size: 0.9em !important; font-weight: 600; }
.stCaption { color: #aaaaaa !important; font-size: 0.78em !important; }

.stButton > button[kind="primary"] {
    background: #111111 !important; color: #ffffff !important; border: none !important;
    border-radius: 4px !important; font-family: 'Poppins', sans-serif !important;
    font-size: 0.82em !important; font-weight: 600; letter-spacing: 0.05em; padding: 10px 20px !important;
}
.stButton > button[kind="primary"]:hover { background: #333 !important; }
div.stButton > button:not([kind="primary"]) {
    background: transparent !important; color: #111 !important;
    border: 1.5px solid #ccc !important; border-radius: 4px !important; font-size: 0.8em !important;
}
div.stButton > button:not([kind="primary"]):hover { border-color: #111 !important; }

.stDownloadButton > button {
    background: #f3f3f3 !important; color: #111 !important;
    border: 1.5px solid #111 !important; border-radius: 4px !important; font-size: 0.8em !important;
}

.stTextInput > div > div > input {
    background: #fff !important; color: #111 !important; border: 1.5px solid #ddd !important;
    border-radius: 4px !important; font-family: 'IBM Plex Sans', sans-serif !important; font-size: 13px !important;
}
.stTextInput > div > div > input:focus { border-color: #111 !important; box-shadow: 0 0 0 1px #11111120 !important; }

.stSelectbox > div > div { background: #fff !important; border: 1.5px solid #ddd !important; border-radius: 4px !important; }
.stMultiSelect > div > div { background: #fff !important; border: 1.5px solid #ddd !important; border-radius: 4px !important; }
.stMultiSelect span[data-baseweb="tag"] { background: #f0f0f0 !important; color: #111 !important; border: 1px solid #ccc !important; border-radius: 4px !important; }

[data-testid="stFileUploaderDropzone"] { background: #fafafa !important; border: 1.5px dashed #ccc !important; border-radius: 6px !important; }
.stProgress > div > div > div > div { background: #111111 !important; }
hr { border-color: #e2e2e2 !important; margin: 12px 0 !important; }

.stTabs [data-baseweb="tab-list"] { border-bottom: 1.5px solid #e2e2e2 !important; background: transparent !important; gap: 0; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #bbb !important; font-family: 'Poppins', sans-serif !important; font-size: 0.76em !important; font-weight: 500; letter-spacing: 0.07em; text-transform: uppercase; padding: 8px 20px !important; border: none !important; border-bottom: 2px solid transparent !important; }
.stTabs [aria-selected="true"] { color: #111 !important; border-bottom: 2px solid #111 !important; }

[data-testid="metric-container"] { background: #f8f8f8 !important; border: 1px solid #e2e2e2 !important; border-radius: 6px !important; padding: 16px !important; }
[data-testid="metric-container"] label { color: #aaa !important; font-size: 0.68em !important; letter-spacing: 0.1em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: #111 !important; font-size: 2em !important; font-weight: 700; }

.stDataFrame { border: 1px solid #e2e2e2 !important; border-radius: 4px !important; }
.stCheckbox label { color: #555 !important; font-size: 0.84em !important; }
.stAlert { border-radius: 4px !important; font-size: 0.82em !important; }

[data-testid="stBaseButton-pills"] {
    background: #f5f5f5 !important;
    color: #555555 !important;
    border: 1.5px solid #cccccc !important;
}
[data-testid="stBaseButton-pillsActive"] {
    background: #722F37 !important;
    color: #ffffff !important;
    border-color: #722F37 !important;
}

.brand-toggle-on  { display:inline-block; background:#111; color:#fff; border:1px solid #111; border-radius:4px; padding:3px 10px; font-size:11px; font-family:'IBM Plex Sans',sans-serif; font-weight:600; margin:2px; cursor:pointer; letter-spacing:.03em; }
.brand-toggle-off { display:inline-block; background:#f4f4f4; color:#888; border:1px solid #ddd; border-radius:4px; padding:3px 10px; font-size:11px; font-family:'IBM Plex Sans',sans-serif; font-weight:400; margin:2px; cursor:pointer; letter-spacing:.03em; }

.car-road { background: #f2f2f2 !important; border-color: #ddd !important; }
.car-road-surface { background: #e4e4e4 !important; border-top-color: #ccc !important; }
.car-road-dashes-anim, .car-road-dashes-static { background: repeating-linear-gradient(90deg, #99999966 0, #99999966 28px, transparent 28px, transparent 56px) !important; }
.car-status { color: #111 !important; }
</style>
"""

_CSS_DARK = """
<style>
.stApp { background: #06080f !important; }
section[data-testid="stSidebar"] { background: #08090f !important; border-right: 1px solid #151d2b !important; }

p, label, li, td, th, small,
.stMarkdown p, .stText, .stCaption,
[data-testid="stWidgetLabel"] p,
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small {
    color: #ffffff !important;
}

h1 { color: #00d4aa !important; font-size: 1.4em !important; font-weight: 700; border-bottom: 1px solid #151d2b; padding-bottom: 8px; letter-spacing: 0.04em; }
h2 { color: #ffffff !important; font-size: 0.78em !important; font-weight: 400; letter-spacing: 0.1em; text-transform: uppercase; }
h3 { color: #ffffff !important; font-size: 0.9em !important; font-weight: 500; }
.stCaption { color: #ffffff !important; font-size: 0.78em !important; }

.stButton > button[kind="primary"] {
    background: #00d4aa !important; color: #06080f !important; border: none !important;
    border-radius: 4px !important; font-family: 'Poppins', sans-serif !important;
    font-size: 0.82em !important; font-weight: 700; letter-spacing: 0.05em; padding: 10px 20px !important;
}
.stButton > button[kind="primary"]:hover { background: #00b894 !important; }
div.stButton > button:not([kind="primary"]) {
    background: transparent !important; color: #00d4aa !important;
    border: 1px solid #1e3a2e !important; border-radius: 4px !important; font-size: 0.8em !important;
}
div.stButton > button:not([kind="primary"]):hover { border-color: #00d4aa !important; }

.stDownloadButton > button {
    background: #0a1f18 !important; color: #00d4aa !important;
    border: 1px solid #00d4aa !important; border-radius: 4px !important; font-size: 0.8em !important;
}

.stTextInput > div > div > input {
    background: #0a0d16 !important; color: #ffffff !important; border: 1px solid #151d2b !important;
    border-radius: 4px !important; font-family: 'IBM Plex Sans', sans-serif !important; font-size: 13px !important;
}
.stTextInput > div > div > input:focus { border-color: #00d4aa !important; box-shadow: 0 0 0 1px #00d4aa1a !important; }

.stSelectbox > div > div { background: #0a0d16 !important; border: 1px solid #151d2b !important; border-radius: 4px !important; color: #ffffff !important; }
.stMultiSelect > div > div { background: #0a0d16 !important; border: 1px solid #151d2b !important; border-radius: 4px !important; }
.stMultiSelect span[data-baseweb="tag"] { background: #0a1f18 !important; color: #00d4aa !important; border: 1px solid #00d4aa33 !important; border-radius: 4px !important; }

[data-testid="stFileUploaderDropzone"] { background: #0a0d16 !important; border: 1px dashed #1e2a3a !important; border-radius: 6px !important; }
.stProgress > div > div > div > div { background: #00d4aa !important; }
hr { border-color: #151d2b !important; margin: 12px 0 !important; }

.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #151d2b !important; background: transparent !important; gap: 0; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #ffffff !important; font-family: 'Poppins', sans-serif !important; font-size: 0.76em !important; font-weight: 500; letter-spacing: 0.07em; text-transform: uppercase; padding: 8px 20px !important; border: none !important; border-bottom: 2px solid transparent !important; opacity: 0.45; }
.stTabs [aria-selected="true"] { color: #00d4aa !important; border-bottom: 2px solid #00d4aa !important; opacity: 1; }

[data-testid="metric-container"] { background: #0a0d16 !important; border: 1px solid #151d2b !important; border-radius: 6px !important; padding: 16px !important; }
[data-testid="metric-container"] label { color: #ffffff !important; font-size: 0.68em !important; letter-spacing: 0.1em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: #00d4aa !important; font-size: 2em !important; font-weight: 700; }

.stDataFrame { border: 1px solid #151d2b !important; border-radius: 4px !important; }
.stCheckbox label { color: #ffffff !important; font-size: 0.84em !important; }
.stAlert { border-radius: 4px !important; font-size: 0.82em !important; }

[data-testid="stBaseButton-pills"] {
    background: #0a1218 !important;
    color: #ffffff !important;
    border: 1px solid #1e2e3a !important;
}
[data-testid="stBaseButton-pillsActive"] {
    background: #00d4aa !important;
    color: #06080f !important;
    border-color: #00d4aa !important;
}

.brand-toggle-on  { display:inline-block; background:#00d4aa; color:#06080f; border:1px solid #00d4aa; border-radius:4px; padding:3px 10px; font-size:11px; font-family:'IBM Plex Sans',sans-serif; font-weight:700; margin:2px; cursor:pointer; letter-spacing:.03em; }
.brand-toggle-off { display:inline-block; background:#0a1f18; color:#3a6a5a; border:1px solid #1e3a2e; border-radius:4px; padding:3px 10px; font-size:11px; font-family:'IBM Plex Sans',sans-serif; font-weight:400; margin:2px; cursor:pointer; letter-spacing:.03em; }

[data-testid="stHeader"],
[data-testid="stToolbar"],
header[data-testid="stHeader"] {
    background: #06080f !important;
    border-bottom: 1px solid #151d2b !important;
}
[data-testid="stToolbar"] button,
[data-testid="stToolbar"] a,
[data-testid="stHeader"] button {
    color: #ffffff !important;
}

.car-road { background: #080c18 !important; border-color: #1a2535 !important; }
.car-road-surface { background: #0d1520 !important; border-top-color: #1a2535 !important; }
.car-road-dashes-anim, .car-road-dashes-static { background: repeating-linear-gradient(90deg, #00d4aa55 0, #00d4aa55 28px, transparent 28px, transparent 56px) !important; }
.car-status { color: #00d4aa !important; }
</style>
"""

_CSS_AUTO = """
<style>
@media (prefers-color-scheme: light) {
""" + _CSS_LIGHT.replace("<style>","").replace("</style>","") + """
}
@media (prefers-color-scheme: dark) {
""" + _CSS_DARK.replace("<style>","").replace("</style>","") + """
}
</style>
"""

# ─── CAR ANIMATION ────────────────────────────────────────────────────────────

DRIVING_CAR_HTML = """
<div class="car-road">
    <div class="car-road-surface"></div>
    <div class="car-road-dashes-anim"></div>
    <div class="car-driving">🚗</div>
</div>
<div class="car-status car-status-blink">DESCARGANDO TESTIGOS...</div>
"""

PARKED_CAR_HTML = """
<div class="car-road">
    <div class="car-road-surface"></div>
    <div class="car-road-dashes-static"></div>
    <div class="car-parked">🚗</div>
</div>
<div class="car-status">PROCESO COMPLETADO</div>
"""


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def find_base_path() -> str:
    cloud = Path.home() / "Library" / "CloudStorage"
    if cloud.exists():
        for gd in sorted(cloud.glob("GoogleDrive-*")):
            candidate = (
                gd / "Unidades compartidas"
                / "Business Intelligence"
                / "Automotriz"
                / "Testigos Competencia"
            )
            if candidate.exists():
                return str(candidate)
    return str(Path.home() / "Desktop")


def detect_source(df: pd.DataFrame) -> str:
    cols = set(df.columns)
    if "Testigo" in cols:
        return "auditsa"
    if "Advertisement" in cols:
        return "admetricks"
    if "Url" in cols and "TipoPublicidad" in cols:
        return "ooh"
    return "unknown"


def normalize_brand(raw: str) -> str:
    b = str(raw).strip().upper()
    return BRAND_ALIASES.get(b, b)


def normalize_medio(raw: str) -> str:
    return MEDIO_MAP.get(str(raw).strip().lower(), "online")


def brand_in_selection(raw: str, selected: list[str]) -> bool:
    return normalize_brand(raw) in [normalize_brand(s) for s in selected]


def has_offer(text) -> bool:
    if not text or (isinstance(text, float) and pd.isna(text)):
        return False
    t = str(text).lower()
    return any(re.search(p, t) for p in OFFER_PATTERNS)


def get_extension(content_type: str, url: str) -> str:
    ct = content_type.lower()
    for token, ext in [
        ("jpeg", ".jpg"), ("jpg", ".jpg"), ("png", ".png"),
        ("gif", ".gif"), ("pdf", ".pdf"), ("mp4", ".mp4"), ("webp", ".webp"),
    ]:
        if token in ct:
            return ext
    _, ext = os.path.splitext(url.split("?")[0])
    return ext if ext else ".jpg"


def sanitize(s: str, max_len: int = 50) -> str:
    return re.sub(r"[^\w\-]", "_", str(s).strip())[:max_len]


def slug(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "_", s).strip("_")


def get_save_folder(base: str, marca: str, month_folder: str) -> Path:
    folder = Path(base) / slug(month_folder) / slug(normalize_brand(marca))
    target_name = folder.name
    parent = folder.parent
    parent.mkdir(parents=True, exist_ok=True)
    # macOS es case-insensitive: siempre revisar si hay variante en mayúsculas y renombrarla
    for existing in parent.iterdir():
        if existing.is_dir() and existing.name.lower() == target_name and existing.name != target_name:
            existing.rename(folder)
            break
    folder.mkdir(exist_ok=True)
    return folder


def list_month_folders(base_path: str) -> list[str]:
    p = Path(base_path)
    if not p.exists():
        return []
    skip = {".streamlit", ".DS_Store", ".git", ".claude"}
    return sorted(
        [d.name for d in p.iterdir() if d.is_dir() and d.name not in skip],
        reverse=True,
    )


def extract_year(folder_name: str) -> str:
    for part in folder_name.split():
        if part.isdigit() and len(part) == 4:
            return part
    return "Sin año"


def download_file(url: str, folder: Path, filename_base: str):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        r = requests.get(url, headers=headers, timeout=30, stream=True)
        r.raise_for_status()
        ext = get_extension(r.headers.get("content-type", ""), url)
        fname = f"{filename_base}{ext}"
        fpath = folder / fname
        with open(fpath, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        return True, fname, None
    except Exception as e:
        return False, None, str(e)


# ─── PROCESAMIENTO ────────────────────────────────────────────────────────────

def process_file(df, source, selected_brands, base_path, month_folder, prog_bar, status_txt):
    results = []
    brand_counters: dict = {}

    if source == "auditsa":
        url_col, desc_col, fuente_col, medio_col = (
            "Testigo", "Texto de nota", "Fuente", "Medio"
        )
    elif source == "ooh":
        url_col, desc_col, fuente_col, medio_col = (
            "Url", "ProductoTag", "Ciudad", "TipoPublicidad"
        )
    else:
        url_col, desc_col, fuente_col, medio_col = (
            "Advertisement", "Nombre de campaña", "Sitio web", "Formato"
        )

    df = df[df["Marca"].notna()].copy()
    df = df[~df["Marca"].astype(str).str.strip().isin(["Total", "No se han aplicado filtros", "nan"])].copy()
    df = df[df["Marca"].apply(lambda x: brand_in_selection(x, selected_brands))].copy()
    df = df.drop_duplicates(subset=[url_col])

    df["_marca_norm"] = df["Marca"].apply(normalize_brand)
    df["_medio_norm"] = df[medio_col].apply(normalize_medio) if medio_col in df.columns else "online"

    if source == "ooh":
        df = (
            df.groupby(["_marca_norm", "_medio_norm"], group_keys=False)
            .apply(lambda g: g.sample(min(MAX_PER_MEDIO, len(g)), random_state=None))
            .reset_index(drop=True)
        )
    else:
        df = (
            df.groupby(["_marca_norm", "_medio_norm"], group_keys=False)
            .apply(lambda g: g.head(MAX_PER_MEDIO))
            .reset_index(drop=True)
        )

    total = len(df)
    if total == 0:
        return results

    for i, (_, row) in enumerate(df.iterrows()):
        marca  = normalize_brand(row.get("Marca", ""))
        fuente = sanitize(row.get(fuente_col, "desconocido"))
        medio  = normalize_medio(row.get(medio_col, "")) if medio_col in df.columns else "online"
        fecha  = row.get("Fecha", datetime.now())
        url    = str(row.get(url_col, "")).strip()

        desc = str(row.get(desc_col, ""))
        if source == "admetricks":
            tags = str(row.get("Etiquetas de campaña", ""))
            desc = f"{desc} {tags}"

        prog_bar.progress((i + 1) / total)
        status_txt.text(f"{i+1}/{total}   {marca}   ({medio})")

        if not url or url in ("nan", ""):
            results.append({
                "Marca": marca, "Medio": medio, "Fuente": fuente,
                "Fecha": str(fecha)[:10], "Exito": False,
                "Archivo": "", "Error": "URL vacia",
                "Oferta Comercial": has_offer(desc), "Texto": desc[:300],
            })
            continue

        fecha_str  = fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha)[:10]
        folder     = get_save_folder(base_path, marca, month_folder)
        brand_counters[marca] = brand_counters.get(marca, 0) + 1
        fname_base = f"{slug(marca)}_{slug(medio)}_{brand_counters[marca]}"

        ok, fname, err = download_file(url, folder, fname_base)

        oferta = False if source == "ooh" else has_offer(desc)
        results.append({
            "Marca":            marca,
            "Medio":            medio,
            "Fuente":           fuente,
            "Fecha":            fecha_str,
            "Exito":            ok,
            "Archivo":          fname or "",
            "Error":            err or "",
            "Oferta Comercial": oferta,
            "Texto":            desc[:300] if oferta else "",
        })

    return results


# ─── ZIP ──────────────────────────────────────────────────────────────────────

def build_zip(base_path: str, month_folder: str) -> bytes | None:
    target = Path(base_path) / month_folder
    if not target.exists():
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(target.rglob("*")):
            if file.is_file():
                zf.write(file, Path(month_folder) / file.relative_to(target))
    buf.seek(0)
    return buf.read()


# ─── UI ───────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Testigos Competencia", page_icon=None, layout="wide")

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "◑"
if "brand_pills_widget" not in st.session_state:
    st.session_state["brand_pills_widget"] = BRANDS_LIST

theme_icon = st.session_state.theme_mode
if theme_icon == "☀️":
    st.markdown(_CSS_BASE + _CSS_LIGHT, unsafe_allow_html=True)
elif theme_icon == "🌙":
    st.markdown(_CSS_BASE + _CSS_DARK, unsafe_allow_html=True)
else:
    st.markdown(_CSS_BASE + _CSS_AUTO, unsafe_allow_html=True)

st.title("Testigos — Competencia Automotriz")
st.caption(
    "Auditsa (revista · radio · tv · periodico)  +  Admetricks (online)  +  OOH (exterior)"
    "  ·  Max. 3 testigos por medio por marca"
)

with st.sidebar:
    tema = st.segmented_control(
        "Tema",
        options=["☀️", "◑", "🌙"],
        default=st.session_state.theme_mode,
        key="tema_seg",
    )
    if tema and tema != st.session_state.theme_mode:
        st.session_state.theme_mode = tema
        st.rerun()

    st.divider()
    st.header("Configuracion")

    default_path = find_base_path()
    base_path = st.text_input(
        "Carpeta raiz:",
        value=default_path,
        help="Ruta local de la carpeta Testigos Competencia",
    )

    st.divider()
    st.subheader("Marcas competencia")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Todas", use_container_width=True):
            st.session_state["brand_pills_widget"] = BRANDS_LIST
            st.rerun()
    with c2:
        if st.button("Ninguna", use_container_width=True):
            st.session_state["brand_pills_widget"] = []
            st.rerun()

    brand_selection = st.pills(
        "Marcas",
        BRANDS_LIST,
        selection_mode="multi",
        key="brand_pills_widget",
        label_visibility="collapsed",
    )
    selected_brands = brand_selection or []
    if not selected_brands:
        st.warning("No hay marcas seleccionadas.")

    st.divider()
    st.subheader("Descargar ZIP del mes")

    avail_months = list_month_folders(base_path) if base_path else []

    if avail_months:
        year_map: dict[str, list[str]] = {}
        for m in avail_months:
            y = extract_year(m)
            year_map.setdefault(y, []).append(m)

        chosen_year  = st.selectbox("Año:", sorted(year_map.keys(), reverse=True))
        chosen_month = st.text_input(
            "Mes:",
            value=sorted(year_map.get(chosen_year, [f"Enero {chosen_year}"]), reverse=True)[0],
            placeholder="ej. Marzo 2026",
        )

        if st.button("Generar ZIP", use_container_width=True):
            with st.spinner("Comprimiendo..."):
                zip_bytes = build_zip(base_path, chosen_month)
            if zip_bytes:
                st.download_button(
                    label=f"Descargar {chosen_month}.zip",
                    data=zip_bytes,
                    file_name=f"{chosen_month}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.error("Carpeta vacia o no encontrada.")
    else:
        st.info("Configura la carpeta raiz para ver los meses.")

st.subheader("Archivos a procesar")

uploaded_files = st.file_uploader(
    "Sube uno o mas archivos Excel (.xlsx / .xlsm) de Auditsa, Admetricks u OOH:",
    type=["xlsx", "xlsm"],
    accept_multiple_files=True,
    label_visibility="visible",
)

if uploaded_files:
    default_folder = f"{MONTHS_ES[datetime.now().month]} {datetime.now().year}"
    month_folder = st.text_input(
        "Nombre de la carpeta del mes:",
        value=default_folder,
        placeholder="ej. Marzo 2026",
        help="Los testigos se guardaran en: Testigos Competencia / [nombre] / marca / testigo",
    )
    st.caption(f"Ruta: .../{month_folder.strip() or '?'}/marca/testigo.jpg")

    if st.button("Procesar archivos", type="primary", use_container_width=True):
        if not selected_brands:
            st.error("Selecciona al menos una marca en el panel izquierdo.")
        elif not base_path or not Path(base_path).exists():
            st.error(f"La carpeta raiz no existe: {base_path}")
        elif not month_folder.strip():
            st.error("Escribe el nombre de la carpeta del mes.")
        else:
            all_results = []
            car_slot = st.empty()
            car_slot.markdown(DRIVING_CAR_HTML, unsafe_allow_html=True)

            for uf in uploaded_files:
                st.markdown(f"---\n**{uf.name}**")
                try:
                    df = pd.read_excel(uf)
                    source = detect_source(df)

                    if source == "unknown":
                        st.warning(f"Formato no reconocido en {uf.name} — se omite.")
                        continue

                    label = {
                        "auditsa":    "Auditsa  (impreso / radio / tele)",
                        "admetricks": "Admetricks  (online)",
                        "ooh":        "OOH  (exterior · muestreo aleatorio)",
                    }.get(source, source)
                    st.info(f"Fuente: **{label}** — {len(df):,} registros")

                    prog   = st.progress(0)
                    status = st.empty()

                    results = process_file(
                        df, source, selected_brands, base_path,
                        month_folder.strip(), prog, status,
                    )
                    all_results.extend(results)

                    ok_n = sum(1 for r in results if r["Exito"])
                    prog.progress(1.0)
                    status.success(f"{ok_n} / {len(results)} testigos descargados")

                except Exception as e:
                    st.error(f"Error leyendo {uf.name}: {e}")

            car_slot.markdown(PARKED_CAR_HTML, unsafe_allow_html=True)

            if all_results:
                st.divider()
                st.header("Resultados")

                df_res = pd.DataFrame(all_results)

                col1, col2, col3 = st.columns(3)
                col1.metric("Total procesados",    len(df_res))
                col2.metric("Descargados OK",       int(df_res["Exito"].sum()))
                col3.metric("Con oferta comercial", int(df_res["Oferta Comercial"].sum()))

                tab1, tab2, tab3 = st.tabs(["Descargados", "Ofertas Comerciales", "Errores"])

                with tab1:
                    ok_df = df_res[df_res["Exito"]][
                        ["Marca", "Medio", "Fuente", "Fecha", "Archivo"]
                    ].reset_index(drop=True)
                    st.dataframe(ok_df, use_container_width=True)

                with tab2:
                    offer_df = df_res[df_res["Oferta Comercial"]][
                        ["Marca", "Medio", "Fuente", "Fecha", "Texto"]
                    ].reset_index(drop=True)
                    if len(offer_df):
                        st.dataframe(offer_df, use_container_width=True)
                    else:
                        st.info("No se detectaron ofertas comerciales.")

                with tab3:
                    err_df = df_res[~df_res["Exito"]][
                        ["Marca", "Medio", "Fuente", "Fecha", "Error"]
                    ].reset_index(drop=True)
                    if len(err_df):
                        st.dataframe(err_df, use_container_width=True)
                    else:
                        st.success("Sin errores en este lote.")
