use crate::engine::state::GameState;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const CHECKPOINT_STEPS: [usize; 23] = [
    0, 72, 120, 144, 168, 216, 240, 264, 288, 312, 336, 360,
    480, 600, 672, 695, 696, 700, 705, 710, 715, 719, 720,
];

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CheckpointSnapshot {
    pub step: usize,
    pub day: usize,
    pub hour: usize,
    pub hero_cash: f64,
    pub opp_cash: f64,
    pub market_prices: HashMap<String, i64>,
    pub market_inventory: HashMap<String, i64>,
    pub hero_quads: usize,
    pub opp_quads: usize,
    pub hero_hands: usize,
    pub opp_hands: usize,
    pub hero_farmer_pos: (usize, usize),
    pub opp_farmer_pos: (usize, usize),
    pub hero_shed: HashMap<String, i64>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EpisodeTrace {
    pub seed: u64,
    pub hero_seat: usize,
    pub hero_policy: String,
    pub opp_policy: String,
    pub final_rewards: [f64; 2],
    pub hero_won: bool,
    pub checkpoints: HashMap<String, CheckpointSnapshot>,
}

impl EpisodeTrace {
    pub fn new(seed: u64, hero_seat: usize, hero_policy: &str, opp_policy: &str) -> Self {
        Self {
            seed,
            hero_seat,
            hero_policy: hero_policy.to_string(),
            opp_policy: opp_policy.to_string(),
            final_rewards: [0.0, 0.0],
            hero_won: false,
            checkpoints: HashMap::new(),
        }
    }

    pub fn record_checkpoint(&mut self, state: &GameState, hero_seat: usize) {
        let opp_seat = 1 - hero_seat;
        let hero_farm = &state.farms[hero_seat];
        let opp_farm = &state.farms[opp_seat];
        let hero_priv = &state.privates[hero_seat];

        let mut market_prices = HashMap::new();
        let mut market_inventory = HashMap::new();
        for (k, v) in &state.market.prices {
            market_prices.insert(k.name().to_string(), *v);
        }
        for (k, v) in &state.market.inventory {
            market_inventory.insert(k.name().to_string(), *v);
        }

        let snap = CheckpointSnapshot {
            step: state.step,
            day: state.day,
            hour: state.hour,
            hero_cash: hero_farm.money,
            opp_cash: opp_farm.money,
            market_prices,
            market_inventory,
            hero_quads: hero_farm.unlocked_quadrants.len(),
            opp_quads: opp_farm.unlocked_quadrants.len(),
            hero_hands: hero_farm.hands.len(),
            opp_hands: opp_farm.hands.len(),
            hero_farmer_pos: hero_farm.farmer,
            opp_farmer_pos: opp_farm.farmer,
            hero_shed: hero_priv.shed.clone(),
        };

        self.checkpoints.insert(format!("Step_{}", state.step), snap);
    }
}
