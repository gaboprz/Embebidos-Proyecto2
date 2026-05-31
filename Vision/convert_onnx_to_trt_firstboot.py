#!/usr/bin/env python3
"""
Conversión automática ONNX → TensorRT en primer boot
"""

import os
import sys

MODEL_DIR = "/opt/banana-disease/models"
ONNX_PATH = f"{MODEL_DIR}/best_model.onnx"
TRT_PATH = f"{MODEL_DIR}/best_model_fp16.trt"
MARKER_FILE = f"{MODEL_DIR}/.converted"

def main():
    print("=" * 70)
    print("CONVERSIÓN AUTOMÁTICA ONNX → TensorRT")
    print("=" * 70)
    
    # Verificar si ya se convirtió
    if os.path.exists(MARKER_FILE):
        print("✅ Modelo TensorRT ya existe. Saliendo.")
        sys.exit(0)
    
    if os.path.exists(TRT_PATH):
        print("✅ Archivo .trt ya existe. Marcando como convertido.")
        open(MARKER_FILE, 'w').close()
        sys.exit(0)
    
    # Verificar ONNX
    if not os.path.exists(ONNX_PATH):
        print(f"❌ ERROR: No se encuentra {ONNX_PATH}")
        sys.exit(1)
    
    print(f"\n📂 Modelo ONNX encontrado: {ONNX_PATH}")
    print(f"🔨 Iniciando conversión a TensorRT...")
    print(f"⏰ Esto tomará 3-5 minutos...\n")
    
    # Importar aquí para dar tiempo al sistema
    try:
        import tensorrt as trt
        import pycuda.driver as cuda
        import pycuda.autoinit
    except ImportError as e:
        print(f"❌ ERROR: No se puede importar TensorRT: {e}")
        sys.exit(1)
    
    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
    
    # Construir engine
    builder = trt.Builder(TRT_LOGGER)
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    )
    parser = trt.OnnxParser(network, TRT_LOGGER)
    
    # Parsear ONNX
    print("🔍 Parseando ONNX...")
    with open(ONNX_PATH, 'rb') as model:
        if not parser.parse(model.read()):
            print('❌ ERROR: No se pudo parsear ONNX')
            for error in range(parser.num_errors):
                print(f"   {parser.get_error(error)}")
            sys.exit(1)
    
    print("✅ ONNX parseado correctamente")
    
    # Configurar builder
    config = builder.create_builder_config()
    config.max_workspace_size = 1 << 30  # 1GB
    
    # FP16
    if builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)
        print("✅ Usando modo FP16")
    
    # Construir engine
    print("\n🔨 Construyendo engine TensorRT...")
    print("   (Esto es normal que tome varios minutos)\n")
    
    engine = builder.build_engine(network, config)
    
    if engine is None:
        print("❌ ERROR: No se pudo construir engine")
        sys.exit(1)
    
    # Guardar
    print(f"\n💾 Guardando engine en {TRT_PATH}...")
    with open(TRT_PATH, "wb") as f:
        f.write(engine.serialize())
    
    # Marcar como completado
    open(MARKER_FILE, 'w').close()
    
    print("\n" + "=" * 70)
    print("✅ CONVERSIÓN COMPLETADA")
    print("=" * 70)
    print(f"\nArchivo generado: {TRT_PATH}")
    print("El sistema está listo para inferencia.\n")

if __name__ == "__main__":
    main()
