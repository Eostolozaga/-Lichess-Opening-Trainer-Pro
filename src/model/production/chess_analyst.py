"""
chess_analyst.py  ─  Orquestador End-to-End del Sistema de Análisis de Ajedrez
═══════════════════════════════════════════════════════════════════════════════

FLUJO COMPLETO:
  1. Descarga partidas vía API Lichess  (ChessIntelligenceSystem)
  2. Evalúa con Stockfish + cruza teoría  → master_dataset_ml.csv
  3. Clasifica al usuario con K-means     → grupo (principiante / intermedio / avanzado)
  4. Construye ML DataFrame + etiqueta aperturas  (label_apertura)
  5. Genera ranking de aperturas por prioridad
  6. Recomienda cursos/libros             → plan de estudio imprimible

USO:
  python chess_analyst.py --user tecojoytetruqueo
  python chess_analyst.py --user tecojoytetruqueo --max-games 100 --top-n 5

DEPENDENCIAS (ya existen en tus notebooks):
  chess_intelligence_system  ← ChessIntelligenceSystem  (del Esqueleto)
  eda_cursos                 ← build_ml_dataframe, recomendar_recursos, etc.

  Si aún no has exportado esos módulos, puedes copiar las clases/funciones
  directamente en este archivo (sección PASTE-ZONE al final).
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import argparse
import io
import os
import pickle
import re
import sys
import warnings
from pathlib import Path

import berserk
import chess
import chess.pgn
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from stockfish import Stockfish

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN CENTRALIZADA  ← edita sólo aquí
# ─────────────────────────────────────────────────────────────────────────────
CFG = {
    "stockfish_path": r"C:\Users\Eneko\Desktop\stockfish-windows-x86-64-avx2.exe",
    "pkl_path":       "theory_db.pkl",
    "lichess_token":  os.getenv("LICHESS_TOKEN", ""),
    "master_csv":     "master_dataset_ml.csv",
    "resources_csv":  "chess_resources_v2.csv",
    "study_id":       "bomPuW2h",   # ID del estudio Lichess donde se suben los blunders
    "blunder_threshold_cp": 100,    # pérdida mínima en centipeones para considerar blunder
    "max_games":      50,
    "top_n_recursos": 3,
    "min_games_label": 5,
    "kmeans_seed":    42,
}

# ─────────────────────────────────────────────────────────────────────────────
# GRUPOS — única fuente de verdad (copiada de EDA_Cursos)
# ─────────────────────────────────────────────────────────────────────────────
GRUPOS = {
    "principiante": {
        "rating_min": 0,    "rating_max": 1399,
        "label_tier": "beginner",
        "acc_low": 55,      "acc_high": 65,
        "teo_low": 4,       "teo_high": 9,
        "study_focus": ["general", "tactics", "opening"],
        "avoid_types": [],
        "acc_high_global": 65,
    },
    "intermedio": {
        "rating_min": 1400, "rating_max": 1999,
        "label_tier": "intermediate",
        "acc_low": 63,      "acc_high": 74,
        "teo_low": 5,       "teo_high": 11,
        "study_focus": ["opening", "middlegame", "tactics"],
        "avoid_types": [],
        "acc_high_global": 74,
    },
    "avanzado": {
        "rating_min": 2000, "rating_max": 9999,
        "label_tier": "advanced",
        "acc_low": 72,      "acc_high": 82,
        "teo_low": 7,       "teo_high": 13,
        "study_focus": ["opening", "endgame", "middlegame"],
        "avoid_types": ["general"],
        "acc_high_global": 82,
    },
}

LABEL_PRIORITY = {
    "PUNTO_CRITICO": 1,
    "TEORIA_VACIA":  2,
    "NEUTRO":        3,
    "EXITO_NATURAL": 4,
    "DOMINIO":       5,
    "VOLUMEN_BAJO":  99,
}

LABEL_COURSE_TYPE = {
    "PUNTO_CRITICO": ["opening",    "general"],
    "TEORIA_VACIA":  ["opening",    "middlegame"],
    "EXITO_NATURAL": ["middlegame", "general"],
    "DOMINIO":       ["endgame",    "tactics"],
    "NEUTRO":        ["tactics",    "general"],
}

LABEL_EMOJI = {
    "PUNTO_CRITICO": "🔴",
    "TEORIA_VACIA":  "🟠",
    "NEUTRO":        "🟡",
    "EXITO_NATURAL": "🟢",
    "DOMINIO":       "🏆",
    "VOLUMEN_BAJO":  "⚪",
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def acl_to_accuracy(acl: float) -> float:
    return round(max(0.0, min(100.0, 100 * np.exp(-0.0035 * acl))), 1)


def get_grupo(rating: float) -> str:
    for nombre, cfg in GRUPOS.items():
        if cfg["rating_min"] <= rating <= cfg["rating_max"]:
            return nombre
    return "avanzado"


def get_grupo_cfg(rating: float) -> dict:
    return GRUPOS[get_grupo(rating)]


# ─────────────────────────────────────────────────────────────────────────────
# LICHESS STUDY — SUBIDA DE BLUNDERS
# ─────────────────────────────────────────────────────────────────────────────

def subir_error_a_estudio(
    game_id:  str,
    apertura: str,
    fen:      str,
    perdida:  float,
    study_id: str | None = None,
) -> bool:
    """
    Sube la posición del blunder como nuevo capítulo al estudio de Lichess.
    Endpoint: POST /api/study/{studyId}/import-pgn

    Correcciones aplicadas (igual que en el Esqueleto):
      1. URL correcta al endpoint de capítulos (no a la raíz)
      2. SetUp va ANTES que FEN en el bloque de tags PGN
      3. FEN completado a 6 campos si viene de board.epd() (4 campos)
      4. Nombre de capítulo truncado para evitar límite de Lichess
    """
    sid = study_id or CFG["study_id"]

    # Validar y completar FEN (board.fen()=6 campos, board.epd()=4)
    fen_campos = fen.strip().split()
    if len(fen_campos) < 4:
        print(f"   ❌ FEN inválido ({len(fen_campos)} campos): {fen[:50]}")
        return False
    if len(fen_campos) == 4:
        fen = fen + " 0 1"

    perdida_peon = round(float(perdida) / 100, 1)
    nombre_cap   = f"Blunder -{perdida_peon}p | {apertura[:28]}"

    # PGN: SetUp ANTES de FEN (requisito del parser de Lichess)
    pgn_data = (
        f'[Event "{nombre_cap}"]\n'
        f'[Site "{game_id}"]\n'
         '[SetUp "1"]\n'
        f'[FEN "{fen}"]\n'
        '\n*'
    )

    url     = f"https://lichess.org/api/study/{sid}/import-pgn"
    headers = {"Authorization": f"Bearer {CFG['lichess_token']}"}
    payload = {"name": nombre_cap, "pgn": pgn_data}

    try:
        r = requests.post(url, headers=headers, data=payload, timeout=10)
        if r.status_code == 200:
            print("   ✨ Posición subida.")
            return True
        # 400=PGN malformado, 401=token inválido, 403=sin permisos en el estudio
        print(f"   ❌ Lichess {r.status_code}: {r.text[:120]}")
        return False
    except requests.exceptions.Timeout:
        print("   ❌ Timeout — Lichess no respondió en 10s")
        return False
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False


def subir_blunders_del_usuario(
    df_usuario_raw: pd.DataFrame,
    system,                        # ChessIntelligenceSystem
    games_cache: list,             # lista de objetos chess.pgn.Game ya descargados
    study_id: str | None = None,
) -> int:
    """
    Recorre las partidas del usuario buscando el peor blunder de cada una
    (ACL_Post_Teo > blunder_threshold_cp) y lo sube al estudio de Lichess.

    Devuelve el número de capítulos subidos.
    """
    threshold = CFG["blunder_threshold_cp"]
    subidos   = 0

    # Índice rápido game_id → objeto Game
    game_index: dict = {}
    for g in games_cache:
        gid = g.headers.get("Site", "").split("/")[-1]
        if gid:
            game_index[gid] = g

    for _, row in df_usuario_raw.iterrows():
        if row["ACL_Post_Teo"] <= threshold:
            continue

        game_id  = str(row["Game_ID"])
        apertura = str(row["Apertura"])
        game_obj = game_index.get(game_id)

        if game_obj is None:
            continue  # partida no disponible en caché

        # Reproducir hasta el punto de salida de teoría para obtener el FEN
        try:
            board      = game_obj.board()
            moves      = list(game_obj.mainline_moves())
            fin_teoria = int(row.get("Fin_Teoria", 0))
            color_str  = str(row.get("Color", "Blancas"))
            player_col = chess.WHITE if color_str == "Blancas" else chess.BLACK

            for m in moves[:fin_teoria]:
                board.push(m)

            # Buscar la jugada exacta que causó el mayor loss en la ventana post-teoría
            eval_prev = system.get_eval(board.fen())
            worst_fen  = board.fen()
            worst_loss = 0.0
            side = 1.0 if player_col == chess.WHITE else -1.0

            for m in moves[fin_teoria: fin_teoria + 12]:
                is_player = (board.turn == player_col)
                fen_antes  = board.fen()
                board.push(m)
                eval_now = system.get_eval(board.fen())

                if is_player:
                    loss = float(max(0.0, (eval_prev - eval_now) * side))
                    if loss > worst_loss:
                        worst_loss = loss
                        worst_fen  = fen_antes  # posición ANTES del error

                eval_prev = eval_now

            if worst_loss > threshold:
                print(f"   ⚠️  Blunder en '{apertura}' ({worst_loss:.0f}cp). Subiendo...")
                ok = subir_error_a_estudio(
                    game_id  = game_id,
                    apertura = apertura,
                    fen      = worst_fen,
                    perdida  = worst_loss,
                    study_id = study_id,
                )
                if ok:
                    subidos += 1

        except Exception as e:
            print(f"   ⚠️  Error procesando blunder de {game_id}: {e}")

    return subidos


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1 — CLASIFICADOR K-MEANS
#   Entrena con el master CSV existente y devuelve el grupo del usuario nuevo.
#   Si el master aún no tiene suficientes datos, usa reglas de rating directo.
# ─────────────────────────────────────────────────────────────────────────────

def clasificar_usuario_kmeans(rating: float, df_master: pd.DataFrame) -> str:
    """
    Usa K-Means (k=3) sobre [Rating_Usuario, Accuracy_Pct, Fin_Teoria]
    para asignar grupo. Fallback a reglas si df_master es pequeño.
    """
    MIN_FILAS = 30  # mínimo para que K-Means tenga sentido

    if df_master is None or len(df_master) < MIN_FILAS:
        return get_grupo(rating)

    features = ["Rating_Usuario", "ACL_Post_Teo", "Fin_Teoria"]
    df_clean = df_master[features].dropna().copy()
    df_clean["Accuracy_Pct"] = df_clean["ACL_Post_Teo"].apply(acl_to_accuracy)

    X = df_clean[["Rating_Usuario", "Accuracy_Pct", "Fin_Teoria"]].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=3, random_state=CFG["kmeans_seed"], n_init=10)
    km.fit(X_scaled)

    # Identificar qué cluster corresponde a cada grupo por rating medio
    df_clean["cluster"] = km.labels_
    medias = df_clean.groupby("cluster")["Rating_Usuario"].mean().sort_values()
    cluster_to_grupo = {
        medias.index[0]: "principiante",
        medias.index[1]: "intermedio",
        medias.index[2]: "avanzado",
    }

    # Clasificar al usuario nuevo
    user_acc = acl_to_accuracy(
        df_master[df_master["Rating_Usuario"].between(rating - 200, rating + 200)]["ACL_Post_Teo"].mean()
        if not df_master.empty else 70
    )
    user_teo = (
        df_master[df_master["Rating_Usuario"].between(rating - 200, rating + 200)]["Fin_Teoria"].mean()
        if not df_master.empty else 8
    )

    user_point = scaler.transform([[rating, user_acc, user_teo]])
    cluster_pred = km.predict(user_point)[0]
    return cluster_to_grupo.get(cluster_pred, get_grupo(rating))


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2 — ETIQUETADO DE APERTURAS (de EDA_Cursos)
# ─────────────────────────────────────────────────────────────────────────────

def label_apertura(row: pd.Series) -> str:
    MIN_GAMES = CFG["min_games_label"]

    if row["n_games"] < MIN_GAMES:
        return "VOLUMEN_BAJO"

    cfg     = get_grupo_cfg(row["Rating_Usuario"])
    acc     = row["Accuracy_Pct"]
    teo     = row["Fin_Teoria_Med"]
    vol_rel = row["vol_rel"]

    acc_high = acc  >= cfg["acc_high"]
    acc_low  = acc  <  cfg["acc_low"]
    teo_high = teo  >= cfg["teo_high"]
    teo_low  = teo  <= cfg["teo_low"]
    high_vol = vol_rel >= 0.15

    if teo_low  and acc_high: return "EXITO_NATURAL"
    if teo_high and acc_high: return "DOMINIO"
    if teo_high and acc_low:  return "TEORIA_VACIA"
    if high_vol and acc_low:  return "PUNTO_CRITICO"
    return "NEUTRO"


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3 — BUILD ML DATAFRAME (de EDA_Cursos)
# ─────────────────────────────────────────────────────────────────────────────

def build_ml_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df["Accuracy_Pct"] = df["ACL_Post_Teo"].apply(acl_to_accuracy)

    agg = df.groupby(["Usuario", "Apertura", "Color"], observed=True).agg(
        n_games         = ("Game_ID",        "count"),
        Rating_Usuario  = ("Rating_Usuario", "mean"),
        Fin_Teoria_Med  = ("Fin_Teoria",     "mean"),
        Fin_Teoria_Std  = ("Fin_Teoria",     "std"),
        ACL_Med         = ("ACL_Post_Teo",   "mean"),
        ACL_Std         = ("ACL_Post_Teo",   "std"),
        Accuracy_Pct    = ("Accuracy_Pct",   "mean"),
        Win_Rate        = ("Victoria",       "mean"),
        ACL_P25         = ("ACL_Post_Teo",   lambda x: np.percentile(x, 25)),
        ACL_P75         = ("ACL_Post_Teo",   lambda x: np.percentile(x, 75)),
    ).reset_index()

    total_por_usuario = (
        df.groupby("Usuario")["Game_ID"].count().rename("total_user_games")
    )
    agg = agg.merge(total_por_usuario, on="Usuario")
    agg["vol_rel"]      = agg["n_games"] / agg["total_user_games"]
    agg["consistency"]  = 1 - (agg["ACL_Std"] / (agg["ACL_Med"] + 1e-6)).clip(0, 1)
    agg["teo_acc_gap"]  = agg["Fin_Teoria_Med"] - (agg["Accuracy_Pct"] / 10)
    agg["grupo"]        = agg["Rating_Usuario"].apply(get_grupo)
    agg["color_enc"]    = (agg["Color"] == "Blancas").astype(int)
    agg["label"]        = agg.apply(label_apertura, axis=1)

    return agg


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4 — RECOMENDADOR DE RECURSOS (de EDA_Cursos)
# ─────────────────────────────────────────────────────────────────────────────

def recomendar_recursos(
    perfil: pd.Series,
    df_recursos: pd.DataFrame,
    top_n: int = 3,
) -> pd.DataFrame:

    cfg       = get_grupo_cfg(perfil["Rating_Usuario"])
    label     = perfil["label"]
    apertura  = perfil["Apertura"].split(":")[0].split(",")[0].strip().lower()
    color_en  = "white" if perfil["Color"] == "Blancas" else "black"
    accuracy  = perfil["Accuracy_Pct"]

    df_r = df_recursos.copy()

    # Filtro duro: rango de nivel
    df_r = df_r[
        (df_r["level_min"].fillna(0)    <= perfil["Rating_Usuario"]) &
        (df_r["level_max"].fillna(9999) >= perfil["Rating_Usuario"])
    ]

    if cfg["avoid_types"]:
        df_r = df_r[~df_r["course_type"].isin(cfg["avoid_types"])]

    df_r = df_r.copy()
    df_r["score"] = 0.0

    # A) Coincidencia de apertura (+40)
    df_r["score"] += (
        df_r["openings"].fillna("").str.lower().str.contains(apertura, regex=False)
        .astype(float) * 40
    )
    # B) Color (+10/+5)
    df_r["score"] += df_r["color"].fillna("Both").str.lower().apply(
        lambda c: 10 if c == color_en else (5 if c == "both" else 0)
    )
    # C) Tipo de curso según label (+20/+10)
    preferred = LABEL_COURSE_TYPE.get(label, ["general"])
    df_r["score"] += df_r["course_type"].fillna("").apply(
        lambda t: 20 if t == preferred[0] else (10 if t in preferred else 0)
    )
    # D) Bonus focus de grupo (+8)
    df_r["score"] += df_r["course_type"].fillna("").apply(
        lambda t: 8 if t in cfg["study_focus"] else 0
    )
    # E) Calidad del recurso
    if "popularity_score" in df_r.columns:
        df_r["score"] += df_r["popularity_score"].fillna(0) * 5
    if "richness_score" in df_r.columns:
        df_r["score"] += df_r["richness_score"].fillna(0) * 5
    # F) Penalización si accuracy ya es alta
    if accuracy >= cfg["acc_high"] and label not in ["PUNTO_CRITICO", "TEORIA_VACIA"]:
        df_r["score"] -= df_r["course_type"].eq("opening").astype(float) * 15

    cols_out = [c for c in ["title", "source", "resource_type", "course_type",
                             "price_eur", "url"] if c in df_r.columns]
    return df_r.nlargest(top_n, "score")[cols_out].reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# PASO 5 — RANKING DE APERTURAS
# ─────────────────────────────────────────────────────────────────────────────

def ranking_aperturas(df_user_ml: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve las aperturas del usuario ordenadas por prioridad de estudio.
    Excluye VOLUMEN_BAJO del ranking principal.
    """
    df = df_user_ml.copy()
    df["prioridad"] = df["label"].map(LABEL_PRIORITY).fillna(99)
    df = df[df["label"] != "VOLUMEN_BAJO"].copy()
    return (
        df.sort_values(["prioridad", "Accuracy_Pct"])
          .reset_index(drop=True)
    )


