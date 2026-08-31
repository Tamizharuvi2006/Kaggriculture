//! EXP177 — Wheat -> Fertilizer -> High-Value Crop Closed-Loop Causal Reconstruction Harness.

use fastsim::engine::state::GameState;
use fastsim::engine::step::{step_game, PlayerAction};
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::workers::UnitAction;
use fastsim::farm::{Animal, Tile, Crop};
use rayon::prelude::*;
use std::collections::HashMap;
use std::time::Instant;

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum LoopArmType {
    ArmAControl,
    ArmBFertilizerApplicationOnly,
    ArmCSafeWheatFeed,
    ArmDActiveManureRecycling,
    ArmEMicroLivestockSurplus,
    ArmFBorderWheatLoop,
}

pub struct EXP177Policy {
    base: AdaptiveTerminalPolicy,
    arm_type: LoopArmType,
}

impl EXP177Policy {
    pub fn new(arm_type: LoopArmType) -> Self {
        Self {
            base: AdaptiveTerminalPolicy::new(),
            arm_type,
        }
    }
}

impl Policy for EXP177Policy {
    fn name(&self) -> &'static str {
        match self.arm_type {
            LoopArmType::ArmAControl => "arm_a_control",
            LoopArmType::ArmBFertilizerApplicationOnly => "arm_b_fert_apply",
            LoopArmType::ArmCSafeWheatFeed => "arm_c_safe_feed",
            LoopArmType::ArmDActiveManureRecycling => "arm_d_manure_loop",
            LoopArmType::ArmEMicroLivestockSurplus => "arm_e_micro_expansion",
            LoopArmType::ArmFBorderWheatLoop => "arm_f_border_wheat",
        }
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut act = self.base.act(state, player_idx);
        let step = state.step;
        let day = state.day;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        if self.arm_type == LoopArmType::ArmAControl {
            return act;
        }

        // ARM B & HIGHER: Retain fertilizer in shed instead of selling into market if we have active Strawberry crops
        if self.arm_type != LoopArmType::ArmAControl {
            let has_strawberry = farm.tiles.iter().flatten().any(|t| {
                if let Tile::Plant(p) = t { p.crop == Crop::Strawberry } else { false }
            });

            if has_strawberry {
                // Suppress raw market selling of Fertilizer so we can use it to double strawberry yields!
                act.market.retain(|order| {
                    if let MarketOrder::Sell(Product::Fertilizer, _) = order {
                        false
                    } else {
                        true
                    }
                });
            }
        }

        // ARM D & HIGHER: Active Manure Collection & Livestock Feeding
        if matches!(self.arm_type, LoopArmType::ArmDActiveManureRecycling | LoopArmType::ArmEMicroLivestockSurplus | LoopArmType::ArmFBorderWheatLoop) {
            // Count livestock
            let mut cows = 0;
            let mut sheep = 0;
            for row in &farm.tiles {
                for tile in row {
                    if let Tile::Animal(a) = tile {
                        if a.animal == Animal::Cow { cows += 1; }
                        else if a.animal == Animal::Sheep { sheep += 1; }
                    }
                }
            }

            // Feed livestock ONLY if we have safe cash buffer
            let safe_cash = if day < 10 { 800.0 } else { 400.0 };
            if (cows + sheep) > 0 && money >= safe_cash {
                let wheat_in_shed = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
                if wheat_in_shed < (cows as i64 + sheep as i64) * 2 {
                    act.market.push(MarketOrder::BuyProduct(Product::Wheat, (cows as i64 + sheep as i64) * 2));
                }
            }
        }

        // ARM E: Micro-Livestock Addition strictly out of excess cash surplus (Step >= 168, Money >= $3,000)
        if self.arm_type == LoopArmType::ArmEMicroLivestockSurplus {
            if step >= 168 && money >= 3000.0 && farm.unlocked_quadrants.len() >= 2 {
                let mut total_cows = 0;
                for row in &farm.tiles {
                    for tile in row {
                        if let Tile::Animal(a) = tile {
                            if a.animal == Animal::Cow { total_cows += 1; }
                        }
                    }
                }
                let cows_in_shed = *priv_farm.shed.get("COW").unwrap_or(&0) as usize;
                if total_cows + cows_in_shed < 5 {
                    act.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
                }
            }
        }

