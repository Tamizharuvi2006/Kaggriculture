from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ML_ENGINE_DIR = Path(__file__).resolve().parent
CURRENT_DATA_DIR = ML_ENGINE_DIR / "data" / "current" / "step3g_targeted_1000"
REPORT_PATH = ML_ENGINE_DIR / "evaluation" / "ML_ARTIFACT_LAYOUT_VERIFY.json"


def _path_status(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def main() -> int:
    dataset_path = CURRENT_DATA_DIR / "expert_demos_step3g_targeted_1000.npz"
    labels_path = CURRENT_DATA_DIR / "opponent_labels_step3g_targeted_1000.npz"
    classifier_path = ML_ENGINE_DIR / "checkpoints" / "opponent_classifier" / "opponent_classifier.pt"
    strategy_smoke_path = ML_ENGINE_DIR / "checkpoints" / "strategy_selector" / "strategy_selector_smoke.pt"
    strategy_timing_path = ML_ENGINE_DIR / "checkpoints" / "strategy_selector" / "strategy_selector_timing_smoke.pt"
    invalidation_note = (
        ML_ENGINE_DIR
        / "data"
        / "invalidated"
        / "original_seat_bug"
        / "EXPERT_DEMOS_INVALIDATION_NOTE.md"
    )

    required_paths = {
        "dataset": dataset_path,
        "labels": labels_path,
        "classifier_checkpoint": classifier_path,
        "strategy_smoke_checkpoint": strategy_smoke_path,
        "strategy_timing_checkpoint": strategy_timing_path,
        "step4_report": ML_ENGINE_DIR / "evaluation" / "step4_classifier" / "opponent_classifier_report.json",
        "step5_smoke_report": ML_ENGINE_DIR / "evaluation" / "step5_strategy" / "strategy_selector_smoke_report.json",
        "step5_timing_report": ML_ENGINE_DIR / "evaluation" / "step5_strategy" / "strategy_timing_diagnostic_report.json",
        "invalidated_marker": invalidation_note,
    }

    status: dict[str, object] = {
        "ok": True,
        "required_paths": {name: _path_status(path) for name, path in required_paths.items()},
    }

    missing = [name for name, path in required_paths.items() if not path.exists()]
    if missing:
        status["ok"] = False
        status["missing"] = missing
    else:
        with np.load(dataset_path, allow_pickle=False) as dataset:
            status["dataset"] = {
                "files": list(dataset.files),
                "features_shape": list(dataset["features"].shape),
                "features_dtype": str(dataset["features"].dtype),
                "opponent_features_shape": list(dataset["opponent_features"].shape),
                "opponent_features_dtype": str(dataset["opponent_features"].dtype),
            }
        with np.load(labels_path, allow_pickle=False) as labels:
            label_key = "labels" if "labels" in labels.files else labels.files[0]
            label_values = labels[label_key]
            classes, counts = np.unique(label_values, return_counts=True)
            status["labels"] = {
                "files": list(labels.files),
                "label_key": label_key,
                "shape": list(label_values.shape),
                "dtype": str(label_values.dtype),
                "class_distribution": {
                    str(int(cls)): int(count) for cls, count in zip(classes, counts)
                },
            }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
