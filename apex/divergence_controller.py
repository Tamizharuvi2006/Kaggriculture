"""L+ APEX 2.5-E: DivergenceController Engine.
Forces execution of EXACTLY ONE safe zero-cost policy deviation per episode (Steps 100-600).
"""

from __future__ import annotations
import math
from typing import Dict, List, Any, Optional, Tuple
from apex.world_model import WorldState

class DivergenceCandidateRank:
    def __init__(self, score: float, candidate: List[Any], reason: str, novelty_bonus: float, action_key: str):
        self.score = score
        self.candidate = candidate
        self.reason = reason
        self.novelty_bonus = novelty_bonus
        self.action_key = action_key
        self.quality_rank_score = score + novelty_bonus

class DivergenceController:
    """DivergenceController Engine:
    Forces execution of EXACTLY ONE safe zero-cost deviation per episode (Steps 100-600).
    Ranks safety-approved candidates by quality, novelty, and transit advantage.
    """

    def __init__(self, max_deviations_per_episode: int = 1):
        self.max_deviations_per_episode = max_deviations_per_episode
        self.deviations_executed_this_episode = 0
        self.action_history: Dict[str, int] = {}

    def reset_episode(self):
        """Reset per-episode deviation tracker."""
        self.deviations_executed_this_episode = 0

    def select_controlled_deviation(
        self,
        approved_candidates: List[Tuple[float, List[Any], str]],
        state: WorldState
    ) -> Optional[DivergenceCandidateRank]:
        # Rule 1: Max 1 Deviation per episode
        if self.deviations_executed_this_episode >= self.max_deviations_per_episode:
            return None

        # Rule 2: Window Guard (Steps 100-600 only)
        if state.step < 100 or state.step > 600:
            return None

        ranked_list: List[DivergenceCandidateRank] = []

        for cand_score, cand, reason in approved_candidates:
            # Safely unwrap order lists
            first_ord = cand[0] if isinstance(cand, list) and len(cand) > 0 else cand
            cmd = first_ord[0] if isinstance(first_ord, list) and len(first_ord) > 0 else first_ord
            
            # Rule 3: Zero-Capital-Cost Curriculum Only (SELL)
            if cmd == "SELL":
                item = first_ord[1] if len(first_ord) > 1 else "WHEAT"
                qty = first_ord[2] if len(first_ord) > 2 else 1
                action_key = f"{cmd}_{item}_{qty}"
                
                # Novelty / Uncertainty Bonus calculation calibrated for MCV domain
                n_obs = self.action_history.get(action_key, 0)
                novelty_bonus = 2.50 / math.sqrt(n_obs + 1.0)

                ranked_list.append(DivergenceCandidateRank(
                    score=cand_score,
                    candidate=cand,
                    reason=reason,
                    novelty_bonus=novelty_bonus,
                    action_key=action_key
                ))

        if not ranked_list:
            return None

        # Rank candidates by Quality Score + Novelty Bonus
        ranked_list.sort(key=lambda x: x.quality_rank_score, reverse=True)
        chosen = ranked_list[0]

        self.deviations_executed_this_episode += 1
        self.action_history[chosen.action_key] = self.action_history.get(chosen.action_key, 0) + 1

        return chosen
