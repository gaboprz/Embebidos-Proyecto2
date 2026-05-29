SUMMARY = "Vision AI Banana Disease Classifier con MobileNetV2"
DESCRIPTION = "Clasificador de enfermedades de banano usando MobileNetV2 + ONNX Runtime"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://vision-model-prebaked.tar.gz;unpack=0 \
    file://inference.py \
    file://setup-vision.sh \
    file://vision.service \
"

S = "${WORKDIR}"

inherit systemd

SYSTEMD_SERVICE_${PN} = "vision.service"
SYSTEMD_AUTO_ENABLE_${PN} = "enable"

# onnxruntime NO está en Yocto Dunfell — se instala vía setup-vision.sh en primer boot
RDEPENDS_${PN} += " \
    python3 \
    python3-pip \
    python3-numpy \
    python3-pillow \
"

do_install() {
    install -d ${D}/opt/vision/bin
    install -d ${D}/opt/vision/models

    # Extraer modelo, model_info.json e inference.py del tar.gz
    tar --no-same-owner -xzf ${WORKDIR}/vision-model-prebaked.tar.gz \
        -C ${D}/opt/vision/models/

    # Instalar NUESTRA inference.py en bin/ (sobreescribe si hay otra)
    install -m 0755 ${WORKDIR}/inference.py ${D}/opt/vision/bin/inference.py

    install -d ${D}/usr/local/bin
    install -m 0755 ${WORKDIR}/setup-vision.sh ${D}/usr/local/bin/setup-vision.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/vision.service \
        ${D}${systemd_system_unitdir}/vision.service
}

FILES_${PN} += " \
    /opt/vision/ \
    /usr/local/bin/setup-vision.sh \
    ${systemd_system_unitdir}/vision.service \
"

INSANE_SKIP_${PN} = "already-stripped"
