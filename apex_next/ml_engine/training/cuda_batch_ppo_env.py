"""Batch PPO environment over the immutable OPT-1 CUDA engine."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv, _load_opt1_engine_class


class CudaBatchPPOEnv:
    """Run independent PPO episodes together through one CUDA engine batch."""

    def __init__(self, opponent_fns: Sequence[Any], device: str = "cuda:0") -> None:
        if not opponent_fns:
            raise ValueError("CudaBatchPPOEnv requires at least one opponent")
        self.opponent_fns = list(opponent_fns)
        self.batch_size = len(self.opponent_fns)
        engine_class = _load_opt1_engine_class()
        self.engine = engine_class(batch_size=self.batch_size, base_seed=0, device=device)
        if not self.engine.actual_cuda_used:
            raise RuntimeError("OPT-1 batch PPO environment did not activate CUDA tensors")
        self.step_count = 0
        self.configuration = None

    @property
    def actual_cuda_used(self) -> bool:
        return bool(self.engine.actual_cuda_used)

    def reset(self, seeds: Sequence[int], extract_initial_features: bool = True) -> list[np.ndarray]:
        if len(seeds) != self.batch_size:
            raise ValueError("seed count must equal batch size")
        self.engine.reset([int(seed) for seed in seeds])
        self.step_count = 0
        if extract_initial_features:
            return [extract_features(self.observation(idx, 0)) for idx in range(self.batch_size)]
        return []

    def observation(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        return self.engine.observation(env_idx, player_idx)

    def step(
        self,
        our_actions: Sequence[dict[str, Any]],
        extract_next_features: bool = True,
    ) -> tuple[list[np.ndarray], list[float], list[bool], list[dict[str, Any]]]:
        if len(our_actions) != self.batch_size:
            raise ValueError("action count must equal batch size")
        opponent_actions = []
        for env_idx, opponent_fn in enumerate(self.opponent_fns):
            opponent_obs = self.observation(env_idx, 1)
            opponent_actions.append(sanitize_action(call_agent(opponent_fn, opponent_obs, self.configuration)))
        self.engine.step_integrated(
            [sanitize_action(action) for action in our_actions],
            opponent_actions,
        )
        self.step_count = int(self.engine.step_idx)
        features = (
            [extract_features(self.observation(idx, 0)) for idx in range(self.batch_size)]
            if extract_next_features
            else []
        )
        rewards: list[float] = []
        dones: list[bool] = []
        infos: list[dict[str, Any]] = []
        for env_idx in range(self.batch_size):
            metrics = self.engine.terminal_metrics(env_idx, 0)
            done = bool(self.step_count >= self.engine.TERMINAL_STEP)
            rewards.append(float(metrics["raw_terminal_reward"]))
            dones.append(done)
            infos.append(
                {
                    "step": self.step_count,
                    "terminal": done,
                    "terminal_metrics": metrics,
                    "actual_cuda_used": self.actual_cuda_used,
                    "tensor_device": str(self.engine.money.device),
                    "opponent_action": opponent_actions[env_idx],
                }
            )
        return features, rewards, dones, infos
