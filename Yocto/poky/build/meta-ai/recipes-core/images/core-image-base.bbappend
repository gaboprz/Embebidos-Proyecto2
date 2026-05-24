IMAGE_INSTALL_append = " autologin show-ip ollama"

ROOTFS_POSTPROCESS_COMMAND_append = " \
    configure_sshd; \
    enable_timesyncd; \
    fix_cuda_symlinks; \
    install_ollama_env; \
    install_setup_script; \
"

LLAMA_SCRIPT := "${@os.path.dirname(d.getVar('FILE'))}/files/setup-llama.sh"

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

    install -d "${IMAGE_ROOTFS}/etc/ld.so.conf.d"
    echo "/usr/local/cuda-10.2/lib" > \
        "${IMAGE_ROOTFS}/etc/ld.so.conf.d/cuda.conf"

    GCC_INC="${IMAGE_ROOTFS}/usr/lib/gcc/aarch64-poky-linux/9.5.0/include"
    install -d "${GCC_INC}"
    cat > "${GCC_INC}/arm_bf16.h" << 'BFEOF'
/* Stub arm_bf16.h */
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

    ln -sf /usr/local/cuda-10.2/lib \
        "${IMAGE_ROOTFS}/usr/local/cuda-10.2/lib64"

    CUDA_INC="${IMAGE_ROOTFS}/usr/local/cuda-10.2/include"
    install -d "${CUDA_INC}"
    cat > "${CUDA_INC}/cuda_bf16.h" << 'BFEOF'
#ifndef CUDA_BF16_H
#define CUDA_BF16_H
#include <cuda_fp16.h>
typedef half  nv_bfloat16;
typedef half2 nv_bfloat162;
#endif
BFEOF

    cat > "${CUDA_INC}/cuda_bf16.hpp" << 'BFEOF'
#ifndef CUDA_BF16_HPP
#define CUDA_BF16_HPP
#include "cuda_bf16.h"
#endif
BFEOF

    # Copiar SDK CUDA completo (cublas_v2.h, cufft.h, etc.) desde el
    # recipe-sysroot de cuda-libraries, disponible en build time.
    # cp -rf para garantizar que cublas_v2.h y otros lleguen al rootfs.
    for _cuda_inc in ${TMPDIR}/work/*-poky-linux/cuda-libraries/*/recipe-sysroot/usr/local/cuda-10.2/include; do
        if [ -d "${_cuda_inc}" ]; then
            cp -rf "${_cuda_inc}/"* \
                "${IMAGE_ROOTFS}/usr/local/cuda-10.2/include/" 2>/dev/null || true
            bbnote "fix_cuda_symlinks: SDK CUDA completo copiado desde ${_cuda_inc}"
            break
        fi
    done

    # host_config.h VA SIEMPRE AL FINAL — el cp -rf anterior puede sobreescribirlo
    # con la versión sin parchear del staging. Se re-aplica aquí para garantizarlo.
    HOST_CFG="${IMAGE_ROOTFS}/usr/local/cuda-10.2/include/crt/host_config.h"
    if [ -f "${HOST_CFG}" ]; then
        sed -i 's/__GNUC__ > 8/__GNUC__ > 9/' "${HOST_CFG}"
        bbnote "fix_cuda_symlinks: host_config.h parcheado para GCC 9.x"
    fi

    bbnote "fix_cuda_symlinks: configuracion CUDA completa OK."
}

install_ollama_env() {
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
    install -d ${IMAGE_ROOTFS}/usr/local/bin
    install -m 0755 ${LLAMA_SCRIPT} \
        ${IMAGE_ROOTFS}/usr/local/bin/setup-llama.sh
}
