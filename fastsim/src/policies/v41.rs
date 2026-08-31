//! V4.1 Historical Policy (Kaggle ~1479.8 Elo Closed-Loop Multi-Expert Architecture).

use super::Policy;
use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::farm::Tile;
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use serde_json::Value;
use std::collections::HashMap;
use std::sync::Mutex;

const V41_RUNTIME_JSON: &str = include_str!("../../data/v41_full_runtime.json");

const V18_PRODUCTS: [&str; 9] = [
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
];

struct ExpertData {
    actions: Vec<PlayerAction>,
    prototypes_by_day: Vec<Vec<f64>>,
}

pub struct V41Policy {
    board_by_seat: [String; 2],
    experts: HashMap<String, ExpertData>,
    scales: Vec<f64>,
    market_bias_by_seat: [HashMap<String, f64>; 2],
    distance_strength: f64,
    stay_bonus: f64,
    runtime_state: Mutex<V41RuntimeState>,
}

struct V41RuntimeState {
    selected_market: [Option<String>; 2],
    selected_day: [Option<usize>; 2],
}

impl V41Policy {
    pub fn new() -> Self {
        let v: Value = serde_json::from_str(V41_RUNTIME_JSON)
            .expect("Failed to parse embedded V4.1 runtime JSON");

        let b0 = v["board_by_seat"]["0"].as_str().unwrap_or("mohit").to_string();
        let b1 = v["board_by_seat"]["1"].as_str().unwrap_or("mohit").to_string();

        let scales: Vec<f64> = v["feature_standardization"]["scale"]
            .as_array().unwrap()
            .iter().map(|x| x.as_f64().unwrap_or(1.0)).collect();

        let distance_strength = v["distance_strength"].as_f64().unwrap_or(1.0);
        let stay_bonus = v["stay_bonus"].as_f64().unwrap_or(0.0);

        let mut market_bias_by_seat = [HashMap::new(), HashMap::new()];
        for seat in 0..2 {
            if let Some(bias_obj) = v["market_bias_by_seat"][seat.to_string().as_str()].as_object() {
                for (k, val) in bias_obj {
                    market_bias_by_seat[seat].insert(k.clone(), val.as_f64().unwrap_or(0.0));
                }
            }
        }

        let mut experts = HashMap::new();
        if let Some(exp_obj) = v["experts"].as_object() {
            for (name, exp_val) in exp_obj {
                let mut actions = Vec::new();
                if let Some(act_arr) = exp_val["actions"].as_array() {
                    for a in act_arr {
                        actions.push(parse_json_action(a));
                    }
                }

                let mut prototypes_by_day = Vec::new();
                if let Some(proto_arr) = exp_val["prototypes_by_day"].as_array() {
                    for p in proto_arr {
                        let row: Vec<f64> = p.as_array().unwrap().iter().map(|x| x.as_f64().unwrap_or(0.0)).collect();
                        prototypes_by_day.push(row);
                    }
                }

                experts.insert(name.clone(), ExpertData { actions, prototypes_by_day });
            }
        }

        Self {
            board_by_seat: [b0, b1],
            experts,
            scales,
            market_bias_by_seat,
            distance_strength,
            stay_bonus,
            runtime_state: Mutex::new(V41RuntimeState {
                selected_market: [None, None],
                selected_day: [None, None],
            }),
        }
    }

    pub fn extract_features(&self, state: &GameState, player_idx: usize) -> Vec<f64> {
        let farm = &state.farms[player_idx];
        let priv_state = &state.privates[player_idx];

        let mut counts = HashMap::new();
        for &name in &["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "COW", "SHEEP", "GOOSE"] {
            counts.insert(name, 0.0);
        }

        for row in &farm.tiles {
            for tile in row {
                match tile {
                    Tile::Plant(p) => {
                        *counts.entry(p.crop.name()).or_insert(0.0) += 1.0;
                    }
                    Tile::Animal(a) => {
                        *counts.entry(a.animal.name()).or_insert(0.0) += 1.0;
                    }
                    _ => {}
                }
            }
        }

        let mut values = Vec::with_capacity(29);
        values.push((1.0 + farm.money.max(0.0)).ln());
        values.push(farm.hands.len() as f64 / 16.0);
        values.push(farm.unlocked_quadrants.len() as f64 / 4.0);

        for &name in &["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "COW", "SHEEP", "GOOSE"] {
            values.push(counts.get(name).cloned().unwrap_or(0.0) / 50.0);
        }

        for &name in &V18_PRODUCTS {
            let shed_val = priv_state.shed.get(name).cloned().unwrap_or(0) as f64;
            values.push((1.0 + shed_val.max(0.0)).ln());
        }

        let mut price_values = Vec::with_capacity(9);
        for &name in &V18_PRODUCTS {
            let prod = Product::from_name(name).unwrap();
            let p = state.market.prices.get(&prod).cloned().unwrap_or(1) as f64;
            price_values.push(p.max(1.0));
        }

        let mean_price: f64 = price_values.iter().sum::<f64>() / price_values.len() as f64;
        for &p in &price_values {
            values.push((p / mean_price).ln());
        }

        values
    }
}

