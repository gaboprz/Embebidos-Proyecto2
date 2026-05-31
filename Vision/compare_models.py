#!/usr/bin/env python3
"""
Script para comparar diferentes versiones del modelo optimizado
Genera un reporte comparativo entre FP32, FP16 e INT8
"""

import json
import argparse
from pathlib import Path
from tabulate import tabulate
import matplotlib.pyplot as plt
import numpy as np


def load_benchmark_result(json_path):
    """
    Carga los resultados de un benchmark desde JSON
    """
    with open(json_path, 'r') as f:
        return json.load(f)


def compare_results(results_dict):
    """
    Compara múltiples resultados de benchmark
    
    Args:
        results_dict: Dict con formato {nombre: resultado_json}
    """
    print("\n" + "="*80)
    print("📊 COMPARACIÓN DE MODELOS OPTIMIZADOS")
    print("="*80)
    
    # Preparar datos para tabla
    table_data = []
    headers = ["Modelo", "Latencia (ms)", "FPS", "Tamaño (MB)", "Memoria (MB)", "Speedup"]
    
    # Baseline (FP32) para calcular speedup
    baseline_latency = None
    
    for name, result in results_dict.items():
        latency_mean = result['latency']['mean_ms']
        fps = result['latency']['fps']
        memory_mb = result['memory']['process_rss_mb']
        
        # Obtener tamaño del engine (estimado desde el path si está disponible)
        engine_path = Path(result.get('engine_path', ''))
        if engine_path.exists():
            size_mb = engine_path.stat().st_size / (1024 * 1024)
        else:
            size_mb = 0
        
        # Calcular speedup
        if baseline_latency is None:
            baseline_latency = latency_mean
            speedup = "1.0x (baseline)"
        else:
            speedup = f"{baseline_latency / latency_mean:.2f}x"
        
        table_data.append([
            name,
            f"{latency_mean:.2f}",
            f"{fps:.2f}",
            f"{size_mb:.2f}",
            f"{memory_mb:.2f}",
            speedup
        ])
    
    # Imprimir tabla
    print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Verificar restricciones
    print("\n" + "="*80)
    print("✅ VERIFICACIÓN DE RESTRICCIONES")
    print("="*80)
    
    for name, result in results_dict.items():
        latency_mean = result['latency']['mean_ms']
        memory_used = result['memory']['system_used_mb']
        
        print(f"\n{name}:")
        
        # Restricción 1: Latencia < 3000ms
        if latency_mean < 3000:
            print(f"  ✓ Latencia: {latency_mean:.2f}ms < 3000ms")
        else:
            print(f"  ✗ Latencia: {latency_mean:.2f}ms > 3000ms (FALLA)")
        
        # Restricción 2: RAM < 3500MB
        if memory_used < 3500:
            print(f"  ✓ Memoria: {memory_used:.2f}MB < 3500MB")
        else:
            print(f"  ✗ Memoria: {memory_used:.2f}MB > 3500MB (FALLA)")


