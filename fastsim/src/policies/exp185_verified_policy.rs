//! EXP185 — Dual-Head Policy with FastSim Lookahead Verification (Zero-Risk Execution).
//! Uses Policy Head for intervention ranking, Value Head for magnitude estimation, and FastSim for guaranteed verification.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop, Quadrant};
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct DualHeadWeights {
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
    pub policy_head_weight: Vec<Vec<f32>>,
    pub policy_head_bias: Vec<f32>,
    pub value_head_weight: Vec<Vec<f32>>,
    pub value_head_bias: Vec<f32>,
}

pub struct EXP185VerifiedPolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: DualHeadWeights,
}

impl EXP185VerifiedPolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp185_dual_head_weights.json");
        let weights: DualHeadWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp185_dual_head_weights.json");

        Self {
            name: "exp185_verified",
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
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

    /// Forward pass through Dual-Head Trunk -> (Policy Logits [14], Value Preds [14])
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
            for j in 0..16 {
                sum += w.trunk_fc1_weight[i][j] * norm_feat[j];
            }
            h1[i] = sum;
        }

        // LayerNorm 1 + ReLU
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
            for j in 0..128 {
                sum += w.trunk_fc2_weight[i][j] * h1[j];
            }
            h2[i] = sum;
        }

        // LayerNorm 2 + ReLU
        let mean2: f32 = h2.iter().sum::<f32>() / 128.0;
        let var2: f32 = h2.iter().map(|v| (v - mean2).powi(2)).sum::<f32>() / 128.0;
        let std2 = (var2 + 1e-5).sqrt();
        for i in 0..128 {
            let norm = (h2[i] - mean2) / std2;
            h2[i] = (norm * w.trunk_ln2_weight[i] + w.trunk_ln2_bias[i]).max(0.0);
        }

        // Policy Head: 128 -> 14
        let mut logits = [0.0f32; 14];
        for i in 0..14 {
            let mut sum = w.policy_head_bias[i];
            for j in 0..128 {
                sum += w.policy_head_weight[i][j] * h2[j];
            }
            logits[i] = sum;
        }

        // Value Head: 128 -> 14
        let mut values = [0.0f32; 14];
        for i in 0..14 {
            let mut sum = w.value_head_bias[i];
            for j in 0..128 {
                sum += w.value_head_weight[i][j] * h2[j];
            }
            values[i] = sum;
        }

        (logits, values)
    }

    pub fn is_action_feasible(action_id: usize, money: f64, quads: usize, hands: usize) -> bool {
        match action_id {
            0 => true,
            1 => money >= 50.0 && hands < 16,
            2 => money >= 100.0 && hands < 15,
            3 => money >= 150.0 && hands < 14,
            4 => money >= 480.0,
            5 => money >= 640.0,
            6 => money >= 400.0,
            7 => money >= 800.0,
            8 => money >= 1600.0,
            9 => money >= 40.0,
            10 => money >= 800.0,
            11 => {
                let cost = match quads {
                    1 => 1000.0,
                    2 => 2000.0,
                    3 => 4000.0,
                    _ => 999999.0,
                };
                money >= cost && quads < 4
            }
            12 => true,
            13 => true,
            _ => false,
        }
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
                    if count > 0 {
                        market.push(MarketOrder::Sell(prod, count));
                    }
                }
            }
            13 => {
                market.retain(|o| !matches!(o, MarketOrder::Sell(_, _)));
            }
            _ => {}
        }
    }

    /// FastSim lookahead verification: evaluates candidate action vs baseline in clone
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

impl Policy for EXP185VerifiedPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let hour = state.hour;
        let step = state.step;
        let day = state.day;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;
        let quads = farm.unlocked_quadrants.len();
        let hands = farm.hands.len();

        // Evaluate at Key Decision Checkpoints (Days 0..25 hour 0)
        if hour == 0 && day <= 25 && step < 690 {
            let features = Self::extract_features(state, player_idx);
            let (logits, values) = self.forward(&features);

            // Rank candidate actions by policy logit + value bonus
            let mut candidates = Vec::new();
            for a in 1..14 {
                if Self::is_action_feasible(a, money, quads, hands) {
                    let score = logits[a] + (values[a] / 5000.0).max(-2.0);
                    candidates.push((a, score));
                }
            }

            candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

            // If top candidate has positive signal, verify in FastSim clone
            if let Some(&(best_cand, best_score)) = candidates.first() {
                if best_score > 0.0 || logits[best_cand] > 1.0 {
                    let verified_delta = Self::verify_action_gain(
                        state, player_idx, best_cand, &base_action, &priv_farm.shed
                    );

                    // Execute ONLY if verified positive (> +$50)!
                    if verified_delta > 50.0 {
                        Self::apply_action_to_market(best_cand, &mut base_action.market, &priv_farm.shed);
                    }
                }
            }
        }

        base_action
    }
}