# ─────────────────────────────────────────────────────────────────────────────
# PASO 6 — PLAN DE ESTUDIO COMPLETO
# ─────────────────────────────────────────────────────────────────────────────

def generar_plan_estudio(
    df_user_ml: pd.DataFrame,
    df_recursos: pd.DataFrame,
    top_n: int = 3,
) -> dict:
    ranking = ranking_aperturas(df_user_ml)
    plan = {}
    for _, row in ranking.iterrows():
        key = f"{row['Apertura']} ({row['Color']})"
        plan[key] = {
            "label":      row["label"],
            "prioridad":  row["prioridad"],
            "accuracy":   row["Accuracy_Pct"],
            "teoria_med": row["Fin_Teoria_Med"],
            "win_rate":   row["Win_Rate"],
            "n_games":    row["n_games"],
            "recursos":   recomendar_recursos(row, df_recursos, top_n=top_n),
        }
    return plan


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT — IMPRESIÓN DEL INFORME FINAL
# ─────────────────────────────────────────────────────────────────────────────

def imprimir_informe(
    usuario: str,
    rating: float,
    grupo: str,
    plan: dict,
) -> None:
    W = 82
    print("\n" + "═" * W)
    print(f"  ♟  INFORME DE REPERTORIO — {usuario.upper()}".center(W))
    print("═" * W)
    print(f"  Rating: {int(rating)}  │  Grupo K-Means: {grupo.upper()}")
    print("─" * W)

    if not plan:
        print("  ⚠️  No hay aperturas con volumen suficiente para analizar.")
        print("═" * W)
        return

    # Tabla resumen
    print(f"\n  {'#':<3} {'APERTURA':<35} {'LABEL':<15} {'ACC%':>5} {'TEO':>5} {'WR%':>5} {'N':>4}")
    print("  " + "─" * (W - 2))
    for i, (apertura, datos) in enumerate(plan.items(), 1):
        emoji = LABEL_EMOJI.get(datos["label"], "")
        lbl   = f"{emoji} {datos['label']}"
        print(
            f"  {i:<3} {apertura:<35} {lbl:<17} "
            f"{datos['accuracy']:>5.1f} {datos['teoria_med']:>5.1f} "
            f"{datos['win_rate']*100:>5.1f} {datos['n_games']:>4}"
        )

    # Detalle con recursos por apertura
    print("\n" + "═" * W)
    print("  PLAN DE ESTUDIO DETALLADO".center(W))
    print("═" * W)

    for apertura, datos in plan.items():
        emoji = LABEL_EMOJI.get(datos["label"], "")
        print(f"\n  {emoji} {apertura}")
        print(f"     Label: {datos['label']}  │  Acc: {datos['accuracy']}%  │  "
              f"Teoría: {datos['teoria_med']:.1f}j  │  WR: {datos['win_rate']*100:.0f}%  │  "
              f"Partidas: {datos['n_games']}")

        _EXPLICACIONES = {
            "PUNTO_CRITICO": "Alto volumen pero precisión baja → estudiar o cambiar apertura.",
            "TEORIA_VACIA":  "Conoces las líneas pero juegas mal después → trabajar el middlegame.",
            "EXITO_NATURAL": "Poca teoría, buena precisión → consolida y profundiza.",
            "DOMINIO":       "Dominas esta apertura. Enfócate en finales y táctica.",
            "NEUTRO":        "Rendimiento medio. Mejora táctica general.",
        }
        print(f"     💡 {_EXPLICACIONES.get(datos['label'], '')}")

        rec = datos["recursos"]
        if rec.empty:
            print("     📚 Sin recursos específicos disponibles en la base de datos.")
        else:
            print("     📚 Recursos recomendados:")
            for _, r in rec.iterrows():
                precio = f"€{r['price_eur']:.0f}" if "price_eur" in r and pd.notna(r.get("price_eur")) else ""
                fuente = r.get("source", r.get("resource_type", ""))
                url    = f"  → {r['url']}" if "url" in r and pd.notna(r.get("url")) else ""
                print(f"       • {r['title']}  [{fuente}] {precio}{url}")

    print("\n" + "═" * W + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def analizar_usuario(
    username: str,
    max_games: int = CFG["max_games"],
    top_n: int     = CFG["top_n_recursos"],
    skip_download: bool = False,
) -> dict:
    """
    Punto de entrada único.
    Retorna el dict del plan de estudio (también lo imprime).
    """

    print(f"\n{'─'*50}")
    print(f"  🚀 INICIANDO ANÁLISIS: {username}")
    print(f"{'─'*50}")

    # ── 1. MOTOR + TEORÍA ────────────────────────────────────────────────────
    try:
        from chess_intelligence_system import ChessIntelligenceSystem  # type: ignore
    except ImportError:
        # Si no está como módulo separado, asume que ya está en el namespace
        # (ejecución desde el mismo notebook/script que define la clase)
        ChessIntelligenceSystem = _get_chess_intelligence_system()

    system = ChessIntelligenceSystem(CFG["stockfish_path"])
    client = berserk.Client(berserk.TokenSession(CFG["lichess_token"]))

    # ── 2. RATING DEL USUARIO ────────────────────────────────────────────────
    perfil_lichess = client.users.get_public_data(username)
    perfs = perfil_lichess.get("perfs", {})
    rating = (
        perfs.get("blitz", {}).get("rating", 0)
        or perfs.get("rapid", {}).get("rating", 0)
        or perfs.get("classical", {}).get("rating", 0)
    )
    print(f"  📊 Rating detectado: {rating}")

    if rating == 0:
        print(f"  ⚠️  Sin rating activo en Lichess.")
        return {}

    # ── 3. DESCARGA Y ANÁLISIS ───────────────────────────────────────────────
    master_path = CFG["master_csv"]
    df_master   = pd.read_csv(master_path) if os.path.exists(master_path) else None

    if not skip_download:
        print(f"  📥 Descargando hasta {max_games} partidas...")
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

        if not games:
            print("  ❌ No se encontraron partidas.")
            return {}

        print(f"  🔍 Analizando {len(games)} partidas con Stockfish...")
        df_nuevos = system.analyze_games(games, username, rating)

        # Persistencia
        if df_master is not None:
            df_master = (
                pd.concat([df_master, df_nuevos])
                .drop_duplicates(subset=["Game_ID"], keep="first")
            )
        else:
            df_master = df_nuevos

        df_master.to_csv(master_path, index=False)
        print(f"  ✅ Dataset actualizado → {len(df_master)} registros totales.")

        # ── 3b. SUBIDA DE BLUNDERS AL ESTUDIO DE LICHESS ─────────────────────
        df_user_raw = df_nuevos[df_nuevos["Usuario"] == username].copy()
        if not df_user_raw.empty and CFG.get("study_id"):
            print(f"  📤 Subiendo blunders al estudio Lichess ({CFG['study_id']})...")
            n_subidos = subir_blunders_del_usuario(
                df_usuario_raw = df_user_raw,
                system         = system,
                games_cache    = games,
            )
            if n_subidos:
                print(f"  ✅ {n_subidos} blunder(s) subido(s) → "
                      f"https://lichess.org/study/{CFG['study_id']}")
            else:
                print("  ℹ️  Sin blunders nuevos por encima del umbral "
                      f"({CFG['blunder_threshold_cp']}cp).")

    # ── 4. K-MEANS: CLASIFICAR GRUPO ─────────────────────────────────────────
    grupo = clasificar_usuario_kmeans(rating, df_master)
    print(f"  🎯 Grupo asignado (K-Means): {grupo.upper()}")

    # ── 5. ML DATAFRAME + ETIQUETADO ─────────────────────────────────────────
    df_ml   = build_ml_dataframe(df_master)
    df_user = df_ml[df_ml["Usuario"] == username].copy()

    if df_user.empty:
        print("  ⚠️  Sin datos suficientes para este usuario en el dataset.")
        return {}

    # Sobreescribe el grupo con el resultado K-Means
    df_user["grupo"] = grupo

    # ── 6. RECURSOS ──────────────────────────────────────────────────────────
    resources_path = CFG["resources_csv"]
    if not os.path.exists(resources_path):
        print(f"  ⚠️  No se encontró '{resources_path}'. Se omiten recomendaciones.")
        df_recursos = pd.DataFrame()
    else:
        df_recursos = pd.read_csv(resources_path)

    # ── 7. PLAN DE ESTUDIO ───────────────────────────────────────────────────
    plan = generar_plan_estudio(df_user, df_recursos, top_n=top_n)

    # ── 8. IMPRIMIR INFORME ──────────────────────────────────────────────────
    imprimir_informe(username, rating, grupo, plan)

    return plan


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK: si ChessIntelligenceSystem no está como módulo independiente,
# importa la definición inline aquí (pega la clase del Esqueleto en esta función)
# ─────────────────────────────────────────────────────────────────────────────

def _get_chess_intelligence_system():
    """
    Devuelve ChessIntelligenceSystem si se ejecuta como script standalone
    y la clase no está en un módulo separado.
    Copia aquí la definición completa de la clase del Esqueleto.
    """
    raise ImportError(
        "ChessIntelligenceSystem no encontrada. Opciones:\n"
        "  a) Guarda el Esqueleto como 'chess_intelligence_system.py'\n"
        "  b) Pega la clase directamente en _get_chess_intelligence_system()"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Chess Repertoire Analyst — análisis end-to-end de un usuario Lichess"
    )
    parser.add_argument("--user",         required=True,          help="Username de Lichess")
    parser.add_argument("--max-games",    type=int, default=50,   help="Partidas a descargar (def: 50)")
    parser.add_argument("--top-n",        type=int, default=3,    help="Recursos por apertura (def: 3)")
    parser.add_argument("--skip-download", action="store_true",   help="Salta la descarga, usa CSV existente")
    args = parser.parse_args()

    analizar_usuario(
        username      = args.user,
        max_games     = args.max_games,
        top_n         = args.top_n,
        skip_download = args.skip_download,
    )


if __name__ == "__main__":
    main()
