//! EXP181 — Offline Counterfactual Value Search & RL Preparation Harness.
//! Evaluates parameterized Day 0-12 macro decisions against AdaptiveTerminal across 60,000+ paired matches.

use fastsim::engine::state::GameState;
use fastsim::engine::step::{step_game, PlayerAction};
use fastsim::policies::{AdaptiveTerminalPolicy, Policy};
use fastsim::market::{Product, MarketOrder};
use fastsim::workers::UnitAction;
use fastsim::farm::{Animal, Tile, Crop, Quadrant};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct MacroSearchArm {
    pub id: usize,
    pub name: &'static str,
    pub melon_seeds: usize,
    pub wheat_seeds: usize,
    pub buy_cow_day0: bool,
    pub initial_hands: usize,
    pub straw_transition_day: usize,
    pub q2_cash_threshold: f64,
    pub q3_cash_threshold: f64,
    pub liquidity_buffer: f64,
}

pub struct ParametricDispatcherPolicy {
    config: MacroSearchArm,
}

impl ParametricDispatcherPolicy {
    pub fn new(config: MacroSearchArm) -> Self {
        Self { config }
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

impl Policy for ParametricDispatcherPolicy {
    fn name(&self) -> &'static str {
        self.config.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let step = state.step;
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;
        let quads = &farm.unlocked_quadrants;
        let cfg = &self.config;

        let mut market = Vec::new();

        // 1. Day 0 Macro Allocation
        if step == 0 || (step == 1 && farm.hands.is_empty()) {
            for _ in 0..cfg.initial_hands {
                market.push(MarketOrder::Hire);
            }
            if cfg.buy_cow_day0 {
                market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
            }
            if cfg.melon_seeds > 0 {
                market.push(MarketOrder::BuySeed(Crop::Melon, cfg.melon_seeds as i64));
            }
            if cfg.wheat_seeds > 0 {
                market.push(MarketOrder::BuySeed(Crop::Wheat, cfg.wheat_seeds as i64));
            }
            let starting_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
            if starting_wheat > 0 {
                market.push(MarketOrder::Sell(Product::Wheat, starting_wheat));
            }
        }

        // Daily hiring schedule
        if hour == 0 && step > 1 {
            let max_hands = if day < 4 { cfg.initial_hands } else if day < 10 { 6 } else if quads.len() >= 3 { 12 } else { 8 };
            if farm.hands.len() < max_hands && money >= cfg.liquidity_buffer + 100.0 {
                market.push(MarketOrder::Hire);
            }
        }

        // Crop seed replenishments
        if hour == 0 {
            if day >= cfg.straw_transition_day && day < 26 {
                let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
                let target_straw = if quads.len() >= 3 { 45 } else if quads.len() >= 2 { 30 } else { 15 };
                if (straw_seeds as usize) < target_straw && money >= cfg.liquidity_buffer {
                    let buy_amt = (((money - cfg.liquidity_buffer).max(0.0) / 30.0).floor() as i64).min(target_straw as i64 - straw_seeds).min(10);
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

        // Dynamic Land Unlocks
        if hour == 0 {
            if quads.len() == 1 && day >= 8 && money >= cfg.q2_cash_threshold {
                market.push(MarketOrder::BuyLand);
            } else if quads.len() == 2 && day >= 11 && money >= cfg.q3_cash_threshold {
                market.push(MarketOrder::BuyLand);
            }
        }

        // Terminal clearance at Step 700..719
        if step >= 700 {
            for prod in Product::ALL {
                let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
                if count > 0 {
                    market.push(MarketOrder::Sell(prod, count));
                }
            }
        }

        // 2. Target Generation & Dispatch Queue
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
                        if day < cfg.straw_transition_day && melon_seeds > 0 {
                            tickets.push(TargetTicket { x, y, task: TaskType::Plant(Crop::Melon), priority: 60 });
                        } else if day < cfg.straw_transition_day && wheat_seeds > 0 {
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
    println!("EXP181 — OFFLINE COUNTERFACTUAL VALUE SEARCH (60,000+ MATCHES / 12 THREADS)");
    println!("================================================================================");

    let arms = [
        MacroSearchArm { id: 1, name: "Arm 1: Pure Melon Kickstart (6M + 0W, Cow, Tr:D6, Q2:$2.0k)", melon_seeds: 6, wheat_seeds: 0, buy_cow_day0: true, initial_hands: 2, straw_transition_day: 6, q2_cash_threshold: 2000.0, q3_cash_threshold: 4000.0, liquidity_buffer: 300.0 },
        MacroSearchArm { id: 2, name: "Arm 2: Dual Melon+Wheat (6M + 6W, Cow, Tr:D6, Q2:$2.0k)", melon_seeds: 6, wheat_seeds: 6, buy_cow_day0: true, initial_hands: 2, straw_transition_day: 6, q2_cash_threshold: 2000.0, q3_cash_threshold: 4000.0, liquidity_buffer: 300.0 },
        MacroSearchArm { id: 3, name: "Arm 3: High-Melon Engine (8M + 4W, Cow, Tr:D8, Q2:$2.5k)", melon_seeds: 8, wheat_seeds: 4, buy_cow_day0: true, initial_hands: 3, straw_transition_day: 8, q2_cash_threshold: 2500.0, q3_cash_threshold: 4500.0, liquidity_buffer: 400.0 },
        MacroSearchArm { id: 4, name: "Arm 4: Early Strawberry Transition (4M + 4W, Cow, Tr:D4, Q2:$1.8k)", melon_seeds: 4, wheat_seeds: 4, buy_cow_day0: true, initial_hands: 2, straw_transition_day: 4, q2_cash_threshold: 1800.0, q3_cash_threshold: 3500.0, liquidity_buffer: 300.0 },
        MacroSearchArm { id: 5, name: "Arm 5: No-Cow Pure Crop Kickstart (8M + 6W, NoCow, Tr:D6, Q2:$2.0k)", melon_seeds: 8, wheat_seeds: 6, buy_cow_day0: false, initial_hands: 3, straw_transition_day: 6, q2_cash_threshold: 2000.0, q3_cash_threshold: 4000.0, liquidity_buffer: 300.0 },
        MacroSearchArm { id: 6, name: "Arm 6: Aggressive Land Scaling (6M + 6W, Cow, Tr:D6, Q2:$1.5k, Q3:$3.0k)", melon_seeds: 6, wheat_seeds: 6, buy_cow_day0: true, initial_hands: 2, straw_transition_day: 6, q2_cash_threshold: 1500.0, q3_cash_threshold: 3000.0, liquidity_buffer: 200.0 },
    ];

    let seeds: Vec<u64> = (1000..6000).collect(); // 5,000 seeds x 2 seats = 10,000 matches PER ARM (60,000 total)
    let control = AdaptiveTerminalPolicy::new();

    for arm in &arms {
        let hero = ParametricDispatcherPolicy::new(*arm);
        let t0 = Instant::now();

        let mut tasks = Vec::new();
        for &seed in &seeds {
            tasks.push((seed, 0));
            tasks.push((seed, 1));
        }

        let results: Vec<(f64, f64, [f64; 6])> = tasks.into_par_iter().map(|(seed, seat)| {
            let opp_seat = 1 - seat;
            let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
            let mut day_cash = [0.0; 6];
            let check_days = [1, 4, 7, 11, 15, 29];

            while !state.done && state.step < 720 {
                let day = state.day;
                let cash = state.farms[seat].money;
                for (i, &d) in check_days.iter().enumerate() {
                    if day == d && state.hour == 0 {
                        day_cash[i] = cash;
                    }
                }

                let a_hero = hero.act(&state, seat);
                let a_opp = control.act(&state, opp_seat);
                let actions = if seat == 0 { [a_hero, a_opp] } else { [a_opp, a_hero] };
                step_game(&mut state, &actions);
            }
            day_cash[5] = state.farms[seat].money;

            (state.farms[seat].money, state.farms[opp_seat].money, day_cash)
        }).collect();

        let total = results.len();
        let mut wins = 0;
        let mut sum_hero = 0.0;
        let mut sum_ctrl = 0.0;
        let mut avg_cash = [0.0; 6];

        for (h, c, dc) in &results {
            sum_hero += h;
            sum_ctrl += c;
            for i in 0..6 { avg_cash[i] += dc[i]; }
            if *h > *c + 1.0 { wins += 1; }
        }

        for i in 0..6 { avg_cash[i] /= total as f64; }

        let elapsed = t0.elapsed().as_secs_f64();
        let mean_hero = sum_hero / total as f64;
        let mean_ctrl = sum_ctrl / total as f64;
        let wr = (wins as f64 / total as f64) * 100.0;

        println!("\n>>> {}", arm.name);
        println!("    Matches: {} in {:.2}s ({:.1} eps/s) | Win Rate: {:4.1}%", total, elapsed, total as f64 / elapsed, wr);
        println!("    Reward : Hero ${:7.1} vs Ctrl ${:7.1} | Delta: {:+6.1}", mean_hero, mean_ctrl, mean_hero - mean_ctrl);
        println!("    Cash   : D1=${:.0}, D4=${:.0}, D7=${:.0}, D11=${:.0}, D15=${:.0}, D30=${:.0}",
            avg_cash[0], avg_cash[1], avg_cash[2], avg_cash[3], avg_cash[4], avg_cash[5]
        );
    }
}
