# 🏆 Lichess Opening Trainer Pro

Sistema de análisis y recomendación de repertorio de aperturas para usuarios de Lichess.

## 🚀 Setup

### 1. Clonar repositorio
```bash
git clone [tu-repo-url]
cd "Proyecto ML"
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Descargar Stockfish
- Descargar desde: https://stockfishchess.org/download/
- Colocar en: `resources/engines/stockfish.exe` (Windows) o `resources/engines/stockfish` (Linux/Mac)

### 4. Generar datos base
```bash
# Ejecutar notebook de creación de datos
jupyter notebook Creacion_de_datos_y_esqueleto_del_programa.ipynb
```

### 5. Ejecutar aplicación
```bash
streamlit run app_17.py
```

## 📁 Estructura de Datos

### Archivos que debes generar localmente:
- `src/data/PKL/theory_db.pkl` - Base de datos de teoría (327K posiciones)
- `src/data/PKL/km_apertura_pura.pkl` - Modelo KMeans entrenado
- `src/data/PKL/scaler_apertura_pura.pkl` - Scaler de features

### Archivos incluidos:
- `src/data/chess_resources_v3.csv` - Catálogo de recursos educativos

## 🔑 Configuración API Lichess
Necesitas token de API de Lichess:
1. Ir a https://lichess.org/account/oauth/token
2. Crear token con permisos de lectura
3. Configurar en la app

