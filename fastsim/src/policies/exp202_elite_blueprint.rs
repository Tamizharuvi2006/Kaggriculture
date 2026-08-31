//! EXP202 — Elite Macro Blueprint Policy.
//! Implements the 3000+ Elite Replay Blueprint:
//! 1. Day 2 (Step 50): Direct Wheat Feed Injection + Double Worker Hire + Early Melon Sowing.
//! 2. Day 3 (Step 80): Instant Cow Fertilizer Liquidation (+$800 instant cash).
//! 3. Day 6 (Step 160): 4th Cow Herd Reinvestment (scaling milk income to $640/day).
//! 4. Day 7 (Step 170): Quadrant 2 Land Expansion.
//! 5. Day 10 (Step 260): Melon Harvest Cash Liquidation (+$3,900 surge).
//! 6. Day 12 (Step 290): Multi-Worker Scaling (4-5 workers) + Bulk Feed + 4 Sheep.

use super::Policy;
use super::adaptive::AdaptiveTerminalPolicy;
use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::farm::{Animal, Crop, Tile};
use crate::market::{Product, MarketOrder};

pub struct EXP202EliteBlueprintPolicy {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl EXP202EliteBlueprintPolicy {
    pub fn new() -> Self {
        Self {
            base_adaptive: AdaptiveTerminalPolicy::new(),
        }
    }
}

impl Policy for EXP202EliteBlueprintPolicy {
    fn name(&self) -> &'static str {
        "exp202_elite_blueprint"
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let step = state.step;
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // 1. Day 2 (Step 50): Direct Wheat Feed Injection + 2 Workers + Melon Sowing
        if day == 2 && hour == 2 {
            if money >= 120.0 {
                action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4));
            }
            if money >= 80.0 && farm.hands.len() < 2 {
                action.market.push(MarketOrder::Hire);
                action.market.push(MarketOrder::Hire);
            }
            if money >= 50.0 {
                action.market.push(MarketOrder::BuySeed(Crop::Melon, 1));
            }
        }

        // 2. Day 3 (Step 80): Instant Cow Fertilizer Liquidation (+$400 - $800 cash injection)
        if day == 3 && hour == 8 {
            let fert_in_shed = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert_in_shed >= 2 {
                action.market.push(MarketOrder::Sell(Product::Fertilizer, fert_in_shed));
            }
        }

        // 3. Day 6 (Step 160): Fourth Cow Herd Reinvestment
        if day == 6 && hour == 16 {
            let mut cow_count = 0;
            for row in &farm.tiles {
                for tile in row {
                    if let Tile::Animal(a) = tile {
                        if a.animal == Animal::Cow { cow_count += 1; }
                    }
                }
            }
            if cow_count < 4 && money >= 1000.0 {
                action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
            }
        }

        // 4. Day 7 (Step 170): Quadrant 2 Land Expansion
        if day == 7 && hour == 2 {
            if farm.unlocked_quadrants.len() < 2 && money >= 500.0 {
                action.market.push(MarketOrder::BuyLand);
            }
            let wheat_in_shed = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
            if wheat_in_shed < 4 && money >= 200.0 {
                action.market.push(MarketOrder::BuyProduct(Product::Wheat, 6));
            }
        }

        // 5. Day 10 (Step 260): Melon Harvest Cash Liquidation
        if day == 10 && hour == 20 {
            let melon_in_shed = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melon_in_shed > 0 {
                action.market.push(MarketOrder::Sell(Product::Melon, melon_in_shed));
            }
        }

        // 6. Day 12 (Step 290): Multi-Worker Scaling (Hire up to 4 workers + bulk feed)
        if day == 12 && hour == 2 {
            if farm.hands.len() < 4 && money >= 200.0 {
                action.market.push(MarketOrder::Hire);
            }
            let wheat_in_shed = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
            if wheat_in_shed < 10 && money >= 500.0 {
                action.market.push(MarketOrder::BuyProduct(Product::Wheat, 15));
            }
        }

        // 7. Middle & Late Game Fertilizer Liquidation
        if step > 200 && step % 48 == 0 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 4 {
                let has_sell_fert = action.market.iter().any(|o| matches!(o, MarketOrder::Sell(Product::Fertilizer, _)));
                if !has_sell_fert {
                    action.market.push(MarketOrder::Sell(Product::Fertilizer, fert));
                }
            }
        }

        action
    }
}
