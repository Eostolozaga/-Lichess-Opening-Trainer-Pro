#!/usr/bin/env python
# coding: utf-8

# # Chess Intelligence System
# ## Descarga, Tratamiento y Análisis de Partidas de Ajedrez con Stockfish
# 
# **Autor:** Eneko  
# **Descripción:** Este notebook implementa un sistema de análisis de repertorio de ajedrez que combina la API de Lichess, una base de datos teórica de grandes maestros y el motor Stockfish. El objetivo es generar un dataset etiquetado listo para alimentar un modelo de Machine Learning que categorice el rendimiento por apertura de cada jugador.
# 
# ---
# 
# ### Flujo del sistema
# 1. **Ingesta:** Descarga de partidas vía API de Lichess (incluye Rating del jugador).  
# 2. **Análisis Teórico:** Cruce con la DB local (`.pkl`) para identificar hasta qué jugada se sigue la teoría.  
# 3. **Análisis de Rendimiento:** Stockfish evalúa las jugadas post-teoría y mide la pérdida en centipeones (ACL).  
# 4. **Dashboard:** Categorización de aperturas en Riesgo, Dominio Teórico y Feeling Natural.  
# 5. **Persistencia:** Guardado incremental en el dataset maestro CSV para uso en ML.

# ---
# ## 1. Importaciones y Configuración Global
# 
# Se cargan todas las librerías necesarias y se definen las rutas del proyecto siguiendo la estructura de carpetas estándar. **Ajustar `PROJECT_ROOT` si se ejecuta desde una ubicación distinta.**

# In[2]:


import io
import os
import re
import time
import datetime
import pickle
import chess
import chess.pgn
import pandas as pd
import berserk
import requests
import numpy as np
from stockfish import Stockfish
from tqdm import tqdm
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# RUTAS DEL PROYECTO
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = r"C:\Users\Eneko\Desktop\Ejercicios Data\Proyectos\Proyecto ML"

# Datos
DATA_DIR       = os.path.join(PROJECT_ROOT, "src", "data")
CSV_DIR        = os.path.join(DATA_DIR, "CSV")
PKL_DIR        = os.path.join(DATA_DIR, "PKL")
BACKUPS_DIR    = os.path.join(DATA_DIR, "Backups")
PGN_MASTERS_DIR = os.path.join(DATA_DIR, "Libro aperturas")

# Recursos
RESOURCES_DIR  = os.path.join(PROJECT_ROOT, "resources")
ENGINES_DIR    = os.path.join(RESOURCES_DIR, "engines")
IMG_DIR        = os.path.join(RESOURCES_DIR, "img")

# Archivos principales
STOCKFISH_PATH = os.path.join(ENGINES_DIR, "stockfish-windows-x86-64-avx2.exe")
PKL_PATH       = os.path.join(PKL_DIR, "theory_db.pkl")
FILENAME_ML    = os.path.join(CSV_DIR, "master_dataset_ml.csv")

# ──────────────────────────────────────────────────────────────────────────────
# CREDENCIALES Y PARÁMETROS DE LICHESS
# ──────────────────────────────────────────────────────────────────────────────

LICHESS_TOKEN = os.getenv("LICHESS_TOKEN")
STUDY_ID      = os.getenv("LICHESS_STUDY_ID")

# Crear directorios si no existen (útil en entornos nuevos)
for d in [CSV_DIR, PKL_DIR, BACKUPS_DIR, IMG_DIR]:
    os.makedirs(d, exist_ok=True)

print("✅ Configuración cargada correctamente.")
print(f"   Dataset maestro → {FILENAME_ML}")
print(f"   Base teórica    → {PKL_PATH}")


# ---
# ## 2. Construcción de la Base de Datos Teórica
# 
# Se procesan archivos PGN de partidas de grandes maestros para extraer las posiciones de las primeras **15 jugadas** de cada partida. Cada posición se almacena en formato EPD (representación compacta de FEN) dentro de un `set` de Python para búsquedas O(1).  
# 
# El resultado se serializa en `theory_db.pkl`. **Solo es necesario ejecutar esta celda una vez.**  
# Si el archivo ya existe, pasar directamente a la Sección 3.

