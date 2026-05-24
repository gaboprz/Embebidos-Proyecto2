#!/bin/bash
# setup-llama.sh — Compila llama.cpp b5050 con CUDA sm_53 en Jetson Nano P3450
# Requiere: internet en primer arranque, ~85 minutos de compilacion.
# Referencia: https://gist.github.com/kreier/6871691130ec3ab907dd2815f9313c5d

set -e

LLAMA_BUILD_DIR="/opt/llama.cpp"
LLAMA_COMMIT="23106f9"
CMAKE_VERSION="3.26.4"
CMAKE_DIR="/usr/local/cmake-${CMAKE_VERSION}-linux-aarch64"

log() { echo "[setup-llama] $*"; }

find_model() {
    local largest="" max=0
    for f in /root/.ollama/models/blobs/*; do
        [ -f "$f" ] || continue
        local size
        size=$(wc -c < "$f" 2>/dev/null || echo 0)
        if [ "$size" -gt "$max" ]; then max="$size"; largest="$f"; fi
    done
    echo "$largest"
}

log "=== Configurando llama.cpp ${LLAMA_COMMIT} con CUDA sm_53 ==="
log "Referencia: https://gist.github.com/kreier/6871691130ec3ab907dd2815f9313c5d"

# 1. Verificar prerequisitos CUDA
log "[1/5] Verificando prerequisitos CUDA..."
for req in \
    /usr/local/cuda-10.2/include/cuda_runtime.h \
    /usr/local/cuda-10.2/include/cublas_v2.h \
    /usr/local/cuda-10.2/lib/libcudadevrt.a \
    /usr/local/cuda-10.2/lib/libcudart_static.a \
    /usr/local/cuda-10.2/include/cuda_bf16.h \
    /usr/local/cuda-10.2/bin/nvcc; do
    if [ ! -f "$req" ] && [ ! -x "$req" ]; then
        log "ERROR: falta $req"
        log "Asegurese de que la imagen incluye cuda-cudart-dev y cuda-libraries"
        exit 1
    fi
done
log "CUDA 10.2 prerequisitos OK"

# 2. cmake 3.26
log "[2/5] Verificando cmake >= 3.18..."
if ! cmake --version 2>/dev/null | grep -qE "3\.[2-9][0-9]"; then
    log "Descargando cmake ${CMAKE_VERSION}..."
    cd /tmp
    wget -q --show-progress \
        "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-aarch64.tar.gz"
    tar -xzf "cmake-${CMAKE_VERSION}-linux-aarch64.tar.gz" -C /usr/local/
    ln -sf "${CMAKE_DIR}/bin/cmake" /usr/local/bin/cmake
    rm -f "cmake-${CMAKE_VERSION}-linux-aarch64.tar.gz"
fi
log "$(cmake --version | head -1) disponible"

# Si ya esta compilado, mostrar instrucciones y salir
if [ -x /usr/local/bin/llama-cli ]; then
    log "llama-cli ya disponible. Compilacion previa detectada."
    MODEL_PATH=$(find_model)
    [ -n "$MODEL_PATH" ] && log "Modelo: $MODEL_PATH"
    log "Uso: llama-cli --model \"$MODEL_PATH\" --n-gpu-layers 99 -c 512 -ub 64 -n 400"
    exit 0
fi

# 3. Clonar b5050
log "[3/5] Clonando llama.cpp commit ${LLAMA_COMMIT} (b5050)..."
rm -rf "$LLAMA_BUILD_DIR"
git clone https://github.com/ggml-org/llama.cpp "$LLAMA_BUILD_DIR"
cd "$LLAMA_BUILD_DIR"
git checkout "$LLAMA_COMMIT"
git checkout -b llamaJetsonNanoCUDA

# 4. Seis parches de compatibilidad CUDA 10.2 + GCC 9.5
log "[4/5] Aplicando parches de compatibilidad..."

sed -i '14a if(NOT DEFINED ${CMAKE_CUDA_ARCHITECTURES})\n    set(CMAKE_CUDA_ARCHITECTURES 53)\nendif()' \
    CMakeLists.txt

sed -i '/set_target_properties(ggml PROPERTIES PUBLIC_HEADER/a add_link_options(-Wl,--copy-dt-needed-entries)' \
    ggml/CMakeLists.txt

sed -i '455s/static constexpr __device__/static __device__/' \
    ggml/src/ggml-cuda/common.cuh

sed -i '623s/__builtin_assume/\/\/__builtin_assume/' ggml/src/ggml-cuda/fattn-common.cuh
sed -i '71s/__builtin_assume/\/\/__builtin_assume/'  ggml/src/ggml-cuda/fattn-vec-f32.cuh
sed -i '73s/__builtin_assume/\/\/__builtin_assume/'  ggml/src/ggml-cuda/fattn-vec-f16.cuh

log "Parches aplicados OK"

# 5. Compilar
log "[5/5] Compilando (~85 minutos)..."
export PATH="${CMAKE_DIR}/bin:$PATH"
export LD_LIBRARY_PATH="/usr/local/cuda-10.2/lib:/usr/lib:${LD_LIBRARY_PATH}"

cmake -B build \
    -DGGML_CUDA=ON \
    -DLLAMA_CURL=OFF \
    -DCMAKE_CUDA_STANDARD=14 \
    -DCMAKE_CUDA_STANDARD_REQUIRED=true \
    -DGGML_CPU_ARM_ARCH=armv8-a \
    -DGGML_NATIVE=off \
    -DCMAKE_CUDA_ARCHITECTURES=53 \
    -DCMAKE_CUDA_COMPILER=/usr/local/cuda-10.2/bin/nvcc \
    -DCUDAToolkit_ROOT=/usr/local/cuda-10.2 \
    -DCMAKE_C_COMPILER=/usr/bin/aarch64-poky-linux-gcc \
    -DCMAKE_CXX_COMPILER=/usr/bin/aarch64-poky-linux-g++ \
    -DCMAKE_CUDA_RUNTIME_LIBRARY=SHARED

find build/ -type f 2>/dev/null | \
    xargs grep -l "stdc++fs" 2>/dev/null | \
    while read f; do sed -i 's/-lstdc++fs//g' "$f"; done

cmake --build build --config Release -j4

install -m 0755 build/bin/llama-cli    /usr/local/bin/llama-cli
install -m 0755 build/bin/llama-server /usr/local/bin/llama-server
install -m 0755 build/bin/llama-bench  /usr/local/bin/llama-bench

log "=== Compilacion exitosa. Binarios en /usr/local/bin/ ==="

MODEL_PATH=$(find_model)
if [ -n "$MODEL_PATH" ]; then
    log "Modelo: $MODEL_PATH"
    log "Uso GPU: llama-cli --model \"$MODEL_PATH\" --n-gpu-layers 99 -c 512 -ub 64 -n 400"
fi
