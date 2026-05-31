#!/usr/bin/env python3
"""
Sistema de Recomendaciones Agronómicas
Proyecto: Reconocimiento de Enfermedades en Banano
Genera recomendaciones basadas en enfermedad detectada y confianza
"""

import json
import sys
from datetime import datetime


# ============================================================================
# BASE DE CONOCIMIENTO AGRONÓMICO
# ============================================================================

DISEASE_DATABASE = {
    "Black Sigatoka": {
        "scientific_name": "Mycosphaerella fijiensis",
        "common_names": ["Sigatoka Negra", "Raya Negra"],
        
        "symptoms": [
            "Manchas alargadas de color marrón oscuro o negro",
            "Lesiones con halo amarillo alrededor",
            "Coalescencia de manchas en estados avanzados",
            "Necrosis del tejido foliar"
        ],
        
        "severity_levels": {
            "high": {  # confianza > 90%
                "level": "Alta",
                "description": "Infección confirmada de Sigatoka Negra con alta certeza",
                "urgency": "Inmediata",
                "economic_impact": "Alto - puede causar pérdidas del 30-50%",
                "treatment": "Control químico urgente combinado con manejo cultural",
                "recommendations": [
                    "Aplicar fungicida sistémico inmediatamente (triazoles o estrobirulinas)",
                    "Aumentar frecuencia de monitoreo a inspecciones semanales",
                    "Eliminar hojas severamente afectadas mediante deshoje sanitario",
                    "Mejorar drenaje del cultivo para reducir humedad",
                    "Registrar incidencia en sistema de trazabilidad fitosanitaria",
                    "Considerar rotación de fungicidas para evitar resistencia"
                ]
            },
            "medium": {  # confianza 75-90%
                "level": "Moderada",
                "description": "Probable infección de Sigatoka Negra - requiere confirmación",
                "urgency": "Alta",
                "economic_impact": "Moderado - riesgo de escalamiento",
                "treatment": "Control preventivo con monitoreo estrecho",
                "recommendations": [
                    "Confirmar diagnóstico con técnico agrónomo especializado",
                    "Iniciar aplicaciones preventivas con fungicidas protectantes",
                    "Monitorear evolución cada 3-5 días",
                    "Mejorar ventilación del cultivo",
                    "Preparar plan de control químico si confirma"
                ]
            },
            "low": {  # confianza < 75%
                "level": "Baja certeza",
                "description": "Posible Sigatoka Negra - imagen poco concluyente",
                "urgency": "Media",
                "economic_impact": "A determinar tras confirmación",
                "treatment": "Diagnóstico adicional requerido",
                "recommendations": [
                    "Tomar nuevas imágenes con mejor iluminación y enfoque",
                    "Consultar con agrónomo para inspección visual directa",
                    "Mantener programa de monitoreo preventivo rutinario",
                    "No tomar decisiones de control sin confirmación"
                ]
            }
        },
        
        "prevention": [
            "Deshoje sanitario regular de hojas afectadas",
            "Control de malezas para mejorar circulación de aire",
            "Aplicaciones preventivas de fungicidas en rotación",
            "Uso de variedades resistentes cuando esté disponible",
            "Manejo adecuado de densidad de siembra"
        ]
    },
    
    "Yellow Sigatoka": {
        "scientific_name": "Mycosphaerella musicola",
        "common_names": ["Sigatoka Amarilla", "Raya Amarilla"],
        
        "symptoms": [
            "Manchas inicialmente pequeñas de color amarillo",
            "Rayas pardas en el centro de las lesiones",
            "Áreas necróticas con halo amarillento",
            "Menos agresiva que Sigatoka Negra"
        ],
        
        "severity_levels": {
            "high": {
                "level": "Alta",
                "description": "Infección confirmada de Sigatoka Amarilla",
                "urgency": "Alta",
                "economic_impact": "Moderado - pérdidas del 10-20%",
                "treatment": "Control químico con fungicidas protectantes",
                "recommendations": [
                    "Aplicar fungicida protectante (mancozeb o clorotalonil)",
                    "Realizar deshoje de hojas afectadas",
                    "Mejorar nutrición del cultivo (K y microelementos)",
                    "Monitorear evolución cada 7-10 días",
                    "Evaluar densidad de plantas y mejorar aireación"
                ]
            },
            "medium": {
                "level": "Moderada",
                "description": "Probable infección de Sigatoka Amarilla",
                "urgency": "Media",
                "economic_impact": "Bajo a Moderado",
                "treatment": "Control preventivo",
                "recommendations": [
                    "Aplicar fungicida preventivo",
                    "Monitorear progresión de síntomas",
                    "Mejorar drenaje si es necesario",
                    "Verificar estado nutricional del cultivo"
                ]
            },
            "low": {
                "level": "Baja certeza",
                "description": "Posible Sigatoka Amarilla",
                "urgency": "Baja",
                "economic_impact": "A determinar",
                "treatment": "Diagnóstico adicional",
                "recommendations": [
                    "Mejorar calidad de imagen para nuevo diagnóstico",
                    "Continuar monitoreo preventivo rutinario"
                ]
            }
        },
        
        "prevention": [
            "Rotación de fungicidas para evitar resistencia",
            "Deshoje sanitario periódico",
            "Fertilización balanceada con énfasis en potasio",
            "Control de densidad poblacional"
        ]
    },
    
    "Panama": {
        "scientific_name": "Fusarium oxysporum f. sp. cubense",
        "common_names": ["Mal de Panamá", "Fusariosis", "Marchitez por Fusarium"],
        
        "symptoms": [
            "Amarillamiento progresivo de hojas más viejas",
            "Marchitez vascular irreversible",
            "Decoloración marrón-rojiza en pseudotallo al corte transversal",
            "Colapso completo de la planta"
        ],
        
        "severity_levels": {
            "high": {
                "level": "CRÍTICA",
                "description": "Infección confirmada de Fusarium - ENFERMEDAD CUARENTENARIA",
                "urgency": "URGENCIA MÁXIMA",
                "economic_impact": "Muy Alto - puede destruir plantación completa",
                "treatment": "Erradicación y cuarentena (NO HAY CURA QUÍMICA)",
                "recommendations": [
                    "⚠️  ALERTA FITOSANITARIA: NO EXISTE CURA QUÍMICA",
                    "ELIMINAR PLANTA INFECTADA INMEDIATAMENTE",
                    "Quemar o enterrar profundamente todo material vegetal afectado",
                    "Desinfectar herramientas con hipoclorito de sodio al 5% entre plantas",
                    "Establecer CUARENTENA estricta en área afectada (mínimo 10m de radio)",
                    "REPORTAR OBLIGATORIAMENTE a autoridades fitosanitarias (MAG)",
                    "NO replantar banano en el mismo sitio por mínimo 5 años",
                    "Considerar análisis de suelo antes de replantación",
                    "Evaluar cambio a variedades resistentes o cultivos alternativos"
                ]
            },
            "medium": {
                "level": "Alta sospecha",
                "description": "Sospecha fuerte de Fusarium - requiere confirmación urgente",
                "urgency": "URGENTE",
                "economic_impact": "Potencialmente devastador",
                "treatment": "Confirmación inmediata necesaria",
                "recommendations": [
                    "Confirmar diagnóstico URGENTEMENTE con análisis de laboratorio",
                    "Aislar planta sospechosa mientras se confirma",
                    "Preparar protocolo de bioseguridad",
                    "Contactar inmediatamente a extensionista agrícola",
                    "No movilizar material vegetal del área"
                ]
            },
            "low": {
                "level": "Sospecha",
                "description": "Posible Fusarium - requiere confirmación de laboratorio",
                "urgency": "Alta",
                "economic_impact": "A determinar - potencialmente muy alto",
                "treatment": "Diagnóstico profesional necesario",
                "recommendations": [
                    "Tomar muestras para análisis de laboratorio especializado",
                    "Monitorear planta diariamente",
                    "Preparar protocolo de bioseguridad preventivo",
                    "No tomar decisiones drásticas sin confirmación"
                ]
            }
        },
        
        "prevention": [
            "Usar EXCLUSIVAMENTE semilla certificada libre de patógeno",
            "Desinfección obligatoria de herramientas entre plantas",
            "Control estricto de movimiento de suelo y material vegetal",
            "Preferir variedades resistentes certificadas (ej: FHIA-25, FHIA-01, FHIA-23)",
            "Implementar barreras fitosanitarias en la finca"
        ]
    },
    
    "Healthy": {
        "scientific_name": "N/A",
        "common_names": ["Sana", "Sin enfermedad"],
        
        "symptoms": [
            "Color verde uniforme y vigoroso",
            "Ausencia de manchas o lesiones",
            "Textura foliar normal",
            "Crecimiento saludable"
        ],
        
        "severity_levels": {
            "high": {
                "level": "Ninguna",
                "description": "Hoja completamente sana - sin signos de enfermedad",
                "urgency": "Ninguna",
                "economic_impact": "Ninguno - estado óptimo",
                "treatment": "Mantenimiento preventivo",
                "recommendations": [
                    "Mantener programa de monitoreo preventivo rutinario",
                    "Continuar con prácticas de manejo integrado de plagas (MIP)",
                    "Registrar como punto de control en sistema de trazabilidad",
                    "Realizar inspecciones semanales para detección temprana",
                    "Mantener nutrición balanceada del cultivo",
                    "Asegurar condiciones óptimas de drenaje y aireación"
                ]
            },
            "medium": {
                "level": "Ninguna",
                "description": "Probablemente sana - sin síntomas evidentes",
                "urgency": "Ninguna",
                "economic_impact": "Ninguno",
                "treatment": "Prevención",
                "recommendations": [
                    "Continuar monitoreo rutinario",
                    "Mantener buenas prácticas agrícolas",
                    "Verificar que la planta reciba nutrición adecuada"
                ]
            },
            "low": {
                "level": "Incierta",
                "description": "Imagen poco clara - imposible confirmar estado",
                "urgency": "Baja",
                "economic_impact": "N/A",
                "treatment": "Validación adicional",
                "recommendations": [
                    "Tomar nueva imagen con mejor calidad (iluminación, enfoque)",
                    "Realizar inspección visual directa de la hoja",
                    "Continuar con programa de monitoreo preventivo"
                ]
            }
        },
        
        "prevention": [
            "Nutrición balanceada (N-P-K + microelementos)",
            "Sistema de drenaje eficiente",
            "Control preventivo integrado de plagas y enfermedades",
            "Monitoreo regular y sistemático",
            "Deshoje sanitario preventivo de hojas senescentes"
        ]
    }
}


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def get_severity_category(confidence):
    """Determina nivel de severidad según confianza"""
    if confidence >= 90:
        return 'high'
    elif confidence >= 75:
        return 'medium'
    else:
        return 'low'


