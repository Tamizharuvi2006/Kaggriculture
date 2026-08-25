import numpy as np

from apex_next.ml_engine.env_wrapper import (
    KaggricultureGymEnv,
    adapt_observation_for_apex_style_agent,
    sanitize_action,
)


def pass_opponent(obs, config):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def test_sanitize_action_preserves_valid_shell():
    action = sanitize_action(
        {
            "farmer": ["MOVE_RIGHT", "MOVE_LEFT"],
            "hands": ["WHEAT_SEEDS", "CARROT_SEEDS"],
            "market": [["SELL", "MILK", 1]] * 12,
        }
    )

    assert action["farmer"] == ["MOVE_RIGHT", "MOVE_LEFT"]
    assert action["hands"] == ["WHEAT_SEEDS", "CARROT_SEEDS"]
    assert len(action["market"]) == 10


def test_env_reset_returns_feature_vector():
    env = KaggricultureGymEnv(opponent_fn=pass_opponent)
    features = env.reset(seed=1)

    assert features.shape == (128,)
    assert features.dtype == np.float32
    assert not np.isnan(features).any()


def test_env_step_advances_real_environment():
    env = KaggricultureGymEnv(opponent_fn=pass_opponent)
    env.reset(seed=2)

    features, reward, done, info = env.step({"farmer": ["PASS"], "hands": [], "market": []})

    assert features.shape == (128,)
    assert features.dtype == np.float32
    assert reward == 0.0
    assert done is False
    assert info["step"] == 1


def test_apex_style_adapter_makes_seat1_farm_index_zero():
    obs = {
        "player": 1,
        "step": None,
        "farms": [
            {"money": 111, "name": "agent0"},
            {"money": 222, "name": "agent1"},
        ],
        "private": {"shed": {"WHEAT": 7}},
    }

    adapted = adapt_observation_for_apex_style_agent(obs, fallback_step=42)

    assert adapted["player"] == 0
    assert adapted["step"] == 42
    assert adapted["farms"][0]["name"] == "agent1"
    assert adapted["farms"][1]["name"] == "agent0"
    assert obs["farms"][0]["name"] == "agent0"


def test_apex_style_adapter_does_not_leak_other_private_state():
    obs = {
        "player": 1,
        "farms": [{"money": 100}, {"money": 200}],
        "private": {"shed": {"MILK": 3}, "orders_pending": [["SELL", "MILK", 1]]},
    }

    adapted = adapt_observation_for_apex_style_agent(obs)
    adapted["private"]["shed"]["MILK"] = 99

    assert adapted["private"]["shed"]["MILK"] == 99
    assert obs["private"]["shed"]["MILK"] == 3
    assert "opponent_private" not in adapted
