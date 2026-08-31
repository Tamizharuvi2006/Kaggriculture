//! EXP197 — Contrastive Joint Residual-Q Policy with Scheduled Decision Windows.
//! Combines Pairwise Contrastive Ranking on 16-d state representation with FastSim Lookahead Verification.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::farm::{Animal, Crop, Tile};
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct ContrastiveQWeights {
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
    pub q_head_weight: Vec<Vec<f32>>,
    pub q_head_bias: Vec<f32>,
}

pub struct EXP197ContrastivePolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: ContrastiveQWeights,
}

impl EXP197ContrastivePolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp197_contrastive_q_weights.json");
        let weights: ContrastiveQWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp197_contrastive_q_weights.json");

        Self {
            name: "exp197_contrastive_policy",
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
        }
    }

    pub fn extract_features(state: &GameState, player_idx: usize) -> [f32; 16] {
        let opp_idx = 1 - player_idx;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let opp_farm = &state.farms[opp_idx];

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

        // Opponent features
        let opp_cash = opp_farm.money as f32;
        let opp_quads = opp_farm.unlocked_quadrants.len() as f32;
        let opp_workers = opp_farm.hands.len() as f32;

        let mut opp_cows = 0;
        let mut opp_sheep = 0;
        let mut opp_straws = 0;

        for row in &opp_farm.tiles {
            for tile in row {
                match tile {
                    Tile::Animal(a) => {
                        if a.animal == Animal::Cow { opp_cows += 1; }
                        if a.animal == Animal::Sheep { opp_sheep += 1; }
                    }
                    Tile::Plant(p) => {
                        if p.crop == Crop::Strawberry { opp_straws += 1; }
                    }
                    _ => {}
                }
            }
        }

        [
            p_milk, cash, cows as f32, sheep as f32, shed_wheat, hands, quads, day, unwatered as f32, mature as f32,
            opp_cash, opp_cows as f32, opp_sheep as f32, opp_quads, opp_workers, opp_straws as f32,
        ]
    }

    pub fn forward(&self, features: &[f32; 16]) -> [f32; 6] {
        let w = &self.weights;
        let mut norm_feat = [0.0f32; 16];
        for i in 0..16 {
            norm_feat[i] = (features[i] - w.state_mean[i]) / w.state_std[i];
        }

        // Layer 1: 16 -> 128
        let mut h1 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.trunk_fc1_bias[i];
            for j in 0..16 { sum += w.trunk_fc1_weight[i][j] * norm_feat[j]; }
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

        // Q Head: 64 -> 6
        let mut q_vals = [0.0f32; 6];
        for i in 0..6 {
            let mut sum = w.q_head_bias[i];
            for j in 0..64 { sum += w.q_head_weight[i][j] * h2[j]; }
            q_vals[i] = sum;
        }

        q_vals
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

impl Policy for EXP197ContrastivePolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let step = state.step;
        let day = state.day;
        let hour = state.hour;

        // Scheduled Decision Windows:
        // Window 1: Day 0 Step 0 (Early wheat insurance: action a1)
        // Window 2: Day 6 Hour 0 (Labor rescue: action a2)
        // Window 3: Day 8 Hour 4 (Sheep sizing: actions a3, a4, a5)
        let candidate_set: Option<&[usize]> = if step == 0 {
            Some(&[1])
        } else if day == 6 && hour == 0 {
            Some(&[2])
        } else if day == 8 && hour == 4 {
            Some(&[3, 4, 5])
        } else {
            None
        };

        if let Some(cands) = candidate_set {
            let features = Self::extract_features(state, player_idx);
            let q_scores = self.forward(&features);

            let q_base = q_scores[0]; // a0 baseline score
            let mut best_cand = 0;
            let mut max_q = q_base;

            for &cand in cands {
                if q_scores[cand] > max_q {
                    max_q = q_scores[cand];
                    best_cand = cand;
                }
            }

            // If a candidate beats the baseline by threshold, verify in FastSim
            if best_cand != 0 && (max_q - q_base) >= 50.0 {
                let verified_gain = Self::verify_action_gain(state, player_idx, best_cand, &base_action);

                if verified_gain >= 100.0 {
                    match best_cand {
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
