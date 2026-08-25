"""Step 4 opponent archetype classifier for APEX 4.1 Hybrid ML."""

from __future__ import annotations

import torch
import torch.nn as nn


class OpponentClassifier(nn.Module):
    """MLP classifier over the 24 public opponent features."""

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(24, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 5),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return unnormalized logits for the five opponent archetypes."""

        return self.net(x)

    def predict_proba(self, opponent_features: torch.Tensor) -> torch.Tensor:
        """Return class probabilities for already-extracted opponent features."""

        return torch.softmax(self.forward(opponent_features), dim=-1)
