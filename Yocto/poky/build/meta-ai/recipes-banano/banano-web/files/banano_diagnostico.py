#!/usr/bin/env python3
"""
Banano Diagnóstico — Backend FastAPI
Clasificación visual: MobileNetV2 + ONNX Runtime  → puerto 8080
Explicación natural:  gemma2:2b via llama-server  → puerto 8081 (interno)
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import subprocess
import tempfile
import asyncio
import json
import os
import urllib.request as urlreq

app = FastAPI(title="Banano AI — Diagnóstico de Enfermedades")

INFERENCE_SCRIPT     = "/opt/vision/bin/inference.py"
VISION_MODEL         = "/opt/vision/models/banana_disease_classifier.onnx"
STATIC_DIR           = "/opt/banano-web/static"
LLM_URL              = "http://127.0.0.1:8081"
CONFIDENCE_THRESHOLD = 0.60   # Debajo de esto: posible imagen no-banano
LLM_MAX_TOKENS       = 600
LLM_TIMEOUT          = 480

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


# ─── Inferencia ONNX ──────────────────────────────────────────────────────────

def run_vision_inference(image_bytes: bytes) -> dict:
    """Corre MobileNetV2 sobre la imagen via subprocess de inference.py."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["python3", INFERENCE_SCRIPT, tmp_path, "--model", VISION_MODEL],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Error en inferencia ONNX")
        return json.loads(result.stdout.strip())
    finally:
        os.unlink(tmp_path)


# ─── Prompt para el LLM ───────────────────────────────────────────────────────

def build_llm_prompt(disease: str, confidence: float, user_text: str = None) -> str:
    """Construye el prompt según el caso: solo imagen, solo texto, o imagen+texto."""

    no_markdown = (
        "IMPORTANTE: responde SOLO en texto plano. "
        "No uses asteriscos, guiones para negritas, ni formato Markdown. "
        "Usa mayúsculas para los títulos de sección."
    )

    # ── CASO 2: Solo texto del agricultor, sin imagen ─────────────────────────
    if disease == "Indeterminado" and user_text:
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

    # ── Imagen con confianza baja (posible no-banano) ─────────────────────────
    if confidence < CONFIDENCE_THRESHOLD:
        base = (
            f"Eres un experto agrícola en banano de Costa Rica. "
            f"Un sistema de visión artificial analizó una imagen con confianza muy baja "
            f"({confidence:.0%}), lo que indica que posiblemente no es una hoja de banano "
            f"o la imagen no es suficientemente clara para diagnosticar. "
        )
        if user_text:
            base += (
                f"Sin embargo, el agricultor también describe: \"{user_text}\". "
                f"Usa esta descripción para orientar al agricultor sobre posibles problemas "
                f"y recomiéndale tomar una foto más clara para confirmar. "
            )
        else:
            base += (
                f"Explica esto al agricultor en 3 oraciones y dale instrucciones concretas "
                f"sobre cómo tomar una buena foto de la hoja: distancia, iluminación y ángulo. "
            )
        base += f"Responde en español. {no_markdown}"
        return base

    # ── Planta sana ───────────────────────────────────────────────────────────
    if disease == "Healthy":
        base = (
            f"Eres un experto agrícola en banano de Costa Rica. "
            f"Un sistema de visión artificial confirmó que la planta está SANA "
            f"con {confidence:.0%} de confianza. "
        )
        if user_text:
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

    # ── CASO 1 y 3: Enfermedad detectada (con o sin texto adicional) ──────────
    context = DISEASE_CONTEXT.get(disease, disease)
    base = (
        f"Eres un experto agrícola en banano de Costa Rica. "
        f"Un sistema de visión artificial detectó {disease} con {confidence:.0%} "
        f"de confianza en una hoja de banano. Contexto: {context} "
    )
    if user_text:
        base += (
            f"\n\nAdicionalmente, el agricultor describe: \"{user_text}\". "
            f"Considera tanto el diagnóstico visual como esta descripción para un "
            f"análisis más completo y preciso. "
        )
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

