//! Genuine Tier 2 (1000–1200 Elo) Benchmark: AgroHybridPolicy.
//! Combines V4.1 melon/cow kickstart with smooth Day 10 Strawberry scaling.

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::MarketOrder;
use crate::farm::{Animal, Crop};
use crate::policies::{Policy, V41Policy};

pub struct AgroHybridPolicy {
    name: &'static str,
    base_policy: V41Policy,
}


impl AgroHybridPolicy {
    pub fn new() -> Self {
        Self {
            name: "agro_hybrid_t2",
            base_policy: V41Policy::new(),
        }
    }
}

impl Policy for AgroHybridPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut act = self.base_policy.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];

        // Day 10-18: Scaled Strawberry onboarding
        if (10..=18).contains(&day) && hour == 0 {
            let money = farm.money;
            let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
            if straw_seeds < 10 && money >= 400.0 {
                let buy_count = ((money - 200.0) / 20.0).floor().min(10.0) as i64;
                if buy_count > 0 {
                    act.market.push(MarketOrder::BuySeed(Crop::Strawberry, buy_count));
                }
            }
        }

        // Mid-game sheep onboarding if cash is healthy
        if day == 8 && hour == 4 && farm.money >= 1800.0 {
            act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
        }

        act
    }
}
