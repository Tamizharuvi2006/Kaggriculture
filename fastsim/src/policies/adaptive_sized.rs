//! EXP190 — State-Conditioned Sized Livestock Policy.
//! Implements the EXP189 Decision Surface: Sizing Day 8 livestock purchases to 1 Sheep (retaining >$1,000 reserve).

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::MarketOrder;
use crate::farm::Animal;
use crate::policies::{Policy, AdaptiveTerminalPolicy};

pub struct AdaptiveSizedPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
}

impl AdaptiveSizedPolicy {
    pub fn new() -> Self {
        Self {
            name: "adaptive_sized",
            base_policy: AdaptiveTerminalPolicy::new(),
        }
    }
}

impl Policy for AdaptiveSizedPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let day = state.day;

        // Day 8 Livestock Sizing Governor derived from EXP189 Decision Surface
        if (7..=9).contains(&day) {
            let money = state.farms[player_idx].money;
            let max_sheep = if money >= 2400.0 { 2 } else if money >= 1200.0 { 1 } else { 0 };

            let mut sheep_bought = 0;
            base_action.market.retain_mut(|order| {
                if let MarketOrder::BuyAnimal(Animal::Sheep, count) = order {
                    if sheep_bought >= max_sheep {
                        false // Cancel excess sheep
                    } else {
                        let allowed = (*count).min(max_sheep as i64 - sheep_bought as i64);
                        if allowed > 0 {
                            *count = allowed;
                            sheep_bought += allowed as usize;
                            true
                        } else {
                            false
                        }
                    }
                } else {
                    true
                }
            });
        }

        base_action
    }
}
