"""
orquestador.py
══════════════════════════════════════════════════════════════════════════════
Chess Intelligence System — Orquestador principal

Flujo completo para un usuario de Lichess:

  FASE 1 — ANÁLISIS
  ├── 1.1  Descarga de partidas vía API de Lichess
  ├── 1.2  Análisis teórico (cruce con theory_db.pkl)
  ├── 1.3  Evaluación post-teoría con Stockfish (ACL / Accuracy)
  ├── 1.4  Persistencia incremental en master_game_level_ml.csv
  ├── 1.5  Dashboard de aperturas (Riesgo / Dominio / Feeling)
  └── 1.6  Ranking de aperturas con clasificación por nivel (KMeans)

  FASE 2 — RECOMENDACIÓN
  ├── 2.1  Recomendador por perfil directo (v2 - reglas)
  ├── 2.2  Recomendador por similitud de usuarios (KNN v2)
  └── 2.3  Plan de estudio unificado (fusión con deduplicación)

  FASE 3 — OPCIONAL
  └── 3.1  Creación de estudio Lichess con posiciones blunder

USO:
  python orquestador.py                        # modo interactivo
  python orquestador.py --usuario tecojoytetruqueo --partidas 50
  python orquestador.py --usuario tecojoytetruqueo --sin-stockfish   # solo teoría

DEPENDENCIAS:
  pip install berserk chess stockfish requests beautifulsoup4
  pip install pandas numpy scikit-learn joblib tqdm
══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import io
import os
import re
import sys
import time
import pickle
import argparse
import textwrap
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional

import chess
import chess.pgn
import joblib
import numpy as np
import pandas as pd
import requests
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

try:
    import berserk
except ImportError:
    sys.exit("❌  Instala berserk: pip install berserk")

try:
    from stockfish import Stockfish
    STOCKFISH_AVAILABLE = True
except ImportError:
    STOCKFISH_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# 0. RUTAS Y CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _encontrar_raiz() -> Path:
    """Localiza la carpeta 'Proyecto ML' subiendo desde el directorio actual."""
    for p in [Path.cwd()] + list(Path.cwd().parents):
        if p.name == "Proyecto ML":
            return p
        if (p / "Proyecto ML").exists():
            return p / "Proyecto ML"
    raise FileNotFoundError(
        "No se encontró la carpeta 'Proyecto ML'.\n"
        "Ejecuta el script desde dentro del proyecto."
    )


ROOT      = _encontrar_raiz()
SRC       = ROOT / "src"
DATA_DIR  = SRC / "data"
CSV_DIR   = DATA_DIR / "CSV"
PKL_DIR   = DATA_DIR / "PKL"
MODEL_DIR = SRC / "model" / "production"
IMG_DIR   = ROOT / "resources" / "img"

for d in [CSV_DIR, PKL_DIR, MODEL_DIR, IMG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Archivos de datos
MASTER_CSV    = CSV_DIR / "master_game_level_ml.csv"
RECURSOS_CSV  = CSV_DIR / "chess_resources_v3.csv"
THEORY_PKL    = PKL_DIR / "theory_db.pkl"
STOCKFISH_EXE = ROOT / "resources" / "engines" / "stockfish-windows-x86-64-avx2.exe"

# Modelos KMeans (generados por Sección 10 de MODELOS_ML_v4)
KM_PKL     = PKL_DIR / "km_apertura_pura.pkl"
SCALER_PKL = PKL_DIR / "scaler_apertura_pura.pkl"

# Colores de terminal
C = {
    "verde":    "\033[92m",
    "amarillo": "\033[93m",
    "rojo":     "\033[91m",
    "cyan":     "\033[96m",
    "bold":     "\033[1m",
    "reset":    "\033[0m",
    "dim":      "\033[2m",
}

SEP  = "═" * 70
SEP2 = "─" * 70


def _c(texto: str, color: str) -> str:
    return f"{C.get(color,'')}{texto}{C['reset']}"


def _titulo(texto: str) -> None:
    print(f"\n{SEP}")
    print(f"  {_c(texto, 'bold')}")
    print(SEP)


def _ok(msg: str)   -> None: print(f"  {_c('✅', 'verde')}  {msg}")
def _warn(msg: str) -> None: print(f"  {_c('⚠️ ', 'amarillo')} {msg}")
def _err(msg: str)  -> None: print(f"  {_c('❌', 'rojo')}  {msg}")
def _info(msg: str) -> None: print(f"  {_c('ℹ️ ', 'cyan')}  {msg}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. UTILIDADES COMPARTIDAS
# ══════════════════════════════════════════════════════════════════════════════

def acpl_to_accuracy(acpl: float) -> float:
    """Convierte pérdida media en centipeones → porcentaje de precisión [0-100]."""
    return round(float(max(0, min(100, 100 * np.exp(-0.0035 * float(acpl))))), 1)


def acl_ajustada(fin_teoria: float, accuracy: float,
                 bonus_max: float = 15.0, max_teo: float = 15.0) -> float:
    """Accuracy ajustada: premia líneas más largas de teoría."""
    return round(min(100.0, accuracy + np.log1p(fin_teoria) / np.log1p(max_teo) * bonus_max), 1)


def teoria_ponderada(fin_teoria: float, max_teo: float = 15.0) -> float:
    """Profundidad teórica normalizada logarítmicamente."""
    return np.log1p(fin_teoria) / np.log1p(max_teo)


# ══════════════════════════════════════════════════════════════════════════════
# 2. MOTOR DE ANÁLISIS (FASE 1)
# ══════════════════════════════════════════════════════════════════════════════

class ChessIntelligenceSystem:
    """
    Motor de análisis de repertorio de ajedrez.
    Combina theory_db.pkl (posiciones FEN de maestros) con Stockfish
    para medir la precisión post-teoría de cada apertura.
    """

    MATE_SCORE = 1_000  # Cap en CP para no distorsionar medias con posiciones de mate

    def __init__(self, stockfish_path: Optional[Path] = None):
        self.theory_positions: set = set()
        self.sf: Optional[object]  = None
        self.blunders: list        = []   # acumula (game_id, apertura, fen, perdida)

        self._cargar_teoria()

        if stockfish_path and STOCKFISH_AVAILABLE:
            _info(f"Iniciando Stockfish desde {stockfish_path} ...")
            try:
                self.sf = Stockfish(
                    path=str(stockfish_path),
                    parameters={"Threads": 4, "Hash": 512}
                )
                self.sf.set_depth(16)
                _ok("Stockfish listo.")
            except Exception as e:
                _warn(f"No se pudo iniciar Stockfish: {e}")
                _warn("El análisis continuará SIN evaluación de engine.")
        else:
            _warn("Stockfish no disponible — solo análisis teórico.")

    # ── Carga de la base teórica ──────────────────────────────────────────────

    def _cargar_teoria(self) -> None:
        """Carga el set de posiciones EPD desde theory_db.pkl."""
        if not THEORY_PKL.exists():
            _err(f"theory_db.pkl no encontrado en {THEORY_PKL}")
            _info("Genera la base teórica ejecutando la Sección 2 del notebook de ingesta.")
            return
        with open(THEORY_PKL, "rb") as f:
            self.theory_positions = pickle.load(f)
        _ok(f"Base teórica cargada: {len(self.theory_positions):,} posiciones.")

    # ── Evaluación Stockfish ──────────────────────────────────────────────────

    def get_eval(self, fen: str) -> float:
        """Evalúa una posición con Stockfish. Devuelve CP clampeado a ±MATE_SCORE."""
        if not self.sf:
            return 0.0
        try:
            self.sf.set_fen_position(fen, do_validation=False)
            ev = self.sf.get_evaluation()
            if ev["type"] == "mate":
                return float(self.MATE_SCORE if ev["value"] > 0 else -self.MATE_SCORE)
            return float(max(-self.MATE_SCORE, min(self.MATE_SCORE, ev["value"])))
        except Exception:
            return 0.0

    # ── Cálculo de ACL post-teoría ────────────────────────────────────────────

    def calcular_acl(self, game, player_color: chess.Color,
                     start_move: int, apertura: str,
                     game_id: str, window: int = 12) -> Optional[float]:
        """
        Calcula el ACL (Average Centipawn Loss) post-teoría.

        Estrategia N+1: reutiliza la evaluación previa como eval_prev del
        turno siguiente → mitad de llamadas a Stockfish.
        También registra el primer blunder (>100 CP) en self.blunders.

        Parameters
        ----------
        window : jugadas post-teoría a evaluar (default 12).
        """
        if not self.sf:
            return None   # Sin Stockfish no hay ACL

        board  = game.board()
        moves  = list(game.mainline_moves())
        losses = []
        blunder_registrado = False

        # Avanzar hasta el fin de la teoría
        for m in moves[:start_move]:
            board.push(m)

        end_idx = min(start_move + window, len(moves))
        if end_idx <= start_move:
            return None

        eval_cache = self.get_eval(board.fen())

        for i in range(start_move, end_idx):
            es_turno_jugador = (board.turn == player_color)
            fen_antes        = board.fen()
            eval_prev        = eval_cache

            board.push(moves[i])
            eval_cache = self.get_eval(board.fen())

            if es_turno_jugador:
                side = 1.0 if player_color == chess.WHITE else -1.0
                loss = float(max(0.0, (eval_prev - eval_cache) * side))
                losses.append(loss)

                # Registrar primer blunder del jugador en esta partida
                if loss > 100.0 and not blunder_registrado:
                    self.blunders.append({
                        "game_id":  game_id,
                        "apertura": apertura,
                        "fen":      fen_antes,
                        "perdida":  round(loss, 0),
                    })
                    blunder_registrado = True

        return sum(losses) / len(losses) if losses else None

    # ── Análisis de una lista de partidas ────────────────────────────────────

    def analizar_partidas(self, games_list: list,
                          target_user: str, user_rating: int) -> pd.DataFrame:
        """
        Analiza una lista de objetos chess.pgn.Game.

        Por cada partida determina: apertura, color, fin de teoría (tolerante
        a 1 transposición) y ACL post-teoría.

        Returns
        -------
        DataFrame con una fila por partida analizada con éxito.
        """
        results = []
        total   = len(games_list)

        for idx, game in enumerate(games_list):
            if not game:
                continue

            headers  = game.headers
            game_id  = headers.get("Site", "").split("/")[-1]
            is_white = headers.get("White", "").lower() == target_user.lower()
            color    = chess.WHITE if is_white else chess.BLACK

            apertura_full = headers.get("Opening", "Desconocida")
            apertura_base = apertura_full.split(":")[0].split(",")[0].strip()

            res = headers.get("Result", "*")
            if   (res == "1-0" and is_white) or (res == "0-1" and not is_white):
                victoria = 1.0
            elif res == "1/2-1/2":
                victoria = 0.5
            else:
                victoria = 0.0

            # ── Detectar fin de teoría (tolerante a 1 transposición) ──────────
            board              = game.board()
            moves              = list(game.mainline_moves())
            theory_end         = 0
            off_theory_streak  = 0

            for i, move in enumerate(moves[:30]):
                board.push(move)
                if board.epd() in self.theory_positions:
                    theory_end        = i + 1
                    off_theory_streak = 0
                else:
                    off_theory_streak += 1
                    if off_theory_streak >= 2:
                        break   # Dos jugadas consecutivas fuera → salida definitiva

            # ── ACL post-teoría ───────────────────────────────────────────────
            acl = self.calcular_acl(
                game, color, theory_end, apertura_base, game_id
            )

            # ── Construir fila de resultado ───────────────────────────────────
            accuracy  = acpl_to_accuracy(acl) if acl is not None else None
            acc_ajust = acl_ajustada(theory_end, accuracy) if accuracy is not None else None

            results.append({
                "Game_ID":        game_id,
                "Usuario":        target_user,
                "Rating_Usuario": user_rating,
                "Apertura":       apertura_base,
                "Color":          "Blancas" if is_white else "Negras",
                "Fin_Teoria":     theory_end,
                "ACL_Post_Teo":   round(acl, 1) if acl is not None else None,
                "acl_winsorized": min(acl, 500) if acl is not None else None,
                "Accuracy":       accuracy,
                "AccAjustada":    acc_ajust,
                "Victoria":       victoria,
            })

            engine_str = f"ACL: {acl:.0f}cp" if acl is not None else "sin engine"
            print(f"   [{idx+1:>3}/{total}] {apertura_base[:35]:<35} "
                  f"| Teo: {theory_end:>2}j | {engine_str}")

        return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════════════════════
# 3. DESCARGA DE PARTIDAS Y PIPELINE DE USUARIO
# ══════════════════════════════════════════════════════════════════════════════

def descargar_partidas(client: berserk.Client,
                       username: str, max_games: int) -> tuple[list, int]:
    """
    Descarga las últimas N partidas del usuario y obtiene su rating.

    Returns
    -------
    (lista de chess.pgn.Game, rating_referencia)
    """
    _info(f"Obteniendo perfil de {username} ...")
    perfil  = client.users.get_public_data(username)
    perfs   = perfil.get("perfs", {})
    r_blitz = perfs.get("blitz", {}).get("rating", 0)
    r_rapid = perfs.get("rapid", {}).get("rating", 0)
    rating  = r_blitz if r_blitz > 0 else r_rapid

    print(f"   Blitz: {r_blitz} | Rapid: {r_rapid} | Referencia: {_c(str(rating), 'bold')}")

    if rating == 0:
        _warn("Sin ratings activos en Lichess.")
        return [], 0

    _info(f"Descargando últimas {max_games} partidas ...")
    games_gen = client.games.export_by_player(
        username, max=max_games, opening=True, as_pgn=True
    )
    games = []
    for g_str in games_gen:
        if isinstance(g_str, dict):
            continue
        game_obj = chess.pgn.read_game(io.StringIO(g_str))
        if game_obj:
            games.append(game_obj)
        if len(games) >= max_games:
            break

    _ok(f"{len(games)} partidas descargadas.")
    return games, rating


def guardar_incrementalmente(df_nuevas: pd.DataFrame) -> pd.DataFrame:
    """
    Concatena df_nuevas al CSV maestro eliminando duplicados por Game_ID.
    Crea el CSV si no existe.
    """
    if MASTER_CSV.exists():
        df_hist  = pd.read_csv(MASTER_CSV)
        df_final = (
            pd.concat([df_hist, df_nuevas], ignore_index=True)
            .drop_duplicates(subset=["Game_ID"], keep="first")
        )
        nuevas = len(df_final) - len(df_hist)
    else:
        df_final = df_nuevas.copy()
        nuevas   = len(df_nuevas)

    df_final.to_csv(MASTER_CSV, index=False)
    _ok(f"Dataset guardado → {MASTER_CSV.name}  (+{nuevas} nuevas | {len(df_final):,} total)")
    return df_final


# ══════════════════════════════════════════════════════════════════════════════
# 4. DASHBOARD Y RANKING DE APERTURAS (FASE 1.5 + 1.6)
# ══════════════════════════════════════════════════════════════════════════════

def generar_dashboard(df_raw: pd.DataFrame, username: str) -> pd.DataFrame:
    """
    Agrega por (Apertura, Color) y calcula los índices de rendimiento:
      - Score_Prep    : teoría × precisión
      - Risk_Index    : teoría × imprecisión
      - Score_Feeling : precisión alta con poca teoría
    """
    df = df_raw[df_raw["Usuario"] == username].copy()
    if df.empty:
        return pd.DataFrame()

    df["ACL_clean"] = df["ACL_Post_Teo"].clip(upper=500)

    agg = df.groupby(["Apertura", "Color"]).agg(
        Avg_Teoria = ("Fin_Teoria",  "mean"),
        Avg_ACL    = ("ACL_clean",   "mean"),
        Volumen    = ("Game_ID",     "count"),
        Win_Rate   = ("Victoria",    "mean"),
    ).reset_index()

    agg["Accuracy"]      = agg["Avg_ACL"].apply(acpl_to_accuracy)
    agg["Score_Prep"]    = (agg["Avg_Teoria"] / 15) * (agg["Accuracy"] / 100)
    agg["Risk_Index"]    = (agg["Avg_Teoria"] / 15) * (100 - agg["Accuracy"])
    agg["Score_Feeling"] = np.where(
        (agg["Avg_Teoria"] < 7) & (agg["Accuracy"] >= 65.0) & (agg["Volumen"] >= 2),
        agg["Accuracy"], 0
    )
    return agg


def imprimir_dashboard(df_m: pd.DataFrame, username: str) -> None:
    """Imprime el dashboard técnico con 3 categorías por color."""
    if df_m is None or df_m.empty:
        _warn("Sin datos suficientes para el dashboard.")
        return

    _titulo(f"🔬 DASHBOARD DE APERTURAS — {username}")

    for color in ["Blancas", "Negras"]:
        subset = df_m[df_m["Color"] == color].copy()
        if subset.empty:
            continue

        print(f"\n  ♟  {_c(color.upper(), 'bold')}")

        # ── RIESGO ────────────────────────────────────────────────────────────
        muro      = subset.sort_values("Risk_Index", ascending=False).head(3)
        muro_list = muro["Apertura"].tolist()
        print(f"\n  {_c('⚠️  RIESGO (estudiar o revisar):', 'amarillo')}")
        for i, (_, r) in enumerate(muro.iterrows(), 1):
            print(f"     {i}. {r['Apertura'][:30]:<30} "
                  f"| Acc: {str(r['Accuracy']).rjust(5)}% "
                  f"| Teo: {round(r['Avg_Teoria'],1):>4}j "
                  f"| n={int(r['Volumen'])}")

        # ── DOMINIO ───────────────────────────────────────────────────────────
        top_p = subset[
            ~subset["Apertura"].isin(muro_list) & (subset["Volumen"] >= 3)
        ].sort_values("Score_Prep", ascending=False).head(3)
        print(f"\n  {_c('🌟  DOMINIO TEÓRICO:', 'verde')}")
        if top_p.empty:
            print("     N/A")
        else:
            for i, (_, r) in enumerate(top_p.iterrows(), 1):
                print(f"     {i}. {r['Apertura'][:30]:<30} "
                      f"| Acc: {str(r['Accuracy']).rjust(5)}% "
                      f"| Teo: {round(r['Avg_Teoria'],1):>4}j "
                      f"| n={int(r['Volumen'])}")

        # ── FEELING ───────────────────────────────────────────────────────────
        top_f = subset[subset["Score_Feeling"] > 0].sort_values(
            "Score_Feeling", ascending=False
        ).head(3)
        print(f"\n  {_c('🧠  FEELING NATURAL (potenciar):', 'cyan')}")
        if top_f.empty:
            print("     N/A")
        else:
            for i, (_, r) in enumerate(top_f.iterrows(), 1):
                print(f"     {i}. {r['Apertura'][:30]:<30} "
                      f"| Acc: {str(r['Accuracy']).rjust(5)}% "
                      f"| Teo: {round(r['Avg_Teoria'],1):>4}j "
                      f"| n={int(r['Volumen'])}")


def clasificar_aperturas_kmeans(df_usuario: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica cada partida en (apertura_solida / apertura_media / apertura_debil)
    usando el KMeans entrenado sin leakage de rating.

    Requiere km_apertura_pura.pkl y scaler_apertura_pura.pkl en src/data/PKL/.
    Si no existen, devuelve el DataFrame sin columna de nivel.
    """
    if not KM_PKL.exists() or not SCALER_PKL.exists():
        _warn("km_apertura_pura.pkl o scaler_apertura_pura.pkl no encontrados.")
        _warn("Ejecuta la Sección 10 de MODELOS_ML_v4.ipynb para generarlos.")
        return df_usuario

    km     = joblib.load(KM_PKL)
    scaler = joblib.load(SCALER_PKL)

    NOMBRES = {0: "apertura_solida", 1: "apertura_media", 2: "apertura_debil"}

    # Features que usa el modelo (deben coincidir con las de entrenamiento)
    FEATURES = ["Fin_Teoria", "acl_winsorized", "game_prep_score", "game_risk_index"]
    disponibles = [f for f in FEATURES if f in df_usuario.columns]

    if len(disponibles) < 2:
        # Fallback con lo que tenemos: teoria + acl
        df_usuario["game_prep_score"]  = (df_usuario["Fin_Teoria"] / 15) * (df_usuario.get("Accuracy", 50) / 100)
        df_usuario["game_risk_index"]  = (df_usuario["Fin_Teoria"] / 15) * (100 - df_usuario.get("Accuracy", 50))
        disponibles = ["Fin_Teoria", "acl_winsorized", "game_prep_score", "game_risk_index"]
        disponibles = [f for f in disponibles if f in df_usuario.columns]

    X = df_usuario[disponibles].fillna(0).values
    # Alinear al número de features que espera el scaler
    if X.shape[1] != scaler.n_features_in_:
        _warn(f"Dimensión de features ({X.shape[1]}) ≠ scaler ({scaler.n_features_in_}). "
              f"Reclasificación omitida.")
        return df_usuario

    labels = km.predict(scaler.transform(X))

    # Ordenar clusters por ACL ascendente (0=mejor) igual que en entrenamiento
    orden = (
        pd.Series(labels)
        .groupby(labels)
        .count()
        .index.tolist()
    )
    # Usar el mapa original si los centroides están en el mismo orden
    df_usuario["nivel_apertura"]        = [NOMBRES.get(l, "apertura_media") for l in labels]
    df_usuario["nivel_apertura_codigo"] = labels

    return df_usuario


