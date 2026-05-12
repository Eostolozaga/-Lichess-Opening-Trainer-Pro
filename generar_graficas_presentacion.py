"""
Generación de Gráficas para Presentación - Dificultades Técnicas
Lichess Opening Trainer Pro
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.patches import Rectangle
import pandas as pd

# ============================================================================
# CONFIGURACIÓN VISUAL - TEMA DARK DEL PROYECTO
# ============================================================================

plt.style.use('dark_background')

COLORS = {
    'bg': '#060a10',
    'bg2': '#0a0f1a',
    'bg3': '#0d1628',
    'blue': '#3b82f6',
    'blue_bright': '#60a5fa',
    'blue_dim': '#1e3a6e',
    'gold': '#d4a853',
    'gold_dim': '#8a6930',
    'text': '#e2e8f0',
    'text_muted': '#b8d0f0',
    'text_dim': '#8aafd4',
    'success': '#22c55e',
    'danger': '#ef4444',
    'warning': '#f59e0b'
}

def setup_plot_style(ax):
    """Aplica estilo consistente a los axes"""
    ax.set_facecolor(COLORS['bg2'])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['blue_dim'])
    ax.spines['bottom'].set_color(COLORS['blue_dim'])
    ax.tick_params(colors=COLORS['text_muted'], labelsize=9)
    ax.grid(True, alpha=0.1, color=COLORS['blue_dim'], linestyle='--')

# ============================================================================
# GRÁFICA 1: PROBLEMA DE OVERFITTING (Rating Feature)
# ============================================================================

def grafica_overfitting():
    """
    Comparación: Modelo Supervisado (con Rating) vs No Supervisado (sin Rating)
    Muestra cómo el rating causa overfitting perfecto
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(COLORS['bg'])
    
    # === SUBPLOT 1: Modelo Supervisado (Overfitting) ===
    ax1.set_title('Modelo Supervisado\n(CON Rating como Feature)',
                  fontsize=13, fontweight='bold', color=COLORS['text'], pad=15)
    
    # Datos simulados: accuracy casi perfecta
    ratings = [800, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400]
    accuracy_train = [98, 98, 99, 98, 99, 98, 99, 98, 99]
    accuracy_test = [42, 38, 51, 45, 62, 48, 55, 49, 53]  # Colapso en test
    
    x = np.arange(len(ratings))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, accuracy_train, width, label='Train Accuracy',
                    color=COLORS['success'], alpha=0.9)
    bars2 = ax1.bar(x + width/2, accuracy_test, width, label='Test Accuracy',
                    color=COLORS['danger'], alpha=0.9)
    
    ax1.set_xlabel('Rating Usuario', fontsize=10, color=COLORS['text_muted'])
    ax1.set_ylabel('Accuracy (%)', fontsize=10, color=COLORS['text_muted'])
    ax1.set_xticks(x)
    ax1.set_xticklabels(ratings, rotation=45)
    ax1.legend(loc='upper left', framealpha=0.9)
    ax1.set_ylim([0, 105])
    
    # Anotación de overfitting
    ax1.text(4.5, 75, '⚠ OVERFITTING\n98% train → 48% test',
             fontsize=11, fontweight='bold', color=COLORS['danger'],
             ha='center', bbox=dict(boxstyle='round,pad=0.5', 
                                    facecolor=COLORS['bg3'], 
                                    edgecolor=COLORS['danger'], linewidth=2))
    
    setup_plot_style(ax1)
    
    # === SUBPLOT 2: Modelo No Supervisado (Sin Rating) ===
    ax2.set_title('Clustering No Supervisado\n(SIN Rating - Features Puras)',
                  fontsize=13, fontweight='bold', color=COLORS['text'], pad=15)
    
    # Datos simulados: distribución más realista
    features = ['Accuracy\nPost-Teoría', 'Fin de\nTeoría (jug)', 
                'ACL\nWinsorized', 'Game\nRisk Index']
    importancia = [0.35, 0.28, 0.22, 0.15]
    
    bars = ax2.barh(features, importancia, color=COLORS['blue'], alpha=0.9)
    
    # Gradiente de color por importancia
    for i, (bar, imp) in enumerate(zip(bars, importancia)):
        bar.set_color(plt.cm.Blues(0.3 + imp * 0.7))
    
    ax2.set_xlabel('Importancia Relativa', fontsize=10, color=COLORS['text_muted'])
    ax2.set_xlim([0, 0.4])
    
    # Anotación de solución
    ax2.text(0.2, 3.5, '✓ GENERALIZABLE\nSilhouette Score: 0.68',
             fontsize=11, fontweight='bold', color=COLORS['success'],
             ha='center', bbox=dict(boxstyle='round,pad=0.5', 
                                    facecolor=COLORS['bg3'], 
                                    edgecolor=COLORS['success'], linewidth=2))
    
    setup_plot_style(ax2)
    ax2.spines['left'].set_visible(False)
    ax2.yaxis.set_ticks_position('none')
    
    plt.tight_layout()
    plt.savefig('grafica_1_overfitting.png', dpi=300, facecolor=COLORS['bg'], 
                bbox_inches='tight')
    print("✓ Gráfica 1 guardada: grafica_1_overfitting.png")

