#!/usr/bin/env python3
"""
SCRIPT DE INTEGRACIÓN AUTOMÁTICA DE RECURSOS - VERSIÓN WINDOWS
===============================================================
Detecta automáticamente la ubicación de los archivos CSV

Ejecutar desde cualquier ubicación:
python mergear_recursos_v3_windows.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import os

# ═══════════════════════════════════════════════════════════════════════════
# DETECCIÓN AUTOMÁTICA DE RUTAS
# ═══════════════════════════════════════════════════════════════════════════

def encontrar_directorio_csv():
    """
    Busca el directorio CSV en las ubicaciones más probables
    """
    # Obtener directorio del script
    script_dir = Path(__file__).parent.absolute()
    
    # Posibles ubicaciones del directorio CSV
    posibles_rutas = [
        # Si el script está en src/notebooks/
        script_dir.parent / "data" / "CSV",
        # Si el script está en el directorio raíz del proyecto
        script_dir / "src" / "data" / "CSV",
        # Si el script está en la carpeta de outputs
        script_dir.parent.parent / "src" / "data" / "CSV",
        # Ruta relativa desde donde se ejecuta
        Path.cwd() / "src" / "data" / "CSV",
        # Directorio actual (por si los CSV están en la misma carpeta)
        Path.cwd(),
    ]
    
    print("🔍 Buscando archivos CSV...")
    for ruta in posibles_rutas:
        print(f"   Verificando: {ruta}")
        v3_path = ruta / "chess_resources_v3.csv"
        final_path = ruta / "chess_resources_final.csv"
        
        if v3_path.exists() and final_path.exists():
            print(f"   ✅ Encontrados en: {ruta}")
            return ruta
    
    # Si no se encuentra, pedir al usuario
    print("\n⚠️  No se encontraron los archivos CSV automáticamente")
    print("\nPor favor, ingresa la ruta completa del directorio donde están los CSV:")
    print("Ejemplo: C:\\Users\\Eneko\\Desktop\\Ejercicios Data\\Proyectos\\Proyecto ML\\src\\data\\CSV")
    
    ruta_manual = input("\nRuta: ").strip()
    ruta_manual = Path(ruta_manual)
    
    if not ruta_manual.exists():
        raise FileNotFoundError(f"El directorio no existe: {ruta_manual}")
    
    v3_path = ruta_manual / "chess_resources_v3.csv"
    final_path = ruta_manual / "chess_resources_final.csv"
    
    if not v3_path.exists() or not final_path.exists():
        raise FileNotFoundError(f"No se encontraron los archivos CSV en: {ruta_manual}")
    
    return ruta_manual

# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONES (IGUAL QUE ANTES)
# ═══════════════════════════════════════════════════════════════════════════

def crear_backup(archivo_path, backup_dir):
    """Crea backup con timestamp"""
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"{archivo_path.stem}_backup_{timestamp}.csv"
    
    df = pd.read_csv(archivo_path)
    df.to_csv(backup_file, index=False)
    
    print(f"✅ Backup creado: {backup_file}")
    return backup_file

def mapear_columnas(df_source, columnas_target):
    """Mapea df_source (38 cols) a las columnas de target (28 cols)"""
    df_mapped = df_source[columnas_target].copy()
    return df_mapped

def identificar_recursos_nuevos(df_v3, df_final):
    """Identifica recursos que están en final pero NO en v3"""
    ids_v3 = set(df_v3['resource_id'].values)
    ids_final = set(df_final['resource_id'].values)
    
    ids_nuevos = ids_final - ids_v3
    
    print(f"\n📊 Análisis de recursos:")
    print(f"   En v3:           {len(ids_v3)}")
    print(f"   En final:        {len(ids_final)}")
    print(f"   Nuevos a añadir: {len(ids_nuevos)}")
    
    return ids_nuevos

def mergear_recursos(df_v3, df_final, ids_nuevos, columnas_v3):
    """Mergea los recursos nuevos en v3 manteniendo su estructura"""
    df_nuevos = df_final[df_final['resource_id'].isin(ids_nuevos)].copy()
    df_nuevos_mapped = mapear_columnas(df_nuevos, columnas_v3)
    df_merged = pd.concat([df_v3, df_nuevos_mapped], ignore_index=True)
    
    print(f"\n✅ Merge completado:")
    print(f"   Recursos originales:  {len(df_v3)}")
    print(f"   Recursos añadidos:    {len(df_nuevos_mapped)}")
    print(f"   Total final:          {len(df_merged)}")
    
    return df_merged

def verificar_integridad(df):
    """Verifica que no haya duplicados ni problemas"""
    print(f"\n🔍 Verificación de integridad:")
    
    duplicados = df['resource_id'].duplicated().sum()
    print(f"   Duplicados:           {duplicados}")
    
    if duplicados > 0:
        print(f"   ⚠️  ADVERTENCIA: Se encontraron {duplicados} duplicados")
        print("   Eliminando duplicados...")
        df = df.drop_duplicates(subset=['resource_id'], keep='first')
        print(f"   ✅ Duplicados eliminados. Total: {len(df)}")
    
    print(f"\n📦 Top 10 fuentes:")
    fuentes = df['source'].value_counts().head(10)
    for source, count in fuentes.items():
        print(f"   {source:<20} {count:>4}")
    
    telegram_count = df['source'].str.contains('telegram', case=False, na=False).sum()
    chessable_count = (df['source'] == 'chessable').sum()
    
    print(f"\n🎯 Verificación de fuentes críticas:")
    print(f"   Telegram:   {telegram_count:>4} recursos ✅" if telegram_count > 0 else "   Telegram:      0 recursos ❌")
    print(f"   Chessable:  {chessable_count:>4} recursos ✅" if chessable_count > 0 else "   Chessable:     0 recursos ❌")
    
    return df

def generar_reporte_cambios(df_antes, df_despues):
    """Genera reporte de cambios por nivel y fuente"""
    print(f"\n" + "="*70)
    print("REPORTE DE CAMBIOS")
    print("="*70)
    
    print(f"\n📊 Cambios por nivel:")
    print(f"{'Nivel':<15} {'Antes':<10} {'Después':<10} {'Diferencia':<10}")
    print("-" * 50)
    
    for nivel in ['beginner', 'intermediate', 'advanced', 'expert']:
        antes = (df_antes['level_tier'] == nivel).sum()
        despues = (df_despues['level_tier'] == nivel).sum()
        diff = despues - antes
        if diff != 0 or antes > 0 or despues > 0:
            emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➖"
            print(f"{nivel:<15} {antes:<10} {despues:<10} {'+' if diff > 0 else ''}{diff:<9} {emoji}")
    
    print("-" * 50)
    print(f"{'TOTAL':<15} {len(df_antes):<10} {len(df_despues):<10} +{len(df_despues) - len(df_antes)}")

# ═══════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("="*70)
    print("INTEGRACIÓN AUTOMÁTICA DE RECURSOS FALTANTES")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 0. Detectar ubicación de archivos
    try:
        csv_dir = encontrar_directorio_csv()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Asegúrate de que los archivos CSV estén en:")
        print("   - chess_resources_v3.csv")
        print("   - chess_resources_final.csv")
        input("\nPresiona Enter para salir...")
        return
    
    # Configurar rutas
    archivo_v3 = csv_dir / "chess_resources_v3.csv"
    archivo_final = csv_dir / "chess_resources_final.csv"
    backup_dir = csv_dir / "backups"
    
    print(f"\n📂 Directorio de trabajo: {csv_dir}")
    print(f"   Archivo v3:    {archivo_v3.name}")
    print(f"   Archivo final: {archivo_final.name}")
    
    # 1. Crear backup
    print("\n🔄 Paso 1: Creando backup...")
    try:
        backup_file = crear_backup(archivo_v3, backup_dir)
    except Exception as e:
        print(f"❌ ERROR creando backup: {e}")
        input("\nPresiona Enter para salir...")
        return
    
    # 2. Cargar archivos
    print("\n🔄 Paso 2: Cargando archivos...")
    df_v3 = pd.read_csv(archivo_v3)
    df_final = pd.read_csv(archivo_final)
    
    print(f"   Cargado v3:    {len(df_v3)} recursos, {len(df_v3.columns)} columnas")
    print(f"   Cargado final: {len(df_final)} recursos, {len(df_final.columns)} columnas")
    
    # 3. Identificar recursos nuevos
    print("\n🔄 Paso 3: Identificando recursos nuevos...")
    columnas_v3 = df_v3.columns.tolist()
    ids_nuevos = identificar_recursos_nuevos(df_v3, df_final)
    
    if len(ids_nuevos) == 0:
        print("\n✅ No hay recursos nuevos para añadir. El archivo ya está completo.")
        input("\nPresiona Enter para salir...")
        return
    
    # 4. Mergear
    print("\n🔄 Paso 4: Mergeando recursos...")
    df_merged = mergear_recursos(df_v3, df_final, ids_nuevos, columnas_v3)
    
    # 5. Verificar integridad
    print("\n🔄 Paso 5: Verificando integridad...")
    df_merged = verificar_integridad(df_merged)
    
    # 6. Generar reporte
    print("\n🔄 Paso 6: Generando reporte de cambios...")
    generar_reporte_cambios(df_v3, df_merged)
    
    # 7. Guardar
    print(f"\n🔄 Paso 7: Guardando archivo actualizado...")
    df_merged.to_csv(archivo_v3, index=False)
    print(f"   ✅ Guardado: {archivo_v3}")
    
    # Resumen final
    print("\n" + "="*70)
    print("✅ INTEGRACIÓN COMPLETADA EXITOSAMENTE")
    print("="*70)
    print(f"\nResumen:")
    print(f"  • Backup: {backup_file}")
    print(f"  • Recursos originales: {len(df_v3)}")
    print(f"  • Recursos añadidos: {len(ids_nuevos)}")
    print(f"  • Total final: {len(df_merged)}")
    print(f"\n✨ Telegram: {(df_merged['source'] == 'telegram_file').sum()} cursos")
    print(f"✨ Chessable: {(df_merged['source'] == 'chessable').sum()} cursos")
    print("\n" + "="*70)
    
    input("\n✅ Proceso completado. Presiona Enter para salir...")

# ═══════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        print("\nDetalles del error:")
        import traceback
        traceback.print_exc()
        input("\nPresiona Enter para salir...")
