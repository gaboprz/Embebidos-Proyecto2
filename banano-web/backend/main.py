from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import base64
import random
import time

app = FastAPI(title="Banano AI Diagnostic System")

# Servir archivos estáticos (la interfaz web)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Función simulada de diagnóstico (para probar sin Ollama)
def simulate_diagnosis(has_image, has_text):
    """
    Esta función simula lo que haría Ollama.
    Más adelante la reemplazaremos con la llamada real a Ollama.
    """
    diseases = [
        "Sigatoka Negra",
        "Sigatoka Amarilla", 
        "Fusarium (Mal de Panamá)",
        "Deficiencia Nutricional",
        "Planta Sana"
    ]
    
    recommendations = {
        "Sigatoka Negra": "Aplicar fungicida sistémico (Propiconazol) cada 14 días. Eliminar hojas severamente infectadas. Mejorar drenaje del suelo.",
        "Sigatoka Amarilla": "Aplicar fungicida protectante (Mancozeb). Monitorear semanalmente. Remover hojas afectadas.",
        "Fusarium (Mal de Panamá)": "ALERTA: Enfermedad del suelo. Aislar área afectada. No plantar banano en este lote por 5+ años. Consultar SENASA.",
        "Deficiencia Nutricional": "Análisis de suelo recomendado. Aplicar fertilizante NPK 15-5-30. Verificar pH del suelo (óptimo: 5.5-6.5).",
        "Planta Sana": "Continuar con monitoreo preventivo. Mantener programa de nutrición actual."
    }
    
    # Simular procesamiento (para que se vea realista)
    time.sleep(2)
    
    # Seleccionar diagnóstico aleatorio
    disease = random.choice(diseases)
    confidence = random.uniform(0.75, 0.98)
    
    return {
        "enfermedad": disease,
        "confianza": confidence,
        "recomendacion": recommendations[disease],
        "modalidad": "multimodal" if (has_image and has_text) else ("visual" if has_image else "textual")
    }


@app.post("/diagnose")
async def diagnose(
    image: UploadFile = File(None),
    text: str = Form(None)
):
    """
    Endpoint principal de diagnóstico.
    Acepta: imagen, texto, o ambos.
    """
    # Validar que al menos hay algo
    if not image and not text:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos una imagen o descripción de texto"
        )
    
    has_image = image is not None
    has_text = text is not None and text.strip() != ""
    
    # Por ahora simulamos el diagnóstico
    # Más adelante aquí llamaremos a Ollama
    result = simulate_diagnosis(has_image, has_text)
    
    # Guardar info de debug
    print(f"📸 Imagen recibida: {has_image}")
    print(f"✍️  Texto recibido: {has_text}")
    if has_text:
        print(f"   Contenido: {text[:100]}...")
    
    return result


@app.get("/health")
async def health_check():
    """Verificar que el servidor está funcionando"""
    return {
        "status": "online",
        "backend": "FastAPI",
        "ollama": "simulated (will connect later)",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Servir la página principal"""
    html_path = Path("static/index.html")
    if not html_path.exists():
        return HTMLResponse(
            "<h1>Error: index.html no encontrado</h1>"
            "<p>Asegúrate de crear el archivo static/index.html</p>"
        )
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
