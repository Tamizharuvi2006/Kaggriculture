import numpy as np
import torch

from apex_next.ml_engine.models.strategy_selector import StrategySelector
from apex_next.ml_engine.training.train_strategy_selector_ppo import _selector_input


def test_strategy_selector_outputs_valid_ranges():
    model = StrategySelector()
    x = torch.zeros((3, 133), dtype=torch.float32)

    weights, confidence, value = model(x)

    assert weights.shape == (3, 4)
    assert confidence.shape == (3, 1)
    assert value.shape == (3, 1)
    assert torch.allclose(weights.sum(dim=1), torch.ones(3), atol=1e-6)
    assert bool(((confidence >= 0.0) & (confidence <= 1.0)).all())


def test_selector_input_is_133_dimensional_and_finite():
    features = np.zeros(128, dtype=np.float32)
    opponent_probs = np.asarray([0.1, 0.2, 0.3, 0.15, 0.25], dtype=np.float32)

    x = _selector_input(features, opponent_probs, torch.device("cpu"))

    assert x.shape == (1, 133)
    assert torch.isfinite(x).all()
