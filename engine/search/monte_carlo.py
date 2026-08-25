"""Monte Carlo rollout and decision override engine layered on Variant D."""
from __future__ import annotations
import copy
from typing import Dict, Any, List, Tuple, Optional

from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketState
from engine.search.evaluator import StateEvaluator

class MonteCarloOverrideEngine:
    """Evaluates high-impact discrete branch overrides against Variant D."""

    @staticmethod
    def evaluate_decision_overrides(
        obs: Observation,
        farm: FarmState,
        market: MarketState,
        variant_d_action: Dict[str, Any],
        min_override_margin: float = 150.0,
    ) -> Dict[str, Any]:
        step = obs.step
        day = obs.day
        hour = obs.hour
        remaining_days = obs.remaining_days

        # Only evaluate branch points on high-impact milestones to conserve CPU time
        # 1. Late-game Hiring Decision (Days 18-26)
        # 2. Ambiguous Price Inflection Selling
        is_hiring_turn = any(len(m) >= 1 and m[0] == "HIRE" for m in variant_d_action.get("market", []))
        has_large_inventory = (farm.shed.get("STRAWBERRY", 0) >= 6 or farm.shed.get("MILK", 0) >= 6)

        if not (is_hiring_turn or has_large_inventory):
            return variant_d_action

        # Generate Candidate Overrides
        candidates: List[Tuple[str, Dict[str, Any]]] = [("VARIANT_D", variant_d_action)]

        # Candidate 2: Suppress Hiring (Save wages in late game)
        if is_hiring_turn and day >= 20:
            suppressed_act = copy.deepcopy(variant_d_action)
            suppressed_act["market"] = [m for m in suppressed_act["market"] if m[0] != "HIRE"]
            candidates.append(("SUPPRESS_HIRE", suppressed_act))

        # Candidate 3: Batch Selling Hold (Hold for price rebound if velocity is positive)
        p_straw = market.price("STRAWBERRY")
        v_straw = market.velocity("STRAWBERRY")
        if p_straw < 135.0 and v_straw > 0 and has_large_inventory:
            hold_act = copy.deepcopy(variant_d_action)
            hold_act["market"] = [m for m in hold_act["market"] if not (len(m) >= 2 and m[0] == "SELL" and m[1] in ("STRAWBERRY", "MILK"))]
            candidates.append(("HOLD_LIQUIDATION_1_DAY", hold_act))

        # Evaluate Candidates via Forward Projection
        standing_straw = len(farm.plants_by_crop.get("STRAWBERRY", []))
        standing_cows = len(farm.animals_by_type.get("COW", []))
        market_prices = {item: market.price(item) for item in ("STRAWBERRY", "MILK", "WHEAT", "CARROT", "TOMATO", "MELON", "WOOL")}

        scores = {}
        for name, cand_act in candidates:
            # Estimate immediate cash flow from cand_act
            cash_delta = 0.0
            workers_delta = 0
            sim_shed = dict(farm.shed)

            for m in cand_act.get("market", []):
                if m[0] == "HIRE":
                    cash_delta -= 10.0  # Approx hire fee
                    workers_delta += 1
                elif m[0] == "SELL" and len(m) >= 3:
                    item, qty = m[1], int(m[2])
                    cash_delta += qty * market_prices.get(item, 100.0) * 0.95
                    sim_shed[item] = max(0, sim_shed.get(item, 0) - qty)

            sim_money = farm.money + cash_delta
            sim_workers = farm.num_workers + workers_delta

            ev = StateEvaluator.evaluate_terminal_wealth(
                current_money=sim_money,
                standing_strawberries=standing_straw,
                standing_cows=standing_cows,
                shed_inventory=sim_shed,
                market_prices=market_prices,
                remaining_days=remaining_days,
                num_workers=sim_workers,
            )
            scores[name] = ev

        best_cand_name, best_ev = max(scores.items(), key=lambda x: x[1])
        variant_d_ev = scores["VARIANT_D"]

        # Safety Gate: Only override Variant D if EV strictly beats it by min_override_margin
        if best_cand_name != "VARIANT_D" and (best_ev - variant_d_ev) >= min_override_margin:
            for name, act in candidates:
                if name == best_cand_name:
                    return act

        return variant_d_action
