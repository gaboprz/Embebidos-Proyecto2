"""
Instrucciones para correr el script:
cd ~/Taller_Embebidos/Vison

# Por clase (agarra primera imagen)
python3 test_onnx.py Healthy
python3 test_onnx.py "Black Sigatoka"
python3 test_onnx.py Panama
python3 test_onnx.py "Yellow Sigatoka"

"""



import onnxruntime as ort
import numpy as np
from PIL import Image
import sys
import time
from pathlib import Path

# Clases del modelo
CLASS_NAMES = ['Black Sigatoka', 'Healthy', 'Panama', 'Yellow Sigatoka']

def preprocess_image(image_path, size=224):
    """
    Preprocesar imagen para inferencia
    Mismo preprocesamiento que en entrenamiento
    """
    # Cargar imagen
    img = Image.open(image_path).convert('RGB')
    
    # Resize
    img = img.resize((size, size), Image.BILINEAR)
    
    # A numpy array
    img_array = np.array(img).astype(np.float32)
    
    # Normalizar [0, 255] -> [0, 1]
    img_array = img_array / 255.0
    
    # Normalización ImageNet (como en entrenamiento)
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    img_array = (img_array - mean) / std
    
    # HWC -> CHW
    img_array = np.transpose(img_array, (2, 0, 1))
    
    # Agregar batch dimension
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array.astype(np.float32)


def load_onnx_model(onnx_path):
    """
    Cargar modelo ONNX con ONNX Runtime
    """
    print(f"Cargando modelo ONNX: {onnx_path}")
    
    # Crear sesión
    session = ort.InferenceSession(onnx_path)
    
    # Info del modelo
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    
    print(f"   Modelo cargado")
    print(f"   Input: {input_name}")
    print(f"   Output: {output_name}")
    
    return session, input_name, output_name


def inference_single_image(session, input_name, output_name, image_path):
    """
    Inferencia en una sola imagen
    """
    print(f"\n  Procesando: {image_path}")
    
    # Preprocesar
    start_preprocess = time.time()
    img_array = preprocess_image(image_path)
    preprocess_time = (time.time() - start_preprocess) * 1000
    
    # Inferencia
    start_inference = time.time()
    outputs = session.run([output_name], {input_name: img_array})
    inference_time = (time.time() - start_inference) * 1000
    
    # Procesar salida
    logits = outputs[0][0]
    
    # Softmax para probabilidades
    exp_logits = np.exp(logits - np.max(logits))
    probabilities = exp_logits / np.sum(exp_logits)
    
    # Predicción
    pred_idx = np.argmax(probabilities)
    pred_class = CLASS_NAMES[pred_idx]
    confidence = probabilities[pred_idx] * 100
    
    # Mostrar resultados
    print(f"\n RESULTADO:")
    print(f"   Enfermedad: {pred_class}")
    print(f"   Confianza: {confidence:.2f}%")
    
    print(f"\n Probabilidades:")
    for i, (class_name, prob) in enumerate(zip(CLASS_NAMES, probabilities)):
        print(f"   {class_name:20s}: {prob*100:6.2f}%")
    
    print(f"\n  Tiempos:")
    print(f"   Preprocesamiento: {preprocess_time:.2f} ms")
    print(f"   Inferencia: {inference_time:.2f} ms")
    print(f"   Total: {preprocess_time + inference_time:.2f} ms")
    
    return {
        'class': pred_class,
        'confidence': confidence,
        'probabilities': probabilities.tolist(),
        'preprocess_ms': preprocess_time,
        'inference_ms': inference_time,
        'total_ms': preprocess_time + inference_time
    }


