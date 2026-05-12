"""
Componente de Profesor Virtual Animado
Muestra mensajes personalizados en un bocadillo según el nivel del jugador
"""

def render_profesor_virtual(nivel, rating, accuracy_media, mensaje_custom=None):
    """
    Renderiza un profesor virtual animado con bocadillo de diálogo.
    
    Args:
        nivel: "sin_base", "desarrollo", "dominio"
        rating: ELO del jugador
        accuracy_media: Precisión promedio
        mensaje_custom: Mensaje personalizado opcional
    """
    import streamlit as st
    
    # Determinar avatar y mensaje según nivel
    avatares = {
        "sin_base": "🎓",      # Estudiante
        "desarrollo": "👨‍🏫",   # Profesor
        "dominio": "🏆"         # Maestro
    }
    
    if mensaje_custom:
        mensaje = mensaje_custom
    else:
        if nivel == "sin_base":
            mensajes = [
                f"¡Bienvenido! Con {rating} ELO, estás comenzando tu viaje. ¡Vamos a construir una base sólida! 💪",
                f"Tu accuracy promedio es {accuracy_media:.1f}%. ¡Hay mucho potencial de mejora! 📈",
                "Enfócate primero en las aperturas de 'Éxito Natural' - son tu punto fuerte.",
            ]
        elif nivel == "desarrollo":
            mensajes = [
                f"¡Excelente progreso! Con {rating} ELO y {accuracy_media:.1f}% de accuracy, estás en buen camino. 🚀",
                "Tu repertorio tiene una base sólida. Ahora profundicemos en teoría.",
                "Las aperturas en 'Riesgo' necesitan atención - ¡son oportunidades de mejora!",
            ]
        else:  # dominio
            mensajes = [
                f"¡Impresionante! {rating} ELO con {accuracy_media:.1f}% accuracy. ¡Eres un experto! 👑",
                "Tu dominio técnico es sobresaliente. Hora de perfeccionar los detalles.",
                "Mantén tus fortalezas y trabaja en las pocas debilidades restantes.",
            ]
        
        import random
        mensaje = random.choice(mensajes)
    
    avatar = avatares.get(nivel, "👨‍🏫")
    
    # Colores según nivel
    colores = {
        "sin_base": {"bg": "#fee2e2", "border": "#ef4444", "text": "#991b1b"},
        "desarrollo": {"bg": "#fef3c7", "border": "#f59e0b", "text": "#92400e"},
        "dominio": {"bg": "#d1fae5", "border": "#22c55e", "text": "#065f46"}
    }
    
    color = colores.get(nivel, colores["desarrollo"])
    
    html_code = f"""
    <style>
    @keyframes slideInRight {{
        from {{
            transform: translateX(100%);
            opacity: 0;
        }}
        to {{
            transform: translateX(0);
            opacity: 1;
        }}
    }}
    
    @keyframes bounce {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-10px); }}
    }}
    
    @keyframes pulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
    }}
    
    .profesor-container {{
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        animation: slideInRight 0.6s ease-out;
        max-width: 350px;
    }}
    
    .profesor-avatar {{
        font-size: 3.5rem;
        animation: bounce 2s ease-in-out infinite;
        display: inline-block;
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));
    }}
    
    .speech-bubble {{
        position: relative;
        background: {color['bg']};
        border: 2px solid {color['border']};
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: pulse 3s ease-in-out infinite;
    }}
    
    .speech-bubble::after {{
        content: '';
        position: absolute;
        bottom: -20px;
        right: 30px;
        width: 0;
        height: 0;
        border: 10px solid transparent;
        border-top-color: {color['border']};
    }}
    
    .speech-text {{
        color: {color['text']};
        font-size: 0.9rem;
        line-height: 1.5;
        font-weight: 500;
        margin: 0;
    }}
    
    .profesor-close {{
        position: absolute;
        top: 8px;
        right: 8px;
        background: transparent;
        border: none;
        font-size: 1.2rem;
        cursor: pointer;
        color: {color['text']};
        opacity: 0.6;
        transition: opacity 0.2s;
    }}
    
    .profesor-close:hover {{
        opacity: 1;
    }}
    
    .profesor-level-badge {{
        display: inline-block;
        background: {color['border']};
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }}
    </style>
    
    <div class="profesor-container" id="profesorContainer">
        <div class="speech-bubble">
            <button class="profesor-close" onclick="document.getElementById('profesorContainer').style.display='none'">×</button>
            <div class="profesor-level-badge">
                {'Principiante' if nivel == 'sin_base' else 'Intermedio' if nivel == 'desarrollo' else 'Experto'}
            </div>
            <p class="speech-text">{mensaje}</p>
        </div>
        <div style="text-align: right; padding-right: 30px;">
            <span class="profesor-avatar">{avatar}</span>
        </div>
    </div>
    
    <script>
    // Auto-cerrar después de 15 segundos
    setTimeout(() => {{
        const container = document.getElementById('profesorContainer');
        if (container) {{
            container.style.animation = 'slideInRight 0.4s ease-out reverse';
            setTimeout(() => container.style.display = 'none', 400);
        }}
    }}, 15000);
    </script>
    """
    
    st.components.v1.html(html_code, height=200, scrolling=False)


# ══════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import streamlit as st
    
    st.set_page_config(page_title="Demo Profesor Virtual", layout="wide")
    
    st.title("🎓 Demo: Profesor Virtual Animado")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nivel = st.selectbox("Nivel", ["sin_base", "desarrollo", "dominio"])
    with col2:
        rating = st.number_input("Rating", value=1500, step=50)
    with col3:
        accuracy = st.number_input("Accuracy", value=75.0, step=1.0)
    
    if st.button("Mostrar Profesor"):
        render_profesor_virtual(nivel, rating, accuracy)
    
    st.markdown("---")
    st.info("El profesor aparecerá en la esquina inferior derecha con un mensaje personalizado según tu nivel.")
