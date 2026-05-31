#!/usr/bin/env python3
'''Instruscion para correr:

# Healthy
python3 test_inference.py "Healthy"

# Black Sigatoka
python3 test_inference.py "Black Sigatoka"

# Panama
python3 test_inference.py "Panama"

# Yellow Sigatoka
python3 test_inference.py "Yellow Sigatoka"

'''



import sys
import subprocess
import os
import glob

if len(sys.argv) < 2:
    print("Uso: python3 test_inference.py <clase>")
    print("Clases disponibles: Healthy, 'Black Sigatoka', Panama, 'Yellow Sigatoka'")
    sys.exit(1)

clase = sys.argv[1]
carpeta = f"dataset/test/{clase}/"

# Buscar primer imagen
imagenes = glob.glob(f"{carpeta}*.jpg")

if not imagenes:
    print(f"No hay imágenes en {carpeta}")
    sys.exit(1)

primera_imagen = imagenes[0]
print(f"Usando: {primera_imagen}")

# Ejecutar inferencia
subprocess.run(["python3", "inference_pt.py", primera_imagen])
