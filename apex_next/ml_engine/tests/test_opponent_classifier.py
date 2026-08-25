import numpy as np
import torch

from apex_next.ml_engine.models.opponent_classifier import OpponentClassifier
from apex_next.ml_engine.training.train_opponent_classifier import _episode_stratified_transition_split, _stratified_split


def test_opponent_classifier_architecture_outputs_five_logits():
    model = OpponentClassifier()
    x = torch.zeros((4, 24), dtype=torch.float32)

    logits = model(x)

    assert logits.shape == (4, 5)
    assert sum(param.numel() for param in model.parameters()) == 3845


def test_stratified_split_preserves_all_classes():
    labels = np.repeat(np.arange(5, dtype=np.int64), 20)

    train_idx, val_idx = _stratified_split(labels, val_ratio=0.2, seed=123)

    assert train_idx.shape == (80,)
    assert val_idx.shape == (20,)
    assert np.bincount(labels[train_idx], minlength=5).tolist() == [16, 16, 16, 16, 16]
    assert np.bincount(labels[val_idx], minlength=5).tolist() == [4, 4, 4, 4, 4]


def test_episode_stratified_split_keeps_episodes_disjoint():
    episode_ids = np.arange(50, dtype=np.int32)
    episode_labels = np.repeat(np.arange(5, dtype=np.int64), 10)
    transition_episode_ids = np.repeat(episode_ids, 3)
    transition_labels = np.repeat(episode_labels, 3)

    train_episodes, val_episodes, train_idx, val_idx = _episode_stratified_transition_split(
        transition_labels=transition_labels,
        transition_episode_ids=transition_episode_ids,
        episode_ids=episode_ids,
        episode_labels=episode_labels,
        val_ratio=0.2,
        seed=123,
    )

    assert set(train_episodes).isdisjoint(set(val_episodes))
    assert train_idx.shape == (120,)
    assert val_idx.shape == (30,)
    assert np.bincount(transition_labels[train_idx], minlength=5).tolist() == [24, 24, 24, 24, 24]
    assert np.bincount(transition_labels[val_idx], minlength=5).tolist() == [6, 6, 6, 6, 6]
