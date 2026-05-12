# ♟ Lichess Opening Trainer Pro

<div align="center">

**Análisis inteligente de repertorio de aperturas con Machine Learning**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-K--Means-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Stockfish](https://img.shields.io/badge/Stockfish-16-6d4c41?style=flat-square)](https://stockfishchess.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

*¿Cuántas partidas llevas jugadas sin saber qué aperturas realmente dominas?*

</div>

---

## ¿Qué es esto?

**Lichess Opening Trainer Pro** conecta la API de Lichess con un motor de ajedrez (Stockfish) y un modelo de clustering K-Means para responder una pregunta que ninguna plataforma te contesta:

> *"De todas las aperturas que juegas, ¿cuáles dominas de verdad, cuáles son una trampa recurrente y cuáles juegas bien por instinto sin saber por qué?"*

El sistema descarga tus partidas, las evalúa movimiento a movimiento, clasifica cada apertura en uno de tres niveles y genera un plan de estudio personalizado con recursos concretos (libros, cursos de Chessable, vídeos de YouTube) filtrados por tu Elo.

---

## Características principales

- **Descarga automática** de hasta 500 partidas desde la API de Lichess
- **Análisis con Stockfish 16** (depth=16) en una ventana de 12 jugadas post-teoría
- **Base teórica de 327.000 posiciones EPD** para detectar con precisión cuándo sales de la teoría
- **Clustering K-Means (K=3)** que clasifica cada apertura en: `Dominio` · `Desarrollo` · `Sin Base`
- **Detección de Feeling Natural**: aperturas que juegas bien por instinto sin conocer la teoría
- **Catálogo de 1.472 recursos** (YouTube, Chessable, Telegram, bases públicas) con matching semántico
- **Detección y exportación de blunders** (>100cp) directamente a un estudio de Lichess
- **Dashboard interactivo** con métricas personalizadas y plan de estudio priorizado

---

## Demo

```
Usuario: tu_nick_de_lichess
Partidas analizadas: 150
Tiempo de análisis: ~4 min (Stockfish local, depth=16)
```

| Métrica | Ejemplo |
|---|---|
| Precisión media post-apertura | 67.4% |
| Jugadas de teoría seguidas (media) | 8.2 |
| Aperturas en zona de riesgo | 3 |
| Aperturas de feeling natural | 5 |
| Blunders detectados | 12 |

---

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────┐
│                    INGESTA DE DATOS                     │
│  API Lichess (/api/games/user/{user})  →  PGN Parser    │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  ANÁLISIS TEÓRICO                       │
│  theory_db.pkl (327K posiciones EPD)  →  Fin_Teoria     │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│               ANÁLISIS DE RENDIMIENTO                   │
│  Stockfish 16 (depth=16)  →  ACL_Post_Teo + blunders    │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  FEATURE ENGINEERING                    │
│  AccAjustada · game_prep_score · game_risk_index        │
└──────────────────────────┬──────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
┌─────────▼─────────┐             ┌─────────▼──────────┐
│   K-MEANS (K=3)   │             │  RECOMENDADOR       │
│  Dominio          │             │  1.472 recursos     │
│  Desarrollo       │             │  Matching semántico │
│  Sin Base         │             │  Filtro por Elo     │
└─────────┬─────────┘             └─────────┬──────────┘
          │                                 │
┌─────────▼─────────────────────────────────▼──────────┐
│                  DASHBOARD STREAMLIT                   │
│         Dashboard · Plan de Estudio · Blunders        │
└───────────────────────────────────────────────────────┘
```

---

## Estructura del proyecto

```
Proyecto ML/
│
├── app_15.py                        # Aplicación principal Streamlit
│
├── src/
│   ├── data/
│   │   ├── CSV/                     # Datasets generados
│   │   │   ├── master_game_level_ml.csv   # Dataset principal (18K partidas)
│   │   │   ├── master_dataset_ml.csv      # Dataset base (feature engineering)
│   │   │   ├── chess_resources_v3.csv     # Catálogo de recursos (1.472)
│   │   │   ├── user_opening_profiles.csv  # Perfiles por apertura
│   │   │   ├── perfiles_lichess_final.csv # Perfiles finales con clusters
│   │   │   ├── user_profiles_summary.csv  # Resumen de perfiles
│   │   │   └── blunders_pendientes.csv    # Blunders detectados
│   │   │
│   │   ├── PKL/                     # Modelos serializados
│   │   │   ├── km_apertura_pura.pkl       # Modelo K-Means entrenado
│   │   │   ├── scaler_apertura_pura.pkl   # StandardScaler
│   │   │   └── theory_db.pkl              # 327K posiciones EPD
│   │   │
│   │   └── Libro aperturas/         # Fuentes teóricas
│   │
│   ├── model/
│   │   └── production/              # Artefactos de producción
│   │
│   ├── notebooks/                   # Exploración y entrenamiento
│   │   ├── 01_EDA.ipynb
│   │   ├── 02_feature_engineering.ipynb
│   │   ├── 03_clustering.ipynb
│   │   └── 04_recomendador.ipynb
│   │
│   └── util/
│       └── chess_game_level_augmentation.py  # Funciones de enriquecimiento
│
└── resources/
    ├── engines/
    │   └── stockfish                # Binario de Stockfish 16
    └── img/                         # Assets visuales
```

---

## Instalación

### Requisitos previos

- Python 3.10+
- Stockfish 16 ([descargar aquí](https://stockfishchess.org/download/))
- Token de API de Lichess ([obtener aquí](https://lichess.org/account/oauth/token))

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu_usuario/lichess-opening-trainer-pro.git
cd lichess-opening-trainer-pro

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Colocar el binario de Stockfish
# Linux/Mac: copiar a resources/engines/stockfish
# Windows:   copiar a resources/engines/stockfish.exe

# 5. Lanzar la aplicación
streamlit run app_15.py
```

### requirements.txt

```txt
streamlit>=1.32.0
python-chess>=1.999
stockfish>=3.28.0
scikit-learn>=1.4.0
pandas>=2.2.0
numpy>=1.26.0
joblib>=1.3.0
requests>=2.31.0
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.25.0
```

---

## Configuración

En el panel lateral de la app introduce:

| Campo | Descripción | Obligatorio |
|---|---|---|
| **Usuario de Lichess** | Tu nick exacto en Lichess | ✅ |
| **Token de API** | Token OAuth de Lichess (scope: `games:read`) | ✅ |
| **Study ID** | ID del estudio de Lichess para exportar blunders | ⬜ opcional |
| **Nº de partidas** | Máximo a analizar (recomendado: 100) | ✅ |

> **Nota sobre el token**: El token se usa exclusivamente para descargar tus partidas y subir blunders a tu estudio. No se almacena en disco en ningún momento.

---

## Cómo funciona el modelo

### Feature Engineering

A partir de los datos brutos se derivan tres variables clave:

| Variable | Fórmula | Qué detecta |
|---|---|---|
| `AccAjustada` | `Accuracy × (1 - 0.15 × teoria_norm)` | Penaliza precisión sin respaldo teórico |
| `game_prep_score` | `(Fin_Teoria/15) × (Accuracy/100)` | Jugador bien preparado que ejecuta bien |
| `game_risk_index` | `(Fin_Teoria/15) × (100 - Accuracy)` | Mucha teoría memorizada, baja ejecución |

### Clustering K-Means

```python
KMeans(n_clusters=3, init='k-means++', n_init=20, random_state=42)
```

| Cluster | Etiqueta | ACL medio | Teoría media |
|---|---|---|---|
| 0 | **Dominio** | 35 cp | 11.2 jugadas |
| 1 | **Desarrollo** | 65 cp | 8.5 jugadas |
| 2 | **Sin Base** | 110 cp | 5.8 jugadas |

**Silhouette Score: 0.48** — robusto para datos de comportamiento humano.

### Sistema de recomendación

El motor de recomendación aplica tres filtros en orden:

```
1. Matching semántico  →  normaliza nombres ("Ruy Lopez" = "Spanish Game")
2. Filtro por Elo      →  level_min ≤ Rating usuario ≤ level_max
3. Scoring ponderado   →  60×apertura + 20×título + 0.5×rating_score
4. Fallback            →  búsqueda automática en Lichess Studies públicos
```

El catálogo de 1.472 recursos fue construido mediante scraping multi-fuente:
- **YouTube API v3**: 800+ vídeos con metadatos de visualizaciones y nivel
- **Telegram** (Telethon): 350+ recursos de 15 canales especializados (`@ChessCourses`, `@ChessOpenings`…)
- **Chessable**: 200+ cursos con rating sugerido, autor y número de variantes
- **Bases públicas**: Lichess Studies y Chess.com Articles

---

## Dataset

El dataset principal `master_game_level_ml.csv` contiene **18.041 registros** con las siguientes variables:

| Variable | Tipo | Descripción |
|---|---|---|
| `Game_ID` | String | ID único de Lichess |
| `Usuario` | String | Nick del jugador |
| `Rating_Usuario` | Integer | Elo Blitz |
| `Apertura` | String | Nombre ECO de la apertura |
| `Color` | String | `Blancas` / `Negras` |
| `Fin_Teoria` | Integer | Jugada de salida de teoría (máx. 15) |
| `ACL_Post_Teo` | Float | Pérdida media en centipeones (12 jugadas post-teoría) |
| `Accuracy` | Float | `100 × exp(-0.0035 × ACL)` |
| `Victoria` | Float | `1.0` victoria · `0.5` tablas · `0.0` derrota |
| `game_prep_score` | Float | Índice de preparación efectiva |
| `game_risk_index` | Float | Índice de riesgo de la apertura |
| `AccAjustada` | Float | Precisión penalizada por baja teoría |

---

## Resultados

### Categorías de aperturas

| Categoría | Criterio | Acción recomendada |
|---|---|---|
| ⚠️ **Riesgo** | Risk Index > p60 AND Accuracy < media−10 | Estudiar o cambiar de repertorio |
| ✦ **Dominio** | Score Prep > p50 AND Accuracy > media−5 | Ampliar variantes |
| ◈ **Feeling Natural** | Teoría < media−20% AND Accuracy > media−8 | Explotar como ventaja competitiva |

### Validación del clustering

Los tres clusters presentan gradientes **claros y monótonos** en todas las features: el cluster `Dominio` siempre tiene el menor ACL y más teoría, `Sin Base` el mayor ACL y menos teoría. Jugadores reales reconocen sus aperturas en las tres categorías sin necesidad de explicación.

---

## Limitaciones conocidas

- Requiere **mínimo 2 partidas por apertura** para clasificar (evita falsos positivos)
- La ventana de análisis son **12 jugadas propias** post-teoría — no cubre errores en medio-juego tardío
- Las Blancas tienen sistemáticamente más teoría que las Negras; el análisis se separa por color para compensar
- Aperturas ultra-minoritarias (Polish Opening, Owen Defense, Grob) tienen cobertura limitada en el catálogo (<3 recursos)
- El scraping de Telegram requiere mantenimiento continuo por la volatilidad de los canales

---

## Roadmap

**Corto plazo**
- [ ] Análisis de variantes específicas dentro de cada apertura (Najdorf vs Dragon en la Siciliana)
- [ ] Dashboard comparativo contra jugadores del mismo rango de Elo
- [ ] Evolución temporal: detección de mejora en aperturas críticas tras estudio

**Medio plazo**
- [ ] Modelo supervisado (Random Forest / XGBoost) para predecir victoria en función de apertura + perfil
- [ ] Sistema de alertas: notificación cuando una apertura pasa de Desarrollo a Riesgo
- [ ] Integración automática con Lichess Studies para variantes de aperturas en riesgo

**Largo plazo**
- [ ] Embeddings de posición con modelos transformers (Leela Chess Zero)
- [ ] Expansión a Chess.com con análisis multi-plataforma
- [ ] Modelo freemium: 50 partidas gratis / histórico completo premium

---

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | Streamlit 1.x + CSS custom (Inter + Rajdhani) |
| ML | scikit-learn (K-Means, StandardScaler) |
| Motor de ajedrez | Stockfish 16 (depth=16) |
| Procesamiento PGN | python-chess |
| Base teórica | 327K posiciones EPD (EPD format) |
| Datos | pandas, numpy, joblib |
| APIs externas | Lichess REST API, YouTube Data API v3 |
| Scraping | BeautifulSoup, Telethon (Telegram) |
| Serialización | pickle, joblib (.pkl) |

---

## Autor

**Eneko Ostolozaga**
Bootcamp Data Science e IA Generativa · 2026

---

## Licencia

Distribuido bajo licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

<div align="center">

*"El ajedrez tiene 500 años de teoría. Los datos tienen 500 millones de partidas online.*
*Por primera vez podemos cruzar ambas cosas a nivel individual."*

</div>
