#!/bin/sh
export LD_LIBRARY_PATH=/usr/local/cuda-10.2/lib:/usr/lib:$LD_LIBRARY_PATH

pkill -9 -f banano_diagnostico 2>/dev/null
pkill -9 -f uvicorn 2>/dev/null
pkill -9 -f llama-server 2>/dev/null
pkill -9 -f llama-cli 2>/dev/null
sleep 2

MODEL=$(for f in /root/.ollama/models/blobs/*; do
    echo "$(wc -c < $f 2>/dev/null) $f"
done | sort -rn | head -1 | awk '{print $2}')

echo "[start-banano] Modelo: $MODEL"
echo "[start-banano] Iniciando llama-server..."

llama-server \
    --model "$MODEL" \
    --n-gpu-layers 99 \
    -c 1024 -ub 64 \
    --host 127.0.0.1 \
    --port 8081 \
    --no-warmup \
    --log-disable &

LLAMA_PID=$!
echo "[start-banano] llama-server PID: $LLAMA_PID"
echo "[start-banano] Esperando que este listo..."

i=0
while [ $i -lt 90 ]; do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health', timeout=2)" 2>/dev/null; then
        echo "[start-banano] llama-server listo en ${i}s"
        break
    fi
    i=$((i + 2))
    sleep 2
done

echo "[start-banano] Iniciando banano-web en puerto 8080..."
cd /opt/banano-web
python3 backend/banano_diagnostico.py
