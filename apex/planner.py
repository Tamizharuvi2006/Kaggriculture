"""L+ APEX 2.5-E: Candidate Action Planner with Zero-Cost Sell Batch & Market Substitution.
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState, SELLABLE, CROPS

class ActionPlanner:
    """APEX 2.5 Action Planner Engine:
    Generates zero-capital-cost alternative candidate actions:
    1. Sell Batch Sizing (25%, 50%, 75%, 100%)
    2. High-Value Liquidation Preference
    3. Safe Opening Seed Alternatives (when cash is ample)
    """

    @staticmethod
    def generate_market_candidates(state: WorldState, expert_act: Dict[str, Any] = None) -> List[List[Any]]:
        candidates: List[List[Any]] = []

        # -----------------------------------------------------------------
        # 1. Family #1: Expert Sell Order Variations (Sell Quantity Divergence)
        # -----------------------------------------------------------------
        if expert_act and "market" in expert_act:
            for ord in expert_act["market"]:
                if len(ord) > 1 and ord[0] == "SELL":
                    item = ord[1]
                    expert_qty = ord[2] if len(ord) > 2 else 1
                    # Generate alternative batch fractions
                    alt_qtys = {max(1, int(expert_qty * 0.5)), max(1, expert_qty + 1), max(1, expert_qty - 1)}
                    for q in alt_qtys:
                        if q != expert_qty:
                            candidates.append([["SELL", item, q]])

        # -----------------------------------------------------------------
        # 2. Family #2: Inventory & Ready Harvest Sell Batch Breakpoints
        # -----------------------------------------------------------------
        for item in ("STRAWBERRY", "MELON", "MILK", "WOOL", "WHEAT", "CARROT", "TOMATO"):
            inv_qty = state.inventory.get(item, 0)
            ready_qty = sum(t.get("yield", 0) for t in state.ready_harvests if t.get("crop") == item)
            total_avail = inv_qty + ready_qty

            if total_avail > 0:
                pcts = [0.25, 0.50, 0.75, 1.00]
                for pct in pcts:
                    batch_qty = max(1, int(total_avail * pct))
                    candidates.append([["SELL", item, batch_qty]])

        # -----------------------------------------------------------------
        # 3. Family #3: High-Value Liquidation Preference Orders
        # -----------------------------------------------------------------
        high_val_items = [
            (item, float(state.prices.get(item, 0.0)))
            for item in ("STRAWBERRY", "MELON", "MILK", "WOOL")
            if state.inventory.get(item, 0) > 0 or any(t.get("crop") == item for t in state.ready_harvests)
        ]
        high_val_items.sort(key=lambda x: x[1], reverse=True)

        if len(high_val_items) >= 1:
            best_item = high_val_items[0][0]
            best_qty = max(1, state.inventory.get(best_item, 1))
            candidates.append([["SELL", best_item, best_qty]])

        # -----------------------------------------------------------------
        # 4. Safe Candidate Return (No Artificial Fallback Candidates)
        # -----------------------------------------------------------------
        return candidates

