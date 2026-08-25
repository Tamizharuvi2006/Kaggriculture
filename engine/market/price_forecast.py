"""Price forecaster integrating town drain and estimated opponent supply."""
from __future__ import annotations
import math
from typing import Dict, Any
from engine.state.market_state import MarketState, MARKET_PARAMS, MARKET_I0, PRICE_FLOOR
from engine.state.opponent_state import OpponentState

class PriceForecaster:
    """Forecasts expected sale prices over given harvest horizons."""

    @staticmethod
    def forecast_sale_price(
        product: str,
        horizon_days: float,
        planned_batch_qty: int,
        market: MarketState,
        opponent: OpponentState
    ) -> float:
        p_cfg = MARKET_PARAMS.get(product, {"base": 25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt", "above_func": "sqrt"})
        base_price = float(p_cfg["base"])
        current_inv = market.inventory.get(product, float(MARKET_I0))
        T = float(p_cfg["T"])

        # 1. Project town consumption over the horizon
        drain_units = market.town_drain_rate(product) * (horizon_days * 24.0)
        
        # 2. Project opponent dumping impact
        opp_inv = opponent.inventory.get(product)
        expected_opp_dump = (opp_inv.estimate * opp_inv.dump_probability) if opp_inv else 0.0

        # 3. Projected market inventory right before our sale
        projected_inv = current_inv - drain_units + expected_opp_dump
        
        # 4. Average price we will receive across our batch of size `planned_batch_qty`
        # Because selling per unit moves inventory linearly, integrate over [projected_inv, projected_inv + batch]
        start_inv = projected_inv
        end_inv = projected_inv + max(1, planned_batch_qty)
        mid_inv = (start_inv + end_inv) / 2.0

        if mid_inv < MARKET_I0:
            drained = MARKET_I0 - mid_inv
            u = drained / T
            func = p_cfg.get("below_func", "linear")
            below_target = float(p_cfg.get("below_target", 0.40))
            if func == "hinge":
                shape = u + 8.0 * max(0.0, u - 1.0) ** 2
            elif func == "sqrt":
                shape = math.sqrt(drained) / math.sqrt(T)
            elif func == "log":
                shape = math.log(1.0 + drained) / math.log(1.0 + T)
            else:
                shape = u
            price = base_price + (below_target * base_price) * shape
        else:
            glut = mid_inv - MARKET_I0
            func = p_cfg.get("above_func", "linear")
            above_target = float(p_cfg.get("above_target", 0.40))
            if func == "sqrt":
                shape = math.sqrt(glut) / math.sqrt(T)
            elif func == "sq":
                shape = (glut / T) ** 2
            elif func == "linear":
                shape = glut / T
            else:
                shape = math.log(1.0 + glut) / math.log(1.0 + T)
            price = base_price - (above_target * base_price) * shape

        return max(float(PRICE_FLOOR), float(round(price, 1)))
