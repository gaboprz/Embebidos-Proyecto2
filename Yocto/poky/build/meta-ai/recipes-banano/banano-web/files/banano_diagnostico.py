#!/usr/bin/env python3
"""
Banano Diagnóstico — Backend FastAPI
Clasificación visual: MobileNetV2 + ONNX Runtime  → puerto 8080
Explicación natural:  phi3:mini / gemma2:2b via llama-server  → puerto 8081 (interno)

Este archivo es el servidor web central del sistema. Recibe peticiones del
navegador del usuario, coordina los dos motores de IA (visión y lenguaje),
y devuelve el diagnóstico completo.
"""

# ── Importaciones ─────────────────────────────────────────────────────────────
# FastAPI: framework web moderno para Python. Maneja rutas, tipos de datos
# y documentación automática. Es async (no bloqueante), lo que permite
# atender múltiples peticiones sin que una bloquee a las otras.
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse  # Para servir el HTML del frontend
from pathlib import Path                    # Manejo de rutas de archivos

# subprocess: ejecuta inference.py como un proceso externo separado.
# Se usa en lugar de importar inference.py directamente para evitar
# conflictos entre el event loop de FastAPI y ONNX Runtime.
import subprocess

# tempfile: crea archivos temporales. La imagen del usuario se guarda
# en disco brevemente para que inference.py pueda leerla.
import tempfile

# asyncio: biblioteca de Python para programación asíncrona.
# Permite ejecutar tareas que tardan mucho (como esperar al LLM)
# sin bloquear el servidor para otras peticiones.
import asyncio

import json                        # Leer/escribir datos en formato JSON
import os                          # Borrar archivos temporales del disco
import urllib.request as urlreq    # Cliente HTTP simple para llamar al LLM.
                                   # Se usa en lugar de httpx porque httpx async
                                   # falla en el entorno de red de Yocto.

# ── Instancia de la aplicación web ───────────────────────────────────────────
# Crea el servidor FastAPI. El parámetro title aparece en la
# documentación automática accesible en /docs.
app = FastAPI(title="Banano AI — Diagnóstico de Enfermedades")


# ── Constantes de configuración ───────────────────────────────────────────────
# Rutas fijas de los componentes del sistema en la Jetson.
INFERENCE_SCRIPT = "/opt/vision/bin/inference.py"   # Clasificador visual
VISION_MODEL     = "/opt/vision/models/banana_disease_classifier.onnx"  # Modelo entrenado
STATIC_DIR       = "/opt/banano-web/static"         # Carpeta del frontend HTML

# llama-server escucha solo en localhost (127.0.0.1), no es accesible
# desde fuera de la Jetson. Esto es intencional por seguridad.
LLM_URL = "http://127.0.0.1:8081"

# Si la red neuronal tiene menos de 60% de confianza en su respuesta,
# la imagen probablemente no es una hoja de banano o está muy borrosa.
CONFIDENCE_THRESHOLD = 0.60

# Límite de tokens que puede generar el LLM en su respuesta.
# phi3:mini genera ~3 tokens/segundo en esta Jetson.
# 600 tokens ≈ 3-4 minutos de generación.
LLM_MAX_TOKENS = 600

# Tiempo máximo de espera para la respuesta del LLM, en segundos.
# 480 = 8 minutos. Se necesita tanto porque el prompt es largo
# y el modelo es lento en esta GPU de 128 núcleos.
LLM_TIMEOUT = 480


# ── Contexto técnico de cada enfermedad ───────────────────────────────────────
# Este diccionario se inyecta en el prompt del LLM cuando se detecta
# una enfermedad. Le da información de fondo al modelo para que
# su respuesta sea más precisa sin necesitar "recordarlo" por sí solo.
DISEASE_CONTEXT = {
    "Black Sigatoka": (
        "Sigatoka Negra causada por el hongo Mycosphaerella fijiensis. "
        "La más destructiva en plantaciones de banano a nivel mundial."
    ),
    "Yellow Sigatoka": (
        "Sigatoka Amarilla causada por Mycosphaerella musicola. "
        "Menos agresiva que la negra pero causa pérdidas importantes."
    ),
    "Panama Disease": (
        "Mal de Panamá causado por Fusarium oxysporum cubense. "
        "Enfermedad del suelo sin cura que puede devastar plantaciones enteras."
    ),
    "Healthy": "planta sin signos visibles de enfermedad",
}


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 1 — INFERENCIA VISUAL (ONNX)
# ═════════════════════════════════════════════════════════════════════════════

