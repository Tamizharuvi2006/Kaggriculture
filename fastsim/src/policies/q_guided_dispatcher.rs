//! EXP183 — Q-Guided Target Dispatcher Policy (Arm C).
//! Evaluates Q(s, a) neural network in native Rust to dynamically guide macro decisions.

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop, Quadrant};
use crate::policies::Policy;
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct QWeights {
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

#[derive(Clone)]
pub struct QGuidedDispatcherPolicy {
    name: &'static str,
    weights: QWeights,
}

impl QGuidedDispatcherPolicy {
    pub fn new() -> Self {
        let weights_json = include_str!("../../../models/exp182_q_weights.json");
        let weights: QWeights = serde_json::from_str(weights_json).expect("Failed to parse exp182_q_weights.json");
        Self {
            name: "q_guided_dispatcher",
            weights,
        }
    }

    pub fn extract_features(state: &GameState, player_idx: usize) -> [f32; 10] {
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0) as f32;
        let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0) as f32;
        let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0) as f32;
        let quads = farm.unlocked_quadrants.len() as f32;

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

        [
            state.step as f32,
            state.day as f32,
            farm.money as f32,
            melon_seeds,
            wheat_seeds,
            straw_seeds,
            quads,
            num_plants as f32,
            num_cows as f32,
            farm.hands.len() as f32,
        ]
    }

    /// Native Rust forward pass for Q(s, a)
    pub fn predict_q(&self, features: &[f32; 10], action_id: usize) -> f32 {
        let w = &self.weights;
        let mut norm_feat = [0.0f32; 10];
        for i in 0..10 {
            norm_feat[i] = (features[i] - w.state_mean[i]) / w.state_std[i];
        }

        let a_emb = &w.action_embed[action_id];
        let mut x = [0.0f32; 26];
        for i in 0..10 { x[i] = norm_feat[i]; }
        for i in 0..16 { x[10 + i] = a_emb[i]; }

        // Layer 1: Linear 26 -> 128
        let mut h1 = vec![0.0f32; 128];
        for i in 0..128 {
            let mut sum = w.fc1_bias[i];
            for j in 0..26 {
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
            h1[i] = (norm * w.ln1_weight[i] + w.ln1_bias[i]).max(0.0); // ReLU
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
            h2[i] = (norm * w.ln2_weight[i] + w.ln2_bias[i]).max(0.0); // ReLU
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
            0 => true, // HOLD
            1 => money >= 50.0 && hands < 16, // HIRE_1
            2 => money >= 100.0 && hands < 15, // HIRE_2
            3 => money >= 150.0 && hands < 14, // HIRE_3
            4 => money >= 480.0, // BUY_SEED_MELON_6
            5 => money >= 640.0, // BUY_SEED_MELON_8
            6 => money >= 40.0, // BUY_SEED_WHEAT_4
            7 => money >= 60.0, // BUY_SEED_WHEAT_6
            8 => money >= 400.0, // BUY_SEED_STRAW_4
            9 => money >= 800.0, // BUY_SEED_STRAW_8
            10 => money >= 800.0, // BUY_COW_1
            11 => {
                let cost = match quads {
                    1 => 1000.0,
                    2 => 2000.0,
                    3 => 4000.0,
                    _ => 999999.0,
                };
                money >= cost && quads < 4
            }
            _ => false,
        }
    }

    pub fn get_market_orders(action_id: usize) -> Vec<MarketOrder> {
        match action_id {
            0 => vec![],
            1 => vec![MarketOrder::Hire],
            2 => vec![MarketOrder::Hire, MarketOrder::Hire],
            3 => vec![MarketOrder::Hire, MarketOrder::Hire, MarketOrder::Hire],
            4 => vec![MarketOrder::BuySeed(Crop::Melon, 6)],
            5 => vec![MarketOrder::BuySeed(Crop::Melon, 8)],
            6 => vec![MarketOrder::BuySeed(Crop::Wheat, 4)],
            7 => vec![MarketOrder::BuySeed(Crop::Wheat, 6)],
            8 => vec![MarketOrder::BuySeed(Crop::Strawberry, 4)],
            9 => vec![MarketOrder::BuySeed(Crop::Strawberry, 8)],
            10 => vec![MarketOrder::BuyAnimal(Animal::Cow, 1)],
            11 => vec![MarketOrder::BuyLand],
            _ => vec![],
        }
    }

    pub fn step_toward(from_x: usize, from_y: usize, to_x: usize, to_y: usize) -> UnitAction {
        if from_x < to_x { UnitAction::East }
        else if from_x > to_x { UnitAction::West }
        else if from_y < to_y { UnitAction::South }
        else if from_y > to_y { UnitAction::North }
        else { UnitAction::Pass }
    }

    pub fn is_tile_unlocked(x: usize, y: usize, unlocked: &[Quadrant]) -> bool {
        let quad = Quadrant::of(x, y, 10);
        unlocked.contains(&quad)
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum TaskType {
    Harvest,
    Water,
    Plant(Crop),
    Feed,
    CollectFertilizer,
    Care,
}

#[derive(Clone, Debug)]
pub struct TargetTicket {
    pub x: usize,
    pub y: usize,
    pub task: TaskType,
    pub priority: i32,
}

impl Policy for QGuidedDispatcherPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let step = state.step;
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;
        let quads = &farm.unlocked_quadrants;

        let mut market = Vec::new();

        // 1. Q-Guided Macro Action Evaluation at Hour 0 / Key Decision Points
        if hour == 0 || step == 0 {
            let features = Self::extract_features(state, player_idx);
            let mut best_action = 0;
            let mut max_q = -1e9f32;

            for a in 0..12 {
                if Self::is_action_feasible(a, money, quads.len(), farm.hands.len()) {
                    let q_val = self.predict_q(&features, a);
                    if q_val > max_q {
                        max_q = q_val;
                        best_action = a;
                    }
                }
            }

            let mut orders = Self::get_market_orders(best_action);
            market.append(&mut orders);
        }

        // 2. Real-time Inventory Liquidations (Instant Cash Realization)
        for prod in [
            Product::Fertilizer,
            Product::Melon,
            Product::Strawberry,
            Product::Wheat,
            Product::Milk,
            Product::Wool,
            Product::Carrot,
            Product::Tomato,
        ] {
            let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
            if count > 0 {
                market.push(MarketOrder::Sell(prod, count));
            }
        }

        // Terminal clearance at Steps 700..719
        if step >= 700 {
            for prod in Product::ALL {
                let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
                if count > 0 {
                    market.push(MarketOrder::Sell(prod, count));
                }
            }
        }

        // =========================================================================
        // 3. PHYSICAL TARGET DISPATCH QUEUE (EXP180 BFS ROUTING)
        // =========================================================================
        let mut tickets: Vec<TargetTicket> = Vec::new();
        let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
        let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
        let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);

        for y in 0..10 {
            for x in 0..10 {
                if !Self::is_tile_unlocked(x, y, quads) { continue; }

                match &farm.tiles[y][x] {
                    Tile::Plant(p) => {
                        let is_mature = (day as i32 - p.planted_day >= p.crop.first_yield_day()) && p.yield_units > 0;
                        if is_mature {
                            tickets.push(TargetTicket { x, y, task: TaskType::Harvest, priority: 100 });
                        } else if !p.watered_today {
                            tickets.push(TargetTicket { x, y, task: TaskType::Water, priority: 90 });
                        }
                    }
                    Tile::Animal(a) => {
                        if a.fertilizer_available {
                            tickets.push(TargetTicket { x, y, task: TaskType::CollectFertilizer, priority: 80 });
                        } else if !a.fed_today {
                            tickets.push(TargetTicket { x, y, task: TaskType::Feed, priority: 70 });
                        } else {
                            tickets.push(TargetTicket { x, y, task: TaskType::Care, priority: 10 });
                        }
                    }
                    Tile::Empty => {
                        if day < 4 && melon_seeds > 0 {
                            tickets.push(TargetTicket { x, y, task: TaskType::Plant(Crop::Melon), priority: 60 });
                        } else if day < 4 && wheat_seeds > 0 {
                            tickets.push(TargetTicket { x, y, task: TaskType::Plant(Crop::Wheat), priority: 55 });
                        } else if straw_seeds > 0 {
                            tickets.push(TargetTicket { x, y, task: TaskType::Plant(Crop::Strawberry), priority: 50 });
                        } else if melon_seeds > 0 {
                            tickets.push(TargetTicket { x, y, task: TaskType::Plant(Crop::Melon), priority: 45 });
                        } else if wheat_seeds > 0 {
                            tickets.push(TargetTicket { x, y, task: TaskType::Plant(Crop::Wheat), priority: 40 });
                        }
                    }
                    _ => {}
                }
            }
        }

        tickets.sort_by(|a, b| b.priority.cmp(&a.priority));

        // Physical worker routing
        let (fx, fy) = farm.farmer;
        let farmer_inv = priv_farm.inventories.first();
        let farmer_wheat = farmer_inv.and_then(|inv| inv.get("WHEAT")).copied().unwrap_or(0);
        let farmer_total = farmer_inv.map(|inv| inv.values().sum::<i64>()).unwrap_or(0);

        let farmer_action = if farmer_total >= 3 || (farmer_total > 0 && tickets.is_empty()) {
            if fx == 0 && fy == 0 { UnitAction::Drop }
            else { Self::step_toward(fx, fy, 0, 0) }
        } else if let Some(ticket) = tickets.iter().find(|t| matches!(t.task, TaskType::CollectFertilizer | TaskType::Feed | TaskType::Harvest | TaskType::Care)) {
            if fx == ticket.x && fy == ticket.y {
                match ticket.task {
                    TaskType::CollectFertilizer => UnitAction::CollectFertilizer,
                    TaskType::Feed => {
                        if farmer_wheat > 0 { UnitAction::Feed }
                        else if *priv_farm.shed.get("WHEAT").unwrap_or(&0) > 0 {
                            if fx == 0 && fy == 0 { UnitAction::Pickup("WHEAT".to_string(), 2) }
                            else { Self::step_toward(fx, fy, 0, 0) }
                        } else { UnitAction::Care }
                    }
                    TaskType::Harvest => UnitAction::Harvest,
                    TaskType::Care => UnitAction::Care,
                    _ => UnitAction::Pass,
                }
            } else {
                Self::step_toward(fx, fy, ticket.x, ticket.y)
            }
        } else {
            UnitAction::Pass
        };

        let mut hands_actions = Vec::new();
        let plant_and_water_tickets: Vec<&TargetTicket> = tickets.iter().filter(|t| matches!(t.task, TaskType::Water | TaskType::Plant(_))).collect();

        for (h_idx, &(hx, hy)) in farm.hands.iter().enumerate() {
            let h_inv = priv_farm.inventories.get(h_idx + 1);
            let h_total = h_inv.map(|inv| inv.values().sum::<i64>()).unwrap_or(0);

            if h_total >= 3 {
                if hx == 0 && hy == 0 { hands_actions.push(UnitAction::Drop); }
                else { hands_actions.push(Self::step_toward(hx, hy, 0, 0)); }
            } else if let Some(ticket) = plant_and_water_tickets.get(h_idx % plant_and_water_tickets.len().max(1)) {
                if hx == ticket.x && hy == ticket.y {
                    match ticket.task {
                        TaskType::Water => hands_actions.push(UnitAction::Water),
                        TaskType::Plant(crop) => hands_actions.push(UnitAction::Plant(crop)),
                        _ => hands_actions.push(UnitAction::Pass),
                    }
                } else {
                    hands_actions.push(Self::step_toward(hx, hy, ticket.x, ticket.y));
                }
            } else {
                hands_actions.push(UnitAction::Pass);
            }
        }

        PlayerAction {
            farmer: farmer_action,
            hands: hands_actions,
            market,
        }
    }
}
