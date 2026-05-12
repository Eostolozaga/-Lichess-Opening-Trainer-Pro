"""
Lichess Opening Trainer Pro
Estética: tablero de ajedrez clásico — crema e ivory, fondo cuadriculado
"""
import io, os, re, time, datetime, pickle, random
import chess, chess.pgn, chess.svg, joblib, requests
import numpy as np, pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from stockfish import Stockfish

st.set_page_config(
    page_title="Lichess Opening Trainer Pro",
    page_icon="♟",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap');

/* ── Base ── */
.stApp {
    background-color: #080b12;
    background-image:
        repeating-conic-gradient(#0d1220 0% 25%, #0a0e1a 0% 50%);
    background-size: 56px 56px;
}
.block-container { padding: 0 1.5rem 2rem !important; max-width: 1400px !important; }
*, *::before, *::after { font-family: 'Inter', system-ui, sans-serif !important; }
h1,h2,h3 { font-family: 'Rajdhani', 'Inter', sans-serif !important; }

/* ── Header ── */
.header-bar {
    background: linear-gradient(135deg, #0a0e1a 0%, #0f1628 60%, #0a0e1a 100%);
    padding: 1.5rem 2rem; display: flex; align-items: center; gap: 1.4rem;
    border-bottom: 1px solid #1e3a6e;
    position: relative; overflow: hidden;
}
.header-bar::after {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #3b82f6 30%, #60a5fa 50%, #3b82f6 70%, transparent);
}
.header-bar h1 {
    color: #e2e8f0 !important; font-size: 2rem !important; font-weight: 700 !important;
    margin: 0 !important; letter-spacing: 0.06em !important; text-transform: uppercase;
}
.header-sub { color: #4b6cb7; font-size: 0.8rem; margin-top: 0.3rem; letter-spacing: 0.1em; text-transform: uppercase; }
.hbadge {
    background: rgba(59,130,246,0.12); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3);
    font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.14em;
    padding: 2px 8px; border-radius: 3px; margin-right: 0.4rem; display: inline-block; margin-top: 0.5rem;
}

/* ── Config panel ── */
.config-wrap {
    background: rgba(10,14,26,0.95);
    border-bottom: 1px solid #1e3a6e;
    padding: 1rem 1.8rem 1.2rem;
    backdrop-filter: blur(4px);
}
.config-wrap label, .config-wrap p, .config-wrap div { color: #cbd5e1 !important; }

/* ══════════════════════════════════════
   BOTONES — sistema de clases wrapper
   ══════════════════════════════════════ */
/* Reset base — visible siempre */
.stButton > button {
    font-family: 'Rajdhani', 'Inter', sans-serif !important;
    font-size: 0.92rem !important; font-weight: 600 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
    border-radius: 4px !important; cursor: pointer !important;
    transition: all 0.18s ease !important;
    min-height: 2.2rem !important; line-height: 1.3 !important;
}
/* Botón ANALIZAR — azul eléctrico */
.btn-primary .stButton > button {
    background: #2563eb !important;
    color: #ffffff !important;
    border: 1px solid #3b82f6 !important;
    padding: 0.4rem 1.4rem !important;
    box-shadow: 0 0 12px rgba(59,130,246,0.35) !important;
}
.btn-primary .stButton > button:hover {
    background: #3b82f6 !important;
    border-color: #60a5fa !important;
    box-shadow: 0 0 20px rgba(59,130,246,0.5) !important;
}
.btn-primary .stButton > button:disabled {
    background: #1e3a6e !important;
    color: #4b6cb7 !important;
    border-color: #1e3a6e !important;
    box-shadow: none !important;
}
/* Botón TOGGLE — gris con borde azul */
.btn-toggle .stButton > button {
    background: #0f1628 !important;
    color: #94a3b8 !important;
    border: 1px solid #1e3a6e !important;
    padding: 0.28rem 0.9rem !important;
    font-size: 0.75rem !important;
    box-shadow: none !important;
}
.btn-toggle .stButton > button:hover {
    background: #1a2540 !important;
    color: #e2e8f0 !important;
    border-color: #3b82f6 !important;
}
/* Botón SUBIR BLUNDERS — ámbar */
.btn-upload .stButton > button {
    background: #92400e !important;
    color: #fef3c7 !important;
    border: 1px solid #d97706 !important;
    padding: 0.4rem 1.2rem !important;
    box-shadow: 0 0 8px rgba(217,119,6,0.3) !important;
}
.btn-upload .stButton > button:hover {
    background: #b45309 !important;
    border-color: #f59e0b !important;
    box-shadow: 0 0 14px rgba(217,119,6,0.45) !important;
}

/* ── Inputs ── */
.stTextInput input, .stNumberInput input {
    background: #0f1628 !important; border: 1px solid #1e3a6e !important;
    border-radius: 4px !important; color: #e2e8f0 !important; font-size: 0.85rem !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #3b82f6 !important; box-shadow: 0 0 0 2px rgba(59,130,246,0.25) !important;
}
label { color: #94a3b8 !important; font-size: 0.78rem !important; }
.stTextInput label, .stNumberInput label {
    color: #94a3b8 !important; font-size: 0.76rem !important;
}

/* ── Checkbox ── */
.stCheckbox { background: rgba(15,22,40,0.8) !important; border-radius: 4px !important; padding: 0.2rem 0.5rem !important; }
.stCheckbox label { color: #cbd5e1 !important; font-size: 0.82rem !important; font-weight: 500 !important; }
input[type="checkbox"] { accent-color: #3b82f6 !important; width: 14px !important; height: 14px !important; }

/* ── Spinner y mensajes ── */
.stSpinner > div { border-top-color: #3b82f6 !important; }
.stSpinner p, [data-testid="stSpinner"] p { color: #e2e8f0 !important; font-weight: 500 !important; }
[data-testid="stMarkdownContainer"] p { color: #cbd5e1 !important; }
.stSuccess, .stInfo, .stWarning, .stError { color: #e2e8f0 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: #080b12 !important; border-bottom: 1px solid #1e3a6e !important; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Rajdhani', sans-serif !important; font-size: 0.9rem !important;
    font-weight: 600 !important; letter-spacing: 0.08em !important; text-transform: uppercase !important;
    color: #475569 !important; background: transparent !important; border-radius: 0 !important;
    padding: 0.5rem 1.4rem !important;
}
.stTabs [aria-selected="true"] { color: #60a5fa !important; border-bottom: 2px solid #3b82f6 !important; }
.stTabs [data-baseweb="tab-panel"] { background: rgba(8,11,18,0.98) !important; padding: 1.2rem 0.5rem !important; }

/* ── Stat boxes ── */
.stat-box {
    background: #0f1628; border: 1px solid #1e3a6e;
    border-top: 2px solid #3b82f6; border-radius: 6px;
    padding: 1rem 1.2rem; text-align: center;
}
.stat-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.16em; color: #475569; margin-bottom: 0.3rem; }
.stat-value { font-family: 'Rajdhani', sans-serif !important; font-size: 2rem; font-weight: 700; color: #60a5fa; }
.stat-sub { font-size: 0.68rem; color: #334155; margin-top: 0.1rem; }

/* ── Opening cards ── */
.op-card {
    background: #0f1628; border: 1px solid #1e3a6e;
    border-left: 3px solid #3b82f6; border-radius: 4px;
    padding: 0.75rem 0.9rem; margin-bottom: 0.4rem; transition: background 0.12s;
}
.op-card:hover { background: #1a2540; }
.op-card.risk    { border-left-color: #ef4444; }
.op-card.dominio { border-left-color: #22c55e; }
.op-card.feeling { border-left-color: #a855f7; }
.op-name { font-family: 'Rajdhani', sans-serif !important; font-size: 0.95rem; font-weight: 600; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: 0.04em; }
.op-stats { font-size: 0.7rem; color: #475569; margin-top: 0.15rem; }
.op-acc { font-family: 'Rajdhani', sans-serif !important; font-size: 1.2rem; font-weight: 700; float: right; margin-top: -1.5rem; }
.op-note { font-size: 0.68rem; color: #64748b; font-style: italic; margin-top: 0.2rem; }
.acc-hi  { color: #22c55e; } .acc-mid { color: #f59e0b; } .acc-lo { color: #ef4444; }

/* ── Profesor card ── */
.prof-card {
    background: linear-gradient(135deg, #0f1628 0%, #0a1428 100%);
    border: 1px solid #1e3a6e; border-radius: 8px;
    padding: 1.4rem 1.8rem; margin: 0.8rem 0 1.4rem;
    position: relative; overflow: hidden;
}
.prof-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #3b82f6 30%, #60a5fa 50%, #3b82f6 70%, transparent);
}
.prof-title { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.2em; color: #3b82f6; margin-bottom: 0.5rem; }
.prof-nivel { font-family: 'Rajdhani', sans-serif !important; font-size: 1.8rem; font-weight: 700; color: #e2e8f0; letter-spacing: 0.06em; }
.prof-desc { font-size: 0.82rem; color: #64748b; margin-top: 0.4rem; line-height: 1.6; }
.prof-stats { display: flex; gap: 1.5rem; margin-top: 0.9rem; padding-top: 0.9rem; border-top: 1px solid #1e3a6e; flex-wrap: wrap; }
.prof-stat { text-align: center; }
.prof-stat-val { font-family: 'Rajdhani', sans-serif !important; font-size: 1.4rem; font-weight: 700; color: #60a5fa; }
.prof-stat-lbl { font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.12em; color: #334155; }

/* ── Plan card ── */
.plan-card {
    background: #0f1628; border: 1px solid #1e3a6e;
    border-left: 3px solid #3b82f6; border-radius: 6px;
    padding: 1rem 1.3rem; margin-bottom: 1rem;
}
.plan-card.sin_base   { border-left-color: #ef4444; }
.plan-card.desarrollo { border-left-color: #f59e0b; }
.plan-card.dominio    { border-left-color: #22c55e; }
.color-section {
    background: rgba(15,22,40,0.6); border: 1px solid #1e3a6e;
    border-radius: 6px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
}
.color-section-title {
    font-family: 'Rajdhani', sans-serif; font-size: 0.85rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.12em; color: #94a3b8;
    margin-bottom: 0.7rem; padding-bottom: 0.4rem; border-bottom: 1px solid #1e3a6e;
}

/* ── Recurso card ── */
.res-card {
    background: #080b12; border: 1px solid #1e3a6e;
    border-left: 2px solid #2563eb; border-radius: 3px;
    padding: 0.5rem 0.8rem; margin: 0.25rem 0;
}
.res-card.free  { border-left-color: #22c55e; background: rgba(34,197,94,0.04); }
.res-card.paid  { border-left-color: #f59e0b; background: rgba(245,158,11,0.04); }
.res-card.study { border-left-color: #a855f7; background: rgba(168,85,247,0.04); }
.res-title { font-size: 0.83rem; color: #cbd5e1; }
.res-title a { color: #60a5fa; text-decoration: none; }
.res-title a:hover { text-decoration: underline; color: #93c5fd; }
.res-meta { font-size: 0.68rem; color: #475569; margin-top: 0.12rem; display:flex; gap:0.4rem; flex-wrap:wrap; align-items:center; }
.res-badge {
    font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.1em;
    padding: 1px 5px; border-radius: 2px; font-weight: 600;
}
.res-badge.video   { background: rgba(239,68,68,0.15);  color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
.res-badge.book    { background: rgba(34,197,94,0.15);  color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
.res-badge.course  { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.res-badge.study   { background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); }
.res-badge.free-lbl{ background: rgba(34,197,94,0.12);  color: #4ade80; border: 1px solid rgba(34,197,94,0.25); }
.res-badge.paid-lbl{ background: rgba(245,158,11,0.12); color: #fbbf24; border: 1px solid rgba(245,158,11,0.25); }
/* Columnas free/paid dentro de cada apertura */
.res-col-header {
    font-family: 'Rajdhani', sans-serif; font-size: 0.65rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.18em; padding: 0.2rem 0 0.4rem;
    border-bottom: 1px solid #1e3a6e; margin-bottom: 0.4rem;
}
.res-col-header.free { color: #22c55e; }
.res-col-header.paid { color: #f59e0b; }
.res-empty { font-size: 0.72rem; color: #334155; font-style: italic; padding: 0.3rem 0; }

/* ── Blunder rows ── */
.bl-row { display: flex; align-items: center; gap: 0.8rem; padding: 0.5rem 0; border-bottom: 1px solid #0f1628; font-size: 0.82rem; }
.bl-badge { font-family: 'Rajdhani', sans-serif !important; font-size: 0.85rem; font-weight: 700; padding: 1px 9px; border-radius: 3px; min-width: 62px; text-align: center; }
.bl-badge.severe { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); }
.bl-badge.warn   { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); }

/* ── Divisores ── */
.gold-div { height: 1px; background: linear-gradient(90deg, transparent, #1e3a6e 20%, #3b82f6 50%, #1e3a6e 80%, transparent); margin: 1rem 0; }
.sec-label { font-family: 'Rajdhani', sans-serif !important; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.2em; color: #334155; margin-bottom: 0.7rem; border-bottom: 1px solid #1e3a6e; padding-bottom: 0.28rem; }

/* ── Pills ── */
.pill { display: inline-block; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; padding: 2px 7px; border-radius: 3px; margin-left: 0.3rem; }
.pill-green  { background: rgba(34,197,94,0.15);  color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }
.pill-yellow { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.pill-red    { background: rgba(239,68,68,0.15);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }

/* ── Progress ── */
.stProgress > div > div { background-color: #3b82f6 !important; }
.stAlert { border-radius: 4px !important; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RUTAS
# ══════════════════════════════════════════════════════════════════════════════
PROJECT_ROOT      = r"C:\Users\Eneko\Desktop\Ejercicios Data\Proyectos\Proyecto ML"
DATA_DIR          = os.path.join(PROJECT_ROOT, "src", "data")
CSV_DIR           = os.path.join(DATA_DIR, "CSV")
PKL_DIR           = os.path.join(DATA_DIR, "PKL")
ENGINES_DIR       = os.path.join(PROJECT_ROOT, "resources", "engines")
STOCKFISH_PATH    = os.path.join(ENGINES_DIR, "stockfish-windows-x86-64-avx2.exe")
PKL_PATH          = os.path.join(PKL_DIR, "theory_db.pkl")
KM_PATH           = os.path.join(PKL_DIR, "km_apertura_pura.pkl")
SCALER_PATH       = os.path.join(PKL_DIR, "scaler_apertura_pura.pkl")
FILENAME_ML       = os.path.join(CSV_DIR, "master_game_level_ml.csv")
FILENAME_BLUNDERS = os.path.join(CSV_DIR, "blunders_pendientes.csv")
RECURSOS_PATH     = os.path.join(CSV_DIR, "chess_resources_v3.csv")
for _d in [CSV_DIR, PKL_DIR]:
    os.makedirs(_d, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
RISK_INDEX_MIN = 15.0
NIVEL_A_TIER   = {"sin_base": "beginner", "desarrollo": "intermediate", "dominio": "expert"}
TIER_FALLBACK  = {"expert": ["expert","intermediate","beginner"], "intermediate": ["intermediate","beginner","expert"], "beginner": ["beginner","intermediate","expert"]}
NIVEL_PRIO     = {"sin_base": 0, "desarrollo": 1, "dominio": 2}

SINONIMOS_APERTURAS = {
    "rapport-jobava system":          ["jobava london","london system"],
    "london system":                  ["london system"],
    "king's indian attack":           ["king's indian attack"],
    "nimzo-larsen attack":            ["nimzo-larsen"],
    "trompowsky attack":              ["trompowsky attack"],
    "hungarian opening":              ["hungarian opening", "king's fianchetto", "1.e4 e5 2.bc4"],
    "polish opening":                 ["polish opening", "orangutan", "1.b4", "sokolsky"],
    "bird opening":                   ["bird opening"],
    "english opening":                ["english opening"],
    "zukertort opening":              ["zukertort opening","colle system"],
    "yusupov-rubinstein system":      ["nimzo-indian defense"],
    "east indian defense":            ["king's indian defense","benoni defense"],
    "queen's pawn game":              ["queen's pawn game","queen's gambit","colle system"],
    "king's pawn game":               ["king's pawn game"],
    "pseudo queen's indian defense":  ["queen's indian defense"],
    "indian defense":                 ["indian defense"],
    "queen's indian defense":         ["queen's indian defense"],
    "nimzo-indian defense":           ["nimzo-indian defense"],
    "king's indian defense":          ["king's indian defense"],
    "benoni defense":                 ["benoni defense"],
    "benko gambit accepted":          ["benko gambit","volga gambit"],
    "grünfeld defense":               ["grünfeld defense","grunfeld defense"],
    "grunfeld defense":               ["grünfeld defense","grunfeld defense"],
    "sicilian defense":               ["sicilian defense"],
    "french defense":                 ["french defense"],
    "caro-kann defense":              ["caro-kann defense"],
    "pirc defense":                   ["pirc defense"],
    "modern defense":                 ["modern defense"],
    "alekhine defense":               ["alekhine defense"],
    "petrov's defense":               ["petrov's defense","russian game"],
    "ruy lopez":                      ["ruy lopez","spanish game"],
    "english defense":                ["english defense", "1.d4 b6", "queens fianchetto"],
    "owen defense":                   ["owen defense", "b6 defense", "1...b6"],
    "queen's gambit declined":        ["queen's gambit declined"],
    "queen's gambit accepted":        ["queen's gambit accepted"],
    "slav defense":                   ["slav defense"],
    "semi-slav defense":              ["semi-slav defense"],
    "catalan opening":                ["catalan opening"],
    "dutch defense":                  ["dutch defense"],
    "englund gambit":                 ["englund gambit", "1.d4 e5"],
}

APERTURAS_PRINCIPALES = [
    "french defense","sicilian defense","caro-kann defense","queen's gambit",
    "king's indian defense","nimzo-indian defense","queen's indian defense",
    "ruy lopez","italian game","english opening","dutch defense",
    "slav defense","grünfeld defense","benoni defense","pirc defense",
    "alekhine defense","king's gambit",
]
_WORD_TERMS = {"slav","pirc","bird","reti","benoni","benko","catalan","french","sicilian","alekhine","grunfeld","trompowsky","petrov"}


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════════════════════
def acpl_to_accuracy(acpl):
    return round(float(max(0, min(100, 100 * np.exp(-0.0035 * acpl)))), 1)

def _term_in_text(term, text):
    if term in _WORD_TERMS:
        return bool(re.search(r'(?<![a-z])' + re.escape(term) + r'(?![a-z])', text))
    return term in text

def normalizar_apertura(apertura):
    ap = apertura.strip().lower()
    terminos = [ap]
    for clave, sins in SINONIMOS_APERTURAS.items():
        if clave in ap or ap in clave:
            terminos.extend(sins)
    vistos = set()
    return [t for t in terminos if not (t in vistos or vistos.add(t))]


# ══════════════════════════════════════════════════════════════════════════════
# BLUNDERS
# ══════════════════════════════════════════════════════════════════════════════
def _guardar_blunder_local(game_id, usuario, apertura, fen, loss_cp):
    """
    Guarda el peor blunder de cada partida.
    En re-análisis SIEMPRE resetea Subido=False para que el blunder
    vuelva a aparecer en pantalla y esté disponible para subir de nuevo.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    nuevo = pd.DataFrame([{
        "Game_ID": game_id, "Usuario": usuario, "Apertura": apertura,
        "FEN": fen, "Loss_CP": round(float(loss_cp), 1),
        "Fecha": now, "Subido": False,
    }])
    if os.path.exists(FILENAME_BLUNDERS):
        df_b = pd.read_csv(FILENAME_BLUNDERS)
        mask = df_b["Game_ID"] == game_id
        if mask.any():
            # Re-análisis: actualizar si el nuevo error es peor, y SIEMPRE
            # resetear Subido=False para que vuelva a mostrarse en pantalla.
            if float(df_b.loc[mask, "Loss_CP"].iloc[0]) < float(loss_cp):
                df_b.loc[mask, "Loss_CP"] = round(float(loss_cp), 1)
                df_b.loc[mask, "FEN"]     = fen
            df_b.loc[mask, "Fecha"]  = now
            df_b.loc[mask, "Subido"] = False   # ← siempre visible tras re-análisis
            df_b.to_csv(FILENAME_BLUNDERS, index=False)
            return
        df_b = pd.concat([df_b, nuevo], ignore_index=True)
    else:
        df_b = nuevo
    df_b.to_csv(FILENAME_BLUNDERS, index=False)

def obtener_todos_blunders(usuario=None):
    """Devuelve TODOS los blunders del usuario, independientemente de si
    han sido subidos a Lichess o no. Se usa para el display en pantalla."""
    if not os.path.exists(FILENAME_BLUNDERS):
        return pd.DataFrame(columns=["Game_ID","Usuario","Apertura","FEN","Loss_CP","Fecha","Subido"])
    df_b = pd.read_csv(FILENAME_BLUNDERS)
    if usuario:
        df_b = df_b[df_b["Usuario"] == usuario]
    return df_b.sort_values("Loss_CP", ascending=False).reset_index(drop=True)

def obtener_blunders_pendientes(usuario=None):
    """Devuelve solo los blunders aún NO subidos a Lichess (Subido=False).
    Se usa exclusivamente para la lógica de subida al estudio."""
    if not os.path.exists(FILENAME_BLUNDERS):
        return pd.DataFrame(columns=["Game_ID","Usuario","Apertura","FEN","Loss_CP","Fecha","Subido"])
    df_b = pd.read_csv(FILENAME_BLUNDERS)
    df_b = df_b[df_b["Subido"] == False].copy()
    if usuario:
        df_b = df_b[df_b["Usuario"] == usuario]
    return df_b.reset_index(drop=True)

def resetear_blunders_usuario(usuario):
    """Marca todos los blunders del usuario como Subido=False,
    permitiendo volver a subirlos aunque ya estuvieran enviados."""
    if not os.path.exists(FILENAME_BLUNDERS):
        return
    df_b = pd.read_csv(FILENAME_BLUNDERS)
    if usuario:
        df_b.loc[df_b["Usuario"] == usuario, "Subido"] = False
    else:
        df_b["Subido"] = False
    df_b.to_csv(FILENAME_BLUNDERS, index=False)


def subir_blunders_pendientes(study_id, token, usuario):
    """Sube los blunders pendientes (Subido=False) a un estudio de Lichess.
    
    Args:
        study_id: ID del estudio de Lichess (8 caracteres)
        token: API token de Lichess
        usuario: Usuario de Lichess
        
    Returns:
        dict: {"subidos": int, "errores": int}
    """
    pendientes = obtener_blunders_pendientes(usuario)
    if pendientes.empty:
        return {"subidos": 0, "errores": 0}
    df_b = pd.read_csv(FILENAME_BLUNDERS)
    subidos = errores = 0
    for _, row in pendientes.iterrows():
        fen = str(row["FEN"]).strip()
        if len(fen.split()) == 4:
            fen += " 0 1"
        nombre = f"Blunder -{round(float(row['Loss_CP'])/100,1)}p | {row['Apertura'][:28]}"
        pgn = f'[Event "{nombre}"]\n[Site "{row["Game_ID"]}"]\n[SetUp "1"]\n[FEN "{fen}"]\n\n*'
        try:
            r = requests.post(
                f"https://lichess.org/api/study/{study_id}/import-pgn",
                headers={"Authorization": f"Bearer {token}"},
                data={"name": nombre, "pgn": pgn}, timeout=10
            )
            if r.status_code == 200:
                df_b.loc[df_b["Game_ID"] == row["Game_ID"], "Subido"] = True
                subidos += 1
            else:
                errores += 1
        except Exception:
            errores += 1
        time.sleep(0.4)
    df_b.to_csv(FILENAME_BLUNDERS, index=False)
    return {"subidos": subidos, "errores": errores}


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════
def enriquecer_dataset(df):
    df = df.copy()
    df["Accuracy"]       = df["ACL_Post_Teo"].apply(acpl_to_accuracy)
    df["acl_winsorized"] = df["ACL_Post_Teo"].clip(upper=500)
    df["accuracy_game"]  = df["acl_winsorized"].apply(acpl_to_accuracy)
    tn = (df["Fin_Teoria"].clip(upper=15) / 15).clip(0, 1)
    df["AccAjustada"]    = (df["Accuracy"] * (1 - 0.15 * tn)).round(1)
    df["teoria_norm"]    = tn
    df["game_prep_score"]    = ((df["Fin_Teoria"] / 15) * (df["Accuracy"] / 100)).round(4)
    df["game_risk_index"]    = ((df["Fin_Teoria"] / 15) * (100 - df["Accuracy"])).round(4)
    df["is_theory_expert"]   = ((df["Fin_Teoria"] >= 10) & (df["Accuracy"] >= 70)).astype(int)
    df["is_feeling_natural"] = ((df["Fin_Teoria"] <   7) & (df["Accuracy"] >= 65)).astype(int)
    df["is_critical_point"]  = ((df["Fin_Teoria"] >= 10) & (df["Accuracy"] <  60)).astype(int)
    df["color_bin"]          = (df["Color"] == "Blancas").astype(int)
    usr = df.groupby("Usuario").agg(
        win_rate_user   = ("Victoria",       "mean"),
        avg_teoria_user = ("Fin_Teoria",     "mean"),
        avg_acl_user    = ("acl_winsorized", "mean"),
        std_acl_user    = ("acl_winsorized", "std"),
        n_games_user    = ("Game_ID",        "count"),
        accuracy_user   = ("accuracy_game",  "mean"),
    ).reset_index()
    usr["std_acl_user"]      = usr["std_acl_user"].fillna(0)
    usr["consistency_score"] = (1 - (usr["std_acl_user"] / (usr["avg_acl_user"] + 1e-9)).clip(0, 1))
    drop = ["win_rate_user","avg_teoria_user","avg_acl_user","std_acl_user",
            "n_games_user","consistency_score","accuracy_user","delta_acl_vs_user"]
    df = df.drop(columns=[c for c in drop if c in df.columns])
    df = df.merge(usr, on="Usuario", how="left")
    df["delta_acl_vs_user"] = (df["acl_winsorized"] - df["avg_acl_user"]).round(2)
    df["nivel_3class"] = pd.cut(df["Rating_Usuario"], bins=[0,1400,1800,5000],
        labels=["principiante","intermedio","avanzado"], right=False).astype(str)
    df["nivel_num"] = (df["Rating_Usuario"].clip(500,3000) - 500) / 2500
    return df

def generar_dashboard_data(df_u):
    """
    Genera el DataFrame de dashboard con categorización RELATIVA al perfil del jugador.

    Umbrales relativos:
    - RIESGO:   Risk_Index > percentil 60 del jugador (las peores aperturas)
                Y Accuracy < acc_media_jugador - 15 puntos
                Con mínimo absoluto Risk_Index > 8 para no mostrar falsas alarmas
    - DOMINIO:  Score_Prep en el tercio superior, o Accuracy >= acc_media + 5
    - FEELING:  Teoría por debajo de la media del jugador - 20%
                Y Accuracy >= acc_media - 5 (buena para el nivel relativo)
                Y n >= 2 partidas
    """
    df = df_u.copy()
    df["ACL_clean"] = df["ACL_Post_Teo"].clip(upper=500)
    dm = df.groupby(["Apertura","Color"]).agg(
        Avg_Teoria = ("Fin_Teoria",  "mean"),
        Avg_ACL    = ("ACL_clean",   "mean"),
        Volumen    = ("Game_ID",     "count"),
        Win_Rate   = ("Victoria",    "mean"),
    ).reset_index()
    dm["Accuracy"]   = dm["Avg_ACL"].apply(acpl_to_accuracy)
    dm["Score_Prep"] = (dm["Avg_Teoria"] / 15) * (dm["Accuracy"] / 100)
    dm["Risk_Index"] = (dm["Avg_Teoria"] / 15) * (100 - dm["Accuracy"])

    # ── Umbrales relativos al jugador ────────────────────────────────────────
    acc_media  = dm["Accuracy"].mean()
    teo_media  = dm["Avg_Teoria"].mean()
    risk_p60   = dm["Risk_Index"].quantile(0.60)   # peor 40% del repertorio

    # RIESGO: está en el 40% peor Y accuracy por debajo de la media del jugador
    dm["es_riesgo"] = (
        (dm["Risk_Index"] > max(risk_p60, 8.0)) &
        (dm["Accuracy"] < acc_media - 10)
    )

    # DOMINIO: buen Score_Prep Y accuracy encima de la media
    prep_p50 = dm["Score_Prep"].quantile(0.50)
    dm["es_dominio"] = (
        (dm["Score_Prep"] >= prep_p50) &
        (dm["Accuracy"] >= acc_media - 5) &
        (dm["Volumen"] >= 2)
    )

    # FEELING: poca teoría (< media - 20%) Y buena accuracy relativa
    teo_umbral = max(teo_media * 0.8, 5)
    dm["Score_Feeling"] = np.where(
        (dm["Avg_Teoria"] <= teo_umbral) &
        (dm["Accuracy"] >= acc_media - 8) &
        (dm["Volumen"] >= 2),
        dm["Accuracy"], 0
    )

    return dm


# ══════════════════════════════════════════════════════════════════════════════
# CLUSTERING
# ══════════════════════════════════════════════════════════════════════════════
def asignar_nivel_apertura(df_u):
    FEAT = ["Fin_Teoria","acl_winsorized","game_prep_score","game_risk_index"]
    try:
        km = joblib.load(KM_PATH); scaler = joblib.load(SCALER_PATH)
    except FileNotFoundError:
        return pd.DataFrame()
    df = df_u.copy()
    if "acl_winsorized"  not in df.columns: df["acl_winsorized"]  = df["ACL_Post_Teo"].clip(upper=500)
    if "Accuracy"        not in df.columns: df["Accuracy"]        = df["ACL_Post_Teo"].apply(acpl_to_accuracy)
    if "game_prep_score" not in df.columns: df["game_prep_score"] = ((df["Fin_Teoria"]/15)*(df["Accuracy"]/100)).round(4)
    if "game_risk_index" not in df.columns: df["game_risk_index"] = ((df["Fin_Teoria"]/15)*(100-df["Accuracy"])).round(4)
    if "AccAjustada"     not in df.columns:
        tn = (df["Fin_Teoria"].clip(upper=15)/15).clip(0,1)
        df["AccAjustada"] = (df["Accuracy"]*(1-0.15*tn)).round(1)
    res = df.groupby(["Apertura","Color"]).agg(
        n_partidas=("Game_ID","count"), Teo_Med=("Fin_Teoria","mean"),
        AccAdj_Med=("AccAjustada","mean"), win_rate=("Victoria","mean"),
        Fin_Teoria=("Fin_Teoria","mean"), acl_winsorized=("acl_winsorized","mean"),
        game_prep_score=("game_prep_score","mean"), game_risk_index=("game_risk_index","mean"),
    ).reset_index()
    res = res[res["n_partidas"] >= 2].copy()
    if res.empty: return res
    X = scaler.transform(res[FEAT].fillna(0))
    res["cluster_raw"] = km.predict(X)
    centroides = km.cluster_centers_
    res["distancia"] = np.linalg.norm(X - centroides[res["cluster_raw"].values], axis=1)
    orden = res.groupby("cluster_raw")["acl_winsorized"].mean().sort_values().index.tolist()
    mapa  = {c: r for r, c in enumerate(orden)}
    res["rango"] = res["cluster_raw"].map(mapa)
    res["nivel_apertura"] = res["rango"].map({0:"dominio",1:"desarrollo",2:"sin_base"})
    return res.drop(columns=["cluster_raw","rango"])


# ══════════════════════════════════════════════════════════════════════════════
# RECOMENDADOR
# ══════════════════════════════════════════════════════════════════════════════

def buscar_estudios_lichess(apertura, token=None, top_n=3):
    """
    Fallback: busca estudios públicos en Lichess relacionados con la apertura.
    Parsea /study/search?q=<apertura> con regex. Si falla la red devuelve
    al menos el link de búsqueda para que el usuario lo explore directamente.
    Siempre retorna is_free=1 (estudios Lichess son gratuitos).
    """
    query      = apertura.strip()
    search_url = "https://lichess.org/study/search?q=" + requests.utils.quote(query)
    headers    = {"Accept": "text/html,application/xhtml+xml"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(search_url, headers=headers, timeout=8)
        r.raise_for_status()
        html = r.text
        ids    = re.findall(r'href="/study/([a-zA-Z0-9]{8})"', html)
        titles = re.findall(
            r'class="(?:study__name|title)[^"]*"[^>]*>([^<]{3,80})<', html
        )
        if not ids:
            return [{
                "title": f'Buscar "{query}" en Lichess Studies',
                "url": search_url, "source": "lichess_studies",
                "course_type": "lichess_study", "level_tier": "any", "is_free": 1,
            }]
        resultados = []
        seen = set()
        for sid, title in zip(ids, titles + [""] * len(ids)):
            if sid in seen:
                continue
            seen.add(sid)
            titulo_limpio = title.strip() or f"Estudio: {query}"
            resultados.append({
                "title": titulo_limpio[:72],
                "url": f"https://lichess.org/study/{sid}",
                "source": "lichess_studies",
                "course_type": "lichess_study",
                "level_tier": "any",
                "is_free": 1,
            })
            if len(resultados) >= top_n:
                break
        # Link de búsqueda general al final si hay hueco
        if len(resultados) < top_n:
            resultados.append({
                "title": f'Ver más estudios de "{query}"',
                "url": search_url, "source": "lichess_studies",
                "course_type": "lichess_study", "level_tier": "any", "is_free": 1,
            })
        return resultados
    except Exception:
        return [{
            "title": f'Buscar "{query}" en Lichess Studies',
            "url": search_url, "source": "lichess_studies",
            "course_type": "lichess_study", "level_tier": "any", "is_free": 1,
        }]


def _seleccionar_diverso(df, top_n):
    """Greedy: selecciona top_n filas evitando que un mismo course_type acapare todo."""
    if "course_type" not in df.columns or len(df) <= top_n:
        return df.head(top_n)
    MAX_POR_TIPO = max(1, top_n // 2)
    sel = []
    conteo = {}
    ids_sel = set()
    for idx, row in df.iterrows():
        tipo = str(row.get("course_type", "")).lower()
        if conteo.get(tipo, 0) < MAX_POR_TIPO:
            sel.append(row)
            conteo[tipo] = conteo.get(tipo, 0) + 1
            ids_sel.add(idx)
        if len(sel) >= top_n:
            break
    # Completar sin restricción si el pool es pequeño
    if len(sel) < top_n:
        for idx, row in df.iterrows():
            if idx not in ids_sel:
                sel.append(row)
            if len(sel) >= top_n:
                break
    return pd.DataFrame(sel) if sel else pd.DataFrame()


def buscar_recursos(apertura, color_jugador, df_rec, rating, nivel,
                    top_n=3, ya_recomendados=None,
                    lichess_token=None, is_free_filter=None):
    """
    Retorna hasta top_n recursos del CSV con PRIORIDAD CORRECTA:

    PRIORIDAD 1 — Apertura exacta + Nivel del usuario (tier_obj)
    PRIORIDAD 2 — Apertura exacta + Cualquier nivel   (si P1 insuficiente)
    PRIORIDAD 3 — Recursos generales sin match        (último recurso)

    is_free_filter=1  → SIEMPRE Lichess Studies (links siempre válidos)
    is_free_filter=0  → solo de pago (CSV)
    is_free_filter=None → todos (CSV)
    """
    if ya_recomendados is None:
        ya_recomendados = set()

    # ─── CANAL GRATUITO: siempre Lichess Studies ──────────────────────────
    # Los links de video/PDF del CSV tienden a caducar y romperse.
    # Lichess Studies es siempre válido, gratuito y actualizado.
    if is_free_filter == 1:
        return buscar_estudios_lichess(apertura, lichess_token, top_n)

    tier_obj = NIVEL_A_TIER.get(nivel, "intermediate")
    terminos  = normalizar_apertura(apertura)

    TIPO_BONUS = {"video": 8, "youtube": 8, "book": 6, "libro": 6, "lichess_study": 4}

    # ─── PREPARACIÓN DEL POOL BASE ────────────────────────────────────────
    color_en = "White" if color_jugador == "Blancas" else "Black"
    if "color" in df_rec.columns:
        col_norm = df_rec["color"].fillna("Both").str.strip().str.lower()
        mask_c   = col_norm.isin([color_en.lower(), "both"])
        pool     = df_rec[mask_c].copy()
        if len(pool) < 10:
            pool = df_rec.copy()
    else:
        pool = df_rec.copy()

    if is_free_filter is not None and "is_free" in pool.columns:
        pool = pool[pool["is_free"] == is_free_filter].copy()

    if "level_min" in pool.columns and "level_max" in pool.columns:
        mask_r = (
            (pool["level_min"].fillna(0) <= rating)
            & (pool["level_max"].fillna(9999) >= rating)
        )
        pool_r = pool[mask_r]
        pool   = pool_r if not pool_r.empty else pool

    if ya_recomendados and "resource_id" in pool.columns:
        pool = pool[~pool["resource_id"].isin(ya_recomendados)]

    if pool.empty:
        if is_free_filter != 0:
            return buscar_estudios_lichess(apertura, lichess_token, top_n)
        return []

    # ─── FUNCIÓN DE MATCHING ──────────────────────────────────────────────
    def _match_ap(col):
        return col.fillna("").str.lower().apply(
            lambda c: any(_term_in_text(t, c) for t in terminos)
        )

    def _score(sub):
        """Calcula score de relevancia para un subset."""
        sub = sub.copy()
        sub["_sc"] = 0.0
        if "openings" in sub.columns:
            sub["_sc"] += _match_ap(sub["openings"]).astype(float) * 60
        if "title" in sub.columns:
            sub["_sc"] += _match_ap(sub["title"]).astype(float) * 20
        if "rating_score" in sub.columns:
            sub["_sc"] += sub["rating_score"].fillna(0) * 0.5
        if "course_type" in sub.columns:
            sub["_sc"] += sub["course_type"].fillna("").str.lower().apply(
                lambda t: next((v for k, v in TIPO_BONUS.items() if k in t), 0)
            )
        return sub.sort_values("_sc", ascending=False)

    # Calcular mask de apertura una sola vez
    m_open  = _match_ap(pool["openings"]) if "openings" in pool.columns else pd.Series(False, index=pool.index)
    m_title = _match_ap(pool["title"])    if "title"    in pool.columns else pd.Series(False, index=pool.index)
    mask_apertura = m_open | m_title

    # ─── PRIORIDAD 1: Apertura + Nivel exacto ─────────────────────────────
    if "level_tier" in pool.columns:
        p1_raw = pool[mask_apertura & (pool["level_tier"] == tier_obj)]
    else:
        p1_raw = pool[mask_apertura]
    pool_p1 = _score(p1_raw) if not p1_raw.empty else pd.DataFrame()

    # ─── PRIORIDAD 2: Apertura + Cualquier nivel ──────────────────────────
    pool_p2 = pd.DataFrame()
    if len(pool_p1) < top_n:
        ids_p1 = set(pool_p1["resource_id"].tolist()) if not pool_p1.empty and "resource_id" in pool_p1.columns else set()
        p2_raw = pool[mask_apertura].copy()
        if ids_p1 and "resource_id" in p2_raw.columns:
            p2_raw = p2_raw[~p2_raw["resource_id"].isin(ids_p1)]
        pool_p2 = _score(p2_raw) if not p2_raw.empty else pd.DataFrame()

    # ─── PRIORIDAD 3: Otros recursos generales ────────────────────────────
    pool_p3 = pd.DataFrame()
    total_p1_p2 = len(pool_p1) + len(pool_p2)
    if total_p1_p2 < top_n:
        ids_usados = set()
        for df_used in [pool_p1, pool_p2]:
            if not df_used.empty and "resource_id" in df_used.columns:
                ids_usados.update(df_used["resource_id"].tolist())
        p3_raw = pool[~mask_apertura].copy()
        if ids_usados and "resource_id" in p3_raw.columns:
            p3_raw = p3_raw[~p3_raw["resource_id"].isin(ids_usados)]
        # Score básico sin bonus de apertura
        p3_raw = p3_raw.copy()
        p3_raw["_sc"] = 0.0
        if "rating_score" in p3_raw.columns:
            p3_raw["_sc"] += p3_raw["rating_score"].fillna(0) * 0.5
        if "course_type" in p3_raw.columns:
            p3_raw["_sc"] += p3_raw["course_type"].fillna("").str.lower().apply(
                lambda t: next((v for k, v in TIPO_BONUS.items() if k in t), 0)
            )
        pool_p3 = p3_raw.sort_values("_sc", ascending=False) if not p3_raw.empty else pd.DataFrame()

    # ─── COMBINAR Y DIVERSIFICAR ──────────────────────────────────────────
    frames = [f for f in [pool_p1, pool_p2, pool_p3] if not f.empty]
    final  = pd.concat(frames).head(top_n * 2) if frames else pd.DataFrame()

    final_div = _seleccionar_diverso(final, top_n)

    cols   = [c for c in ["resource_id","title","source","course_type","level_tier","url","is_free"] if c in final_div.columns]
    result = [row[cols].to_dict() for _, row in final_div.iterrows()] if not final_div.empty else []

    # Marcar si vino de prioridad 2 ó 3 (distinto nivel)
    if not pool_p1.empty and "resource_id" in pool_p1.columns:
        ids_p1 = set(pool_p1["resource_id"].tolist())
        for r in result:
            rid = r.get("resource_id")
            if rid and rid not in ids_p1:
                r["fallback_tier"] = r.get("level_tier","any")

    # ── Completar con Lichess si el CSV da pocos resultados (solo gratuito) ─
    if len(result) < top_n and is_free_filter != 0:
        extras = buscar_estudios_lichess(apertura, lichess_token, top_n - len(result))
        result.extend(extras)

    return result

def generar_plan_estudio(df_u, df_rec, rating, top_n_ap=5, top_n_res=3, lichess_token=None):
    """
    Genera el plan de estudio separado por Blancas y Negras.
    Retorna dict {"Blancas": [...], "Negras": [...]}
    Cada entrada incluye 'recursos_free' y 'recursos_paid' separados
    para mostrarlos en dos columnas (gratuito / de pago) sin excluirse.
    El campo 'recursos' (union) se mantiene por retrocompatibilidad.
    """
    res = asignar_nivel_apertura(df_u)
    if res.empty: return {"Blancas": [], "Negras": []}
    res["prio"] = res["nivel_apertura"].map(NIVEL_PRIO)
    res = res[res["n_partidas"] >= 2].sort_values(["prio","win_rate"], ascending=[True,True])

    plan = {"Blancas": [], "Negras": []}
    for color in ["Blancas", "Negras"]:
        res_color = res[res["Color"] == color].head(top_n_ap)
        ya_free = set()
        ya_paid = set()
        for _, f in res_color.iterrows():
            apertura = f["Apertura"]
            nivel    = f["nivel_apertura"]
            # Canal gratuito (YouTube, Lichess Studies, PDFs...)
            recursos_free = buscar_recursos(
                apertura, color, df_rec, rating, nivel,
                top_n=top_n_res, ya_recomendados=ya_free,
                lichess_token=lichess_token, is_free_filter=1,
            )
            # Canal de pago (Amazon libros, Chessable, cursos...)
            recursos_paid = buscar_recursos(
                apertura, color, df_rec, rating, nivel,
                top_n=top_n_res, ya_recomendados=ya_paid,
                lichess_token=lichess_token, is_free_filter=0,
            )
            for r in recursos_free:
                if r.get("resource_id"): ya_free.add(r["resource_id"])
            for r in recursos_paid:
                if r.get("resource_id"): ya_paid.add(r["resource_id"])
            plan[color].append({
                "apertura":      apertura,
                "color":         color,
                "nivel":         nivel,
                "n_partidas":    int(f["n_partidas"]),
                "teo_med":       round(f["Teo_Med"], 1),
                "acc_adj":       round(f["AccAdj_Med"], 1),
                "win_rate":      round(f["win_rate"] * 100, 1),
                "distancia":     round(f["distancia"], 3),
                "recursos_free": recursos_free,
                "recursos_paid": recursos_paid,
                "recursos":      recursos_free + recursos_paid,
            })
    return plan


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR STOCKFISH
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def cargar_teoria():
    """Carga la base teórica (327K posiciones). Se cachea porque es costosa."""
    with open(PKL_PATH, "rb") as f:
        theory = pickle.load(f)
    return theory

def crear_stockfish():
    """Crea una instancia fresca de Stockfish. NO se cachea para evitar estado corrupto."""
    sf = Stockfish(path=STOCKFISH_PATH, parameters={"Threads": 4, "Hash": 512})
    sf.set_depth(16)
    return sf

def get_eval(sf, fen, cap=1000):
    """
    Evalúa una posición con Stockfish.
    Retorna None si falla (no 0.0) para distinguir error de evaluación real de 0.
    """
    try:
        # Validar que el FEN tiene al menos 4 campos
        if not fen or len(fen.strip().split()) < 4:
            return None
        sf.set_fen_position(fen, do_validation=False)
        ev = sf.get_evaluation()
        if ev is None:
            return None
        if ev["type"] == "mate":
            return float(cap if ev["value"] > 0 else -cap)
        return float(max(-cap, min(cap, ev["value"])))
    except Exception as e:
        # No silenciar: guardar en session_state para debug
        if "sf_errors" not in st.session_state:
            st.session_state["sf_errors"] = []
        st.session_state["sf_errors"].append(str(e)[:80])
        return None

def analizar_partidas(games_list, target_user, user_rating, sf, theory_positions, progress_bar):
    """Analiza partidas. Guarda el PEOR blunder (>100cp) por partida."""
    results = []
    total   = len(games_list)
    for idx, game in enumerate(games_list):
        if not game: continue
        h        = game.headers
        game_id  = h.get("Site","").split("/")[-1]
        is_white = h.get("White","").lower() == target_user.lower()
        color    = chess.WHITE if is_white else chess.BLACK
        apertura = h.get("Opening","Desconocida").split(":")[0].split(",")[0].strip()
        res      = h.get("Result","*")
        victoria = (1.0 if (res=="1-0" and is_white) or (res=="0-1" and not is_white)
                    else 0.5 if res=="1/2-1/2" else 0.0)

        # Detectar fin de teoría
        board = game.board(); moves = list(game.mainline_moves())
        theory_end = 0; streak = 0
        for i, mv in enumerate(moves[:30]):
            board.push(mv)
            if board.epd() in theory_positions:
                theory_end = i + 1; streak = 0
            else:
                streak += 1
                if streak >= 2: break

        # Calcular ACL + detectar peor blunder
        # WINDOW = 12 jugadas PROPIAS del jugador (no 12 jugadas del tablero)
        board2 = game.board()
        for m in moves[:theory_end]: board2.push(m)
        losses      = []
        peor_loss   = 0.0
        peor_fen    = None
        propias_cnt = 0
        MAX_PROPIAS = 12  # jugadas propias a analizar post-teoría

        if theory_end < len(moves):
            eval_cache = get_eval(sf, board2.fen())
            if eval_cache is not None:
                if "n_eval_ok" not in st.session_state: st.session_state["n_eval_ok"] = 0
                st.session_state["n_eval_ok"] += 1
            for i in range(theory_end, len(moves)):
                if propias_cnt >= MAX_PROPIAS:
                    break
                is_player = (board2.turn == color)
                fen_antes  = board2.fen()
                eval_prev  = eval_cache
                board2.push(moves[i])
                eval_cache = get_eval(sf, board2.fen())
                if eval_cache is not None:
                    if "n_eval_ok" not in st.session_state: st.session_state["n_eval_ok"] = 0
                    st.session_state["n_eval_ok"] += 1
                if is_player:
                    propias_cnt += 1
                    # Solo calcular loss si ambas evaluaciones son válidas (no None)
                    if eval_prev is not None and eval_cache is not None:
                        side = 1.0 if color == chess.WHITE else -1.0
                        loss = float(max(0.0, (eval_prev - eval_cache) * side))
                        losses.append(loss)
                        if loss > 100.0 and loss > peor_loss:
                            peor_loss = loss
                            peor_fen  = fen_antes

        # Persistir blunder si existe
        if peor_fen is not None:
            _guardar_blunder_local(game_id, target_user, apertura, peor_fen, peor_loss)

        acl = sum(losses) / len(losses) if losses else None
        if acl is not None:
            results.append({
                "Game_ID": game_id, "Usuario": target_user,
                "Rating_Usuario": user_rating, "Apertura": apertura,
                "Color": "Blancas" if is_white else "Negras",
                "Fin_Teoria": theory_end, "ACL_Post_Teo": round(acl,1),
                "Victoria": victoria,
            })
        progress_bar.progress((idx + 1) / total)
    return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTES UI
# ══════════════════════════════════════════════════════════════════════════════
def render_gold_divider():
    st.markdown('<div class="gold-div"></div>', unsafe_allow_html=True)

def render_section_label(text):
    st.markdown(f'<div class="sec-label">{text}</div>', unsafe_allow_html=True)

def render_metric(label, value, sub=""):
    st.markdown(f'<div class="stat-box"><div class="stat-label">{label}</div><div class="stat-value">{value}</div><div class="stat-sub">{sub}</div></div>', unsafe_allow_html=True)

def render_opening_card(nombre, acc, teo, n, wr, tipo="dominio", nota=""):
    cls  = "acc-hi" if acc >= 80 else "acc-mid" if acc >= 60 else "acc-lo"
    nota_html = f'<div class="op-note">— {nota}</div>' if nota else ""
    st.markdown(f'<div class="op-card {tipo}"><div class="op-name">{nombre}</div><span class="op-acc {cls}">{acc:.1f}%</span><div class="op-stats">Teo {teo:.1f}j &middot; n={n} &middot; WR {wr*100:.0f}%</div>{nota_html}</div>', unsafe_allow_html=True)

def render_resource(rec):
    titulo = rec.get("title", "Sin título")[:68]
    url    = rec.get("url", "")
    tipo   = rec.get("course_type", "").lower()
    tier   = rec.get("level_tier", "")
    es_free = rec.get("is_free", None)
    fb     = f"· ↓ {rec['fallback_tier']}" if "fallback_tier" in rec else ""
    link   = f'<a href="{url}" target="_blank">{titulo}</a>' if url and url != "nan" else titulo

    # Icono e indicador de tipo
    if "study" in tipo or rec.get("source") == "lichess_studies":
        icono = "♟"; badge_tipo = "study"; badge_label = "Lichess Study"
        card_cls = "study"
    elif "video" in tipo or "youtube" in tipo:
        icono = "▶"; badge_tipo = "video"; badge_label = "Video"
        card_cls = "free"
    elif "book" in tipo or "libro" in tipo:
        icono = "📖"; badge_tipo = "book"; badge_label = "Libro"
        card_cls = "paid" if es_free == 0 else "free"
    elif es_free == 0:
        icono = "▸"; badge_tipo = "course"; badge_label = "Curso"
        card_cls = "paid"
    else:
        icono = "▸"; badge_tipo = "course"; badge_label = tipo.capitalize() or "Recurso"
        card_cls = "free"

    tier_html = f'<span class="res-badge course">{tier.upper()}</span>' if tier and tier != "any" else ""
    fb_html   = f'<span style="color:#475569">{fb}</span>' if fb else ""

    st.markdown(
        f'<div class="res-card {card_cls}">',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="res-title">{icono} {link}</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="res-meta"><span class="res-badge {badge_tipo}">{badge_label}</span>{tier_html}{fb_html}</div></div>',
        unsafe_allow_html=True
    )


def render_profesor_card(rating, df_u):
    if df_u is None or df_u.empty: return
    acc_med = df_u["Accuracy"].mean()   if "Accuracy"   in df_u.columns else 0
    teo_med = df_u["Fin_Teoria"].mean() if "Fin_Teoria"  in df_u.columns else 0
    n_p     = len(df_u)
    wr      = df_u["Victoria"].mean()   if "Victoria"    in df_u.columns else 0

    if   rating >= 2200: nivel="Gran Maestro Amateur"; icono="♔"
    elif rating >= 2000: nivel="Maestro FIDE";         icono="♕"
    elif rating >= 1800: nivel="Jugador Avanzado";     icono="♖"
    elif rating >= 1600: nivel="Competidor de Club";   icono="♗"
    elif rating >= 1400: nivel="Jugador Intermedio";   icono="♘"
    elif rating >= 1200: nivel="Principiante Avanzado";icono="♙"
    else:                nivel="Principiante";          icono="♟"

    if   acc_med >= 80 and teo_med >= 10: diag = f"Tu precisión post-apertura ({acc_med:.0f}%) y profundidad teórica ({teo_med:.1f}j) están bien alineadas con tu Elo. Foco en profundizar las aperturas de riesgo."
    elif acc_med >= 80 and teo_med <  7:  diag = f"Instinto posicional sobresaliente ({acc_med:.0f}%) con poca teoría. Eres un jugador de feeling: potencia esas líneas naturales."
    elif acc_med <  65 and teo_med >= 10: diag = f"Mucha teoría ({teo_med:.1f}j) pero precisión post-apertura baja ({acc_med:.0f}%). Estudia estructuras de peones, no solo movimientos."
    elif acc_med <  65:                   diag = f"Precisión post-apertura ({acc_med:.0f}%) con margen de mejora. Prioriza las aperturas marcadas como riesgo antes de ampliar repertorio."
    else:                                 diag = f"Perfil equilibrado: {acc_med:.0f}% de precisión y {teo_med:.1f}j de teoría media. Consolida las aperturas de dominio y trabaja las de riesgo."

    st.markdown(f"""
    <div class="prof-card">
        <div class="prof-title">Diagnóstico del Profesor</div>
        <div class="prof-nivel">{icono}&nbsp; {nivel}</div>
        <div class="prof-desc">{diag}</div>
        <div class="prof-stats">
            <div class="prof-stat"><div class="prof-stat-val">{rating:.0f}</div><div class="prof-stat-lbl">Elo Blitz</div></div>
            <div class="prof-stat"><div class="prof-stat-val">{acc_med:.0f}%</div><div class="prof-stat-lbl">Precisión</div></div>
            <div class="prof-stat"><div class="prof-stat-val">{teo_med:.1f}j</div><div class="prof-stat-lbl">Teoría media</div></div>
            <div class="prof-stat"><div class="prof-stat-val">{wr*100:.0f}%</div><div class="prof-stat-lbl">Win rate</div></div>
            <div class="prof-stat"><div class="prof-stat-val">{n_p}</div><div class="prof-stat-lbl">Partidas</div></div>
        </div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PROFESOR VIRTUAL ANIMADO (integrado desde profesor_virtual.py)
# ══════════════════════════════════════════════════════════════════════════════

def render_profesor_virtual(nivel, rating, accuracy_media, mensaje_custom=None):
    """
    Renderiza un profesor virtual animado con bocadillo de diálogo.
    Aparece en esquina inferior derecha con animación y auto-cierre a 15s.
    Args:
        nivel: "sin_base", "desarrollo", "dominio"
        rating: ELO del jugador
        accuracy_media: Precisión promedio
        mensaje_custom: Mensaje personalizado opcional
    """
    avatares = {
        "sin_base": "🎓",
        "desarrollo": "👨\u200d🏫",
        "dominio": "🏆"
    }

    if mensaje_custom:
        mensaje = mensaje_custom
    else:
        if nivel == "sin_base":
            mensajes = [
                f"¡Bienvenido! Con {rating} ELO, estás comenzando tu viaje. ¡Vamos a construir una base sólida! 💪",
                f"Tu accuracy promedio es {accuracy_media:.1f}%. ¡Hay mucho potencial de mejora! 📈",
                "Enfócate primero en las aperturas de 'Éxito Natural' — son tu punto fuerte.",
            ]
        elif nivel == "desarrollo":
            mensajes = [
                f"¡Excelente progreso! Con {rating} ELO y {accuracy_media:.1f}% de accuracy, estás en buen camino. 🚀",
                "Tu repertorio tiene una base sólida. Ahora profundicemos en teoría.",
                "Las aperturas en 'Riesgo' necesitan atención — ¡son oportunidades de mejora!",
            ]
        else:
            mensajes = [
                f"¡Impresionante! {rating} ELO con {accuracy_media:.1f}% accuracy. ¡Eres un experto! 👑",
                "Tu dominio técnico es sobresaliente. Hora de perfeccionar los detalles.",
                "Mantén tus fortalezas y trabaja en las pocas debilidades restantes.",
            ]
        mensaje = random.choice(mensajes)

    avatar  = avatares.get(nivel, "👨\u200d🏫")
    colores = {
        "sin_base":   {"bg": "#fee2e2", "border": "#ef4444", "text": "#991b1b"},
        "desarrollo": {"bg": "#fef3c7", "border": "#f59e0b", "text": "#92400e"},
        "dominio":    {"bg": "#d1fae5", "border": "#22c55e", "text": "#065f46"},
    }
    color    = colores.get(nivel, colores["desarrollo"])
    nivel_lbl = {"sin_base": "Principiante", "desarrollo": "Intermedio", "dominio": "Experto"}.get(nivel, nivel)

    html_code = f"""
    <style>
    @keyframes slideInRight {{
        from {{ transform: translateX(110%); opacity: 0; }}
        to   {{ transform: translateX(0);   opacity: 1; }}
    }}
    @keyframes bounce {{
        0%, 100% {{ transform: translateY(0); }}
        50%       {{ transform: translateY(-8px); }}
    }}
    .profesor-container {{
        position: fixed; bottom: 24px; right: 24px; z-index: 9999;
        animation: slideInRight 0.55s ease-out;
        max-width: 320px; font-family: Inter, system-ui, sans-serif;
    }}
    .speech-bubble {{
        position: relative; background: {color['bg']};
        border: 2px solid {color['border']}; border-radius: 12px;
        padding: 1rem 1.2rem; margin-bottom: 0.5rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }}
    .speech-bubble::after {{
        content: ''; position: absolute; bottom: -18px; right: 28px;
        width: 0; height: 0;
        border: 9px solid transparent;
        border-top-color: {color['border']};
    }}
    .speech-text {{ color: {color['text']}; font-size: 0.88rem; line-height: 1.5; font-weight: 500; margin: 0; }}
    .profesor-close {{
        position: absolute; top: 8px; right: 10px;
        background: transparent; border: none;
        font-size: 1.1rem; cursor: pointer; color: {color['text']}; opacity: 0.5;
        transition: opacity 0.2s;
    }}
    .profesor-close:hover {{ opacity: 1; }}
    .profesor-level-badge {{
        display: inline-block; background: {color['border']}; color: white;
        padding: 2px 8px; border-radius: 4px;
        font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.6px; margin-bottom: 0.4rem;
    }}
    .profesor-avatar {{
        font-size: 3rem; animation: bounce 2.2s ease-in-out infinite;
        display: inline-block; filter: drop-shadow(0 3px 5px rgba(0,0,0,0.1));
    }}
    </style>
    <div class="profesor-container" id="profesorContainer">
        <div class="speech-bubble">
            <button class="profesor-close"
                onclick="document.getElementById('profesorContainer').style.display='none'">×</button>
            <div class="profesor-level-badge">{nivel_lbl}</div>
            <p class="speech-text">{mensaje}</p>
        </div>
        <div style="text-align:right;padding-right:28px;">
            <span class="profesor-avatar">{avatar}</span>
        </div>
    </div>
    <script>
    setTimeout(() => {{
        const c = document.getElementById('profesorContainer');
        if (c) c.style.display = 'none';
    }}, 15000);
    </script>
    """
    components.html(html_code, height=190, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# TABLERO PROFESIONAL (integrado desde tablero_profesional.py)
# ══════════════════════════════════════════════════════════════════════════════

def render_tablero_profesional(fen, apertura_nombre="", jugadas_siguientes=None, width=380):
    """
    Renderiza un tablero de ajedrez SVG de alta calidad para una posición FEN.
    Usa st.markdown (SVG inline) en lugar de components.html para máxima
    compatibilidad dentro de tabs y columnas de Streamlit.
    """
    try:
        board = chess.Board(fen)
    except Exception:
        st.warning(f"FEN inválido: {fen}")
        return

    svg_raw = chess.svg.board(
        board=board,
        size=width,
        coordinates=True,
        colors={
            "square light":          "#f0d9b5",
            "square dark":           "#b58863",
            "square dark lastmove":  "#aaa23a",
            "square light lastmove": "#cdd26a",
        }
    )

    turno       = "Blancas" if board.turn else "Negras"
    turno_color = "#3b82f6" if board.turn else "#94a3b8"
    titulo      = f"📖 {apertura_nombre}" if apertura_nombre else "♟️ Posición"

    moves_html = ""
    if jugadas_siguientes:
        chips = "".join(
            f'<span style="display:inline-block;background:rgba(59,130,246,0.15);color:#60a5fa;'
            f'border:1px solid rgba(59,130,246,0.3);padding:3px 9px;border-radius:4px;'
            f'font-size:0.78rem;margin:0 0.25rem 0.25rem 0;font-family:Courier New,monospace;'
            f'font-weight:600;">{m}</span>'
            for m in jugadas_siguientes
        )
        moves_html = (
            f'<div style="margin-top:0.6rem;padding:0.6rem;background:rgba(10,14,26,0.8);'
            f'border-radius:6px;border:1px solid #1e3a6e;">'
            f'<div style="color:#60a5fa;font-size:0.75rem;font-weight:600;margin-bottom:0.35rem;'
            f'text-transform:uppercase;letter-spacing:0.1em;">💡 Jugadas principales</div>'
            f'{chips}</div>'
        )

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f1628 0%,#0a1428 100%);
            border:1px solid #1e3a6e;border-radius:10px;padding:1rem;
            max-width:{width + 60}px;margin:0 auto;">
  <div style="text-align:center;margin-bottom:0.6rem;padding-bottom:0.6rem;
              border-bottom:1px solid #1e3a6e;">
    <div style="color:#e2e8f0;font-size:1rem;font-weight:700;
                font-family:Rajdhani,sans-serif;margin-bottom:0.3rem;">{titulo}</div>
    <span style="display:inline-block;background:{turno_color};color:white;
                 padding:2px 9px;border-radius:4px;font-size:0.75rem;
                 font-weight:600;text-transform:uppercase;">Juegan {turno}</span>
  </div>
  <div style="display:flex;justify-content:center;background:#1a2540;
              padding:0.6rem;border-radius:8px;">
    {svg_raw}
  </div>
  {moves_html}
  <div style="margin-top:0.4rem;padding:0.4rem 0.6rem;
              background:rgba(10,14,26,0.9);border-radius:4px;
              border:1px solid #1e3a6e;">
    <div style="color:#94a3b8;font-size:0.62rem;text-transform:uppercase;
                letter-spacing:0.1em;margin-bottom:0.15rem;">FEN</div>
    <div style="color:#94a3b8;font-family:Courier New,monospace;font-size:0.68rem;
                word-break:break-all;">{fen}</div>
  </div>
</div>
""", unsafe_allow_html=True)




# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
LOGO_IMG = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAgAAAQABAAD/wAARCAREBEQDACIAAREBAhEB/9sAQwAIBgYHBgUIBwcHCQkICgwUDQwLCwwZEhMPFB0aHx4dGhwcICQuJyAiLCMcHCg3KSwwMTQ0NB8nOT04MjwuMzQy/9sAQwEJCQkMCwwYDQ0YMiEcITIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMAAAERAhEAPwDwKiiimIKKKKACkpaO1ABRRRQAUUUUAFFFFABRRQKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiimAlLRRQAUUUUAFFFFIA+lFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABR9KKKACiiimAUUUUAFFFFABRSUtAAaKKKQBRRRQAUUUUAFFFFABRRRQAUUUUwCijvRSAKKKKACiiigAoowKKACiiigAooooAKKKSmAtFFFIAooooASilooAKKOaKACiiigAooooAKKKKACiikoAWiiigAooooAKKKKACiiigAooooAKKKKACiiigAoNFFABRRRQAUUUUAFFFFABRRRQAUUtFMBKKKKQBRRRQAUUUUAHFFFFABRRRQAUUUUAFJS0UAFFFFABRRRQAUUUUAFFFFABRRRQAUd6KKACkpaKYBR2o7UUAFFGKKACiiigAooooAM0UlLQAUUUZpAJS0UUwCiiigAooopAFFGKKACiiigAooooAKKKKACiiigAooooAKKKKACgUUUwCiiigAooopAFFGaQUwFooooAKKKKACkpaM0gAUUZopgFFFFABRRRQAlLRRQAd6KKKACiiigAooooAKKKKAA0CiikAlLRRQAUUUUwCigGgmgA70UUUAFFGKKQBRRRTAKKKKACiiikAUZoopgFIKWikAUUUUAHFFFFABRRRQAUUUlMBaTFL2opAFFFFABRRRQAUlLRmgBOlLQeaKACiiigAooooAKKM0UAFFFFMAooopAFFHaigAooooAKKKKACiiigApOaWigAopKWgApM0tFABRRRQAUUUUAFFFFABRRRQAUUUlMBaKKKQBRRRQAUUlLQAUUUlAC0UUUAFFFFABRRRQAlLRRQAUUUUAFFFFACZpaKKACiiigAooooAKTNFLQAUUlFMBaKKKQBRRSUALRRSUwFooooAKKKKQBSUtFMAooooAKKKKACiiigAooooAKKKKADvRRRQAUGiikAUUDrR3pgFHeiikAUUUUwCjmiigAooopAFFFFACZopaSgBaKKKACiiimAUlLSUALRRRSAKKKKACiiigAooooAKKKKYBRRRSAKKKKACiiigAooooASlooFABRQaKACiiigAooooAKKKKACiiigAoopKACloxRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUGkoAKWkpaACiiigAooooAKKKSgBaKDRQAUUUUAFFJS0AFJSig0AFJS0UAJS0UUAFFFFABRSUtABRRRQAUUUUAFB60UUwCiiikAhpaKKACiiigAooooAKKKKAEpaKKACgdKKSmAtFJSikAUUUlAC0UUUAFFFFABRRSUALRRRTAKO1FFABRRRQAd6KKKACiiigANJS0UAFJS0UgCkopaYBRRRQAUlLRQAUZoooAKKKKADvRRRQAUUUUAFFFFIAopBS0AJS0UUwCikpaACiiikAUUGigAooooAKKKKACgUUUAFFIaKAFopKWgAooooAKO9HaigA4pKKWgAoopKAFo7UUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAJRS0UAJS0UUAFFFFABRRRQAUUUgoAWiiigAooooAKKKKACiiigAooooATpS0GkxQAtFFFABRSUtABRRRQAUUUlAC0lFFAC0UUUAFFFB6UAFFFJigBaKKKACiiigAooooAKKKM0AFFGaKACiiigAooooAKKKKACkpaO9AB2ooopgIaWiikAUUUUAFFJiloAKKKKACiiimAUUdKKACiiikAUGiigAooooAKKKKACiiigApKWimAUUUUAFFFFABQKKKAEpaKKAEpRRRQAUUUdaACijFFIBKKWimAUUUUAFFFFIAo70UUAFFFFABRRRQAUlLRQAUUUUAFJS0UAFFFFABRRRQAUUUUAFFFFABQaKKAEpaSloASloooAKKKKADtRRRQAUUUUAFFFFABRRRQAgNLSUUALRRRQAUUUUAGaM0cUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUlAC0UlKKACkpaKAEpaKKACjNFFABRRRQAUUUUwCiiigAoopKQC0UUUAFJilooATFLQKKYBRRRSAKKKKACjNFFABRRRTAKKKKQBRR3ooAM0UlLQAUUUUwCiiigAopKWgAooooAKKKKACiiigAooooAKKMUZoAKKKKACiiigAoooJoAKKMUlAC0UUUAFFFFABRRRSAKKO9BoADRRRTAKKKM0AFFFFIAozRRQAUUUUAFFFFABRSUtABRRRQAUmaWjFACdaWiigAzRRRQAUUUUAFFFFABRQKKACiiigAooooAO1FFFABR3oo70AFFFFABRRRQAlLRRQAUUUUAJS0Un06UALRRRQAUUlFAC0lLRQAlLRRQAUUUUAFFFFABRRSUALRRRQAUUUUAFFFFABRRQKACiiigBKWkooAWiiigAooooAKKSloASlozSUwFooopAFJS0UwCiiikAUUUUAFFFFABRRRQAUUUUAFFFIaAFooHWigAopKWgAooopgFFJS0AFJS0YoAKKKKQBRRRQAUUUUAFHaiigAzRRR3pgFFHeigAooooAKMUUUgCiiimAUUUlAC9qKKKACiikNABS0UCgAooooAKDRRQAUUYoPSgAooooAKKSloAO9GKKP5UAFFFFIAoo7UlAC0UUUAFFFJQAUtA6UUAFFFGaYBRRSUgFopKKAFpKKKAClpKWgAopKWgA7UUUUAFFFFABSUUtABSUtFABSUtJQAtFBooASloooAKKKKYCUtFFIAooooAO9IaWkNABS0UCgAooooAKKKKACiiigAo70UUAFJS0UAJS0UlAC0UUUAFFFFABRRRQAlLSUtABRRRQAUUUmKAFooooAKO9FFABRRRQAUUUUAFJRS5oAKKKKACiijigAooooASloopgFFFFABRRQaACj8aKKQBRRRTAO9FFFABSUUYoAWiiikAUlLRQAUUdaKYBRRRQAUUZooASloooAKKMUtACUYpaKAExRiloHSgAoopKAFooozQAnSijrS0AJQKXFJigAoozRmgAHWiiigA70UUUAFFFFABRRRQAUUUUAFFFFABQaKKADNFJilFIApKWigAooopgFFFFIBKWiigAooooAKKKKACkpaKACiiigAoNFFACCloooAKKO9FABRSUtABRRRQAUUUUAFFFFABRRRTAKKKKQBRRRQAUUdaKACiiigAooooAKTpS0UAJS0YooAKKKKACiiigAooooAKKKKACiiigAooooAKSlooAKKKO1ABRRRQAUUUUAITzS0lFAC0UUUAFFFFAB9aSlooAKKKKACiiigAoopKAFopKWgAooooAKKKKADFFFFMAooooAKKKKACiiigAooooAKKKKAAUUUUAFFAoNABQBRRQAuKKKSgBaKKOtABRR0pSKAEopRRjmnYQUUYoxRYLiUUuKKLBcSilxSUAFFFFKwwxRRRQAlFLikoAO1FHUUUAFFLSGgAooooAKKKKQBRR0opgFFFFABmiiikAUUUUAFFFFABRRRQAUUUUAFFFFABSdKXvSGgBaSlFGKACiikzQAtFFFABRRRQAd6KKKACiiigAooNJQAtFFFABRRRQAUUUUwEopaKQBRSd6U0AFFFFABRRRQAlLSUtABRRQetABRRRQAUUUUAFFFFABSUUtABSUUUALRRRQAUUUUAFJS0UAJS0UgoAWiiigAooooAKKKKACiiigAooooAKKBRQAUUUUAFFFFABRRRQAUGig0AIKWkFLTAOaKB1pKAFooopAFFIKWgApKWimAUUlLSASloooAKKKKACiiimAUc0CloAKKKKACiiimkAUoFFLTsIMUUoGaUKWYAZJPQDvTAaM07Fbum+DPEurhfsOhX8wPRhAVH5niuqsfgj42ugDJZW9qp/573Cgj8Bmj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IAoooNMAooopAFFFFABRRRQAUUUUwEooopALRRRQAUUUUAFFFFMAooooAKKSlpAFJS9qKYBRxRRQAUUUUgCikpaACiiigAooooABRRSUAFLSUtAAKKKKACik70c0ALRRRQAUUUUAJ3paKKACiiigAooooAKKKKACiiigApKWjBoAKKXaRSFTQAlLRSUAFFLRQAUUUUAJS0UlABS0UUAFFFFABRRRQAUUUUAFFFFABRRRQAUUlLQAUlLR2oAQUtFFABRRRQAUUUUAFFFFABRRRQAlLRRQAlFLRQAUUUUAFFFFABSUtFABRRRQAUUUUAFFJS0wCiiigAooopAFFFFACUtFFABRRRQAUUUUAFFFFACUtFFABRRQKACiiigAooooAKKKKACiiigAo70UUwCkpaKQB2ooooAKKKKACiiigBBS0UUAFFFFABRRRQAUUlKKACkpaKACiiigAooooAKKKKYBRRRzSAKKKKYBRSUtIAooooAKKKKACiiigAooooAKKKKACiikoAXNFJiloAKKKKACiiigAooooAKKKKACik6UUALQOtGK2/C9lb32sqtyN0UUbSsv97aOlVCLnJRXUU5KEXJ7INI8M6hqk8DfZ5EtXYBpiOAO5rUuPEVjp9y1pZaRZyWsZ2Fpk3PJjgkntVJ9ee/1+3nup5oLNJVAWA48tAf4R64q34tit5/JvYFtVklZ93kOMMufkYj1x1rtXLCEvZatb7fgcUm5ziqysnsrtfeWl0HTW8VfNGwsTa/bTAD225259Kgi8UWF5OLW70SySyc7AY0w6A8ZBrcSMf8ACRBf+oJg/wDfFcp4bggWS4ublITDFEW3OwyrDptHc1bThJKCSu/8jGLU4t1G3ZLrbq/x0ItV8MahYTTyLbu9mrfLMoyNvbNYmK2bHWL2z1ETJK77mw6MciQHqCKi8QW0Vrrd1FCpWMPkL/dBGcfrXNVhBpzg+p20pVFaNT7zKooxQK5joJZLd4oopGxiQErj2OKirT1Fcabphx1iY/8AjxrMFVJWZEXdBRRQakoKKKTNAC0UUUAFFFHegAooNGaACiijtQAUUUdqACiirD2hWwiut3+skZMY9AP8aaTewm7FeikpaQwooooAKKOaOtABRSc0tABQaKKAEFLRijFABRQaKACiiigAFFFFABRRRQAUUYoAoAKKKKACiiigAooozQAU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08RazFpp06PVb1bI8G3WdgmPTGentVBJ5kjkjSV0jkAEiq2A4ByAR35qKloAlW5nS3kgWaQQyMGeMN8rEdCR68moqSloAKKKKACiiigA7UUUUAFFFFABRRRQAUUUUAFFJS0AFFJS0AFFFFABRRRQAUUUDrQAUlL+tJQAtFFFACUtFFABQKKKACiiigAooxRQAUUUUAFFFFABSUtFABR3oooAKKKKACiiigAozRSYoAWikpaACiiigAoHWiigB8crxOroxDKcgjsa3B4plbbJPY2k9wvSZ4/m/GsCitIVZw0iyJ04z1kjQGs3q6r/AGl5x+05yT2+n0rRHiyeNXa3tLS3nkBDTpH8wz1x6Vz1JVRxFSN7PcmVCnLRoc7F2LZOTySab3opaxbvqarQKBxRRQApZiACSQOgPam0tFACUUtGKAEopaKAEpaKKACiiigAoozRQAUUUUAFIaWigAooooAKKTFLQAUUUUAIaKWkxQAtJS0mKADiiiigApaSloAKSlooAKKKKACiiigAooooAKKKKACiiigA70UUUAFFFFACUtFFABRRRQAUUUUAFFFFABRQaBQAUlLRQAUUUUAFFFFABRRRQAlLRRQAlFLRjmgAooooAKKKKACijNFABRRRQAUUnWloAKOKKMUAFFFFABRRRQAUUUUAHaiik6UALRRmigBKX8KKTNAC0UUUAFFFFABRSdaWgAFFFFABRRRQAUUUUAFFFFABRRRQAUlLRQAUUUUAFFFJTAWiiikAUUUUAFFFFABRRRQAUUUUAGKKKBQAUUUUAFFFFABRRRQAUhooNABRRS0AFFFHagAooPNJ0oAWikpaAEzS0UUAFFFFABRRRQAUUUlAC0UUUAFBoooAKKKKACiiigAooooAKKKKACiiigAoNFFACCloooAKKKKACiiigAooozQAUUUlAC0UUUAFFFFABRRRQAmaM0tFABRSUtABRRRQAUUUUAFFJRQAtFFFABRRRQAUUUUAFFFFABRRRTASloopAFFHeigAooooAKSlooAKKKSgBaSlooAKKKKAEzS0lFAC0UUUAFFGaKACiiigAooooASloooAKMUUUAFFFFABRRRQAUUUUAFFFFABRRRTAKKKKQCUtFFABSUtFABRRRQAUUUUAA6UUUlAC0UUUAFFFFABRRRQAUUUUAFFFJQAtFFFACUtFFABRRRQAUUUUAFBoNFABRRRQAlLSUtABRRRQAUUUUAFFFFABRRRTAKKKKQBRRRQAUUUUAFFFFABSUtFABRRRQAUUUUAHaiiigAooooAKKKKACiiigAopKWgAoxRRQAUUUlABS0lLQAlLRRQAUUUUAFFFFABSUtFABRRQaACikFLQAUUUlABS0UUAFFB6UUAFFFFABRRRQAUUUUAFFFFABRRRQAYpKXtSUALRRRQAUUUlABS0UlAC0UUUAFFHeigAoopKAFooooAKKKKACiiigBKKXiigAFFFFACUUtFABRRRQAlLRRQAlLRRQAlLQKKACiiigAooooAKKKKACiiigAooooAKKKKACijpQKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigBKWiigBKKWjtQAUUUUAFFFFABRRRQAUUUUwCiiikAlLRRQAUGig0AJS0gpaACkpaKACiijtQAUlLR1oAKKKKAAUHrRRTAKKDRQAUUUUgCiiigAopMUtABRRQBTAKKKKQBRRRQAUUUUAFFFFABRRQaACiiigAooooAKKKSgBaKKKACiiimAUUUUgCiiigAooooAKKKKACikooAKWiigAooooAKKKKACiiimAlLRRSAKKO9FABRRSUALRRRQAUUUUAFFFFABRRRQAUUUUAFFFAoAKO9FFABRRRQAUUUUAFJS0UAFFFGKACiiigAooooAKKKKACiiigAooooAKBRRQAUUUUAFFFFABRSUtMBM0daXFFIAooooAKKKKACiiigAooooAKMc0UUAFFFFABRRSUAGaWikoAWiiigAoopKADNLSUtABRRRQAUUUUAGaKKKACg0UUAIKWiigApKXtRQAmaWikoAWiikzTAWiikznigBaKKKACiiikAUUUUwCiiikAUUUUAFFIaUUAGKKKKACiiigAooooAKKKKACiikoAWiiigAooooAKM0UUAFFFFABSUtIaYC0UUUgCikopgLRRRSAKKKKACig0UAFFFFABRRRQAd6KO9FABRRRQAUUUUAFFFGaACiiigAooooAKKKKACiiigAooopgFFFFIAooooAKKKKACiiigAooooAKKKSgBaM0UUAFFJS0AFFFFABSUtFABRRRQAcUUUlAC0UCigApKWigAooooAKKKKACkpaKACkpaKACikpRQAUUUUAFFFFACUtFJQAtFFFABRRRQAcUUUlAC0UlKKACiiigAooooAKKKKACiikoAU0UUUAFFFJQAtFFJQAtFFFABg0UGigAooooAKKKSgBaKKKACiiimAUZoooAKKSlFABRSUtABRRRQAUlFLQACkpaKACiiigAopKWgAoopKQC0UUUAFFFFABRRSUALRRSUALRRRTAKSlopAFJS0UAFFFFABRRRQAlLRRQAUUUUwCkNLRSAKSlooAKSlooAKKKKACiiigAooooASloooAKKKKACij60UAFFFFABRRRQAUUUUAFFFFABRRQKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAopKWgANJS0UAJS0UUAFFFFABRRRQAUUUUAFFJS0AJRRS0AFJS0UAFFFFABRRRQAUUUUAJS0UUAFHaiigBKUUUUAJRS0UAJS0UUAFFFFABRRRQAUUUUAFFFFABQelFFAAOlFFJQAtFFFABSUtFABSUvaigAooooAKO9FFMAo7UUUgEpaKKYBRRRQAGiiigBKWiigAooooAKQ0tFIBKWiigAooooAKKKKACiiimAUlL3opAFFAo70AFBoooAKKKKAEo70tJQAUtFFABRRRQAUUUUAFFFFAAaKKKACikpaACkpeKKACiiigAooooAKKKKACiiimAUd6KKQAaKKKAAdKKKKACiiigAooooAKKSloAKKKKACiiigAoowKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooozQAUUUUwCiiikAUUUYoAKKSloAKKKKAEPWloxzRQAUmKWigA70d6O9FABRmkNFAC0UUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRiikoAWiiigAooooAKKKKACiiigA70UUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUwCiiikAUUZooAKKKKACiiimAUUUUgCiiigAooooAKKKKACijFFABRRRQAUUUUwCk70tJ3pALRRRQAUUUUAFFFGKACiiigAooooAKKKKACiiimAUUUUgCiiigAooooAKKKKACiiigAooooAKKKKACiiigA4oopKACloo70AHaiiigAooooABSUtFAAKXNJRQAUUUUAFFFFABRRRQAlLRRQAUUUUAFFFFABRRRQAUUlLQAUUUUAFFFFABRSUvegAooooAKKKKACikpaACkzS0UAJRS0UAFFFFABQaKKACiiigAoFFFABmiiigAoo7UUAFFFFABRRRQAUlLRQAgpaKKACiiigAooooAKKKKACiiigAooooAKTNLRQAUUlLQAUUUUAFFFFMAooopAFFFJQAuMUUUUAFFFFABRRRTAKSlooAKKKKACiiikAUUUUAFFFFABRRRQAUUUUAFJS0UwCkzS0UgCiiigAopKWgAooooAKKKKACiiigAo96KKYBRRRSAKKKKACiiigAooooAKO9FFAB3ooooAKKKKACiiigAooo/CgAooooAKKKKACiiigBKWiigAooooAKKSloAKKKKACkpaKACkpaKACkpaKACiiigAooooAMUlLRQAUUUUAFFFFABQetFJQAppBS0UAFFFFABRRSUALRRRQAUd6KKAA9aKKKACiiigAooooAKKKKACiiigApKWigApKWigAooooAKKKKACiiigAooooAKO1FFACUtFFABRRRQAUUUUAFFFFABRRRTAKSlopAFFFFABRRRQAUUUUAFGKKKACg0UUAIOtLRRQAUUUUAFFFFMANFFFIAooooAKQ9KKWgAopBS0AFFFFABRRRQAUCkpRQAUUUUAFFFFABRRRQAUUUhoAWikpaACiiigAooooAKSlooASloooAKM0UUAFFFFMBKWiikAUUUUAFFFFABiiiigApKWigAooooAKKKKACiig9aAAUtJRQAHrRQetFABRRRQAUlLSUALRRRQAUUUUAFBooNAAOlAoHSgUAFFFFABRRRTAKKKKQBRRRQAUGgUGgBO9LSd6WgAooooAKO1FHagAooooAKKKKACiiigBKWkpaACiiigAooopgFFFFIAooooAKKKKACiiigAooooAKKKKACiiigAooooAKSlpKAFooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACkNLSGgBRSUopKBi0UUUCCiiigAooooASiiigApaSloAQUtIKWgBKWkpaACiiigAooooAKKKKACkpaSgBaKKKACkNLSGgBaKKKACiiigApDS0hoAUUUCigAooooAKKKKACiiimAUUUUgAdKQ9KUdKQ9KAFpDS0hpgLQOtFA60AFFFFIBBS0gpaACiiigAooooAKKKKYH/9k="

st.markdown(f"""
<div class="header-bar">
    <div style="flex-shrink:0;">
        <img src="{LOGO_IMG}" alt="Logo" style="width:140px;height:140px;object-fit:contain;">
    </div>
    <div style="flex:1;">
        <h1>Lichess Opening Trainer Pro</h1>
        <div class="header-sub">AI Powered &nbsp;|&nbsp; Deep Opening Knowledge &nbsp;|&nbsp; Maximum Precision</div>
        <div>
            <span class="hbadge">327K posiciones</span>
            <span class="hbadge">Stockfish 16</span>
            <span class="hbadge">K-means K=3</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PANEL DE CONFIGURACIÓN COLAPSABLE
# ══════════════════════════════════════════════════════════════════════════════
if "panel_visible" not in st.session_state:
    st.session_state.panel_visible = True

lbl_toggle = "▲  Ocultar configuración" if st.session_state.panel_visible else "▼  Configurar análisis"
st.markdown('<div class="btn-toggle">', unsafe_allow_html=True)
if st.button(lbl_toggle, key="toggle_panel"):
    st.session_state.panel_visible = not st.session_state.panel_visible
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

_u = st.session_state.get("luser",""); _t = st.session_state.get("ltoken","")
_mx = st.session_state.get("lmax",50); _pl = st.session_state.get("lplan",True); _st = st.session_state.get("lstudy","")
analizar_btn = False

if st.session_state.panel_visible:
    st.markdown('<div class="config-wrap">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns([2.2,2.2,0.9,1.5,1.2])
    with c1: lichess_user  = st.text_input("Usuario de Lichess", value=_u, placeholder="ej: MagnusCarlsen", key="iu")
    with c2: lichess_token = st.text_input("API Key de Lichess",  value=_t, type="password", placeholder="lip_xxxxxxxxxxxx", key="it")
    with c3: max_partidas  = st.number_input("Partidas", min_value=10, max_value=500, value=_mx, step=10, key="im")
    with c4:
        study_id = st.text_input("ID Estudio Lichess", value=_st, placeholder="8 caracteres", key="is_")
        if study_id and len(study_id) == 8:
            st.markdown(f'<div style="font-size:0.68rem;color:#8b7040;font-style:italic;">lichess.org/study/{study_id}</div>', unsafe_allow_html=True)
    with c5:
        mostrar_plan = st.checkbox("Plan de estudio", value=_pl, key="ip")
        st.markdown("<div style='height:0.15rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        analizar_btn = st.button("♟  Analizar repertorio", disabled=(not lichess_user or not lichess_token), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.session_state.luser=lichess_user; st.session_state.ltoken=lichess_token
    st.session_state.lmax=max_partidas; st.session_state.lplan=mostrar_plan; st.session_state.lstudy=study_id
else:
    lichess_user=_u; lichess_token=_t; max_partidas=_mx; mostrar_plan=_pl; study_id=_st


# ══════════════════════════════════════════════════════════════════════════════
# FLUJO DE ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════════
if analizar_btn:
    import berserk
    status = st.empty()

    with st.spinner("Cargando base teórica..."):
        try:
            theory_positions = cargar_teoria()
        except Exception as e:
            st.error(f"No se pudo cargar la base teórica: {e}"); st.stop()

    # Reset contadores de diagnóstico
    st.session_state["sf_errors"] = []
    st.session_state["n_eval_ok"] = 0

    with st.spinner("Iniciando Stockfish..."):
        try:
            sf = crear_stockfish()
        except Exception as e:
            st.error(f"No se pudo iniciar Stockfish: {e}"); st.stop()

    status.info(f"Consultando perfil de {lichess_user}...")
    try:
        client = berserk.Client(berserk.TokenSession(lichess_token))
        perfil = client.users.get_public_data(lichess_user)
        perfs  = perfil.get("perfs",{})
        rating = (perfs.get("blitz",{}).get("rating",0)
               or perfs.get("rapid",{}).get("rating",0)
               or perfs.get("bullet",{}).get("rating",0))
        if not rating: st.warning("Sin rating activo."); st.stop()
        st.session_state.rating = rating
    except Exception as e:
        st.error(f"Error Lichess: {e}"); st.stop()

    status.info(f"Descargando {max_partidas} partidas...")
    try:
        gen = client.games.export_by_player(lichess_user, max=max_partidas, opening=True, as_pgn=True)
        games = []
        for g in gen:
            if isinstance(g,dict): continue
            obj = chess.pgn.read_game(io.StringIO(g))
            if obj: games.append(obj)
            if len(games) >= max_partidas: break
        if not games: st.error("No se encontraron partidas."); st.stop()
    except Exception as e:
        st.error(f"Error descarga: {e}"); st.stop()

    status.info(f"Analizando {len(games)} partidas con Stockfish...")
    pb = st.progress(0)
    df_nuevos = analizar_partidas(games, lichess_user, rating, sf, theory_positions, pb)
    pb.empty()
    if df_nuevos.empty: st.warning("Sin resultados analizables."); st.stop()

    COLS_BASE = ["Game_ID","Usuario","Rating_Usuario","Apertura","Color","Fin_Teoria","ACL_Post_Teo","Victoria"]
    if os.path.exists(FILENAME_ML):
        df_h  = pd.read_csv(FILENAME_ML)
        cols_h = [c for c in COLS_BASE if c in df_h.columns]
        df_acc = (pd.concat([df_h[cols_h], df_nuevos[COLS_BASE]])
                  .drop_duplicates(subset=["Game_ID"], keep="first").reset_index(drop=True))
    else:
        df_acc = df_nuevos[COLS_BASE].copy()

    status.info("Calculando features ML...")
    df_enr = enriquecer_dataset(df_acc)
    df_enr.to_csv(FILENAME_ML, index=False)

    df_usr = df_enr[df_enr["Usuario"] == lichess_user].copy()
    st.session_state.df_dash         = generar_dashboard_data(df_usr)
    st.session_state.df_usuario_data = df_usr
    st.session_state.rating          = rating

    if mostrar_plan and os.path.exists(RECURSOS_PATH) and os.path.exists(KM_PATH):
        status.info("Generando plan de estudio...")
        df_rec = pd.read_csv(RECURSOS_PATH)
        st.session_state.plan = generar_plan_estudio(df_usr, df_rec, rating, lichess_token=lichess_token)
    else:
        st.session_state.plan = []

    bl = obtener_todos_blunders(lichess_user)
    status.success(f"✓ Análisis completado — {len(df_usr)} partidas · {rating} Elo · {len(bl)} blunder(s) detectado(s)")


# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.get("df_dash") is not None:
    df_dash = st.session_state.df_dash
    plan    = st.session_state.get("plan", [])
    rating  = st.session_state.get("rating", 0)
    df_usr  = st.session_state.get("df_usuario_data", pd.DataFrame())
    lichess_user  = st.session_state.get("luser","")
    lichess_token = st.session_state.get("ltoken","")
    study_id      = st.session_state.get("lstudy","")

    render_profesor_card(rating, df_usr)

    # ── Profesor Virtual Animado ──────────────────────────────────────────
    if st.session_state.get("mostrar_profesor_virtual", True):
        df_dash_v = st.session_state.get("df_dash")
        if df_dash_v is not None and not df_dash_v.empty:
            acc_media_v = df_dash_v["Accuracy"].mean() if "Accuracy" in df_dash_v.columns else 0
            # Determinar nivel dominante del jugador para el profesor
            _res_v = asignar_nivel_apertura(st.session_state.get("df_usuario_data", pd.DataFrame()))
            if not _res_v.empty and "nivel_apertura" in _res_v.columns:
                nivel_dominante = _res_v["nivel_apertura"].value_counts().idxmax()
            else:
                if rating >= 1800: nivel_dominante = "dominio"
                elif rating >= 1400: nivel_dominante = "desarrollo"
                else: nivel_dominante = "sin_base"
            render_profesor_virtual(nivel_dominante, rating, acc_media_v)

    tab1,tab2,tab3 = st.tabs(["  ♙  Dashboard  ","  📚  Plan de Estudio  ","  ⚠  Blunders  "])

    with tab1:
        acc_m = df_dash["Accuracy"].mean(); teo_m = df_dash["Avg_Teoria"].mean()
        n_ap  = len(df_dash);               wr_g  = df_dash["Win_Rate"].mean()
        c1,c2,c3,c4 = st.columns(4)
        with c1: render_metric("Precisión media",  f"{acc_m:.1f}%", "post-apertura")
        with c2: render_metric("Teoría media",     f"{teo_m:.1f}j", "jugadas seguidas")
        with c3: render_metric("Aperturas",        str(n_ap),        "líneas distintas")
        with c4: render_metric("Win rate",         f"{wr_g*100:.0f}%","victorias globales")
        render_gold_divider()

        for color_p in ["Blancas","Negras"]:
            sym = "♙" if color_p == "Blancas" else "♟"
            st.markdown(f"### {sym} {color_p}")
            subset = df_dash[df_dash["Color"] == color_p].copy()
            if subset.empty: st.caption("Sin datos."); continue
            cr,cd,cf = st.columns(3)
            with cr:
                render_section_label("⚠ Riesgo — estudiar o cambiar")
                en_riesgo = subset[subset["es_riesgo"] == True].sort_values("Risk_Index",ascending=False).head(4)
                if en_riesgo.empty:
                    st.markdown('<div style="font-size:0.83rem;color:#22c55e;padding:0.4rem 0;">✓ Sin aperturas en zona de riesgo</div>', unsafe_allow_html=True)
                else:
                    for _,r in en_riesgo.iterrows():
                        nota = "Precisión por debajo de tu media" if r["Accuracy"] >= 75 else ""
                        render_opening_card(r["Apertura"],r["Accuracy"],r["Avg_Teoria"],int(r["Volumen"]),r["Win_Rate"],"risk",nota)
            with cd:
                render_section_label("✦ Dominio teórico")
                excl_ap  = en_riesgo["Apertura"].tolist() if not en_riesgo.empty else []
                top_p = subset[subset["es_dominio"] & ~subset["Apertura"].isin(excl_ap)].sort_values("Score_Prep",ascending=False).head(4)
                if top_p.empty: st.caption("Sin líneas de dominio relativo.")
                else:
                    for _,r in top_p.iterrows(): render_opening_card(r["Apertura"],r["Accuracy"],r["Avg_Teoria"],int(r["Volumen"]),r["Win_Rate"],"dominio")
            with cf:
                render_section_label("◈ Feeling natural")
                top_f = subset[subset["Score_Feeling"] > 0].sort_values("Score_Feeling",ascending=False).head(4)
                if top_f.empty: st.caption("Sin líneas de feeling.")
                else:
                    for _,r in top_f.iterrows(): render_opening_card(r["Apertura"],r["Accuracy"],r["Avg_Teoria"],int(r["Volumen"]),r["Win_Rate"],"feeling")
            render_gold_divider()

    with tab2:
        plan_vacio = not plan or (not plan.get("Blancas") and not plan.get("Negras"))
        if plan_vacio:
            st.info("Plan no disponible. Necesitas los PKL de clustering y el catálogo de recursos.")
        else:
            ICONO_N={"sin_base":"⚠","desarrollo":"↑","dominio":"✓"}
            DESC_N ={"sin_base":"Necesita trabajo urgente","desarrollo":"En progreso — pulir teoría","dominio":"Dominada — ampliar variantes"}
            COLOR_N={"sin_base":"#ef4444","desarrollo":"#f59e0b","dominio":"#22c55e"}

            def render_plan_entries(entries):
                for e in entries:
                    nv=e["nivel"]; clr=COLOR_N.get(nv,"#60a5fa"); tier=NIVEL_A_TIER.get(nv,"").upper()
                    st.markdown(f"""
                    <div class="plan-card {nv}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                            <div>
                                <div style="font-family:'Rajdhani',sans-serif;font-size:1rem;font-weight:700;
                                            color:#e2e8f0;letter-spacing:0.04em;">
                                    {ICONO_N.get(nv,"·")} {e['apertura']}
                                </div>
                                <div style="font-size:0.75rem;color:{clr};margin-top:0.15rem;">{DESC_N.get(nv,"")}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-family:'Rajdhani',sans-serif;font-size:1.5rem;font-weight:700;color:{clr};">{e['acc_adj']:.1f}%</div>
                                <div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:0.1em;">precisión</div>
                            </div>
                        </div>
                        <div style="display:flex;gap:1.5rem;margin-top:0.5rem;font-size:0.72rem;color:#475569;flex-wrap:wrap;">
                            <span>Teo: {e['teo_med']:.1f}j</span>
                            <span>Partidas: {e['n_partidas']}</span>
                            <span>WR: {e['win_rate']:.0f}%</span>
                            <span style="background:rgba(59,130,246,0.15);color:#60a5fa;
                                         border:1px solid rgba(59,130,246,0.3);padding:1px 7px;
                                         border-radius:3px;font-size:0.6rem;text-transform:uppercase;">{tier}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)

                    # ── Material en dos columnas: Gratuito | De pago ───────
                    recursos_free = e.get("recursos_free", [])
                    recursos_paid = e.get("recursos_paid", [])
                    # Retrocompatibilidad: si no hay claves separadas, usar 'recursos'
                    if not recursos_free and not recursos_paid:
                        todos = e.get("recursos", [])
                        recursos_free = [r for r in todos if r.get("is_free", 1) != 0]
                        recursos_paid = [r for r in todos if r.get("is_free", 0) == 0]

                    hay_algo = recursos_free or recursos_paid
                    if hay_algo:
                        col_free, col_paid = st.columns(2, gap="small")
                        with col_free:
                            st.markdown(
                                '<div class="res-col-header free">📹 Material gratuito</div>',
                                unsafe_allow_html=True
                            )
                            if recursos_free:
                                for rec in recursos_free:
                                    render_resource(rec)
                            else:
                                ap_quoted = requests.utils.quote(e["apertura"])
                                st.markdown(
                                    '<div class="res-empty">Sin resultados en la base. '
                                    f'<a href="https://lichess.org/study/search?q={ap_quoted}"'
                                    ' target="_blank" style="color:#60a5fa">'
                                    'Buscar en Lichess Studies ↗</a></div>',
                                    unsafe_allow_html=True
                                )
                        with col_paid:
                            st.markdown(
                                '<div class="res-col-header paid">💳 Material de pago</div>',
                                unsafe_allow_html=True
                            )
                            if recursos_paid:
                                for rec in recursos_paid:
                                    render_resource(rec)
                            else:
                                st.markdown(
                                    '<div class="res-empty">Sin cursos de pago en el catálogo '
                                    'para esta apertura.</div>',
                                    unsafe_allow_html=True
                                )
                    else:
                        st.markdown(
                            '<div style="font-size:0.75rem;color:#334155;font-style:italic;margin-bottom:0.5rem;">'
                            'Sin recursos específicos en el catálogo.</div>',
                            unsafe_allow_html=True
                        )
                    render_gold_divider()

            col_b, col_n = st.columns(2)
            with col_b:
                st.markdown('<div class="color-section">', unsafe_allow_html=True)
                st.markdown('<div class="color-section-title">♙ Blancas</div>', unsafe_allow_html=True)
                entries_b = plan.get("Blancas", [])
                if entries_b:
                    render_plan_entries(entries_b)
                else:
                    st.caption("Sin datos suficientes para Blancas.")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_n:
                st.markdown('<div class="color-section">', unsafe_allow_html=True)
                st.markdown('<div class="color-section-title">♟ Negras</div>', unsafe_allow_html=True)
                entries_n = plan.get("Negras", [])
                if entries_n:
                    render_plan_entries(entries_n)
                else:
                    st.caption("Sin datos suficientes para Negras.")
                st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        # ── Diagnóstico Stockfish ─────────────────────────────────────────
        sf_errors = st.session_state.get("sf_errors", [])
        if sf_errors:
            with st.expander(f"⚠️ Stockfish tuvo {len(sf_errors)} error(es) durante el análisis — click para ver", expanded=True):
                st.warning(
                    "Stockfish falló en algunas evaluaciones. Esto puede causar que no se detecten blunders. "
                    "Posibles causas: ruta incorrecta del ejecutable, FEN inválido, o proceso caído."
                )
                for err in sf_errors[:10]:
                    st.code(err, language=None)
                if len(sf_errors) > 10:
                    st.caption(f"... y {len(sf_errors)-10} errores más")
        elif st.session_state.get("df_dash") is not None:
            # Análisis completado sin errores de SF
            n_eval_ok = st.session_state.get("n_eval_ok", 0)
            if n_eval_ok > 0:
                st.success(f"✅ Stockfish funcionó correctamente ({n_eval_ok} evaluaciones realizadas)")
            else:
                st.warning(
                    "⚠️ No se realizaron evaluaciones de Stockfish. "
                    "Verifica que la ruta del ejecutable es correcta: "
                    f"`{STOCKFISH_PATH}`"
                )

        st.markdown('<div style="font-size:0.82rem;color:#8b7040;margin-bottom:0.8rem;">Posiciones con pérdida >100cp. Se guarda el peor error de cada partida.</div>', unsafe_allow_html=True)

        # ── Siempre leer TODOS los blunders, nunca filtrar por Subido ────────
        blunders_todos = obtener_todos_blunders(lichess_user if lichess_user else None)

        if blunders_todos.empty:
            st.info("No se detectaron blunders (pérdida >100cp) en las partidas analizadas.")
        else:
            # ── Lista de blunders (siempre visible) ───────────────────────
            ya_subidos = int(blunders_todos["Subido"].sum()) if "Subido" in blunders_todos.columns else 0
            pendientes = len(blunders_todos) - ya_subidos

            # Inicializar estado del tablero de blunders
            if "tablero_blunder_idx" not in st.session_state:
                st.session_state.tablero_blunder_idx = None

            for bl_idx, (_, row) in enumerate(blunders_todos.iterrows()):
                lcp       = float(row["Loss_CP"])
                cls       = "severe" if lcp > 200 else "warn"
                subido    = bool(row.get("Subido", False))
                badge     = ('<span style="font-size:0.6rem;color:#22c55e;'
                             'border:1px solid rgba(34,197,94,0.4);padding:1px 5px;'
                             'border-radius:2px;margin-left:0.5rem;">✓ enviado</span>'
                             if subido else '')
                col_bl, col_btn = st.columns([8, 1])
                with col_bl:
                    st.markdown(
                        f'<div class="bl-row">'
                        f'<span class="bl-badge {cls}">-{lcp:.0f}cp</span>'
                        f'<span style="flex:1;color:#cbd5e1;">{row["Apertura"]}{badge}</span>'
                        f'<span style="color:#8b7040;font-size:0.75rem;">{row["Fecha"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with col_btn:
                    fen_val = str(row.get("FEN", "")).strip()
                    if fen_val:
                        btn_label = "✕" if st.session_state.tablero_blunder_idx == bl_idx else "♟"
                        if st.button(btn_label, key=f"ver_blunder_{bl_idx}", help="Ver posición en tablero"):
                            if st.session_state.tablero_blunder_idx == bl_idx:
                                st.session_state.tablero_blunder_idx = None
                            else:
                                st.session_state.tablero_blunder_idx = bl_idx
                            st.rerun()

                # Mostrar tablero si está activo para este blunder
                if st.session_state.tablero_blunder_idx == bl_idx:
                    fen_val = str(row.get("FEN", "")).strip()
                    if fen_val:
                        if len(fen_val.split()) == 4:
                            fen_val += " 0 1"
                        col_t1, col_t2, col_t3 = st.columns([1, 3, 1])
                        with col_t2:
                            render_tablero_profesional(
                                fen=fen_val,
                                apertura_nombre=f"{row['Apertura']} (−{lcp:.0f}cp)",
                                width=360
                            )

            render_gold_divider()

            # ── Sección de subida ─────────────────────────────────────────
            if study_id and len(study_id) == 8:
                st.markdown(
                    f'<div style="font-size:0.82rem;color:#3a2808;margin-bottom:0.8rem;">'
                    f'Estudio: <a href="https://lichess.org/study/{study_id}" target="_blank" '
                    f'style="color:#8b6914;">lichess.org/study/{study_id}</a>'
                    f' &middot; {len(blunders_todos)} blunder(s) detectado(s)'
                    f'</div>',
                    unsafe_allow_html=True
                )

                col_sub1, col_sub2 = st.columns([2, 1], gap="small")

                with col_sub1:
                    # Botón principal: sube solo los pendientes (Subido=False)
                    if pendientes > 0:
                        st.markdown('<div class="btn-upload">', unsafe_allow_html=True)
                        if st.button(f"📤  Subir {pendientes} blunder(s) pendiente(s)", key="btn_subir"):
                            with st.spinner("Subiendo a Lichess..."):
                                res = subir_blunders_pendientes(study_id, lichess_token, lichess_user)
                            if res["errores"] == 0:
                                st.success(f"✓ {res['subidos']} posición(es) subida(s).")
                            else:
                                st.warning(f"Subidos: {res['subidos']} · Errores: {res['errores']}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.success(f"✓ Todos los blunders ya están en el estudio ({ya_subidos} posiciones).")

                with col_sub2:
                    # Botón secundario: re-subir TODO (útil si se borró el estudio)
                    if st.button("🔄  Re-subir todo", key="btn_resubir",
                                 help="Resetea el estado de envío y vuelve a subir todos los blunders. "
                                      "Útil si borraste el estudio de Lichess."):
                        resetear_blunders_usuario(lichess_user)
                        with st.spinner("Re-subiendo todos los blunders..."):
                            res = subir_blunders_pendientes(study_id, lichess_token, lichess_user)
                        if res["errores"] == 0:
                            st.success(f"✓ {res['subidos']} posición(es) re-subida(s).")
                        else:
                            st.warning(f"Subidos: {res['subidos']} · Errores: {res['errores']}")
            else:
                st.info("Introduce el ID de tu estudio en el panel superior para subir blunders a Lichess.")

elif not analizar_btn:
    st.markdown("""
    <div style="text-align:center;padding:5rem 2rem;">
        <div style="font-size:4rem;opacity:0.25;margin-bottom:1.5rem;">♟</div>
        <div style="font-family:'Playfair Display',serif;font-size:1.1rem;color:#6a5a30;max-width:380px;margin:0 auto;line-height:1.8;">
            Introduce tu usuario y clave de API en el panel superior para comenzar el análisis de repertorio.
        </div>
    </div>
    """, unsafe_allow_html=True)
