"""
DEMO COMPLETO - Profesor Virtual + Tablero de Ajedrez
Muestra cómo se ven ambos componentes integrados en la aplicación
"""

import streamlit as st
from profesor_virtual import render_profesor_virtual
from tablero_ajedrez import render_tablero_ajedrez

st.set_page_config(
    page_title="Lichess Opening Trainer Pro - Demo Enhanced",
    page_icon="♟",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════
# CSS BASE (simplificado del app_16.py)
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp {
    background-color: #080b12;
    background-image: repeating-conic-gradient(#0d1220 0% 25%, #0a0e1a 0% 50%);
    background-size: 56px 56px;
}

.op-card {
    background: #0f1628;
    border: 1px solid #1e3a6e;
    border-left: 3px solid #3b82f6;
    border-radius: 4px;
    padding: 0.75rem 0.9rem;
    margin-bottom: 0.4rem;
    transition: all 0.2s;
}

.op-card:hover {
    background: #1a2540;
    transform: translateX(4px);
}

.op-card.dominio { border-left-color: #22c55e; }
.op-card.feeling { border-left-color: #a855f7; }
.op-card.risk { border-left-color: #ef4444; }

.op-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: #e2e8f0;
}

.op-stats {
    font-size: 0.7rem;
    color: #475569;
    margin-top: 0.15rem;
}

.op-acc {
    font-size: 1.2rem;
    font-weight: 700;
    float: right;
    margin-top: -1.5rem;
}

.acc-hi { color: #22c55e; }
.acc-mid { color: #f59e0b; }
.acc-lo { color: #ef4444; }

.demo-header {
    background: linear-gradient(135deg, #0a0e1a 0%, #0f1628 60%, #0a0e1a 100%);
    padding: 2rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    border: 1px solid #1e3a6e;
}

.demo-title {
    color: #e2e8f0;
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.demo-subtitle {
    color: #94a3b8;
    font-size: 1.1rem;
}

.feature-card {
    background: rgba(15, 22, 40, 0.8);
    border: 1px solid #1e3a6e;
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1rem 0;
}

.feature-title {
    color: #60a5fa;
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.feature-desc {
    color: #cbd5e1;
    font-size: 0.9rem;
    line-height: 1.6;
}

.stButton > button {
    background: #2563eb !important;
    color: white !important;
    border: 1px solid #3b82f6 !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}

.stButton > button:hover {
    background: #3b82f6 !important;
    box-shadow: 0 0 12px rgba(59,130,246,0.4) !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="demo-header">
    <div class="demo-title">♟️ Lichess Opening Trainer Pro</div>
    <div class="demo-subtitle">✨ Enhanced Edition - Con Profesor Virtual y Tablero Interactivo</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SECCIÓN 1: DEMO DEL PROFESOR VIRTUAL
# ══════════════════════════════════════════════════════════════
st.markdown("## 👨‍🏫 Función 1: Profesor Virtual Animado")

st.markdown("""
<div class="feature-card">
    <div class="feature-title">🎓 ¿Qué hace?</div>
    <div class="feature-desc">
        El profesor virtual aparece automáticamente después del análisis con un mensaje
        personalizado según tu nivel (Principiante / Intermedio / Experto). Incluye:
        <br><br>
        • 📊 Análisis de tu perfil (Rating + Accuracy)<br>
        • 💡 Consejos específicos según tu nivel<br>
        • 🎨 Animaciones suaves (slide-in + bounce)<br>
        • ⏰ Auto-cierre después de 15 segundos<br>
        • ❌ Botón manual para cerrar
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    demo_nivel = st.selectbox(
        "Nivel del jugador",
        ["sin_base", "desarrollo", "dominio"],
        format_func=lambda x: {
            "sin_base": "🎓 Principiante",
            "desarrollo": "👨‍🏫 Intermedio",
            "dominio": "🏆 Experto"
        }[x]
    )

with col2:
    demo_rating = st.number_input("Rating", value=1650, step=50, min_value=800, max_value=3000)

with col3:
    demo_accuracy = st.number_input("Accuracy %", value=72.5, step=1.0, min_value=0.0, max_value=100.0)

if st.button("🎬 Mostrar Profesor Virtual", type="primary"):
    render_profesor_virtual(demo_nivel, demo_rating, demo_accuracy)

st.markdown("---")

# ══════════════════════════════════════════════════════════════
# SECCIÓN 2: DEMO DE APERTURAS CON TABLERO
# ══════════════════════════════════════════════════════════════
st.markdown("## ♟️ Función 2: Tablero de Ajedrez Interactivo")

st.markdown("""
<div class="feature-card">
    <div class="feature-title">🎯 ¿Qué hace?</div>
    <div class="feature-desc">
        Cada apertura en tu dashboard tiene un botón para ver la posición en un tablero
        interactivo. Incluye:
        <br><br>
        • ♟️ Tablero visual con la posición exacta (FEN)<br>
        • 🔄 Flip del tablero para ver desde ambos lados<br>
        • 💡 Jugadas principales recomendadas<br>
        • 📋 Código FEN para referencia<br>
        • 🎨 Diseño integrado con el estilo de la app
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 📊 Dashboard de Aperturas (Simulado)")

# Datos de ejemplo
aperturas_ejemplo = [
    {
        "apertura": "Sicilian Defense, Najdorf Variation",
        "volumen": 15,
        "accuracy": 78.5,
        "teoria": 12.3,
        "win_rate": 0.65,
        "categoria": "dominio",
        "fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
        "jugadas": ["Be3", "Be2", "f3", "Qd2", "g4"]
    },
    {
        "apertura": "French Defense, Winawer Variation",
        "volumen": 8,
        "accuracy": 65.2,
        "teoria": 8.5,
        "win_rate": 0.48,
        "categoria": "feeling",
        "fen": "rnbqk2r/ppp2ppp/4pn2/3p4/1b1PP3/2N2N2/PPP2PPP/R1BQKB1R w KQkq - 0 5",
        "jugadas": ["Bd3", "Qg4", "a3", "Nf3"]
    },
    {
        "apertura": "Queen's Gambit Declined",
        "volumen": 12,
        "accuracy": 58.1,
        "teoria": 9.2,
        "win_rate": 0.42,
        "categoria": "risk",
        "fen": "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4",
        "jugadas": ["cxd5", "Bg5", "Nf3", "e3"]
    }
]

# Inicializar session state
if "tablero_activo" not in st.session_state:
    st.session_state.tablero_activo = False
if "apertura_actual" not in st.session_state:
    st.session_state.apertura_actual = None

# Renderizar cards
for idx, ap in enumerate(aperturas_ejemplo):
    col1, col2 = st.columns([5, 1])
    
    with col1:
        acc_class = "acc-hi" if ap["accuracy"] >= 75 else "acc-mid" if ap["accuracy"] >= 65 else "acc-lo"
        
        st.markdown(f"""
        <div class="op-card {ap['categoria']}">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <div class="op-name">{ap['apertura']}</div>
                    <div class="op-stats">
                        {ap['volumen']} partidas · Teoría: {ap['teoria']:.1f} · WR: {ap['win_rate']*100:.0f}%
                    </div>
                </div>
                <div class="op-acc {acc_class}">{ap['accuracy']:.0f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("♟️", key=f"ver_pos_{idx}", help="Ver posición"):
            st.session_state.tablero_activo = True
            st.session_state.apertura_actual = idx
            st.rerun()

# Mostrar tablero si está activo
if st.session_state.tablero_activo and st.session_state.apertura_actual is not None:
    st.markdown("---")
    st.markdown("### 🎯 Posición de la Apertura Seleccionada")
    
    ap_sel = aperturas_ejemplo[st.session_state.apertura_actual]
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        render_tablero_ajedrez(
            fen=ap_sel["fen"],
            apertura_nombre=ap_sel["apertura"],
            jugadas_siguientes=ap_sel["jugadas"],
            orientation="white"
        )
    
    if st.button("✕ Cerrar Tablero", type="secondary"):
        st.session_state.tablero_activo = False
        st.session_state.apertura_actual = None
        st.rerun()

# ══════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div class="feature-card">
    <div class="feature-title">🎨 Beneficios de las Mejoras</div>
    <div class="feature-desc">
        <strong>Visual:</strong> Animaciones suaves, diseño moderno, feedback visual inmediato<br>
        <strong>Funcional:</strong> Tablero interactivo, profesor virtual contextual, navegación intuitiva<br>
        <strong>UX:</strong> Menos clicks, más información visual, experiencia más profesional<br>
        <strong>Tiempo de implementación:</strong> ~20 minutos copiando los componentes
    </div>
</div>
""", unsafe_allow_html=True)

st.info("💡 **Tip:** Esta es una demo. En la versión real, las posiciones FEN vienen de tus partidas analizadas.")
