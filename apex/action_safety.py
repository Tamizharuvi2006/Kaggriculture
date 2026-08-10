"""L+ APEX 2.3: Hard Action & Liquidity Safety Gate Engine (Fixed Command Unwrapping).
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState, CROPS, ANIMALS

class ActionSafetyGate:
    """Evaluates candidate actions against hard liquidity, worker, and terminal safety bounds:
    1. Liquidity & Disposable Cash Check
    2. Worker Continuity & Hiring Reserve
    3. Terminal Step Maturity Check (Must mature before Step 720)
    4. Bankruptcy & Operating Floor Preservation
    """

    @staticmethod
    def calculate_disposable_cash(state: WorldState) -> float:
        """Calculates disposable cash after subtracting mandatory operating reserve."""
        num_workers = max(1, len(state.workers))
        worker_maintenance = num_workers * 50.0  # Daily worker maintenance allowance
        safety_margin = 300.0 if state.day <= 20 else 150.0  # Dynamic operating floor
        
        mandatory_reserve = worker_maintenance + safety_margin
        disposable = max(0.0, state.money - mandatory_reserve)
        return disposable

    @staticmethod
    def is_action_safe(candidate: List[Any], state: WorldState) -> Tuple[bool, str]:
        if not candidate:
            return True, "SAFE_EMPTY"

        # Safely unwrap order lists (e.g. [["BUY_LAND", "NE"]] vs ["BUY_LAND", "NE"])
        first_ord = candidate[0] if isinstance(candidate, list) and len(candidate) > 0 else candidate
        if isinstance(first_ord, list) and len(first_ord) > 0:
            cmd = first_ord[0]
            ord_args = first_ord
        else:
            cmd = first_ord
            ord_args = candidate

        disposable_cash = ActionSafetyGate.calculate_disposable_cash(state)
        remaining = state.remaining_steps

        # 1. Terminal Phase Protection (Step >= 696 / Remaining <= 24)
        if remaining <= 24 and cmd != "SELL":
            return False, "REJECT_TERMINAL_WINDOW_PROTECTION"

        # 2. Market Sells are ALWAYS SAFE (generate cash, zero risk)
        if cmd == "SELL":
            return True, "SAFE_LIQUIDATION_SELL"

        # 3. Seed Buying Safety Audit
        if cmd == "BUY_SEED":
            crop = ord_args[1] if len(ord_args) > 1 else "WHEAT"
            qty = ord_args[2] if len(ord_args) > 2 else 1
            cfg = CROPS.get(crop, {})
            cost = cfg.get("seed", 10.0) * qty
            cycle_steps = cfg.get("first", 2) * 24

            if cost > disposable_cash:
                return False, f"REJECT_LIQUIDITY_STARVATION_COST_${cost:.1f}_VS_DISPOSABLE_${disposable_cash:.1f}"

            if remaining < cycle_steps:
                return False, f"REJECT_TERMINAL_IMMATURITY_NEED_{cycle_steps}_STEPS_HAVE_{remaining}"

            return True, "SAFE_SEED_INVESTMENT"

        # 4. Animal Buying Safety Audit
        if cmd == "BUY_ANIMAL":
            animal = ord_args[1] if len(ord_args) > 1 else "COW"
            cfg = ANIMALS.get(animal, {})
            cost = cfg.get("cost", 400.0)

            if cost > disposable_cash:
                return False, f"REJECT_LIQUIDITY_STARVATION_COST_${cost:.1f}"

            if remaining < 48:
                return False, "REJECT_TERMINAL_ANIMAL_IMMATURITY"

            return True, "SAFE_ANIMAL_INVESTMENT"

        # 5. Land Buying Safety Audit
        if cmd == "BUY_LAND":
            cost = 500.0
            if cost > disposable_cash:
                return False, f"REJECT_LIQUIDITY_STARVATION_LAND_COST_${cost:.1f}"

            if state.day >= 18:
                return False, "REJECT_LATE_LAND_EXPANSION"

            return True, "SAFE_LAND_EXPANSION"

        # 6. Hiring Safety Audit
        if cmd == "HIRE":
            cost = 100.0
            if cost > disposable_cash:
                return False, f"REJECT_HIRE_LIQUIDITY_COST_${cost:.1f}"

            if state.day >= 22:
                return False, "REJECT_LATE_GAME_HIRE"

            return True, "SAFE_HIRE"

        return True, "SAFE_DEFAULT"