def run_vision_inference(image_bytes: bytes) -> dict:
    """
    Clasifica una imagen usando MobileNetV2 + ONNX Runtime.

    Recibe los bytes crudos de la imagen (como llegaron del navegador),
    los pasa al clasificador y devuelve la enfermedad detectada.

    Retorna un diccionario con:
        disease    (str):   nombre de la enfermedad o "Healthy"
        confidence (float): nivel de certeza de 0.0 a 1.0
        all_scores (dict):  probabilidad de cada una de las 4 clases
    """

    # La imagen llega como bytes en memoria. inference.py necesita leerla
    # desde el disco, así que se guarda en un archivo temporal.
    # delete=False: no borrar automáticamente al cerrar, se borra al final.
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)   # Escribir los bytes de la imagen en el archivo
        tmp_path = tmp.name      # Guardar la ruta para usarla luego

    try:
        # Ejecutar inference.py como un proceso separado de Python.
        # Por qué proceso separado y no import directo?
        # ONNX Runtime en Python 3.8 tiene incompatibilidades al cargarse
        # dentro del event loop async de FastAPI. El proceso separado
        # corre de forma aislada y evita esos conflictos.
        result = subprocess.run(
            ["python3", INFERENCE_SCRIPT, tmp_path, "--model", VISION_MODEL],
            capture_output=True,  # Capturar stdout y stderr en variables
            text=True,            # Decodificar bytes como texto UTF-8
            timeout=30            # Si tarda más de 30 segundos, cancelar
        )

        # Si inference.py terminó con error (código de salida != 0),
        # lanzar una excepción con el mensaje de error.
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Error en inferencia ONNX")

        # inference.py imprime el resultado en JSON a stdout.
        # json.loads lo convierte al diccionario Python.
        # Ejemplo: {"disease": "Black Sigatoka", "confidence": 0.923, "all_scores": {...}}
        return json.loads(result.stdout.strip())

    finally:
        # Borrar el archivo temporal siempre, incluso si hubo un error.
        # "finally" se ejecuta sin importar qué ocurrió en el "try".
        os.unlink(tmp_path)


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 2 — CONSTRUCCIÓN DEL PROMPT PARA EL LLM
# ═════════════════════════════════════════════════════════════════════════════

