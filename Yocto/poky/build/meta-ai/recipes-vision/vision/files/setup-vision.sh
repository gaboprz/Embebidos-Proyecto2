#!/bin/sh
# setup-vision.sh — Instala ONNX Runtime para el clasificador de banano
# Se ejecuta una vez en el primer arranque con internet disponible.

set -e

log() { echo "[setup-vision] $*"; }

# Verificar si ya está instalado
if python3 -c "import onnxruntime" 2>/dev/null; then
    log "onnxruntime ya instalado: $(python3 -c 'import onnxruntime; print(onnxruntime.__version__)')"
    exit 0
fi

log "Instalando ONNX Runtime (CPU)..."

# onnxruntime CPU para aarch64 Python 3.8
pip3 install --no-cache-dir onnxruntime==1.16.3 numpy==1.24.4

log "Verificando instalación..."
python3 -c "import onnxruntime as ort; print('[setup-vision] onnxruntime', ort.__version__, 'OK')"

log "Verificando modelo..."
if [ ! -f /opt/vision/models/banana_disease_classifier.onnx ]; then
    log "ERROR: modelo no encontrado en /opt/vision/models/"
    exit 1
fi

# Prueba de carga del modelo
python3 -c "
import onnxruntime as ort
session = ort.InferenceSession(
    '/opt/vision/models/banana_disease_classifier.onnx',
    providers=['CPUExecutionProvider']
)
inp = session.get_inputs()[0]
print(f'[setup-vision] Modelo OK — entrada: {inp.name} shape: {inp.shape}')
"

log "=== Setup de Vision AI completo ==="
log "Uso: python3 /opt/vision/bin/inference.py /ruta/imagen.jpg"
