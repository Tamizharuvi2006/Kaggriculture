"""Train the Step 4 opponent classifier from validated Step 3G labels."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.models.opponent_classifier import OpponentClassifier
from apex_next.ml_engine.training.label_opponents import CLASS_NAMES


ML_ENGINE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ML_ENGINE_DIR / "data"
CURRENT_DATA_DIR = DATA_DIR / "current" / "step3g_targeted_1000"
DEFAULT_DATASET = CURRENT_DATA_DIR / "expert_demos_step3g_targeted_1000.npz"
DEFAULT_LABELS = CURRENT_DATA_DIR / "opponent_labels_step3g_targeted_1000.npz"
DEFAULT_CHECKPOINT = ML_ENGINE_DIR / "checkpoints" / "opponent_classifier" / "opponent_classifier.pt"
DEFAULT_REPORT = ML_ENGINE_DIR / "evaluation" / "step4_classifier" / "opponent_classifier_report.json"


def train_opponent_classifier(
    dataset_path: Path = DEFAULT_DATASET,
    labels_path: Path = DEFAULT_LABELS,
    checkpoint_path: Path = DEFAULT_CHECKPOINT,
    report_path: Path = DEFAULT_REPORT,
    epochs: int = 100,
    lr: float = 1e-3,
    batch_size: int = 8192,
    seed: int = 4104,
    require_cuda: bool = True,
) -> dict[str, Any]:
    """Train the 24->64->32->5 classifier and write checkpoint/report artifacts."""

    _seed_everything(seed)
    started = time.perf_counter()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if require_cuda and device.type != "cuda":
        raise RuntimeError("CUDA is required for Step 4 training but torch.cuda.is_available() is False")

    dataset = _load_dataset(dataset_path, labels_path)
    train_episode_ids, val_episode_ids, train_idx, val_idx = _episode_stratified_transition_split(
        transition_labels=dataset["labels"],
        transition_episode_ids=dataset["transition_episode_ids"],
        episode_ids=dataset["episode_ids"],
        episode_labels=dataset["episode_labels"],
        val_ratio=0.2,
        seed=seed,
    )

    x_train_np = dataset["opponent_features"][train_idx]
    y_train_np = dataset["labels"][train_idx]
    x_val_np = dataset["opponent_features"][val_idx]
    y_val_np = dataset["labels"][val_idx]

    mean = x_train_np.mean(axis=0, dtype=np.float64).astype(np.float32)
    std = x_train_np.std(axis=0, dtype=np.float64).astype(np.float32)
    std[std < 1e-6] = np.float32(1.0)

    x_train = torch.from_numpy((x_train_np - mean) / std).to(device=device, dtype=torch.float32)
    y_train = torch.from_numpy(y_train_np).to(device=device, dtype=torch.long)
    x_val = torch.from_numpy((x_val_np - mean) / std).to(device=device, dtype=torch.float32)
    y_val = torch.from_numpy(y_val_np).to(device=device, dtype=torch.long)

    model = OpponentClassifier().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    device_checks = {
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "selected_device": str(device),
        "model_device": str(next(model.parameters()).device),
        "x_train_device": str(x_train.device),
        "y_train_device": str(y_train.device),
        "x_val_device": str(x_val.device),
        "y_val_device": str(y_val.device),
    }
    if require_cuda and not all(value.startswith("cuda") for key, value in device_checks.items() if key.endswith("_device")):
        raise RuntimeError(f"Step 4 tensors/model are not all on CUDA: {device_checks}")

    history: list[dict[str, float]] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_val_accuracy = -1.0
    best_epoch = -1

    for epoch in range(1, epochs + 1):
        model.train()
        permutation = torch.randperm(x_train.shape[0], device=device)
        train_loss_total = 0.0
        train_correct = 0

        for start in range(0, x_train.shape[0], batch_size):
            batch_idx = permutation[start : start + batch_size]
            xb = x_train[batch_idx]
            yb = y_train[batch_idx]
            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()

            train_loss_total += float(loss.detach().item()) * int(yb.shape[0])
            train_correct += int((logits.argmax(dim=1) == yb).sum().item())

        val_loss, val_accuracy, _ = _evaluate(model, criterion, x_val, y_val, batch_size)
        train_loss = train_loss_total / int(x_train.shape[0])
        train_accuracy = train_correct / int(x_train.shape[0])
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": train_loss,
                "train_accuracy": train_accuracy,
                "val_loss": val_loss,
                "val_accuracy": val_accuracy,
            }
        )
        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    train_loss, train_accuracy, _ = _evaluate(model, criterion, x_train, y_train, batch_size)
    val_loss, val_accuracy, predictions = _evaluate(model, criterion, x_val, y_val, batch_size)
    confusion = _confusion_matrix(y_val.detach().cpu().numpy(), predictions, len(CLASS_NAMES))
    per_class = _per_class_metrics(confusion)

    report = {
        "status": "PASS" if val_accuracy >= 0.70 else "FAIL",
        "step": "STEP 4 - Opponent Classifier",
        "source_dataset": str(dataset_path),
        "source_labels": str(labels_path),
        "checkpoint_path": str(checkpoint_path),
        "epochs": epochs,
        "best_epoch": best_epoch,
        "batch_size": batch_size,
        "learning_rate": lr,
        "optimizer": "Adam",
        "loss": "CrossEntropyLoss",
        "architecture": "24 -> 64 -> 32 -> 5",
        "train_size": int(train_idx.shape[0]),
        "validation_size": int(val_idx.shape[0]),
        "train_episodes": int(train_episode_ids.shape[0]),
        "validation_episodes": int(val_episode_ids.shape[0]),
        "class_mapping": {str(index): name for index, name in enumerate(CLASS_NAMES)},
        "class_distribution": {
            "all": _class_distribution(dataset["labels"]),
            "train": _class_distribution(y_train_np),
            "validation": _class_distribution(y_val_np),
            "train_episodes": _class_distribution(dataset["episode_labels"][np.isin(dataset["episode_ids"], train_episode_ids)]),
            "validation_episodes": _class_distribution(dataset["episode_labels"][np.isin(dataset["episode_ids"], val_episode_ids)]),
        },
        "device": device_checks,
        "final_metrics": {
            "train_loss": train_loss,
            "train_accuracy": train_accuracy,
            "validation_loss": val_loss,
            "validation_accuracy": val_accuracy,
            "per_class": per_class,
            "confusion_matrix": confusion.tolist(),
        },
        "final_epoch_metrics": history[-1],
        "history": history,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "feature_mean": mean,
            "feature_std": std,
            "class_names": CLASS_NAMES,
            "architecture": "24-64-32-5",
            "source_dataset": str(dataset_path),
        "source_labels": str(labels_path),
        "split": "episode-level stratified 80/20",
        "report": report,
        },
        checkpoint_path,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _load_dataset(dataset_path: Path, labels_path: Path) -> dict[str, np.ndarray]:
    with np.load(dataset_path, allow_pickle=False) as demos, np.load(labels_path, allow_pickle=False) as labels_npz:
        opponent_features = demos["opponent_features"]
        full_features = demos["features"]
        transition_episode_ids = demos["episode_ids"]
        labels = labels_npz["labels"]
        label_episode_ids = labels_npz["episode_ids"]
        episode_labels = labels_npz["episode_labels"]
        class_names = tuple(_decode_text(row) for row in labels_npz["class_names"])

    if opponent_features.shape != (labels.shape[0], 24):
        raise AssertionError(f"expected opponent_features shape ({labels.shape[0]}, 24), got {opponent_features.shape}")
    if opponent_features.dtype != np.float32:
        raise AssertionError(f"expected opponent_features dtype float32, got {opponent_features.dtype}")
    if full_features.shape != (labels.shape[0], 128):
        raise AssertionError(f"expected features shape ({labels.shape[0]}, 128), got {full_features.shape}")
    if full_features.dtype != np.float32:
        raise AssertionError(f"expected features dtype float32, got {full_features.dtype}")
    if not np.allclose(opponent_features, full_features[:, 60:84]):
        raise AssertionError("opponent_features does not match features[:, 60:84]")
    if not np.isfinite(opponent_features).all():
        raise AssertionError("opponent_features contains NaN or Inf")
    if labels.dtype != np.int64:
        raise AssertionError(f"expected labels dtype int64, got {labels.dtype}")
    if labels.shape != (opponent_features.shape[0],):
        raise AssertionError(f"expected labels shape ({opponent_features.shape[0]},), got {labels.shape}")
    if transition_episode_ids.shape != labels.shape:
        raise AssertionError("transition episode_ids must match transition labels shape")
    if label_episode_ids.shape != episode_labels.shape:
        raise AssertionError("label episode_ids must match episode_labels shape")
    if not bool(((labels >= 0) & (labels < len(CLASS_NAMES))).all()):
        raise AssertionError("labels contain values outside the 0..4 class range")
    if not bool(((episode_labels >= 0) & (episode_labels < len(CLASS_NAMES))).all()):
        raise AssertionError("episode_labels contain values outside the 0..4 class range")
    if class_names != CLASS_NAMES:
        raise AssertionError(f"class_names mismatch: {class_names}")

    unique_transition_episode_ids = np.unique(transition_episode_ids)
    if not np.array_equal(unique_transition_episode_ids, label_episode_ids):
        raise AssertionError("dataset episode_ids do not match label episode_ids")
    for episode_id, episode_label in zip(label_episode_ids, episode_labels):
        indices = transition_episode_ids == episode_id
        if not np.all(labels[indices] == episode_label):
            raise AssertionError(f"transition labels are not constant for episode {int(episode_id)}")

    return {
        "opponent_features": opponent_features.astype(np.float32, copy=False),
        "labels": labels.astype(np.int64, copy=False),
        "transition_episode_ids": transition_episode_ids.astype(np.int32, copy=False),
        "episode_ids": label_episode_ids.astype(np.int32, copy=False),
        "episode_labels": episode_labels.astype(np.int64, copy=False),
    }


def _stratified_split(labels: np.ndarray, val_ratio: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    train_indices: list[np.ndarray] = []
    val_indices: list[np.ndarray] = []
    for class_id in range(len(CLASS_NAMES)):
        class_indices = np.flatnonzero(labels == class_id)
        if class_indices.size < 2:
            raise AssertionError(f"class {CLASS_NAMES[class_id]} has fewer than two samples")
        rng.shuffle(class_indices)
        val_count = max(1, int(round(class_indices.size * val_ratio)))
        val_indices.append(class_indices[:val_count])
        train_indices.append(class_indices[val_count:])

    train = np.concatenate(train_indices).astype(np.int64, copy=False)
    val = np.concatenate(val_indices).astype(np.int64, copy=False)
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def _episode_stratified_transition_split(
    transition_labels: np.ndarray,
    transition_episode_ids: np.ndarray,
    episode_ids: np.ndarray,
    episode_labels: np.ndarray,
    val_ratio: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    train_episode_ids, val_episode_ids = _stratified_split(episode_labels, val_ratio=val_ratio, seed=seed)
    train_episodes = episode_ids[train_episode_ids]
    val_episodes = episode_ids[val_episode_ids]

    train_mask = np.isin(transition_episode_ids, train_episodes)
    val_mask = np.isin(transition_episode_ids, val_episodes)
    if bool(np.any(train_mask & val_mask)):
        raise AssertionError("episode-level split leaked transitions across train and validation")
    if int(train_mask.sum() + val_mask.sum()) != int(transition_labels.shape[0]):
        raise AssertionError("episode-level split did not cover every transition")

    return (
        train_episodes.astype(np.int32, copy=False),
        val_episodes.astype(np.int32, copy=False),
        np.flatnonzero(train_mask).astype(np.int64, copy=False),
        np.flatnonzero(val_mask).astype(np.int64, copy=False),
    )


def _evaluate(
    model: OpponentClassifier,
    criterion: nn.Module,
    x: torch.Tensor,
    y: torch.Tensor,
    batch_size: int,
) -> tuple[float, float, np.ndarray]:
    model.eval()
    loss_total = 0.0
    correct = 0
    predictions: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, x.shape[0], batch_size):
            xb = x[start : start + batch_size]
            yb = y[start : start + batch_size]
            logits = model(xb)
            loss = criterion(logits, yb)
            loss_total += float(loss.item()) * int(yb.shape[0])
            pred = logits.argmax(dim=1)
            correct += int((pred == yb).sum().item())
            predictions.append(pred.detach().cpu().numpy())

    return loss_total / int(x.shape[0]), correct / int(x.shape[0]), np.concatenate(predictions)


def _confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, class_count: int) -> np.ndarray:
    matrix = np.zeros((class_count, class_count), dtype=np.int64)
    for truth, pred in zip(y_true, y_pred):
        matrix[int(truth), int(pred)] += 1
    return matrix


def _per_class_metrics(confusion: np.ndarray) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for class_id, class_name in enumerate(CLASS_NAMES):
        tp = float(confusion[class_id, class_id])
        fp = float(confusion[:, class_id].sum() - confusion[class_id, class_id])
        fn = float(confusion[class_id, :].sum() - confusion[class_id, class_id])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics[class_name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": int(confusion[class_id, :].sum()),
        }
    return metrics


def _class_distribution(labels: np.ndarray) -> dict[str, dict[str, float]]:
    total = int(labels.shape[0])
    return {
        class_name: {
            "count": int((labels == class_id).sum()),
            "ratio": float((labels == class_id).sum() / total) if total else 0.0,
        }
        for class_id, class_name in enumerate(CLASS_NAMES)
    }


def _decode_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "item"):
        return _decode_text(value.item())
    return str(value)


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the APEX 4.1 Step 4 opponent classifier.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=4104)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    report = train_opponent_classifier(
        dataset_path=args.dataset,
        labels_path=args.labels,
        checkpoint_path=args.checkpoint,
        report_path=args.report,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        seed=args.seed,
        require_cuda=not args.allow_cpu,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