def build_llm_prompt(disease: str, confidence: float, user_text: str = None) -> str:
    """
    Construye el mensaje de texto que se envía al LLM para que genere
    su análisis. El mensaje varía según qué información está disponible.

    Hay 4 escenarios posibles:
      A. Solo texto del agricultor (sin imagen)
      B. Imagen con confianza baja (imagen poco clara o no es banano)
      C. Planta sana confirmada por la imagen
      D. Enfermedad detectada (con o sin texto adicional)
    """

    # Instrucción que se añade al final de todos los prompts.
    # Los LLMs tienden a usar Markdown (asteriscos para negrita, # para títulos)
    # aunque no se les pida. En HTML esos caracteres se ven literalmente.
    # Esta instrucción reduce ese comportamiento, aunque no lo elimina del todo.
    # Por eso también existe strip_markdown() que limpia la respuesta.
    no_markdown = (
        "IMPORTANTE: responde SOLO en texto plano. "
        "No uses asteriscos, guiones para negritas, ni formato Markdown. "
        "Usa mayúsculas para los títulos de sección."
    )

    # ── ESCENARIO A: Solo texto, sin imagen ───────────────────────────────────
    # Se activa cuando no se envió imagen (disease queda como "Indeterminado")
    # pero sí llegó texto escrito por el agricultor.
    if disease == "Indeterminado" and user_text:
        # El prompt restringe al LLM a elegir SOLO entre las 4 clases que
        # conoce el modelo visual. Esto mantiene consistencia entre ambos
        # modos de diagnóstico. Si el texto no da suficiente información,
        # el LLM debe decirlo explícitamente en lugar de inventar un diagnóstico.
        return (
            f"Eres un agrónomo experto en cultivos de banano de Costa Rica. "
            f"Un agricultor describe lo siguiente sobre su planta:\n"
            f"\"{user_text}\"\n\n"
            f"Basándote ÚNICAMENTE en esta descripción, determina cuál de las siguientes "
            f"opciones aplica para esta planta. No puedes sugerir ninguna otra enfermedad "
            f"fuera de estas cuatro opciones:\n"
            f"1. Sigatoka Negra\n"
            f"2. Sigatoka Amarilla\n"
            f"3. Mal de Panama (Fusarium)\n"
            f"4. Planta Sana\n\n"
            f"Si la descripción no menciona síntomas claros o no tiene suficiente información "
            f"para distinguir entre estas opciones, responde que la información suministrada "
            f"no es suficiente para realizar un diagnóstico y explica qué síntomas específicos "
            f"necesitarías para poder diagnosticar.\n\n"
            f"Si sí hay suficiente información, responde con estas secciones:\n\n"
            f"DIAGNOSTICO: indica cuál de las 4 opciones aplica y por qué.\n\n"
            f"SINTOMAS IDENTIFICADOS: enumera los síntomas de la descripción que "
            f"llevaron a ese diagnóstico.\n\n"
            f"RECOMENDACIONES: 3 pasos concretos a seguir, incluyendo si debe "
            f"confirmar el diagnóstico enviando una foto al sistema.\n\n"
            f"NIVEL DE URGENCIA: si requiere acción inmediata o puede esperar.\n\n"
            f"{no_markdown}"
        )

    # ── ESCENARIO B: Imagen con confianza baja ────────────────────────────────
    # Se activa cuando la red neuronal devuelve una confianza menor al 60%.
    # Esto ocurre cuando la imagen no es una hoja de banano, está muy borrosa,
    # tiene mala iluminación, o el ángulo no es el adecuado.
    if confidence < CONFIDENCE_THRESHOLD:
        # Construir el mensaje base explicando el problema de la imagen.
        base = (
            f"Eres un experto agrícola en banano de Costa Rica. "
            f"Un sistema de visión artificial analizó una imagen con confianza muy baja "
            f"({confidence:.0%}), lo que indica que posiblemente no es una hoja de banano "
            f"o la imagen no es suficientemente clara para diagnosticar. "
        )
        if user_text:
            # Si el agricultor también escribió texto, usarlo para orientar
            # la respuesta aunque la imagen no sirva.
            base += (
                f"Sin embargo, el agricultor también describe: \"{user_text}\". "
                f"Usa esta descripción para orientar al agricultor sobre posibles problemas "
                f"y recomiéndale tomar una foto más clara para confirmar. "
            )
        else:
            # Si solo había imagen (sin texto), dar instrucciones para mejorarla.
            base += (
                f"Explica esto al agricultor en 3 oraciones y dale instrucciones concretas "
                f"sobre cómo tomar una buena foto de la hoja: distancia, iluminación y ángulo. "
            )
        base += f"Responde en español. {no_markdown}"
        return base

    # ── ESCENARIO C: Planta sana ──────────────────────────────────────────────
    # Se activa cuando ONNX clasificó la imagen como "Healthy" con suficiente
    # confianza. El LLM confirma y da recomendaciones preventivas.
    if disease == "Healthy":
        base = (
            f"Eres un experto agrícola en banano de Costa Rica. "
            f"Un sistema de visión artificial confirmó que la planta está SANA "
            f"con {confidence:.0%} de confianza. "
        )
        if user_text:
            # Si el agricultor describió algo, considerarlo por si hay
            # síntomas que el modelo visual no captó claramente.
            base += (
                f"Adicionalmente, el agricultor describe: \"{user_text}\". "
                f"Considera esta información en tu respuesta. "
            )
        base += (
            f"Proporciona: confirmación del estado de la planta, "
            f"un programa de monitoreo preventivo mensual, "
            f"3 buenas prácticas de manejo para mantenerla sana, "
            f"y señales tempranas a vigilar. "
            f"Responde en español. {no_markdown}"
        )
        return base

    # ── ESCENARIO D: Enfermedad detectada ─────────────────────────────────────
    # Caso principal. ONNX detectó una de las 3 enfermedades con confianza
    # suficiente. El LLM genera un informe completo con 6 secciones.
    # Este escenario cubre tanto el Caso 1 (solo imagen) como el Caso 3
    # (imagen + texto), diferenciados por si user_text tiene contenido.

    # Recuperar el contexto técnico de la enfermedad detectada.
    # Esto le da al LLM información de fondo sin que tenga que "recordarla".
    context = DISEASE_CONTEXT.get(disease, disease)

    base = (
        f"Eres un experto agrícola en banano de Costa Rica. "
        f"Un sistema de visión artificial detectó {disease} con {confidence:.0%} "
        f"de confianza en una hoja de banano. Contexto: {context} "
    )

    if user_text:
        # Caso 3: agregar la descripción del agricultor al prompt.
        # El LLM puede usar el texto para confirmar o matizar el diagnóstico visual.
        base += (
            f"\n\nAdicionalmente, el agricultor describe: \"{user_text}\". "
            f"Considera tanto el diagnóstico visual como esta descripción para un "
            f"análisis más completo y preciso. "
        )

    # Solicitar el informe estructurado con secciones fijas.
    # Las secciones en MAYÚSCULAS son detectadas por strip_markdown()
    # para agregar saltos de línea y mejorar la presentación.
    base += (
        f"Proporciona un informe completo en español con estas secciones:\n\n"
        f"DESCRIPCION DE LA ENFERMEDAD: qué es, cómo se propaga y en qué condiciones "
        f"se desarrolla en plantaciones costarricenses.\n\n"
        f"SINTOMAS VISIBLES: 4 síntomas específicos que el agricultor puede observar.\n\n"
        f"NIVEL DE URGENCIA: si requiere acción inmediata, en días, o puede esperar.\n\n"
        f"TRATAMIENTO: 4 pasos concretos con productos disponibles en Costa Rica.\n\n"
        f"PREVENCION: 3 medidas para evitar propagación y reaparición.\n\n"
        f"IMPACTO ECONOMICO: impacto potencial si no se trata a tiempo.\n\n"
        f"{no_markdown}"
    )
    return base


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 3 — LIMPIEZA DE LA RESPUESTA DEL LLM
# ═════════════════════════════════════════════════════════════════════════════

