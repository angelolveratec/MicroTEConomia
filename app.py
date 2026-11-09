import streamlit as st
import datetime
import os
import re
from dotenv import load_dotenv
from gemini_tutor import (
    generate_tutor_stream,
    SYSTEM_INSTRUCTION,
    get_available_models,
    test_api_connection,
    get_cdmx_now
)

# Cargar variables de entorno si existen (.env)
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Oferta, Demanda & Cía. - Tutor Socrático",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos visuales personalizados
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .badge-role {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
    }
    .activity-summary-box {
        background-color: #F0FDF4;
        border: 2px solid #22C55E;
        border-radius: 8px;
        padding: 15px;
        font-family: monospace;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# Inicialización del estado de sesión
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "¡Hola! 👋 Te doy la bienvenida a **Oferta, Demanda & Cía.**, tu tutor socrático "
                "de Microeconomía Básica.\n\n"
                "Para iniciar nuestra sesión de trabajo, por favor **indica tu número de matrícula o ID de estudiante**."
            )
        }
    ]

if "start_time" not in st.session_state:
    st.session_state.start_time = None

if "student_id" not in st.session_state:
    st.session_state.student_id = None

if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = None

if "completed" not in st.session_state:
    st.session_state.completed = False

if "final_summary" not in st.session_state:
    st.session_state.final_summary = ""

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    # Manejo de API Key
    default_api_key = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=default_api_key,
        type="password",
        placeholder="AIzaSy...",
        help="Obtén tu API Key gratuita en https://aistudio.google.com/"
    )
    
    api_key_clean = api_key_input.strip() if api_key_input else None

    if api_key_clean:
        col_status, col_test = st.columns([0.5, 0.5])
        with col_status:
            st.caption("🟢 API Key lista")
        with col_test:
            if st.button("⚡ Probar Conexión", use_container_width=True):
                with st.spinner("Comprobando..."):
                    res = test_api_connection(api_key_clean)
                    if res.get("success"):
                        st.success(f"✅ {res.get('message')}")
                    else:
                        st.error(f"❌ {res.get('error')}")
    else:
        st.warning("⚠️ Ingresa tu API Key de Gemini para comenzar.")
        st.markdown("[👉 Obtener API Key gratis en Google AI Studio](https://aistudio.google.com/)")

    available_models = get_available_models(api_key_clean)
    default_idx = 0
    if "gemini-3.1-flash-lite" in available_models:
        default_idx = available_models.index("gemini-3.1-flash-lite")

    model_option = st.selectbox(
        "Modelo de Gemini",
        options=available_models,
        index=default_idx,
        help="gemini-3.1-flash-lite es el modelo predeterminado: ultra rápido, eficiente y con alta disponibilidad."
    )

    st.divider()

    # Panel de Estado de la Sesión
    st.markdown("### 📊 Estado de la Sesión")
    
    # Hora actual en la Ciudad de México
    current_cdmx = get_cdmx_now()
    st.caption(f"🕒 **Hora CDMX:** {current_cdmx.strftime('%H:%M:%S')}")

    # Mostrar ID de estudiante y tema
    if st.session_state.student_id:
        st.markdown(f"**Matrícula:** `{st.session_state.student_id}`")
    else:
        st.info("Esperando ingreso de matrícula...")

    if st.session_state.selected_topic:
        st.markdown(f"**Tema:** `{st.session_state.selected_topic}`")

    # Cronómetro de sesión en hora CDMX
    if st.session_state.start_time:
        elapsed = get_cdmx_now() - st.session_state.start_time
        mins, secs = divmod(int(elapsed.total_seconds()), 60)
        st.metric(label="⏱️ Tiempo transcurrido", value=f"{mins}m {secs}s")
        st.caption(f"Inicio: {st.session_state.start_time.strftime('%H:%M:%S')} (CDMX)")
    else:
        st.metric(label="⏱️ Tiempo transcurrido", value="0m 0s")

    # Progreso de la actividad
    st.markdown("**Ciclo de Ejercicios:**")
    assistant_text = " ".join([m["content"] for m in st.session_state.messages if m["role"] == "assistant"])
    ex_count = 0
    if "Ejercicio 1" in assistant_text:
        ex_count = 1
    if "Ejercicio 2" in assistant_text:
        ex_count = 2
    if "Ejercicio 3" in assistant_text:
        ex_count = 3
    if "=== REGISTRO DE ACTIVIDAD ===" in assistant_text:
        ex_count = 3
        st.session_state.completed = True

    st.progress(ex_count / 3.0, text=f"{ex_count}/3 ejercicios avanzados")

    st.divider()

    # Fórmulas de Microeconomía
    with st.expander("📘 Formulario de Apoyo"):
        st.markdown("""
        **Función de Demanda:**
        $$Q_d = a - bP$$
        *(Relación inversa entre precio y cantidad demandada)*

        **Función de Oferta:**
        $$Q_s = c + dP$$
        *(Relación directa entre precio y cantidad ofrecida)*

        **Condición de Equilibrio:**
        $$Q_d = Q_s \\implies P^* = \\frac{a - c}{b + d}$$
        $$Q^* = a - b(P^*)$$

        **Concepto Clave:**
        - **Movimiento a lo largo de la curva:** Provocado *únicamente* por cambios en el precio del bien ($P$).
        - **Desplazamiento de la curva:** Provocado por variables externas (tecnología, costos, ingresos, preferencias, clima).
        """)

    st.divider()

    # Botón de reinicio
    col_reset, col_down = st.columns(2)
    with col_reset:
        if st.button("🔄 Reiniciar", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": (
                        "¡Hola! 👋 Te doy la bienvenida a **Oferta, Demanda & Cía.**, tu tutor socrático "
                        "de Microeconomía Básica.\n\n"
                        "Para iniciar nuestra sesión de trabajo, por favor **indica tu número de matrícula o ID de estudiante**."
                    )
                }
            ]
            st.session_state.start_time = None
            st.session_state.student_id = None
            st.session_state.selected_topic = None
            st.session_state.completed = False
            st.session_state.final_summary = ""
            st.rerun()

    # Si la sesión terminó, permitir descargar el comprobante
    if st.session_state.completed and st.session_state.final_summary:
        with col_down:
            st.download_button(
                label="📥 Registro",
                data=st.session_state.final_summary,
                file_name=f"registro_microeconomia_{st.session_state.student_id or 'estudiante'}.txt",
                mime="text/plain",
                use_container_width=True
            )

