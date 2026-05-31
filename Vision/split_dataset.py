import os
import shutil
from pathlib import Path
from sklearn.model_selection import train_test_split
import random

# Configuración
DATASET_ROOT = Path.home() / "Taller_Embebidos" / "Vision" / "dataset"
TRAIN_DIR = DATASET_ROOT / "train"
VAL_DIR = DATASET_ROOT / "val"
TEST_DIR = DATASET_ROOT / "test"

# Proporciones (ajustables)
TRAIN_RATIO = 0.70
VAL_RATIO = 0.20
TEST_RATIO = 0.10

# Semilla para reproducibilidad
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

def split_dataset():
    """Divide el dataset en train/val/test manteniendo la estructura de clases"""
    
    classes = [d for d in os.listdir(TRAIN_DIR) if os.path.isdir(TRAIN_DIR / d)]
    
    print(f" Clases encontradas: {classes}")
    print(f" Proporción: Train={TRAIN_RATIO*100}%, Val={VAL_RATIO*100}%, Test={TEST_RATIO*100}%")
    print("-" * 60)
    
    for class_name in classes:
        print(f"\n Procesando clase: {class_name}")
        
        # Obtener todas las imágenes de esta clase
        class_train_dir = TRAIN_DIR / class_name
        images = [f for f in os.listdir(class_train_dir) 
                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
        
        total_images = len(images)
        print(f"   Total de imágenes: {total_images}")
        
        if total_images < 3:
            print(f"    Muy pocas imágenes para dividir, dejando todas en train")
            continue
        
        # Mezclar aleatoriamente
        random.shuffle(images)
        
        # Calcular divisiones
        # Primero separar test
        train_val_images, test_images = train_test_split(
            images, 
            test_size=TEST_RATIO,
            random_state=RANDOM_SEED
        )
        
        # Luego separar val del resto
        val_ratio_adjusted = VAL_RATIO / (TRAIN_RATIO + VAL_RATIO)
        train_images, val_images = train_test_split(
            train_val_images,
            test_size=val_ratio_adjusted,
            random_state=RANDOM_SEED
        )
        
        print(f"   ✓ Train: {len(train_images)} imágenes")
        print(f"   ✓ Val:   {len(val_images)} imágenes")
        print(f"   ✓ Test:  {len(test_images)} imágenes")
        
        # Crear directorios de clase en val y test
        val_class_dir = VAL_DIR / class_name
        test_class_dir = TEST_DIR / class_name
        val_class_dir.mkdir(parents=True, exist_ok=True)
        test_class_dir.mkdir(parents=True, exist_ok=True)
        
        # Mover imágenes a val
        for img in val_images:
            src = class_train_dir / img
            dst = val_class_dir / img
            shutil.move(str(src), str(dst))
        
        # Mover imágenes a test
        for img in test_images:
            src = class_train_dir / img
            dst = test_class_dir / img
            shutil.move(str(src), str(dst))
    
    print("\n" + "=" * 60)
    print(" División completada exitosamente!")
    print("=" * 60)
    
    # Verificar resultado final
    print("\n Resumen final:")
    for split in ['train', 'val', 'test']:
        split_dir = DATASET_ROOT / split
        print(f"\n{split.upper()}:")
        for class_name in classes:
            class_dir = split_dir / class_name
            if class_dir.exists():
                count = len([f for f in os.listdir(class_dir) 
                           if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))])
                print(f"  - {class_name}: {count} imágenes")

if __name__ == "__main__":
    print("Iniciando división del dataset...")
    print("IMPORTANTE: Este script moverá archivos desde train/ a val/ y test/")
    print("   Si algo sale mal, tendrás que reorganizar manualmente.\n")
    
    response = input("¿Continuar? (s/n): ")
    if response.lower() in ['s', 'si', 'y', 'yes']:
        split_dataset()
    else:
        print("Operación cancelada")