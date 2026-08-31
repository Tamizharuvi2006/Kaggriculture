//! EXP192 — Verified State-Conditioned Sheep Policy.
//! Uses Sheep Q-Network for state-conditioned sizing + FastSim full-terminal verification guard.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::farm::Animal;
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct SheepQWeights {
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
    pub advantage_head_weight: Vec<Vec<f32>>,
    pub advantage_head_bias: Vec<f32>,
    pub policy_logits_weight: Vec<Vec<f32>>,
    pub policy_logits_bias: Vec<f32>,
}

pub struct EXP192VerifiedSheepPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: SheepQWeights,
}

impl EXP192VerifiedSheepPolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp192_sheep_q_weights.json");
        let weights: SheepQWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp192_sheep_q_weights.json");

        Self {
            name: "exp192_verified_sheep",
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
        }
    }

    pub fn extract_features(state: &GameState, player_idx: usize) -> [f32; 6] {
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];

        let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f32;
        let cash = farm.money as f32;
        let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0) as f32;
        let hands = farm.hands.len() as f32;
        let quads = farm.unlocked_quadrants.len() as f32;

        let mut cow_count = 0;
        for row in &farm.tiles {
            for tile in row {
                if let crate::farm::Tile::Animal(a) = tile {
                    if a.animal == Animal::Cow { cow_count += 1; }
                }
            }
        }


        [p_milk, cash, cow_count as f32, shed_wheat, hands, quads]
    }

    /// Forward pass through Trunk -> (Advantages [5], Logits [5])
    pub fn forward(&self, features: &[f32; 6]) -> ([f32; 5], [f32; 5]) {
        let w = &self.weights;
        let mut norm_feat = [0.0f32; 6];
        for i in 0..6 {
            norm_feat[i] = (features[i] - w.state_mean[i]) / w.state_std[i];
        }

        // Layer 1: 6 -> 128
        let mut h1 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.trunk_fc1_bias[i];
            for j in 0..6 { sum += w.trunk_fc1_weight[i][j] * norm_feat[j]; }
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

        // Advantage Head: 64 -> 5
        let mut adv = [0.0f32; 5];
        for i in 0..5 {
            let mut sum = w.advantage_head_bias[i];
            for j in 0..64 { sum += w.advantage_head_weight[i][j] * h2[j]; }
            adv[i] = sum;
        }

        // Policy Logits: 64 -> 5
        let mut logits = [0.0f32; 5];
        for i in 0..5 {
            let mut sum = w.policy_logits_bias[i];
            for j in 0..64 { sum += w.policy_logits_weight[i][j] * h2[j]; }
            logits[i] = sum;
        }

        (adv, logits)
    }

    /// FastSim lookahead verification: evaluates candidate sheep count vs baseline N=4
    pub fn verify_sheep_gain(
        state: &GameState,
        player_idx: usize,
        cand_n: usize,
        base_act: &PlayerAction,
    ) -> f64 {
        let opp_policy = AdaptiveTerminalPolicy::new();
        let eval_policy = AdaptiveTerminalPolicy::new();

        // 1. Baseline rollout to terminal (N=4)
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

        // 2. Candidate sheep rollout to terminal (cand_n)
        let mut cf_state = state.clone();
        let mut cand_hero_act = base_act.clone();
        cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
        if cand_n > 0 {
            let cost = 600.0 * (cand_n as f64);
            if cf_state.farms[player_idx].money >= cost {
                cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, cand_n as i64));
            }
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

impl Policy for EXP192VerifiedSheepPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;

        // Evaluate at the exact sheep purchase window: Day 8 Hour 4
        if day == 8 && hour == 4 {
            let features = Self::extract_features(state, player_idx);
            let (adv, logits) = self.forward(&features);

            // Find best N according to model
            let mut best_n = 4;
            let mut max_logit = logits[4];
            for n in 0..5 {
                if logits[n] > max_logit {
                    max_logit = logits[n];
                    best_n = n;
                }
            }

            // If model proposes deviation from baseline 4 sheep with expected positive advantage
            if best_n != 4 && adv[best_n] > 0.0 {
                let verified_gain = Self::verify_sheep_gain(state, player_idx, best_n, &base_action);

                // Execute ONLY if verified strictly positive (+>$100)!
                if verified_gain >= 100.0 {
                    base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                    if best_n > 0 {
                        base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, best_n as i64));
                    }
                }
            }
        }

        base_action
    }
}