def strip_markdown(text: str) -> str:
    """
    Limpia el texto generado por el LLM para que se vea bien en el navegador.

    Problema: los modelos de lenguaje formatean sus respuestas con Markdown
    (**negrita**, _itálica_, # Título) aunque se les pida que no lo hagan.
    En HTML, esos caracteres se ven literalmente en pantalla.

    Esta función hace dos cosas:
    1. Elimina los caracteres de formato Markdown
    2. Agrega saltos de línea reales antes de cada sección
    """
    import re

    # ── Eliminar formato Markdown ─────────────────────────────────────────────
    # Cada re.sub busca un patrón y lo reemplaza.
    # r'\1' significa "dejar solo el grupo capturado entre paréntesis".

    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **texto** → texto (negrita)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)  # *texto*   → texto (itálica)
    text = re.sub(r'__(.+?)__',     r'\1', text)  # __texto__ → texto (negrita alt)
    text = re.sub(r'_(.+?)_',       r'\1', text)  # _texto_   → texto (itálica alt)
    text = re.sub(r'^#{1,6}\s+',    '',    text,   # # Título  → Título
                  flags=re.MULTILINE)              # MULTILINE: aplica a cada línea
    text = re.sub(r'`(.+?)`',       r'\1', text)  # `código`  → código

    # ── Agregar saltos de línea antes de secciones en MAYÚSCULAS ─────────────
    # El LLM responde con títulos como "TRATAMIENTO: ..." todo seguido.
    # Esta expresión busca palabras en mayúsculas seguidas de dos puntos
    # y les agrega \n\n adelante para que aparezcan como párrafos separados.
    # Ejemplo: "TRATAMIENTO: 1. Paso" → "\n\nTRATAMIENTO:\n1. Paso"
    # [A-ZÁÉÍÓÚÑ]{3,}: al menos 3 letras mayúsculas (con tildes y ñ).
    text = re.sub(r'\s{0,2}([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,}:)', r'\n\n\1', text)

    # ── Agregar salto antes de ítems numerados ────────────────────────────────
    # Convierte "texto 1. Primer paso 2. Segundo paso" en líneas separadas.
    # \d+\.: uno o más dígitos seguidos de un punto (1. 2. 3. etc.)
    text = re.sub(r'\s+(\d+\.)\s', r'\n\1 ', text)

    # Eliminar espacios y saltos de línea sobrantes al inicio y al final.
    return text.strip()


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 4 — COMUNICACIÓN CON EL LLM
# ═════════════════════════════════════════════════════════════════════════════

