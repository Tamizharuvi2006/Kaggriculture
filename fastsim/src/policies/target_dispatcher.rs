//! EXP180 — Target Dispatch & Deterministic Motion Router Policy (Immediate Shed Deposit & Cash Realization).

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop, Quadrant};
use crate::policies::Policy;

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum TaskType {
    Harvest,
    Water,
    Plant(Crop),
    Feed,
    CollectFertilizer,
    DropAtShed,
    Care,
}

#[derive(Clone, Debug)]
pub struct TargetTicket {
    pub x: usize,
    pub y: usize,
    pub task: TaskType,
    pub priority: i32,
}

pub struct TargetDispatcherPolicy {
    name: &'static str,
}

impl TargetDispatcherPolicy {
    pub fn new() -> Self {
        Self {
            name: "target_dispatcher_v1",
        }
    }

    /// Compute BFS / Manhattan single step from (from_x, from_y) to (to_x, to_y)
    pub fn step_toward(from_x: usize, from_y: usize, to_x: usize, to_y: usize) -> UnitAction {
        if from_x < to_x {
            UnitAction::East
        } else if from_x > to_x {
            UnitAction::West
        } else if from_y < to_y {
            UnitAction::South
        } else if from_y > to_y {
            UnitAction::North
        } else {
            UnitAction::Pass
        }
    }

    /// Check if tile (x, y) is inside unlocked land quadrants
    pub fn is_tile_unlocked(x: usize, y: usize, unlocked: &[Quadrant]) -> bool {
        let quad = Quadrant::of(x, y, 10);
        unlocked.contains(&quad)
    }
}

impl Policy for TargetDispatcherPolicy {
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

        // =========================================================================
        // 1. MACRO ECONOMIC CONTROLLER (GRANDMASTER WATERFALL)
        // =========================================================================

        // Step 0: Initial Grandmaster Melon + Wheat Kickstart Opening
        if step == 0 || (step == 1 && farm.hands.is_empty()) {
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
            market.push(MarketOrder::BuySeed(Crop::Melon, 6));
            market.push(MarketOrder::BuySeed(Crop::Wheat, 6));
            let starting_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
            if starting_wheat > 0 {
                market.push(MarketOrder::Sell(Product::Wheat, starting_wheat));
            }
        }

        // Daily hiring schedule: scale workers smoothly with available capital
        if hour == 0 && step > 1 {
            let max_hands = if day < 4 { 3 } else if day < 10 { 6 } else if quads.len() >= 3 { 12 } else { 8 };
            if farm.hands.len() < max_hands && money >= 300.0 {
                market.push(MarketOrder::Hire);
            }
        }

        // Mid-game crop seed replenishments
        if hour == 0 {
            if day >= 4 && day < 10 {
                let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
                if straw_seeds < 6 && money >= 800.0 {
                    market.push(MarketOrder::BuySeed(Crop::Strawberry, 3));
                }
            } else if day >= 10 && day < 26 {
                let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
                let target_straw = if quads.len() >= 3 { 50 } else if quads.len() >= 2 { 35 } else { 18 };
                if (straw_seeds as usize) < target_straw && money >= 400.0 {
                    let buy_amt = ((money / 30.0).floor() as i64).min(target_straw as i64 - straw_seeds).min(10);
                    if buy_amt > 0 {
                        market.push(MarketOrder::BuySeed(Crop::Strawberry, buy_amt));
                    }
                }
            }
        }

        // Real-time Inventory Liquidations (Instant Cash Capture)
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

