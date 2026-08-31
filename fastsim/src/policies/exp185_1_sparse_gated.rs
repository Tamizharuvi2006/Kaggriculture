//! EXP185.1 — Sparse-Gated Intervention Policy with Dynamic Runway Guard & Intervention Budget.
//! Principles: Detect tail stall early, execute the minimum required correction, then get out of the way.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop, Quadrant};
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use crate::policies::exp185_verified_policy::DualHeadWeights;
use std::sync::Mutex;

#[derive(Clone, Copy, Debug)]
pub struct SparseGatedConfig {
    pub max_interventions: usize,
    pub confidence_weighted: bool,
    pub min_expected_gain: f64,
    pub min_prob_threshold: f32,
}

pub struct EXP185_1_SparseGatedPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: DualHeadWeights,
    config: SparseGatedConfig,
    interventions_used: Mutex<usize>,
}

impl EXP185_1_SparseGatedPolicy {
    pub fn new(name: &'static str, config: SparseGatedConfig) -> Self {
        let weights_json = include_str!("../../../models/exp185_dual_head_weights.json");
        let weights: DualHeadWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp185_dual_head_weights.json");

        Self {
            name,
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
            config,
            interventions_used: Mutex::new(0),
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

    /// Forward pass through Dual-Head Trunk -> (Policy Softmax Probs [14], Value Preds [14])
    pub fn forward(&self, features: &[f32; 16]) -> ([f32; 14], [f32; 14]) {
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

        // Layer 2: 128 -> 128
        let mut h2 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.trunk_fc2_bias[i];
            for j in 0..128 { sum += w.trunk_fc2_weight[i][j] * h1[j]; }
            h2[i] = sum;
        }

        let mean2: f32 = h2.iter().sum::<f32>() / 128.0;
        let var2: f32 = h2.iter().map(|v| (v - mean2).powi(2)).sum::<f32>() / 128.0;
        let std2 = (var2 + 1e-5).sqrt();
        for i in 0..128 {
            let norm = (h2[i] - mean2) / std2;
            h2[i] = (norm * w.trunk_ln2_weight[i] + w.trunk_ln2_bias[i]).max(0.0);
        }

        // Policy Head
        let mut logits = [0.0f32; 14];
        for i in 0..14 {
            let mut sum = w.policy_head_bias[i];
            for j in 0..128 { sum += w.policy_head_weight[i][j] * h2[j]; }
            logits[i] = sum;
        }

        // Softmax
        let max_l = logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let exp_sum: f32 = logits.iter().map(|&l| (l - max_l).exp()).sum();
        let mut probs = [0.0f32; 14];
        for i in 0..14 {
            probs[i] = (logits[i] - max_l).exp() / exp_sum;
        }

        // Value Head
        let mut values = [0.0f32; 14];
        for i in 0..14 {
            let mut sum = w.value_head_bias[i];
            for j in 0..128 { sum += w.value_head_weight[i][j] * h2[j]; }
            values[i] = sum;
        }

        (probs, values)
    }

    /// Dynamic Runway & Obligation Safety Calculator
    pub fn is_action_safe_runway(action_id: usize, state: &GameState, player_idx: usize) -> bool {
        let farm = &state.farms[player_idx];
        let money = farm.money;
        let hands = farm.hands.len();
        let mut num_cows = 0;
        for row in &farm.tiles {
            for tile in row {
                if let Tile::Animal(a) = tile {
                    if a.animal == Animal::Cow { num_cows += 1; }
                }
            }
        }

        let cost = match action_id {
            1 => 50.0,
            2 => 100.0,
            3 => 150.0,
            4 => 480.0,
            5 => 640.0,
            6 => 400.0,
            7 => 800.0,
            8 => 1600.0,
            9 => 40.0,
            10 => 800.0,
            11 => match farm.unlocked_quadrants.len() {
                1 => 1000.0,
                2 => 2000.0,
                3 => 4000.0,
                _ => 999999.0,
            },
            12 | 13 => 0.0,
            _ => 0.0,
        };

        if money < cost { return false; }
        let post_cash = money - cost;

        // Required 2-day worker wages + 2-day cow feed + liquidity reserve
        let worker_obligation = (hands as f64 + if (1..=3).contains(&action_id) { action_id as f64 } else { 0.0 }) * 10.0 * 2.0;
        let cow_obligation = (num_cows as f64 + if action_id == 10 { 1.0 } else { 0.0 }) * 15.0 * 2.0;
        let min_reserve = if state.day < 5 { 200.0 } else if state.day < 10 { 350.0 } else { 150.0 };

        let required_safe_cash = worker_obligation + cow_obligation + min_reserve;
        post_cash >= required_safe_cash
    }

    pub fn apply_action_to_market(
        action_id: usize,
        market: &mut Vec<MarketOrder>,
        priv_shed: &std::collections::HashMap<String, i64>,
    ) {
        match action_id {
            0 => {}
            1 => market.push(MarketOrder::Hire),
            2 => { market.push(MarketOrder::Hire); market.push(MarketOrder::Hire); }
            3 => { market.push(MarketOrder::Hire); market.push(MarketOrder::Hire); market.push(MarketOrder::Hire); }
            4 => market.push(MarketOrder::BuySeed(Crop::Melon, 6)),
            5 => market.push(MarketOrder::BuySeed(Crop::Melon, 8)),
            6 => market.push(MarketOrder::BuySeed(Crop::Strawberry, 4)),
            7 => market.push(MarketOrder::BuySeed(Crop::Strawberry, 8)),
            8 => market.push(MarketOrder::BuySeed(Crop::Strawberry, 16)),
            9 => market.push(MarketOrder::BuySeed(Crop::Wheat, 4)),
            10 => market.push(MarketOrder::BuyAnimal(Animal::Cow, 1)),
            11 => market.push(MarketOrder::BuyLand),
            12 => {
                for prod in Product::ALL {
                    let count = *priv_shed.get(prod.name()).unwrap_or(&0);
                    if count > 0 { market.push(MarketOrder::Sell(prod, count)); }
                }
            }
            13 => {
                market.retain(|o| !matches!(o, MarketOrder::Sell(_, _)));
            }
            _ => {}
        }
    }

    pub fn verify_action_gain(
        state: &GameState,
        player_idx: usize,
        cand_action: usize,
        base_act: &PlayerAction,
        priv_shed: &std::collections::HashMap<String, i64>,
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

        // 2. Candidate counterfactual rollout to terminal
        let mut cf_state = state.clone();
        let mut cand_hero_act = base_act.clone();
        Self::apply_action_to_market(cand_action, &mut cand_hero_act.market, priv_shed);

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

impl Policy for EXP185_1_SparseGatedPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let hour = state.hour;
        let day = state.day;
        let step = state.step;
        let priv_farm = &state.privates[player_idx];

        // Reset intervention counter on step 0
        if step == 0 {
            if let Ok(mut count) = self.interventions_used.lock() {
                *count = 0;
            }
        }

        let used = self.interventions_used.lock().map(|g| *g).unwrap_or(0);

        // Evaluate ONLY if intervention budget remains (Days 0..10 primarily)
        if used < self.config.max_interventions && hour == 0 && day <= 12 && step < 690 {
            let features = Self::extract_features(state, player_idx);
            let (probs, values) = self.forward(&features);

            let mut candidates = Vec::new();
            for a in 1..14 {
                if Self::is_action_safe_runway(a, state, player_idx) {
                    let score = if self.config.confidence_weighted {
                        probs[a] * (values[a] / 1000.0).max(0.0)
                    } else {
                        probs[a] + (values[a] / 5000.0).max(-1.0)
                    };

                    if probs[a] >= self.config.min_prob_threshold {
                        candidates.push((a, score, probs[a], values[a]));
                    }
                }
            }

            candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

            if let Some(&(best_cand, _, _, exp_val)) = candidates.first() {
                if (exp_val as f64) >= self.config.min_expected_gain {
                    let verified_delta = Self::verify_action_gain(
                        state, player_idx, best_cand, &base_action, &priv_farm.shed
                    );

                    // Execute ONLY if verified positive (> +$250) and update budget!
                    if verified_delta >= self.config.min_expected_gain {
                        Self::apply_action_to_market(best_cand, &mut base_action.market, &priv_farm.shed);
                        if let Ok(mut count) = self.interventions_used.lock() {
                            *count += 1;
                        }
                    }
                }
            }
        }

        base_action
    }
}
