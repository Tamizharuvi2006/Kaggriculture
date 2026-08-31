//! EXP184 — Residual Q-Adaptive Policy (Arm D / Production ML Candidate).
//! Predicts ΔQ(s, a) over the AdaptiveTerminal baseline; executes high-confidence positive-EV actions with baseline fallback.

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop, Quadrant};
use crate::policies::{Policy, AdaptiveTerminalPolicy};
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct ResidualQWeights {
    pub feature_cols: Vec<String>,
    pub state_mean: Vec<f32>,
    pub state_std: Vec<f32>,
    pub action_embed: Vec<Vec<f32>>,
    pub fc1_weight: Vec<Vec<f32>>,
    pub fc1_bias: Vec<f32>,
    pub ln1_weight: Vec<f32>,
    pub ln1_bias: Vec<f32>,
    pub fc2_weight: Vec<Vec<f32>>,
    pub fc2_bias: Vec<f32>,
    pub ln2_weight: Vec<f32>,
    pub ln2_bias: Vec<f32>,
    pub fc3_weight: Vec<Vec<f32>>,
    pub fc3_bias: Vec<f32>,
}

pub struct ResidualQAdaptivePolicy {
    name: &'static str,
    base_policy: AdaptiveTerminalPolicy,
    weights: ResidualQWeights,
    min_confidence_threshold: f32,
}

impl ResidualQAdaptivePolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp184_residual_q_weights.json");
        let weights: ResidualQWeights = serde_json::from_str(weights_json)
            .expect("Failed to parse exp184_residual_q_weights.json");

        Self {
            name: "residual_q_adaptive",
            base_policy: AdaptiveTerminalPolicy::new(),
            weights,
            min_confidence_threshold: 250.0, // Only intervene if predicted ΔQ > +$250
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

    /// Predicts ΔQ(s, a) over the baseline AdaptiveTerminal return
    pub fn predict_delta_q(&self, features: &[f32; 16], action_id: usize) -> f32 {
        if action_id == 0 {
            return 0.0; // Baseline ΔQ is exactly $0
        }

        let w = &self.weights;
        let mut norm_feat = [0.0f32; 16];
        for i in 0..16 {
            norm_feat[i] = (features[i] - w.state_mean[i]) / w.state_std[i];
        }

        let a_emb = &w.action_embed[action_id];
        let mut x = [0.0f32; 32];
        for i in 0..16 { x[i] = norm_feat[i]; }
        for i in 0..16 { x[16 + i] = a_emb[i]; }

        // Layer 1: Linear 32 -> 128
        let mut h1 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.fc1_bias[i];
            for j in 0..32 {
                sum += w.fc1_weight[i][j] * x[j];
            }
            h1[i] = sum;
        }

        // LayerNorm 1
        let mean1: f32 = h1.iter().sum::<f32>() / 128.0;
        let var1: f32 = h1.iter().map(|v| (v - mean1).powi(2)).sum::<f32>() / 128.0;
        let std1 = (var1 + 1e-5).sqrt();
        for i in 0..128 {
            let norm = (h1[i] - mean1) / std1;
            h1[i] = (norm * w.ln1_weight[i] + w.ln1_bias[i]).max(0.0);
        }

        // Layer 2: Linear 128 -> 128
        let mut h2 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.fc2_bias[i];
            for j in 0..128 {
                sum += w.fc2_weight[i][j] * h1[j];
            }
            h2[i] = sum;
        }

        // LayerNorm 2
        let mean2: f32 = h2.iter().sum::<f32>() / 128.0;
        let var2: f32 = h2.iter().map(|v| (v - mean2).powi(2)).sum::<f32>() / 128.0;
        let std2 = (var2 + 1e-5).sqrt();
        for i in 0..128 {
            let norm = (h2[i] - mean2) / std2;
            h2[i] = (norm * w.ln2_weight[i] + w.ln2_bias[i]).max(0.0);
        }

        // Layer 3: Linear 128 -> 1
        let mut out = w.fc3_bias[0];
        for j in 0..128 {
            out += w.fc3_weight[0][j] * h2[j];
        }
        out
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
}

impl Policy for ResidualQAdaptivePolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_policy.act(state, player_idx);
        let hour = state.hour;
        let step = state.step;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;
        let quads = farm.unlocked_quadrants.len();
        let hands = farm.hands.len();

        // Evaluate Residual Q at Key Strategic Decision Windows
        if hour == 0 && step < 690 {
            let features = Self::extract_features(state, player_idx);
            let mut best_action = 0;
            let mut max_delta_q = 0.0f32;

            for a in 1..14 {
                if Self::is_action_feasible(a, money, quads, hands) {
                    let delta_q = self.predict_delta_q(&features, a);
                    if delta_q > max_delta_q {
                        max_delta_q = delta_q;
                        best_action = a;
                    }
                }
            }

            // If predicted improvement exceeds confidence threshold, execute residual action!
            if max_delta_q >= self.min_confidence_threshold {
                Self::apply_action_to_market(best_action, &mut base_action.market, &priv_farm.shed);
            }
        }

        base_action
    }
}