def generate_recommendations(disease, confidence):
    """Genera recomendaciones basadas en enfermedad y confianza"""
    
    if disease not in DISEASE_DATABASE:
        return {
            "error": f"Enfermedad '{disease}' no reconocida",
            "available_diseases": list(DISEASE_DATABASE.keys())
        }
    
    disease_info = DISEASE_DATABASE[disease]
    severity_cat = get_severity_category(confidence)
    severity_info = disease_info["severity_levels"][severity_cat]
    
    return {
        "disease": disease,
        "scientific_name": disease_info["scientific_name"],
        "common_names": disease_info["common_names"],
        "confidence": round(confidence, 2),
        "severity": {
            "level": severity_info["level"],
            "description": severity_info["description"],
            "urgency": severity_info["urgency"],
            "economic_impact": severity_info["economic_impact"]
        },
        "symptoms": disease_info["symptoms"],
        "treatment": severity_info["treatment"],
        "recommendations": severity_info["recommendations"],
        "prevention": disease_info["prevention"],
        "timestamp": datetime.now().isoformat()
    }


def format_diagnosis_text(diagnosis):
    """Formatea diagnóstico en texto legible"""
    
    if not diagnosis.get("disease"):
        return f"❌ ERROR: {diagnosis.get('error', 'Error desconocido')}"
    
    text = f"""
╔══════════════════════════════════════════════════════════════════════╗
║           DIAGNÓSTICO FITOSANITARIO - HOJA DE BANANO                 ║
╚══════════════════════════════════════════════════════════════════════╝

📋 RESULTADO DE CLASIFICACIÓN
   Enfermedad: {diagnosis['disease']}
   Nombre científico: {diagnosis['scientific_name']}
   Confianza: {diagnosis['confidence']:.1f}%
   
🎯 SEVERIDAD
   Nivel: {diagnosis['severity']['level']}
   Urgencia: {diagnosis['severity']['urgency']}
   
📝 DESCRIPCIÓN
   {diagnosis['severity']['description']}

💰 IMPACTO ECONÓMICO
   {diagnosis['severity']['economic_impact']}

🔬 SÍNTOMAS CARACTERÍSTICOS
"""
    
    for i, symptom in enumerate(diagnosis['symptoms'], 1):
        text += f"   {i}. {symptom}\n"
    
    text += f"\n💊 TRATAMIENTO RECOMENDADO\n   {diagnosis['treatment']}\n"
    
    text += "\n📌 RECOMENDACIONES DE MANEJO\n"
    for i, rec in enumerate(diagnosis['recommendations'], 1):
        text += f"   {i}. {rec}\n"
    
    text += "\n🛡️  MEDIDAS PREVENTIVAS\n"
    for i, prev in enumerate(diagnosis['prevention'], 1):
        text += f"   {i}. {prev}\n"
    
    text += f"\n🕐 TIMESTAMP\n   {diagnosis['timestamp']}\n"
    text += "\n" + "═" * 70 + "\n"
    
    return text