# ============================================================================
# GRÁFICA 2: CLUSTERING K=3 vs K=4 (Problema del Winrate)
# ============================================================================

def grafica_clustering():
    """
    Comparación visual de K=3 (correcto) vs K=4 (winrate noise)
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(COLORS['bg'])
    
    # Datos simulados de clustering
    np.random.seed(42)
    
    # === K=4: Con ruido de winrate ===
    ax1.set_title('K=4 Clusters\n(Separación por Winrate = Ruido)',
                  fontsize=13, fontweight='bold', color=COLORS['text'], pad=15)
    
    # Generar 4 clusters donde 2 son idénticos salvo winrate
    cluster1 = np.random.randn(40, 2) + [2, 2]    # Dominio High Winrate
    cluster2 = np.random.randn(40, 2) + [2, 2]    # Dominio Low Winrate (DUPLICADO)
    cluster3 = np.random.randn(40, 2) + [-2, 0]   # Desarrollo
    cluster4 = np.random.randn(40, 2) + [0, -2]   # Sin Base
    
    ax1.scatter(cluster1[:, 0], cluster1[:, 1], c=COLORS['success'], 
                alpha=0.6, s=60, label='Dominio (W%>55)', edgecolors='white', linewidth=0.5)
    ax1.scatter(cluster2[:, 0], cluster2[:, 1], c=COLORS['gold'], 
                alpha=0.6, s=60, label='Dominio (W%<45)', edgecolors='white', linewidth=0.5)
    ax1.scatter(cluster3[:, 0], cluster3[:, 1], c=COLORS['blue'], 
                alpha=0.6, s=60, label='Desarrollo', edgecolors='white', linewidth=0.5)
    ax1.scatter(cluster4[:, 0], cluster4[:, 1], c=COLORS['danger'], 
                alpha=0.6, s=60, label='Sin Base', edgecolors='white', linewidth=0.5)
    
    ax1.set_xlabel('Accuracy Post-Teoría', fontsize=10, color=COLORS['text_muted'])
    ax1.set_ylabel('Fin de Teoría (jugadas)', fontsize=10, color=COLORS['text_muted'])
    ax1.legend(loc='upper left', framealpha=0.9, fontsize=8)
    
    # Círculos de problema
    circle1 = plt.Circle((2, 2), 1.5, color=COLORS['warning'], fill=False, 
                        linewidth=3, linestyle='--', label='Overlap')
    ax1.add_patch(circle1)
    ax1.text(2, 4.5, '⚠ Mismo perfil\nde juego', fontsize=10, 
             color=COLORS['warning'], ha='center', fontweight='bold')
    
    setup_plot_style(ax1)
    
    # === K=3: Sin winrate ===
    ax2.set_title('K=3 Clusters FINAL\n(Solo Métricas de Calidad de Juego)',
                  fontsize=13, fontweight='bold', color=COLORS['text'], pad=15)
    
    # 3 clusters bien separados
    cluster1_clean = np.random.randn(80, 2) + [2, 2]   # Dominio (fusionado)
    cluster2_clean = np.random.randn(40, 2) + [-2, 0]  # Desarrollo
    cluster3_clean = np.random.randn(40, 2) + [0, -2]  # Sin Base
    
    ax2.scatter(cluster1_clean[:, 0], cluster1_clean[:, 1], c=COLORS['success'], 
                alpha=0.7, s=60, label='Dominio', edgecolors='white', linewidth=0.5)
    ax2.scatter(cluster2_clean[:, 0], cluster2_clean[:, 1], c=COLORS['blue'], 
                alpha=0.7, s=60, label='Desarrollo', edgecolors='white', linewidth=0.5)
    ax2.scatter(cluster3_clean[:, 0], cluster3_clean[:, 1], c=COLORS['danger'], 
                alpha=0.7, s=60, label='Sin Base', edgecolors='white', linewidth=0.5)
    
    ax2.set_xlabel('Accuracy Post-Teoría', fontsize=10, color=COLORS['text_muted'])
    ax2.set_ylabel('Fin de Teoría (jugadas)', fontsize=10, color=COLORS['text_muted'])
    ax2.legend(loc='upper left', framealpha=0.9, fontsize=9)
    
    # Anotación de éxito
    ax2.text(0, 4, '✓ Separación clara\nSilhouette: 0.68', fontsize=11, 
             color=COLORS['success'], ha='center', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=COLORS['bg3'], 
                      edgecolor=COLORS['success'], linewidth=2))
    
    setup_plot_style(ax2)
    
    plt.tight_layout()
    plt.savefig('grafica_2_clustering.png', dpi=300, facecolor=COLORS['bg'], 
                bbox_inches='tight')
    print("✓ Gráfica 2 guardada: grafica_2_clustering.png")

# ============================================================================
# GRÁFICA 3: DATA COLLECTION MULTI-FUENTE
# ============================================================================

def grafica_data_sources():
    """
    Distribución de recursos por fuente de datos
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(COLORS['bg'])
    
    ax.set_title('Recolección Multi-Fuente de Datos\n1,472 Recursos de 15 Plataformas',
                 fontsize=14, fontweight='bold', color=COLORS['text'], pad=20)
    
    # Datos reales del proyecto
    sources = ['Modern-Chess', 'Telegram', 'YouTube', 'Chessable', 
               'Manual', 'Chess.com', 'Udemy', 'Otros']
    counts = [827, 227, 148, 84, 77, 42, 25, 42]
    colors_sources = [COLORS['blue'], COLORS['gold'], COLORS['danger'], 
                      COLORS['success'], COLORS['text_muted'], COLORS['warning'],
                      COLORS['blue_bright'], COLORS['text_dim']]
    
    # Crear barras horizontales
    bars = ax.barh(sources, counts, color=colors_sources, alpha=0.85, 
                   edgecolor='white', linewidth=1)
    
    # Añadir valores y porcentajes
    total = sum(counts)
    for i, (bar, count) in enumerate(zip(bars, counts)):
        width = bar.get_width()
        percentage = (count / total) * 100
        ax.text(width + 20, bar.get_y() + bar.get_height()/2, 
                f'{count} ({percentage:.1f}%)',
                ha='left', va='center', fontsize=10, color=COLORS['text'],
                fontweight='bold')
    
    ax.set_xlabel('Número de Recursos', fontsize=11, color=COLORS['text_muted'])
    ax.set_xlim([0, 900])
    
    # Anotaciones de dificultad
    ax.text(850, 7, '⚠ ETL complejo\n4 formatos diferentes', 
            fontsize=9, color=COLORS['warning'], ha='right', 
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['bg3'], 
                     edgecolor=COLORS['warning'], linewidth=1.5))
    
    setup_plot_style(ax)
    ax.spines['left'].set_visible(False)
    ax.yaxis.set_ticks_position('none')
    
    plt.tight_layout()
    plt.savefig('grafica_3_data_sources.png', dpi=300, facecolor=COLORS['bg'], 
                bbox_inches='tight')
    print("✓ Gráfica 3 guardada: grafica_3_data_sources.png")