        // ARM F: Border Wheat Planting on outer edge tiles
        if self.arm_type == LoopArmType::ArmFBorderWheatLoop {
            if day < 10 && money >= 500.0 {
                let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);
                if wheat_seeds < 4 {
                    act.market.push(MarketOrder::BuySeed(Crop::Wheat, 4 - wheat_seeds));
                }
            }
        }

        act
    }
}

#[derive(Clone, Debug, Default)]
pub struct DetailedBalanceSheet {
    pub arm_name: &'static str,
    pub total_matches: usize,
    pub wins: usize,
    pub ties: usize,
    pub losses: usize,
    pub mean_reward: f64,
    pub ctrl_mean_reward: f64,
    pub delta_margin: f64,
    
    // Balance Sheet
    pub avg_cash_d1: f64,
    pub avg_cash_d5: f64,
    pub avg_cash_d10: f64,
    pub avg_cash_d15: f64,
    pub avg_cash_d20: f64,
    pub avg_cash_d25: f64,
    pub avg_cash_d30: f64,
    pub min_runway_cash: f64,

    // Production breakdown
    pub straw_revenue: f64,
    pub fert_applied_count: f64,
    pub fert_sold_rev: f64,
    pub milk_rev: f64,
    pub wheat_feed_cost: f64,
}

pub fn run_arm_evaluation(arm_type: LoopArmType, seeds: &[u64]) -> DetailedBalanceSheet {
    let hero_policy = EXP177Policy::new(arm_type);
    let control_policy = AdaptiveTerminalPolicy::new();

    let mut tasks = Vec::new();
    for &seed in seeds {
        tasks.push((seed, 0));
        tasks.push((seed, 1));
    }

    let results: Vec<(f64, f64, [f64; 7], f64)> = tasks.into_par_iter().map(|(seed, seat)| {
        let opp_seat = 1 - seat;

        // Run Control
        let mut ctrl_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !ctrl_state.done && ctrl_state.step < 720 {
            let a0 = control_policy.act(&ctrl_state, seat);
            let a1 = control_policy.act(&ctrl_state, opp_seat);
            let actions = if seat == 0 { [a0, a1] } else { [a1, a0] };
            step_game(&mut ctrl_state, &actions);
        }
        let ctrl_reward = ctrl_state.farms[seat].money;

        // Run Hero Arm
        let mut hero_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let mut day_cash = [0.0; 7]; // Days 1, 5, 10, 15, 20, 25, 30
        let days_idx = [1, 5, 10, 15, 20, 25, 29];
        let mut min_cash: f64 = 3000.0;

        while !hero_state.done && hero_state.step < 720 {
            let day = hero_state.day;
            let cash = hero_state.farms[seat].money;
            min_cash = min_cash.min(cash);

            for (i, &d) in days_idx.iter().enumerate() {
                if day == d && hero_state.hour == 0 {
                    day_cash[i] = cash;
                }
            }

            let a0 = hero_policy.act(&hero_state, seat);
            let a1 = control_policy.act(&hero_state, opp_seat);
            let actions = if seat == 0 { [a0, a1] } else { [a1, a0] };
            step_game(&mut hero_state, &actions);
        }
        day_cash[6] = hero_state.farms[seat].money;
        let hero_reward = hero_state.farms[seat].money;

        (hero_reward, ctrl_reward, day_cash, min_cash)
    }).collect();

    let total = results.len();
    let mut wins = 0;
    let mut ties = 0;
    let mut losses = 0;
    let mut sum_hero = 0.0;
    let mut sum_ctrl = 0.0;
    let mut avg_cash = [0.0; 7];
    let mut avg_min_cash = 0.0;

    for (h, c, dc, mc) in &results {
        sum_hero += h;
        sum_ctrl += c;
        avg_min_cash += mc;
        for i in 0..7 {
            avg_cash[i] += dc[i];
        }

        if *h > *c + 1.0 { wins += 1; }
        else if *c > *h + 1.0 { losses += 1; }
        else { ties += 1; }
    }

    for i in 0..7 {
        avg_cash[i] /= total as f64;
    }

    let mean_reward = sum_hero / total as f64;
    let ctrl_mean_reward = sum_ctrl / total as f64;

    DetailedBalanceSheet {
        arm_name: hero_policy.name(),
        total_matches: total,
        wins,
        ties,
        losses,
        mean_reward,
        ctrl_mean_reward,
        delta_margin: mean_reward - ctrl_mean_reward,
        avg_cash_d1: avg_cash[0],
        avg_cash_d5: avg_cash[1],
        avg_cash_d10: avg_cash[2],
        avg_cash_d15: avg_cash[3],
        avg_cash_d20: avg_cash[4],
        avg_cash_d25: avg_cash[5],
        avg_cash_d30: avg_cash[6],
        min_runway_cash: avg_min_cash / total as f64,
        ..Default::default()
    }
}

