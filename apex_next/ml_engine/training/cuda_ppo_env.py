"""PPO adapter for the immutable Step 3H OPT-1 CUDA engine."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OPT1_ENGINE_PATH = (
    PROJECT_ROOT
    / "reports"
    / "step3h"
    / "source_snapshots"
    / "corrected_cuda_engine_GOLDEN_OPT1_BATCH_PHYSICAL_SYNC_1p7585.py"
)
OPT1_ENGINE_SHA256 = "90848D5A29B834CA77251F403616AD31FE4F8AEF18897B39A93500FCB9E6C973"

AgentFn = Callable[[dict[str, Any], Any], dict[str, list[Any]]]


def _load_opt1_engine_class() -> type[Any]:
    if not OPT1_ENGINE_PATH.exists():
        raise FileNotFoundError(f"Immutable OPT-1 snapshot not found: {OPT1_ENGINE_PATH}")
    digest = hashlib.sha256(OPT1_ENGINE_PATH.read_bytes()).hexdigest().upper()
    if digest != OPT1_ENGINE_SHA256:
        raise RuntimeError(f"OPT-1 snapshot hash mismatch: expected {OPT1_ENGINE_SHA256}, got {digest}")
    module_name = "apex41_opt1_cuda_snapshot"
    spec = importlib.util.spec_from_file_location(module_name, OPT1_ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load OPT-1 snapshot: {OPT1_ENGINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.CorrectedCudaPairedEngine


class CudaPPOEnv:
    """Single-environment view over the batch-capable OPT-1 CUDA simulator."""

    def __init__(self, opponent_fn: AgentFn, device: str = "cuda:0") -> None:
        self.opponent_fn = opponent_fn
        self.configuration = None
        self.engine_class = _load_opt1_engine_class()
        self.engine = self.engine_class(batch_size=1, base_seed=0, device=device)
        if not self.engine.actual_cuda_used:
            raise RuntimeError("OPT-1 PPO environment did not activate CUDA tensors")
        self.step_count = 0

    @property
    def actual_cuda_used(self) -> bool:
        return bool(self.engine.actual_cuda_used)

    @property
    def state(self) -> Any:
        return self.engine

    def reset(self, seed: int) -> np.ndarray:
        self.engine.reset([int(seed)])
        self.step_count = 0
        from apex_next.ml_engine.feature_extractor import extract_features

        return extract_features(self.observation(0))

    def observation(self, player_idx: int) -> dict[str, Any]:
        return self.engine.observation(0, player_idx)

    def step(self, our_action: dict[str, Any]) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
        from apex_next.ml_engine.feature_extractor import extract_features

        opponent_obs = self.observation(1)
        opponent_action = sanitize_action(call_agent(self.opponent_fn, opponent_obs, self.configuration))
        self.engine.step_integrated([sanitize_action(our_action)], [opponent_action])
        self.step_count = int(self.engine.step_idx)
        terminal = bool(self.step_count >= self.engine.TERMINAL_STEP)
        metrics = self.engine.terminal_metrics(0, 0)
        features = extract_features(self.observation(0))
        return features, float(metrics["raw_terminal_reward"]), terminal, {
            "step": self.step_count,
            "terminal": terminal,
            "terminal_metrics": metrics,
            "actual_cuda_used": self.actual_cuda_used,
            "tensor_device": str(self.engine.money.device),
        }