# ============================================================================
# GRÁFICA 4: CAMBIO DE GRANULARIDAD (Jugador → Apertura)
# ============================================================================

def grafica_granularidad():
    """
    Visualización del cambio de enfoque: Análisis por jugador vs por apertura
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(COLORS['bg'])
    
    # === SUBPLOT 1: Análisis por Jugador (Problema) ===
    ax1.set_title('❌ Análisis por JUGADOR\n(Pérdida de Información)',
                  fontsize=13, fontweight='bold', color=COLORS['danger'], pad=15)
    
    jugadores = ['User A\n(1800)', 'User B\n(1650)', 'User C\n(2000)']
    accuracy_global = [72, 65, 78]
    
    bars = ax1.bar(jugadores, accuracy_global, color=COLORS['danger'], 
                   alpha=0.7, edgecolor='white', linewidth=2)
    
    ax1.set_ylabel('Accuracy Global (%)', fontsize=10, color=COLORS['text_muted'])
    ax1.set_ylim([0, 100])
    
    # Anotación del problema
    ax1.text(1, 85, '⚠ Un jugador 1800 puede:\n• Dominar Sicilian (85% acc)\n• Ser débil en French (55% acc)',
             fontsize=9, color=COLORS['text'], ha='center',
             bbox=dict(boxstyle='round,pad=0.6', facecolor=COLORS['bg3'], 
                      edgecolor=COLORS['danger'], linewidth=2))
    
    setup_plot_style(ax1)
    
    # === SUBPLOT 2: Análisis por Apertura (Solución) ===
    ax2.set_title('✓ Análisis por (USUARIO, APERTURA)\n(Granularidad Fina)',
                  fontsize=13, fontweight='bold', color=COLORS['success'], pad=15)
    
    # Datos de ejemplo: User A con diferentes aperturas
    aperturas = ['Sicilian\nDefense', 'French\nDefense', 'Caro-Kann\nDefense', 
                 'Italian\nGame', 'Queen\'s\nGambit']
    accuracy_por_apertura = [85, 55, 78, 92, 68]
    colores_aperturas = [COLORS['success'], COLORS['danger'], COLORS['blue'],
                         COLORS['success'], COLORS['warning']]
    
    bars2 = ax2.bar(aperturas, accuracy_por_apertura, 
                    color=colores_aperturas, alpha=0.7, 
                    edgecolor='white', linewidth=2)
    
    ax2.set_ylabel('Accuracy por Apertura (%)', fontsize=10, color=COLORS['text_muted'])
    ax2.set_ylim([0, 100])
    ax2.set_xlabel('User A (1800 rating)', fontsize=10, 
                   color=COLORS['text_muted'], fontweight='bold')
    
    # Líneas de umbral
    ax2.axhline(y=80, color=COLORS['success'], linestyle='--', 
                linewidth=1.5, alpha=0.5, label='Dominio (>80%)')
    ax2.axhline(y=60, color=COLORS['danger'], linestyle='--', 
                linewidth=1.5, alpha=0.5, label='Riesgo (<60%)')
    ax2.legend(loc='upper right', framealpha=0.9, fontsize=8)
    
    # Anotación de solución
    ax2.text(2, 48, '✓ Detección de\nfortalezas/debilidades\nPOR VARIANTE',
             fontsize=9, color=COLORS['success'], ha='center', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=COLORS['bg3'], 
                      edgecolor=COLORS['success'], linewidth=2))
    
    setup_plot_style(ax2)
    
    plt.tight_layout()
    plt.savefig('grafica_4_granularidad.png', dpi=300, facecolor=COLORS['bg'], 
                bbox_inches='tight')
    print("✓ Gráfica 4 guardada: grafica_4_granularidad.png")

# ============================================================================
# EJECUTAR TODAS LAS GRÁFICAS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("GENERANDO GRÁFICAS PARA PRESENTACIÓN")
    print("="*70 + "\n")
    
    print("[1/4] Gráfica de Overfitting...")
    grafica_overfitting()
    
    print("[2/4] Gráfica de Clustering K=3 vs K=4...")
    grafica_clustering()
    
    print("[3/4] Gráfica de Data Sources...")
    grafica_data_sources()
    
    print("[4/4] Gráfica de Granularidad...")
    grafica_granularidad()
    
    print("\n" + "="*70)
    print("✅ TODAS LAS GRÁFICAS GENERADAS EXITOSAMENTE")
    print("="*70)
    print("\nArchivos creados:")
    print("  • grafica_1_overfitting.png")
    print("  • grafica_2_clustering.png")
    print("  • grafica_3_data_sources.png")
    print("  • grafica_4_granularidad.png")
    print("\nGuárdalas en: resources/img/")
