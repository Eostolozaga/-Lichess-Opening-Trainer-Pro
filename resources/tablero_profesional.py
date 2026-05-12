"""
Tablero de Ajedrez Profesional - Versión Mejorada
Usa python-chess con SVG nativo de alta calidad
"""

import streamlit as st
import chess
import chess.svg
from io import StringIO

def render_tablero_profesional(fen, apertura_nombre="", jugadas_siguientes=None, width=400):
    """
    Renderiza tablero de ajedrez usando python-chess (SVG de alta calidad).
    
    Args:
        fen: Posición FEN
        apertura_nombre: Nombre de la apertura
        jugadas_siguientes: Lista de jugadas en notación algebraica
        width: Ancho del tablero en pixels
    """
    
    # Crear board desde FEN
    board = chess.Board(fen)
    
    # Generar SVG con python-chess (mucho más profesional)
    svg = chess.svg.board(
        board=board,
        size=width,
        coordinates=True,
        colors={
            "square light": "#f0d9b5",
            "square dark": "#b58863",
            "square dark lastmove": "#aaa23a",
            "square light lastmove": "#cdd26a"
        }
    )
    
    # Header con estilo
    turno = "Blancas" if board.turn else "Negras"
    turno_color = "#3b82f6" if board.turn else "#94a3b8"
    
    html_code = f"""
    <style>
    .chess-widget {{
        background: linear-gradient(135deg, #0f1628 0%, #0a1428 100%);
        border: 1px solid #1e3a6e;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        max-width: {width + 100}px;
        margin: 0 auto;
    }}
    
    .chess-header {{
        text-align: center;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #1e3a6e;
    }}
    
    .apertura-name {{
        color: #e2e8f0;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }}
    
    .turno-indicator {{
        display: inline-block;
        background: {turno_color};
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
    }}
    
    .board-container {{
        display: flex;
        justify-content: center;
        margin: 1rem 0;
        background: #1a2540;
        padding: 1rem;
        border-radius: 8px;
    }}
    
    .board-container svg {{
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }}
    
    .moves-section {{
        margin-top: 1rem;
        padding: 1rem;
        background: rgba(10, 14, 26, 0.8);
        border-radius: 6px;
        border: 1px solid #1e3a6e;
    }}
    
    .moves-title {{
        color: #60a5fa;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}
    
    .move-chip {{
        display: inline-block;
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        margin: 0 0.3rem 0.3rem 0;
        font-family: 'Courier New', monospace;
        font-weight: 600;
    }}
    
    .fen-section {{
        margin-top: 0.5rem;
        padding: 0.7rem;
        background: rgba(15, 22, 40, 0.9);
        border-radius: 4px;
        border: 1px solid #1e3a6e;
    }}
    
    .fen-label {{
        color: #94a3b8;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.3rem;
    }}
    
    .fen-text {{
        color: #cbd5e1;
        font-family: 'Courier New', monospace;
        font-size: 0.75rem;
        word-break: break-all;
    }}
    </style>
    
    <div class="chess-widget">
        <div class="chess-header">
            <div class="apertura-name">{'📖 ' + apertura_nombre if apertura_nombre else '♟️ Posición'}</div>
            <span class="turno-indicator">Juegan {turno}</span>
        </div>
        
        <div class="board-container">
            {svg}
        </div>
        
        {'<div class="moves-section">' +
         '<div class="moves-title">💡 Jugadas Principales</div>' +
         ''.join([f'<span class="move-chip">{mov}</span>' for mov in jugadas_siguientes]) +
         '</div>' if jugadas_siguientes else ''}
        
        <div class="fen-section">
            <div class="fen-label">FEN Position</div>
            <div class="fen-text">{fen}</div>
        </div>
    </div>
    """
    
    st.components.v1.html(html_code, height=width + 250, scrolling=False)


# Ejemplo de uso
if __name__ == "__main__":
    st.set_page_config(page_title="Tablero Profesional", layout="wide")
    
    st.title("♟️ Tablero de Ajedrez Profesional")
    st.caption("Usando python-chess con SVG de alta calidad")
    
    ejemplos = {
        "Posición Inicial": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "Siciliana Najdorf": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
        "Ruy López": "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
    }
    
    sel = st.selectbox("Selecciona apertura:", list(ejemplos.keys()))
    
    render_tablero_profesional(
        fen=ejemplos[sel],
        apertura_nombre=sel,
        jugadas_siguientes=["e4", "d4", "Nf3", "c4"],
        width=400
    )
