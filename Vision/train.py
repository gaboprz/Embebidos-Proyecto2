'''
Instruccion para correr el train:
python3 train.py
'''

import os
import copy
import torch
import wandb
import random
import numpy as np
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
import seaborn as sns

from collections import Counter

from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import (
    mobilenet_v2,
    MobileNet_V2_Weights
)

from torch.utils.data import (
    DataLoader,
    WeightedRandomSampler
)

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    matthews_corrcoef,
    confusion_matrix
)

# =========================================================
# W&B INIT
# =========================================================
run = wandb.init(
    entity="Proyecto1_Embebidos",
    project="banana-disease"
)

# =========================================================
# CONFIG
# =========================================================
def get_config():

    defaults = {
        "batch_size": 8,
        "num_epochs": 20,
        "learning_rate": 5e-4,
        "dropout": 0.5,
        "weight_decay": 4e-4,
        "scheduler_patience": 3,
        "early_stopping_patience": 5,
        "label_smoothing": 0.05,
        "unfreeze_blocks": 4,
        "seed": 42
    }

    cfg = dict(wandb.config) if wandb.run is not None else {}

    for k, v in defaults.items():
        cfg.setdefault(k, v)

    return cfg

config = get_config()

# =========================================================
# REPRODUCIBILITY
# =========================================================
torch.manual_seed(config["seed"])
np.random.seed(config["seed"])
random.seed(config["seed"])

# =========================================================
# PATHS
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TRAIN_DIR = os.path.join(BASE_DIR, "dataset", "train")
VAL_DIR   = os.path.join(BASE_DIR, "dataset", "val")
TEST_DIR  = os.path.join(BASE_DIR, "dataset", "test")

MODEL_SAVE_PATH = "weights/best_mobilenetv2.pt"

os.makedirs("weights", exist_ok=True)
os.makedirs("results", exist_ok=True)

# =========================================================
# DEVICE
# =========================================================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 60)
print("BANANA DISEASE CLASSIFICATION")
print("=" * 60)
print(f"Using device: {DEVICE}")

