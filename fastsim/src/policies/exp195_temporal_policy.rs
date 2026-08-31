//! EXP195 — Temporal Sequence Action Ranker Policy.
//! Combines 5-step historical state trajectories with ListNet Action Ranking and FastSim Lookahead Verification.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::farm::{Animal, Crop, Tile};
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use serde::Deserialize;
use std::sync::Mutex;

#[derive(Clone, Deserialize)]
pub struct TemporalRankingWeights {
    pub feature_cols: Vec<String>,
    pub state_mean: Vec<f32>,
    pub state_std: Vec<f32>,
    pub trunk_fc1_weight: Vec<Vec<f32>>,
    pub trunk_fc1_bias: Vec<f32>,
    pub trunk_ln1_weight: Vec<f32>,
    pub trunk_ln1_bias: Vec<f32>,
    pub trunk_fc2_weight: Vec<Vec<f32>>,
    pub trunk_fc2_bias: Vec<f32>,
    pub trunk_ln2_weight: Vec<f32>,
    pub trunk_ln2_bias: Vec<f32>,
    pub score_head_weight: Vec<Vec<f32>>,
    pub score_head_bias: Vec<f32>,
}

#[derive(Clone, Default)]
pub struct TemporalStepSnapshot {
    pub cash: f32,
    pub p_milk: f32,
    pub p_straw: f32,
    pub shed_wheat: f32,
    pub shed_milk: f32,
    pub cows: f32,
    pub sheep: f32,
    pub hands: f32,
    pub quads: f32,
    pub unwatered: f32,
    pub opp_cash: f32,
    pub opp_straws: f32,
}

pub struct EXP195TemporalPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: TemporalRankingWeights,
    history: Mutex<Vec<TemporalStepSnapshot>>,
}

