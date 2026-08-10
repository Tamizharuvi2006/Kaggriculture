"""L+ APEX: Memory & Experience System (Short-Term, Episodic, Strategy, Failure).
"""

from __future__ import annotations
import json
import os
from typing import List, Dict, Any, Optional

class MemorySystem:
    """Manages multi-tiered agent memory for autonomous decision making."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or os.path.dirname(os.path.abspath(__file__))
        self.short_term: List[Dict[str, Any]] = []
        self.episodic: List[Dict[str, Any]] = []
        self.strategy_memory: List[Dict[str, Any]] = []
        self.failure_memory: List[Dict[str, Any]] = []

    def record_turn(self, state_dict: Dict[str, Any], action: Dict[str, Any]):
        self.short_term.append({
            "step": state_dict.get("step"),
            "state": state_dict,
            "action": action
        })

    def record_episode(self, episode_id: str, final_wealth: float, opp_wealth: float, is_win: bool):
        record = {
            "episode_id": episode_id,
            "final_wealth": final_wealth,
            "opp_wealth": opp_wealth,
            "margin": final_wealth - opp_wealth,
            "is_win": is_win,
            "trajectory_len": len(self.short_term)
        }
        self.episodic.append(record)
        if is_win:
            self.strategy_memory.append(record)
        else:
            self.failure_memory.append(record)

    def clear_short_term(self):
        self.short_term = []

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_episodes": len(self.episodic),
            "wins": len(self.strategy_memory),
            "losses": len(self.failure_memory),
            "win_rate": (len(self.strategy_memory) / max(1, len(self.episodic))) * 100.0
        }
