//! EXP186 — Dedicated Tail-Stall Emergency Rescue Policy.
//! Detects failing trajectories early using the binary classifier, executes exactly ONE verified rescue action, then steps aside.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop};
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use serde::Deserialize;
use std::sync::Mutex;

#[derive(Clone, Deserialize)]
pub struct TailClassifierWeights {
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
    pub stall_head_weight: Vec<Vec<f32>>,
    pub stall_head_bias: Vec<f32>,
    pub action_head_weight: Vec<Vec<f32>>,
    pub action_head_bias: Vec<f32>,
}

pub struct EXP186RescuePolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: TailClassifierWeights,
    rescue_executed: Mutex<bool>,
    min_stall_prob_threshold: f32,
    min_verified_gain: f64,
}

impl EXP186RescuePolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp186_tail_classifier_weights.json");
        let weights: TailClassifierWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp186_tail_classifier_weights.json");

        Self {
            name: "exp186_rescue",
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
            rescue_executed: Mutex::new(false),
            min_stall_prob_threshold: 0.65, // Only fire when stall probability is >= 65%
            min_verified_gain: 500.0,        // Must produce at least +$500 verified terminal gain
        }
    }

    pub fn extract_features(state: &GameState, player_idx: usize) -> [f32; 16] {
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let opp_farm = &state.farms[1 - player_idx];

        let mut num_plants = 0;
        let mut num_cows = 0;
        for row in &farm.tiles {
            for tile in row {
                match tile {
                    Tile::Plant(_) => num_plants += 1,
                    Tile::Animal(a) if a.animal == Animal::Cow => num_cows += 1,
                    _ => {}
                }
            }
        }

        let shed_straw = *priv_farm.shed.get("STRAWBERRY").unwrap_or(&0) as f32;
        let shed_milk = *priv_farm.shed.get("MILK").unwrap_or(&0) as f32;
        let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0) as f32;

        let p_straw = *state.market.prices.get(&Product::Strawberry).unwrap_or(&120) as f32;
        let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f32;
        let p_melon = *state.market.prices.get(&Product::Melon).unwrap_or(&100) as f32;

        [
            state.step as f32,
            state.day as f32,
            state.hour as f32,
            farm.money as f32,
            farm.unlocked_quadrants.len() as f32,
            farm.hands.len() as f32,
            num_plants as f32,
            num_cows as f32,
            shed_straw,
            shed_milk,
            shed_wheat,
            p_straw,
            p_milk,
            p_melon,
            opp_farm.money as f32,
            opp_farm.unlocked_quadrants.len() as f32,
        ]
    }

    /// Predicts (stall_probability, [expected_gain_wheat, expected_gain_hire1, expected_gain_hire2])
    pub fn forward(&self, features: &[f32; 16]) -> (f32, [f32; 3]) {
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

        // Stall Head: 64 -> 1 Sigmoid
        let mut stall_logit = w.stall_head_bias[0];
        for j in 0..64 { stall_logit += w.stall_head_weight[0][j] * h2[j]; }
        let stall_prob = 1.0 / (1.0 + (-stall_logit).exp());

        // Action Head: 64 -> 3
        let mut act_gains = [0.0f32; 3];
        for i in 0..3 {
            let mut sum = w.action_head_bias[i];
            for j in 0..64 { sum += w.action_head_weight[i][j] * h2[j]; }
            act_gains[i] = sum;
        }

        (stall_prob, act_gains)
    }

    /// FastSim lookahead verification: evaluates candidate emergency rescue vs baseline
    pub fn verify_rescue_gain(
        state: &GameState,
        player_idx: usize,
        rescue_type: usize, // 0: BUY_WHEAT_4, 1: HIRE_1, 2: HIRE_2
        base_act: &PlayerAction,
    ) -> f64 {
        let opp_policy = AdaptiveTerminalPolicy::new();
        let eval_policy = AdaptiveTerminalPolicy::new();

        // 1. Baseline rollout to terminal
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

        // 2. Candidate emergency counterfactual rollout to terminal
        let mut cf_state = state.clone();
        let mut cand_hero_act = base_act.clone();

        match rescue_type {
            0 => cand_hero_act.market.push(MarketOrder::BuySeed(Crop::Wheat, 4)),
            1 => cand_hero_act.market.push(MarketOrder::Hire),
            2 => { cand_hero_act.market.push(MarketOrder::Hire); cand_hero_act.market.push(MarketOrder::Hire); }
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

impl Policy for EXP186RescuePolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let hour = state.hour;
        let day = state.day;
        let step = state.step;
        let farm = &state.farms[player_idx];

        // Reset rescue state on step 0
        if step == 0 {
            if let Ok(mut r) = self.rescue_executed.lock() {
                *r = false;
            }
        }

        let already_rescued = self.rescue_executed.lock().map(|g| *g).unwrap_or(false);

        // Emergency detection window: Day 0 (Feed) or Days 4..7 (Labor) at Hour 0
        if !already_rescued && hour == 0 && (day == 0 || (4..=7).contains(&day)) {
            let features = Self::extract_features(state, player_idx);
            let (stall_prob, act_gains) = self.forward(&features);

            // If classifier detects high stall probability (>= 65%)
            if stall_prob >= self.min_stall_prob_threshold {
                let cand_rescue = if day == 0 {
                    0 // BUY_WHEAT_4 on Day 0
                } else {
                    if act_gains[2] > act_gains[1] && farm.money >= 100.0 && farm.hands.len() < 15 {
                        2 // HIRE_2
                    } else if farm.money >= 50.0 && farm.hands.len() < 16 {
                        1 // HIRE_1
                    } else {
                        0
                    }
                };

                // Verify terminal gain in FastSim clone
                let verified_gain = Self::verify_rescue_gain(state, player_idx, cand_rescue, &base_action);

                if verified_gain >= self.min_verified_gain {
                    match cand_rescue {
                        0 => base_action.market.push(MarketOrder::BuySeed(Crop::Wheat, 4)),
                        1 => base_action.market.push(MarketOrder::Hire),
                        2 => { base_action.market.push(MarketOrder::Hire); base_action.market.push(MarketOrder::Hire); }
                        _ => {}
                    }
                    if let Ok(mut r) = self.rescue_executed.lock() {
                        *r = true; // Mark rescue complete — zero further interventions
                    }
                }
            }
        }

        base_action
    }
}
