### Paso a paso replicable para futuras imágenes, versión 2.0

Una vez que el bootloader de la QSPI ya fue flasheado con `--spi-only`, para las próximas imágenes solo hay que repetir los pasos de la SD.

**Parte 1 — Preparar la imagen en el host**

```bash
# Crear carpeta limpia y extraer
mkdir ~/Escritorio/jetson-flash-limpio
tar -xzf core-image-base-jetson-nano-devkit.tegraflash.tar.gz -C ~/Escritorio/jetson-flash-limpio/
cd ~/Escritorio/jetson-flash-limpio

# Verificar integridad del ext4
sudo e2fsck -n core-image-base.ext4
# Debe decir: clean

# Corregir tamano del ext4 (multiplo de 1MB)
SIZE=$(stat -c%s core-image-base.ext4)
REMAINDER=$((SIZE % 1048576))
if [ $REMAINDER -ne 0 ]; then
    PADDING=$((1048576 - REMAINDER))
    dd if=/dev/zero bs=1 count=$PADDING >> core-image-base.ext4
fi
echo "Residuo: $(($(stat -c%s core-image-base.ext4) % 1048576)) -- debe ser 0"
```

**Parte 2 — Flashear el bootloader en la QSPI (solo la primera vez)**

```bash
# 1. Cortocircuitar pines FC REC y GND del header J40 (pines 3 y 4, revision A02)
# 2. Conectar Micro-USB entre Jetson y laptop

# Verificar Recovery Mode
lsusb | grep -i nvidia
# Debe mostrar: ID 0955:7f21 NVIDIA Corp. APX

# Flashear solo la QSPI
sudo ./doflash.sh --spi-only

# Quitar el jumper al terminar
```

**Parte 3 — Generar y flashear la SD**

```bash
# Generar imagen completa de SD
sudo ./dosdcard.sh jetson-nano-sdcard.img
# Responder: yes

# Verificar integridad de la imagen
sudo losetup -P /dev/loop99 jetson-nano-sdcard.img
sudo e2fsck -n /dev/loop99p1
sudo losetup -d /dev/loop99
# Debe decir: clean

# Identificar la SD (RM=1 en lsblk)
lsblk -d | grep -v loop

# Desmontar si está montada
sudo umount -l /dev/sdb1 2>/dev/null

# Limpiar la tabla de particiones
sudo dd if=/dev/zero of=/dev/sdb bs=512 count=34 status=progress
sudo dd if=/dev/zero of=/dev/sdb bs=512 seek=121802718 count=34 status=progress
sync

# Verificar que el kernel ve 58GB
sudo fdisk -l /dev/sdb | grep "GiB"
# Debe mostrar: 58,08 GiB

# Flashear
sudo dd if=jetson-nano-sdcard.img of=/dev/sdb bs=4M status=progress conv=fsync
sync

# Reparar checksums
sudo umount -l /dev/sdb1 2>/dev/null
sudo e2fsck -y /dev/sdb1

# Verificar
sudo mount /dev/sdb1 /mnt/jetson-sd
ls /mnt/jetson-sd
sudo umount /mnt/jetson-sd
# Debe mostrar: bin boot etc home usr var
```

**Parte 4 — Arrancar la Jetson**

```bash
# 1. Insertar la SD en el slot microSD de la Jetson
# 2. Confirmar que NO hay jumper en pines FC REC y GND
# 3. Conectar monitor por HDMI
# 4. Conectar alimentacion por Micro-USB
# 5. Esperar 1-2 minutos

# En el monitor deberia aparecer:
# - Logo de NVIDIA
# - Mensajes de boot de Linux
# - Banner show-ip con la IP de eth0
# - Prompt de autologin de root

# Conectarse por SSH desde la laptop
ssh root@<IP_DE_LA_JETSON>
```