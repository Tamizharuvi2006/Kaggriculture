"""Marginal crop valuation and ROI calculation with comprehensive cost accounting."""
from __future__ import annotations
from typing import Dict, Any, Optional
from engine.state.observation import Observation, CROPS
from engine.state.market_state import MarketState
from engine.state.opponent_state import OpponentState
from engine.market.price_forecast import PriceForecaster

class CropEconomics:
    """Detailed economic breakdown for a crop planting decision."""
    def __init__(
        self,
        crop: str,
        seed_cost: float,
        feasible_waves: int,
        total_yield_units: int,
        forecasted_unit_price: float,
        gross_revenue: float,
        labor_cost: float,
        travel_cost: float,
        feed_opportunity_cost: float,
        market_slot_cost: float,
        completion_prob: float,
        sale_prob: float,
        net_terminal_cash: float,
        roi_per_tile_day: float,
    ):
        self.crop = crop
        self.seed_cost = seed_cost
        self.feasible_waves = feasible_waves
        self.total_yield_units = total_yield_units
        self.forecasted_unit_price = forecasted_unit_price
        self.gross_revenue = gross_revenue
        self.labor_cost = labor_cost
        self.travel_cost = travel_cost
        self.feed_opportunity_cost = feed_opportunity_cost
        self.market_slot_cost = market_slot_cost
        self.completion_prob = completion_prob
        self.sale_prob = sale_prob
        self.net_terminal_cash = net_terminal_cash
        self.roi_per_tile_day = roi_per_tile_day

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop": self.crop,
            "seed_cost": self.seed_cost,
            "feasible_waves": self.feasible_waves,
            "total_yield_units": self.total_yield_units,
            "forecasted_unit_price": round(self.forecasted_unit_price, 1),
            "gross_revenue": round(self.gross_revenue, 1),
            "labor_cost": round(self.labor_cost, 1),
            "travel_cost": round(self.travel_cost, 1),
            "feed_opportunity_cost": round(self.feed_opportunity_cost, 1),
            "completion_prob": round(self.completion_prob, 2),
            "sale_prob": round(self.sale_prob, 2),
            "net_terminal_cash": round(self.net_terminal_cash, 1),
            "roi_per_tile_day": round(self.roi_per_tile_day, 2),
        }

class CropROIValuator:
    """Comprehensive Marginal ROI Valuation Engine."""

    @staticmethod
    def evaluate_crop(
        crop: str,
        obs: Observation,
        market: MarketState,
        opponent: OpponentState,
        planned_batch_qty: int = 4,
        distance_from_shed: float = 3.0,
    ) -> CropEconomics:
        cfg = CROPS[crop]
        seed_cost = float(cfg["seed"])
        day = obs.day
        remaining_days = max(0.0, 30.0 - day)
        first_day = float(cfg["first"])
        interval = float(cfg.get("interval", 1) or 1)
        max_waves = int(cfg["max_yield"])
        is_ongoing = bool(cfg.get("ongoing", False))

        # Calculate feasible harvest waves before match ends at Day 30 (Turn 720)
        if remaining_days < first_day:
            feasible_waves = 0
        elif is_ongoing:
            extra_days = remaining_days - first_day
            extra_waves = int(extra_days // interval)
            feasible_waves = min(max_waves, 1 + extra_waves)
        else:
            feasible_waves = 1

        if feasible_waves <= 0:
            return CropEconomics(
                crop=crop,
                seed_cost=seed_cost,
                feasible_waves=0,
                total_yield_units=0,
                forecasted_unit_price=0.0,
                gross_revenue=0.0,
                labor_cost=0.0,
                travel_cost=0.0,
                feed_opportunity_cost=0.0,
                market_slot_cost=0.0,
                completion_prob=0.0,
                sale_prob=0.0,
                net_terminal_cash=-seed_cost,
                roi_per_tile_day=-999.0
            )

        units_per_wave = 4 if crop in ("CARROT", "TOMATO", "STRAWBERRY") else 6
        total_yield_units = feasible_waves * units_per_wave

        # Forecast sale price for this crop over its cycle horizon
        cycle_horizon_days = first_day + ((feasible_waves - 1) * interval if is_ongoing else 0.0)
        forecasted_unit_price = PriceForecaster.forecast_sale_price(
            crop, cycle_horizon_days, total_yield_units * planned_batch_qty, market, opponent
        )

        gross_revenue = total_yield_units * forecasted_unit_price

        # Cost Accounting:
        # 1. Labor cost: ~1 water action per day active (~$2/day equivalent wage share)
        days_active = min(remaining_days, cycle_horizon_days + 1)
        labor_cost = days_active * 2.5
        
        # 2. Travel/time cost: distance * $0.5
        travel_cost = distance_from_shed * 0.8
        
        # 3. Feed opportunity cost: if wheat, selling gives feed or seed
        feed_opportunity_cost = 0.0
        
        # 4. Market order slot cost
        market_slot_cost = 1.0

        # 5. Probabilistic execution discounts
        completion_prob = 0.96 if days_active <= 8 else 0.90
        # If opponent is heavy in this crop, sale success at forecasted price has discount
        opp_inv = opponent.inventory.get(crop)
        sale_prob = max(0.60, 1.0 - (opp_inv.floor_risk * 0.40)) if opp_inv else 0.95

        expected_gross = gross_revenue * completion_prob * sale_prob
        total_costs = seed_cost + labor_cost + travel_cost + feed_opportunity_cost + market_slot_cost

        net_terminal_cash = expected_gross - total_costs
        roi_per_tile_day = net_terminal_cash / max(1.0, days_active)

        return CropEconomics(
            crop=crop,
            seed_cost=seed_cost,
            feasible_waves=feasible_waves,
            total_yield_units=total_yield_units,
            forecasted_unit_price=forecasted_unit_price,
            gross_revenue=gross_revenue,
            labor_cost=labor_cost,
            travel_cost=travel_cost,
            feed_opportunity_cost=feed_opportunity_cost,
            market_slot_cost=market_slot_cost,
            completion_prob=completion_prob,
            sale_prob=sale_prob,
            net_terminal_cash=net_terminal_cash,
            roi_per_tile_day=roi_per_tile_day
        )
