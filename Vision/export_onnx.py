import os
import torch
import torch.nn as nn
from torchvision import models
import onnx

# =========================
# Cargar modelo
# =========================

print("🔄 Cargando modelo...")

checkpoint = torch.load(
    'weights/best_mobilenetv2.pt',
    map_location='cpu'
)

# MobileNetV2
model = models.mobilenet_v2(weights=None)

# Ajustar clasificador
model.classifier[1] = nn.Linear(model.last_channel, 4)

# Cargar pesos
model.load_state_dict(checkpoint)

# Modo evaluación
model.eval()
model.cpu()

print("✅ Modelo cargado")

# =========================
# Verificar parámetros
# =========================

total_params = sum(p.numel() for p in model.parameters())
print(f"📊 Parámetros: {total_params:,}")

# =========================
# Exportar a ONNX
# =========================

print("\n🔄 Exportando a ONNX...")

dummy_input = torch.randn(1, 3, 224, 224).cpu()

torch.onnx.export(
    model,
    dummy_input,
    'weights/best_model.onnx',

    export_params=True,
    opset_version=13,          # ← Mejor que 11
    do_constant_folding=True,

    input_names=['input'],
    output_names=['output'],

    # IMPORTANTE:
    # quitar dynamic_axes para Jetson/TensorRT
    # dynamic_axes=None

    training=torch.onnx.TrainingMode.EVAL,

    verbose=False
)

print("✅ Exportado")

# =========================
# Verificar tamaño
# =========================

size_mb = os.path.getsize(
    'weights/best_model.onnx'
) / (1024 * 1024)

print(f"📏 Tamaño ONNX: {size_mb:.2f} MB")

# =========================
# Verificar modelo ONNX
# =========================

onnx_model = onnx.load('weights/best_model.onnx')

onnx.checker.check_model(onnx_model)

print("✅ Modelo ONNX válido")

# =========================
# Mostrar opset
# =========================

print(
    f"📦 Opset: "
    f"{onnx_model.opset_import[0].version}"
)