#!/usr/bin/env python3
"""
Script de benchmark para modelos TensorRT en Jetson Nano
Mide latencia, throughput y uso de recursos
"""

import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
import numpy as np
import time
import argparse
import psutil
import json
from pathlib import Path
from datetime import datetime


TRT_LOGGER = trt.Logger(trt.Logger.WARNING)


class TRTInference:
    """
    Clase para ejecutar inferencia con TensorRT
    """
    def __init__(self, engine_path):
        """
        Inicializa el motor de inferencia
        """
        print(f"📥 Cargando engine desde: {engine_path}")
        
        # Cargar engine
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(TRT_LOGGER)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        if self.engine is None:
            raise RuntimeError("Error cargando engine")
        
        self.context = self.engine.create_execution_context()
        
        # Obtener información de bindings
        self.input_shape = None
        self.output_shape = None
        self.bindings = []
        self.host_inputs = []
        self.host_outputs = []
        self.cuda_inputs = []
        self.cuda_outputs = []
        
        for binding in self.engine:
            shape = self.engine.get_binding_shape(binding)
            size = trt.volume(shape)
            dtype = trt.nptype(self.engine.get_binding_dtype(binding))
            
            # Allocar memoria
            host_mem = cuda.pagelocked_empty(size, dtype)
            cuda_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(cuda_mem))
            
            if self.engine.binding_is_input(binding):
                self.input_shape = shape
                self.host_inputs.append(host_mem)
                self.cuda_inputs.append(cuda_mem)
            else:
                self.output_shape = shape
                self.host_outputs.append(host_mem)
                self.cuda_outputs.append(cuda_mem)
        
        print(f"   ✓ Engine cargado exitosamente")
        print(f"   Input shape: {self.input_shape}")
        print(f"   Output shape: {self.output_shape}")
    
    def infer(self, input_data):
        """
        Ejecuta inferencia
        """
        # Copiar input a GPU
        np.copyto(self.host_inputs[0], input_data.ravel())
        cuda.memcpy_htod_async(self.cuda_inputs[0], self.host_inputs[0])
        
        # Ejecutar inferencia
        self.context.execute_v2(bindings=self.bindings)
        
        # Copiar output de GPU
        cuda.memcpy_dtoh_async(self.host_outputs[0], self.cuda_outputs[0])
        cuda.Context.synchronize()
        
        return self.host_outputs[0].reshape(self.output_shape)


def measure_latency(model, input_shape, num_iterations=100, warmup=10):
    """
    Mide la latencia de inferencia
    
    Returns:
        dict con estadísticas de latencia
    """
    print(f"\n⏱️  Midiendo latencia...")
    print(f"   Warmup iterations: {warmup}")
    print(f"   Benchmark iterations: {num_iterations}")
    
    # Crear input de prueba
    test_input = np.random.randn(*input_shape).astype(np.float32)
    
    # Warmup
    print(f"   Calentando GPU...")
    for _ in range(warmup):
        _ = model.infer(test_input)
    
    # Benchmark
    print(f"   Ejecutando benchmark...")
    latencies = []
    
    for i in range(num_iterations):
        start = time.time()
        _ = model.infer(test_input)
        end = time.time()
        latencies.append((end - start) * 1000)  # Convertir a ms
        
        if (i + 1) % 20 == 0:
            print(f"      Progreso: {i+1}/{num_iterations}")
    
    # Calcular estadísticas
    latencies = np.array(latencies)
    stats = {
        'mean_ms': float(np.mean(latencies)),
        'median_ms': float(np.median(latencies)),
        'std_ms': float(np.std(latencies)),
        'min_ms': float(np.min(latencies)),
        'max_ms': float(np.max(latencies)),
        'p95_ms': float(np.percentile(latencies, 95)),
        'p99_ms': float(np.percentile(latencies, 99)),
        'fps': float(1000 / np.mean(latencies))
    }
    
    return stats, latencies


def measure_memory():
    """
    Mide el uso de memoria del sistema
    """
    process = psutil.Process()
    memory_info = process.memory_info()
    
    # Memoria virtual
    virtual_memory = psutil.virtual_memory()
    
    return {
        'process_rss_mb': memory_info.rss / (1024 * 1024),  # Resident Set Size
        'process_vms_mb': memory_info.vms / (1024 * 1024),  # Virtual Memory Size
        'system_total_mb': virtual_memory.total / (1024 * 1024),
        'system_available_mb': virtual_memory.available / (1024 * 1024),
        'system_used_mb': virtual_memory.used / (1024 * 1024),
        'system_percent': virtual_memory.percent
    }


def measure_power():
    """
    Intenta medir el consumo de energía (específico de Jetson)
    """
    try:
        # En Jetson Nano, la información de poder está en:
        # /sys/bus/i2c/drivers/ina3221x/6-0040/iio:device0/
        power_file = Path('/sys/bus/i2c/drivers/ina3221x/6-0040/iio:device0/in_power0_input')
        
        if power_file.exists():
            with open(power_file, 'r') as f:
                power_mw = int(f.read().strip())
                return {'power_watts': power_mw / 1000.0}
    except:
        pass
    
    return {'power_watts': None}


