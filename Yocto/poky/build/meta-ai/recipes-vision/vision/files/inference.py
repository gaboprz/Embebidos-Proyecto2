#!/usr/bin/env python3
"""
Banana Disease Classifier — MobileNetV2 + ONNX Runtime
Uso: python3 inference.py <imagen.jpg> [--model /ruta/modelo.onnx]
Salida: JSON con enfermedad, confianza y scores de todas las clases
"""

import sys
import json
import argparse
import numpy as np
from PIL import Image

# Orden de clases según cómo fue entrenado el modelo
# IMPORTANTE: debe coincidir con el orden del dataset de entrenamiento
CLASSES = [
    "Black Sigatoka",
    "Healthy",
    "Panama Disease",
    "Yellow Sigatoka"
]

# Normalización ImageNet estándar (usada en MobileNetV2 preentrenado)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

MODEL_PATH = "/opt/vision/models/banana_disease_classifier.onnx"


def preprocess(image_path: str) -> np.ndarray:
    """
    Preprocesa imagen para MobileNetV2:
    1. Abrir y convertir a RGB (elimina canal alpha si existe)
    2. Redimensionar a 224×224 (tamaño de entrada del modelo)
    3. Normalizar con media/std de ImageNet
    4. Convertir a formato NCHW (batch, canales, alto, ancho)
    """
    img = Image.open(image_path).convert("RGB")
    img = img.resize((224, 224), Image.BILINEAR)

    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD

    # HWC → CHW → NCHW
    arr = arr.transpose(2, 0, 1)
    arr = np.expand_dims(arr, axis=0)
    return arr


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x))
    return e / e.sum()


def predict(image_path: str, model_path: str = MODEL_PATH) -> dict:
    """
    Corre inferencia sobre una imagen.
    Retorna dict con clase, confianza y scores de todas las clases.
    """
    import onnxruntime as ort

    # Cargar sesión ONNX (se puede reutilizar entre llamadas si se importa)
    session = ort.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"]
    )

    input_name  = session.get_inputs()[0].name
    input_data  = preprocess(image_path)

    # Inferencia
    outputs     = session.run(None, {input_name: input_data})
    logits      = outputs[0][0]           # shape: (4,)
    probs       = softmax(logits)

    class_idx   = int(np.argmax(probs))
    confidence  = float(probs[class_idx])

    return {
        "disease":    CLASSES[class_idx],
        "confidence": round(confidence, 4),
        "all_scores": {
            cls: round(float(p), 4)
            for cls, p in zip(CLASSES, probs)
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Banana Disease Classifier"
    )
    parser.add_argument("image",  help="Ruta a la imagen")
    parser.add_argument(
        "--model",
        default=MODEL_PATH,
        help="Ruta al modelo ONNX"
    )
    args = parser.parse_args()

    try:
        result = predict(args.image, args.model)
        print(json.dumps(result, ensure_ascii=False))
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Inferencia fallida: {str(e)}"}))
        sys.exit(1)