# In[3]:


def crear_base_teorica(limit_per_file: int = 10_000) -> None:
    """
    Recorre todos los PGN de maestros en PGN_MASTERS_DIR y extrae las
    posiciones de las primeras 15 jugadas de cada partida.
    El resultado se guarda como un set serializado en PKL_PATH.

    Parámetros
    ----------
    limit_per_file : int
        Número máximo de partidas a procesar por archivo PGN.
    """
    theory_positions: set = set()
    files = [f for f in os.listdir(PGN_MASTERS_DIR) if f.endswith(".pgn")]

    if not files:
        print(f"⚠️  No se encontraron archivos PGN en: {PGN_MASTERS_DIR}")
        return

    start_time = time.time()

    for filename in files:
        print(f"Procesando {filename}...")
        count = 0
        filepath = os.path.join(PGN_MASTERS_DIR, filename)

        with open(filepath, encoding="utf-8") as pgn:
            while count < limit_per_file:
                game = chess.pgn.read_game(pgn)   # cuello de botella: I/O
                if not game:
                    break

                board = game.board()
                for i, move in enumerate(game.mainline_moves()):
                    if i >= 15:
                        break
                    board.push(move)
                    theory_positions.add(board.epd())   # EPD como clave

                count += 1
                if count % 1_000 == 0:
                    print(f"   > {count} partidas procesadas...")

    # Serialización → src/data/PKL/
    with open(PKL_PATH, "wb") as f:
        pickle.dump(theory_positions, f)

    elapsed = (time.time() - start_time) / 60
    print(f"\n✅ Base teórica guardada en: {PKL_PATH}")
    print(f"   Posiciones únicas: {len(theory_positions):,}")
    print(f"   Tiempo total: {elapsed:.2f} minutos.")


# Descomentar para regenerar la base teórica desde cero:
# crear_base_teorica(limit_per_file=10_000)


# ---
# ## 3. Funciones Auxiliares
# 
# Utilidades independientes del motor de análisis:  
# - **`acpl_to_accuracy`**: Convierte la pérdida media en centipeones (ACL) a un porcentaje de precisión usando decaimiento exponencial (estándar de Lichess).  
# - **`subir_error_a_estudio`**: Sube una posición blunder a un estudio de Lichess vía REST API para revisión manual posterior.  
# - **`buscar_estudios_lichess`**: Raspado ligero de Lichess para sugerir estudios públicos relacionados con una apertura dada.

# In[4]:


def acpl_to_accuracy(acpl: float) -> float:
    """
    Convierte la pérdida media en centipeones (ACPL) a un porcentaje de
    precisión [0, 100] usando la curva exponencial de Lichess.

    Fórmula: accuracy = 100 * exp(-0.0035 * acpl)
    """
    return round(float(max(0, min(100, 100 * np.exp(-0.0035 * acpl)))), 1)


def subir_error_a_estudio(game_id: str, apertura: str,
                           fen: str, perdida: float) -> bool:
    """
    Sube una posición blunder como nuevo capítulo al estudio de Lichess
    configurado en STUDY_ID.

    Endpoint: POST /api/study/{studyId}/import-pgn

    Parámetros
    ----------
    game_id  : ID de la partida en Lichess.
    apertura : Nombre de la apertura (usado en el título del capítulo).
    fen      : FEN/EPD de la posición blunder.
    perdida  : Pérdida en centipeones del blunder.

    Retorna True si la subida fue exitosa.
    """
    # Completar FEN si viene como EPD (4 campos en lugar de 6)
    fen_campos = fen.strip().split()
    if len(fen_campos) < 4:
        print(f"   ❌ FEN inválido ({len(fen_campos)} campos): {fen[:50]}")
        return False
    if len(fen_campos) == 4:
        fen = fen + " 0 1"

    perdida_peon = round(float(perdida) / 100, 1)
    nombre_cap   = f"Blunder -{perdida_peon}p | {apertura[:28]}"

    # PGN mínimo válido: SetUp ANTES de FEN (requisito del parser de Lichess)
    pgn_data = (
        f'[Event "{nombre_cap}"]\n'
        f'[Site "{game_id}"]\n'
         '[SetUp "1"]\n'
        f'[FEN "{fen}"]\n'
        '\n*'
    )

    url     = f"https://lichess.org/api/study/{STUDY_ID}/import-pgn"
    headers = {"Authorization": f"Bearer {LICHESS_TOKEN}"}
    payload = {"name": nombre_cap, "pgn": pgn_data}

    try:
        r = requests.post(url, headers=headers, data=payload, timeout=10)
        if r.status_code == 200:
            return True
        print(f"   ❌ Lichess {r.status_code}: {r.text[:120]}")
        return False
    except requests.exceptions.Timeout:
        print("   ❌ Timeout — Lichess no respondió en 10 s")
        return False
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False