fn parse_json_action(val: &Value) -> PlayerAction {
    if !val.is_object() {
        return PlayerAction::default();
    }

    let farmer = val.get("farmer")
        .and_then(|v| v.as_array())
        .and_then(|arr| UnitAction::from_json_array(arr))
        .unwrap_or(UnitAction::Pass);

    let mut hands = Vec::new();
    if let Some(hands_arr) = val.get("hands").and_then(|v| v.as_array()) {
        for h in hands_arr {
            if let Some(h_arr) = h.as_array() {
                if let Some(u_act) = UnitAction::from_json_array(h_arr) {
                    hands.push(u_act);
                } else {
                    hands.push(UnitAction::Pass);
                }
            }
        }
    }

    let mut market = Vec::new();
    if let Some(m_arr) = val.get("market").and_then(|v| v.as_array()) {
        for order_val in m_arr {
            if let Some(o_arr) = order_val.as_array() {
                if let Some(order) = MarketOrder::from_json_array(o_arr) {
                    market.push(order);
                }
            }
        }
    }

    PlayerAction { farmer, hands, market }
}

impl Policy for V41Policy {
    fn name(&self) -> &'static str {
        "v41"
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let step = state.step;
        let day = state.day;

        let base_board_name = &self.board_by_seat[player_idx];
        let board_actions = &self.experts[base_board_name].actions;
        let bounded_step = step.min(board_actions.len() - 1);
        let board_act = &board_actions[bounded_step];

        // Closed-Loop Market Expert Selection at day boundaries
        let mut rt = self.runtime_state.lock().unwrap();
        if step == 0 {
            rt.selected_market[player_idx] = None;
            rt.selected_day[player_idx] = None;
        }

        if rt.selected_day[player_idx] != Some(day) || rt.selected_market[player_idx].is_none() {
            let current = self.extract_features(state, player_idx);
            let bias = &self.market_bias_by_seat[player_idx];
            let prev_selected = rt.selected_market[player_idx].clone();

            let mut best_score = f64::NEG_INFINITY;
            let mut best_name = base_board_name.clone();

            for (name, expert) in &self.experts {
                let proto_idx = day.min(expert.prototypes_by_day.len() - 1);
                let prototype = &expert.prototypes_by_day[proto_idx];

                let distance: f64 = current.iter().zip(prototype.iter()).zip(self.scales.iter())
                    .map(|((v, c), s)| {
                        let diff = (v - c) / s.max(1e-12);
                        diff * diff
                    })
                    .sum::<f64>() / current.len() as f64;

                let stay = if prev_selected.as_ref() == Some(name) { self.stay_bonus } else { 0.0 };
                let score = bias.get(name).cloned().unwrap_or(0.0) + stay - self.distance_strength * distance;

                if score > best_score {
                    best_score = score;
                    best_name = name.clone();
                }
            }

            rt.selected_market[player_idx] = Some(best_name.clone());
            rt.selected_day[player_idx] = Some(day);
        }

        let market_expert_name = rt.selected_market[player_idx].as_ref().unwrap_or(base_board_name);
        let market_actions = &self.experts[market_expert_name].actions;
        let market_act = &market_actions[bounded_step.min(market_actions.len() - 1)];

        let mut market_orders = market_act.market.clone();

        // Reorder market orders by product priority
        if market_orders.len() > 1 {
            let milk_price = state.market.prices.get(&Product::Milk).cloned().unwrap_or(160);
            let mut decorated: Vec<(usize, usize, MarketOrder)> = market_orders.into_iter().enumerate().map(|(idx, ord)| {
                let prio = match &ord {
                    MarketOrder::Sell(p, _) => {
                        match p {
                            Product::Milk if milk_price >= 200 => 0,
                            Product::Melon => 1,
                            Product::Strawberry => 2,
                            Product::Wheat => 3,
                            _ => 4,
                        }
                    }
                    _ => 10,
                };
                (prio, idx, ord)
            }).collect();

            decorated.sort_by_key(|&(prio, idx, _)| (prio, idx));
            market_orders = decorated.into_iter().map(|(_, _, ord)| ord).collect();
        }

        market_orders.truncate(8);

        PlayerAction {
            farmer: board_act.farmer.clone(),
            hands: board_act.hands.clone(),
            market: market_orders,
        }
    }
}
