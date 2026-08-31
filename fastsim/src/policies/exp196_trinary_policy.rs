//! EXP196 — High-Precision Trinary Intervention Policy (BAD / NEUTRAL / GOOD).
//! Only triggers challenger interventions when P(GOOD) >= 0.60 and verified positive by FastSim.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::farm::{Animal, Crop, Tile};
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct TrinaryClassifierWeights {
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
    pub action_heads_weight: Vec<Vec<f32>>,
    pub action_heads_bias: Vec<f32>,
}

pub struct EXP196TrinaryPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: TrinaryClassifierWeights,
}

impl EXP196TrinaryPolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp196_trinary_weights.json");
        let weights: TrinaryClassifierWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp196_trinary_weights.json");

        Self {
            name: "exp196_trinary_policy",
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
        }
    }

    pub fn extract_features(state: &GameState, player_idx: usize) -> [f32; 10] {
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];

        let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f32;
        let cash = farm.money as f32;
        let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0) as f32;
        let hands = farm.hands.len() as f32;
        let quads = farm.unlocked_quadrants.len() as f32;
        let day = state.day as f32;

        let mut cows = 0;
        let mut sheep = 0;
        let mut unwatered = 0;
        let mut mature = 0;

        for row in &farm.tiles {
            for tile in row {
                match tile {
                    Tile::Animal(a) => {
                        if a.animal == Animal::Cow { cows += 1; }
                        if a.animal == Animal::Sheep { sheep += 1; }
                    }
                    Tile::Plant(p) => {
                        if p.yield_units > 0 { mature += 1; }
                        else if !p.watered_today { unwatered += 1; }
                    }
                    _ => {}
                }
            }
        }

        [p_milk, cash, cows as f32, sheep as f32, shed_wheat, hands, quads, day, unwatered as f32, mature as f32]
    }

    /// Forward pass: returns P(GOOD) for 5 candidate actions (a1..a5)
    pub fn predict_good_probabilities(&self, features: &[f32; 10]) -> [f32; 5] {
        let w = &self.weights;
        let mut norm_feat = [0.0f32; 10];
        for i in 0..10 {
            norm_feat[i] = (features[i] - w.state_mean[i]) / w.state_std[i];
        }

        // Layer 1: 10 -> 128
        let mut h1 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.trunk_fc1_bias[i];
            for j in 0..10 { sum += w.trunk_fc1_weight[i][j] * norm_feat[j]; }
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

        // Action Heads: 64 -> 15 (5 actions x 3 classes: BAD, NEUTRAL, GOOD)
        let mut raw_logits = [0.0f32; 15];
        for i in 0..15 {
            let mut sum = w.action_heads_bias[i];
            for j in 0..64 { sum += w.action_heads_weight[i][j] * h2[j]; }
            raw_logits[i] = sum;
        }

        let mut p_good = [0.0f32; 5];
        for act in 0..5 {
            let offset = act * 3;
            let l0 = raw_logits[offset];
            let l1 = raw_logits[offset + 1];
            let l2 = raw_logits[offset + 2];
            let max_l = l0.max(l1).max(l2);
            let e0 = (l0 - max_l).exp();
            let e1 = (l1 - max_l).exp();
            let e2 = (l2 - max_l).exp();
            let sum_e = e0 + e1 + e2;
            p_good[act] = e2 / sum_e; // Probability of class 2 (GOOD)
        }

        p_good
    }

    /// FastSim lookahead verification
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
            1 => { // Buy Wheat
                cand_hero_act.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
            }
            2 => { // Hire 1
                if cf_state.farms[player_idx].money >= 40.0 {
                    cand_hero_act.market.push(MarketOrder::Hire);
                }
            }
            3 => { // 1 Sheep
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_state.farms[player_idx].money >= 600.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                }
            }
            4 => { // 2 Sheep
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_state.farms[player_idx].money >= 1200.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                }
            }
            5 => { // 4 Sheep
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

impl Policy for EXP196TrinaryPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let step = state.step;
        let day = state.day;
        let hour = state.hour;

        // Check if current step corresponds to candidate intervention windows
        let cand_action_idx = if step == 0 {
            Some(1) // a1: Buy Wheat
        } else if day == 6 && hour == 0 {
            Some(2) // a2: Hire 1
        } else if day == 8 && hour == 4 {
            Some(4) // a4: 2 Sheep (or 3: 1 Sheep)
        } else {
            None
        };

        if let Some(cand_a) = cand_action_idx {
            let features = Self::extract_features(state, player_idx);
            let p_good = self.predict_good_probabilities(&features);

            // If classifier indicates high confidence of genuine alpha (P(GOOD) >= 0.60)
            if p_good[cand_a - 1] >= 0.60 {
                let verified_gain = Self::verify_action_gain(state, player_idx, cand_a, &base_action);

                if verified_gain >= 100.0 {
                    match cand_a {
                        1 => {
                            base_action.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
                        }
                        2 => {
                            if state.farms[player_idx].money >= 40.0 {
                                base_action.market.push(MarketOrder::Hire);
                            }
                        }
                        4 => {
                            base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                            if state.farms[player_idx].money >= 1200.0 {
                                base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
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