# =========================================================
# TRANSFORMS
# =========================================================
train_transform = transforms.Compose([

    transforms.Resize((256, 256)),

    transforms.RandomResizedCrop(
        224,
        scale=(0.7, 1.0)
    ),

    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),

    transforms.RandomRotation(20),

    transforms.RandomPerspective(
        distortion_scale=0.2,
        p=0.3
    ),

    transforms.RandomAffine(
        degrees=10,
        translate=(0.05, 0.05),
        scale=(0.95, 1.05)
    ),

    transforms.ColorJitter(
        brightness=0.3,
        contrast=0.3,
        saturation=0.3,
        hue=0.1
    ),

    transforms.GaussianBlur(kernel_size=3),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

val_transform = transforms.Compose([

    transforms.Resize((224, 224)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# =========================================================
# DATASETS
# =========================================================
print("\nLoading datasets...")

train_dataset = ImageFolder(
    TRAIN_DIR,
    transform=train_transform
)

val_dataset = ImageFolder(
    VAL_DIR,
    transform=val_transform
)

test_dataset = ImageFolder(
    TEST_DIR,
    transform=val_transform
)

class_names = train_dataset.classes
num_classes = len(class_names)

print(f"Classes: {class_names}")
print(f"Num classes: {num_classes}")

# =========================================================
# BALANCED SAMPLER
# =========================================================
train_counts = Counter(train_dataset.targets)

print("\nClass distribution:")
for cls, count in zip(class_names, train_counts.values()):
    print(f"{cls}: {count}")

class_sample_counts = [
    train_counts[i]
    for i in range(num_classes)
]

weights = 1.0 / torch.tensor(
    class_sample_counts,
    dtype=torch.float
)

sample_weights = [
    weights[t]
    for t in train_dataset.targets
]

sampler = WeightedRandomSampler(
    sample_weights,
    num_samples=len(sample_weights),
    replacement=True
)

# =========================================================
# DATALOADERS
# =========================================================
train_loader = DataLoader(
    train_dataset,
    batch_size=config["batch_size"],
    sampler=sampler,
    num_workers=2,
    pin_memory=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=config["batch_size"],
    shuffle=False,
    num_workers=2,
    pin_memory=True
)

test_loader = DataLoader(
    test_dataset,
    batch_size=config["batch_size"],
    shuffle=False,
    num_workers=2,
    pin_memory=True
)

dataloaders = {
    "train": train_loader,
    "val": val_loader
}

# =========================================================
# MODEL
# =========================================================
print("\nLoading MobileNetV2...")

model = mobilenet_v2(
    weights=MobileNet_V2_Weights.DEFAULT
)

# =========================================================
# FREEZE ALL
# =========================================================
for param in model.features.parameters():
    param.requires_grad = False

# =========================================================
# PARTIAL FINE-TUNING
# =========================================================
print(f"Unfreezing last {config['unfreeze_blocks']} blocks")

for block in model.features[-config["unfreeze_blocks"]:]:
    for param in block.parameters():
        param.requires_grad = True

# =========================================================
# CLASSIFIER
# =========================================================
model.classifier = nn.Sequential(
    nn.Dropout(config["dropout"]),
    nn.Linear(1280, num_classes)
)

model = model.to(DEVICE)

# =========================================================
# LOSS
# =========================================================
class_weights = torch.tensor([
    2.5,   # Black
    1.0,   # Healthy
    3.0,   # Panama
    4.0    # Yellow
]).to(DEVICE)

criterion = nn.CrossEntropyLoss(
    weight=class_weights,
    label_smoothing=config["label_smoothing"]
)

# =========================================================
# OPTIMIZER
# =========================================================
optimizer = optim.Adam(

    filter(
        lambda p: p.requires_grad,
        model.parameters()
    ),

    lr=config["learning_rate"],
    weight_decay=config["weight_decay"]
)

# =========================================================
# SCHEDULER
# =========================================================
scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode='min',
    factor=0.1,
    patience=config["scheduler_patience"]
)

# =========================================================
# TRAINING
# =========================================================
def train_model():

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    early_stop_counter = 0

    for epoch in range(config["num_epochs"]):

        print("\n" + "=" * 60)
        print(f"Epoch {epoch+1}/{config['num_epochs']}")
        print("=" * 60)

        for phase in ["train", "val"]:

            if phase == "train":
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloaders[phase]:

                inputs = inputs.to(DEVICE)
                labels = labels.to(DEVICE)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == "train"):

                    outputs = model(inputs)

                    _, preds = torch.max(outputs, 1)

                    loss = criterion(outputs, labels)

                    if phase == "train":
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)

                running_corrects += torch.sum(
                    preds == labels.data
                )

            epoch_loss = (
                running_loss /
                len(dataloaders[phase].dataset)
            )

            epoch_acc = (
                running_corrects.double() /
                len(dataloaders[phase].dataset)
            )

            print(
                f"{phase.upper()} "
                f"Loss: {epoch_loss:.4f} | "
                f"Acc: {epoch_acc:.4f}"
            )

            wandb.log({
                f"{phase}_loss": epoch_loss,
                f"{phase}_accuracy": epoch_acc.item(),
                "learning_rate": optimizer.param_groups[0]["lr"],
                "epoch": epoch
            })

            # =============================================
            # VALIDATION
            # =============================================
            if phase == "val":

                scheduler.step(epoch_loss)

                if epoch_acc > best_acc:

                    best_acc = epoch_acc

                    best_model_wts = copy.deepcopy(
                        model.state_dict()
                    )

                    torch.save(
                        model.state_dict(),
                        MODEL_SAVE_PATH
                    )

                    print("✅ Best model updated")

                    early_stop_counter = 0

                else:
                    early_stop_counter += 1

        # =============================================
        # EARLY STOPPING
        # =============================================
        if early_stop_counter >= config["early_stopping_patience"]:

            print("\n⛔ Early stopping triggered")
            break

    model.load_state_dict(best_model_wts)

    print(f"\n🏆 Best Validation Accuracy: {best_acc:.4f}")

    return model

# =========================================================
# EVALUATION
# =========================================================
def evaluate_model():

    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():

        for inputs, labels in test_loader:

            inputs = inputs.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(inputs)

            _, preds = torch.max(outputs, 1)

            all_preds.extend(
                preds.cpu().numpy()
            )

            all_labels.extend(
                labels.cpu().numpy()
            )

    # =====================================================
    # METRICS
    # =====================================================
    accuracy = accuracy_score(
        all_labels,
        all_preds
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            all_labels,
            all_preds,
            average='weighted'
        )
    )

    mcc = matthews_corrcoef(
        all_labels,
        all_preds
    )

    report = classification_report(
        all_labels,
        all_preds,
        target_names=class_names
    )

    # =====================================================
    # CONFUSION MATRIX
    # =====================================================
    cm = confusion_matrix(
        all_labels,
        all_preds
    )

    plt.figure(figsize=(8, 6))

    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=class_names,
        yticklabels=class_names
    )

    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title("Confusion Matrix")

    plt.tight_layout()

    confusion_path = "results/confusion_matrix.png"

    plt.savefig(confusion_path)

    plt.close()

    # =====================================================
    # SAVE REPORT
    # =====================================================
    with open(
        "results/classification_report.txt",
        "w"
    ) as f:
        f.write(report)

    # =====================================================
    # LOG TO W&B
    # =====================================================
    wandb.log({

        "test_accuracy": accuracy,
        "test_precision": precision,
        "test_recall": recall,
        "test_f1": f1,
        "test_mcc": mcc,

        "confusion_matrix": wandb.Image(
            confusion_path
        )
    })

    # =====================================================
    # PRINT RESULTS
    # =====================================================
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    print(f"\nAccuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1-Score : {f1:.4f}")
    print(f"MCC      : {mcc:.4f}")

    print("\nClassification Report:\n")
    print(report)

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":

    trained_model = train_model()

    evaluate_model()

    torch.save(
        trained_model.state_dict(),
        "weights/final_mobilenetv2.pt"
    )

    wandb.finish()

    print("\n✅ Training complete!")