fn main() {
    println!("================================================================================");
    println!("EXP177: CLOSED-LOOP WHEAT -> FERTILIZER -> HIGH-VALUE CROP CAUSAL SEARCH");
    println!("================================================================================");

    let arms = [
        (LoopArmType::ArmAControl, "Arm A: Control (Candidate AdaptiveTerminal)"),
        (LoopArmType::ArmBFertilizerApplicationOnly, "Arm B: Fertilizer Retention & Application (Strawberry Boost)"),
        (LoopArmType::ArmCSafeWheatFeed, "Arm C: Safe-Runway Wheat Feed Retention"),
        (LoopArmType::ArmDActiveManureRecycling, "Arm D: Active 4-Cow Manure Recycling Loop"),
        (LoopArmType::ArmEMicroLivestockSurplus, "Arm E: Micro-Expansion (+1 Cow on Cash Surplus)"),
        (LoopArmType::ArmFBorderWheatLoop, "Arm F: Dedicated Border-Wheat Feed Loop"),
    ];

    let screening_seeds: Vec<u64> = (1000..2000).collect(); // 1,000 seeds x 2 seats = 2,000 matches per arm
    println!("PHASE 1: Screening Sweep (2,000 matches per arm across {} arms)...", arms.len());
    let t0 = Instant::now();

    let mut sheets = Vec::new();
    for &(arm_type, desc) in &arms {
        let sheet = run_arm_evaluation(arm_type, &screening_seeds);
        let wr = (sheet.wins as f64 / sheet.total_matches as f64) * 100.0;
        println!("\n>>> {}", desc);
        println!("    Matches: {} | Win Rate: {:5.1}% | Ties: {:4.1}%", sheet.total_matches, wr, (sheet.ties as f64 / sheet.total_matches as f64) * 100.0);
        println!("    Reward : ${:7.1} vs Ctrl: ${:7.1} (Delta: {:+6.1})", sheet.mean_reward, sheet.ctrl_mean_reward, sheet.delta_margin);
        println!("    Runway : D1=${:.0}, D5=${:.0}, D10=${:.0}, D15=${:.0}, D20=${:.0}, D25=${:.0}, Min=${:.0}",
            sheet.avg_cash_d1, sheet.avg_cash_d5, sheet.avg_cash_d10, sheet.avg_cash_d15, sheet.avg_cash_d20, sheet.avg_cash_d25, sheet.min_runway_cash
        );
        sheets.push(sheet);
    }

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nScreening complete in {:.2}s ({:.1} matches/sec)!", elapsed, (arms.len() * screening_seeds.len() * 2) as f64 / elapsed);

    // Rank by Delta Margin
    sheets.sort_by(|a, b| b.delta_margin.partial_cmp(&a.delta_margin).unwrap());

    println!("\n================================================================================");
    println!("PHASE 2: RANKED ARMS BY CAUSAL DELTA MARGIN");
    println!("================================================================================");
    for (i, s) in sheets.iter().enumerate() {
        let wr = (s.wins as f64 / s.total_matches as f64) * 100.0;
        println!("#{}: {:25} | WR: {:5.1}% | Mean: ${:7.1} | Delta: {:+6.1} | Min Runway: ${:.0}",
            i + 1, s.arm_name, wr, s.mean_reward, s.delta_margin, s.min_runway_cash
        );
    }
}
