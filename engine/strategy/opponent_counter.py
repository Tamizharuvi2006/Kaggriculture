"""Anti-herd opponent counter-strategy engine."""
from __future__ import annotations
from typing import Dict, Any
from engine.state.opponent_state import OpponentState

class OpponentCounterEngine:
    """Detects opponent strategy patterns and generates targeted economic counters."""

    @staticmethod
    def evaluate_counter_measures(opponent: OpponentState) -> Dict[str, Any]:
        """Anti-Herd Heuristics:
        1. If opponent is CARROT RUSHER (>= 6 carrots) -> Avoid carrots (imminent supply crash).
        2. If opponent has ZERO TOMATOES and tomato demand active -> Strong opportunity for tomato pivot.
        3. If opponent is COW HEAVY (>= 6 cows) -> Feed prices will rise; secure early wheat feed.
        """
        avoid_carrots = opponent.is_carrot_rusher
        exploit_tomatoes = opponent.has_zero_tomatoes
        prioritize_feed_early = opponent.is_livestock_heavy

        return {
            "avoid_carrots": avoid_carrots,
            "exploit_tomatoes": exploit_tomatoes,
            "prioritize_feed_early": prioritize_feed_early,
            "profile": (
                "CARROT_RUSHER" if opponent.is_carrot_rusher
                else ("LIVESTOCK_HEAVY" if opponent.is_livestock_heavy
                else ("STRAWBERRY_HEAVY" if opponent.is_strawberry_heavy else "BALANCED"))
            )
        }
