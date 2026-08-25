import json

import numpy as np

from apex_next.ml_engine.training.label_opponents import (
    AGGRESSIVE_EXPAND,
    BALANCED,
    CROP_HEAVY,
    LIVESTOCK_HEAVY,
    label_opponents,
    validate_labels,
    MARKET_MANIPULATOR,
)


def test_label_opponents_applies_documented_rule_priority(tmp_path):
    dataset_path = tmp_path / "expert_demos.npz"
    output_path = tmp_path / "opponent_labels.npz"
    audit_path = tmp_path / "opponent_labels_audit.json"

    features = np.zeros((10, 128), dtype=np.float32)
    opponent_features = features[:, 60:84]
    terminals = np.zeros(10, dtype=np.bool_)
    episode_ids = np.repeat(np.arange(5, dtype=np.int32), 2)
    steps = np.asarray([200, 719, 200, 719, 200, 719, 200, 719, 200, 719], dtype=np.int16)

    terminals[[1, 3, 5, 7, 9]] = True
    opponent_features[1, 4] = np.float32(9 / 14)
    opponent_features[2:4, 8] = np.float32(21 / 34)
    opponent_features[4, 23] = np.float32(1.0)
    opponent_features[5, 23] = np.float32(1.0)
    features[4, 6] = np.float32(1 / 4)
    opponent_features[4, 1] = np.float32(2 / 4)
    opponent_actions = [b'{"farmer":["PASS"],"hands":[],"market":[]}' for _ in range(10)]
    crop_seed_action = json.dumps(
        {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["BUY_SEED", "STRAWBERRY", 1] for _ in range(50)],
        }
    ).encode("utf-8")
    opponent_actions[2] = crop_seed_action
    opponent_actions[3] = crop_seed_action
    opponent_actions[8] = b'{"farmer":["PASS"],"hands":[],"market":[["BUY_PRODUCT","WHEAT",1],["SELL","WHEAT",1]]}'
    opponent_actions[9] = b'{"farmer":["PASS"],"hands":[],"market":[["BUY_PRODUCT","WHEAT",1],["SELL","WHEAT",1]]}'

    np.savez_compressed(
        dataset_path,
        features=features,
        opponent_features=opponent_features.copy(),
        terminals=terminals,
        episode_ids=episode_ids,
        steps=steps,
        opponent_ids=np.asarray([b"test"] * 10, dtype=np.bytes_),
        opponent_actions_json=np.asarray(opponent_actions, dtype=np.bytes_),
    )

    audit = label_opponents(dataset_path, output_path, audit_path)

    with np.load(output_path, allow_pickle=False) as labels_npz:
        assert labels_npz["episode_labels"].tolist() == [
            LIVESTOCK_HEAVY,
            CROP_HEAVY,
            AGGRESSIVE_EXPAND,
            BALANCED,
            BALANCED,
        ]
        assert labels_npz["labels"].shape == (10,)

    assert audit["status"] == "PASS"
    assert validate_labels(output_path, expected_transitions=10, expected_episodes=5)["status"] == "PASS"
    saved_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert saved_audit["unlabeled"] == 0
    assert saved_audit["invalid_labels"] == 0


def test_label_opponents_uses_conservative_market_telemetry(tmp_path):
    dataset_path = tmp_path / "expert_demos.npz"
    output_path = tmp_path / "opponent_labels.npz"
    audit_path = tmp_path / "opponent_labels_audit.json"
    rows = 1200
    features = np.zeros((rows, 128), dtype=np.float32)
    opponent_features = features[:, 60:84]
    terminals = np.zeros(rows, dtype=np.bool_)
    terminals[-1] = True
    episode_ids = np.zeros(rows, dtype=np.int32)
    steps = np.arange(1, rows + 1, dtype=np.int16)
    action = b'{"farmer":["PASS"],"hands":[],"market":[["BUY_PRODUCT","WHEAT",1],["SELL","WHEAT",1],["BUY_PRODUCT","WHEAT",1]]}'

    np.savez_compressed(
        dataset_path,
        features=features,
        opponent_features=opponent_features.copy(),
        terminals=terminals,
        episode_ids=episode_ids,
        steps=steps,
        opponent_ids=np.asarray([b"market"] * rows, dtype=np.bytes_),
        opponent_actions_json=np.asarray([action] * rows, dtype=np.bytes_),
    )

    label_opponents(dataset_path, output_path, audit_path)

    with np.load(output_path, allow_pickle=False) as labels_npz:
        assert labels_npz["episode_labels"].tolist() == [MARKET_MANIPULATOR]


def test_label_opponents_rejects_corrupt_opponent_slice(tmp_path):
    dataset_path = tmp_path / "expert_demos.npz"
    features = np.zeros((2, 128), dtype=np.float32)
    opponent_features = np.ones((2, 24), dtype=np.float32)

    np.savez_compressed(
        dataset_path,
        features=features,
        opponent_features=opponent_features,
        terminals=np.asarray([False, True], dtype=np.bool_),
        episode_ids=np.asarray([0, 0], dtype=np.int32),
        steps=np.asarray([1, 719], dtype=np.int16),
    )

    try:
        label_opponents(dataset_path, tmp_path / "labels.npz", tmp_path / "audit.json")
    except AssertionError as exc:
        assert "opponent_features does not match" in str(exc)
    else:
        raise AssertionError("label_opponents should reject mismatched opponent features")