def buscar_estudios_lichess(apertura: str, n: int = 1) -> list:
    """
    Realiza una búsqueda ligera en Lichess para encontrar estudios públicos
    relacionados con la apertura indicada.

    Retorna una lista de dicts con claves 'nombre' y 'link'.
    """
    # Limpiar la query: eliminar palabras genéricas y normalizar
    query = apertura.split(':')[-1].split(',')[-1].strip().lower()
    for word in ["variation", "defense", "opening", "attack", "gambit", "declined"]:
        query = query.replace(word, "").strip()
    query = re.sub(r'\s+', '+', query).strip('+')

    url  = f"https://lichess.org/study/search?q={query}&order=hot"
    hdrs = {"User-Agent": "Mozilla/5.0"}
    estudios = []

    try:
        r = requests.get(url, headers=hdrs, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Los estudios de Lichess tienen rutas /study/XXXXXXXX (8 chars)
                if href.startswith('/study/') and len(href.split('/')[-1]) == 8:
                    nombre = link.get_text(strip=True)
                    if len(nombre) > 5:
                        estudios.append({
                            'nombre': nombre,
                            'link': f"https://lichess.org{href}"
                        })
                if len(estudios) >= n:
                    break
    except Exception:
        pass

    return estudios


# ---
# ## 4. Motor de Análisis: `ChessIntelligenceSystem`
# 
# Clase principal que encapsula toda la lógica de análisis por partida. Sus responsabilidades son:
# 
# | Método | Descripción |
# |---|---|
# | `_load_masters_theory` | Carga el `set` de posiciones teóricas desde el PKL |
# | `get_eval` | Consulta Stockfish y devuelve la evaluación en centipeones |
# | `calculate_player_acl` | Calcula la pérdida media post-teoría; detecta y sube blunders |
# | `analyze_games` | Orquesta el análisis de una lista de partidas y devuelve un DataFrame |
# 
# > **Nota de optimización:** Se utiliza una estrategia de cache `eval_cache` que reduce las llamadas a Stockfish de `2×N` a `N+1` por ventana de jugadas.

# In[5]:


class ChessIntelligenceSystem:
    """
    Motor de análisis de repertorio de ajedrez.

    Combina una base de datos teórica de grandes maestros con el motor
    Stockfish para evaluar la precisión post-teoría de un jugador y
    detectar sus puntos de mejora por apertura.
    """

    MATE_SCORE = 1_000  # Cap en cp para no distorsionar medias con posiciones de mate

    def __init__(self, stockfish_path: str):
        self.theory_positions: set = set()
        print("Iniciando motor Stockfish...")
        self.sf = Stockfish(
            path=stockfish_path,
            parameters={"Threads": 4, "Hash": 512}
        )
        self.sf.set_depth(16)
        self._load_masters_theory()

    def _load_masters_theory(self) -> None:
        """Carga el set de posiciones teóricas desde el archivo PKL."""
        try:
            with open(PKL_PATH, 'rb') as f:
                self.theory_positions = pickle.load(f)
            print(f"✅ Base teórica cargada: {len(self.theory_positions):,} posiciones.")
        except FileNotFoundError:
            print(f"❌ No se encuentra la base teórica en: {PKL_PATH}")
            print("   Ejecuta primero la Sección 2 para generarla.")

    def get_eval(self, fen: str) -> float:
        """
        Consulta Stockfish para una posición dada.

        Retorna la evaluación en centipeones clampeada a ±MATE_SCORE.
        Positivo = ventaja para las blancas.
        """
        try:
            self.sf.set_fen_position(fen, do_validation=False)
            ev = self.sf.get_evaluation()
            if ev["type"] == "mate":
                return float(self.MATE_SCORE if ev["value"] > 0 else -self.MATE_SCORE)
            return float(max(-self.MATE_SCORE, min(self.MATE_SCORE, ev["value"])))
        except Exception:
            return 0.0

    def calculate_player_acl(self, game, player_color: chess.Color,
                              start_move: int, apertura: str,
                              game_id: str, window: int = 12) -> float | None:
        """
        Calcula el ACL (Average Centipawn Loss) post-teoría del jugador.

        Estrategia de evaluación: N+1 llamadas a Stockfish (en vez de 2xN)
        reutilizando la evaluación previa como eval_prev del siguiente turno.
        También detecta y sube el primer blunder (>100 cp) de cada partida
        al estudio de Lichess.

        Parámetros
        ----------
        window : número de jugadas post-teoría a analizar (por defecto 12).
        """
        board  = game.board()
        moves  = list(game.mainline_moves())
        losses = []
        error_reportado = False

        # Avanzar el tablero hasta el fin de la teoría
        for m in moves[:start_move]:
            board.push(m)

        end_idx = min(start_move + window, len(moves))
        if end_idx <= start_move:
            return None

        eval_cache = self.get_eval(board.fen())   # Evaluación inicial (reutilizable)

        for i in range(start_move, end_idx):
            is_player_turn = (board.turn == player_color)
            fen_antes      = board.fen()
            eval_prev      = eval_cache

            board.push(moves[i])
            eval_cache = self.get_eval(board.fen())   # 1 llamada por jugada

            if is_player_turn:
                side = 1.0 if player_color == chess.WHITE else -1.0
                loss = float(max(0.0, (eval_prev - eval_cache) * side))
                losses.append(loss)

                # Detección y reporte del primer blunder de la partida
                if loss > 100.0 and not error_reportado:
                    print(f"   ⚠️  Blunder en '{apertura}' ({loss:.0f}cp). Subiendo...")
                    if subir_error_a_estudio(game_id, apertura, fen_antes, loss):
                        print("   ✨ Posición subida al estudio.")
                        error_reportado = True

        return sum(losses) / len(losses) if losses else None

    def analyze_games(self, games_list: list,
                      target_user: str, user_rating: int) -> pd.DataFrame:
        """
        Orquesta el análisis de una lista de objetos `chess.pgn.Game`.

        Para cada partida determina: apertura, color del jugador, fin de
        teoría (tolerante a 1 transposición) y ACL post-teoría.

        Retorna un DataFrame con una fila por partida analizada con éxito.
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
            apertura_base = apertura_full.split(':')[0].split(',')[0].strip()

            res = headers.get("Result", "*")
            if (res == "1-0" and is_white) or (res == "0-1" and not is_white):
                victoria = 1.0
            elif res == "1/2-1/2":
                victoria = 0.5
            else:
                victoria = 0.0

            # Detectar fin de teoría (tolerante a 1 transposición)
            board             = game.board()
            moves             = list(game.mainline_moves())
            theory_end        = 0
            off_theory_streak = 0

            for i, move in enumerate(moves[:30]):
                board.push(move)
                if board.epd() in self.theory_positions:
                    theory_end        = i + 1
                    off_theory_streak = 0
                else:
                    off_theory_streak += 1
                    if off_theory_streak >= 2:
                        break   # Dos jugadas fuera de teoría → salida definitiva

            acl = self.calculate_player_acl(
                game, color, theory_end, apertura_base, game_id
            )

            if acl is not None:
                results.append({
                    'Game_ID':        game_id,
                    'Usuario':        target_user,
                    'Rating_Usuario': user_rating,
                    'Apertura':       apertura_base,
                    'Color':          "Blancas" if is_white else "Negras",
                    'Fin_Teoria':     theory_end,
                    'ACL_Post_Teo':   round(acl, 1),
                    'Victoria':       victoria,
                })
                print(f"   [{idx+1}/{total}] {apertura_base} | Teo: {theory_end}j | ACL: {acl:.0f}cp")

        return pd.DataFrame(results)


# ---
# ## 5. Generación del Dashboard de Análisis
# 
# A partir del dataset acumulado, se agregan los datos por `(Apertura, Color)` y se calculan tres índices:
# 
# | Índice | Fórmula | Interpretación |
# |---|---|---|
# | `Score_Prep` | `(Teo/15) × (Acc/100)` | Mucha teoría + alta precisión → apertura bien preparada |
# | `Risk_Index` | `(Teo/15) × (100 - Acc)` | Mucha teoría + baja precisión → punto crítico de estudio |
# | `Score_Feeling` | `Acc` si `Teo<7 ∧ Acc≥65 ∧ n≥2` | Baja teoría + alta precisión → talento posicional natural |
# 
# **Winsorización:** Se capan los valores de ACL a 500 cp para evitar que blunders extremos sesguen la media de una apertura completa.

# In[6]:


def generar_dashboard_tecnico(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega el dataset por (Apertura, Color) y calcula los índices de
    rendimiento: Score_Prep, Risk_Index y Score_Feeling.

    Winsoriza el ACL a 500 cp antes de agregar para evitar que blunders
    extremos distorsionen la media de toda una apertura.
    """
    df = df_raw.copy()
    df['ACL_clean'] = df['ACL_Post_Teo'].clip(upper=500)
    col_ap = 'Apertura_Base' if 'Apertura_Base' in df.columns else 'Apertura'

    df_m = df.groupby([col_ap, 'Color']).agg(
        Avg_Teoria = ('Fin_Teoria',  'mean'),
        Avg_ACL    = ('ACL_clean',   'mean'),
        Volumen    = ('Game_ID',     'count'),
        Win_Rate   = ('Victoria',    'mean'),
    ).reset_index()
    df_m.rename(columns={col_ap: 'Apertura'}, inplace=True)

    df_m['Accuracy'] = df_m['Avg_ACL'].apply(acpl_to_accuracy)

    # Índice de preparación teórica
    df_m['Score_Prep'] = (df_m['Avg_Teoria'] / 15) * (df_m['Accuracy'] / 100)

    # Índice de feeling natural: pocas jugadas de teoría pero alta precisión
    df_m['Score_Feeling'] = np.where(
        (df_m['Avg_Teoria'] < 7) & (df_m['Accuracy'] >= 65.0) & (df_m['Volumen'] >= 2),
        df_m['Accuracy'], 0
    )

    # Índice de riesgo: mucha teoría + baja precisión
    df_m['Risk_Index'] = (df_m['Avg_Teoria'] / 15) * (100 - df_m['Accuracy'])

    return df_m


def imprimir_dashboard(df_m: pd.DataFrame, username: str) -> None:
    """
    Imprime el dashboard técnico con tres categorías por color:
    - ⚠️  RIESGO: aperturas con alto Risk_Index (estudiar o cambiar).
    - 🌟 DOMINIO: aperturas con alto Score_Prep y volumen ≥ 3.
    - 🧠 FEELING: aperturas con alto Score_Feeling (talento natural).
    """
    if df_m is None or df_m.empty:
        print("⚠️  DataFrame vacío, no hay datos que mostrar.")
        return

    print("\n╔" + "═"*85 + "╗")
    print(f"║ 🔬 DASHBOARD TÉCNICO — {username} ".ljust(86) + "║")
    print("╚" + "═"*85 + "╝")

    for color in ['Blancas', 'Negras']:
        subset = df_m[df_m['Color'] == color].copy()
        if subset.empty:
            continue
        print(f"\n  ♟  {color.upper()}")

        # 1. Aperturas críticas (mayor Risk_Index)
        muro      = subset.sort_values('Risk_Index', ascending=False).head(3)
        muro_list = muro['Apertura'].tolist()
        print("  ⚠️  RIESGO (estudiar o abandonar):")
        for i, (_, r) in enumerate(muro.iterrows(), 1):
            print(f"     {i}. {r['Apertura'][:27].ljust(27)} | "
                  f"Acc: {str(r['Accuracy']).rjust(5)}% | "
                  f"Teo: {str(round(r['Avg_Teoria'], 1)).rjust(4)}j | "
                  f"n={int(r['Volumen'])}")
            # Sugerir estudios de Lichess para las aperturas de riesgo
            estudios = buscar_estudios_lichess(r['Apertura'])
            for e in estudios:
                print(f"      📖 {e['nombre']} → {e['link']}")

        # 2. Aperturas bien preparadas
        top_p = subset[
            ~subset['Apertura'].isin(muro_list) & (subset['Volumen'] >= 3)
        ].sort_values('Score_Prep', ascending=False).head(3)
        print("  🌟  DOMINIO TEÓRICO:")
        if top_p.empty:
            print("     N/A — sin líneas con n≥3 fuera del muro.")
        else:
            for i, (_, r) in enumerate(top_p.iterrows(), 1):
                print(f"     {i}. {r['Apertura'][:27].ljust(27)} | "
                      f"Acc: {str(r['Accuracy']).rjust(5)}% | "
                      f"Teo: {str(round(r['Avg_Teoria'], 1)).rjust(4)}j | "
                      f"n={int(r['Volumen'])}")

        # 3. Aperturas con talento natural (pocas jugadas de teoría, alta precisión)
        top_f = subset[
            subset['Score_Feeling'] > 0
        ].sort_values('Score_Feeling', ascending=False).head(3)
        print("  🧠  FEELING NATURAL (potenciar):")
        if top_f.empty:
            print("     N/A — sin líneas cortas con Accuracy≥65% y n≥2.")
        else:
            for i, (_, r) in enumerate(top_f.iterrows(), 1):
                print(f"     {i}. {r['Apertura'][:27].ljust(27)} | "
                      f"Acc: {str(r['Accuracy']).rjust(5)}% | "
                      f"Teo: {str(round(r['Avg_Teoria'], 1)).rjust(4)}j | "
                      f"n={int(r['Volumen'])}")


# ---
# ## 6. Pipeline Principal: Análisis por Usuario
# 
# Esta función orquesta el flujo completo para un usuario de Lichess:
# 
# 1. Consulta el perfil y obtiene el rating (Blitz > Rapid como fuente principal).  
# 2. Descarga las últimas `max` partidas con información de apertura.  
# 3. Analiza cada partida con `ChessIntelligenceSystem`.  
# 4. **Persistencia incremental:** concatena los resultados al CSV maestro y elimina duplicados por `Game_ID`.  
# 5. Genera e imprime el dashboard para el usuario actual.

# In[7]:


def procesar_usuario(nombre_target: str, max_partidas: int = 50) -> None:
    """
    Flujo completo de análisis para un usuario de Lichess:
    descarga → análisis → persistencia → dashboard.

    Parámetros
    ----------
    nombre_target : nombre de usuario en Lichess.
    max_partidas  : número máximo de partidas a descargar y analizar.
    """
    print("\n" + "─"*60)
    print(f"📥 ANALIZANDO PERFIL: {nombre_target}")

    try:
        # 1. Obtener rating del jugador
        perfil   = client.users.get_public_data(nombre_target)
        perfs    = perfil.get('perfs', {})
        r_blitz  = perfs.get('blitz', {}).get('rating', 0)
        r_rapid  = perfs.get('rapid', {}).get('rating', 0)
        rating   = r_blitz if r_blitz > 0 else r_rapid

        print(f"📊 Rating — Blitz: {r_blitz} | Rapid: {r_rapid} | Referencia: {rating}")
        print("─"*60)

        if rating == 0:
            print(f"⚠️  {nombre_target} no tiene ratings activos. Saltando.")
            return

        # 2. Descargar partidas
        print(f"📥 Descargando últimas {max_partidas} partidas...")
        games_gen = client.games.export_by_player(
            nombre_target, max=max_partidas, opening=True, as_pgn=True
        )
        games = []
        for g_str in games_gen:
            if isinstance(g_str, dict):
                continue   # Descartar metadatos inesperados
            game_obj = chess.pgn.read_game(io.StringIO(g_str))
            if game_obj:
                games.append(game_obj)
            if len(games) >= max_partidas:
                break

        if not games:
            print(f"❌ No se encontraron partidas para {nombre_target}.")
            return

        # 3. Analizar partidas con el motor
        print(f"🔍 Analizando {len(games)} partidas...")
        df_nuevos = system.analyze_games(games, nombre_target, rating)

        # 4. Persistencia incremental en CSV maestro (src/data/CSV/)
        if os.path.exists(FILENAME_ML):
            df_hist  = pd.read_csv(FILENAME_ML)
            df_final = (
                pd.concat([df_hist, df_nuevos])
                .drop_duplicates(subset=['Game_ID'], keep='first')
            )
            nuevos = len(df_final) - len(df_hist)
        else:
            df_final = df_nuevos
            nuevos   = len(df_nuevos)

        df_final.to_csv(FILENAME_ML, index=False)
        print(f"✅ Dataset actualizado → {FILENAME_ML} (+{nuevos} partidas nuevas)")

        # 5. Dashboard para el usuario actual
        df_usuario = df_final[df_final['Usuario'] == nombre_target]
        df_dash    = generar_dashboard_tecnico(df_usuario)
        imprimir_dashboard(df_dash, nombre_target)

    except Exception as e:
        print(f"❌ Error crítico con {nombre_target}: {e}")


# ---
# ## 7. Ejecución
# 
# Instanciar el motor y el cliente de Lichess, luego llamar a `procesar_usuario` con el nombre de usuario deseado.  
# Cada ejecución acumula datos en `master_dataset_ml.csv` sin duplicar partidas ya procesadas.  
# 
# Para construir el dataset de entrenamiento ML, repetir con distintos usuarios cubriendo todos los tramos de rating.

# In[8]:


# Instanciar el motor y el cliente de Lichess
system = ChessIntelligenceSystem(STOCKFISH_PATH)
client = berserk.Client(berserk.TokenSession(LICHESS_TOKEN))

# ── Cambiar el nombre de usuario según el jugador a analizar ──
usuario_a_analizar = "tecojoytetruqueo"
procesar_usuario(usuario_a_analizar, max_partidas=10)


# ---
# ## 8. Auditoría del Dataset Maestro
# 
# Herramienta de control de calidad del dataset acumulado. Muestra:
# - Estadísticas globales (número de partidas, usuarios únicos, precisión mediana).  
# - Distribución de partidas y métricas técnicas segmentadas por **tramo de rating**.  
# - Alerta si algún tramo tiene menos de 2 usuarios (desequilibrio que puede sesgar el modelo).  
# - Top 5 usuarios con más partidas aportadas al dataset.
# 
# Ejecutar periódicamente para asegurar que el dataset está balanceado antes de entrenar el modelo.

# In[9]:


def diagnosticar_dataset(filename: str = FILENAME_ML) -> None:
    """
    Imprime un resumen de calidad y distribución del dataset maestro.

    Segmenta los datos por tramos de rating y alerta si algún tramo
    está sub-representado (< 2 usuarios), lo que podría sesgar el modelo.
    """
    if not os.path.exists(filename):
        print(f"❌ No existe '{filename}'. Analiza primero algún usuario.")
        return

    df = pd.read_csv(filename)

    print("\n" + "═"*80)
    print(" 📊 AUDITORÍA DEL DATASET MAESTRO ".center(80, "═"))
    print("═"*80)

    acl_mediana = df['ACL_Post_Teo'].median()
    teo_media   = df['Fin_Teoria'].mean()
    print(f"  📂 Partidas: {len(df):,} | 👤 Usuarios: {df['Usuario'].nunique()}")
    print(f"  📉 Calidad (mediana): {acpl_to_accuracy(acl_mediana)}% Acc "
          f"| 📖 Teoría media: {teo_media:.1f} jugadas")
    print("─"*80)

    # Segmentación por tramos de Elo
    bins   = [0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 5000]
    labels = ["<1000","1000-1200","1200-1400","1400-1600",
              "1600-1800","1800-2000","2000-2200","2200-2400",">2400"]

    df['Tramo'] = pd.cut(df['Rating_Usuario'], bins=bins, labels=labels)

    dist = df.groupby('Tramo', observed=True).agg(
        Users    = ('Usuario',      'nunique'),
        Games    = ('Game_ID',      'count'),
        Teo_Med  = ('Fin_Teoria',   'mean'),
        Avg_ACL  = ('ACL_Post_Teo', 'mean'),
        Win_Rate = ('Victoria',     'mean'),
    )
    dist['Acc%'] = dist['Avg_ACL'].apply(acpl_to_accuracy)
    dist['Win%'] = (dist['Win_Rate'] * 100).round(1)
    dist['Teo_Med'] = dist['Teo_Med'].round(1)

    print("  DISTRIBUCIÓN TÉCNICA POR RATING:")
    print(dist[['Users', 'Games', 'Teo_Med', 'Acc%', 'Win%']].to_string())
    print("─"*80)

    # Alerta de desequilibrio
    faltantes = [str(t) for t, r in dist.iterrows() if r['Users'] < 2]
    if faltantes:
        print(f"  ⚠️  Tramos con pocos datos: {', '.join(faltantes)}")
    else:
        print("  ✅ Dataset equilibrado en todos los tramos de rating.")

    print("─"*80)
    print("  TOP 5 CONTRIBUYENTES:")
    top = df.groupby(['Usuario', 'Rating_Usuario']).agg(
        Partidas = ('Game_ID',     'count'),
        Teoria   = ('Fin_Teoria',  'mean')
    ).sort_values('Partidas', ascending=False).head(5)

    for (user, rat), r in top.iterrows():
        print(f"    {str(user)[:20].ljust(20)} | "
              f"Elo: {int(rat):>4} | "
              f"Partidas: {int(r['Partidas']):>3} | "
              f"Teo: {r['Teoria']:4.1f}j")

    print("═"*80 + "\n")


# Ejecutar auditoría sobre el dataset actual
diagnosticar_dataset()


# ---
# ## 9. Exportación del Notebook a Script `.py`
# 
# Utilidad opcional para exportar este notebook como script Python limpio.  
# Útil para integrar el pipeline en un entorno de producción o en el módulo `src/util/`.  
# Requiere tener instalado `nbconvert` (`pip install nbconvert`).

# In[ ]:


import nbformat
from nbconvert import PythonExporter

def exportar_notebook_a_script(nb_path: str, output_path: str) -> None:
    """
    Convierte un notebook .ipynb a un script .py limpio
    usando nbconvert.

    Parámetros
    ----------
    nb_path     : ruta al notebook origen.
    output_path : ruta de destino para el script .py.
    """
    with open(nb_path, encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    code, _ = PythonExporter().from_notebook_node(nb)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"✅ Script exportado → {output_path}")


NOTEBOOKS_DIR = os.path.join(PROJECT_ROOT, "src", "notebooks")
UTIL_DIR      = os.path.join(PROJECT_ROOT, "src", "util")

exportar_notebook_a_script(
    nb_path     = os.path.join(NOTEBOOKS_DIR, "Creacion de datos y esqueleto del programa.ipynb"),
    output_path = os.path.join(UTIL_DIR, "chess_intelligence_system.py")
)

