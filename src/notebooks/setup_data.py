#!/usr/bin/env python3
"""
Script de configuración para descargar archivos pesados del proyecto
Lichess Opening Trainer Pro

Descarga automáticamente:
- Stockfish engine (15-20 MB)
- theory_db.pkl (50-70 MB)
- Datasets CSV de ejemplo (opcional)
"""

import os
import sys
import zipfile
import platform
import requests
from pathlib import Path
from tqdm import tqdm


# ============================================================================
# CONFIGURACIÓN DE RUTAS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
ENGINES_DIR = PROJECT_ROOT / "resources" / "engines"
PKL_DIR = PROJECT_ROOT / "src" / "data" / "PKL"
CSV_DIR = PROJECT_ROOT / "src" / "data" / "CSV"

# ============================================================================
# ENLACES DE DESCARGA
# ============================================================================

# Stockfish: detección automática según OS
STOCKFISH_URLS = {
    "Windows": "https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-windows-x86-64-avx2.zip",
    "Linux": "https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64-avx2.tar",
    "Darwin": "https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-macos-m1-apple-silicon.tar"
}

# ⚠️ IMPORTANTE: Reemplaza estos enlaces con tus archivos de Google Drive/Dropbox
THEORY_DB_URL = "https://drive.google.com/uc?export=download&id=15H-iux9QCX-soiag5ijWJNqNLM2C_0KT"
CSV_EXAMPLES_URL = None  # Opcional: URL de archivo ZIP con CSVs de ejemplo

# ============================================================================
# FUNCIONES DE DESCARGA
# ============================================================================

def download_file(url: str, destination: Path, description: str = "Descargando"):
    """
    Descarga un archivo con barra de progreso
    """
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        with open(destination, 'wb') as file, tqdm(
            desc=description,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                size = file.write(chunk)
                bar.update(size)
        
        print(f"✅ {description} completado: {destination}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al descargar {description}: {e}")
        return False


def download_stockfish():
    """
    Descarga Stockfish según el sistema operativo
    """
    print("\n" + "="*60)
    print("📥 DESCARGANDO STOCKFISH ENGINE")
    print("="*60)
    
    system = platform.system()
    
    if system not in STOCKFISH_URLS:
        print(f"❌ Sistema operativo no soportado: {system}")
        print("⚠️  Descarga manual desde: https://stockfishchess.org/download/")
        return False
    
    url = STOCKFISH_URLS[system]
    temp_file = PROJECT_ROOT / f"stockfish_temp.{'zip' if system == 'Windows' else 'tar'}"
    
    # Descargar archivo
    if not download_file(url, temp_file, f"Stockfish para {system}"):
        return False
    
    # Extraer archivo
    try:
        print("📦 Extrayendo archivos...")
        ENGINES_DIR.mkdir(parents=True, exist_ok=True)
        
        if system == "Windows":
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(ENGINES_DIR)
            
            # Buscar el ejecutable dentro de la carpeta extraída
            for root, dirs, files in os.walk(ENGINES_DIR):
                for file in files:
                    if file.endswith('.exe'):
                        src = Path(root) / file
                        dst = ENGINES_DIR / "stockfish-windows-x86-64-avx2.exe"
                        if src != dst:
                            src.rename(dst)
                        break
        else:
            import tarfile
            with tarfile.open(temp_file) as tar_ref:
                tar_ref.extractall(ENGINES_DIR)
        
        temp_file.unlink()  # Eliminar archivo temporal
        print("✅ Stockfish extraído correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al extraer Stockfish: {e}")
        return False


def download_theory_db():
    """
    Descarga la base de datos teórica theory_db.pkl
    """
    print("\n" + "="*60)
    print("📥 DESCARGANDO BASE DE DATOS TEÓRICA")
    print("="*60)
    
    if "TU_FILE_ID_AQUI" in THEORY_DB_URL:
        print("⚠️  URL de theory_db.pkl no configurada")
        print("⚠️  Por favor, edita setup_data.py y reemplaza THEORY_DB_URL")
        print("⚠️  con el enlace de descarga directa de tu archivo")
        return False
    
    destination = PKL_DIR / "theory_db.pkl"
    
    return download_file(THEORY_DB_URL, destination, "theory_db.pkl")


def download_csv_examples():
    """
    Descarga CSVs de ejemplo (opcional)
    """
    if CSV_EXAMPLES_URL is None:
        print("\n⏭️  CSVs de ejemplo no configurados (opcional)")
        return True
    
    print("\n" + "="*60)
    print("📥 DESCARGANDO CSV DE EJEMPLO")
    print("="*60)
    
    temp_file = PROJECT_ROOT / "csv_examples.zip"
    
    if not download_file(CSV_EXAMPLES_URL, temp_file, "CSVs de ejemplo"):
        return False
    
    # Extraer CSVs
    try:
        with zipfile.ZipFile(temp_file, 'r') as zip_ref:
            zip_ref.extractall(CSV_DIR)
        
        temp_file.unlink()
        print("✅ CSVs de ejemplo extraídos correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al extraer CSVs: {e}")
        return False


def verify_installation():
    """
    Verifica que todos los archivos necesarios estén en su lugar
    """
    print("\n" + "="*60)
    print("🔍 VERIFICANDO INSTALACIÓN")
    print("="*60)
    
    required_files = [
        (ENGINES_DIR / "stockfish-windows-x86-64-avx2.exe", "Stockfish Engine"),
        (PKL_DIR / "theory_db.pkl", "Base de Datos Teórica"),
    ]
    
    all_ok = True
    
    for file_path, name in required_files:
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"✅ {name}: {file_path} ({size_mb:.1f} MB)")
        else:
            print(f"❌ {name}: NO ENCONTRADO")
            all_ok = False
    
    return all_ok


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║   LICHESS OPENING TRAINER PRO - Setup de Datos Pesados      ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Este script descargará automáticamente:
    1. ✅ Stockfish Engine (~15-20 MB)
    2. ⚠️  theory_db.pkl (~50-70 MB) [REQUIERE CONFIGURACIÓN]
    3. ⏭️  CSVs de ejemplo (opcional)
    
    """)
    
    # Crear directorios si no existen
    ENGINES_DIR.mkdir(parents=True, exist_ok=True)
    PKL_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    
    # Descargas
    results = {
        "stockfish": download_stockfish(),
        "theory_db": download_theory_db(),
        "csv_examples": download_csv_examples()
    }
    
    # Verificación final
    print("\n")
    if verify_installation():
        print("\n" + "="*60)
        print("🎉 ¡INSTALACIÓN COMPLETADA CON ÉXITO!")
        print("="*60)
        print("\nPuedes ejecutar la aplicación con:")
        print("  streamlit run app_17.py")
    else:
        print("\n" + "="*60)
        print("⚠️  INSTALACIÓN INCOMPLETA")
        print("="*60)
        print("\nPor favor, descarga manualmente los archivos faltantes.")
        print("Consulta el README.md para instrucciones detalladas.")
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        sys.exit(1)
