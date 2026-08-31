//! Adaptive Terminal Policy (D.1 + Step 360-696 Price Governor + 3-Quadrant Guardrail).

use super::Policy;
use super::d1::D1Policy;
use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::{Product, MarketOrder};

pub struct AdaptiveTerminalPolicy {
    d1: D1Policy,
}

impl AdaptiveTerminalPolicy {
    pub fn new() -> Self {
        Self {
            d1: D1Policy::new(),
        }
    }
}

impl Policy for AdaptiveTerminalPolicy {
    fn name(&self) -> &'static str {
        "adaptive"
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.d1.act(state, player_idx);
        let step = state.step;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];

        // 1. Enforce strict 3-quadrant ceiling guardrail
        if farm.unlocked_quadrants.len() >= 3 {
            base_action.market.retain(|order| !matches!(order, MarketOrder::BuyLand));
        }

        // 2. Middle-to-Late Game Liquidity & Price Timing Governor (Steps 360..=696)
        if step >= 360 && step <= 696 {
            let money = farm.money;
            let straw_in_shed = *priv_farm.shed.get("STRAWBERRY").unwrap_or(&0);
            let milk_in_shed = *priv_farm.shed.get("MILK").unwrap_or(&0);

            let p_straw = *state.market.prices.get(&Product::Strawberry).unwrap_or(&120) as f64;
            let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;

            let safe_buffer = if step < 480 { 600.0 } else { 400.0 };
            let is_cash_constrained = money < safe_buffer;

            // Compute approximate velocity (or current deviation from base)
            let v_straw = 0.0; // In standard step, price updates per day/hour
            let v_milk = 0.0;

            if is_cash_constrained {
                // REGIME 1: Cash-Constrained. Unconditional liquidity execution!
                let has_sell_straw = base_action.market.iter().any(|o| matches!(o, MarketOrder::Sell(Product::Strawberry, _)));
                if straw_in_shed >= 2 && !has_sell_straw {
                    base_action.market.push(MarketOrder::Sell(Product::Strawberry, straw_in_shed));
                }

                let has_sell_milk = base_action.market.iter().any(|o| matches!(o, MarketOrder::Sell(Product::Milk, _)));
                if milk_in_shed >= 2 && !has_sell_milk {
                    base_action.market.push(MarketOrder::Sell(Product::Milk, milk_in_shed));
                }
            } else {
                // REGIME 2: Cash-Flushed. Gentle rebound market timing!
                base_action.market.retain(|order| {
                    if let MarketOrder::Sell(product, _) = order {
                        if *product == Product::Strawberry && p_straw < 115.0 && v_straw < 0.0 {
                            return false;
                        }
                        if *product == Product::Milk && p_milk < 95.0 && v_milk < 0.0 {
                            return false;
                        }
                    }
                    true
                });

                let has_sell_straw = base_action.market.iter().any(|o| matches!(o, MarketOrder::Sell(Product::Strawberry, _)));
                if p_straw >= 140.0 && straw_in_shed >= 4 && !has_sell_straw {
                    base_action.market.push(MarketOrder::Sell(Product::Strawberry, straw_in_shed));
                }

                let has_sell_milk = base_action.market.iter().any(|o| matches!(o, MarketOrder::Sell(Product::Milk, _)));
                if p_milk >= 115.0 && milk_in_shed >= 4 && !has_sell_milk {
                    base_action.market.push(MarketOrder::Sell(Product::Milk, milk_in_shed));
                }
            }
        }

        base_action
    }
}