def _call_llm_sync(prompt: str):
    """
    Envía el prompt a llama-server y devuelve la respuesta del LLM.

    Esta función es SINCRÓNICA (bloquea hasta recibir la respuesta).
    Puede tardar entre 3 y 8 minutos dependiendo del modelo y el prompt.

    Se usa urllib.request (librería estándar de Python) en lugar de httpx
    porque httpx async tiene un bug con la configuración de red de Yocto
    que hace fallar todas las conexiones TCP.
    """

    # Construir el cuerpo de la petición en formato JSON.
    # Este es el formato estándar de la API de OpenAI, que llama-server imita.
    payload = json.dumps({
        "model":       "gemma2",       # llama-server ignora este campo y usa
                                       # el modelo que se cargó al arrancar.
        "messages":    [{"role": "user", "content": prompt}],
                                       # El historial de conversación. Aquí
                                       # siempre es solo un mensaje del usuario.
        "max_tokens":  LLM_MAX_TOKENS, # Límite de tokens en la respuesta (600).
        "temperature": 0.3,            # Qué tan "creativo" es el modelo.
                                       # 0.0 = siempre la misma respuesta.
                                       # 1.0 = muy variado y creativo.
                                       # 0.3 = consistente pero con variación leve.
        "stream":      False           # Esperar la respuesta completa de una vez,
                                       # no recibirla token por token.
    }).encode()                        # Convertir el string JSON a bytes

    # Crear la petición HTTP POST al endpoint de completions de llama-server.
    req = urlreq.Request(
        f"{LLM_URL}/v1/chat/completions",       # URL del endpoint
        data=payload,                            # Cuerpo de la petición
        headers={"Content-Type": "application/json"}  # Tipo de contenido
    )

    try:
        # Enviar la petición y esperar la respuesta.
        # timeout=LLM_TIMEOUT: si no responde en 480 segundos, lanzar error.
        with urlreq.urlopen(req, timeout=LLM_TIMEOUT) as r:
            data = json.loads(r.read())  # Leer y parsear la respuesta JSON
            # Navegar la estructura de la respuesta para llegar al texto generado.
            # data["choices"][0]: primera (y única) opción de respuesta
            # ["message"]["content"]: el texto generado por el LLM
            raw_text = data["choices"][0]["message"]["content"]
            return strip_markdown(raw_text)  # Limpiar antes de devolver
    except Exception as e:
        # Si algo falla (timeout, LLM caído, error de red), registrar en
        # la consola del servidor y devolver None.
        # El endpoint /diagnose mostrará el mensaje de fallback al usuario.
        print(f"[LLM ERROR] {type(e).__name__}: {e}")
        return None


