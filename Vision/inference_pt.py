#!/usr/bin/env python3
"""
Inferencia con modelo PyTorch (.pt)
"""
import sys
import json
import numpy as np
from PIL import Image
import torch
import torchvision.models as models

# Clases
CLASS_NAMES = ['Black Sigatoka', 'Healthy', 'Panama', 'Yellow Sigatoka']

# Ruta del modelo
MODEL_PATH = "./weights/best_mobilenetv2.pt"  # Modelo de pesos entrenado
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_model():
    """Cargar modelo PyTorch"""
    model = models.mobilenet_v2(pretrained=False)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, 4)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE)) # Se carga el modelo
    model = model.float()
    model.eval()
    model.to(DEVICE)
    return model

def preprocess_image(image_path, size=224):
    """Preprocesar imagen"""
    img = Image.open(image_path).convert('RGB')
    img = img.resize((size, size), Image.BILINEAR)
    
    img_array = np.array(img).astype(np.float32) / 255.0
    
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    img_array = (img_array - mean) / std
    
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)
    
    return torch.from_numpy(img_array).float().to(DEVICE)

def predict(image_path, model):
    """Predicción"""
    input_tensor = preprocess_image(image_path)
    
    with torch.no_grad():
        output = model(input_tensor)
    
    logits = output.cpu().numpy()[0]
    
    # Softmax
    exp_logits = np.exp(logits - np.max(logits))
    probabilities = exp_logits / np.sum(exp_logits)
    
    # Predicción
    pred_idx = np.argmax(probabilities)
    pred_class = CLASS_NAMES[pred_idx]
    confidence = probabilities[pred_idx] * 100
    
    return {
        "success": True,
        "prediction": {
            "disease": pred_class,
            "confidence": float(confidence),
            "is_certain": bool(confidence >= 75)
        },
        "probabilities": {
            CLASS_NAMES[i]: float(probabilities[i] * 100)
            for i in range(len(CLASS_NAMES))
        },
        "engine": "pytorch",
        "device": str(DEVICE)
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "No image path provided"
        }))
        sys.exit(1)
    
    try:
        print(f"Cargando modelo desde {MODEL_PATH}...", file=sys.stderr)
        model = load_model()
        print(f"Ejecutando inferencia en {DEVICE}...", file=sys.stderr)
        result = predict(sys.argv[1], model)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)
