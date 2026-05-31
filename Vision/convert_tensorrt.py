#!/usr/bin/env python3
"""
Script para convertir modelo ONNX a TensorRT
Incluye cuantización FP16 e INT8 para Jetson Nano
"""

import tensorrt as trt
import argparse
import numpy as np
from pathlib import Path
import pycuda.driver as cuda
import pycuda.autoinit


# Logger de TensorRT
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)


class Calibrator(trt.IInt8EntropyCalibrator2):
    """
    Calibrador para cuantización INT8
    Usa un dataset de calibración para determinar los rangos dinámicos
    """
    def __init__(self, calibration_data, cache_file="calibration.cache"):
        super().__init__()
        self.cache_file = cache_file
        self.data = calibration_data
        self.batch_size = 1
        self.current_index = 0
        
        # Reservar memoria en GPU
        self.device_input = cuda.mem_alloc(self.data[0].nbytes)
    
    def get_batch_size(self):
        return self.batch_size
    
    def get_batch(self, names):
        """
        Obtiene el siguiente batch de datos para calibración
        """
        if self.current_index < len(self.data):
            batch = self.data[self.current_index]
            cuda.memcpy_htod(self.device_input, batch)
            self.current_index += 1
            return [int(self.device_input)]
        return None
    
    def read_calibration_cache(self):
        """
        Lee cache de calibración si existe
        """
        if Path(self.cache_file).exists():
            with open(self.cache_file, 'rb') as f:
                return f.read()
        return None
    
    def write_calibration_cache(self, cache):
        """
        Guarda cache de calibración
        """
        with open(self.cache_file, 'wb') as f:
            f.write(cache)


def build_engine(onnx_path, engine_path, precision='fp16', calibration_data=None, 
                 max_batch_size=1, workspace_size=1<<30):
    """
    Construye un engine de TensorRT desde un modelo ONNX
    
    Args:
        onnx_path: Ruta al modelo ONNX
        engine_path: Ruta de salida del engine TensorRT
        precision: 'fp32', 'fp16', o 'int8'
        calibration_data: Datos para calibración INT8 (numpy arrays)
        max_batch_size: Tamaño máximo de batch
        workspace_size: Tamaño del workspace en bytes (default: 1GB)
    """
    print(f"\n🔧 Construyendo engine TensorRT...")
    print(f"   Precisión: {precision.upper()}")
    print(f"   Max batch size: {max_batch_size}")
    print(f"   Workspace: {workspace_size / (1<<30):.1f} GB")
    
    # Crear builder y network
    builder = trt.Builder(TRT_LOGGER)
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    )
    parser = trt.OnnxParser(network, TRT_LOGGER)
    
    # Parsear modelo ONNX
    print(f"\n📖 Parseando modelo ONNX...")
    with open(onnx_path, 'rb') as model:
        if not parser.parse(model.read()):
            print('❌ ERROR parseando ONNX:')
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            return None
    
    print(f"   ✓ Modelo parseado exitosamente")
    
    # Configurar builder
    config = builder.create_builder_config()
    config.max_workspace_size = workspace_size
    
    # Configurar precisión
    if precision == 'fp16':
        if builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
            print(f"   ✓ FP16 habilitado")
        else:
            print(f"   ⚠️  FP16 no soportado en esta plataforma, usando FP32")
    
    elif precision == 'int8':
        if builder.platform_has_fast_int8:
            config.set_flag(trt.BuilderFlag.INT8)
            
            # Configurar calibrador
            if calibration_data is not None:
                calibrator = Calibrator(calibration_data)
                config.int8_calibrator = calibrator
                print(f"   ✓ INT8 habilitado con calibración")
            else:
                print(f"   ⚠️  INT8 requiere datos de calibración")
                return None
        else:
            print(f"   ⚠️  INT8 no soportado en esta plataforma")
            return None
    
    # Construir engine
    print(f"\n🏗️  Construyendo engine (esto puede tardar varios minutos)...")
    engine = builder.build_engine(network, config)
    
    if engine is None:
        print("❌ Error construyendo engine")
        return None
    
    # Serializar y guardar engine
    print(f"\n💾 Guardando engine...")
    with open(engine_path, 'wb') as f:
        f.write(engine.serialize())
    
    print(f"   ✓ Engine guardado en: {engine_path}")
    
    return engine


def generate_calibration_data(num_samples=100, input_shape=(1, 3, 224, 224)):
    """
    Genera datos sintéticos para calibración INT8
    En producción, deberías usar imágenes reales de tu dataset
    """
    print(f"\n🎲 Generando datos de calibración sintéticos...")
    print(f"   ⚠️  IMPORTANTE: Para mejores resultados, usa imágenes reales")
    print(f"   Número de muestras: {num_samples}")
    
    calibration_data = []
    for i in range(num_samples):
        # Generar imagen random normalizada [0, 1]
        # En producción: cargar y preprocesar imágenes reales
        img = np.random.rand(*input_shape).astype(np.float32)
        calibration_data.append(img)
    
    return calibration_data