async def call_llm(prompt: str):
    """
    Versión async de la llamada al LLM para no bloquear el servidor web.

    Problema: FastAPI es async. Si llamamos a _call_llm_sync() directamente
    desde un endpoint async, el servidor queda bloqueado durante 3-8 minutos
    y no puede atender ninguna otra petición mientras espera al LLM.

    Solución: run_in_executor() ejecuta la función síncrona en un hilo
    (thread) separado del sistema operativo. FastAPI puede seguir atendiendo
    otras peticiones mientras ese hilo espera la respuesta del LLM.

    asyncio.get_event_loop(): obtiene el gestor de eventos async actual.
    run_in_executor(None, func, arg): ejecuta func(arg) en un hilo separado
    y devuelve su resultado cuando termina. None = usar el pool por defecto.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_llm_sync, prompt)


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 5 — ENDPOINTS (RUTAS DEL SERVIDOR WEB)
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/diagnose")
async def diagnose(
    image: UploadFile = File(None),  # Archivo de imagen (opcional)
    text:  str        = Form(None)   # Texto descriptivo (opcional)
):
    """
    Endpoint principal. Recibe imagen, texto o ambos, y devuelve el diagnóstico.

    Es el punto de entrada de todas las peticiones de diagnóstico desde
    el navegador. Coordina el clasificador visual y el modelo de lenguaje.
    """

    # Validar que llegó al menos uno de los dos: imagen o texto.
    # Si no hay ninguno, devolver error HTTP 400 (Bad Request).
    if not image and not text:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos una imagen o descripción"
        )

    # Inicializar variables con valores por defecto.
    # Si no llega imagen, estos valores se quedan como están.
    disease    = "Indeterminado"  # Clase detectada por ONNX
    confidence = 0.0              # Certeza de la clasificación (0.0 a 1.0)
    all_scores = {}               # Probabilidad de cada una de las 4 clases

    # Limpiar el texto: eliminar espacios al inicio/final.
    # Si solo hay espacios vacíos, tratar como None (no hay texto real).
    user_text = text.strip() if text and text.strip() else None

    # ── Paso 1: Clasificación visual (solo si hay imagen) ─────────────────────
    if image:
        # Leer los bytes de la imagen desde la petición HTTP.
        # "await" pausa aquí hasta que los bytes estén disponibles,
        # sin bloquear otras peticiones.
        image_bytes = await image.read()
        try:
            vision_result = run_vision_inference(image_bytes)
        except Exception as e:
            # Si el clasificador falla, devolver error HTTP 500 (Server Error).
            raise HTTPException(
                status_code=500,
                detail=f"Error en clasificación visual: {str(e)}"
            )
        # Extraer los valores del diccionario devuelto por inference.py.
        # .get(key, default): si la clave no existe, usar el valor por defecto.
        disease    = vision_result.get("disease",    "Indeterminado")
        confidence = vision_result.get("confidence", 0.0)
        all_scores = vision_result.get("all_scores", {})

    # ── Paso 2: Análisis del LLM (si hay algo que analizar) ───────────────────
    recomendacion = None
    # Llamar al LLM si:
    # - Se detectó una enfermedad o planta sana (disease != "Indeterminado"), O
    # - El agricultor escribió una descripción (user_text tiene contenido)
    if disease != "Indeterminado" or user_text:
        prompt        = build_llm_prompt(disease, confidence, user_text)
        recomendacion = await call_llm(prompt)  # Espera 3-8 minutos

    # ── Paso 3: Determinar la modalidad de la petición ────────────────────────
    # La modalidad se incluye en la respuesta para que el frontend
    # pueda mostrar información contextual al usuario.
    if image and user_text:
        modalidad = "multimodal"   # Llegaron imagen Y texto
    elif user_text:
        modalidad = "textual"      # Solo llegó texto
    else:
        modalidad = "visual"       # Solo llegó imagen

    # ── Paso 4: Construir y devolver la respuesta JSON ────────────────────────
    return {
        # Si hubo imagen, mostrar la enfermedad detectada.
        # Si solo hubo texto, indicar que es un análisis descriptivo.
        "enfermedad":    disease if image else "Análisis por descripción",

        # Confianza numérica: solo aplica cuando hubo imagen.
        # None en JSON se convierte a null, que el frontend interpreta
        # como "no mostrar confianza".
        "confianza":     round(confidence, 4) if image else None,

        # Indica si la imagen tuvo suficiente calidad para el diagnóstico.
        # True si confidence >= 0.60, False si es menor.
        "imagen_valida": (confidence >= CONFIDENCE_THRESHOLD) if image else None,

        # Probabilidades de todas las clases. Útil para mostrar
        # al usuario qué tan seguro estuvo el modelo.
        "all_scores":    all_scores,

        # Análisis del LLM. Si el LLM no está disponible, mensaje de fallback.
        "recomendacion": recomendacion or "Servicio LLM no disponible — inicie llama-server.",

        # Indica si el LLM respondió correctamente (True) o falló (False).
        # Permite al frontend saber si el análisis textual es real.
        "llm_activo":    recomendacion is not None,

        "modalidad":     modalidad
    }


@app.get("/health")
async def health():
    """
    Endpoint de diagnóstico del sistema. Verifica que los tres componentes
    estén funcionando correctamente.

    Accesible en: http://10.42.0.203:8080/health
    Útil para verificar el estado antes de usar el sistema.
    """
    # Verificar que el archivo del modelo ONNX existe en disco.
    model_ok = Path(VISION_MODEL).exists()

    onnx_ok = False
    llm_ok  = False

    # Intentar importar onnxruntime. Si no está instalado (setup-vision.sh
    # no se ejecutó aún), la importación falla silenciosamente.
    try:
        import onnxruntime
        onnx_ok = True
    except ImportError:
        pass  # onnxruntime no instalado, onnx_ok queda False

    # Intentar contactar llama-server en el puerto 8081.
    # Se verifica que la respuesta tenga {"status": "ok"} (no solo 200 HTTP),
    # porque llama-server puede responder 200 mientras aún carga el modelo.
    try:
        with urlreq.urlopen(f"{LLM_URL}/health", timeout=3) as r:
            llm_ok = json.loads(r.read()).get("status") == "ok"
    except Exception:
        pass  # llama-server no está corriendo, llm_ok queda False

    return {
        "status":      "online",    # Este servidor está activo
        "onnx_model":  model_ok,    # El archivo .onnx existe
        "onnxruntime": onnx_ok,     # La librería está instalada
        "llm_server":  llm_ok,      # llama-server está respondiendo
        "version":     "2.1.0"
    }


@app.get("/")
async def root():
    """
    Sirve la página principal del frontend (index.html).

    Cuando el usuario abre http://10.42.0.203:8080 en el navegador,
    este endpoint devuelve el archivo HTML con la interfaz visual.
    Si el archivo no existe (no se copiaron los archivos estáticos),
    devuelve un mensaje de error informativo.
    """
    html_path = Path(STATIC_DIR) / "index.html"

    if not html_path.exists():
        # El directorio static/ existe pero no tiene el HTML.
        # Ocurre si no se corrió: scp -r static/ root@jetson:/opt/banano-web/
        return HTMLResponse(
            "<h1>Banano AI</h1>"
            f"<p>Backend activo. Interfaz no encontrada en {STATIC_DIR}/index.html</p>"
        )

    # Leer el archivo HTML y devolverlo como respuesta.
    # encoding="utf-8": necesario para los caracteres especiales en español.
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ── Punto de entrada ─────────────────────────────────────────────────────────
# Este bloque solo se ejecuta cuando se corre el archivo directamente:
#   python3 banano_diagnostico.py
# No se ejecuta si el archivo es importado por otro módulo.
if __name__ == "__main__":
    import uvicorn
    # uvicorn: servidor ASGI de alto rendimiento para apps FastAPI.
    # host="0.0.0.0": escuchar en todas las interfaces de red de la Jetson,
    #                 no solo en localhost. Necesario para acceso desde la red.
    # port=8080: puerto donde escucha el servidor.
    uvicorn.run(app, host="0.0.0.0", port=8080)
