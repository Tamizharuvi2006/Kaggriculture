"""Exact v1.32.7 Scarcity Knee Detector and Runaway Acceleration Valuation."""
from __future__ import annotations
import math
from typing import Dict, Any, Optional
from engine.state.market_state import MarketState, MARKET_PARAMS, MARKET_I0
from engine.state.opponent_state import OpponentState

class ScarcityReport:
    """Detailed scarcity analysis for a single commodity."""
    def __init__(
        self,
        product: str,
        price: float,
        base_price: float,
        inventory: float,
        u_ratio: float,
        knee_status: str,  # "BELOW_KNEE", "APPROACHING_KNEE", "IN_RUNAWAY_KNEE", "GLUT"
        velocity: float,
        acceleration: float,
        projected_peak_price: float,
        scarcity_index: float,
        opponent_risk_discount: float,
        effective_upside: float,
    ):
        self.product = product
        self.price = price
        self.base_price = base_price
        self.inventory = inventory
        self.u_ratio = u_ratio
        self.knee_status = knee_status
        self.velocity = velocity
        self.acceleration = acceleration
        self.projected_peak_price = projected_peak_price
        self.scarcity_index = scarcity_index
        self.opponent_risk_discount = opponent_risk_discount
        self.effective_upside = effective_upside

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product": self.product,
            "price": round(self.price, 1),
            "base_price": self.base_price,
            "inventory": round(self.inventory, 1),
            "u_ratio": round(self.u_ratio, 3),
            "knee_status": self.knee_status,
            "velocity": round(self.velocity, 2),
            "acceleration": round(self.acceleration, 2),
            "projected_peak_price": round(self.projected_peak_price, 1),
            "scarcity_index": round(self.scarcity_index, 3),
            "opponent_risk_discount": round(self.opponent_risk_discount, 3),
            "effective_upside": round(self.effective_upside, 1),
        }

class ScarcityDetector:
    """Scarcity Detector implementing the exact v1.32.7 Hinge Pricing Dynamics."""

    @staticmethod
    def evaluate(product: str, market: MarketState, opponent: OpponentState) -> ScarcityReport:
        p_cfg = MARKET_PARAMS.get(product, {"base": 25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt"})
        base_price = float(p_cfg["base"])
        current_price = market.price(product)
        inv = market.inventory.get(product, float(MARKET_I0))
        T = float(p_cfg["T"])
        func = p_cfg.get("below_func", "linear")

        # Compute u ratio: normalized scarcity depth
        drained = max(0.0, float(MARKET_I0) - inv)
        u_ratio = drained / max(1.0, T) if inv < MARKET_I0 else 0.0

        vel = market.velocity(product, window=2)
        acc = market.acceleration(product)

        # Knee classification
        if inv >= MARKET_I0:
            knee_status = "GLUT"
        elif u_ratio >= 1.0:
            knee_status = "IN_RUNAWAY_KNEE"
        elif u_ratio >= 0.70 or current_price >= base_price * 1.30:
            knee_status = "APPROACHING_KNEE"
        else:
            knee_status = "BELOW_KNEE"

        # Theoretical peak price under continued town drain (next 48 steps / 2 days)
        drain_rate = market.town_drain_rate(product)
        projected_drain = drained + (drain_rate * 48.0)
        u_proj = projected_drain / max(1.0, T)
        
        if func == "hinge":
            shape_proj = u_proj + 8.0 * max(0.0, u_proj - 1.0) ** 2
            below_target = float(p_cfg.get("below_target", 0.40))
            projected_peak_price = base_price + (below_target * base_price) * shape_proj
        elif func == "sqrt":
            shape_proj = math.sqrt(projected_drain) / math.sqrt(T)
            below_target = float(p_cfg.get("below_target", 0.70))
            projected_peak_price = base_price + (below_target * base_price) * shape_proj
        else:
            projected_peak_price = current_price * 1.10

        # Opponent risk discount: if opponent has large ready/growing stock, they can dump and kill the price
        opp_inv_info = opponent.inventory.get(product)
        opp_floor_risk = opp_inv_info.floor_risk if opp_inv_info else 0.0
        opp_dump_prob = opp_inv_info.dump_probability if opp_inv_info else 0.0
        
        # Risk discount factor in [0.10, 1.0]: 1.0 means zero opponent competition
        opponent_risk_discount = max(0.10, 1.0 - (opp_floor_risk * 0.70 + opp_dump_prob * 0.30))

        # Scarcity Index: normalized score combining price ratio, momentum, and scarcity depth
        price_ratio = current_price / max(1.0, base_price)
        momentum_mult = 1.20 if vel > 0 else (0.80 if vel < 0 else 1.0)
        scarcity_index = (price_ratio * 0.4 + u_ratio * 0.6) * momentum_mult

        # Effective upside: projected peak price discounted by opponent crash risk
        effective_upside = max(current_price, projected_peak_price * opponent_risk_discount)

        return ScarcityReport(
            product=product,
            price=current_price,
            base_price=base_price,
            inventory=inv,
            u_ratio=u_ratio,
            knee_status=knee_status,
            velocity=vel,
            acceleration=acc,
            projected_peak_price=projected_peak_price,
            scarcity_index=scarcity_index,
            opponent_risk_discount=opponent_risk_discount,
            effective_upside=effective_upside
        )