def plot_comparison(results_dict, output_path='comparison.png'):
    """
    Genera gráficos comparativos
    """
    models = list(results_dict.keys())
    
    # Extraer métricas
    latencies = [r['latency']['mean_ms'] for r in results_dict.values()]
    fps_values = [r['latency']['fps'] for r in results_dict.values()]
    memory_values = [r['memory']['process_rss_mb'] for r in results_dict.values()]
    
    # Crear figura con subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Plot 1: Latencia
    axes[0].bar(models, latencies, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    axes[0].set_ylabel('Latencia (ms)')
    axes[0].set_title('Latencia de Inferencia')
    axes[0].axhline(y=3000, color='r', linestyle='--', label='Objetivo: 3000ms')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot 2: FPS
    axes[1].bar(models, fps_values, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    axes[1].set_ylabel('FPS')
    axes[1].set_title('Throughput (FPS)')
    axes[1].grid(True, alpha=0.3)
    
    # Plot 3: Memoria
    axes[2].bar(models, memory_values, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    axes[2].set_ylabel('Memoria (MB)')
    axes[2].set_title('Uso de Memoria')
    axes[2].axhline(y=3500, color='r', linestyle='--', label='Objetivo: 3500MB')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"\n📈 Gráfico comparativo guardado en: {output_path}")


def generate_report(results_dict, output_path='comparison_report.md'):
    """
    Genera un reporte en formato Markdown
    """
    report = []
    report.append("# 📊 Reporte Comparativo de Optimización\n")
    report.append(f"Fecha: {results_dict[list(results_dict.keys())[0]]['timestamp']}\n")
    report.append("\n## Resumen\n")
    
    # Tabla de comparación
    report.append("\n| Modelo | Latencia (ms) | FPS | Memoria (MB) | Cumple Objetivos |")
    report.append("|--------|---------------|-----|--------------|------------------|")
    
    for name, result in results_dict.items():
        latency = result['latency']['mean_ms']
        fps = result['latency']['fps']
        memory = result['memory']['system_used_mb']
        
        # Verificar objetivos
        meets_objectives = "✅" if (latency < 3000 and memory < 3500) else "❌"
        
        report.append(f"| {name} | {latency:.2f} | {fps:.2f} | {memory:.2f} | {meets_objectives} |")
    
    # Recomendación
    report.append("\n## 💡 Recomendación\n")
    
    # Encontrar el mejor modelo (balance entre velocidad y memoria)
    best_model = None
    best_score = float('inf')
    
    for name, result in results_dict.items():
        latency = result['latency']['mean_ms']
        memory = result['memory']['system_used_mb']
        
        # Score simple: priorizar latencia, pero penalizar si excede límites
        score = latency
        if latency > 3000:
            score *= 10  # Penalización fuerte
        if memory > 3500:
            score *= 5   # Penalización moderada
        
        if score < best_score:
            best_score = score
            best_model = name
    
    report.append(f"**Modelo recomendado:** {best_model}\n")
    
    # Análisis detallado
    report.append("\n## 📈 Análisis Detallado\n")
    
    for name, result in results_dict.items():
        report.append(f"\n### {name}\n")
        report.append(f"- **Latencia media:** {result['latency']['mean_ms']:.2f} ms")
        report.append(f"- **Latencia P95:** {result['latency']['p95_ms']:.2f} ms")
        report.append(f"- **Latencia P99:** {result['latency']['p99_ms']:.2f} ms")
        report.append(f"- **FPS:** {result['latency']['fps']:.2f}")
        report.append(f"- **Memoria del proceso:** {result['memory']['process_rss_mb']:.2f} MB")
        report.append(f"- **Memoria del sistema:** {result['memory']['system_used_mb']:.2f} MB\n")
    
    # Guardar reporte
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"\n📄 Reporte guardado en: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Comparar diferentes versiones del modelo optimizado'
    )
    parser.add_argument(
        '--results',
        type=str,
        nargs='+',
        required=True,
        help='Archivos JSON con resultados de benchmark (ej: fp32.json fp16.json int8.json)'
    )
    parser.add_argument(
        '--names',
        type=str,
        nargs='+',
        default=None,
        help='Nombres para cada modelo (default: usa nombres de archivo)'
    )
    parser.add_argument(
        '--plot',
        action='store_true',
        help='Generar gráficos comparativos'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generar reporte en Markdown'
    )
    
    args = parser.parse_args()
    
    # Cargar resultados
    results_dict = {}
    
    for i, result_path in enumerate(args.results):
        # Determinar nombre
        if args.names and i < len(args.names):
            name = args.names[i]
        else:
            name = Path(result_path).stem
        
        # Cargar resultado
        try:
            result = load_benchmark_result(result_path)
            results_dict[name] = result
        except Exception as e:
            print(f"⚠️  Error cargando {result_path}: {e}")
    
    if not results_dict:
        print("❌ No se pudieron cargar resultados")
        return
    
    # Comparar resultados
    compare_results(results_dict)
    
    # Generar gráfico si se solicitó
    if args.plot:
        try:
            plot_comparison(results_dict)
        except Exception as e:
            print(f"⚠️  Error generando gráfico: {e}")
    
    # Generar reporte si se solicitó
    if args.report:
        generate_report(results_dict)
    
    print("\n" + "="*80)
    print("✅ COMPARACIÓN COMPLETADA")
    print("="*80)


if __name__ == '__main__':
    main()
