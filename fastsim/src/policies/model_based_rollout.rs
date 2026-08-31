//! EXP183 — Model-Based Policy (Arm D).
//! Top-K Q(s, a) filtering + FastSim Terminal Rollout Lookahead + EXP180 Target Dispatcher.

use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop, Quadrant};
use crate::policies::{Policy, TargetDispatcherPolicy, AdaptiveTerminalPolicy};
use crate::policies::q_guided_dispatcher::{QGuidedDispatcherPolicy, QWeights, TaskType, TargetTicket};

pub struct ModelBasedRolloutPolicy {
    name: &'static str,
    q_policy: QGuidedDispatcherPolicy,
    top_k: usize,
}

impl ModelBasedRolloutPolicy {
    pub fn new() -> Self {
        Self {
            name: "model_based_rollout",
            q_policy: QGuidedDispatcherPolicy::new(),
            top_k: 3,
        }
    }

    /// Evaluates candidate action via fast forward simulation to terminal
    pub fn evaluate_action_to_terminal(
        state: &GameState,
        player_idx: usize,
        action_id: usize,
    ) -> f64 {
        let mut sim_state = state.clone();
        let opp_policy = AdaptiveTerminalPolicy::new();
        let rollout_policy = TargetDispatcherPolicy::new();

        // 1. Apply candidate action at current step
        let hero_orders = QGuidedDispatcherPolicy::get_market_orders(action_id);
        let opp_act = opp_policy.act(&sim_state, 1 - player_idx);

        let mut hero_act = rollout_policy.act(&sim_state, player_idx);
        hero_act.market = hero_orders;

        let actions = if player_idx == 0 {
            [hero_act, opp_act]
        } else {
            [opp_act, hero_act]
        };

        step_game(&mut sim_state, &actions);

        // 2. Rollout to terminal (step 720)
        while !sim_state.done {
            let a0 = rollout_policy.act(&sim_state, 0);
            let a1 = opp_policy.act(&sim_state, 1);
            step_game(&mut sim_state, &[a0, a1]);
        }

        sim_state.farms[player_idx].money
    }
}

impl Policy for ModelBasedRolloutPolicy {
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

        // 1. Model-Based Search at Key Strategic Decision Windows
        let is_decision_checkpoint = step == 0 || (hour == 0 && (day <= 15 || day % 2 == 0));
        if is_decision_checkpoint {
            let features = QGuidedDispatcherPolicy::extract_features(state, player_idx);
            let mut action_q_pairs = Vec::new();

            for a in 0..12 {
                if QGuidedDispatcherPolicy::is_action_feasible(a, money, quads.len(), farm.hands.len()) {
                    let q_val = self.q_policy.predict_q(&features, a);
                    action_q_pairs.push((a, q_val));
                }
            }

            // Sort by Q-value descending and take Top-K
            action_q_pairs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
            let candidates: Vec<usize> = action_q_pairs.iter().take(self.top_k).map(|&(a, _)| a).collect();

            // Run FastSim terminal evaluation on Top-K candidates
            let mut best_action = 0;
            let mut best_sim_return = -1e9;

            for &cand_a in &candidates {
                let sim_return = Self::evaluate_action_to_terminal(state, player_idx, cand_a);
                if sim_return > best_sim_return {
                    best_sim_return = sim_return;
                    best_action = cand_a;
                }
            }

            let mut orders = QGuidedDispatcherPolicy::get_market_orders(best_action);
            market.append(&mut orders);
        }

        // 2. Real-time Inventory Liquidations
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

        // 3. Physical Worker Routing using EXP180 Target Dispatcher
        let mut tickets: Vec<TargetTicket> = Vec::new();
        let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
        let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
        let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);

        for y in 0..10 {
            for x in 0..10 {
                if !QGuidedDispatcherPolicy::is_tile_unlocked(x, y, quads) { continue; }

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
            else { QGuidedDispatcherPolicy::step_toward(fx, fy, 0, 0) }
        } else if let Some(ticket) = tickets.iter().find(|t| matches!(t.task, TaskType::CollectFertilizer | TaskType::Feed | TaskType::Harvest | TaskType::Care)) {
            if fx == ticket.x && fy == ticket.y {
                match ticket.task {
                    TaskType::CollectFertilizer => UnitAction::CollectFertilizer,
                    TaskType::Feed => {
                        if farmer_wheat > 0 { UnitAction::Feed }
                        else if *priv_farm.shed.get("WHEAT").unwrap_or(&0) > 0 {
                            if fx == 0 && fy == 0 { UnitAction::Pickup("WHEAT".to_string(), 2) }
                            else { QGuidedDispatcherPolicy::step_toward(fx, fy, 0, 0) }
                        } else { UnitAction::Care }
                    }
                    TaskType::Harvest => UnitAction::Harvest,
                    TaskType::Care => UnitAction::Care,
                    _ => UnitAction::Pass,
                }
            } else {
                QGuidedDispatcherPolicy::step_toward(fx, fy, ticket.x, ticket.y)
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
                else { hands_actions.push(QGuidedDispatcherPolicy::step_toward(hx, hy, 0, 0)); }
            } else if let Some(ticket) = plant_and_water_tickets.get(h_idx % plant_and_water_tickets.len().max(1)) {
                if hx == ticket.x && hy == ticket.y {
                    match ticket.task {
                        TaskType::Water => hands_actions.push(UnitAction::Water),
                        TaskType::Plant(crop) => hands_actions.push(UnitAction::Plant(crop)),
                        _ => hands_actions.push(UnitAction::Pass),
                    }
                } else {
                    hands_actions.push(QGuidedDispatcherPolicy::step_toward(hx, hy, ticket.x, ticket.y));
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
