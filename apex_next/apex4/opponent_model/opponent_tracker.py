"""
APEX 4.0 Opponent Tracker
Tracks public and legal opponent state to infer expansion pacing and market demand.
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class OpponentTracker:
    """
    Infers opponent strategy, expansion rate, and crop maturity from public state only.
    """
    def __init__(self):
        self.opp_cash_history = []
        self.opp_unlocked_count = 1
        self.opp_expansion_velocity = "STANDARD"

    def update(self, world_model):
        self.opp_cash_history.append(world_model.opp_money)
        self.opp_unlocked_count = len(world_model.opp_unlocked_quadrants)
        
        # Infer expansion velocity
        if world_model.step <= 160 and self.opp_unlocked_count >= 2:
            self.opp_expansion_velocity = "FAST_EXPANDER"
        elif world_model.step > 200 and self.opp_unlocked_count == 1:
            self.opp_expansion_velocity = "SLOW_EXPANDER"
        else:
            self.opp_expansion_velocity = "STANDARD"

    def should_accelerate_land(self, world_model):
        # If opponent expanded early and our cash allows, accelerate land purchase
        return (self.opp_expansion_velocity == "FAST_EXPANDER" and 
                len(world_model.unlocked_quadrants) == 1 and 
                world_model.money >= 1000.0)
