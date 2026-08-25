"""Continuous two-control policy for the redesigned Step 5B target."""

from __future__ import annotations

import torch
import torch.nn as nn


class TwoControlSelector(nn.Module):
    """Map 128 game features plus 5 opponent probabilities to two controls."""

    def __init__(self) -> None:
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(133, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
        )
        self.control_head = nn.Linear(32, 2)
        self.log_std = nn.Parameter(torch.full((2,), -1.0))
        self.confidence_head = nn.Linear(32, 1)
        self.value_head = nn.Linear(32, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        h = self.shared(x)
        controls = 0.25 * torch.tanh(self.control_head(h))
        confidence = torch.sigmoid(self.confidence_head(h))
        value = self.value_head(h)
        return controls, confidence, value

    def distribution(self, x: torch.Tensor) -> tuple[torch.distributions.Normal, torch.Tensor, torch.Tensor]:
        controls, confidence, value = self.forward(x)
        std = self.log_std.exp().expand_as(controls)
        return torch.distributions.Normal(controls, std), confidence, value
