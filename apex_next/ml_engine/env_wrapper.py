"""Gym-like Kaggriculture wrapper for the real APEX 4.1 ML pipeline."""

from __future__ import annotations

import copy
import importlib.util
import inspect
from pathlib import Path
from typing import Any, Callable

import kaggle_environments
import numpy as np

try:
    from .feature_extractor import FEATURE_DIM, extract_features
except ImportError:  # Allows direct script execution from this directory.
    from feature_extractor import FEATURE_DIM, extract_features


Action = dict[str, list[Any]]
AgentFn = Callable[[dict[str, Any], Any], Action]


PASS_ACTION: Action = {"farmer": ["PASS"], "hands": [], "market": []}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPPONENT_PATH = PROJECT_ROOT / "submission.py"


class KaggricultureGymEnv:
    """Wrap kaggle_environments with real observations and sparse MCV reward."""

    def __init__(
        self,
        opponent_fn: AgentFn | None = None,
        opponent_path: str | Path | None = None,
        adapt_opponent_observation: bool = True,
    ):
        self.env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720})
        self.opponent_fn = opponent_fn
        self.opponent_path = Path(opponent_path) if opponent_path is not None else DEFAULT_OPPONENT_PATH
        self.adapt_opponent_observation = adapt_opponent_observation
        self.feature_dim = FEATURE_DIM
        self.step_count = 0
        self.state: list[Any] | None = None
        self._opponent_agent: AgentFn | None = None

    def reset(self, seed: int | None = None) -> np.ndarray:
        """Reset the environment and return initial 128-dimensional features."""

        if seed is not None:
            self.env.configuration.randomSeed = int(seed)
        self.state = self.env.reset(num_agents=2)
        self.step_count = 0
        return extract_features(_observation(self.state[0]))

    def step(self, our_action: Action) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        """Advance one environment step with our action and the configured opponent."""

        if self.state is None:
            self.reset()

        assert self.state is not None
        own_action = sanitize_action(our_action)
        opp_obs = _observation(self.state[1])
        if self.adapt_opponent_observation:
            own_obs = _observation(self.state[0])
            opp_obs = adapt_observation_for_apex_style_agent(opp_obs, fallback_step=own_obs.get("step"))
        raw_opp_action = self._opponent(opp_obs, self.env.configuration)
        opp_action = sanitize_action(raw_opp_action)

        self.state = self.env.step([own_action, opp_action])
        self.step_count += 1

        obs = _observation(self.state[0])
        features = extract_features(obs)
        done = _is_done(self.state)
        reward = _terminal_reward(self.state) if done else 0.0
        info = {
            "obs": obs,
            "step": self.step_count,
            "raw_state": self.state,
            "our_action": own_action,
            "raw_opponent_action": raw_opp_action,
            "opponent_action": opp_action,
            "opponent_observation": opp_obs,
        }
        return features, float(reward), bool(done), info

    def _opponent(self, obs: dict[str, Any], config: Any) -> Action:
        if self.opponent_fn is not None:
            return call_agent(self.opponent_fn, obs, config)
        if self._opponent_agent is None:
            self._opponent_agent = load_agent(self.opponent_path)
        return call_agent(self._opponent_agent, obs, config)


# Keep the spelling used by README_ML_PLAN.md as a compatibility alias.
KaggriculureGymEnv = KaggricultureGymEnv


def load_agent(path: str | Path) -> AgentFn:
    """Load a self-contained Kaggle submission file and return its agent()."""

    agent_path = Path(path)
    spec = importlib.util.spec_from_file_location(agent_path.stem, agent_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load agent from {agent_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    agent = getattr(module, "agent", None)
    if not callable(agent):
        raise AttributeError(f"{agent_path} does not expose callable agent")
    return agent


def call_agent(agent: AgentFn, obs: dict[str, Any], config: Any) -> Action:
    """Call agents that expose either agent(obs) or agent(obs, configuration)."""

    try:
        signature = inspect.signature(agent)
        positional = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            and parameter.default is inspect.Parameter.empty
        ]
        accepts_varargs = any(
            parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in signature.parameters.values()
        )
        if not accepts_varargs and len(positional) <= 1:
            return agent(obs)  # type: ignore[misc]
    except (TypeError, ValueError):
        pass
    return agent(obs, config)


def adapt_observation_for_apex_style_agent(obs: dict[str, Any], fallback_step: Any = None) -> dict[str, Any]:
    """Return an observation where farms[0] is the receiving agent's farm.

    Kaggriculture seat-1 observations keep the global farm order. The sealed
    APEX-style agents were written for Kaggle's single-agent entry point and
    assume their own farm is always at farms[0]. This adapter changes only the
    public farm order for player 1 and preserves the seat's own private state.
    """

    if not isinstance(obs, dict):
        return {}
    adapted = copy.deepcopy(obs)
    farms = adapted.get("farms")
    player = _player_index(adapted, len(farms) if isinstance(farms, list) else 0)
    if player == 1 and isinstance(farms, list) and len(farms) == 2:
        adapted["farms"] = [farms[1], farms[0]]
        adapted["player"] = 0
        if "index" in adapted:
            adapted["index"] = 0
        if "agentIndex" in adapted:
            adapted["agentIndex"] = 0
    if adapted.get("step") is None and fallback_step is not None:
        adapted["step"] = fallback_step
    return adapted


def sanitize_action(action: Any) -> Action:
    """Return a valid Kaggriculture action shell, preserving legal user orders."""

    if not isinstance(action, dict):
        return dict(PASS_ACTION)
    farmer = _as_list(action.get("farmer", ["PASS"])) or ["PASS"]
    hands = _as_list(action.get("hands", []))
    market = [list(order) for order in _as_list(action.get("market", [])) if isinstance(order, (list, tuple))][:10]
    return {"farmer": farmer, "hands": hands, "market": market}


def _observation(agent_state: Any) -> dict[str, Any]:
    obs = getattr(agent_state, "observation", {})
    return obs if isinstance(obs, dict) else {}


def _is_done(state: list[Any]) -> bool:
    return any(str(getattr(agent_state, "status", "")).upper() == "DONE" for agent_state in state)


def _terminal_reward(state: list[Any]) -> float:
    own_reward = getattr(state[0], "reward", 0.0) or 0.0
    opp_reward = getattr(state[1], "reward", 0.0) or 0.0
    return float(own_reward) - float(opp_reward)


def _player_index(obs: dict[str, Any], farm_count: int) -> int:
    for key in ("player", "index", "agentIndex"):
        try:
            player = int(obs.get(key))
        except (TypeError, ValueError):
            continue
        if 0 <= player < farm_count:
            return player
    return 0


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]