def imprimir_ranking_kmeans(df_usuario: pd.DataFrame) -> None:
    """Imprime el ranking de aperturas por nivel KMeans."""
    if "nivel_apertura" not in df_usuario.columns:
        return

    _titulo("📊 CLASIFICACIÓN DE APERTURAS POR NIVEL (KMeans)")

    COLORES_NIVEL = {
        "apertura_solida": "verde",
        "apertura_media":  "amarillo",
        "apertura_debil":  "rojo",
    }
    ICONOS_NIVEL = {
        "apertura_solida": "✅",
        "apertura_media":  "📈",
        "apertura_debil":  "⚠️ ",
    }

    resumen = (
        df_usuario
        .groupby(["Apertura", "Color", "nivel_apertura"])
        .agg(n=("Game_ID", "count"), acc=("Accuracy", "mean"))
        .reset_index()
        .sort_values(["nivel_apertura", "acc"], ascending=[True, False])
    )

    for nivel in ["apertura_solida", "apertura_media", "apertura_debil"]:
        sub = resumen[resumen["nivel_apertura"] == nivel]
        if sub.empty:
            continue
        label = nivel.replace("_", " ").upper()
        icono = ICONOS_NIVEL[nivel]
        color = COLORES_NIVEL[nivel]
        print(f"\n  {icono}  {_c(label, color)} ({len(sub)} aperturas)")
        print(f"  {'─'*60}")
        for _, r in sub.iterrows():
            acc_str = f"{r['acc']:.1f}%" if pd.notna(r["acc"]) else "  N/A "
            print(f"     {r['Apertura'][:32]:<32} "
                  f"| {r['Color']:<7} | Acc: {acc_str:>6} | n={int(r['n'])}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. RECOMENDADOR (FASE 2)
# ══════════════════════════════════════════════════════════════════════════════

SINONIMOS = {
    "rapport-jobava system":   ["jobava", "london"],
    "jobava london":           ["jobava", "london"],
    "london system":           ["london"],
    "king's indian attack":    ["king's indian attack"],
    "king's indian defense":   ["king's indian"],
    "queen's indian defense":  ["queen's indian"],
    "nimzo-indian defense":    ["nimzo-indian"],
    "sicilian defense":        ["sicilian"],
    "caro-kann defense":       ["caro-kann"],
    "french defense":          ["french defense"],
    "queen's gambit declined": ["queen's gambit declined", "qgd"],
    "queen's gambit accepted": ["queen's gambit accepted", "qga"],
    "queen's gambit":          ["queen's gambit"],
    "slav defense":            ["slav defense", "slav"],
    "semi-slav defense":       ["semi-slav"],
    "queen's pawn game":       ["queen's pawn", "1.d4", "colle", "torre"],
    "king's pawn game":        ["king's pawn", "1.e4"],
    "zukertort opening":       ["zukertort", "réti"],
    "english opening":         ["english opening"],
    "dutch defense":           ["dutch defense"],
    "pirc defense":            ["pirc defense"],
    "ruy lopez":               ["ruy lopez", "spanish game"],
    "italian game":            ["italian game"],
    "scotch game":             ["scotch game"],
    "vienna game":             ["vienna game"],
    "petrov defense":          ["petrov", "russian game"],
    "grunfeld defense":        ["Grünfeld", "grunfeld"],
    "benoni defense":          ["benoni"],
}

NIVEL_PRIO = {"sin_base": 1, "desarrollo": 2, "dominio": 3}


def _terminos_busqueda(apertura: str) -> list:
    """Expande el nombre de una apertura con sinónimos conocidos."""
    ap = apertura.strip().lower()
    t  = [ap]
    for clave, sins in SINONIMOS.items():
        if clave in ap or ap in clave:
            t.extend(sins)
    return list(dict.fromkeys(t))


def _match_openings(openings_cell: str, terminos: list) -> bool:
    if pd.isna(openings_cell):
        return False
    cell = openings_cell.lower()
    return any(t in cell for t in terminos)


def buscar_recursos(apertura: str, df_rec: pd.DataFrame,
                    rating: float, nivel: str, top_n: int = 3) -> list:
    """
    Busca recursos en el catálogo para una apertura y nivel dados.
    Ordena por rating_score desc, is_free asc.
    Incluye fallback por tier si no hay match específico.
    """
    terminos = _terminos_busqueda(apertura)
    mask     = df_rec["openings"].apply(lambda c: _match_openings(c, terminos))
    cands    = df_rec[mask].copy()

    # Filtrar por rango de rating del usuario
    cands = cands[
        (cands["level_min"].fillna(0)    <= rating) &
        (cands["level_max"].fillna(9999) >= rating)
    ]

    if not cands.empty:
        cands = cands.sort_values(["rating_score", "is_free"], ascending=[False, True])
        return cands[["title", "source", "url", "level_tier",
                       "is_free", "course_type"]].head(top_n).to_dict("records")

    # Fallback: cualquier recurso de apertura en el tier correcto
    if   rating >= 2000: tier = "expert"
    elif rating >= 1200: tier = "intermediate"
    else:                tier = "beginner"

    fallback = df_rec[
        (df_rec["level_tier"] == tier) & (df_rec["course_type"] == "opening")
    ].head(top_n)

    if not fallback.empty:
        return fallback[["title", "source", "url", "level_tier",
                          "is_free", "course_type"]].to_dict("records")
    return [{"title": "Sin recurso específico en catálogo", "source": "-",
             "url": "", "level_tier": "-", "is_free": None, "course_type": "-"}]


def recomendar_perfil_directo(usuario: str, df_raw: pd.DataFrame,
                               df_rec: pd.DataFrame,
                               top_n_aperturas: int = 5,
                               top_n_recursos:  int = 3) -> tuple[list, float]:
    """
    Recomendador v2 — basado en el perfil directo del usuario.
    Prioriza: sin_base > desarrollo > dominio, luego por win_rate asc.
    Solo considera aperturas con ≥5 partidas.
    """
    df_u = df_raw[df_raw["Usuario"] == usuario].copy()
    if df_u.empty:
        return [], 0.0

    rating = float(df_u["Rating_Usuario"].mean())

    # Mapear nivel_apertura al esquema del recomendador
    MAPA_NIVEL = {
        "apertura_debil":  "sin_base",
        "apertura_media":  "desarrollo",
        "apertura_solida": "dominio",
    }
    df_u["nivel_rec"] = df_u.get("nivel_apertura", pd.Series(
        ["desarrollo"] * len(df_u), index=df_u.index
    )).map(MAPA_NIVEL).fillna("desarrollo")

    resumen = (
        df_u.groupby(["Apertura", "Color", "nivel_rec"])
        .agg(
            n_partidas = ("Game_ID",    "count"),
            acc_media  = ("Accuracy",   "mean"),
            win_rate   = ("Victoria",   "mean"),
        )
        .reset_index()
    )
    resumen["prio"] = resumen["nivel_rec"].map(NIVEL_PRIO).fillna(2)
    resumen = (
        resumen[resumen["n_partidas"] >= 5]
        .sort_values(["prio", "win_rate"], ascending=[True, True])
        .head(top_n_aperturas)
    )

    recomendaciones = []
    for _, fila in resumen.iterrows():
        recursos = buscar_recursos(
            fila["Apertura"], df_rec, rating, fila["nivel_rec"], top_n_recursos
        )
        recomendaciones.append({
            "fuente":     "perfil_directo",
            "apertura":   fila["Apertura"],
            "nivel":      fila["nivel_rec"],
            "color":      fila["Color"],
            "n_partidas": int(fila["n_partidas"]),
            "acc_media":  round(fila["acc_media"], 1) if pd.notna(fila["acc_media"]) else None,
            "recursos":   recursos,
        })
    return recomendaciones, rating


def _construir_perfiles_knn(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega el dataset a nivel de usuario para el espacio KNN.
    Imputa NaN con la mediana global para usuarios con pocas partidas.
    """
    MAPA = {"apertura_debil": "sin_base", "apertura_media": "desarrollo",
            "apertura_solida": "dominio"}

    df = df.copy()
    if "nivel_apertura" in df.columns:
        df["nivel_rec"] = df["nivel_apertura"].map(MAPA).fillna("desarrollo")
    else:
        df["nivel_rec"] = "desarrollo"

    # Columna de accuracy: usar AccAjustada si existe, sino Accuracy, sino 50
    if "AccAjustada" in df.columns:
        df["_acc"] = pd.to_numeric(df["AccAjustada"], errors="coerce")
    elif "Accuracy" in df.columns:
        df["_acc"] = pd.to_numeric(df["Accuracy"], errors="coerce")
    else:
        df["_acc"] = 50.0

    perfiles = []
    for usuario, grupo in df.groupby("Usuario"):
        n      = len(grupo)
        counts = grupo["nivel_rec"].value_counts()
        perfiles.append({
            "Usuario":        usuario,
            "rating_medio":   grupo["Rating_Usuario"].mean(),
            "acc_media":      grupo["_acc"].mean(),
            "teo_media":      grupo["Fin_Teoria"].mean(),
            "pct_dominio":    counts.get("dominio",    0) / n,
            "pct_desarrollo": counts.get("desarrollo", 0) / n,
            "pct_sin_base":   counts.get("sin_base",   0) / n,
            "win_rate":       grupo["Victoria"].mean() if "Victoria" in grupo.columns else 0.5,
            "n_aperturas":    grupo["Apertura"].nunique() if "Apertura" in grupo.columns else 1,
        })

    df_out = pd.DataFrame(perfiles).set_index("Usuario")

    # Imputar NaN con la mediana de cada feature (usuarios con pocas partidas
    # pueden tener acc_media NaN si todas sus partidas carecen de ACL)
    FEATURE_V2 = ["acc_media", "teo_media", "pct_dominio",
                  "pct_desarrollo", "pct_sin_base", "win_rate", "n_aperturas"]
    for col in FEATURE_V2:
        if col in df_out.columns and df_out[col].isna().any():
            mediana = df_out[col].median()
            df_out[col] = df_out[col].fillna(mediana if pd.notna(mediana) else 50.0)

    return df_out


def recomendar_knn(usuario: str, df_raw: pd.DataFrame, df_rec: pd.DataFrame,
                   top_n_recursos: int = 3, k: int = 5) -> tuple[list, float]:
    """
    Recomendador KNN — detecta aperturas que dominan usuarios similares
    pero que el usuario objetivo aun no ha trabajado.
    Requiere al menos 3 usuarios en el dataset para funcionar.
    """
    df_perfiles = _construir_perfiles_knn(df_raw)

    if usuario not in df_perfiles.index:
        _warn("KNN: usuario no encontrado en los perfiles.")
        return [], 0.0

    if len(df_perfiles) < 3:
        _warn("KNN: dataset con menos de 3 usuarios — recomendador KNN omitido.")
        _info("El recomendador por perfil directo sigue activo.")
        return [], 0.0

    rating     = float(df_perfiles.loc[usuario, "rating_medio"])
    FEATURE_V2 = ["acc_media", "teo_media", "pct_dominio",
                  "pct_desarrollo", "pct_sin_base", "win_rate", "n_aperturas"]
    PESOS_V2   = np.array([2.5, 2.5, 2.0, 2.0, 2.0, 1.0, 0.5])

    sc    = StandardScaler()
    X_all = sc.fit_transform(df_perfiles[FEATURE_V2].fillna(0).values) * PESOS_V2

    k = min(k, len(df_perfiles) - 1)

    knn = NearestNeighbors(n_neighbors=k + 1, metric="cosine", algorithm="brute")
    knn.fit(X_all)

    usuarios_idx = df_perfiles.index.tolist()
    vec = (sc.transform(df_perfiles.loc[[usuario], FEATURE_V2].values) * PESOS_V2)
    dists, idxs = knn.kneighbors(vec)

    vecinos = [
        usuarios_idx[idx] for idx, d in zip(idxs[0], dists[0])
        if usuarios_idx[idx] != usuario
    ][:k]

    MIN_P = 5

    def ap_dominadas(u: str) -> set:
        """Aperturas con ≥MIN_P partidas en nivel dominio para el usuario u."""
        sub = df_raw[
            (df_raw["Usuario"] == u) &
            (df_raw.get("nivel_apertura", pd.Series(dtype=str)) == "apertura_solida")
        ]
        c = sub.groupby("Apertura").size()
        return set(c[c >= MIN_P].index)

    ap_objetivo = ap_dominadas(usuario)
    ap_vecinos  = {v: ap_dominadas(v) for v in vecinos}
    todas_vec   = set().union(*ap_vecinos.values())
    gaps        = todas_vec - ap_objetivo

    freq_gap  = {
        ap: sum(1 for v_ap in ap_vecinos.values() if ap in v_ap)
        for ap in gaps
    }
    gaps_ord  = sorted(freq_gap.items(), key=lambda x: x[1], reverse=True)

    recomendaciones = []
    for apertura, freq in gaps_ord[:5]:
        recursos = buscar_recursos(apertura, df_rec, rating, "desarrollo", top_n_recursos)
        recomendaciones.append({
            "fuente":       "knn",
            "apertura":     apertura,
            "freq_vecinos": freq,
            "k_total":      k,
            "recursos":     recursos,
        })

    return recomendaciones, rating


def fusionar_planes(recs_perfil: list, recs_knn: list,
                    rating: float) -> tuple[dict, list]:
    """
    Fusiona los dos recomendadores con deduplicación.

    Scoring:
      - Solo perfil directo → 1.0
      - Solo KNN            → 0.8
      - Ambos               → 1.5 (+0.5 boost, cap 2.0)
    """
    recursos_vistos = {}  # resource_id → dict
    plan_aperturas  = {}  # apertura    → metadatos

    def registrar(apertura, meta, recursos, fuente, boost):
        if apertura not in plan_aperturas:
            plan_aperturas[apertura] = {**meta, "fuentes": set(), "recursos_ids": []}
        plan_aperturas[apertura]["fuentes"].add(fuente)

        for r in recursos:
            rid = r.get("url") or r.get("title", "sin_id")
            if rid not in recursos_vistos:
                recursos_vistos[rid] = {
                    **r,
                    "score":    boost,
                    "fuentes":  {fuente},
                    "aperturas": [apertura],
                }
            else:
                recursos_vistos[rid]["score"]   += boost * 0.5
                recursos_vistos[rid]["fuentes"].add(fuente)
                if apertura not in recursos_vistos[rid]["aperturas"]:
                    recursos_vistos[rid]["aperturas"].append(apertura)

    for entrada in recs_perfil:
        meta = {k: v for k, v in entrada.items() if k != "recursos"}
        registrar(entrada["apertura"], meta, entrada["recursos"], "perfil", 1.0)

    for entrada in recs_knn:
        meta = {k: v for k, v in entrada.items() if k != "recursos"}
        registrar(entrada["apertura"], meta, entrada["recursos"], "knn", 0.8)

    # Boost a recursos que aparecen en ambas fuentes
    for r in recursos_vistos.values():
        if len(r["fuentes"]) == 2:
            r["score"] = min(r["score"] + 0.5, 2.0)

    recursos_ordenados = sorted(
        recursos_vistos.values(), key=lambda x: x["score"], reverse=True
    )
    return plan_aperturas, recursos_ordenados


def imprimir_plan_unificado(usuario: str, rating: float,
                             plan_aperturas: dict, recursos: list) -> None:
    """Imprime el plan de estudio fusionado."""
    _titulo(f"📚 PLAN DE ESTUDIO UNIFICADO — {usuario}  |  {rating:.0f} Elo")

    ICONO_NIVEL = {"sin_base": "⚠️ ", "desarrollo": "📈", "dominio": "✅ "}
    libre_icon  = lambda r: "🆓" if r.get("is_free") == 1 else "💰"

    # ── Aperturas analizadas ────────────────────────────────────────────────
    print(f"\n  {'APERTURA':<33} {'NIVEL':<12} {'FUENTE':<8} {'N':>5} {'ACC':>6}")
    print(f"  {'─'*33} {'─'*12} {'─'*8} {'─'*5} {'─'*6}")

    for ap, meta in sorted(
        plan_aperturas.items(),
        key=lambda x: NIVEL_PRIO.get(x[1].get("nivel", "dominio"), 2)
    ):
        icono  = ICONO_NIVEL.get(meta.get("nivel", ""), "   ")
        fuente = "+".join(sorted(meta["fuentes"]))
        n_p    = meta.get("n_partidas", "—")
        acc    = meta.get("acc_media",  "—")
        nivel  = meta.get("nivel", "—")
        print(f"  {icono} {ap[:28]:<28} {nivel:<12} {fuente:<8} "
              f"{str(n_p):>5} {str(acc):>6}")

    # ── Recursos recomendados ───────────────────────────────────────────────
    print(f"\n\n  {'RECURSOS RECOMENDADOS (ordenados por relevancia, deduplicados)'}")
    print(f"  {SEP2}")

    for i, r in enumerate(recursos[:10], 1):
        fuentes_str = "+".join(sorted(r["fuentes"]))
        doble       = _c("⭐", "amarillo") if len(r["fuentes"]) == 2 else "  "
        print(f"\n  [{i:02d}] {doble} score={r['score']:.2f}  [{fuentes_str}]")
        print(f"       {libre_icon(r)} {r['title'][:60]}")
        if r.get("source"):
            print(f"          {_c(r['source'], 'dim')} · {r.get('level_tier','?')} "
                  f"· {r.get('course_type','?')}")
        if r.get("url"):
            print(f"          {_c(r['url'], 'cyan')}")
        if len(r.get("aperturas", [])) > 1:
            print(f"          📌 Cubre: {', '.join(r['aperturas'][:3])}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. LICHESS STUDY — CREACIÓN OPCIONAL (FASE 3)
# ══════════════════════════════════════════════════════════════════════════════

def subir_estudio_lichess(blunders: list, lichess_token: str,
                           study_id: str) -> None:
    """
    Sube cada posición blunder como capítulo de un estudio de Lichess.
    Solo se llama si el usuario confirma explícitamente.
    """
    _titulo("📖 CREACIÓN DE ESTUDIO EN LICHESS")

    if not blunders:
        _info("No se detectaron blunders durante el análisis.")
        return

    headers = {"Authorization": f"Bearer {lichess_token}"}
    url     = f"https://lichess.org/api/study/{study_id}/import-pgn"
    subidos = 0

    print(f"  Blunders a subir: {len(blunders)}\n")

    for b in blunders:
        fen    = b["fen"]
        campos = fen.strip().split()
        if len(campos) < 4:
            _warn(f"FEN inválido: {fen[:50]}")
            continue
        if len(campos) == 4:
            fen = fen + " 0 1"

        perdida_p = round(float(b["perdida"]) / 100, 1)
        nombre    = f"Blunder -{perdida_p}p | {b['apertura'][:28]}"

        pgn_data = (
            f'[Event "{nombre}"]\n'
            f'[Site "{b["game_id"]}"]\n'
             '[SetUp "1"]\n'
            f'[FEN "{fen}"]\n'
            '\n*'
        )

        try:
            r = requests.post(url, headers=headers,
                              data={"name": nombre, "pgn": pgn_data}, timeout=10)
            if r.status_code == 200:
                _ok(f"Subido: {nombre}")
                subidos += 1
            else:
                _err(f"Error {r.status_code}: {r.text[:80]}")
        except requests.exceptions.Timeout:
            _err("Timeout — Lichess no respondió.")
        except Exception as e:
            _err(f"Error de red: {e}")

    print(f"\n  ✅ {subidos}/{len(blunders)} posiciones subidas al estudio.")
    if subidos:
        print(f"  🔗 https://lichess.org/study/{study_id}")


def preguntar_estudio(blunders: list) -> bool:
    """
    Pregunta al usuario si desea crear el estudio de Lichess.
    Muestra un resumen previo de los blunders detectados.
    """
    if not blunders:
        return False

    print(f"\n{SEP2}")
    print(f"  {_c('📖 CREACIÓN DE ESTUDIO EN LICHESS — OPCIONAL', 'bold')}")
    print(SEP2)
    print(f"\n  Se detectaron {_c(str(len(blunders)), 'bold')} posiciones blunder durante el análisis:")

    for i, b in enumerate(blunders[:8], 1):
        print(f"    {i}. {b['apertura'][:35]:<35} | -{b['perdida']:.0f} CP "
              f"| partida: {b['game_id']}")
    if len(blunders) > 8:
        print(f"    ... y {len(blunders) - 8} más.")

    print()
    while True:
        resp = input("  ¿Deseas subir estas posiciones a tu estudio de Lichess? [s/n]: ").strip().lower()
        if resp in ("s", "si", "sí", "y", "yes"):
            return True
        if resp in ("n", "no"):
            print("  ↳ Estudio omitido.")
            return False
        print("  Responde 's' para sí o 'n' para no.")


# ══════════════════════════════════════════════════════════════════════════════
# 7. ORQUESTADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def orquestar(username:       str,
              lichess_token:  str,
              max_partidas:   int          = 50,
              usar_stockfish: bool         = True,
              study_id:       Optional[str] = None) -> None:
    """
    Pipeline completo: análisis → dashboard → ranking → recomendación → estudio.

    Parameters
    ----------
    username       : nombre de usuario en Lichess.
    lichess_token  : token OAuth de la API de Lichess.
    max_partidas   : número máximo de partidas a analizar.
    usar_stockfish : si False, omite la evaluación de engine (solo teoría).
    study_id       : ID del estudio de Lichess para los blunders (opcional).
    """
    t_inicio = time.time()

    print(f"\n{'═'*70}")
    print(f"  {_c('♟  CHESS INTELLIGENCE SYSTEM', 'bold')}".center(80))
    print(f"  Usuario: {_c(username, 'cyan')}  |  "
          f"Partidas: {max_partidas}  |  "
          f"Engine: {'✅' if usar_stockfish else '⛔'}")
    print(f"{'═'*70}")

    # ── Inicializar cliente Lichess ──────────────────────────────────────────
    _titulo("🔌 CONEXIÓN CON LICHESS")
    try:
        client = berserk.Client(berserk.TokenSession(lichess_token))
    except Exception as e:
        _err(f"No se pudo conectar con Lichess: {e}")
        return

    # ── FASE 1: ANÁLISIS ─────────────────────────────────────────────────────
    _titulo("🔍 FASE 1 — ANÁLISIS DE PARTIDAS")

    # 1.1 Descargar partidas
    games, rating = descargar_partidas(client, username, max_partidas)
    if not games:
        _err("No se pudieron descargar partidas. Abortando.")
        return

    # 1.2 + 1.3 Análisis teórico + Stockfish
    sf_path = STOCKFISH_EXE if (usar_stockfish and STOCKFISH_AVAILABLE) else None
    system  = ChessIntelligenceSystem(stockfish_path=sf_path)

    print(f"\n  Analizando {len(games)} partidas...\n")
    df_nuevas = system.analizar_partidas(games, username, rating)

    if df_nuevas.empty:
        _err("El análisis no produjo resultados. Comprueba los logs.")
        return

    # 1.4 Persistencia incremental
    _titulo("💾 GUARDANDO RESULTADOS")
    df_maestro = guardar_incrementalmente(df_nuevas)

    # Filtrar solo las partidas del usuario actual para el análisis
    df_usuario = df_maestro[df_maestro["Usuario"] == username].copy()

    # 1.5 Dashboard de aperturas
    _titulo("📊 DASHBOARD DE APERTURAS")
    df_dashboard = generar_dashboard(df_maestro, username)
    imprimir_dashboard(df_dashboard, username)

    # 1.6 Clasificación KMeans
    df_usuario = clasificar_aperturas_kmeans(df_usuario)
    imprimir_ranking_kmeans(df_usuario)

    # ── FASE 2: RECOMENDACIÓN ────────────────────────────────────────────────
    _titulo("📚 FASE 2 — RECOMENDACIÓN DE MATERIALES")

    if not RECURSOS_CSV.exists():
        _warn(f"Catálogo de recursos no encontrado: {RECURSOS_CSV}")
        _warn("Omitiendo fase de recomendación.")
    else:
        df_rec = pd.read_csv(RECURSOS_CSV)
        _ok(f"Catálogo cargado: {len(df_rec)} recursos.")

        # 2.1 Recomendador por perfil directo
        recs_perfil, _ = recomendar_perfil_directo(
            username, df_usuario, df_rec,
            top_n_aperturas=5, top_n_recursos=3
        )

        # 2.2 Recomendador KNN
        recs_knn, _    = recomendar_knn(
            username, df_maestro, df_rec,
            top_n_recursos=3, k=5
        )

        # 2.3 Plan unificado
        if recs_perfil or recs_knn:
            plan_ap, recursos_ord = fusionar_planes(recs_perfil, recs_knn, rating)
            imprimir_plan_unificado(username, rating, plan_ap, recursos_ord)
        else:
            _warn("Sin recomendaciones disponibles (puede que no haya aperturas con ≥5 partidas).")

    # ── FASE 3: ESTUDIO LICHESS OPCIONAL ────────────────────────────────────
    blunders = system.blunders
    if blunders and study_id:
        if preguntar_estudio(blunders):
            subir_estudio_lichess(blunders, lichess_token, study_id)
    elif blunders and not study_id:
        _info(f"Se detectaron {len(blunders)} blunders pero no se configuró STUDY_ID.")
        _info("Añade --study-id <ID> para habilitar la creación del estudio.")

    # ── Resumen de tiempo ────────────────────────────────────────────────────
    elapsed = time.time() - t_inicio
    print(f"\n{SEP}")
    _ok(f"Pipeline completado en {elapsed:.1f}s  ({elapsed/60:.1f} min)")
    print(SEP)


# ══════════════════════════════════════════════════════════════════════════════
# 8. PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

def _modo_interactivo() -> dict:
    """Solicita los parámetros necesarios al usuario por consola."""
    print(f"\n{'═'*70}")
    print("  ♟  CHESS INTELLIGENCE SYSTEM — Modo interactivo".center(70))
    print(f"{'═'*70}\n")

    token    = input("  Token de Lichess (lip_...): ").strip()
    usuario  = input("  Nombre de usuario en Lichess: ").strip()
    n_str    = input("  Número de partidas a analizar [50]: ").strip()
    n        = int(n_str) if n_str.isdigit() else 50
    engine   = input("  ¿Usar Stockfish? [S/n]: ").strip().lower()
    study    = input("  ID del estudio Lichess para blunders (Enter para omitir): ").strip()

    return {
        "username":       usuario,
        "lichess_token":  token,
        "max_partidas":   n,
        "usar_stockfish": engine not in ("n", "no"),
        "study_id":       study or None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chess Intelligence System — Orquestador",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Ejemplos:
              python orquestador.py
              python orquestador.py --usuario tecojoytetruqueo --token lip_xxx --partidas 30
              python orquestador.py --usuario tecojoytetruqueo --token lip_xxx --sin-stockfish
              python orquestador.py --usuario tecojoytetruqueo --token lip_xxx --study-id bomPuW2h
        """),
    )
    parser.add_argument("--usuario",       type=str, help="Nombre de usuario en Lichess")
    parser.add_argument("--token",         type=str, help="Token OAuth de Lichess (lip_...)")
    parser.add_argument("--partidas",      type=int, default=50, help="Número de partidas [50]")
    parser.add_argument("--sin-stockfish", action="store_true",  help="Omitir análisis con engine")
    parser.add_argument("--study-id",      type=str, default=None, help="ID de estudio Lichess para blunders")
    args = parser.parse_args()

    # Si no se pasan argumentos clave, modo interactivo
    if not args.usuario or not args.token:
        params = _modo_interactivo()
    else:
        params = {
            "username":       args.usuario,
            "lichess_token":  args.token,
            "max_partidas":   args.partidas,
            "usar_stockfish": not args.sin_stockfish,
            "study_id":       args.study_id,
        }

    orquestar(**params)


if __name__ == "__main__":
    main()