        // Dynamic Land Unlocks: Q2 on Day 10+ (funded by Day 10 Melon harvest), Q3 on Day 13+
        if hour == 0 {
            if quads.len() == 1 && day >= 10 && money >= 2500.0 {
                market.push(MarketOrder::BuyLand);
            } else if quads.len() == 2 && day >= 13 && money >= 4500.0 {
                market.push(MarketOrder::BuyLand);
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
        // 2. TARGET TASK GENERATION & DISPATCH QUEUE
        // =========================================================================

        let mut tickets: Vec<TargetTicket> = Vec::new();

        let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
        let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
        let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);

        for y in 0..10 {
            for x in 0..10 {
                if !Self::is_tile_unlocked(x, y, quads) {
                    continue;
                }

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

        // =========================================================================
        // 3. PHYSICAL WORKER ROUTING & EXECUTION
        // =========================================================================

        let (fx, fy) = farm.farmer;
        let farmer_inv = priv_farm.inventories.first();
        let farmer_wheat = farmer_inv.and_then(|inv| inv.get("WHEAT")).copied().unwrap_or(0);
        let farmer_total = farmer_inv.map(|inv| inv.values().sum::<i64>()).unwrap_or(0);

        let farmer_action = if farmer_total >= 3 || (farmer_total > 0 && tickets.is_empty()) {
            if fx == 0 && fy == 0 {
                UnitAction::Drop
            } else {
                Self::step_toward(fx, fy, 0, 0)
            }
        } else if let Some(ticket) = tickets.iter().find(|t| matches!(t.task, TaskType::CollectFertilizer | TaskType::Feed | TaskType::Harvest | TaskType::Care)) {
            if fx == ticket.x && fy == ticket.y {
                match ticket.task {
                    TaskType::CollectFertilizer => UnitAction::CollectFertilizer,
                    TaskType::Feed => {
                        if farmer_wheat > 0 {
                            UnitAction::Feed
                        } else if *priv_farm.shed.get("WHEAT").unwrap_or(&0) > 0 {
                            if fx == 0 && fy == 0 {
                                UnitAction::Pickup("WHEAT".to_string(), 2)
                            } else {
                                Self::step_toward(fx, fy, 0, 0)
                            }
                        } else {
                            UnitAction::Care
                        }
                    }
                    TaskType::Harvest => UnitAction::Harvest,
                    TaskType::Care => UnitAction::Care,
                    _ => UnitAction::Pass,
                }
            } else {
                Self::step_toward(fx, fy, ticket.x, ticket.y)
            }
        } else if fx == 0 && fy == 0 {
            UnitAction::Pass
        } else {
            Self::step_toward(fx, fy, 0, 0)
        };

        let mut hands = vec![UnitAction::Pass; farm.hands.len()];
        let mut assigned_ticket_indices = Vec::new();

        for (i, &h_pos) in farm.hands.iter().enumerate() {
            let (hx, hy) = h_pos;
            let h_inv = priv_farm.inventories.get(i + 1);
            let h_total = h_inv.map(|inv| inv.values().sum::<i64>()).unwrap_or(0);

            // Immediate Shed Deposit: if carrying any harvested crops or fertilizer, return to shed when free
            if h_total >= 2 || (h_total > 0 && tickets.is_empty()) {
                if hx == 0 && hy == 0 {
                    hands[i] = UnitAction::Drop;
                } else {
                    hands[i] = Self::step_toward(hx, hy, 0, 0);
                }
                continue;
            }

            let mut best_ticket_idx = None;
            let mut best_dist = usize::MAX;

            for (t_idx, ticket) in tickets.iter().enumerate() {
                if assigned_ticket_indices.contains(&t_idx) {
                    continue;
                }
                let dist = (hx.abs_diff(ticket.x)) + (hy.abs_diff(ticket.y));
                if dist < best_dist {
                    best_dist = dist;
                    best_ticket_idx = Some(t_idx);
                }
            }

            if let Some(t_idx) = best_ticket_idx {
                assigned_ticket_indices.push(t_idx);
                let ticket = &tickets[t_idx];

                if hx == ticket.x && hy == ticket.y {
                    hands[i] = match ticket.task {
                        TaskType::Harvest => UnitAction::Harvest,
                        TaskType::Water => UnitAction::Water,
                        TaskType::Plant(c) => UnitAction::Plant(c),
                        TaskType::CollectFertilizer => UnitAction::CollectFertilizer,
                        TaskType::Feed => UnitAction::Feed,
                        TaskType::Care => UnitAction::Care,
                        TaskType::DropAtShed => UnitAction::Drop,
                    };
                } else {
                    hands[i] = Self::step_toward(hx, hy, ticket.x, ticket.y);
                }
            } else {
                if hx == 0 && hy == 0 {
                    hands[i] = UnitAction::Pass;
                } else {
                    hands[i] = Self::step_toward(hx, hy, 0, 0);
                }
            }
        }

        PlayerAction {
            farmer: farmer_action,
            hands,
            market,
        }
    }
}