def strip_markdown(text: str) -> str:
    """Elimina Markdown y formatea secciones con saltos de línea."""
    import re
    # Quitar formato Markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'__(.+?)__',     r'\1', text)
    text = re.sub(r'_(.+?)_',       r'\1', text)
    text = re.sub(r'^#{1,6}\s+',    '',    text, flags=re.MULTILINE)
    text = re.sub(r'`(.+?)`',       r'\1', text)

    # Agregar salto doble antes de cada título de sección en mayúsculas
    # Ejemplo: "TRATAMIENTO:" → "\n\nTRATAMIENTO:"
    text = re.sub(r'\s{0,2}([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,}:)', r'\n\n\1', text)

    # Agregar salto antes de ítems numerados (1. 2. 3.)
    text = re.sub(r'\s+(\d+\.)\s', r'\n\1 ', text)

    return text.strip()

# ─── Llamada al LLM via urllib (httpx async no funciona en Yocto) ─────────────

def _call_llm_sync(prompt: str):
    """Llama a llama-server usando urllib.request (sincrónico)."""
    payload = json.dumps({
        "model":       "gemma2",
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  LLM_MAX_TOKENS,
        "temperature": 0.3,
        "stream":      False
    }).encode()

    req = urlreq.Request(
        f"{LLM_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urlreq.urlopen(req, timeout=LLM_TIMEOUT) as r:
            data = json.loads(r.read())
            return strip_markdown(data["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"[LLM ERROR] {type(e).__name__}: {e}")
        return None


async def call_llm(prompt: str):
    """Ejecuta la llamada síncrona al LLM en un thread para no bloquear FastAPI."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_llm_sync, prompt)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/diagnose")
async def diagnose(
    image: UploadFile = File(None),
    text:  str        = Form(None)
):
    if not image and not text:
        raise HTTPException(status_code=400,
            detail="Debe proporcionar al menos una imagen o descripción")

    disease    = "Indeterminado"
    confidence = 0.0
    all_scores = {}
    user_text  = text.strip() if text and text.strip() else None

    # Correr ONNX solo si hay imagen
    if image:
        image_bytes = await image.read()
        try:
            vision_result = run_vision_inference(image_bytes)
        except Exception as e:
            raise HTTPException(status_code=500,
                detail=f"Error en clasificación visual: {str(e)}")
        disease    = vision_result.get("disease",    "Indeterminado")
        confidence = vision_result.get("confidence", 0.0)
        all_scores = vision_result.get("all_scores", {})

    # Llamar al LLM si hay algo que analizar
    recomendacion = None
    if disease != "Indeterminado" or user_text:
        prompt        = build_llm_prompt(disease, confidence, user_text)
        recomendacion = await call_llm(prompt)

    # Determinar modalidad
    if image and user_text:
        modalidad = "multimodal"
    elif user_text:
        modalidad = "textual"
    else:
        modalidad = "visual"

    return {
        "enfermedad":    disease if image else "Análisis por descripción",
        "confianza":     round(confidence, 4) if image else None,
        "imagen_valida": (confidence >= CONFIDENCE_THRESHOLD) if image else None,
        "all_scores":    all_scores,
        "recomendacion": recomendacion or "Servicio LLM no disponible — inicie llama-server.",
        "llm_activo":    recomendacion is not None,
        "modalidad":     modalidad
    }

@app.get("/health")
async def health():
    model_ok = Path(VISION_MODEL).exists()
    onnx_ok  = False
    llm_ok   = False

    try:
        import onnxruntime
        onnx_ok = True
    except ImportError:
        pass

    try:
        with urlreq.urlopen(f"{LLM_URL}/health", timeout=3) as r:
            llm_ok = json.loads(r.read()).get("status") == "ok"
    except Exception:
        pass

    return {
        "status":      "online",
        "onnx_model":  model_ok,
        "onnxruntime": onnx_ok,
        "llm_server":  llm_ok,
        "version":     "2.1.0"
    }


@app.get("/")
async def root():
    html_path = Path(STATIC_DIR) / "index.html"
    if not html_path.exists():
        return HTMLResponse(
            "<h1>Banano AI</h1>"
            f"<p>Backend activo. Interfaz no encontrada en {STATIC_DIR}/index.html</p>"
        )
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
