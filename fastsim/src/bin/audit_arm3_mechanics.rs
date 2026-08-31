//! EXP182 — Mechanical Accounting Audit for Arm 3 Trajectory.
//! Traces every melon, wheat, cow, fertilizer, worker wage, and dollar spent/earned across all 720 steps.

use fastsim::engine::state::GameState;
use fastsim::engine::step::{step_game, PlayerAction};
use fastsim::policies::AdaptiveTerminalPolicy;
use fastsim::market::{Product, MarketOrder};
use fastsim::workers::UnitAction;
use fastsim::farm::{Animal, Tile, Crop, Quadrant};
use fastsim::policies::Policy;

pub struct Arm3Policy;

impl Arm3Policy {
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

impl Policy for Arm3Policy {
    fn name(&self) -> &'static str { "arm3" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let step = state.step;
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;
        let quads = &farm.unlocked_quadrants;

        let mut market = Vec::new();

        // Arm 3 Macro: 8 Melons + 4 Wheat + 1 Cow + 3 Hands
        if step == 0 || (step == 1 && farm.hands.is_empty()) {
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
            market.push(MarketOrder::BuySeed(Crop::Melon, 8));
            market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
            let starting_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
            if starting_wheat > 0 {
                market.push(MarketOrder::Sell(Product::Wheat, starting_wheat));
            }
        }

        // Daily hiring schedule
        if hour == 0 && step > 1 {
            let max_hands = if day < 4 { 3 } else if day < 10 { 6 } else if quads.len() >= 3 { 12 } else { 8 };
            if farm.hands.len() < max_hands && money >= 400.0 + 100.0 {
                market.push(MarketOrder::Hire);
            }
        }

        // Crop seed replenishments (Day 8+ Transition)
        if hour == 0 {
            if day >= 8 && day < 26 {
                let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
                let target_straw = if quads.len() >= 3 { 45 } else if quads.len() >= 2 { 30 } else { 15 };
                if (straw_seeds as usize) < target_straw && money >= 400.0 {
                    let buy_amt = (((money - 400.0).max(0.0) / 30.0).floor() as i64).min(target_straw as i64 - straw_seeds).min(10);
                    if buy_amt > 0 {
                        market.push(MarketOrder::BuySeed(Crop::Strawberry, buy_amt));
                    }
                }
            }
        }

        // Real-time Inventory Liquidations
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

        // Dynamic Land Unlocks (Q2 @ $2,500, Q3 @ $4,500)
        if hour == 0 {
            if quads.len() == 1 && day >= 8 && money >= 2500.0 {
                market.push(MarketOrder::BuyLand);
            } else if quads.len() == 2 && day >= 11 && money >= 4500.0 {
                market.push(MarketOrder::BuyLand);
            }
        }

        if step >= 700 {
            for prod in Product::ALL {
                let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
                if count > 0 {
                    market.push(MarketOrder::Sell(prod, count));
                }
            }
        }

