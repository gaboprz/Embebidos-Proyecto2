#!/bin/bash
set -e

# Rutas de tus archivos
MODELO_ONNX="./weights/best_model.onnx"
INFERENCE_PY="./inference.py"

echo "=== Empaquetando modelo para Yocto ==="

# Verificar archivos
if [ ! -f "$MODELO_ONNX" ]; then
    echo "❌ ERROR: No se encuentra $MODELO_ONNX"
    exit 1
fi

if [ ! -f "$INFERENCE_PY" ]; then
    echo "❌ ERROR: No se encuentra $INFERENCE_PY"
    exit 1
fi

echo "✅ Archivo modelo encontrado: $MODELO_ONNX"
echo "✅ Archivo inference encontrado: $INFERENCE_PY"

# Crear estructura temporal
mkdir -p vision-model-package

# Copiar archivos
echo "📦 Copiando archivos..."
cp "$MODELO_ONNX" vision-model-package/banana_disease_classifier.onnx
cp "$INFERENCE_PY" vision-model-package/inference.py

# Crear metadata
cat > vision-model-package/model_info.json << 'INNER_EOF'
{
  "model_name": "banana_disease_classifier",
  "architecture": "MobileNetV2",
  "version": "1.0",
  "input_size": [224, 224],
  "num_classes": 4,
  "classes": [
    "Black Sigatoka",
    "Healthy",
    "Panama",
    "Yellow Sigatoka"
  ],
  "preprocessing": {
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225]
  }
}
INNER_EOF

# Crear tarball
echo "🗜️  Creando tarball..."
tar -czvf vision-model-prebaked.tar.gz -C vision-model-package .

# Mostrar resultado
SIZE=$(du -h vision-model-prebaked.tar.gz | cut -f1)
echo ""
echo "✅ Tarball creado exitosamente!"
echo "   📄 Archivo: vision-model-prebaked.tar.gz"
echo "   📏 Tamaño: $SIZE"
echo ""
echo "📋 Contenido:"
tar -tzf vision-model-prebaked.tar.gz

# Cleanup
rm -rf vision-model-package

echo ""
echo "🎯 SIGUIENTE PASO:"
echo "   Copiar archivos a Yocto con estos comandos:"
echo ""
echo "   cp vision-model-prebaked.tar.gz \\"
echo "      ~/Taller_Embebidos/yocto_jetson/meta-custom/recipes-ai/vision/files/"
echo ""
echo "   cp vision.service \\"
echo "      ~/Taller_Embebidos/yocto_jetson/meta-custom/recipes-ai/vision/files/"
echo ""
echo "   cp vision_1.0.bb \\"
echo "      ~/Taller_Embebidos/yocto_jetson/meta-custom/recipes-ai/vision/"
