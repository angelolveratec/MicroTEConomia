"""
Módulo del Tutor Socrático de Microeconomía - Oferta, Demanda & Cía.
Configuración del sistema, llamadas a la API de Gemini y gestión de la sesión.
"""

import os
import time
from typing import Generator, List, Dict, Any, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from google.genai import errors

# Zona horaria oficial de la Ciudad de México
CDMX_TZ = ZoneInfo("America/Mexico_City")

def get_cdmx_now() -> datetime:
    """Retorna la fecha y hora actual en la zona horaria de la Ciudad de México (CDMX)."""
    return datetime.now(CDMX_TZ)

SYSTEM_INSTRUCTION = """
Rol: Eres un tutor socrático experto en Microeconomía Básica, especializado en el tema de Oferta y Demanda. Tu objetivo es guiar al estudiante mediante el análisis crítico, la conceptualización y la detección de errores.

Flujo de la Interacción
Fase 1: Identificación, Selección de Tema y Marca de Tiempo
Solicita al estudiante su número de matrícula o ID para comenzar.
En cuanto proporcione su ID, toma nota internamente de la hora de inicio de la sesión.
Pregúntale qué tema o tipo de ejercicio desea trabajar en esta sesión, dándole a elegir entre las siguientes opciones:
a) Oferta
b) Demanda
c) Equilibrio de mercado
d) Graficación
e) Resolver un ejercicio de equilibrio de mercado
Explícale brevemente que la sesión constará de un ciclo de 3 ejercicios consecutivos sobre el tema seleccionado para completar la actividad.

Fase 2: Ciclo de Ejercicios (Se repite exactamente 3 veces: Ejercicio 1, Ejercicio 2 y Ejercicio 3)
Para cada uno de los 3 ejercicios, sigue rigurosamente esta secuencia:

Paso A (Planteamiento del Ejercicio):
Presenta un problema práctico acorde al tema elegido.
Pide al estudiante que explique únicamente el proceso conceptual o metodológico que seguiría para resolverlo, sin realizar cálculos ni gráficas todavía.

Paso B (Retroalimentación de Método y Solución de la IA):
Analiza el proceso propuesto por el estudiante y dale una retroalimentación constructiva.
A continuación, presenta un procedimiento paso a paso para resolver el ejercicio. Decide aleatoriamente entre:
- Presentar un procedimiento completamente correcto.
- Presentar un procedimiento con un error conceptual, gráfico o matemático sutil (p. ej., confundir desplazamiento de la curva con movimiento a lo largo de la curva, un despeje erróneo, o una interpretación equivocada del precio/cantidad de equilibrio).
Pregunta al estudiante: "¿El procedimiento y resultado presentados son correctos? Explica por qué sí o por qué no y, si hay un error, indica exactamente en qué paso está."

Paso C (Guiado Socrático y Cierre del Ejercicio):
Evalúa la respuesta del estudiante:
- Si identifica correctamente el error (o valida con buenos argumentos que está correcto), felicítalo, refuerza el aprendizaje y pasa al siguiente ejercicio (o a la Fase 3 si ya es el tercer ejercicio).
- Si pasa por alto el error o inventa uno donde no lo hay, no le des la respuesta. Hazle preguntas guía para que reflexione sobre su argumento hasta que llegue a la conclusión correcta antes de avanzar.

Fase 3: Cierre y Registro de Sesión (Se activa solo tras concluir el Ejercicio 3)
Al finalizar con éxito el tercer ejercicio, felicita al estudiante por haber completado la serie.
Registra la hora de finalización y calcula el tiempo transcurrido (duración total de la sesión en minutos).
Muestra en pantalla el resumen formateado para sus registros con la siguiente estructura exacta:
=== REGISTRO DE ACTIVIDAD ===
ID Estudiante: [Número ingresado]
Tema trabajado: [Opción seleccionada por el alumno]
Ejercicios completados: 3 / 3
Tiempo de interacción: [X minutos / tiempo transcurrido]
Estado: Completado con éxito
Resumen del desempeño: [Breve nota sobre la precisión general del alumno en los 3 ejercicios al identificar métodos y errores]
=============================

Directrices pedagógicas adicionales:
- Mantén siempre un tono amable, motivador, académico y socrático.
- Utiliza notación matemática clara con formato Markdown / LaTeX (por ejemplo, $Q_d$, $Q_s$, $P^*$, $Q^*$, ecuaciones de equilibrio).
- Nunca te saltes un paso ni des la solución completa antes de que el estudiante reflexione sobre ella.
""".strip()

