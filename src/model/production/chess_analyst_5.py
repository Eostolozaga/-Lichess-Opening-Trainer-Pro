"""
chess_analyst.py  ─  Orquestador End-to-End
════════════════════════════════════════════
USO:
  python chess_analyst.py --user tecojoytetruqueo
  python chess_analyst.py --user JanistanTV --max-games 100 --top-n 5
  python chess_analyst.py --user tecojoytetruqueo --skip-download
"""

import argparse
import io
import os
import sys

# Añade src/util al path para encontrar los módulos exportados
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "util"))

import berserk
import chess
import chess.pgn
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ── Módulos exportados desde los notebooks ────────────────────────────────────
from chess_intelligence_system import (
    ChessIntelligenceSystem,
    subir_error_a_estudio,
    generar_dashboard_tecnico_v11,
    imprimir_dashboard,
)
from eda_cursos import (
    build_ml_dataframe,
    generar_plan_estudio,
    get_grupo,
    acl_to_accuracy,
    label_apertura,
    recomendar_recursos,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN CENTRALIZADA
# ─────────────────────────────────────────────────────────────────────────────
CFG = {
    "stockfish_path":       r"C:\Users\Eneko\Desktop\stockfish-windows-x86-64-avx2.exe",
    "pkl_path":             r"C:\Users\Eneko\Desktop\Ejercicios Data\Proyectos\Proyecto ML\src\data\PKL\theory_db.pkl",
    "lichess_token":        os.getenv("LICHESS_TOKEN", ""),
    "master_csv":           r"C:\Users\Eneko\Desktop\Ejercicios Data\Proyectos\Proyecto ML\src\data\CSV\master_dataset_ml.csv",
    "resources_csv":        r"C:\Users\Eneko\Desktop\Ejercicios Data\Proyectos\Proyecto ML\src\data\CSV\chess_resources_v2.csv",
    "study_id":             "bomPuW2h",
    "blunder_threshold_cp": 100,
    "max_games":            50,
    "top_n_recursos":       3,
    "min_games_label":      5,
    "kmeans_seed":          42,
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES QUE NO ESTÁN EN LOS NOTEBOOKS — viven solo aquí
# ─────────────────────────────────────────────────────────────────────────────

LABEL_EMOJI = {
    "PUNTO_CRITICO": "🔴",
    "TEORIA_VACIA":  "🟠",
    "NEUTRO":        "🟡",
    "EXITO_NATURAL": "🟢",
    "DOMINIO":       "🏆",
    "VOLUMEN_BAJO":  "⚪",
}

LABEL_PRIORITY = {
    "PUNTO_CRITICO": 1,
    "TEORIA_VACIA":  2,
    "NEUTRO":        3,
    "EXITO_NATURAL": 4,
    "DOMINIO":       5,
    "VOLUMEN_BAJO":  99,
}

LABEL_EXPLICACION = {
    "PUNTO_CRITICO": "Alto volumen pero precisión baja → estudiar o cambiar apertura.",
    "TEORIA_VACIA":  "Conoces las líneas pero juegas mal después → trabajar el middlegame.",
    "EXITO_NATURAL": "Poca teoría, buena precisión → consolida y profundiza.",
    "DOMINIO":       "Dominas esta apertura. Enfócate en finales y táctica.",
    "NEUTRO":        "Rendimiento medio. Mejora táctica general.",
}


def clasificar_usuario_kmeans(rating: float, df_master: pd.DataFrame) -> str:
    """
    K-Means (k=3) sobre [Rating, Accuracy, Teoria] para asignar grupo.
    Fallback a reglas de rating si el dataset es pequeño.
    """
    if df_master is None or len(df_master) < 30:
        return get_grupo(rating)

    df_clean = df_master[["Rating_Usuario", "ACL_Post_Teo", "Fin_Teoria"]].dropna().copy()
    df_clean["Accuracy_Pct"] = df_clean["ACL_Post_Teo"].apply(acl_to_accuracy)

    X = df_clean[["Rating_Usuario", "Accuracy_Pct", "Fin_Teoria"]].values
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=3, random_state=CFG["kmeans_seed"], n_init=10)
    km.fit(X_scaled)

    df_clean["cluster"] = km.labels_
    medias = df_clean.groupby("cluster")["Rating_Usuario"].mean().sort_values()
    cluster_to_grupo = {
        medias.index[0]: "principiante",
        medias.index[1]: "intermedio",
        medias.index[2]: "avanzado",
    }

    rango = df_master[df_master["Rating_Usuario"].between(rating - 200, rating + 200)]
    user_acc = rango["ACL_Post_Teo"].mean() if not rango.empty else 70.0
    user_acc = acl_to_accuracy(user_acc)
    user_teo = rango["Fin_Teoria"].mean() if not rango.empty else 8.0

    user_point  = scaler.transform([[rating, user_acc, user_teo]])
    cluster_pred = km.predict(user_point)[0]
    return cluster_to_grupo.get(cluster_pred, get_grupo(rating))


def imprimir_informe(username: str, rating: float, grupo: str, plan: dict) -> None:
    W = 82
    print("\n" + "═" * W)
    print(f"  ♟  INFORME DE REPERTORIO — {username.upper()}".center(W))
    print("═" * W)
    print(f"  Rating: {int(rating)}  │  Grupo K-Means: {grupo.upper()}")
    print("─" * W)

    if not plan:
        print("  ⚠️  No hay aperturas con volumen suficiente para analizar.")
        print("═" * W)
        return

    # Tabla resumen
    print(f"\n  {'#':<3} {'APERTURA':<35} {'LABEL':<17} {'ACC%':>5} {'TEO':>5} {'WR%':>5} {'N':>4}")
    print("  " + "─" * (W - 2))
    for i, (apertura, datos) in enumerate(plan.items(), 1):
        emoji = LABEL_EMOJI.get(datos["label"], "")
        lbl   = f"{emoji} {datos['label']}"
        print(
            f"  {i:<3} {apertura:<35} {lbl:<19} "
            f"{datos['accuracy']:>5.1f} {datos['teoria_med']:>5.1f} "
            f"{datos['win_rate']*100:>5.1f} {datos['n_games']:>4}"
        )

    # Detalle con recursos
    print("\n" + "═" * W)
    print("  PLAN DE ESTUDIO DETALLADO".center(W))
    print("═" * W)

    for apertura, datos in plan.items():
        emoji = LABEL_EMOJI.get(datos["label"], "")
        print(f"\n  {emoji} {apertura}")
        print(f"     Label: {datos['label']}  │  Acc: {round(datos['accuracy'], 1)}%  │  "
              f"Teoría: {datos['teoria_med']:.1f}j  │  "
              f"WR: {datos['win_rate']*100:.0f}%  │  Partidas: {datos['n_games']}")
        print(f"     💡 {LABEL_EXPLICACION.get(datos['label'], '')}")

        rec = datos["recursos"]
        if rec.empty:
            print("     📚 Sin recursos específicos en la base de datos.")
        else:
            print("     📚 Recursos recomendados:")
            for _, r in rec.iterrows():
                precio = f"€{r['price_eur']:.0f}" if "price_eur" in r and pd.notna(r.get("price_eur")) else ""
                fuente = r.get("source", r.get("resource_type", ""))
                url    = f"  → {r['url']}" if "url" in r and pd.notna(r.get("url")) else ""
                print(f"       • {r['title']}  [{fuente}] {precio}{url}")

    print("\n" + "═" * W + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER PRIVADO — subida del peor blunder de cada partida
# ─────────────────────────────────────────────────────────────────────────────

def _subir_blunders(df_nuevos: pd.DataFrame, system, games: list) -> int:
    threshold  = CFG["blunder_threshold_cp"]
    game_index = {
        g.headers.get("Site", "").split("/")[-1]: g
        for g in games
    }
    subidos = 0

    for _, row in df_nuevos[df_nuevos["ACL_Post_Teo"] > threshold].iterrows():
        game_id  = str(row["Game_ID"])
        apertura = str(row["Apertura"])
        game_obj = game_index.get(game_id)
        if game_obj is None:
            continue

        try:
            board      = game_obj.board()
            moves      = list(game_obj.mainline_moves())
            fin_teoria = int(row.get("Fin_Teoria", 0))
            player_col = chess.WHITE if row.get("Color") == "Blancas" else chess.BLACK
            side       = 1.0 if player_col == chess.WHITE else -1.0

            for m in moves[:fin_teoria]:
                board.push(m)

            eval_prev  = system.get_eval(board.fen())
            worst_fen  = board.fen()
            worst_loss = 0.0

            for m in moves[fin_teoria: fin_teoria + 12]:
                is_player = (board.turn == player_col)
                fen_antes = board.fen()
                board.push(m)
                eval_now  = system.get_eval(board.fen())

                if is_player:
                    loss = float(max(0.0, (eval_prev - eval_now) * side))
                    if loss > worst_loss:
                        worst_loss = loss
                        worst_fen  = fen_antes

                eval_prev = eval_now

            if worst_loss > threshold:
                print(f"   ⚠️  Blunder en '{apertura}' ({worst_loss:.0f}cp). Subiendo...")
                if subir_error_a_estudio(game_id, apertura, worst_fen, worst_loss):
                    subidos += 1

        except Exception as e:
            print(f"   ⚠️  Error en blunder {game_id}: {e}")

    return subidos


# ─────────────────────────────────────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def analizar_usuario(
    username:      str,
    max_games:     int  = CFG["max_games"],
    top_n:         int  = CFG["top_n_recursos"],
    skip_download: bool = False,
) -> dict:

    print(f"\n{'─'*50}")
    print(f"  🚀 INICIANDO ANÁLISIS: {username}")
    print(f"{'─'*50}")

    # ── 1. MOTOR + CLIENTE ────────────────────────────────────────────────────
    # Sobreescribimos PKL_PATH en el módulo exportado antes de instanciar
    import chess_intelligence_system as _cis
    _cis.PKL_PATH = CFG["pkl_path"]

    system = ChessIntelligenceSystem(CFG["stockfish_path"])
    client = berserk.Client(berserk.TokenSession(CFG["lichess_token"]))

    # ── 2. RATING ─────────────────────────────────────────────────────────────
    perfil_lichess = client.users.get_public_data(username)
    perfs  = perfil_lichess.get("perfs", {})
    rating = (
        perfs.get("blitz",        {}).get("rating", 0)
        or perfs.get("rapid",     {}).get("rating", 0)
        or perfs.get("classical", {}).get("rating", 0)
    )
    print(f"  📊 Rating detectado: {rating}")
    if rating == 0:
        print("  ⚠️  Sin rating activo en Lichess.")
        return {}

    # ── 3. CARGA DEL MASTER CSV ───────────────────────────────────────────────
    master_path = CFG["master_csv"]
    df_master   = pd.read_csv(master_path) if os.path.exists(master_path) else None
    games       = []

    # ── 4. DESCARGA + STOCKFISH ───────────────────────────────────────────────
    if not skip_download:
        print(f"  📥 Descargando hasta {max_games} partidas...")
        games_gen = client.games.export_by_player(
            username, max=max_games, opening=True, as_pgn=True
        )
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

        if df_master is not None:
            df_master = (
                pd.concat([df_master, df_nuevos])
                .drop_duplicates(subset=["Game_ID"], keep="first")
            )
        else:
            df_master = df_nuevos

        df_master.to_csv(master_path, index=False)
        print(f"  ✅ Dataset actualizado → {len(df_master)} registros totales.")

        # ── 5. BLUNDERS → LICHESS STUDY ───────────────────────────────────────
        if CFG.get("study_id"):
            print(f"  📤 Buscando blunders (>{CFG['blunder_threshold_cp']}cp)...")
            n = _subir_blunders(
                df_nuevos = df_nuevos[df_nuevos["Usuario"] == username],
                system    = system,
                games     = games,
            )
            if n:
                print(f"  ✅ {n} blunder(s) → https://lichess.org/study/{CFG['study_id']}")
            else:
                print("  ℹ️  Sin blunders nuevos por encima del umbral.")

    # ── 6. K-MEANS ────────────────────────────────────────────────────────────
    grupo = clasificar_usuario_kmeans(rating, df_master)
    print(f"  🎯 Grupo K-Means: {grupo.upper()}")

    # ── 7. ML DATAFRAME + ETIQUETAS ───────────────────────────────────────────
    df_ml   = build_ml_dataframe(df_master)
    df_user = df_ml[df_ml["Usuario"] == username].copy()
    df_user["grupo"] = grupo

    if df_user.empty:
        print("  ⚠️  Sin datos suficientes para este usuario.")
        return {}

    # ── 8. RECURSOS ───────────────────────────────────────────────────────────
    resources_path = CFG["resources_csv"]
    df_recursos = (
        pd.read_csv(resources_path)
        if os.path.exists(resources_path)
        else pd.DataFrame()
    )

    plan = generar_plan_estudio(df_user, df_recursos)

    # ── 9. INFORME ────────────────────────────────────────────────────────────
    imprimir_informe(username, rating, grupo, plan)

    return plan


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Chess Repertoire Analyst — análisis end-to-end de un usuario Lichess"
    )
    parser.add_argument("--user",          required=True,        help="Username de Lichess")
    parser.add_argument("--max-games",     type=int, default=50, help="Partidas a descargar")
    parser.add_argument("--top-n",         type=int, default=3,  help="Recursos por apertura")
    parser.add_argument("--skip-download", action="store_true",  help="Usa el CSV existente")
    args = parser.parse_args()

    analizar_usuario(
        username      = args.user,
        max_games     = args.max_games,
        top_n         = args.top_n,
        skip_download = args.skip_download,
    )


if __name__ == "__main__":
    main()