def print_statistics(stats, memory_stats):
    """
    Imprime estadísticas de forma legible
    """
    print("\n" + "="*60)
    print("📊 RESULTADOS DEL BENCHMARK")
    print("="*60)
    
    # Latencia
    print(f"\n⏱️  LATENCIA:")
    print(f"   Media:     {stats['mean_ms']:.2f} ms")
    print(f"   Mediana:   {stats['median_ms']:.2f} ms")
    print(f"   Std Dev:   {stats['std_ms']:.2f} ms")
    print(f"   Min:       {stats['min_ms']:.2f} ms")
    print(f"   Max:       {stats['max_ms']:.2f} ms")
    print(f"   P95:       {stats['p95_ms']:.2f} ms")
    print(f"   P99:       {stats['p99_ms']:.2f} ms")
    
    # Throughput
    print(f"\n🚀 THROUGHPUT:")
    print(f"   FPS:       {stats['fps']:.2f}")
    
    # Memoria
    print(f"\n💾 USO DE MEMORIA:")
    print(f"   Proceso (RSS):     {memory_stats['process_rss_mb']:.2f} MB")
    print(f"   Sistema usado:     {memory_stats['system_used_mb']:.2f} MB")
    print(f"   Sistema total:     {memory_stats['system_total_mb']:.2f} MB")
    print(f"   Sistema disponible: {memory_stats['system_available_mb']:.2f} MB")
    print(f"   Uso del sistema:   {memory_stats['system_percent']:.1f}%")
    
    # Verificar restricciones del proyecto
    print(f"\n✅ VERIFICACIÓN DE RESTRICCIONES:")
    
    # Restricción 1: Inferencia < 3 segundos
    if stats['mean_ms'] < 3000:
        print(f"   ✓ Latencia: {stats['mean_ms']:.2f}ms < 3000ms (objetivo)")
    else:
        print(f"   ✗ Latencia: {stats['mean_ms']:.2f}ms > 3000ms (EXCEDE objetivo)")
    
    # Restricción 2: RAM < 3.5 GB
    if memory_stats['system_used_mb'] < 3500:
        print(f"   ✓ RAM: {memory_stats['system_used_mb']:.2f}MB < 3500MB (objetivo)")
    else:
        print(f"   ✗ RAM: {memory_stats['system_used_mb']:.2f}MB > 3500MB (EXCEDE objetivo)")


def save_results(results, output_path):
    """
    Guarda los resultados en formato JSON
    """
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Resultados guardados en: {output_path}")


def plot_latency_distribution(latencies, output_path):
    """
    Genera un histograma de la distribución de latencias
    """
    try:
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(10, 6))
        plt.hist(latencies, bins=50, edgecolor='black', alpha=0.7)
        plt.xlabel('Latencia (ms)')
        plt.ylabel('Frecuencia')
        plt.title('Distribución de Latencias')
        plt.axvline(np.mean(latencies), color='r', linestyle='--', 
                   label=f'Media: {np.mean(latencies):.2f}ms')
        plt.axvline(np.median(latencies), color='g', linestyle='--', 
                   label=f'Mediana: {np.median(latencies):.2f}ms')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path)
        print(f"   📈 Gráfico guardado en: {output_path}")
    except ImportError:
        print(f"   ⚠️  matplotlib no disponible, saltando gráfico")


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark de modelo TensorRT en Jetson Nano'
    )
    parser.add_argument(
        '--engine',
        type=str,
        required=True,
        help='Ruta al engine TensorRT (.engine o .trt)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='Número de iteraciones para benchmark (default: 100)'
    )
    parser.add_argument(
        '--warmup',
        type=int,
        default=10,
        help='Número de iteraciones de warmup (default: 10)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='benchmark_results.json',
        help='Archivo de salida para resultados (default: benchmark_results.json)'
    )
    parser.add_argument(
        '--plot',
        action='store_true',
        help='Generar gráfico de distribución de latencias'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 BENCHMARK TensorRT - Jetson Nano")
    print("="*60)
    print(f"\nEngine: {args.engine}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Cargar modelo
    model = TRTInference(args.engine)
    
    # Medir uso de memoria inicial
    memory_before = measure_memory()
    print(f"\n💾 Memoria inicial: {memory_before['system_used_mb']:.2f} MB")
    
    # Ejecutar benchmark de latencia
    stats, latencies = measure_latency(
        model,
        model.input_shape,
        args.iterations,
        args.warmup
    )
    
    # Medir uso de memoria final
    memory_after = measure_memory()
    
    # Medir consumo de energía (si está disponible)
    power_stats = measure_power()
    
    # Imprimir resultados
    print_statistics(stats, memory_after)
    
    if power_stats['power_watts'] is not None:
        print(f"\n⚡ CONSUMO DE ENERGÍA:")
        print(f"   Power: {power_stats['power_watts']:.2f} W")
    
    # Preparar resultados completos
    results = {
        'timestamp': datetime.now().isoformat(),
        'engine_path': args.engine,
        'input_shape': list(model.input_shape),
        'output_shape': list(model.output_shape),
        'latency': stats,
        'memory': memory_after,
        'power': power_stats,
        'config': {
            'iterations': args.iterations,
            'warmup': args.warmup
        }
    }
    
    # Guardar resultados
    save_results(results, args.output)
    
    # Generar gráfico (opcional)
    if args.plot:
        plot_output = Path(args.output).with_suffix('.png')
        plot_latency_distribution(latencies, plot_output)
    
    print("\n" + "="*60)
    print("✅ BENCHMARK COMPLETADO")
    print("="*60)


if __name__ == '__main__':
    main()