def get_gemini_client(api_key: Optional[str] = None):
    """
    Inicializa el cliente de Google GenAI usando google-genai.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("No se encontró la clave de API de Gemini (GEMINI_API_KEY).")
    
    from google import genai
    return genai.Client(api_key=key)

def get_available_models(api_key: Optional[str] = None) -> List[str]:
    """
    Obtiene la lista de modelos activos y compatibles para la clave proporcionada.
    Por defecto utiliza los modelos de la generación Gemini 3.
    """
    recommended = [
        "gemini-3.8-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.1-pro-preview",
        "gemini-3-flash",
    ]
    if not api_key:
        return recommended

    try:
        client = get_gemini_client(api_key)
        fetched = []
        for m in client.models.list():
            clean_name = m.name.replace("models/", "") if m.name else ""
            actions = getattr(m, "supported_actions", []) or []
            if ("generateContent" in actions or not actions) and "gemini" in clean_name.lower():
                # Descartar modelos legacy que generan 404 a proyectos nuevos
                if not any(legacy in clean_name for legacy in ["1.0", "1.5", "2.0", "2.5", "experimental", "vision", "cyber"]):
                    fetched.append(clean_name)
        if fetched:
            def sort_key(name):
                if "3.8-flash" in name: return 0
                if "3.1-flash-lite" in name: return 1
                if "3.1-pro" in name: return 2
                if "3-flash" in name: return 3
                return 4
            fetched.sort(key=sort_key)
            return fetched
    except Exception:
        pass
    return recommended

def test_api_connection(api_key: str, model_name: str = "gemini-3.8-flash") -> Dict[str, Any]:
    """
    Realiza una prueba de conectividad inmediata con la API de Gemini.
    """
    try:
        client = get_gemini_client(api_key)
        models_to_test = [model_name, "gemini-3.1-flash-lite", "gemini-3-flash", "gemini-3.1-pro-preview"]
        for m in models_to_test:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents="Responde únicamente: OK",
                )
                if response and response.text:
                    return {"success": True, "model": m, "message": f"Conectado exitosamente con {m}"}
            except Exception as e:
                err = str(e).lower()
                if "404" in err or "503" in err or "unavailable" in err:
                    continue
                else:
                    return {"success": False, "error": str(e)}
        return {"success": False, "error": "Los modelos probados no estuvieron disponibles temporalmente. Intenta nuevamente."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_tutor_stream(
    messages: List[Dict[str, str]],
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.8-flash",
    system_instruction: str = SYSTEM_INSTRUCTION
) -> Generator[str, None, None]:
    """
    Genera una respuesta en streaming para el chat del tutor socrático con:
    - Alternancia estricta de turnos (user -> model -> user).
    - Auto-reintento con pausa ante sobrecarga temporal (503 / UNAVAILABLE / 429).
    - Auto-fallback transparente a modelos alternativos de la familia Gemini 3 si uno está saturado o devuelve 404.
    - Respaldo de llamada estándar (non-streaming) si el stream falla.
    """
    client = get_gemini_client(api_key)
    from google.genai import types

    # Garantizar alternancia user/model empezando siempre en user
    formatted_messages = list(messages)
    if formatted_messages and formatted_messages[0]["role"] == "assistant":
        formatted_messages = [
            {"role": "user", "content": "Hola, inicio la sesión de tutoría de Microeconomía."}
        ] + formatted_messages

    contents = []
    for msg in formatted_messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )

    # Contexto temporal explícito en CDMX (UTC-6)
    cdmx_now = get_cdmx_now()
    time_context = (
        f"\n\n[CONTEXTO TEMPORAL DEL ENTORNO]\n"
        f"- Zona Horaria: Ciudad de México (CDMX, UTC-6).\n"
        f"- Fecha y hora actual en CDMX: {cdmx_now.strftime('%d/%m/%Y %H:%M:%S')}.\n"
        f"- Toda marca de tiempo (hora de inicio en Fase 1, hora de cierre en Fase 3 y cálculo de minutos transcurridos) "
        f"debe corresponder estrictamente a la hora oficial de la Ciudad de México (CDMX)."
    )
    effective_instruction = system_instruction + time_context

    config = types.GenerateContentConfig(
        system_instruction=effective_instruction,
        temperature=0.7,
        top_p=0.95,
    )

    # Construir lista de candidatos (modelo seleccionado + familia Gemini 3 de respaldo)
    candidate_models = [model_name]
    fallback_pool = [
        "gemini-3.8-flash",
        "gemini-3.1-flash-lite",
        "gemini-3-flash",
        "gemini-3.1-pro-preview"
    ]
    for m in fallback_pool:
        if m not in candidate_models:
            candidate_models.append(m)

    last_exception = None

    for candidate in candidate_models:
        for attempt in range(2):
            try:
                response_stream = client.models.generate_content_stream(
                    model=candidate,
                    contents=contents,
                    config=config,
                )
                stream_started = False
                for chunk in response_stream:
                    if chunk.text:
                        stream_started = True
                        yield chunk.text
                if stream_started:
                    return
            except Exception as e:
                err_msg = str(e).lower()
                last_exception = e
                # 503 UNAVAILABLE o 429 RESOURCE_EXHAUSTED (picos de tráfico de Google)
                is_overload = "503" in err_msg or "unavailable" in err_msg or "high demand" in err_msg or "429" in err_msg or "resource_exhausted" in err_msg
                # 404 NOT_FOUND (modelo deprecado o no disponible en este tier)
                is_not_found = "404" in err_msg or "not_found" in err_msg or "no longer available" in err_msg

                if is_overload:
                    if attempt == 0:
                        time.sleep(2.0)
                        continue
                    else:
                        break  # Pasar al siguiente modelo de respaldo
                elif is_not_found:
                    break  # Pasar inmediatamente al siguiente modelo
                else:
                    # Errores no recuperables por cambio de modelo (ej. 403 clave inválida o API deshabilitada)
                    raise e

    # Respaldo final: intentar llamada síncrona simple si el streaming fue bloqueado
    for candidate in candidate_models[:2]:
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=contents,
                config=config,
            )
            if response and response.text:
                yield response.text
                return
        except Exception:
            pass

    if last_exception:
        raise last_exception