def main():
    """Punto de entrada principal"""
    
    if len(sys.argv) < 2:
        print("""
USO:
   python recommendations.py <resultado.json>
   python recommendations.py test

EJEMPLOS:
   python recommendations.py resultado_inferencia.json
   python recommendations.py test
        """)
        sys.exit(0)
    
    # Modo test
    if sys.argv[1] == "test":
        print("\n🧪 MODO TEST\n")
        test_result = {
            "disease": "Black Sigatoka",
            "confidence": 94.5
        }
        
        diagnosis = generate_recommendations(
            test_result["disease"],
            test_result["confidence"]
        )
        print(format_diagnosis_text(diagnosis))
        sys.exit(0)
    
    # Leer resultado de inferencia
    try:
        if sys.argv[1] == "-":
            # Leer de stdin
            data = json.load(sys.stdin)
        else:
            # Leer de archivo
            with open(sys.argv[1], 'r') as f:
                data = json.load(f)
        
        # Extraer enfermedad y confianza
        if "prediction" in data:
            disease = data["prediction"]["disease"]
            confidence = data["prediction"]["confidence"]
        elif "disease" in data:
            disease = data["disease"]
            confidence = data["confidence"]
        else:
            print("❌ ERROR: Formato de JSON inválido")
            sys.exit(1)
        
        # Generar recomendaciones
        diagnosis = generate_recommendations(disease, confidence)
        
        # Mostrar en terminal
        print(format_diagnosis_text(diagnosis))
        
        # Output JSON si se solicita
        if len(sys.argv) > 2 and sys.argv[2] == "--json":
            print("\n" + "="*70)
            print("JSON OUTPUT:")
            print(json.dumps(diagnosis, indent=2, ensure_ascii=False))
        
    except FileNotFoundError:
        print(f"❌ ERROR: No se encuentra el archivo {sys.argv[1]}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: JSON inválido: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