def benchmark(session, input_name, output_name, iterations=100):
    """
    Ejecutar benchmark de rendimiento
    """
    print(f"\n BENCHMARK - {iterations} iteraciones")
    print("="*60)
    
    # Crear input dummy
    dummy_input = np.random.randn(1, 3, 224, 224).astype(np.float32)
    
    # Warm-up
    print("\n Warm-up (10 iteraciones)...")
    for _ in range(10):
        session.run([output_name], {input_name: dummy_input})
    
    # Benchmark real
    print(f"⚡ Ejecutando {iterations} inferencias...\n")
    
    times = []
    for i in range(iterations):
        start = time.time()
        session.run([output_name], {input_name: dummy_input})
        elapsed = (time.time() - start) * 1000  # ms
        times.append(elapsed)
        
        if (i + 1) % 20 == 0:
            print(f"   Completadas: {i+1}/{iterations}")
    
    # Estadísticas
    times = np.array(times)
    
    print("\n" + "="*60)
    print(" RESULTADOS DEL BENCHMARK")
    print("="*60)
    
    print(f"\n LATENCIA:")
    print(f"   Media:     {np.mean(times):.2f} ms")
    print(f"   Mediana:   {np.median(times):.2f} ms")
    print(f"   Mínima:    {np.min(times):.2f} ms")
    print(f"   Máxima:    {np.max(times):.2f} ms")
    print(f"   Std Dev:   {np.std(times):.2f} ms")
    print(f"   P95:       {np.percentile(times, 95):.2f} ms")
    print(f"   P99:       {np.percentile(times, 99):.2f} ms")
    
    print(f"\n THROUGHPUT:")
    print(f"   FPS promedio:  {1000/np.mean(times):.2f}")
    print(f"   FPS mediano:   {1000/np.median(times):.2f}")
    
    print(f"\n VERIFICACIÓN DE RESTRICCIONES:")
    avg_time = np.mean(times)
    if avg_time < 3000:
        print(f"    Latencia: {avg_time:.2f}ms < 3000ms (objetivo)")
    else:
        print(f"    Latencia: {avg_time:.2f}ms > 3000ms (objetivo)")
    
    print(f"\n NOTA:")
    print(f"   Esto es en CPU. En Jetson con TensorRT será ~5-10x más rápido")
    print(f"   Esperado en Jetson: ~50-200 ms")
    
    return {
        'mean': np.mean(times),
        'median': np.median(times),
        'min': np.min(times),
        'max': np.max(times),
        'std': np.std(times),
        'p95': np.percentile(times, 95),
        'p99': np.percentile(times, 99),
        'fps_mean': 1000/np.mean(times),
        'fps_median': 1000/np.median(times)
    }


def main():
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║              TEST DE INFERENCIA ONNX EN CPU                          ║
╚══════════════════════════════════════════════════════════════════════╝

USO:
   python test_onnx.py <imagen.jpg>           # Inferencia en una imagen
   python test_onnx.py benchmark               # Ejecutar benchmark
   python test_onnx.py benchmark --n 200       # Benchmark con 200 iters

EJEMPLOS:
   python test_onnx.py dataset/test/Healthy/img001.jpg
   python test_onnx.py dataset/test/Black_Sigatoka/img001.jpg
   python test_onnx.py benchmark
   python test_onnx.py benchmark --n 200
        """)
        sys.exit(0)
    
    # Modelo ONNX
    onnx_path = "weights/best_model.onnx"
    
    if not Path(onnx_path).exists():
        print(f" ERROR: No se encuentra {onnx_path}")
        print(f"   Ejecuta primero: python export_onnx.py")
        sys.exit(1)
    
    # Cargar modelo
    session, input_name, output_name = load_onnx_model(onnx_path)
    
    # Modo benchmark
    if sys.argv[1] == "benchmark":
        iterations = 100
        if len(sys.argv) > 2 and sys.argv[2] == "--n":
            iterations = int(sys.argv[3])
        
        benchmark(session, input_name, output_name, iterations)
    
    # Modo inferencia
    else:
        image_path = sys.argv[1]
        
        if not Path(image_path).exists():
            print(f" ERROR: No se encuentra {image_path}")
            sys.exit(1)
        
        result = inference_single_image(session, input_name, output_name, image_path)
        
        print("\n" + "="*60)
        print(" Inferencia completada exitosamente")
        print("="*60)


if __name__ == '__main__':
    main()