impl EXP195TemporalPolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp195_ranking_weights.json");
        let weights: TemporalRankingWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp195_ranking_weights.json");

        Self {
            name: "exp195_temporal_policy",
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
            history: Mutex::new(Vec::new()),
        }
    }

    pub fn record_snapshot(&self, state: &GameState, player_idx: usize) {
        let opp_idx = 1 - player_idx;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let opp_farm = &state.farms[opp_idx];

        let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f32;
        let p_straw = *state.market.prices.get(&Product::Strawberry).unwrap_or(&120) as f32;
        let cash = farm.money as f32;
        let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0) as f32;
        let shed_milk = *priv_farm.shed.get("MILK").unwrap_or(&0) as f32;
        let hands = farm.hands.len() as f32;
        let quads = farm.unlocked_quadrants.len() as f32;

        let mut cows = 0;
        let mut sheep = 0;
        let mut unwatered = 0;

        for row in &farm.tiles {
            for tile in row {
                match tile {
                    Tile::Animal(a) => {
                        if a.animal == Animal::Cow { cows += 1; }
                        if a.animal == Animal::Sheep { sheep += 1; }
                    }
                    Tile::Plant(p) => {
                        if p.yield_units == 0 && !p.watered_today { unwatered += 1; }
                    }
                    _ => {}
                }
            }
        }

        let opp_cash = opp_farm.money as f32;
        let mut opp_straws = 0;
        for row in &opp_farm.tiles {
            for tile in row {
                if let Tile::Plant(p) = tile {
                    if p.crop == Crop::Strawberry { opp_straws += 1; }
                }
            }
        }

        let snap = TemporalStepSnapshot {
            cash,
            p_milk,
            p_straw,
            shed_wheat,
            shed_milk,
            cows: cows as f32,
            sheep: sheep as f32,
            hands,
            quads,
            unwatered: unwatered as f32,
            opp_cash,
            opp_straws: opp_straws as f32,
        };

        let mut h = self.history.lock().unwrap();
        h.push(snap);
        if h.len() > 10 {
            h.remove(0);
        }
    }

    pub fn get_60d_features(&self) -> [f32; 60] {
        let h = self.history.lock().unwrap();
        let mut feat = [0.0f32; 60];
        let n = h.len();

        for i in 0..5 {
            let snap = if n >= 5 - i {
                &h[n - (5 - i)]
            } else if n > 0 {
                &h[0]
            } else {
                continue;
            };

            let offset = i * 12;
            feat[offset] = snap.cash;
            feat[offset + 1] = snap.p_milk;
            feat[offset + 2] = snap.p_straw;
            feat[offset + 3] = snap.shed_wheat;
            feat[offset + 4] = snap.shed_milk;
            feat[offset + 5] = snap.cows;
            feat[offset + 6] = snap.sheep;
            feat[offset + 7] = snap.hands;
            feat[offset + 8] = snap.quads;
            feat[offset + 9] = snap.unwatered;
            feat[offset + 10] = snap.opp_cash;
            feat[offset + 11] = snap.opp_straws;
        }

        feat
    }

    pub fn forward(&self, features: &[f32; 60]) -> [f32; 6] {
        let w = &self.weights;
        let mut norm_feat = [0.0f32; 60];
        for i in 0..60 {
            norm_feat[i] = (features[i] - w.state_mean[i]) / w.state_std[i];
        }

        // Layer 1: 60 -> 128
        let mut h1 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.trunk_fc1_bias[i];
            for j in 0..60 { sum += w.trunk_fc1_weight[i][j] * norm_feat[j]; }
            h1[i] = sum;
        }

        let mean1: f32 = h1.iter().sum::<f32>() / 128.0;
        let var1: f32 = h1.iter().map(|v| (v - mean1).powi(2)).sum::<f32>() / 128.0;
        let std1 = (var1 + 1e-5).sqrt();
        for i in 0..128 {
            let norm = (h1[i] - mean1) / std1;
            h1[i] = (norm * w.trunk_ln1_weight[i] + w.trunk_ln1_bias[i]).max(0.0);
        }

        // Layer 2: 128 -> 64
        let mut h2 = vec![0.0f32; 64];
        for i in 0..64 {
            let mut sum = w.trunk_fc2_bias[i];
            for j in 0..128 { sum += w.trunk_fc2_weight[i][j] * h1[j]; }
            h2[i] = sum;
        }

        let mean2: f32 = h2.iter().sum::<f32>() / 64.0;
        let var2: f32 = h2.iter().map(|v| (v - mean2).powi(2)).sum::<f32>() / 64.0;
        let std2 = (var2 + 1e-5).sqrt();
        for i in 0..64 {
            let norm = (h2[i] - mean2) / std2;
            h2[i] = (norm * w.trunk_ln2_weight[i] + w.trunk_ln2_bias[i]).max(0.0);
        }

        // Score Head: 64 -> 6
        let mut scores = [0.0f32; 6];
        for i in 0..6 {
            let mut sum = w.score_head_bias[i];
            for j in 0..64 { sum += w.score_head_weight[i][j] * h2[j]; }
            scores[i] = sum;
        }

        scores
    }

    pub fn verify_action_gain(
        state: &GameState,
        player_idx: usize,
        cand_action: usize,
        base_act: &PlayerAction,
    ) -> f64 {
        let opp_policy = AdaptiveTerminalPolicy::new();
        let eval_policy = AdaptiveTerminalPolicy::new();

        let mut base_state = state.clone();
        let opp_act_0 = opp_policy.act(&base_state, 1 - player_idx);

        let actions_base = if player_idx == 0 {
            [base_act.clone(), opp_act_0.clone()]
        } else {
            [opp_act_0.clone(), base_act.clone()]
        };
        step_game(&mut base_state, &actions_base);

        while !base_state.done {
            let a0 = eval_policy.act(&base_state, 0);
            let a1 = opp_policy.act(&base_state, 1);
            step_game(&mut base_state, &[a0, a1]);
        }
        let base_reward = base_state.farms[player_idx].money;

        let mut cf_state = state.clone();
        let mut cand_hero_act = base_act.clone();

        match cand_action {
            1 => {
                cand_hero_act.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
            }
            2 => {
                if cf_state.farms[player_idx].money >= 40.0 {
                    cand_hero_act.market.push(MarketOrder::Hire);
                }
            }
            3 => {
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_state.farms[player_idx].money >= 600.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                }
            }
            4 => {
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_state.farms[player_idx].money >= 1200.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                }
            }
            5 => {
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_state.farms[player_idx].money >= 2400.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
                }
            }
            _ => {}
        }

        let actions_cf = if player_idx == 0 {
            [cand_hero_act, opp_act_0]
        } else {
            [opp_act_0, cand_hero_act]
        };
        step_game(&mut cf_state, &actions_cf);

        while !cf_state.done {
            let a0 = eval_policy.act(&cf_state, 0);
            let a1 = opp_policy.act(&cf_state, 1);
            step_game(&mut cf_state, &[a0, a1]);
        }
        let cf_reward = cf_state.farms[player_idx].money;

        cf_reward - base_reward
    }
}

impl Policy for EXP195TemporalPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        if state.step == 0 {
            self.history.lock().unwrap().clear();
        }

        self.record_snapshot(state, player_idx);
        let mut base_action = self.base_policy.act(state, player_idx);

        let step = state.step;
        let day = state.day;
        let hour = state.hour;

        let is_decision_step = step == 0 || (day == 6 && hour == 0) || (day == 8 && hour == 4);

        if is_decision_step {
            let features = self.get_60d_features();
            let scores = self.forward(&features);

            let mut best_a = 0;
            let mut max_s = scores[0];
            for a in 0..6 {
                if scores[a] > max_s {
                    max_s = scores[a];
                    best_a = a;
                }
            }

            // Execute challenger action only if top ranked action is NOT a0 and verifies positive
            if best_a != 0 {
                let verified_gain = Self::verify_action_gain(state, player_idx, best_a, &base_action);

                if verified_gain >= 100.0 {
                    match best_a {
                        1 => {
                            base_action.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
                        }
                        2 => {
                            if state.farms[player_idx].money >= 40.0 {
                                base_action.market.push(MarketOrder::Hire);
                            }
                        }
                        3 => {
                            base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                            if state.farms[player_idx].money >= 600.0 {
                                base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                            }
                        }
                        4 => {
                            base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                            if state.farms[player_idx].money >= 1200.0 {
                                base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                            }
                        }
                        5 => {
                            base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                            if state.farms[player_idx].money >= 2400.0 {
                                base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
                            }
                        }
                        _ => {}
                    }
                }
            }
        }

        base_action
    }
}
