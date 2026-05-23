IMAGE_INSTALL_append = " autologin show-ip ollama"

ROOTFS_POSTPROCESS_COMMAND_append = " \
    configure_sshd; \
    enable_timesyncd; \
    configure_wifi; \
    configure_networkd; \
    fix_cuda_symlinks; \
    install_ollama_env; \
    install_setup_script; \
"

configure_sshd() {
    SSHD_CONFIG="${IMAGE_ROOTFS}/etc/ssh/sshd_config"
    if [ ! -f "${SSHD_CONFIG}" ]; then
        bbwarn "configure_sshd: sshd_config no encontrado, omitiendo."
        return 0
    fi
    sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/'          "${SSHD_CONFIG}"
    sed -i 's/^#*PermitEmptyPasswords.*/PermitEmptyPasswords yes/' "${SSHD_CONFIG}"
    sed -i 's/^#*UsePAM.*/UsePAM no/'                             "${SSHD_CONFIG}"
    grep -q "^PermitRootLogin"      "${SSHD_CONFIG}" || echo "PermitRootLogin yes"      >> "${SSHD_CONFIG}"
    grep -q "^PermitEmptyPasswords" "${SSHD_CONFIG}" || echo "PermitEmptyPasswords yes" >> "${SSHD_CONFIG}"
    grep -q "^UsePAM"               "${SSHD_CONFIG}" || echo "UsePAM no"                >> "${SSHD_CONFIG}"
}

enable_timesyncd() {
    WANTS_DIR="${IMAGE_ROOTFS}/etc/systemd/system/sysinit.target.wants"
    UNIT="${IMAGE_ROOTFS}/lib/systemd/system/systemd-timesyncd.service"
    if [ -f "${UNIT}" ]; then
        install -d "${WANTS_DIR}"
        ln -sf /lib/systemd/system/systemd-timesyncd.service \
               "${WANTS_DIR}/systemd-timesyncd.service"
    else
        bbwarn "enable_timesyncd: systemd-timesyncd.service no encontrado."
    fi
}

fix_cuda_symlinks() {
    # Los paquetes instalan libcudart.so.10.2 pero el linker necesita
    # libcudart.so sin versión para resolver -lcudart al compilar llama.cpp.
    CUDA_LIB="${IMAGE_ROOTFS}/usr/local/cuda-10.2/lib"
    if [ ! -d "${CUDA_LIB}" ]; then
        bbwarn "fix_cuda_symlinks: directorio CUDA lib no encontrado."
        return 0
    fi
    for versioned in "${CUDA_LIB}"/lib*.so.[0-9]*; do
        [ -f "${versioned}" ] || continue
        base=$(basename "${versioned}" | sed 's/\.so\.[0-9].*/.so/')
        [ -f "${CUDA_LIB}/${base}" ] || \
            ln -sf "$(basename ${versioned})" "${CUDA_LIB}/${base}"
    done

    # ldconfig para que el linker dinámico encuentre las CUDA libs en runtime
    install -d "${IMAGE_ROOTFS}/etc/ld.so.conf.d"
    echo "/usr/local/cuda-10.2/lib" > \
        "${IMAGE_ROOTFS}/etc/ld.so.conf.d/cuda.conf"

    # Stub arm_bf16.h — GCC 9 no lo incluye.
    # El código MLX de llama.cpp lo necesita aunque nunca ejecute
    # instrucciones BF16 en el Cortex-A57 (ARMv8.0).
    GCC_INC="${IMAGE_ROOTFS}/usr/lib/gcc/aarch64-poky-linux/9.5.0/include"
    install -d "${GCC_INC}"
    cat > "${GCC_INC}/arm_bf16.h" << 'BFEOF'
/* Stub arm_bf16.h — ARMv8.0 no tiene BF16 nativo, GCC 9 no incluye este header */
#ifndef __ARM_BF16_H
#define __ARM_BF16_H
typedef unsigned short bfloat16_t;
typedef unsigned short __bf16;
#ifdef __ARM_NEON
#include <arm_neon.h>
typedef uint16x4_t bfloat16x4_t;
typedef uint16x8_t bfloat16x8_t;
#endif
#endif
BFEOF
    bbnote "fix_cuda_symlinks: CUDA symlinks, ldconf y arm_bf16.h configurados."
}

