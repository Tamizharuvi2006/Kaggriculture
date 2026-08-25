import numpy as np

from apex_next.ml_engine.feature_extractor import FEATURE_DIM, opponent_features, extract_features


def test_extract_features_uses_real_observation_shape_and_dtype():
    obs = {
        "step": 71,
        "player": 0,
        "farms": [
            {
                "money": 350,
                "unlocked_quadrants": ["NW", "NE"],
                "animals": {"COW": 2, "SHEEP": 1},
                "workers": [{"carrying": None}, {"carrying": "MILK"}],
                "tiles": [
                    [{"tilled": True, "crop": "STRAWBERRY", "stage": "RIPE", "watered": True}],
                    [{"tilled": True, "crop": "WHEAT", "stage": "GROWING"}],
                ],
            },
            {
                "money": 700,
                "unlocked_quadrants": ["NW", "NE", "SW"],
                "animals": {"COW": 6, "SHEEP": 0},
                "workers": [{}, {}, {}],
                "tiles": [[{"crop": "MELON", "stage": "RIPE"}]],
            },
        ],
        "private": {"shed": {"MILK": 5, "STRAWBERRY": 6, "WHEAT_SEEDS": 3}},
        "market": {"prices": {"MILK": 210, "STRAWBERRY": 145}},
    }

    features = extract_features(obs)

    assert features.shape == (FEATURE_DIM,)
    assert features.dtype == np.float32
    assert not np.isnan(features).any()
    assert not np.isinf(features).any()
    assert features[0] == np.float32(71 / 720)
    assert features[60] == np.float32(700 / 10000)
    assert opponent_features(features).shape == (24,)


def test_extract_features_is_total_on_missing_fields():
    features = extract_features({"step": 0})

    assert features.shape == (FEATURE_DIM,)
    assert features.dtype == np.float32
    assert not np.isnan(features).any()
    assert features[0] == 0.0
