"""Paired identical-seed evaluation framework."""
from __future__ import annotations
import copy
from typing import Dict, Any, List, Callable, Tuple
import kaggle_environments

class PairedEvaluator:
    """Runs candidate vs control agent on identical seeds across both seats."""

    @staticmethod
    def evaluate_pair(
        candidate_agent: Callable,
        control_agent: Callable,
        seed: int,
        steps: int = 720,
    ) -> Dict[str, Any]:
        """Runs match twice: (Candidate Seat 0 vs Control Seat 1) and (Control Seat 0 vs Candidate Seat 1)."""
        # Match 1: Candidate = Seat 0, Control = Seat 1
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
        env1.reset()
        
        while not env1.done:
            obs0 = env1.state[0].observation
            obs1 = env1.state[1].observation
            act0 = candidate_agent(obs0)
            act1 = control_agent(obs1)
            env1.step([act0, act1])
            
        cand_reward_seat0 = float(env1.state[0].reward or 0.0)
        ctrl_reward_seat1 = float(env1.state[1].reward or 0.0)
        m1_win = 1 if cand_reward_seat0 > ctrl_reward_seat1 else (0.5 if cand_reward_seat0 == ctrl_reward_seat1 else 0)

        # Match 2: Control = Seat 0, Candidate = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
        env2.reset()
        
        while not env2.done:
            obs0 = env2.state[0].observation
            obs1 = env2.state[1].observation
            act0 = control_agent(obs0)
            act1 = candidate_agent(obs1)
            env2.step([act0, act1])
            
        ctrl_reward_seat0 = float(env2.state[0].reward or 0.0)
        cand_reward_seat1 = float(env2.state[1].reward or 0.0)
        m2_win = 1 if cand_reward_seat1 > ctrl_reward_seat0 else (0.5 if cand_reward_seat1 == ctrl_reward_seat0 else 0)

        total_cand_reward = cand_reward_seat0 + cand_reward_seat1
        total_ctrl_reward = ctrl_reward_seat0 + ctrl_reward_seat1
        paired_delta = total_cand_reward - total_ctrl_reward
        win_rate = (m1_win + m2_win) / 2.0

        return {
            "seed": seed,
            "cand_seat0": cand_reward_seat0,
            "ctrl_seat1": ctrl_reward_seat1,
            "m1_win": m1_win,
            "ctrl_seat0": ctrl_reward_seat0,
            "cand_seat1": cand_reward_seat1,
            "m2_win": m2_win,
            "paired_delta": paired_delta,
            "win_rate": win_rate,
        }