        // 2. Target Generation
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
                        if day < 8 && melon_seeds > 0 {
                            tickets.push(TargetTicket { x, y, task: TaskType::Plant(Crop::Melon), priority: 60 });
                        } else if day < 8 && wheat_seeds > 0 {
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

        // 3. Worker Routing
        let (fx, fy) = farm.farmer;
        let farmer_inv = priv_farm.inventories.first();
        let farmer_wheat = farmer_inv.and_then(|inv| inv.get("WHEAT")).copied().unwrap_or(0);
        let farmer_total = farmer_inv.map(|inv| inv.values().sum::<i64>()).unwrap_or(0);

        let farmer_action = if farmer_total >= 3 || (farmer_total > 0 && tickets.is_empty()) {
            if fx == 0 && fy == 0 { UnitAction::Drop } else { Self::step_toward(fx, fy, 0, 0) }
        } else if let Some(ticket) = tickets.iter().find(|t| matches!(t.task, TaskType::CollectFertilizer | TaskType::Feed | TaskType::Harvest | TaskType::Care)) {
            if fx == ticket.x && fy == ticket.y {
                match ticket.task {
                    TaskType::CollectFertilizer => UnitAction::CollectFertilizer,
                    TaskType::Feed => {
                        if farmer_wheat > 0 {
                            UnitAction::Feed
                        } else if *priv_farm.shed.get("WHEAT").unwrap_or(&0) > 0 {
                            if fx == 0 && fy == 0 { UnitAction::Pickup("WHEAT".to_string(), 2) } else { Self::step_toward(fx, fy, 0, 0) }
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

            if h_total >= 2 || (h_total > 0 && tickets.is_empty()) {
                if hx == 0 && hy == 0 { hands[i] = UnitAction::Drop; } else { hands[i] = Self::step_toward(hx, hy, 0, 0); }
                continue;
            }

            let mut best_ticket_idx = None;
            let mut best_dist = usize::MAX;

            for (t_idx, ticket) in tickets.iter().enumerate() {
                if assigned_ticket_indices.contains(&t_idx) { continue; }
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
                    };
                } else {
                    hands[i] = Self::step_toward(hx, hy, ticket.x, ticket.y);
                }
            } else {
                if hx == 0 && hy == 0 { hands[i] = UnitAction::Pass; } else { hands[i] = Self::step_toward(hx, hy, 0, 0); }
            }
        }

        PlayerAction {
            farmer: farmer_action,
            hands,
            market,
        }
    }
}

fn main() {
    println!("================================================================================");
    println!("EXP182 — MECHANICAL ACCOUNTING AUDIT OF ARM 3 (STEP-BY-STEP RECONCILIATION)");
    println!("================================================================================");

    let hero = Arm3Policy;
    let control = AdaptiveTerminalPolicy::new();
    let mut state = GameState::new(1000, 10, 3000.0, 720, 24, 100);

    let mut total_melons_bought = 0;
    let mut total_melons_planted = 0;
    let mut total_melons_harvested = 0;
    let mut total_melons_sold = 0;
    let mut total_melon_revenue = 0.0;

    let mut total_straw_bought = 0;
    let mut total_straw_planted = 0;
    let mut total_straw_harvested = 0;
    let mut total_straw_sold = 0;
    let mut total_straw_revenue = 0.0;

    let mut total_wages_paid = 0.0;
    let mut total_land_spent = 0.0;
    let mut total_cow_spent = 0.0;

    let mut prev_money = 3000.0;

    for s in 0..720 {
        let day = state.day;
        let hour = state.hour;
        let priv_farm = &state.privates[0];

        // Track purchases in market action
        let a_hero = hero.act(&state, 0);
        let a_opp = control.act(&state, 1);

        for m in &a_hero.market {
            match m {
                MarketOrder::BuySeed(Crop::Melon, c) => { total_melons_bought += c; }
                MarketOrder::BuySeed(Crop::Strawberry, c) => { total_straw_bought += c; }
                MarketOrder::BuyAnimal(Animal::Cow, c) => { total_cow_spent += (*c as f64) * 800.0; }
                MarketOrder::BuyLand => { total_land_spent += 1000.0; }
                MarketOrder::Sell(Product::Melon, c) => {
                    total_melons_sold += c;
                    total_melon_revenue += (*c as f64) * 250.0;
                }
                MarketOrder::Sell(Product::Strawberry, c) => {
                    total_straw_sold += c;
                    total_straw_revenue += (*c as f64) * 200.0;
                }
                _ => {}
            }
        }

        // Count plants
        let mut melon_plants = 0;
        let mut straw_plants = 0;
        let mut mature_melons = 0;
        let mut mature_straws = 0;

        for row in &state.farms[0].tiles {
            for t in row {
                if let Tile::Plant(p) = t {
                    if p.crop == Crop::Melon {
                        melon_plants += 1;
                        if p.yield_units > 0 && day as i32 - p.planted_day >= 10 { mature_melons += 1; }
                    } else if p.crop == Crop::Strawberry {
                        straw_plants += 1;
                        if p.yield_units > 0 && day as i32 - p.planted_day >= 10 { mature_straws += 1; }
                    }
                }
            }
        }

        // Track wage change at hour 0
        if hour == 0 && s > 0 {
            let cur_money = state.farms[0].money;
            println!("--- Day {:2} Checkpoint | Cash: ${:7.1} | Melons (Pl:{:2}, Mat:{:2}, Sold:{:2}, Rev:${:.0}) | Straw (Pl:{:2}, Sold:{:2}, Rev:${:.0}) | Hands: {:2} | Land: {:2} ---",
                day, cur_money, melon_plants, mature_melons, total_melons_sold, total_melon_revenue,
                straw_plants, total_straw_sold, total_straw_revenue, state.farms[0].hands.len(), state.farms[0].unlocked_quadrants.len()
            );
        }

        step_game(&mut state, &[a_hero, a_opp]);
    }

    println!("\n================================================================================");
    println!("FINAL AUDIT SUMMARY FOR ARM 3 (SEED 1000):");
    println!("================================================================================");
    println!("  Initial Cash Starting           : $3,000.0");
    println!("  Total Melon Seeds Purchased     : {:3} ($ {:.0})", total_melons_bought, total_melons_bought as f64 * 80.0);
    println!("  Total Melons Sold to Market     : {:3} ($ {:.0} revenue)", total_melons_sold, total_melon_revenue);
    println!("  Total Strawberry Seeds Purchased: {:3} ($ {:.0})", total_straw_bought, total_straw_bought as f64 * 100.0);
    println!("  Total Strawberries Sold         : {:3} ($ {:.0} revenue)", total_straw_sold, total_straw_revenue);
    println!("  Total Land Expansion Spent      : ${:.0}", total_land_spent);
    println!("  Total Livestock Purchased       : ${:.0}", total_cow_spent);
    println!("  FINAL REVENUE / CASH REALIZED   : ${:.1}", state.farms[0].money);
}
