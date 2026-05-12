"""
chess_game_level_augmentation.py
=================================
Amplía la muestra de ~90 usuarios → ~4.500 registros tratando
cada partida individual como una unidad de clasificación ML.

ESTRATEGIA:
    En lugar de agregar las 200 partidas de cada usuario en UNA fila
    (perfil de usuario), cada partida genera su propia fila con features
    derivadas de SU contexto + el contexto promedio del usuario.

    Esto permite pasar de ~90 muestras a ~18.000+ muestras (200 partidas × 90 usuarios)
    manteniendo las proporciones por nivel de rating.

COLUMNAS DEL DATAFRAME RESULTANTE:
    - Identidad:      Game_ID, Usuario, Rating_Usuario, nivel_label
    - Apertura:       Apertura, Color, Fin_Teoria
    - Performance:    ACL_Post_Teo, Accuracy_Game, Victoria
    - Contexto user:  rating_bin, avg_acl_user, avg_teoria_user,
                      win_rate_user, n_games_user
    - Features ML:    teoria_norm, acl_winsorized, delta_acl_vs_user,
                      is_theory_expert, is_feeling_natural,
                      consistency_score, opening_risk_index

USO:
    python chess_game_level_augmentation.py

    Genera: master_game_level_ml.csv  ← listo para entrenar el modelo
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
INPUT_FILE  = "src/data/CSV/master_dataset_ml.csv"
OUTPUT_FILE = "src/data/CSV/master_game_level_ml.csv"
MIN_GAMES_PER_USER = 10   # usuarios con menos partidas se descartan
ACL_WINSOR_CAP     = 500  # capping de ACL en cp para evitar outliers extremos

# Definición de niveles (labels para el clasificador)
BINS   = [0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 5000]
LABELS = [
    "beginner_low",    # <1000
    "beginner_high",   # 1000-1200
    "intermediate_1",  # 1200-1400
    "intermediate_2",  # 1400-1600
    "intermediate_3",  # 1600-1800
    "advanced_1",      # 1800-2000
    "advanced_2",      # 2000-2200
    "expert_1",        # 2200-2400
    "expert_2",        # >2400
]

# Versión simplificada de 4 clases (más estable para clasificadores pequeños)
BINS_4   = [0, 1200, 1600, 2000, 5000]
LABELS_4 = ["beginner", "intermediate", "advanced", "expert"]
# ─────────────────────────────────────────────────────────────


def acpl_to_accuracy(acpl: float) -> float:
    """Convierte ACL (centipeones medios) a porcentaje de precisión."""
    return round(float(max(0.0, min(100.0, 100.0 * np.exp(-0.0035 * acpl)))), 2)


def load_and_validate(filepath: str) -> pd.DataFrame:
    """Carga y valida el dataset maestro."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No se encuentra '{filepath}'. Ejecuta primero el scraper.")

    df = pd.read_csv(filepath)

    required_cols = {"Game_ID", "Usuario", "Rating_Usuario",
                     "Apertura", "Color", "Fin_Teoria", "ACL_Post_Teo", "Victoria"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en el CSV: {missing}")

    # Limpieza básica
    df = df.dropna(subset=["Game_ID", "Rating_Usuario", "ACL_Post_Teo"])
    df = df.drop_duplicates(subset=["Game_ID"], keep="first")
    df["Rating_Usuario"] = df["Rating_Usuario"].astype(int)
    df["ACL_Post_Teo"]   = pd.to_numeric(df["ACL_Post_Teo"], errors="coerce")
    df = df.dropna(subset=["ACL_Post_Teo"])

    print(f"✅ Dataset cargado: {len(df):,} partidas | {df['Usuario'].nunique()} usuarios")
    return df


def compute_user_context(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula features de contexto a nivel de usuario y las une al dataframe.
    Estas features representan el 'perfil promedio' del jugador
    al momento de cada partida (usando TODAS sus partidas disponibles).
    """
    user_agg = df.groupby("Usuario").agg(
        avg_acl_user    = ("ACL_Post_Teo", "mean"),
        std_acl_user    = ("ACL_Post_Teo", "std"),
        avg_teoria_user = ("Fin_Teoria",   "mean"),
        win_rate_user   = ("Victoria",     "mean"),
        n_games_user    = ("Game_ID",      "count"),
        rating_ref      = ("Rating_Usuario", "first"),
    ).reset_index()

    user_agg["accuracy_user"]  = user_agg["avg_acl_user"].apply(acpl_to_accuracy)
    user_agg["std_acl_user"]   = user_agg["std_acl_user"].fillna(0)

    # Consistencia: menor std relativa = más consistente
    user_agg["consistency_score"] = np.where(
        user_agg["avg_acl_user"] > 0,
        1 - (user_agg["std_acl_user"] / (user_agg["avg_acl_user"] + 1e-9)).clip(0, 1),
        0
    )

    df = df.merge(user_agg, on="Usuario", how="left")
    return df, user_agg


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera todas las features derivadas a nivel de partida individual.
    """
    df = df.copy()

    # ── 1. ACL winsorizado (evita que un blunder en mate distorsione todo) ──
    df["acl_winsorized"] = df["ACL_Post_Teo"].clip(upper=ACL_WINSOR_CAP)

    # ── 2. Accuracy a nivel de partida individual ─────────────────────────
    df["accuracy_game"] = df["acl_winsorized"].apply(acpl_to_accuracy)

    # ── 3. Normalización de teoría [0-1] ──────────────────────────────────
    df["teoria_norm"] = (df["Fin_Teoria"] / 15).clip(0, 1)

    # ── 4. Delta ACL respecto al promedio del usuario ─────────────────────
    #       Positivo = esta partida fue PEOR que su media
    #       Negativo = esta partida fue MEJOR que su media
    df["delta_acl_vs_user"] = df["acl_winsorized"] - df["avg_acl_user"]

    # ── 5. Flags de categorías de apertura ───────────────────────────────
    # Experto teórico: alta teoría (≥10j) y buena precisión (≥65%)
    df["is_theory_expert"] = (
        (df["Fin_Teoria"] >= 10) & (df["accuracy_game"] >= 65.0)
    ).astype(int)

    # Feeling natural: poca teoría (<7j) pero alta precisión (≥70%)
    df["is_feeling_natural"] = (
        (df["Fin_Teoria"] < 7) & (df["accuracy_game"] >= 70.0)
    ).astype(int)

    # Punto crítico: mucha teoría pero baja precisión
    df["is_critical_point"] = (
        (df["Fin_Teoria"] >= 8) & (df["accuracy_game"] < 55.0)
    ).astype(int)

    # ── 6. Risk index de la apertura en esta partida ──────────────────────
    df["game_risk_index"] = df["teoria_norm"] * (100 - df["accuracy_game"])

    # ── 7. Score de preparación en esta partida ────────────────────────────
    df["game_prep_score"] = df["teoria_norm"] * (df["accuracy_game"] / 100)

    # ── 8. Encoding de color ──────────────────────────────────────────────
    df["color_bin"] = (df["Color"] == "Blancas").astype(int)

    # ── 9. Rating bins ────────────────────────────────────────────────────
    df["nivel_9class"] = pd.cut(
        df["Rating_Usuario"], bins=BINS, labels=LABELS
    ).astype(str)

    df["nivel_4class"] = pd.cut(
        df["Rating_Usuario"], bins=BINS_4, labels=LABELS_4
    ).astype(str)

    # Encoding numérico del nivel (útil para modelos de regresión)
    label_map_4 = {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}
    df["nivel_num"] = df["nivel_4class"].map(label_map_4)

    return df


def filter_quality(df: pd.DataFrame, min_games: int = MIN_GAMES_PER_USER) -> pd.DataFrame:
    """
    Elimina usuarios con demasiado pocas partidas para evitar sesgos.
    """
    games_per_user = df.groupby("Usuario")["Game_ID"].count()
    valid_users    = games_per_user[games_per_user >= min_games].index
    df_filtered    = df[df["Usuario"].isin(valid_users)].copy()

    removed = df["Usuario"].nunique() - df_filtered["Usuario"].nunique()
    if removed > 0:
        print(f"⚠️  {removed} usuarios eliminados por tener <{min_games} partidas.")

    return df_filtered


def print_distribution_report(df: pd.DataFrame) -> None:
    """Imprime la distribución del dataset resultante."""
    print("\n" + "═" * 70)
    print(" 📊 DISTRIBUCIÓN DEL DATASET GAME-LEVEL ".center(70, "═"))
    print("═" * 70)
    print(f"  Total partidas (filas ML): {len(df):,}")
    print(f"  Usuarios únicos:           {df['Usuario'].nunique()}")
    print(f"  Features generadas:        {len(get_feature_columns(df))}")
    print("─" * 70)

    dist = df.groupby("nivel_4class", observed=True).agg(
        Usuarios = ("Usuario",       "nunique"),
        Partidas = ("Game_ID",       "count"),
        Acc_Med  = ("accuracy_game", "mean"),
        Teo_Med  = ("Fin_Teoria",    "mean"),
        WinRate  = ("Victoria",      "mean"),
    )
    dist["Acc_Med"] = dist["Acc_Med"].round(1)
    dist["Teo_Med"] = dist["Teo_Med"].round(1)
    dist["WinRate"] = (dist["WinRate"] * 100).round(1)

    # Ordenar por nivel
    order = ["beginner", "intermediate", "advanced", "expert"]
    dist  = dist.reindex([l for l in order if l in dist.index])
    print(dist.to_string())
    print("═" * 70)

    # Alertas de desbalanceo
    max_p = dist["Partidas"].max()
    min_p = dist["Partidas"].min()
    ratio = max_p / max(min_p, 1)
    if ratio > 3:
        print(f"\n⚠️  Desbalanceo detectado (ratio max/min = {ratio:.1f}x).")
        print("   Considera usar class_weight='balanced' en tu clasificador.")
    else:
        print(f"\n✅ Dataset equilibrado (ratio max/min = {ratio:.1f}x).")


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Devuelve la lista de columnas de features para el modelo."""
    feature_cols = [
        # Directas de la partida
        "Rating_Usuario",
        "Fin_Teoria",
        "acl_winsorized",
        "accuracy_game",
        "teoria_norm",
        "color_bin",
        "Victoria",
        # Contexto del usuario
        "avg_acl_user",
        "std_acl_user",
        "avg_teoria_user",
        "accuracy_user",
        "win_rate_user",
        "n_games_user",
        "consistency_score",
        # Features derivadas
        "delta_acl_vs_user",
        "is_theory_expert",
        "is_feeling_natural",
        "is_critical_point",
        "game_risk_index",
        "game_prep_score",
    ]
    return [c for c in feature_cols if c in df.columns]


def main():
    print("=" * 70)
    print("  CHESS GAME-LEVEL AUGMENTATION")
    print("  De perfil-usuario → partida-como-muestra-ML")
    print("=" * 70)

    # 1. Cargar
    df = load_and_validate(INPUT_FILE)

    # 2. Filtrar usuarios con pocas partidas
    df = filter_quality(df, min_games=MIN_GAMES_PER_USER)

    # 3. Contexto de usuario (features agregadas que acompañan cada fila)
    print("\n🔧 Calculando contexto por usuario...")
    df, user_profiles = compute_user_context(df)

    # 4. Feature engineering a nivel de partida
    print("🔧 Generando features por partida...")
    df = engineer_features(df)

    # 5. Seleccionar columnas finales
    id_cols      = ["Game_ID", "Usuario", "Rating_Usuario", "Apertura", "Color",
                     "nivel_4class", "nivel_9class", "nivel_num"]
    feature_cols = get_feature_columns(df)
    final_cols   = id_cols + feature_cols

    df_output = df[[c for c in final_cols if c in df.columns]].copy()

    # 6. Guardar
    df_output.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Dataset game-level guardado en: '{OUTPUT_FILE}'")

    # 7. Guardar también los perfiles de usuario (útil para el sistema de recomendación)
    user_profiles_file = "user_profiles_summary.csv"
    user_profiles["nivel_4class"] = pd.cut(
        user_profiles["rating_ref"], bins=BINS_4, labels=LABELS_4
    ).astype(str)
    user_profiles.to_csv(user_profiles_file, index=False)
    print(f"✅ Perfiles de usuario guardados en: '{user_profiles_file}'")

    # 8. Reporte
    print_distribution_report(df_output)

    # 9. Snippet de uso para el modelo
    print("\n📋 SNIPPET PARA TU NOTEBOOK DE ML:")
    print("─" * 70)
    snippet = '''
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report

df = pd.read_csv("master_game_level_ml.csv")

FEATURES = [
    "Rating_Usuario", "Fin_Teoria", "acl_winsorized", "accuracy_game",
    "teoria_norm", "color_bin", "avg_acl_user", "std_acl_user",
    "avg_teoria_user", "accuracy_user", "win_rate_user", "consistency_score",
    "delta_acl_vs_user", "is_theory_expert", "is_feeling_natural",
    "is_critical_point", "game_risk_index", "game_prep_score",
]
TARGET = "nivel_4class"

X = df[FEATURES].fillna(0)
y = df[TARGET]
groups = df["Usuario"]   # ← evita data leakage entre partidas del mismo usuario

# StratifiedGroupKFold: respeta proporciones de clase Y evita que el mismo
# usuario aparezca en train y test a la vez
sgkf = StratifiedGroupKFold(n_splits=5)

model = RandomForestClassifier(
    n_estimators=300,
    class_weight="balanced",  # compensa desbalanceo residual
    random_state=42,
    n_jobs=-1,
)

for fold, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(f"--- Fold {fold+1} ---")
    print(classification_report(y_test, y_pred))
'''
    print(snippet)
    print("─" * 70)
    print("\n⚠️  IMPORTANTE: Usa StratifiedGroupKFold con groups=Usuario")
    print("   para evitar data leakage (partidas del mismo user en train+test).")


if __name__ == "__main__":
    main()