install_ollama_env() {
    # Variables de entorno de Ollama ajustadas para Jetson Nano:
    # - FLASH_ATTENTION=0: Maxwell no soporta Flash Attention nativo
    # - NUM_GPU=999: intentar poner todas las capas en GPU
    # - NUM_PARALLEL=1: Jetson Nano no tiene RAM suficiente para paralelismo
    # - LD_LIBRARY_PATH: incluye el path de las CUDA libs para runtime
    install -d "${IMAGE_ROOTFS}/etc/ollama"
    cat > "${IMAGE_ROOTFS}/etc/ollama/environment" << 'ENVEOF'
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_MODELS=/root/.ollama/models
OLLAMA_LOAD_TIMEOUT=300s
OLLAMA_KEEP_ALIVE=5m
OLLAMA_GPU_MEMORY_FRACTION=0.80
OLLAMA_NUM_GPU=999
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
OLLAMA_FLASH_ATTENTION=0
CUDA_VISIBLE_DEVICES=0
LD_LIBRARY_PATH=/usr/local/cuda-10.2/lib:/usr/lib:${LD_LIBRARY_PATH}
ENVEOF
}

install_setup_script() {
    # Script que el usuario ejecuta una vez con internet.
    # Compila llama.cpp con CUDA sm_53 (Maxwell) y lo instala como
    # llama-server + llama-cli en /usr/local/bin.
    # El modelo gemma2:2b ya está pre-baked en /root/.ollama/models/blobs/
    # en formato GGUF, compatible directamente con llama.cpp.
    install -d "${IMAGE_ROOTFS}/usr/local/bin"
    cat > "${IMAGE_ROOTFS}/usr/local/bin/setup-inference.sh" << 'SCRIPT'
#!/bin/sh
set -e
echo "=== Configurando llama.cpp con CUDA para Jetson Nano ==="

# Paso 1: CMake 3.26 (el sistema tiene 3.16, necesario 3.18+ para CUDA)
if ! cmake --version 2>/dev/null | grep -qE "3\.[2-9][0-9]"; then
    echo "[1/4] Descargando CMake 3.26..."
    cd /tmp
    wget -q https://github.com/Kitware/CMake/releases/download/v3.26.4/cmake-3.26.4-linux-aarch64.tar.gz
    tar -xzf cmake-3.26.4-linux-aarch64.tar.gz -C /usr/local/
    ln -sf /usr/local/cmake-3.26.4-linux-aarch64/bin/cmake /usr/local/bin/cmake
fi
cmake --version | head -1

# Paso 2: Go 1.21 para ARM64
if [ ! -x /usr/local/go/bin/go ]; then
    echo "[2/4] Descargando Go 1.21..."
    cd /tmp
    wget -q https://go.dev/dl/go1.21.13.linux-arm64.tar.gz
    tar -xzf go1.21.13.linux-arm64.tar.gz -C /usr/local/
fi
export PATH=/usr/local/go/bin:$PATH
go version

# Paso 3: ldconfig
ldconfig

# Paso 4: llama.cpp con CUDA sm_53
if [ ! -x /usr/local/bin/llama-server ]; then
    echo "[3/4] Compilando llama.cpp..."
    cd /tmp
    rm -rf llama.cpp
    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp

    sed -i 's/cmake_minimum_required(VERSION 3.18)/cmake_minimum_required(VERSION 3.14)/' \
        ggml/src/ggml-cuda/CMakeLists.txt

    cmake -B build \
        -DGGML_CUDA=ON \
        -DCMAKE_CUDA_ARCHITECTURES=53 \
        -DCMAKE_CUDA_COMPILER=/usr/local/cuda-10.2/bin/nvcc \
        -DCUDAToolkit_ROOT=/usr/local/cuda-10.2 \
        -DCMAKE_C_COMPILER=/usr/bin/aarch64-poky-linux-gcc \
        -DCMAKE_CXX_COMPILER=/usr/bin/aarch64-poky-linux-g++

    cmake --build build --config Release -j4
    install -m 0755 build/bin/llama-server /usr/local/bin/
    install -m 0755 build/bin/llama-cli    /usr/local/bin/
fi

MODEL=$(find /root/.ollama/models/blobs -type f -size +1G 2>/dev/null | head -1)
echo ""
echo "=== Listo ==="
echo "Modelo: ${MODEL:-no encontrado en /root/.ollama/models/blobs}"
echo ""
echo "Iniciar servidor GPU:"
echo "  llama-server --model \$MODEL --n-gpu-layers 99 --host 0.0.0.0 --port 8080 &"
echo ""
echo "Consulta rápida CPU:"
echo "  llama-cli --model \$MODEL -p 'Tu pregunta' -n 200"
SCRIPT
    chmod +x "${IMAGE_ROOTFS}/usr/local/bin/setup-inference.sh"
}
