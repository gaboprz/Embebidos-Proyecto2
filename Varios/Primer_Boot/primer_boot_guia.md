# Primer Boot — Jetson Nano P3450 con llama.cpp + Vision AI

## Prerequisitos
- Jetson Nano encendida con la SD flasheada
- Cable Ethernet conectado con acceso a internet
- Sesión SSH activa: `ssh root@10.42.0.203`

---

## 0 — Verificación inicial

Antes de cualquier instalación, confirmar que la imagen tiene todo lo necesario:

```bash
echo "=== CUDA ===" && \
ls /usr/local/cuda-10.2/include/cublas_v2.h && \
grep "GNUC" /usr/local/cuda-10.2/include/crt/host_config.h | grep "[0-9]"

echo "=== Scripts ===" && \
ls -lh /usr/local/bin/setup-llama.sh /usr/local/bin/setup-vision.sh

echo "=== Modelo Vision ===" && \
ls -lh /opt/vision/models/banana_disease_classifier.onnx

echo "=== Imágenes muestra ===" && \
ls /opt/vision/samples/

echo "=== Banano Web ===" && \
ls /opt/banano-web/backend/banano_diagnostico.py
```

**Resultado esperado:** todos los archivos presentes sin errores.
Si falta alguno, no continuar — la imagen no se generó correctamente.

---

## 1 — Instalar llama.cpp con CUDA (~85 minutos)

```bash
setup-llama.sh 2>&1 | tee /tmp/setup-llama-log.txt
```

Para monitorear el uso de GPU en otra terminal:

```bash
tegrastats --interval 3000
```

**Resultado esperado al finalizar:**
```
[setup-llama] === Compilacion exitosa. Binarios en /usr/local/bin/ ===
```

---

## 2 — Probar llama.cpp con gemma2:2b

```bash
export LD_LIBRARY_PATH=/usr/local/cuda-10.2/lib:/usr/lib:$LD_LIBRARY_PATH

MODEL=$(for f in /root/.ollama/models/blobs/*; do
    echo "$(wc -c < $f 2>/dev/null) $f"
done | sort -rn | head -1 | awk '{print $2}')

echo "Modelo: $MODEL"

llama-cli --model "$MODEL" --n-gpu-layers 99 \
    -c 256 -ub 64 -n 50 \
    -p "What is 2+2? Answer briefly."
```

**Resultado esperado:** respuesta generada con `offloaded 27/27 layers to GPU` en los logs de inicio.

---

## 3 — Instalar ONNX Runtime

```bash
setup-vision.sh 2>&1 | tee /tmp/setup-vision-log.txt
```

> **Nota:** si el script falla por versión de numpy incompatible, correr manualmente:
> ```bash
> pip3 install --no-cache-dir onnxruntime==1.16.3 numpy==1.24.4
> ```

Verificar instalación limpia:

```bash
python3 -c "
import onnxruntime as ort
import numpy as np
print('onnxruntime:', ort.__version__)
print('numpy:', np.__version__)
print('Providers:', ort.get_available_providers())
"
```

**Resultado esperado:** sin ningún traceback ni warning de numpy.

---

## 4 — Probar inferencia con el modelo de banano

```bash
for img in /opt/vision/samples/*.jpg; do
    echo "--- $(basename $img) ---"
    python3 /opt/vision/bin/inference.py "$img"
    echo ""
done
```

**Resultado esperado por imagen:**
```json
{
  "success": true,
  "prediction": {
    "disease": "Black Sigatoka",
    "confidence": 92.3,
    "is_certain": true
  },
  "engine": "onnx"
}
```

---

## 5 — Instalar dependencias de banano-web

```bash
pip3 install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    python-multipart==0.0.6 \
    httpx==0.25.1
```

---

## 6 — Iniciar banano-web

```bash
cd /opt/banano-web
python3 backend/banano_diagnostico.py
```

**Resultado esperado:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

Verificar desde la Jetson:

```bash
# En otra terminal
python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8080/health')
print(json.loads(r.read()))
"
```

Acceder desde la computadora host: `http://10.42.0.203:8080/health`

---

## 7 — Prueba de diagnóstico completo

Enviar una imagen de muestra al endpoint desde la Jetson:

```bash
python3 << 'PYEOF'
import urllib.request, json

with open('/opt/vision/samples/black_sigatoka_01.jpg', 'rb') as f:
    img_data = f.read()

boundary = 'boundary123'
body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="image"; filename="test.jpg"\r\n'
    f'Content-Type: image/jpeg\r\n\r\n'
).encode() + img_data + f'\r\n--{boundary}--\r\n'.encode()

req = urllib.request.Request(
    'http://localhost:8080/diagnose',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
r = urllib.request.urlopen(req)
print(json.dumps(json.loads(r.read()), indent=2, ensure_ascii=False))
PYEOF
```

**Resultado esperado:**
```json
{
  "enfermedad": "Black Sigatoka",
  "confianza": 0.923,
  "recomendacion": "Aplicar fungicida sistémico...",
  "modalidad": "visual"
}
```

---

## Resumen de tiempos

| Paso | Tiempo estimado |
|---|---|
| Verificación inicial | < 1 min |
| setup-llama.sh | ~85 min |
| Test llama.cpp | ~2 min |
| setup-vision.sh | ~5 min |
| Test inferencia ONNX | < 1 min |
| pip install banano-web | ~2 min |
| Test banano-web | < 1 min |
| **Total** | **~96 min** |
