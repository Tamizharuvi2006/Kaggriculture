//! EXP191 — State-Conditioned Decision Policy.
//! Implements the empirical 2D Decision Surface discovered in EXP191.

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::{Product, MarketOrder};
use crate::farm::Animal;
use crate::policies::{Policy, AdaptiveTerminalPolicy};

pub struct AdaptiveDecisionPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
}

impl AdaptiveDecisionPolicy {
    pub fn new() -> Self {
        Self {
            name: "adaptive_decision",
            base_policy: AdaptiveTerminalPolicy::new(),
        }
    }
}

impl Policy for AdaptiveDecisionPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let day = state.day;

        // Day 8 Livestock Decision Surface derived from EXP191
        if (7..=9).contains(&day) {
            let money = state.farms[player_idx].money;
            let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;

            let optimal_sheep: usize = if money < 1400.0 {
                0
            } else if money < 2200.0 {
                if p_milk < 175.0 { 2 } else { 1 }
            } else {
                2
            };

            let mut sheep_bought = 0;
            base_action.market.retain_mut(|order| {
                if let MarketOrder::BuyAnimal(Animal::Sheep, count) = order {
                    if sheep_bought >= optimal_sheep {
                        false // Cancel excess sheep
                    } else {
                        let allowed = (*count).min(optimal_sheep as i64 - sheep_bought as i64);
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
