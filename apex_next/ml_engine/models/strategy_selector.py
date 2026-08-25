"""Step 5 strategy selector policy/value network for APEX 4.1 Hybrid ML."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


class StrategySelector(nn.Module):
    """PPO policy that maps game state plus opponent probabilities to strategy weights."""

    def __init__(self) -> None:
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(133, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
        )
        self.strategy_head = nn.Linear(32, 4)
        self.confidence_head = nn.Linear(32, 1)
        self.value_head = nn.Linear(32, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return strategy probabilities, confidence, and scalar value."""

        h = self.shared(x)
        strategy_weights = torch.softmax(self.strategy_head(h), dim=-1)
        confidence = torch.sigmoid(self.confidence_head(h))
        value = self.value_head(h)
        return strategy_weights, confidence, value

    def distribution(self, x: torch.Tensor) -> tuple[torch.distributions.Categorical, torch.Tensor, torch.Tensor]:
        """Return a categorical strategy distribution plus confidence/value heads."""

        strategy_weights, confidence, value = self.forward(x)
        return torch.distributions.Categorical(probs=strategy_weights), confidence, value

    def select_strategy(
        self,
        features_128: np.ndarray,
        opp_probs_5: np.ndarray,
        device: torch.device | str | None = None,
    ) -> tuple[np.ndarray, float]:
        """Inference helper returning four strategy weights and confidence."""

        target_device = torch.device(device) if device is not None else next(self.parameters()).device
        x = torch.tensor(np.concatenate([features_128, opp_probs_5]), dtype=torch.float32, device=target_device).unsqueeze(0)
        with torch.no_grad():
            weights, confidence, _ = self.forward(x)
        return weights.squeeze(0).detach().cpu().numpy(), float(confidence.squeeze().detach().cpu().item())
