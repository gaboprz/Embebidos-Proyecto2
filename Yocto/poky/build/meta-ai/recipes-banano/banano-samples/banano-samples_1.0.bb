SUMMARY = "Imágenes de muestra de enfermedades de banano"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://black_sigatoka_01.jpg \
    file://yellow_sigatoka_01.jpg \
    file://panama_disease_01.jpg \
    file://healthy_01.jpg \
"

S = "${WORKDIR}"

do_install() {
    install -d ${D}/opt/vision/samples
    install -m 0644 ${WORKDIR}/black_sigatoka_01.jpg        ${D}/opt/vision/samples/
    install -m 0644 ${WORKDIR}/yellow_sigatoka_01.jpg       ${D}/opt/vision/samples/
    install -m 0644 ${WORKDIR}/panama_disease_01.jpg        ${D}/opt/vision/samples/
    install -m 0644 ${WORKDIR}/healthy_01.jpg               ${D}/opt/vision/samples/
}

FILES_${PN} = "/opt/vision/samples/"