# ================= ÁREA PRINCIPAL =================
col_head1, col_head2 = st.columns([0.8, 0.2])
with col_head1:
    st.markdown('<div class="main-title">📈 Oferta, Demanda & Cía.</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Tutor Socrático de Microeconomía Básica • Análisis Crítico, Métodos y Detección de Errores</div>', unsafe_allow_html=True)
with col_head2:
    st.markdown('<span class="badge-role">🏛️ Modo Socrático</span>', unsafe_allow_html=True)

# Renderizar historial de mensajes
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        with st.chat_message("assistant", avatar="🏛️"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(msg["content"])

# Si ya se concluyó la actividad, mostrar tarjeta de felicitación
if st.session_state.completed:
    st.success("🎉 ¡Excelente trabajo! Has completado con éxito la serie de 3 ejercicios. Puedes copiar tu comprobante arriba o descargarlo desde la barra lateral.")

# Entrada del usuario
prompt = st.chat_input("Escribe tu respuesta, explicación conceptual o consulta aquí...")

if prompt:
    # Si aún no tenemos matrícula y es el primer mensaje de respuesta del usuario
    if not st.session_state.student_id:
        st.session_state.student_id = prompt.strip()
        if not st.session_state.start_time:
            st.session_state.start_time = get_cdmx_now()
    elif not st.session_state.selected_topic:
        lower_p = prompt.strip().lower()
        topic_map = {
            "a": "Oferta",
            "b": "Demanda",
            "c": "Equilibrio de mercado",
            "d": "Graficación",
            "e": "Resolver ejercicio de equilibrio"
        }
        for key, val in topic_map.items():
            if lower_p == key or lower_p.startswith(key + ")") or lower_p.startswith(key + " ") or val.lower() in lower_p:
                st.session_state.selected_topic = val
                break

    # Mostrar mensaje del usuario inmediatamente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(prompt)

    # Validar API Key
    api_key_to_use = api_key_input.strip() if api_key_input else None
    if not api_key_to_use:
        with st.chat_message("assistant", avatar="🏛️"):
            st.error("⚠️ Por favor ingresa una API Key de Gemini en la barra lateral izquierda para continuar con la tutoría.")
    else:
        # Generar respuesta del tutor socrático con streaming
        with st.chat_message("assistant", avatar="🏛️"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                # Iniciar streaming
                stream = generate_tutor_stream(
                    messages=st.session_state.messages,
                    api_key=api_key_to_use,
                    model_name=model_option,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                for chunk in stream:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
                # Guardar respuesta en el historial
                st.session_state.messages.append({"role": "assistant", "content": full_response})

                # Verificar si se emitió el registro final de actividad
                if "=== REGISTRO DE ACTIVIDAD ===" in full_response:
                    st.session_state.completed = True
                    match = re.search(r"=== REGISTRO DE ACTIVIDAD ===[\s\S]*?=============================", full_response)
                    if match:
                        st.session_state.final_summary = match.group(0)
                    else:
                        st.session_state.final_summary = full_response
                    st.rerun()

            except Exception as e:
                err_text = str(e)
                if "403" in err_text and ("SERVICE_DISABLED" in err_text or "PERMISSION_DENIED" in err_text):
                    message_placeholder.error(
                        "❌ **Permiso denegado (403):** La API de Gemini no está habilitada en tu proyecto de Google Cloud.\n\n"
                        "👉 [Haz clic aquí para habilitar la API de Gemini en tu proyecto](https://console.developers.google.com/apis/api/generativelanguage.googleapis.com/overview)"
                    )
                elif "503" in err_text or "UNAVAILABLE" in err_text or "high demand" in err_text.lower():
                    message_placeholder.warning(
                        "⚠️ **Pico de alta demanda temporal en Google (503):**\n\n"
                        "Los servidores de ese modelo están temporalmente ocupados. Selecciona **gemini-3.1-flash-lite** en la barra lateral y vuelve a enviar tu mensaje."
                    )
                elif "404" in err_text or "NOT_FOUND" in err_text:
                    message_placeholder.error(
                        "❌ **Modelo no disponible (404):** Por favor selecciona **gemini-3.8-flash** o **gemini-3.1-flash-lite** en el menú desplegable de la barra lateral."
                    )
                else:
                    message_placeholder.error(f"❌ Ocurrió un error al contactar al tutor: {err_text}")
