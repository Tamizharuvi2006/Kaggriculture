"""Terminal match valuation and future wealth projection."""
from __future__ import annotations
from typing import Dict, Any
from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketState
from engine.state.opponent_state import OpponentState
from engine.economy.crop_roi import CropROIValuator

class TerminalValuator:
    """Projects expected final wealth at Turn 720 for a given farm state."""

    @staticmethod
    def project_terminal_wealth(
        obs: Observation,
        farm: FarmState,
        market: MarketState,
        opponent: OpponentState,
    ) -> float:
        day = obs.day
        remaining_days = max(0.0, 30.0 - day)
        
        # 1. Current liquid cash
        wealth = farm.money

        # 2. Shed inventory liquidation value
        for item, qty in farm.shed.items():
            if qty > 0:
                p = market.price(item)
                wealth += qty * p * 0.95

        # 3. Active standing crops future net revenue
        for crop, tiles in farm.plants_by_crop.items():
            if tiles:
                econ = CropROIValuator.evaluate_crop(crop, obs, market, opponent, planned_batch_qty=len(tiles))
                # Standing crops have already paid seed cost
                standing_unit_val = econ.net_terminal_cash + econ.seed_cost
                wealth += max(0.0, standing_unit_val * len(tiles))

        # 4. Livestock future cashflow (Cows produce ~1 milk/day @ ~$180)
        cows_count = len(farm.animals_by_type.get("COW", []))
        if cows_count > 0:
            milk_p = market.price("MILK")
            daily_rev_per_cow = milk_p * 0.95
            feed_cost_per_cow = market.price("WHEAT")
            net_daily_per_cow = max(0.0, daily_rev_per_cow - feed_cost_per_cow)
            wealth += cows_count * net_daily_per_cow * remaining_days

        # 5. Subtract projected worker wage obligations
        num_workers = farm.num_workers
        wealth -= max(0.0, (num_workers - 1) * 50.0 * (remaining_days / 1.0))

        return round(wealth, 1)
