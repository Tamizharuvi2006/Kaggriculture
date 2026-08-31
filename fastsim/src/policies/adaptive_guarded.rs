//! EXP188 — Adaptive Liquidity-Guarded Policy.
//! Eliminates the Day 8 Over-Expansion Liquidity Trap (cancels animal purchases if post_cash < $800).

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::MarketOrder;
use crate::policies::{Policy, AdaptiveTerminalPolicy};

pub struct AdaptiveGuardedPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
}

impl AdaptiveGuardedPolicy {
    pub fn new() -> Self {
        Self {
            name: "adaptive_guarded",
            base_policy: AdaptiveTerminalPolicy::new(),
        }
    }
}

impl Policy for AdaptiveGuardedPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let day = state.day;

        // Day 8 & Day 9 Liquidity Guard: Never buy an animal if post-buy working capital falls below $800
        if (7..=9).contains(&day) {
            let money = state.farms[player_idx].money;
            base_action.market.retain(|order| {
                if let MarketOrder::BuyAnimal(animal, count) = order {
                    let cost = match animal {
                        crate::farm::Animal::Cow => 800.0 * (*count as f64),
                        crate::farm::Animal::Sheep => 600.0 * (*count as f64),
                        crate::farm::Animal::Goose => 400.0 * (*count as f64),
                    };

                    money - cost >= 800.0 // REJECT if post-cash < $800
                } else {
                    true
                }
            });
        }

        base_action
    }
}
