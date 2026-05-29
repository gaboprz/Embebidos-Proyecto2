SUMMARY = "Banano Web — Backend FastAPI para diagnóstico de enfermedades"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://banano_diagnostico.py \
    file://banano-web.service \
    file://static.tar.gz;unpack=0 \
    file://start-banano.sh \
"

S = "${WORKDIR}"

inherit systemd

SYSTEMD_SERVICE_${PN} = "banano-web.service"
SYSTEMD_AUTO_ENABLE_${PN} = "disable"

RDEPENDS_${PN} += " \
    python3 \
    python3-pip \
    python3-pillow \
"

do_install() {
    install -d ${D}/opt/banano-web/backend
    install -d ${D}/opt/banano-web/static

    install -m 0755 ${WORKDIR}/banano_diagnostico.py \
        ${D}/opt/banano-web/backend/banano_diagnostico.py

    tar --no-same-owner -xzf ${WORKDIR}/static.tar.gz \
        -C ${D}/opt/banano-web/

    install -d ${D}/usr/local/bin
    install -m 0755 ${WORKDIR}/start-banano.sh \
        ${D}/usr/local/bin/start-banano.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/banano-web.service \
        ${D}${systemd_system_unitdir}/banano-web.service
}

FILES_${PN} += " \
    /opt/banano-web/ \
    ${systemd_system_unitdir}/banano-web.service \
"