def load_calibration_images(image_dir, num_samples=100, input_size=224):
    """
    Carga imágenes reales para calibración INT8
    
    Args:
        image_dir: Directorio con imágenes
        num_samples: Número de imágenes a usar
        input_size: Tamaño de entrada del modelo
    """
    from PIL import Image
    import torchvision.transforms as transforms
    
    image_dir = Path(image_dir)
    image_files = list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.png'))
    
    if len(image_files) == 0:
        print(f"⚠️  No se encontraron imágenes en {image_dir}")
        return None
    
    print(f"\n📸 Cargando imágenes para calibración...")
    print(f"   Encontradas: {len(image_files)} imágenes")
    print(f"   Usando: {min(num_samples, len(image_files))} imágenes")
    
    # Transformaciones (ajustar según tu preprocesamiento)
    transform = transforms.Compose([
        transforms.Resize(input_size),
        transforms.CenterCrop(input_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225])
    ])
    
    calibration_data = []
    for i, img_path in enumerate(image_files[:num_samples]):
        try:
            img = Image.open(img_path).convert('RGB')
            img_tensor = transform(img).unsqueeze(0).numpy()
            calibration_data.append(img_tensor)
        except Exception as e:
            print(f"   ⚠️  Error cargando {img_path}: {e}")
    
    print(f"   ✓ Cargadas {len(calibration_data)} imágenes")
    return calibration_data


def get_file_size(file_path):
    """
    Obtiene el tamaño del archivo en MB
    """
    size_mb = Path(file_path).stat().st_size / (1024 * 1024)
    return size_mb


def main():
    parser = argparse.ArgumentParser(
        description='Convertir modelo ONNX a TensorRT para Jetson Nano'
    )
    parser.add_argument(
        '--onnx',
        type=str,
        required=True,
        help='Ruta al modelo ONNX'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Ruta de salida del engine (default: modelo_<precision>.engine)'
    )
    parser.add_argument(
        '--precision',
        type=str,
        choices=['fp32', 'fp16', 'int8'],
        default='fp16',
        help='Precisión del modelo (default: fp16)'
    )
    parser.add_argument(
        '--calibration-images',
        type=str,
        default=None,
        help='Directorio con imágenes para calibración INT8'
    )
    parser.add_argument(
        '--num-calibration-samples',
        type=int,
        default=100,
        help='Número de muestras para calibración INT8 (default: 100)'
    )
    parser.add_argument(
        '--workspace',
        type=int,
        default=1,
        help='Tamaño del workspace en GB (default: 1)'
    )
    parser.add_argument(
        '--input-size',
        type=int,
        default=224,
        help='Tamaño de entrada del modelo (default: 224)'
    )
    
    args = parser.parse_args()
    
    # Determinar nombre de salida
    if args.output is None:
        onnx_path = Path(args.onnx)
        args.output = str(onnx_path.with_suffix('')) + f'_{args.precision}.engine'
    
    print("="*60)
    print("🚀 CONVERSIÓN ONNX → TensorRT para Jetson Nano")
    print("="*60)
    print(f"\nModelo ONNX: {args.onnx}")
    print(f"Engine salida: {args.output}")
    
    # Preparar datos de calibración para INT8
    calibration_data = None
    if args.precision == 'int8':
        if args.calibration_images:
            calibration_data = load_calibration_images(
                args.calibration_images,
                args.num_calibration_samples,
                args.input_size
            )
        
        if calibration_data is None:
            print(f"\n⚠️  Generando datos sintéticos para calibración")
            print(f"    RECOMENDACIÓN: Usa --calibration-images con imágenes reales")
            calibration_data = generate_calibration_data(
                args.num_calibration_samples,
                (1, 3, args.input_size, args.input_size)
            )
    
    # Construir engine
    workspace_bytes = args.workspace * (1 << 30)  # Convertir GB a bytes
    engine = build_engine(
        args.onnx,
        args.output,
        args.precision,
        calibration_data,
        workspace_size=workspace_bytes
    )
    
    if engine is None:
        print("\n❌ Error construyendo engine")
        return
    
    # Mostrar tamaños
    onnx_size = get_file_size(args.onnx)
    engine_size = get_file_size(args.output)
    
    print("\n" + "="*60)
    print("✅ CONVERSIÓN COMPLETADA")
    print("="*60)
    print(f"\n📊 Comparación de tamaños:")
    print(f"   ONNX:   {onnx_size:.2f} MB")
    print(f"   Engine: {engine_size:.2f} MB")
    print(f"   Reducción: {((onnx_size - engine_size) / onnx_size * 100):.1f}%")
    
    print(f"\n💡 Próximos pasos:")
    print(f"   1. Ejecutar benchmark: python benchmark.py --engine {args.output}")
    print(f"   2. Probar inferencia en Jetson Nano")
    print()


if __name__ == '__main__':
    main()
