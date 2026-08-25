"""Market order generation and dual-regime execution engine."""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from engine.state.observation import Observation, SELLABLE, CROPS, ANIMALS
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketState
from engine.state.opponent_state import OpponentState
from engine.safety.solvency import SolvencyGuard
from engine.safety.feed_buffer import FeedBufferGuard
from engine.safety.legality import LegalityGuard
from engine.economy.land_roi import LandROIValuator
from engine.strategy.scarcity_pivot import ScarcityDecision

class MarketExecutor:
    """Generates optimal market orders respecting dual-regime liquidity and solvency."""

    @staticmethod
    def generate_orders(
        obs: Observation,
        farm: FarmState,
        market: MarketState,
        opponent: OpponentState,
        scarcity_decision: Optional[ScarcityDecision] = None,
    ) -> List[List[Any]]:
        orders: List[List[Any]] = []
        budget = farm.money
        day = obs.day
        step = obs.step
        unlocked = farm.unlocked_quadrants
        safe_buffer = SolvencyGuard.get_safe_cash_buffer(unlocked)
        is_constrained = SolvencyGuard.is_cash_constrained(farm)

        # -------------------------------------------------------------
        # 1. CASH GENERATION / LIQUIDATION (DUAL-REGIME)
        # -------------------------------------------------------------
        # Fertilizer sales
        fert_qty = farm.shed.get("FERTILIZER", 0)
        if fert_qty > 0:
            orders.append(["SELL", "FERTILIZER", fert_qty])
            budget += fert_qty * market.price("FERTILIZER") * 0.95

        # Sellable crops and livestock goods
        for item in ("STRAWBERRY", "MILK", "MELON", "CARROT", "TOMATO", "WOOL", "EGG"):
            qty = farm.shed.get(item, 0)
            if qty <= 0:
                continue
            
            p = market.price(item)
            vel = market.velocity(item)

            if is_constrained:
                # REGIME 1: Cash Constrained -> Unconditional immediate sale
                orders.append(["SELL", item, qty])
                budget += qty * p * 0.95
            else:
                # REGIME 2: Cash Flushed -> Favorable market timing
                # Suppress sales only during steep downward price drops
                if item == "STRAWBERRY" and p < 115.0 and vel < 0:
                    continue
                elif item == "MILK" and p < 120.0 and vel < 0:
                    continue
                orders.append(["SELL", item, qty])
                budget += qty * p * 0.95

        # Safe Wheat Surplus Sale
        safe_wheat_sell = FeedBufferGuard.max_safe_wheat_to_sell(farm, day)
        if safe_wheat_sell > 0:
            orders.append(["SELL", "WHEAT", safe_wheat_sell])
            budget += safe_wheat_sell * market.price("WHEAT") * 0.95

        # -------------------------------------------------------------
        # 2. LABOR MAINTENANCE (CRITICAL HIRES)
        # -------------------------------------------------------------
        target_workers = 13 if len(unlocked) >= 3 else (9 if len(unlocked) >= 2 else 5)
        hires_needed = max(0, target_workers - farm.num_workers)
        hires_done = 0
        
        while hires_done < hires_needed and len(orders) < 8:
            hire_cost = 1 if farm.hires_today == 0 else (2 if farm.hires_today == 1 else 3)
            if budget - hire_cost < (0 if is_constrained else 50.0):
                break
            orders.append(["HIRE"])
            budget -= hire_cost
            hires_done += 1

        # -------------------------------------------------------------
        # 3. FEED SECURITY (100% COW FEED CONTINUITY)
        # -------------------------------------------------------------
        feed_deficit = FeedBufferGuard.calculate_feed_deficit(farm, day)
        if feed_deficit > 0 and len(orders) < 8:
            wheat_p = market.price("WHEAT")
            buy_qty = min(feed_deficit, int(budget // max(1.0, wheat_p)))
            if buy_qty > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", buy_qty])
                budget -= buy_qty * wheat_p

        # -------------------------------------------------------------
        # 4. CAPITAL LAND EXPANSION
        # -------------------------------------------------------------
        land_eval = LandROIValuator.evaluate_land_expansion(unlocked, day, budget, safe_buffer)
        if land_eval.get("should_buy", False) and len(orders) < 9:
            orders.append(["BUY_LAND"])
            budget -= land_eval["cost"]

        # -------------------------------------------------------------
        # 5. SEED PURCHASES (BASELINE OR SCARCITY PIVOT)
        # -------------------------------------------------------------
        target_crop = scarcity_decision.chosen_crop if scarcity_decision else ("MELON" if day <= 2 else "STRAWBERRY")
        seed_cfg = CROPS.get(target_crop, {"seed": 100})
        seed_cost = float(seed_cfg["seed"])
        
        # Calculate needed seeds
        existing_seeds = farm.seeds.get(target_crop, 0)
        standing_plants = len(farm.plants_by_crop.get(target_crop, []))
        desired_plants = 34 if len(unlocked) >= 2 else 16
        needed_seeds = max(0, desired_plants - standing_plants - existing_seeds)

        if needed_seeds > 0 and budget - safe_buffer >= seed_cost and len(orders) < 10:
            affordable = int(max(0, budget - safe_buffer) // seed_cost)
            buy_seed_qty = min(needed_seeds, affordable, 6)  # Buy in batches
            if buy_seed_qty > 0:
                orders.append(["BUY_SEED", target_crop, buy_seed_qty])
                budget -= buy_seed_qty * seed_cost

        # -------------------------------------------------------------
        # 6. ANIMAL EXPANSION (OPENING 2 COWS)
        # -------------------------------------------------------------
        num_cows = len(farm.animals_by_type.get("COW", []))
        if num_cows < 2 and day <= 2 and budget >= 450.0 and len(orders) < 10:
            orders.append(["BUY_ANIMAL", "COW", 1])
            budget -= 400.0

        return LegalityGuard.filter_market_orders(orders)
